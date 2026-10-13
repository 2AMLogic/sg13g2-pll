#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-klt-pex-signoff/run-klt-pex-rerun255.sh (issue #255)
#
# Reruns RECORD-001's nominal single-corner `klt pex` flow on its reconstructed
# original inputs (layout record 20261003-183059-dc5644a; dut/ + requests/ +
# run-klt-pex.sh exactly as of commit e56e14a) and writes the envelopes to NEW
# paths: reports/rerun255/pex.<block>.json. It never touches reports/pex.*.json.
#
#   PDK_ROOT=<parent of ihp-sg13cmos5l> [KLT=<klt>] ./run-klt-pex-rerun255.sh <block>
#   blocks: pfd cp loop_filter vco divider_chain
# One block = one nominal corner (cp = two legs) = single-unit, --backend local.
set -euo pipefail
: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
KLT="${KLT:-klt}"
BASE=e56e14a   # the commit that added RECORD-001, its reports and its inputs
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
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
mkdir -p "$work/inputs" "$HERE/reports/rerun255"
git -C "$REPO" archive "$BASE" sim/sg13cmos5l-klt-pex-signoff/dut sim/sg13cmos5l-klt-pex-signoff/requests | tar -x -C "$work/inputs"
I="$work/inputs/sim/sg13cmos5l-klt-pex-signoff"
args=(); for r in "${reqs[@]}"; do args+=("$I/requests/$r.request.json"); done
cd "$REPO"
"$KLT" pex "$REC/pll_$block.gds" "${args[@]}" --deck sg13cmos5l --top "pll_$block" \
  --pdk ihp-sg13cmos5l --pdk-root "$PDK_ROOT" --pins "$pins" --backend local \
  --outdir "$work/out" -o "$work/pll_$block.pex.spice" --format json \
  > "$HERE/reports/rerun255/pex.$block.json"
