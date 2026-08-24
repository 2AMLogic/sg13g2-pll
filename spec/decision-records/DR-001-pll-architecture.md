# DR-001: PLL architecture — loop type, VCO topology, feedback divider

- **Status**: proposed
- **Date**: 2026-08-24
- **Decided by**: Builder agent, issue #8
- **Related**: #1 (porting plan this record consumes), #6 (T1 checklist —
  this record and DR-002 satisfy item 1), #7 (commit design sources — blocked
  on this record and DR-002 per #8's own problem statement), #8 (this issue),
  DR-002 (supply/device-flavor — settles the remaining per-element bipolar
  questions this record scopes out, and the CMOS device flavor these
  decisions are drawn against)
- **Consumes**: `spec/porting-plan.md` §1.1 ("Architecture decisions"),
  §1.2 row 3 (multiplication ratio), §2.1 ("The VCO — the block BiCMOS
  changes most"), §2.3 ("The dividers"), and the "Summary" section's item 1
  ("survey the same four questions gf180-pll's DR-001 surveyed... plus a
  fourth, new question")
- **Sibling precedent cited throughout**: `2AMLogic/gf180-pll`
  `spec/decision-records/DR-001-pll-architecture.md` (fetched via `gh api`
  from that repo directly — the byte-for-byte source, not a from-memory
  reconstruction); `2AMLogic/sky130-pll`
  `spec/decision-records/DR-001-supply-flavor-scope.md` (same method) for
  the divider-architecture disagreement this record must resolve on its own
  merits

**Format note.** Like gf180-pll's own `DR-001`, this record deliberately
carries three decisions (loop type, VCO topology, divider architecture)
because they are mutually constraining — see "Why these are one decision"
below — plus a fourth topic (bipolar VCO insertion) that the porting plan's
own Summary names as the new axis neither sibling's survey had to weigh.
This repo's `spec/decision-records/TEMPLATE.md` (adapted from gf180-pll's own
template) states "one decision per record," and gf180-pll's own `DR-001`
already establishes the precedent for deviating from that rule when the
decisions are genuinely coupled — followed here rather than re-litigated. The
remaining bipolar questions the porting plan raises (bias reference §2.2,
charge-pump cascode §2.2, divider first stage §2.3) are **not** decided here
— they are per-element device-flavor questions, settled together with the
CMOS supply-flavor choice in DR-002, per that record's own scope.

---

## Decision summary

| # | Question | Decision | Basis |
|---|---|---|---|
| 1 | Loop type | Type-II charge-pump PLL: tri-state PFD → charge pump → **passive** 2nd-order (series R + C1, shunt C2) filter → ring VCO → feedback divider. No active filter, no opamp in the loop path. | Both siblings converged here independently; the `ω_c ∝ Icp·R·f_ref` self-compensation argument is a current-starved-ring property, not a device-flavor or process property |
| 2 | VCO topology | **Single-ended, current-starved CMOS inverter ring** (ported default), odd stage count, coarse band-select + fine analog Vctrl. **HBT-based LC-tank oscillator explicitly considered and rejected** for v1. | Porting-plan §2.1; disposition against (a) the flow's phase-noise-evidence gap and (b) the 20:1 continuous tuning-range requirement |
| 3 | Feedback divider | **Cascaded ÷2/3 (Vaucher) chain**, static CMOS, VCO-clocked final retiming flop — matching gf180-pll's `DR-001` Decision 3, **not** sky130-pll's synchronous down-counter | N = 4 must be reachable without a structural floor (rules out pulse-swallow); DR-002's 3.3 V thick-oxide-throughout flavor choice reproduces gf180-pll's own "no matching digital library at this voltage" argument for custom-cell-count economy |

Numbers cited below from gf180-pll are calibration/sanity-check references
only, exactly as porting-plan.md frames them — none is a SG13G2 target. Every
number here is disposition-only; the block's own device-characterization and
tuning-range campaigns (this repo's forthcoming `#4`-equivalent issues) own
the real sizing.

---

## Context

`spec/porting-plan.md`'s own closing Summary names this record as the first
of two prerequisites gating #7 (committing design sources) and every
remaining T1 checklist item in #6. Three of its four questions are the same
ones gf180-pll's `DR-001` surveyed for its own process; the fourth — which
bipolar insertions, if any — exists only because SG13G2 is the first process
in this fleet with SiGe HBTs available at all (porting-plan §2 preamble:
"Neither gf180mcu... nor sky130... had a bipolar option at all").

The spec rows that actually drive this record (porting-plan §1.2, all
currently "re-derive" — no SG13G2 number is ratified yet):

- **Output band**: unknown, re-derive (row 1) — but the **20:1 continuous
  tuning-range shape** of the requirement carries over as a structural
  constraint even before the actual band numbers are known, per gf180-pll's
  own row 1 and sky130-pll's independent convergence on the same shape.
- **Multiplication ratio**: **port the requirement N ⊇ 4–64, no holes, as-is**
  (row 3) — this is the number that most directly disqualifies one divider
  family below.
- **Loop bandwidth / phase margin**: port the *sampled-loop stability
  criteria* (`f_c < f_ref/10`, ≥45° PM) and the *mechanism* (coarse Icp trim)
  as-is (row 6/6a) — this is what makes Decision 1 below portable independent
  of SG13G2's own numeric Kvco/Icp values.

## Why these are one decision

The coupling argument is identical to gf180-pll's own `DR-001`, restated
against SG13G2's own devices rather than assumed to transfer by citation
alone:

1. A **current-starved** ring has `f_osc ∝ I_ctrl`, so `Kvco = ∂f/∂V ∝ f_osc`
   — this is a property of the *topology* (current starving), not of gf180's
   180 nm-class devices specifically, so it re-derives on SG13G2 the same way
   it did on sky130 (porting-plan §1.1 row 2, "device swap, topology as-is").
2. The loop's unity-gain frequency for a type-II CP-PLL is
   `ω_c ≈ Icp·Kvco·R / (2π·N)`; with `N = f_out/f_ref` and `Kvco ∝ f_out`, the
   `f_out` terms cancel, so `ω_c ∝ Icp·R·f_ref` is approximately invariant
   across the whole output band and N range — this is what makes a **fixed**
   passive filter (Decision 1) viable, and it depends on Decision 2 (a
   current-starved ring, not a supply-regulated one or an HBT tank) holding.
3. The divider (Decision 3) is constrained by the same band: whatever
   family is chosen must keep dividing at the bottom of the band and during
   slow acquisition transients, which rules out any dynamic logic family
   regardless of which CMOS flavor the divider is built on (DR-002).

Recording these separately would hide exactly this coupling, which is why
this record follows gf180-pll's own precedent for keeping them together.

---

# Decision 1 — Loop type

## Decision

**Confirmed as-is**: classic type-II charge-pump PLL — tri-state
phase-frequency detector → charge pump → **passive** second-order loop
filter (series R + C1, shunt C2) → ring VCO → feedback divider. No active
filter, no opamp in the loop path (a bias buffer that never carries loop
signal charge remains compatible, per gf180-pll's `DR-005` four-condition
test, which this record adopts as the same test for any SG13G2 bias element
touching the loop-filter node). Filter R and C are fixed; the only
programmability is a coarse charge-pump-current trim, sized once SG13G2's
own Kvco table exists (porting-plan §1.2 row 6/6a).

## Alternatives considered

Both siblings' `DR-001`-equivalents (gf180-pll `DR-001` Decision 1) already
ran this survey — sub-sampling/sampling PLL, injection-locked clock
multiplier, all-digital PLL (TDC + digital filter + DCO), active loop filter,
programmable R/C filter banks — and rejected every alternative for reasons
that are **topology and flow properties, not gf180-specific device
properties**: the phase-noise-evidence gap (ngspice has no direct `.noise`
result for a free-running oscillator, independent of device class —
porting-plan §1.2 row 9, "port the omission as-is"), the lack of a matching
digital standard-cell library at any SG13G2 CMOS voltage this design is
likely to use (an ADPLL's digital loop filter has the same synthesis-library
problem on SG13G2 that it had on gf180mcu's 5 V-only libraries), and the
`Kvco ∝ f_out` self-compensation that a programmable filter bank is designed
to work around but this topology does not need. **This record does not
re-run that survey independently** — it confirms the same conclusion holds
because the reasons cited are process-independent, and names the one place
SG13G2 genuinely adds a new alternative worth naming on its own terms: an
HBT-based tank oscillator, which is a Decision 2 question (VCO topology),
not a Decision 1 question (loop type stays the same either way).

## Consequences

- Same as gf180-pll's own: one fixed passive filter spans the whole
  (not-yet-derived) SG13G2 output band and N range, so there is one
  loop-dynamics story to verify, not one per configuration.
- The filter's actual R/C values, the Icp-trim code table, and the ζ/`f_c`
  sizing are **entirely re-derive** (porting-plan §1.2 row 6/6a) — this
  decision fixes the topology, not a single number in it.

---

# Decision 2 — VCO topology

## Decision

**Ported default: single-ended, current-starved CMOS inverter ring**, odd
stage count, coarse band-select (digital, static configuration input) + fine
analog Vctrl through a source-degenerated V→I converter into the starving
bias mirror — the same technique-level description porting-plan §1.4 carries
over from gf180-pll's `design/README.md`. Stage count, band-overlap plan, and
the Kvco-vs-band-vs-corner table are **not** decided here; they are re-derived
from a SG13G2-specific tuning-range campaign (this repo's own `#4`-class
issue, following gf180-pll `DR-003`'s precedent that these numbers are only
real once extracted, corner-swept data exists).

**The HBT-based LC-tank oscillator is explicitly considered and rejected for
v1**, per porting-plan §2.1's own analysis, which this decision adopts as its
reasoning rather than re-deriving independently (the analysis is sound and
SG13G2-specific already):

1. **Phase-noise-evidence gap.** An LC-tank oscillator's headline advantage
   over a ring is phase noise. This repo's flow (xschem + ngspice) cannot
   produce a direct `.noise` result for a free-running oscillator of *either*
   topology — CLAUDE.md's "no claim without a testbench" then applies
   identically to a tank as it did to sub-sampling/ILCM architectures both
   siblings already rejected on this exact evidentiary ground (gf180-pll
   `DR-001` Decision 1, "Alternatives considered"). Choosing an LC-tank VCO
   for phase noise reproduces an argument this fleet has already rejected
   once, on a different justification.
2. **Tuning-range requirement.** A varactor-tuned LC tank commonly reaches
   1.3–2:1 tuning range before quality/linearity degrade badly — against the
   **20:1** continuous band a current-starved ring delivers and every carried
   spec row in porting-plan §1.2 assumes (row 1). This is the harder
   objection of the two: even setting the evidence gap aside, an LC tank does
   not structurally meet the requirement this block exists to satisfy.

**Disposition: rejected for v1, not merely deferred.** Unlike the bias
reference and divider-first-stage bipolar questions (settled in DR-002),
which are named and deferred pending a trigger condition, the LC-tank
oscillator core is rejected outright because the tuning-range shortfall is a
**requirement mismatch**, not a data gap that future evidence could close —
more tank-quality-factor data would not change a 1.3–2:1 range into 20:1.
Revisit only if the ratified output-band requirement itself narrows enough
(porting-plan §1.2 row 1, currently unknown) to fall inside an LC tank's
realistic range — at which point this would be a superseding record, not an
amendment.

## Alternatives considered

- **HBT-based LC-tank oscillator (cross-coupled pair or Colpitts)** —
  rejected, see above.
- **Supply-regulated ring, fully differential ring, pseudo-differential
  ring, switched-capacitor-tuned ring** — the same CMOS alternatives
  gf180-pll's `DR-001` Decision 2 considered and rejected on tuning-range and
  power/complexity grounds specific to a 20:1 requirement (regulated-ring
  rejection: `f ∝ (V_reg − V_th)^~1.3`, so 20:1 range needs `V_reg` spanning
  threshold to rail, which breaks regulation; differential/pseudo-differential:
  extra bias current, replica-bias/level-shifter complexity, no
  quadrature-output requirement to justify it). These arguments are
  topology-vs-requirement arguments, not gf180-specific device arguments, so
  they re-apply on SG13G2 without modification. **Not re-litigated in full
  here** — cited by reference to avoid duplicating gf180-pll `DR-001`'s own
  reasoning, which this record adopts rather than repeats.
- **An HBT-based bias/reference element inside an otherwise-CMOS ring** (not
  the oscillator core itself) — this is a smaller, separable question
  (porting-plan §2.1, penultimate bullet) that does not reopen the
  ring-vs-tank decision above; settled in DR-002 alongside the other
  per-element bipolar questions.

## Consequences

- Same supply-noise risk gf180-pll `DR-001` names for this topology: a
  current-starved single-ended ring has the weakest supply rejection of the
  CMOS options considered, and it is being accepted again on SG13G2 for the
  same tuning-range reason. Whichever device-characterization campaign
  extracts SG13G2's own Kvco table must also produce a supply-noise/jitter
  testbench, not just a clean-supply sweep.
- **Band select remains a static configuration input, no auto-calibration
  FSM in v1**, consistent with porting-plan §1.1's carried-as-is scope call
  (both siblings made this call independently).
- Stage count, band-overlap, and Kvco-table numbers are entirely open until
  the tuning-range campaign runs — this decision fixes the *topology*, which
  is what #7 (commit design sources) needs to draw the VCO schematic against;
  it does not fix a single transistor size.

---

# Decision 3 — Feedback divider architecture

## Decision

**Cascaded ÷2/3 (Vaucher-style modular) cells, static CMOS throughout, a
final retiming DFF clocked by the VCO** — matching gf180-pll's `DR-001`
Decision 3 in family, **not** sky130-pll's synchronous down-counter with
programmable reload. Exact chain length (cell count) is re-derived once
SG13G2's own top-of-band N requirement is known (porting-plan §1.2 row 3
ports the *requirement*, N ⊇ 4–64 with no holes, as-is; the specific chain
length that covers it is a sizing question, not an architecture question).

Retiming discipline carries over as-is (porting-plan §1.1, "Retiming
discipline" row): the feedback edge the PFD sees is a single flop's clk→Q
after a VCO edge, independent of N — this is what keeps the PFD's static
phase offset from moving when N is reprogrammed, and the argument for it is
topology-independent.

## Alternatives considered

Porting-plan §1.1 states this explicitly as "a live disagreement between the
two ported references, not something to average" — gf180-pll chose the ÷2/3
cascade, sky130-pll built a synchronous down-counter "without a decision
record arguing the choice against N = 4." This record resolves the
disagreement on SG13G2's own merits rather than by precedent-counting:

- **Pulse-swallow counter (÷P/P+1 prescaler + program/swallow counters)** —
  rejected on the same hard range violation gf180-pll `DR-001` found: the
  structure requires `M ≥ S`, which floors the continuously reachable N at
  roughly `P²`/`P·(P−1)` — around N ≥ 12–16 for the smallest practical
  prescaler (÷4/5). Porting-plan §1.2 row 3 ports N ⊇ 4–64 with **no holes**
  as a requirement, and N = 4 sits inside the region a pulse-swallow floor
  would need a bypass mode to cover. Disqualified on the same range grounds
  gf180-pll disqualified it on, independent of device flavor.
- **Synchronous programmable counter (binary counter + comparator + reload)**
  — this is sky130-pll's own choice, and it is **not** disqualified by the
  N = 4 range test (a synchronous down-counter has no structural floor the
  way pulse-swallow does). It is rejected here on the same power and
  custom-cell-count grounds gf180-pll's `DR-001` argued against it: every
  flop toggles at the full VCO rate, so a counter wide enough to cover N up
  to 64+ burns materially more dynamic power than the ÷2/3 chain's first
  cell (which is the only cell running at the full rate; every subsequent
  cell in the cascade halves it). **Whether SG13G2's own digital standard-cell
  library at some voltage could make a synchronous counter cheap to build
  does not change this argument** — DR-002 settles the whole design
  (including the digital majority) on the same CMOS flavor as the analog core
  specifically so there is no matching-digital-library shortcut available
  here, reproducing gf180-pll's own "no library at this voltage" situation
  rather than sky130-pll's "reuse the stdcell flops" situation. Given that,
  the ÷2/3 chain's "one cell verified once, replicated" economy (gf180-pll
  `DR-001` Consequences) is the cheaper verification path on SG13G2 too.
- **Ripple (asynchronous) counter with decode/reload** — rejected on the
  same grounds gf180-pll's `DR-001` rejected it: output delay accumulates
  with the programmed chain length (N-dependent static phase offset and loop
  delay) and piles per-stage delay noise into the feedback edge, directly
  against the period-jitter spec row (porting-plan §1.2 row 8).
- **Dynamic logic (TSPC/E-TSPC) for the first cell** — rejected as the
  default for the same reason gf180-pll rejected it: dynamic logic has a
  minimum operating frequency, and this divider must keep dividing at the
  bottom of the (not-yet-known) output band and slower still during
  acquisition transients. Retained as the same **targeted, swappable
  fallback** gf180-pll reserved for a stretch-frequency contingency
  (porting-plan §2.3's own framing: "the pragmatic reading, absent a
  demonstrated speed problem, keep static CMOS as the default... treat a
  bipolar/ECL first-stage swap as the same kind of targeted fallback").
  **This record explicitly defers, rather than commits to, an ECL/CML
  first-stage swap** — see DR-002, which owns the remaining bipolar
  per-element questions and states the trigger condition.

## Consequences

- **One cell to verify, replicated** — the cheapest evidence path available,
  matching gf180-pll `DR-001`'s own consequence and reasoning.
- **Interface contract to the PFD**: feedback edge is the retiming DFF's
  rising edge; pulse width ≥ PFD reset delay; feedback delay is constant vs.
  N. This is the same contract porting-plan §1.4 already lists as "the one
  technique both siblings kept even though their divider architectures
  diverge."
- **Divider power scales as ~2× the first cell**, not `k×`, since each
  subsequent cell runs at half the previous cell's rate — the first cell is
  the one that must be optimized, and (per DR-002) it is drawn in the same
  CMOS flavor as the rest of the design, so no cross-domain interface exists
  at this boundary.
- **N > (chain length)'s natural ceiling is reachable but unspecified** —
  same caution gf180-pll names: do not let spare coverage leak into the spec
  table as a claim without corner evidence.
- Chain length, per-cell sizing, and the retiming setup-margin closure at the
  slow corner are entirely open until #11-class (feedback-divider) design/sim
  work runs against SG13G2's own extracted devices.

---

## Consequences (whole-architecture)

**What this makes possible**

- #7 (commit design sources) can proceed against a fixed architecture: loop
  type, VCO topology family, and divider family are all decided, so the
  schematics committed there have a target to draw against instead of a
  blank page.
- A single fixed loop filter spans whatever output band SG13G2's own
  tuning-range campaign finds, so there is one loop-dynamics story to verify.
- The divider is one custom cell replicated, the cheapest verification path
  available given DR-002's single-flavor CMOS choice (no matching digital
  library at the chosen voltage, same situation gf180-pll faced).

**What this makes harder / what is accepted**

- Supply-noise-induced jitter remains the top technical risk, by
  construction, exactly as it was for gf180-pll: the delay cell with the
  weakest supply rejection is the one that spans a 20:1 range.
  Whichever future tuning-range/jitter campaign runs must include a
  supply-noise testbench, not just a clean-supply sweep.
- The LC-tank VCO option this port uniquely had available is explicitly
  foreclosed for v1 — if a future requirement narrows the output-band
  requirement enough to reopen it, that is a superseding record, not an
  amendment to this one.
- No auto-band-calibration FSM, no glitch-free on-the-fly N switching — both
  carried over as v1 scope calls from both siblings' own precedent.

**What must be re-derived before any of this enters a ratified spec**

Every number implicit in this record (Kvco shape, stage count, chain length,
filter R/C) is a disposition-only placeholder for the *topology* choice, not
a design value. Porting-plan §1.2's own per-row disposition table
("re-derive" for nearly every numeric row) governs what happens next: a
SG13G2-specific device-characterization campaign, then a VCO tuning-range
campaign, then loop-filter/charge-pump sizing — each producing its own
decision record or evidence record, per this repo's normal `spec/`/`sim/`
discipline, before `spec/target-spec.md` (or this repo's equivalent) can
carry a ratified number.
