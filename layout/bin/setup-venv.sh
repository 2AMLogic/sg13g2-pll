#!/usr/bin/env bash
# Source or run me: creates/refreshes layout/.venv with the pinned `klt`
# build from layout/requirements.txt.
#
#   layout/bin/setup-venv.sh          # create if missing, otherwise no-op
#   layout/bin/setup-venv.sh --force  # reinstall even if .venv/bin/klt exists
#
# Provenance: adapted from 2AMLogic/sky130-pll's own layout/bin/setup-venv.sh
# (itself adapted from sky130-bandgap), per this repo's CLAUDE.md
# harness-bootstrap rule, including the `--force-reinstall` install step.
# That flag is load-bearing whenever requirements.txt pins `klt` by git
# commit: upstream may not bump the reported package version between two
# different commits, so pip would otherwise consider an already-installed
# build "up to date" and silently keep the old `klt` in place after a pin
# bump.
set -euo pipefail

LAYOUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$LAYOUT_DIR/.venv"

if [[ -x "$VENV/bin/klt" && "${1:-}" != "--force" ]]; then
  echo "setup-venv.sh: $VENV already has klt installed (pass --force to reinstall)"
  "$VENV/bin/klt" --version
  exit 0
fi

echo "setup-venv.sh: creating $VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet --force-reinstall -r "$LAYOUT_DIR/requirements.txt"

echo "setup-venv.sh: installed"
"$VENV/bin/klt" --version
"$VENV/bin/klt" pdk find --pdk ihp-sg13g2 || {
  echo "setup-venv.sh: WARNING: no resolvable ihp-sg13g2 PDK install found." >&2
  echo "  Point \$PDK_ROOT (or pass --pdk-root to run-pll-layout-flow.sh) at" >&2
  echo "  an IHP-Open-PDK (ihp-sg13g2) install." >&2
}
# The SG13CMOS5L port (issue #24) resolves a *second*, separate PDK install
# (IHP-GmbH/ihp-sg13cmos5l, not a variant inside IHP-Open-PDK), so check it
# independently rather than assuming the sg13g2 hit above covers both.
"$VENV/bin/klt" pdk find --pdk ihp-sg13cmos5l || {
  echo "setup-venv.sh: WARNING: no resolvable ihp-sg13cmos5l PDK install found." >&2
  echo "  layout/bin/run-pll-cmos5l-layout-flow.sh needs one; point \$PDK_ROOT" >&2
  echo "  at an ihp-sg13cmos5l install (see layout/sg13cmos5l-pll/README.md)." >&2
}
