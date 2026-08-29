#!/usr/bin/env bash
# The repeatable driver for layout/pll/'s device-level layout flow
# (issue #13): plan.json (always, PDK-free) -> build.json (attempts every
# planned klt gen group and records the real result) -> record.md.
#
#   layout/bin/setup-venv.sh              # once, or after bumping requirements.txt
#   layout/bin/run-pll-layout-flow.sh     # writes a fresh record
#
# Writes layout/pll/reports/<record-id>/ and updates
# layout/pll/reports/LATEST to point at it. Never edits a prior record --
# see layout/pll/README.md's "Directory layout" section.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYOUT_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$LAYOUT_DIR/.." && pwd)"
PLL_DIR="$LAYOUT_DIR/pll"

KLT="$LAYOUT_DIR/.venv/bin/klt"
PDK_VARIANT="${PDK:-ihp-sg13g2}"
PDK_ROOT_ARG=()
if [[ -n "${PDK_ROOT:-}" ]]; then
  PDK_ROOT_ARG=(--pdk-root "$PDK_ROOT")
fi

if [[ ! -x "$KLT" ]]; then
  echo "run-pll-layout-flow.sh: no $KLT -- run layout/bin/setup-venv.sh first" >&2
  exit 1
fi

SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
DIRTY=""
git -C "$REPO_ROOT" diff --quiet -- . ":(exclude)layout/pll/reports" || DIRTY="-dirty"
git -C "$REPO_ROOT" diff --cached --quiet -- . ":(exclude)layout/pll/reports" || DIRTY="-dirty"
RECORD_ID="$(date -u +%Y%m%d-%H%M%S)-${SHA}${DIRTY}"
RECORD_DIR="$PLL_DIR/reports/$RECORD_ID"
mkdir -p "$RECORD_DIR"

echo "run-pll-layout-flow.sh: writing $RECORD_DIR"

python3 "$HERE/pll_layout.py" \
  --netlist-dir "$REPO_ROOT/design/netlist" \
  --out-dir "$RECORD_DIR" \
  --klt "$KLT" \
  --pdk "$PDK_VARIANT" \
  "${PDK_ROOT_ARG[@]}"

python3 "$HERE/render-pll-record.py" "$RECORD_DIR" "$KLT" "$PDK_VARIANT" "${PDK_ROOT:-}"

echo "$RECORD_ID" > "$PLL_DIR/reports/LATEST"
echo "run-pll-layout-flow.sh: done -- $RECORD_DIR/record.md"
