* OP-convergence probe (issue #232) -- asdrawn, ic=applied
.option scale=1
.global sub!
.include divider_chain.spice
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
.ic v(xdiv.xd0.xdffq.m)=0 v(xdiv.xd0.xdffq.s)=0 v(xdiv.xd0.xdffm.m)=0 v(xdiv.xd0.xdffm.s)=0
.ic v(xdiv.xd1.xdffq.m)=0 v(xdiv.xd1.xdffq.s)=0 v(xdiv.xd1.xdffm.m)=0 v(xdiv.xd1.xdffm.s)=0
.ic v(xdiv.xd2.xdffq.m)=0 v(xdiv.xd2.xdffq.s)=0 v(xdiv.xd2.xdffm.m)=0 v(xdiv.xd2.xdffm.s)=0
.ic v(xdiv.xd3.xdffq.m)=0 v(xdiv.xd3.xdffq.s)=0 v(xdiv.xd3.xdffm.m)=0 v(xdiv.xd3.xdffm.s)=0
.ic v(xdiv.xd4.xdffq.m)=0 v(xdiv.xd4.xdffq.s)=0 v(xdiv.xd4.xdffm.m)=0 v(xdiv.xd4.xdffm.s)=0
.ic v(xdiv.xd5.xdffq.m)=0 v(xdiv.xd5.xdffq.s)=0 v(xdiv.xd5.xdffm.m)=0 v(xdiv.xd5.xdffm.s)=0
.ic v(xdiv.xfrt.m)=0 v(xdiv.xfrt.s)=0
