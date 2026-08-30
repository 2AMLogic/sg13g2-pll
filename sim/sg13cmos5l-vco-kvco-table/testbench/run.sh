#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-vco-kvco-table/testbench/run.sh
# (issue #23, Part of #16 -- SG13CMOS5L PVT-cornered sim campaign)
#
# Runs the open-loop VCO frequency-vs-VCTRL-vs-band-code sweep this record's
# ../records/RECORD-001 describes (spec/porting-plan.md row 4/5, the
# Kvco-vs-band-code table), and writes the raw per-run results to
# ../corners/results.csv.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Matrix (see ../corners/matrix.md for the full rationale):
#   3 PVT bundles (typ/slow/fast) x 4 band codes (B0,B1 in {00,01,10,11}) x
#   5 VCTRL points (0.3/0.9/1.5/2.1/2.7 V) = 60 transient runs.
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

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"

# This testbench's DUT (the ring + bias core) uses only sg13_hv_nmos/pmos
# (PSP103, via psp103.osdi/psp103_nqs.osdi/mosvar.osdi) and rppd/rhigh (via
# r3_cmc.osdi) -- no cap_cmomi/cap_cmomf instance survives the XCDECAP-strip
# below, so this .spiceinit deliberately does NOT load cap_cmomi.osdi/
# cap_cmomf.osdi (see "Why XCDECAP is stripped" below for why that is safe
# for this specific claim, and a host-specific finding worth recording: on
# at least one build of this installed PDK, cap_cmomi.osdi/cap_cmomf.osdi
# are x86-64 ELF shared objects that fail `dlopen` on an arm64 host --
# "slice is not valid mach-o file" -- while psp103.osdi/psp103_nqs.osdi/
# mosvar.osdi/r3_cmc.osdi are all native Mach-O arm64 and load cleanly. This
# is orthogonal to this record's own claim and is not fixed or routed around
# here; it simply does not block a testbench that never needs cap_cmomi.
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

# Why XCDECAP is stripped: this testbench drives VDD_VCO/GND_VCO with ideal,
# zero-impedance DC voltage sources (Vdd/node 0 below) -- an ideal voltage
# source enforces the node voltage regardless of any capacitance in
# parallel with it, so XCDECAP's own value (or even its presence) cannot
# affect any node voltage this testbench measures. This is a testbench-local
# derivation from the frozen ../netlist-snapshots/vco.spice (which stays an
# exact, unmodified export), not an edit to the design itself, and it makes
# no claim whatsoever about XCDECAP's own MOM-cap sensitivity -- that claim
# is already covered by the separate sg13cmos5l-vco-decap-momcap record.
sed -e '/^XCDECAP/ s/^/*/' "$RECORD_DIR/netlist-snapshots/vco.spice" > "$WORK/vco_open.spice"

# 3 correlated PVT bundles, not the full 5(mos) x 3(res) x 3(temp) cross
# product -- see ../corners/matrix.md for the explicit subset rationale.
#   name   mos-corner  res-corner  temp
BUNDLES=(
  "typ  mos_tt res_typ 27"
  "slow mos_ss res_wcs 125"
  "fast mos_ff res_bcs -40"
)

# (label, B0 volts, B1 volts) -- 2-bit band select, each bit either 0V or 3.3V
BAND_CODES=(
  "00 0.0 0.0"
  "10 3.3 0.0"
  "01 0.0 3.3"
  "11 3.3 3.3"
)

VCTRL_POINTS=(0.3 0.9 1.5 2.1 2.7)

echo "pvt_bundle,mos_corner,res_corner,temp_c,band_code,vctrl_v,period_s,freq_hz" > "$OUT_CSV"

run_one() {
  local mos_corner="$1" res_corner="$2" temp="$3" b0v="$4" b1v="$5" vctrl="$6"
  local name="tb_${mos_corner}_${res_corner}_${temp}_${b0v}_${b1v}_${vctrl}.sp"
  sed -e "s/@CORNER_MOS@/$mos_corner/" -e "s/@CORNER_RES@/$res_corner/" \
      -e "s/@TEMP@/$temp/" -e "s/@VCTRL@/$vctrl/" \
      -e "s/@B0V@/$b0v/" -e "s/@B1V@/$b1v/" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|" -e "s|@PDK@|$PDK|" \
    "$HERE/tb_vco_kvco.sp.tmpl" > "$WORK/$name"
  # Do not silently discard ngspice's stderr (issue #43): a fatal error (e.g.
  # an unresolved .lib path) must be visible, not masked into a "no
  # oscillation measured" NA result indistinguishable from real behavior.
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
  read -r bname mos_corner res_corner temp <<< "$bundle"
  for band in "${BAND_CODES[@]}"; do
    read -r blabel b0v b1v <<< "$band"
    for vctrl in "${VCTRL_POINTS[@]}"; do
      period="$(run_one "$mos_corner" "$res_corner" "$temp" "$b0v" "$b1v" "$vctrl" || true)"
      if [[ -z "$period" ]]; then
        echo "WARNING: no oscillation measured at ${bname}/${blabel}/VCTRL=${vctrl} -- recording NA" >&2
        echo "${bname},${mos_corner},${res_corner},${temp},${blabel},${vctrl},NA,NA" >> "$OUT_CSV"
        continue
      fi
      freq="$(python3 -c "print(1.0/${period})")"
      echo "${bname},${mos_corner},${res_corner},${temp},${blabel},${vctrl},${period},${freq}" >> "$OUT_CSV"
      echo "${bname}/${blabel} VCTRL=${vctrl}: period=${period}s freq=${freq}Hz" >&2
    done
  done
done

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
