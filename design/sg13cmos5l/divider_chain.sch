v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: divider_chain -- 6-cell /2//3 cascade + VCO-clocked retiming flop
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
DR-001 Decision 3. SIMPLIFIED v1: the chain-length-termination and one-hot output mux described in gf180-pll's design/README.md ("divider_chain") -- the mechanism that covers the full N=4..64 range with NO holes using a variably-active shorter chain -- is deferred; this v1 hardwires all 6 cells always active (MODIN of the last cell tied high), giving continuous N coverage over the fixed chain's own natural range rather than the full programmable-length range. This is a documented scope reduction, not a silent one: DR-001 Decision 3 Consequences already states chain length and per-cell sizing are open until real divider-ratio design/sim work runs, which this issue's Non-goals exclude.
SG13CMOS5L port (issue #22, DR-004): pure hierarchy, no direct PDK device instance in this cell -- nothing to substitute here; see the leaf cells this composes for the actual device-symbol path changes.
}
G {}
K {}
V {}
S {}
E {}
C {div23_cell.sym} 0 -300 0 0 {name=XD0 }
C {lab_pin.sym} -40 -300 0 0 {name=l1 lab=P0}
C {lab_pin.sym} -20 -420 0 0 {name=l2 lab=VDD_DIV}
C {lab_pin.sym} 20 -180 0 0 {name=l3 lab=VSS}
C {div23_cell.sym} 500 -300 0 0 {name=XD1 }
C {lab_pin.sym} 460 -300 0 0 {name=l4 lab=P1}
C {lab_pin.sym} 480 -420 0 0 {name=l5 lab=VDD_DIV}
C {lab_pin.sym} 520 -180 0 0 {name=l6 lab=VSS}
C {div23_cell.sym} 1000 -300 0 0 {name=XD2 }
C {lab_pin.sym} 960 -300 0 0 {name=l7 lab=P2}
C {lab_pin.sym} 980 -420 0 0 {name=l8 lab=VDD_DIV}
C {lab_pin.sym} 1020 -180 0 0 {name=l9 lab=VSS}
C {div23_cell.sym} 1500 -300 0 0 {name=XD3 }
C {lab_pin.sym} 1460 -300 0 0 {name=l10 lab=P3}
C {lab_pin.sym} 1480 -420 0 0 {name=l11 lab=VDD_DIV}
C {lab_pin.sym} 1520 -180 0 0 {name=l12 lab=VSS}
C {div23_cell.sym} 2000 -300 0 0 {name=XD4 }
C {lab_pin.sym} 1960 -300 0 0 {name=l13 lab=P4}
C {lab_pin.sym} 1980 -420 0 0 {name=l14 lab=VDD_DIV}
C {lab_pin.sym} 2020 -180 0 0 {name=l15 lab=VSS}
C {div23_cell.sym} 2500 -300 0 0 {name=XD5 }
C {lab_pin.sym} 2460 -300 0 0 {name=l16 lab=P5}
C {lab_pin.sym} 2480 -420 0 0 {name=l17 lab=VDD_DIV}
C {lab_pin.sym} 2520 -180 0 0 {name=l18 lab=VSS}
C {lab_pin.sym} -40 -260 0 0 {name=l19 lab=CKIN}
C {lab_pin.sym} 40 -320 0 0 {name=l20 lab=ck1}
C {lab_pin.sym} 460 -260 0 0 {name=l21 lab=ck1}
C {lab_pin.sym} 540 -320 0 0 {name=l22 lab=ck2}
C {lab_pin.sym} 960 -260 0 0 {name=l23 lab=ck2}
C {lab_pin.sym} 1040 -320 0 0 {name=l24 lab=ck3}
C {lab_pin.sym} 1460 -260 0 0 {name=l25 lab=ck3}
C {lab_pin.sym} 1540 -320 0 0 {name=l26 lab=ck4}
C {lab_pin.sym} 1960 -260 0 0 {name=l27 lab=ck4}
C {lab_pin.sym} 2040 -320 0 0 {name=l28 lab=ck5}
C {lab_pin.sym} 2460 -260 0 0 {name=l29 lab=ck5}
C {lab_pin.sym} 2540 -320 0 0 {name=l30 lab=DIVOUT}
C {lab_pin.sym} -40 -340 0 0 {name=l31 lab=mod0}
C {lab_pin.sym} 540 -280 0 0 {name=l32 lab=mod0}
C {lab_pin.sym} 460 -340 0 0 {name=l33 lab=mod1}
C {lab_pin.sym} 1040 -280 0 0 {name=l34 lab=mod1}
C {lab_pin.sym} 960 -340 0 0 {name=l35 lab=mod2}
C {lab_pin.sym} 1540 -280 0 0 {name=l36 lab=mod2}
C {lab_pin.sym} 1460 -340 0 0 {name=l37 lab=mod3}
C {lab_pin.sym} 2040 -280 0 0 {name=l38 lab=mod3}
C {lab_pin.sym} 1960 -340 0 0 {name=l39 lab=mod4}
C {lab_pin.sym} 2540 -280 0 0 {name=l40 lab=mod4}
C {lab_pin.sym} 2460 -340 0 0 {name=l41 lab=VDD_DIV}
C {dff_tg_hv.sym} 2800 300 0 0 {name=XFRT }
C {lab_pin.sym} 2760 280 0 0 {name=l42 lab=DIVOUT}
C {lab_pin.sym} 2760 320 0 0 {name=l43 lab=CKIN_VCO}
C {lab_pin.sym} 2840 300 0 0 {name=l44 lab=FB}
C {lab_pin.sym} 2780 220 0 0 {name=l45 lab=VDD_DIV}
C {lab_pin.sym} 2820 380 0 0 {name=l46 lab=VSS}
C {ipin.sym} -300 -350 0 0 {name=p1 lab=CKIN}
C {ipin.sym} 2800 -200 0 0 {name=p2 lab=CKIN_VCO}
C {ipin.sym} -300 -20 0 0 {name=p3 lab=P0}
C {ipin.sym} -300 -60 0 0 {name=p4 lab=P1}
C {ipin.sym} -300 -100 0 0 {name=p5 lab=P2}
C {ipin.sym} -300 -140 0 0 {name=p6 lab=P3}
C {ipin.sym} -300 -180 0 0 {name=p7 lab=P4}
C {ipin.sym} -300 -220 0 0 {name=p8 lab=P5}
C {opin.sym} 3000 -100 0 0 {name=p9 lab=FB}
C {opin.sym} -300 700 0 0 {name=p10 lab=DIVOUT}
C {iopin.sym} -300 -700 0 0 {name=p11 lab=VDD_DIV}
C {iopin.sym} -300 1000 0 0 {name=p12 lab=VSS}
