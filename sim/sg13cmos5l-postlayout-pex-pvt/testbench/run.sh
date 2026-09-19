#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/run.sh
# (issue #30, Part of #16 -- post-layout PEX + PVT re-simulation)
#
# Re-runs the SG13CMOS5L VCO's ratified PVT corner matrix -- the one
# ../../sg13cmos5l-vco-kvco-table/corners/matrix.md defines, unchanged:
# 3 PVT bundles x 4 band codes x 5 VCTRL points = 60 transient runs -- twice:
#
#   arm=postlayout  against ../netlist-snapshots/pll_vco.pex.spice, the
#                   parasitic-annotated netlist `../extraction/run-pex.sh`
#                   produced from the routed GDS;
#   arm=schematic   against the SAME frozen schematic netlist the original
#                   campaign simulated, re-run HERE, on this host, with this
#                   ngspice and this PDK.
#
# Both arms are run because the deviation this record has to analyse is
# "what did the extracted interconnect do", not "what did a different host
# do". Comparing a fresh post-layout number against a months-old committed
# schematic number would confound the two; re-running the schematic arm makes
# the comparison a controlled one. The schematic arm's agreement with the
# committed ../../sg13cmos5l-vco-kvco-table/corners/results.csv is itself
# checked, and reported in the record.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh                            # both arms
#   PEX_ARMS=postlayout ./run.sh        # one arm only
#   PEX_JOBS=4 ./run.sh                 # parallel ngspice processes (default 4)
#   PEX_WORK=/path/to/dir ./run.sh      # persistent, RESUMABLE scratch dir
#
# `PEX_WORK` makes the run resumable: each (arm, bundle, band, VCTRL) point
# writes its own `res.<tag>` file, and a point whose `res.<tag>` already
# exists is skipped rather than re-simulated. The post-layout arm is ~15x
# more expensive per point than the schematic arm (170 extracted parasitic
# resistors and 344 parasitic capacitors), so a full matrix is long enough
# that losing a partially-complete run to an interrupted session is a real
# cost. Without `PEX_WORK` the scratch dir is a `mktemp -d` torn down on
# exit, exactly as before -- the resume path is opt-in and never silently
# reuses a stale result.
#
# Requires: ngspice on PATH, and ../netlist-snapshots/ already populated by
# ../extraction/run-pex.sh.

WORK="${PEX_WORK:-}"
# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SIM_ROOT="$(cd "$RECORD_DIR/.." && pwd)"
SNAP="$RECORD_DIR/netlist-snapshots"
OUT_CSV="$RECORD_DIR/corners/results.csv"
JOBS="${PEX_JOBS:-4}"
ARMS="${PEX_ARMS:-postlayout schematic}"

mkdir -p "$RECORD_DIR/corners"

# This DUT reaches only sg13_hv_nmos/pmos (PSP103) and rppd/rhigh (r3_cmc).
# No cap_cmomi/cap_cmomf instance exists on either arm -- the routed cell has
# no MOM cap drawn, and the schematic arm strips XCDECAP for the reason the
# original campaign's run.sh states -- so those two OSDI objects are
# deliberately not loaded (see ../../PORTING-osdi-host-arch.md).
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

# --- arm inputs -------------------------------------------------------------

# postlayout: the extracted netlist, made ngspice-parseable by exactly the
# three mechanical transforms ./pex-to-ngspice.py documents and self-checks.
python3 "$HERE/pex-to-ngspice.py" "$SNAP/pll_vco.pex.spice" "$WORK/vco_pex.spice"
python3 "$HERE/make-inst.py" "$WORK/vco_pex.spice" pll_vco vco \
  VCTRL=vctrl B0=b0 B1=b1 CLK=clk VDD_VCO=vdd GND_VCO=0 > "$WORK/vco_inst.spice"

# schematic: byte-identical derivation to the original campaign's own run.sh
# -- the frozen export with XCDECAP commented out, nothing else.
sed -e '/^XCDECAP/ s/^/*/' \
  "$SIM_ROOT/sg13cmos5l-vco-kvco-table/netlist-snapshots/vco.spice" \
  > "$WORK/vco_open.spice"

# --- the ratified matrix, copied verbatim from the original campaign --------

BUNDLES=(
  "typ  mos_tt res_typ 27"
  "slow mos_ss res_wcs 125"
  "fast mos_ff res_bcs -40"
)
BAND_CODES=(
  "00 0.0 0.0"
  "10 3.3 0.0"
  "01 0.0 3.3"
  "11 3.3 3.3"
)
VCTRL_POINTS=(0.3 0.9 1.5 2.1 2.7)

run_one() {
  local arm="$1" mos_corner="$2" res_corner="$3" temp="$4" b0v="$5" b1v="$6" vctrl="$7"
  local tmpl name
  case "$arm" in
    postlayout) tmpl="$HERE/tb_vco_kvco_pex.sp.tmpl" ;;
    schematic)  tmpl="$HERE/tb_vco_kvco_sch.sp.tmpl" ;;
    *) echo "unknown arm $arm" >&2; return 1 ;;
  esac
  name="tb_${arm}_${mos_corner}_${res_corner}_${temp}_${b0v}_${b1v}_${vctrl}.sp"
  sed -e "s/@CORNER_MOS@/$mos_corner/" -e "s/@CORNER_RES@/$res_corner/" \
      -e "s/@TEMP@/$temp/" -e "s/@VCTRL@/$vctrl/" \
      -e "s/@B0V@/$b0v/" -e "s/@B1V@/$b1v/" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|" -e "s|@PDK@|$PDK|" \
    "$tmpl" > "$WORK/$name"
  # Do not silently discard ngspice's stderr (issue #43): a fatal error must
  # be visible, not masked into an "NA" indistinguishable from real behavior.
  local err="$WORK/${name}.err" out
  if ! out="$(cd "$WORK" && ngspice -b "$name" 2>"$err")"; then
    echo "ERROR: ngspice exited non-zero for $name:" >&2
    tail -20 "$err" >&2
    return 1
  fi
  printf '%s\n' "$out" | grep -E '^per1 = ' | awk '{print $3}'
}

# One worker per (arm, bundle, band, vctrl) point, written to its own result
# file so the parallel fan-out below can never interleave CSV lines.
worker() {
  local arm="$1" bname="$2" mos="$3" res="$4" temp="$5" blabel="$6" b0v="$7" b1v="$8" vctrl="$9"
  local tag="${arm}_${bname}_${blabel}_${vctrl}"
  local period
  # Resume: a point already solved in a persistent PEX_WORK is not re-run.
  if [[ -s "$WORK/res.$tag" ]]; then
    echo "resume: ${tag} already solved -- $(cat "$WORK/res.$tag")" >&2
    return 0
  fi
  period="$(run_one "$arm" "$mos" "$res" "$temp" "$b0v" "$b1v" "$vctrl" || true)"
  if [[ -z "$period" ]]; then
    echo "WARNING: no oscillation measured at ${arm}/${bname}/${blabel}/VCTRL=${vctrl} -- recording NA" >&2
    echo "${arm},${bname},${mos},${res},${temp},${blabel},${vctrl},NA,NA" > "$WORK/res.$tag"
    return 0
  fi
  local freq
  freq="$(python3 -c "print(1.0/${period})")"
  echo "${arm},${bname},${mos},${res},${temp},${blabel},${vctrl},${period},${freq}" > "$WORK/res.$tag"
  echo "${arm} ${bname}/${blabel} VCTRL=${vctrl}: period=${period}s freq=${freq}Hz" >&2
}

pids=()
throttle() {
  while (( $(jobs -rp | wc -l) >= JOBS )); do sleep 2; done
}

for arm in $ARMS; do
  for bundle in "${BUNDLES[@]}"; do
    read -r bname mos_corner res_corner temp <<< "$bundle"
    for band in "${BAND_CODES[@]}"; do
      read -r blabel b0v b1v <<< "$band"
      for vctrl in "${VCTRL_POINTS[@]}"; do
        throttle
        worker "$arm" "$bname" "$mos_corner" "$res_corner" "$temp" \
               "$blabel" "$b0v" "$b1v" "$vctrl" &
        pids+=($!)
      done
    done
  done
done
wait

{
  echo "arm,pvt_bundle,mos_corner,res_corner,temp_c,band_code,vctrl_v,period_s,freq_hz"
  # Sorted so the committed CSV is deterministic regardless of completion order.
  cat "$WORK"/res.* | LC_ALL=C sort
} > "$OUT_CSV"

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
