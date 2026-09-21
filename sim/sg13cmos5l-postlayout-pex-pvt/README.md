# `sg13cmos5l-postlayout-pex-pvt`

Post-layout (parasitic-extracted) PVT re-simulation of the SG13CMOS5L PLL
port — issue **#30** (Part of #16), the named follow-up issue #24's own
acceptance criteria required when #24 scoped post-layout PVT out; and
issue **#101** (sub-issue A of the #100 split) for the floorplan-aware
`pll_vco` re-route and the PVT re-run against it; and issue **#102**
(sub-issue B of the #100 split) for the `pfd`/`lock_detector` post-layout
arms.

**Read [`records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md`](records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md)
first, then
[`records/RECORD-002-floorplan-aware-vco-route.md`](records/RECORD-002-floorplan-aware-vco-route.md),
then [`records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md`](records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md)
for the `pfd`/`lock_detector` arms issue #102 added.** The three things a
reader must not miss, stated here so they are not
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
  run_pfd.sh                   Matrix D: pll_pfd UP/DN duty space (issue #102)
  run_lock_detector.sh         Matrix E: pll_lock_detector window/ladder/current
                               (issue #102), incl. the as-layout twin
  derive_ld_as_layout.py       the as-layout twin (resize snapshot minus its
                               two cap_cmomi cards -- diagnostic-only)
  tb_ld_wholecell_win.sp.tmpl  whole-cell ERR->ERRD window deck (both arms)
  gen_pex_ladder.py            post-layout ladder/recovery deck generator,
                               reduce-compatible with the sibling campaign
  analyze.py                   every roll-up number RECORD-001 quotes
  analyze_pfd_ld.py            every roll-up number RECORD-003 quotes
corners/matrix.md              the five matrices and what they deliberately omit
corners/*.csv                  raw per-point results
records/                       append-only; RECORD-001 = original route,
                               RECORD-002 = locality-routed re-run,
                               RECORD-003 = pfd/lock_detector arms
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

`pfd` and `lock_detector` (RECORD-003), as measured against the
`20260921-155747-c44fa68` extraction — `pfd`'s snapshot is byte-identical
to the `457cf5b` one it supersedes, `lock_detector`'s was re-extracted
(see RECORD-003's DUT pin):

| Measurement | Schematic control | Post-layout (PEX) |
|---|---|---|
| `pfd` UP hold, reflead (3 offsets) | 5.674 / 10.674 / 20.674 ns | +0.525 ns at every offset |
| `pfd` FB-lead polarity (3 offsets) | DN-dominant (textbook, all 3) | **inverted: UP holds `T_ref − τ`, DN 2.39 %** |
| `lock_detector` window vs committed crowbarfix control (3.3 V grid) | 5.01 – 9.42 ns | as-built chain **0.18 – 0.31 ns** — the layout's two MOM caps are absent |
| `lock_detector` whole-cell window, post-layout vs as-layout twin | — | **+62.9 % … +68.9 %** across 29 PVT points |

All control arms reproduce their committed campaigns: 60/60 VCO frequencies
byte-identical (RECORD-001 and again in RECORD-002), `cp` to within
4.9e-5 %, and (RECORD-003) the whole committed 102-point `lock_detector`
window matrix plus its 15 device rows byte-identical, with the `pfd`
control at −0.52 % against the campaign's productionised-reset rows.

Attribution of the VCO's deviation (`corners/rc_attribution.csv`) — the
composition is the finding in **both** layouts: **≈99% parasitic
capacitance**. At `d5355e1` the full extraction costs −49.21% of frequency
(device geometry alone −0.69%, parasitic R ~−0.7 pp more); at the
locality-routed geometry the same arms cost −22.53% full / −0.70% devices /
−1.35% R-only — the device floor is shared by both layouts, so the entire
improvement came out of the interconnect's capacitive share.
