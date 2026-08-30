v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: pfd -- tri-state PFD: 2x edgedet + 2x srlatch, shared AND(UP,DN) reset
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
DR-001 Decision 1 loop type. Reset-delay margin is a 3-stage inverter buffer here -- a simplified placeholder for gf180-pll's measured 24-stage charge-domain-sized reset chain (design/README.md "PFD (pfd.sch)"); re-sizing this against real charge-pump turn-on data is future device-characterization work, out of this issue's scope (issue #7 Non-goals).
Issue #56: the reset chain must produce reset = AND(UP,DN) (ODD inverter
count after reset_raw = NAND(UP,DN)) so the SR latches (srlatch.sym) stay
non-transparent except right at a UP/DN coincidence -- see
sim/sg13cmos5l-closed-loop-lock/records/RECORD-002-pfd-reset-parity-root-cause.md.
The as-drawn 2-stage buffer (XI1, XI2) had EVEN parity, handing reset back
as NAND(UP,DN) instead; XI1B below is the third stage that restores odd
parity.
SG13CMOS5L port (issue #22, DR-004): pure hierarchy, no direct PDK device instance in this cell -- nothing to substitute here; see the leaf cells this composes for the actual device-symbol path changes.
}
G {}
K {}
V {}
S {}
E {}
C {edgedet.sym} 0 -300 0 0 {name=XED_UP }
C {lab_pin.sym} -40 -300 0 0 {name=l1 lab=REF}
C {lab_pin.sym} 40 -300 0 0 {name=l2 lab=set_up}
C {lab_pin.sym} -20 -340 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 -260 0 0 {name=l4 lab=VSS}
C {edgedet.sym} 0 300 0 0 {name=XED_DN }
C {lab_pin.sym} -40 300 0 0 {name=l5 lab=FB}
C {lab_pin.sym} 40 300 0 0 {name=l6 lab=set_dn}
C {lab_pin.sym} -20 260 0 0 {name=l7 lab=VDD}
C {lab_pin.sym} 20 340 0 0 {name=l8 lab=VSS}
C {srlatch.sym} 500 -300 0 0 {name=XLU }
C {lab_pin.sym} 460 -320 0 0 {name=l9 lab=set_up}
C {lab_pin.sym} 460 -280 0 0 {name=l10 lab=reset}
C {lab_pin.sym} 540 -320 0 0 {name=l11 lab=UP}
C {lab_pin.sym} 480 -380 0 0 {name=l12 lab=VDD}
C {lab_pin.sym} 520 -220 0 0 {name=l13 lab=VSS}
C {srlatch.sym} 500 300 0 0 {name=XLD }
C {lab_pin.sym} 460 280 0 0 {name=l14 lab=set_dn}
C {lab_pin.sym} 460 320 0 0 {name=l15 lab=reset}
C {lab_pin.sym} 540 280 0 0 {name=l16 lab=DN}
C {lab_pin.sym} 480 220 0 0 {name=l17 lab=VDD}
C {lab_pin.sym} 520 380 0 0 {name=l18 lab=VSS}
C {nand2_hv.sym} 900 0 0 0 {name=XNR }
C {lab_pin.sym} 860 -20 0 0 {name=l19 lab=UP}
C {lab_pin.sym} 860 20 0 0 {name=l20 lab=DN}
C {lab_pin.sym} 940 0 0 0 {name=l21 lab=reset_raw}
C {lab_pin.sym} 880 -80 0 0 {name=l22 lab=VDD}
C {lab_pin.sym} 920 80 0 0 {name=l23 lab=VSS}
C {inv_hv.sym} 1200 0 0 0 {name=XI1 }
C {lab_pin.sym} 1160 0 0 0 {name=l24 lab=reset_raw}
C {lab_pin.sym} 1240 0 0 0 {name=l25 lab=reset_d1}
C {lab_pin.sym} 1180 -40 0 0 {name=l26 lab=VDD}
C {lab_pin.sym} 1220 40 0 0 {name=l27 lab=VSS}
C {inv_hv.sym} 1500 0 0 0 {name=XI1B }
C {lab_pin.sym} 1460 0 0 0 {name=l28 lab=reset_d1}
C {lab_pin.sym} 1540 0 0 0 {name=l29 lab=reset_d2}
C {lab_pin.sym} 1480 -40 0 0 {name=l30 lab=VDD}
C {lab_pin.sym} 1520 40 0 0 {name=l31 lab=VSS}
C {inv2x_hv.sym} 1800 0 0 0 {name=XI2 }
C {lab_pin.sym} 1760 0 0 0 {name=l32 lab=reset_d2}
C {lab_pin.sym} 1840 0 0 0 {name=l33 lab=reset}
C {lab_pin.sym} 1780 -40 0 0 {name=l34 lab=VDD}
C {lab_pin.sym} 1820 40 0 0 {name=l35 lab=VSS}
C {ipin.sym} -250 -300 0 0 {name=p1 lab=REF}
C {ipin.sym} -250 300 0 0 {name=p2 lab=FB}
C {opin.sym} 750 -300 0 0 {name=p3 lab=UP}
C {opin.sym} 750 300 0 0 {name=p4 lab=DN}
C {iopin.sym} -250 -600 0 0 {name=p5 lab=VDD}
C {iopin.sym} -250 600 0 0 {name=p6 lab=VSS}
