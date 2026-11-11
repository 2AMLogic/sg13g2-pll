* RECORD-001 hold stage rerun (issue #232), variant fbfix
.option scale=1
.global sub!
.include divider_chain_fbfix.spice
.param vddp=3.3
Vdd vdd 0 dc 'vddp'
Vsub sub! 0 dc 0
Vd d 0 dc 'vddp'
Vclk clk 0 pwl 0 0 0.9n 0 1.0n 'vddp' 1.9n 'vddp' 2.0n 0
Xdut d clk q vdd 0 dff_tg_hv
.ic v(xdut.m)=0 v(xdut.s)=0
