v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: lock_detector -- phase-error window comparator: XOR(UP,DN) + delay window + integrator + Schmitt
Device flavour: SG13G2 3.3V thick-oxide CMOS throughout (sg13_hv_nmos /
sg13_hv_pmos), per spec/decision-records/DR-002-supply-device-flavor.md
Decision 0. Sizing is a first-pass, provisional placeholder (not yet
simulation-grounded against real SG13G2 device data) -- a future
device-characterization / tuning-range campaign (T1 items 8-9, out of
this issue's scope per spec/porting-plan.md and issue #7's Non-goals)
re-derives every number here, per spec/decision-records/DR-001-pll-architecture.md.
Connectivity is label-driven (lab_pin stubs on every device terminal),
matching the gf180-pll/sky130-pll fleet convention documented in
design/README.md.
DR-001 Decision 2 Consequences / DR-002 Decision 4: passive monitor, no FSM, no loop-node drive.
SG13CMOS5L port (issue #22, DR-004): cap_cmim (MIM, unavailable on SG13CMOS5L per DR-003 Finding 2) replaced by cap_cmomi (interdigitated MOM). mmin/mmax/feed/subblock/mm_ok have no cap_cmim equivalent and are set to the PDK's own documented defaults: full M1-M4 stack, double-sided feed. See design/README.md SG13CMOS5L section for the full per-instance mapping table and DR-004 for the MoM 'not validated on CMOS5L silicon' caveat this carries forward from DR-003 Finding 2.
Issue #52 (Part of #16) re-derived XRPU (rhigh, was w=0.5u l=6u) and XCW (cap_cmomi, was w=8u l=8u m=1) from issue #38's RECORD-001 measurement that the integrating node's R*C time constant sat 23-1412x BELOW the reference period at every corner, so the node tracked the coincidence gate almost combinationally instead of averaging it over many reference cycles. XRPU l=700u (R = 1.35-3.30 MOhm over res_bcs/res_typ/res_wcs x -40/27/125C) with XCW w=40u l=40u m=1 (1.691 pF nominal) puts R*C at 2.29-5.58 us, i.e. 8.0-19.5x ABOVE the slowest period of row 2's DR-005-amended f_ref range (3.5-24.4 MHz, T_ref <= 286 ns), and 6.4-23.4x once the +/-20% MOM-model-uncertainty band on XCW is included. Measured consequence: the block is steady at the deep out-of-lock phase error at every ladder corner re-measured, where RECORD-001 found chatter at 92/92 -- see sim/sg13cmos5l-lock-detector-window/records/RECORD-002-resized-window-hysteresis-chatter.md. XCW is therefore no longer the "provisional placeholder size" design/README.md's cap_cmomi table used to record for this instance (delaywin_hv's own XC1, one schematic level down, was re-derived by the same issue -- see delaywin_hv.sch's own header).
NOT fixed by issue #52, and NOT to be read as passing row 16 in full: the hysteresis criterion (>= 25% of window) still fails, and RECORD-002 attributes that to two things outside the three instances #52 resized -- XSCH (schmitt_hv) has its two feedback devices tied to the wrong rails, measuring 1.1 mV of input-referred hysteresis where the classic connection measures 932 mV; and the settled-VWIN-vs-phase-error characteristic is far too steep for any Schmitt hysteresis to become a >= 25%-of-window PHASE-ERROR width, that steepness being set by the XRPU/XMPD strength ratio rather than by R*C. Do not "fix" either by moving XRPU or XCW: that trades the R*C margin above straight back for it.
}
G {}
K {}
V {}
S {}
E {}
C {xor2_hv.sym} 0 -300 0 0 {name=XXOR }
C {lab_pin.sym} -40 -320 0 0 {name=l1 lab=UP}
C {lab_pin.sym} -40 -280 0 0 {name=l2 lab=DN}
C {lab_pin.sym} 40 -300 0 0 {name=l3 lab=ERR}
C {lab_pin.sym} -20 -380 0 0 {name=l4 lab=VDD}
C {lab_pin.sym} 20 -220 0 0 {name=l5 lab=VSS}
C {delaywin_hv.sym} 350 -300 0 0 {name=XDW }
C {lab_pin.sym} 310 -300 0 0 {name=l6 lab=ERR}
C {lab_pin.sym} 390 -300 0 0 {name=l7 lab=ERRD}
C {lab_pin.sym} 330 -340 0 0 {name=l8 lab=VDD}
C {lab_pin.sym} 370 -260 0 0 {name=l9 lab=VSS}
C {nand2_hv.sym} 700 -150 0 0 {name=XNW }
C {lab_pin.sym} 660 -170 0 0 {name=l10 lab=ERR}
C {lab_pin.sym} 660 -130 0 0 {name=l11 lab=ERRD}
C {lab_pin.sym} 740 -150 0 0 {name=l12 lab=nwide}
C {lab_pin.sym} 680 -230 0 0 {name=l13 lab=VDD}
C {lab_pin.sym} 720 -70 0 0 {name=l14 lab=VSS}
C {inv_hv.sym} 1000 -150 0 0 {name=XIW }
C {lab_pin.sym} 960 -150 0 0 {name=l15 lab=nwide}
C {lab_pin.sym} 1040 -150 0 0 {name=l16 lab=WIDE}
C {lab_pin.sym} 980 -190 0 0 {name=l17 lab=VDD}
C {lab_pin.sym} 1020 -110 0 0 {name=l18 lab=VSS}
C {sg13cmos5l_pr/rhigh.sym} 1300 -400 0 0 {name=RPU model=rhigh body=sub! spiceprefix=X w=0.5u l=700u b=0 m=1}
C {lab_pin.sym} 1300 -430 0 0 {name=l19 lab=VDD}
C {lab_pin.sym} 1300 -370 0 0 {name=l20 lab=VWIN}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 1300 -100 0 0 {name=MPD model=sg13_hv_nmos w=2u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 1320 -130 0 0 {name=l21 lab=VWIN}
C {lab_pin.sym} 1280 -100 0 0 {name=l22 lab=WIDE}
C {lab_pin.sym} 1320 -70 0 0 {name=l23 lab=VSS}
C {lab_pin.sym} 1320 -100 0 0 {name=l24 lab=VSS}
C {sg13cmos5l_pr/cap_cmomi.sym} 1600 -400 0 0 {name=CW model=cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double subblock=0 mm_ok=1 m=1 spiceprefix=X}
C {lab_pin.sym} 1600 -430 0 0 {name=l25 lab=VWIN}
C {lab_pin.sym} 1600 -370 0 0 {name=l26 lab=VSS}
C {schmitt_hv.sym} 1300 200 0 0 {name=XSCH }
C {lab_pin.sym} 1260 200 0 0 {name=l27 lab=VWIN}
C {lab_pin.sym} 1340 200 0 0 {name=l28 lab=LOCK}
C {lab_pin.sym} 1280 160 0 0 {name=l29 lab=VDD}
C {lab_pin.sym} 1320 240 0 0 {name=l30 lab=VSS}
C {ipin.sym} -250 -330 0 0 {name=p1 lab=UP}
C {ipin.sym} -250 -270 0 0 {name=p2 lab=DN}
C {opin.sym} 1650 200 0 0 {name=p3 lab=LOCK}
C {iopin.sym} -250 -700 0 0 {name=p4 lab=VDD}
C {iopin.sym} -250 700 0 0 {name=p5 lab=VSS}
