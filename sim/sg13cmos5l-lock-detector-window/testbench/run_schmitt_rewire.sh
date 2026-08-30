#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/run_schmitt_rewire.sh
# (issue #66, Part of #16)
#
# BEFORE/AFTER evidence for issue #66's schmitt_hv feedback rewiring, on BOTH
# PDKs, from ONE script.
#
# ../records/RECORD-002 found (by scratch control, not by argument) that
# schmitt_hv's two feedback devices were tied to the SAME rail as their own
# series stack:
#
#     XMP3 np  OUT VDD VDD      <-- drain np, source VDD
#     XMN3 nn  OUT VSS VSS      <-- drain nn, source VSS
#
# A six-transistor CMOS Schmitt trigger gets its hysteresis from feedback
# devices tied to the OPPOSITE rail, so as drawn the cell had no state memory
# at all.  Issue #66 LANDS the classic connection in both
# design/sg13cmos5l/schmitt_hv.sch and design/schmitt_hv.sch:
#
#     XMP3 VSS OUT np  VDD
#     XMN3 VDD OUT nn  VSS
#
# This script measures the committed (fixed) cell and, as its control, the
# as-drawn cell reconstructed by REVERSING those two substitutions in a temp
# copy -- the mirror image of the way RECORD-002's own diagnostic built the
# fix as a scratch control on the as-drawn netlist.  Nothing is ever written
# back into design/.
#
# Both PDKs are run because the defect was in the cell on both and issue #66
# fixes both: ihp-sg13cmos5l (design/sg13cmos5l/netlist/lock_detector.spice)
# and ihp-sg13g2 (design/netlist/lock_detector.spice).  ../testbench/
# tb_schmitt_rewire.sp.tmpl instantiates ONLY the schmitt_hv subcircuit and
# includes no capacitor model, which is what lets one deck cover both PDKs --
# SG13G2 has no cap_cmomi (DR-003 Finding 2) and CMOS5L has no cap_cmim.
#
# Grid: 3 MOS corners x 3 temperatures x 3 supplies = 27 points per (PDK, DUT),
# 108 rows.  No resistor-corner and no MOM axis: schmitt_hv contains neither a
# resistor nor a capacitor instance (stated here rather than silently dropped,
# per ../corners/matrix.md).
#
# Writes ../corners/schmitt_rewire.csv.  It does NOT touch
# ../corners/schmitt.csv (RECORD-001), ../corners/schmitt_resized.csv
# (RECORD-002), or ../corners/hysteresis_diag_schmitt.csv (RECORD-002) --
# sim/README.md's evidence is append-only.
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing BOTH PDK trees
#   ./run_schmitt_rewire.sh
#
# Requires: ngspice on PATH, python3, and PDK_ROOT resolving BOTH
# ihp-sg13cmos5l/ and ihp-sg13g2/.  Runtime: ~2 min.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$RECORD_DIR/../.." && pwd)"
CORNERS="$RECORD_DIR/corners"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/ and ihp-sg13g2/}"

# Reverse the landed fix to rebuild the as-drawn control.  Fails loudly if the
# committed netlist does not carry the fixed lines -- that would mean this
# script is measuring something other than what it claims to.
as_drawn() {  # as_drawn <fixed-netlist> <out>
  python3 - "$1" "$2" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()
subs = [
    ("XMP3 VSS OUT np VDD sg13_hv_pmos", "XMP3 np OUT VDD VDD sg13_hv_pmos"),
    ("XMN3 VDD OUT nn VSS sg13_hv_nmos", "XMN3 nn OUT VSS VSS sg13_hv_nmos"),
]
for new, old in subs:
    if new not in text:
        raise SystemExit(
            "run_schmitt_rewire: expected the LANDED feedback connection %r in "
            "%s -- refusing to build an 'as drawn' control from a netlist that "
            "is not the fixed one." % (new, src))
    text = text.replace(new, old)
open(dst, "w").write(text)
PY
}

echo "pdk,dut,mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd" \
  > "$CORNERS/schmitt_rewire.csv"

for pair in "ihp-sg13cmos5l design/sg13cmos5l/netlist/lock_detector.spice" \
            "ihp-sg13g2     design/netlist/lock_detector.spice"; do
  read -r pdk rel <<< "$pair"
  net="$REPO_ROOT/$rel"
  [ -f "$net" ] || { echo "ERROR: missing netlist $net" >&2; exit 1; }

  OSDI="$PDK_ROOT/$pdk/libs.tech/ngspice/osdi"
  # Only the MOS models are referenced by this deck, so only those four objects
  # are preflighted -- and they stay HARD (there is no substitute for a MOS
  # model).  cap_cmomi is deliberately NOT on the list: this deck never
  # instantiates a capacitor, and SG13G2 does not ship the object at all.
  "$HERE/../../tools/check-osdi-arch.sh" --quiet \
    "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" \
    "$OSDI/r3_cmc.osdi"
  {
    echo "osdi $OSDI/psp103.osdi"
    echo "osdi $OSDI/psp103_nqs.osdi"
    echo "osdi $OSDI/mosvar.osdi"
    echo "osdi $OSDI/r3_cmc.osdi"
    echo "set num_threads=1"   # see run.sh's TOOLING NOTE
  } > "$WORK/.spiceinit"

  cp "$net" "$WORK/dut_rewired.spice"
  as_drawn "$net" "$WORK/dut_as_drawn.spice"

  for dut in dut_as_drawn dut_rewired; do
    label="$([ "$dut" = dut_as_drawn ] && echo as_drawn || echo feedback_rewired)"
    for mos in mos_tt mos_ff mos_ss; do
      for temp in -40 27 125; do
        for vsup in 2.97 3.3 3.63; do
          vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
          sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@TEMP@/$temp/g" \
              -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" \
              -e "s|@DUT@|$WORK/${dut}.spice|g" \
              -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$pdk|g" \
            "$HERE/tb_schmitt_rewire.sp.tmpl" > "$WORK/s.sp"
          err="$WORK/s.err"
          if ! slog="$( cd "$WORK" && ngspice -b s.sp 2>"$err" )"; then
            echo "ERROR: ngspice exited non-zero for ${pdk}/${label}/${mos}/${temp}C/${vsup}V:" >&2
            cat "$err" >&2
            exit 1
          fi
          vup="$(printf '%s\n' "$slog" | sed -n 's/^vth_up *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
          vdn="$(printf '%s\n' "$slog" | sed -n 's/^vth_dn *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
          row="$(python3 -c "
u='${vup:-}'; d='${vdn:-}'
if u and d:
    h=float(u)-float(d)
    print('%s,%s,%.6e,%.4f' % (u, d, h, 100*h/float('$vsup')))
else:
    print('NA,NA,NA,NA')")"
          echo "${pdk},${label},${mos},${temp},${vsup},${row}" \
            >> "$CORNERS/schmitt_rewire.csv"
          echo "[${pdk}/${label}] ${mos}/${temp}C/${vsup}V: ${row}" >&2
        done
      done
    done
  done
done

echo "done: $(wc -l < "$CORNERS/schmitt_rewire.csv") lines (incl. header) -> $CORNERS/schmitt_rewire.csv" >&2
