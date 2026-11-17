#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-pfd-input-threshold/testbench/run_batch.sh (issue #403)
# Submits the REF input-threshold grid (threshold_grid.py) to the batch fleet,
# sharded into 6 deck-list requests (one per PVT-corner group; threshold_grid.py
# writes request.shard<k>.json) so no single job sits inside the ~1 h
# spot-reclamation window, then reduces to ../corners/results.csv.
# Never calls ngspice directly; a refused submit is reported, not run locally.
#   ./run_batch.sh --dry-run    # validate the request only
#   ./run_batch.sh              # full grid (9 DC decks + 72 edge decks)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORNERS="$(cd "$HERE/.." && pwd)/corners"
WORKDIR="${WORKDIR:-$(mktemp -d -t pfd-threshold.XXXXXX)}"
echo "[batch] WORKDIR=$WORKDIR" >&2
python3 -I "$HERE/threshold_grid.py" gen "$WORKDIR"
d="$WORKDIR/pfdthr"
if [ "${1:-}" = "--dry-run" ]; then
  klt sim --dry-run --backend batch "$d/request.json" -o "$d/dry" --format json >"$d/dryrun.json"
else
  set +e
  for shard in "$d"/request.shard*.json; do
    base="$(basename "$shard" .json)"
    klt sim --backend batch --wait-for-capacity 600 "$shard" -o "$d/out" \
      --format json --report-out "$d/report.$base.json" \
      >"$d/$base.stdout.json" 2>"$d/$base.stderr.log" </dev/null
    rc=$?
    grep -o 'klt-sim-[0-9a-f]*' "$d/$base.stderr.log" | head -1 | sed "s/^/[batch] $base job /" >&2
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 4 ]; then
      echo "ERROR: batch submit failed for $base (rc=$rc); report it, do NOT run locally." >&2
      tail -5 "$d/$base.stderr.log" >&2; exit "$rc"
    fi
  done
  set -e
  python3 -I "$HERE/threshold_grid.py" reduce "$WORKDIR" "$CORNERS"
fi
