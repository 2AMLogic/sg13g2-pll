* sg13g2-pll :: sim/sg13cmos5l-divider-nrange-retiming (issue #36, Part of #16)
* RETIMING-MARGIN deck (spec/porting-plan.md row 3) at the measured
* top-of-band VCO frequency, 1562.0 MHz -- the `fast` bundle / band `11` /
* VCTRL = 2.7 V point of
* sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md.
*
* What "retiming margin" means here, concretely: `DIVOUT` is the last divider
* cell's Q, so its edge is displaced from the VCO edge that caused it by the
* accumulated clk->Q delay of the whole six-cell chain. `XFRT` then re-clocks
* `DIVOUT` on the *next* VCO edge. The two numbers this deck produces are
*
*   setup_avail -- t(next CKIN_VCO rising 50% crossing) - t(DIVOUT rising
*                  50% crossing). The window `DIVOUT` actually gets.
*   clk2q_frt   -- t(FB rising 50% crossing) - t(that capture edge). The
*                  `XFRT` flop's own clk->Q at this frequency.
*
* CKIN and CKIN_VCO are the same net (see tb_div_func.sp.tmpl's header). The
* CKIN rising 50% crossings are therefore at exactly t = @TR2@ + k*6.40205120e-10 for
* integer k -- an ideal source, so run.sh's extractor derives the capture edge
* arithmetically instead of hunting for it with a fragile indexed `meas`.
*
* Substituted by ../testbench/run.sh: mos_tt, 27, 3.3, 1.65,
* 6.40205120e-10, 2.816903e-10, 1.280410e-11, 1.638925e-07, 4.302178e-08, 0..0, 0.001, divider_chain.spice,
* and @PDK_ROOT@/@PDK@ (resolved filesystem path -- ngspice's `.lib` parser
* does not expand shell/OS environment variables, issue #61).

.lib $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.option scale=1 temp=27
.options reltol=0.001 vntol=1e-4 abstol=1e-9 trtol=7
.global sub!

.include divider_chain.spice

Vdd vdd 0 dc 3.3
Vsub sub! 0 dc 0
Vck ck 0 pulse(0 3.3 0 60p 60p 2.816903e-10 6.40205120e-10)
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

.save v(ck) v(divout) v(fb) i(vdd)
.tran 1.280410e-11 1.638925e-07

.control
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103_nqs.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/mosvar.osdi
run
meas tran tdiv when v(divout)=1.65 rise=2
meas tran tfb  when v(fb)=1.65 rise=2
meas tran dvo_max max v(divout) from=4.302178e-08 to=1.638925e-07
meas tran dvo_min min v(divout) from=4.302178e-08 to=1.638925e-07
meas tran fb_max  max v(fb)     from=4.302178e-08 to=1.638925e-07
meas tran fb_min  min v(fb)     from=4.302178e-08 to=1.638925e-07
meas tran idd avg i(vdd) from=4.302178e-08 to=1.638925e-07
print tdiv tfb dvo_max dvo_min fb_max fb_min idd
.endc
.end
