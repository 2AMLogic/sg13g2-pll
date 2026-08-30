#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/run_hysteresis_diag.sh
# (issue #52, Part of #16)
#
# SUPPLEMENTARY DIAGNOSTIC, not part of the main campaign.  ./run.sh measures
# spec/porting-plan.md row 16's three criteria (assert window, hysteresis,
# chatter) against the resized block.  Issue #52's resize fixes the window and
# the chatter criteria; the HYSTERESIS criterion still fails, and this script
# exists so ../records/RECORD-002 can attribute that failure to a measured
# mechanism instead of to an argument -- the same discipline RECORD-001 used
# when it root-caused its own chatter finding to the R*C time constant.
#
# In this topology the phase-error hysteresis row 16 asks for is the product
# of exactly two things:
#
#   H_tau  ~=  H_volts(schmitt_hv)  /  |dVWIN/dtau|
#
# so it is zero if EITHER term is degenerate.  This script measures both, at
# one corner, and separates them:
#
#   A. |dVWIN/dtau| -- the width, in units of the comparator window, of the
#      region over which the settled integrating-node voltage moves from rail
#      to rail.  Swept finely with ../testbench/tb_hyst_diag.sp.tmpl (which
#      reports VWIN itself, not just the thresholded LOCK pin).
#
#   B. H_volts -- schmitt_hv's own input-referred hysteresis.  Measured by
#      ../testbench/tb_schmitt_hyst.sp.tmpl twice: once on the block AS DRAWN,
#      and once on a SCRATCH variant in which schmitt_hv's two feedback
#      devices are re-tied to the opposite rail (XMP3 drain -> VSS with its
#      source on np, XMN3 drain -> VDD with its source on nn -- the classic
#      six-transistor CMOS Schmitt connection).  Comparing the two isolates
#      how much of the missing hysteresis is attributable to that wiring.
#
# Sweep A is run against THREE DUTs so each candidate mechanism is separated
# by a control rather than by an argument:
#
#   as_drawn                    the resized block exactly as committed.
#   schmitt_feedback_rewired    as_drawn + the schmitt_hv rewiring above.  If
#                               the phase-error transition does not move, then
#                               schmitt_hv's missing VOLTAGE hysteresis is not
#                               the binding term -- dVWIN/dtau is.
#   xmpd_weakened               as_drawn + XMPD (the WIDE-gated pull-down)
#                               weakened from w=2u l=0.5u to w=0.5u l=8u, i.e.
#                               ~64x its on-resistance, with XRPU and XCW (and
#                               therefore R*C) untouched.  The settled VWIN is
#                               set by the balance between XRPU's charge over
#                               one reference period and XMPD's discharge over
#                               one WIDE pulse, so this is the knob that sets
#                               the WIDTH of the transition without touching
#                               the R*C margin.  If the transition widens,
#                               the XRPU/XMPD strength ratio is confirmed as
#                               the mechanism.
#
# ALL scratch variants are built in a temp dir and are NEVER written back into
# design/ or ../netlist-snapshots/: they are diagnostic controls, not
# proposals this script is authorised to land.
#
# Writes ../corners/hysteresis_diag.csv (sweep A) and
# ../corners/hysteresis_diag_schmitt.csv (sweep B).
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root
#   export PDK=ihp-sg13cmos5l
#   ./run_hysteresis_diag.sh

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
CORNERS="$RECORD_DIR/corners"
SNAP="$RECORD_DIR/netlist-snapshots/lock_detector_resized.spice"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"

# Same OSDI host-architecture preflight run.sh uses, with the same single
# `--soft` opt-out for cap_cmomi -- see run.sh's own HOST NOTE for why this
# one object has a fallback and the other four do not.
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

# The cap_cmomi `osdi` line is emitted only when the preflight says the object
# is loadable -- a guaranteed-failing dlopen in .spiceinit buys nothing and
# only obscures the real diagnosis this script's own decks would print.
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
  python3 "$HERE/mom_inject.py" "$SNAP" "$WORK/dut.spice" real
else
  python3 "$HERE/mom_inject.py" "$SNAP" "$WORK/dut.spice" ideal 0.00 "$C_XCW" "$C_XC1"
fi

# Scratch schmitt_hv control variant (see header B).  Re-ties the two feedback
# devices to the opposite rail; every other line is untouched.
python3 - "$WORK/dut.spice" "$WORK/dut_schfix.spice" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()
subs = [
    ("XMP3 np OUT VDD VDD sg13_hv_pmos", "XMP3 VSS OUT np VDD sg13_hv_pmos"),
    ("XMN3 nn OUT VSS VSS sg13_hv_nmos", "XMN3 VDD OUT nn VSS sg13_hv_nmos"),
]
for old, new in subs:
    if old not in text:
        raise SystemExit("run_hysteresis_diag: schmitt_hv line not found: " + old)
    text = text.replace(old, new)
open(dst, "w").write(text)
PY

# Scratch weakened-XMPD control variant (see header, sweep A's third DUT).
# XRPU and XCW -- and therefore R*C -- are left exactly as committed.
python3 - "$WORK/dut.spice" "$WORK/dut_weakpd.spice" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()
old = "XMPD VWIN WIDE VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1"
new = "XMPD VWIN WIDE VSS VSS sg13_hv_nmos w=0.5u l=8u ng=1 m=1"
if old not in text:
    raise SystemExit("run_hysteresis_diag: XMPD line not found: " + old)
open(dst, "w").write(text.replace(old, new))
PY

MOS=mos_tt
RES=res_typ
TEMP=27
VSUP=3.3
VMID=1.65
FREF=3.5e6
TRST=1n

# ---------------------------------------------------------------------------
# B. schmitt_hv input-referred hysteresis, as drawn vs. the rewired control.
# ---------------------------------------------------------------------------
echo "dut,mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd" \
  > "$CORNERS/hysteresis_diag_schmitt.csv"
for dut in dut dut_schfix; do
  for mos in mos_tt mos_ff mos_ss; do
    for temp in -40 27 125; do
      vm="$(python3 -c "print('%.6f' % ($VSUP/2))")"
      sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$VSUP/g" \
          -e "s/@VMID@/$vm/g" -e "s|@DUT@|$WORK/${dut}.spice|g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_schmitt_hyst.sp.tmpl" > "$WORK/s.sp"
      slog="$( ( cd "$WORK" && ngspice -b s.sp ) 2>/dev/null || true )"
      vup="$(printf '%s\n' "$slog" | sed -n 's/^vth_up *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
      vdn="$(printf '%s\n' "$slog" | sed -n 's/^vth_dn *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
      row="$(python3 -c "
u='${vup:-}'; d='${vdn:-}'
if u and d:
    h=float(u)-float(d)
    print('%s,%s,%.6e,%.4f' % (u, d, h, 100*h/$VSUP))
else:
    print('NA,NA,NA,NA')")"
      label="$([ "$dut" = dut ] && echo as_drawn || echo schmitt_feedback_rewired)"
      echo "${label},${mos},${temp},${VSUP},${row}" >> "$CORNERS/hysteresis_diag_schmitt.csv"
      echo "[S/${label}] ${mos}/${temp}C: ${row}" >&2
    done
  done
done

# ---------------------------------------------------------------------------
# A. Settled VWIN vs. phase error, finely swept across the transition, for
#    both DUTs (so the LOCK columns also show whether the rewired Schmitt
#    produces any resolvable PHASE-ERROR hysteresis once its VOLTAGE
#    hysteresis is restored).
# ---------------------------------------------------------------------------
read -r TWIN _ <<< "$( sed -e "s/@CORNER_MOS@/$MOS/g" -e "s/@CORNER_RES@/$RES/g" \
      -e "s/@TEMP@/$TEMP/g" -e "s/@VSUP@/$VSUP/g" -e "s/@VMID@/$VMID/g" \
      -e "s/@TSTEP@/20p/g" -e "s|@DUT@|$WORK/dut.spice|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
    ( cd "$WORK" && ngspice -b w.sp ) 2>/dev/null \
      | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
echo "[diag] twin_r at ${MOS}/${RES}/${TEMP}C = ${TWIN}" >&2

TREF="$(python3 -c "print(1.0/$FREF)")"
RC="$(python3 -c "print(2.266979e6 * $C_XCW)")"   # res_typ/27C, from rc_extract
NCYC="$(python3 -c "
import math
print(int(math.ceil(min(4*$RC, 16e-6)/$TREF)))")"
TSTOP="$(python3 -c "print($NCYC*$TREF)")"
TSETTLE="$(python3 -c "print($TSTOP - 2*$TREF)")"
TSTEP="$(python3 -c "print($TREF/25.0)")"

echo "dut,tau_xwin,tau_s,vwin_discharged_start_avg_v,vwin_charged_start_avg_v,vwin_discharged_start_min_v,vwin_discharged_start_max_v,lock_discharged_start_avg_v,lock_charged_start_avg_v,lock_discharged_start_min_v,lock_discharged_start_max_v" \
  > "$CORNERS/hysteresis_diag.csv"
for dut in dut dut_schfix dut_weakpd; do
  case "$dut" in
    dut)         label=as_drawn ;;
    dut_schfix)  label=schmitt_feedback_rewired ;;
    dut_weakpd)  label=xmpd_weakened ;;
  esac
  for frac in 0.60 0.80 0.95 1.00 1.05 1.10 1.20 1.40 1.80 2.50; do
    tau="$(python3 -c "print('%.6e' % ($frac*$TWIN))")"
    sed -e "s/@CORNER_MOS@/$MOS/g" -e "s/@CORNER_RES@/$RES/g" -e "s/@TEMP@/$TEMP/g" \
        -e "s/@VSUP@/$VSUP/g" -e "s/@TREF@/$TREF/g" -e "s/@TRST@/$TRST/g" \
        -e "s/@TAU@/$tau/g" -e "s/@TSTEP@/$TSTEP/g" -e "s/@TSTOP@/$TSTOP/g" \
        -e "s/@TSETTLE@/$TSETTLE/g" -e "s|@DUT@|$WORK/${dut}.spice|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_hyst_diag.sp.tmpl" > "$WORK/h.sp"
    hlog="$( ( cd "$WORK" && ngspice -b h.sp ) 2>/dev/null || true )"
    get() { printf '%s\n' "$hlog" | sed -n "s/^$1 *= *\([0-9.eE+-]*\).*/\1/p" | head -1; }
    echo "${label},${frac},${tau},$(get va_avg),$(get vb_avg),$(get va_min),$(get va_max),$(get la_avg),$(get lb_avg),$(get la_min),$(get la_max)" \
      >> "$CORNERS/hysteresis_diag.csv"
    echo "[diag/${label}] tau=${frac}x twin: VWIN(A)=$(get va_avg) VWIN(B)=$(get vb_avg) LOCK(A)=$(get la_avg) LOCK(B)=$(get lb_avg)" >&2
  done
done

echo "done:" >&2
for f in hysteresis_diag hysteresis_diag_schmitt; do
  echo "  $(wc -l < "$CORNERS/$f.csv") lines (incl. header) -> $CORNERS/$f.csv" >&2
done
