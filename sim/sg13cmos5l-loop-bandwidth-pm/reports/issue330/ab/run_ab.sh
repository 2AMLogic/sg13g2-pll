#!/usr/bin/env bash
# issue #330 :: single-corner local A/B of the DR-008 `fast` (-40 C) C_cp = 0 anchor.
# One `ngspice -b` per variant, sequential, no grid. Inputs (Kd, Kv, 1/N) are the
# values already written in tb_loop_ac_ccp_issue196.sp for dr008_fast_nocp.
set -euo pipefail
R=/home/ubuntu/GitHub/sg13g2-pll/.loom/worktrees/issue-330/sim/sg13cmos5l-loop-bandwidth-pm
AB=/home/ubuntu/GitHub/sg13g2-pll/.loom/worktrees/issue-330/sim/sg13cmos5l-loop-bandwidth-pm/reports/issue330/ab
P=/home/ubuntu/share/pdk/ihp-sg13cmos5l
M=$P/libs.tech/ngspice/models

cp "$R/netlist-snapshots/loop_filter_resized.spice" "$AB/loop_filter_snap_resized.spice"
cat > "$AB/.spiceinit" <<EOF
osdi $P/libs.tech/ngspice/osdi/cap_cmomi.osdi
osdi $P/libs.tech/ngspice/osdi/cap_cmomf.osdi
osdi $P/libs.tech/ngspice/osdi/r3_cmc.osdi
EOF

mk() { # name, extra-lib-line, temp-lines
  sed -e "s#@PDK_ROOT@#/home/ubuntu/share/pdk#; s#@PDK@#ihp-sg13cmos5l#; s#@CORNER_RES@#res_bcs#" \
      -e "s#@KD@#1.750782359932964e-06#; s#@KV@#461985148.381761#; s#@INVN@#0.007874015748031496#" \
      -e "s#^\.option scale=1 temp=@TEMP@#$3#" \
      -e "s#^\.global sub!#$2\n.global sub!#" \
      -e "s#wrdata ac.dat#wrdata ac_$1.dat#" \
      "$R/testbench/tb_loop_ac_real_resized.sp.tmpl" > "$AB/tb_$1.sp"
}
mk A_orig "" ".option scale=1 temp=-40"
mk B_mosff ".lib $M/cornerMOShv.lib mos_ff" ".option scale=1 temp=-40"
mk C_mosff_dottemp ".lib $M/cornerMOShv.lib mos_ff" ".option scale=1\n.temp -40"

cd "$AB"
for v in A_orig B_mosff C_mosff_dottemp; do
  rc=0; ngspice -b "tb_$v.sp" > "$v.log" 2>&1 || rc=$?
  echo "$v rc=$rc"; tail -2 "$v.log"
done
