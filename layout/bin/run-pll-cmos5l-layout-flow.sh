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
#
# This is a thin, flow-specific wrapper: the shared driver loop (record-id/
# dirty detection, the klt preflight, the layout -> renderer -> record_store
# dedupe calls, and the LATEST pointer write) is shared with
# layout/bin/run-pll-layout-flow.sh via layout/bin/layout-flow.sh (issue
# #415) -- see that file's header for the parameter contract this wrapper
# fills in below.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYOUT_DIR="$(cd "$HERE/.." && pwd)"
# shellcheck disable=SC2034  # consumed by the sourced lib below, not this file
DRIVER_NAME="run-pll-cmos5l-layout-flow.sh"
# shellcheck disable=SC2034
PLL_DIR_REL="layout/sg13cmos5l-pll/"
# shellcheck disable=SC2034
PDK_VARIANT_DEFAULT="ihp-sg13cmos5l"
# shellcheck disable=SC2034
DECK="${DECK:-sg13cmos5l}"
# shellcheck disable=SC2034
NETLIST_DIR_REL="design/sg13cmos5l/netlist"
# shellcheck disable=SC2034
LAYOUT_SCRIPT="$HERE/pll_cmos5l_layout.py"
# shellcheck disable=SC2034
RENDER_SCRIPT="$HERE/render-pll-cmos5l-record.py"
# The drawing half needs `klayout.db`, which the pinned klt install already
# brings in -- run under the venv's own interpreter rather than the system
# python3 so a bare host without klayout still works.
# shellcheck disable=SC2034
PYEXE="$LAYOUT_DIR/.venv/bin/python"

# shellcheck disable=SC2317  # invoked by layout-flow.sh via EXTRA_PREFLIGHT
cmos5l_klayout_preflight() {
  if ! "$PYEXE" -c "import klayout.db" 2>/dev/null; then
    echo "$DRIVER_NAME: $PYEXE has no klayout.db -- re-run layout/bin/setup-venv.sh --force" >&2
    exit 1
  fi
}
# shellcheck disable=SC2034
EXTRA_PREFLIGHT=cmos5l_klayout_preflight

# shellcheck source=layout-flow.sh
source "${HERE}/layout-flow.sh"
