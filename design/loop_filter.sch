v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: loop_filter -- passive fixed 2nd-order filter: series R + shunt C1 + C2
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
DR-001 Decision 1: no active filter, no R/C trim banks. R = rppd (LVS-recognized per klayout-tools PR #1236); C1/C2 = cap_cmim (MIM). MIM LVS recognition is an already-tracked, open upstream gap (klayout-tools #1233 "no MIM capacitor recognition") -- cited here per spec/decision-records/DR-002 Sec"Deck-gap check", not re-filed (audit-before-filing: #1233 already names cap_cmim specifically, so a new report would be a duplicate).
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/rppd.sym} 0 0 0 0 {name=R1 model=rppd body=sub! spiceprefix=X w=4u l=120u b=0 m=1}
C {sg13g2_pr/cap_cmim.sym} 400 300 0 0 {name=C1 model=cap_cmim w=40u l=40u m=1 spiceprefix=X}
C {sg13g2_pr/cap_cmim.sym} -400 -300 0 0 {name=C2 model=cap_cmim w=8u l=8u m=1 spiceprefix=X}
C {lab_pin.sym} 0 -30 0 0 {name=l1 lab=VCTRL}
C {lab_pin.sym} 0 30 0 0 {name=l2 lab=NZ}
C {lab_pin.sym} 400 270 0 0 {name=l3 lab=NZ}
C {lab_pin.sym} 400 330 0 0 {name=l4 lab=VSS}
C {lab_pin.sym} -400 -330 0 0 {name=l5 lab=VCTRL}
C {lab_pin.sym} -400 -270 0 0 {name=l6 lab=VSS}
C {iopin.sym} -600 0 0 0 {name=p1 lab=VCTRL}
C {iopin.sym} -600 600 0 0 {name=p2 lab=VSS}
