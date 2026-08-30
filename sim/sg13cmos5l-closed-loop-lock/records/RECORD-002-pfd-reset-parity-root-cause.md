# RECORD-002: root cause of Part B's non-convergence — PFD self-reset inverter-parity defect

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #50 (Part of #16) — follow-up to #37's own `RECORD-001`, which
  found Part B (the proposal loop: `R1` × 20 + a behavioural divide-by-64,
  both known defects deliberately set aside) drifts monotonically away from
  lock over its full 2.5 µs window, ruled out a simple `cp` `UP`/`DN`
  pin-swap as the explanation, and left the actual cause **undetermined**.
- **This record does not edit `RECORD-001`** (append-only, per this
  directory's own convention) — it resolves the open question that record's
  own "What this does not bound" section left for #50.
- **DUT**: two NEW, standalone diagnostics, neither of which is part of
  `../testbench/run.sh`'s own two decks and neither of which touches
  `../corners/results_as_drawn.csv` / `results_proposal.csv` /
  `lock_trace_as_drawn.csv` / `lock_trace_proposal.csv` (RECORD-001's own
  evidence is untouched):
  1. `../testbench/run_pfd_diag.sh` + `../testbench/tb_pfd_only.sp.tmpl` —
     a **standalone, PFD-only** gate-level testbench (Scope item 1: "read
     the gate-level `pfd.spice` behaviour directly, or instrument a
     standalone PFD-only testbench").
  2. `../testbench/run_closed_loop_pfdfix_diag.sh` — a **confirmatory
     closed-loop control run**, structured exactly like `RECORD-001`'s own
     400 ns `UP`/`DN`-pin-swap control run: Part B's own deck, unchanged,
     with ONLY the `pfd` block's netlist swapped for a diagnostic patch (see
     below).
- **Tooling**: `ngspice-47`, installed `~/share/pdk/ihp-sg13cmos5l`, arm64
  macOS host — same host/tooling as `RECORD-001`, same OSDI constraint
  discussion (irrelevant to diagnostic 1: `pfd.spice` instantiates no
  `cap_cmomi`/`cap_cmomf`, confirmed by grep against the frozen snapshot).
- **Reproduce**:
  `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ../testbench/run_pfd_diag.sh`
  (writes `../corners/pfd_polarity_diag.csv`, ~seconds) and
  `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ../testbench/run_closed_loop_pfdfix_diag.sh`
  (writes `../corners/lock_trace_proposal_pfdfix.csv`, ~400 s wall on this
  host — the six-block netlist's own measured ~1 ns/s rate, `RECORD-001`
  "Why these durations").

## Root cause: found, and it is Scope item 1 (PFD-level), not a wiring polarity swap

`../netlist-snapshots/pfd.spice`'s self-reset chain (the frozen, committed
netlist every closed-loop deck in this directory uses):

```
XLU set_up reset UP net1 VDD VSS srlatch
XLD set_dn reset DN net2 VDD VSS srlatch
XNR UP DN reset_raw VDD VSS nand2_hv     reset_raw = NAND(UP,DN)
XI1 reset_raw reset_d1 VDD VSS inv_hv    reset_d1  = NOT(reset_raw) = AND(UP,DN)
XI2 reset_d1 reset VDD VSS inv2x_hv      reset     = NOT(reset_d1) = NAND(UP,DN)
```

Two inversions after `reset_raw` hand `reset` back the **same NAND(UP,DN)
sense `reset_raw` already had**. `srlatch.sym`'s own gate-level definition
(`XIR R RB inv_hv` then `XNQB RB Q QB nand2_hv`) needs its `R` input to sit
LOW (deasserted) by default and pulse HIGH only once **both** `UP` and `DN`
have been set — i.e. `reset` should equal `AND(UP,DN)`, one inversion after
`reset_raw`, not two. With the as-drawn parity, `reset` sits at logic **1**
by default (true whenever `UP` and `DN` are not *both* 1, which is true
almost always, including at idle) — so each latch stays in its `R`-asserted
mode essentially all the time, where the latch's own logic collapses to
`Q = S` combinationally (verified directly from the gate-level netlist:
`R=1` forces `QB=1` unconditionally via `XNQB`, at which point
`Q=NAND(SB,1)=NOT(SB)=S`). **`UP` and `DN` never hold a phase-error-encoded
pulse width — they are short, symmetric edge-triggered blips at every
`REF`/`FB` edge respectively, with no phase memory at all.** This is a real
defect in the committed gate-level netlist (and, since `pfd.spice` is
generated verbatim by `design/sg13cmos5l/netlist.sh` from `pfd.sch`, in the
schematic itself) — **not** a testbench-local wiring bug, and **not** a
`cp`/testbench `UP`/`DN` pin-assignment polarity issue. This is exactly why
`RECORD-001`'s own pin-swap experiment found "nearly identical" trajectories
either way: swapping which physical pin the charge pump calls `UP` vs. `DN`
cannot matter when the PFD generating those signals was never encoding
phase information into them in the first place.

## Diagnostic 1: standalone PFD-only testbench — confirms the defect directly

`../testbench/run_pfd_diag.sh` drives the frozen `pfd` subckt alone with two
known, FIXED per-cycle phase relationships (a 5 ns offset on a 50 ns period,
10% — the same order as `RECORD-001`'s own near-zero initial `Δf`, so this
reads the PFD's small-phase-error behaviour, not a large-frequency-error
corner case) — `reflead` (`REF`'s edge arrives first every cycle) and
`fblead` (`FB`'s edge arrives first every cycle) — and reads `UP`/`DN`'s
average level (≈ duty cycle × `VDD`) back out over 300 ns after a 200 ns
settle. Run against BOTH the as-drawn netlist and a diagnostic-only patch
(see "The patch" below), full results in
`../corners/pfd_polarity_diag.csv`:

| Variant | Case | `up` duty | `dn` duty | Verdict |
|---|---|---|---|---|
| as-drawn | REF leads FB | 0.70% | 0.71% | Symmetric — no tristate hold |
| as-drawn | FB leads REF | 0.70% | 0.71% | Symmetric — no tristate hold |
| fixed | REF leads FB | 11.41% | 1.40% | `UP`-dominant (textbook) |
| fixed | FB leads REF | 1.41% | 11.41% | `DN`-dominant (textbook) |

The as-drawn netlist's `up`/`dn` duty cycles are **identical to three
significant figures regardless of which signal leads** — direct, decisive
confirmation that the committed PFD does not distinguish "REF leads FB" from
"FB leads REF" at all. The patched netlist's duty cycles swap correctly with
the lead/lag direction and scale with the phase offset in the expected
sense (11.4% vs. the 10% nominal offset, the small excess consistent with
added gate delay in the reset path) — direct confirmation that the parity
bug, once corrected, restores standard tri-state PFD behaviour.

### The patch (diagnostic only — NOT a proposal to change the committed design here)

`run_pfd_diag.sh` (and `run_closed_loop_pfdfix_diag.sh`, diagnostic 2 below)
derive a `pfd_fixed_diag.spice` **programmatically** from the frozen
snapshot (never a hand-edited copy), adding a third inverter to the reset
chain (odd inversion count after `reset_raw`, restoring `reset = AND(UP,DN)`):

```
XI1 reset_raw reset_d1 VDD VSS inv_hv
XI2 reset_d1 reset_d2 VDD VSS inv2x_hv   (same net renamed, same two gates)
XI3 reset_d2 reset VDD VSS inv_hv        (NEW)
```

This file is **never** written to `../netlist-snapshots/pfd.spice` (frozen,
`sim/README.md` convention) or to `design/sg13cmos5l/` — a schematic-level
fix to `pfd.sch` is a real design change (needs re-export via
`design/lib/netlist-export.sh`, LVS, and re-verification of every record
that already assumed the as-drawn netlist) and is out of this diagnostic
issue's scope. Filed as its own follow-up issue (see "Follow-up" below).

## Diagnostic 2: closed-loop confirmation — the fixed PFD changes the qualitative signature

`../testbench/run_closed_loop_pfdfix_diag.sh` re-runs Part B's own proposal
deck (identical operating point, identical `cp`/resized `loop_filter`/`vco`/
behavioural divide-by-64/ideal-cap substitutions to `RECORD-001`'s own Part
B) for 400 ns — the SAME duration as `RECORD-001`'s own `UP`/`DN`-pin-swap
control run, chosen for the same direct point-by-point comparability — with
only the `pfd` block replaced by the diagnostic patch above. `vctrl`:
2.46 V → 2.360 V (`../corners/lock_trace_proposal_pfdfix.csv`), still
falling, but the `Δf` trajectory's own SHAPE is qualitatively different from
Part B's own recorded trace at the identical timestamps:

| `t` | Part B, as-drawn PFD (`RECORD-001`, `lock_trace_proposal.csv`) | Part B, fixed PFD (`lock_trace_proposal_pfdfix.csv`) |
|---|---|---|
| 50 ns | +0.00835 | +0.00998 |
| 100 ns | +0.00151 | +0.00198 |
| 150 ns | −0.00415 | −0.00402 |
| 200 ns | −0.00964 | −0.00854 |
| 250 ns | −0.01387 | −0.01125 |
| 300 ns | −0.01926 | −0.01186 |
| 350 ns | −0.02372 | −0.01185 |

The as-drawn-PFD trace keeps **accelerating** more negative through all
seven points (the "monotonically more negative... not a lock trajectory"
signature `RECORD-001` reports). The fixed-PFD trace **decelerates and
plateaus** from 250 ns onward (−0.01125 → −0.01186 → −0.01185 — essentially
flat over the last 100 ns), the qualitative signature of a loop beginning to
exhibit negative-feedback correction rather than running open. This is
exactly the discriminator between "structurally broken PFD" (predicts
deceleration/plateau once fixed, even without full lock in a short window)
and "genuine capture-range/timescale limit" or "downstream testbench bug"
(neither of which the parity fix would touch, so neither predicts this
change) — Scope items 2 and 3 would leave the trajectory's *shape*
unaffected by a PFD-only patch; only a Scope-item-1 (PFD-level) cause
explains the change actually observed.

**This is stated as a bounded, qualitative confirmation, not a lock claim**:
400 ns is far short of the ~2.5 µs this deck's own row-7 criterion needs
(`RECORD-001` "Why these durations"), `Δf` is still negative and has not
reversed sign, and no `hold_n`-consecutive-cycle lock criterion is claimed
or evaluated here. Per the Test Plan's own edge-case requirement, this
record does NOT claim the fixed loop "eventually converges" — only that its
short-window trajectory shape changes in exactly the way the identified root
cause predicts, which is the evidence Scope item 1 asked for.

## Disposition of issue #50's Scope items

- **Scope item 1 (PFD-level polarity)**: **CONFIRMED as the root cause** —
  not a polarity/pin-assignment issue in the textbook sense (the PFD does
  not have the "opposite" convention), but a structural sequential-logic
  defect that makes `UP`/`DN` phase-blind. Directly demonstrated by
  Diagnostic 1 (standalone PFD-only testbench) and corroborated by
  Diagnostic 2 (closed-loop trajectory-shape change).
- **Scope item 2 (capture range/timescale)**: **Ruled out as the primary
  cause.** A genuine capture-range/timescale limit would not explain why a
  PFD-only patch — touching nothing downstream of `pfd` — changes the
  closed-loop trajectory's qualitative shape. Not itself re-tested at longer
  `TSTOP` in this record (the as-drawn-PFD deck's own accelerating
  divergence, `RECORD-001`, is not a capture-range signature to begin with —
  a capture-range limit bounds *how far* a loop can start from lock and
  still pull in, it does not by itself produce accelerating divergence from
  a near-zero initial `Δf`).
- **Scope item 3 (testbench-local integration bug)**: **Ruled out.** The
  defect is inside `pfd.spice` itself, which is a verbatim, un-modified
  snapshot of the committed `design/sg13cmos5l/netlist/pfd.spice` — not
  testbench wiring, not a missing `.ic`, not a bias-replica interaction.

## What this does not bound

- **Whether the fixed PFD, run to Part B's own full 2.5 µs window (or
  longer), actually achieves and holds the row-7 lock criterion** — not
  re-run here (400 ns only, for direct comparability with `RECORD-001`'s own
  control-run precedent and this host's ~1 ns/s runtime). The 400 ns
  plateau is consistent with, but does not itself prove, eventual lock.
- **Whether fixing `pfd.sch`/`pfd.spice` in the committed design changes any
  OTHER already-recorded result in this campaign** that used the
  as-drawn `pfd` (e.g. `sg13cmos5l-cp-icp-trim`'s own DC characterisation
  drives `UP`/`DN` directly with ideal voltage sources and does not
  instantiate `pfd` at all, so it is unaffected; `sg13cmos5l-lock-detector-window`
  likewise drives `lock_detector`'s `UP`/`DN` inputs directly). No record in
  `sim/README.md` currently instantiates `pfd` other than this one.
- **The as-drawn loop's own Part A** — Part A's `fb` never toggles at all
  (the `divider_chain` defect, `RECORD-001`), so Part A's own non-lock is
  independently over-determined by that separate, already-recorded defect;
  this record's finding does not change Part A's own disposition.
- **A schematic-level fix to `pfd.sch`** — deliberately out of scope here
  (see "The patch" above); filed as a follow-up issue.

## Row-by-row disposition (updates `RECORD-001`'s own call, does not edit it)

- **Row 7 (lock time)**: still `insufficient-evidence` for Part B (no
  completed lock demonstration), but the open question `RECORD-001` left
  ("the root cause ... is not determined") is now closed: the root cause is
  a real PFD self-reset defect in the committed design, evidenced two
  independent ways.
- **Row 10 (reference spur)**: unchanged, still `insufficient-evidence` —
  this record does not produce a locked carrier either.

## Follow-up

Filed as issue #56 (design-level fix to `design/sg13cmos5l/pfd.sch`/
`pfd.spice`'s self-reset chain, its re-export via
`design/lib/netlist-export.sh`, LVS, and a full-duration re-run of this
directory's own two decks against the corrected design) — out of this
diagnostic issue's own scope, which is root-cause determination only, per
its Affected Files list (`sim/` only, no `design/` path).
