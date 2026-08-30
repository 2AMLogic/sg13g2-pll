# DR-006: `lock_detector`'s `f_ref`-dependent lock threshold is accepted, not redesigned

- **Status**: ratified
- **Date**: 2026-08-30
- **Decided by**: Builder agent, issue #77
- **Related**: #66 (Part of #16, Chipalooza Challenge #6 — landed the
  `schmitt_hv` rewiring + `XMPD` re-size this record's residual was split
  from), #77 (this issue), DR-005 (ratifies the 3.5–24.4 MHz `f_ref` range
  this record's measured span is quoted against)
- **Consumes**:
  `sim/sg13cmos5l-lock-detector-window/records/RECORD-003-hysteresis-fix.md`
  ("Term 2" and "What this does not bound" — the record that first measured
  and named this property), `spec/porting-plan.md` row 16 (the criterion set
  this decision confirms is **not** touched), `design/README.md` §
  "SG13CMOS5L port" (where the resulting bound is now stated per this
  record's Decision)

---

## Context

`lock_detector`'s integrating node (`VWIN`) settles to a balance between a
continuous, always-on pull-up (`XRPU`, `rhigh`) charging over one **reference
period** and an event-gated pull-down (`XMPD`) discharging over one `WIDE`
(out-of-window) pulse:

```
VWIN  ≈  VDD  −  I_sat(XMPD) · R(XRPU) · (τ − t_win) / T_ref
```

`T_ref` sits in the denominator of the slope, so both the assert/de-assert
thresholds and the phase-error hysteresis scale with `T_ref` — i.e. with
`1/f_ref`. `spec/porting-plan.md` row 2, as amended by DR-005, spans
3.5–24.4 MHz (a 7× range), so this block's own detection threshold moves by
a comparable factor across the ported operating range *by construction of
the topology*, independent of how `XMPD` is sized. RECORD-003 (issue #66)
measured this directly rather than arguing it:

| | 3.5 MHz (`T_ref` = 285.7 ns) | 24.4 MHz (`T_ref` = 41.0 ns) |
|---|---|---|
| Assert threshold | 5.00× window = 33.3 ns = **11.7% of `T_ref`** | 1.50× window = 10.0 ns = **24.4% of `T_ref`** |
| De-assert threshold | 8.00× window = 53.3 ns = **18.7% of `T_ref`** | 2.25× window = 15.0 ns = **36.6% of `T_ref`** |
| Hysteresis | 3.00× window = 20.0 ns = 7.0% of `T_ref` | 0.75× window = 5.0 ns = 12.2% of `T_ref` |

**No `spec/porting-plan.md` row is violated by this** — row 16's own
"assert window" criterion is `twin_r`, `delaywin_hv`'s own propagation
delay, which does not depend on `f_ref` at all and is met at every
corner RECORD-003 measured (3.688–11.24 ns against the ≥2.5 ns floor,
102/102 points). What issue #77 asks this record to settle is a design
judgement row 16 does not state: is a lock-threshold that moves by
roughly 2× (as a fraction of `T_ref`) across the ported reference range
the intended behaviour of this topology, or an artifact this repo should
design out by replacing the continuous pull-up with a reference-gated
charge source?

### Fleet comparison (issue #77 scope item 1)

Per this repo's own CLAUDE.md ("the PDK is the variable, not the design"),
the deciding comparison is against the fleet siblings this block is a port
of, read directly rather than assumed:

**`2AMLogic/gf180-pll` has the identical topology.** Its
`design/lock_detector.sch` (fetched via the GitHub API, commit tree at time
of writing) instantiates exactly the same three-device integrator this
repo's block does:

- `MUPW` — a single, always-on, deliberately weak long-channel PFET
  (`W=0.22u L=20u`) tied directly across `VDD`→`VWIN`. There is no gating
  signal into this device at all: it is a continuous pull-up exactly like
  this repo's `XRPU`, differing only in device class (a weak FET here vs. a
  `rhigh` resistor in this repo — DR-002/DR-003's own device-flavour
  divergence, not a topology difference).
- `MDNW` — an NFET (`W=2u L=0.5u`) gated by `WIDE` (`ERR . ERRD`, the same
  "error pulse outlasted the comparator window" signal this repo's `XMPD`
  is gated by), discharging `VWIN` hard on every out-of-window pulse.
- `MCW` — the integrating capacitor (`W=30u L=6u` NFET cap), playing the
  same role as this repo's `XCW`.

gf180-pll's own schematic header states the mechanism in the same terms this
repo's RECORD-003 derives independently: *"Deliberate asymmetry: assert is
SLOW (weak pull-up must charge MCW, i.e. the error must stay inside the
window for many reference cycles) and deassert is FAST (one out-of-window
error pulse dumps the node)."* This is architecturally the same "continuous
pull-up integrates against a per-cycle coincidence pulse" mechanism this
issue is asking about, not a coincidentally similar one.

**gf180-pll's own most recent lock-detector record
(`sim/lock-detector/records/20260802-050119-c24ee3a.md`, fetched directly)
names this exact `f_ref`-dependence as a stated limitation of the block, and
does not redesign it out:**

> *"Limitation -- low end of the reference range. The assert time is set by
> a weak pull-up charging a MOS capacitor, i.e. an absolute time, not a
> count of reference cycles. Reliable deassert requires that hold-off to be
> much longer than one reference period; at the 25 MHz characterised here
> that is tens of reference cycles, but extrapolating the same hold-off to
> the 1 MHz bottom of the draft reference range leaves only of order one
> reference period, where the flag would be expected to chatter. That
> extrapolation is a hand argument, not a measured result -- this record
> makes no claim at 1 MHz."*

This is the same physics this record's Context describes (an absolute-time
integrator whose ratio to `T_ref` moves with `f_ref`), stated by the fleet
sibling as an accepted, disclosed limitation of its own record — not
resolved by a reference-gated redesign in any of that repo's three
superseding lock-detector records (`20260731-095213-0bffe91` →
`20260731-162119-0a12e6c` → `20260802-050119-c24ee3a`, the last two
superseding for **tooling migration reasons only**, per each record's own
"Supersedes" field — never for a topology change).

**`2AMLogic/sky130-pll` has no lock detector block at all.** Its
`design/` tree (fetched via the GitHub API) contains `divider`,
`loop-filter`, `pfd-cp`, `top`, and `vco` only — no `lock_detector` schematic,
symbol, or `sim/` slug of any name resembling one. This sibling therefore
offers no comparison data point for this specific question; the fleet
comparison rests on gf180-pll alone.

## Decision

**The `f_ref`-dependent lock threshold is accepted as an intended property
of this topology, not redesigned.** No reference-gated integrator (issue
#77 scope item 2) is built. This is a direct port of the fleet's own
disposition: the sibling block gf180-pll ported from (a) has the identical
topology, (b) exhibits the identical `T_ref`-proportional threshold
mechanism by the same physical argument, and (c) has already stated this as
an accepted, disclosed limitation across three of its own lock-detector
records rather than fixing it with an architecture change. Per this repo's
own CLAUDE.md, "anything that breaks should be assumed to be the PDK, the
deck, or the tools before it is assumed to be the circuit" — this is not
something SG13G2/SG13CMOS5L broke; it is the topology's own behaviour,
reproduced faithfully from the fleet, already known to the fleet, and never
treated there as a defect requiring a different block.

**The resulting bound is stated explicitly** (issue #77 scope item 3, see
`design/README.md`): at the DR-005-amended `f_ref` range (3.5–24.4 MHz), the
landed `sg13cmos5l` `lock_detector`'s assert/de-assert thresholds fall
between roughly 12% and 37% of a reference period (RECORD-003's measured
range, restated in full above), and this fraction is expected to widen
further below 3.5 MHz by the same extrapolation gf180-pll's own record
makes (not measured here — row 2's amended floor is 3.5 MHz and this record
does not extend the sim campaign below it).

## Alternatives considered

- **Build a reference-gated integrator (issue #77 scope item 2)** — rejected
  for this pass. This would replace `XRPU`'s continuous charge with a charge
  source that delivers a fixed quantity of charge once per reference period
  (e.g. a one-shot pulse-gated pull-up synchronized to the reference edge),
  making the balance `T_ref`-independent by construction. This is a
  legitimate design and would be a strictly "better" lock detector by this
  one metric — but it is **a different block**, not a resize: it needs its
  own schematic, its own decision record under DR-001's architecture (a new
  gating input into `lock_detector`, most likely a reference-edge tap that
  does not currently exist at this block's boundary), and the whole row-16
  campaign (`sim/sg13cmos5l-lock-detector-window/`) re-run against it,
  exactly as issue #77 itself says. Building it is not warranted by any
  failing spec row (row 16 is fully met, per RECORD-003) and is not what the
  fleet itself has done with the identical topology across three of its own
  records — so it is not undertaken here. If a future requirement
  (e.g. an `f_ref` floor pushed materially below 3.5 MHz, where gf180-pll's
  own hand argument predicts chatter) makes the `T_ref`-dependence a real
  problem rather than a stated bound, this alternative is the correct one to
  revisit, and this record's existence is what should trigger that
  reconsideration rather than a silent resize attempt.
- **Treat the absence of a sky130-pll comparison point as blocking** —
  rejected: issue #77's own scope names gf180-pll and sky130-pll as the
  comparison, not gf180-pll alone; sky130-pll simply not having built a lock
  detector yet is itself informative (it has made no competing design choice
  to weigh against gf180-pll's), and gf180-pll alone already supplies a
  same-topology, same-behaviour, already-disclosed data point sufficient to
  decide item 1 per issue #77's own stated framing ("if the fleet's lock
  detectors have the same topology and the same behaviour, the answer is
  probably 'accepted, and stated'").

## Consequences

**What this makes possible**: issue #77 is closed without a topology change,
`XMPD`'s sizing (RECORD-003's two-sided measured bound) is not reopened
(issue #77's own Non-goals), and no new `sim/` campaign is owed by this
decision.

**What is accepted, stated plainly**: a consumer gating logic on this
block's `LOCK` output should treat the assert/de-assert phase-error
thresholds as **`f_ref`-dependent, spanning roughly 12–37% of a reference
period at the ported 3.5–24.4 MHz range** (RECORD-003's measured figures),
not as a fixed phase-error number. This is now stated in `design/README.md`
so it is discoverable without reading a `sim/` record, per issue #77 scope
item 3.

**What remains open**: if a future `f_ref` floor requirement pushes
materially below 3.5 MHz, gf180-pll's own (unmeasured, hand-argued)
extrapolation predicts chatter as the hold-off collapses toward one
reference period — this repo has not measured that regime either (RECORD-003
stops at row 2's amended 3.5 MHz floor) and would need to before extending
any claim there. This decision does not close that door; it only settles
that the currently-ported range does not need it closed today.
