* OP-convergence probe -- repaired, ic=none
.lib $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.option scale=1 temp=27
.global sub!
.include divider_chain.spice
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
.control
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103_nqs.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/mosvar.osdi
op
print v(divout) v(fb)
.endc
.end
