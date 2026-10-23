#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-pfd-reset-parity/testbench/run.sh (issue #283)
#
# Reproduces RECORD-001.  No shell loop over corners: the 4 PVT grids (before/after
# x reflead/fblead, 3 process x 3 temperature each) are `klt sim` requests and go to
# the batch fleet as one --batch-set.
#
#   python3 gen.py        # regenerates ../requests/*.json and tb_*.sp
set -euo pipefail
KLT="${KLT:-klt}"
OUT="${OUT:-$(mktemp -d)}"
cd "$(dirname "${BASH_SOURCE[0]}")/../requests"
$KLT sim --batch-set before_reflead_pvt.request.json before_fblead_pvt.request.json \
    after_reflead_pvt.request.json after_fblead_pvt.request.json \
    -o "$OUT" --format json > "$OUT/batch.json"
echo "reports in $OUT; copy to ../corners/reports/ and run python3 analyze.py"
