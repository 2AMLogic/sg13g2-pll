#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run.sh
# (issue #37, Part of #16 -- SG13CMOS5L closed-loop transient)
#
# Drives the two decks documented in this directory's own testbench headers:
#   Part A (tb_pll_closed.sp.tmpl)   -- AS-DRAWN loop: real pfd/cp/loop_filter
#                                       (R1=120u, as-committed)/vco/
#                                       divider_chain/lock_detector.
#   Part B (tb_pll_proposal.sp.tmpl) -- PROPOSAL loop: R1 x20 (2400u, the
#                                       ../../sg13cmos5l-loop-bandwidth-pm
#                                       widest-margin pick) + a behavioural
#                                       divide-by-64, NEITHER of which is the
#                                       committed design (see that template's
#                                       own header for why the divider swap
#                                       is forced, not chosen).
#
# Both decks share:
#  - a single PVT point (mos_tt/res_typ/27C/3.3V, "typ"), NOT the full
#    matrix -- see ../corners/matrix.md for the runtime-cost rationale
#    (explicit subset, per sim/README.md's own convention for when a
#    subset is allowed).
#  - f_ref = 20 MHz, N = 64 (P5..P0 = 000000, the divider's own structural
#    floor), both inside DR-005's amended f_ref/N ranges
#    (spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md).
#  - Icp trim code = 10 uA (the code ../../sg13cmos5l-cp-icp-trim and
#    ../../sg13cmos5l-vco-duty-cycle already report vdd_vco/cp current at).
#  - ideal-capacitor substitutions for every cap_cmomi instance (loop_filter
#    XC1/XC2, lock_detector XCW/XC1) -- see "OSDI host constraint" below --
#    and an XCDECAP strip on vco (see ../../sg13cmos5l-vco-kvco-table's own
#    precedent: VDD_VCO/GND_VCO are ideal DC sources here too, so XCDECAP's
#    value cannot affect any measurement this deck makes).
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh                # both parts, writes ../corners/*.csv + wave dumps
#   ./run.sh --quick         # short sanity transient (TSTOP overridden), no CSV
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree.
#
# ---------------------------------------------------------------------------
# OSDI host constraint (arm64 macOS): cap_cmomi.osdi/cap_cmomf.osdi ship as
# x86-64 ELF only (confirmed with file(1) on this host) -- they cannot be
# dlopen'd here at all, on ANY netlist that instantiates them. This is a HOST
# constraint, not a design change: every cap_cmomi instance below is replaced
# by an ideal capacitor at the value ../../sg13cmos5l-loop-filter-momcap
# measured (loop_filter's own C1/C2, nominal MOM point) or, for the two
# lock_detector instances that record never measured (row 16's own gap, see
# sim/README.md), at that record's measured area density applied to the
# lock_detector instances' own W*L. Every substitution is stated below, not
# silently applied.
# ---------------------------------------------------------------------------

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

OUT_A="$RECORD_DIR/corners/results_as_drawn.csv"
OUT_B="$RECORD_DIR/corners/results_proposal.csv"

QUICK=0
[[ "${1:-}" == "--quick" ]] && QUICK=1

# psp103 (+ its NQS/variability companions) for every MOS device, r3_cmc for
# rppd/rhigh. NOT cap_cmomi/cap_cmomf -- see header above.
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

# ---------------------------------------------------------------------------
# Derive the per-block netlists both decks .include, from the FROZEN
# snapshots (never edited in place).
# ---------------------------------------------------------------------------
python3 - "$RECORD_DIR" "$WORK" <<'PY'
import re, sys
rec, work = sys.argv[1], sys.argv[2]
snap = f"{rec}/netlist-snapshots"

def read(name):
    with open(f"{snap}/{name}") as f:
        return f.read()

def write(path, text):
    with open(path, "w") as f:
        f.write(text)

# pfd, cp, divider_chain: verbatim, no cap_cmomi/cap_cmomf instance in any of
# the three (confirmed by grep against the frozen snapshots).
write(f"{work}/pfd_snap.spice", read("pfd.spice"))
write(f"{work}/cp_snap.spice", read("cp.spice"))
write(f"{work}/divider_chain_snap.spice", read("divider_chain.spice"))

# vco: strip XCDECAP (comment it out) -- same precedent as
# ../../sg13cmos5l-vco-kvco-table/testbench/run.sh's own XCDECAP-strip.
vco = read("vco.spice")
vco = re.sub(r'(?m)^XCDECAP', '*XCDECAP', vco)
assert "*XCDECAP" in vco, "XCDECAP strip did not match"
write(f"{work}/vco_tb.spice", vco)

# loop_filter (as-drawn, R1 = 4u/120u): XC1/XC2 -> ideal caps at the measured
# nominal (mos_tt/res_typ/27C, mom_frac=0) values from
# ../../sg13cmos5l-loop-filter-momcap/corners/results.csv, reused verbatim
# (same numbers ../../sg13cmos5l-loop-bandwidth-pm's own real-subckt AC runs
# used for the identical substitution reason).
C1_F = 1.691196e-12   # XC1, w=40u l=40u
C2_F = 1.001529e-13   # XC2, w=10u l=10u

def sub_cap(text, xname, node1, node2, value, m=1):
    pat = re.compile(rf'(?m)^X{xname}\s+{node1}\s+{node2}\s+cap_cmomi\b.*$')
    total = value  # value already reflects the instance's total capacitance
    repl = f"C{xname} {node1} {node2} {total:.6e}"
    new, n = pat.subn(repl, text)
    assert n == 1, f"expected exactly 1 match for X{xname} {node1} {node2}, got {n}"
    return new

lf = read("loop_filter.spice")
lf = sub_cap(lf, "C1", "NZ", "VSS", C1_F)
lf = sub_cap(lf, "C2", "VCTRL", "VSS", C2_F)
write(f"{work}/loop_filter_tb.spice", lf)

# Proposal variant: R1 (XR1, rppd, w=4u l=120u) resized to l=2400u (x20),
# ../../sg13cmos5l-loop-bandwidth-pm/corners/proposal.csv's widest-margin
# pick (PM 58.6-61.8 deg at every PVT bundle with the 10 uA trim code). The
# resistor stays the real rppd compact model -- only its length changes.
lf_prop = re.sub(r'(?m)^(XR1\s+VCTRL\s+NZ\s+sub!\s+rppd\s+w=4u\s+l=)120u',
                  r'\g<1>2400u', lf)
assert lf_prop != lf, "R1 resize substitution did not match"
write(f"{work}/loop_filter_prop.spice", lf_prop)

# lock_detector: XCW/XC1 -> ideal caps. Neither instance was measured by
# ../../sg13cmos5l-loop-filter-momcap (that record's own three-instance list
# is loop_filter.XC1/XC2 + vco.XCDECAP only -- row 16's own gap, see
# sim/README.md deferred-rows table). Extrapolated here from that record's
# OWN measured area density (C2/area, the closer-sized reference instance:
# 1.001529e-13 F / (10u*10u) = 1.001529e-15 F/um^2) applied to each
# instance's own W*L*m -- an approximation, stated as one, not a second
# independent measurement.
DENSITY = C2_F / (10e-6 * 10e-6)  # F/m^2, from C2's own w=10u l=10u
CW_F = DENSITY * (8e-6 * 8e-6)          # XCW: w=8u l=8u, m=1
C1LD_F = DENSITY * (4e-6 * 4e-6) * 2    # XC1: w=4u l=4u, m=2

ld = read("lock_detector.spice")
ld = sub_cap(ld, "CW", "VWIN", "VSS", CW_F)
ld = sub_cap(ld, "C1", "OUT", "VSS", C1LD_F)
write(f"{work}/lock_detector_tb.spice", ld)

# Combined proposal bundle: real pfd/cp/vco/lock_detector (identical to
# Part A's own derived copies) + the RESIZED loop_filter. The divider is
# NOT included here -- tb_pll_proposal.sp.tmpl defines the behavioural
# divide-by-64 inline (see that template's own header, item 2).
prop = (read("pfd.spice") + "\n" + read("cp.spice") + "\n" + lf_prop + "\n"
        + vco + "\n" + ld)
write(f"{work}/pll_blocks_prop.spice", prop)

print(f"C1={C1_F:.4e}F C2={C2_F:.4e}F CW={CW_F:.4e}F C1_ld={C1LD_F:.4e}F "
      f"density={DENSITY*1e12:.4f}fF/um^2", file=sys.stderr)
PY

# ---------------------------------------------------------------------------
# PVT point (single "typ" bundle -- see ../corners/matrix.md).
# ---------------------------------------------------------------------------
MOS_CORNER=mos_tt
RES_CORNER=res_typ
TEMP=27
VDD=3.3
IREF=10u

# Operating point: f_ref=20 MHz, N=64 (P5..P0=000000) -> target f_out=1280
# MHz, band code 11 (B0=B1=VDD), VC0=2.46V (typ/band-11 secant interpolation
# of ../../sg13cmos5l-vco-kvco-table/corners/results.csv -- an initial
# condition only, not a claim about the locked value).
FREF=20e6
TREF=$(python3 -c "print(f'{1/${FREF}:.6e}')")
TREFH=$(python3 -c "print(f'{1/${FREF}/2 - 100e-12:.6e}')")
B0V=$VDD
B1V=$VDD
VC0=2.46

# Measured on this host (arm64 macOS, ngspice-47): 200 ns of this six-block
# netlist costs ~200 s wall (~1 ns/s) -- see ../corners/matrix.md. TSTOP is
# per-deck, not a shared budget: Part A (as-drawn) only needs enough window
# to show startup + steady-state domain currents and the qualitative
# divergence trend (it is not expected to acquire lock -- see
# ../records/RECORD-001). Part B (proposal) needs enough window to plausibly
# acquire AND hold the row-7 criterion (estimate from the measured f_c/PM:
# see ../records/RECORD-001 "Why these durations").
if [[ $QUICK -eq 1 ]]; then
  TSTOP_A=200n; TAVG0_A=100n
  TSTOP_B=200n; TAVG0_B=100n
else
  TSTOP_A=${TSTOP_A_OVERRIDE:-500n}
  TAVG0_A=${TAVG0_A_OVERRIDE:-300n}
  TSTOP_B=${TSTOP_B_OVERRIDE:-2500n}
  TAVG0_B=${TAVG0_B_OVERRIDE:-2000n}
fi
TPRINT=100p
TMAX=100p

run_ngspice() {
  local tmpl="$1" tag="$2" tstop="$3" tavg0="$4"
  local out="$WORK/tb_$tag.sp"
  cp "$tmpl" "$out"
  sed -i.bak \
    -e "s#\\\$PDK_ROOT/\\\$PDK#$PDK_ROOT/$PDK#g" \
    -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@CORNER_RES@/$RES_CORNER/g" \
    -e "s/@TEMP@/$TEMP/g" -e "s/@VDD@/$VDD/g" \
    -e "s/@FREF@/$FREF/g" -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
    -e "s/@IREF@/$IREF/g" -e "s/@B0V@/$B0V/g" -e "s/@B1V@/$B1V/g" \
    -e "s/@VC0@/$VC0/g" -e "s/@R1L@/2400u/g" \
    -e "s/@TSTOP@/$tstop/g" -e "s/@TPRINT@/$TPRINT/g" -e "s/@TMAX@/$TMAX/g" \
    -e "s/@TAVG0@/$tavg0/g" \
    "$out"
  rm -f "$out.bak"
  ( cd "$WORK" && ngspice -b "tb_$tag.sp" > "$WORK/log_$tag.txt" 2>&1 )
  mv "$WORK/wave.dat" "$WORK/wave_$tag.dat.last" 2>/dev/null || true
}

echo "=== Part A: as-drawn ($TSTOP_A simulated) ===" >&2
run_ngspice "$HERE/tb_pll_closed.sp.tmpl" as_drawn "$TSTOP_A" "$TAVG0_A"
grep -E "^i_|^vc_" "$WORK/log_as_drawn.txt" || true

echo "=== Part B: proposal ($TSTOP_B simulated) ===" >&2
run_ngspice "$HERE/tb_pll_proposal.sp.tmpl" proposal "$TSTOP_B" "$TAVG0_B"
grep -E "^i_|^vc_" "$WORK/log_proposal.txt" || true

if [[ $QUICK -eq 1 ]]; then
  echo "--quick sanity run only, no CSV written" >&2
  exit 0
fi

# ---------------------------------------------------------------------------
# Extraction: lock criterion (row 7), reference spur (row 10), domain
# currents (row 11) -- see ../records/RECORD-001 for the full numbers.
# ---------------------------------------------------------------------------
python3 "$HERE/extract.py" "$WORK" "$RECORD_DIR" "$FREF" "$TSTOP_A,$TSTOP_B" "$TAVG0_A,$TAVG0_B"
