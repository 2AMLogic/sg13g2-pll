#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-lock-detector-window/testbench/run.sh
# (issue #81, Part of #16 via #78 -- SG13G2 PVT campaign, Phase 1/2)
#
# Split out of #78 (SG13G2 lock_detector had no sim/ campaign at all).  This
# is the FIRST HALF: stand up the slug and extract R/C over the PVT grid.
# Per issue #81's own Scope item 4, this script does NOT resize any device
# and does NOT draw a pass/fail conclusion -- that is issue #82's job, using
# ../corners/rc_extract.csv as its own re-derivation's input. The window /
# ladder / schmitt / tstep_convergence sections below are stood up (reusing
# the SG13CMOS5L sibling's topology-generic testbench structure, issue #81
# Scope item 1) so #82 has the same measurement machinery to re-run once it
# resizes XRPU/XCW/XDW.XC1/XMPD -- their CSVs are raw evidence, not a record.
#
# Writes six CSVs into ../corners/:
#
#   rc_extract.csv          XRPU (rhigh) resistance over the resistor-corner
#                     x temperature grid, and the two cap_cmim instances'
#                     capacitance over cap_cmim's OWN process corner x
#                     temperature grid (see tb_extract_c.sp.tmpl's header for
#                     why this is a real corner axis on this PDK and was not
#                     one for SG13CMOS5L's cap_cmomi)
#   window.csv        the comparator window twin_r / twin_f, per corner
#   schmitt.csv        the readout Schmitt's own hysteresis, V_TH+/V_TH-
#   ladder.csv        one row per corner point: assert threshold, de-assert
#                     threshold, hysteresis, chatter verdict, recovery time,
#                     in-lock and out-of-lock supply current
#   ladder_raw.csv    every ladder point's per-copy settled state/levels
#   tstep_convergence.csv   twin_r vs. maximum internal timestep
#
# APPEND-ONLY EVIDENCE (sim/README.md).  This is the ONLY record's worth of
# CSVs for this slug so far -- no resize has landed yet, so there is exactly
# one netlist snapshot (../netlist-snapshots/lock_detector.spice) and one CSV
# set (unsuffixed).  A future resize (issue #82) adds a second snapshot and a
# parallel suffixed CSV set, exactly as the SG13CMOS5L sibling's own
# RECORD-001 -> RECORD-002 transition did; it must not overwrite these.
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
#   export PDK=ihp-sg13g2
#   ./run.sh
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13g2 tree.
#
# ---------------------------------------------------------------------------
# TOOLING NOTE -- `set num_threads=1` in the generated .spiceinit.
#
# Carried over from the SG13CMOS5L sibling (issue #38): ngspice's OpenMP
# matrix solve spins on its barriers, and on a deck this small the spin
# dominates -- a ~100x wall-clock difference measured there, with bit-
# identical results either way.  General ngspice property, not a PDK issue.
# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------
# WHY THIS CAMPAIGN HAS NO --soft / cap_cmomi-STYLE OSDI FALLBACK (issue #81
# Scope item 2).
#
# The SG13CMOS5L sibling's own preflight has a --soft branch because
# cap_cmomi.osdi ships as a prebuilt x86-64 ELF TRACKED FILE that can be the
# wrong architecture on an arm64 host (sim/PORTING-osdi-host-arch.md).
# SG13G2's own `cap_cmim` has NO OSDI object at all -- it is a plain SPICE
# .subckt (capacitors_mod.lib), confirmed directly against the installed
# ihp-sg13g2 tree before writing this script -- so there is no cross-tree,
# prebuilt-binary risk for it to begin with.  The four OSDI objects this
# script DOES load (psp103, psp103_nqs, mosvar, r3_cmc) are native BUILD
# PRODUCTS of the ihp-sg13g2 tree itself on every host that installed the PDK
# correctly, so the preflight below stays a plain hard-abort call with no
# --soft names -- simpler, not a workaround, per issue #81's own prediction
# ("this may make the campaign simpler, not harder").
# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------
# THE THIRD CORNER AXIS -- @CORNER_CAP@ (issue #81 Scope item 2).
#
# cap_cmim has a REAL characterised process corner (cornerCAP.lib: cap_typ /
# cap_bcs / cap_wcs, +/-10% area+perimeter scaling) and a genuine TC1/TC2
# temperature coefficient -- unlike cap_cmomi, whose installed cornerCAP.lib
# maps every corner/mismatch/stat section to the SAME nominal model.  So this
# script sweeps it as a first-class axis (mirroring @CORNER_RES@) rather than
# re-injecting a synthetic +/-20% ideal-capacitor band the way the
# SG13CMOS5L sibling's mom_inject.py/cmomi_nominal.py do -- that whole
# mechanism does not carry over here (issue #81 Scope item 2's own
# instruction), and there is exactly one DUT file (the frozen snapshot,
# included directly by every template) instead of several dut_<variant>.spice
# files, because corner selection lives in the calling deck's own `.lib`
# lines, not in a rebuilt netlist.
# ---------------------------------------------------------------------------

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
DUT="$RECORD_DIR/netlist-snapshots/lock_detector.spice"

VSUP_NOM=3.3
TRST=1n
FREF_SLOW=3.5e6     # slow end of the DR-005-amended f_ref range (row 2)
FREF_FAST=24.4e6    # fast end
LADDER_SET=record002

# ---------------------------------------------------------------------------
# ngspice invocation wrapper -- carried over from the SG13CMOS5L sibling
# (issue #54/#66): a way for a deck to die fatally instead of a failure being
# swallowed into a silent NA row, plus one recorded, non-silent retry with
# trtol=1 (a genuine truncation-error relaxation, so it is never in the
# templates themselves and is only used after a deck has already failed
# outright).
# ---------------------------------------------------------------------------
run_ngspice_or_die() {
  local name="$1"
  local err="$WORK/${name}.err"
  local out
  if out="$( cd "$WORK" && ngspice -b "$name" 2>"$err" )"; then
    printf '%s\n' "$out"
    return 0
  fi
  echo "WARNING: ngspice exited non-zero for $name; retrying once with trtol=1" >&2
  sed -n 's/^doAnalyses.*$/  ngspice said: &/p' "$err" >&2
  sed -i.bak 's/^\(\.options reltol=.*\)$/\1 trtol=1/' "$WORK/$name"
  if ! out="$( cd "$WORK" && ngspice -b "$name" 2>"$err" )"; then
    echo "ERROR: ngspice exited non-zero for $name even with trtol=1:" >&2
    cat "$err" >&2
    return 1
  fi
  echo "${RETRY_TAG:-<unlabelled>} ($name)" >> "$CORNERS/solver_retries.txt"
  echo "[solver-retry] ${RETRY_TAG:-<unlabelled>} ($name) completed with trtol=1" >&2
  printf '%s\n' "$out"
}

# ---------------------------------------------------------------------------
# 0. OSDI preflight -- hard abort only, no --soft (see header note above).
# ---------------------------------------------------------------------------
"$HERE/../../tools/check-osdi-arch.sh" --quiet \
  "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" "$OSDI/r3_cmc.osdi"

{
  echo "osdi $OSDI/psp103.osdi"
  echo "osdi $OSDI/psp103_nqs.osdi"
  echo "osdi $OSDI/mosvar.osdi"
  echo "osdi $OSDI/r3_cmc.osdi"
  echo "set num_threads=1"
} > "$WORK/.spiceinit"

: > "$CORNERS/solver_retries.txt"

# ---------------------------------------------------------------------------
# 1. Device extraction: R (rhigh, XRPU) over the resistor-corner x temperature
#    grid, C (cap_cmim, XCW + XDW.XC1) over cap_cmim's own process corner x
#    temperature grid.
# ---------------------------------------------------------------------------
echo "kind,instance,corner,temp_c,w,l,m,value,source" > "$CORNERS/rc_extract.csv"

declare -A RVAL
for rc in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    sed -e "s/@RES_CORNER@/$rc/g" -e "s/@TEMP@/$temp/g" \
        -e "s/@W@/0.5u/g" -e "s/@L@/6u/g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_extract_r.sp.tmpl" > "$WORK/r.sp"
    RETRY_TAG="rc_extract R ${rc}/${temp}C"
    val="$( run_ngspice_or_die r.sp \
            | sed -n 's/^rval *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "R,XRPU(rhigh),${rc},${temp},0.5u,6u,1,${val:-NA},ngspice-subckt" \
      >> "$CORNERS/rc_extract.csv"
    echo "[R] ${rc}/${temp}C: ${val:-NA} ohm" >&2
    RVAL["${rc},${temp}"]="$val"
  done
done

declare -A CNOM
for geom in "XCW 6u 6u 1" "XDW.XC1 4u 4u 1"; do
  read -r inst w l m <<< "$geom"
  for cc in cap_typ cap_bcs cap_wcs; do
    for temp in -40 27 125; do
      sed -e "s/@CAP_CORNER@/$cc/g" -e "s/@W@/$w/g" -e "s/@L@/$l/g" \
          -e "s/@M@/$m/g" -e "s/@TEMP@/$temp/g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_extract_c.sp.tmpl" > "$WORK/c.sp"
      RETRY_TAG="rc_extract C ${inst}/${cc}/${temp}C"
      val="$( run_ngspice_or_die c.sp \
              | awk '/^0[[:space:]]/ {print $3; exit}' )"
      echo "C,${inst}(cap_cmim),${cc},${temp},${w},${l},${m},${val:-NA},ngspice-subckt" \
        >> "$CORNERS/rc_extract.csv"
      echo "[C] ${inst}/${cc}/${temp}C: ${val:-NA} F" >&2
      if [ "$cc" = "cap_typ" ] && [ "$temp" = "27" ]; then CNOM[$inst]="$val"; fi
    done
  done
done

C_XCW="${CNOM[XCW]}"
C_XC1="${CNOM[XDW.XC1]}"
echo "nominal C (cap_typ/27C): XCW=$C_XCW  XDW.XC1=$C_XC1" >&2

# ---------------------------------------------------------------------------
# 2. Corner bundles.  Rows: mos res cap.  MOS/RES/CAP are bundled at matching
#    "speed" labels for the main grid (mirroring the SG13CMOS5L sibling's own
#    mos/res bundling), plus RES-only and CAP-only isolation points at fixed
#    mos_tt so each axis's own effect is separable, not only visible bundled.
# ---------------------------------------------------------------------------
MAIN_BUNDLES=(
  "mos_tt res_typ cap_typ"
  "mos_ss res_wcs cap_wcs"
  "mos_ff res_bcs cap_bcs"
  "mos_sf res_typ cap_typ"
  "mos_fs res_typ cap_typ"
)
RES_ISO_BUNDLES=(
  "mos_tt res_wcs cap_typ"
  "mos_tt res_bcs cap_typ"
)
CAP_ISO_BUNDLES=(
  "mos_tt res_typ cap_wcs"
  "mos_tt res_typ cap_bcs"
)

ftag() {  # ftag <fref_hz> -> a filename-safe reference-frequency label
  python3 -c "print(('%.1f' % (float('$1')/1e6)).replace('.','p') + 'MHz')"
}

# ---------------------------------------------------------------------------
# 3. Window matrix.  Rows: mos res cap temp vsup fref.
# ---------------------------------------------------------------------------
WINDOW_POINTS=()
for bundle in "${MAIN_BUNDLES[@]}" "${RES_ISO_BUNDLES[@]}" "${CAP_ISO_BUNDLES[@]}"; do
  for temp in -40 27 125; do
    WINDOW_POINTS+=("$bundle $temp $VSUP_NOM $FREF_FAST")
  done
done
for temp in -40 27 125; do
  for vsup in 2.97 3.63; do
    WINDOW_POINTS+=("mos_tt res_typ cap_typ $temp $vsup $FREF_FAST")
  done
done
for fref in "$FREF_SLOW" 12e6; do
  WINDOW_POINTS+=("mos_tt res_typ cap_typ 27 $VSUP_NOM $fref")
done

echo "corner_tag,mos_corner,res_corner,cap_corner,temp_c,vsup_v,fref_hz,twin_r_s,twin_f_s" \
  > "$CORNERS/window.csv"

measure_window() {  # measure_window mos res cap temp vsup -> "twin_r twin_f"
  local mos="$1" res="$2" cap="$3" temp="$4" vsup="$5"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
      -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TSTEP@/20p/g" \
      -e "s|@DUT@|$DUT|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
  local wlog tr tf
  wlog="$( run_ngspice_or_die w.sp )"
  tr="$(printf '%s\n' "$wlog" | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  tf="$(printf '%s\n' "$wlog" | sed -n 's/^twin_f *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  echo "${tr:-NA} ${tf:-NA}"
}

n=0
for pt in "${WINDOW_POINTS[@]}"; do
  read -r mos res cap temp vsup fref <<< "$pt"
  tag="${mos}_${res}_${cap}_${temp}c_${vsup}v_$(ftag "$fref")"
  RETRY_TAG="window ${tag}"
  wpair="$(measure_window "$mos" "$res" "$cap" "$temp" "$vsup")"
  read -r twin_r twin_f <<< "$wpair"
  echo "${tag},${mos},${res},${cap},${temp},${vsup},${fref},${twin_r},${twin_f}" \
    >> "$CORNERS/window.csv"
  n=$((n + 1))
  echo "  [window $n/${#WINDOW_POINTS[@]}] ${tag}: twin_r=${twin_r}" >&2
done

# ---------------------------------------------------------------------------
# 4. Ladder matrix.  Same bundles as the window's main + isolation grid, at
#    BOTH ends of the f_ref range (SG13G2's current sizing has a small R*C --
#    same order as the SG13CMOS5L sibling's own pre-resize RECORD-001 -- so a
#    4-reference-period settling transient is tractable at every corner,
#    unlike the post-resize sibling's own many-cycle budget; the one-point-
#    at-a-time split machinery is reused anyway per issue #81 Scope item 1).
# ---------------------------------------------------------------------------
echo "corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,tau_deassert_xwin,hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,lock_max_deep_v,trec_s,vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,ladder_states_discharged_start,ladder_states_charged_start,rc_s,tref_s,rc_over_tref" \
  > "$CORNERS/ladder.csv"
echo "corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,lka_max_v,lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v" \
  > "$CORNERS/ladder_raw.csv"

N_LADDER_PTS="$(python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('gen_ladder', '$HERE/gen_ladder.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(len(m.LADDER_FRACS_SETS['$LADDER_SET']))")"

run_ladder_corner() {
  local mos="$1" res="$2" cap="$3" temp="$4" vsup="$5" fref="$6"
  local tag="${mos}_${res}_${cap}_${temp}c_${vsup}v_$(ftag "$fref")"
  local RETRY_TAG="ladder ${tag}"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"

  local twin_r twin_f
  local wpair
  wpair="$(measure_window "$mos" "$res" "$cap" "$temp" "$vsup")"
  read -r twin_r twin_f <<< "$wpair"
  if [ "$twin_r" = NA ]; then
    echo "${tag},NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA" \
      >> "$CORNERS/ladder.csv"
    echo "[!] ${tag}: window measurement failed, ladder skipped" >&2
    return
  fi

  # tstop = 4 reference periods (SG13G2's current R*C is small -- same order
  # as the SG13CMOS5L sibling's own pre-resize block -- so this is ample
  # margin; settle window = the last 2), tstep = tref/500.
  local tref rc c_val n_cycles rc_over tstop tsettle tstep
  tref="$(python3 -c "print(1.0/float('$fref'))")"
  c_val="${CNOM[XCW]}"
  rc="$(python3 -c "print(${RVAL[$res,$temp]} * $c_val)")"
  rc_over="$(python3 -c "print('%.6f' % ($rc/$tref))")"
  tstop="$(python3 -c "print(4*$tref)")"
  tsettle="$(python3 -c "print(2*$tref)")"
  tstep="$(python3 -c "print($tref/500.0)")"

  echo "[L] ${tag}: twin_r=${twin_r} RC=${rc}s RC/tref=${rc_over}" >&2

  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
      -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TREF@/$tref/g" \
      -e "s/@TRST@/$TRST/g" -e "s/@TAUBIG@/$(python3 -c "print(10.00*$twin_r)")/g" \
      -e "s/@TSTEP@/$tstep/g" -e "s/@TSTOP@/$tstop/g" -e "s/@TSETTLE@/$tsettle/g" \
      -e "s|@DUT@|$DUT|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_lock_recovery.sp.tmpl" > "$WORK/base.sp"
  local combined="$WORK/combined.log"
  run_ngspice_or_die base.sp > "$combined"

  local k
  for k in $(seq 0 $((N_LADDER_PTS - 1))); do
    python3 "$HERE/gen_ladder.py" gen \
      --template "$HERE/tb_lock_ladder_point.sp.tmpl" --out "$WORK/pt.sp" --dut "$DUT" \
      --fracs-set "$LADDER_SET" \
      --corner-mos "$mos" --corner-res "$res" --corner-cap "$cap" --temp "$temp" --vsup "$vsup" \
      --tref "$tref" --trst "$TRST" --twin "$twin_r" \
      --tstep "$tstep" --tstop "$tstop" --tsettle "$tsettle" \
      --pdk-root "$PDK_ROOT" --pdk "$PDK" \
      --only-index "$k" > /dev/null
    run_ngspice_or_die pt.sp >> "$combined"
  done

  python3 "$HERE/gen_ladder.py" reduce --tag "$tag" --vsup "$vsup" \
      --fracs-set "$LADDER_SET" \
      --twin "$twin_r" --raw "$CORNERS/ladder_raw.csv" < "$combined" \
    | python3 -c "
import sys
print(sys.stdin.read().strip() + ',%.6e,%.6e,%s' % ($rc, $tref, '$rc_over'))" \
    >> "$CORNERS/ladder.csv"
  echo "[L] ${tag}: $(tail -1 "$CORNERS/ladder.csv" | cut -d, -f3-10)" >&2
}

LADDER_POINTS=()
for bundle in "${MAIN_BUNDLES[@]}" "${RES_ISO_BUNDLES[@]}" "${CAP_ISO_BUNDLES[@]}"; do
  for temp in -40 27 125; do
    LADDER_POINTS+=("$bundle $temp $VSUP_NOM $FREF_FAST")
  done
done
# Slow end: full resistor-corner x temperature grid at mos_tt/cap_typ -- the
# binding combination for an R*C-vs-T_ref comparison, mirroring the
# SG13CMOS5L sibling's own convention.
for rc in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    LADDER_POINTS+=("mos_tt $rc cap_typ $temp $VSUP_NOM $FREF_SLOW")
  done
done

n=0
for pt in "${LADDER_POINTS[@]}"; do
  read -r mos res cap temp vsup fref <<< "$pt"
  run_ladder_corner "$mos" "$res" "$cap" "$temp" "$vsup" "$fref"
  n=$((n + 1))
  echo "  (ladder $n/${#LADDER_POINTS[@]})" >&2
done

# ---------------------------------------------------------------------------
# 5. Schmitt readout hysteresis, per MOS corner x temperature x supply.
#    (No resistor and no cap_cmim instance inside schmitt_hv, so neither the
#    RES-corner nor the CAP-corner axis applies to it -- stated here rather
#    than silently dropped, per sim/README.md's convention.)
# ---------------------------------------------------------------------------
echo "mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd" \
  > "$CORNERS/schmitt.csv"
for mos in mos_tt mos_ss mos_ff mos_sf mos_fs; do
  for temp in -40 27 125; do
    for vsup in 2.97 3.3 3.63; do
      vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
      sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" \
          -e "s/@VMID@/$vmid/g" -e "s|@DUT@|$DUT|g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_schmitt_hyst.sp.tmpl" > "$WORK/s.sp"
      RETRY_TAG="schmitt ${mos}_${temp}c_${vsup}v"
      slog="$( run_ngspice_or_die s.sp )"
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
# 6. Timestep-convergence cross-check.  twin_r is an interpolated difference
#    of two threshold crossings and is the number every phase-error threshold
#    in ladder.csv is scaled by, so it is the one measurement here whose value
#    could plausibly be a discretisation artifact.
# ---------------------------------------------------------------------------
echo "mos_corner,res_corner,cap_corner,temp_c,tstep,twin_r_s" \
  > "$CORNERS/tstep_convergence.csv"
for tstep in 20p 5p 1.25p; do
  for probe in "mos_tt res_typ cap_typ 27" "mos_ss res_wcs cap_wcs 125" \
               "mos_ff res_bcs cap_bcs -40" "mos_sf res_typ cap_typ 27"; do
    read -r mos res cap temp <<< "$probe"
    sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
        -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$VSUP_NOM/g" -e "s/@VMID@/1.65/g" -e "s/@TSTEP@/$tstep/g" \
        -e "s|@DUT@|$DUT|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
    RETRY_TAG="tstep_convergence ${mos}_${res}_${cap}_${temp}c_${tstep}"
    tw="$( run_ngspice_or_die w.sp \
           | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "${mos},${res},${cap},${temp},${tstep},${tw:-NA}" \
      >> "$CORNERS/tstep_convergence.csv"
    echo "[conv ${tstep}] ${mos}/${res}/${cap}/${temp}C: twin_r=${tw:-NA}" >&2
  done
done

n_retry="$(wc -l < "$CORNERS/solver_retries.txt")"
if [ "$n_retry" -eq 0 ]; then
  echo "solver retries: none -- every deck converged on the committed .options" >&2
else
  echo "solver retries: ${n_retry} deck(s) needed trtol=1 -- see $CORNERS/solver_retries.txt" >&2
fi

echo "done:" >&2
for f in rc_extract window schmitt ladder ladder_raw tstep_convergence; do
  echo "  $(wc -l < "$CORNERS/${f}.csv") lines (incl. header) -> $CORNERS/${f}.csv" >&2
done
