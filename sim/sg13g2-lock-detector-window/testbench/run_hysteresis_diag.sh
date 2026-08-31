#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-lock-detector-window/testbench/run_hysteresis_diag.sh
# (issue #82, Part of #16 via #78 -- SG13G2 PVT campaign, Phase 2/2)
#
# WHY THIS EXISTS -- it closes a RESOLUTION gap in ./run.sh's own ladder, not a
# coverage gap.
#
# ./run.sh's ladder answers "which state does the block settle into at this
# phase error", which is what spec/porting-plan.md row 16's assert / de-assert
# / chatter criteria are stated in.  Its `resized` ladder steps 0.25 x window
# through the transition region, so the SMALLEST non-zero hysteresis it can
# report is exactly one step -- 25.0% of the window, which is row 16's
# criterion itself.  At the ladder's own minimum-hysteresis corner
# (mos_tt/res_wcs/cap_typ/-40 C at 24.4 MHz) that is precisely what it
# reports: assert at 1.25 x window, de-assert at 1.50 x, hysteresis 25.0%,
# i.e. a margin of exactly 1.00x -- which is a statement about the ladder's
# resolution, not about the block.  A pass that lands on the quantisation step
# is not a measurement of the margin, so this script measures the same corner
# without the quantiser.
#
# HOW.  Same method ./run_xmpd_sizing.sh uses to select XMPD, applied here to
# the LANDED block: sweep tau finely across the transition and report the
# SETTLED INTEGRATING-NODE VOLTAGE (not just the thresholded LOCK pin), so
# ../records/RECORD-001 can interpolate the two trip points against the SAME
# corner's own measured Schmitt trip voltages from ../corners/schmitt_resized.csv:
#
#     H_tau  =  tau(VWIN = V_TH-)  -  tau(VWIN = V_TH+)
#
# Two copies at each tau, as the ladder deck uses: copy A starts fully
# DISCHARGED, copy B fully CHARGED, so any genuine state-dependence shows up
# as a difference between the two settled results at the same tau.
#
# CORNERS.  Both at the fast end of row 2's DR-005-amended f_ref range, which
# is the binding end for row 16's hysteresis criterion (the settled VWIN is
# VDD - I_sat(XMPD)*R(XRPU)*(tau-twin_r)/T_ref, so the transition's
# phase-error width is proportional to T_ref):
#
#   A. mos_tt/res_wcs/cap_typ/-40 C -- the corner ../corners/ladder_resized.csv
#      reports 25.0% at, i.e. the one the ladder cannot resolve.
#   B. mos_ff/res_wcs/cap_typ/-40 C -- the stack ./run_xmpd_sizing.sh selected
#      XMPD against.  Included as a CROSS-CHECK: this script runs the frozen
#      ../netlist-snapshots/lock_detector_resized.spice while that sweep ran the
#      pre-XMPD ../netlist-snapshots/lock_detector_rc_resized.spice with XMPD
#      substituted in, so agreement here confirms the two snapshots differ in
#      nothing that matters and the sizing sweep's own selection row is
#      reproducible against the landed block.
#
# Output: ../corners/hysteresis_diag.csv.
#
# DIAG_JOBS=<n> runs up to n points concurrently (default 1) -- same
# independence argument as ./run.sh's LADDER_JOBS; see its header.
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
#   export PDK=ihp-sg13g2
#   ./run_hysteresis_diag.sh            # or: DIAG_JOBS=6 ./run_hysteresis_diag.sh
#
# Runtime: ~65 min serial, ~20 min at DIAG_JOBS=4 (each point is a 700-cycle
# 24.4 MHz transient).

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
SNAP="$RECORD_DIR/netlist-snapshots/lock_detector_resized.spice"

"$HERE/../../tools/check-osdi-arch.sh" --quiet \
  "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" "$OSDI/r3_cmc.osdi"

{
  echo "osdi $OSDI/psp103.osdi"
  echo "osdi $OSDI/psp103_nqs.osdi"
  echo "osdi $OSDI/mosvar.osdi"
  echo "osdi $OSDI/r3_cmc.osdi"
  echo "set num_threads=1"
} > "$WORK/.spiceinit"

K_SETTLE=4
TSTOP_MAX=32e-6   # see ./run.sh's own note -- 16 us left settle_frac = 0.89 here
TSTEP_DIV=25
FREF=24.4e6

# Same lookup ./run_xmpd_sizing.sh uses: the landed geometries' R and C, out of
# this slug's own committed ../corners/rc_extract_resized.csv (./run.sh's
# section-1 measurement against the landed block).  Used only to size each
# transient's settling budget.
rc_lookup() {  # rc_lookup <kind> <instance-prefix> <corner> <temp>
  python3 - "$CORNERS/rc_extract_resized.csv" "$1" "$2" "$3" "$4" <<'PY'
import csv, sys
path, kind, inst, corner, temp = sys.argv[1:6]
for r in csv.DictReader(open(path)):
    if (r["kind"] == kind and r["instance"].startswith(inst)
            and r["corner"] == corner and r["temp_c"] == temp):
        print(r["value"]); break
else:
    raise SystemExit("run_hysteresis_diag: no %s row for %s %s/%sC in %s"
                     % (kind, inst, corner, temp, path))
PY
}

FRACS="0.90 1.00 1.05 1.10 1.15 1.20 1.25 1.30 1.40 1.50 1.60 1.75 2.00"

echo "corner_tag,mos_corner,res_corner,cap_corner,temp_c,vsup_v,fref_hz,r_xrpu_ohm,c_xcw_f,rc_s,n_cycles,settle_frac,twin_r_s,tau_xwin,tau_s,vwin_discharged_start_avg_v,vwin_charged_start_avg_v,lock_discharged_start_avg_v,lock_charged_start_avg_v" \
  > "$CORNERS/hysteresis_diag.csv"

JOBS="${DIAG_JOBS:-1}"
ORDER=()

run_point() {
  local rowf="$1" tag="$2" mos="$3" res="$4" cap="$5" temp="$6" rval="$7" cval="$8"
  local rc="$9" ncyc="${10}" sfrac="${11}" twin="${12}" tref="${13}" tstop="${14}"
  local tsettle="${15}" tstep="${16}" frac="${17}"
  local vsup=3.3 trst=1n
  local sfx; sfx="$(echo "${tag}_${frac}" | tr -c 'A-Za-z0-9_' '_')"
  local tau; tau="$(python3 -c "print('%.6e' % ($frac*$twin))")"

  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
      -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@TREF@/$tref/g" -e "s/@TRST@/$trst/g" \
      -e "s/@TAU@/$tau/g" -e "s/@TSTEP@/$tstep/g" -e "s/@TSTOP@/$tstop/g" \
      -e "s/@TSETTLE@/$tsettle/g" -e "s|@DUT@|$SNAP|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_hyst_diag.sp.tmpl" > "$WORK/d_$sfx.sp"

  local hlog err="$WORK/d_$sfx.err"
  if ! hlog="$( cd "$WORK" && ngspice -b "d_$sfx.sp" 2>"$err" )"; then
    echo "WARNING: ngspice exited non-zero for $tag tau=${frac}x; retrying with trtol=1" >&2
    sed -i.bak 's/^\(\.options reltol=.*\)$/\1 trtol=1/' "$WORK/d_$sfx.sp"
    if ! hlog="$( cd "$WORK" && ngspice -b "d_$sfx.sp" 2>"$err" )"; then
      echo "ERROR: ngspice exited non-zero for $tag tau=${frac}x even with trtol=1:" >&2
      cat "$err" >&2
      return 1
    fi
    echo "hysteresis_diag ${tag} tau=${frac}x" >> "$CORNERS/solver_retries_diag.txt"
  fi
  get() { printf '%s\n' "$hlog" | sed -n "s/^$1 *= *\([0-9.eE+-]*\).*/\1/p" | head -1; }
  echo "${tag},${mos},${res},${cap},${temp},${vsup},${FREF},${rval},${cval},${rc},${ncyc},${sfrac},${twin},${frac},${tau},$(get va_avg),$(get vb_avg),$(get la_avg),$(get lb_avg)" \
    > "$rowf"
  echo "  [$tag tau=${frac}x] VWIN(d)=$(get va_avg) VWIN(c)=$(get vb_avg) LOCK(d)=$(get la_avg) LOCK(c)=$(get lb_avg)" >&2
}

sweep_corner() {  # sweep_corner <mos> <res> <cap> <temp>
  local mos="$1" res="$2" cap="$3" temp="$4"
  local tag="${mos}_${res}_${cap}_${temp}c"
  local vsup=3.3 vmid=1.65

  local twin
  twin="$( sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
        -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" \
        -e "s/@TSTEP@/20p/g" -e "s|@DUT@|$SNAP|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_window.sp.tmpl" > "$WORK/w_$tag.sp"
      ( cd "$WORK" && ngspice -b "w_$tag.sp" ) 2>/dev/null \
        | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
  [ -n "$twin" ] || { echo "ERROR: twin_r did not resolve at $tag" >&2; exit 1; }

  local rval cval tref rc ncyc tstop tsettle tstep sfrac
  rval="$(rc_lookup R XRPU "$res" "$temp")"
  cval="$(rc_lookup C XCW "$cap" "$temp")"
  tref="$(python3 -c "print(1.0/$FREF)")"
  rc="$(python3 -c "print($rval * $cval)")"
  ncyc="$(python3 -c "
import math
print(int(math.ceil(min($K_SETTLE*$rc, $TSTOP_MAX)/$tref)))")"
  tstop="$(python3 -c "print($ncyc*$tref)")"
  sfrac="$(python3 -c "
import math
print('%.4f' % (1.0 - math.exp(-$tstop/$rc)))")"
  tsettle="$(python3 -c "print($tstop - 2*$tref)")"
  tstep="$(python3 -c "print($tref/$TSTEP_DIV.0)")"
  echo "[$tag] twin_r=$twin R=$rval C=$cval RC=${rc}s n_cycles=$ncyc settle_frac=$sfrac" >&2

  local frac rowf
  for frac in $FRACS; do
    rowf="$WORK/row_$(printf '%04d' ${#ORDER[@]})"
    ORDER+=("$rowf")
    if [ "$JOBS" -gt 1 ]; then
      while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n; done
      run_point "$rowf" "$tag" "$mos" "$res" "$cap" "$temp" "$rval" "$cval" "$rc" \
                "$ncyc" "$sfrac" "$twin" "$tref" "$tstop" "$tsettle" "$tstep" "$frac" &
    else
      run_point "$rowf" "$tag" "$mos" "$res" "$cap" "$temp" "$rval" "$cval" "$rc" \
                "$ncyc" "$sfrac" "$twin" "$tref" "$tstop" "$tsettle" "$tstep" "$frac"
    fi
  done
  if [ "$JOBS" -gt 1 ]; then
    wait || { echo "ERROR: at least one concurrent diagnostic point failed" >&2; exit 1; }
  fi
}

sweep_corner mos_tt res_wcs cap_typ -40    # ladder's own 25.0% corner
sweep_corner mos_ff res_wcs cap_typ -40    # run_xmpd_sizing.sh's selection stack

for rowf in "${ORDER[@]}"; do
  [ -s "$rowf" ] || { echo "ERROR: missing diagnostic row $rowf" >&2; exit 1; }
  cat "$rowf" >> "$CORNERS/hysteresis_diag.csv"
done

echo "done: $(wc -l < "$CORNERS/hysteresis_diag.csv") lines (incl. header) -> $CORNERS/hysteresis_diag.csv" >&2
