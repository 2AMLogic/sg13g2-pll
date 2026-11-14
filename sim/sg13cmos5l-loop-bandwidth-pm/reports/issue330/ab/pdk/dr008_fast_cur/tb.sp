* sg13g2-pll :: sim/sg13cmos5l-loop-bandwidth-pm (issue #41, Part of #16)
* Same as tb_loop_ac_real.sp.tmpl, but built around the RESIZED `loop_filter`
* subckt (`../netlist-snapshots/loop_filter_resized.spice`, issue #41 /
* DR-006: XR1 rppd w=4u l=120u -> w=0.6u l=810u), not the as-drawn one.
* ../records/RECORD-001 stays the as-drawn filter's own record; this
* template exists so ../records/RECORD-002 re-measures the SAME open-loop
* AC scenario against the post-resize filter without touching
* tb_loop_ac_real.sp.tmpl or anything RECORD-001 cites.
*
* `../testbench/run.sh` substitutes res_bcs (cornerRES.lib section),
* -40 (degC), 1.750782359932964e-06 (charge-pump gain Icp/2*pi, A/rad), 461985148.381761 (VCO gain
* 2*pi*Kvco, rad/s per V), 0.007874015748031496 (1/N) per ../corners/matrix.md, and
* /home/ubuntu/share/pdk/ihp-sg13cmos5l (resolved filesystem path -- ngspice's `.lib`/`.include`
* parser does not expand shell/OS environment variables, issue #44).
*
* ---------------------------------------------------------------------------
* WHAT IS REAL HERE AND WHAT IS BEHAVIOURAL
* ---------------------------------------------------------------------------
* REAL (extracted compact models, swept over their own corners):
*   - the RESIZED loop filter's R1 (`rppd`, w=0.6u l=810u) and C1/C2
*     (`cap_cmomi`, unchanged), instantiated from the frozen post-resize
*     design export with no further edit.
* BEHAVIOURAL (linearised small-signal stand-ins, each with its own numeric
* value taken from a REAL measurement recorded elsewhere in this repo):
*   - the phase detector + charge pump, as a transconductance 1.750782359932964e-06 =
*     Icp/(2*pi) A/rad. Icp comes from
*     ../../sg13cmos5l-cp-icp-trim/corners/results.csv (a real DC sweep of
*     the committed `cp` subckt), not from an assumption.
*   - the VCO, as an ideal phase integrator of gain 461985148.381761 = 2*pi*Kvco. Kvco
*     comes from ../../sg13cmos5l-vco-kvco-table/corners/results.csv (a real
*     PVT-cornered transient sweep of the committed `vco` subckt).
*   - the feedback divider, as a memoryless 1/N gain (0.007874015748031496). This is the
*     standard continuous-time approximation and is exactly why the
*     f_c < f_ref/10 sampled-loop ceiling exists as a separate criterion --
*     see ../records/RECORD-001 "What this does not bound".
* No transistor-level closed-loop transient is run here; ../records/RECORD-002
* states plainly which spec rows that leaves unbounded.
* ---------------------------------------------------------------------------

.lib /home/ubuntu/share/pdk/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_bcs
.include /home/ubuntu/share/pdk/ihp-sg13cmos5l/libs.tech/ngspice/models/cap_cmomi.lib
.option scale=1 temp=-40
.global sub!

.include loop_filter_snap_resized.spice

Vsub sub! 0 dc 0

* 1 rad of AC phase error into the phase detector
Vpe pe 0 dc 0 ac 1

* Phase detector + charge pump: Icp/(2*pi) amperes per radian, injected into
* the filter node.
Gcp 0 vctrl pe 0 1.750782359932964e-06

* The real, RESIZED loop filter (VCTRL, VSS)
XLF vctrl 0 loop_filter

* VCO as an ideal phase integrator: 1 F on `vph` makes V(vph) the running
* integral of 461985148.381761 * V(vctrl), i.e. a transfer of @KV@/s rad per volt.
* Rleak only keeps the node DC-defined; its own pole sits at 1.6e-16 Hz.
Gvco 0 vph vctrl 0 461985148.381761
Cint vph 0 1
Rleak vph 0 1e15

* Feedback divider: memoryless 1/N
Ediv fb 0 vph 0 0.007874015748031496

.control
ac dec 200 10 1e9
let mag_ol = mag(v(fb))
let ph_ol = 180*cph(v(fb))/pi
wrdata ac.dat mag_ol ph_ol
.endc
.end
