#!/usr/bin/env bash
# Submit one converted request dir to the batch fleet (never local), write
# report + stdout/stderr logs. usage: submit.sh REQDIR OUTDIR REPORT LOGPREFIX
set -uo pipefail
REQ="${1:?}"; OUT="${2:?}"; REPORT="${3:?}"; LOG="${4:?}"
cd "$REQ" && klt sim --backend batch --wait-for-capacity 600 request.json \
  -o "$OUT" --report-out "$REPORT" --format json > "$LOG.stdout" 2> "$LOG.stderr"
echo "submit rc=$?"
