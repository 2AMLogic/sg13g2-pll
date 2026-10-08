#!/usr/bin/env bash
# Reproduce this record's five analog `klt erc` supply reports (issue #147).
#
# Run from the repository root. KLT must be the pinned grading build
# (klayout-tools @ e6284fbe62e25d9b293eed07889cb80a0b87e2f4, klayout 0.30.10,
# the build .github/workflows/signoff.yml installs), e.g.:
#
#   git clone https://github.com/2AMLogic/klayout-tools /tmp/klt
#   git -C /tmp/klt checkout e6284fbe62e25d9b293eed07889cb80a0b87e2f4
#   uv venv /tmp/klt-venv && VIRTUAL_ENV=/tmp/klt-venv uv pip install "klayout==0.30.10" /tmp/klt
#   KLT=/tmp/klt-venv/bin/klt layout/sg13cmos5l-pll/reports/20261008-230856-cd95c87/run-erc.sh
#
# Exit 4 from `klt erc` is expected: it is the antenna half's `not_checked`
# (no sg13cmos5l antenna table, klayout-tools#1994/#2179); the connectivity
# verdict is `erc_status`. Exit 1/2 is an error and stops the script --
# except the one deliberately recorded loop_filter deck-form error below.
set -euo pipefail

KLT="${KLT:-klt}"
REC=layout/sg13cmos5l-pll/reports/20261008-230856-cd95c87
GDS=layout/sg13cmos5l-pll/reports/20261003-183059-dc5644a
SPECS=layout/sg13cmos5l-pll

"$KLT" --version

run() {  # run <block> [extra klt erc args...]
  local block="$1"; shift
  local rc=0
  "$KLT" erc "$GDS/pll_${block}.gds" "$SPECS/erc-supply-spec.pll_${block}.json" \
    --top "pll_${block}" "$@" --format json > "$REC/erc.supply-spec.pll_${block}.json" || rc=$?
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 4 ]; then
    echo "klt erc failed on pll_${block} (exit $rc)" >&2
    exit 1
  fi
  echo "pll_${block}: exit $rc"
}

# The four MOS blocks: gate area = poly & Activ, and the curated deck's own
# rppd/rhigh/rsil bodies carved out of the GatPoly role.
run pfd --deck sg13cmos5l
run cp --deck sg13cmos5l
run vco --deck sg13cmos5l
run lock_detector --deck sg13cmos5l

# loop_filter (passive): no transistor gate exists, so klt erc refuses the
# MOS blocks' form (exit 1, "no net ... has any geometry on the declared gate
# role"). That refusal is recorded as friction evidence, then the block is
# run in the form its spec documents (no active_layer, no --deck).
rc=0
jq '.stackup[0].active_layer = "1/0"' "$SPECS/erc-supply-spec.pll_loop_filter.json" \
  > "${TMPDIR:-/tmp}/erc-loop_filter-deckform.json"
"$KLT" erc "$GDS/pll_loop_filter.gds" "${TMPDIR:-/tmp}/erc-loop_filter-deckform.json" \
  --top pll_loop_filter --deck sg13cmos5l --format json \
  > "$REC/erc.deckform-error.pll_loop_filter.json" 2>&1 || rc=$?   # the error envelope goes to stderr
echo "pll_loop_filter (MOS-block form, expected to error): exit $rc"
[ "$rc" -eq 1 ] || { echo "expected exit 1 from the gate-less deck form" >&2; exit 1; }
run loop_filter

sha256sum "$GDS"/pll_{pfd,cp,loop_filter,vco,lock_detector}.gds \
  "$SPECS"/erc-supply-spec.pll_{pfd,cp,loop_filter,vco,lock_detector}.json
