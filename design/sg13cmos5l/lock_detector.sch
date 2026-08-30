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
SG13CMOS5L port (issue #22, DR-004): cap_cmim (MIM, unavailable on SG13CMOS5L per DR-003 Finding 2) replaced by cap_cmomi (interdigitated MOM). Sizes are chosen so cap_cmomi.tcl's own display-capacitance formula lands within ~10% of the original cap_cmim instance's value -- a provisional placeholder, not a re-derived size (mmin/mmax/feed/subblock/mm_ok have no cap_cmim equivalent and are set to the PDK's own documented defaults: full M1-M4 stack, double-sided feed). See design/README.md SG13CMOS5L section for the full per-instance mapping table and DR-004 for the MoM 'not validated on CMOS5L silicon' caveat this carries forward from DR-003 Finding 2.
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
C {sg13cmos5l_pr/rhigh.sym} 1300 -400 0 0 {name=RPU model=rhigh body=sub! spiceprefix=X w=0.5u l=6u b=0 m=1}
C {lab_pin.sym} 1300 -430 0 0 {name=l19 lab=VDD}
C {lab_pin.sym} 1300 -370 0 0 {name=l20 lab=VWIN}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 1300 -100 0 0 {name=MPD model=sg13_hv_nmos w=2u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 1320 -130 0 0 {name=l21 lab=VWIN}
C {lab_pin.sym} 1280 -100 0 0 {name=l22 lab=WIDE}
C {lab_pin.sym} 1320 -70 0 0 {name=l23 lab=VSS}
C {lab_pin.sym} 1320 -100 0 0 {name=l24 lab=VSS}
C {sg13cmos5l_pr/cap_cmomi.sym} 1600 -400 0 0 {name=CW model=cap_cmomi w=8u l=8u mmin=1 mmax=4 feed=double subblock=0 mm_ok=1 m=1 spiceprefix=X}
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
