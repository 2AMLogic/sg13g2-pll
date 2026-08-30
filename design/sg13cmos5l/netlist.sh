#!/usr/bin/env bash
# sg13g2-pll :: export the xschem schematic hierarchies under design/sg13cmos5l/
# to SPICE, on the SG13CMOS5L PDK -- the parallel-PDK port (issue #22, Part of
# #16, Chipalooza Challenge #6). Sibling of design/netlist.sh; SG13G2's own
# script/schematics/netlists are untouched by this port (parallel target, not
# a replacement -- see design/README.md "SG13CMOS5L port").
#
#   ./design/sg13cmos5l/netlist.sh                  # regenerate netlist/*.spice
#   ./design/sg13cmos5l/netlist.sh --check          # regenerate into a temp dir and diff
#   ./design/sg13cmos5l/netlist.sh --top <block>    # regenerate one committed block
#
# One exporter for every block named in spec/porting-plan.md Sec1.4: pfd, cp,
# loop_filter, vco, divider_chain, lock_detector. Each top is netlisted with
# its full hierarchy into one self-contained file under
# design/sg13cmos5l/netlist/, which is committed -- same fleet convention as
# design/netlist.sh (see that script's own header for the full rationale this
# one summarizes).
#
# `--check` regenerates into a temp dir and diffs against the committed copy
# instead of writing, so a stale committed netlist fails loudly -- this is
# the "regenerated on design change, not a one-off drop" reproducibility bar
# issue #7 / docs/design-evidence-tiers.md's T1 item 1 pass condition names.
#
# Requires: xschem on PATH, and the SG13CMOS5L PDK resolvable via PDK_ROOT/PDK
# (the same variables design/sg13cmos5l/xschemrc reads, matching `klt pdk
# find --pdk ihp-sg13cmos5l`).
#
# This is a thin, PDK-specific wrapper: the export pipeline itself (arg
# parsing, the BLOCKS list, expected_subckts()/check_export()/normalize()/
# banner()/export_block(), and the --check/write drivers) is shared with
# design/netlist.sh via design/lib/netlist-export.sh (issue #45) -- see that
# file's own header for the parameter contract this wrapper fills in below.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # consumed by the sourced lib below, not this file
DESIGN_REL="design/sg13cmos5l/"
# shellcheck disable=SC2034
SCRIPT_REL="design/sg13cmos5l/netlist.sh"
# shellcheck disable=SC2034
USAGE_NAME="sg13cmos5l/netlist.sh"
# shellcheck disable=SC2034
BANNER_SUFFIX=" (SG13CMOS5L)"

# shellcheck source=../lib/netlist-export.sh
source "${HERE}/../lib/netlist-export.sh"
