# `sg13cmos5l-postlayout-pex-pvt`

Post-layout (parasitic-extracted) PVT re-simulation of the SG13CMOS5L PLL
port — issue **#30** (Part of #16), the named follow-up issue #24's own
acceptance criteria required when #24 scoped post-layout PVT out; and
issue **#101** (sub-issue A of the #100 split) for the floorplan-aware
`pll_vco` re-route and the PVT re-run against it.

**Read [`records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md`](records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md)
first, then
[`records/RECORD-002-floorplan-aware-vco-route.md`](records/RECORD-002-floorplan-aware-vco-route.md).**
The three things a reader must not miss, stated here so they are not
buried:

1. **Real extracted parasitics WERE modelled** — klt-extracted R/C from the
   routed layout's own geometry, with the curated `sg13cmos5l` metal
   coefficient table (klayout-tools#2126, merged 2026-09-19). **No metal
   level fell back to a zero coefficient on any of the six blocks.** This is
   a *different* answer than issue #30's own body expects, because
   klayout-tools#2113 closed after that issue text was written; both records
   re-verify it live and reproduce the committed extraction
   byte-identically rather than trusting either source.
2. **Every post-layout number is bounded by routing style, not predicted by
   a floorplan — RECORD-002 halves that bound on `vco`.** The port's flow
   drew 7 178 µm of wire for a ~45-device ring VCO (413 µm on `ring1` alone)
   and 147 mm on `divider_chain`; RECORD-001 measured the consequence
   (~2× frequency loss, ~99% of it capacitance) and issue #101's locality
   pass cut `vco` to 3 913 µm (126 µm on `ring1`) with DRC/LVS verdicts
   unchanged. RECORD-002 re-extracts and re-runs Matrix A/C against the new
   geometry: the mean per-point deviation narrows −49.3% → −22.6%, band
   223.68 – 789.50 → 347.55 – 1182.79 MHz, control arm 60/60 byte-identical.
   `divider_chain`'s 147 mm is untouched, so the bound there has not moved.
3. **Only three of six blocks have a confirmed layout↔schematic topology
   match.** `cp`'s results rest on one; `vco`'s do not; `lock_detector`
   cannot be compared at all. This is as true for RECORD-002 as for
   RECORD-001 — the locality pass changes wire, not verdicts.

## Layout

```
extraction/run-pex.sh          klt extract --parasitics over every routed block
netlist-snapshots/             the 6 parasitic-annotated netlists + klt's own
                               per-block JSON reports + provenance.json
lvs-recheck/                   re-runs LVS for all 6 blocks at the current klt,
                               adding the one reference.device_map entry klt's
                               own error message names
testbench/
  pex-to-ngspice.py            3 documented, self-checked mechanical transforms
  make-inst.py                 derives the instantiation from the cell's own pins
  run.sh                       Matrix A: pll_vco Kvco, both arms
  run_cp.sh                    Matrix B: pll_cp Icp trim, both arms
  run_rc_attribution.sh        Matrix C: which parasitic caused the deviation
  analyze.py                   every roll-up number the record quotes
corners/matrix.md              the three matrices and what they deliberately omit
corners/*.csv                  raw per-point results
records/                       append-only; RECORD-001 = original route, 
                               RECORD-002 = locality-routed re-run
```

## Headline numbers

`vco`, as measured against each record's own layout record:

| Measurement | Schematic control | @`d5355e1` (RECORD-001) | @`c44fa68` locality pass (RECORD-002) |
|---|---|---|---|
| output band (60 points) | 445.26 – 1561.97 MHz | 223.68 – 789.50 MHz | **347.55 – 1182.79 MHz** |
| f_post/f_sch, 60/60 points | — | 0.4768 – 0.5312 | **0.7394 – 0.7892** |
| Kvco avg, per bundle×band | 144.2 – 422.4 MHz/V | 67.6 – 207.6 MHz/V | **106.4 – 313.1 MHz/V** |

`cp` (its GDS and extracted netlist are byte-identical at `c44fa68`, so its
RECORD-001 rows remain the measurement):

| Measurement | Schematic control | Post-layout (PEX) |
|---|---|---|
| `cp` Icp, UP state (102 points) | — | +0.055% … +0.632% |
| `cp` Icp, DN state (102 points) | — | +0.017% … +0.211% |

Both control arms reproduce their committed campaigns: 60/60 VCO frequencies
byte-identical (RECORD-001 and again in RECORD-002), and `cp` to within
4.9e-5 %.

Attribution of the VCO's deviation (`corners/rc_attribution.csv`) — the
composition is the finding in **both** layouts: **≈99% parasitic
capacitance**. At `d5355e1` the full extraction costs −49.21% of frequency
(device geometry alone −0.69%, parasitic R ~−0.7 pp more); at the
locality-routed geometry the same arms cost −22.53% full / −0.70% devices /
−1.35% R-only — the device floor is shared by both layouts, so the entire
improvement came out of the interconnect's capacitive share.
