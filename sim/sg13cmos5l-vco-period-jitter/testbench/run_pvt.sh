#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-vco-period-jitter/testbench/run_pvt.sh
# (issue #518 steps 4-5: the seeded PVT campaign and the row-12
# supply-ripple units)
#
# Drives the ladder the issue's step-6 park path sanctions, in order:
#
#   1. per-operating-point calibration on the batch fleet (bias .op decks
#      first, then the noise/ac pair at each measured VBP/VBN), writing
#      ../corners/calibration_{bias_,}pvt.csv + campaign_sigma.csv via
#      `extract.py calset` (which fail-closes on any non-passing deck and
#      cross-checks the reference point against RECORD-001's committed
#      calibration);
#   2. the structured corner-matrix requests (gen_campaign.py --phase pvt):
#      12 seeded campaign units + 6 row-12 supply-ripple units + the
#      1-unit probe;
#   3. the 1-unit fleet probe FIRST (confirm the collected report carries
#      environment.transient_noise.seed), then the grid as one --batch-set;
#   4. `extract.py campaign` / `extract.py ripple` -> ../corners/
#      {pvt_jitter,ripple}.csv with every unit's seed echo verified.
#
# Every klt sim batch call passes --wait-for-capacity 600 (host rule).  A
# fleet refusal or a runner that drops options.transient_noise_seed is
# captured to ../corners/fleetgap_probe.txt and FAILS the run (an
# unseeded campaign is not citable evidence); do not work around it
# locally.
#
#   export PINNED_PDK=$HOME/share/pdk/ihp-sg13cmos5l   # the PDK-PIN tree
#   ./run_pvt.sh [--skip-cal] [--skip-probe-local]
#
# --skip-cal reuses the committed ../corners/campaign_sigma.csv (the
# calibration below already ran and is committed); --skip-probe-local
# skips the local method-bridge check.  run.sh (the local method replay)
# is untouched by this script.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
GEN="$HERE/gen_campaign.py"
EXTRACT="$HERE/extract.py"
: "${PINNED_PDK:?set PINNED_PDK to the ihp-sg13cmos5l tree at the sim/README.md PDK-PIN revision}"
KLT="${KLT:-klt}"

SKIP_CAL=0; SKIP_LOCAL=0
for a in "$@"; do
  case "$a" in
    --skip-cal) SKIP_CAL=1 ;;
    --skip-probe-local) SKIP_LOCAL=1 ;;
    *) echo "run_pvt.sh: unknown arg $a" >&2; exit 2 ;;
  esac
done

WORK="$WORK" # scratch under the preamble's mktemp trap

fleet_fail() {
  {
    echo "fleet gap captured $(date -u +%Y-%m-%dT%H:%M:%SZ):"
    echo "client klt $($KLT --version 2>/dev/null | head -1)"
    tail -40 "$1"
  } >> "$CORNERS/fleetgap_probe.txt"
  echo "FLEET GAP: see $CORNERS/fleetgap_probe.txt (appended)" >&2
  exit 1
}

if [ "$SKIP_CAL" -eq 0 ]; then
  # -- 1a. bias-only calibration pass (deck list; models.pdk deliberately
  # absent so the default runner image is used -- the cmos5l image profile
  # is IAM-refused per sg13g2-pll#524 / 2am#7963, and the #318 staged
  # closure makes the runner's own PDK tree unnecessary anyway)
  python3 -I "$GEN" --phase cal "$WORK/cal1" --pinned-pdk "$PINNED_PDK"
  if ! $KLT sim "$WORK/cal1/request.json" --backend batch \
        --wait-for-capacity 600 -o "$WORK/cal1/out" --format json \
        --report-out "$WORK/cal1/report.json" >"$WORK/cal1/submit.log" 2>&1; then
    fleet_fail "$WORK/cal1/submit.log"
  fi
  cp "$WORK/cal1/cal_meta.json" "$WORK/cal1/out/"
  python3 -I "$EXTRACT" calset "$WORK/cal1/out" "$WORK/cal1/report.json" "$CORNERS"

  # -- 1b. full calibration (noise + ac at the measured biases)
  python3 -I "$GEN" --phase cal "$WORK/cal2" --pinned-pdk "$PINNED_PDK" \
      --bias-csv "$CORNERS/calibration_bias_pvt.csv"
  if ! $KLT sim "$WORK/cal2/request.json" --backend batch \
        --wait-for-capacity 600 -o "$WORK/cal2/out" --format json \
        --report-out "$WORK/cal2/report.json" >"$WORK/cal2/submit.log" 2>&1; then
    fleet_fail "$WORK/cal2/submit.log"
  fi
  cp "$WORK/cal2/cal_meta.json" "$WORK/cal2/out/"
  python3 -I "$EXTRACT" calset "$WORK/cal2/out" "$WORK/cal2/report.json" "$CORNERS"
  # keep the committed redacted report current (RECORD-003 cites it)
  python3 - "$WORK/cal2/report.json" "$CORNERS/cal_report_pvt.json" <<'PY'
import json, sys, pathlib
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
def walk(o):
    if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
    if isinstance(o, list): return [walk(x) for x in o]
    if isinstance(o, str) and o.startswith("/tmp/"): return "OUTDIR"
    return o
dst.write_text(json.dumps(walk(json.loads(src.read_text())), indent=1) + "\n")
PY
fi

# -- 2. the structured requests
python3 -I "$GEN" --phase pvt "$WORK/pvt" --pinned-pdk "$PINNED_PDK" \
    --sigma-csv "$CORNERS/campaign_sigma.csv"

# -- 3a. local method-bridge probe (single corner, local backend -- host
# rule): the structured path at RECORD-001's reference point must
# reproduce the committed ring_s42_t10p row and echo seed 42
if [ "$SKIP_LOCAL" -eq 0 ]; then
  python3 - "$WORK/pvt/probe/request.json" > "$WORK/pvt/probe/local.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
r["backend"] = "local"
r["options"]["ngspice_init"] = ["set numdgt=12"]   # single-threaded: the
r.pop("batch", None)                               # bit-identity bridge
json.dump(r, sys.stdout, indent=2)
PY
  $KLT sim "$WORK/pvt/probe/local.json" --backend local \
      -o "$WORK/pvt/probe-local-out" --format json \
      --report-out "$WORK/pvt/probe-local.report.json"
  # partial-by-design: writes to the scratch tree, never ../corners
  python3 -I "$EXTRACT" campaign --allow-partial "$WORK/pvt/units.csv" \
      "$WORK/pvt/probe-local.report.json" "$WORK/bridge-check" && \
      echo "local bridge probe: seed echo + extraction OK" || \
      { echo "local bridge probe failed" >&2; exit 1; }
fi

# -- 3b. the 1-unit fleet probe: MUST carry the seed echo or we stop
if ! $KLT sim "$WORK/pvt/probe/request.json" --backend batch \
      --wait-for-capacity 600 -o "$WORK/pvt/probe-out" --format json \
      --report-out "$WORK/pvt/probe.report.json" >"$WORK/pvt/probe.submit.log" 2>&1; then
  fleet_fail "$WORK/pvt/probe.submit.log"
fi

# -- 3c. the grid: every remaining member as one batch-set
set -- "$WORK"/pvt/*/request.json
members=""
for r in "$@"; do
  [ "$(basename "$(dirname "$r")")" = "probe" ] && continue
  members="$members $r"
done
# shellcheck disable=SC2086
if ! $KLT sim --batch-set $members --wait-for-capacity 600 \
      --capacity-retries 3 --format json \
      --report-out "$WORK/pvt/pvt.report.json" >"$WORK/pvt/grid.submit.log" 2>&1; then
  fleet_fail "$WORK/pvt/grid.submit.log"
fi

# -- 4. reduction
python3 -I "$EXTRACT" campaign "$WORK/pvt/units.csv" \
    "$WORK/pvt/probe.report.json" "$WORK/pvt/pvt.report.json" "$CORNERS"
python3 -I "$EXTRACT" ripple "$WORK/pvt/units.csv" \
    "$WORK/pvt/pvt.report.json" "$CORNERS"
echo "wrote pvt_jitter.csv and ripple.csv to $CORNERS" >&2
