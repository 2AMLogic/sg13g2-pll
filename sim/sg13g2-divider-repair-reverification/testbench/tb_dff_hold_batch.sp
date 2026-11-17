* sg13g2-pll :: sim/sg13g2-divider-repair-reverification (issue #235): one dff_tg_hv latch hold.
* Circuit BODY for klt sim; same stimulus/.ic/measure as tb_dff_hold.sp.tmpl.
.options reltol=0.001
.global sub!
.include ../netlist-snapshots/divider_chain_repaired.spice
.param vdd_p=3.3
Vdd vdd 0 dc 'vdd_p'
Vsub sub! 0 dc 0
Vd d 0 dc 'vdd_p'
Vclk clk 0 pwl 0 0 0.9n 0 1.0n 'vdd_p' 1.9n 'vdd_p' 2.0n 0
Xdut d clk q vdd 0 dff_tg_hv
.ic v(xdut.m)=0 v(xdut.s)=0
.save v(q) v(xdut.s)
