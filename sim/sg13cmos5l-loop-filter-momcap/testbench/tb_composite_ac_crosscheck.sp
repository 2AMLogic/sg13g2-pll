* sg13g2-pll :: sim/sg13cmos5l-loop-filter-momcap (issue #23, Part of #16)
* Cross-check: AC impedance sweep of the FULL loop_filter subckt exactly as
* instantiated in ../netlist-snapshots/loop_filter.spice (not the individual
* R1/C1/C2 extractions run.sh does), at the nominal (res_typ, 27C, mom_frac=0)
* corner only. Confirms the closed-form fz = 1/(2*pi*R1*C1) and
* fp = (C1+C2)/(2*pi*R1*C1*C2) run.sh computes from independently-measured
* R1/C1/C2 actually matches the real simulated composite impedance's
* magnitude-slope knee -- i.e. the analytic formula reflects the real
* compact models, not just the textbook topology. See RECORD-001 "Cross-
* check" for the numeric comparison.
*
* Run directly (not templated -- single fixed corner):
*   ngspice -b tb_composite_ac_crosscheck.sp

.lib $PDK_ROOT/$PDK/libs.tech/ngspice/models/cornerRES.lib res_typ
.include $PDK_ROOT/$PDK/libs.tech/ngspice/models/cap_cmomi.lib
.option scale=1

.subckt loop_filter VCTRL VSS
XR1 VCTRL NZ sub! rppd w=4u l=120u m=1 b=0
XC1 NZ VSS cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1
XC2 VCTRL VSS cap_cmomi w=10u l=10u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1
.ends

Xlf vctrl 0 loop_filter
Vsub sub! 0 0
Iac vctrl 0 dc 0 ac 1
Rbleed vctrl 0 1e14

.control
ac dec 5 10 1000meg
print vm(vctrl)
.endc
.end
