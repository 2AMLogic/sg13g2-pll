v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: inv2x_hv -- 2x-strength static CMOS inverter (buffering/driving)
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
SG13CMOS5L port (issue #22, DR-004): device symbols resolved from sg13cmos5l_pr/ instead of sg13g2_pr/ -- no device-name or subcircuit-signature change (DR-003 Finding 1: sg13_hv_nmos/sg13_hv_pmos/rppd/rhigh are identical on both PDKs). Sizing carried over unchanged from the SG13G2 schematic as a provisional starting point; re-derivation is owed to the sim-campaign follow-up issue.
}
G {}
K {}
V {}
S {}
E {}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} 0 -100 0 0 {name=MP model=sg13_hv_pmos w=10u l=0.5u ng=1 m=1 spiceprefix=X}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 0 100 0 0 {name=MN model=sg13_hv_nmos w=4u l=0.5u ng=1 m=1 spiceprefix=X}
C {ipin.sym} -300 0 0 0 {name=p1 lab=A}
C {opin.sym} 300 0 0 0 {name=p2 lab=Y}
C {iopin.sym} -300 -200 0 0 {name=p3 lab=VDD}
C {iopin.sym} -300 200 0 0 {name=p4 lab=VSS}
C {lab_pin.sym} -20 -100 0 0 {name=l1 lab=A}
C {lab_pin.sym} 20 -70 0 0 {name=l2 lab=Y}
C {lab_pin.sym} 20 -130 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 -100 0 0 {name=l4 lab=VDD}
C {lab_pin.sym} -20 100 0 0 {name=l5 lab=A}
C {lab_pin.sym} 20 70 0 0 {name=l6 lab=Y}
C {lab_pin.sym} 20 130 0 0 {name=l7 lab=VSS}
C {lab_pin.sym} 20 100 0 0 {name=l8 lab=VSS}
