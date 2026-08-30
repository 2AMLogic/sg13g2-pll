#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim/testbench/run_issue83_finetrim.sh
# (issue #83, Part of #16 -- closes the band=00/mid/f_ref=4.5MHz PM gap
# ../../sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md
# left open)
#
# A TARGETED addition to the trim-code ladder ../testbench/run.sh already
# characterises (2.5/5/10/20/40/80 uA), NOT a re-run of that full campaign.
# ../corners/matrix.md's own trim-code row states the mechanism plainly:
# `cp.sch` has no on-chip unit-element trim array (design/README.md), so the
# "trim code" IS the mirror reference current an (not-yet-drawn) bias
# generator would deliver -- any value is a legitimate measurement, not a
# hardware-infeasible one. This script measures exactly ONE new code
# (3.75 uA, the arithmetic midpoint of the existing 2.5/5 uA codes) at
# exactly the ONE PVT point issue #83's gap needs (`mos_ss`/125 C/3.3 V --
# the "slow" bundle `../../sg13cmos5l-loop-bandwidth-pm/testbench/run.sh`
# maps to `band=00, mid interval, f_ref=4.5MHz`, the only bundle reachable at
# that operating point).
#
# Writes ../corners/results_issue83_finetrim.csv (same 7-column schema as
# ../corners/results.csv, kept in a SEPARATE file per this repo's
# append-only evidence convention -- ../corners/results.csv is not touched).
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_issue83_finetrim.sh

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

OUT_CSV="$RECORD_DIR/corners/results_issue83_finetrim.csv"

cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

cp "$RECORD_DIR/netlist-snapshots/cp.spice" "$WORK/cp_snap.spice"

MOS="mos_ss"
TEMP="125"
VDD="3.3"
IREF="3.75u"

STATES=(
  "up   1 0"
  "dn   0 1"
  "both 1 1"
)

echo "mos_corner,temp_c,vdd_v,iref_a,state,vout_v,icp_a" > "$OUT_CSV"

run_one() {
  local mos="$1" temp="$2" vdd="$3" iref="$4" upv="$5" dnv="$6" tag="$7"
  local voutmax
  voutmax="$(python3 -c "print(round(${vdd}-0.15,4))")"
  sed -e "s/@CORNER_MOS@/$mos/" -e "s/@TEMP@/$temp/" -e "s/@VDD@/$vdd/" \
      -e "s/@IREF@/$iref/" -e "s/@UPV@/$upv/" -e "s/@DNV@/$dnv/" \
      -e "s/@VOUTMAX@/$voutmax/" \
      -e "s#@PDK_ROOT@#$PDK_ROOT#" -e "s#@PDK@#$PDK#" \
    "$HERE/tb_cp_dc.sp.tmpl" > "$WORK/tb_$tag.sp"
  local log="$WORK/ngspice_$tag.log"
  if ( cd "$WORK" && ngspice -b "tb_$tag.sp" > "$log" 2>&1 ); then
    ( cd "$WORK" && mv sweep.dat "sweep_$tag.dat" )
  else
    echo "ngspice failed for $tag; see $log" >&2
    tail -n 20 "$log" >&2
    return 1
  fi
}

n=0
for st in "${STATES[@]}"; do
  read -r slabel sup sdn <<< "$st"
  upv="$(python3 -c "print(${sup}*${VDD})")"
  dnv="$(python3 -c "print(${sdn}*${VDD})")"
  tag="${MOS}_${TEMP}_${VDD}_${IREF}_${slabel}"
  if ! run_one "$MOS" "$TEMP" "$VDD" "$IREF" "$upv" "$dnv" "$tag"; then
    echo "WARNING: ngspice failed for $tag -- recording NA" >&2
    echo "${MOS},${TEMP},${VDD},${IREF},${slabel},NA,NA" >> "$OUT_CSV"
    continue
  fi
  python3 - "$WORK/sweep_$tag.dat" "$MOS" "$TEMP" "$VDD" "$IREF" "$slabel" \
           "$OUT_CSV" <<'PY'
import sys
dat, mos, temp, vdd, iref, state, out_csv = sys.argv[1:8]
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
PY
  n=$((n + 1))
  echo "[$n] $tag" >&2
done

echo "wrote $(wc -l < "$OUT_CSV") lines to $OUT_CSV" >&2
