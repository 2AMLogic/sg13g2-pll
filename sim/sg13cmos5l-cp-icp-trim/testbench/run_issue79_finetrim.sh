#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim/testbench/run_issue79_finetrim.sh
# (issue #79, Part of #16 -- closes the band=00/low/f_ref=4.5MHz PM gap
# ../../sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md
# left open)
#
# A TARGETED addition to the trim-code ladder ../testbench/run.sh already
# characterises (2.5/5/10/20/40/80 uA), NOT a re-run of that full campaign,
# and a SEPARATE addition from issue #83's own 3.75 uA code (a different
# operating-point tuple -- band=00, MID interval, not LOW). `cp.sch` has no
# on-chip Icp trim array (design/README.md) -- the "trim code" is an
# external mirror reference current an (not-yet-drawn) bias generator would
# deliver, so any value is a legitimate measurement, not a hardware-
# infeasible one (../corners/matrix.md).
#
# This script measures exactly ONE new code (11 uA) at all THREE PVT points
# issue #79's gap needs -- unlike issue #83's gap (reachable at only the
# `slow` bundle), RECORD-002 found band=00/low/f_ref=4.5MHz reachable at
# ALL THREE bundles (n_div=127/114/103 for fast/typ/slow respectively), so
# this script measures `mos_ff/-40C`, `mos_tt/27C`, `mos_ss/125C` -- the
# three PVT points ../../sg13cmos5l-loop-bandwidth-pm/testbench/run.sh's own
# BUNDLES table maps `fast`/`typ`/`slow` to -- all at 3.3 V.
#
# Why 11 uA: ../../sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md
# found the existing 10 uA code passes for `typ`/`slow` but falls 0.87 deg
# short of the 45 deg PM floor for `fast` (44.127 deg, the binding bundle at
# this tuple), while 20 uA clears PM everywhere but blows the fc ceiling for
# ALL THREE bundles. A real-subckt scan (see
# spec/decision-records/DR-008-cp-icp-trim-fine-code-band00-low-fref4p5.md
# "Decision") found the feasible window bounded by two DIFFERENT bundles at
# each edge -- `fast`'s PM=45 deg floor near 10.6 uA, `slow`'s fc=ceiling
# near 11.47 uA -- and chose 11 uA, close to that window's own arithmetic
# midpoint (~11.05 uA), for balanced real margin on both binding
# constraints simultaneously.
#
# Writes ../corners/results_issue79_finetrim.csv (same 7-column schema as
# ../corners/results.csv, kept in a SEPARATE file per this repo's
# append-only evidence convention -- ../corners/results.csv,
# ../corners/results_issue83_finetrim.csv, and ../corners/compliance.csv
# are none of them touched).
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_issue79_finetrim.sh

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

OUT_CSV="$RECORD_DIR/corners/results_issue79_finetrim.csv"

cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

cp "$RECORD_DIR/netlist-snapshots/cp.spice" "$WORK/cp_snap.spice"

IREF="11u"

# (mos_corner, temp_c) pairs -- the three PVT points
# ../../sg13cmos5l-loop-bandwidth-pm/testbench/run.sh's own BUNDLES table
# maps fast/typ/slow to, all at VDD=3.3V (the sole supply RECORD-002's
# band=00/low/f_ref=4.5MHz tuple was measured at).
PVT_POINTS=(
  "mos_ff -40"
  "mos_tt 27"
  "mos_ss 125"
)

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
VDD="3.3"
for pvt in "${PVT_POINTS[@]}"; do
  read -r MOS TEMP <<< "$pvt"
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
done

echo "wrote $(wc -l < "$OUT_CSV") lines to $OUT_CSV" >&2
