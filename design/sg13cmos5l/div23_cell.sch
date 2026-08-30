v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: div23_cell -- one /2//3 divider cell (Vaucher-style modular cell)
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
DR-001 Decision 3. Q'=/Q./(MODIN.P.MODOUT), MODOUT'=MODIN.Q -- MODOUT is this cell's OWN state (an output, fed back into its own AND3 gate and also driving the next-faster cell's MODIN), not an external input. Q doubles as this cell's own clock output for the next-faster cell in the cascade (no separate CKOUT pin), built from dff_tg_hv + static-CMOS combinational logic.
SG13CMOS5L port (issue #22, DR-004): pure hierarchy, no direct PDK device instance in this cell -- nothing to substitute here; see the leaf cells this composes for the actual device-symbol path changes.
}
G {}
K {}
V {}
S {}
E {}
C {nand3_hv.sym} 0 -300 0 0 {name=XN3 }
C {lab_pin.sym} -40 -340 0 0 {name=l1 lab=MODIN}
C {lab_pin.sym} -40 -300 0 0 {name=l2 lab=P}
C {lab_pin.sym} -40 -260 0 0 {name=l3 lab=MODOUT}
C {lab_pin.sym} 40 -300 0 0 {name=l4 lab=nt}
C {lab_pin.sym} -20 -420 0 0 {name=l5 lab=VDD}
C {lab_pin.sym} 20 -180 0 0 {name=l6 lab=VSS}
C {inv_hv.sym} 350 -300 0 0 {name=XI1 }
C {lab_pin.sym} 310 -300 0 0 {name=l7 lab=nt}
C {lab_pin.sym} 390 -300 0 0 {name=l8 lab=t1}
C {lab_pin.sym} 330 -340 0 0 {name=l9 lab=VDD}
C {lab_pin.sym} 370 -260 0 0 {name=l10 lab=VSS}
C {nor2_hv.sym} 650 -100 0 0 {name=XNOR }
C {lab_pin.sym} 610 -120 0 0 {name=l11 lab=Q}
C {lab_pin.sym} 610 -80 0 0 {name=l12 lab=t1}
C {lab_pin.sym} 690 -100 0 0 {name=l13 lab=dq}
C {lab_pin.sym} 630 -180 0 0 {name=l14 lab=VDD}
C {lab_pin.sym} 670 -20 0 0 {name=l15 lab=VSS}
C {dff_tg_hv.sym} 1000 -300 0 0 {name=XDFFQ }
C {lab_pin.sym} 960 -320 0 0 {name=l16 lab=dq}
C {lab_pin.sym} 960 -280 0 0 {name=l17 lab=CKIN}
C {lab_pin.sym} 1040 -300 0 0 {name=l18 lab=Q}
C {lab_pin.sym} 980 -380 0 0 {name=l19 lab=VDD}
C {lab_pin.sym} 1020 -220 0 0 {name=l20 lab=VSS}
C {nand2_hv.sym} 0 300 0 0 {name=XN2 }
C {lab_pin.sym} -40 280 0 0 {name=l21 lab=MODIN}
C {lab_pin.sym} -40 320 0 0 {name=l22 lab=Q}
C {lab_pin.sym} 40 300 0 0 {name=l23 lab=nm}
C {lab_pin.sym} -20 220 0 0 {name=l24 lab=VDD}
C {lab_pin.sym} 20 380 0 0 {name=l25 lab=VSS}
C {inv_hv.sym} 350 300 0 0 {name=XI2 }
C {lab_pin.sym} 310 300 0 0 {name=l26 lab=nm}
C {lab_pin.sym} 390 300 0 0 {name=l27 lab=dmodout}
C {lab_pin.sym} 330 260 0 0 {name=l28 lab=VDD}
C {lab_pin.sym} 370 340 0 0 {name=l29 lab=VSS}
C {dff_tg_hv.sym} 1000 300 0 0 {name=XDFFM }
C {lab_pin.sym} 960 280 0 0 {name=l30 lab=dmodout}
C {lab_pin.sym} 960 320 0 0 {name=l31 lab=CKIN}
C {lab_pin.sym} 1040 300 0 0 {name=l32 lab=MODOUT}
C {lab_pin.sym} 980 220 0 0 {name=l33 lab=VDD}
C {lab_pin.sym} 1020 380 0 0 {name=l34 lab=VSS}
C {ipin.sym} -300 -300 0 0 {name=p1 lab=MODIN}
C {ipin.sym} -300 -100 0 0 {name=p2 lab=P}
C {ipin.sym} -300 -700 0 0 {name=p3 lab=CKIN}
C {opin.sym} 1350 -300 0 0 {name=p4 lab=Q}
C {opin.sym} 1350 100 0 0 {name=p5 lab=MODOUT}
C {iopin.sym} -300 -1000 0 0 {name=p6 lab=VDD}
C {iopin.sym} -300 1000 0 0 {name=p7 lab=VSS}
