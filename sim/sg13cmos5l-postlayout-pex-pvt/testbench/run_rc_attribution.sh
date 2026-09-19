#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/run_rc_attribution.sh
# (issue #30, Part of #16 -- post-layout PEX + PVT re-simulation)
#
# DIAGNOSTIC, not a design measurement. ../corners/deviation.csv establishes
# that the parasitic-annotated `pll_vco` oscillates at 0.477-0.531x its own
# schematic frequency across the whole ratified matrix. This script answers
# the next question -- "which parasitic did that?" -- by re-running a subset
# of the same matrix against four deliberately-degraded variants of the SAME
# extracted netlist:
#
#   full    every extracted element, i.e. ../corners/results.csv's own
#           post-layout arm, re-run here as this script's own control
#   c_only  every parasitic RESISTOR shorted (R -> 1e-6 ohm), every
#           capacitor kept
#   r_only  every parasitic CAPACITOR removed, every resistor kept
#   none    both removed -- the extracted DEVICE netlist with no interconnect
#           parasitics at all
#
# plus three FLOORPLAN-SENSITIVITY variants, `cscale25`/`cscale10`/`cscale05`,
# which keep every parasitic resistor and multiply every parasitic capacitance
# by 0.25 / 0.10 / 0.05.
#
# Those three are a PARAMETRIC SENSITIVITY, NOT A PREDICTION, and the record
# must not read them as one. They exist because this port's routing flow
# (`layout/bin/cmos5l_route.py`) draws 7177.9 um of 0.3 um wire for a ~45-
# device ring VCO -- 413.1 um of it on `ring1` alone, a node a compact ring
# layout would close in a few microns. The extracted capacitance is therefore
# an upper bound set by routing style, not by the circuit, and "how far does
# the conclusion move if the wire were k times shorter" is the only honest way
# this record can say how much of its own headline number is floorplan
# artifact. A uniform scalar on C is a crude stand-in for that (it scales the
# device-adjacent and via capacitance too, which a shorter route would not),
# so the variants bracket rather than estimate.
#
# `none` is the load-bearing one: it isolates how much of the deviation is
# interconnect at all, versus how much is the difference between the
# extracted devices' own geometry (drawn W/L plus junction AS/AD/PS/PD, which
# the schematic netlist does not carry) and the schematic devices'. Without
# it, a reader cannot tell "the wires did this" from "the extracted junctions
# did this", and this record would be claiming the former on evidence that
# only supports "one of the two".
#
# Only the parasitic R/C cards are touched. `M`/`X` device cards, their
# parameters, the subcircuit's pin list, and the testbench are byte-identical
# across all four variants -- the transforms are asserted by count, and the
# script fails rather than writing a variant whose device cards moved.
#
#   export PDK_ROOT=/path/to/pdk/root
#   export PDK=ihp-sg13cmos5l
#   ./run_rc_attribution.sh
#
# Output: ../corners/rc_attribution.csv

WORK="${RCATTR_WORK:-}"
# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SNAP="$RECORD_DIR/netlist-snapshots"
OUT_CSV="$RECORD_DIR/corners/rc_attribution.csv"
JOBS="${RCATTR_JOBS:-4}"
THREADS="${PEX_OMP_THREADS:-1}"
export OMP_NUM_THREADS="$THREADS"

mkdir -p "$RECORD_DIR/corners"

cat > "$WORK/.spiceinit" <<EOF
set num_threads=$THREADS
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOF

python3 "$HERE/pex-to-ngspice.py" "$SNAP/pll_vco.pex.spice" "$WORK/vco_full.spice"
python3 "$HERE/make-inst.py" "$WORK/vco_full.spice" pll_vco vco \
  VCTRL=vctrl B0=b0 B1=b1 CLK=clk VDD_VCO=vdd GND_VCO=0 > "$WORK/vco_inst.spice"

# --- the four variants ------------------------------------------------------
python3 - "$WORK" <<'PY'
import os, re, sys

work = sys.argv[1]
src = open(os.path.join(work, "vco_full.spice")).read().splitlines()

# A two-terminal parasitic resistor card klt emits: `R$t0 a b 1.57`
# (no model name -- the PDK resistor DEVICES were already rebound to X cards
# by pex-to-ngspice.py, so anything still matching this is interconnect).
par_r = re.compile(r"^(R\S+\s+\S+\s+\S+\s+)([-+0-9.eE]+)\s*$")
# `C<name> <n+> <n-> <value>` -- klt writes plain two-terminal parasitic
# capacitors, net-to-substrate and net-to-net alike.
par_c = re.compile(r"^(C\S+\s+\S+\s+\S+\s+)([-+0-9.eE]+)\s*$")
par_c_any = re.compile(r"^C\S+\s+")
dev = re.compile(r"^[MXQD]", re.I)

def build(name, short_r, drop_c, c_scale=1.0):
    out, nr, nc, nd = [], 0, 0, 0
    for ln in src:
        if dev.match(ln):
            nd += 1
        m = par_r.match(ln)
        if m:
            nr += 1
            # Shorting to 0 ohms is not representable in every ngspice
            # build's sparse matrix; 1 micro-ohm is electrically a short
            # against the 0.11-88 ohm/sq metal this deck models and keeps
            # the node count identical to the `full` variant.
            out.append(m.group(1) + ("1e-6" if short_r else m.group(2)))
            continue
        if par_c_any.match(ln):
            nc += 1
            if drop_c:
                out.append("*" + ln)
                continue
            if c_scale != 1.0:
                mc = par_c.match(ln)
                if not mc:
                    sys.exit("FATAL: unparseable parasitic C card: %r" % ln)
                out.append(mc.group(1) + repr(float(mc.group(2)) * c_scale))
                continue
        out.append(ln)
    path = os.path.join(work, "vco_%s.spice" % name)
    open(path, "w").write("\n".join(out) + "\n")
    return nr, nc, nd

base = None
for name, short_r, drop_c, c_scale in (
    ("full", False, False, 1.0),
    ("c_only", True, False, 1.0),
    ("r_only", False, True, 1.0),
    ("none", True, True, 1.0),
    ("cscale25", False, False, 0.25),
    ("cscale10", False, False, 0.10),
    ("cscale05", False, False, 0.05),
):
    counts = build(name, short_r, drop_c, c_scale)
    if base is None:
        base = counts
    elif counts != base:
        sys.exit("FATAL: variant %s changed the R/C/device card counts: %s != %s"
                 % (name, counts, base))
    print("variant %-7s %d parasitic R, %d parasitic C, %d device cards"
          % (name, counts[0], counts[1], counts[2]), file=sys.stderr)
PY

# --- matrix: all 3 ratified bundles, band 00 and 11, all 5 VCTRL points -----
# Bands 01/10 are omitted: ../corners/deviation.csv shows the deviation's
# band-to-band spread is 0.6 percentage points against a ~50 point effect,
# so the two extreme codes bracket it and the middle two add no attribution
# information. Stated here rather than silently dropped, per sim/README.md.
BUNDLES=(
  "typ  mos_tt res_typ 27"
  "slow mos_ss res_wcs 125"
  "fast mos_ff res_bcs -40"
)
BAND_CODES=("00 0.0 0.0" "11 3.3 3.3")
VCTRL_POINTS=(0.3 0.9 1.5 2.1 2.7)
VARIANTS=(full c_only r_only none cscale25 cscale10 cscale05)

worker() {
  local variant="$1" bname="$2" mos="$3" res="$4" temp="$5" blabel="$6" \
        b0v="$7" b1v="$8" vctrl="$9"
  local tag="${variant}_${bname}_${blabel}_${vctrl}"
  [[ -s "$WORK/rc.$tag" ]] && ! grep -q ',NA$' "$WORK/rc.$tag" && return 0
  local name="tbrc_${tag}.sp"
  sed -e "s/@CORNER_MOS@/$mos/" -e "s/@CORNER_RES@/$res/" \
      -e "s/@TEMP@/$temp/" -e "s/@VCTRL@/$vctrl/" \
      -e "s/@B0V@/$b0v/" -e "s/@B1V@/$b1v/" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|" -e "s|@PDK@|$PDK|" \
      -e "s|vco_pex.spice|vco_${variant}.spice|" \
    "$HERE/tb_vco_kvco_pex.sp.tmpl" > "$WORK/$name"
  local out period freq
  if out="$(cd "$WORK" && ngspice -b "$name" 2>"$WORK/${name}.err")"; then
    period="$(printf '%s\n' "$out" | grep -E '^per1 = ' | awk '{print $3}')"
  fi
  if [[ -z "${period:-}" ]]; then
    echo "WARNING: no oscillation at ${tag} -- recording NA" >&2
    echo "${variant},${bname},${mos},${res},${temp},${blabel},${vctrl},NA,NA" \
      > "$WORK/rc.$tag"
    return 0
  fi
  freq="$(python3 -c "print(1.0/${period})")"
  echo "${variant},${bname},${mos},${res},${temp},${blabel},${vctrl},${period},${freq}" \
    > "$WORK/rc.$tag"
  echo "${tag}: ${freq} Hz" >&2
}

throttle() { while (( $(jobs -rp | wc -l) >= JOBS )); do sleep 1; done; }

for variant in "${VARIANTS[@]}"; do
  for bundle in "${BUNDLES[@]}"; do
    read -r bname mos res temp <<< "$bundle"
    for band in "${BAND_CODES[@]}"; do
      read -r blabel b0v b1v <<< "$band"
      for vctrl in "${VCTRL_POINTS[@]}"; do
        throttle
        worker "$variant" "$bname" "$mos" "$res" "$temp" \
               "$blabel" "$b0v" "$b1v" "$vctrl" &
      done
    done
  done
done
wait

{
  echo "variant,pvt_bundle,mos_corner,res_corner,temp_c,band_code,vctrl_v,period_s,freq_hz"
  cat "$WORK"/rc.* | LC_ALL=C sort
} > "$OUT_CSV"

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
