#!/usr/bin/env bash
# sg13g2-pll :: sim/tools/check-osdi-arch.sh   (issue #59)
#
# Preflight: assert that every OSDI compact-model object a deck is about to
# `osdi`-load is built for the architecture/binary format of the host that is
# about to dlopen it.
#
# WHY THIS EXISTS
# ---------------
# The installed `ihp-sg13cmos5l` tree does not build all of its OSDI objects
# the same way:
#
#   psp103 / psp103_nqs / mosvar / r3_cmc  -- gitignored BUILD PRODUCTS of the
#       sibling `ihp-sg13g2` tree, symlinked in.  A host that installed the PDK
#       correctly built these locally (ihp-sg13g2/libs.tech/verilog-a/
#       openvaf-compile-va.sh), so they are native to that host.
#   cap_cmomi / cap_cmomf  -- TRACKED FILES committed into the upstream
#       ihp-sg13cmos5l git repository as prebuilt x86-64 ELF shared objects.
#       They are whatever architecture the upstream committer's host was,
#       regardless of the host that checked them out.  Upstream's own Makefile
#       says as much: "unlike the OSDI above these two are tracked files, so a
#       pull is the fix rather than a build".
#
# On an x86-64 Linux host the two happen to agree and nothing is visibly
# wrong.  On an arm64 macOS host they do not: the four build products are
# arm64 Mach-O and the two tracked MOM-capacitor objects are still x86-64 ELF,
# so ngspice fails at dlopen with
#
#   Error opening osdi lib ".../cap_cmomi.osdi": dlopen(...):
#       (slice is not valid mach-o file)
#   Error: Library .../cap_cmomi.osdi couldn't be loaded!
#   Unable to find definition of model xcap:cap_cmomi_mod
#
# which reads like a broken testbench and is not one.  This script turns that
# into a named diagnosis plus the one command that fixes it.  See
# ../PORTING-osdi-host-arch.md for the full finding, the remedy, and the
# cross-check protocol that must be satisfied before a locally rebuilt model
# is trusted for a new sim/ record.
#
# USAGE
#   check-osdi-arch.sh [--warn-only] [--quiet] <osdi-file> [<osdi-file>...]
#   check-osdi-arch.sh --osdi-dir <dir> [--warn-only] [--quiet]
#   check-osdi-arch.sh --self-test
#
# EXIT
#   0  every object is loadable by this host (or --warn-only was given)
#   1  at least one object is built for a different architecture/format
#   2  usage error, or a named object does not exist
#
# Deliberately does NOT shell out to file(1): its output wording differs
# between GNU file and the macOS/BSD build, and the hosts that need this check
# most are exactly the ones where that wording differs.  The classification
# below reads the object's own header bytes instead, which is stable
# everywhere `od` exists.

set -uo pipefail

PROG="$(basename "$0")"

# ---------------------------------------------------------------------------
# Header classification.
#
# ELF (Linux):  7f 45 4c 46 | EI_CLASS@4 | EI_DATA@5 ... e_machine@0x12 (u16)
#     EM_X86_64 = 0x3e, EM_AARCH64 = 0xb7
# Mach-O 64 (macOS): magic cf fa ed fe (LE) | cputype@4 (u32 LE)
#     CPU_TYPE_X86_64 = 0x01000007, CPU_TYPE_ARM64 = 0x0100000c
# Universal / "fat" (macOS): magic ca fe ba be (BE, 32-bit offsets) or
#     ca fe ba bf (BE, 64-bit offsets); nfat_arch@4 (u32 BE); then per-slice
#     records whose first u32 (BE) is the slice cputype.
#
# Emits a single space-separated token list:  <format> <arch>[ <arch>...]
# `unknown` for anything unrecognised -- reported, never silently passed.
# ---------------------------------------------------------------------------

_bytes() { # file offset count -> hex string, no separators
  od -An -v -tx1 -j "$2" -N "$3" "$1" 2>/dev/null | tr -d ' \n'
}

_u32be() { # file offset -> decimal
  local h; h="$(_bytes "$1" "$2" 4)"
  [ ${#h} -eq 8 ] || { echo ""; return; }
  echo $(( 16#$h ))
}

classify_osdi() {
  local f="$1" magic
  magic="$(_bytes "$f" 0 4)"

  case "$magic" in
    7f454c46) # ELF
      local cls data mach_hex
      cls="$(_bytes "$f" 4 1)"
      data="$(_bytes "$f" 5 1)"
      [ "$cls" = "02" ] || { echo "elf32 unknown"; return; }
      if [ "$data" = "01" ]; then                       # little-endian
        mach_hex="$(_bytes "$f" 18 2)"
        mach_hex="${mach_hex:2:2}${mach_hex:0:2}"       # swap to big-endian
      else
        mach_hex="$(_bytes "$f" 18 2)"
      fi
      case "$mach_hex" in
        003e) echo "elf x86_64" ;;
        00b7) echo "elf aarch64" ;;
        *)    echo "elf unknown" ;;
      esac
      ;;
    cffaedfe) # Mach-O 64, little-endian host order
      local ct; ct="$(_bytes "$f" 4 4)"
      ct="${ct:6:2}${ct:4:2}${ct:2:2}${ct:0:2}"         # swap to big-endian
      case "$ct" in
        01000007) echo "macho x86_64" ;;
        0100000c) echo "macho arm64" ;;
        *)        echo "macho unknown" ;;
      esac
      ;;
    cafebabe|cafebabf) # universal ("fat") archive
      local wide=0 n i off ct out="fat"
      [ "$magic" = "cafebabf" ] && wide=1
      n="$(_u32be "$f" 4)"
      if [ -z "$n" ] || [ "$n" -le 0 ] || [ "$n" -gt 32 ]; then echo "fat unknown"; return; fi
      for (( i = 0; i < n; i++ )); do
        if [ "$wide" -eq 1 ]; then off=$(( 8 + i * 32 )); else off=$(( 8 + i * 20 )); fi
        ct="$(_bytes "$f" "$off" 4)"
        case "$ct" in
          01000007) out="$out x86_64" ;;
          0100000c) out="$out arm64" ;;
          *)        out="$out unknown" ;;
        esac
      done
      echo "$out"
      ;;
    "") echo "empty unknown" ;;
    *)  echo "unknown unknown" ;;
  esac
}

# ---------------------------------------------------------------------------
# What this host can dlopen.
#
# OSDI_CHECK_FAKE_UNAME_S / _M override the detected host, so the arm64-macOS
# diagnosis this script exists for can be rehearsed (and its wording checked)
# from an x86-64 Linux host.  They are a TEST hook -- never set them in a
# testbench.
# ---------------------------------------------------------------------------

_uname_s() { echo "${OSDI_CHECK_FAKE_UNAME_S:-$(uname -s)}"; }
_uname_m() { echo "${OSDI_CHECK_FAKE_UNAME_M:-$(uname -m)}"; }

host_format() {
  case "$(_uname_s)" in
    Darwin) echo "macho" ;;
    Linux)  echo "elf" ;;
    *)      echo "elf" ;;   # every other POSIX host this repo targets is ELF
  esac
}

host_arch() {
  case "$(_uname_m)" in
    x86_64|amd64)   echo "x86_64" ;;
    arm64|aarch64)  echo "arm64" ;;
    *)              _uname_m ;;
  esac
}

# Mach-O spells 64-bit ARM `arm64`, ELF spells it `aarch64`; they are the same
# machine.  Normalise before comparing so the check does not fire spuriously.
norm_arch() {
  case "$1" in
    aarch64|arm64) echo "arm64" ;;
    *)             echo "$1" ;;
  esac
}

# `<format> <arch>...` from classify_osdi is loadable if the container matches
# the host's and ANY slice matches the host's machine (a fat object needs only
# one usable slice).
is_loadable() { # classification host_format host_arch
  local cls="$1" hfmt="$2" harch="$3"
  local fmt; fmt="${cls%% *}"
  local arches="${cls#* }"

  case "$fmt" in
    elf)   [ "$hfmt" = "elf" ]   || return 1 ;;
    macho) [ "$hfmt" = "macho" ] || return 1 ;;
    fat)   [ "$hfmt" = "macho" ] || return 1 ;;
    *)     return 1 ;;
  esac

  local a
  for a in $arches; do
    [ "$(norm_arch "$a")" = "$(norm_arch "$harch")" ] && return 0
  done
  return 1
}

# ---------------------------------------------------------------------------
# Remedy.  Which openvaf-compile-va.sh rebuilds a given object depends on
# which tree owns its Verilog-A source, NOT on which tree the object sits in:
# cap_cmomi/cap_cmomf are sourced in ihp-sg13cmos5l, the other four in
# ihp-sg13g2 (ihp-sg13cmos5l only symlinks those in).
# ---------------------------------------------------------------------------

remedy_for() {
  # SC2016 is intentional below: $PDK_ROOT must stay LITERAL in the printed
  # command, so a reader can paste it with their own PDK_ROOT exported.
  # shellcheck disable=SC2016
  case "$(basename "$1")" in
    cap_cmomi.osdi|cap_cmomf.osdi)
      echo 'cd "$PDK_ROOT/ihp-sg13cmos5l/libs.tech/verilog-a" && ./openvaf-compile-va.sh' ;;
    *)
      echo 'cd "$PDK_ROOT/ihp-sg13g2/libs.tech/verilog-a" && ./openvaf-compile-va.sh' ;;
  esac
}

# ---------------------------------------------------------------------------
# Self-test.  Synthesises headers for every (format, arch) pair this
# classifier claims to recognise, so the arm64/Mach-O paths are exercised on
# an x86-64 Linux host too -- the alternative is a classifier whose only
# interesting branch is never executed anywhere it can be run.
# ---------------------------------------------------------------------------

_mkhdr() { # out_file hexstring
  local out="$1" hex="$2"
  printf '%b' "$(printf '%s' "$hex" | sed 's/../\\x&/g')" > "$out"
}

self_test() {
  local dir rc=0
  dir="$(mktemp -d)"
  # shellcheck disable=SC2064
  trap "rm -rf '$dir'" RETURN

  # 4-byte magic, then pad to a fixed 64-byte header we can index into.
  local pad; pad="$(printf '0%.0s' $(seq 1 96))"

  # ELF64 LE: e_ident[16] | e_type@16 (u16) | e_machine@18 (u16).
  _mkhdr "$dir/elf_x86_64.osdi"  "7f454c4602010100${pad:0:16}02003e00${pad:0:64}"
  _mkhdr "$dir/elf_aarch64.osdi" "7f454c4602010100${pad:0:16}0200b700${pad:0:64}"
  # Mach-O 64 LE, cputype at 4.
  _mkhdr "$dir/macho_x86_64.osdi" "cffaedfe07000001${pad:0:64}"
  _mkhdr "$dir/macho_arm64.osdi"  "cffaedfe0c000001${pad:0:64}"
  # Universal, 2 slices (x86_64 then arm64), 20-byte arch records at 8 and 28.
  _mkhdr "$dir/fat_both.osdi" \
    "cafebabe00000002010000070000000300000000000000000000000c0100000c${pad:0:32}"
  _mkhdr "$dir/garbage.osdi" "deadbeef${pad:0:32}"

  local checks=(
    "elf_x86_64.osdi|elf x86_64"
    "elf_aarch64.osdi|elf aarch64"
    "macho_x86_64.osdi|macho x86_64"
    "macho_arm64.osdi|macho arm64"
    "garbage.osdi|unknown unknown"
  )
  local c name want got
  for c in "${checks[@]}"; do
    name="${c%%|*}"; want="${c#*|}"
    got="$(classify_osdi "$dir/$name")"
    if [ "$got" = "$want" ]; then
      echo "ok       classify $name -> $got"
    else
      echo "NOT OK   classify $name -> '$got' (want '$want')"; rc=1
    fi
  done

  got="$(classify_osdi "$dir/fat_both.osdi")"
  case "$got" in
    "fat x86_64 arm64") echo "ok       classify fat_both.osdi -> $got" ;;
    *) echo "NOT OK   classify fat_both.osdi -> '$got' (want 'fat x86_64 arm64')"; rc=1 ;;
  esac

  # The load matrix.  Each row: classification | host_format | host_arch | want
  local matrix=(
    "elf x86_64|elf|x86_64|yes"
    "elf x86_64|elf|arm64|no"
    "elf aarch64|elf|arm64|yes"
    "elf x86_64|macho|arm64|no"       # the exact issue-#59 failure
    "macho arm64|macho|arm64|yes"
    "macho x86_64|macho|arm64|no"
    "macho arm64|elf|x86_64|no"
    "fat x86_64 arm64|macho|arm64|yes"
    "fat x86_64|macho|arm64|no"
    "unknown unknown|elf|x86_64|no"
  )
  local row cls hf ha
  for row in "${matrix[@]}"; do
    IFS='|' read -r cls hf ha want <<< "$row"
    if is_loadable "$cls" "$hf" "$ha"; then got=yes; else got=no; fi
    if [ "$got" = "$want" ]; then
      echo "ok       loadable '$cls' on $hf/$ha -> $got"
    else
      echo "NOT OK   loadable '$cls' on $hf/$ha -> $got (want $want)"; rc=1
    fi
  done

  # aarch64/arm64 must be treated as one machine, not two.
  if is_loadable "elf aarch64" "elf" "aarch64"; then
    echo "ok       loadable 'elf aarch64' on elf/aarch64 -> yes"
  else
    echo "NOT OK   loadable 'elf aarch64' on elf/aarch64 -> no (want yes)"; rc=1
  fi

  # Remedy routing: the MOM caps come from the cmos5l tree, everything else
  # from the sg13g2 tree.
  case "$(remedy_for /x/y/cap_cmomi.osdi)" in
    *ihp-sg13cmos5l*) echo "ok       remedy cap_cmomi.osdi -> ihp-sg13cmos5l" ;;
    *) echo "NOT OK   remedy cap_cmomi.osdi did not name ihp-sg13cmos5l"; rc=1 ;;
  esac
  case "$(remedy_for /x/y/psp103.osdi)" in
    *ihp-sg13g2*) echo "ok       remedy psp103.osdi -> ihp-sg13g2" ;;
    *) echo "NOT OK   remedy psp103.osdi did not name ihp-sg13g2"; rc=1 ;;
  esac

  if [ "$rc" -eq 0 ]; then echo "self-test: PASS"; else echo "self-test: FAIL"; fi
  return "$rc"
}

# ---------------------------------------------------------------------------

usage() {
  # Prints from the "# USAGE" header through the line just before
  # `set -uo pipefail` -- sentinel-driven so a future edit to the comment
  # block above (WHY THIS EXISTS) can't silently truncate this, the way a
  # hard-coded line range once did.
  awk '
    /^# USAGE/          { p = 1 }
    /^set -uo pipefail/ { exit }
    p                   { print }
  ' "$0" | sed 's/^# \{0,1\}//'
  exit 2
}

main() {
  local warn_only=0 quiet=0 files=() osdi_dir=""

  while [ $# -gt 0 ]; do
    case "$1" in
      --self-test) self_test; exit $? ;;
      --warn-only) warn_only=1; shift ;;
      --quiet)     quiet=1; shift ;;
      --osdi-dir)  osdi_dir="${2:-}"; [ -n "$osdi_dir" ] || usage; shift 2 ;;
      -h|--help)   usage ;;
      -*)          echo "$PROG: unknown option '$1'" >&2; usage ;;
      *)           files+=("$1"); shift ;;
    esac
  done

  if [ -n "$osdi_dir" ]; then
    [ -d "$osdi_dir" ] || { echo "$PROG: no such directory: $osdi_dir" >&2; exit 2; }
    local f
    for f in "$osdi_dir"/*.osdi; do [ -e "$f" ] && files+=("$f"); done
  fi

  [ "${#files[@]}" -gt 0 ] || usage

  local hfmt harch
  hfmt="$(host_format)"; harch="$(host_arch)"

  local bad=() f cls
  for f in "${files[@]}"; do
    if [ ! -e "$f" ]; then
      echo "$PROG: no such OSDI object: $f" >&2
      exit 2
    fi
    cls="$(classify_osdi "$f")"
    if is_loadable "$cls" "$hfmt" "$harch"; then
      [ "$quiet" -eq 1 ] || echo "$PROG: ok   $(basename "$f"): $cls (host $hfmt/$harch)" >&2
    else
      bad+=("$f|$cls")
    fi
  done

  [ "${#bad[@]}" -eq 0 ] && return 0

  {
    echo
    echo "$PROG: OSDI object(s) not loadable by this host ($hfmt/$harch, $(_uname_s)/$(_uname_m)):"
    local entry
    for entry in "${bad[@]}"; do
      f="${entry%%|*}"; cls="${entry#*|}"
      echo "    $f"
      echo "        built for: $cls"
      echo "        rebuild:   $(remedy_for "$f")"
    done
    echo
    echo "  This is a HOST/PDK-PROVISIONING gap, not a broken testbench: ngspice"
    echo "  will fail these with 'Error opening osdi lib ... couldn't be loaded'"
    echo "  and then 'Unable to find definition of model ...'."
    echo "  Full finding, remedy and the mandatory numeric cross-check before a"
    echo "  rebuilt model is trusted for a new record:"
    echo "      sim/PORTING-osdi-host-arch.md   (issue #59)"
    echo
  } >&2

  [ "$warn_only" -eq 1 ] && return 0
  return 1
}

main "$@"
