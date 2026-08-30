# RECORD-002: `loop_filter` R1/C1/C2 after the R1 resize (issue #41, DR-006)

- **Slug**: `sg13cmos5l-loop-filter-momcap`
- **Issue**: #41 (Part of #16, Chipalooza Challenge #6). Supersedes nothing:
  `RECORD-001` measured the **pre-resize** `loop_filter` (`XR1` `rppd`
  `w=4u l=120u`) and stands unedited, with its own frozen netlist snapshot
  and its own unsuffixed `../corners/results.csv`. This record measures the
  **post-resize** filter (`XR1` `rppd` `w=0.9u l=546u`) against the same
  claim.
- **DUT**: `../netlist-snapshots/loop_filter_resized.spice`, frozen from
  `design/sg13cmos5l/netlist/loop_filter.spice` at this record's own branch
  (parent commit `15de40cbb38392c5b38b758e263d60a42f60776d`). Differs from
  `RECORD-001`'s own snapshot in **exactly one instance's geometry**:

  | Instance | RECORD-001 (was) | RECORD-002 (now) |
  |---|---|---|
  | `XR1` (`rppd`, series filter resistor) | `w=4u l=120u b=0 m=1` | **`w=0.9u l=546u b=0 m=1`** |

  `XC1`, `XC2` (both `cap_cmomi`) are **untouched**.
- **Claim under test**: same as `RECORD-001` — `spec/decision-records/DR-003`
  Finding 2's MOM-uncertainty obligation, plus (new to this record) whether
  the resize lands `R1` at the target scale
  `sim/sg13cmos5l-loop-bandwidth-pm/corners/proposal.csv` identified ("R1
  x20, ~156 kOhm nominal") once measured through the real `r3_cmc` compact
  model at real process corners, not just the `rppd` symbol's own display
  formula.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host — same install `RECORD-001` and the sanity re-run below used.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  now writes **both** `../corners/results.csv` (as-drawn, unchanged,
  byte-identical to `RECORD-001`) **and** `../corners/results_resized.csv`
  (27 rows, this record's own data) in the same invocation.

## Pre-resize sanity check (issue #41's own Test Plan)

Before touching the schematic, `sim/sg13cmos5l-loop-bandwidth-pm/testbench/run.sh`
was re-run against the **unmodified** filter (this record's sibling
directory's own `RECORD-001` snapshot) to confirm the original 0/90
phase-margin finding reproduces from this environment's PDK setup. It does,
**byte-for-byte**: `results.csv`, `mom_band.csv`, `proposal.csv` and
`crosscheck.txt` in `sim/sg13cmos5l-loop-bandwidth-pm/corners/` reproduced
identical to the already-committed files (`git diff` empty after the run),
confirming PM = 1.55-20.33 deg, 0/90 combinations meeting the 45 deg
criterion, before any resize was made.

## Headline result

**R1 lands at 19.97x-19.99x the as-drawn value across every PVT corner
measured** — matching the "R1 x20" target
`sim/sg13cmos5l-loop-bandwidth-pm/corners/proposal.csv` identified, to
within 0.15%:

| Metric | As-drawn (`results.csv`) | Resized (`results_resized.csv`) | Scale factor |
|---|---|---|---|
| `R1` (nominal, `res_typ`/27C) | 7.794 kOhm | **155.7 kOhm** | **19.981x** |
| `R1` (full PVT range) | 6.950 - 8.746 kOhm | **138.83 - 174.80 kOhm** | 19.974x - 19.988x |
| `fz` (nominal, `mom_frac`=0) | 12.07 MHz | **604.3 kHz** | 0.0500x (1/19.98) |
| `fp` (nominal, `mom_frac`=0) | 216.0 MHz | **10.81 MHz** | 0.0500x (1/19.98) |
| `fz` (full matrix) | 8.97 - 16.92 MHz | **448.6 kHz - 847.3 kHz** | -- |
| `fp` (full matrix, computed directly from `results.csv`/`results_resized.csv`) | 160.39 - 302.72 MHz | **8.024 - 15.155 MHz** | -- |

(`RECORD-001`'s own "full matrix" range table only tabulates `fz`'s
min/max, 8.97-16.92 MHz — the `fp` full-matrix range above is computed
directly from the `fp_hz` column of both CSVs for this record, not quoted
from `RECORD-001`'s prose.)

`C1`/`C2` are untouched by the resize (`1.691 pF` / `100.15 fF` nominal,
identical to `RECORD-001`), so `fp/fz = (C1+C2)/C2` is unchanged at ~16.9,
and both `fz` and `fp` scale down by exactly the same `R1` factor (~1/19.98)
— consistent with `RECORD-001`'s own finding that `R*C`-family quantities
scale together under a pure `R1` resize.

## Why the geometry chosen (`w=0.9u l=546u`), not a simpler single-axis scale

`rppd`'s DRC bounds (`sg13cmos5l_tech.json`): `rppd_minW = 0.5u`,
`rppd_maxL = 1m` (1000 um). Both single-axis options that keep the *other*
dimension fixed at its as-drawn value are **infeasible**:

- **Length-only** (`w=4u` fixed, `l = 120u x 20 = 2400u`) — exceeds
  `rppd_maxL` (1000u) by 2.4x. Not drawable.
- **Width-only** (`l=120u` fixed, `w = 4u / 20 = 0.2u`) — violates
  `rppd_minW` (0.5u). Not drawable.

Both bounds are violated because `rppd`'s DC resistance (from the symbol's
own display formula, cross-checked against the real `r3_cmc` model to
<0.2% at the as-drawn geometry — `RECORD-001`'s nominal `R1` = 7.794 kOhm
vs. the formula's 7805.8 ohm) is `R ~ 70e-6/w + 260*l/(w+6e-9)`, i.e.
dominated by the `l/w` "squares" term for `l >> w`: pushing 20x resistance
through a single axis needs either a 20x length or a 20x-narrower width, and
`rppd`'s own bounds only leave headroom of ~8.3x on length (1000u/120u) and
~8x on width (4u/0.5u) individually — neither alone reaches 20x.

**Co-scaling both axes** (`l` up, `w` down) is not just a workaround for the
DRC bound — it is also the area-minimizing choice. For a fixed sheet
resistance, `R ~ l/w` and `Area = l*w`, so `R*Area ~ l^2` — i.e., for a
target `R` increase factor `k`, scaling `l` by `sqrt(k)` and `w` by
`1/sqrt(k)` holds `Area` **constant**, while any other split (e.g. `l` up
more than `sqrt(k)`, `w` down less) increases area. `sqrt(20) = 4.472`;
`120u x 4.472 = 536.7u`, `4u / 4.472 = 0.894u` — the geometry actually
chosen (`l=546u`, `w=0.9u`, rounded from that ideal split to land the
*measured*, not just formula-predicted, nominal `R1` within 0.1% of the
155,883 ohm target) sits almost exactly on this minimum-area curve. See
DR-006 for the resulting area-cost comparison against scaling `C1` instead.

## What this does not bound

Same scope boundary as `RECORD-001`: this record measures `R1`/`C1`/`C2`
and the filter's own `fz`/`fp` in isolation (single-device extraction plus
the closed-form two-port formula), not the closed-loop `f_c`/phase-margin
number — that is `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002`'s
claim, using this record's own `results_resized.csv` as one of its three
real-measurement inputs (matching `RECORD-001`'s own dependency structure
on this directory's `results.csv`).
