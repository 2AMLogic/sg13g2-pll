#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run_cp_pulse_charge.sh
# (issue #150, Part of #16) -- RECORD-006 open-loop charge-per-pulse bench.
#
# ONE short nominal-corner transient (cp + ideal drivers only; no pfd, vco,
# loop) per invocation.  Single unit, no loop.  Outputs (new files):
#   ../corners/cppulse_events_<variant><tag>.csv   one row per applied pulse
#   ../corners/cppulse_summary_<variant><tag>.json linear fits Q = I*w + Q0, quiet levels
#   ../corners/cpdiag_variant_<variant>.diff        generated cp vs frozen snapshot
#
#   export PDK_ROOT=... PDK=ihp-sg13cmos5l
#   VARIANT=control_probe|ideal_sw|ideal_dump|ideal_dump_ofs|ideal_both [RUN_TAG=...] \
#     ./run_cp_pulse_charge.sh
#
# Conditions: mos_tt, res_typ, 27 C, VDD 3.3 V, IREF 10 uA (same four current
# sources as the closed-loop deck), VOUT held at 2.387 V (the RECORD-005
# final vc_avg, 2.3869 V), drive edges 250 ps, pulses 0 -> 3.3 V.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

: "${VARIANT:?set VARIANT}"
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

python3 -I - "$WORK" <<'PY'
import sys
work = sys.argv[1]
EDGE = 250e-12
V = 3.3
SPACING = 60e-9
T0 = 100e-9
WIDTHS = [1.6e-9, 3.2e-9, 6.4e-9]
MODES = ["up", "dn", "both"]
events = []      # (mode, width, start)
t = T0
for rep in range(2):
    for mode in MODES:
        for w in WIDTHS:
            events.append((mode, w, t))
            t += SPACING
tstop = t + 20e-9

def pwl(active):
    pts = [(0.0, 0.0)]
    for mode, w, s in events:
        if mode in active:
            pts += [(s, 0.0), (s + EDGE, V), (s + w, V), (s + w + EDGE, 0.0)]
    return " ".join(f"{a:.6e} {b:.4f}" for a, b in pts)

with open(f"{work}/events.csv", "w") as f:
    f.write("mode,width_cmd_s,start_s\n")
    for mode, w, s in events:
        f.write(f"{mode},{w:.6e},{s:.6e}\n")
open(f"{work}/pwl_up.txt", "w").write(pwl({"up", "both"}))
open(f"{work}/pwl_dn.txt", "w").write(pwl({"dn", "both"}))
open(f"{work}/tstop.txt", "w").write(f"{tstop:.6e}")
PY

out="$WORK/tb_run.sp"
cp "$HERE/tb_cp_pulse_charge.sp.tmpl" "$out"
UPPWL="$(cat "$WORK/pwl_up.txt")"; DNPWL="$(cat "$WORK/pwl_dn.txt")"; TSTOP="$(cat "$WORK/tstop.txt")"
sed -i \
  -e "s#\\\$PDK_ROOT/\\\$PDK#$PDK_ROOT/$PDK#g" \
  -e "s/@CORNER_MOS@/mos_tt/g" -e "s/@CORNER_RES@/res_typ/g" \
  -e "s/@TEMP@/27/g" -e "s/@VDD@/3.3/g" -e "s/@IREF@/10u/g" -e "s/@VOUT@/2.387/g" \
  -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/100p/g" -e "s/@TMAX@/100p/g" \
  -e "s#@UPPWL@#$UPPWL#" -e "s#@DNPWL@#$DNPWL#" \
  "$out"

echo "=== cp pulse-charge bench variant=$VARIANT ===" >&2
set +e
( cd "$WORK" && ngspice -b tb_run.sp > "$WORK/log_run.txt" 2>&1 )
RC=$?
set -e
echo "ngspice exit status: $RC" >&2
grep -E "^i_|^vdump|rror|singular|no convergence" "$WORK/log_run.txt" >&2 || true
[ "$RC" -eq 0 ] || { tail -30 "$WORK/log_run.txt" >&2; exit "$RC"; }

python3 -I "$HERE/cpdiag_pulse_post.py" "$VARIANT" "$TAG" "$WORK" "$OUTDIR" "$SNAP" "$RC"
