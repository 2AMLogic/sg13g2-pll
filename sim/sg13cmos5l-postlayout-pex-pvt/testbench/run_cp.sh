#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/run_cp.sh
# (issue #30, Part of #16 -- post-layout PEX + PVT re-simulation)
#
# Re-runs the SG13CMOS5L charge pump's ratified PVT corner matrix -- the one
# ../../sg13cmos5l-cp-icp-trim/corners/matrix.md defines, unchanged: 17 PVT
# points (5 MOS corners x 3 temperatures at 3.3 V, plus a +-10% supply
# sub-axis at mos_tt/27 C) x 6 trim codes x 3 UP/DN switch states = 306 DC
# sweeps -- twice:
#
#   arm=postlayout  against ../netlist-snapshots/pll_cp.pex.spice, the
#                   parasitic-annotated netlist ../extraction/run-pex.sh
#                   produced from the routed GDS;
#   arm=schematic   against the SAME frozen schematic netlist the original
#                   campaign simulated, re-run HERE, on this host.
#
# WHY THIS BLOCK, in addition to ./run.sh's `pll_vco`: `cp` is one of the
# three blocks ../lvs-recheck/summary.json confirms LVS-MATCHES its schematic
# (20/20 devices, 18/18 nets, 0 errors). `pll_vco` does not. A deviation
# measured on `cp` is therefore attributable to the extracted parasitics; a
# deviation measured on `pll_vco` is attributable to the parasitics OR to
# whatever the unverified topology difference is. Having both is what lets
# ../records/RECORD-001 separate those two readings instead of conflating
# them.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_cp.sh
#   CP_ARMS=postlayout ./run_cp.sh      # one arm only
#   CP_JOBS=4 ./run_cp.sh               # parallel ngspice processes
#   CP_WORK=/path/to/dir ./run_cp.sh    # persistent, RESUMABLE scratch dir
#
# Resume and thread-pinning semantics are identical to ./run.sh's -- see that
# script's header, including why a recorded `NA` is deliberately never
# resumed and why `set num_threads=1` is a large speed-up here rather than a
# slow-down.
#
# Output: ../corners/cp_results.csv (Icp at VDD/2, one row per run, both arms)

WORK="${CP_WORK:-}"
# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SIM_ROOT="$(cd "$RECORD_DIR/.." && pwd)"
SNAP="$RECORD_DIR/netlist-snapshots"
OUT_CSV="$RECORD_DIR/corners/cp_results.csv"
JOBS="${CP_JOBS:-4}"
ARMS="${CP_ARMS:-postlayout schematic}"
THREADS="${PEX_OMP_THREADS:-1}"
export OMP_NUM_THREADS="$THREADS"

mkdir -p "$RECORD_DIR/corners"

# All-MOS DUT on both arms: no resistor and no cap_cmomi/cap_cmomf instance
# appears anywhere in `cp`, extracted or schematic, so only the PSP103 bundle
# is loaded (same set the original campaign's run.sh loads).
cat > "$WORK/.spiceinit" <<EOF
set num_threads=$THREADS
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

# --- arm inputs -------------------------------------------------------------
python3 "$HERE/pex-to-ngspice.py" "$SNAP/pll_cp.pex.spice" "$WORK/cp_pex.spice"
# VSS MUST be named explicitly. `make-inst.py` surfaces every unmapped pin of
# the extracted cell at the top level under its own name, which is harmless
# for a genuinely internal net but catastrophic for a supply rail: `VSS` would
# become a floating top-level node rather than ground, and the measured Icp
# would be a property of that floating node. (Measured, not assumed: the first
# run of this script omitted `VSS=0` and produced Icp ratios from +200% to
# -362253% against the schematic arm -- an obviously non-physical result that
# is exactly what a floating ground looks like. Recorded here so the next
# reader does not have to rediscover it.)
python3 "$HERE/make-inst.py" "$WORK/cp_pex.spice" pll_cp cp \
  VSS=0 > "$WORK/cp_inst.spice"

# Verbatim copy of the frozen schematic snapshot -- no strip, no edit, exactly
# as the original campaign's own run.sh does it.
cp "$SIM_ROOT/sg13cmos5l-cp-icp-trim/netlist-snapshots/cp.spice" "$WORK/cp_snap.spice"

# --- the ratified matrix, copied verbatim from the original campaign --------
PVT=(
  "mos_tt 27  3.3"  "mos_tt 125 3.3"  "mos_tt -40 3.3"
  "mos_ss 27  3.3"  "mos_ss 125 3.3"  "mos_ss -40 3.3"
  "mos_ff 27  3.3"  "mos_ff 125 3.3"  "mos_ff -40 3.3"
  "mos_sf 27  3.3"  "mos_sf 125 3.3"  "mos_sf -40 3.3"
  "mos_fs 27  3.3"  "mos_fs 125 3.3"  "mos_fs -40 3.3"
  "mos_tt 27  3.0"  "mos_tt 27  3.6"
)
IREFS=(2.5u 5u 10u 20u 40u 80u)
STATES=("up 1 0" "dn 0 1" "both 1 1")

worker() {
  local arm="$1" mos="$2" temp="$3" vdd="$4" iref="$5" slabel="$6" \
        upv="$7" dnv="$8"
  local tag="${arm}_${mos}_${temp}_${vdd}_${iref}_${slabel}"
  [[ -s "$WORK/cp.$tag" ]] && ! grep -q ',NA$' "$WORK/cp.$tag" && return 0

  local tmpl
  case "$arm" in
    postlayout) tmpl="$HERE/tb_cp_dc_pex.sp.tmpl" ;;
    schematic)  tmpl="$HERE/tb_cp_dc_sch.sp.tmpl" ;;
    *) echo "unknown arm $arm" >&2; return 1 ;;
  esac

  local voutmax
  voutmax="$(python3 -c "print(round(${vdd}-0.15,4))")"
  sed -e "s/@CORNER_MOS@/$mos/" -e "s/@TEMP@/$temp/" -e "s/@VDD@/$vdd/" \
      -e "s/@IREF@/$iref/" -e "s/@UPV@/$upv/" -e "s/@DNV@/$dnv/" \
      -e "s/@VOUTMAX@/$voutmax/" \
      -e "s#@PDK_ROOT@#$PDK_ROOT#" -e "s#@PDK@#$PDK#" \
    "$tmpl" > "$WORK/tb_$tag.sp"

  # Each run needs its own sweep.dat: `wrdata` writes a fixed filename into
  # the process's cwd, so the fan-out gives every point a private directory.
  local d="$WORK/d_$tag"
  rm -rf "$d"; mkdir -p "$d"
  cp "$WORK/.spiceinit" "$WORK/tb_$tag.sp" "$d/"
  for f in cp_pex.spice cp_inst.spice cp_snap.spice; do
    [ -f "$WORK/$f" ] && cp "$WORK/$f" "$d/"
  done

  if ! ( cd "$d" && ngspice -b "tb_$tag.sp" > ngspice.log 2>&1 ); then
    echo "ERROR: ngspice failed for $tag" >&2
    tail -5 "$d/ngspice.log" >&2
    echo "${arm},${mos},${temp},${vdd},${iref},${slabel},NA,NA" > "$WORK/cp.$tag"
    return 0
  fi

  python3 - "$d/sweep.dat" "$arm" "$mos" "$temp" "$vdd" "$iref" "$slabel" \
           "$WORK/cp.$tag" <<'PY'
import sys
dat, arm, mos, temp, vdd, iref, state, out = sys.argv[1:9]
rows = []
for line in open(dat):
    p = line.split()
    if len(p) >= 2:
        try:
            rows.append((float(p[0]), float(p[1])))
        except ValueError:
            pass
if not rows:
    open(out, "w").write("%s,%s,%s,%s,%s,%s,NA,NA\n"
                         % (arm, mos, temp, vdd, iref, state))
    raise SystemExit(0)
# The trim-table row is the sweep point nearest VDD/2, exactly as the
# original campaign selects it.
best = min(rows, key=lambda r: abs(r[0] - float(vdd) / 2.0))
open(out, "w").write("%s,%s,%s,%s,%s,%s,%.6g,%.9g\n"
                     % (arm, mos, temp, vdd, iref, state, best[0], best[1]))
PY
  rm -rf "$d"
  echo "${tag}: $(cut -d, -f8 "$WORK/cp.$tag")" >&2
}

throttle() { while (( $(jobs -rp | wc -l) >= JOBS )); do sleep 1; done; }

for arm in $ARMS; do
  for pvt in "${PVT[@]}"; do
    read -r mos temp vdd <<< "$pvt"
    for iref in "${IREFS[@]}"; do
      for st in "${STATES[@]}"; do
        read -r slabel sup sdn <<< "$st"
        upv="$(python3 -c "print(${sup}*${vdd})")"
        dnv="$(python3 -c "print(${sdn}*${vdd})")"
        throttle
        worker "$arm" "$mos" "$temp" "$vdd" "$iref" "$slabel" "$upv" "$dnv" &
      done
    done
  done
done
wait

{
  echo "arm,mos_corner,temp_c,vdd_v,iref_a,state,vout_v,icp_a"
  cat "$WORK"/cp.* | LC_ALL=C sort
} > "$OUT_CSV"

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
