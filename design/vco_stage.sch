v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: vco_stage -- current-starved delay cell: PMOS head + inverter + NMOS tail
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
Matched PMOS-head/NMOS-tail starving devices per spec/porting-plan.md Sec1.4.
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/sg13_hv_pmos.sym} 0 -300 0 0 {name=MPH model=sg13_hv_pmos w=10u l=0.5u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_pmos.sym} 0 0 0 0 {name=MP model=sg13_hv_pmos w=5u l=0.28u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 0 300 0 0 {name=MN model=sg13_hv_nmos w=2u l=0.28u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 0 600 0 0 {name=MNT model=sg13_hv_nmos w=4u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 20 -330 0 0 {name=l1 lab=VDDV}
C {lab_pin.sym} -20 -300 0 0 {name=l2 lab=VBP}
C {lab_pin.sym} 20 -270 0 0 {name=l3 lab=nh}
C {lab_pin.sym} 20 -300 0 0 {name=l4 lab=VDDV}
C {lab_pin.sym} 20 -30 0 0 {name=l5 lab=nh}
C {lab_pin.sym} -20 0 0 0 {name=l6 lab=IN}
C {lab_pin.sym} 20 30 0 0 {name=l7 lab=OUT}
C {lab_pin.sym} 20 0 0 0 {name=l8 lab=VDDV}
C {lab_pin.sym} 20 330 0 0 {name=l9 lab=nt}
C {lab_pin.sym} -20 300 0 0 {name=l10 lab=IN}
C {lab_pin.sym} 20 270 0 0 {name=l11 lab=OUT}
C {lab_pin.sym} 20 300 0 0 {name=l12 lab=GNDV}
C {lab_pin.sym} 20 630 0 0 {name=l13 lab=GNDV}
C {lab_pin.sym} -20 600 0 0 {name=l14 lab=VBN}
C {lab_pin.sym} 20 570 0 0 {name=l15 lab=nt}
C {lab_pin.sym} 20 600 0 0 {name=l16 lab=GNDV}
C {ipin.sym} -350 0 0 0 {name=p1 lab=IN}
C {opin.sym} 350 30 0 0 {name=p2 lab=OUT}
C {ipin.sym} -350 -300 0 0 {name=p3 lab=VBP}
C {ipin.sym} -350 600 0 0 {name=p4 lab=VBN}
C {iopin.sym} -350 -600 0 0 {name=p5 lab=VDDV}
C {iopin.sym} -350 900 0 0 {name=p6 lab=GNDV}
