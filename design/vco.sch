v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: vco -- 5-stage current-starved ring VCO with band select and output buffer
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
DR-001 Decision 2. On-chip decap on the dedicated VDD_VCO/GND_VCO domain per DR-001 Decision 2 Consequences (supply-noise risk).
}
G {}
K {}
V {}
S {}
E {}
C {vco_bias.sym} 0 0 0 0 {name=XBIAS }
C {lab_pin.sym} -40 -40 0 0 {name=l1 lab=VCTRL}
C {lab_pin.sym} -40 0 0 0 {name=l2 lab=B0}
C {lab_pin.sym} -40 40 0 0 {name=l3 lab=B1}
C {lab_pin.sym} 40 -20 0 0 {name=l4 lab=VBP}
C {lab_pin.sym} 40 20 0 0 {name=l5 lab=VBN}
C {lab_pin.sym} -20 -120 0 0 {name=l6 lab=VDD_VCO}
C {lab_pin.sym} 20 120 0 0 {name=l7 lab=GND_VCO}
C {vco_stage.sym} 500 300 0 0 {name=XS1 }
C {lab_pin.sym} 460 300 0 0 {name=l8 lab=VBP}
C {lab_pin.sym} 460 340 0 0 {name=l9 lab=VBN}
C {lab_pin.sym} 480 180 0 0 {name=l10 lab=VDD_VCO}
C {lab_pin.sym} 520 420 0 0 {name=l11 lab=GND_VCO}
C {vco_stage.sym} 850 300 0 0 {name=XS2 }
C {lab_pin.sym} 810 300 0 0 {name=l12 lab=VBP}
C {lab_pin.sym} 810 340 0 0 {name=l13 lab=VBN}
C {lab_pin.sym} 830 180 0 0 {name=l14 lab=VDD_VCO}
C {lab_pin.sym} 870 420 0 0 {name=l15 lab=GND_VCO}
C {vco_stage.sym} 1200 300 0 0 {name=XS3 }
C {lab_pin.sym} 1160 300 0 0 {name=l16 lab=VBP}
C {lab_pin.sym} 1160 340 0 0 {name=l17 lab=VBN}
C {lab_pin.sym} 1180 180 0 0 {name=l18 lab=VDD_VCO}
C {lab_pin.sym} 1220 420 0 0 {name=l19 lab=GND_VCO}
C {vco_stage.sym} 1550 300 0 0 {name=XS4 }
C {lab_pin.sym} 1510 300 0 0 {name=l20 lab=VBP}
C {lab_pin.sym} 1510 340 0 0 {name=l21 lab=VBN}
C {lab_pin.sym} 1530 180 0 0 {name=l22 lab=VDD_VCO}
C {lab_pin.sym} 1570 420 0 0 {name=l23 lab=GND_VCO}
C {vco_stage.sym} 1900 300 0 0 {name=XS5 }
C {lab_pin.sym} 1860 300 0 0 {name=l24 lab=VBP}
C {lab_pin.sym} 1860 340 0 0 {name=l25 lab=VBN}
C {lab_pin.sym} 1880 180 0 0 {name=l26 lab=VDD_VCO}
C {lab_pin.sym} 1920 420 0 0 {name=l27 lab=GND_VCO}
C {lab_pin.sym} 540 300 0 0 {name=l28 lab=ring1}
C {lab_pin.sym} 810 260 0 0 {name=l29 lab=ring1}
C {lab_pin.sym} 890 300 0 0 {name=l30 lab=ring2}
C {lab_pin.sym} 1160 260 0 0 {name=l31 lab=ring2}
C {lab_pin.sym} 1240 300 0 0 {name=l32 lab=ring3}
C {lab_pin.sym} 1510 260 0 0 {name=l33 lab=ring3}
C {lab_pin.sym} 1590 300 0 0 {name=l34 lab=ring4}
C {lab_pin.sym} 1860 260 0 0 {name=l35 lab=ring4}
C {lab_pin.sym} 1940 300 0 0 {name=l36 lab=ring5}
C {lab_pin.sym} 460 260 0 0 {name=l37 lab=ring5}
C {inv2x_hv.sym} 2350 700 0 0 {name=XBUF1 }
C {lab_pin.sym} 2310 700 0 0 {name=l38 lab=ring1}
C {lab_pin.sym} 2390 700 0 0 {name=l39 lab=bufmid}
C {lab_pin.sym} 2330 660 0 0 {name=l40 lab=VDD_VCO}
C {lab_pin.sym} 2370 740 0 0 {name=l41 lab=GND_VCO}
C {inv2x_hv.sym} 2650 700 0 0 {name=XBUF2 }
C {lab_pin.sym} 2610 700 0 0 {name=l42 lab=bufmid}
C {lab_pin.sym} 2690 700 0 0 {name=l43 lab=CLK}
C {lab_pin.sym} 2630 660 0 0 {name=l44 lab=VDD_VCO}
C {lab_pin.sym} 2670 740 0 0 {name=l45 lab=GND_VCO}
C {sg13g2_pr/cap_cmim.sym} 0 900 0 0 {name=CDECAP model=cap_cmim w=60u l=60u m=1 spiceprefix=X}
C {lab_pin.sym} 0 870 0 0 {name=l46 lab=VDD_VCO}
C {lab_pin.sym} 0 930 0 0 {name=l47 lab=GND_VCO}
C {ipin.sym} -400 -90 0 0 {name=p1 lab=VCTRL}
C {ipin.sym} -400 -45 0 0 {name=p2 lab=B0}
C {ipin.sym} -400 0 0 0 {name=p3 lab=B1}
C {opin.sym} 2950 700 0 0 {name=p4 lab=CLK}
C {iopin.sym} -400 -270 0 0 {name=p5 lab=VDD_VCO}
C {iopin.sym} -400 270 0 0 {name=p6 lab=GND_VCO}
