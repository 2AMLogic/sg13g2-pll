* sg13g2-pll :: sim/sg13cmos5l-loop-filter-momcap (issue #23, Part of #16)
* Single-device DC extraction: loop_filter.XR1 (rppd, w=4u l=120u), the same
* instance parameters as ../netlist-snapshots/loop_filter.spice's XR1 line.
* Forces 1uA through the resistor and reads V(N1)/I to get R at the process
* corner + temperature this run.sh instantiation substitutes below.
*
* Template placeholders (substituted by ../testbench/run.sh, not meant to be
* run directly): res_bcs (res_typ|res_bcs|res_wcs, cornerRES.lib),
* 125 (degC), 0.6u, 810u (device geometry), $PDK_ROOT/ihp-sg13cmos5l (resolved
* filesystem path -- ngspice's `.lib` parser does not expand shell/OS
* environment variables, issue #43).

.lib $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_bcs
.option scale=1 temp=125

Xr1 n1 0 sub! rppd w=0.6u l=810u m=1 b=0
Vsub sub! 0 0
I1 n1 0 dc 1u

.control
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/cap_cmomi.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/cap_cmomf.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/r3_cmc.osdi
op
let rval = abs(v(n1)/1e-6)
print rval
.endc
.end
