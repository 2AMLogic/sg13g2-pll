#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-vco-decap-momcap/testbench/run.sh
# (issue #23, Part of #16 -- SG13CMOS5L PVT-cornered sim campaign)
#
# Runs the vco.XCDECAP MOM-cap-uncertainty sweep this record's
# ../records/RECORD-001 describes, and writes the raw per-run results to
# ../corners/results.csv.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Matrix (see RECORD-001 "Corner matrix" for the full rationale):
#   - Nominal C_decap measured at 27C, then re-measured at -40C/125C to
#     confirm cap_cmomi's own temperature-invariance (same finding as
#     ../../sg13cmos5l-loop-filter-momcap's record; no PDK process-corner
#     axis exists for this device either -- cornerCAP.lib's own header
#     confirms every corner maps to the same nominal model).
#   - 3 MOM-model-uncertainty fractions (-20%/0/+20%) applied as a parallel
#     delta capacitor, each run through a real ngspice AC sweep of an
#     illustrative R_src-C_decap single-pole network (tb_decap_pole_ac.sp.tmpl)
#     to extract the resulting -3dB corner frequency.
#   R_src = 3000 ohm is an ILLUSTRATIVE value chosen only so the resulting
#   pole lands inside this testbench's swept band (~10 MHz) -- it is NOT a
#   measured or extracted on-chip source impedance (none exists pre-layout).
#   See RECORD-001 "What this does not bound" for why the fractional
#   pole-frequency sensitivity to the MOM band (the actual claim under test)
#   does not depend on this choice, even though the illustrative absolute
#   corner frequency does.
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

# See ../../sg13cmos5l-loop-filter-momcap/testbench/run.sh for why this
# generated .spiceinit (and running every ngspice invocation with $WORK as
# cwd) is required for cap_cmomi's OSDI model to resolve.
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

MOM_FRACS=(-0.20 0.00 0.20)
RSRC=3000

# Do not silently discard ngspice's stderr (issue #43): a fatal error (e.g.
# an unresolved .include path) must be visible, not masked into a blank/NA
# result indistinguishable from real behavior.
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

extract_cdecap() {
  local temp="$1"
  local name="cdecap_${temp}.sp"
  sed -e "s/@TEMP@/$temp/" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|" -e "s|@PDK@|$PDK|" \
    "$HERE/tb_extract_cdecap.sp.tmpl" > "$WORK/$name"
  run_ngspice_or_die "$WORK/$name" | grep -E '^[0-9]+[[:space:]]' | tail -1 | awk '{print $3}'
}

pole_freq_db3() {
  local delta_f="$1"
  local name="pole_${delta_f}.sp"
  sed -e "s/@RSRC@/$RSRC/" -e "s/@DELTA_F@/$delta_f/" -e "s/@TEMP@/27/" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|" -e "s|@PDK@|$PDK|" \
    "$HERE/tb_decap_pole_ac.sp.tmpl" > "$WORK/$name"
  run_ngspice_or_die "$WORK/$name" | grep -E '^[0-9]+[[:space:]]' \
    | awk '{print $2, $3}' | python3 -c "
import sys
rows = [tuple(map(float, l.split())) for l in sys.stdin]
target = -3.0103
for (f0, m0), (f1, m1) in zip(rows, rows[1:]):
    if m0 > target >= m1:
        # linear interpolation in log-frequency
        import math
        frac = (target - m0) / (m1 - m0)
        f = math.exp(math.log(f0) + frac * (math.log(f1) - math.log(f0)))
        print(f'{f:.6e}')
        break
else:
    print('NA')
"
}

echo "measurement,temp_c,mom_frac,cdecap_f,pole_hz_db3" > "$OUT_CSV"

C_NOM="$(extract_cdecap 27)"
echo "measured nominal C_decap=${C_NOM} F (27C, mom_frac=0)" >&2
echo "nominal,27,0.00,${C_NOM}," >> "$OUT_CSV"

for t in -40 125; do
  c_t="$(extract_cdecap "$t")"
  echo "C_decap at ${t}C = ${c_t} F (temperature-invariance check)" >&2
  echo "temp-check,${t},0.00,${c_t}," >> "$OUT_CSV"
done

for frac in "${MOM_FRACS[@]}"; do
  delta_f="$(python3 -c "print(${C_NOM} * ${frac})")"
  pole="$(pole_freq_db3 "$delta_f")"
  c_used="$(python3 -c "print(${C_NOM} * (1 + ${frac}))")"
  echo "mom-sweep,27,${frac},${c_used},${pole}" >> "$OUT_CSV"
done

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
