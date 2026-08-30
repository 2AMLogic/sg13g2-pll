v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: cp_dumpbuf -- VDUMP tracking buffer (simplified NMOS source follower)
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
SIMPLIFIED v1: a single NMOS source follower sensing VOUT and driving VDUMP, not gf180-pll's full closed-loop complementary 5T-OTA pair (design/README.md "Charge pump (cp.sch)"). This still satisfies DR-005's no-loop-signal-charge compatibility test (it only senses VOUT, drives nothing back into it) but is an offset follower, not a unity-gain buffer -- re-deriving the full closed-loop version is future refinement work once real headroom data exists (spec/porting-plan.md Sec2.2).
SG13CMOS5L port (issue #22, DR-004): device symbols resolved from sg13cmos5l_pr/ instead of sg13g2_pr/ -- no device-name or subcircuit-signature change (DR-003 Finding 1: sg13_hv_nmos/sg13_hv_pmos/rppd/rhigh are identical on both PDKs). Sizing carried over unchanged from the SG13G2 schematic as a provisional starting point; re-derivation is owed to the sim-campaign follow-up issue.
}
G {}
K {}
V {}
S {}
E {}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 0 0 0 0 {name=M1 model=sg13_hv_nmos w=6u l=0.5u ng=1 m=1 spiceprefix=X}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 0 300 0 0 {name=M2 model=sg13_hv_nmos w=4u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 20 -30 0 0 {name=l1 lab=VDD}
C {lab_pin.sym} -20 0 0 0 {name=l2 lab=VOUT}
C {lab_pin.sym} 20 30 0 0 {name=l3 lab=VDUMP}
C {lab_pin.sym} 20 0 0 0 {name=l4 lab=VSS}
C {lab_pin.sym} 20 270 0 0 {name=l5 lab=VDUMP}
C {lab_pin.sym} -20 300 0 0 {name=l6 lab=IBIAS}
C {lab_pin.sym} 20 330 0 0 {name=l7 lab=VSS}
C {lab_pin.sym} 20 300 0 0 {name=l8 lab=VSS}
C {ipin.sym} -350 0 0 0 {name=p1 lab=VOUT}
C {ipin.sym} -350 300 0 0 {name=p2 lab=IBIAS}
C {opin.sym} 350 150 0 0 {name=p3 lab=VDUMP}
C {iopin.sym} -350 -300 0 0 {name=p4 lab=VDD}
C {iopin.sym} -350 600 0 0 {name=p5 lab=VSS}
