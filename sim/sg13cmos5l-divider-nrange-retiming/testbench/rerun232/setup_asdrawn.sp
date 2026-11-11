* RECORD-001 setup stage rerun (issue #232), variant asdrawn
.option scale=1
.global sub!
.include divider_chain.spice
.param vddp=3.3 tsu=300p tcap=5.151641e-09
Vdd vdd 0 dc 'vddp'
Vsub sub! 0 dc 0
Vclk clk 0 pulse(0 'vddp' 0 60p 60p 3.201026e-10 6.402051e-10)
Vd d 0 pwl 0 0 'tcap - tsu - 15p' 0 'tcap - tsu + 15p' 'vddp'
Xdut d clk q vdd 0 dff_tg_hv
.ic v(xdut.m)=0 v(xdut.s)=0
