#!/usr/bin/env bash
# sg13g2-pll :: export the xschem schematic hierarchies under design/sg13cmos5l/
# to SPICE, on the SG13CMOS5L PDK -- the parallel-PDK port (issue #22, Part of
# #16, Chipalooza Challenge #6). Sibling of design/netlist.sh; SG13G2's own
# script/schematics/netlists are untouched by this port (parallel target, not
# a replacement -- see design/README.md "SG13CMOS5L port").
#
#   ./design/sg13cmos5l/netlist.sh                  # regenerate netlist/*.spice
#   ./design/sg13cmos5l/netlist.sh --check          # regenerate into a temp dir and diff
#   ./design/sg13cmos5l/netlist.sh --top <block>    # regenerate one committed block
#
# One exporter for every block named in spec/porting-plan.md Sec1.4: pfd, cp,
# loop_filter, vco, divider_chain, lock_detector. Each top is netlisted with
# its full hierarchy into one self-contained file under
# design/sg13cmos5l/netlist/, which is committed -- same fleet convention as
# design/netlist.sh (see that script's own header for the full rationale this
# one summarizes).
#
# `--check` regenerates into a temp dir and diffs against the committed copy
# instead of writing, so a stale committed netlist fails loudly -- this is
# the "regenerated on design change, not a one-off drop" reproducibility bar
# issue #7 / docs/design-evidence-tiers.md's T1 item 1 pass condition names.
#
# Requires: xschem on PATH, and the SG13CMOS5L PDK resolvable via PDK_ROOT/PDK
# (the same variables design/sg13cmos5l/xschemrc reads, matching `klt pdk
# find --pdk ihp-sg13cmos5l`).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The six blocks spec/porting-plan.md Sec1.4 names -- issue #7's own Test
# Plan requires every one of these to be represented, not a partial subset.
# Same set as design/netlist.sh -- the SG13CMOS5L port carries every block
# over (DR-003: no block is dropped by the device-swap surface).
BLOCKS=(pfd cp loop_filter vco divider_chain lock_detector)

# Expected `.subckt` set per top -- the connectivity guard below fails the
# run if any of these is missing from the corresponding export, catching a
# hierarchy that silently lost a branch. Identical to design/netlist.sh's own
# table: DR-003 Finding 1 means no leaf cell is added, renamed, or dropped by
# the SG13CMOS5L port.
expected_subckts() {
  case "$1" in
    pfd)            echo "pfd edgedet srlatch nand2_hv inv_hv inv2x_hv" ;;
    cp)             echo "cp cp_leg_n cp_leg_p cp_dumpbuf inv_hv" ;;
    loop_filter)    echo "loop_filter" ;;
    vco)            echo "vco vco_bias vco_stage inv2x_hv" ;;
    divider_chain)  echo "divider_chain div23_cell dff_tg_hv tgate_hv inv_hv nand2_hv nand3_hv nor2_hv" ;;
    lock_detector)  echo "lock_detector xor2_hv delaywin_hv nand2_hv inv_hv schmitt_hv" ;;
    *)              echo "" ;;
  esac
}

usage() {
  cat >&2 <<'EOF'
usage: sg13cmos5l/netlist.sh [--top <block>] [--check]

  (no args)       regenerate every committed export under
                  design/sg13cmos5l/netlist/
  --top <block>   restrict to one top (pfd, cp, loop_filter, vco,
                  divider_chain, lock_detector)
  --check         diff against the committed export, do not write
EOF
}

TOP=""
CHECK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --top)     TOP="${2:-}"
               [ -n "${TOP}" ] || { echo "ERROR: --top needs a value" >&2; usage; exit 2; }
               shift 2 ;;
    --top=*)   TOP="${1#--top=}"; shift ;;
    --check)   CHECK=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*)        echo "ERROR: unknown option '$1'" >&2; usage; exit 2 ;;
    *)         echo "ERROR: unexpected argument '$1'" >&2; usage; exit 2 ;;
  esac
done

command -v xschem >/dev/null 2>&1 || {
  echo "ERROR: xschem not found on PATH" >&2
  exit 1
}

XSCHEM_VERSION="$(xschem --no_x -q --version 2>/dev/null | head -1 || echo unknown)"

# ------------------------------------------------------------ shared check --
# Three cheap invariants applied to EVERY export: the expected .subckt set
# must exist, no .subckt HEADER may contain an auto-generated `netN` name
# (which would mean xschem could not resolve a label -- almost always a
# missing/shadowed XSCHEM_LIBRARY_PATH entry), and no pin may be reported
# "IS MISSING".
check_export() {
  local netlist="$1"; shift
  local cell
  for cell in "$@"; do
    grep -qiE "^\.subckt +${cell}( |$)" "${netlist}" || {
      echo "ERROR: .subckt ${cell} missing from ${netlist}" >&2
      exit 1
    }
  done
  if grep -iE "^\.subckt " "${netlist}" | grep -qE '\bnet[0-9]+\b'; then
    echo "ERROR: auto-generated net name in a .subckt port list -- xschem could" >&2
    echo "       not resolve a label symbol (check XSCHEM_LIBRARY_PATH)." >&2
    exit 1
  fi
  if grep -q "IS MISSING" "${netlist}"; then
    echo "ERROR: unconnected pin(s) reported by xschem:" >&2
    grep "IS MISSING" "${netlist}" >&2
    exit 1
  fi
}

# ------------------------------------------------------------- path stamps --
# xschem stamps the absolute filesystem path of every .sch/.sym it expands
# into a comment (`** sch_path: /abs/checkout/design/sg13cmos5l/foo.sch`).
# Rewriting those comment lines (and only those) to repo-relative form at
# write time keeps the committed bytes -- and any snapshot hash a future
# sim/ record takes of them -- independent of which checkout produced them.
normalize() {
  sed -E 's#^(\*\* (sch|sym)_path: ).*/design/sg13cmos5l/#\1design/sg13cmos5l/#' "$1" >"$2"
}

banner() {
  printf '%s\n' \
    "* sg13g2-pll :: $1 (SG13CMOS5L) -- generated by design/sg13cmos5l/netlist.sh from $1.sch" \
    "* xschem ${XSCHEM_VERSION}; do not edit by hand."
}

export_block() {
  local blk="$1" outdir="$2" work="$3"

  (cd "${HERE}" && xschem --no_x -n -s -q \
      --rcfile "${HERE}/xschemrc" -o "${work}" "${HERE}/${blk}.sch" >"${work}/${blk}.xschem.log" 2>&1) || true

  [ -f "${work}/${blk}.spice" ] || {
    echo "ERROR: xschem produced no netlist for ${blk} at ${work}/${blk}.spice" >&2
    echo "       see ${work}/${blk}.xschem.log" >&2
    exit 1
  }

  {
    banner "${blk}"
    # Promote the top cell's commented **.subckt / **.ends header to a real
    # one and drop the trailing .end, so the file is .include-able by a
    # future testbench.
    awk '
      /^\*\*\.subckt/ { sub(/^\*\*/, ""); print; next }
      /^\*\*\.ends/   { sub(/^\*\*/, ""); print; next }
      /^\.end$/       { next }
      { print }
    ' "${work}/${blk}.spice"
  } >"${work}/${blk}.raw.spice"

  normalize "${work}/${blk}.raw.spice" "${outdir}/${blk}.spice"

  # shellcheck disable=SC2046  # word splitting of the cell list is intended
  check_export "${outdir}/${blk}.spice" $(expected_subckts "${blk}")
}

SELECTED=("${BLOCKS[@]}")
if [ -n "${TOP}" ]; then
  found=0
  for blk in "${BLOCKS[@]}"; do
    [ "${blk}" = "${TOP}" ] && found=1
  done
  [ "${found}" -eq 1 ] || {
    echo "ERROR: unknown --top '${TOP}' (expected one of: ${BLOCKS[*]})" >&2
    usage; exit 2
  }
  SELECTED=("${TOP}")
fi

WORK="$(mktemp -d)"
GENDIR="$(mktemp -d)"
trap 'rm -rf "${WORK}" "${GENDIR}"' EXIT

for blk in "${SELECTED[@]}"; do
  [ -f "${HERE}/${blk}.sch" ] || {
    echo "ERROR: no schematic at design/sg13cmos5l/${blk}.sch" >&2
    exit 1
  }
  export_block "${blk}" "${GENDIR}" "${WORK}"
done

if [ "${CHECK}" -eq 1 ]; then
  rc=0
  for blk in "${SELECTED[@]}"; do
    committed="${HERE}/netlist/${blk}.spice"
    if [ ! -f "${committed}" ]; then
      echo "STALE: design/sg13cmos5l/netlist/${blk}.spice is missing -- run design/sg13cmos5l/netlist.sh" >&2
      rc=1
      continue
    fi
    normalize "${committed}" "${WORK}/${blk}.committed.norm"
    normalize "${GENDIR}/${blk}.spice" "${WORK}/${blk}.regen.norm"
    if ! diff -u --label "design/sg13cmos5l/netlist/${blk}.spice (committed)" \
                 --label "design/sg13cmos5l/${blk}.sch (regenerated)" \
                 "${WORK}/${blk}.committed.norm" "${WORK}/${blk}.regen.norm"; then
      echo "STALE: design/sg13cmos5l/netlist/${blk}.spice differs from ${blk}.sch" >&2
      rc=1
    fi
  done
  if [ "${rc}" -eq 0 ]; then
    echo "design/sg13cmos5l/netlist.sh --check: all ${#SELECTED[@]} netlists match the schematics"
  else
    echo "ERROR: design/sg13cmos5l/netlist.sh --check failed -- see STALE errors above" >&2
  fi
  exit "${rc}"
fi

mkdir -p "${HERE}/netlist"
for blk in "${SELECTED[@]}"; do
  cp "${GENDIR}/${blk}.spice" "${HERE}/netlist/${blk}.spice"
  echo "netlisted ${blk} -> design/sg13cmos5l/netlist/${blk}.spice"
done
