v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: schmitt_hv -- 6T inverting Schmitt trigger (hysteresis comparator)
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
FEEDBACK-DEVICE CONNECTION (issue #66, Part of #16) -- read before editing MP3/MN3. A six-transistor CMOS Schmitt trigger gets its hysteresis from two feedback devices that pull the internal stack nodes toward the OPPOSITE rail from their own series stack. As originally drawn both feedback devices were tied to the SAME rail as their stack (MP3: drain np, source VDD; MN3: drain nn, source VSS), which leaves this cell with no state memory at all -- a plain inverter with a manufacturing tolerance. MP3 and MN3 are now on the classic connection: MP3 source np / drain VSS, MN3 source nn / drain VDD (netlist: "XMP3 VSS OUT np VDD", "XMN3 VDD OUT nn VSS").
This defect was FOUND on the SG13CMOS5L sibling design/sg13cmos5l/schmitt_hv.sch, which carried the identical wiring, and it is fixed here in the same change because it is a CONNECTIVITY defect in a cell both PDKs share, not a port artifact or a sizing choice. It is measured on BOTH PDKs rather than argued across from one: sim/sg13cmos5l-lock-detector-window/testbench/run_schmitt_rewire.sh runs the same as-drawn-vs-rewired ramp on ihp-sg13g2 AND ihp-sg13cmos5l and writes ../corners/schmitt_rewire.csv with a `pdk` column. Measured on ihp-sg13g2: 0.89-1.55 mV as drawn -> 879-979 mV rewired, 27 corner points each. Nothing else in this SG13G2 hierarchy is touched by issue #66 -- in particular XRPU/XCW/XMPD here are still at their pre-#52 values and a SG13G2 lock_detector sizing campaign is owed; see design/README.md.
}
G {}
K {}
V {}
S {}
E {}
C {sg13g2_pr/sg13_hv_pmos.sym} 0 -300 0 0 {name=MP1 model=sg13_hv_pmos w=5u l=2u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_pmos.sym} 0 -150 0 0 {name=MP2 model=sg13_hv_pmos w=5u l=2u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_pmos.sym} 300 -300 0 0 {name=MP3 model=sg13_hv_pmos w=5u l=2u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 0 150 0 0 {name=MN1 model=sg13_hv_nmos w=2u l=2u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 0 300 0 0 {name=MN2 model=sg13_hv_nmos w=2u l=2u ng=1 m=1 spiceprefix=X}
C {sg13g2_pr/sg13_hv_nmos.sym} 300 300 0 0 {name=MN3 model=sg13_hv_nmos w=2u l=2u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 20 -330 0 0 {name=l1 lab=VDD}
C {lab_pin.sym} -20 -300 0 0 {name=l2 lab=IN}
C {lab_pin.sym} 20 -270 0 0 {name=l3 lab=np}
C {lab_pin.sym} 20 -180 0 0 {name=l4 lab=np}
C {lab_pin.sym} -20 -150 0 0 {name=l5 lab=IN}
C {lab_pin.sym} 20 -120 0 0 {name=l6 lab=OUT}
C {lab_pin.sym} 320 -330 0 0 {name=l7 lab=np}
C {lab_pin.sym} 280 -300 0 0 {name=l8 lab=OUT}
C {lab_pin.sym} 320 -270 0 0 {name=l9 lab=VSS}
C {lab_pin.sym} 20 -300 0 0 {name=l10 lab=VDD}
C {lab_pin.sym} 20 -150 0 0 {name=l11 lab=VDD}
C {lab_pin.sym} 320 -300 0 0 {name=l12 lab=VDD}
C {lab_pin.sym} 20 180 0 0 {name=l13 lab=nn}
C {lab_pin.sym} -20 150 0 0 {name=l14 lab=IN}
C {lab_pin.sym} 20 120 0 0 {name=l15 lab=OUT}
C {lab_pin.sym} 20 330 0 0 {name=l16 lab=VSS}
C {lab_pin.sym} -20 300 0 0 {name=l17 lab=IN}
C {lab_pin.sym} 20 270 0 0 {name=l18 lab=nn}
C {lab_pin.sym} 320 330 0 0 {name=l19 lab=nn}
C {lab_pin.sym} 280 300 0 0 {name=l20 lab=OUT}
C {lab_pin.sym} 320 270 0 0 {name=l21 lab=VDD}
C {lab_pin.sym} 20 150 0 0 {name=l22 lab=VSS}
C {lab_pin.sym} 20 300 0 0 {name=l23 lab=VSS}
C {lab_pin.sym} 320 300 0 0 {name=l24 lab=VSS}
C {ipin.sym} -350 0 0 0 {name=p1 lab=IN}
C {opin.sym} 650 -75 0 0 {name=p2 lab=OUT}
C {iopin.sym} -350 -500 0 0 {name=p3 lab=VDD}
C {iopin.sym} -350 500 0 0 {name=p4 lab=VSS}
