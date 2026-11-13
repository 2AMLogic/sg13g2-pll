# DR-013: retire the `+/-3.5 %` `cp` up/dn mismatch screening limit; propose no mismatch bound derived from row 7

- **Status**: proposed
- **Date**: 2026-11-13
- **Decided by**: Builder agent, issue #385

## Context

`sim/sg13cmos5l-cp-icp-trim-mc` grades its 1500-sample `cp` up/dn
mirror-mismatch campaign (`records/RECORD-002`) against **`+/-3.5 %`**.
That number is not in `spec/target-spec.md` and nobody ratified it. It is a
screening value the bench derived in one step from the only quantitative
closed-loop statement the repo had: row 7's `|static phase error| < 5 %` of
`T_ref`, divided by **1.4293 pp/pp** — the 9.176 % static phase error
measured at -6.42 % DC mismatch in `sg13cmos5l-closed-loop-lock`
`RECORD-003` and `sg13cmos5l-cp-icp-trim` `RECORD-002` — assumed linear and
through the origin. Both inputs to that division were measured on the
**pre-DR-010** `cp`, before `cp_dumpbuf` was rebuilt as the tracking OTA
pair. The gain had never been re-measured on the `cp` the campaign actually
simulates.

Issue #385 re-measured it. `sim/sg13cmos5l-closed-loop-lock`
`records/RECORD-014-cp-mismatch-phase-error-gain.md` steps the DC up/dn
mismatch of the committed DR-010 snapshot across **-11.998 % to +12.009 %**
(+/-3.1 sigma of the campaign's own 3.8769 % sigma) by scaling one mirror
leg, measures each perturbed snapshot's own DC mismatch, and runs
RECORD-007's closed-loop deck at each point at -40 / 27 / 125 C on the
batch fleet. What it found:

| | assumed by `+/-3.5 %` | measured on the DR-010 `cp` |
|---|---|---|
| slope | **+1.4293 pp/pp** | **-0.03940 pp/pp** (-40 C), **-0.04842 pp/pp** (27 C) |
| intercept | 0 (through origin) | **+0.84199 pp** (-40 C), **+0.75401 pp** (27 C) |
| model fit | assumed | two-parameter R^2 = 0.99921 / 0.99278, residual RMS 0.0094 / 0.0348 pp |
| forced through origin | — | residual RMS **0.8401 / 0.7528 pp**, i.e. 90x / 22x worse |

The measured gain is about **30x smaller** than the assumed one and **of
the opposite sign** (a UP-heavy pump *reduces* the static phase error,
because the DR-010 residual RECORD-006 identified removes charge from the
filter each cycle and the loop answers with a UP-leading offset). The
linear-through-origin model is rejected by the data: the intercept is the
`cp`'s own zero-mismatch residual, which current matching cannot remove and
which RECORD-007 measured independently at 0.779 %.

**So the 5 % static-phase criterion does not meaningfully constrain `cp` DC
up/dn mismatch on the DR-010 design.** Across the whole measured +/-11.92 %
span, at both temperatures where the deck acquires lock, the worst
final-20-cycle mean static phase error is **1.3265 %** and the worst single
cycle **+1.447 %** — at least 3.55 pp inside the criterion. Over that same
span the mismatch term contributes only +/-0.58 pp, less than the
zero-mismatch intercept contributes by itself.

## Decision

1. **The `+/-3.5 %` screening limit is retired as a row-7-derived number.**
   Its derivation is superseded by RECORD-014: both the magnitude and the
   sign of the gain it divides by are wrong for the DR-010 `cp`, and its
   linear-through-origin form is rejected at R^2-level confidence. No record
   may cite it as a bound derived from row 7 after this DR.
   `RECORD-002` itself is unedited and keeps its own figures — it was
   explicit that the value was a screening value and declared no
   `target_yield`, so nothing in it becomes false.

2. **This DR proposes no `cp` up/dn DC mismatch bound derived from spec
   row 7, because row 7 does not bind it.** Inverting RECORD-014's fit puts
   the 5 % crossing at `mismatch_pct` = **-87.7 %** (27 C) and **-105.5 %**
   (-40 C) — 7x to 9x outside the measured span, 23 to 27 sigma out on the
   campaign's own sigma, and (the measure saturates at +/-200 %) an UP leg
   carrying about a third of the DN leg's current. The fit is not validated
   there and no bound is extrapolated from it. **No number is chosen to
   make the campaign's yield pass**, which is what inventing one here would
   amount to.

3. **No `target_yield` is proposed.** A yield claim needs a ratified limit.
   `spec/target-spec.md` is `Status: DRAFT`, carries no `cp` mismatch row,
   and this DR adds no bound, so there is nothing for a `target_yield` to
   qualify. `sim/sg13cmos5l-cp-icp-trim-mc/records/RECORD-003` re-grades
   the committed samples and declares none, exactly as `RECORD-002` did.

4. **For re-grading only, the bound of the evidence is stated as
   `+/-11.92 %`** — the narrower end on each side of the span over which
   RECORD-014 demonstrated row-7 compliance (-11.9984 / +11.9244 % at
   -40 C, -11.9616 / +11.9686 % at 27 C). This is **not a spec limit, not a
   requirement and not a pass/fail threshold**: it says how far the evidence
   reaches, nothing more. `sim/sg13cmos5l-cp-icp-trim-mc/records/RECORD-003`
   grades the committed 1500 samples against it and gets 99.60 %
   (95 % CI [99.13 %, 99.85 %]), Cpk 0.9973, with `klt yield`'s sample-size
   verdict turning `sufficient` (`required_n` 8907 -> 154). Any later
   ratified limit replaces this bound outright; `corners/mc-samples.csv`
   makes that a re-grade, not a re-simulation.

5. **What would set a real limit is named, not left implicit.** `cp` up/dn
   mismatch is an input to three spec rows, and each needs evidence that
   does not exist yet:
   - **Row 10 (reference spur)** is the physically right owner: mismatch
     drives the reference sideband directly. The repo has no spur
     measurement at all (`RECORD-001` of this slug found no locked carrier;
     row 10 proposes no number), so no limit can be derived from it today.
   - **Row 16's second half** ("window >= 2x worst static phase offset") is
     computable once row 16's open half closes. With a worst static phase
     error of 1.3265 % over +/-11.92 % of mismatch, it is a weak constraint
     at today's numbers.
   - **Row 7 itself, on the committed loop** rather than the proposal deck.
     Every number above is from the behavioural-divider deck
     (`R1` x20, ideal MOM caps, ideal `IREF`); a committed-loop gain could
     differ, and RECORD-014's own intercept is the term that grows at low
     `Icp * T_ref`.

   Until one of those produces a bound, the honest spec state is "no
   evidence-derived `cp` mismatch limit exists", which is what
   `spec/target-spec.md` R-12 now records.

## Alternatives considered

- **Re-derive `+/-3.5 %` with the new gain** (i.e. 5 % / 0.04842 pp/pp,
  giving about +/-88 %) — rejected. It is the same linear-through-origin
  division this DR just showed the data rejects, applied 7x outside the
  measured span, and it would hand the ratifiers a number with no physical
  content.
- **Propose +/-11.92 % as the ratified limit** — rejected. It is where the
  evidence happens to stop, not where a requirement starts. Ratifying the
  edge of a sweep as a spec bound is how a measurement budget becomes a
  design rule by accident, and it would also be the number that makes the
  campaign's yield read 99.6 %, which is precisely the move the issue
  forbids. It is used as a re-grade bound and labelled as such in the limits
  file, the envelope's `spec_row` field and RECORD-003.
- **Keep `+/-3.5 %` until a better limit exists** — rejected. It is not
  conservative, it is wrong: it grades today's `cp` against a sensitivity
  the design no longer has, and it was already producing a 63 % "yield"
  that measures the stale derivation rather than the circuit.
- **Leave the limit question to the campaign resize (#385 step 3)** —
  rejected, and this is the issue's own argument: `klt yield`'s
  `required_n` scales as `p(1-p)`, so it is a function of the limit. Buying
  7407 more samples against `+/-3.5 %` would have bought a sharper estimate
  of the wrong quantity. RECORD-003 confirms it concretely — at the
  evidence bound the existing 1500 samples are already `sufficient`.
- **Derive the limit analytically from the PFD reset window** instead of
  measuring it — rejected, as `RECORD-004` of the closed-loop slug already
  rejected it: the analytic gain is not derived anywhere in this repo, and
  this repo's rule is no claim without a testbench.

## Consequences

- **`sim/sg13cmos5l-cp-icp-trim-mc`'s grading value loses its derivation.**
  `testbench/mc.request.json` still carries `min -3.5 / max 3.5` and is
  **not edited** (the committed request is what produced the committed
  samples; editing it would invalidate `reports/sim.mc.json`'s provenance).
  The bench README now says the value is retired and points here.
- **T1 item `6.analog` does not become `met`, and this DR does not move
  it.** `manifests/README.md` grades only against a two-key-ratified spec;
  this record is `proposed`, declares no `target_yield` and adds no row, and
  `manifests/sg13g2-pll.json` is not re-pointed. Item 6 still cites
  `reports/sim.mc.json` and still grades `unmet` / `undersized_sample`. What
  changes is that the reason is now visible: there is no limit, not too few
  samples.
- **A resize of the campaign is no longer indicated on sample-size
  grounds.** At the evidence bound, 1500 samples resolve the estimate to
  +/-0.36 pp and `required_n` is 154. If a ratified limit later lands near
  the distribution's body, `required_n` rises again and the question
  reopens — against that limit, with the committed samples re-graded first.
- **The `negative_control` gap survives this DR.** Both envelopes warn that
  no seeded known-bad variant has shown these statistics can detect a
  degraded design. RECORD-003 states the disposition and
  RECORD-014's generator now provides the material for one (a `cp` whose DC
  mismatch is +11.97 %); closing it needs a second campaign and
  `klt yield-samples`, which is follow-up work (issue #389).
- **A new deck gap is on the record**: the proposal deck does not acquire
  lock at 125 C at any mismatch point, including the unperturbed one
  (`vctrl` rails at 3.289 V). Every earlier closed-loop record in that slug
  ran at 27 C only, so this is newly visible. It bounds how far RECORD-014's
  gain is established (two temperatures, not three) and is filed as issue
  #389.
- **If the ratifiers disagree** and want a bound now, the ruling they are
  being asked for is R-12 in `spec/target-spec.md`: whether a `cp` mismatch
  limit must exist for T1, and which row owns it. A superseding DR would
  replace this one; nothing here is written in a way that makes that
  harder.
