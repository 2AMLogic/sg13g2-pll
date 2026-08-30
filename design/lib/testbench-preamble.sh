# shellcheck shell=bash
# sg13g2-pll :: shared setup preamble for sim/*/testbench/run.sh (issue #86).
#
# This file is a *library*, not a standalone script: it must be `source`d,
# as close to the top as possible, by a sim/*/testbench/run.sh script --
# directly at that script's own top level, not from inside a function or a
# second layer of sourcing, since this file locates the caller via
# `${BASH_SOURCE[1]}` (the frame `source` pushes for whoever sourced it).
#
# What sourcing this file sets, in order:
#
#   (nothing to set first -- unlike design/lib/netlist-export.sh's wrapper
#   contract, this library needs no input variables from the caller except
#   the optional WORK pre-set described below.)
#
#   set -euo pipefail   applied to the sourcing script too (same shell).
#   HERE           absolute path of the testbench/ directory the sourcing
#                  run.sh lives in, derived from the CALLER's own
#                  BASH_SOURCE (BASH_SOURCE[1] from inside this file) --
#                  the exact computation every run.sh used to do itself
#                  from its own BASH_SOURCE[0] before this extraction.
#   RECORD_DIR     that record's directory, i.e. "$HERE/..".
#   WORK           a scratch directory. If the wrapper pre-set WORK to a
#                  non-empty path BEFORE sourcing this file, that directory
#                  is reused (mkdir -p'd, not torn down on EXIT) -- this is
#                  how sg13cmos5l-divider-nrange-retiming's DIV36_WORK
#                  debugging override works: its wrapper sets
#                  `WORK="${DIV36_WORK:-}"` before the source line. Every
#                  other wrapper leaves WORK unset, so this file `mktemp
#                  -d`'s a fresh one and registers `trap 'rm -rf "$WORK"'
#                  EXIT` to clean it up.
#   PDK_ROOT, PDK  validated present (guard-clause failure if unset),
#                  values otherwise untouched.
#   OSDI           "$PDK_ROOT/$PDK/libs.tech/ngspice/osdi" -- every run.sh's
#                  OSDI model directory.
#
# Left to each wrapper, written AFTER the source line (these depend on
# RECORD_DIR, which does not exist until this file has run):
#   - OUT_CSV / OUT_COMP / OUT_A / OUT_B / SIM_ROOT / CORNERS / SNAP, or
#     whatever other record-specific path variables it needs;
#   - the .spiceinit OSDI model list (differs block to block -- not every
#     testbench needs every OSDI object);
#   - every PVT-matrix / sweep-loop line, which is the actual substance of
#     each testbench and is untouched by this extraction.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "ERROR: design/lib/testbench-preamble.sh must be sourced by a" >&2
  echo "       sim/*/testbench/run.sh script, not executed directly." >&2
  exit 1
fi

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
# shellcheck disable=SC2034  # consumed by the sourcing run.sh, not this file
RECORD_DIR="$(cd "$HERE/.." && pwd)"

if [ -n "${WORK:-}" ]; then
  mkdir -p "$WORK"
else
  WORK="$(mktemp -d)"
  trap 'rm -rf "$WORK"' EXIT
fi

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

# shellcheck disable=SC2034  # consumed by the sourcing run.sh, not this file
OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"
