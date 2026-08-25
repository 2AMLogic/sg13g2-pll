v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: cp_leg_n -- charge-pump NMOS sink leg: mirror + cascode + dual steering switches
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
Wide-swing cascode technique per spec/porting-plan.md Sec1.4 (device-swap from gf180-pll's own cp_leg_n.sch); bias generation (IBN/ICN) is out of this block's scope per DR-002 Decision 1.
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/sg13_hv_nmos.sym} 0 0 0 0 {name=M1 model=sg13_hv_nmos w=8u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 0 -300 0 0 {name=M2 model=sg13_hv_nmos w=8u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 400 -600 0 0 {name=SWO model=sg13_hv_nmos w=6u l=0.3u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} -400 -600 0 0 {name=SWD model=sg13_hv_nmos w=6u l=0.3u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} -20 0 0 0 {name=l1 lab=IBN}
C {lab_pin.sym} 20 30 0 0 {name=l2 lab=VSS}
C {lab_pin.sym} 20 0 0 0 {name=l3 lab=VSS}
C {lab_pin.sym} 20 -30 0 0 {name=l4 lab=tail}
C {lab_pin.sym} 20 -270 0 0 {name=l5 lab=tail}
C {lab_pin.sym} -20 -300 0 0 {name=l6 lab=ICN}
C {lab_pin.sym} 20 -330 0 0 {name=l7 lab=sw}
C {lab_pin.sym} 20 -300 0 0 {name=l8 lab=VSS}
C {lab_pin.sym} 420 -570 0 0 {name=l9 lab=sw}
C {lab_pin.sym} 380 -600 0 0 {name=l10 lab=DN}
C {lab_pin.sym} 420 -630 0 0 {name=l11 lab=VOUT}
C {lab_pin.sym} 420 -600 0 0 {name=l12 lab=VSS}
C {lab_pin.sym} -380 -570 0 0 {name=l13 lab=sw}
C {lab_pin.sym} -420 -600 0 0 {name=l14 lab=DNB}
C {lab_pin.sym} -380 -630 0 0 {name=l15 lab=VDUMP}
C {lab_pin.sym} -380 -600 0 0 {name=l16 lab=VSS}
C {ipin.sym} -700 0 0 0 {name=p1 lab=IBN}
C {ipin.sym} -700 -300 0 0 {name=p2 lab=ICN}
C {ipin.sym} -700 -600 0 0 {name=p3 lab=DNB}
C {ipin.sym} 700 -600 0 0 {name=p4 lab=DN}
C {opin.sym} 400 -900 0 0 {name=p5 lab=VOUT}
C {opin.sym} -400 -900 0 0 {name=p6 lab=VDUMP}
C {iopin.sym} -700 300 0 0 {name=p7 lab=VSS}
