#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_pfdfix_diag.sh
# (issue #50, Part of #16 -- root-cause investigation for the proposal
# deck's non-convergence)
#
# CONFIRMATORY closed-loop control run: re-runs Part B's own proposal deck
# (`tb_pll_proposal.sp.tmpl`, R1 x20 + behavioural divide-by-64, identical
# operating point to ../records/RECORD-001) with ONE change -- the `pfd`
# block is `pfd_fixed_diag.spice` (the diagnostic reset-chain patch
# `run_pfd_diag.sh` derives and documents, NOT the committed design) instead
# of the frozen ../netlist-snapshots/pfd.spice. Everything else (cp,
# resized loop_filter, vco, behavioural divider, operating point, PVT
# point, ideal-cap substitutions) is IDENTICAL to Part B.
#
# Mirrors ../records/RECORD-001's own precedent exactly: a short (400 ns),
# NOT-part-of-the-committed-testbench control run, compared point-by-point
# against Part B's own recorded ../corners/lock_trace_proposal.csv at the
# same timestamps -- the same comparison method that record's own
# UP/DN-pin-swap control run used.
#
#   export PDK_ROOT=/path/to/pdk/root
#   export PDK=ihp-sg13cmos5l
#   ./run_closed_loop_pfdfix_diag.sh
#
# Measured on the arm64-macOS host this diagnostic was produced on: ~400 s
# wall (same ~1 ns/s rate ../records/RECORD-001 "Why these durations"
# reports for this six-block netlist).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
OUT="$RECORD_DIR/corners/lock_trace_proposal_pfdfix.csv"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

SNAP="$HERE/../netlist-snapshots"

# ---------------------------------------------------------------------------
# Derive the same block netlists ../testbench/run.sh derives for Part B,
# with `pfd` replaced by the diagnostic-patched variant. See
# ./run_pfd_diag.sh's own header for exactly what the patch changes and why.
# ---------------------------------------------------------------------------
python3 - "$SNAP" "$WORK" <<'PY'
import re, sys
snap, work = sys.argv[1], sys.argv[2]

def read(name):
    with open(f"{snap}/{name}") as f:
        return f.read()

def write(path, text):
    with open(path, "w") as f:
        f.write(text)

# --- pfd: same diagnostic patch as run_pfd_diag.sh (odd inversion count
# after reset_raw, so `reset` = AND(UP,DN) instead of NAND(UP,DN)) ---
pfd = read("pfd.spice")
old = "XI1 reset_raw reset_d1 VDD VSS inv_hv\nXI2 reset_d1 reset VDD VSS inv2x_hv"
new = ("XI1 reset_raw reset_d1 VDD VSS inv_hv\n"
       "XI2 reset_d1 reset_d2 VDD VSS inv2x_hv\n"
       "XI3 reset_d2 reset VDD VSS inv_hv")
assert pfd.count(old) == 1, "reset-chain pattern not found exactly once"
pfd_fixed = pfd.replace(old, new)

# --- vco: strip XCDECAP, same precedent as ../testbench/run.sh ---
vco = read("vco.spice")
vco = re.sub(r'(?m)^XCDECAP', '*XCDECAP', vco)
assert "*XCDECAP" in vco, "XCDECAP strip did not match"

# --- loop_filter: XC1/XC2 -> ideal caps at the SAME measured nominal
# values ../testbench/run.sh uses, then R1 resized x20 (Part B proposal) ---
C1_F = 1.691196e-12
C2_F = 1.001529e-13

def sub_cap(text, xname, node1, node2, value):
    pat = re.compile(rf'(?m)^X{xname}\s+{node1}\s+{node2}\s+cap_cmomi\b.*$')
    repl = f"C{xname} {node1} {node2} {value:.6e}"
    new_text, n = pat.subn(repl, text)
    assert n == 1, f"expected exactly 1 match for X{xname} {node1} {node2}, got {n}"
    return new_text

lf = read("loop_filter.spice")
lf = sub_cap(lf, "C1", "NZ", "VSS", C1_F)
lf = sub_cap(lf, "C2", "VCTRL", "VSS", C2_F)
lf_prop = re.sub(r'(?m)^(XR1\s+VCTRL\s+NZ\s+sub!\s+rppd\s+w=4u\s+l=)120u',
                  r'\g<1>2400u', lf)
assert lf_prop != lf, "R1 resize substitution did not match"

# --- lock_detector: XCW/XC1 -> ideal caps, same density-extrapolation as
# ../testbench/run.sh ---
DENSITY = C2_F / (10e-6 * 10e-6)
CW_F = DENSITY * (8e-6 * 8e-6)
C1LD_F = DENSITY * (4e-6 * 4e-6) * 2
ld = read("lock_detector.spice")
ld = sub_cap(ld, "CW", "VWIN", "VSS", CW_F)
ld = sub_cap(ld, "C1", "OUT", "VSS", C1LD_F)

bundle = (pfd_fixed + "\n" + read("cp.spice") + "\n" + lf_prop + "\n"
          + vco + "\n" + ld)
write(f"{work}/pll_blocks_prop_pfdfix.spice", bundle)
PY

# ---------------------------------------------------------------------------
# tb_pll_proposal.sp.tmpl, unmodified apart from the `.include` target.
# ---------------------------------------------------------------------------
sed 's/\.include pll_blocks_prop\.spice/.include pll_blocks_prop_pfdfix.spice/' \
  "$HERE/tb_pll_proposal.sp.tmpl" > "$WORK/tb_proposal_pfdfix.sp.tmpl"

MOS_CORNER=mos_tt
RES_CORNER=res_typ
TEMP=27
VDD=3.3
IREF=10u
FREF=20e6
TREF=$(python3 -c "print(f'{1/${FREF}:.6e}')")
TREFH=$(python3 -c "print(f'{1/${FREF}/2 - 100e-12:.6e}')")
B0V=$VDD
B1V=$VDD
VC0=2.46
TSTOP="${TSTOP_OVERRIDE:-400n}"   # same duration as RECORD-001's own control run
TAVG0="${TAVG0_OVERRIDE:-300n}"
TPRINT=100p
TMAX=100p

out="$WORK/tb_run.sp"
cp "$WORK/tb_proposal_pfdfix.sp.tmpl" "$out"
sed -i.bak \
  -e "s#\\\$PDK_ROOT/\\\$PDK#$PDK_ROOT/$PDK#g" \
  -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@CORNER_RES@/$RES_CORNER/g" \
  -e "s/@TEMP@/$TEMP/g" -e "s/@VDD@/$VDD/g" \
  -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
  -e "s/@IREF@/$IREF/g" -e "s/@B0V@/$B0V/g" -e "s/@B1V@/$B1V/g" \
  -e "s/@VC0@/$VC0/g" \
  -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/$TPRINT/g" -e "s/@TMAX@/$TMAX/g" \
  -e "s/@TAVG0@/$TAVG0/g" \
  "$out"
rm -f "$out.bak"

echo "=== proposal + fixed-pfd ($TSTOP simulated) ===" >&2
( cd "$WORK" && ngspice -b tb_run.sp > "$WORK/log_run.txt" 2>&1 )
grep -E "^i_|^vc_" "$WORK/log_run.txt" || true
mv "$WORK/wave.dat" "$WORK/wave_run.dat.last"

python3 - "$WORK" "$OUT" "$FREF" <<'PY'
import sys
work, out, fref_s = sys.argv[1], sys.argv[2], sys.argv[3]
fref = float(fref_s)

def read_wave(path, ncols=10):
    t, ref, fb, vctrl = [], [], [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) < ncols:
                continue
            try:
                vals = [float(x) for x in p[:ncols]]
            except ValueError:
                continue
            t.append(vals[0]); ref.append(vals[1]); fb.append(vals[3]); vctrl.append(vals[5])
    return t, ref, fb, vctrl

def rising_edges(t, v, vth):
    out = []
    for i in range(1, len(v)):
        if v[i - 1] < vth <= v[i]:
            frac = (vth - v[i - 1]) / (v[i] - v[i - 1]) if v[i] != v[i - 1] else 0.0
            out.append(t[i - 1] + frac * (t[i] - t[i - 1]))
    return out

def lock_trace(t, ref, fb, vth, fref):
    ref_edges = rising_edges(t, ref, vth)
    fb_edges = rising_edges(t, fb, vth)
    tref = 1.0 / fref
    trace = []
    if len(ref_edges) < 2 or not fb_edges:
        return trace
    fb_idx = 0
    for i in range(1, len(ref_edges)):
        r0, r1 = ref_edges[i - 1], ref_edges[i]
        period_ref = r1 - r0
        while fb_idx + 1 < len(fb_edges) and fb_edges[fb_idx + 1] <= r1:
            fb_idx += 1
        nearest = min(fb_edges, key=lambda e: abs(e - r1)) if fb_edges else None
        if nearest is None:
            continue
        phase_err = (nearest - r1) / tref
        prior = max([e for e in fb_edges if e < nearest], default=None)
        if prior is None:
            continue
        period_fb = nearest - prior
        if period_fb > 0 and period_ref > 0:
            df = (1.0 / period_fb - 1.0 / period_ref) / fref
        else:
            df = float("inf")
        trace.append((r1, df, phase_err))
    return trace

t, ref, fb, vctrl = read_wave(f"{work}/wave_run.dat.last")
trace = lock_trace(t, ref, fb, 1.65, fref)
with open(out, "w") as f:
    f.write("t_s,delta_f_frac,phase_err_frac\n")
    for row in trace:
        f.write(",".join(str(x) for x in row) + "\n")
print(f"vctrl: {vctrl[0] if vctrl else None} -> {vctrl[-1] if vctrl else None}", file=sys.stderr)
for row in trace:
    print(row, file=sys.stderr)
PY

echo "Wrote $OUT" >&2
