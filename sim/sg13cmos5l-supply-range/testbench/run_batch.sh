#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-supply-range/testbench/run_batch.sh (issue #187)
# Submits the supply-range grid (supply_grid.py) to the batch fleet, one `klt sim`
# per block, then reduces to ../corners/*.csv.  Never calls ngspice directly; a
# refused submit is reported, not run locally.
#   ./run_batch.sh --dry-run    # validate the three requests only
#   ./run_batch.sh              # full grid
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORNERS="$(cd "$HERE/.." && pwd)/corners"
WORKDIR="${WORKDIR:-$(mktemp -d -t supply-range.XXXXXX)}"
echo "[batch] WORKDIR=$WORKDIR" >&2
for b in vco lockdet divider; do
  python3 -I "$HERE/supply_grid.py" gen "$WORKDIR" "$b"
  d="$WORKDIR/$b"
  if [ "${1:-}" = "--dry-run" ]; then
    klt sim --dry-run --backend batch "$d/request.json" -o "$d/dry" --format json >"$d/dryrun.json"; continue
  fi
  set +e
  klt sim --backend batch --wait-for-capacity 600 "$d/request.json" -o "$d/out" \
    --format json --report-out "$d/report.json" >"$d/stdout.json" 2>"$d/stderr.log"
  rc=$?; set -e
  grep -o 'klt-sim-[0-9a-f]*' "$d/stderr.log" | head -1 | sed "s/^/[batch] $b job /" >&2
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 4 ]; then
    echo "ERROR: batch submit failed for $b (rc=$rc); report it, do NOT run locally." >&2; tail -5 "$d/stderr.log" >&2; exit "$rc"
  fi
done
[ "${1:-}" = "--dry-run" ] || python3 -I "$HERE/supply_grid.py" reduce "$WORKDIR" "$CORNERS"
