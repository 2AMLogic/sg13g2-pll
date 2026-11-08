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
  (line 268, in-window `LOCK` rail is `lo`; that record is the pre-fix block
  that chattered, so it is the weakest citation); the current-topology polarity
  evidence `sim/sg13cmos5l-lock-detector-window/corners/ladder_hystfix.csv`
  (`in_window_lock_rail` = `lo` at 21/21) and
  `sim/sg13g2-lock-detector-window/records/RECORD-001-resized-window-hysteresis-chatter.md`
  (`lo` at 21/21 and 36/36); DR-006's measured 3.5 / 24.4 MHz table (from
  RECORD-003, `mos_tt`/`res_typ`/27 C only)

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

### 1. `lock_detector` supported `f_ref` range: 3.5 to 50 MHz

DR-005's `f_ref` range is amended **for the `lock_detector` block only** (a
reused block, consumer 2AMLogic/sg13g2-lc-pll) from 3.5 to 24.4 MHz to
**3.5 to 50 MHz**. The PLL's own reference-input range (`spec/target-spec.md`
and `spec/porting-plan.md` row 2) **stays 3.5 to 24.4 MHz**; those rows only
note the `lock_detector` extension. The 3.5 MHz floor and the DR-005 derivation
of the 24.4 MHz figure (VCO ceiling 1562.0 MHz over N = 64) are not touched by
this record.

The PLL as a whole cannot lock above 24.4 MHz under the current rows: row 1
(`f_vco` <= 1562.0 MHz) and row 3 (N >= 64) force `N x f_ref` <= 1562.0 MHz, so
`f_ref` <= 24.4 MHz (50 MHz x 64 = 3.2 GHz is out of band). This is arithmetic
on rows 1 and 3, not an open question. Reaching a higher whole-PLL `f_ref`
would need a change to row 1 (faster VCO band) or row 3 (smaller N), which is
its own decision record and is not made here.

### 2. DR-006 restated for 3.5 to 50 MHz

DR-006's disposition stands for the extended range: the `f_ref`-dependent
threshold is an accepted property of this topology, stated and not hidden. A
consumer treats the thresholds as `f_ref`-dependent fractions of `T_ref`, not
a fixed phase-error number. What changes is the **number** accepted: the
`mos_tt`/`res_typ`/27 C figure of 12 to 37 % does not describe the block over
PVT or at 50 MHz, so the band below replaces it as the pass/fail criterion.

**Decision 2 and Decision 3 are in tension** (see the Decision 3 feasibility
note): the DR-006 topology is re-accepted as a disclosure of its `f_ref`
dependence, **not** as a claim that it can land in the Decision 3 band. If the
band proves unreachable with the accepted `XRPU`/`XMPD` integrator, meeting it
reopens the reference-gated alternative that DR-006 rejected as "a different
block" and a superseding record is owed (Decision 3).

### 3. Numeric trip band, % of `T_ref`, for 3.5 to 50 MHz, all PVT corners (a target)

| Trip | Lower bound | Upper bound |
|---|---|---|
| Assert (lock declared) | 11 % of `T_ref`, and not below the 2.5 ns window floor (12.5 % at 50 MHz) | 25 % of `T_ref` |
| De-assert (lock lost) | 18 % of `T_ref` | 37 % of `T_ref` |

Plus, at every corner: de-assert is above assert by at least 25 % of the
comparator window (row 16 hysteresis, unchanged), and no chatter (unchanged).
The assert and de-assert ranges overlap (assert up to 25 %, de-assert from
18 %); they are only consistent together with this per-corner hysteresis
constraint. At 50 MHz with a window near 2.5 ns it is about 0.63 ns, about 3 %
of `T_ref`.

**Basis, stated honestly.**

- The edges are the **single-corner** `mos_tt`/`res_typ`/27 C values at the
  two range ends (assert 11.7 to 24.4 %, de-assert 18.7 to 36.6 % at 3.5 and
  24.4 MHz, RECORD-003), rounded outward by under one point. They are **not** an
  all-PVT span.
- The committed 21-corner ladder
  (`sim/sg13cmos5l-lock-detector-window/corners/ladder_hystfix.csv`, RECORD-003
  topology, pre-bodyfix netlist) spans **assert 6.1 to 46.0 %** and
  **de-assert 12.3 to 58.3 %** of `T_ref` at 3.5 to 24.4 MHz. 9 of 21 corners
  fall outside the band. At 3.5 MHz alone the assert trip spans 6.1 to 22.3 %
  (about 3.6x) against a band that allows 2.3x.
- Two corners have de-assert above 50 % of `T_ref` at 24.4 MHz (`mos_ss`/
  `res_bcs`/125 C 57.5 %; `mos_tt`/`res_bcs`/125 C 58.3 %), so lock-lost is
  unreachable inside |phi| <= `T_ref`/2 there. The block therefore **does not
  meet the proposed band across PVT today at 3.5 to 24.4 MHz**, as well as at
  50 MHz (nominal trips 38 to 39 % / 49.9 %; lock-lost unreachable in 24 of 45
  corners). The existing range is not already covered by the band; #302 must rework
  inside the existing range too, not only at 50 MHz.
- RECORD-005/006 (the current committed netlist, `rhigh` body on VSS) are
  nominal only, so small shifts from the 21-corner figures are possible.

Justification for the edges:

- **The 37 % upper bound on de-assert leaves 13 points of `T_ref`** (2.6 ns at
  50 MHz) below `T_ref`/2, so the lock-lost trip is reachable inside the
  largest phase error the PFD presents.
- **The window floor sets the lower assert edge at 50 MHz.** 2.5 ns is 0.9 % of
  `T_ref` at 3.5 MHz, so it does not bind there, but it is 12.5 % at 50 MHz.
  Row 16 requires the 2.5 ns assert window and this record does not relax it.

**Feasibility is not shown, and looks unlikely for the accepted topology.**
Nothing was simulated for this record. A derivation (not a measurement) from
DR-006's relation `assert ~ t_win + k x T_ref`, with `k` about 8 to 9 %
nominal:

1. Assert >= 11 % at 3.5 MHz needs `k` >= about 8 to 10 % at every corner.
2. Assert <= 25 % at 50 MHz with `t_win` >= 2.5 ns needs `t_win + k x 20 ns`
   <= 5 ns, so `t_win` <= about 3 ns and `k` <= about 12.5 % at every corner.
3. So `t_win` (an inverter-chain delay) would have to hold to about 2.5 to
   3 ns and `k` to about +/-10 % over PVT.
4. Measured `t_win` spans 3.688 to 11.24 ns (about 3x) and `k` tracks
   `R(rhigh) x I_sat(XMPD)`, with `R` alone spanning 1.351 to 3.297 MOhm
   (about 2.4x). The widest measured window (11.24 ns) is 56 % of `T_ref` at
   50 MHz.

For the `XRPU`/`XMPD` integrator that Decision 2 re-accepts, the band therefore
looks unreachable by sizing alone. **Expectation: #302 needs a topology
change, e.g. the reference-gated integrator DR-006 rejected as "a different
block". If so, DR-006's rejected alternative is reopened and a superseding
record is owed.** The alternative is to re-derive a band (or a per-`f_ref`
band) from the corner data with stated physical justification; the band is new
and not previously ratified, so widening it is not a relaxation of the spec.
Either way the 2.5 ns floor, hysteresis and no-chatter targets are not
loosened to make results pass, and #302 comes back with a superseding record
rather than silently missing the band.

### 3a. Netlist the band governs

The band and the polarity evidence above come from the **target flavor**,
`design/sg13cmos5l/netlist/lock_detector.spice` (`XRPU` l=700u, `XMPD` l=16u,
MOM cap). The 50 MHz report on #296 measured the **SG13G2 sizing**,
`design/netlist/lock_detector.spice` (`XRPU` l=500u, `sub!` body, `XMPD`
l=12u, MIM-type cap). Topology and the `schmitt_hv` stage are the same in both.
The band is a requirement on the block, so **both flavors are graded against
it**; #302 and #303 must state which netlist each result is for, and the
operator confirms which one sg13g2-lc-pll consumes (not established here).

The "window >= 2x worst static phase offset" half of row 16 stays unmeasured
(`spec/target-spec.md` R-2) and this record does not change it.

### 4. LOCK polarity contract: active-low, as netlisted

`LOCK` is **active-low**: `LOCK` = 0 means locked (phase error inside the
assert threshold); `LOCK` = VDD means not locked. No output inverter is
added. The pin keeps the name `LOCK` to avoid netlist and schematic churn
outside this issue; consumers must read it as active-low.

Why:

- It is the behaviour every existing record measured. For the current topology,
  `ladder_hystfix.csv` has the in-window `LOCK` rail `lo` at 21/21 corners and
  `sg13g2-lock-detector-window` RECORD-001 has it at 21/21 and 36/36; the
  netlist agrees (in lock `WIDE` = 0, `XMPD` is off, `XRPU` charges `VWIN` to
  VDD, and the inverting `schmitt_hv` drives `LOCK` low; at power-up `VWIN` is
  discharged so `LOCK` = VDD, not locked, a safe default). The pre-fix
  RECORD-001 line 268 (`lo` at 92/92) agrees but is the weakest citation, since
  that block chattered. The 50 MHz re-grade also agrees. Nothing measured at
  3.5 to 24.4 MHz is invalidated.
- **Departure from the parent.** `2AMLogic/gf180-pll` `design/lock_detector.sch`
  is active-high: its Schmitt drives `LOCKB` and an inverter `XILK` gives
  `LOCK` (power-on `LOCK` = 0). The SG13G2 port dropped `XILK`. Dropping it is
  now a deliberate contract, not an accident of the port.
- Adding an inverter changes the output stage that RECORD-003 (hysteresis),
  RECORD-004 (crowbar current) and RECORD-005 sized and measured, and adds
  delay and current to a block whose rework (#302) already has to move the trip
  points. It is more change for the same information.
- Nothing in the ratified spec demands active-high. A consumer wanting
  active-high adds an inverter at its own boundary.
- **Integration risk, stated.** Public lock-detect outputs surveyed in the
  market review (TI LMX2572, CDCE62005) are high when locked, and an active-low
  signal would usually be named `LOCK_N`/`LOCKB`. The pin here is called `LOCK`
  and reads 0 when locked. A chip-level wrapper or `pll_top` (none exists yet)
  should either export the signal as `LOCK_N`/`LOCKB` or invert it so the
  product pin is active-high. Until then the `*.opin LOCK` note in the source
  schematic should say "(active-low)".

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
  chosen; one band over the whole range is simpler. (The existing
  single-corner span does not make the band safe over PVT, see Decision 3. A per-`f_ref` band is the fallback named there if the single
  band proves unreachable.)

## Consequences

- #302 reworks `lock_detector` to land both trips inside the Decision 3 band
  over PVT at **both** 50 MHz (45 corners) **and** the existing 3.5 to 24.4 MHz
  range (where 9/21 committed corners are outside today). A topology change and
  a superseding record are likely (Decision 3). #303 benches it. Neither is
  started by this record.
- `spec/target-spec.md` and `spec/porting-plan.md` f_ref row 2 and row 16 are
  amended as this record directs; every edit cites DR-011. The row 16 measured
  figure (12 to 37 % over 3.5 to 24.4 MHz) is left as the measurement it is,
  next to the new band.
- Gate G5 of 2AMLogic/sg13g2-lc-pll can close only after this record is
  ratified (EE key, market key, then operator) and #302/#303 land. Until then
  nothing here counts as ratified.
- The whole PLL stays at 3.5 to 24.4 MHz (Decision 1). Reaching a higher
  whole-PLL `f_ref`, including the common 25 MHz reference value (the PLL tops
  out 2.4 % below it, predating this record, DR-005), needs a row 1 or row 3
  change under its own record; the operator ruling on #296 should cover it.
- DR-005 is not edited to point forward to this record while both are
  `proposed`; add an "amended by DR-011" line at ratification so a reader of
  DR-005 alone does not take 24.4 MHz as the lock-detector limit.
- The measured 50 MHz figures are the sg13g2-lc-pll authors' simulations as
  reported on #296; this record did not read or re-run them. If #303 measures
  differently, the band's feasibility note applies.
- Bad consequence: the band is wide (a factor of about 2 on each trip), which
  is what the topology gives (DR-006), so a consumer still cannot treat the
  trips as a precise phase-error number.
