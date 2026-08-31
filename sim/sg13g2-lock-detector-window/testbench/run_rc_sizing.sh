#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-lock-detector-window/testbench/run_rc_sizing.sh
# (issue #82, Part of #16 via #78 -- SG13G2 PVT campaign, Phase 2/2)
#
# SIZING EVIDENCE for this issue's XRPU / XCW / XDW.XC1 re-size.  It is NOT
# part of the pass/fail campaign -- ./run.sh measures spec/porting-plan.md
# row 16's criteria against the block as committed.  THIS script is the
# measurement the three chosen geometries are argued from, so each choice is a
# bound read off a committed CSV rather than a number asserted in a schematic
# header (and, per issue #82's own non-goals, is NOT the sibling PDK's number
# copied across).
#
# ---------------------------------------------------------------------------
# THE TWO CRITERIA, AND WHY THEY SPLIT INTO TWO INDEPENDENT SIZING PROBLEMS.
#
#   1. `R(XRPU) * C(XCW)  >>  T_ref`  -- the integrating-node time constant.
#      This is the inequality issue #52 found violated by ~3 orders of
#      magnitude on the SG13CMOS5L sibling, and ../corners/rc_extract.csv
#      (issue #81, this slug's own Phase 1) found violated by the same margin
#      here: 0.65-1.57 ns against a 41-286 ns T_ref range.  It is ONE-SIDED
#      (R*C must EXCEED T_ref), and T_ref only shrinks as f_ref rises, so the
#      BINDING point is row 2's DR-005-amended SLOW end, f_ref = 3.5 MHz,
#      T_ref = 285.7 ns; and within that, the corner where R*C is smallest
#      (res_bcs / 125 C / cap_bcs).
#
#   2. `twin_r >= 2.5 ns`  -- row 16's assert-window floor.  twin_r is the
#      four-inverter delaywin_hv chain's low->high delay loaded by XDW.XC1, so
#      it is set by XC1 and NOT by XRPU/XCW at all.  A floor is a worst-case
#      claim, so the binding point is the corner that MINIMISES twin_r: every
#      fast-direction axis stacked at once (mos_ff / res_bcs / cap_bcs /
#      -40 C / 3.63 V), which is exactly the stack the SG13CMOS5L sibling's
#      own RECORD-002 had to add after RECORD-001's sub-sweeps missed it.
#
# The two criteria therefore do not trade against each other here: XC1 is
# sized by (2) alone, and the XRPU/XCW pair by (1) alone.  What DOES trade is
# how criterion (1)'s R*C product is split between R and C -- a larger R keeps
# the MIM area down but raises the integrating node's impedance (leakage and
# coupling sensitivity, and a weaker pull-up for XMPD to work against, which
# is the ./run_xmpd_sizing.sh knob).  Section 1 below sweeps XRPU's length so
# that split is visible in the CSV rather than asserted.
#
# ---------------------------------------------------------------------------
# WHY THIS IS A RE-DERIVATION AND NOT A PORT OF THE SIBLING'S NUMBERS.
#
# `rhigh` IS the same device on both PDKs (../testbench/tb_extract_r.sp.tmpl's
# header records that the two installed trees carry the same cornerRES.lib
# with the same 1360/1020/1700 ohm/sq values), so section 1's R-vs-length
# numbers are expected to land on the sibling's -- and section 1 measures them
# on THIS PDK's installed tree anyway rather than citing them.
#
# The capacitor is NOT the same device.  SG13CMOS5L's `cap_cmomi` is an
# interdigitated MoM whose 40u x 40u m=1 instance the sibling measured at
# 1.691 pF (~1.06 fF/um^2); SG13G2's `cap_cmim` is a MIM stack, and section 2
# measures it at ~1.5 fF/um^2 + a small perimeter term.  Dropping the
# sibling's geometries onto this PDK would therefore land ~1.4x more
# capacitance than intended at both instance sites -- which is precisely the
# "four numbers with no derivation on that PDK" issue #78 refused.  Both
# capacitor geometries below are chosen from THIS script's own CSV.
#
# Output:
#   ../corners/rc_sizing.csv      one row per (device, geometry, corner, temp)
#                                 for the XRPU-length and XCW-geometry
#                                 candidate grids, plus, for every
#                                 (XRPU-length x XCW-geometry) pair, the
#                                 worst-case (smallest) R*C over the whole
#                                 corner grid and its ratio to T_ref at the
#                                 binding 3.5 MHz slow end.
#   ../corners/window_sizing.csv  twin_r / twin_f vs. XDW.XC1 candidate
#                                 geometry at three window corners: the
#                                 worst-case FAST stack (the binding one for
#                                 the 2.5 ns floor), nominal, and the
#                                 worst-case SLOW stack.
#
# Nothing is written back into design/ or ../netlist-snapshots/ -- every
# geometry is simulated on a scratch copy in a temp dir.
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
#   export PDK=ihp-sg13g2
#   ./run_rc_sizing.sh
#
# Runtime: ~2 min (every deck here is a single-device DC/AC solve or a 60 ns
# transient on a bare delaywin_hv).

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
SNAP="$RECORD_DIR/netlist-snapshots/lock_detector.spice"   # the PRE-resize snapshot

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

TREF_SLOW=285.714285714e-9   # 1 / 3.5 MHz -- row 2 (DR-005) slow end, binding for R*C

# `0.5u:6u` is the AS-DRAWN (pre-#82) XRPU; the rest bracket the landed choice
# in both directions so it is visibly a bound and not a pick.
XRPU_GEOMS="0.5u:6u 0.5u:100u 0.5u:300u 0.5u:500u 0.5u:700u 0.5u:1000u"
# `6u:6u` is the AS-DRAWN XCW; `4u:4u` the as-drawn XDW.XC1.  The cap
# candidate grid is shared by both instance sites (one extraction serves both
# sections) because they are the same device at the same corners.
CAP_GEOMS="4u:4u 6u:6u 20u:20u 30u:30u 36u:36u 40u:40u 45u:45u 50u:50u"

echo "kind,geom_w,geom_l,geom_m,corner,temp_c,value,source" > "$CORNERS/rc_sizing.csv"

declare -A RVAL CVAL
for geom in $XRPU_GEOMS; do
  IFS=: read -r w l <<< "$geom"
  for rc in res_typ res_bcs res_wcs; do
    for temp in -40 27 125; do
      sed -e "s/@RES_CORNER@/$rc/g" -e "s/@TEMP@/$temp/g" \
          -e "s/@W@/$w/g" -e "s/@L@/$l/g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_extract_r.sp.tmpl" > "$WORK/r.sp"
      val="$( cd "$WORK" && ngspice -b r.sp 2>/dev/null \
              | sed -n 's/^rval *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
      [ -n "$val" ] || { echo "ERROR: R did not resolve at $geom/$rc/${temp}C" >&2; exit 1; }
      echo "R(rhigh),${w},${l},1,${rc},${temp},${val},ngspice-subckt" >> "$CORNERS/rc_sizing.csv"
      RVAL["$geom,$rc,$temp"]="$val"
    done
  done
  echo "[R] ${geom}: $(printf '%s ' "${RVAL[$geom,res_bcs,125]}" "${RVAL[$geom,res_typ,27]}" "${RVAL[$geom,res_wcs,-40]}")ohm (bcs/125C, typ/27C, wcs/-40C)" >&2
done

for geom in $CAP_GEOMS; do
  IFS=: read -r w l <<< "$geom"
  for cc in cap_typ cap_bcs cap_wcs; do
    for temp in -40 27 125; do
      sed -e "s/@CAP_CORNER@/$cc/g" -e "s/@W@/$w/g" -e "s/@L@/$l/g" -e "s/@M@/1/g" \
          -e "s/@TEMP@/$temp/g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_extract_c.sp.tmpl" > "$WORK/c.sp"
      val="$( cd "$WORK" && ngspice -b c.sp 2>/dev/null \
              | awk '/^0[[:space:]]/ {print $3; exit}' )"
      [ -n "$val" ] || { echo "ERROR: C did not resolve at $geom/$cc/${temp}C" >&2; exit 1; }
      echo "C(cap_cmim),${w},${l},1,${cc},${temp},${val},ngspice-subckt" >> "$CORNERS/rc_sizing.csv"
      CVAL["$geom,$cc,$temp"]="$val"
    done
  done
  echo "[C] ${geom}: ${CVAL[$geom,cap_typ,27]} F (cap_typ/27C)" >&2
done

# ---------------------------------------------------------------------------
# Derived: worst-case R*C over the FULL 3x3 res-corner x 3x3 cap-corner x
# temperature grid, per (XRPU length, XCW geometry) pair.  The temperature
# axis is shared between R and C (one die, one temperature), so the pairing
# below only combines rows at the SAME temp -- pairing res_bcs/125 C with
# cap_bcs/-40 C would be a corner that cannot happen.
# ---------------------------------------------------------------------------
{
  echo "xrpu_w,xrpu_l,xcw_w,xcw_l,rc_min_s,rc_min_at,rc_max_s,rc_max_at,rc_min_over_tref_slow,rc_max_over_tref_slow"
  for rgeom in $XRPU_GEOMS; do
    for cgeom in $CAP_GEOMS; do
      IFS=: read -r rw rl <<< "$rgeom"
      IFS=: read -r cw cl <<< "$cgeom"
      best=""; worst=""
      for rc in res_typ res_bcs res_wcs; do
        for cc in cap_typ cap_bcs cap_wcs; do
          for temp in -40 27 125; do
            prod="$(python3 -c "print(${RVAL[$rgeom,$rc,$temp]}*${CVAL[$cgeom,$cc,$temp]})")"
            tag="${rc}/${cc}/${temp}C"
            if [ -z "$best" ] || python3 -c "import sys; sys.exit(0 if $prod < ${best%%|*} else 1)"; then
              best="$prod|$tag"
            fi
            if [ -z "$worst" ] || python3 -c "import sys; sys.exit(0 if $prod > ${worst%%|*} else 1)"; then
              worst="$prod|$tag"
            fi
          done
        done
      done
      python3 -c "
rmin, tmin = '${best%%|*}', '${best##*|}'
rmax, tmax = '${worst%%|*}', '${worst##*|}'
print('$rw,$rl,$cw,$cl,%.6e,%s,%.6e,%s,%.4f,%.4f'
      % (float(rmin), tmin, float(rmax), tmax,
         float(rmin)/$TREF_SLOW, float(rmax)/$TREF_SLOW))"
    done
  done
} > "$CORNERS/rc_pairing.csv"

# ---------------------------------------------------------------------------
# Section 3: twin_r vs. XDW.XC1 geometry -- row 16's assert-window floor.
#
# Three window corners per candidate.  `fast_stack` is the binding one: a
# floor is a worst-case claim, and this stacks every axis that shortens the
# delaywin_hv chain's own delay at once.  `nominal` and `slow_stack` are
# reported alongside so the record can state the FULL spread the landed
# geometry produces, not only the number the criterion is read from.
# ---------------------------------------------------------------------------
echo "stack,mos_corner,res_corner,cap_corner,temp_c,vsup_v,xc1_w,xc1_l,xc1_m,twin_r_s,twin_f_s,twin_r_over_floor" \
  > "$CORNERS/window_sizing.csv"

WINDOW_STACKS=(
  "fast_stack mos_ff res_bcs cap_bcs -40 3.63"
  "nominal    mos_tt res_typ cap_typ  27 3.3"
  "slow_stack mos_ss res_wcs cap_wcs 125 2.97"
)

for geom in $CAP_GEOMS; do
  IFS=: read -r w l <<< "$geom"
  python3 - "$SNAP" "$WORK/dut_xc1.spice" "$w" "$l" <<'PY'
import re, sys
src, dst, w, l = sys.argv[1:5]
text = open(src).read()
pat = re.compile(r"^XC1 OUT VSS cap_cmim w=\S+ l=\S+(.*)$", re.M)
if not pat.search(text):
    raise SystemExit("run_rc_sizing: XC1 line not found in " + src)
open(dst, "w").write(
    pat.sub(lambda m: "XC1 OUT VSS cap_cmim w=%s l=%s%s" % (w, l, m.group(1)), text))
PY
  for stack in "${WINDOW_STACKS[@]}"; do
    read -r label mos res cap temp vsup <<< "$stack"
    vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
    sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
        -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TSTEP@/20p/g" \
        -e "s|@DUT@|$WORK/dut_xc1.spice|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
    wlog="$( cd "$WORK" && ngspice -b w.sp 2>/dev/null )"
    tr="$(printf '%s\n' "$wlog" | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
    tf="$(printf '%s\n' "$wlog" | sed -n 's/^twin_f *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
    [ -n "$tr" ] || { echo "ERROR: twin_r did not resolve at ${geom}/${label}" >&2; exit 1; }
    echo "${label},${mos},${res},${cap},${temp},${vsup},${w},${l},1,${tr},${tf},$(python3 -c "print('%.4f' % ($tr/2.5e-9))")" \
      >> "$CORNERS/window_sizing.csv"
    echo "  [W ${geom} ${label}] twin_r=${tr} (=$(python3 -c "print('%.3f' % ($tr/2.5e-9))")x the 2.5 ns floor)" >&2
  done
done

echo "done:" >&2
for f in rc_sizing rc_pairing window_sizing; do
  echo "  $(wc -l < "$CORNERS/${f}.csv") lines (incl. header) -> $CORNERS/${f}.csv" >&2
done
