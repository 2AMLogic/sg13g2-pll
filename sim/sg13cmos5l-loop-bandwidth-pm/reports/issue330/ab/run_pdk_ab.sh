#!/usr/bin/env bash
# issue #330 :: C_cp = 0 anchor, three tuples x two PDK trees (current vs the
# pre-2026-10-15 .bak tree). Six sequential single-unit `ngspice -b` runs. No grid.
# Deck = tb_loop_ac_real_resized.sp.tmpl verbatim (the RECORD-003/004 deck), inputs
# (Kd, Kv, 1/N) copied from the dr00x_<b>_nocp loop of tb_loop_ac_ccp_issue196.sp.
set -euo pipefail
R=/home/ubuntu/GitHub/sg13g2-pll/.loom/worktrees/issue-330/sim/sg13cmos5l-loop-bandwidth-pm
OUT=/home/ubuntu/GitHub/sg13g2-pll/.loom/worktrees/issue-330/sim/sg13cmos5l-loop-bandwidth-pm/reports/issue330/ab/pdk

run() { # tag pdkdir res temp kd kv invn
  local tag=$1 pdk=$2 res=$3 temp=$4 kd=$5 kv=$6 invn=$7
  local d=$OUT/$tag; mkdir -p "$d"
  cp "$R/netlist-snapshots/loop_filter_resized.spice" "$d/loop_filter_snap_resized.spice"
  printf 'osdi %s/libs.tech/ngspice/osdi/cap_cmomi.osdi\nosdi %s/libs.tech/ngspice/osdi/cap_cmomf.osdi\nosdi %s/libs.tech/ngspice/osdi/r3_cmc.osdi\n' "$pdk" "$pdk" "$pdk" > "$d/.spiceinit"
  sed -e "s#@PDK_ROOT@/@PDK@#$pdk#; s#@CORNER_RES@#$res#; s#@TEMP@#$temp#" \
      -e "s#@KD@#$kd#; s#@KV@#$kv#; s#@INVN@#$invn#; s#wrdata ac.dat#wrdata ac.dat#" \
      "$R/testbench/tb_loop_ac_real_resized.sp.tmpl" > "$d/tb.sp"
  (cd "$d" && ngspice -b tb.sp > ngspice.log 2>&1) || { echo "$tag FAILED"; return 1; }
  printf '%s ' "$tag"; python3 -I "$OUT/../pm.py" "$d/ac.dat" | sed 's#.*: ##'
}

NEW=/home/ubuntu/share/pdk/ihp-sg13cmos5l
OLD=/home/ubuntu/share/pdk/ihp-sg13cmos5l.bak-20261015T153636Z
for t in cur:$NEW old:$OLD; do
  n=${t%%:*}; p=${t#*:}
  run dr008_fast_$n "$p" res_bcs -40 1.750782359932964e-06 461985148.381761 0.007874015748031496
  run dr008_slow_$n "$p" res_wcs 125 1.7508269233170294e-06 399248171.4081036 0.009708737864077669
  run dr007_slow_$n "$p" res_wcs 125 5.969071126574055e-07 1057966511.934083 0.008403361344537815
done
