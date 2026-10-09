#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-real-divider/testbench/run.sh
# (issue #159, Part of #16)
#
# NOMINAL-ONLY (mos_tt / res_typ / 27 C / 3.3 V), pre-layout. Runs ONE arm per
# invocation (a single local ngspice -b; never a grid):
#
#   PDK_ROOT=<root> PDK=ihp-sg13cmos5l ./run.sh control
#   PDK_ROOT=<root> PDK=ihp-sg13cmos5l ./run.sh real
#
# Calls extract.py, which writes ../corners/trace_<arm>.csv (per-ref-cycle
# lock trace), ../corners/summary_<arm>.json and ../corners/vctrl_<arm>.csv
# (decimated vctrl/fb waveform, ~1 sample/ns); this script also copies the
# ngspice log to ../corners/log_<arm>.txt. Overrides: TSTOP_OVERRIDE, TAVG0_OVERRIDE, TAG_SUFFIX.
ARM="${1:?usage: run.sh control|real}"
case "$ARM" in control|real) ;; *) echo "arm must be control|real" >&2; exit 2;; esac

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SNAP="$HERE/../netlist-snapshots"
cat > "$WORK/.spiceinit" <<EOF
set num_threads=${NGSPICE_THREADS:-2}
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

MOS_CORNER=mos_tt; RES_CORNER=res_typ; TEMP=27; VDD=3.3; IREF=10u
FREF=20e6
TREF=$(python3 -c "print(f'{1/${FREF}:.6e}')")
TREFH=$(python3 -c "print(f'{1/${FREF}/2 - 100e-12:.6e}')")
B0V=$VDD; B1V=$VDD; VC0=2.46
TSTOP="${TSTOP_OVERRIDE:-2500n}"; TAVG0="${TAVG0_OVERRIDE:-2000n}"
TPRINT=100p; TMAX=100p
SUFFIX="${TAG_SUFFIX:-}"

python3 -I - "$SNAP" "$WORK" "$HERE" "$ARM" <<'PY'
import re, sys
snap, work, here, arm = sys.argv[1:5]
rd = lambda n: open(f"{snap}/{n}").read()
vco = re.sub(r'(?m)^XCDECAP', '*XCDECAP', rd("vco.spice"))
assert "*XCDECAP" in vco
C1_F, C2_F = 1.691196e-12, 1.001529e-13   # campaign's measured nominal values
def sub_cap(text, x, n1, n2, v):
    new, n = re.subn(rf'(?m)^X{x}\s+{n1}\s+{n2}\s+cap_cmomi\b.*$', f"C{x} {n1} {n2} {v:.6e}", text)
    assert n == 1; return new
lf = sub_cap(sub_cap(rd("loop_filter.spice"), "C1", "NZ", "VSS", C1_F), "C2", "VCTRL", "VSS", C2_F)
blocks = [rd("pfd.spice"), rd("cp.spice"), lf, vco]
if arm == "real":
    blocks.append(rd("divider_chain.spice"))
open(f"{work}/pll_blocks_realdiv.spice", "w").write("\n".join(blocks))
tmpl = open(f"{here}/tb_pll_realdiv.sp.tmpl").read()
inc = open(f"{here}/arm_{arm}.inc").read()
open(f"{work}/tb_run.sp", "w").write(tmpl.replace("@ARM_BLOCK@", inc))
PY

sed -i \
  -e "s#@PDK_ROOT@#$PDK_ROOT#g" -e "s#@PDK@#$PDK#g" \
  -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@CORNER_RES@/$RES_CORNER/g" \
  -e "s/@TEMP@/$TEMP/g" -e "s/@VDD@/$VDD/g" \
  -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
  -e "s/@IREF@/$IREF/g" -e "s/@B0V@/$B0V/g" -e "s/@B1V@/$B1V/g" \
  -e "s/@VC0@/$VC0/g" \
  -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/$TPRINT/g" -e "s/@TMAX@/$TMAX/g" \
  -e "s/@TAVG0@/$TAVG0/g" "$WORK/tb_run.sp"
! grep -n '@[A-Z0-9_]*@' "$WORK/tb_run.sp" || { echo "unsubstituted token" >&2; exit 1; }

echo "=== arm=$ARM tstop=$TSTOP ===" >&2
START=$(date +%s)
( cd "$WORK" && timeout "${NGSPICE_TIMEOUT:-2400}" ngspice -b tb_run.sp > log_run.txt 2>&1 ) || echo "ngspice exit status $?" >&2
echo "wall_seconds=$(( $(date +%s) - START ))" >&2
cp "$WORK/log_run.txt" "$RECORD_DIR/corners/log_${ARM}${SUFFIX}.txt"
grep -E "^i_|^vc_" "$WORK/log_run.txt" || true
[ -s "$WORK/wave.dat" ] || { echo "no waveform produced (see log)" >&2; exit 3; }
python3 -I "$HERE/extract.py" "$ARM$SUFFIX" "$WORK/wave.dat" "$RECORD_DIR/corners" "$FREF" "$TAVG0"
