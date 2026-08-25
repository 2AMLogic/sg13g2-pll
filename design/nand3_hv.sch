v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: nand3_hv -- 3-input static CMOS NAND
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
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/sg13_hv_pmos.sym} 0 -100 0 0 {name=MP1 model=sg13_hv_pmos w=5u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} -20 -100 0 0 {name=l1 lab=A1}
C {lab_pin.sym} 20 -70 0 0 {name=l2 lab=Y}
C {lab_pin.sym} 20 -130 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 -100 0 0 {name=l4 lab=VDD}
C {sg13g2_pr/sg13_hv_pmos.sym} 150 -100 0 0 {name=MP2 model=sg13_hv_pmos w=5u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 130 -100 0 0 {name=l5 lab=A2}
C {lab_pin.sym} 170 -70 0 0 {name=l6 lab=Y}
C {lab_pin.sym} 170 -130 0 0 {name=l7 lab=VDD}
C {lab_pin.sym} 170 -100 0 0 {name=l8 lab=VDD}
C {sg13g2_pr/sg13_hv_pmos.sym} 300 -100 0 0 {name=MP3 model=sg13_hv_pmos w=5u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 280 -100 0 0 {name=l9 lab=A3}
C {lab_pin.sym} 320 -70 0 0 {name=l10 lab=Y}
C {lab_pin.sym} 320 -130 0 0 {name=l11 lab=VDD}
C {lab_pin.sym} 320 -100 0 0 {name=l12 lab=VDD}
C {sg13g2_pr/sg13_hv_nmos.sym} 0 150 0 0 {name=MN1 model=sg13_hv_nmos w=2u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} -20 150 0 0 {name=l13 lab=A1}
C {lab_pin.sym} 20 120 0 0 {name=l14 lab=Y}
C {lab_pin.sym} 20 180 0 0 {name=l15 lab=mid1}
C {lab_pin.sym} 20 150 0 0 {name=l16 lab=VSS}
C {sg13g2_pr/sg13_hv_nmos.sym} 150 150 0 0 {name=MN2 model=sg13_hv_nmos w=2u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 130 150 0 0 {name=l17 lab=A2}
C {lab_pin.sym} 170 120 0 0 {name=l18 lab=mid1}
C {lab_pin.sym} 170 180 0 0 {name=l19 lab=mid2}
C {lab_pin.sym} 170 150 0 0 {name=l20 lab=VSS}
C {sg13g2_pr/sg13_hv_nmos.sym} 300 150 0 0 {name=MN3 model=sg13_hv_nmos w=2u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 280 150 0 0 {name=l21 lab=A3}
C {lab_pin.sym} 320 120 0 0 {name=l22 lab=mid2}
C {lab_pin.sym} 320 180 0 0 {name=l23 lab=VSS}
C {lab_pin.sym} 320 150 0 0 {name=l24 lab=VSS}
C {opin.sym} -250 0 0 0 {name=p1 lab=Y}
C {ipin.sym} -250 300 0 0 {name=p2 lab=A1}
C {ipin.sym} -250 360 0 0 {name=p3 lab=A2}
C {ipin.sym} -250 420 0 0 {name=p4 lab=A3}
C {iopin.sym} -250 -300 0 0 {name=p5 lab=VDD}
C {iopin.sym} -250 600 0 0 {name=p6 lab=VSS}
