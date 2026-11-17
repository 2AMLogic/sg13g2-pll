* sg13g2-pll :: sim/sg13cmos5l-divider-nrange-retiming (issue #36, Part of #16)
* `divider_chain` FUNCTIONAL / division-ratio deck (spec/porting-plan.md row 3),
* plus the divider's own average supply current at the same operating point
* (a real measured input to row 11's power budget -- see ../records/RECORD-001
* for what that does and does not bound).
*
* Both clock inputs are driven from the same source, because in the closed
* loop they are the same net: `CKIN` is the VCO output the chain divides, and
* `CKIN_VCO` is the VCO output the `XFRT` retiming flop re-clocks `DIVOUT`
* onto. Driving them separately would invent a skew the design does not have.
*
* Measured:
*   ck<k>_max/min  -- rail excursion of every internal stage output ck1..ck5
*                     and of DIVOUT/FB over the measurement window. This is
*                     what tells you WHICH stage stops toggling when the chain
*                     does not divide -- a single "DIVOUT is dead" bit does not.
*   tdiv_a, tdiv_b -- two successive DIVOUT rising 50% crossings (indices
*                     2/3, chosen by run.sh to skip startup)
*   tck_a, tck_b   -- two successive CKIN rising 50% crossings, so the divide
*                     ratio is measured against the clock the deck actually
*                     produced rather than against its nominal period
*   idd            -- average I(vdd) over the measurement window
*
* `../testbench/run.sh` substitutes mos_tt, 27, 3.3, 1.65
* (= 3.3/2), 1.000000e-08 / 4.400000e-09 (CKIN period / high time), 3.3..0 (the
* programming word, 0 or 3.3), 3.000000e-10, 2.210000e-06, 6.825000e-07 (start of the
* averaging/excursion window), 2/3, 0.001 and divider_chain.spice per
* ../corners/matrix.md. Also substitutes @PDK_ROOT@/@PDK@ (resolved
* filesystem path -- ngspice's `.lib` parser does not expand shell/OS
* environment variables, issue #61).
*
* divider_chain.spice selects the DUT variant -- `divider_chain.spice` (the committed
* design, verbatim from the frozen ../netlist-snapshots/ copy) or
* `divider_chain_fbfix.spice` (the PROPOSAL variant run.sh derives locally;
* NOT the committed design). See run.sh's header for the exact derivation.

.lib $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.option scale=1 temp=27
.options reltol=0.001 vntol=1e-4 abstol=1e-9 trtol=7
.global sub!

.include divider_chain.spice

Vdd vdd 0 dc 3.3
Vsub sub! 0 dc 0
Vck ck 0 pulse(0 3.3 0 60p 60p 4.400000e-09 1.000000e-08)
Vp0 p0 0 dc 3.3
Vp1 p1 0 dc 0
Vp2 p2 0 dc 0
Vp3 p3 0 dc 0
Vp4 p4 0 dc 0
Vp5 p5 0 dc 0

Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain

* `divider_chain` has NO reset pin: its 13 `dff_tg_hv` state elements have no
* defined power-up state, so the DC operating point is indeterminate and
* ngspice's gmin/source stepping cannot resolve it. These `.ic` statements are
* the minimum symmetry break that makes an OP exist -- they are a TESTBENCH
* workaround for a DESIGN gap, recorded as Finding 1 of ../records/RECORD-001,
* not a property of the block.
.ic v(xdiv.xd0.xdffq.m)=0 v(xdiv.xd0.xdffq.s)=0 v(xdiv.xd0.xdffm.m)=0 v(xdiv.xd0.xdffm.s)=0
.ic v(xdiv.xd1.xdffq.m)=0 v(xdiv.xd1.xdffq.s)=0 v(xdiv.xd1.xdffm.m)=0 v(xdiv.xd1.xdffm.s)=0
.ic v(xdiv.xd2.xdffq.m)=0 v(xdiv.xd2.xdffq.s)=0 v(xdiv.xd2.xdffm.m)=0 v(xdiv.xd2.xdffm.s)=0
.ic v(xdiv.xd3.xdffq.m)=0 v(xdiv.xd3.xdffq.s)=0 v(xdiv.xd3.xdffm.m)=0 v(xdiv.xd3.xdffm.s)=0
.ic v(xdiv.xd4.xdffq.m)=0 v(xdiv.xd4.xdffq.s)=0 v(xdiv.xd4.xdffm.m)=0 v(xdiv.xd4.xdffm.s)=0
.ic v(xdiv.xd5.xdffq.m)=0 v(xdiv.xd5.xdffq.s)=0 v(xdiv.xd5.xdffm.m)=0 v(xdiv.xd5.xdffm.s)=0
.ic v(xdiv.xfrt.m)=0 v(xdiv.xfrt.s)=0

.save v(ck) v(divout) v(fb) v(xdiv.ck1) v(xdiv.ck2) v(xdiv.ck3) v(xdiv.ck4) v(xdiv.ck5) i(vdd)
.tran 3.000000e-10 2.210000e-06

.control
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103_nqs.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/mosvar.osdi
run
meas tran ck1_max max v(xdiv.ck1) from=6.825000e-07 to=2.210000e-06
meas tran ck1_min min v(xdiv.ck1) from=6.825000e-07 to=2.210000e-06
meas tran ck2_max max v(xdiv.ck2) from=6.825000e-07 to=2.210000e-06
meas tran ck2_min min v(xdiv.ck2) from=6.825000e-07 to=2.210000e-06
meas tran ck3_max max v(xdiv.ck3) from=6.825000e-07 to=2.210000e-06
meas tran ck3_min min v(xdiv.ck3) from=6.825000e-07 to=2.210000e-06
meas tran ck4_max max v(xdiv.ck4) from=6.825000e-07 to=2.210000e-06
meas tran ck4_min min v(xdiv.ck4) from=6.825000e-07 to=2.210000e-06
meas tran ck5_max max v(xdiv.ck5) from=6.825000e-07 to=2.210000e-06
meas tran ck5_min min v(xdiv.ck5) from=6.825000e-07 to=2.210000e-06
meas tran dvo_max max v(divout) from=6.825000e-07 to=2.210000e-06
meas tran dvo_min min v(divout) from=6.825000e-07 to=2.210000e-06
meas tran fb_max  max v(fb)     from=6.825000e-07 to=2.210000e-06
meas tran fb_min  min v(fb)     from=6.825000e-07 to=2.210000e-06
meas tran tdiv_a when v(divout)=1.65 rise=2
meas tran tdiv_b when v(divout)=1.65 rise=3
meas tran tck_a  when v(ck)=1.65 rise=3
meas tran tck_b  when v(ck)=1.65 rise=4
meas tran idd    avg i(vdd) from=6.825000e-07 to=2.210000e-06
print ck1_max ck1_min ck2_max ck2_min ck3_max ck3_min ck4_max ck4_min
print ck5_max ck5_min dvo_max dvo_min fb_max fb_min
print tdiv_a tdiv_b tck_a tck_b idd
.endc
.end
