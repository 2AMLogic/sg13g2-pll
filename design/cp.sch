v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: cp -- charge pump: single unit leg per polarity + tracking dump node
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
DR-001 Decision 1 / DR-002 Decision 2 (CMOS wide-swing cascode, no HBT). No Icp unit-element trim in this v1 pass -- a single fixed-current leg per polarity, documented simplification of gf180-pll's 2-bit trim (design/README.md "Charge pump (cp.sch)"); IBIAS for cp_dumpbuf's tail is reused from ICN as a v1 wiring simplification rather than adding a dedicated bias pin.
}
G {}
K {}
V {}
S {}
E {}
C {inv_hv.sym} 0 -300 0 0 {name=XIUP }
C {lab_pin.sym} -40 -300 0 0 {name=l1 lab=UP}
C {lab_pin.sym} 40 -300 0 0 {name=l2 lab=UPB}
C {lab_pin.sym} -20 -340 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 -260 0 0 {name=l4 lab=VSS}
C {inv_hv.sym} 0 300 0 0 {name=XIDN }
C {lab_pin.sym} -40 300 0 0 {name=l5 lab=DN}
C {lab_pin.sym} 40 300 0 0 {name=l6 lab=DNB}
C {lab_pin.sym} -20 260 0 0 {name=l7 lab=VDD}
C {lab_pin.sym} 20 340 0 0 {name=l8 lab=VSS}
C {cp_leg_p.sym} 500 -300 0 0 {name=XLEGP }
C {lab_pin.sym} 460 -360 0 0 {name=l9 lab=IBP}
C {lab_pin.sym} 460 -320 0 0 {name=l10 lab=ICP}
C {lab_pin.sym} 460 -280 0 0 {name=l11 lab=UP}
C {lab_pin.sym} 460 -240 0 0 {name=l12 lab=UPB}
C {lab_pin.sym} 540 -320 0 0 {name=l13 lab=VOUT}
C {lab_pin.sym} 540 -280 0 0 {name=l14 lab=VDUMP}
C {lab_pin.sym} 500 -460 0 0 {name=l15 lab=VDD}
C {cp_leg_n.sym} 500 300 0 0 {name=XLEGN }
C {lab_pin.sym} 460 240 0 0 {name=l16 lab=IBN}
C {lab_pin.sym} 460 280 0 0 {name=l17 lab=ICN}
C {lab_pin.sym} 460 360 0 0 {name=l18 lab=DNB}
C {lab_pin.sym} 460 320 0 0 {name=l19 lab=DN}
C {lab_pin.sym} 540 280 0 0 {name=l20 lab=VOUT}
C {lab_pin.sym} 540 320 0 0 {name=l21 lab=VDUMP}
C {lab_pin.sym} 500 140 0 0 {name=l22 lab=VSS}
C {cp_dumpbuf.sym} 900 0 0 0 {name=XBUF }
C {lab_pin.sym} 860 -20 0 0 {name=l23 lab=VOUT}
C {lab_pin.sym} 860 20 0 0 {name=l24 lab=ICN}
C {lab_pin.sym} 940 0 0 0 {name=l25 lab=VDUMP}
C {lab_pin.sym} 880 -80 0 0 {name=l26 lab=VDD}
C {lab_pin.sym} 920 80 0 0 {name=l27 lab=VSS}
C {ipin.sym} -250 -300 0 0 {name=p1 lab=UP}
C {ipin.sym} -250 300 0 0 {name=p2 lab=DN}
C {ipin.sym} -250 -600 0 0 {name=p3 lab=IBP}
C {ipin.sym} -250 -500 0 0 {name=p4 lab=ICP}
C {ipin.sym} -250 600 0 0 {name=p5 lab=IBN}
C {ipin.sym} -250 500 0 0 {name=p6 lab=ICN}
C {opin.sym} 1200 0 0 0 {name=p7 lab=VOUT}
C {iopin.sym} -250 -900 0 0 {name=p8 lab=VDD}
C {iopin.sym} -250 900 0 0 {name=p9 lab=VSS}
