# RECORD-001: loop bandwidth and phase margin (linearised, PVT-cornered)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #27 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L
  closed-loop PVT campaign)
- **DUT**: the type-II charge-pump loop formed by the committed
  SG13CMOS5L blocks. The **loop filter is the real, unmodified
  `loop_filter` subckt** (`../netlist-snapshots/loop_filter.spice`, frozen
  at commit `db5ec6afaf79a04aeb13b9a43a4b5905472ff37a`), simulated through
  its own `rppd` and `cap_cmomi` compact models at real process corners. The
  phase detector + charge pump, VCO and divider are **linearised
  small-signal stand-ins whose every numeric value comes from a real
  measurement recorded elsewhere in this repo** — see "What is real here"
  below, which states the boundary precisely.
- **Claim under test**: `spec/porting-plan.md` row 6/6a. That row carries
  the *criteria* (`f_c < f_ref/10`, PM ≥ 45°) and the *mechanism* (a coarse
  `Icp` trim keyed to `f_ref`) over as-is, and marks "every kHz number and
  the trim-code table" as re-derive. Both #23 records that touch this row
  mark it `insufficient-evidence` pending the Kvco and Icp-trim tables;
  both now exist, so this record closes the gap.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  writes `../corners/results.csv` (90 rows), `../corners/mom_band.csv` (54),
  `../corners/proposal.csv` (108) and `../corners/crosscheck.txt`.

## Headline result

**No trim code closes the loop with the as-drawn filter.** Across all 90
real-subckt runs — 3 PVT bundles x 2 band codes x 2 `Kvco` intervals x the
admissible `f_ref`/`N` scenarios x 6 trim codes — the phase margin never
exceeds **20.33°**, against a 45° requirement, and the single best-PM point
also violates the `f_c < f_ref/10` ceiling. **Zero of 90 rows meet PM ≥ 45°;
zero meet both criteria.** This is not a marginal shortfall that a trim code
choice can recover: `f_c` and PM move in the *same* direction with `Icp`
here, so there is no code that trades one against the other.

The cause is specific and measurable: the filter's zero sits at
**f_z ≈ 9.0 – 16.9 MHz** (`sg13cmos5l-loop-filter-momcap` measured
`R1 ≈ 6.95 – 8.75 kΩ`, `C1 ≈ 1.35 – 2.03 pF`), while every achievable `f_c`
is **0.33 – 4.64 MHz**. The crossover is far *below* the zero, so the loop
is still behaving as an uncompensated double integrator there — phase
margin is whatever little the zero contributes at `f_c ≪ f_z`. The
`C1/C2 ≈ 16.9` ratio is *not* the problem (it affords up to ~63° of margin
at the optimum crossover); the problem is that `R1·C1 ≈ 1.3×10⁻⁸ s` places
the zero one to two decades above any crossover the loop can reach at a
reference frequency this design is allowed to use.

## What is real here, and what is linearised

| Loop term | Source | Real or behavioural |
|---|---|---|
| Loop filter `Z(s)` | `../netlist-snapshots/loop_filter.spice` instantiated verbatim, `rppd` + `cap_cmomi` compact models, `cornerRES.lib` section per bundle | **Real** (Parts A/A′) |
| `Icp` | `../../sg13cmos5l-cp-icp-trim/corners/results.csv` — a real DC sweep of the committed `cp` block at the matching MOS corner/temperature | Real *value*, behavioural *element* (`Icp/2π` A/rad transconductance) |
| `Kvco` | `../../sg13cmos5l-vco-kvco-table/corners/results.csv` — a real PVT-cornered transient sweep of the committed `vco` block; local secant slope over two `VCTRL` intervals | Real *value*, behavioural *element* (ideal `2π·Kvco/s` phase integrator) |
| Divider | memoryless `1/N` | Behavioural |

**No transistor-level closed-loop transient is run in this record.** That is
stated plainly here and again under "What this does not bound", because it
is the difference between what this record can and cannot settle.

## Cross-check: does the linearisation track the real subckt?

`../corners/crosscheck.txt`, at the nominal point (`typ` bundle, band `11`,
`top` Kvco interval, `f_ref` = 25 MHz, N = 50, 10 µA trim code,
`mom_frac` = 0):

|  | `f_c` | PM |
|---|---|---|
| real `loop_filter` subckt | 954.6 kHz | 4.275° |
| lumped R/C from the predecessor record's measured values | 967.8 kHz | 4.326° |
| difference | **+1.38%** | **+0.051°** |

The lumped equivalent (needed only because `cap_cmomi` has no
MOM-uncertainty knob to sweep) tracks the real compact-model filter to
1.4% in `f_c`. This mirrors the cross-check discipline the predecessor
loop-filter record used on its own closed-form `f_z`/`f_p`.

## Results — as-drawn filter, real `loop_filter` subckt

All at `f_ref` = 25 MHz, `N` = round(f_VCO / f_ref). `f_c` and PM columns
give the range across the 2.5 µA → 80 µA trim ladder
(`../corners/results.csv`, 90 rows):

| Bundle | Band | Kvco interval | Kvco (MHz/V) | f_VCO (MHz) | N | f_c range (MHz) | PM range (°) |
|---|---|---|---|---|---|---|---|
| typ | 00 | mid | 203.2 | 594.0 | 24 | 0.542 – 3.104 | 2.43 – 13.61 |
| typ | 00 | top | 206.0 | 849.2 | 34 | 0.458 – 2.614 | 2.06 – 11.54 |
| typ | 11 | mid | 496.6 | 713.1 | 29 | 0.771 – 4.490 | 3.46 – 19.21 |
| typ | 11 | top | 328.6 | 1260.5 | 50 | 0.477 – 2.725 | 2.14 – 12.01 |
| slow | 00 | mid | 168.4 | 533.9 | 21 | 0.527 – 3.030 | 2.65 – 14.84 |
| slow | 00 | top | 162.2 | 742.6 | 30 | 0.433 – 2.473 | 2.18 – 12.22 |
| slow | 11 | mid | 382.7 | 626.4 | 25 | 0.729 – 4.262 | 3.67 – **20.33** |
| slow | 11 | top | 239.4 | 1042.0 | 42 | 0.445 – 2.541 | 2.24 – 12.54 |
| fast | 00 | mid | 229.9 | 661.3 | 26 | 0.554 – 3.165 | 2.22 – 12.42 |
| fast | 00 | top | 238.5 | 953.8 | 38 | 0.467 – 2.656 | 1.87 – 10.48 |
| fast | 11 | mid | 590.2 | 806.9 | 32 | 0.800 – 4.639 | 3.20 – 17.82 |
| fast | 11 | top | 379.9 | 1448.0 | 58 | 0.477 – 2.714 | 1.91 – 10.71 |

**Overall: `f_c` ∈ 0.332 – 4.639 MHz, PM ∈ 1.55 – 20.33°.** The `f_c <
f_ref/10` ceiling *is* met by the lower trim codes (it is the easy
criterion); PM is met by nothing.

## Results — MOM-cap uncertainty at the loop level

Propagating DR-003 Finding 2's ±20% MOM band (band `11`, `top` interval,
10 µA code, `f_ref` = 25 MHz — `../corners/mom_band.csv`):

| Bundle | `mom_frac` = −0.20 | 0.00 | +0.20 |
|---|---|---|---|
| typ | 1081.7 kHz / 3.87° | 967.8 kHz / 4.33° | 883.7 kHz / 4.74° |
| slow | 1007.4 kHz / 4.04° | 901.4 kHz / 4.52° | 823.1 kHz / 4.95° |
| fast | 1079.8 kHz / 3.45° | 966.0 kHz / 3.85° | 882.1 kHz / 4.22° |

The MOM band moves `f_c` by roughly **∓10%** and PM by **±0.4°**. That is
the first *loop-level* number DR-003 Finding 2's obligation has produced —
and its practical significance is that MOM-model uncertainty is nowhere
near the dominant term in this row. The design shortfall is ~40° of phase
margin; the MOM band is worth ~0.9° of it.

## Results — what would close the loop (PROPOSAL, not the committed design)

`../corners/proposal.csv` sweeps `R1` above its as-drawn value with `C1`,
`C2` and their ratio unchanged, and asks which (filter, trim code) pairs
meet **both** criteria. The pairs that pass are **identical at all three
PVT bundles**:

| `R1` scale | Trim code | `f_c` (MHz), typ / slow / fast | PM (°), typ / slow / fast |
|---|---|---|---|
| ×10 | 20 µA | 1.841 / 1.756 / 1.737 | 51.9 / 53.3 / 48.0 |
| ×20 | 5 µA | 0.922 / 0.879 / 0.870 | 51.9 / 53.3 / 48.0 |
| **×20** | **10 µA** | **1.631 / 1.570 / 1.498** | **61.1 / 61.8 / 58.6** |
| ×50 | 2.5 µA | 0.974 / 0.940 / 0.886 | 63.4 / 63.4 / 62.6 |
| ×50 | 5 µA | 1.802 / 1.731 / 1.651 | 59.7 / 58.7 / 61.9 |
| ×100 | 2.5 µA | 1.572 / 1.494 / 1.478 | 49.6 / 48.1 / 53.4 |

`R1` ×20 (≈156 kΩ, versus 7.79 kΩ as drawn) with the **10 µA trim code**
is the widest-margin single choice that holds at every bundle: PM 58.6–61.8°,
`f_c` 1.50–1.63 MHz, comfortably under the 2.5 MHz ceiling. It also leaves
the trim ladder doing what row 6/6a says it should — one code step either
side still meets both criteria at ×20 and ×50, which is exactly the
"coarse Icp trim keyed to f_ref" mechanism being usable rather than
saturated.

**These rows are a proposal, not a measurement of the committed design.**
They are kept in a separate CSV for that reason. Scaling `R1` rather than
`C1` is deliberate: raising `C1` by 20x instead would need ≈34 pF of
`cap_cmomi` (≈183 × 183 µm at the measured density, ≈0.033 mm², about 22%
of `spec/porting-plan.md` row 15's whole 0.15 mm² area budget for one
capacitor), and would push the required `Icp` to ~200 µA, off the top of
the measured trim ladder. Choosing between "longer `rppd`" and "bigger
MOM cap" is a design decision for a decision record, not something this
sim record settles.

## The reference-frequency range is not reachable, either

A second, independent finding fell out of generating the scenario list.
`spec/porting-plan.md` row 2 carries a **1–25 MHz** reference interface and
row 3 carries **N ∈ [4, 64]**, while `sg13cmos5l-vco-kvco-table` measures the
VCO's own band as **445.3 – 1562.0 MHz** across all corners. Those three are
mutually inconsistent: reaching even the VCO's floor requires
`f_ref ≥ 445.3/64 = 6.96 MHz`, so **no reference frequency below ~7 MHz is
usable at all**, and at 10 MHz only 3 of the 12 (bundle, band, interval)
combinations admit an in-range `N` (the rest need N > 64). Recorded here
because it constrains row 6/6a directly — the `f_c < f_ref/10` ceiling is
set by `f_ref`, and the usable `f_ref` range is much narrower than the
ported row implies. Whether the resolution is a wider `N` range, a lower
VCO band, or an amended row 2 is a spec question, not a sim question;
deferred to issue #40 (Part of #16).

**A related structural note on `N`, read from the netlist rather than
simulated.** The scenario table above derives `N` from the *spec's* range
(row 3: `N ∈ [4, 64]`). The divider as actually drawn is a fixed-length
6-cell Vaucher ÷2/3 chain with every cell always active
(`design/README.md` states this simplification explicitly), whose natural
ratio is `N = 2⁶ + Σ pᵢ2ⁱ`, i.e. **`N ∈ [64, 127]`** — a range that barely
touches the spec's and has no overlap below 64. This is a reading of
`divider_chain.spice`'s topology, **not** a measured division ratio; this
record makes no simulated claim about the divider (deferred to issue #36,
Part of #16). It is noted here only because `N` is a loop-gain term: a larger
`N` lowers loop gain, which lowers `f_c`, which — at `f_c ≪ f_z` — lowers
phase margin further. So if the real `N` range is 64–127 rather than the
21–58 used above, this record's headline conclusion is **strengthened**,
never weakened.

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 6/6a — loop bandwidth / phase margin**: **bounded by this record,
  and the bound is a failure to meet the criteria.** `f_c` = 0.33 – 4.64 MHz
  and PM = 1.55 – 20.33° across the full measured matrix; the ≥45° PM
  criterion is met by none of the 90 combinations. The
  `insufficient-evidence` marking the two #23 records left on this row is
  **cleared** — the row now has real numbers. It is *not* replaced by a
  passing result, and this record does not relax the criterion to make it
  pass (this repo's CLAUDE.md: "agents do not relax the ratified spec to
  make results pass"). The concrete, evidence-backed remedy is in
  "Proposal" above, and is filed as issue #41 (Part of #16).
- **Row 6/6a — Icp-trim mechanism**: **bounded**, by the sibling record
  `sg13cmos5l-cp-icp-trim`, and shown here to be usable once the filter is
  resized (one code step of margin either side of the working point).
- **Row 2 / row 3 — reference range and N range**: **newly contradicted by
  measured data** (see above). Not this record's claim to settle; recorded
  and filed.
- **Row 7 — lock time**: **`insufficient-evidence`, and structurally so.**
  A settling time is only defined for a loop that settles; with PM ≤ 20.3°
  the as-drawn loop's step response is severely under-damped, so no lock-time
  number derived from this linearisation would describe the committed
  design. This record deliberately does not report one, and does **not**
  substitute the linearised second-order settling formula for the
  transistor-level closed-loop transient that row needs. Deferred to issue
  #37 (Part of #16).

## What this does not bound

- **Any large-signal or acquisition behaviour** — this is a small-signal
  linearisation around a locked operating point. Cycle slipping, the PFD's
  own dead zone, charge-pump compliance limits at the extremes of `VCTRL`
  (which `sg13cmos5l-cp-icp-trim` shows do bite at the cold corner), and the
  frequency-detect region of the PFD are all invisible to it.
- **Sampled-loop (z-domain) effects** — the `f_c < f_ref/10` criterion is
  *evaluated* here, never assumed; where it is violated the continuous-time
  `f_c`/PM figures in the table are themselves optimistic.
- **Reference spur, jitter and phase noise** — none is an AC open-loop
  quantity.
- **The `f_ref`-to-trim-code rule itself** — row 6/6a's mechanism is "a
  coarse Icp trim *keyed to f_ref*". Producing a normative keying table
  needs a filter that closes the loop first; the proposal section shows
  which code works for the ×20 filter at 25 MHz, not a full per-`f_ref`
  rule.
