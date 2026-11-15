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
#
# This is a thin, flow-specific wrapper: the shared driver loop (record-id/
# dirty detection, the klt preflight, the layout -> renderer -> record_store
# dedupe calls, and the LATEST pointer write) is shared with
# layout/bin/run-pll-cmos5l-layout-flow.sh via layout/bin/layout-flow.sh
# (issue #415) -- see that file's header for the parameter contract this
# wrapper fills in below.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYOUT_DIR="$(cd "$HERE/.." && pwd)"
# shellcheck disable=SC2034  # consumed by the sourced lib below, not this file
DRIVER_NAME="run-pll-layout-flow.sh"
# shellcheck disable=SC2034
PLL_DIR_REL="layout/pll/"
# shellcheck disable=SC2034
PDK_VARIANT_DEFAULT="ihp-sg13g2"
# shellcheck disable=SC2034
NETLIST_DIR_REL="design/netlist"
# shellcheck disable=SC2034
LAYOUT_SCRIPT="$HERE/pll_layout.py"
# shellcheck disable=SC2034
RENDER_SCRIPT="$HERE/render-pll-record.py"
# shellcheck disable=SC2034  # the stdlib-only flow runs on the system python3
PYEXE="python3"

# shellcheck source=layout-flow.sh
source "${HERE}/layout-flow.sh"
