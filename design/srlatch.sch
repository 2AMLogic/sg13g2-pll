v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: srlatch -- NAND cross-coupled SR latch, active-high S/R interface
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
C {inv_hv.sym} 0 -200 0 0 {name=XIS }
C {lab_pin.sym} -40 -200 0 0 {name=l1 lab=S}
C {lab_pin.sym} 40 -200 0 0 {name=l2 lab=SB}
C {lab_pin.sym} -20 -240 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 -160 0 0 {name=l4 lab=VSS}
C {inv_hv.sym} 0 200 0 0 {name=XIR }
C {lab_pin.sym} -40 200 0 0 {name=l5 lab=R}
C {lab_pin.sym} 40 200 0 0 {name=l6 lab=RB}
C {lab_pin.sym} -20 160 0 0 {name=l7 lab=VDD}
C {lab_pin.sym} 20 240 0 0 {name=l8 lab=VSS}
C {nand2_hv.sym} 400 -100 0 0 {name=XNQ }
C {lab_pin.sym} 360 -120 0 0 {name=l9 lab=SB}
C {lab_pin.sym} 360 -80 0 0 {name=l10 lab=QB}
C {lab_pin.sym} 440 -100 0 0 {name=l11 lab=Q}
C {lab_pin.sym} 380 -180 0 0 {name=l12 lab=VDD}
C {lab_pin.sym} 420 -20 0 0 {name=l13 lab=VSS}
C {nand2_hv.sym} 400 200 0 0 {name=XNQB }
C {lab_pin.sym} 360 180 0 0 {name=l14 lab=RB}
C {lab_pin.sym} 360 220 0 0 {name=l15 lab=Q}
C {lab_pin.sym} 440 200 0 0 {name=l16 lab=QB}
C {lab_pin.sym} 380 120 0 0 {name=l17 lab=VDD}
C {lab_pin.sym} 420 280 0 0 {name=l18 lab=VSS}
C {ipin.sym} -250 -200 0 0 {name=p1 lab=S}
C {ipin.sym} -250 200 0 0 {name=p2 lab=R}
C {opin.sym} 700 -100 0 0 {name=p3 lab=Q}
C {opin.sym} 700 200 0 0 {name=p4 lab=QB}
C {iopin.sym} -250 -500 0 0 {name=p5 lab=VDD}
C {iopin.sym} -250 500 0 0 {name=p6 lab=VSS}
