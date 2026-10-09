#!/usr/bin/env bash
# issue #159 supporting diagnostic: ONE nominal ngspice run of divider_chain alone
# at one ideal clock frequency.  Usage: PDK_ROOT=.. PDK=.. ./run_div_speed.sh <fclk_Hz>
# Counts clk rising edges between successive fb rising edges (threshold 1.65 V).
FCLK="${1:?usage: run_div_speed.sh <fclk_hz>}"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"
SNAP="$HERE/../netlist-snapshots"
cat > "$WORK/.spiceinit" <<EOS
set num_threads=2
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOS
read -r CP CH < <(python3 -c "p=1/${FCLK};print(f'{p:.6e} {p/2-80e-12:.6e}')")
TSTOP="${TSTOP_OVERRIDE:-400n}"
grep -v '^\*' "$SNAP/divider_chain.spice" > "$WORK/div_only.spice"
sed -e "s#@PDK_ROOT@#$PDK_ROOT#g" -e "s#@PDK@#$PDK#g" -e "s/@FCLK@/$FCLK/g" \
    -e "s/@CP@/$CP/g" -e "s/@CH@/$CH/g" -e "s/@TSTOP@/$TSTOP/g" -e "s/@TAVG0@/100n/g" \
    "$HERE/tb_div_speed.sp.tmpl" > "$WORK/tb.sp"
START=$(date +%s)
( cd "$WORK" && timeout 1200 ngspice -b tb.sp > log.txt 2>&1 ) || echo "ngspice exit $?" >&2
mkdir -p "$RECORD_DIR/corners"
cp "$WORK/log.txt" "$RECORD_DIR/corners/log_divspeed_$(python3 -c "print(int(${FCLK}/1e6))")MHz.txt"
echo "wall_seconds=$(( $(date +%s) - START ))" >&2
python3 -I - "$WORK/wave.dat" "$FCLK" <<'PY'
import sys
rows=[l.split() for l in open(sys.argv[1]) if l.strip()]
t=[float(r[0]) for r in rows]; clk=[float(r[1]) for r in rows]; fb=[float(r[3]) for r in rows]
def edges(v):
    return [t[i-1]+(1.65-v[i-1])/(v[i]-v[i-1])*(t[i]-t[i-1]) for i in range(1,len(v)) if v[i-1]<1.65<=v[i]]
c,f=edges(clk),edges(fb)
r=[sum(1 for x in c if f[i]<=x<f[i+1]) for i in range(len(f)-1)]
print(f"fclk={sys.argv[2]} clk_edges={len(c)} fb_edges={len(f)} clk_edges_per_fb_period={r}")
PY
grep -E "^i_div" "$WORK/log.txt" || true
