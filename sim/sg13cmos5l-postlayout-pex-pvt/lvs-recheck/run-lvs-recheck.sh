#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/lvs-recheck/run-lvs-recheck.sh
# (issue #30, Part of #16 -- post-layout PEX + PVT re-simulation)
#
# WHY THIS EXISTS, in one sentence: a post-layout number is only comparable
# to its schematic-level twin if the layout it came from is the same circuit
# as the schematic, and for three of this port's six blocks that was never
# established -- so this record re-establishes it (or records that it still
# cannot be), rather than quietly comparing numbers across an unverified
# topology.
#
# Background. The committed layout record's own LVS artifacts
# (layout/sg13cmos5l-pll/reports/<record>/lvs.<block>.json) show:
#
#   pfd, cp, divider_chain      returncode 0  -- a real compare ran
#   loop_filter, vco,           returncode 1  -- NOT COMPARED AT ALL: klt
#   lock_detector                              refused to convert the
#                                              subckt-call reference netlist,
#                                              because `cap_cmomi` was not a
#                                              known device for the deck
#
# That third class is not "LVS failed", it is "LVS never ran" -- and those
# are exactly the three blocks whose schematic instantiates a MoM capacitor.
#
# What this script does differently: klt's own error message names the fix
# ("if it is a real device, pass reference.device_map to map it explicitly"),
# so each request document is re-emitted with one added `device_map` entry
# per MoM class the reference netlist actually instantiates:
#
#     "cap_cmomi": {"kind": "capacitor", "class": "cap_cmomi"}
#
# Nothing else about any request changes -- same GDS, same reference netlist,
# same deck, same flatten options -- so the three previously-comparable
# blocks are re-run byte-identically and act as a control on the klt upgrade
# itself.
#
# Usage:
#   ./run-lvs-recheck.sh
#
#   KLT_BIN=...              override the klt executable
#   LVS_KLT_PYTHONPATH=...   run `python3 -m klayout_tools.cli` from a
#                            klayout-tools source checkout instead
#   LVS_LAYOUT_RECORD=...    override the layout record (default: LATEST)
#
# Outputs, all under this directory:
#   requests/<block>.request.json   the exact request each compare was given
#   reports/<block>.lvs.json        klt's own full structured report
#   summary.json                    per-block verdict roll-up
#
# Exit status is 0 even when a block mismatches: a mismatch is this script's
# *finding*, not its failure. A block that still cannot be COMPARED is what
# it flags loudly, because that is the state the record has to disclose.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$RECORD_DIR/../.." && pwd)"

LAYOUT_REPORTS="$REPO_ROOT/layout/sg13cmos5l-pll/reports"
LAYOUT_RECORD="${LVS_LAYOUT_RECORD:-$(cat "$LAYOUT_REPORTS/LATEST")}"
SRC="$LAYOUT_REPORTS/$LAYOUT_RECORD"

REQ_DIR="$HERE/requests"
REP_DIR="$HERE/reports"
mkdir -p "$REQ_DIR" "$REP_DIR"

BLOCKS=(pfd cp loop_filter vco divider_chain lock_detector)

klt_run() {
  if [ -n "${LVS_KLT_PYTHONPATH:-}" ]; then
    PYTHONPATH="$LVS_KLT_PYTHONPATH" python3 -m klayout_tools.cli "$@"
  else
    "${KLT_BIN:-klt}" "$@"
  fi
}

KLT_VERSION="$(klt_run --version 2>&1 | head -1)"
echo "klt: $KLT_VERSION" >&2
echo "layout record: $LAYOUT_RECORD" >&2

# klt lvs resolves the request's relative `layout.file`/`reference.netlist`
# against the request document's own directory, so the compare runs from a
# scratch copy of the record's inputs rather than writing into the committed
# layout record.
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

for block in "${BLOCKS[@]}"; do
  src_req="$SRC/lvs.${block}.request.json"
  [ -f "$src_req" ] || { echo "FATAL: no $src_req" >&2; exit 1; }

  cp "$SRC/pll_${block}.gds" "$SRC/${block}.reference.spice" "$WORK/"

  python3 - "$src_req" "$WORK/${block}.request.json" \
           "$SRC/${block}.reference.spice" <<'PY'
import json, re, sys

src, dst, ref = sys.argv[1], sys.argv[2], sys.argv[3]
req = json.load(open(src))
text = open(ref).read()

dm = req.setdefault("reference", {}).setdefault("device_map", {})
added = []
for cls in ("cap_cmomi", "cap_cmomf"):
    # Only map a class the reference netlist actually instantiates -- an
    # unused mapping would be dead configuration in a committed artifact.
    if re.search(r"(?mi)^\s*X\S+.*\b%s\b" % cls, text) and cls not in dm:
        dm[cls] = {"kind": "capacitor", "class": cls}
        added.append(cls)

json.dump(req, open(dst, "w"), indent=2, sort_keys=True)
open(dst, "a").write("\n")
print("device_map additions: %s" % (", ".join(added) or "(none)"), file=sys.stderr)
PY

  cp "$WORK/${block}.request.json" "$REQ_DIR/${block}.request.json"

  echo "lvs ${block} ..." >&2
  rc=0
  klt_run lvs "$WORK/${block}.request.json" --format json \
    > "$REP_DIR/${block}.lvs.json" 2> "$WORK/${block}.err" || rc=$?
  # klt exits 3 on "compared, and it mismatches" -- a verdict, not a crash.
  # Any other non-zero means no compare happened; keep klt's own JSON error
  # as the report body so the summary can say so precisely.
  if [ ! -s "$REP_DIR/${block}.lvs.json" ]; then
    cp "$WORK/${block}.err" "$REP_DIR/${block}.lvs.json"
  fi
  echo "  ${block}: klt exit ${rc}" >&2
done

python3 - "$REP_DIR" "$LAYOUT_RECORD" "$KLT_VERSION" "${BLOCKS[@]}" <<'PY'
import json, os, sys

rep_dir, layout_record, klt_version = sys.argv[1], sys.argv[2], sys.argv[3]
blocks = sys.argv[4:]

out = {
    "layout_record": layout_record,
    "klt_version": klt_version,
    "device_map_addition": {
        "classes": ["cap_cmomi"],
        "why": "the committed layout record's own lvs.<block>.json shows "
               "loop_filter/vco/lock_detector were never compared -- klt "
               "refused to convert their subckt-call reference netlists "
               "because cap_cmomi was not a known device for the deck. klt's "
               "own error names device_map as the fix; nothing else in any "
               "request changed.",
    },
    "blocks": {},
}

for b in blocks:
    d = json.load(open(os.path.join(rep_dir, "%s.lvs.json" % b)))
    if "error" in d:
        out["blocks"][b] = {
            "compared": False,
            "status": None,
            "error": d["error"].get("message", d["error"]),
        }
        continue
    counts = d.get("counts", {})
    out["blocks"][b] = {
        "compared": True,
        "status": d.get("status"),
        "mismatch_count": d.get("mismatch_count"),
        "error_count": d.get("error_count"),
        "category_counts": d.get("category_counts"),
        "counts": counts,
    }

path = os.path.join(os.path.dirname(rep_dir), "summary.json")
json.dump(out, open(path, "w"), indent=2, sort_keys=True)
open(path, "a").write("\n")

for b in blocks:
    r = out["blocks"][b]
    if not r["compared"]:
        print("  %-14s NOT COMPARED: %s" % (b, r["error"][:90]), file=sys.stderr)
    else:
        c = r["counts"].get("devices", {})
        print("  %-14s %-10s devices %s/%s matched, %s mismatch(es)"
              % (b, r["status"], c.get("matched"), c.get("reference"),
                 r["mismatch_count"]), file=sys.stderr)
print("wrote %s" % path, file=sys.stderr)
PY
