# shellcheck shell=bash
# sg13g2-pll :: shared driver loop for layout/bin's two device-level layout
# flow drivers, run-pll-layout-flow.sh and run-pll-cmos5l-layout-flow.sh
# (issue #415).
#
# This file is a *library*, not a standalone script: it must be `source`d by
# a thin flow-specific wrapper that sets the following variables first, then
# sources this file as its last line. Mirrors design/lib/netlist-export.sh
# (issue #45) -- the same collapse, one layer up in the same flow.
#
#   DRIVER_NAME          the wrapper's own name, used in every user-facing
#                        message (e.g. "run-pll-layout-flow.sh").
#   LAYOUT_DIR           absolute path of the layout/ directory the wrapper
#                        lives under; the lib derives REPO_ROOT and KLT
#                        ($LAYOUT_DIR/.venv/bin/klt) from it.
#   PLL_DIR_REL          repo-relative flow directory, trailing slash
#                        included (e.g. "layout/pll/"). Records are written
#                        under <PLL_DIR_REL>reports/<record-id>/ and the
#                        LATEST pointer at <PLL_DIR_REL>reports/LATEST.
#   PDK_VARIANT_DEFAULT  PDK_VARIANT when $PDK is unset (e.g. "ihp-sg13g2").
#   NETLIST_DIR_REL      repo-relative netlist dir passed as --netlist-dir
#                        (e.g. "design/netlist").
#   LAYOUT_SCRIPT        absolute path of the flow's plan/build python
#                        script.
#   RENDER_SCRIPT        absolute path of the flow's record renderer.
#   PYEXE                interpreter for all three python calls -- the
#                        system python3 for the stdlib-only SG13G2 flow,
#                        the pinned venv's python for the SG13CMOS5L flow
#                        (whose drawing half needs klayout.db).
#   DECK                 optional. When non-empty, the layout call grows a
#                        --deck "$DECK" and the renderer gets "$DECK" as its
#                        4th argument. Leave unset/empty for the SG13G2
#                        flow, which takes no deck.
#   EXTRA_PREFLIGHT      optional. Name of a wrapper-defined function,
#                        invoked after the klt preflight (the SG13CMOS5L
#                        wrapper's klayout.db import check).
#
# The wrapper may also export PDK / PDK_ROOT: $PDK overrides
# PDK_VARIANT_DEFAULT; a non-empty $PDK_ROOT becomes --pdk-root "$PDK_ROOT"
# for both the layout and the renderer call.
#
# Everything below -- the scaffold (record id, dirty detection, reports dir,
# user-facing messages), the klt preflight, the three calls (layout script
# -> renderer -> record_store.py dedupe), and the LATEST pointer write --
# is flow-invariant and shared verbatim between both drivers. The dirty
# detection excludes BOTH flows' reports subtrees: each driver's own last
# step updates its tracked reports/LATEST, so an own-subtree-only exclusion
# let one flow's LATEST write stamp the sibling's record id "-dirty" when
# the documented bump discipline (layout/requirements.txt, "Bump
# discipline") re-runs both flows back to back -- a false provenance claim
# in a record id, removed once, here.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "ERROR: layout/bin/layout-flow.sh must be sourced by a flow driver" >&2
  echo "       (run-pll-layout-flow.sh or run-pll-cmos5l-layout-flow.sh)," >&2
  echo "       not executed directly." >&2
  exit 1
fi

: "${DRIVER_NAME:?layout-flow.sh: DRIVER_NAME must be set by the wrapper}"
: "${LAYOUT_DIR:?layout-flow.sh: LAYOUT_DIR must be set by the wrapper}"
: "${PLL_DIR_REL:?layout-flow.sh: PLL_DIR_REL must be set by the wrapper}"
: "${PDK_VARIANT_DEFAULT:?layout-flow.sh: PDK_VARIANT_DEFAULT must be set by the wrapper}"
: "${NETLIST_DIR_REL:?layout-flow.sh: NETLIST_DIR_REL must be set by the wrapper}"
: "${LAYOUT_SCRIPT:?layout-flow.sh: LAYOUT_SCRIPT must be set by the wrapper}"
: "${RENDER_SCRIPT:?layout-flow.sh: RENDER_SCRIPT must be set by the wrapper}"
: "${PYEXE:?layout-flow.sh: PYEXE must be set by the wrapper}"

set -euo pipefail

REPO_ROOT="$(cd "$LAYOUT_DIR/.." && pwd)"
BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KLT="$LAYOUT_DIR/.venv/bin/klt"
PDK_VARIANT="${PDK:-$PDK_VARIANT_DEFAULT}"
DECK="${DECK:-}"
PDK_ROOT_ARG=()
if [[ -n "${PDK_ROOT:-}" ]]; then
  PDK_ROOT_ARG=(--pdk-root "$PDK_ROOT")
fi
LAYOUT_DECK_ARGS=()
RENDER_DECK_ARGS=()
if [[ -n "$DECK" ]]; then
  LAYOUT_DECK_ARGS=(--deck "$DECK")
  RENDER_DECK_ARGS=("$DECK")
fi

if [[ ! -x "$KLT" ]]; then
  echo "$DRIVER_NAME: no $KLT -- run layout/bin/setup-venv.sh first" >&2
  exit 1
fi

if [[ -n "${EXTRA_PREFLIGHT:-}" ]]; then
  "$EXTRA_PREFLIGHT"
fi

SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
DIRTY=""
# Both flows' tracked reports/LATEST pointers are rewritten by their own
# driver's last step, so BOTH reports subtrees must be excluded here --
# excluding only this flow's own subtree lets the sibling's LATEST write
# stamp this run's record id "-dirty" (see the header).
git -C "$REPO_ROOT" diff --quiet -- . \
  ":(exclude)layout/pll/reports" ":(exclude)layout/sg13cmos5l-pll/reports" || DIRTY="-dirty"
git -C "$REPO_ROOT" diff --cached --quiet -- . \
  ":(exclude)layout/pll/reports" ":(exclude)layout/sg13cmos5l-pll/reports" || DIRTY="-dirty"
RECORD_ID="$(date -u +%Y%m%d-%H%M%S)-${SHA}${DIRTY}"
RECORD_DIR="$REPO_ROOT/${PLL_DIR_REL}reports/$RECORD_ID"
mkdir -p "$RECORD_DIR"

echo "$DRIVER_NAME: writing $RECORD_DIR"

"$PYEXE" "$LAYOUT_SCRIPT" \
  --netlist-dir "$REPO_ROOT/$NETLIST_DIR_REL" \
  --out-dir "$RECORD_DIR" \
  --klt "$KLT" \
  --pdk "$PDK_VARIANT" \
  "${LAYOUT_DECK_ARGS[@]}" \
  "${PDK_ROOT_ARG[@]}"

"$PYEXE" "$RENDER_SCRIPT" \
  "$RECORD_DIR" "$KLT" "$PDK_VARIANT" "${RENDER_DECK_ARGS[@]}" "${PDK_ROOT:-}"

# Storage only (issue #261): move large artifacts into the shared immutable
# reports/objects/ store, leave same-path symlinks, write artifacts.json and
# verify every reference. record.md/plan.json/build.json stay inline.
"$PYEXE" "$BIN_DIR/record_store.py" dedupe "$RECORD_DIR"

echo "$RECORD_ID" > "$REPO_ROOT/${PLL_DIR_REL}reports/LATEST"
echo "$DRIVER_NAME: done -- $RECORD_DIR/record.md"
