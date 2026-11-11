#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/run_rerun328.sh
# (issue #328, Part of #257)
#
# Batch-fleet driver for the lock_detector campaign run.sh runs locally.  Same
# grid, same templates, same reducers -- expressed as three `klt sim`
# deck-list requests (see batch_grid_rerun328.py's header for why deck-list rather than
# corner requests, and for the phase dependencies).  Nothing here ever calls
# ngspice directly; every simulation goes through `klt sim --backend batch`.
#
# Usage (no PDK_ROOT needed; decks carry the runner's own $PDK_ROOT):
#   ./run_rerun328.sh --dry-run             # generate + `klt sim --dry-run` phase0 only
#   ./run_rerun328.sh                       # RECORD-002's full grid -> corners/*_rerun328.*
#
# Writes only the `rerun328` suffix; run.sh's outputs, RECORD-001..007's files and the snapshots are never touched.
#
# WORKDIR (default: a fresh mktemp -d, kept) holds the generated requests,
# decks, reports and raw stdout.  Phases are resumable: set WORKDIR to a prior
# directory and a phase whose report.json exists with status pass is skipped.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORNERS="$(cd "$HERE/.." && pwd)/corners"
WAIT_FOR_CAPACITY="${WAIT_FOR_CAPACITY:-600}"
WORKDIR="${WORKDIR:-$(mktemp -d -t lockdet-batch.XXXXXX)}"
NOM=()
DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; fi
echo "[batch] WORKDIR=$WORKDIR" >&2

gen() { python3 -I "$HERE/batch_grid_rerun328.py" gen "$WORKDIR" "$1" "${NOM[@]}"; }

submit() {  # submit <request dir>  -> runs one klt sim, never falls back to local
  local d="$1"
  if [ "$DRY" = 1 ]; then
    klt sim --dry-run --backend batch "$d/request.json" -o "$d/out" --format json >"$d/dryrun.json"
    echo "[batch] dry-run OK: $d" >&2
    return 0
  fi
  if [ -s "$d/report.json" ] && [ "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$d/report.json")" = pass ]; then
    echo "[batch] $d already complete, skipped" >&2; return 0
  fi
  # exit 4 = some unit errored (handled by the trtol retry below); anything else >0 is fatal.
  # A refused submit (batch_no_capacity after the wait, etc.) is reported, NOT run locally.
  set +e
  klt sim --backend batch --wait-for-capacity "$WAIT_FOR_CAPACITY" "$d/request.json" \
    -o "$d/out" --format json --report-out "$d/report.json" >"$d/stdout.json" 2>"$d/stderr.log"
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 4 ]; then
    echo "ERROR: klt sim batch submit failed (rc=$rc) for $d -- see $d/stderr.log." >&2
    echo "       Report this error; do NOT fall back to running the grid locally." >&2
    tail -5 "$d/stderr.log" >&2 || true
    exit "$rc"
  fi
  grep -o '"job_id": *"[^"]*"' "$d/report.json" | head -1 | sed 's/^/[batch] /' >&2 || true
}

phase() {  # phase <name>: gen, submit, one trtol=1 retry for errored units
  gen "$1"
  submit "$WORKDIR/$1"
  if [ "$DRY" = 1 ]; then return 0; fi
  python3 -I "$HERE/batch_grid_rerun328.py" retry "$WORKDIR" "$1"
  if [ -s "$WORKDIR/$1_retry/request.json" ]; then
    submit "$WORKDIR/$1_retry"
    if ! python3 -c "import json,sys;sys.exit(0 if json.load(open(sys.argv[1]))['status']=='pass' else 1)" \
         "$WORKDIR/$1_retry/report.json"; then
      echo "ERROR: unit(s) failed even with trtol=1 in $1 -- see $WORKDIR/$1_retry/report.json" >&2
      exit 1
    fi
  fi
}

phase phase0
if [ "$DRY" = 1 ]; then
  echo "[batch] --dry-run: later phases depend on phase0/1 results and are generated only after them." >&2
  exit 0
fi
phase phase1
phase phase2
python3 -I "$HERE/batch_grid_rerun328.py" reduce "$WORKDIR" "$CORNERS" "${NOM[@]}"
echo "[batch] done; evidence in $WORKDIR, CSVs in $CORNERS" >&2
