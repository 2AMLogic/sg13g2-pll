#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-vco-kvco-table/testbench/run.sh
# (issue #97 -- SG13G2 PVT-cornered sim campaign, the SG13G2 twin of
# sg13cmos5l-vco-kvco-table/ issue #23, Part of #16)
#
# Runs the open-loop VCO frequency-vs-VCTRL-vs-band-code sweep this record's
# ../records/RECORD-001 describes (spec/porting-plan.md row 1/4/5, the
# output band / Kvco-vs-band-code table), and writes the raw per-run results
# to ../corners/results.csv.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
#   export PDK=ihp-sg13g2
#   ./run.sh
#
# Matrix (see ../corners/matrix.md for the full rationale):
#   3 PVT bundles (typ/slow/fast) x 4 band codes (B0,B1 in {00,01,10,11}) x
#   5 VCTRL points (0.3/0.9/1.5/2.1/2.7 V) = 60 transient runs, at a fixed
#   3.3V supply (DR-002).
#
# Requires: ngspice on PATH, PDK_ROOT/PDK resolving the installed
# ihp-sg13g2 tree (same variables design/netlist.sh reads).

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

OUT_CSV="$RECORD_DIR/corners/results.csv"
DUT="$RECORD_DIR/netlist-snapshots/vco.spice"

# ---------------------------------------------------------------------------
# 0. OSDI preflight -- hard abort only, no --soft.
#
# Unlike the SG13CMOS5L sibling (whose cap_cmomi/cap_cmomf ship as prebuilt
# x86-64 ELF tracked files that can be the wrong architecture on an arm64
# host, sim/PORTING-osdi-host-arch.md), SG13G2's cap_cmim has NO OSDI object
# at all -- it is a plain SPICE .subckt (capacitors_mod.lib, resolved via
# cornerCAP.lib below), confirmed directly against the installed ihp-sg13g2
# tree. The four OSDI objects this script DOES load (psp103, psp103_nqs,
# mosvar, r3_cmc) are native BUILD PRODUCTS of the ihp-sg13g2 tree itself on
# every host that installed the PDK correctly, so this preflight stays a
# plain hard-abort call with no --soft names, mirroring
# sim/sg13g2-lock-detector-window/testbench/run.sh's identical preflight.
# ---------------------------------------------------------------------------
"$HERE/../../tools/check-osdi-arch.sh" --quiet \
  "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" "$OSDI/r3_cmc.osdi"

cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

# 3 correlated PVT bundles, not the full 5(mos) x 3(res) x 3(cap) x 3(temp)
# cross product -- see ../corners/matrix.md for the explicit subset
# rationale (mirrors the SG13CMOS5L sibling's own 3-bundle convention, with
# a cap_cmim process corner bundled in as this PDK's third axis).
#   name   mos-corner  res-corner  cap-corner  temp
BUNDLES=(
  "typ  mos_tt res_typ cap_typ 27"
  "slow mos_ss res_wcs cap_wcs 125"
  "fast mos_ff res_bcs cap_bcs -40"
)

# (label, B0 volts, B1 volts) -- 2-bit band select, each bit either 0V or 3.3V
BAND_CODES=(
  "00 0.0 0.0"
  "10 3.3 0.0"
  "01 0.0 3.3"
  "11 3.3 3.3"
)

VCTRL_POINTS=(0.3 0.9 1.5 2.1 2.7)

echo "pvt_bundle,mos_corner,res_corner,cap_corner,temp_c,band_code,vctrl_v,period_s,freq_hz" > "$OUT_CSV"

run_one() {
  local mos_corner="$1" res_corner="$2" cap_corner="$3" temp="$4" b0v="$5" b1v="$6" vctrl="$7"
  local name="tb_${mos_corner}_${res_corner}_${cap_corner}_${temp}_${b0v}_${b1v}_${vctrl}.sp"
  sed -e "s/@CORNER_MOS@/$mos_corner/" -e "s/@CORNER_RES@/$res_corner/" \
      -e "s/@CORNER_CAP@/$cap_corner/" \
      -e "s/@TEMP@/$temp/" -e "s/@VCTRL@/$vctrl/" \
      -e "s/@B0V@/$b0v/" -e "s/@B1V@/$b1v/" \
      -e "s|@DUT@|$DUT|" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|" -e "s|@PDK@|$PDK|" \
    "$HERE/tb_vco_kvco.sp.tmpl" > "$WORK/$name"
  # Do not silently discard ngspice's stderr (SG13CMOS5L sibling issue #43):
  # a fatal error (e.g. an unresolved .lib path) must be visible, not masked
  # into a "no oscillation measured" NA result indistinguishable from real
  # behavior.
  local err="$WORK/${name}.err"
  local out
  if ! out="$(cd "$WORK" && ngspice -b "$name" 2>"$err")"; then
    echo "ERROR: ngspice exited non-zero for $name:" >&2
    cat "$err" >&2
    return 1
  fi
  printf '%s\n' "$out" | grep -E '^per1 = ' | awk '{print $3}'
}

for bundle in "${BUNDLES[@]}"; do
  read -r bname mos_corner res_corner cap_corner temp <<< "$bundle"
  for band in "${BAND_CODES[@]}"; do
    read -r blabel b0v b1v <<< "$band"
    for vctrl in "${VCTRL_POINTS[@]}"; do
      period="$(run_one "$mos_corner" "$res_corner" "$cap_corner" "$temp" "$b0v" "$b1v" "$vctrl" || true)"
      if [[ -z "$period" ]]; then
        echo "WARNING: no oscillation measured at ${bname}/${blabel}/VCTRL=${vctrl} -- recording NA" >&2
        echo "${bname},${mos_corner},${res_corner},${cap_corner},${temp},${blabel},${vctrl},NA,NA" >> "$OUT_CSV"
        continue
      fi
      freq="$(python3 -c "print(1.0/${period})")"
      echo "${bname},${mos_corner},${res_corner},${cap_corner},${temp},${blabel},${vctrl},${period},${freq}" >> "$OUT_CSV"
      echo "${bname}/${blabel} VCTRL=${vctrl}: period=${period}s freq=${freq}Hz" >&2
    done
  done
done

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
