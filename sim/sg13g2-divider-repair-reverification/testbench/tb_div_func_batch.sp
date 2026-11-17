* sg13g2-pll :: sim/sg13g2-divider-repair-reverification (issue #235, supersedes RECORD-001 / issue #120)
* Circuit BODY for `klt sim` (no .control/.end; klt owns those). Same stimulus,
* .ic symmetry break and measurements as testbench/tb_div_func.sp.tmpl, with the
* template substitutions turned into .param values so one body serves every
* corner: vdd_p (supply, swept via corners.params), b0..b5 (programming word
* bits), tper/ton (100 MHz CKIN).
* DUT: ../netlist-snapshots/divider_chain_repaired.spice (frozen, unchanged).
.options reltol=0.001 vntol=1e-4 abstol=1e-9 trtol=7
.global sub!
.include ../netlist-snapshots/divider_chain_repaired.spice
.param vdd_p=3.3 tper=10n ton=4.4n
.param b0=0 b1=0 b2=0 b3=0 b4=0 b5=0
Vdd vdd 0 dc 'vdd_p'
Vsub sub! 0 dc 0
Vck ck 0 pulse(0 'vdd_p' 0 60p 60p 'ton' 'tper')
Vp0 p0 0 dc 'b0*vdd_p'
Vp1 p1 0 dc 'b1*vdd_p'
Vp2 p2 0 dc 'b2*vdd_p'
Vp3 p3 0 dc 'b3*vdd_p'
Vp4 p4 0 dc 'b4*vdd_p'
Vp5 p5 0 dc 'b5*vdd_p'
Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain
.ic v(xdiv.xd0.xdffq.m)=0 v(xdiv.xd0.xdffq.s)=0 v(xdiv.xd0.xdffm.m)=0 v(xdiv.xd0.xdffm.s)=0
.ic v(xdiv.xd1.xdffq.m)=0 v(xdiv.xd1.xdffq.s)=0 v(xdiv.xd1.xdffm.m)=0 v(xdiv.xd1.xdffm.s)=0
.ic v(xdiv.xd2.xdffq.m)=0 v(xdiv.xd2.xdffq.s)=0 v(xdiv.xd2.xdffm.m)=0 v(xdiv.xd2.xdffm.s)=0
.ic v(xdiv.xd3.xdffq.m)=0 v(xdiv.xd3.xdffq.s)=0 v(xdiv.xd3.xdffm.m)=0 v(xdiv.xd3.xdffm.s)=0
.ic v(xdiv.xd4.xdffq.m)=0 v(xdiv.xd4.xdffq.s)=0 v(xdiv.xd4.xdffm.m)=0 v(xdiv.xd4.xdffm.s)=0
.ic v(xdiv.xd5.xdffq.m)=0 v(xdiv.xd5.xdffq.s)=0 v(xdiv.xd5.xdffm.m)=0 v(xdiv.xd5.xdffm.s)=0
.ic v(xdiv.xfrt.m)=0 v(xdiv.xfrt.s)=0
.save v(ck) v(divout) v(fb) v(xdiv.ck1) v(xdiv.ck2) v(xdiv.ck3) v(xdiv.ck4) v(xdiv.ck5) i(vdd)
