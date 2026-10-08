#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-klt-pex-signoff/run-klt-pex.sh (issue #152)
#
# Runs `klt pex` (single nominal corner, --backend local: one corner is a
# single-unit run that stays local; multi-corner grids go through `klt sim`
# corners/monte_carlo to the batch fleet and are NOT launched from here) for
# one block against the committed layout record, and writes the verbatim JSON
# envelope to reports/pex.<block>.json -- the file manifests/sg13g2-pll.json
# cites as item 7.
#
#   PDK_ROOT=<parent of ihp-sg13cmos5l> ./run-klt-pex.sh <block>
#   blocks: pfd cp loop_filter vco divider_chain
set -euo pipefail
: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
REC="layout/sg13cmos5l-pll/reports/20261003-183059-dc5644a"
block="${1:?block}"
case "$block" in
  pfd)           reqs=(pfd);              pins=DN,FB,REF,UP,VDD,VSS ;;
  cp)            reqs=(cp_up cp_dn);      pins=DN,IBN,IBP,ICN,ICP,UP,VDD,VOUT,VSS ;;
  loop_filter)   reqs=(loop_filter);      pins=NZ,VCTRL,VSS ;;
  vco)           reqs=(vco);              pins=B0,B1,CLK,GND_VCO,VCTRL,VDD_VCO ;;
  divider_chain) reqs=(divider_chain);    pins=CKIN,CKIN_VCO,DIVOUT,FB,P0,P1,P2,P3,P4,P5,VDD_DIV,VSS ;;
  *) echo "unknown block $block" >&2; exit 2 ;;
esac
# The schematic leg dut/pll_<block>.schematic.sp is regenerated from the design
# netlist by flatten-schematic.py (see the README); it is committed, not rebuilt here.
args=(); for r in "${reqs[@]}"; do args+=("sim/sg13cmos5l-klt-pex-signoff/requests/$r.request.json"); done
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
cd "$REPO"
klt pex "$REC/pll_$block.gds" "${args[@]}" --deck sg13cmos5l --top "pll_$block" \
  --pdk ihp-sg13cmos5l --pdk-root "$PDK_ROOT" --pins "$pins" --backend local \
  --outdir "$work" -o "$work/pll_$block.pex.spice" --format json \
  > "sim/sg13cmos5l-klt-pex-signoff/reports/pex.$block.json"
