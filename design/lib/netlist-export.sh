# shellcheck shell=bash
# sg13g2-pll :: shared xschem-export pipeline for design/netlist.sh and
# design/sg13cmos5l/netlist.sh (issue #45).
#
# This file is a *library*, not a standalone script: it must be `source`d by
# a thin PDK-specific wrapper that sets the following variables first, then
# sources this file as its last line.
#
#   HERE           absolute path of the design directory the wrapper lives
#                  in (e.g. ".../design" or ".../design/sg13cmos5l"),
#                  computed by the wrapper from its own BASH_SOURCE so the
#                  script keeps working under `git worktree` / relocation.
#   DESIGN_REL     repo-relative path prefix to that directory, trailing
#                  slash included (e.g. "design/" or "design/sg13cmos5l/").
#                  Used in every user-facing message and in the sch/sym
#                  path-stamp rewrite in normalize().
#   SCRIPT_REL     repo-relative path to the wrapper script itself (e.g.
#                  "design/netlist.sh" or "design/sg13cmos5l/netlist.sh").
#                  Used in banners, STALE hints, and the --check summary.
#   USAGE_NAME     the name used in the `usage: ...` line printed by -h /
#                  argument errors (e.g. "netlist.sh" or
#                  "sg13cmos5l/netlist.sh").
#   BANNER_SUFFIX  text appended after the block name in the generated
#                  file's banner comment (e.g. "" for SG13G2, or
#                  " (SG13CMOS5L)" for the parallel port). May be empty but
#                  must be set (even to "").
#
# Everything below -- argument parsing, the BLOCKS list, the
# expected_subckts() connectivity guard, check_export()'s three invariant
# checks, normalize(), banner(), export_block(), and the --check/write
# drivers -- is PDK-invariant xschem-export logic shared verbatim between
# both PDK targets (DR-003 Finding 1: the SG13CMOS5L port carries every
# block over unchanged, so a single shared BLOCKS/expected_subckts table is
# correct, not a simplification that loses information).

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "ERROR: design/lib/netlist-export.sh must be sourced by a PDK-specific" >&2
  echo "       wrapper (design/netlist.sh or design/sg13cmos5l/netlist.sh)," >&2
  echo "       not executed directly." >&2
  exit 1
fi

: "${HERE:?netlist-export.sh: HERE must be set by the wrapper}"
: "${DESIGN_REL:?netlist-export.sh: DESIGN_REL must be set by the wrapper}"
: "${SCRIPT_REL:?netlist-export.sh: SCRIPT_REL must be set by the wrapper}"
: "${USAGE_NAME:?netlist-export.sh: USAGE_NAME must be set by the wrapper}"
[ -n "${BANNER_SUFFIX+set}" ] || {
  echo "ERROR: netlist-export.sh: BANNER_SUFFIX must be set (may be empty) by the wrapper" >&2
  exit 1
}

set -euo pipefail

# The six blocks spec/porting-plan.md Sec1.4 names -- issue #7's own Test
# Plan requires every one of these to be represented, not a partial subset.
BLOCKS=(pfd cp loop_filter vco divider_chain lock_detector)

# Expected `.subckt` set per top -- the connectivity guard below fails the
# run if any of these is missing from the corresponding export, catching a
# hierarchy that silently lost a branch. Identical between both PDK targets
# per DR-003 Finding 1: no leaf cell is added, renamed, or dropped by the
# SG13CMOS5L port.
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
  cat >&2 <<EOF
usage: ${USAGE_NAME} [--top <block>] [--check]

  (no args)       regenerate every committed export under ${DESIGN_REL}netlist/
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
# into a comment (`** sch_path: /abs/checkout/<DESIGN_REL>foo.sch`).
# Rewriting those comment lines (and only those) to repo-relative form at
# write time keeps the committed bytes -- and any snapshot hash a future
# sim/ record takes of them -- independent of which checkout produced them.
normalize() {
  sed -E "s#^(\*\* (sch|sym)_path: ).*/${DESIGN_REL}#\1${DESIGN_REL}#" "$1" >"$2"
}

banner() {
  printf '%s\n' \
    "* sg13g2-pll :: $1${BANNER_SUFFIX} -- generated by ${SCRIPT_REL} from $1.sch" \
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
    echo "ERROR: no schematic at ${DESIGN_REL}${blk}.sch" >&2
    exit 1
  }
  export_block "${blk}" "${GENDIR}" "${WORK}"
done

if [ "${CHECK}" -eq 1 ]; then
  rc=0
  for blk in "${SELECTED[@]}"; do
    committed="${HERE}/netlist/${blk}.spice"
    if [ ! -f "${committed}" ]; then
      echo "STALE: ${DESIGN_REL}netlist/${blk}.spice is missing -- run ${SCRIPT_REL}" >&2
      rc=1
      continue
    fi
    normalize "${committed}" "${WORK}/${blk}.committed.norm"
    normalize "${GENDIR}/${blk}.spice" "${WORK}/${blk}.regen.norm"
    if ! diff -u --label "${DESIGN_REL}netlist/${blk}.spice (committed)" \
                 --label "${DESIGN_REL}${blk}.sch (regenerated)" \
                 "${WORK}/${blk}.committed.norm" "${WORK}/${blk}.regen.norm"; then
      echo "STALE: ${DESIGN_REL}netlist/${blk}.spice differs from ${blk}.sch" >&2
      rc=1
    fi
  done
  if [ "${rc}" -eq 0 ]; then
    echo "${SCRIPT_REL} --check: all ${#SELECTED[@]} netlists match the schematics"
  else
    echo "ERROR: ${SCRIPT_REL} --check failed -- see STALE errors above" >&2
  fi
  exit "${rc}"
fi

mkdir -p "${HERE}/netlist"
for blk in "${SELECTED[@]}"; do
  cp "${GENDIR}/${blk}.spice" "${HERE}/netlist/${blk}.spice"
  echo "netlisted ${blk} -> ${DESIGN_REL}netlist/${blk}.spice"
done
