#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/run.sh
# (issue #38, Part of #16 -- SG13CMOS5L PVT campaign)
#
# Runs the whole lock_detector campaign this record's ../records/RECORD-001
# describes (spec/porting-plan.md row 16: assert window, hysteresis, chatter;
# plus row 11's lock_detector power domain), and writes five CSVs into
# ../corners/:
#
#   rc_extract.csv    XRPU (rhigh) resistance and the two un-swept cap_cmomi
#                     instances' capacitance -- the R and the C that set the
#                     integrating node's time constant
#   window.csv        the comparator window twin_r / twin_f, per corner, per
#                     MOM band point
#   schmitt.csv       the readout Schmitt's own hysteresis, V_TH+ / V_TH-
#   ladder.csv        one row per corner point: assert threshold, de-assert
#                     threshold, hysteresis, chatter verdict, recovery time,
#                     in-lock and out-of-lock supply current
#   ladder_raw.csv    every ladder point's per-copy settled state and levels
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree.
#
# ---------------------------------------------------------------------------
# TOOLING NOTE -- `set num_threads=1` in the generated .spiceinit.
#
# This is NOT a stylistic choice and removing it makes the campaign
# impractical.  ngspice's OpenMP matrix solve spins on its barriers, and on a
# deck this small (~40 lock_detector copies, still only a few hundred devices)
# the spin dominates: the identical 200 ns transient measured here took
# ~50-95 s wall with the default thread count and 0.55 s with num_threads=1 --
# roughly a 100x difference, and the two runs produce bit-identical measured
# values.  The effect is worse on a loaded host, where the spinning threads
# are also competing with everything else.  This is a general ngspice
# property, not an SG13CMOS5L or PDK issue, so it is recorded here as a
# testbench note rather than filed anywhere upstream.
# ---------------------------------------------------------------------------

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
CORNERS="$RECORD_DIR/corners"
SNAP="$RECORD_DIR/netlist-snapshots/lock_detector.spice"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"

# psp103/psp103_nqs/mosvar for sg13_hv_nmos/pmos, r3_cmc for rhigh, and
# cap_cmomi for the two MOM instances this record exists to sweep.
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
osdi $OSDI/cap_cmomi.osdi
set num_threads=1
EOF

VSUP_NOM=3.3
TRST=1n

# ---------------------------------------------------------------------------
# 1. Device extraction: R (rhigh, XRPU) and C (the two cap_cmomi instances)
# ---------------------------------------------------------------------------
echo "kind,instance,corner,temp_c,w,l,m,value" > "$CORNERS/rc_extract.csv"

for rc in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    sed -e "s/@RES_CORNER@/$rc/g" -e "s/@TEMP@/$temp/g" \
        -e "s/@W@/0.5u/g" -e "s/@L@/6u/g" \
      "$HERE/tb_extract_r.sp.tmpl" > "$WORK/r.sp"
    val="$( ( cd "$WORK" && ngspice -b r.sp ) 2>/dev/null \
            | sed -n 's/^rval *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "R,XRPU(rhigh),${rc},${temp},0.5u,6u,1,${val:-NA}" >> "$CORNERS/rc_extract.csv"
    echo "[R] ${rc}/${temp}C: ${val:-NA} ohm" >&2
  done
done

declare -A CNOM
for geom in "XCW 8u 8u 1" "XDW.XC1 4u 4u 2"; do
  read -r inst w l m <<< "$geom"
  for temp in -40 27 125; do
    sed -e "s/@W@/$w/g" -e "s/@L@/$l/g" -e "s/@M@/$m/g" -e "s/@TEMP@/$temp/g" \
      "$HERE/tb_extract_c.sp.tmpl" > "$WORK/c.sp"
    val="$( ( cd "$WORK" && ngspice -b c.sp ) 2>/dev/null \
            | awk '/^0[[:space:]]/ {print $3; exit}' )"
    echo "C,${inst}(cap_cmomi),none,${temp},${w},${l},${m},${val:-NA}" \
      >> "$CORNERS/rc_extract.csv"
    echo "[C] ${inst}/${temp}C: ${val:-NA} F" >&2
    if [ "$temp" = "27" ]; then CNOM[$inst]="$val"; fi
  done
done

C_XCW="${CNOM[XCW]}"
C_XC1="${CNOM[XDW.XC1]}"
echo "nominal C: XCW=$C_XCW  XDW.XC1=$C_XC1" >&2

# ---------------------------------------------------------------------------
# 2. DUT variants.  `real` is the frozen snapshot byte for byte -- the
#    committed design.  The three `ideal` variants replace both cap_cmomi
#    instances by ideal linear capacitors at 0.8 / 1.0 / 1.2 x their measured
#    nominal value; the 1.0 variant is the control point that separates
#    ideal-vs-real modelling error from the band itself.  See mom_inject.py's
#    header for why the band is expressed this way and not as a parallel delta
#    capacitor.
# ---------------------------------------------------------------------------
python3 "$HERE/mom_inject.py" "$SNAP" "$WORK/dut_real.spice" real
for frac in -0.20 0.00 0.20; do
  python3 "$HERE/mom_inject.py" "$SNAP" "$WORK/dut_ideal${frac}.spice" \
    ideal "$frac" "$C_XCW" "$C_XC1"
done

# ---------------------------------------------------------------------------
# 3. Corner matrix.  Rows: mos res temp vsup fref variant
#    (see ../corners/matrix.md)
# ---------------------------------------------------------------------------
POINTS=()
# Main grid: 5 MOS/RES bundles + 2 resistor-axis isolation points,
#            x 3 temperatures x 4 DUT variants, at 3.3 V / 25 MHz.
for bundle in "mos_tt res_typ" "mos_ss res_wcs" "mos_ff res_bcs" \
              "mos_sf res_typ" "mos_fs res_typ" \
              "mos_tt res_wcs" "mos_tt res_bcs"; do
  read -r mos res <<< "$bundle"
  for temp in -40 27 125; do
    for variant in real ideal-0.20 ideal0.00 ideal0.20; do
      POINTS+=("$mos $res $temp $VSUP_NOM 25e6 $variant")
    done
  done
done
# Supply sub-axis: +/-10% of the 3.3 V rail, at the typical bundle.
for temp in -40 27 125; do
  for vsup in 2.97 3.63; do
    POINTS+=("mos_tt res_typ $temp $vsup 25e6 real")
  done
done
# Reference-frequency sub-axis: the bottom of the ported f_ref range
# (spec/porting-plan.md row 2, 1-25 MHz), at the typical bundle.
for fref in 1e6 5e6; do
  POINTS+=("mos_tt res_typ 27 $VSUP_NOM $fref real")
done

echo "corner_tag,mos_corner,res_corner,temp_c,vsup_v,fref_hz,dut_variant,twin_r_s,twin_f_s" \
  > "$CORNERS/window.csv"
echo "corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,tau_deassert_xwin,hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,lock_max_deep_v,trec_s,vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,ladder_states_discharged_start,ladder_states_charged_start" \
  > "$CORNERS/ladder.csv"
echo "corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,lka_max_v,lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v" \
  > "$CORNERS/ladder_raw.csv"

run_point() {
  local mos="$1" res="$2" temp="$3" vsup="$4" fref="$5" variant="$6" out_ladder="$7"
  local tag="${mos}_${res}_${temp}c_${vsup}v_$(python3 -c "print(int(float('$fref')/1e6))")MHz_${variant}"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
  local dut="$WORK/dut_${variant}.spice"

  # -- comparator window at this corner (also the ladder's scale factor) ----
  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@TEMP@/$temp/g" \
      -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TSTEP@/20p/g" \
      -e "s|@DUT@|$dut|g" \
    "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
  local wlog twin_r twin_f
  wlog="$( ( cd "$WORK" && ngspice -b w.sp ) 2>/dev/null || true )"
  twin_r="$(printf '%s\n' "$wlog" | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  twin_f="$(printf '%s\n' "$wlog" | sed -n 's/^twin_f *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  echo "${tag},${mos},${res},${temp},${vsup},${fref},${variant},${twin_r:-NA},${twin_f:-NA}" \
    >> "$CORNERS/window.csv"

  if [ "$out_ladder" != "yes" ]; then return; fi
  if [ -z "${twin_r:-}" ]; then
    echo "${tag},NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA" \
      >> "$CORNERS/ladder.csv"
    echo "[!] ${tag}: window measurement failed, ladder skipped" >&2
    return
  fi

  # -- phase-error ladder, scaled by this corner's own window --------------
  # tstop = 4 reference periods (the stimulus starts at 1), settle window =
  # the last 2 of them.  The maximum internal timestep is scaled with the
  # reference period so every point in the f_ref sub-axis costs the same;
  # tref/500 was checked against tref/1000 at the typical corner and every
  # reduced number in ladder.csv was identical, so the coarser step is not
  # costing accuracy here (the window itself is measured by the separate,
  # much finer tb_window.sp.tmpl run above, not by this deck).
  local tref tstop tsettle tstep
  read -r tref tstop tsettle tstep <<< "$(python3 -c "
f=float('$fref'); t=1.0/f
print('%.6e %.6e %.6e %.6e' % (t, 4*t, 2*t, t/500))")"

  python3 "$HERE/gen_ladder.py" gen \
    --template "$HERE/tb_lock_ladder.sp.tmpl" --out "$WORK/l.sp" --dut "$dut" \
    --corner-mos "$mos" --corner-res "$res" --temp "$temp" --vsup "$vsup" \
    --tref "$tref" --trst "$TRST" --twin "$twin_r" \
    --tstep "$tstep" --tstop "$tstop" --tsettle "$tsettle" > /dev/null

  ( cd "$WORK" && ngspice -b l.sp ) 2>/dev/null \
    | python3 "$HERE/gen_ladder.py" reduce --tag "$tag" --vsup "$vsup" \
        --twin "$twin_r" --raw "$CORNERS/ladder_raw.csv" \
    >> "$CORNERS/ladder.csv"
  echo "[L] ${tag}: $(tail -1 "$CORNERS/ladder.csv" | cut -d, -f2-10)" >&2
}

n=0
for pt in "${POINTS[@]}"; do
  read -r mos res temp vsup fref variant <<< "$pt"
  run_point "$mos" "$res" "$temp" "$vsup" "$fref" "$variant" yes
  n=$((n + 1))
  echo "  ($n/${#POINTS[@]})" >&2
done

# ---------------------------------------------------------------------------
# 4. Schmitt readout hysteresis, per MOS corner x temperature x supply.
#    (No resistor and no cap_cmomi instance inside schmitt_hv, so neither the
#    RES-corner nor the MOM axis applies to this sub-measurement -- stated in
#    ../corners/matrix.md rather than silently dropped.)
# ---------------------------------------------------------------------------
echo "mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd" \
  > "$CORNERS/schmitt.csv"
for mos in mos_tt mos_ss mos_ff mos_sf mos_fs; do
  for temp in -40 27 125; do
    for vsup in 2.97 3.3 3.63; do
      vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
      sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" \
          -e "s/@VMID@/$vmid/g" -e "s|@DUT@|$WORK/dut_real.spice|g" \
        "$HERE/tb_schmitt_hyst.sp.tmpl" > "$WORK/s.sp"
      slog="$( ( cd "$WORK" && ngspice -b s.sp ) 2>/dev/null || true )"
      vup="$(printf '%s\n' "$slog" | sed -n 's/^vth_up *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
      vdn="$(printf '%s\n' "$slog" | sed -n 's/^vth_dn *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
      row="$(python3 -c "
u='${vup:-}'; d='${vdn:-}'
if u and d:
    h=float(u)-float(d)
    print('%s,%s,%.6e,%.4f' % (u, d, h, 100*h/float('$vsup')))
else:
    print('NA,NA,NA,NA')")"
      echo "${mos},${temp},${vsup},${row}" >> "$CORNERS/schmitt.csv"
      echo "[S] ${mos}/${temp}C/${vsup}V: ${row}" >&2
    done
  done
done

# ---------------------------------------------------------------------------
# 5. Timestep-convergence cross-check.  twin_r is an interpolated difference
#    of two threshold crossings and is the number every phase-error threshold
#    in ladder.csv is scaled by, so it is the one measurement here whose value
#    could plausibly be a discretisation artifact.  Re-run a few
#    representative corners at 4x and 16x finer maximum internal timestep and
#    record all three, so the record states the observed sensitivity instead
#    of asserting it is small.
# ---------------------------------------------------------------------------
echo "mos_corner,res_corner,temp_c,dut_variant,tstep,twin_r_s" \
  > "$CORNERS/tstep_convergence.csv"
for tstep in 20p 5p 1.25p; do
  for probe in "mos_tt res_typ 27 real" "mos_ss res_wcs 125 ideal0.20" \
               "mos_ff res_bcs -40 ideal-0.20" "mos_sf res_typ 27 real"; do
    read -r mos res temp variant <<< "$probe"
    sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@TEMP@/$temp/g" \
        -e "s/@VSUP@/$VSUP_NOM/g" -e "s/@VMID@/1.65/g" -e "s/@TSTEP@/$tstep/g" \
        -e "s|@DUT@|$WORK/dut_${variant}.spice|g" \
      "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
    tw="$( ( cd "$WORK" && ngspice -b w.sp ) 2>/dev/null \
           | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "${mos},${res},${temp},${variant},${tstep},${tw:-NA}" \
      >> "$CORNERS/tstep_convergence.csv"
    echo "[conv ${tstep}] ${mos}/${temp}C/${variant}: twin_r=${tw:-NA}" >&2
  done
done

echo "done:" >&2
for f in rc_extract window schmitt ladder ladder_raw tstep_convergence; do
  echo "  $(wc -l < "$CORNERS/$f.csv") lines (incl. header) -> $CORNERS/$f.csv" >&2
done
