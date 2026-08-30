v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: xor2_hv -- 2-input XOR (4x nand2_hv)
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
SG13CMOS5L port (issue #22, DR-004): pure hierarchy, no direct PDK device instance in this cell -- nothing to substitute here; see the leaf cells this composes for the actual device-symbol path changes.
}
G {}
K {}
V {}
S {}
E {}
C {nand2_hv.sym} 0 0 0 0 {name=XN1 }
C {nand2_hv.sym} 300 -150 0 0 {name=XN2 }
C {nand2_hv.sym} 300 150 0 0 {name=XN3 }
C {nand2_hv.sym} 600 0 0 0 {name=XN4 }
C {lab_pin.sym} -40 -20 0 0 {name=l1 lab=A}
C {lab_pin.sym} -40 20 0 0 {name=l2 lab=B}
C {lab_pin.sym} 40 0 0 0 {name=l3 lab=n1}
C {lab_pin.sym} -20 -80 0 0 {name=l4 lab=VDD}
C {lab_pin.sym} 20 80 0 0 {name=l5 lab=VSS}
C {lab_pin.sym} 260 -170 0 0 {name=l6 lab=A}
C {lab_pin.sym} 260 -130 0 0 {name=l7 lab=n1}
C {lab_pin.sym} 340 -150 0 0 {name=l8 lab=n2}
C {lab_pin.sym} 280 -230 0 0 {name=l9 lab=VDD}
C {lab_pin.sym} 320 -70 0 0 {name=l10 lab=VSS}
C {lab_pin.sym} 260 130 0 0 {name=l11 lab=B}
C {lab_pin.sym} 260 170 0 0 {name=l12 lab=n1}
C {lab_pin.sym} 340 150 0 0 {name=l13 lab=n3}
C {lab_pin.sym} 280 70 0 0 {name=l14 lab=VDD}
C {lab_pin.sym} 320 230 0 0 {name=l15 lab=VSS}
C {lab_pin.sym} 560 -20 0 0 {name=l16 lab=n2}
C {lab_pin.sym} 560 20 0 0 {name=l17 lab=n3}
C {lab_pin.sym} 640 0 0 0 {name=l18 lab=Y}
C {lab_pin.sym} 580 -80 0 0 {name=l19 lab=VDD}
C {lab_pin.sym} 620 80 0 0 {name=l20 lab=VSS}
C {ipin.sym} -250 -30 0 0 {name=p1 lab=A}
C {ipin.sym} -250 30 0 0 {name=p2 lab=B}
C {opin.sym} 900 0 0 0 {name=p3 lab=Y}
C {iopin.sym} -250 -300 0 0 {name=p4 lab=VDD}
C {iopin.sym} -250 400 0 0 {name=p5 lab=VSS}
