* sg13g2-pll :: sim/sg13cmos5l-divider-nrange-retiming (issue #36, Part of #16)
* dff_tg_hv SETUP-TIME deck -- the *requirement* side of the retiming margin.
*
* tb_div_retime.sp.tmpl measures how much setup window `DIVOUT` actually gets
* before the next VCO edge. That number only means something against how much
* the `XFRT` flop needs, so this deck measures the need directly, on the same
* cell, at the same 1562.0 MHz retiming clock.
*
* Method: hold the flop's D at 0, then step it to the rail at
* t = t_capture - 40p, where t_capture is the rising CKIN_VCO edge at
* 5.151641e-09. Sample Q one quarter-period after the capture edge -- which is how
* `XFRT`'s output is actually consumed downstream. Sweeping 40p down from a
* comfortably-large value walks the flop from "captures the 1" to "does not";
* the crossover is the setup time. Sampling a QUARTER period after the edge
* (rather than at the following edge) is deliberate: it separates the setup
* question from the hold-retention question tb_dff_hold.sp.tmpl asks.
*
* Substituted by ../testbench/run.sh: mos_tt, 27, 3.3, 6.402051e-10,
* 3.201026e-10, 5.151641e-09, 40p, 5.311692e-09, divider_chain.spice, and @PDK_ROOT@/@PDK@ (resolved
* filesystem path -- ngspice's `.lib` parser does not expand shell/OS
* environment variables, issue #61).

.lib $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.option scale=1 temp=27
.global sub!

.include divider_chain.spice

Vdd vdd 0 dc 3.3
Vsub sub! 0 dc 0
* Rising 50% crossings of clk are at 30p + k*6.402051e-10; 5.151641e-09 names the capture edge.
Vclk clk 0 pulse(0 3.3 0 60p 60p 3.201026e-10 6.402051e-10)
* D steps 0 -> rail with a 30 ps edge centred 40p before the capture edge.
Vd d 0 pwl 0 0 '5.151641e-09 - 40p - 15p' 0 '5.151641e-09 - 40p + 15p' 3.3

Xdut d clk q vdd 0 dff_tg_hv

.ic v(xdut.m)=0 v(xdut.s)=0

.tran 5p '5.311692e-09 + 20p'

.control
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103_nqs.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/mosvar.osdi
run
meas tran q_s find v(q) at=5.311692e-09
print q_s
.endc
.end
