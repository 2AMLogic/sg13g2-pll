v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: dff_tg_hv -- transmission-gate master-slave positive-edge-triggered DFF
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
C {inv_hv.sym} 0 -400 0 0 {name=XICLK }
C {lab_pin.sym} -40 -400 0 0 {name=l1 lab=CLK}
C {lab_pin.sym} 40 -400 0 0 {name=l2 lab=CLKB}
C {lab_pin.sym} -20 -440 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 -360 0 0 {name=l4 lab=VSS}
C {tgate_hv.sym} 300 0 0 0 {name=XTG1 }
C {lab_pin.sym} 260 -40 0 0 {name=l5 lab=D}
C {lab_pin.sym} 340 0 0 0 {name=l6 lab=M}
C {lab_pin.sym} 260 0 0 0 {name=l7 lab=CLKB}
C {lab_pin.sym} 260 40 0 0 {name=l8 lab=CLK}
C {lab_pin.sym} 280 -120 0 0 {name=l9 lab=VDD}
C {lab_pin.sym} 320 120 0 0 {name=l10 lab=VSS}
C {inv_hv.sym} 600 0 0 0 {name=XIM }
C {lab_pin.sym} 560 0 0 0 {name=l11 lab=M}
C {lab_pin.sym} 640 0 0 0 {name=l12 lab=MB}
C {lab_pin.sym} 580 -40 0 0 {name=l13 lab=VDD}
C {lab_pin.sym} 620 40 0 0 {name=l14 lab=VSS}
C {tgate_hv.sym} 900 0 0 0 {name=XTGFBM }
C {lab_pin.sym} 860 -40 0 0 {name=l15 lab=MB}
C {lab_pin.sym} 940 0 0 0 {name=l16 lab=M}
C {lab_pin.sym} 860 0 0 0 {name=l17 lab=CLK}
C {lab_pin.sym} 860 40 0 0 {name=l18 lab=CLKB}
C {lab_pin.sym} 880 -120 0 0 {name=l19 lab=VDD}
C {lab_pin.sym} 920 120 0 0 {name=l20 lab=VSS}
C {tgate_hv.sym} 1200 0 0 0 {name=XTG2 }
C {lab_pin.sym} 1160 -40 0 0 {name=l21 lab=M}
C {lab_pin.sym} 1240 0 0 0 {name=l22 lab=S}
C {lab_pin.sym} 1160 0 0 0 {name=l23 lab=CLK}
C {lab_pin.sym} 1160 40 0 0 {name=l24 lab=CLKB}
C {lab_pin.sym} 1180 -120 0 0 {name=l25 lab=VDD}
C {lab_pin.sym} 1220 120 0 0 {name=l26 lab=VSS}
C {inv_hv.sym} 1500 0 0 0 {name=XIS }
C {lab_pin.sym} 1460 0 0 0 {name=l27 lab=S}
C {lab_pin.sym} 1540 0 0 0 {name=l28 lab=SB}
C {lab_pin.sym} 1480 -40 0 0 {name=l29 lab=VDD}
C {lab_pin.sym} 1520 40 0 0 {name=l30 lab=VSS}
C {tgate_hv.sym} 1800 0 0 0 {name=XTGFBS }
C {lab_pin.sym} 1760 -40 0 0 {name=l31 lab=SB}
C {lab_pin.sym} 1840 0 0 0 {name=l32 lab=S}
C {lab_pin.sym} 1760 0 0 0 {name=l33 lab=CLKB}
C {lab_pin.sym} 1760 40 0 0 {name=l34 lab=CLK}
C {lab_pin.sym} 1780 -120 0 0 {name=l35 lab=VDD}
C {lab_pin.sym} 1820 120 0 0 {name=l36 lab=VSS}
C {inv_hv.sym} 2100 0 0 0 {name=XBQ }
C {lab_pin.sym} 2060 0 0 0 {name=l37 lab=SB}
C {lab_pin.sym} 2140 0 0 0 {name=l38 lab=Q}
C {lab_pin.sym} 2080 -40 0 0 {name=l39 lab=VDD}
C {lab_pin.sym} 2120 40 0 0 {name=l40 lab=VSS}
C {ipin.sym} -250 0 0 0 {name=p1 lab=D}
C {ipin.sym} -250 -400 0 0 {name=p2 lab=CLK}
C {opin.sym} 2350 0 0 0 {name=p3 lab=Q}
C {iopin.sym} -250 -700 0 0 {name=p4 lab=VDD}
C {iopin.sym} -250 700 0 0 {name=p5 lab=VSS}
