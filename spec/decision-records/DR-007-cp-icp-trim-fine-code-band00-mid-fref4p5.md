# DR-007: a fine (3.75 uA) `cp` Icp-trim code closes the `band=00, mid, f_ref=4.5MHz` PM gap

- **Status**: proposed
- **Date**: 2026-08-30
- **Decided by**: Builder agent, issue #83
- **Related**: #16 (parent, epic), #83 (this issue), #41 / DR-006
  (`spec/decision-records/DR-006-loop-filter-r1-resize.md`, the R1 resize
  this gap was found against), #79 (a *different*, still-open PM gap at the
  same R1 resize -- `band=00, low interval, f_ref=4.5MHz` -- not touched by
  this record)
- **Consumes**: `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  (the gap this record closes), `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`
  and `sim/sg13cmos5l-cp-icp-trim/records/RECORD-003-issue83-finetrim-icp.md`
  (the evidence this record cites), `spec/decision-records/DR-006-cp-cascode-bias-replica.md`
  (confirms `cp`'s `IBP`/`ICP`/`IBN`/`ICN` pins are current inputs so any
  reference-current value is a legitimate operating point, not a hardware
  modification)

## Context

`sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
re-verified the resized `loop_filter` (DR-006, `R1` ~x44.2) across the full
amended `f_ref` range and found one operating point, `band=00`, mid `Kvco`
interval, `f_ref` = 4.5 MHz (only the `slow` PVT bundle reachable, `n_div` =
119), where **no code in the existing six-code Icp-trim ladder** (2.5, 5,
10, 20, 40, 80 uA) meets both stability criteria (`f_c < f_ref/10`, PM
>= 45 deg) simultaneously: at 2.5 uA, `fc_hz` = 2.69e5 clears the 4.5e5 Hz
ceiling but `pm_deg` = 43.639 misses 45 deg by 1.36 deg; at 5 uA and above,
PM clears but `fc_hz` blows through the ceiling (5 uA itself: `fc_hz` =
4.520837e5, only 0.46% over the 4.5e5 Hz ceiling). Filed as issue #83.

`spec/porting-plan.md` row 6/6a ports the *mechanism* behind this ladder as
a "coarse Icp trim keyed to f_ref, not a filter redesign" -- and
`design/README.md` / `sim/sg13cmos5l-cp-icp-trim/corners/matrix.md` both
state plainly that `cp.sch` has **no on-chip unit-element trim array**: the
"trim code" is the mirror reference current a not-yet-drawn bias generator
would deliver, driven directly into `cp`'s `IBP`/`ICP`/`IBN`/`ICN` current
inputs (`DR-006-cp-cascode-bias-replica.md`). The existing six-code ladder
is therefore a *characterisation grid*, not a hardware-fixed set of legal
values -- any reference-current magnitude the bias generator could someday
deliver is a legitimate operating point to measure and, if useful, to
program.

## Decision

**A seventh Icp-trim code, 3.75 uA -- the arithmetic midpoint of the
existing 2.5/5 uA codes -- is added to the trim table, measured for the
`slow` PVT bundle (`mos_ss`/125 C/3.3 V) only** (the only bundle reachable
at the `band=00, mid interval, f_ref=4.5MHz` tuple, per RECORD-002). This is
a **value** addition to the trim table, not a geometry change: `R1`/`C1`/`C2`
are untouched, and no other trim code, PVT bundle, or (band, interval,
`f_ref`) combination is affected.

Real-subckt measurement, real `cp` block into the real resized `loop_filter`
(not lumped): `Icp` = 3.750478 uA (measured, `mos_ss`/125 C/3.3 V, `up`
state), `fc_hz` = 3.592385e5, `pm_deg` = 49.973, ceiling = 4.5e5 Hz. **Both
criteria clear with real margin**: `fc_hz` is 20.2% under the ceiling,
`pm_deg` is 4.97 deg over the 45 deg floor -- see
`sim/sg13cmos5l-cp-icp-trim/records/RECORD-003-issue83-finetrim-icp.md` and
`sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`
for the full evidence.

**A part built to this design and operated at `f_ref` = 4.5 MHz in `band=00`,
`Kvco` mid interval, must be trimmed to the 3.75 uA code, not one of the
original six**, exactly as `spec/porting-plan.md` row 6/6a's own ported
mechanism ("a coarse Icp trim keyed to f_ref") already anticipates a
per-`f_ref` trim selection. This decision adds one entry to that
not-yet-fully-built selection table; it does not attempt the full 30-tuple
per-`f_ref` trim rule gf180-pll's own `DR-006` Decision 5 builds (out of
scope for issue #83 -- see "What remains open" below).

## Alternatives considered

- **A joint `R1`/`C1`/`C2` re-tune** -- rejected for this gap specifically:
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  ("Why x44.2, not x20") already found PM margin non-monotonic in `R1`
  scale across the amended matrix -- pushing `R1` further to help this one
  point risks reopening the `band=00/low/f_ref=4.5MHz` gap (#79) or a
  currently-passing point elsewhere, for a problem the existing Icp
  reference-current mechanism already solves with zero geometry risk.
- **Frequency-planning narrowing** (excluding `band=00, mid interval,
  f_ref~4.5MHz` from the design's practical operating range) -- not
  pursued: unnecessary once the existing trim mechanism, used at a finer
  granularity, closes the gap outright with comfortable margin (4.97 deg
  PM, 20% `fc` headroom), not a marginal squeeze that would justify
  narrowing the ratified range instead.
- **Accepting the 1.36 deg shortfall as within model/process uncertainty**
  -- not needed: the fix is cheap (one additional characterisation point,
  no geometry change) and closes the gap with real margin rather than
  documented uncertainty, which is strictly better evidence for this
  repo's own "no claim without a testbench" standard.
- **Extending the fine-trim measurement to `typ`/`fast` bundles at this
  tuple too** -- not applicable: RECORD-002 already established only the
  `slow` bundle reaches a legal `n_div` (`n_div` in [64,127]) at
  `band=00, mid interval, f_ref=4.5MHz`; `typ`/`fast` do not have this
  operating point at all (confirmed directly against
  `sim/sg13cmos5l-loop-bandwidth-pm/corners/results_resized.csv`, which
  carries `f_ref=5.5MHz` as the lowest reachable point at `band=00, mid`
  for those two bundles).

## Consequences

**What becomes possible**:

- `spec/porting-plan.md` row 6/6a's accounting improves from "16 of 17
  full-3-bundle-coverage regions plus 12 of 13 partial-coverage regions
  pass" (`DR-006-loop-filter-r1-resize.md` Consequences) to the same 16 of
  17, plus **13 of 13** partial-coverage regions passing at every bundle
  actually simulated -- `band=00, mid interval, f_ref=4.5MHz` (`slow`
  bundle) now closes with real, PVT-real-subckt margin, real, not
  estimated.
- Confirms the existing "coarse Icp trim keyed to f_ref" mechanism
  (`spec/porting-plan.md` row 6/6a) scales to a finer granularity than the
  original six-code characterisation grid without any circuit change --
  useful precedent for #79's own still-open gap, which this record does
  not itself attempt to close (a different operating-point tuple, per
  issue #83's own "Why this is not the same issue as #79").

**What remains open / accepted**:

- Issue #79's `band=00, low interval, f_ref=4.5MHz` gap (0.87 deg short,
  full 3-bundle coverage) is untouched by this record -- it is a different
  (band, interval, `f_ref`) tuple, filed and scoped separately.
- The 12 other partial-PVT-coverage combinations `RECORD-002` flagged (only
  1-2 of 3 bundles simulated) remain partially covered; this record does
  not extend that coverage.
- A full per-`f_ref` trim-selection table (mapping every reachable (band,
  interval, `f_ref`) tuple to its required trim code, the way
  `gf180-pll DR-006` Decision 5 does) is **not** built here -- this record
  adds exactly the one entry issue #83 needs. A future record could
  generalise this into the same kind of load-bearing per-`f_ref` rule
  gf180-pll's own `DR-006` documents, if the remaining partial-coverage
  gap is worked further.
- The still-undesigned Icp reference-current generator
  (`spec/decision-records/DR-006-cp-cascode-bias-replica.md` "Relationship
  to DR-002 Decision 1") now has one more concrete reference-current value
  (3.75 uA) it must be able to deliver at the `mos_ss`/125 C corner, in
  addition to the original six -- not a new category of requirement, but a
  finer one.
