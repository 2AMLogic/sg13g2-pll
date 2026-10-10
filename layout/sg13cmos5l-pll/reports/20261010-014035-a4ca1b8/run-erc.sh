#!/usr/bin/env bash
# Reproduce this record's five analog `klt erc` supply reports (issue #195),
# against the GDS of layout record 20261010-012952-a4ca1b8 (the DR-010 cp).
#
# Run from the repository root with two pinned klt builds, each installed from
# a clean clone into a throwaway venv (never the host klt):
#
#   KLT     = the grading build, klayout-tools @ e6284fbe62e25d9b293eed07889cb80a0b87e2f4
#             with klayout==0.30.10 (what .github/workflows/signoff.yml installs).
#             This build runs pfd, loop_filter, vco and lock_detector, with the
#             same specs and form as record 20261008-230856-cd95c87.
#   KLT_CP  = klayout-tools @ 1eb3e4bfd0f5957bb643fdecfde26c7badea2c67 with
#             klayout==0.30.12 (the build behind the item-7 klt pex envelopes).
#             This build runs cp, because cp's PSRC well needs the box well
#             selectors (klayout-tools#2540), which the grading build lacks. See
#             layout/sg13cmos5l-pll/erc-supply-spec.pll_cp.md.
#
#   git clone https://github.com/2AMLogic/klayout-tools /tmp/klt
#   git -C /tmp/klt checkout e6284fbe62e25d9b293eed07889cb80a0b87e2f4
#   uv venv /tmp/klt-venv && VIRTUAL_ENV=/tmp/klt-venv uv pip install "klayout==0.30.10" /tmp/klt
#   git clone /tmp/klt /tmp/klt-cp && git -C /tmp/klt-cp checkout 1eb3e4bfd0f5957bb643fdecfde26c7badea2c67
#   uv venv /tmp/klt-cp-venv && VIRTUAL_ENV=/tmp/klt-cp-venv uv pip install "klayout==0.30.12" /tmp/klt-cp
#   KLT=/tmp/klt-venv/bin/klt KLT_CP=/tmp/klt-cp-venv/bin/klt \
#     layout/sg13cmos5l-pll/reports/20261010-014035-a4ca1b8/run-erc.sh
#
# Exit 4 from `klt erc` is expected. It means the antenna half is not_checked
# because there is no sg13cmos5l antenna table (klayout-tools#1994/#2179). The
# connectivity verdict is in `erc_status`. Exit 1/2 is an error and stops the
# script, except for the deliberately recorded error and negative runs below.
set -euo pipefail

KLT="${KLT:?set KLT to the grading build (e6284fbe62e2)}"
KLT_CP="${KLT_CP:?set KLT_CP to klayout-tools 1eb3e4bfd0f5}"
REC=layout/sg13cmos5l-pll/reports/20261010-014035-a4ca1b8
GDS=layout/sg13cmos5l-pll/reports/20261010-012952-a4ca1b8
SPECS=layout/sg13cmos5l-pll
NEG="${TMPDIR:-/tmp}/erc-cp-negative"
mkdir -p "$NEG"

"$KLT" --version
"$KLT_CP" --version

run() {  # run <klt> <block> [extra klt erc args...]
  local klt="$1" block="$2"; shift 2
  local rc=0
  "$klt" erc "$GDS/pll_${block}.gds" "$SPECS/erc-supply-spec.pll_${block}.json" \
    --top "pll_${block}" "$@" --format json > "$REC/erc.supply-spec.pll_${block}.json" || rc=$?
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 4 ]; then
    echo "klt erc failed on pll_${block} (exit $rc)" >&2
    exit 1
  fi
  echo "pll_${block}: exit $rc"
}

# The three unchanged MOS blocks, at the grading build (gate area = poly & Activ,
# and the curated deck's rppd/rhigh/rsil bodies carved out of the GatPoly role).
run "$KLT" pfd --deck sg13cmos5l
run "$KLT" vco --deck sg13cmos5l
run "$KLT" lock_detector --deck sg13cmos5l

# cp, the DR-010 two-OTA dump buffer, uses the box-selected well ties.
run "$KLT_CP" cp --deck sg13cmos5l

# loop_filter (passive) is recorded exactly as in 20261008-230856-cd95c87:
# klt refuses the MOS form (exit 1, klayout-tools#2896), and that refusal is
# kept as friction evidence. The block is then run in its spec's no-deck form.
rc=0
jq '.stackup[0].active_layer = "1/0"' "$SPECS/erc-supply-spec.pll_loop_filter.json" \
  > "${TMPDIR:-/tmp}/erc-loop_filter-deckform.json"
"$KLT" erc "$GDS/pll_loop_filter.gds" "${TMPDIR:-/tmp}/erc-loop_filter-deckform.json" \
  --top pll_loop_filter --deck sg13cmos5l --format json \
  > "$REC/erc.deckform-error.pll_loop_filter.json" 2>&1 || rc=$?   # the error envelope goes to stderr
echo "pll_loop_filter (MOS-block form, expected to error): exit $rc"
[ "$rc" -eq 1 ] || { echo "expected exit 1 from the gate-less deck form" >&2; exit 1; }
run "$KLT" loop_filter

# --- cp negative runs: evidence that the cp tie declaration is falsifiable ---
negative() {  # negative <klt> <spec> <out-name> <expected exit>
  local klt="$1" spec="$2" out="$3" want="$4" rc=0
  "$klt" erc "$GDS/pll_cp.gds" "$spec" --top pll_cp --deck sg13cmos5l --format json \
    > "$REC/$out" 2>&1 || rc=$?
  echo "negative $out: exit $rc"
  [ "$rc" -eq "$want" ] || { echo "negative $out: expected exit $want" >&2; exit 1; }
}
# (a) The pre-#195 two-tie cp spec (the committed spec at a4ca1b8), run at the
#     grading build on the new GDS. Expected result: one erc.missing_tie on the
#     PSRC well against VDD.
git show a4ca1b8:layout/sg13cmos5l-pll/erc-supply-spec.pll_cp.json > "$NEG/old-two-tie.json"
negative "$KLT" "$NEG/old-two-tie.json" erc.negative-old-two-tie-spec.pll_cp.json 3
# (b) The current spec with the PSRC box moved onto a VDD well
#     (cp_pfet_w6_l0p3). Expected result: both box-selected ties report
#     erc.missing_tie.
jq '(.ties[0].well_excludes_boxes, .ties[1].well_requires_boxes) = [[192.6, 0.34, 208.36, 4.18]]' \
  "$SPECS/erc-supply-spec.pll_cp.json" > "$NEG/box-on-vdd-well.json"
negative "$KLT_CP" "$NEG/box-on-vdd-well.json" erc.negative-box-on-vdd-well.pll_cp.json 3
# (c) The PSRC box moved off every well. Expected result: both box-selected
#     ties are skipped (degenerate_well_selection), and nwell_tap, which now
#     excludes nothing, reports the PSRC well against VDD.
jq '(.ties[0].well_excludes_boxes, .ties[1].well_requires_boxes) = [[600, 0.34, 610, 4.38]]' \
  "$SPECS/erc-supply-spec.pll_cp.json" > "$NEG/box-on-no-well.json"
negative "$KLT_CP" "$NEG/box-on-no-well.json" erc.negative-box-on-no-well.pll_cp.json 3

sha256sum "$GDS"/pll_{pfd,cp,loop_filter,vco,lock_detector}.gds \
  "$SPECS"/erc-supply-spec.pll_{pfd,cp,loop_filter,vco,lock_detector}.json
