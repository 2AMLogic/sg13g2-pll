# DR-008: an 11 uA `cp` Icp-trim code closes the `band=00, low, f_ref=4.5MHz` PM gap

- **Status**: proposed
- **Date**: 2026-08-31
- **Decided by**: Builder agent, issue #79
- **Related**: #16 (parent, epic), #79 (this issue), #41 / DR-006
  (`spec/decision-records/DR-006-loop-filter-r1-resize.md`, the R1 resize
  this gap was found against), #83 / DR-007
  (`spec/decision-records/DR-007-cp-icp-trim-fine-code-band00-mid-fref4p5.md`,
  the SAME mitigation *mechanism* -- a fine Icp-trim code -- applied to a
  DIFFERENT (band, interval, `f_ref`) tuple; that record's own methodology
  is reused here, not superseded), `spec/decision-records/DR-006-cp-cascode-bias-replica.md`
  (confirms `cp`'s `IBP`/`ICP`/`IBN`/`ICN` pins are current inputs so any
  reference-current value is a legitimate operating point, not a hardware
  modification)
- **Consumes**: `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  (the gap this record closes), `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`
  and `sim/sg13cmos5l-cp-icp-trim/records/RECORD-004-issue79-finetrim-icp.md`
  (the evidence this record cites)

## Context

`sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
re-verified the resized `loop_filter` (DR-006, `R1` ~x44.2) across the full
amended `f_ref` range and found one operating point, `band=00`, low `Kvco`
interval, `f_ref` = 4.5 MHz (reachable at **all three** PVT bundles,
`n_div` = 127/114/103 for fast/typ/slow), where **no code in the existing
six-code Icp-trim ladder** (2.5, 5, 10, 20, 40, 80 uA) meets both stability
criteria (`f_c < f_ref/10`, PM >= 45 deg) simultaneously at every bundle:
at 10 uA, `typ` (47.624 deg) and `slow` (52.226 deg) both pass, but `fast`
(the binding bundle) is `pm_deg` = 44.127, **0.87 deg short** of the 45 deg
floor while `fc_hz` = 3.459239e5, comfortably under the 4.5e5 Hz ceiling;
at 20 uA, PM clears at every bundle (54.429/56.764/58.798 deg) but `fc_hz`
exceeds the ceiling at **all three** (5.833e5/6.225e5/7.217e5 Hz). Filed as
issue #79.

`spec/porting-plan.md` row 6/6a ports the *mechanism* behind this ladder as
a "coarse Icp trim keyed to f_ref, not a filter redesign", and, as
established by `DR-007`, the six-code ladder is a *characterisation grid*,
not a hardware-fixed set of legal values -- any reference-current magnitude
a (not-yet-drawn) bias generator could someday deliver is a legitimate
operating point to measure and, if useful, to program.

## Decision

**A new Icp-trim code, 11 uA, is added to the trim table, measured for all
three PVT bundles** (`mos_ff/-40C`, `mos_tt/27C`, `mos_ss/125C`, all at
3.3 V -- the only three points reachable at the `band=00, low interval,
f_ref=4.5MHz` tuple, per `RECORD-002`). This is a **value** addition to the
trim table, not a geometry change: `R1`/`C1`/`C2` are untouched, and no
other trim code, PVT bundle, or (band, interval, `f_ref`) combination is
affected. It is a **separate** code from issue #83's own 3.75 uA addition
(DR-007) -- a different (band, interval, `f_ref`) tuple with a different
binding-bundle structure (see "Why a fine code, and why 11 uA specifically"
below).

Real-subckt measurement, real `cp` block into the real resized
`loop_filter` (not lumped), all three PVT bundles, at `Icp` = 11 uA:

| `pvt_bundle` | `icp_a` | `fc_hz` | `pm_deg` | `meets_ceiling` | `meets_pm45` |
|---|---|---|---|---|---|
| fast | 1.100049e-05 | 3.686111e+05 | 45.592 | yes (18.1% headroom) | yes (0.592 deg margin) |
| typ | 1.100050e-05 | 3.851478e+05 | 49.043 | yes (14.4% headroom) | yes (4.043 deg margin) |
| slow | 1.100077e-05 | 4.352370e+05 | 53.454 | yes (3.28% headroom) | yes (8.454 deg margin) |

**All three criteria clear, real subckt, real margin** (not estimated) --
see `sim/sg13cmos5l-cp-icp-trim/records/RECORD-004-issue79-finetrim-icp.md`
and `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`
for the full evidence, including the real-subckt scan that established the
feasible Icp window's own bounds.

**A part built to this design and operated at `f_ref` = 4.5 MHz in
`band=00`, `Kvco` low interval, must be trimmed to the 11 uA code**, in
addition to the 3.75 uA code DR-007 documents for the `band=00, mid
interval, f_ref=4.5MHz` tuple -- both are entries in the same not-yet-fully-
built per-`f_ref` trim-selection table `spec/porting-plan.md` row 6/6a's
mechanism anticipates.

### Why a fine code, and why 11 uA specifically

Unlike issue #83's gap (a single binding PVT bundle, `slow`, with the two
nearest existing codes bracketing a wide feasible window), this gap's
existing-ladder failure is structurally different: `fast` fails PM at
10 uA while `typ`/`slow` already pass, and at 20 uA **all three** bundles
fail the `fc` ceiling. A real-subckt scan (documented in full in
`sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`
"Why 11 uA") found the feasible Icp window bounded by **two different
bundles at each edge**: `fast`'s PM=45 deg floor near 10.6 uA (below
that, `fast` fails PM), and `slow`'s `fc`=450 kHz ceiling near 11.47 uA
(above that, `slow` fails the ceiling) -- a window only ~0.85 uA wide, far
narrower than issue #83's own bracket. 11 uA sits close to this window's
own arithmetic midpoint (~11.05 uA), giving the most balanced real margin
achievable on both binding constraints from an Icp-trim-code change alone.

## Alternatives considered

- **A joint `R1`/`C1`/`C2` re-tune** -- rejected for this gap specifically,
  for the same reason DR-007 rejected it for issue #83's gap: `RECORD-002`
  ("Why x44.2, not x20") already found PM margin non-monotonic in `R1`
  scale across the amended matrix -- pushing `R1` further to widen this
  one tuple's Icp window risks reopening a currently-passing point
  elsewhere in the 30-combination matrix, for a problem the existing Icp
  reference-current mechanism already solves (if narrowly) with zero
  geometry risk. A wider window via `R1`/`C1`/`C2` retuning remains
  available as future work if a later operating point needs it and an
  Icp-only fix cannot reach it -- not needed here.
- **Frequency-planning narrowing** (excluding `band=00, low interval,
  f_ref~4.5MHz` from the design's practical operating range) -- not
  pursued: unnecessary once the existing trim mechanism, used at a finer
  granularity, closes the gap outright with real (if narrow) margin at
  every bundle, not a shortfall that would justify narrowing the ratified
  range instead.
- **Accepting the 0.87 deg shortfall as within model/process uncertainty**
  -- not needed: the fix is cheap (one additional characterisation point,
  no geometry change) and closes the gap with real, measured margin rather
  than documented uncertainty, which is strictly better evidence for this
  repo's own "no claim without a testbench" standard.
- **A code with wider margin than 11 uA** -- not achievable: the scan in
  `RECORD-004` (loop-bandwidth-pm) shows the feasible window itself is only
  ~0.85 uA wide (bounded above by `slow`'s ceiling, below by `fast`'s PM
  floor), so no single code offers both a large PM margin for `fast` and a
  large `fc` headroom for `slow` simultaneously. 11 uA (near the window's
  own midpoint) is the best simultaneously-achievable balance from this
  one-dimensional mitigation; a code closer to either edge would trade
  more margin on one bundle for less on the other, not gain margin
  overall.

## Consequences

**What becomes possible**:

- `spec/porting-plan.md` row 6/6a's accounting improves from "16 of 17
  full-3-bundle-coverage regions plus 12 of 13 partial-coverage regions
  pass, 2 outright failures across the full 30-combination matrix"
  (`RECORD-002`'s own "Full accounting, all 30 combinations", after DR-007
  had already closed one of the two) to **zero remaining outright
  failures**: both of the two (band, interval, `f_ref`)
  tuples `RECORD-002` identified as failing at every existing trim code
  (`band=00/mid/f_ref=4.5MHz`, DR-007; `band=00/low/f_ref=4.5MHz`, this
  record) now pass with real, PVT-real-subckt margin, real, not estimated,
  at every bundle reachable at that tuple.
- Establishes that the "coarse Icp trim keyed to f_ref" mechanism
  (`spec/porting-plan.md` row 6/6a) can close a gap even when the
  feasible Icp window is narrow and bounded by different PVT bundles at
  each edge -- a harder case than DR-007's own single-bundle-bound gap,
  and useful precedent that a fine-trim-code mitigation does not require a
  wide bracket to be viable, provided the real-subckt scan is run to find
  the window's actual edges rather than assumed from the coarse ladder.

**What remains open / accepted**:

- The 12 partial-PVT-coverage combinations `RECORD-002` flagged (only 1-2
  of 3 bundles simulated) remain partially covered; this record does not
  extend that coverage.
- A full per-`f_ref` trim-selection table (mapping every reachable (band,
  interval, `f_ref`) tuple to its required trim code, the way
  `gf180-pll DR-006` Decision 5 does) is **not** built here -- this record
  adds exactly the one entry issue #79 needs, alongside DR-007's own entry
  for issue #83. A future record could generalise both into the same kind
  of load-bearing per-`f_ref` rule gf180-pll's own `DR-006` documents, if
  the remaining partial-coverage gap is worked further.
- The still-undesigned Icp reference-current generator
  (`spec/decision-records/DR-006-cp-cascode-bias-replica.md` "Relationship
  to DR-002 Decision 1") now has two more concrete reference-current values
  it must be able to deliver (3.75 uA at `mos_ss`/125 C; 11 uA at
  `mos_ff`/-40C, `mos_tt`/27C, and `mos_ss`/125 C), in addition to the
  original six -- not a new category of requirement, but a finer one, and
  one whose two entries are now both narrower-margin than the original
  six-code ladder's own headroom, worth keeping in mind for that
  generator's own design tolerance budget.
