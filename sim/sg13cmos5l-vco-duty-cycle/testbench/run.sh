#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-vco-duty-cycle/testbench/run.sh
# (issue #27, Part of #16 -- SG13CMOS5L closed-loop PVT campaign)
#
# Runs the open-loop VCO output duty-cycle sweep this record's
# ../records/RECORD-001 describes (spec/porting-plan.md row 13), and writes
# ../corners/results.csv. Each run also records the ring's own average supply
# current at that operating point -- a real measured input to row 11's power
# budget, carried in the same CSV rather than re-simulated separately.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Matrix (see ../corners/matrix.md): 5 MOS corners (INCLUDING the split
# mos_sf/mos_fs corners the Kvco record named as its own open duty-cycle
# axis) x 3 temperatures x 4 band codes x 5 VCTRL points = 300 transient
# runs.
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

OUT_CSV="$RECORD_DIR/corners/results.csv"

# Same OSDI set (and the same reason for its shape) as the Kvco record: the
# XCDECAP strip below removes the only cap_cmomi instance in this DUT, so no
# MOM-cap model is loaded here and none is needed.
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

# XCDECAP strip: identical derivation, and identical justification, to the
# sg13cmos5l-vco-kvco-table record -- VDD_VCO/GND_VCO are driven by ideal
# zero-impedance sources here too, so XCDECAP cannot affect any node voltage
# or supply current this deck measures. The frozen snapshot is not edited.
sed -e '/^XCDECAP/ s/^/*/' "$RECORD_DIR/netlist-snapshots/vco.spice" > "$WORK/vco_open.spice"

# "mos_corner res_corner" pairs. The three bundled pairs match the Kvco
# record's own bundles; mos_sf/mos_fs are run against res_typ because they
# are a device-symmetry (NMOS-vs-PMOS) axis, not a resistor axis.
MOS_PAIRS=(
  "mos_tt res_typ"
  "mos_ss res_wcs"
  "mos_ff res_bcs"
  "mos_sf res_typ"
  "mos_fs res_typ"
)
TEMPS=(-40 27 125)
BAND_CODES=(
  "00 0.0 0.0"
  "10 3.3 0.0"
  "01 0.0 3.3"
  "11 3.3 3.3"
)
VCTRL_POINTS=(0.3 0.9 1.5 2.1 2.7)
TSTEP=20p

echo "mos_corner,res_corner,temp_c,band_code,vctrl_v,period_s,thigh_s,duty_pct,period2_s,thigh2_s,duty2_pct,idd_avg_a" > "$OUT_CSV"

run_one() {
  local mos="$1" res="$2" temp="$3" b0v="$4" b1v="$5" vctrl="$6" tstep="$7"
  local name="tb_${mos}_${res}_${temp}_${b0v}_${b1v}_${vctrl}_${tstep}.sp"
  sed -e "s/@CORNER_MOS@/$mos/" -e "s/@CORNER_RES@/$res/" -e "s/@TEMP@/$temp/" \
      -e "s/@VCTRL@/$vctrl/" -e "s/@B0V@/$b0v/" -e "s/@B1V@/$b1v/" \
      -e "s/@TSTEP@/$tstep/" \
      -e "s#@PDK_ROOT@#$PDK_ROOT#" -e "s#@PDK@#$PDK#" \
    "$HERE/tb_vco_duty.sp.tmpl" > "$WORK/$name"
  local errlog="$WORK/${name%.sp}.err"
  local out
  if ! out="$( cd "$WORK" && ngspice -b "$name" 2>"$errlog" )"; then
    echo "ngspice failed for $name; stderr:" >&2
    cat "$errlog" >&2
    return 1
  fi
  printf '%s\n' "$out"
}

# The extractor is written to a file rather than fed to `python3 -` from a
# heredoc: a heredoc occupies stdin, which would shadow the piped ngspice
# output the extractor is supposed to read (and kill ngspice with SIGPIPE).
cat > "$WORK/extract.py" <<'PY'
import re, sys
txt = sys.stdin.read()
def g(name):
    m = re.search(rf"^{name}\s*=\s*(\S+)\s*$", txt, re.M)
    return float(m.group(1)) if m else None
vals = {k: g(k) for k in ("rise1","fall1","rise2","rise3","fall3","rise4","idd_avg")}
if any(v is None for v in vals.values()):
    print("NA,NA,NA,NA,NA,NA,NA"); raise SystemExit
per  = vals["rise2"] - vals["rise1"]
thi  = vals["fall1"] - vals["rise1"]
per2 = vals["rise4"] - vals["rise3"]
thi2 = vals["fall3"] - vals["rise3"]
if per <= 0 or thi <= 0 or per2 <= 0 or thi2 <= 0:
    print("NA,NA,NA,NA,NA,NA,NA"); raise SystemExit
print(f"{per:.6e},{thi:.6e},{100*thi/per:.4f},{per2:.6e},{thi2:.6e},"
      f"{100*thi2/per2:.4f},{abs(vals['idd_avg']):.6e}")
PY

extract() {
  python3 "$WORK/extract.py"
}

n=0
for pair in "${MOS_PAIRS[@]}"; do
  read -r mos res <<< "$pair"
  for temp in "${TEMPS[@]}"; do
    for band in "${BAND_CODES[@]}"; do
      read -r blabel b0v b1v <<< "$band"
      for vctrl in "${VCTRL_POINTS[@]}"; do
        out="$(run_one "$mos" "$res" "$temp" "$b0v" "$b1v" "$vctrl" "$TSTEP" | extract)"
        echo "${mos},${res},${temp},${blabel},${vctrl},${out}" >> "$OUT_CSV"
        n=$((n + 1))
        echo "[$n] ${mos}/${temp}C/${blabel}/${vctrl}: ${out}" >&2
      done
    done
  done
done

# Timestep-convergence cross-check: the duty-cycle number is a difference of
# two interpolated threshold crossings, so it is the one measurement in this
# record whose value could plausibly be a discretisation artifact. Re-run a
# few representative points at 4x finer resolution and record both, so the
# record can state the observed sensitivity instead of asserting it is small.
echo "mos_corner,res_corner,temp_c,band_code,vctrl_v,tstep,duty_pct" \
  > "$RECORD_DIR/corners/tstep_convergence.csv"
for tstep in 20p 5p; do
  for probe in "mos_tt res_typ 27 00 0.0 0.0 1.5" \
               "mos_sf res_typ 27 11 3.3 3.3 2.7" \
               "mos_fs res_typ 27 11 3.3 3.3 2.7" \
               "mos_ss res_wcs 125 00 0.0 0.0 0.9"; do
    read -r mos res temp blabel b0v b1v vctrl <<< "$probe"
    out="$(run_one "$mos" "$res" "$temp" "$b0v" "$b1v" "$vctrl" "$tstep" | extract)"
    duty="$(echo "$out" | cut -d, -f3)"
    echo "${mos},${res},${temp},${blabel},${vctrl},${tstep},${duty}" \
      >> "$RECORD_DIR/corners/tstep_convergence.csv"
    echo "[conv ${tstep}] ${mos}/${temp}C/${blabel}/${vctrl}: duty=${duty}" >&2
  done
done

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
