#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run_cp_dynamic_diag.sh
# (issue #150, Part of #16) -- RECORD-006 charge-pump dynamic-term diagnostic.
#
# ONE nominal-corner closed-loop transient per invocation, for ONE variant of
# RECORD-005's deck (mitigated cp_cascbias + frozen pfd + R1 x20 + behavioural
# divide-by-64).  Nothing under design/, no frozen snapshot, no historical CSV
# is written; every output is a NEW file named for the variant (and an
# optional RUN_TAG for repeats):
#
#   ../corners/lock_trace_cpdiag_<variant><tag>.csv   per-cycle df / phase error
#   ../corners/cpdiag_cycles_<variant><tag>.csv       per-cycle pulse/charge (probe variants)
#   ../corners/cpdiag_summary_<variant><tag>.json     metrics, meas, versions, input hashes
#   ../corners/cpdiag_variant_<variant>.diff          diff of generated cp/pfd vs frozen snapshot
#
#   export PDK_ROOT=/path/to/pdk/root PDK=ihp-sg13cmos5l
#   VARIANT=control_hist|control_probe|ideal_sw|ideal_dump|ideal_dump_ofs|reset_narrow|reset_wide \
#     [RUN_TAG=_rep] [TSTOP_OVERRIDE=500n OUT_PREFIX=/tmp/x] ./run_cp_dynamic_diag.sh
#
# Fixed (identical to RECORD-005): mos_tt, res_typ, 27 C, 3.3 V, 20 MHz REF,
# N=64, IREF=10 uA, VC0=2.46 V, TSTOP=2.5 us, TPRINT=TMAX=100 ps, .meas window
# 2.0-2.5 us.  `set num_threads=1` is added to .spiceinit (shared-host rule;
# see ../../sg13cmos5l-lock-detector-window/testbench/run.sh TOOLING NOTE).
#
# Multi-corner follow-ups must go through `klt sim`; this script is
# single-unit by design and deliberately has no loop.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

: "${VARIANT:?set VARIANT (see header)}"
TAG="${RUN_TAG:-}"
OUTDIR="${OUT_PREFIX:-$RECORD_DIR/corners}"
mkdir -p "$OUTDIR"
SNAP="$HERE/../netlist-snapshots"

cat > "$WORK/.spiceinit" <<EOS
set num_threads=1
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOS

python3 -I "$HERE/cpdiag_build.py" "$VARIANT" "$SNAP" "$WORK"
cp "$WORK/variant.diff" "$OUTDIR/cpdiag_variant_${VARIANT}.diff"

if [ "$VARIANT" = control_hist ]; then
  cp "$WORK/pll_blocks_cpdiag.spice" "$WORK/pll_blocks_prop_cascbias.spice"
  TMPL="$HERE/tb_pll_proposal_cascbias.sp.tmpl"
else
  TMPL="$HERE/tb_pll_cpdiag.sp.tmpl"
fi

MOS_CORNER=mos_tt; RES_CORNER=res_typ; TEMP=27; VDD=3.3; IREF=10u; FREF=20e6
TREF=$(python3 -c "print(f'{1/${FREF}:.6e}')")
TREFH=$(python3 -c "print(f'{1/${FREF}/2 - 100e-12:.6e}')")
B0V=$VDD; B1V=$VDD; VC0=2.46
TSTOP="${TSTOP_OVERRIDE:-2500n}"
TAVG0="${TAVG0_OVERRIDE:-2000n}"
TPRINT=100p; TMAX=100p

out="$WORK/tb_run.sp"
cp "$TMPL" "$out"
sed -i \
  -e "s#\\\$PDK_ROOT/\\\$PDK#$PDK_ROOT/$PDK#g" \
  -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@CORNER_RES@/$RES_CORNER/g" \
  -e "s/@TEMP@/$TEMP/g" -e "s/@VDD@/$VDD/g" \
  -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
  -e "s/@IREF@/$IREF/g" -e "s/@B0V@/$B0V/g" -e "s/@B1V@/$B1V/g" \
  -e "s/@VC0@/$VC0/g" \
  -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/$TPRINT/g" -e "s/@TMAX@/$TMAX/g" \
  -e "s/@TAVG0@/$TAVG0/g" \
  "$out"

echo "=== cpdiag variant=$VARIANT tag='$TAG' TSTOP=$TSTOP ===" >&2
set +e
( cd "$WORK" && ngspice -b tb_run.sp > "$WORK/log_run.txt" 2>&1 )
RC=$?
set -e
echo "ngspice exit status: $RC" >&2
grep -E "^i_|^vc_|rror|singular|no convergence" "$WORK/log_run.txt" >&2 || true
[ "$RC" -eq 0 ] || { tail -30 "$WORK/log_run.txt" >&2; exit "$RC"; }

python3 -I "$HERE/cpdiag_post.py" "$VARIANT" "$TAG" "$WORK" "$OUTDIR" "$FREF" "$TSTOP" \
  "$TMPL" "$SNAP" "$RC"
