#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-vco-output-levels/testbench/run.sh
# (issue #190, spec row 14 output levels / drive, T1 item 5)
#
# Expresses the 54-point grid as ONE `klt sim` deck-list request and submits it
# (batch fleet by default; host policy forbids hand-launched ngspice grids),
# then extracts ../corners/results.csv.  Nothing here loops over ngspice.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   ./run.sh [WORKDIR]                  # BACKEND=local only for a debug probe
#
# Requires: klt on PATH, python3.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
WORK="${1:-$(mktemp -d)}"
BACKEND="${BACKEND:-batch}"

python3 -I "$HERE/gen_requests.py" "$WORK"
klt sim "$WORK/request.json" --backend "$BACKEND" --wait-for-capacity 600 \
    -o "$WORK/out" --format json --report-out "$WORK/report.json"
python3 -I "$HERE/extract.py" "$WORK/out" "$WORK/decks.sha256.csv" "$RECORD_DIR/corners/results.csv"
cp "$WORK/decks.sha256.csv" "$RECORD_DIR/corners/decks.sha256.csv"
echo "report: $WORK/report.json" >&2
