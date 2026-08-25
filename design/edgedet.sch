v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: edgedet -- rising-edge pulse: AND(X, NOT(X delayed 5 inverters))
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
5-stage (odd) inverter chain per gf180-pll design/README.md's own edgedet sizing rationale: an odd count makes the chain's own output the already-inverted delayed copy, so OUT = NAND(X,XD5) + INV = AND(X, NOT(delay(X))) with no extra inverter needed on that leg.
}
G {}
K {}
V {}
S {}
E {}
C {inv_hv.sym} 0 0 0 0 {name=XD1 }
C {lab_pin.sym} -40 0 0 0 {name=l1 lab=X}
C {lab_pin.sym} 40 0 0 0 {name=l2 lab=d1}
C {lab_pin.sym} -20 -40 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 40 0 0 {name=l4 lab=VSS}
C {inv_hv.sym} 250 0 0 0 {name=XD2 }
C {lab_pin.sym} 210 0 0 0 {name=l5 lab=d1}
C {lab_pin.sym} 290 0 0 0 {name=l6 lab=d2}
C {lab_pin.sym} 230 -40 0 0 {name=l7 lab=VDD}
C {lab_pin.sym} 270 40 0 0 {name=l8 lab=VSS}
C {inv_hv.sym} 500 0 0 0 {name=XD3 }
C {lab_pin.sym} 460 0 0 0 {name=l9 lab=d2}
C {lab_pin.sym} 540 0 0 0 {name=l10 lab=d3}
C {lab_pin.sym} 480 -40 0 0 {name=l11 lab=VDD}
C {lab_pin.sym} 520 40 0 0 {name=l12 lab=VSS}
C {inv_hv.sym} 750 0 0 0 {name=XD4 }
C {lab_pin.sym} 710 0 0 0 {name=l13 lab=d3}
C {lab_pin.sym} 790 0 0 0 {name=l14 lab=d4}
C {lab_pin.sym} 730 -40 0 0 {name=l15 lab=VDD}
C {lab_pin.sym} 770 40 0 0 {name=l16 lab=VSS}
C {inv_hv.sym} 1000 0 0 0 {name=XD5 }
C {lab_pin.sym} 960 0 0 0 {name=l17 lab=d4}
C {lab_pin.sym} 1040 0 0 0 {name=l18 lab=XD5}
C {lab_pin.sym} 980 -40 0 0 {name=l19 lab=VDD}
C {lab_pin.sym} 1020 40 0 0 {name=l20 lab=VSS}
C {nand2_hv.sym} 1400 0 0 0 {name=XN1 }
C {lab_pin.sym} 1360 -20 0 0 {name=l21 lab=X}
C {lab_pin.sym} 1360 20 0 0 {name=l22 lab=XD5}
C {lab_pin.sym} 1440 0 0 0 {name=l23 lab=ntmp}
C {lab_pin.sym} 1380 -80 0 0 {name=l24 lab=VDD}
C {lab_pin.sym} 1420 80 0 0 {name=l25 lab=VSS}
C {inv_hv.sym} 1700 0 0 0 {name=XOUT }
C {lab_pin.sym} 1660 0 0 0 {name=l26 lab=ntmp}
C {lab_pin.sym} 1740 0 0 0 {name=l27 lab=OUT}
C {lab_pin.sym} 1680 -40 0 0 {name=l28 lab=VDD}
C {lab_pin.sym} 1720 40 0 0 {name=l29 lab=VSS}
C {ipin.sym} -250 0 0 0 {name=p1 lab=X}
C {opin.sym} 1950 0 0 0 {name=p2 lab=OUT}
C {iopin.sym} -250 -300 0 0 {name=p3 lab=VDD}
C {iopin.sym} -250 300 0 0 {name=p4 lab=VSS}
