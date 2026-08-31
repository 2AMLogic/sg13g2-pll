#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/run_xmpd_sizing.sh
# (issue #66, Part of #16)
#
# SIZING EVIDENCE for issue #66's XMPD re-size.  Not part of the pass/fail
# campaign -- ./run.sh measures spec/porting-plan.md row 16's three criteria
# against the block as committed.  THIS script is the measurement the chosen
# XMPD geometry is argued from, so the choice is a two-sided bound read off a
# committed CSV rather than a number asserted in a schematic header.
#
# ---------------------------------------------------------------------------
# THE MECHANISM, IN ONE PARAGRAPH (measured by ../records/RECORD-002, not new
# here).  Row 16's hysteresis criterion is a PHASE-ERROR width, and in this
# topology it factors:
#
#     H_tau  ~=  H_volts(schmitt_hv)  /  |dVWIN/dtau|
#
# RECORD-002 measured H_volts ~ 1 mV (a two-net wiring defect, fixed by issue
# #66 and measured by ../testbench/run_schmitt_rewire.sh) and, binding over it,
# a |dVWIN/dtau| so steep that the whole settled-VWIN transition was <= 0.05x
# the window wide -- five times too narrow to hold a 0.25x-window hysteresis
# whatever the Schmitt does.  The settled VWIN is the balance between XRPU's
# charge over ONE REFERENCE PERIOD and XMPD's discharge over ONE WIDE PULSE:
#
#     VWIN  ~=  VDD  -  I_sat(XMPD) * R(XRPU) * (tau - twin) / T_ref
#
# so the transition width is set by the XRPU/XMPD strength ratio, and R*C --
# which issue #52 spent its whole scope on -- does not appear in it at all.
# XMPD is therefore the knob that buys transition width WITHOUT spending
# #52's R*C margin.  This script measures the trade that knob actually makes.
#
# ---------------------------------------------------------------------------
# WHY BOTH ENDS OF THE f_ref RANGE, AND WHY THEY PULL OPPOSITE WAYS.  T_ref is
# in the numerator above, so at row 2's DR-005-amended FAST end (24.4 MHz,
# T_ref = 41 ns) the transition is ~7x STEEPER -- i.e. the hysteresis in units
# of the window is ~7x SMALLER -- than at the slow end (3.5 MHz, 286 ns).  The
# fast end is therefore the BINDING end for row 16's >= 25%-of-window
# criterion, which RECORD-002's 3.5 MHz-only diagnostic could not see.
#
# The same T_ref factor also scales the assert/de-assert THRESHOLDS, so
# weakening XMPD until the fast end clears the criterion simultaneously pushes
# the slow end's de-assert threshold out.  If it goes past ~half a reference
# period the block stops being a lock detector at the slow end.  Hence a
# two-sided bound, and hence this script sweeps candidate geometries at BOTH:
#
#   A. mos_ff/res_wcs/-40C @ 24.4 MHz -- STRONGEST discharge relative to
#      charge (max I_sat(XMPD) x max R(XRPU), shortest twin_r), i.e. the
#      SMALLEST hysteresis corner.  Sets the lower bound on how strong XMPD
#      may be.
#   B. mos_tt/res_bcs/125C @ 3.5 MHz -- WEAKEST discharge relative to charge
#      (min R, hot), i.e. the corner whose de-assert threshold sits furthest
#      out.  Sets the upper bound on how weak XMPD may be.
#
# Output ../corners/xmpd_sizing.csv reports the SETTLED INTEGRATING-NODE
# VOLTAGE (not just the thresholded LOCK pin) per geometry per phase-error
# point, plus both LOCK copies, so the record can interpolate the two trip
# points against the same corner's measured Schmitt trip voltages from
# ../corners/schmitt_rewire.csv instead of relying on ladder quantisation.
#
# Every geometry is simulated on a scratch copy in a temp dir; nothing is
# written back into design/ or ../netlist-snapshots/.
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root
#   export PDK=ihp-sg13cmos5l
#   ./run_xmpd_sizing.sh
#
# Runtime: ~35 min (the 24.4 MHz sweep needs ~390 reference periods per point).

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
SNAP="$RECORD_DIR/netlist-snapshots/lock_detector_hystfix.spice"

# Same preflight and same single `--soft` opt-out run.sh uses -- see its HOST
# NOTE for why cap_cmomi is the one object with a validated substitute.
set +e
SOFT_UNLOADABLE="$( "$HERE/../../tools/check-osdi-arch.sh" --quiet \
  --soft cap_cmomi.osdi \
  "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" \
  "$OSDI/r3_cmc.osdi" "$OSDI/cap_cmomi.osdi" )"
OSDI_RC=$?
set -e
case "$OSDI_RC" in
  0) VARIANT=real ;;
  3)
    if [ "$SOFT_UNLOADABLE" != "cap_cmomi.osdi" ]; then
      echo "ERROR: OSDI preflight reported an unexpected soft-unloadable set:" >&2
      printf '%s\n' "$SOFT_UNLOADABLE" >&2
      exit 1
    fi
    VARIANT=ideal0.00
    ;;
  *) exit "$OSDI_RC" ;;
esac
echo "[osdi] primary DUT variant: $VARIANT" >&2

{
  echo "osdi $OSDI/psp103.osdi"
  echo "osdi $OSDI/psp103_nqs.osdi"
  echo "osdi $OSDI/mosvar.osdi"
  echo "osdi $OSDI/r3_cmc.osdi"
  if [ "$VARIANT" = real ]; then echo "osdi $OSDI/cap_cmomi.osdi"; fi
  echo "set num_threads=1"
} > "$WORK/.spiceinit"

C_XCW="$(python3 "$HERE/cmomi_nominal.py" 40 40 1)"
C_XC1="$(python3 "$HERE/cmomi_nominal.py" 40 40 2)"
if [ "$VARIANT" = real ]; then
  python3 "$HERE/mom_inject.py" "$SNAP" "$WORK/dut_base.spice" real
else
  python3 "$HERE/mom_inject.py" "$SNAP" "$WORK/dut_base.spice" ideal 0.00 "$C_XCW" "$C_XC1"
fi

# Candidate geometries, as "W:L".  `2u:0.5u` is the AS-DRAWN device (the
# RECORD-002 control point, kept in the sweep so the CSV carries its own
# baseline); `0.25u:16u` is what issue #66 lands.  The others bracket it in
# both directions so the landed choice is visibly a bound and not a pick.
GEOMS="2u:0.5u 0.5u:8u 0.25u:8u 0.5u:16u 0.35u:16u 0.25u:16u 0.25u:32u"

# XRPU resistance per (res_corner, temp), from ../corners/rc_extract_resized.csv
# (issue #52 measured these on the real r3_cmc model; XRPU is untouched by
# issue #66, so they are reused rather than re-extracted).  Used only to size
# each transient's own settling budget, exactly as run.sh does.
r_of() {
  case "$1" in
    res_wcs,-40) echo 3.297015e6 ;;
    res_bcs,125) echo 1.351358e6 ;;
    res_typ,27)  echo 2.266979e6 ;;
    *) echo "ERROR: no extracted R for $1" >&2; exit 1 ;;
  esac
}

echo "sweep,mos_corner,res_corner,temp_c,vsup_v,fref_hz,xmpd_w,xmpd_l,xmpd_l_over_w,twin_r_s,tau_xwin,tau_s,vwin_discharged_start_avg_v,vwin_charged_start_avg_v,lock_discharged_start_avg_v,lock_charged_start_avg_v" \
  > "$CORNERS/xmpd_sizing.csv"

sweep_corner() {  # sweep_corner <label> <mos> <res> <temp> <fref> <fracs...>
  local label="$1" mos="$2" res="$3" temp="$4" fref="$5"; shift 5
  local fracs=("$@")
  local vsup=3.3 vmid=1.65 trst=1n

  local twin
  twin="$( sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" \
        -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" \
        -e "s/@TSTEP@/20p/g" -e "s|@DUT@|$WORK/dut_base.spice|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
      ( cd "$WORK" && ngspice -b w.sp ) 2>/dev/null \
        | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
  [ -n "$twin" ] || { echo "ERROR: twin_r did not resolve at $label" >&2; exit 1; }

  local rval tref rc ncyc tstop tsettle tstep
  rval="$(r_of "$res,$temp")"
  tref="$(python3 -c "print(1.0/$fref)")"
  rc="$(python3 -c "print($rval * $C_XCW)")"
  # Same settling budget rule run.sh uses: 4*R*C, capped at 16 us, rounded up
  # to a whole number of reference periods.
  ncyc="$(python3 -c "
import math
print(int(math.ceil(min(4*$rc, 16e-6)/$tref)))")"
  tstop="$(python3 -c "print($ncyc*$tref)")"
  tsettle="$(python3 -c "print($tstop - 2*$tref)")"
  tstep="$(python3 -c "print($tref/25.0)")"
  echo "[$label] twin_r=$twin R=$rval RC=${rc}s n_cycles=$ncyc" >&2

  local geom w l h frac tau hlog
  for geom in $GEOMS; do
    IFS=: read -r w l <<< "$geom"
    python3 - "$WORK/dut_base.spice" "$WORK/dut_pd.spice" "$w" "$l" <<'PY'
import re, sys
src, dst, w, l = sys.argv[1:5]
text = open(src).read()
pat = re.compile(r"^(XMPD VWIN WIDE VSS VSS sg13_hv_nmos )w=\S+ l=\S+(.*)$", re.M)
if not pat.search(text):
    raise SystemExit("run_xmpd_sizing: XMPD line not found in " + src)
open(dst, "w").write(pat.sub(lambda m: "%sw=%s l=%s%s" % (m.group(1), w, l, m.group(2)), text))
PY
    h="$(python3 -c "
def um(s):
    return float(s[:-1]) if s.endswith('u') else float(s)
print('%.4g' % (um('$l')/um('$w')))")"
    for frac in "${fracs[@]}"; do
      tau="$(python3 -c "print('%.6e' % ($frac*$twin))")"
      sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@TEMP@/$temp/g" \
          -e "s/@VSUP@/$vsup/g" -e "s/@TREF@/$tref/g" -e "s/@TRST@/$trst/g" \
          -e "s/@TAU@/$tau/g" -e "s/@TSTEP@/$tstep/g" -e "s/@TSTOP@/$tstop/g" \
          -e "s/@TSETTLE@/$tsettle/g" -e "s|@DUT@|$WORK/dut_pd.spice|g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_hyst_diag.sp.tmpl" > "$WORK/h.sp"
      # Same one-shot, recorded trtol=1 retry run.sh uses -- see its
      # run_ngspice_or_die header.  The candidate geometries swept here are
      # deliberately WEAKER than anything that could be landed, which is
      # exactly the regime that stresses the solver, so a sizing sweep that
      # dies two geometries in tells us nothing.
      local err="$WORK/h.err"
      if ! hlog="$( cd "$WORK" && ngspice -b h.sp 2>"$err" )"; then
        echo "WARNING: ngspice exited non-zero for $label ${w}/${l} tau=${frac}x; retrying with trtol=1" >&2
        sed -i.bak 's/^\(\.options reltol=.*\)$/\1 trtol=1/' "$WORK/h.sp"
        if ! hlog="$( cd "$WORK" && ngspice -b h.sp 2>"$err" )"; then
          echo "ERROR: ngspice exited non-zero for $label ${w}/${l} tau=${frac}x even with trtol=1:" >&2
          cat "$err" >&2
          exit 1
        fi
        echo "sizing ${label} ${w}/${l} tau=${frac}x" >> "$CORNERS/solver_retries.txt"
      fi
      get() { printf '%s\n' "$hlog" | sed -n "s/^$1 *= *\([0-9.eE+-]*\).*/\1/p" | head -1; }
      echo "${label},${mos},${res},${temp},${vsup},${fref},${w},${l},${h},${twin},${frac},${tau},$(get va_avg),$(get vb_avg),$(get la_avg),$(get lb_avg)" \
        >> "$CORNERS/xmpd_sizing.csv"
      echo "  [$label ${w}/${l} tau=${frac}x] VWIN=$(get va_avg) LOCK(dis)=$(get la_avg) LOCK(chg)=$(get lb_avg)" >&2
    done
  done
}

# A. Smallest-hysteresis corner, fast reference end.  Dense across the
#    transition, which sits between 1x and 2.5x the window at every candidate.
sweep_corner min_hysteresis mos_ff res_wcs -40 24.4e6 \
  1.00 1.20 1.40 1.60 1.80 2.00 2.50

# B. Furthest-threshold corner, slow reference end.  Coarser but much longer
#    reach: the same geometries put their de-assert threshold 5-20x the window
#    out here, which is the bound that stops XMPD getting weaker still.
sweep_corner max_threshold mos_tt res_bcs 125 3.5e6 \
  1.00 2.00 4.00 6.00 8.00 10.00 12.00 14.00 16.00 20.00 24.00

echo "done: $(wc -l < "$CORNERS/xmpd_sizing.csv") lines (incl. header) -> $CORNERS/xmpd_sizing.csv" >&2
