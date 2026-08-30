#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-loop-filter-momcap/testbench/run.sh
# (issue #23, Part of #16 -- SG13CMOS5L PVT-cornered sim campaign)
#
# Runs the loop_filter R1/C1/C2 corner + MOM-cap-uncertainty sweep this
# record's ../records/RECORD-001 describes, and writes the raw per-corner
# results to ../corners/results.csv.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Matrix (see RECORD-001 "Corner matrix" for the full rationale):
#   R1 (rppd):        3 process corners (cornerRES.lib res_typ/res_bcs/res_wcs)
#                      x 3 temperatures (-40/27/125 C) = 9 combinations
#   C1, C2 (cap_cmomi): 3 MOM-model-uncertainty fractions (-20%/0/+20%),
#                      applied uniformly to both instances -- cap_cmomi is
#                      confirmed temperature- and process-corner-invariant in
#                      the installed model (see RECORD-001), so no separate
#                      temp/process axis is swept for the caps themselves.
#   Total: 9 x 3 = 27 (R, C1, C2, fz, fp) rows written to results.csv.
#
# Requires: ngspice on PATH, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree (same variables design/sg13cmos5l/netlist.sh reads).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
OUT_CSV="$RECORD_DIR/corners/results.csv"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

# cap_cmomi (Verilog-A/OSDI compact model) and rppd/rhigh (r3_cmc OSDI
# resistor model) both require their OSDI objects loaded via ngspice's
# `osdi` command *before* a netlist referencing them is parsed -- ngspice
# only honors `osdi` from a `.spiceinit` auto-sourced at startup (or
# interactively), not from a `.control` block inside the netlist itself
# (confirmed directly against the installed ngspice-46: an in-`.control`
# `osdi` line still fails "Unable to find definition of model" because the
# netlist's own device-model elaboration already ran by the time `.control`
# executes). So every ngspice invocation below runs with $WORK as its cwd,
# and this generated `.spiceinit` is what makes that resolve.
cat > "$WORK/.spiceinit" <<EOF
osdi $PDK_ROOT/$PDK/libs.tech/ngspice/osdi/cap_cmomi.osdi
osdi $PDK_ROOT/$PDK/libs.tech/ngspice/osdi/cap_cmomf.osdi
osdi $PDK_ROOT/$PDK/libs.tech/ngspice/osdi/r3_cmc.osdi
EOF

# OSDI host-architecture preflight (issue #59).  cap_cmomi.osdi/cap_cmomf.osdi
# are architecture-specific binaries TRACKED in the upstream ihp-sg13cmos5l git
# repo (prebuilt x86-64 ELF) rather than host-local build products like
# psp103/r3_cmc, so on a non-x86-64 host they fail ngspice's dlopen with
# "Error opening osdi lib ... couldn't be loaded" -- which reads like a broken
# deck and is not one.  Fail here instead, naming the one-command rebuild
# (ihp-sg13cmos5l/libs.tech/verilog-a/openvaf-compile-va.sh).  Full finding and
# the cross-check protocol for a rebuilt model: ../../PORTING-osdi-host-arch.md
"$HERE/../../tools/check-osdi-arch.sh" --quiet \
  "$PDK_ROOT/$PDK/libs.tech/ngspice/osdi/cap_cmomi.osdi" \
  "$PDK_ROOT/$PDK/libs.tech/ngspice/osdi/cap_cmomf.osdi" \
  "$PDK_ROOT/$PDK/libs.tech/ngspice/osdi/r3_cmc.osdi"

RES_CORNERS=(res_typ res_bcs res_wcs)
TEMPS=(-40 27 125)
MOM_FRACS=(-0.20 0.00 0.20)

# loop_filter instance geometry -- must match netlist-snapshots/loop_filter.spice
R1_W=4u; R1_L=120u
C1_W=40u; C1_L=40u
C2_W=10u; C2_L=10u

# Do not silently discard ngspice's stderr (issue #43): a fatal error (e.g.
# an unresolved .lib/.include path) must be visible, not masked into a
# blank/NA result indistinguishable from real behavior.
run_ngspice_or_die() {
  local sp="$1"
  local err="${sp}.err"
  local out
  if ! out="$(cd "$WORK" && ngspice -b "$(basename "$sp")" 2>"$err")"; then
    echo "ERROR: ngspice exited non-zero for $(basename "$sp"):" >&2
    cat "$err" >&2
    return 1
  fi
  printf '%s\n' "$out"
}

extract_r() {
  local corner="$1" temp="$2"
  local name="r_${corner}_${temp}.sp"
  sed -e "s/@RES_CORNER@/$corner/" -e "s/@TEMP@/$temp/" \
      -e "s/@W@/$R1_W/" -e "s/@L@/$R1_L/" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|" -e "s|@PDK@|$PDK|" \
    "$HERE/tb_extract_r.sp.tmpl" > "$WORK/$name"
  run_ngspice_or_die "$WORK/$name" | grep '^rval' | awk '{print $3}'
}

extract_c_nominal() {
  local w="$1" l="$2" temp="$3"
  local name="c_${w}_${l}_${temp}.sp"
  sed -e "s/@W@/$w/" -e "s/@L@/$l/" -e "s/@TEMP@/$temp/" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|" -e "s|@PDK@|$PDK|" \
    "$HERE/tb_extract_c.sp.tmpl" > "$WORK/$name"
  # AC sweep prints an "Index  frequency  cnom" table; the cap is flat across
  # the swept band (see RECORD-001 "Frequency-flatness check"), so take the
  # last row's cnom column.
  run_ngspice_or_die "$WORK/$name" | grep -E '^[0-9]+[[:space:]]' | tail -1 | awk '{print $3}'
}

echo "res_corner,temp_c,mom_frac,r1_ohm,c1_f,c2_f,fz_hz,fp_hz" > "$OUT_CSV"

# Nominal C1/C2 at 27C (temperature-invariance is checked separately below,
# not swept into the main matrix -- see RECORD-001).
C1_NOM="$(extract_c_nominal "$C1_W" "$C1_L" 27)"
C2_NOM="$(extract_c_nominal "$C2_W" "$C2_L" 27)"
echo "measured nominal C1=${C1_NOM} F, C2=${C2_NOM} F (27C, mom_frac=0)" >&2

# Temperature-invariance check for cap_cmomi (documents the finding, does
# not feed the main matrix): C1 at -40C and 125C should match the 27C value.
for t in -40 125; do
  c1_t="$(extract_c_nominal "$C1_W" "$C1_L" "$t")"
  echo "C1 at ${t}C = ${c1_t} F (temperature-invariance check)" >&2
done

for corner in "${RES_CORNERS[@]}"; do
  for temp in "${TEMPS[@]}"; do
    r1="$(extract_r "$corner" "$temp")"
    for frac in "${MOM_FRACS[@]}"; do
      python3 - "$r1" "$C1_NOM" "$C2_NOM" "$frac" "$corner" "$temp" >> "$OUT_CSV" <<'PYEOF'
import sys, math
r1, c1_nom, c2_nom, frac, corner, temp = sys.argv[1:7]
r1 = float(r1); c1_nom = float(c1_nom); c2_nom = float(c2_nom); frac = float(frac)
c1 = c1_nom * (1 + frac)
c2 = c2_nom * (1 + frac)
fz = 1 / (2 * math.pi * r1 * c1)
fp = (c1 + c2) / (2 * math.pi * r1 * c1 * c2)
print(f"{corner},{temp},{frac:.2f},{r1:.6e},{c1:.6e},{c2:.6e},{fz:.6e},{fp:.6e}")
PYEOF
    done
  done
done

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
