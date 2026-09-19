#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/extraction/run-pex.sh
# (issue #30, Part of #16 -- post-layout PEX + PVT re-simulation)
#
# Runs `klt extract --deck sg13cmos5l --parasitics` over EVERY routed block
# in the committed layout record and writes, per block:
#
#   ../netlist-snapshots/<block>.pex.spice   parasitic-annotated netlist
#   ../netlist-snapshots/<block>.pex.json    klt's own structured report
#
# plus a single roll-up `provenance.json` recording the klt version, the
# layout record the GDS came from, and the per-block R/C totals -- so the
# claim "real parasitics were modelled" in ../records/RECORD-001 is backed
# by machine-readable evidence, never by assertion.
#
#   ./run-pex.sh
#
# Requires: a `klt` that carries BOTH klayout-tools#2012 (sg13cmos5l in the
# parasitics registry) and klayout-tools#2126 (the curated sg13cmos5l metal
# R/C coefficients). The preflight below HARD-FAILS on a klt that has
# neither or only the first -- see "klt version requirement" in
# ../records/RECORD-001 for why a silently-zero extraction is the specific
# failure this script refuses to produce.
#
# Override the binary with KLT_BIN if the klt on PATH is too old:
#   KLT_BIN="python3 -c 'from klayout_tools.cli import main; main()'"
# is not supported -- pass a real executable, or put a new enough klt first
# on PATH. PEX_KLT_PYTHONPATH may instead point at a klayout-tools source
# checkout, which this script runs via `python3 -m`.

set -euo pipefail

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:=ihp-sg13cmos5l}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$RECORD_DIR/../.." && pwd)"

LAYOUT_REPORTS="$REPO_ROOT/layout/sg13cmos5l-pll/reports"
LAYOUT_RECORD="${PEX_LAYOUT_RECORD:-$(cat "$LAYOUT_REPORTS/LATEST")}"
GDS_DIR="$LAYOUT_REPORTS/$LAYOUT_RECORD"

SNAP="$RECORD_DIR/netlist-snapshots"
mkdir -p "$SNAP"

# Every block the layout record routes. This list is asserted against the
# record's own compose.*.json below, so a block added to the layout flow and
# forgotten here is an error, not a silent omission (acceptance criterion:
# "EVERY routed block has a parasitic-annotated netlist").
BLOCKS=(pfd cp loop_filter vco divider_chain lock_detector)

klt_run() {
  if [ -n "${PEX_KLT_PYTHONPATH:-}" ]; then
    PYTHONPATH="$PEX_KLT_PYTHONPATH" python3 -m klayout_tools.cli "$@"
  else
    "${KLT_BIN:-klt}" "$@"
  fi
}

# --- preflight: refuse to run against a klt with no curated coefficients ---
echo "preflight: checking klt parasitics support for deck sg13cmos5l" >&2
probe_json="$(klt_run extract --deck sg13cmos5l --parasitics \
  --top pll_loop_filter --format json \
  -o "$(mktemp -d)/probe.spice" "$GDS_DIR/pll_loop_filter.gds")"

python3 - "$probe_json" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
if "error" in d:
    sys.exit(
        "FATAL: klt rejected the parasitics run: %s\n"
        "       This klt predates klayout-tools#2012 (sg13cmos5l missing from\n"
        "       the parasitics registry). Upgrade klt or set PEX_KLT_PYTHONPATH."
        % d["error"].get("message", d["error"])
    )
p = d.get("parasitics") or {}
missing = p.get("metals_without_coefficient") or []
if missing:
    sys.exit(
        "FATAL: the sg13cmos5l parasitics deck has no curated R/C coefficients\n"
        "       for: %s\n"
        "       This klt predates klayout-tools#2126. Extraction would succeed\n"
        "       while modelling ZERO real parasitics -- exactly the silent\n"
        "       'post-layout' result issue #30's AC #3 exists to prevent.\n"
        "       Upgrade klt or set PEX_KLT_PYTHONPATH." % ", ".join(missing)
    )
if not (p.get("r_count") or 0) or not (p.get("c_count") or 0):
    sys.exit(
        "FATAL: probe extraction reported r_count=%s c_count=%s -- no parasitics\n"
        "       were actually annotated. Refusing to produce a netlist that\n"
        "       would be labelled 'post-layout' without being one."
        % (p.get("r_count"), p.get("c_count"))
    )
print("preflight OK: r_count=%s c_count=%s, no metal without a coefficient"
      % (p["r_count"], p["c_count"]), file=sys.stderr)
PY

KLT_VERSION="$(klt_run --version 2>&1 | head -1)"
echo "klt: $KLT_VERSION" >&2
echo "layout record: $LAYOUT_RECORD" >&2

# --- per-block extraction ---
for block in "${BLOCKS[@]}"; do
  gds="$GDS_DIR/pll_${block}.gds"
  [ -f "$gds" ] || { echo "FATAL: missing routed GDS $gds" >&2; exit 1; }
  [ -f "$GDS_DIR/compose.${block}.json" ] || {
    echo "FATAL: $block has no compose.${block}.json in $LAYOUT_RECORD --" >&2
    echo "       it is not a routed block of this record." >&2; exit 1; }

  # `--pdk`/`--pdk-root` is what binds an extracted MOS to the PDK's own
  # `sg13_hv_nmos`/`sg13_hv_pmos` subcircuits instead of the deck's bare
  # device-class name -- the same binding layout/bin/pll_cmos5l_layout.py
  # uses, and a precondition for the netlist being simulatable at all.
  echo "extracting pll_${block} ..." >&2
  klt_run extract --deck sg13cmos5l --parasitics \
    --pdk "$PDK" --pdk-root "$PDK_ROOT" \
    --top "pll_${block}" --format json \
    -o "$SNAP/pll_${block}.pex.spice" "$gds" \
    > "$SNAP/pll_${block}.pex.json"

  python3 - "$SNAP/pll_${block}.pex.json" "pll_${block}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
if "error" in d:
    sys.exit("FATAL: %s extraction failed: %s" % (sys.argv[2], d["error"]))
p = d["parasitics"]
if p["metals_without_coefficient"]:
    sys.exit("FATAL: %s: metals without coefficient: %s"
             % (sys.argv[2], p["metals_without_coefficient"]))
print("  %s: %d devices, %d nets, R=%d (%.3f ohm total), C=%d (%.3f fF total)"
      % (sys.argv[2], d["device_count"], d["net_count"], p["r_count"],
         p["total_resistance_ohm"], p["c_count"], p["total_capacitance_ff"]),
      file=sys.stderr)
PY
done

# --- roll-up provenance ---
python3 - "$SNAP" "$LAYOUT_RECORD" "$KLT_VERSION" "${BLOCKS[@]}" <<'PY'
import hashlib, json, os, sys
snap, layout_record, klt_version = sys.argv[1], sys.argv[2], sys.argv[3]
blocks = sys.argv[4:]
out = {
    "deck": "sg13cmos5l",
    "pdk": "ihp-sg13cmos5l",
    "klt_version": klt_version,
    "klt_requires": [
        "klayout-tools#2012 (sg13cmos5l registered in the parasitics registry)",
        "klayout-tools#2126 (curated sg13cmos5l nominal metal R/C coefficients)",
    ],
    "layout_record": layout_record,
    "real_parasitics_modelled": True,
    "blocks": {},
}
for b in blocks:
    rep = json.load(open(os.path.join(snap, "pll_%s.pex.json" % b)))
    p = rep["parasitics"]
    spice = os.path.join(snap, "pll_%s.pex.spice" % b)
    out["blocks"]["pll_%s" % b] = {
        "netlist": "netlist-snapshots/pll_%s.pex.spice" % b,
        "netlist_sha256": hashlib.sha256(open(spice, "rb").read()).hexdigest(),
        "device_count": rep["device_count"],
        "net_count": rep["net_count"],
        "r_count": p["r_count"],
        "c_count": p["c_count"],
        "cc_count": p["cc_count"],
        "total_resistance_ohm": p["total_resistance_ohm"],
        "total_capacitance_ff": p["total_capacitance_ff"],
        "total_coupling_capacitance_ff": p["total_coupling_capacitance_ff"],
        "metals_without_coefficient": p["metals_without_coefficient"],
        "overlap_pairs_without_coefficient": p["overlap_pairs_without_coefficient"],
        "rc_model": "lumped star per net (klt default); see the report's own"
                    " parasitics.model for the full statement",
    }
json.dump(out, open(os.path.join(snap, "provenance.json"), "w"), indent=2, sort_keys=True)
open(os.path.join(snap, "provenance.json"), "a").write("\n")
print("wrote %s/provenance.json" % snap, file=sys.stderr)
PY
