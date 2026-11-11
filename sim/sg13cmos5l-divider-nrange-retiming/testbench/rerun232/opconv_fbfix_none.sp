* OP-convergence probe (issue #232) -- fbfix, ic=none
.option scale=1
.global sub!
.include divider_chain_fbfix.spice
.param vddp=3.3
Vdd vdd 0 dc 'vddp'
Vsub sub! 0 dc 0
Vck ck 0 dc 0
Vp0 p0 0 dc 0
Vp1 p1 0 dc 0
Vp2 p2 0 dc 0
Vp3 p3 0 dc 0
Vp4 p4 0 dc 0
Vp5 p5 0 dc 0
Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain
