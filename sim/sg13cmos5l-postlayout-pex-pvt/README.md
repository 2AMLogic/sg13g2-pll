# `sg13cmos5l-postlayout-pex-pvt`

Post-layout (parasitic-extracted) PVT re-simulation of the SG13CMOS5L PLL
port — issue **#30** (Part of #16), the named follow-up issue #24's own
acceptance criteria required when #24 scoped post-layout PVT out.

**Read [`records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md`](records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md)
first.** The three things a reader must not miss, stated here so they are not
buried:

1. **Real extracted parasitics WERE modelled** — klt-extracted R/C from the
   routed layout's own geometry, with the curated `sg13cmos5l` metal
   coefficient table (klayout-tools#2126, merged 2026-09-19). **No metal
   level fell back to a zero coefficient on any of the six blocks.** This is
   a *different* answer than issue #30's own body expects, because
   klayout-tools#2113 closed after that issue text was written; the record
   re-verifies it live and reproduces the committed extraction
   byte-identically rather than trusting either source.
2. **Every post-layout number here is an upper bound set by routing style,
   not a floorplan prediction.** This port's flow draws 7 178 µm of wire for a
   ~45-device ring VCO (413 µm on `ring1` alone) and 147 mm on
   `divider_chain`. The record quantifies how much of its headline number
   that is worth.
3. **Only three of six blocks have a confirmed layout↔schematic topology
   match.** `cp`'s results rest on one; `vco`'s do not; `lock_detector`
   cannot be compared at all.

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
records/                       append-only; RECORD-001 is the whole analysis
```

## Headline numbers

| Measurement | Schematic control | Post-layout (PEX) |
|---|---|---|
| `vco` output band (60 points) | 445.26 – 1561.97 MHz | 223.68 – 789.50 MHz |
| `vco` f_post/f_sch, 60/60 points | — | 0.4768 – 0.5312 |
| `cp` Icp, UP state (102 points) | — | +0.055% … +0.632% |
| `cp` Icp, DN state (102 points) | — | +0.017% … +0.211% |

Both control arms reproduce their committed campaigns: 60/60 VCO frequencies
byte-identical, and `cp` to within 4.9e-5 %.

Attribution of the VCO's ~2× slowdown (`corners/rc_attribution.csv`):
**≈99% parasitic capacitance** — extracted device geometry alone accounts for
0.69% and parasitic resistance for a further ~0.7 percentage points.
