* sg13g2-pll :: sim/sg13g2-lock-detector-window (issue #81, Part of #16 via #78)
* Comparator-window measurement: a BARE delaywin_hv (the four-inverter chain
* plus XC1, the second of this record's two cap_cmim instances) driven by an
* ideal step, so the window that sets the whole detector's phase-error
* threshold is measured DIRECTLY rather than inferred from where the block's
* LOCK output happens to change state.
*
* Carried over (topology, not device-specific) from
* ../../sg13cmos5l-lock-detector-window/testbench/tb_window.sp.tmpl (issue
* #38). The one substantive difference: that deck swaps in a mom_inject.py-
* built DUT variant to express a +/-20% MOM-model-uncertainty band on
* cap_cmomi (which has no real corner of its own); this deck instead
* `.include`s the frozen snapshot directly and sweeps `cap_cmim`'s OWN real
* process corner via @CAP_CORNER@, alongside res_typ -- see
* ../testbench/tb_extract_c.sp.tmpl's header for why that axis exists here
* and did not exist for cap_cmomi.
*
* This is the number `spec/porting-plan.md` row 16's ported target
* ("assert window >= 2.5 ns / >= 2x worst static phase offset") applies to.
* The block's coincidence gate is WIDE = ERR AND delaywin_hv(ERR), so an
* XOR(UP,DN) error pulse only produces a WIDE pulse when it is wider than
* this element's LOW-to-HIGH propagation delay -- twin_r below is therefore
* the quantity the phase-error threshold is built out of, and twin_f is
* reported alongside it because the two are not equal in a chain whose last
* node carries an asymmetrically-driven cap_cmim load.
*
* run.sh runs this deck FIRST at every corner point, and then scales the
* block-level phase-error ladder (tb_lock_ladder_point.sp.tmpl /
* tb_lock_recovery.sp.tmpl) in units of this corner's own measured twin_r.
*
* Substituted by ../testbench/run.sh: mos_tt, res_typ,
* cap_typ, 27, 3.3, 1.65 (= VSUP/2, pre-computed because
* ngspice's .meas val= does not evaluate a .param expression inside a
* .control block), 20p, @DUT@ (the frozen netlist-snapshot file, included
* directly -- no MOM-band variant substitution is needed here, see this
* file's own header), $PDK_ROOT/ihp-sg13g2 (resolved filesystem path --
* ngspice's `.lib`/`.include` parser does not expand shell/OS environment
* variables).

.lib $PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.lib $PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/models/cornerRES.lib res_typ
.lib $PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/models/cornerCAP.lib cap_typ
.option scale=1 temp=27
.global sub!

* ---- frozen snapshot netlist-snapshots/lock_detector_resized.spice inlined verbatim ----
* sg13g2-pll :: sim/sg13g2-lock-detector-window (issue #82, Part of #16 via #78)
* Frozen snapshot of design/netlist/lock_detector.spice at the END of this
* issue's two-stage re-derivation, taken on this issue's own branch with
* parent commit 6c4351b30b58b5de8a25430936317dc440908930.  Independent of whatever
* design/netlist/lock_detector.spice says by the time this record is read
* later -- see sim/README.md's own "Netlist provenance" convention.
*
* This is the block ../records/RECORD-001 draws its spec/porting-plan.md
* row 16 verdicts against.  It differs from ./lock_detector.spice (the
* PRE-resize snapshot issue #81 froze, which stands unedited) in EXACTLY FOUR
* instance values and is byte-identical everywhere else:
*
*   Instance             was              now             evidence
*   XRPU (rhigh)         w=0.5u l=6u      w=0.5u l=500u   ../corners/rc_sizing.csv + rc_pairing.csv (R*C >> T_ref)
*   XCW (cap_cmim)       w=6u l=6u m=1    w=45u l=45u m=1 same
*   XDW.XC1 (cap_cmim)   w=4u l=4u m=1    w=45u l=45u m=1 ../corners/window_sizing.csv (row 16's >= 2.5 ns floor)
*   XMPD (sg13_hv_nmos)  w=2u l=0.5u      w=0.25u l=12u   ../corners/xmpd_sizing.csv (two-sided bound)
*
* schmitt_hv, xor2_hv, nand2_hv, inv_hv and the four-inverter chain's own
* drive are UNTOUCHED.  schmitt_hv in particular already carries the classic
* cross-coupled feedback connection (issue #66) on this PDK -- see XMP3/XMN3
* below -- which is why this record needs no rewired-Schmitt control the way
* the SG13CMOS5L sibling's RECORD-002/RECORD-003 did.
*
* ./lock_detector_rc_resized.spice is the INTERMEDIATE snapshot (stage 1:
* XRPU/XCW/XDW.XC1 only, XMPD still as drawn) that ./testbench/run_xmpd_sizing.sh
* was run against; it is frozen separately so stage 2's input is citable.
*
* xschem XSCHEM V3.4.7; do not edit by hand.
** sch_path: design/lock_detector.sch
.subckt lock_detector UP DN LOCK VDD VSS
*.ipin UP
*.ipin DN
*.opin LOCK
*.iopin VDD
*.iopin VSS
XXOR UP DN ERR VDD VSS xor2_hv
XDW ERR ERRD VDD VSS delaywin_hv
XNW ERR ERRD nwide VDD VSS nand2_hv
XIW nwide WIDE VDD VSS inv_hv
XRPU VDD VWIN sub! rhigh w=0.5u l=500u m=1 b=0
XMPD VWIN WIDE VSS VSS sg13_hv_nmos w=0.25u l=12u ng=1 m=1
XCW VWIN VSS cap_cmim w=45u l=45u m=1
XSCH VWIN LOCK VDD VSS schmitt_hv
.ends

* expanding   symbol:  xor2_hv.sym # of pins=5
** sym_path: design/xor2_hv.sym
** sch_path: design/xor2_hv.sch
.subckt xor2_hv A B Y VDD VSS
*.ipin A
*.ipin B
*.opin Y
*.iopin VDD
*.iopin VSS
XN1 A B n1 VDD VSS nand2_hv
XN2 A n1 n2 VDD VSS nand2_hv
XN3 B n1 n3 VDD VSS nand2_hv
XN4 n2 n3 Y VDD VSS nand2_hv
.ends


* expanding   symbol:  delaywin_hv.sym # of pins=4
** sym_path: design/delaywin_hv.sym
** sch_path: design/delaywin_hv.sch
.subckt delaywin_hv IN OUT VDD VSS
*.ipin IN
*.opin OUT
*.iopin VDD
*.iopin VSS
XI1 IN d1 VDD VSS inv_hv
XI2 d1 d2 VDD VSS inv_hv
XI3 d2 d3 VDD VSS inv_hv
XI4 d3 OUT VDD VSS inv_hv
XC1 OUT VSS cap_cmim w=45u l=45u m=1
.ends


* expanding   symbol:  nand2_hv.sym # of pins=5
** sym_path: design/nand2_hv.sym
** sch_path: design/nand2_hv.sch
.subckt nand2_hv A1 A2 Y VDD VSS
*.opin Y
*.ipin A1
*.ipin A2
*.iopin VDD
*.iopin VSS
XMP1 Y A1 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XMP2 Y A2 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XMN1 Y A1 mid1 VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XMN2 mid1 A2 VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
.ends


* expanding   symbol:  inv_hv.sym # of pins=4
** sym_path: design/inv_hv.sym
** sch_path: design/inv_hv.sch
.subckt inv_hv A Y VDD VSS
*.ipin A
*.opin Y
*.iopin VDD
*.iopin VSS
XMP Y A VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XMN Y A VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
.ends


* expanding   symbol:  schmitt_hv.sym # of pins=4
** sym_path: design/schmitt_hv.sym
** sch_path: design/schmitt_hv.sch
.subckt schmitt_hv IN OUT VDD VSS
*.ipin IN
*.opin OUT
*.iopin VDD
*.iopin VSS
XMP1 np IN VDD VDD sg13_hv_pmos w=5u l=2u ng=1 m=1
XMP2 OUT IN np VDD sg13_hv_pmos w=5u l=2u ng=1 m=1
XMP3 VSS OUT np VDD sg13_hv_pmos w=5u l=2u ng=1 m=1
XMN1 OUT IN nn VSS sg13_hv_nmos w=2u l=2u ng=1 m=1
XMN2 nn IN VSS VSS sg13_hv_nmos w=2u l=2u ng=1 m=1
XMN3 VDD OUT nn VSS sg13_hv_nmos w=2u l=2u ng=1 m=1
.ends

* ---- end snapshot ----

Vsub sub! 0 0
Vdd vdd 0 dc 3.3

* Ideal step in, 100 ps edges: 20 ns high, then low, inside a 60 ns window,
* so both the rising and the falling propagation delay are measured in one
* transient with the chain fully settled before each edge.
Vstep wstep 0 pulse(0 3.3 10n 100p 100p 20n 1000n)
Xw wstep wout vdd 0 delaywin_hv

.options reltol=1e-3 abstol=1e-10 vntol=1e-5 chgtol=1e-13
.tran 20p 60n

.control
run
meas tran twin_r trig v(wstep) val=1.65 rise=1 targ v(wout) val=1.65 rise=1
meas tran twin_f trig v(wstep) val=1.65 fall=1 targ v(wout) val=1.65 fall=1
print twin_r twin_f
.endc
.end
