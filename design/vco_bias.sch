v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: vco_bias -- beta-multiplier core, VFIX offset stack, source-degenerated V-I converter, 2-bit switched-degeneration band select
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
SIMPLIFIED v1 band-select: two switched parallel degeneration resistors on the V-I converter's control branch (B0/B1 pass switches), not gf180-pll's 3-stage geometric mirror cascade (design/README.md "Band map"). Structurally simpler, topologically unambiguous, and honestly flagged: the full geometric cascade is re-derive/future work per DR-001 Decision 2 Consequences ("stage count, band-overlap plan... not decided here").
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/sg13_hv_pmos.sym} 0 -600 0 0 {name=P1 model=sg13_hv_pmos w=6u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_pmos.sym} 300 -600 0 0 {name=P2 model=sg13_hv_pmos w=6u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 0 -300 0 0 {name=N1 model=sg13_hv_nmos w=2u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 300 -300 0 0 {name=N2 model=sg13_hv_nmos w=8u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/rppd.sym} 300 0 0 0 {name=RS model=rppd body=sub! spiceprefix=X w=1u l=30u b=0 m=1}
C {sg13g2_pr/rhigh.sym} -300 -450 0 0 {name=RSTART model=rhigh body=sub! spiceprefix=X w=0.5u l=8u b=0 m=1}
C {lab_pin.sym} 20 -630 0 0 {name=l1 lab=VDD}
C {lab_pin.sym} -20 -600 0 0 {name=l2 lab=vb1}
C {lab_pin.sym} 20 -570 0 0 {name=l3 lab=vb1}
C {lab_pin.sym} 20 -600 0 0 {name=l4 lab=VDD}
C {lab_pin.sym} 320 -630 0 0 {name=l5 lab=VDD}
C {lab_pin.sym} 280 -600 0 0 {name=l6 lab=vb1}
C {lab_pin.sym} 320 -570 0 0 {name=l7 lab=vb2}
C {lab_pin.sym} 320 -600 0 0 {name=l8 lab=VDD}
C {lab_pin.sym} 20 -330 0 0 {name=l9 lab=vb1}
C {lab_pin.sym} -20 -300 0 0 {name=l10 lab=vb2}
C {lab_pin.sym} 20 -270 0 0 {name=l11 lab=VSS}
C {lab_pin.sym} 20 -300 0 0 {name=l12 lab=VSS}
C {lab_pin.sym} 320 -330 0 0 {name=l13 lab=vb2}
C {lab_pin.sym} 280 -300 0 0 {name=l14 lab=vb2}
C {lab_pin.sym} 320 -270 0 0 {name=l15 lab=n2s}
C {lab_pin.sym} 320 -300 0 0 {name=l16 lab=VSS}
C {lab_pin.sym} 300 -30 0 0 {name=l17 lab=n2s}
C {lab_pin.sym} 300 30 0 0 {name=l18 lab=VSS}
C {lab_pin.sym} -300 -480 0 0 {name=l19 lab=VDD}
C {lab_pin.sym} -300 -420 0 0 {name=l20 lab=vb2}
C {sg13g2_pr/sg13_hv_pmos.sym} 700 -600 0 0 {name=P5 model=sg13_hv_pmos w=3u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 700 -300 0 0 {name=N5 model=sg13_hv_nmos w=2u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 700 0 0 0 {name=N6 model=sg13_hv_nmos w=2u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 720 -630 0 0 {name=l21 lab=VDD}
C {lab_pin.sym} 680 -600 0 0 {name=l22 lab=vb1}
C {lab_pin.sym} 720 -570 0 0 {name=l23 lab=VFIX}
C {lab_pin.sym} 720 -600 0 0 {name=l24 lab=VDD}
C {lab_pin.sym} 720 -330 0 0 {name=l25 lab=VFIX}
C {lab_pin.sym} 680 -300 0 0 {name=l26 lab=VFIX}
C {lab_pin.sym} 720 -270 0 0 {name=l27 lab=vfixmid}
C {lab_pin.sym} 720 -300 0 0 {name=l28 lab=VSS}
C {lab_pin.sym} 720 -30 0 0 {name=l29 lab=vfixmid}
C {lab_pin.sym} 680 0 0 0 {name=l30 lab=vfixmid}
C {lab_pin.sym} 720 30 0 0 {name=l31 lab=VSS}
C {lab_pin.sym} 720 0 0 0 {name=l32 lab=VSS}
C {sg13g2_pr/sg13_hv_pmos.sym} 1100 -600 0 0 {name=M6 model=sg13_hv_pmos w=10u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 1100 -300 0 0 {name=M7 model=sg13_hv_nmos w=4u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/rppd.sym} 1100 0 0 0 {name=RDEGA model=rppd body=sub! spiceprefix=X w=1u l=60u b=0 m=1}
C {sg13g2_pr/sg13_hv_nmos.sym} 1400 -300 0 0 {name=M8 model=sg13_hv_nmos w=4u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/rppd.sym} 1400 0 0 0 {name=RDEGB0 model=rppd body=sub! spiceprefix=X w=1u l=60u b=0 m=1}
C {sg13g2_pr/sg13_hv_nmos.sym} 1700 -150 0 0 {name=SWB0 model=sg13_hv_nmos w=4u l=0.3u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/rppd.sym} 1700 150 0 0 {name=RDEGB1 model=rppd body=sub! spiceprefix=X w=1u l=60u b=0 m=1}
C {sg13g2_pr/sg13_hv_nmos.sym} 2000 -150 0 0 {name=SWB1 model=sg13_hv_nmos w=4u l=0.3u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/rppd.sym} 2000 150 0 0 {name=RDEGB2 model=rppd body=sub! spiceprefix=X w=1u l=30u b=0 m=1}
C {lab_pin.sym} 1120 -630 0 0 {name=l33 lab=VDD}
C {lab_pin.sym} 1080 -600 0 0 {name=l34 lab=VBP}
C {lab_pin.sym} 1120 -570 0 0 {name=l35 lab=VBP}
C {lab_pin.sym} 1120 -600 0 0 {name=l36 lab=VDD}
C {lab_pin.sym} 1120 -330 0 0 {name=l37 lab=VBP}
C {lab_pin.sym} 1080 -300 0 0 {name=l38 lab=VFIX}
C {lab_pin.sym} 1120 -270 0 0 {name=l39 lab=dega}
C {lab_pin.sym} 1120 -300 0 0 {name=l40 lab=VSS}
C {lab_pin.sym} 1100 -30 0 0 {name=l41 lab=dega}
C {lab_pin.sym} 1100 30 0 0 {name=l42 lab=VSS}
C {lab_pin.sym} 1420 -330 0 0 {name=l43 lab=VBP}
C {lab_pin.sym} 1380 -300 0 0 {name=l44 lab=VCTRL}
C {lab_pin.sym} 1420 -270 0 0 {name=l45 lab=degb}
C {lab_pin.sym} 1420 -300 0 0 {name=l46 lab=VSS}
C {lab_pin.sym} 1400 -30 0 0 {name=l47 lab=degb}
C {lab_pin.sym} 1400 30 0 0 {name=l48 lab=VSS}
C {lab_pin.sym} 1720 -180 0 0 {name=l49 lab=degb}
C {lab_pin.sym} 1680 -150 0 0 {name=l50 lab=B0}
C {lab_pin.sym} 1720 -120 0 0 {name=l51 lab=nb0}
C {lab_pin.sym} 1720 -150 0 0 {name=l52 lab=VSS}
C {lab_pin.sym} 1700 120 0 0 {name=l53 lab=nb0}
C {lab_pin.sym} 1700 180 0 0 {name=l54 lab=VSS}
C {lab_pin.sym} 2020 -180 0 0 {name=l55 lab=degb}
C {lab_pin.sym} 1980 -150 0 0 {name=l56 lab=B1}
C {lab_pin.sym} 2020 -120 0 0 {name=l57 lab=nb1}
C {lab_pin.sym} 2020 -150 0 0 {name=l58 lab=VSS}
C {lab_pin.sym} 2000 120 0 0 {name=l59 lab=nb1}
C {lab_pin.sym} 2000 180 0 0 {name=l60 lab=VSS}
C {sg13g2_pr/sg13_hv_pmos.sym} 2400 -600 0 0 {name=M11 model=sg13_hv_pmos w=10u l=1u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 2400 -300 0 0 {name=M10 model=sg13_hv_nmos w=4u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 2420 -630 0 0 {name=l61 lab=VDD}
C {lab_pin.sym} 2380 -600 0 0 {name=l62 lab=VBP}
C {lab_pin.sym} 2420 -570 0 0 {name=l63 lab=VBN}
C {lab_pin.sym} 2420 -600 0 0 {name=l64 lab=VDD}
C {lab_pin.sym} 2420 -330 0 0 {name=l65 lab=VBN}
C {lab_pin.sym} 2380 -300 0 0 {name=l66 lab=VBN}
C {lab_pin.sym} 2420 -270 0 0 {name=l67 lab=VSS}
C {lab_pin.sym} 2420 -300 0 0 {name=l68 lab=VSS}
C {ipin.sym} -500 -300 0 0 {name=p1 lab=VCTRL}
C {ipin.sym} -500 -150 0 0 {name=p2 lab=B0}
C {ipin.sym} -500 0 0 0 {name=p3 lab=B1}
C {opin.sym} 2900 -600 0 0 {name=p4 lab=VBP}
C {opin.sym} 2900 -300 0 0 {name=p5 lab=VBN}
C {iopin.sym} -500 -900 0 0 {name=p6 lab=VDD}
C {iopin.sym} -500 900 0 0 {name=p7 lab=VSS}
