# RECORD-005: real mitigated-`cp` Part B re-run — static phase error barely moves despite a 20x DC-mismatch fix

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #72 (Part of #16) — the design-level mitigation
  `RECORD-004`'s own "Decision" section asked for (tighten `cp`'s `up`/`dn`
  current-mirror matching), now re-run against the REAL mitigated `cp`
  (`design/sg13cmos5l/cp.sch` + `spec/decision-records/DR-006-cp-cascode-bias-replica.md`)
  rather than `RECORD-004`'s ideal, diagnostic-only substitution.
- **This record does not edit `RECORD-001`/`RECORD-002`/`RECORD-003`/`RECORD-004`**
  (append-only, per this directory's own convention).
- **DUT**: the same six real subckts as `RECORD-001`/`RECORD-003`/`RECORD-004`
  ("real" here meaning transistor-level, not the ideal behavioural
  substitution `RECORD-004` used), wired at the testbench level exactly as
  `RECORD-001` describes, with ONE change: `cp` is now
  `../netlist-snapshots/cp_cascbias.spice` — the MITIGATED, transistor-level
  block, frozen from `design/sg13cmos5l/netlist/cp.spice` at commit
  `d54ff69` (issue #72's own `cp.sch` change — see that snapshot's own
  provenance header). `pfd` is the `#56`-corrected frozen snapshot
  `RECORD-003`/`RECORD-004` both used; `loop_filter`, `vco`,
  `divider_chain`, `lock_detector` are byte-identical to `RECORD-001`'s own
  frozen snapshots. The as-drawn `../netlist-snapshots/cp.spice` and every
  prior script in this directory are untouched, so `RECORD-001`…`RECORD-004`
  reproduce unchanged.
- **Testbench**: `../testbench/run_closed_loop_cascbias.sh` +
  `../testbench/tb_pll_proposal_cascbias.sp.tmpl` (new, issue #72). The
  ONLY interface difference from `RECORD-003`'s own Part B deck
  (`tb_pll_proposal.sp.tmpl`): `cp`'s `IBP`/`ICP`/`IBN`/`ICN` are current-input
  pins now (issue #72's own change), so this deck drives them with four
  ideal `@IREF@`-derived current sources (`10 uA` mirror-bias branches, the
  cascode-bias branches taken from the same reference per DR-006) in place
  of `tb_pll_proposal.sp.tmpl`'s testbench-local `XMREF*` voltage-bias
  replica. Duration (`TSTOP=2500n`), averaging window (`TAVG0=2000-2500n`),
  PVT point (`mos_tt`/`res_typ`/27 C/3.3 V, per `../corners/matrix.md`'s
  own single-point rationale — unchanged here), initial condition
  (`VC0=2.46`), and every ideal-capacitor substitution are IDENTICAL to
  `RECORD-003`'s own Part B deck and `RECORD-004`'s own diagnostic, so all
  three traces are directly comparable at the same timestamps.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_closed_loop_cascbias.sh`.
  Writes `../corners/lock_trace_proposal_cascbias.csv` (49 reference cycles,
  same count as `RECORD-003`/`RECORD-004`). **Run twice this session, back
  to back, to confirm determinism before trusting the numbers below**: both
  runs produced a byte-for-byte identical 49-row CSV. **Runtime on this
  host, this session: ~7.4 minutes wall** (2.5 us at this six-block
  netlist's rate; faster than `RECORD-003`'s own ~26 minute x86-64-Linux
  Part B figure for the as-drawn `cp`, consistent with the mitigated `cp`'s
  own six extra bias devices being small relative to `pfd`/`vco` staying the
  dominant transistor-level cost either way — the difference is host-load
  variance, not attributed to the design change).

## Result: the static phase error moves from 9.176% to 8.203% — NOT the collapse the DC-mismatch fix predicted

Over the final 20 cycles (`t` > 1.5 us, identical window to
`RECORD-003`/`RECORD-004`):

| Quantity | `RECORD-003` baseline (as-drawn `cp`) | `RECORD-004` diagnostic (ideal, exactly-equal `cp`) | This record (REAL mitigated `cp`) |
|---|---|---|---|
| `vctrl`: IC -> final | 2.46 V -> 2.387 V | 2.46 V -> 2.38696 V | 2.46 V -> 2.38712 V |
| `vc_avg` (2.0-2.5 us) | 2.387 V (range 2.349-2.420 V) | 2.387128 V | 2.386934 V (range 2.350095-2.416685 V) |
| `i_cp` (2.0-2.5 us) | -24.66 uA | 0 uA (ideal source, by construction) | **-39.26 uA** |
| Reference cycles observed | 49 | 49 | 49 |
| `Delta f/f_ref`, final 20 cycles | -0.0293% to +0.0068%, mean -0.0049% | -0.01317% to +0.00054%, mean ~0% | -0.00900% to +0.01250%, **mean -0.00020%** |
| Static phase error, final 20 cycles | 9.110% to 9.196%, **mean 9.176%** | -0.02784% to +0.00054%, **mean -0.00235%** | 8.200% to 8.221%, **mean 8.203%** |
| Longest continuous run meeting the full dual-lock criterion (both `|Delta f/f_ref| < 1%` AND `|phase error| < 5%`) | 4 cycles (`t` = 50-200 ns) | 41 cycles, `t` = 450 ns to end (2.45 us), continuous | **4 cycles (`t` = 100-250 ns)** |
| Longest continuous run meeting the freq-lock criterion alone (`|Delta f/f_ref| < 1%`) | not separately tabulated | not separately tabulated | 42 cycles, `t` = 400 ns to end (2.45 us), continuous |
| `lock_time` (row-7 definition: first cycle of a >=20-consecutive-cycle dual-lock run) | `None` | 450 ns | **`None`** |

**Frequency lock is, if anything, slightly tighter than the as-drawn
baseline** (final-20-cycle spread 0.0215 percentage points here vs. 0.0361
in `RECORD-003`), and is rock-solid from `t` = 400 ns onward (42 consecutive
cycles, zero drop-outs, ending only because the simulated window ends).
**The static phase error is a different story.** After the same initial
transient shape `RECORD-003`'s own trace shows (a dip to 1.56% at `t` =
100 ns before climbing), it settles to a **flat plateau at 8.20% of `T_ref`
by `t` ~ 1050 ns and never leaves that plateau for the rest of the 2.5 us
run** (peak-to-peak spread across the final 20 cycles: 0.021 percentage
points — even flatter than `RECORD-003`'s own 0.086-point spread). That
plateau is **only 0.97 percentage points below `RECORD-003`'s own 9.176%
baseline** — an ~11% relative reduction — against the ~20x reduction in the
DC-measured up/dn magnitude mismatch this same mitigation delivered
(`sim/sg13cmos5l-cp-icp-trim/records/RECORD-002`: 10.28% -> 0.72% worst-case
over the full PVT/`VOUT` matrix; -6.42% -> -0.298% at this exact operating
point, `mos_tt`/27 C/`VOUT` = 2.40 V). **The longest continuous dual-lock
run is unchanged at 4 cycles** — the same length `RECORD-003`'s own as-drawn
`cp` produced, not the 41-cycle unbroken run `RECORD-004`'s ideal
substitution produced. **Row 7's 5% threshold is not met.**

## Why the DC-mismatch fix did not close the gap `RECORD-004`'s diagnostic implied it would

This is the honest finding this record exists to report, not a result to
paper over. `RECORD-004`'s ideal substitution and this record's real
mitigated `cp` both target "the up/dn current-magnitude mismatch," and the
magnitude term is now confirmed (by `sim/sg13cmos5l-cp-icp-trim/RECORD-002`,
a real, transistor-level DC characterization of this exact mitigated block)
to be small at the loop's own operating point (-0.298% at `mos_tt`/27 C/
`VOUT` = 2.40 V, against -6.42% as-drawn). If DC magnitude mismatch were the
whole mechanism, this record's phase error should have collapsed toward
`RECORD-004`'s -0.00235% floor, roughly in proportion to the mismatch
reduction. It did not — it moved less than one order of magnitude less than
that.

**The likely explanation, stated as a candidate and not re-proven here**:
`RECORD-004`'s ideal substitution did not isolate DC magnitude alone. Its
behavioural `cp` replaced the ENTIRE block — comparator-gated ideal current
sources with infinite output impedance, no switch-turn-on/turn-off
dynamics, no charge injection or clock feedthrough from the real `SWO`/
`SWN`-class steering switches, and no leakage in the off state. Any of those
switching-time (dynamic) effects would show up in a real closed loop as a
per-cycle net charge injected onto `VOUT` asymmetrically between the `UP`
and `DN` phases — exactly the kind of static, per-reference-cycle offset a
type-II charge-pump PLL's phase detector would null out with a nonzero
steady-state phase error, the same way it nulls a DC magnitude mismatch.
`RECORD-002` (`sg13cmos5l-cp-icp-trim`) already flagged this gap explicitly,
twice, as something its own DC methodology cannot see: *"Switching
(dynamic) charge mismatch — unchanged from RECORD-001: every measurement
here is DC with the switches held static... The six new bias devices add
gate/junction capacitance on `IBP`/`ICP`/`IBN`/`ICN`, which is a dynamic
property this record cannot see."* This record's own measurement — a large,
real reduction in the DC-characterized mechanism producing only a small
reduction in the closed-loop symptom — is consistent with that flagged gap
being the dominant remaining term, not with the DC magnitude mismatch being
it. **This is stated as the most consistent candidate explanation given the
evidence in hand, not as a newly confirmed mechanism**: no diagnostic in
this record isolates switching charge mismatch the way `RECORD-004`'s
substitution isolated DC magnitude. Confirming it would need a targeted
follow-up (e.g. an ideal substitution that keeps real switch dynamics/timing
but forces equal charge per pulse, or a direct per-edge charge-injection
measurement on the mitigated block's `UP`/`DN` switches) — not attempted
here, and explicitly out of this record's own scope.

**A second, smaller, already-anticipated factor**: `i_cp` rises from
-24.66 uA (as-drawn, `RECORD-003`) to -39.26 uA (mitigated, this record) —
`DR-006`'s own "Consequences" section named this rise and attributed it to
the P-side bias replica moving out of the testbench's own `vddrep` supply
into the block's `vdd_cp` domain. This is a supply-current bookkeeping
change, not obviously a phase-error mechanism on its own (the block's
`UP`/`DN` output currents at the operating point are still the small,
matched values `RECORD-002` measures), but it is reported here as `DR-006`
promised, and flagged as a second candidate a future diagnostic should rule
in or out alongside switching charge mismatch before treating either as
settled.

## What this does not bound

- **Single PVT point only** (`mos_tt`/`res_typ`/27 C/3.3 V, same as
  `RECORD-001`-`RECORD-004`, see `../corners/matrix.md`). No corner sweep of
  this record's own number exists.
- **Part A (as-drawn, committed design) is not re-run here.** Issue #72's
  own Scope is Part B only; Part A's non-lock remains a separate question,
  now further complicated by two closed prerequisite issues whose own scope
  does not obviously cover the closed-loop testbench's specific
  `divider_chain` instantiation (issue #36, closed via PR #60, targeted a
  *standalone* `divider_chain` testbench with explicit `.ic` latch
  initialization — narrower than what this deck's real `divider_chain`,
  embedded without that initialization, exercises; the
  `divider-nrange-retiming` follow-up record separately found the committed
  design does not function as a divider at any tested corner). Neither is
  re-tested here; this record only touches Part B's proposal deck, per issue
  #72's own Scope.
- **The switching-charge-mismatch hypothesis above is not confirmed, only
  argued as the best-fitting candidate** given this record's own measured
  magnitude gap. No new diagnostic isolating it is run in this record.
- **The exact analytic gain from any residual mismatch (of whichever kind)
  to phase offset is still not derived** (`RECORD-003`'s/`RECORD-004`'s own
  caveat, unchanged here).
- **Row 7's own 5% static-phase-error threshold is not revisited here**
  (`RECORD-001`'s own re-derivation, unchanged) — this record neither
  loosens nor re-justifies it; the residual with the mitigated `cp` still
  fails it.
- **This record's `cp` substitution is the committed design**
  (`design/sg13cmos5l/cp.sch` after issue #72), unlike `RECORD-004`'s
  diagnostic-only ideal substitution — but the bias-current sources driving
  its `IBP`/`ICP`/`IBN`/`ICN` pins are still testbench-local ideal current
  sources, per `DR-006`'s own unchanged deferral of the reference-current
  generator (DR-002 Decision 1).

## Row-by-row disposition (updates `RECORD-001`'s/`RECORD-002`'s/`RECORD-003`'s/`RECORD-004`'s own call, does not edit them)

- **Row 7 (lock time)**: **still fails, for both the as-drawn AND the
  mitigated design.** The design-level mitigation issue #72 asked for
  (tighten `cp`'s current-mirror matching) is implemented and independently
  verified to work AS A DC-MISMATCH FIX (`sim/sg13cmos5l-cp-icp-trim/records/RECORD-002`:
  20x worst-case improvement), but the closed-loop static phase error it was
  expected to collapse only drops from 9.176% to 8.203% — an ~11% relative
  reduction, not the ~3,900x reduction `RECORD-004`'s idealized diagnostic
  showed for the same nominal mechanism. **Row 7's own dual-lock criterion
  is not met**: the longest continuous run is unchanged at 4 cycles.
  `RECORD-004`'s own causal attribution (DC up/dn magnitude mismatch is "the
  confirmed dominant mechanism") is **narrowed, not reversed, by this
  record**: it is confirmed as *a* mechanism whose complete idealized
  removal collapses the error, but this record's own measurement shows the
  REAL mitigated design's residual DC magnitude mismatch (already reduced to
  -0.298% at the operating point) is not the dominant remaining term in the
  closed loop — something else, most plausibly the switching/dynamic charge
  mismatch `RECORD-002`'s own DC methodology explicitly cannot see, now
  appears to dominate. Frequency lock remains solid and, if anything,
  slightly improved.
- **Row 10 (reference spur)**: unaffected by this record — still
  `insufficient-evidence`, unchanged from `RECORD-003`'s/`RECORD-004`'s own
  disposition (the loop is frequency-locked but not phase-locked within row
  7's own criterion, so there is still no stable, locked carrier to define a
  spur around per this row's own requirement).
- **Row 11 (power)**: the mitigated `cp` domain draws more current in the
  closed loop than the as-drawn one (`i_cp` -24.66 uA -> -39.26 uA at this
  operating point), consistent with `DR-006`'s own stated consequence. This
  supersedes `RECORD-003`'s own `cp` figure for the mitigated design
  specifically; `RECORD-003`'s own as-drawn figure is unchanged (that design
  is untouched).

## Side effect on row 6/6a, cross-referenced rather than re-measured here

`sim/sg13cmos5l-cp-icp-trim/records/RECORD-002` and
`sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002` already re-verify row
6/6a end to end for the mitigated `cp` (Icp-trim table, loop bandwidth, and
phase margin) — see those records for the numbers. This record adds no new
information on row 6/6a.

## Follow-up

The switching/dynamic charge-mismatch hypothesis above is the natural next
step if row 7 is to be pursued further for this loop: a diagnostic that
keeps the mitigated `cp`'s real switch dynamics (turn-on/turn-off timing,
charge injection, clock feedthrough) while forcing the DC magnitude exactly
equal (the inverse isolation from `RECORD-004`'s own diagnostic, which
forced magnitude equal but discarded switch dynamics entirely) would confirm
or rule out that candidate directly. Not filed as a fresh issue here (that
is a decision for the epic's own triage, not this record) — flagged as the
most actionable, evidence-grounded next step this campaign has identified
for row 7.
