#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_cascbias.sh
# (issue #72, Part of #16 -- the REAL-cp re-run ../records/RECORD-004's own
# "What this does not bound" section says it does NOT deliver)
#
# Re-runs Part B's own proposal deck against the MITIGATED, transistor-level
# `cp` (../netlist-snapshots/cp_cascbias.spice -- the committed design after
# issue #72 / DR-006 added cp.sch's own high-swing cascode bias replica), NOT
# against an ideal behavioural substitute. Everything else -- `pfd` (the
# #56-corrected frozen snapshot), the R1 x20 loop filter, `vco`, the
# behavioural divide-by-64, `lock_detector`, the operating point, the PVT
# point and every ideal-cap substitution -- is IDENTICAL to Part B /
# ../records/RECORD-003 and to ../records/RECORD-004's own diagnostic, so the
# three traces are directly comparable at the same timestamps.
#
# The ONE interface difference from ../testbench/run.sh's Part B: `cp`'s
# IBP/ICP/IBN/ICN are current-input pins now, so this deck uses
# `tb_pll_proposal_cascbias.sp.tmpl` (four ideal @IREF@ current sources) in
# place of `tb_pll_proposal.sp.tmpl`'s testbench-local XMREF* voltage-bias
# replica. Neither the original Part B deck nor either existing diagnostic
# script is modified by this one -- they keep running against the as-drawn
# ../netlist-snapshots/cp.spice, so RECORD-001..004's reproduce commands are
# unaffected.
#
#   export PDK_ROOT=/path/to/pdk/root
#   export PDK=ihp-sg13cmos5l
#   ./run_closed_loop_cascbias.sh
#
# TSTOP/TAVG0 default to the SAME 2.5us/2.0-2.5us window RECORD-003's Part B
# and RECORD-004's diagnostic both used, so the final-20-cycle comparison is
# apples-to-apples against ../corners/lock_trace_proposal.csv and
# ../corners/lock_trace_proposal_icpeq.csv. Override with
# TSTOP_OVERRIDE/TAVG0_OVERRIDE for a quicker sanity pass.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

OUT="$RECORD_DIR/corners/lock_trace_proposal_cascbias.csv"
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

SNAP="$HERE/../netlist-snapshots"

# ---------------------------------------------------------------------------
# Derive the same block netlists ../testbench/run.sh derives for Part B, with
# `cp` taken verbatim from the MITIGATED snapshot. `pfd` is used verbatim from
# the frozen snapshot -- already the #56-fixed netlist on this branch
# (../records/RECORD-003's own provenance header).
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

# --- cp: the REAL, unmodified MITIGATED netlist (issue #72). Read verbatim
# from the frozen snapshot -- no substitution, no strip, no edit. This is the
# whole point of this script versus run_closed_loop_icp_eq_diag.sh.
cp_real = read("cp_cascbias.spice")
assert "XMBP" in cp_real and "XMCN" in cp_real, \
    "snapshot does not contain cp.sch's own cascode bias replica"

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

bundle = (read("pfd.spice") + "\n" + cp_real + "\n" + lf_prop + "\n"
          + vco + "\n" + ld)
write(f"{work}/pll_blocks_prop_cascbias.spice", bundle)
PY

# ---------------------------------------------------------------------------
# tb_pll_proposal_cascbias.sp.tmpl, used verbatim (its `.include` target
# already names the bundle built above).
# ---------------------------------------------------------------------------
cp "$HERE/tb_pll_proposal_cascbias.sp.tmpl" "$WORK/tb_proposal_cascbias.sp.tmpl"

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
TSTOP="${TSTOP_OVERRIDE:-2500n}"     # same duration as RECORD-003's own Part B
TAVG0="${TAVG0_OVERRIDE:-2000n}"     # same averaging window as RECORD-003's own Part B
TPRINT=100p
TMAX=100p

out="$WORK/tb_run.sp"
cp "$WORK/tb_proposal_cascbias.sp.tmpl" "$out"
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

echo "=== proposal + mitigated (cascode-bias) real cp ($TSTOP simulated) ===" >&2
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
