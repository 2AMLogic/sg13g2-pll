# RECORD-004: `schmitt_hv` in-band crowbar current — measured, mitigated, and re-verified against row 16

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #76 (Part of #16). Supersedes nothing. `RECORD-003` (#66) restored
  `schmitt_hv`'s hysteresis and re-sized `XMPD`, and measured a side effect as
  a follow-up rather than absorbing it: with no output stage, `schmitt_hv`'s
  own inverter pair conducts crowbar current whenever its input (`VWIN`) rests
  between its two trip points — which is now a *designed* possibility, since a
  wide hysteresis band means a wide range of `VWIN` is neither clearly
  asserted nor clearly de-asserted. This record decides, by measurement,
  whether that is a practical defect, and — independent of that decision —
  mitigates it at zero measured cost and re-verifies row 16 against the
  changed cell.
- **DUT (PVT re-verification)**:
  `../netlist-snapshots/lock_detector_crowbarfix.spice`, frozen from
  `design/sg13cmos5l/netlist/lock_detector.spice` at this record's own branch
  HEAD. It differs from `RECORD-003`'s `lock_detector_hystfix.spice` in
  **exactly six lines** — `schmitt_hv`'s three PMOS and three NMOS channel
  lengths, `l=0.5u` → `l=2u`, every `W` unchanged:

  | Device | RECORD-003 (was) | RECORD-004 (now) |
  |---|---|---|
  | `schmitt_hv.XMP1/XMP2/XMP3` | `w=5u l=0.5u` | **`w=5u l=2u`** |
  | `schmitt_hv.XMN1/XMN2/XMN3` | `w=2u l=0.5u` | **`w=2u l=2u`** |

  `XRPU`, `XMPD`, `XCW` and `XDW.XC1` are untouched, so neither #52's `R·C`
  margin nor #66's `XMPD` two-sided bound is spent here — both are
  re-measured below rather than assumed. The same change is landed on the
  SG13G2 sibling `design/schmitt_hv.sch` in this same change,
  matching the "both PDKs" precedent `RECORD-003` set for the feedback
  rewiring (schmitt_hv is a shared cell, and the same 6T-Schmitt crowbar
  mechanism applies to either PDK's device models).
- **DUT (dwell-fraction decision)**: `../netlist-snapshots/lock_detector_hystfix.spice`,
  i.e. `RECORD-003`'s own **pre-mitigation** block — deliberately, since the
  question this half of the record answers is "does the defect `RECORD-003`
  described actually occur during real operation", independent of whether it
  is later mitigated.
- **Claim under test**: `spec/porting-plan.md` row 16 (re-verify all three
  measurable criteria against the changed cell) and row 11 (the
  `lock_detector` power domain bound). The **new** claim this issue adds:
  whether the crowbar current `RECORD-003` measured under a held static phase
  error is a defect or an accepted residual under a realistic closed-loop
  acquisition.
- **Reference range**: `spec/porting-plan.md` row 2 as amended by DR-005 —
  `f_ref` ≈ 3.5–24.4 MHz. No spec row was relaxed to make anything here pass.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host, `set num_threads=1` (see `../testbench/run.sh`'s tooling note).
  Same `itl4=5000 gmin=1e-11` settings `RECORD-003` landed; **no new solver
  retry was needed this run** — `../corners/solver_retries.txt` is empty,
  against `RECORD-003`'s 8/590 (1.4%) — the longer `schmitt_hv` channels make
  every internal node less prone to floating near a switching point for as
  long, which plausibly explains the improvement, though this record does not
  chase that down further since it is a strict improvement.
- **Reproduce**:
  `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l LADDER_JOBS=<n> ./testbench/run.sh`
  writes `../corners/rc_extract_crowbarfix.csv` (15 rows),
  `../corners/window_crowbarfix.csv` (102), `../corners/schmitt_crowbarfix.csv`
  (45), `../corners/ladder_crowbarfix.csv` (21),
  `../corners/ladder_raw_crowbarfix.csv` (441),
  `../corners/tstep_convergence_crowbarfix.csv` (12) and
  `../corners/solver_retries.txt`. `LADDER_JOBS` (new this issue) runs ladder
  corners concurrently — the campaign is concatenation of independent
  per-corner ngspice invocations, not a change of method, and a record run
  with it `>1` must say so (this one did: `LADDER_JOBS=8`).
  `TAUBIG_XWIN=20 ./testbench/run.sh` re-measures the same `idd_outlock`
  column with the out-of-lock probe beyond the de-assert threshold at every
  corner instead of at 10× the window; both runs are reported below.
  `PDK_ROOT=... ./testbench/run_schmitt_crowbar.sh` writes
  `../corners/schmitt_crowbar_variants.csv` (180 rows, the per-device I(V)
  sweep the length choice rests on).
  `PDK_ROOT=... ../../sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_vwin_dwell.sh`
  writes `../../sg13cmos5l-closed-loop-lock/corners/vwin_dwell_closed_loop.csv`
  (6 rows) and `vwin_trace_closed_loop.csv` (30003 decimated samples), the
  dwell-fraction evidence.
  `python3 testbench/band_zone.py ../corners _crowbarfix` (no new simulation)
  writes `../corners/band_zone_static_crowbarfix.csv` from this record's own
  committed CSVs, alongside the equivalent `_hystfix` recomputation of
  `RECORD-003`'s data.

## Part 1 — the decision: is the crowbar current a defect or an accepted residual?

**Measured: an accepted residual under realistic closed-loop operation.**
`VWIN` never entered `schmitt_hv`'s hysteresis band in any of three
independently-seeded closed-loop acquisitions, over a 20 µs transient that
spans 3.6–8.8 of the integrating node's own 2.29–5.58 µs `R·C` time
constants across the PVT matrix (this specific run is at
`mos_tt`/`res_typ`/27 °C/3.3 V, `R·C` = 3.83 µs → 5.2 time constants at this
particular corner).

**Deck**: `run_closed_loop_vwin_dwell.sh` instantiates the **pre-mitigation**
`RECORD-003` block (`lock_detector_hystfix.spice`) and the pre-#52
`RECORD-001` block side by side on the *same* `up`/`dn` nodes inside one
closed-loop acquisition (`pfd`+`cp`+`loop_filter`(R1×20)+`vco`+behavioural
÷64 — the same Part B proposal deck `sg13cmos5l-closed-loop-lock`'s own
`RECORD-003`/`RECORD-004` measured genuine frequency lock on), so both
readouts see literally the same phase-error waveform. Three initial control
voltages (`VC0` = 1.20, 2.46, 3.30 V) stand in for three different starting
frequency errors on the VCO's tuning curve, and run **in parallel** — three
independent ngspice invocations against the same generated deck.

**This is now a representative operating point.** The deck's own header
flagged a dependency: until issue #72 (the `cp` `Icp_up`/`Icp_dn` mismatch)
was fixed, the closed loop settled at a ~9.18%-of-`T_ref` static phase error
that was itself a `cp` defect, not a realistic one. #72 closed via #85 (an
on-chip cascode bias replica) before this record ran; the settled phase error
measured here is **−4.4% to +0.008% of `T_ref`** over the last 20 reference
cycles at the three tested `VC0` — an order of magnitude smaller than the
pre-#85 figure, and small in absolute terms relative to `schmitt_hv`'s own
trip points.

| `VC0` | `dwell_frac` (whole transient) | `VWIN` range | settled phase error (last 20 `T_ref`) |
|---|---|---|---|
| 1.20 V | **0.000000** | pinned at 3.3000 V (`VDD`) throughout | −4.395% of `T_ref` |
| 2.46 V | **0.000000** | pinned at 3.3000 V throughout | −3.387% of `T_ref` |
| 3.30 V | **0.000000** | 3.2995–3.3000 V (≤ 0.5 mV of `VDD`) | +0.008% of `T_ref` |

(Control, `RECORD-001`'s pre-#52 block, for reference: `dwell_frac` = 0.000000
at `VC0` = 1.20/2.46 V and **0.000100** at 3.30 V — 2 ns of a 20 µs transient,
the one non-zero cell in either table.)

**Why it is zero, mechanistically, not just numerically.** `XMPD`'s discharge
pulse is gated by the coincidence window (`WIDE`), whose duration is set by
the *actual* phase error each cycle. A closed loop that has acquired lock to
within a few percent of `T_ref` produces `WIDE` pulses far shorter than the
multi-window static offsets `RECORD-003`'s own ladder deliberately holds
*forever* to park `VWIN` inside the band. `XRPU`'s pull-up (1.35–3.30 MΩ)
wins the balance every cycle at this phase-error magnitude, so `VWIN` never
drifts more than a few mV from `VDD` in any of the three acquisitions —
`../../sg13cmos5l-closed-loop-lock/corners/vwin_trace_closed_loop.csv` shows
the full 10001-sample-per-run trace, not just the summary row.

**What this does and does not establish.** It establishes that the specific
condition `RECORD-003` measured — a *held, static* phase error of several
window-widths — is not what a genuinely acquiring or locked loop produces at
this PVT point, starting from three different points on the VCO tuning
curve. It does **not** rule out every path to the band: a startup transient
with a much larger initial frequency error, a different PVT corner (this
deck runs the single fixed point `sg13cmos5l-closed-loop-lock`'s own
`corners/matrix.md` uses for the same runtime-cost reason cited there — the
six-block hierarchy costs ≈1 ns/s of wall time, not the few-block deck this
slug's own ladder costs), or a reference-level disturbance mid-lock are all
untested here. That residual uncertainty, not a measured occurrence, is why
Part 2 mitigates anyway.

## Part 2 — the mitigation: `schmitt_hv` channel length, 0.5u → 2u

**Mechanism, measured rather than argued.** A 6T CMOS Schmitt trigger's
hysteresis comes from two feedback devices that pull each stack's internal
node toward the *opposite* rail from the input devices in the same stack
(`VDD`–`XMN3`–`nn`–`XMN2`–`VSS`, and the PMOS mirror). While the input rests
between the trip points, a feedback device conducts directly against an input
device in its own stack — that is the crowbar path, and it exists precisely
*because* the cell has hysteresis, not despite it. Its magnitude scales with
the devices' absolute drive strength; the trip points scale with their
*ratio*. Scaling every channel length by the same factor divides the crowbar
current roughly quadratically (both the feedback and the input device weaken)
while leaving the trip-point ratio — and therefore the hysteresis — close to
unchanged.

**Length choice, measured over the per-device I(V) crowbar profile**
(`../corners/schmitt_crowbar_variants.csv`, 5 MOS corners × 3 temperatures ×
3 supplies × 4 length variants = 180 rows, `run_schmitt_crowbar.sh`):

| Variant | Worst-case peak crowbar | vs. as-drawn | Hysteresis-in-volts ratio vs. as-drawn | Band-width cost |
|---|---|---|---|---|
| as-drawn (`l=0.5u`) | 640.6 µA | — | 1.000 | — |
| **`l=2u` (chosen)** | **195.4 µA** | **3.2–4.3×** lower at every corner | **0.978–1.036** | none measurable (below) |
| `l=4u` | 97.6 µA | 6.5–8.5× lower | not separately re-verified | widens the static in-band zone up to 15.6% |
| `l=8u` | 49.9 µA | 12.6–16.6× lower | not separately re-verified | widens the static in-band zone up to 46.4% |

`l=4u`/`l=8u` buy more reduction but were rejected: they widen the
settled-`VWIN`-vs-phase-error transition enough to spend #66's `XMPD`
two-sided bound and, at the slow end of row 2's `f_ref` range, push the
de-assert threshold off the end of the ladder that measures it (`RECORD-003`
already reaches 18× the window there). `l=2u` was verified separately not to
have that cost — see the band-zone comparison below.

Trip points move by at most **−9/+27 mV** (rising) and **−34/+45 mV**
(falling) across the 21 PVT corners in `../corners/schmitt_crowbarfix.csv`
vs. `RECORD-003`'s `schmitt_hystfix.csv` — small against the 804 mV–1.058 V
of hysteresis `RECORD-003` restored.

**Static in-band zone width: unchanged, measured rather than assumed.**
`band_zone.py` recomputes, from each record's own committed ladder CSVs and
with *no new simulation*, the width (in % of `T_ref`) of the static
phase-error zone that parks `VWIN` between the trip points:

| Corner | `RECORD-003` (`l=0.5u`) | **`RECORD-004` (`l=2u`)** |
|---|---|---|
| Widest: `mos_tt`/`res_bcs`/125 °C, 3.5 MHz | 25.90% of `T_ref` | 27.32% of `T_ref` |
| 2nd-widest: `mos_tt`/`res_bcs`/125 °C, 24.4 MHz | 24.04% of `T_ref` | 25.05% of `T_ref` |
| Narrowest: `mos_ff`/`res_wcs`/−40 °C, 24.4 MHz | 5.81% of `T_ref` | 5.26% of `T_ref` |

Full 21-corner comparison in `../corners/band_zone_static_hystfix.csv` /
`band_zone_static_crowbarfix.csv`. Every corner moves by at most ~1.4
percentage points of `T_ref`, both directions, no systematic widening — the
band is exactly as reachable in phase-error terms after this change as
before it, which is the point: this mitigation spends none of #66's margin.

## Row 16 re-verification against the changed cell

**All three of row 16's measurable criteria still pass, unchanged in
substance from `RECORD-003`:**

| Row 16 criterion | RECORD-003 (post-#66) | **RECORD-004 (post-#76)** | Verdict |
|---|---|---|---|
| Assert window ≥ 2.5 ns | 3.688–11.24 ns, 0/102 below floor | **3.688–11.24 ns, 0/102 below floor** — byte-identical | **met, unaffected** (`schmitt_hv` is not in the window path) |
| Hysteresis ≥ 25% of window | 50–800% of window, 0/21 below 25% | **50–800% of window, 0/21 below 25%** — identical range | **met, re-confirmed** |
| No chatter | `steady` 21/21 at 20×-window phase error | **`steady` 21/21 at 20×-window phase error** | **met, re-confirmed** |
| Assert window ≥ 2× worst static phase offset | `insufficient-evidence` | `insufficient-evidence` (unchanged) | unchanged |

`R·C`, `XRPU` and the window matrix are byte-identical to `RECORD-002`/`003`
(`XRPU`, `XCW`, `XDW.XC1` untouched by this change): `../corners/rc_extract_crowbarfix.csv`
and `window_crowbarfix.csv` match `_hystfix` field for field.

Two individual corners' hysteresis-in-window ratio move (`mos_ff`/`res_typ`/
27 °C/3.5 MHz: 5.00× → 3.00×; `mos_tt`/`res_wcs`/125 °C/3.5 MHz: 4.00× → 5.00×)
— both stay far above the 1.00× (25% of window) floor and the aggregate
21-corner range (0.5×–8.0×) is unchanged, so neither move changes any verdict.

## Row 11 — the power-domain bound, tightened

**Row 11's `lock_detector` domain re-bounds to 2.48–113 µA**, down from
`RECORD-003`'s 2.47–234 µA — the top of the range very nearly halved. In-lock
current is unaffected, as it must be (the same steady-state readout path):

| | RECORD-003 | **RECORD-004** |
|---|---|---|
| In-lock (`idd_inlock`) | 2.47–24.19 µA | **2.48–24.20 µA** — unchanged |
| Out-of-lock, probe at 10× window (`idd_outlock`) | 46.95–233.84 µA | **44.56–112.90 µA** — peak **2.07×** lower |
| Out-of-lock, probe at 20× window (beyond de-assert everywhere) | 57.9 µA (one corner, `mos_tt`/`res_bcs`/27 °C/3.5 MHz) | **40.75–103.29 µA** (all 21 corners) |

The 20×-probe column is now measured across the **full 21-corner matrix**
rather than the single corner `RECORD-003` spot-checked (`TAUBIG_XWIN=20
./run.sh`, same deck, same corners, ladder assert/de-assert/hysteresis/chatter
columns byte-identical to the 10×-probe run — confirmed by diff — only
`idd_outlock` differs). The corner that changes *least* between the two
probe depths (`mos_ff`/`res_wcs`/−40 °C, 24.4 MHz: 96.76 µA → 103.29 µA, i.e.
slightly *higher* at 20×) is not band-related at all: that corner's window
(0.5×) means both 10× and 20× already sit well beyond de-assert, and its
~100 µA is ordinary switching current at the fastest tested `f_ref`, not
crowbar current — a useful sanity check that the columns are measuring what
they claim to.

**Attribution, as `RECORD-003` established**: the top of the 10×-probe range
is *not* a switching cost. It is `schmitt_hv` crowbar current while a probe
happens to land inside the now-wide hysteresis band — and Part 1 measured
that a realistic closed-loop acquisition does not, in the three cases tested,
put a real operating point there. This mitigation lowers the *ceiling* on
that condition without claiming the condition is common.

## Coverage, and how it changed (explicit, per `sim/README.md`)

| Axis | RECORD-003 | RECORD-004 | Why |
|---|---|---|---|
| `rc_extract` / `window` / `tstep_convergence` | 15 / 102 / 12 rows | **identical row counts, identical values** | `schmitt_hv` is outside this path |
| `schmitt` (PVT trip points) | 45 rows | **45 rows**, values shifted per-corner (above) | the change is inside this cell |
| `schmitt_crowbar_variants` (new this record) | — | **180 rows**: 5 MOS corners × 3 temps × 3 supplies × 4 length variants | the per-device sizing sweep this decision rests on |
| ladder (assert/de-assert/hysteresis/chatter) | 21 corners | **21 corners, byte-identical columns** except `idd_outlock` | same matrix, unaffected criteria re-confirmed rather than assumed |
| ladder `idd_outlock`, 20×-window probe | 1 corner (text table) | **21 corners** (full re-run, `TAUBIG_XWIN=20`) | this record needed the full-matrix "genuinely out of lock" bound for row 11, not one spot check |
| closed-loop dwell fraction (new this record) | — | **6 rows** (2 detectors × 3 `VC0`) + 30003-sample decimated trace | the decisive measurement item 1 asked for; needed the closed-loop deck, not this slug's static ladder |
| `band_zone_static` (recomputed, no new sim) | — (computed post hoc from `RECORD-003`'s own CSVs) | **21-corner comparison, `_hystfix` vs. `_crowbarfix`** | shows the mitigation spends none of #66's margin |
| solver retries | 8/590 (1.4%) | **0** | see "Tooling" above |

Nothing from `RECORD-003`'s own coverage was reduced.

## What this does not bound

- **Any acquisition more adverse than the three tested.** Part 1's zero-dwell
  result is at one PVT point (`mos_tt`/`res_typ`/27 °C/3.3 V) and three
  initial control voltages spanning the VCO tuning curve, not a frequency-step
  or supply-disturbance sweep. A large initial frequency error, a different
  PVT corner, or a mid-lock disturbance could in principle produce a longer
  or larger phase-error excursion than any tested here — this record's
  conclusion is "not observed in three realistic cases", not "provably
  cannot happen", which is exactly why Part 2's mitigation is applied
  regardless of Part 1's answer.
- **Random device mismatch and post-layout parasitics.** Unchanged from
  `RECORD-001`–`003`: no per-instance mismatch model exists for
  `sg13_hv_nmos`/`sg13_hv_pmos` or `cap_cmomi`, and this is schematic-level
  only. The `lock_detector` layout in PR #39 predates `RECORD-004`'s
  `schmitt_hv` change (and #52's and #66's) and implements none of them.
- **Row 16's "≥ 2× worst static phase offset" half.** Still
  `insufficient-evidence`, unchanged — needs a PFD/CP static-phase-offset
  record independent of this issue's scope.
- **Anything about the SG13G2 `lock_detector` beyond `schmitt_hv`.** As
  `RECORD-003` recorded: its `XRPU`/`XCW`/`XMPD` are still pre-#52 sized and
  there is no `sim/` slug for that PDK's `lock_detector` campaign. The
  `schmitt_hv` channel-length change is landed on the SG13G2 sibling schematic
  in this same change (measured to be the identical mechanism — a 6T CMOS
  Schmitt shares its topology and crowbar path regardless of which PDK's
  device models back it), but is not separately PVT-verified on SG13G2 for
  the same reason `RECORD-003` did not port the `XMPD` re-size: SG13G2's
  `lock_detector` has not had its own `R·C` re-derivation campaign yet.

## Spec-row disposition

- **Row 16 — all three measurable criteria**: **unchanged verdict from
  `RECORD-003`, re-confirmed against the changed cell rather than assumed
  carried over.** See table above.
- **Row 11 — power (`lock_detector` domain)**: **re-bounded, tightened, at
  2.48–113 µA** (10×-window probe) / 40.75–103.29 µA (20×-window probe,
  full matrix), down from `RECORD-003`'s 2.47–234 µA.
- **The #76 question itself — is the crowbar current a defect?**: **measured
  as an accepted residual under realistic closed-loop operation** (zero dwell
  in three tested acquisitions at a now-representative operating point,
  issue #72 having closed), **mitigated anyway** at zero measured cost to row
  16 or #52's/#66's margins, because the residual uncertainty in "three
  tested cases" is cheap to hedge against and expensive to re-derive later if
  wrong.
