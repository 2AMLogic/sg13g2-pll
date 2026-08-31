v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: delaywin_hv -- 4-stage inverter delay chain w/ MIM cap load (comparator window)
Device flavour: SG13G2 3.3V thick-oxide CMOS throughout (sg13_hv_nmos /
sg13_hv_pmos), per spec/decision-records/DR-002-supply-device-flavor.md
Decision 0. Sizing is a first-pass, provisional placeholder (not yet
simulation-grounded against real SG13G2 device data) -- a future
device-characterization / tuning-range campaign (T1 items 8-9, out of
this issue's scope per spec/porting-plan.md and issue #7's Non-goals)
re-derives every number here, per spec/decision-records/DR-001-pll-architecture.md.
EXCEPTION (issue #82): XC1 is no longer a placeholder. w=45u l=45u m=1 is
derived from sim/sg13g2-lock-detector-window/corners/window_sizing.csv --
the smallest cap_cmim geometry swept whose worst-case (fast-stack) twin_r
clears spec/porting-plan.md row 16's 2.5 ns assert-window floor with margin;
measured 3.732-10.249 ns over the PVT grid. See that slug's RECORD-001.
The four inverters are untouched and remain provisional.
Connectivity is label-driven (lab_pin stubs on every device terminal),
matching the gf180-pll/sky130-pll fleet convention documented in
design/README.md.
}
G {}
K {}
V {}
S {}
E {}
C {inv_hv.sym} 0 0 0 0 {name=XI1 }
C {lab_pin.sym} -40 0 0 0 {name=l1 lab=IN}
C {lab_pin.sym} 40 0 0 0 {name=l2 lab=d1}
C {lab_pin.sym} -20 -40 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 40 0 0 {name=l4 lab=VSS}
C {inv_hv.sym} 250 0 0 0 {name=XI2 }
C {lab_pin.sym} 210 0 0 0 {name=l5 lab=d1}
C {lab_pin.sym} 290 0 0 0 {name=l6 lab=d2}
C {lab_pin.sym} 230 -40 0 0 {name=l7 lab=VDD}
C {lab_pin.sym} 270 40 0 0 {name=l8 lab=VSS}
C {inv_hv.sym} 500 0 0 0 {name=XI3 }
C {lab_pin.sym} 460 0 0 0 {name=l9 lab=d2}
C {lab_pin.sym} 540 0 0 0 {name=l10 lab=d3}
C {lab_pin.sym} 480 -40 0 0 {name=l11 lab=VDD}
C {lab_pin.sym} 520 40 0 0 {name=l12 lab=VSS}
C {inv_hv.sym} 750 0 0 0 {name=XI4 }
C {lab_pin.sym} 710 0 0 0 {name=l13 lab=d3}
C {lab_pin.sym} 790 0 0 0 {name=l14 lab=OUT}
C {lab_pin.sym} 730 -40 0 0 {name=l15 lab=VDD}
C {lab_pin.sym} 770 40 0 0 {name=l16 lab=VSS}
C {sg13g2_pr/cap_cmim.sym} 1100 0 0 0 {name=C1 model=cap_cmim w=45u l=45u m=1 spiceprefix=X}
C {lab_pin.sym} 1100 -30 0 0 {name=l17 lab=OUT}
C {lab_pin.sym} 1100 30 0 0 {name=l18 lab=VSS}
C {ipin.sym} -250 0 0 0 {name=p1 lab=IN}
C {opin.sym} 1300 0 0 0 {name=p2 lab=OUT}
C {iopin.sym} -250 -300 0 0 {name=p3 lab=VDD}
C {iopin.sym} -250 300 0 0 {name=p4 lab=VSS}
