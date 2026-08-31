#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-lock-detector-window/testbench/run_xmpd_sizing.sh
# (issue #82, Part of #16 via #78 -- SG13G2 PVT campaign, Phase 2/2)
#
# SIZING EVIDENCE for this issue's XMPD re-size, using the two-sided bound
# METHOD of ../../sg13cmos5l-lock-detector-window/testbench/run_xmpd_sizing.sh
# (issue #66 / RECORD-003) -- the method is reused; every NUMBER below is
# re-measured on this PDK, against this PDK's own XRPU/XCW geometries as
# ./run_rc_sizing.sh derived them.  Not part of the pass/fail campaign:
# ./run.sh measures spec/porting-plan.md row 16's criteria against the block
# as committed.  THIS script is the measurement the chosen XMPD geometry is
# argued from, so the choice is a two-sided bound read off a committed CSV
# rather than a number asserted in a schematic header.
#
# ---------------------------------------------------------------------------
# THE MECHANISM, IN ONE PARAGRAPH.  Established by control on the SG13CMOS5L
# sibling (RECORD-002 § "Why the hysteresis criterion still fails" /
# RECORD-003) and reused here as TOPOLOGY, not as a PDK measurement, per
# issue #78's own "Reusable facts" list.  Row 16's hysteresis criterion is a
# PHASE-ERROR width, and in this topology it factors:
#
#     H_tau  ~=  H_volts(schmitt_hv)  /  |dVWIN/dtau|
#
# and the settled VWIN is the balance between XRPU's charge over ONE
# REFERENCE PERIOD and XMPD's discharge over ONE WIDE PULSE:
#
#     VWIN  ~=  VDD  -  I_sat(XMPD) * R(XRPU) * (tau - twin_r) / T_ref
#
# so the transition width is set by the XRPU/XMPD strength ratio, and R*C --
# which ./run_rc_sizing.sh spends its whole margin on -- does not appear in it
# at all.  XMPD is therefore the knob that buys transition width WITHOUT
# spending that R*C margin.
#
# H_volts is NOT a defect on this PDK.  schmitt_hv's feedback devices are
# already on the classic cross-coupled connection here (issue #66 landed that
# on both PDKs; design/netlist/lock_detector.spice's XMP3/XMN3 lines show it),
# and ../corners/schmitt.csv measures 804-1058 mV of it across the full
# 45-point MOS x temperature x supply grid.  So unlike the sibling's own
# campaign, this script does not have to re-measure a rewired control: the
# only unknown left in the factorisation above is |dVWIN/dtau|, i.e. XMPD.
#
# ---------------------------------------------------------------------------
# WHY BOTH ENDS OF THE f_ref RANGE, AND WHY THEY PULL OPPOSITE WAYS.  T_ref is
# in the numerator above, so at row 2's DR-005-amended FAST end (24.4 MHz,
# T_ref = 41 ns) the transition is ~7x STEEPER -- i.e. the hysteresis in units
# of the window is ~7x SMALLER -- than at the slow end (3.5 MHz, 286 ns).  The
# fast end is therefore the BINDING end for row 16's >= 25%-of-window
# criterion.
#
# The same T_ref factor also scales the assert/de-assert THRESHOLDS, so
# weakening XMPD until the fast end clears the criterion simultaneously pushes
# the slow end's de-assert threshold out.  If it goes past ~half a reference
# period the block stops being a lock detector at the slow end.  Hence a
# two-sided bound, and hence this script sweeps candidate geometries at BOTH:
#
#   A. mos_tt/res_wcs/cap_typ/-40C @ 24.4 MHz -- the SMALLEST-hysteresis
#      corner.  Sets the LOWER bound on how strong XMPD may be.
#   B. mos_ss/res_bcs/cap_typ/125C @ 3.5 MHz -- the corner whose de-assert
#      threshold sits furthest out relative to its OWN T_ref/2 ceiling.  Sets
#      the UPPER bound on how weak XMPD may be.
#
# WHY THOSE mos CORNERS AND NOT THE OBVIOUS ONES (measured, not argued).  A
# first pass of this script used mos_ff for A (strongest I_sat => steepest
# transition) and mos_tt for B.  Both are wrong on this block, and
# ../records/RECORD-001 records the correction rather than hiding it:
#
#   - For A, the criterion is a fraction OF THE WINDOW, and twin_r moves with
#     mos_corner too.  Measured at res_wcs/-40C/24.4 MHz with the landed
#     XRPU/XCW: mos_ff gives twin_r = 4.524 ns and 43.5% of window, mos_tt
#     gives twin_r = 5.291 ns and 13.0%.  mos_tt is the worse corner by 3.3x,
#     because the narrow-pulse knee in the settled-VWIN characteristic (see
#     below) lands between schmitt_hv's two trip points there and outside them
#     at mos_ff.  ./run.sh's own ladder carries mos_ff/res_wcs/-40C at the
#     fast end as the control that keeps this visible.
#   - For B, the ceiling is T_ref/2 expressed in units of that corner's OWN
#     window, so the LARGEST twin_r tightens it: mos_ss/res_bcs/125C has
#     twin_r = 8.517 ns and a ceiling of 16.77x window, against mos_tt's
#     7.197 ns and 19.84x.  mos_ss also has the weakest I_sat, which pushes
#     the threshold itself further out.  Both effects point the same way.
#
# THE NARROW-PULSE KNEE.  WIDE = ERR AND delaywin_hv(ERR), so for tau only
# slightly above twin_r the WIDE pulse is very short and the nand2_hv + inv_hv
# pair does not drive XMPD's gate to a full rail.  The settled VWIN therefore
# has a KNEE a few percent of a window above tau = twin_r, across which it
# falls much faster than the linear model above predicts.  Whether row 16's
# hysteresis criterion passes depends on whether schmitt_hv's two trip points
# straddle that knee -- which is a property of the XRPU/XMPD ratio, and is
# exactly what this sweep measures.  It is why the admissible XMPD band below
# is narrow, and why it has to be read off a CSV rather than derived from the
# one-line model.
#
# `cap_corner` is fixed at cap_typ at both.  This script isolates the
# XRPU/XMPD ratio, in which C does not appear at all -- C reaches these decks
# only through the settling budget (n_cycles below), where a +/-10% cap corner
# moves the achieved settling fraction and not the settled value.  The
# capacitor-corner axis is swept at full density by ./run.sh's own window and
# ladder matrices instead.
#
# Output ../corners/xmpd_sizing.csv reports the SETTLED INTEGRATING-NODE
# VOLTAGE (not just the thresholded LOCK pin) per geometry per phase-error
# point, plus both LOCK copies, so ../records/RECORD-001 can interpolate the
# two trip points against ../corners/schmitt.csv's own measured Schmitt trip
# voltages instead of relying on ladder quantisation.
#
# Every geometry is simulated on a scratch copy in a temp dir; nothing is
# written back into design/ or ../netlist-snapshots/.
#
# XMPD_JOBS=<n> runs up to n sweep POINTS concurrently (default 1 = serial).
# Legitimate for the same reason ../../sg13cmos5l-lock-detector-window's own
# LADDER_JOBS is: every point is an independent ngspice invocation against the
# same frozen snapshot, the same template and the same host, and nothing in
# one point's result feeds another's -- so concurrency is concatenation, not a
# change of method.  Each point writes its OWN row file under $WORK and the
# driver concatenates them in sweep order, so the CSV comes out in exactly the
# order a serial run produces and is byte-comparable with one.  A record
# produced with it > 1 must say so, and must not also claim serial per-point
# wall times.
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
#   export PDK=ihp-sg13g2
#   ./run_xmpd_sizing.sh                # or: XMPD_JOBS=6 ./run_xmpd_sizing.sh
#
# Runtime: ~2.5 h serial (the 24.4 MHz sweep needs 782 reference periods per
# point); ~25 min at XMPD_JOBS=6 on an 8-core host.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
# The RC-resized, pre-XMPD snapshot: XRPU / XCW / XDW.XC1 at the geometries
# ./run_rc_sizing.sh derived, XMPD still as drawn.  XMPD is substituted per
# candidate below (including the as-drawn 2u/0.5u baseline), so this snapshot
# is the input to the SECOND half of the derivation and is frozen separately
# from ./lock_detector_resized.spice, which carries the landed XMPD and is
# what ./run.sh's verification CSVs are measured against.
SNAP="$RECORD_DIR/netlist-snapshots/lock_detector_rc_resized.spice"

# Same hard-abort OSDI preflight, and same absence of a --soft branch, that
# ./run.sh uses -- see its header for why cap_cmim needs neither.
"$HERE/../../tools/check-osdi-arch.sh" --quiet \
  "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" "$OSDI/r3_cmc.osdi"

{
  echo "osdi $OSDI/psp103.osdi"
  echo "osdi $OSDI/psp103_nqs.osdi"
  echo "osdi $OSDI/mosvar.osdi"
  echo "osdi $OSDI/r3_cmc.osdi"
  echo "set num_threads=1"
} > "$WORK/.spiceinit"

K_SETTLE=4           # tstop ~ K_SETTLE * R*C  (1 - e^-4 = 98.2%)
# TSTOP_MAX is 32 us, not the 16 us a first pass of this script used.  With the
# landed XRPU/XCW, R*C reaches 7.17 us at the res_wcs/-40C corner sweep A runs
# at, so a 16 us cap left settle_frac = 0.893 there -- and at 89% settled the
# two start-state copies had NOT yet converged, which read out as a spurious
# ~0.2x-window "bistability" that vanished entirely once the budget was
# raised.  Measured directly at mos_tt/res_wcs/-40C, tau = 1.25x window:
# VWIN(discharged-start) / VWIN(charged-start) = 2.017 / 2.334 V at 391 cycles
# (settle_frac 0.893) versus 2.197 / 2.234 V at 782 cycles (settle_frac 0.989).
# 32 us keeps settle_frac >= 0.98 at every corner either sweep runs.
TSTOP_MAX=32e-6      # absolute cap on one transient's simulated time
TSTEP_DIV=25         # maximum internal timestep = tref / TSTEP_DIV

# Candidate geometries, as "W:L".  `2u:0.5u` is the AS-DRAWN (pre-#82) device,
# kept in the sweep so the CSV carries its own baseline; the rest bracket the
# landed choice in both directions -- across a 190x span of W/L -- so it is
# visibly a bound and not a pick.
GEOMS="2u:0.5u 0.5u:4u 0.35u:6u 0.25u:8u 0.25u:10u 0.25u:12u 0.25u:16u"

# XRPU's R and XCW's C at the LANDED geometries, read out of this slug's own
# committed ../corners/rc_sizing.csv (./run_rc_sizing.sh's measurement on this
# PDK) rather than hardcoded here or carried across from the sibling PDK.
# They are used only to size each transient's own settling budget -- the
# settled VALUES this script reports come from the transient itself.
XRPU_W=0.5u; XRPU_L=500u
XCW_W=45u;   XCW_L=45u
rc_lookup() {  # rc_lookup <kind-prefix> <w> <l> <corner> <temp>
  python3 - "$CORNERS/rc_sizing.csv" "$1" "$2" "$3" "$4" "$5" <<'PY'
import csv, sys
path, kind, w, l, corner, temp = sys.argv[1:7]
for r in csv.DictReader(open(path)):
    if (r["kind"].startswith(kind) and r["geom_w"] == w and r["geom_l"] == l
            and r["corner"] == corner and r["temp_c"] == temp):
        print(r["value"]); break
else:
    raise SystemExit("run_xmpd_sizing: no %s row for %s/%s %s/%sC in %s"
                     % (kind, w, l, corner, temp, path))
PY
}

echo "sweep,mos_corner,res_corner,cap_corner,temp_c,vsup_v,fref_hz,r_xrpu_ohm,c_xcw_f,rc_s,n_cycles,settle_frac,xmpd_w,xmpd_l,xmpd_l_over_w,twin_r_s,tau_xwin,tau_s,vwin_discharged_start_avg_v,vwin_charged_start_avg_v,lock_discharged_start_avg_v,lock_charged_start_avg_v" \
  > "$CORNERS/xmpd_sizing.csv"

JOBS="${XMPD_JOBS:-1}"
ORDER=()

run_point() {  # run_point <rowfile> <label> <mos> <res> <cap> <temp> <fref> <w> <l> <twin> <tref> <tstop> <tsettle> <tstep> <r> <c> <rc> <ncyc> <sfrac> <frac>
  local rowf="$1" label="$2" mos="$3" res="$4" cap="$5" temp="$6" fref="$7"
  local w="$8" l="$9" twin="${10}" tref="${11}" tstop="${12}" tsettle="${13}"
  local tstep="${14}" rval="${15}" cval="${16}" rc="${17}" ncyc="${18}"
  local sfrac="${19}" frac="${20}"
  local vsup=3.3 trst=1n
  local sfx; sfx="$(echo "${label}_${w}_${l}_${frac}" | tr -c 'A-Za-z0-9_' '_')"

  python3 - "$SNAP" "$WORK/dut_$sfx.spice" "$w" "$l" <<'PY'
import re, sys
src, dst, w, l = sys.argv[1:5]
text = open(src).read()
pat = re.compile(r"^(XMPD VWIN WIDE VSS VSS sg13_hv_nmos )w=\S+ l=\S+(.*)$", re.M)
if not pat.search(text):
    raise SystemExit("run_xmpd_sizing: XMPD line not found in " + src)
open(dst, "w").write(pat.sub(lambda m: "%sw=%s l=%s%s" % (m.group(1), w, l, m.group(2)), text))
PY

  local tau lw
  tau="$(python3 -c "print('%.6e' % ($frac*$twin))")"
  lw="$(python3 -c "
def um(s): return float(s[:-1]) if s.endswith('u') else float(s)
print('%.4g' % (um('$l')/um('$w')))")"
  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
      -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@TREF@/$tref/g" -e "s/@TRST@/$trst/g" \
      -e "s/@TAU@/$tau/g" -e "s/@TSTEP@/$tstep/g" -e "s/@TSTOP@/$tstop/g" \
      -e "s/@TSETTLE@/$tsettle/g" -e "s|@DUT@|$WORK/dut_$sfx.spice|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_hyst_diag.sp.tmpl" > "$WORK/h_$sfx.sp"

  # Same one-shot, RECORDED trtol=1 retry ./run.sh uses (see its
  # run_ngspice_or_die header).  The candidate geometries swept here are
  # deliberately weaker than anything that could be landed, which is exactly
  # the regime that stresses the solver, so a sizing sweep that dies two
  # geometries in tells us nothing.
  local hlog err="$WORK/h_$sfx.err"
  if ! hlog="$( cd "$WORK" && ngspice -b "h_$sfx.sp" 2>"$err" )"; then
    echo "WARNING: ngspice exited non-zero for $label ${w}/${l} tau=${frac}x; retrying with trtol=1" >&2
    sed -i.bak 's/^\(\.options reltol=.*\)$/\1 trtol=1/' "$WORK/h_$sfx.sp"
    if ! hlog="$( cd "$WORK" && ngspice -b "h_$sfx.sp" 2>"$err" )"; then
      echo "ERROR: ngspice exited non-zero for $label ${w}/${l} tau=${frac}x even with trtol=1:" >&2
      cat "$err" >&2
      return 1
    fi
    echo "xmpd_sizing ${label} ${w}/${l} tau=${frac}x" >> "$CORNERS/solver_retries_xmpd.txt"
  fi
  get() { printf '%s\n' "$hlog" | sed -n "s/^$1 *= *\([0-9.eE+-]*\).*/\1/p" | head -1; }
  echo "${label},${mos},${res},${cap},${temp},${vsup},${fref},${rval},${cval},${rc},${ncyc},${sfrac},${w},${l},${lw},${twin},${frac},${tau},$(get va_avg),$(get vb_avg),$(get la_avg),$(get lb_avg)" \
    > "$rowf"
  echo "  [$label ${w}/${l} tau=${frac}x] VWIN=$(get va_avg) LOCK(dis)=$(get la_avg) LOCK(chg)=$(get lb_avg)" >&2
}

sweep_corner() {  # sweep_corner <label> <mos> <res> <cap> <temp> <fref> <fracs...>
  local label="$1" mos="$2" res="$3" cap="$4" temp="$5" fref="$6"; shift 6
  local fracs=("$@")
  local vsup=3.3 vmid=1.65

  local twin
  twin="$( sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
        -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" \
        -e "s/@TSTEP@/20p/g" -e "s|@DUT@|$SNAP|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_window.sp.tmpl" > "$WORK/w_$label.sp"
      ( cd "$WORK" && ngspice -b "w_$label.sp" ) 2>/dev/null \
        | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
  [ -n "$twin" ] || { echo "ERROR: twin_r did not resolve at $label" >&2; exit 1; }

  local rval cval tref rc ncyc tstop tsettle tstep sfrac
  rval="$(rc_lookup R "$XRPU_W" "$XRPU_L" "$res" "$temp")"
  cval="$(rc_lookup C "$XCW_W" "$XCW_L" "$cap" "$temp")"
  tref="$(python3 -c "print(1.0/$fref)")"
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
  echo "[$label] twin_r=$twin R=$rval C=$cval RC=${rc}s n_cycles=$ncyc settle_frac=$sfrac" >&2

  local geom w l frac rowf
  for geom in $GEOMS; do
    IFS=: read -r w l <<< "$geom"
    for frac in "${fracs[@]}"; do
      rowf="$WORK/row_$(printf '%04d' ${#ORDER[@]})"
      ORDER+=("$rowf")
      if [ "$JOBS" -gt 1 ]; then
        while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n; done
        run_point "$rowf" "$label" "$mos" "$res" "$cap" "$temp" "$fref" "$w" "$l" \
                  "$twin" "$tref" "$tstop" "$tsettle" "$tstep" "$rval" "$cval" \
                  "$rc" "$ncyc" "$sfrac" "$frac" &
      else
        run_point "$rowf" "$label" "$mos" "$res" "$cap" "$temp" "$fref" "$w" "$l" \
                  "$twin" "$tref" "$tstop" "$tsettle" "$tstep" "$rval" "$cval" \
                  "$rc" "$ncyc" "$sfrac" "$frac"
      fi
    done
  done
  if [ "$JOBS" -gt 1 ]; then
    wait || { echo "ERROR: at least one concurrent sizing point failed" >&2; exit 1; }
  fi
}

# A. Smallest-hysteresis corner, fast reference end.  Dense from the window
#    edge outward: with a strong XMPD the whole transition sits inside
#    1.0-1.35x the window, so a coarser ladder would report "no hysteresis"
#    for want of resolution rather than for want of hysteresis.
sweep_corner min_hysteresis mos_tt res_wcs cap_typ -40 24.4e6 \
  1.00 1.10 1.20 1.25 1.30 1.35 1.40 1.50 1.60 1.75 2.00 2.25 2.50

# B. Furthest-threshold corner, slow reference end.  Coarser but much longer
#    reach: the weaker candidates put their de-assert threshold many multiples
#    of the window out here, which is the bound that stops XMPD getting weaker
#    still.
sweep_corner max_threshold mos_ss res_bcs cap_typ 125 3.5e6 \
  1.00 2.00 4.00 6.00 8.00 10.00 12.00 14.00 16.00 18.00 20.00 22.00 24.00

for rowf in "${ORDER[@]}"; do
  [ -s "$rowf" ] || { echo "ERROR: missing sizing row $rowf" >&2; exit 1; }
  cat "$rowf" >> "$CORNERS/xmpd_sizing.csv"
done

echo "done: $(wc -l < "$CORNERS/xmpd_sizing.csv") lines (incl. header) -> $CORNERS/xmpd_sizing.csv" >&2
