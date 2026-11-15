#!/usr/bin/env bash
# One runner pass for the #157 lock_detector re-measurement through the shim.
# Paths all from env: LD157_TREE (scratch repo tree), LD157_RUN (state dir).
# Prints the pass log tail + pending count. The pass may die early on a
# still-unsolved dependency (empty replay) -- that is the cycle protocol, not
# a failure; see the tools header and RECORD-009.
#
# The shim must be executable under the NAME `ngspice` on PATH (the runner
# invokes `ngspice -b`); a shim named anything else silently falls through to
# the real ngspice and runs the grid locally -- the exact failure the batch
# driver exists to prevent. runpass therefore materialises
# $RUN/shim-bin/ngspice -> ngspice-bridge and puts ONLY that directory first
# on PATH.
set -uo pipefail
TREE="${LD157_TREE:?}"; RUN="${LD157_RUN:?}"; PASS="${1:?pass number}"
mkdir -p "$RUN/pending"
find "$RUN/pending" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
export LD157_CACHE="$RUN/cache" LD157_PENDING="$RUN/pending"
mkdir -p "$LD157_CACHE"
TOOLS="$TREE/sim/sg13cmos5l-postlayout-pex-pvt/rerun157/tools"
mkdir -p "$RUN/shim-bin"
ln -sf "$TOOLS/ngspice-bridge" "$RUN/shim-bin/ngspice"
cd "$TREE/sim/sg13cmos5l-postlayout-pex-pvt"
PATH="$RUN/shim-bin:$PATH" PDK_ROOT="${PDK_ROOT:?}" PDK=ihp-sg13cmos5l LD_WORK="$RUN/ldwork" \
  ./testbench/run_lock_detector.sh > "$RUN/pass$PASS.log" 2>&1
rc=$?
echo "pass$PASS runner rc=$rc pending=$(ls "$RUN/pending" | wc -l)"
tail -2 "$RUN/pass$PASS.log"

