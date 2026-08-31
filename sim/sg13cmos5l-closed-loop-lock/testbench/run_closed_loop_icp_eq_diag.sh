#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_icp_eq_diag.sh
# (issue #70 -- diagnostic for the ~9.18% static phase-error residual
# ../records/RECORD-003 measured in Part B after the #56 pfd fix)
#
# DIAGNOSTIC-ONLY closed-loop control run: re-runs Part B's own proposal
# deck (`tb_pll_proposal.sp.tmpl`, R1 x20 + behavioural divide-by-64,
# identical operating point to ../records/RECORD-003) with ONE change --
# the `cp` block is replaced by an IDEAL, exactly-symmetric behavioural
# charge pump (`cp` pin-compatible subckt built inline below, NOT read
# from ../netlist-snapshots/cp.spice) instead of the real transistor-level
# design. Everything else (pfd -- already the #56-corrected snapshot,
# resized loop_filter, vco, behavioural divider, operating point, PVT
# point, ideal-cap substitutions) is IDENTICAL to Part B / RECORD-003.
#
# This is the "ideal-source substitution, diagnostic-only" issue #70's own
# Scope item 1 asks for -- it does NOT modify design/sg13cmos5l/cp.sch or
# any committed netlist. The ideal `cp` sources exactly equal-magnitude
# UP/DN currents (10.208 uA -- the mean of ../../sg13cmos5l-cp-icp-trim's
# own measured |up|/|dn| magnitudes at the 10 uA trim code, mos_tt/27C:
# (10.04607 + 10.36930) / 2 = 10.20769 uA, rounded here to 10.208 uA),
# gated by ideal digital comparators on the UP/DN control nodes (threshold
# 1.65 V = VDD/2, the same threshold ../testbench/run_closed_loop_pfdfix_diag.sh's
# own extraction and this script's own extraction below both already use
# for REF/FB edge detection). Using the MEAN magnitude (rather than, say,
# the 10 uA trim-code nominal) keeps the average |Icp| the loop sees close
# to the real cp's own average, isolating the mismatch variable rather than
# also changing the loop's overall charge-pump gain.
#
#   export PDK_ROOT=/path/to/pdk/root
#   export PDK=ihp-sg13cmos5l
#   ./run_closed_loop_icp_eq_diag.sh
#
# TSTOP/TAVG0 default to the SAME 2.5us/2.0-2.5us window RECORD-003's own
# Part B used, so the final-20-cycle comparison below is apples-to-apples
# against RECORD-003's own baseline trace (../corners/lock_trace_proposal.csv).
# Override with TSTOP_OVERRIDE/TAVG0_OVERRIDE for a quicker sanity pass.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

OUT="$RECORD_DIR/corners/lock_trace_proposal_icpeq.csv"
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

SNAP="$HERE/../netlist-snapshots"

# ---------------------------------------------------------------------------
# Derive the same block netlists ../testbench/run.sh derives for Part B,
# with `cp` replaced by the ideal, exactly-symmetric diagnostic substitute.
# `pfd` is used verbatim from the frozen snapshot -- already the #56-fixed
# netlist on this branch (../records/RECORD-003's own provenance header).
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

# --- cp: IDEAL, exactly-symmetric diagnostic substitute (issue #70).
# Same 9-pin interface as the real `cp` (UP DN IBP ICP IBN ICN VOUT VDD VSS)
# so it drops into the bundle unmodified elsewhere. IBP/ICP/IBN/ICN are
# accepted for pin-count compatibility but carry no current in this ideal
# model -- this diagnostic makes no claim about the real cp's bias network,
# only about UP/DN current-magnitude symmetry.
#
# Direction check (verified against SPICE current-source node-order
# convention with a standalone sanity deck before this script was written):
#   Bup VSS VOUT I=... sources current INTO VOUT when UP is asserted
#     (matches the real cp: UP high -> cp_leg_p's PMOS switch turns on,
#     charging VOUT up).
#   Bdn VOUT VSS I=... sinks current FROM VOUT when DN is asserted
#     (matches the real cp: DN high -> cp_leg_n's NMOS switch turns on,
#     discharging VOUT).
# Both branches use the IDENTICAL magnitude IMAG -- by construction, not
# by tuning, so this is a true forced-equal-current substitution.
cp_ideal = """.subckt cp UP DN IBP ICP IBN ICN VOUT VDD VSS
* Ideal, exactly-symmetric charge-pump substitution -- DIAGNOSTIC ONLY
* (issue #70). NOT the committed cp design. IMAG = 10.208 uA, the mean of
* ../../sg13cmos5l-cp-icp-trim's own measured |up|/|dn| magnitudes at the
* 10 uA trim code (mos_tt/27C): (10.04607 + 10.36930) / 2 uA.
Bup VSS VOUT I='(V(UP,VSS) > 1.65) ? 10.208e-6 : 0'
Bdn VOUT VSS I='(V(DN,VSS) > 1.65) ? 10.208e-6 : 0'
.ends
"""

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

bundle = (read("pfd.spice") + "\n" + cp_ideal + "\n" + lf_prop + "\n"
          + vco + "\n" + ld)
write(f"{work}/pll_blocks_prop_icpeq.spice", bundle)
PY

# ---------------------------------------------------------------------------
# tb_pll_proposal.sp.tmpl, unmodified apart from the `.include` target.
# ---------------------------------------------------------------------------
sed 's/\.include pll_blocks_prop\.spice/.include pll_blocks_prop_icpeq.spice/' \
  "$HERE/tb_pll_proposal.sp.tmpl" > "$WORK/tb_proposal_icpeq.sp.tmpl"

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
cp "$WORK/tb_proposal_icpeq.sp.tmpl" "$out"
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

echo "=== proposal + ideal-symmetric-cp ($TSTOP simulated) ===" >&2
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
