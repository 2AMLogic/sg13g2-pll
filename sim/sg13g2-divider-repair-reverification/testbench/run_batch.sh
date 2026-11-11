#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-divider-repair-reverification/testbench/run_batch.sh
# (issue #235, RECORD-002).  Reproduces RECORD-002 on the batch fleet.  No shell
# loop over corners: every grid is a `klt sim` request (../requests/*.request.json)
# and the whole set goes to the fleet as one --batch-set.  Never hand-launches
# ngspice.  RECORD-001's run.sh is untouched.
#
#   python3 gen_batch.py            # regenerates ../requests/*.json + bench bodies
#   OUT=/some/dir ./run_batch.sh    # submit; then copy each <OUT>/set/<name>.request/report.json
#                                   # to ../corners/reports/<name>.klt-report.json and run
#   python3 analyze_batch.py        # writes ../corners/*_r002.csv, prints the RECORD-001 comparison
set -euo pipefail
KLT="${KLT:-klt}"
OUT="${OUT:-$(mktemp -d)}"
cd "$(dirname "${BASH_SOURCE[0]}")/../requests"
# probe first (one corner), then the set:
$KLT sim probe_func_tt27.request.json --backend batch --wait-for-capacity 600 -o "$OUT/probe" --format json > "$OUT/probe.json"
$KLT sim --batch-set $(ls *.request.json | grep -v '^probe_') --max-in-flight 4 \
    --capacity-retries 3 --wait-for-capacity 600 -o "$OUT/set" --format json > "$OUT/batch.json"
echo "reports in $OUT" >&2
