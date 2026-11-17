* sg13g2-pll :: sim/sg13cmos5l-divider-nrange-retiming (issue #36, Part of #16)
* dff_tg_hv STATIC-HOLD probe -- the root-cause deck for this record.
*
* Every state element in `divider_chain` (12 flops inside the six
* `div23_cell` instances, plus `XFRT`) is one `dff_tg_hv`. This deck isolates
* ONE of them and asks the only question that matters before any divider
* measurement is meaningful: does it hold its state when the clock stops?
*
* Method: load a logic 1 through a single rising clock edge at t = 1 ns, take
* the clock back low at t = 2 ns, and then leave it low for 40n. The slave
* latch is in hold for that whole window. A working master-slave flop keeps
* `Q` at the rail; a flop whose hold path is not a real latch does not.
*
* Measured:
*   q_end   -- V(Q) at the end of the hold window (a rail, or not a rail)
*   s_end   -- V(S), the slave storage node itself
*   t_decay -- time from the clock's falling edge until V(Q) has fallen
*              through 90% of the rail (i.e. left the logic-1 region).
*              `meas` FAILS (and run.sh records `none`) when Q never leaves
*              the rail -- which is the pass condition, not an error.
*
* `../testbench/run.sh` substitutes mos_tt (cornerMOShv.lib section),
* -40, 3.3, 2.9699999999999998 (= 0.9 x 3.3), 40n, divider_chain.spice and
* @PDK_ROOT@/@PDK@ (resolved filesystem path -- ngspice's `.lib` parser does
* not expand shell/OS environment variables, issue #61) per ../corners/matrix.md.
* divider_chain.spice selects the DUT variant:
*   divider_chain.spice        -- the committed design, verbatim from the
*                                 frozen ../netlist-snapshots/ copy
*   divider_chain_fbfix.spice  -- the PROPOSAL variant run.sh derives locally
*                                 (see run.sh's header). NOT the committed
*                                 design and not proposed for commit here.
*
* No RES corner axis: the DUT expands to `sg13_hv_nmos`/`sg13_hv_pmos`
* instances only -- same inapplicability the sg13cmos5l-cp-icp-trim record
* documents for its own all-MOS DUT. No MOM-cap axis: no `cap_cmomi` /
* `cap_cmomf` instance exists anywhere under `divider_chain`.

.lib $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.option scale=1 temp=-40
.global sub!

.include divider_chain.spice

Vdd vdd 0 dc 3.3
Vsub sub! 0 dc 0
Vd d 0 dc 3.3
* one rising edge at 1 ns; clock stays low from 2 ns onward (slave in hold)
Vclk clk 0 pwl 0 0 0.9n 0 1.0n 3.3 1.9n 3.3 2.0n 0

Xdut d clk q vdd 0 dff_tg_hv

* The block has NO reset pin, so its latches have no defined power-up state
* and the DC operating point is indeterminate. These two `.ic` statements are
* the minimum symmetry break that makes an OP exist at all -- see
* ../records/RECORD-001 "Finding 1".
.ic v(xdut.m)=0 v(xdut.s)=0

.tran 20p '40n + 2n'

.control
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103_nqs.osdi
pre_osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/mosvar.osdi
run
meas tran q_end   find v(q)       at='40n + 1.9n'
meas tran s_end   find v(xdut.s)  at='40n + 1.9n'
meas tran t_decay when v(q)=2.9699999999999998 fall=1 td=2.0n
print q_end s_end t_decay
.endc
.end
