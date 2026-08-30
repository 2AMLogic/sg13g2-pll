# RECORD-004: `Icp_up`/`Icp_dn` mismatch diagnostic for `RECORD-003`'s ≈9.18% static phase-error residual

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #70 (follow-up named at the bottom of `RECORD-003`, itself a
  follow-up to #56/`RECORD-003`) — a dedicated diagnostic to test
  `RECORD-003`'s own stated-but-unconfirmed hypothesis for the ≈9.18%
  static phase error its Part B (proposal) deck measured after the `pfd`
  self-reset fix: that `cp`'s already-measured `up`/`dn` current magnitude
  mismatch (`../../sg13cmos5l-cp-icp-trim/corners/results.csv`: `up`
  +10.05 µA vs. `dn` −10.37 µA at the 10 µA trim code, `mos_tt`/27 C — a
  ≈3% magnitude mismatch) forces the nonzero static phase offset.
- **This record does not edit `RECORD-001`/`RECORD-002`/`RECORD-003`**
  (append-only, per this directory's own convention).
- **Diagnostic, not a design change.** The `cp` block is replaced by an
  **ideal, exactly-symmetric behavioural charge pump** —
  `../testbench/run_closed_loop_icp_eq_diag.sh` builds it inline, it is
  NOT read from `../netlist-snapshots/cp.spice` and it is NOT
  `design/sg13cmos5l/cp.sch` or any committed netlist. Everything else in
  the deck — `pfd` (the frozen `../netlist-snapshots/pfd.spice`, already
  the `#56`-corrected netlist per that snapshot's own provenance header),
  the R1×20 loop filter, `vco`, the behavioural divide-by-64, the
  operating point, PVT point, and ideal-capacitor substitutions — is
  IDENTICAL to `RECORD-003`'s own Part B deck.
- **The ideal `cp` substitution**: a 9-pin-compatible `.subckt cp` with two
  behavioural current sources gated by ideal comparators on the `UP`/`DN`
  control nodes (threshold 1.65 V = `VDD`/2, the same threshold this
  script's own edge-extraction and `../testbench/run_closed_loop_pfdfix_diag.sh`'s
  precedent both already use), each sourcing/sinking the **identical**
  magnitude `IMAG = 10.208 µA` — the mean of `../../sg13cmos5l-cp-icp-trim`'s
  own measured `|up|`/`|dn|` magnitudes at the 10 µA trim code
  (`(10.04607 + 10.36930) / 2 = 10.20769 µA`, rounded to 10.208 µA).
  Using the mean magnitude (rather than, say, the 10 µA trim-code nominal)
  keeps the loop's average `|Icp|` close to the real `cp`'s own average,
  isolating the mismatch variable rather than also changing the loop's
  overall charge-pump gain. `IBP`/`ICP`/`IBN`/`ICN` bias pins are present
  for pin-count compatibility but carry no current — this diagnostic makes
  no claim about the real `cp`'s bias network, only about `UP`/`DN`
  current-magnitude symmetry.
  - **Node-order/direction sanity-checked before this script was written**,
    with a standalone two-line SPICE deck (`Vup`/`Vdn` pulse sources into
    the ideal `cp_ideal_eq` subckt driving a load cap): a single `UP` pulse
    raises `VOUT` by exactly `I·t/C` (matches `cp_leg_p`'s own polarity:
    `UP` high turns on the PMOS output switch, charging `VOUT` up), a
    single `DN` pulse lowers it by the same magnitude (matches
    `cp_leg_n`'s own polarity), and simultaneous equal-width `UP`+`DN`
    pulses leave `VOUT` exactly unchanged (net charge = 0, as the "exactly
    equal magnitude" substitution requires by construction).
- **Tooling**: `ngspice-47`, installed `~/share/pdk/ihp-sg13cmos5l`, arm64
  macOS host (same host as `RECORD-001`/`RECORD-002`, a different host/arch
  from `RECORD-003`'s x86-64 Linux run — see `RECORD-003`'s own note; no
  OSDI host-compatibility claim is made either way here since no
  `cap_cmomi`/`cap_cmomf` instance survives the same ideal-cap substitution
  `../testbench/run.sh` already applies).
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_closed_loop_icp_eq_diag.sh`.
  Writes `../corners/lock_trace_proposal_icpeq.csv` (49 reference cycles,
  same count as `RECORD-003`'s own Part B trace, 2.5 µs simulated, TAVG0
  window 2.0–2.5 µs — the SAME duration/window `RECORD-003`'s Part B used,
  so the final-20-cycle comparison below is apples-to-apples against that
  record's own baseline `../corners/lock_trace_proposal.csv`). **Runtime on
  this host, this session**: ~24 minutes wall (2.5 µs at this six-block
  netlist's rate — close to `RECORD-001`'s own ~1 ns/s arm64-macOS figure,
  even with the real `cp` replaced by a much cheaper behavioural model,
  since `pfd`/`vco` remain the dominant transistor-level cost).

## Result: the hypothesis is CONFIRMED — the static phase error collapses to floating-point noise

| Quantity | `RECORD-003` baseline (real, mismatched `cp`) | This diagnostic (ideal, exactly-equal `cp`) |
|---|---|---|
| `vctrl`: IC -> final | 2.46 V -> 2.387 V | 2.46 V -> 2.387 V (2.38696 V) |
| `vc_avg` (2.0-2.5 µs) | not separately tabulated (see `vctrl` range 2.349-2.420 V) | 2.387128 V (range 2.386795-2.387481 V) |
| Reference cycles observed | 49 | 49 |
| `Δf/f_ref`, final 20 cycles (`t` > 1.5 µs) | −0.0293% to +0.0068%, mean −0.0049% | −0.01317% to +0.00054%, mean ≈ 0% |
| Static phase error, final 20 cycles (`t` > 1.5 µs) | 9.110% to 9.196%, **mean 9.176%** | −0.02784% to +0.00054%, **mean −0.00235%** |
| Longest continuous run meeting the dual lock criterion | 4 cycles (`t` = 50–200 ns only) | **41 cycles, `t` = 450 ns to the end of the run (2.45 µs), continuous, zero drop-outs** |
| `lock_time` (row-7 definition: first cycle of a ≥20-consecutive-cycle run) | `None` | **450 ns** |

`vctrl`'s trajectory is essentially unchanged from `RECORD-003`'s own Part B
(`vc_avg` 2.387128 V here vs. `RECORD-003`'s reported 2.387 V average) —
confirming the ideal `cp` substitution did not perturb the loop's overall
operating point, only its `up`/`dn` current *symmetry*.

**The final-20-cycle window (identical definition to `RECORD-003`'s own,
`t` > 1.5 µs) still contains the tail of this run's own convergence
transient** (this trace's loop takes until ≈1.65 µs to fully settle, vs.
`RECORD-003`'s own trace settling by ≈1.25 µs) — reported honestly above
rather than cherry-picking a later, cleaner window. Restricting to the
fully-settled tail (`t` > 1.65 µs, 17 cycles) is far more dramatic: every
row's `Δf/f_ref` and phase error is at or below ~1e-11 fraction of `T_ref`
(literally floating-point noise from the edge-interpolation arithmetic, not
a measured nonzero value) — i.e., **exact cancellation**, exactly what the
"exactly equal magnitude, by construction" substitution predicts: with
`Icp_up = Icp_dn` in magnitude, the loop can hold zero net charge per
reference cycle with equal-width `UP`/`DN` pulses, which (given how `pfd`
derives pulse width from the `REF`/`FB` edge separation) requires zero
phase offset between `REF` and `FB`, not a nonzero one.

**Even using `RECORD-003`'s own, less-favorable final-20-cycle window, the
mean static phase error drops from 9.176% to −0.00235% of `T_ref`** — a
≈3,900× reduction, comfortably inside the 5% row-7 threshold with over
three orders of magnitude of margin. `Δf/f_ref` is likewise tighter than
`RECORD-003`'s own already-passing frequency-lock figure (peak-to-peak
spread 0.0137% here vs. 0.036% there). **This is not a partial, order-of-magnitude-plausible
match to the hypothesis — it is a near-total collapse of the residual to
numerical noise**, and the loop additionally holds the FULL row-7 dual
lock criterion (both `Δf/f_ref` < 1% AND `|`phase error`|` < 5%, ≥20
consecutive cycles) continuously from cycle 10 (`t` = 450 ns) through the
end of the simulated window (`t` = 2.45 µs, cycle 49) — 41 consecutive
cycles, vs. `RECORD-003`'s own longest run of 4 cycles before its phase
error grew past 5% again.

## Decision (issue #70's own Scope item 2 — recorded, not resolved silently)

**The residual is judged NOT acceptable as-is, and warrants a design-level
mitigation to `cp`'s current-mirror matching — not filed as a "characteristic
to tolerate."** Rationale:

1. **This is not a marginal, sub-threshold effect being second-guessed.**
   Removing only the `up`/`dn` current-magnitude mismatch — leaving every
   other block (`pfd`, loop filter, `vco`, divider) untouched — takes the
   loop from *failing* row 7's own 5% threshold by ≈1.8× to *passing* it by
   over three orders of magnitude, and from a longest lock-holding run of 4
   cycles to a full, unbroken 41-cycle run through the end of the observed
   window. A mechanism whose removal alone flips the row-7 verdict from
   fail to (dramatically) pass is a mechanism worth fixing at the source,
   not documenting around.
2. **The magnitude relationship is now bounded, not merely "plausible."**
   `RECORD-003` could only say a ≈3% current mismatch producing a ≈9%
   phase-offset response was "the right order of magnitude." This record
   shows the SAME ≈3% mismatch, in the SAME loop, accounts for
   essentially the ENTIRE observed static phase error (the residual after
   removing it is at simulator floating-point noise, not merely "smaller").
   There is no evidence of a second, comparably-sized mechanism this
   diagnostic would have missed.
3. **The reset-chain delay-symmetry candidate `RECORD-003` also named is
   now effectively ruled out as a material contributor** (issue #70's
   Scope item 3, addressed here even though the primary hypothesis was
   confirmed rather than ruled out): this diagnostic's `pfd` is the
   IDENTICAL 3-gate corrected reset chain `RECORD-003` used — unchanged
   between the baseline and this diagnostic — yet the phase error still
   collapses to ~0 when only `cp`'s current symmetry changes. If the
   reset-chain's own added delay (the #56 fix's extra `inv_hv` stage) were
   a material contributor to the ≈9.18% offset, this diagnostic (which
   does not touch the reset chain at all) could not have driven the
   residual this close to zero. This is consistent with `RECORD-003`'s own
   assessment that the reset-chain hypothesis was the less likely
   candidate (applies symmetrically to both `UP` and `DN` paths) — this
   record adds a second, independent line of evidence for that assessment
   rather than a new investigation of it.
4. **A ≈3% `up`/`dn` current mismatch is not an exotic corner** — it is
   `../../sg13cmos5l-cp-icp-trim`'s own already-measured `mos_tt`/27 C
   nominal, the SAME PVT point every record in this campaign treats as the
   easy case. Nothing here suggests the committed `cp` needs a change of
   topology, only tighter matching between its `cp_leg_p` (PMOS mirror,
   `w=24u l=1u` tail) and `cp_leg_n` (NMOS mirror, `w=8u l=1u` tail) legs —
   e.g., closer output-impedance/`Vth`-mismatch matching, a shared
   reference/cascode structure, or resizing to reduce the PMOS/NMOS
   mobility-ratio-driven asymmetry. The specific mitigation approach is a
   design task, not resolved here.

**Follow-up filed**: issue #72, a dedicated design issue to tighten `cp`'s
current-mirror matching, informed by this record's own bound (mismatch of
this magnitude is directly responsible for the observed row-7 failure) —
see "Follow-up" below.

## What this does not bound

- **Single PVT point only** (`mos_tt`/`res_typ`/27 C/3.3 V, same as
  `RECORD-001`/`RECORD-002`/`RECORD-003`)** — see `../corners/matrix.md`.
  No corner sweep of any number in this record exists. In particular, this
  record does not claim the ≈3% mismatch-to-≈9%-phase-offset relationship
  holds at other corners, only that it is the dominant mechanism AT this
  corner.
- **Not a claim that any specific mitigated `cp` design meets row 7** —
  this record only shows that *removing* the current-magnitude mismatch
  (via an idealized, diagnostic-only substitution) collapses the offset;
  it does not design, size, or verify a real mitigated `cp`.
- **The exact analytic gain from current mismatch to phase offset is still
  not derived** (`RECORD-003`'s own caveat, unchanged here) — this record
  confirms the mechanism empirically (via substitution and comparison), not
  analytically.
- **Part A's own non-lock remains independently over-determined by the
  `divider_chain` defect (issue #36, still open as of this record)** — not
  re-tested here; this record only touches Part B's proposal deck, per
  issue #70's own Scope.
- **Row 7's own 5% static-phase-error threshold is not revisited here**
  (`RECORD-001`'s own re-derivation, unchanged) — this record neither
  loosens nor re-justifies it; the residual with the real `cp` still fails
  it, and this record's own decision above is that the fix belongs in
  `cp`, not in a relaxed threshold.
- **This diagnostic's `cp` substitution is confined to this diagnostic
  run only** — `design/sg13cmos5l/cp.sch`, `design/sg13cmos5l/netlist/cp.spice`,
  and `../netlist-snapshots/cp.spice` are all untouched by this record; the
  ideal `.subckt cp` lives only in
  `../testbench/run_closed_loop_icp_eq_diag.sh`'s own inline Python-generated
  bundle, never written to any committed netlist path.

## Row-by-row disposition (updates `RECORD-001`'s/`RECORD-002`'s/`RECORD-003`'s
own call, does not edit them)

- **Row 7 (lock time)**: still `insufficient-evidence` for the COMMITTED
  design — the real `cp`'s own `up`/`dn` current mismatch, at this single
  measured PVT point, is now the confirmed dominant mechanism keeping Part
  B's proposal loop from meeting the row-7 dual criterion. `RECORD-003`'s
  own frequency-lock finding is unaffected and unchanged (already passing).
  What has changed: the previously-unconfirmed hypothesis for the static
  phase error is now `confirmed`, with the causal chain bounded rather
  than merely plausible, and a design-level mitigation (`cp` current-mirror
  matching) is the identified next step rather than an open question. This
  is not itself a row-7 pass for the committed design — no mitigated `cp`
  has been built or verified — but it materially narrows what remains
  before row 7 can be closed.
- **Row 10 (reference spur)**: unaffected by this record — still
  `insufficient-evidence`, unchanged from `RECORD-003`'s own disposition
  (this diagnostic's deck is not the committed design and was not run with
  the intent of a row-10 measurement).
- **Row 11 (power)**: unaffected by this record — the ideal `cp`
  substitution draws no supply current by construction (`i_cp` = 0 in this
  record's own `.meas` output), so this record makes no power claim about
  any `cp` domain; `RECORD-003`'s own row-11 figures are unchanged.

## Follow-up

Filed as issue #72: tighten `cp`'s `up`/`dn` current-mirror matching
(`cp_leg_p`/`cp_leg_n`, `design/sg13cmos5l/cp.sch`) — this record's own
decision (above) that the ≈9.18% row-7-failing static phase error traces
almost entirely to that mismatch, not to the reset-chain delay symmetry or
another mechanism.
