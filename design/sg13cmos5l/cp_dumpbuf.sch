v {xschem version=3.4.8RC file_version=1.3
sg13g2-pll :: cp_dumpbuf -- VDUMP tracking buffer: complementary pair of unity-gain 5T OTAs
Device flavour: SG13G2 3.3V thick-oxide CMOS throughout (sg13_hv_nmos /
sg13_hv_pmos), per spec/decision-records/DR-002-supply-device-flavor.md
Decision 0.
Connectivity is label-driven (lab_pin stubs on every device terminal),
matching the gf180-pll/sky130-pll fleet convention documented in
design/README.md.
SG13CMOS5L port (issue #22, DR-004): device symbols resolved from sg13cmos5l_pr/.
ISSUE #165 / DR-010: this cell replaces the v1 single NMOS source follower.
That follower held VDUMP one V_GS (~0.94 V) below VOUT, so every idle leg's
switch-common node sat ~0.94 V below VOUT and every UP and DN turn-on pulled
~20-23 fC out of the loop filter (same sign for both legs, -41.3 fC per
cycle): the 8.2% row-7 static phase error isolated in
sim/sg13cmos5l-closed-loop-lock/records/RECORD-006. The fix makes VDUMP TRACK
VOUT at DC, ported from gf180-pll's own cp_dumpbuf.sch (#24 there), which
solved the identical tail-charge term the same way.
TOPOLOGY. Two five-transistor OTAs, each in unity-gain feedback on VDUMP,
outputs tied together:
  MTN/MN1/MN2/MN3/MN4  NMOS input pair, PMOS mirror load -- covers the top of
                       the VOUT range (runs out of tail headroom near
                       VOUT ~ Vgs + Vdsat at the bottom)
  MTP/MP1/MP2/MP3/MP4  PMOS input pair, NMOS mirror load -- covers the bottom
                       (runs out near VDD - Vsg - Vdsat at the top)
MN1/MP1 sense VOUT; MN2/MP2 sense VDUMP and their drains ARE VDUMP, which
closes each unity-gain loop. Where both are in range they act in parallel;
outside its range an OTA's tail collapses and its output device turns off
(high impedance, no fight). Every internal node is diode-clamped to a rail
by its mirror diode, so the DC operating point is defined at every corner.
SIZING (L = 1u except the PMOS input pair).
- Tails: MTN 12u/1u off IBN (1.5x the 8u/1u NMOS mirror device) and MTP
  36u/1u off IBP (1.5x the 24u/1u PMOS mirror device): ~1.5x Icp each, so
  the tail current SCALES WITH THE TRIM CODE. A 5T OTA's output drive is its
  tail current; it must hold VDUMP while one polarity is asserted alone and
  the other leg dumps its full Icp into VDUMP (a one-sided PFD state, i.e.
  acquisition), so tail > Icp at every code.
- Input pairs are deliberately SMALL (MN1/MN2 2u/1u, MP1/MP2 6u/0.5u), the
  opposite of gf180-pll's 16u/48u. Reason: this loop's C1 is ~1.69 pF and C2
  ~0.1 pF (gf180-pll: ~130 pF), and MN1/MP1 gate the loop-filter node. The
  gf180 sizing measured 28-112 fF of added VOUT capacitance (worst where the
  PMOS pair's tail runs out of headroom, VOUT 2.5-2.9 V), 1.7-6.6% of C1 and
  up to 1.1x C2. 2u/1u + 6u/0.5u measures 3.7-10.5 fF over VOUT 0.3-2.9 V
  (<= 0.62% of C1), inside the <= 1% loading condition DR-001 adopts from
  gf180-pll DR-005, at the cost of a larger (still ~15 mV) idle offset.
- Mirror loads 1:1 (MN3/MN4 24u/1u PMOS, MP3/MP4 16u/1u NMOS): a ratioed load
  would buy drive at the price of systematic input offset.
- MP1/MP2 bulk tied to their common source PSRC (own n-well) to remove body
  effect and recover input range at the top. MN1/MN2 bulk stays on VSS.
COST: two ~15 uA tails (~30 uA at the 10 uA code) replace the follower's
~5 uA tail, and two MOS gates (MN1, MP1) now load VOUT. Measured, not
assumed: see sim/sg13cmos5l-cp-icp-trim/records/RECORD-005 and
sim/sg13cmos5l-closed-loop-lock/records/RECORD-007.
PINS: IBIAS is replaced by IBN and a new IBP (the PMOS tail needs its own
mirror gate); cp.sch wires them to its own IBN/IBP mirror-bias nodes.
}
G {}
K {}
V {}
S {}
E {}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 0 300 0 0 {name=MTN model=sg13_hv_nmos w=12u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 20 270 0 0 {name=lMTN_d lab=NSRC}
C {lab_pin.sym} -20 300 0 0 {name=lMTN_g lab=IBN}
C {lab_pin.sym} 20 330 0 0 {name=lMTN_s lab=VSS}
C {lab_pin.sym} 20 300 0 0 {name=lMTN_b lab=VSS}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 300 200 0 0 {name=MN1 model=sg13_hv_nmos w=2u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 320 170 0 0 {name=lMN1_d lab=NDA}
C {lab_pin.sym} 280 200 0 0 {name=lMN1_g lab=VOUT}
C {lab_pin.sym} 320 230 0 0 {name=lMN1_s lab=NSRC}
C {lab_pin.sym} 320 200 0 0 {name=lMN1_b lab=VSS}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 600 200 0 0 {name=MN2 model=sg13_hv_nmos w=2u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 620 170 0 0 {name=lMN2_d lab=VDUMP}
C {lab_pin.sym} 580 200 0 0 {name=lMN2_g lab=VDUMP}
C {lab_pin.sym} 620 230 0 0 {name=lMN2_s lab=NSRC}
C {lab_pin.sym} 620 200 0 0 {name=lMN2_b lab=VSS}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} 300 0 0 0 {name=MN3 model=sg13_hv_pmos w=24u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 320 30 0 0 {name=lMN3_d lab=NDA}
C {lab_pin.sym} 280 0 0 0 {name=lMN3_g lab=NDA}
C {lab_pin.sym} 320 -30 0 0 {name=lMN3_s lab=VDD}
C {lab_pin.sym} 320 0 0 0 {name=lMN3_b lab=VDD}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} 600 0 0 0 {name=MN4 model=sg13_hv_pmos w=24u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 620 30 0 0 {name=lMN4_d lab=VDUMP}
C {lab_pin.sym} 580 0 0 0 {name=lMN4_g lab=NDA}
C {lab_pin.sym} 620 -30 0 0 {name=lMN4_s lab=VDD}
C {lab_pin.sym} 620 0 0 0 {name=lMN4_b lab=VDD}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} 0 -300 0 0 {name=MTP model=sg13_hv_pmos w=36u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 20 -270 0 0 {name=lMTP_d lab=PSRC}
C {lab_pin.sym} -20 -300 0 0 {name=lMTP_g lab=IBP}
C {lab_pin.sym} 20 -330 0 0 {name=lMTP_s lab=VDD}
C {lab_pin.sym} 20 -300 0 0 {name=lMTP_b lab=VDD}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} 300 -200 0 0 {name=MP1 model=sg13_hv_pmos w=6u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 320 -170 0 0 {name=lMP1_d lab=PDA}
C {lab_pin.sym} 280 -200 0 0 {name=lMP1_g lab=VOUT}
C {lab_pin.sym} 320 -230 0 0 {name=lMP1_s lab=PSRC}
C {lab_pin.sym} 320 -200 0 0 {name=lMP1_b lab=PSRC}
C {sg13cmos5l_pr/sg13_hv_pmos.sym} 600 -200 0 0 {name=MP2 model=sg13_hv_pmos w=6u l=0.5u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 620 -170 0 0 {name=lMP2_d lab=VDUMP}
C {lab_pin.sym} 580 -200 0 0 {name=lMP2_g lab=VDUMP}
C {lab_pin.sym} 620 -230 0 0 {name=lMP2_s lab=PSRC}
C {lab_pin.sym} 620 -200 0 0 {name=lMP2_b lab=PSRC}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 300 -400 0 0 {name=MP3 model=sg13_hv_nmos w=16u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 320 -430 0 0 {name=lMP3_d lab=PDA}
C {lab_pin.sym} 280 -400 0 0 {name=lMP3_g lab=PDA}
C {lab_pin.sym} 320 -370 0 0 {name=lMP3_s lab=VSS}
C {lab_pin.sym} 320 -400 0 0 {name=lMP3_b lab=VSS}
C {sg13cmos5l_pr/sg13_hv_nmos.sym} 600 -400 0 0 {name=MP4 model=sg13_hv_nmos w=16u l=1u ng=1 m=1 spiceprefix=X}
C {lab_pin.sym} 620 -430 0 0 {name=lMP4_d lab=VDUMP}
C {lab_pin.sym} 580 -400 0 0 {name=lMP4_g lab=PDA}
C {lab_pin.sym} 620 -370 0 0 {name=lMP4_s lab=VSS}
C {lab_pin.sym} 620 -400 0 0 {name=lMP4_b lab=VSS}
C {ipin.sym} -350 0 0 0 {name=p1 lab=VOUT}
C {ipin.sym} -350 300 0 0 {name=p2 lab=IBN}
C {ipin.sym} -350 -300 0 0 {name=p6 lab=IBP}
C {opin.sym} 900 0 0 0 {name=p3 lab=VDUMP}
C {iopin.sym} -350 -600 0 0 {name=p4 lab=VDD}
C {iopin.sym} -350 600 0 0 {name=p5 lab=VSS}
