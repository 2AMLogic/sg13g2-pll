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
SG13CMOS5L port (issue #22, DR-004): cap_cmim (MIM, unavailable on SG13CMOS5L per DR-003 Finding 2) replaced by cap_cmomi (interdigitated MOM). Sizes are chosen so cap_cmomi.tcl's own display-capacitance formula lands within ~10% of the original cap_cmim instance's value -- a provisional placeholder, not a re-derived size (mmin/mmax/feed/subblock/mm_ok have no cap_cmim equivalent and are set to the PDK's own documented defaults: full M1-M4 stack, double-sided feed). See design/README.md SG13CMOS5L section for the full per-instance mapping table and DR-004 for the MoM 'not validated on CMOS5L silicon' caveat this carries forward from DR-003 Finding 2.
}
G {}
K {}
V {}
S {}
E {}
C {sg13cmos5l_pr/rppd.sym} 0 0 0 0 {name=R1 model=rppd body=sub! spiceprefix=X w=4u l=120u b=0 m=1}
C {sg13cmos5l_pr/cap_cmomi.sym} 400 300 0 0 {name=C1 model=cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double subblock=0 mm_ok=1 m=1 spiceprefix=X}
C {sg13cmos5l_pr/cap_cmomi.sym} -400 -300 0 0 {name=C2 model=cap_cmomi w=10u l=10u mmin=1 mmax=4 feed=double subblock=0 mm_ok=1 m=1 spiceprefix=X}
C {lab_pin.sym} 0 -30 0 0 {name=l1 lab=VCTRL}
C {lab_pin.sym} 0 30 0 0 {name=l2 lab=NZ}
C {lab_pin.sym} 400 270 0 0 {name=l3 lab=NZ}
C {lab_pin.sym} 400 330 0 0 {name=l4 lab=VSS}
C {lab_pin.sym} -400 -330 0 0 {name=l5 lab=VCTRL}
C {lab_pin.sym} -400 -270 0 0 {name=l6 lab=VSS}
C {iopin.sym} -600 0 0 0 {name=p1 lab=VCTRL}
C {iopin.sym} -600 600 0 0 {name=p2 lab=VSS}
