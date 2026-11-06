# DR-011: extend `f_ref` to 50 MHz for `lock_detector`, set the trip band, and state LOCK polarity (active-low)

- **Status**: proposed
- **Date**: 2026-11-06
- **Decided by**: Builder agent, issue #301 (operator ruling r7-q30 on #296,
  option 2). Not ratified: ratification needs the EE key, the market key, then
  the operator, tracked on #296. Agents do not mark this record ratified.
- **Related**: #296 (parent, operator ruling), #301 (this issue), #302
  (`lock_detector` rework, graded against the band below), #303 (full-PVT
  50 MHz bench), DR-005 (amended here), DR-006
  `lock-detector-fref-dependent-threshold` (restated here), Gate G5 of
  2AMLogic/sg13g2-lc-pll
- **Consumes**: `spec/target-spec.md` row 16;
  `sim/sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md`
  (line 268, in-window `LOCK` rail is `lo`); DR-006's measured 3.5 / 24.4 MHz
  table (from RECORD-003)

---

## Context

DR-005 ratifies (proposed status; see `spec/target-spec.md` R-0) an `f_ref`
range of 3.5 to 24.4 MHz. DR-006 accepts the `T_ref`-proportional lock
threshold of `lock_detector` only inside that range, where it measured
11.7 to 24.4 % of `T_ref` (assert) and 18.7 to 36.6 % (de-assert), about
12 to 37 % overall (`spec/target-spec.md` row 16).

Two things changed (#296):

1. **sg13g2-lc-pll targets a 50 MHz reference.** Its Gate G5 cites this
   block's 3.5 to 24.4 MHz range. `REUSE.md` says a block is designed once, so
   the supported range is extended rather than forking a second lock
   detector.
2. **A re-grade at 50 MHz** (reported on #296 from sg13g2-lc-pll
   `sim/lock-detector/`; simulated, pre-layout, not re-run for this record)
   found the nominal-corner trips at about 38 to 39 % of `T_ref` (lock
   asserts) and 49.9 % (lock lost). Over 45 corners at 3.3 V the assert trip
   spans 24.9 to 49.6 %, and in 24 of the 45 the lock-lost trip is not
   reachable inside |phi| <= `T_ref`/2. The same report found `LOCK` is low
   when locked as netlisted, with no polarity statement anywhere in `spec/` or
   `design/README.md`. The window floor itself passes (>= 2.70 ns against the
   2.5 ns floor).

Terms used below, to avoid the active-low ambiguity: **assert** = the block
declares lock (phase error falls inside the threshold); **de-assert** = the
block declares lock lost. Thresholds are phase-error magnitudes in % of
`T_ref`.

## Decision

### 1. Supported `f_ref` range: 3.5 to 50 MHz

DR-005's `f_ref` range is amended, for `lock_detector` and for the f_ref row of
`spec/target-spec.md` / `spec/porting-plan.md`, from 3.5 to 24.4 MHz to
**3.5 to 50 MHz**. The 3.5 MHz floor and the DR-005 derivation of the 24.4 MHz
figure (VCO ceiling 1562.0 MHz over N = 64) are not touched by this record.

**Open and not decided here:** with the DR-005 VCO band (445.3 to 1562.0 MHz)
and N in [64, 127], `f_out = N x f_ref` cannot reach 50 MHz x 64 = 3.2 GHz.
This record extends the range the *lock detector* is specified over. Whether
the PLL as a whole can lock at f_ref above 24.4 MHz is a separate question
(it needs a smaller N or a faster VCO band) and is not settled here; the
ratifiers should rule on it with #296.

### 2. DR-006 restated for 3.5 to 50 MHz

DR-006's disposition stands for the extended range: the `f_ref`-dependent
threshold is an accepted property of this topology, stated and not hidden. A
consumer treats the thresholds as `f_ref`-dependent fractions of `T_ref`, not
a fixed phase-error number. What changes is the **number** accepted: the
measured 12 to 37 % no longer describes the block at 50 MHz, so the band
below replaces it as the pass/fail criterion.

### 3. Numeric trip band, % of `T_ref`, for 3.5 to 50 MHz, all PVT corners

| Trip | Lower bound | Upper bound |
|---|---|---|
| Assert (lock declared) | 11 % of `T_ref`, and not below the 2.5 ns window floor (12.5 % at 50 MHz) | 25 % of `T_ref` |
| De-assert (lock lost) | 18 % of `T_ref` | 37 % of `T_ref` |

Plus, at every corner: de-assert is above assert by at least 25 % of the
comparator window (row 16 hysteresis, unchanged), and no chatter (unchanged).

Justification:

- **Lower and upper edges come from the measured span**, rounded outward by
  under one point: assert 11.7 to 24.4 %, de-assert 18.7 to 36.6 % at
  3.5 to 24.4 MHz. A rework that lands in this band keeps the existing range
  unregressed by definition, and the 3.5 and 24.4 MHz ends need no new
  tolerance.
- **The 37 % upper bound on de-assert leaves 13 points of `T_ref`** (2.6 ns at
  50 MHz) below `T_ref`/2, so the lock-lost trip is reachable inside the
  largest phase error the PFD presents. The 50 MHz report shows this is the
  failing property today (49.9 % nominal, unreachable in 24 of 45 corners).
- **The window floor sets the lower edge at 50 MHz.** 2.5 ns is 0.9 % of
  `T_ref` at 3.5 MHz, so it does not bind there, but it is 12.5 % at 50 MHz.
  Row 16 requires the 2.5 ns assert window and this record does not relax it.
- **Feasibility is not shown.** The band is a target set from measurements
  at 3.5 to 24.4 MHz and the 50 MHz report. Nothing was simulated for this
  record. The widest comparator window measured on this PDK (11.24 ns,
  DR-006 context) is 56 % of `T_ref` at 50 MHz, so #302 may find the window
  spread itself has to narrow to fit. If so, #302 comes back with a
  superseding record; the floor and the band are not loosened to make results
  pass.

The "window >= 2x worst static phase offset" half of row 16 stays unmeasured
(`spec/target-spec.md` R-2) and this record does not change it.

### 4. LOCK polarity contract: active-low, as netlisted

`LOCK` is **active-low**: `LOCK` = 0 means locked (phase error inside the
assert threshold); `LOCK` = VDD means not locked. No output inverter is
added. The pin keeps the name `LOCK` to avoid netlist and schematic churn
outside this issue; consumers must read it as active-low.

Why:

- It is the behaviour every existing record measured: RECORD-001 line 268 reads
  the in-window rail as `lo` at all 92 points, and the 50 MHz re-grade agrees.
  Nothing measured at 3.5 to 24.4 MHz is invalidated.
- Adding an inverter changes the output stage that RECORD-003 (hysteresis),
  RECORD-004 (crowbar current) and RECORD-005 sized and measured, and adds
  delay and current to a block whose rework (#302) already has to move the trip
  points. It is more change for the same information.
- Nothing in the ratified spec demands active-high. A consumer wanting
  active-high adds an inverter at its own boundary.

This is not a PO-level call (no policy or cost trade-off beyond the
reversibility below), so it is recorded here rather than routed through
`operator-decision`. Reversal is cheap: a superseding record plus one
inverter, if the ratifiers prefer active-high.

The contract is stated in `spec/target-spec.md` row 16 and in
`design/README.md`, each citing this record.

## Alternatives considered

- **Keep 3.5 to 24.4 MHz (#296 option 1).** The Curator recommended it; the
  operator ruled option 2 instead, and sg13g2-lc-pll needs the 50 MHz
  reference. Not chosen.
- **Fork a separate 50 MHz lock detector in sg13g2-lc-pll.** Violates the
  design-once reuse rule and leaves two blocks to maintain. Not chosen.
- **Add an output inverter to make `LOCK` active-high.** Valid, but invalidates
  the measured output-stage records and costs delay and current for no
  spec-driven benefit (see Decision 4). Not chosen now; remains available via a
  superseding record.
- **Relax the 2.5 ns window floor to fit 50 MHz.** Rejected outright: agents do
  not relax the ratified spec, and the floor passes (>= 2.70 ns) so there is no
  reason to.
- **A per-frequency band (a different % at each `f_ref`).** More precise but
  gives the rework no single pass/fail and a consumer a table to carry. Not
  chosen; one band over the whole range is simpler and the existing span already
  fits inside it.

## Consequences

- #302 reworks `lock_detector` to land both trips inside the Decision 3 band in
  all 45 PVT corners at 50 MHz without regressing 3.5 to 24.4 MHz. #303 benches
  it. Neither is started by this record.
- `spec/target-spec.md` and `spec/porting-plan.md` f_ref row 2 and row 16 are
  amended as this record directs; every edit cites DR-011. The row 16 measured
  figure (12 to 37 % over 3.5 to 24.4 MHz) is left as the measurement it is,
  next to the new band.
- Gate G5 of 2AMLogic/sg13g2-lc-pll can close only after this record is
  ratified (EE key, market key, then operator) and #302/#303 land. Until then
  nothing here counts as ratified.
- The whole-PLL question in Decision 1 (N and VCO band at f_ref above
  24.4 MHz) is left open and is now visible to the ratifiers.
- The measured 50 MHz figures are the sg13g2-lc-pll authors' simulations as
  reported on #296; this record did not read or re-run them. If #303 measures
  differently, the band's feasibility note applies.
- Bad consequence: the band is wide (a factor of about 2 on each trip), which
  is what the topology gives (DR-006), so a consumer still cannot treat the
  trips as a precise phase-error number.
