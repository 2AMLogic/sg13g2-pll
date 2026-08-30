#!/usr/bin/env bash
# The repeatable driver for layout/sg13cmos5l-pll/'s device-level layout flow
# (issue #24) -- the SG13CMOS5L sibling of run-pll-layout-flow.sh:
# plan.json (always, PDK-free) -> build.json (draws every planned group, then
# DRC/extract/compose/LVS every one against the real curated sg13cmos5l deck
# and records what klt actually said) -> record.md.
#
#   layout/bin/setup-venv.sh                    # once, or after a pin bump
#   layout/bin/run-pll-cmos5l-layout-flow.sh    # writes a fresh record
#
# Writes layout/sg13cmos5l-pll/reports/<record-id>/ and updates
# layout/sg13cmos5l-pll/reports/LATEST to point at it. Never edits a prior
# record -- see layout/sg13cmos5l-pll/README.md's "Directory layout" section.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYOUT_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$LAYOUT_DIR/.." && pwd)"
PLL_DIR="$LAYOUT_DIR/sg13cmos5l-pll"

KLT="$LAYOUT_DIR/.venv/bin/klt"
PY="$LAYOUT_DIR/.venv/bin/python"
PDK_VARIANT="${PDK:-ihp-sg13cmos5l}"
DECK="${DECK:-sg13cmos5l}"
PDK_ROOT_ARG=()
if [[ -n "${PDK_ROOT:-}" ]]; then
  PDK_ROOT_ARG=(--pdk-root "$PDK_ROOT")
fi

if [[ ! -x "$KLT" ]]; then
  echo "run-pll-cmos5l-layout-flow.sh: no $KLT -- run layout/bin/setup-venv.sh first" >&2
  exit 1
fi

# The drawing half needs `klayout.db`, which the pinned klt install already
# brings in -- run under the venv's own interpreter rather than the system
# python3 so a bare host without klayout still works.
if ! "$PY" -c "import klayout.db" 2>/dev/null; then
  echo "run-pll-cmos5l-layout-flow.sh: $PY has no klayout.db -- re-run layout/bin/setup-venv.sh --force" >&2
  exit 1
fi

SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
DIRTY=""
git -C "$REPO_ROOT" diff --quiet -- . ":(exclude)layout/sg13cmos5l-pll/reports" || DIRTY="-dirty"
git -C "$REPO_ROOT" diff --cached --quiet -- . ":(exclude)layout/sg13cmos5l-pll/reports" || DIRTY="-dirty"
RECORD_ID="$(date -u +%Y%m%d-%H%M%S)-${SHA}${DIRTY}"
RECORD_DIR="$PLL_DIR/reports/$RECORD_ID"
mkdir -p "$RECORD_DIR"

echo "run-pll-cmos5l-layout-flow.sh: writing $RECORD_DIR"

"$PY" "$HERE/pll_cmos5l_layout.py" \
  --netlist-dir "$REPO_ROOT/design/sg13cmos5l/netlist" \
  --out-dir "$RECORD_DIR" \
  --klt "$KLT" \
  --pdk "$PDK_VARIANT" \
  --deck "$DECK" \
  "${PDK_ROOT_ARG[@]}"

"$PY" "$HERE/render-pll-cmos5l-record.py" \
  "$RECORD_DIR" "$KLT" "$PDK_VARIANT" "$DECK" "${PDK_ROOT:-}"

echo "$RECORD_ID" > "$PLL_DIR/reports/LATEST"
echo "run-pll-cmos5l-layout-flow.sh: done -- $RECORD_DIR/record.md"
