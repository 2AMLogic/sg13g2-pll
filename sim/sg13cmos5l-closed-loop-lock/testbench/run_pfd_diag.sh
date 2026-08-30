#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run_pfd_diag.sh
# (issue #50, Part of #16 -- root-cause investigation for the proposal
# deck's non-convergence, Scope item 1: PFD-level polarity)
#
# STANDALONE, PFD-ONLY diagnostic. Drives the frozen `pfd` subckt directly
# (`tb_pfd_only.sp.tmpl`) with two known REF/FB phase relationships and
# reads UP/DN back out, independently of `cp`/`loop_filter`/`vco`/
# `divider_chain`/`lock_detector` and independently of
# ../../sg13cmos5l-closed-loop-lock's own two closed-loop decks.
#
#   reflead: REF's rising edge arrives first every cycle (REF leads FB --
#            the textbook convention says this means "FB/VCO needs to
#            speed up", i.e. UP should dominate and STAY asserted until
#            FB's own edge arrives).
#   fblead:  FB's rising edge arrives first every cycle (FB leads REF --
#            textbook convention says "FB/VCO needs to slow down", i.e.
#            DN should dominate and stay asserted until REF's own edge).
#
# Both cases are run against TWO pfd variants:
#
#   asdrawn: verbatim ../netlist-snapshots/pfd.spice (the frozen, committed
#            netlist every closed-loop deck in this directory uses).
#   fixed:   a DIAGNOSTIC-ONLY patch (see "Root-cause patch" below) --
#            NOT a proposal to change the committed design here, and not
#            written back to ../netlist-snapshots/pfd.spice (frozen,
#            sim/README.md convention) or design/sg13cmos5l/ (a schematic-
#            level fix belongs to its own follow-up issue, filed off this
#            record -- see ../records/RECORD-002).
#
# ---------------------------------------------------------------------------
# Root-cause patch ("fixed" variant only)
# ---------------------------------------------------------------------------
# The as-drawn netlist's self-reset chain is:
#   XNR UP DN reset_raw VDD VSS nand2_hv      reset_raw = NAND(UP,DN)
#   XI1 reset_raw reset_d1 VDD VSS inv_hv     reset_d1  = NOT(reset_raw) = AND(UP,DN)
#   XI2 reset_d1 reset VDD VSS inv2x_hv       reset     = NOT(reset_d1) = NAND(UP,DN)
# Two inversions after `reset_raw` hands `reset` back the SAME NAND(UP,DN)
# sense reset_raw already had -- but the SR latches (`srlatch.sym`) need
# `reset` to be an ACTIVE-HIGH pulse of AND(UP,DN) (i.e. asserted only once
# BOTH UP and DN have been set), not NAND(UP,DN) (asserted whenever they are
# NOT both set, which is true almost always, including at idle). With the
# as-drawn parity, `reset` sits at logic 1 by default and only dips low
# during the brief window both UP/DN are 1 -- so each latch stays in its
# transparent (S-follows-through) mode essentially all the time, and UP/DN
# collapse to short combinational blips at every REF/FB edge respectively
# instead of held tristate outputs. The "fixed" variant adds a THIRD
# inverter (odd total after `reset_raw`) so `reset` = AND(UP,DN), restoring
# the intended idle-low / pulse-high-once-both-set behaviour, at the cost of
# one extra gate delay (~0.1-0.2 ns) in the self-reset path:
#   XNR UP DN reset_raw VDD VSS nand2_hv
#   XI1 reset_raw reset_d1 VDD VSS inv_hv
#   XI2 reset_d1 reset_d2 VDD VSS inv2x_hv    (same net renamed, same gates)
#   XI3 reset_d2 reset VDD VSS inv_hv         (NEW)
# No device sizing, topology outside this chain, or pin list changes.
# ---------------------------------------------------------------------------
#
# This is NOT run by ../testbench/run.sh and does not touch its output
# files (../corners/results_as_drawn.csv / results_proposal.csv /
# lock_trace_*.csv) -- it writes its own ../corners/pfd_polarity_diag.csv.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_pfd_diag.sh
#
# Requires: ngspice on PATH, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree. No cap_cmomi/cap_cmomf instance exists anywhere in
# `pfd.spice` (confirmed by grep against the frozen snapshot), so the
# arm64-macOS OSDI host constraint (../records/RECORD-001 "OSDI host
# constraint") that forces ideal-cap substitutions in the two closed-loop
# decks does not apply here -- this deck needs only psp103 (the sg13_hv
# MOS models `pfd.spice` instantiates).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
OUT="$RECORD_DIR/corners/pfd_polarity_diag.csv"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

cp "$HERE/../netlist-snapshots/pfd.spice" "$WORK/pfd_snap.spice"

# Derive the "fixed" diagnostic variant (see header "Root-cause patch")
# programmatically from the frozen snapshot, never by hand-editing a copy.
python3 - "$HERE/../netlist-snapshots/pfd.spice" "$WORK/pfd_fixed_diag.spice" <<'PY'
import re, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()
old = "XI1 reset_raw reset_d1 VDD VSS inv_hv\nXI2 reset_d1 reset VDD VSS inv2x_hv"
new = ("XI1 reset_raw reset_d1 VDD VSS inv_hv\n"
       "XI2 reset_d1 reset_d2 VDD VSS inv2x_hv\n"
       "XI3 reset_d2 reset VDD VSS inv_hv")
assert text.count(old) == 1, "reset-chain pattern not found exactly once"
patched = text.replace(old, new)
header = ("* ===========================================================================\n"
          "* DIAGNOSTIC-ONLY PATCH -- issue #50, NOT the committed design.\n"
          "* Adds a third inverter to the self-reset chain (odd inversion count after\n"
          "* reset_raw) so `reset` = AND(UP,DN) instead of the as-drawn NAND(UP,DN).\n"
          "* See ../testbench/run_pfd_diag.sh header \"Root-cause patch\" for the full\n"
          "* derivation. Never written back to ../netlist-snapshots/pfd.spice or\n"
          "* design/sg13cmos5l/ -- a schematic-level fix is its own follow-up issue.\n"
          "* ===========================================================================\n")
open(dst, "w").write(header + patched)
PY

MOS_CORNER=mos_tt
TEMP=27
VDD=3.3
FREF=20e6
TREF=$(python3 -c "print(f'{1/${FREF}:.6e}')")
TREFH=$(python3 -c "print(f'{1/${FREF}/2 - 100e-12:.6e}')")
# Fixed per-cycle lead/lag under test: 10% of the reference period (5 ns at
# 20 MHz) -- comfortably inside one cycle, well clear of the 100p edge
# rates and the reset-window dead zone, and of the same order as the
# closed-loop deck's own near-zero initial Delta-f (RECORD-001: +0.84% at
# the first cycle), so this reads the PFD's small-phase-error behaviour,
# not a large-frequency-error corner case.
TOFFSET=5e-9
TSTOP=500n
TAVG0=200n   # skip the first 4 reference cycles (startup/reset transient)
TPRINT=100p
TMAX=100p

run_case() {
  local variant="$1" pfd_include="$2" case_tag="$3" ref_delay="$4" fb_delay="$5"
  local tag="${variant}_${case_tag}"
  local out="$WORK/tb_$tag.sp"
  cp "$HERE/tb_pfd_only.sp.tmpl" "$out"
  sed -i.bak \
    -e "s#\\\$PDK_ROOT/\\\$PDK#$PDK_ROOT/$PDK#g" \
    -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@TEMP@/$TEMP/g" \
    -e "s/@VDD@/$VDD/g" -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
    -e "s/@REF_DELAY@/$ref_delay/g" -e "s/@FB_DELAY@/$fb_delay/g" \
    -e "s/@PFD_INCLUDE@/$pfd_include/g" \
    -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/$TPRINT/g" -e "s/@TMAX@/$TMAX/g" \
    -e "s/@TAVG0@/$TAVG0/g" \
    "$out"
  rm -f "$out.bak"
  ( cd "$WORK" && ngspice -b "tb_$tag.sp" > "$WORK/log_$tag.txt" 2>&1 )
  mv "$WORK/wave.dat" "$WORK/wave_$tag.dat.last" 2>/dev/null || true
}

for variant_pair in "asdrawn:pfd_snap.spice" "fixed:pfd_fixed_diag.spice"; do
  variant="${variant_pair%%:*}"; include="${variant_pair##*:}"
  echo "=== $variant / reflead: REF's edge arrives first every cycle ===" >&2
  run_case "$variant" "$include" reflead 0 "$TOFFSET"
  grep -E "^up_avg|^dn_avg" "$WORK/log_${variant}_reflead.txt" || true

  echo "=== $variant / fblead: FB's edge arrives first every cycle ===" >&2
  run_case "$variant" "$include" fblead "$TOFFSET" 0
  grep -E "^up_avg|^dn_avg" "$WORK/log_${variant}_fblead.txt" || true
done

python3 - "$WORK" "$OUT" "$VDD" <<'PY'
import re, sys
work, out, vdd = sys.argv[1], sys.argv[2], float(sys.argv[3])

def read_meas(tag):
    text = open(f"{work}/log_{tag}.txt").read()
    up = float(re.search(r"up_avg\s*=\s*([-\d.eE+]+)", text).group(1))
    dn = float(re.search(r"dn_avg\s*=\s*([-\d.eE+]+)", text).group(1))
    return up, dn

rows = ["variant,case,up_avg_v,dn_avg_v,up_duty_frac,dn_duty_frac,verdict"]
for variant in ("asdrawn", "fixed"):
    for tag, desc in [("reflead", "REF leads FB"), ("fblead", "FB leads REF")]:
        up, dn = read_meas(f"{variant}_{tag}")
        up_duty = up / vdd
        dn_duty = dn / vdd
        if tag == "reflead":
            verdict = "UP-dominant (textbook)" if up > dn else "DN-dominant/symmetric (no tristate hold)"
        else:
            verdict = "DN-dominant (textbook)" if dn > up else "UP-dominant/symmetric (no tristate hold)"
        rows.append(f"{variant},{desc},{up:.6f},{dn:.6f},{up_duty:.6f},{dn_duty:.6f},{verdict}")

open(out, "w").write("\n".join(rows) + "\n")
print("\n".join(rows), file=sys.stderr)
PY

echo "Wrote $OUT" >&2
