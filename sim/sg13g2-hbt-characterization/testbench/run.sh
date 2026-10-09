#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-hbt-characterization/testbench/run.sh (issue #181)
#
# Reproduces RECORD-001.  There is deliberately NO shell loop over corners: every
# grid is a `klt sim` request (../requests/*.json) and goes to the batch fleet
# (KLT_SIM_BACKEND=batch on dispatch workers).  Run from this directory.
#
#   python3 gen.py        # regenerates ../requests/*.json and tb_*.sp
#
# Client pin: RECORD-001 used klayout-tools 0.6.0 as the client, because the
# 0.7.0 client is refused by the fleet runner (runner 0.5.0/0.6.0 image;
# upstream 2AMLogic/klayout-tools#2948).  Use a throwaway venv, not the host tool:
#   uv venv .venv && uv pip install --python .venv/bin/python "klayout-tools==0.6.0"
set -euo pipefail
KLT="${KLT:-klt}"
OUT="${OUT:-$(mktemp -d)}"
cd "$(dirname "${BASH_SOURCE[0]}")/../requests"

$KLT sim -o "$OUT/hbt_ro" hbt_ro.request.json --format json > "$OUT/hbt_ro.json"      # 9 corners, batch
$KLT sim -o "$OUT/hbt_mm" hbt_mm.request.json --format json > "$OUT/hbt_mm.json"      # 9 corners x 50 MC, batch

# CMOS leg: PSP103 is OSDI-only and the batch runner has no OSDI objects, so the
# batch grids (cmos_ro / cmos_mm .request.json) fail with "Unable to find definition
# of model ...psp103va".  Only the single-corner local probe is runnable on a
# dispatch worker:
$KLT sim --backend local -o "$OUT/cmos_nom" cmos_ro_nominal.request.json --format json > "$OUT/cmos_ro_nominal.json"

echo "reports in $OUT; copy to ../corners/reports/ and run python3 analyze.py"
