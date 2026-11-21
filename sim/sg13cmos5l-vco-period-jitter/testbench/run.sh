#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-vco-period-jitter/testbench/run.sh
# (issue #518, Part of #16 -- row 8 method gap, R-7)
#
# Builds and runs the transient-noise period-jitter METHOD bench this
# record's ../records/RECORD-001 describes, at ONE corner
# (mos_tt/res_typ/27C, band 00, VCTRL=1.5V): the noise-injection
# calibration against .noise on a stable single-stage operating point, the
# end-to-end PSD validation of the injected source, the four method
# validation controls (noise-off, timestep halving, amplitude scaling, seed
# repeat), and the first local period-jitter measurement over 1000 periods.
# The PVT campaign and the row-12 supply-ripple unit are deliberately NOT
# run here: the pinned klt cannot pin and report the trrandom seed for a
# batch run (2AMLogic/klayout-tools#5772), and the issue parks this bench
# on that gap -- see RECORD-001 "Park".  A single-unit batch probe
# (default on; SKIP_SEEDGAP_PROBE=1 to skip) demonstrates that gap with a
# real fleet job id.
#
# All ngspice work runs through `klt sim` deck-list requests (no
# hand-launched ngspice loops); everything except the one-unit fleet probe
# runs on the local backend, sequentially.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Writes: ../corners/{calibration_bias,calibration_noise,calibration_fit,
# calibration_psd,period_jitter,crossing_digest,controls}.csv plus the
# redacted klt reports local_report.json / seedgap_report.json.
# extract.py exits non-zero if any validation control fails.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
GEN="$HERE/gen_decks.py"
EXTRACT="$HERE/extract.py"

phase() {
  local name="$1"; shift
  python3 -I "$GEN" --phase "$name" "$WORK/$name" "$@"
  klt sim "$WORK/$name/request.json" --backend local \
      -o "$WORK/$name/out" --format json --report-out "$WORK/$name/report.json"
}

redact() {
  # replace scratch absolute paths with the literal OUTDIR (duty-cycle
  # bench RECORD-002 convention) so the committed report carries no
  # host-private path
  python3 - "$1" "$2" <<'PY'
import sys, pathlib, re, json
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
def walk(o):
    if isinstance(o, dict):
        return {k: walk(v) for k, v in o.items()}
    if isinstance(o, list):
        return [walk(x) for x in o]
    if isinstance(o, str) and o.startswith("/tmp/"):
        return "OUTDIR"
    return o
dst.write_text(json.dumps(walk(json.loads(src.read_text())), indent=1) + "\n")
PY
}

# Phase 1: vco_bias operating point -> VBP/VBN
phase bias
read -r VBP VBN < <(python3 -I "$EXTRACT" bias "$WORK/bias" "$CORNERS")
echo "VBP=$VBP VBN=$VBN (from vco_bias .op)" >&2

# Phase 2: calibration (.op+.noise, |Z_out| .ac, DC transfer) -> sigma
phase cal --vbp "$VBP" --vbn "$VBN"
SIGMA="$(python3 -I "$EXTRACT" cal "$WORK/cal" "$CORNERS")"
echo "calibrated sigma=$SIGMA A (ts=10ps aggregate source)" >&2

# Phase 3: PSD validation + the ring units + the controls
phase main --vbp "$VBP" --vbn "$VBN" --sigma "$SIGMA"
# redact BEFORE extract: an extract failure must not take the report with
# it (the WORK trap deletes the scratch tree on exit either way)
redact "$WORK/main/report.json" "$CORNERS/local_report.json"
python3 -I "$EXTRACT" main "$WORK/main" "$CORNERS"

# One-unit batch probe: the primary seed-42 deck in fleet form, submitted
# to the batch backend so the recorded failure names real job ids.  Its
# numbers are NOT used as jitter evidence (see RECORD-001 "Park").  A fleet
# refusal (IAM/capacity) is itself evidence, not a run failure: it is
# captured to ../corners/seedgap_probe.txt and does not abort the run.
if [ -z "${SKIP_SEEDGAP_PROBE:-}" ]; then
  python3 -I "$GEN" --phase seedgap "$WORK/seedgap" \
      --vbp "$VBP" --vbn "$VBN" --sigma "$SIGMA"
  if klt sim "$WORK/seedgap/request.json" --backend batch --wait-for-capacity 600 \
      -o "$WORK/seedgap/out" --format json \
      --report-out "$WORK/seedgap/report.json" >"$WORK/seedgap/submit.log" 2>&1; then
    redact "$WORK/seedgap/report.json" "$CORNERS/seedgap_report.json"
    echo "seed-gap probe report: $CORNERS/seedgap_report.json" >&2
  else
    {
      echo "seed-gap batch probe submit failed (captured $(date -u +%Y-%m-%dT%H:%M:%SZ)):"
      echo "client klt $(klt --version 2>/dev/null | head -1)"
      tail -40 "$WORK/seedgap/submit.log"
    } >> "$CORNERS/seedgap_probe.txt"
    echo "seed-gap probe submit FAILED (fleet); appended to $CORNERS/seedgap_probe.txt" >&2
  fi
fi

echo "wrote CSVs to $CORNERS" >&2
