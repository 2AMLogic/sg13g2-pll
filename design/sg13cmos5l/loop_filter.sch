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
R1 resize (issue #41, DR-006): sim/sg13cmos5l-loop-bandwidth-pm RECORD-001 measured 0/90 real-subckt PVT combinations meeting the >=45deg phase-margin criterion with R1 as originally drawn (w=4u l=120u, ~7.79 kOhm) -- the filter zero sat one to two decades above any reachable crossover. The initially-proposed "R1 x20" fix (RECORD-001's own proposal.csv, validated only at a single fixed f_ref=25MHz) was re-verified against the FULL amended f_ref range from DR-005 (3.5-24.4 MHz) across both VCO band codes and three Kvco operating intervals (including the near-VCO-floor "low" VCTRL interval DR-005's own floor derivation implies) and found NOT to close the loop at several real, ratified-spec-legal operating points near the amended f_ref floor (worst-case PM shortfall ~22.6deg at band=00, low-VCTRL, f_ref=4.5MHz -- see sim/sg13cmos5l-loop-bandwidth-pm RECORD-002). R1 is instead resized to w=0.6u l=810u (b=0, m=1), landing R1 ~44.2x the as-drawn value (~344.2 kOhm nominal typ corner) -- the scale factor found, via the same full-envelope re-verification, to close every real-subckt-measured (band, Kvco-interval, f_ref) combination with a positive (if occasionally thin, ~+0.75deg worst case) phase-margin surplus, versus x20's up-to-22.6deg deficit at the same points. Area cost is essentially unchanged from x20: R*Area ~ L^2 for a fixed sheet resistance, so co-scaling L up and W down by ~sqrt(scale) holds Area constant regardless of the scale factor chosen (486 um^2 at x44.2 vs. 480 um^2 as-drawn, ~+1.3%, vs. a pure length-only scaling that would need l~5300u, far beyond the rppd_maxL=1mm DRC bound, or a pure width-only scaling that would need w<<rppd_minW=0.5u). See DR-006 for the full R1-vs-C1 area trade, the amended-f_ref-range re-verification methodology, and the residual (thin-margin, not eliminated) risk this scale still carries. Schematic-level only: a future layout pass should use rppd's own `b` (bends) parameter to meander this length into a compact footprint rather than a single straight 810um leg -- not this issue's scope.
}
G {}
K {}
V {}
S {}
E {}
C {sg13cmos5l_pr/rppd.sym} 0 0 0 0 {name=R1 model=rppd body=sub! spiceprefix=X w=0.6u l=810u b=0 m=1}
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
