* sg13g2-pll :: sim/sg13g2-divider-repair-reverification (issue #235): DC OP convergence, ic=none.
.global sub!
.include ../netlist-snapshots/divider_chain_repaired.spice
Vdd vdd 0 dc 3.3
Vsub sub! 0 dc 0
Vck ck 0 dc 0
Vp0 p0 0 dc 0
Vp1 p1 0 dc 0
Vp2 p2 0 dc 0
Vp3 p3 0 dc 0
Vp4 p4 0 dc 0
Vp5 p5 0 dc 0
Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain
