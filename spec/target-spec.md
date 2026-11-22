# Target spec — sg13g2-pll (SG13G2 / SG13CMOS5L)

- **Status**: **DRAFT** — not ratified. Ratification is a separate two-key act
  (`ratification/ee-key`, `ratification/market-key`) and is not performed by
  this document.
- **Drafted by**: Builder agent, issue #148.
- **Inputs**: [`porting-plan.md`](porting-plan.md) §1.2 (the row list),
  the decision records under [`decision-records/`](decision-records/), and
  the committed evidence under `sim/`. Nothing under `decision-records/` is
  edited by this draft.
- **Rule for this draft**: no number is invented. Every bound below is
  quoted from a committed record. A row with no SG13CMOS5L measurement stays
  **open** and names its gate. Numbers from `gf180-pll` / `sky130-pll` are
  not filled in here.

## Where the evidence comes from

Two families of benches exist under `sim/`:

- `sim/sg13cmos5l-*` — the SG13CMOS5L port, the target flavor. All
  "measured" rows below rest on these.
- `sim/sg13g2-*` — three SG13G2 benches (`sg13g2-vco-kvco-table`,
  `sg13g2-lock-detector-window`, `sg13g2-divider-repair-reverification`).
  Where one exists it is cited as corroboration. Per the issue, a row that
  only has an `sg13g2-*` bench would count as unmeasured for the target
  flavor; no row here is in that position.

Pre-layout (schematic) results are the default. Post-layout results
(`sim/sg13cmos5l-postlayout-pex-pvt`, `sim/sg13cmos5l-klt-pex-signoff`)
disagree with them for the VCO; see R-1.

## Operating box

Stated once; rows refer to it.

| Axis | Box | Source |
|---|---|---|
| Device flavor | 3.3 V thick-oxide CMOS (`sg13_hv_nmos` / `sg13_hv_pmos`) throughout; 1.2 V thin-oxide deferred; HBT bias reference, HBT cascode and CML first stage deferred | `decision-records/DR-002-supply-device-flavor.md` Decisions 0-3 (status: proposed) |
| Supply | 3.3 V at every internal domain. The Challenge #6 1.2 V digital rail governs only a future wrapper's I/O boundary, not any node inside the six ported blocks | `decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md` (ratified) |
| Supply tolerance | 3.3 V +/-10% carried from porting-plan row 18. Measured at 3.0 V / 3.6 V on `cp` only, at `mos_tt`/27 C | `sim/sg13cmos5l-cp-icp-trim/corners/matrix.md` |
| Temperature | -40 C / 27 C / 125 C, as swept in the benches | `sim/sg13cmos5l-vco-kvco-table/corners/matrix.md`, `sim/sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md` |
| Process | 3 bundles: `fast` = `mos_ff`/-40 C, `typ` = `mos_tt`/27 C, `slow` = `mos_ss`/125 C. The duty-cycle and `cp` benches add `mos_sf` / `mos_fs`. Resistor and MOM-cap corners are swept where the block has them | same files, plus `decision-records/DR-008-cp-icp-trim-fine-code-band00-low-fref4p5.md` |

The DRs fix the supply and device flavor. They do not state a temperature
range or a corner list; the temperature and process entries are what the
benches swept. See R-9.

## Classification keys

**Status** (exactly one per row):

- **M** — measured, proposed for ratification.
- **P** — proposed without measurement.
- **N** — deliberately not specified.
- **O** — open; the gate is named.

**Kind** (T1 item 6):

- **Det** — deterministic: the bound is a worst case over a declared
  corner set, checked by a corner sweep.
- **Stat** — statistical: the bound is a distribution quantity (noise,
  mismatch). One Monte Carlo record now exists under `sim/` (issue #178):
  `sg13cmos5l-cp-icp-trim-mc/records/RECORD-002-cp-mismatch-mc-yield.md`, a
  1500-sample `cp` up/dn mirror-mismatch campaign with a `klt yield`
  envelope. It grades `cp` mismatch against that bench's own
  evidence-derived screening limit, which is **not** a row of this table and
  is not ratified, so no Stat row below is measured as a statistic. Where a
  Stat row has a corner-sweep number, that number is evidence of the
  deterministic part only. **That screening limit (`+/-3.5 %`) is now
  retired** by DR-013 (issue #385): the mismatch-to-static-phase-error gain
  it was divided out of was re-measured on the DR-010 `cp`
  (`sg13cmos5l-closed-loop-lock`:
  `records/RECORD-014-cp-mismatch-phase-error-gain.md`) and is about 30x
  smaller, of the opposite sign, and not through the origin. DR-013 proposes
  no replacement bound and no `target_yield`, because row 7 does not
  constrain `cp` mismatch at the DR-010 design's measured sensitivity; see
  R-12.

**Partition** (the manifest grades two; `manifests/README.md`): **Analog** =
`pfd`, `cp`, `loop_filter`, `vco`, `lock_detector`. **Digital** =
`divider_chain`.

## Row table

One line per porting-plan §1.2 row. Rows 4/5 and 6/6a are merged rows, as in
the plan.

| Row | Parameter | Status | Kind | Partition | Proposed bound (units / conditions) | Set or amended by | Measured by (bench: record) | Binding corner |
|---|---|---|---|---|---|---|---|---|
| 0 | Supply / device flavor | P | Det | both | 3.3 V thick-oxide CMOS throughout, per the operating box. A decision, not a measured parameter | DR-002 Decision 0 (proposed); DR-004 (ratified) | none | n/a |
| 1 | Output band | M | Det | Analog | 445.3 to 1562.0 MHz, pre-layout, open-loop `vco`, 60/60 points valid, 3 bundles x 4 band codes x 5 `VCTRL` (0.3 to 2.7 V). Post-layout deviates; see R-1 | DR-005 (proposed) reads it as the fixed point for rows 2 and 3 | `sg13cmos5l-vco-kvco-table`: `records/RECORD-001-kvco-band-code-table.md`; corroborated byte-identical by `sg13g2-vco-kvco-table`: `records/RECORD-001-kvco-band-code-table.md` | floor: `slow`, `VCTRL` = 0.3 V (all band codes equal); ceiling: `fast`, band `11`, `VCTRL` = 2.7 V |
| 2 | Reference input | O | Det | Analog (`pfd` input) | Frequency 3.5 to 24.4 MHz (3.51 = 445.3/127; 24.4 = 1562.0/64) — a corner union: floor from the `slow` bundle, ceiling from the `fast`. The PVT intersection this `Det` row requires is 4.317 to 17.403 MHz (548.2/127 `fast` own-floor; 1113.8/64 `slow` own-ceiling), conservative against the unmeasured 2.7 to 3.3 V rail headroom; see DR-014 `fref-window-pvt-intersection` and R-13. DR-015 (proposed) extends the `lock_detector` range to 3.5 to 50 MHz (the PLL's own range stays 3.5 to 24.4 MHz: row 1 and row 3 force `N x f_ref` <= 1562.0 MHz with N >= 64, see DR-015 Decision 1). Shape unchanged: CMOS square wave, rising-edge trigger, 30 to 70% duty. Electrical levels open; see R-5. Gate: R-13 | DR-005 (proposed) amends 1 to 25 MHz; DR-014 (proposed) supersedes DR-005's row-2 numeric derivation (union kept, intersection stated); DR-015 (proposed) extends to 50 MHz for `lock_detector` | derived from the row 1 record; `sg13cmos5l-loop-bandwidth-pm`: `records/RECORD-002-r1-resize-full-fref-range.md` exercises the range | n/a (arithmetic on the row 1 corners) |
| 3 | Multiplication ratio | M | Det | Digital | N in 64 to 127, every integer, no holes. Functional: 20/20 simulated points divide at exactly the commanded N (9 PVT corners at N=64, every program-bit weight, two mixed codes, N=127 at both speed-bracket extremes, 100 MHz). Retiming closure at 1562.0 MHz is **unmet**; see R-3 | DR-005 (proposed) amends 4 to 64 | `sg13cmos5l-divider-nrange-retiming`: `records/RECORD-003-divider-repair-reverification.md`; SG13G2 corroboration `sg13g2-divider-repair-reverification`: `records/RECORD-001-divider-repair-reverification.md` | one-edge closing bound: 825 MHz at `mos_tt`/-40 C, 866 MHz at `mos_tt`/27 C, 1277 MHz at `mos_ff`/27 C |
| 4/5 | Kvco bound / band-selection rule | M | Det | Analog | The per-band, per-corner Kvco table, not a single ceiling. Range across the table: Kvco avg 144.2 to 422.4 MHz/V, Kvco peak local (2.1 to 2.7 V) 162.2 to 379.9 MHz/V. Band code is inert at `VCTRL` = 0.3 V and spreads about 2.8x at 2.7 V. A numeric ceiling and the lowest-band-first rule are not set by any record; see R-4 | none sets a bound; DR-001 / porting-plan row 4/5 name the rule structure | `sg13cmos5l-vco-kvco-table`: `records/RECORD-001-kvco-band-code-table.md` (range figures are quoted in `sim/README.md` from `sg13g2-vco-kvco-table`: `records/RECORD-001-kvco-band-code-table.md`) | per-row in the record's table |
| 6/6a | Loop bandwidth / phase margin | M | Det | Analog | Criteria: `f_c` < `f_ref`/10 (ceiling 0.35 to 2.44 MHz across the row 2 range) and phase margin >= 45 deg. Mechanism: `R1` = `rppd` `w=0.6u l=810u` (about 344.2 kOhm typ) plus an Icp trim table keyed to `f_ref`: the six original codes (2.5 to 80 uA ladder) plus 3.75 uA (band 00, mid interval, `f_ref` = 4.5 MHz) and 11 uA (band 00, low interval, `f_ref` = 4.5 MHz). Coverage is incomplete; see R-6 | DR-006 `loop-filter-r1-resize` (proposed); DR-007 (proposed); DR-008 (proposed); DR-005 left this row as-is | `sg13cmos5l-loop-bandwidth-pm`: `records/RECORD-002-r1-resize-full-fref-range.md`, `records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`, `records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`; `sg13cmos5l-cp-icp-trim`: `records/RECORD-003-issue83-finetrim-icp.md`, `records/RECORD-004-issue79-finetrim-icp.md`; `sg13cmos5l-loop-filter-momcap`: `records/RECORD-002-r1-resize-momcap.md` | band 00, low interval, `f_ref` = 4.5 MHz: `fast` PM 45.592 deg at 11 uA (0.592 deg margin); band 00, mid interval, 4.5 MHz: `slow` PM 49.973 deg at 3.75 uA |
| 7 | Lock time | O | Det | both (closed loop) | No number proposed. Gate: R-2. This row's 5%-of-`T_ref` static-phase criterion is also what the retired `cp` mismatch screening limit was derived from; R-12 | porting-plan row 7 (structure only: dual threshold, held N cycles; the < 100 us and < 20 us gf180 values are not carried); DR-013 (proposed) retires that derived screening value and proposes no `cp` mismatch bound in its place, leaving this row's own criterion unchanged | `sg13cmos5l-closed-loop-lock`: `records/RECORD-006-cp-dynamic-charge-term-diagnostic.md`; `sg13cmos5l-closed-loop-real-divider`: `records/RECORD-001-repaired-divider-in-loop-nominal.md` (both fail at their 20 MHz / band `11` point); `records/RECORD-002-divider-compatible-operating-point-nominal.md` (real-divider arm locks at the divider-compatible point — band `00` / `f_ref` = 9.375 MHz, dual lock held the final 91 cycles at 1.729% of `T_ref`; one nominal point, PVT pending #516); sensitivity of this row's criterion to `cp` mismatch: `sg13cmos5l-closed-loop-lock`: `records/RECORD-014-cp-mismatch-phase-error-gain.md` | n/a |
| 8 | Period jitter | O | Stat | Analog (`vco`) | No number proposed. Gate: R-7 | porting-plan row 8 (percent-of-period framing, ripple-conditional structure) | `sg13cmos5l-vco-decap-momcap`: `records/RECORD-001-decap-momcap-sensitivity.md` bounds the decap value only, not jitter | n/a |
| 9 | Integrated RMS jitter / phase noise | N | Stat | Analog | Not specified, derived-only. ngspice has no direct path to free-running-oscillator phase noise | DR-002 Decision 5 (proposed); ported as-is | none | n/a |
| 10 | Reference spur | O | Stat | Analog (`pfd`, `cp`) | No number proposed. Gate: R-2 (needs a phase-locked carrier) plus a switching-charge-mismatch record | porting-plan row 10 (re-derive entirely) | `sg13cmos5l-closed-loop-lock`: `records/RECORD-001-closed-loop-lock-spur-power.md` (no locked carrier); static `cp` mismatch input in `sg13cmos5l-cp-icp-trim`: `records/RECORD-002-cascode-bias-mismatch-remeasure.md` | n/a |
| 11 | Power | O | Det | both | No whole-PLL total proposed. Per-domain evidence exists (below the table). Gate: R-2 and R-3 | porting-plan row 11 (re-derive, no V^2 rescale) | see per-domain list | n/a |
| 12 | Supply sensitivity | O | Det | Analog (`vco`) | No number proposed (two-budget structure: AC ripple ceiling, DC Vctrl-window ceiling). Gate: R-7 | porting-plan row 12 | `sg13cmos5l-vco-decap-momcap`: `records/RECORD-001-decap-momcap-sensitivity.md` (decap value and fractional pole sensitivity only) | n/a |
| 13 | Output duty cycle | O | Det | Analog (`vco`) | Candidate bound is the ported 45 to 55%, not relaxed. Measured 43.74 to 51.56% over 300 points; 30 of 300 are below 45%, all at -40 C. The candidate is therefore **not met** today; see R-8 | porting-plan row 13 (ported target) | `sg13cmos5l-vco-duty-cycle`: `records/RECORD-001-duty-cycle-and-vco-current.md` | `mos_fs`, -40 C, `VCTRL` = 0.3 V (43.74%) |
| 14 | Output levels / drive | P | Det | Analog (`vco` output buffer) | Interface: the `vco` output buffer pin. Single-ended, per node, rail-referenced: V_OH >= 0.9 x VDD and V_OL <= 0.1 x VDD (2.97 V / 0.33 V at 3.3 V) into <= 50 fF, capacitive, DC-referenced; ported as-is. No differential figure is defined. No SG13CMOS5L measurement found, so no "met" claim is made. The downstream TX-mux figure (0.4 V per side, 0.8 V differential p-p, ~0.6 V common mode, 5.0 GHz, self-biased AC-coupled squarer, as stated in issue #312) is **not assessed**: its load model differs and 5.0 GHz is outside row 1. See DR-011 | porting-plan row 14 | none | n/a |
| 15 | Area | O | Det | both | No number proposed. Gate: a chip-level area record; no `pll_top` or wrapper exists (DR-004; `manifests/README.md`) | porting-plan row 15 (re-derive entirely) | none (per-block layouts exist under `layout/sg13cmos5l-pll/`; no area record) | n/a |
| 16 | Lock detector targets | M | Det | Analog | Assert window >= 2.5 ns (measured 3.688 to 11.24 ns, 0/102 below); hysteresis >= 25% of window (measured 50 to 800%, 0/21 below); no chatter (`steady` 21/21 at a 10x-window phase error). Threshold sits at about 12 to 37% of a reference period over 3.5 to 24.4 MHz at `mos_tt`/`res_typ`/27 C only (measured; over the 21-corner ladder it spans 6 to 58%). DR-015 (proposed) sets the target band over 3.5 to 50 MHz: assert 11 to 25% of `T_ref` (and >= 2.5 ns), de-assert 18 to 37%, all PVT; **not met across PVT today**, at 3.5 to 24.4 MHz (9 of 21 committed corners outside; assert 6.1 to 46.0 %, de-assert 12.3 to 58.3 %, two 24.4 MHz corners above 50 %) as well as at 50 MHz; the 11.7 to 24.4 % / 18.7 to 36.6 % figures are `mos_tt`/`res_typ`/27 C only; meeting it likely needs a topology change and a superseding record (DR-015 Decision 3; rework: #302). `LOCK` is active-low (DR-015): 0 = locked. "Window >= 2x worst static phase offset" is unmeasured; see R-2 | DR-006 `lock-detector-fref-dependent-threshold` (ratified) accepts the f_ref dependence; DR-015 (proposed) restates it for 3.5 to 50 MHz; resize history in the lock-detector records | `sg13cmos5l-lock-detector-window`: `records/RECORD-003-hysteresis-fix.md`, `records/RECORD-004-crowbar-current-mitigation.md`, `records/RECORD-005-rpu-body-on-vss.md` (nominal only); SG13G2 sizing differs: `sg13g2-lock-detector-window`: `records/RECORD-001-resized-window-hysteresis-chatter.md` | per the record's 21-corner ladder; window floor margin 1.475x (RECORD-002) worst case |
| 17 | Standby / power-down | N | Det | both | No power-down mode in v1; waived, ported as-is | porting-plan row 17 | none | n/a |
| 18 | Supply range | P | Det | both | 3.3 V +/-10% (3.0 to 3.6 V), carried from porting-plan. Measured at the two endpoints on `cp` only (`mos_tt`/27 C); all other blocks were run at 3.3 V | porting-plan row 18; gated on DR-002 Decision 0 (proposed); DR-004 (ratified) fixes the internal rail | `sg13cmos5l-cp-icp-trim`: `records/RECORD-001-icp-trim-and-mismatch.md` (`cp` sub-axis only) | `cp`: `mos_tt`/27 C at 3.0 and 3.6 V |

### Row 11 per-domain evidence (supports the open status; proposes no total)

All at 3.3 V, pre-layout.

- `vco` ring: 0.937 to 2.690 mA, 3.09 to 8.88 mW over the 300-point duty-cycle
  matrix: `sim/sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md`.
- `lock_detector`: 2.48 to 113 uA (10x-window probe):
  `sim/sg13cmos5l-lock-detector-window/records/RECORD-004-crowbar-current-mitigation.md`.
- `divider_chain` (repaired): -199.3 to -256.8 uA at 100 MHz over 9 corners:
  `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-003-divider-repair-reverification.md`.
  Not measured at the operating frequency (up to 1562.0 MHz).
- Closed-loop four-domain figure (`pfd`+`cp`+`vco`+`lock_detector`) 2.484 mA (pinned dual-tree rerun, RECORD-010; 2.483 mA in the original run) /
  8.20 mW at one point, on the pre-repair design:
  `sim/sg13cmos5l-closed-loop-lock/records/RECORD-001-closed-loop-lock-spur-power.md`,
  superseded by `sim/sg13cmos5l-closed-loop-lock/records/RECORD-010-closed-loop-lock-rerun-pinned.md`.
  Its `divider_chain` figure (7.653 mA) is flagged in that record as inflated
  by the unrepaired divider, so it is not used here.

## Needs a ruling

Every open row and every conflict, for the ratifiers. Nothing in
`decision-records/` has been changed to resolve any of these.

**R-0. Most of the spec rests on records that are not ratified.** Status in
the files: DR-001, DR-002, DR-003, DR-005, DR-006 (cascode bias replica),
DR-006 (loop-filter R1 resize), DR-007 and DR-008 are `proposed`. Only DR-004
and DR-006 (lock-detector threshold) are `ratified`. The rows that cite
unratified records (0, 1, 2, 3, 6/6a, 9, 18) cannot be ratified ahead of
them. DR-005 also carries its own evidentiary caveat (issue #43: the bench it
cites originally failed every run on one reporter's build). The later
sg13g2 and sg13cmos5l reruns show the 60 values are reproducible; the
ratifiers should confirm that closes DR-005's caveat.

**R-1. Row 1 conflict: schematic band versus post-layout band.** DR-005 and
rows 2 and 3 are built on 445.3 to 1562.0 MHz. `sim/sg13cmos5l-postlayout-pex-pvt`
(`records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md`) measures the routed,
extracted `vco` at 0.4768 to 0.5312 times the schematic frequency at 60/60
points (223.7 to 789.5 MHz). `records/RECORD-002-floorplan-aware-vco-route.md`
and `sim/sg13cmos5l-klt-pex-signoff/records/RECORD-001-klt-pex-nominal-envelopes.md`
(+151.0% on VCO period) bear on the same gap. Those records state the
deviation is an upper bound set by routing style and that `vco` has no
confirmed layout-vs-schematic match, and they amend no row. If the post-layout
band stands, the DR-005 `f_ref` / N windows (3.51 to 24.4 MHz, 64 to 127) no
longer reach it, and DR-005 itself says a materially different band needs a
superseding record. Ruling needed: which band the spec binds to, and whether
a superseding DR is required.

**R-2. Closed-loop rows 7, 10, 11 and the second half of 16 are open on one
gate.** Gate: a phase-locked closed loop that meets the 5% static-phase
criterion on the real blocks. Current evidence: at 20 MHz / band `11` the
mitigated `cp` leaves an 8.204% static phase error (target 5%).
`sim/sg13cmos5l-closed-loop-lock/records/RECORD-006-cp-dynamic-charge-term-diagnostic.md`
attributes it to the dump-buffer follower holding `VDUMP` about 0.94 V below
`VOUT` (about -41.30 fC per UP+DN pair). At the divider-compatible operating
point, though, the real-divider loop acquires and locks:
`sim/sg13cmos5l-closed-loop-real-divider/records/RECORD-002-divider-compatible-operating-point-nominal.md`
(issue #401) runs the N = 64 loop at band `00` / `f_ref` = 9.375 MHz
(600 MHz) and the real-divider arm holds the dual-lock criterion for the
final 91 cycles of its 10 us window at a 1.729% static phase error — under
the 5% criterion, but at ONE nominal point (`mos_tt`/`res_typ`/27 C/3.3 V),
pre-layout, warm-started. RECORD-001's non-acquisition at 20 MHz / band `11`
stands as history, the PVT campaign on the divider-compatible point is
pending (#516), and no spec row is ratified from either record.
Two things the ratifiers may want to look at together: that 8.2% static
error is measured against a lock-detector threshold of about 12 to 37% of a
reference period (DR-006 lock-detector), so the "window >= 2x worst static
phase offset" half of row 16 would need at least about 16.4% at the lower end
of that span. This is arithmetic on two records measured by different
benches; it is not itself a measurement. Rows 7, 10 and 11 still name no
number: a nominal lock now exists (RECORD-002), but no PVT-covered lock
evidence is ratified, so each stays open pending a decision record and
ratification.

**R-3. Row 3 retiming closure is unmet and not relaxed.** The functional N
range passes; the one-edge retiming closing bound is 825 to 1277 MHz by
corner, below the 1562.0 MHz top of band
(`sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-003-divider-repair-reverification.md`).
Above the bound the retimed `FB` latches one VCO period late. A divider-alone
speed diagnostic in `sg13cmos5l-closed-loop-real-divider` divides by 96 at
1.28 GHz instead of 64. Ruling needed: accept the lower top-of-band as the
spec, or hold the row open until the sizing campaign (DR-001 T1 items 8 and 9)
re-closes it. This also gates row 11's divider figure.

**R-4. Row 4/5 has a table but no bound and no selection rule.** No record
sets a Kvco ceiling or states the lowest-band-first rule's content. The
kvco record notes the rule must account for band code being inert at low
`VCTRL` and dominant at high `VCTRL`. Ruling needed: choose the ceiling (or
decide the table is the spec) and the rule.

**R-5. Row 2 electrical levels (V_IL / V_IH) are open.** Porting-plan says
re-derive once the supply flavor settles. Gate: DR-002 ratification plus an
input-buffer / `pfd` input-threshold bench. No such bench exists.

**R-6. Row 6/6a coverage.** DR-006 (R1 resize) records 17 (band, interval,
`f_ref`) tuples with all three bundles, 16 passing; DR-007 and DR-008 close
the two failing tuples, but DR-007 is measured for the `slow` bundle only,
and 13 tuples have only one or two bundles simulated (12 pass at every bundle
run, one is the DR-007 tuple). The per-`f_ref` trim-selection table is
incomplete: DR-007 and DR-008 each say they add one entry to a table not yet
fully built, and decline the 30-tuple rule gf180-pll built. Ruling needed:
whether partial-bundle tuples are accepted, and who owns the full trim rule.

**R-7. Rows 8 and 12 are open on a method gap.** Gate: a transient-noise or
ISF method for the free-running ring, plus a post-layout supply source
impedance. The decap bench
(`sg13cmos5l-vco-decap-momcap`, `records/RECORD-001-decap-momcap-sensitivity.md`)
names both. Row 9 is deliberately not specified for the same flow reason; the
ratifiers should rule whether rows 8 and 12 may stay open for T1, or whether
row 8 should also move to "not specified" by the same logic.

**R-8. Row 13 duty cycle fails the ported 45 to 55% target at -40 C.** 30 of
300 points are below 45% (minimum 43.74%). The row is not relaxed here. Ruling
needed: redesign, or an explicit ratified deviation. Mismatch is not
exercised (no Monte Carlo); see the Kind key.

**R-9. The operating box is incomplete in the DRs.** The DRs fix supply and
device flavor; temperature range and the corner list come from bench
matrices. Row 18's +/-10% tolerance is measured on `cp` only; every other
block ran at 3.3 V nominal. Ruling needed: ratify the -40 / 27 / 125 C and
3-bundle box, and decide whether the +/-10% supply axis must be swept on the
other blocks before row 18 is ratified.

**R-10. Rows with no measurement or no proposed number.** Row 14 (levels; interface and consumer-figure
statement in DR-011), row 15 (area; gate: chip-level area record, which needs a `pll_top` or
wrapper per DR-004). Row 17 is a waiver, row 9 an omission; both need
confirmation rather than evidence.

**R-11. Two sizing sets for row 16.** The SG13CMOS5L and SG13G2
`lock_detector` are sized differently (`cap_cmim` versus `cap_cmomi`); the
SG13G2 bench reports its own window of 3.732 to 10.249 ns. Ruling needed:
which tree the spec is stated for. This draft quotes the SG13CMOS5L numbers.

**R-12. There is no `cp` up/dn mismatch limit, and row 7 does not supply
one.** `sim/sg13cmos5l-cp-icp-trim-mc` graded its 1500-sample campaign
against `+/-3.5 %`, a screening value the bench derived from row 7's 5%
static-phase criterion divided by a 1.4293 pp/pp gain measured on the
**pre-DR-010** `cp`. Issue #385 re-measured that gain on the committed `cp`
(`sim/sg13cmos5l-closed-loop-lock/records/RECORD-014-cp-mismatch-phase-error-gain.md`,
six mismatch points over -11.998 to +12.009 %, i.e. +/-3.1 sigma, at
-40 / 27 / 125 C): the slope is -0.0394 to -0.0484 pp/pp — about 30x
smaller and of the opposite sign — with a +0.754 to +0.842 pp intercept
that is the DR-010 `cp`'s own zero-mismatch residual, and a
linear-through-origin model is rejected (forcing the intercept to zero
multiplies the fit residual by 22x to 90x). Across the whole measured span
the worst static phase error is 1.3265 % against the 5 % criterion, so row 7
is met with >= 3.55 pp of margin at every mismatch point that locks.
`DR-013-cp-mismatch-limit.md` (proposed) therefore retires `+/-3.5 %`,
proposes no replacement bound and no `target_yield`, and names what would
set a limit instead: row 10 (reference spur), which has no measurement at
all, row 16's unmeasured "window >= 2x worst static phase offset" half, or
row 7 re-measured on the committed loop rather than the proposal deck.
**Ruling needed**: whether a `cp` mismatch limit must exist for T1 at all,
and if so which row owns it and what evidence is required — or whether "no
evidence-derived limit exists yet" is the accepted T1 state for this
quantity. Two caveats the ratifiers should see together: every number above
is from the behavioural-divider proposal deck, and that deck does **not**
acquire lock at 125 C at any mismatch point (including the unperturbed one),
so the gain is established at two of three temperatures.

**R-13. Row 2's frequency window is a corner union on a `Det` row; the PVT
intersection is narrower.** Row 2's committed 3.5 to 24.4 MHz endpoints
(`3.51 = 445.3/127`, `24.4 = 1562.0/64`) take the floor from the `slow`
bundle's slowest point and the ceiling from the `fast` bundle's fastest — no
single corner supports both, and this row's own `Kind` = `Det` means "worst
case over a declared corner set". DR-014
(`DR-014-fref-window-pvt-intersection.md`, proposed) derives the
intersection from the committed Kvco table: **4.317 to 17.403 MHz**
(`548.2/127`, the `fast` bundle's own floor; `1113.8/64`, the `slow`
bundle's own ceiling), conservative because the table stops at
`VCTRL` = 2.7 V against the 3.3 V rail (at `mos_tt`/125 C the last 0.6 V
buys 55.6 MHz, per #426 / PR #427). The first operating point to make the
defect bite is the closed-loop deck's 1280 MHz / 125 C non-acquisition
(#426, #427): its `f_ref` = 20 MHz was chosen near the union ceiling, above
the intersection ceiling. Ruling needed: bind row 2's lockable
`f_ref` × N window to the intersection, **together with R-1** — both
windows are arithmetic on row 1's schematic band, so a ruling that binds
the spec to the post-layout band recomputes this one too. The interface
half of row 2 (what the `pfd` / `lock_detector` input can accept, extended
to 50 MHz by #301 per ruling r7-q30 on #296) is a different claim and is
not bounded by this window. Three committed figures elsewhere in this file
derive from row 2's range, and this ruling names them so an implementer
knows which move with it and which do not. Row 6/6a's `f_c` ceiling
("0.35 to 2.44 MHz across the row 2 range") is pure arithmetic on the union
endpoints (`3.5/10`, `24.4/10`), so if this ruling binds the intersection
the ceiling is recomputed in the same edit: **0.432 to 1.740 MHz**
(`4.317/10`, `17.403/10`). Row 16's threshold span ("about 12 to 37% of a
reference period over 3.5 to 24.4 MHz") and R-2's `at least about 16.4%`
arithmetic, which grades `2 x 8.204%` against that span's 12% low end, sit
on the interface side of the line drawn above: they are DR-006's threshold
table evaluated at the union endpoints, owned by ruling r7-q30 (#296) as
extended by #301, and must **not** be rewritten to the intersection when it
binds. And the narrowing only helps them: percent-of-`T_ref` rises with
`f_ref` at both ends of the corner band in the SG13G2 resized ladder
(`sim/sg13g2-lock-detector-window/corners/ladder_resized_rerun236.csv`),
so evaluating the thresholds at the intersection endpoints would shrink the
quoted span — `12 to 37%` stays a conservative outer bound over the
intersection and R-2's test gets easier, not harder.

## Accounting

Rows 0 to 18 as listed in porting-plan §1.2, with 4/5 and 6/6a merged:
18 rows, each appearing once in the table above.

| Status | Rows |
|---|---|
| M (measured, proposed) | 1, 3, 4/5, 6/6a, 16 |
| P (proposed, no measurement) | 0, 14, 18 |
| N (not specified) | 9, 17 |
| O (open, gate named) | 2, 7, 8, 10, 11, 12, 13, 15 |
