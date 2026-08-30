v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: cp -- charge pump: single unit leg per polarity + tracking dump node
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
DR-001 Decision 1 / DR-002 Decision 2 (CMOS wide-swing cascode, no HBT). No Icp unit-element trim in this v1 pass -- a single fixed-current leg per polarity, documented simplification of gf180-pll's 2-bit trim (design/README.md "Charge pump (cp.sch)").
SG13CMOS5L port (issue #22, DR-004): the leaf cells this composes carry the device-symbol path changes; this cell now also instantiates six PDK devices of its own (the bias replica below).
ON-CHIP CASCODE BIAS REPLICA (issue #72, DR-006). IBP/ICP/IBN/ICN were
originally VOLTAGE-input pins with no on-chip diode of their own, so every
testbench tied IBP=ICP and IBN=ICN. Two devices whose gates share one node
cannot both saturate -- the bottom one is forced into triode -- so each leg
degenerated into a SIMPLE mirror of effective length L1+L2, and its
delivered current tracked VOUT through plain channel-length modulation. The
NMOS leg's output conductance is ~8x the PMOS leg's, so the two legs' copy
errors did not cancel: +0.46% (up) vs +3.69% (dn) at VOUT = VDD/2, mos_tt/27C
-- the ~3% up/dn magnitude mismatch sim/sg13cmos5l-cp-icp-trim measured and
sim/sg13cmos5l-closed-loop-lock/records/RECORD-004 traced the row-7 static
phase error to.
The fix restores what "wide-swing cascode" already claimed: a high-swing
cascode bias replica per polarity, inside this cell, ported from gf180-pll's
own cp.sch (MBN/MCN/MBP/MCP there). XMBP/XMBPC and XMBN/XMBNC are exact
same-W/L replicas of the leg stack they bias, with the bottom device's gate
tied to the TOP of its own stack, so the reference's bottom device sits at
the SAME Vds the cascoded leg device does. XMCP/XMCN are the separate
cascode-bias diodes, deliberately made W/L = (leg W/L)/12 so their gate sits
at Vth + ~3.5*Vov, giving the leg's bottom device real saturation margin
rather than the marginal Vth+2*Vov a textbook /4 device gives on this PDK's
PSP103 devices (measured: /4 leaves the bottom device in triode and only
2.5x-improves the mismatch, /12 improves it ~20x).
IBP/ICP/IBN/ICN are therefore CURRENT-input pins now (iopin), each expecting
the trim-code reference current; the off-block reference itself (a bandgap-
referenced Iref) is still not part of this design.
cp_dumpbuf's IBIAS moves from ICN to IBN -- ICN is now a ~3.5*Vov-overdriven
cascode-bias node, and biasing the dump follower's tail from it would triple
that tail's current (measured 103 uA vs 46 uA total cp supply current at
VOUT = 2.4 V). IBN is the mirror-bias node, matching gf180-pll's own
cp_dumpbuf wiring (VBN/VBP), and is the right node for a 1x tail.
}
G {}
K {}
V {}
S {}
E {}
C {inv_hv.sym} 0 -300 0 0 {name=XIUP }
C {lab_pin.sym} -40 -300 0 0 {name=l1 lab=UP}
C {lab_pin.sym} 40 -300 0 0 {name=l2 lab=UPB}
C {lab_pin.sym} -20 -340 0 0 {name=l3 lab=VDD}
C {lab_pin.sym} 20 -260 0 0 {name=l4 lab=VSS}
C {inv_hv.sym} 0 300 0 0 {name=XIDN }
C {lab_pin.sym} -40 300 0 0 {name=l5 lab=DN}
C {lab_pin.sym} 40 300 0 0 {name=l6 lab=DNB}
C {lab_pin.sym} -20 260 0 0 {name=l7 lab=VDD}
C {lab_pin.sym} 20 340 0 0 {name=l8 lab=VSS}
C {cp_leg_p.sym} 500 -300 0 0 {name=XLEGP }
C {lab_pin.sym} 460 -360 0 0 {name=l9 lab=IBP}
C {lab_pin.sym} 460 -320 0 0 {name=l10 lab=ICP}
C {lab_pin.sym} 460 -280 0 0 {name=l11 lab=UP}
C {lab_pin.sym} 460 -240 0 0 {name=l12 lab=UPB}
C {lab_pin.sym} 540 -320 0 0 {name=l13 lab=VOUT}
C {lab_pin.sym} 540 -280 0 0 {name=l14 lab=VDUMP}
C {lab_pin.sym} 500 -460 0 0 {name=l15 lab=VDD}
C {cp_leg_n.sym} 500 300 0 0 {name=XLEGN }
C {lab_pin.sym} 460 240 0 0 {name=l16 lab=IBN}
C {lab_pin.sym} 460 280 0 0 {name=l17 lab=ICN}
C {lab_pin.sym} 460 360 0 0 {name=l18 lab=DNB}
C {lab_pin.sym} 460 320 0 0 {name=l19 lab=DN}
C {lab_pin.sym} 540 280 0 0 {name=l20 lab=VOUT}
C {lab_pin.sym} 540 320 0 0 {name=l21 lab=VDUMP}
C {lab_pin.sym} 500 140 0 0 {name=l22 lab=VSS}
C {cp_dumpbuf.sym} 900 0 0 0 {name=XBUF }
C {lab_pin.sym} 860 -20 0 0 {name=l23 lab=VOUT}
C {lab_pin.sym} 860 20 0 0 {name=l24 lab=IBN}
C {lab_pin.sym} 940 0 0 0 {name=l25 lab=VDUMP}
C {lab_pin.sym} 880 -80 0 0 {name=l26 lab=VDD}
C {lab_pin.sym} 920 80 0 0 {name=l27 lab=VSS}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} -100 -700 0 0 {name=MBP model=sg13_hv_pmos w=24u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} -120 -700 0 0 {name=lMBP_g lab=IBP}
C {lab_pin.sym} -80 -670 0 0 {name=lMBP_d lab=nxp}
C {lab_pin.sym} -80 -700 0 0 {name=lMBP_b lab=VDD}
C {lab_pin.sym} -80 -730 0 0 {name=lMBP_s lab=VDD}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} 200 -700 0 0 {name=MBPC model=sg13_hv_pmos w=24u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 180 -700 0 0 {name=lMBPC_g lab=ICP}
C {lab_pin.sym} 220 -670 0 0 {name=lMBPC_d lab=IBP}
C {lab_pin.sym} 220 -700 0 0 {name=lMBPC_b lab=VDD}
C {lab_pin.sym} 220 -730 0 0 {name=lMBPC_s lab=nxp}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} 500 -700 0 0 {name=MCP model=sg13_hv_pmos w=6u l=3u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 480 -700 0 0 {name=lMCP_g lab=ICP}
C {lab_pin.sym} 520 -670 0 0 {name=lMCP_d lab=ICP}
C {lab_pin.sym} 520 -700 0 0 {name=lMCP_b lab=VDD}
C {lab_pin.sym} 520 -730 0 0 {name=lMCP_s lab=VDD}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} -100 700 0 0 {name=MBN model=sg13_hv_nmos w=8u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} -120 700 0 0 {name=lMBN_g lab=IBN}
C {lab_pin.sym} -80 670 0 0 {name=lMBN_d lab=nxn}
C {lab_pin.sym} -80 700 0 0 {name=lMBN_b lab=VSS}
C {lab_pin.sym} -80 730 0 0 {name=lMBN_s lab=VSS}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 200 700 0 0 {name=MBNC model=sg13_hv_nmos w=8u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 180 700 0 0 {name=lMBNC_g lab=ICN}
C {lab_pin.sym} 220 670 0 0 {name=lMBNC_d lab=IBN}
C {lab_pin.sym} 220 700 0 0 {name=lMBNC_b lab=VSS}
C {lab_pin.sym} 220 730 0 0 {name=lMBNC_s lab=nxn}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 500 700 0 0 {name=MCN model=sg13_hv_nmos w=2u l=3u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 480 700 0 0 {name=lMCN_g lab=ICN}
C {lab_pin.sym} 520 670 0 0 {name=lMCN_d lab=ICN}
C {lab_pin.sym} 520 700 0 0 {name=lMCN_b lab=VSS}
C {lab_pin.sym} 520 730 0 0 {name=lMCN_s lab=VSS}
C {ipin.sym} -250 -300 0 0 {name=p1 lab=UP}
C {ipin.sym} -250 300 0 0 {name=p2 lab=DN}
C {iopin.sym} -250 -600 0 0 {name=p3 lab=IBP}
C {iopin.sym} -250 -500 0 0 {name=p4 lab=ICP}
C {iopin.sym} -250 600 0 0 {name=p5 lab=IBN}
C {iopin.sym} -250 500 0 0 {name=p6 lab=ICN}
C {opin.sym} 1200 0 0 0 {name=p7 lab=VOUT}
C {iopin.sym} -250 -900 0 0 {name=p8 lab=VDD}
C {iopin.sym} -250 900 0 0 {name=p9 lab=VSS}
