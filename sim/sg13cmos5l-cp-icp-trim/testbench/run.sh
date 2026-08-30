#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim/testbench/run.sh
# (issue #27, Part of #16 -- SG13CMOS5L closed-loop PVT campaign)
#
# Runs the charge-pump DC characterisation this record's ../records/RECORD-001
# describes (spec/porting-plan.md row 6/6a's Icp-trim mechanism, and the
# up/down mismatch data row 10's reference-spur derivation needs), and writes
#   ../corners/results.csv     -- Icp at VOUT = VDD/2, one row per run
#   ../corners/compliance.csv  -- the full Icp-vs-VOUT sweep at the nominal
#                                 trim code (Iref = 10 uA), same PVT points
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree (same variables design/sg13cmos5l/netlist.sh reads).
#
# Matrix (see ../corners/matrix.md for the full rationale): 5 MOS corners x
# 3 temperatures at the nominal 3.3 V supply, plus a 2-point supply sub-axis
# at mos_tt/27C, x 6 trim codes x 3 UP/DN switch states.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
OUT_CSV="$RECORD_DIR/corners/results.csv"
OUT_COMP="$RECORD_DIR/corners/compliance.csv"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"

# This DUT is all-MOS (sg13_hv_nmos/sg13_hv_pmos via PSP103) plus the
# testbench-local mirror replica built from the same devices: no resistor and
# no cap_cmomi/cap_cmomf instance appears anywhere in cp.spice, so only the
# PSP103 model bundle is loaded.
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

# Verbatim copy of the frozen snapshot -- no strip, no edit (contrast the
# sg13cmos5l-vco-kvco-table record, whose testbench needed an XCDECAP strip).
cp "$RECORD_DIR/netlist-snapshots/cp.spice" "$WORK/cp_snap.spice"

# PVT points: "mos_corner temp_c vdd_v". cp.spice contains no resistor, so
# cornerRES.lib has nothing to act on and no resistor-corner axis applies
# (stated explicitly rather than silently dropped -- see ../corners/matrix.md).
PVT=(
  "mos_tt 27  3.3"
  "mos_tt 125 3.3"
  "mos_tt -40 3.3"
  "mos_ss 27  3.3"
  "mos_ss 125 3.3"
  "mos_ss -40 3.3"
  "mos_ff 27  3.3"
  "mos_ff 125 3.3"
  "mos_ff -40 3.3"
  "mos_sf 27  3.3"
  "mos_sf 125 3.3"
  "mos_sf -40 3.3"
  "mos_fs 27  3.3"
  "mos_fs 125 3.3"
  "mos_fs -40 3.3"
  "mos_tt 27  3.0"
  "mos_tt 27  3.6"
)

# Trim codes: a binary ladder of mirror reference currents. `cp.sch` has no
# unit-element trim array of its own (design/README.md), so the trim code IS
# the reference current the (not-yet-drawn) bias generator would deliver --
# see ../records/RECORD-001 for that boundary.
IREFS=(2.5u 5u 10u 20u 40u 80u)

# UP/DN switch states, as multiples of VDD: "label up dn"
STATES=(
  "up   1 0"
  "dn   0 1"
  "both 1 1"
)

echo "mos_corner,temp_c,vdd_v,iref_a,state,vout_v,icp_a" > "$OUT_CSV"
echo "mos_corner,temp_c,vdd_v,iref_a,state,vout_v,icp_a" > "$OUT_COMP"

run_one() {
  local mos="$1" temp="$2" vdd="$3" iref="$4" upv="$5" dnv="$6" tag="$7"
  local voutmax
  voutmax="$(python3 -c "print(round(${vdd}-0.15,4))")"
  sed -e "s/@CORNER_MOS@/$mos/" -e "s/@TEMP@/$temp/" -e "s/@VDD@/$vdd/" \
      -e "s/@IREF@/$iref/" -e "s/@UPV@/$upv/" -e "s/@DNV@/$dnv/" \
      -e "s/@VOUTMAX@/$voutmax/" \
    "$HERE/tb_cp_dc.sp.tmpl" > "$WORK/tb_$tag.sp"
  ( cd "$WORK" && ngspice -b "tb_$tag.sp" >/dev/null 2>&1 && mv sweep.dat "sweep_$tag.dat" )
}

n=0
for pvt in "${PVT[@]}"; do
  read -r mos temp vdd <<< "$pvt"
  for iref in "${IREFS[@]}"; do
    for st in "${STATES[@]}"; do
      read -r slabel sup sdn <<< "$st"
      upv="$(python3 -c "print(${sup}*${vdd})")"
      dnv="$(python3 -c "print(${sdn}*${vdd})")"
      tag="${mos}_${temp}_${vdd}_${iref}_${slabel}"
      if ! run_one "$mos" "$temp" "$vdd" "$iref" "$upv" "$dnv" "$tag"; then
        echo "WARNING: ngspice failed for $tag -- recording NA" >&2
        echo "${mos},${temp},${vdd},${iref},${slabel},NA,NA" >> "$OUT_CSV"
        continue
      fi
      # Row for the trim table: the sweep point nearest VDD/2.
      python3 - "$WORK/sweep_$tag.dat" "$mos" "$temp" "$vdd" "$iref" "$slabel" \
               "$OUT_CSV" "$OUT_COMP" <<'PY'
import sys
dat, mos, temp, vdd, iref, state, out_csv, out_comp = sys.argv[1:9]
rows = []
for line in open(dat):
    p = line.split()
    if len(p) >= 2:
        try:
            rows.append((float(p[0]), float(p[1])))
        except ValueError:
            pass
mid = float(vdd) / 2.0
best = min(rows, key=lambda r: abs(r[0] - mid))
with open(out_csv, "a") as f:
    f.write(f"{mos},{temp},{vdd},{iref},{state},{best[0]:.4f},{best[1]:.6e}\n")
# Full compliance curve, but only at the nominal trim code, to keep the
# committed CSV readable (see ../records/RECORD-001 "Corner matrix").
if iref == "10u":
    with open(out_comp, "a") as f:
        for v, i in rows:
            f.write(f"{mos},{temp},{vdd},{iref},{state},{v:.4f},{i:.6e}\n")
PY
      n=$((n + 1))
      echo "[$n] $tag" >&2
    done
  done
done

echo "wrote $(wc -l < "$OUT_CSV") lines to $OUT_CSV" >&2
echo "wrote $(wc -l < "$OUT_COMP") lines to $OUT_COMP" >&2
