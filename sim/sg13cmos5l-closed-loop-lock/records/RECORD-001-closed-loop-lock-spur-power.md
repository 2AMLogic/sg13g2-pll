# RECORD-001: closed-loop transient — lock time (row 7), reference spur (row 10), whole-PLL power (row 11)

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #37 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L
  closed-loop PVT campaign) — the follow-up issue #27 explicitly deferred
  all three of these rows because none of #27's own three records (Icp-trim,
  loop-bandwidth/PM, duty-cycle) is a real transistor-level closed loop.
- **DUT**: six real subckts, wired at the TESTBENCH LEVEL (there is no
  `pll_top` schematic in `design/sg13cmos5l/` — see "Testbench-local
  integration" below) — `pfd`, `cp`, `loop_filter`, `vco`,
  `divider_chain`, `lock_detector`, each instantiated verbatim from
  `../netlist-snapshots/*.spice` (frozen at commit
  `fbebbdbdd57637b8dae0c1dabaf75d3be5411edb`, confirmed unchanged through
  this record's own HEAD — see `../testbench/run.sh`'s own snapshot-freeze
  note).
- **Tooling**: `ngspice-47`, installed `~/share/pdk/ihp-sg13cmos5l`, arm64
  macOS host. **Different host/arch from every prior SG13CMOS5L record in
  this campaign** (all prior records: x86-64 Linux) — this matters directly
  for this record, see "OSDI host constraint" below.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  (add `--quick` for a 200 ns sanity run with no CSV output). Writes
  `../corners/results_as_drawn.csv`, `../corners/results_proposal.csv`,
  `../corners/lock_trace_as_drawn.csv`, `../corners/lock_trace_proposal.csv`.
  **Warning**: the full run took ~50 minutes wall on the host this record
  was produced on — see "Why these durations" below before re-running.

## Decision made up front, per issue #37's own "Important precondition"

This record runs **both** of the two things issue #37 explicitly asked the
builder to choose between, rather than picking one:

- **Part A — the AS-DRAWN, committed design** (`tb_pll_closed.sp.tmpl`):
  real `loop_filter` (`R1` = 4 µm/120 µm, as committed), real
  `divider_chain`. `../../sg13cmos5l-loop-bandwidth-pm/records/RECORD-001`
  already measured 0 of 90 PVT corners meeting the ≥45° phase-margin
  criterion for this filter — this deck exists to observe **what the
  as-drawn loop actually does**, not to re-derive that already-closed
  finding.
- **Part B — a PROPOSAL, explicitly NOT the committed design**
  (`tb_pll_proposal.sp.tmpl`): `R1` × 20 (2400 µm, the widest-margin pick
  `../../sg13cmos5l-loop-bandwidth-pm/corners/proposal.csv` identified) +
  a behavioural divide-by-64 (forced — see "Why the divider is
  substituted in Part B" below). This deck exists to answer the separate
  question "do the loop dynamics work once both open problems (filter
  stability margin, non-dividing chain) are set aside" — every number it
  produces is reported as a **proposal number**, never as a committed-design
  result.

Neither substitution is silent: both decks' own testbench headers
(`../testbench/tb_pll_closed.sp.tmpl`, `../testbench/tb_pll_proposal.sp.tmpl`)
restate this in full, and every number below is labelled A or B.

## Testbench-local integration — there is no `pll_top` schematic

`design/sg13cmos5l/` commits six blocks and no top level (`design/README.md`).
The block-to-block wiring is therefore testbench-local, exactly like
`../../sg13cmos5l-cp-icp-trim`'s own bias-replica boundary discipline. The
full wiring (every net, both directions) is documented in
`../testbench/tb_pll_closed.sp.tmpl`'s own header; not repeated here.

## OSDI host constraint (arm64 macOS) — ideal-capacitor substitution

**New finding, not previously recorded in this campaign**: `cap_cmomi.osdi`
and `cap_cmomf.osdi` in the installed PDK are x86-64 ELF binaries only
(confirmed with `file(1)` directly on this host's copies). Every prior
SG13CMOS5L record ran on an x86-64 Linux host and could `osdi
cap_cmomi.osdi` directly; **this record's host cannot dlopen either library
at all**, on any netlist that instantiates them — this is a hard host/arch
constraint, not a tooling choice, and it affects every one of the four
`cap_cmomi` instances the closed-loop netlist pulls in (`loop_filter.XC1`/
`XC2`, `lock_detector.XCW`/`XC1`; `vco.XCDECAP` is stripped instead, see
below).

**Substitutions made** (`../testbench/run.sh`'s own Python block does this
programmatically, never by hand-editing a snapshot):

| Instance | Real cap_cmomi geometry | Ideal-cap value used | Provenance |
|---|---|---|---|
| `loop_filter.XC1` | `w=40u l=40u` | 1.6912 pF | `../../sg13cmos5l-loop-filter-momcap`'s own measured nominal (`mos_tt`/`res_typ`/27 C, `mom_frac=0`) value — the SAME number `../../sg13cmos5l-loop-bandwidth-pm`'s real-subckt AC runs used for the identical substitution reason |
| `loop_filter.XC2` | `w=10u l=10u` | 100.15 fF | Same source, same nominal point |
| `lock_detector.XCW` | `w=8u l=8u` | 64.10 fF | **Extrapolated**, not measured: `../../sg13cmos5l-loop-filter-momcap` never characterised `lock_detector`'s own two `cap_cmomi` instances (row 16's own gap — see `sim/README.md` deferred-rows table). Uses that record's own measured area density from `XC2` (`100.1529 fF / (10 µm × 10 µm)` = 1.0015 fF/µm²) applied to `XCW`'s own `w×l`. Stated as an approximation, not a second independent measurement |
| `lock_detector.XC1` | `w=4u l=4u`, `m=2` | 32.05 fF | Same density, applied to the instance's own total `w×l×m` |

`vco.XCDECAP` is **stripped** (commented out, not substituted) — same
precedent as `../../sg13cmos5l-vco-kvco-table`'s own testbench: `VDD_VCO`/
`GND_VCO` are driven by an ideal DC source (`Vdd_vco`) in this deck too, so
`XCDECAP`'s value (or even its presence) cannot change any measurement this
deck makes. This makes no claim about `XCDECAP`'s own MOM-cap sensitivity.

**What this substitution does and does not cost**: `loop_filter`'s own
zero/pole location is unaffected — the ideal caps use the SAME nominal
values the real-subckt AC campaign already validated against a lumped model
(`../../sg13cmos5l-loop-bandwidth-pm`'s own "real-subckt vs. lumped-
equivalent agreement" crosscheck). `lock_detector`'s two instances are a
real approximation (density-extrapolated, not measured) — this affects only
`lock_detector`'s own internal RC timing (its `LOCK` output's own hysteresis
window), which this record does not use as its row-7 lock criterion (see
"Row 7" below — the lock/no-lock call is made from `ref`/`fb` edge timing
directly, not from `lock_detector`'s own analog output). `i_ld` (row 11's
`lock_detector` domain current) is affected only to the extent the block's
switching activity depends on this RC value, which is a second-order effect
on average current.

## PVT point and operating point

Single "typ" PVT bundle (`mos_tt`/`res_typ`/27 C/3.3 V) — see
`../corners/matrix.md` for the runtime-cost rationale (an explicit subset,
per `sim/README.md`'s own convention, not a silently dropped axis).
`f_ref` = 20 MHz, `N` = 64, Icp trim code = 10 µA, VCO band `11`; see that
same file for the full operating-point table and its provenance.

## Why these durations, and what they mean for row 7

Measured directly on this host: **200 ns of this six-block netlist costs
>190 s wall** (`TMAX` = 100 ps, `TPRINT` = 100 ps) — two to three orders of
magnitude slower than the ~1 ns/s a single open-loop `vco` transient costs
(issue #37's own runtime warning, confirmed rather than merely repeated).
A real lock acquisition, at the measured `f_c` ≈ 1.6–1.8 MHz / PM ≈ 58–62°
Part B operates at, needs an acquisition time on the order of several
`1/(ζω_n)` time constants (≈150–250 ns each, at this `f_c`/PM) **plus** a
hold window for whatever consecutive-cycle criterion is used — a
multi-microsecond total. At this host's measured rate, a multi-microsecond
transient costs tens of minutes to hours, **per corner** — not reasonable
for the full PVT matrix inside one build session (this is exactly the
constraint `../corners/matrix.md` documents for the single-PVT-point
decision).

This record therefore uses **different, deliberately asymmetric durations**
for its two decks, each sized to what that deck's own question needs:

- **Part A (as-drawn)**: `TSTOP` = 500 ns. This deck is not expected to
  acquire lock (0/90 PM criterion already failed, and the divider's own
  functional defect — see below), so its window only needs to be long
  enough to reach steady-state domain currents (row 11) and show the
  qualitative trend (row 7's "insufficient-evidence, and why" call).
- **Part B (proposal)**: `TSTOP` = 2.5 µs. Sized to plausibly fit both
  acquisition and a 20-reference-cycle (1 µs at `f_ref` = 20 MHz) hold
  window for the row-7 criterion below.

**Row 7's own numeric criterion** (`spec/porting-plan.md` row 7: "port the
lock criterion's *structure* ... re-derive the numeric target" — gf180-pll's
own number is explicitly NOT ported): this record defines lock as
`|Δf|/f_ref < 1%` **and** `|phase error| < 5%` of one reference period,
**both** held for ≥ 20 consecutive reference cycles. This is this record's
own re-derivation, stated as one, not a carried-over number.

## Results — Part A (as-drawn, committed design)

500 ns simulated, currents averaged over the settled 300–500 ns window:

| Domain | Current | Power @ 3.3 V |
|---|---|---|
| `pfd` | −18.83 µA | 62.2 µW |
| `cp` | −22.56 µA | 74.4 µW |
| `vco` | −2.431 mA | 8.023 mW |
| `divider_chain` | **−7.653 mA** | **25.26 mW** |
| `lock_detector` | −10.97 µA | 36.2 µW |

`vctrl`: 2.46 V (IC) → 2.393 V at 500 ns (avg 2.401 V, range 2.265–2.422 V) —
a small, slow drift, not a lock trajectory.

**`fb` never crosses the 1.65 V logic threshold** in this window (observed
range: essentially flat, well below `VDD`/2) — `n_ref_cycles_observed = 0`,
`lock_time = None`. This is a direct, real-closed-loop confirmation of the
divider defect `sim/README.md`'s own deferred-rows table already describes
from an open exploratory testbench (row 3, #36): the chain's feedback output
does not swing rail-to-rail, so the PFD never sees a valid `FB` edge to
compare against `REF`. The as-drawn loop is, in the observed sense, running
**open** — `UP`/`DN` are driven by `REF`'s own toggling against a
non-responsive `FB`, not by genuine phase/frequency comparison.

**The `divider_chain` domain's own 7.65 mA is itself evidence, not just a
number**: it is roughly 3× the VCO's own current at this operating point,
and gf180-pll's *entire* PLL draws under 5 mW total (`spec/porting-plan.md`
row 11's own citation) — a static CMOS ÷2/3 chain drawing 25 mW is not
credible as correctly-functioning digital logic at this frequency. Read
together with the non-toggling `fb` observation, this is consistent with
internal contention or a metastable/oscillating internal node inside the
chain (exactly the kind of symptom a missing reset pin — `sim/README.md`'s
own note — would produce from an ill-defined power-up state), not with a
divider that is merely "slow to lock." This record does **not** attempt to
localise the defect further (that is #36's own scope) — it reports the
symptom as observed, in a real closed loop, plainly.

Reference-spur extraction was run on this deck's own `vctrl` waveform for
completeness (Goertzel magnitude at `f_ref`, converted via the local Kvco
secant) and returns a number (~−39.7 dBc) — but with no stable carrier to
define a spur *around* (no lock, `fb` not even toggling), this number is
**not reported as a measurement of row 10**; see "Row-by-row disposition".

## Results — Part B (proposal, NOT the committed design)

2.5 µs simulated, currents averaged over the 2.0–2.5 µs window:

| Domain | Current | Power @ 3.3 V |
|---|---|---|
| `pfd` | −31.69 µA | 104.6 µW |
| `cp` | −22.64 µA | 74.7 µW |
| `vco` | −1.737 mA | 5.732 mW |
| `divider_chain` | N/A (behavioural, no real current) | — |
| `lock_detector` | −12.74 µA | 42.0 µW |

`vctrl`: 2.46 V (IC) → 1.720 V at 2.5 µs (avg 1.782 V, range 1.694–1.872 V
in the final 500 ns window) — a substantial, **monotonic** drift away from
the initial operating point, not toward a fixed value.

**`fb` toggles correctly this time** (the behavioural divide-by-64 works as
designed), giving 49 full reference cycles of real `Δf`/phase-error data
(`../corners/lock_trace_proposal.csv`). The result: `Δf`/`f_ref` starts near
zero (+0.84% at the first cycle — the `VC0` initial-condition guess was
close) and then grows **monotonically more negative** for the entire 2.5 µs
window (−0.8% → −22.9%, `../corners/lock_trace_proposal.csv`), with the
phase-error trace repeatedly wrapping past ±50% of a reference period (cycle
slips) rather than settling. **`lock_time = None`** — the row-7 dual
threshold (§"Why these durations") is never held even once, let alone for
20 consecutive cycles.

**Diagnostic experiment (not part of the committed testbench, not re-run at
full duration)**: because the drift direction is consistent with `vctrl`
moving the *wrong* way to correct a lagging `fb` (decreasing `VCTRL` lowers
`VCO` frequency, which should make a slow `fb` fall *further* behind, which
is what is observed — the opposite of a self-correcting loop), this builder
ran a 400 ns control deck with the `cp`'s `UP`/`DN` inputs swapped
(`XCP dn up ...` instead of `XCP up dn ...`) to test a wiring-polarity
hypothesis. **Result: the swapped deck's `Δf` trajectory is nearly
identical** to the unswapped one over the same 400 ns window (−0.0236 vs.
−0.0237 at 350 ns) — i.e. swapping `UP`/`DN` did **not** change the
observed drift. This rules out a simple testbench-local `UP`/`DN` pin-swap
as the explanation and leaves the root cause **undetermined** within this
record's compute budget — see "What this does not bound" and follow-up
issue #50 (Part of #16), filed off this record. The charge pump's own DC characterisation
(`../../sg13cmos5l-cp-icp-trim/corners/results.csv`) already confirms its
`UP`/`DN` sourcing/sinking convention is the expected one (`up` state:
+10.05 µA at `mos_tt`/27 C/10 µA code; `dn` state: −10.37 µA), so the
charge pump's own polarity is not itself in question — whatever produces
this drift is elsewhere (or is a genuine capture-range/timescale limit this
record's window is too short to resolve).

Reference-spur extraction on this deck's own `vctrl` (~−36.0 dBc) is,
likewise, **not reported as a row-10 measurement** — there is no stable
carrier here either.

## Row-by-row disposition

- **Row 7 (lock time)**: **`insufficient-evidence` for both decks, stated
  plainly rather than guessed at.** Part A (the committed design) does not
  acquire lock — consistent with, and now independently confirmed beyond,
  `sg13cmos5l-loop-bandwidth-pm`'s own 0/90 phase-margin finding, plus a new
  observation (the divider's `fb` output does not toggle in a real closed
  loop). Part B (the proposal, with both known defects addressed — resized
  filter, working behavioural divider) **also** does not acquire lock within
  its 2.5 µs window; its `Δf` trajectory diverges rather than converges, and
  a diagnostic polarity-swap experiment did not change that outcome. Per
  issue #37's own "important precondition": this is exactly the outcome the
  issue anticipated as legitimate to record for the as-drawn loop, and this
  record additionally shows the *proposal* loop does not straightforwardly
  fix it either — a genuinely new finding, not previously known.
- **Row 10 (reference spur)**: **`insufficient-evidence` for both decks.**
  Neither deck reaches a stable, locked carrier to define a spur around (the
  row's own requirement, per issue #37's "Why"), so the Goertzel-DFT numbers
  computed above are not reported as measurements of this row — reporting a
  dBc figure against an unlocked, drifting `vctrl` would misrepresent what
  was measured as more than it is.
- **Row 11 (power)**: **bounded — all five remaining domains measured
  together, at one consistent (though non-locked) operating point, for the
  first time in this campaign.** Part A's own five domain currents (table
  above) are real, simultaneous measurements of the committed design's
  `pfd`, `cp`, `vco`, `divider_chain` and `lock_detector` blocks. Summed
  with the previously-measured `vdd_vco` (this record's own `vco` figure,
  8.02 mW, is inside `sg13cmos5l-vco-duty-cycle`'s own 3.09–8.88 mW range —
  a real cross-check, not just a repeat) and `cp` (this record's 74 µW is
  the same order as that record's ≈66 µW estimate at the same trim code):
  **whole-PLL current at this operating point ≈ 10.137 mA (33.45 mW at
  3.3 V), of which 7.653 mA (25.26 mW) is the `divider_chain` domain
  alone.** This total is reported with a strong caveat, not as a clean
  design figure: the `divider_chain` current is very likely inflated by the
  same malfunction that keeps `fb` from toggling (see Part A discussion
  above) — a correctly-functioning chain would very plausibly draw
  meaningfully less. Excluding the (likely-defective) `divider_chain`
  domain, the other four measured domains alone total **2.483 mA
  (8.20 mW)** — `pfd` + `cp` + `vco` + `lock_detector`, a more
  representative figure for "what this design costs once the divider is
  fixed," though still not itself a claim about
  what the fixed divider will draw. `spec/porting-plan.md` row 11's own
  disposition ("re-derive — do not scale by V²") is not violated either way:
  no V² rescale is used, and `sg13cmos5l-vco-duty-cycle`'s own finding that
  the VCO alone already exceeds gf180-pll's whole-PLL figure is reaffirmed,
  not contradicted, by this larger number.

## What this does not bound

- **Single PVT point only** (`mos_tt`/`res_typ`/27 C/3.3 V) — see
  `../corners/matrix.md` for the runtime-cost rationale. No corner sweep of
  any of this record's own numbers exists.
- **`lock_detector`'s two `cap_cmomi` instances are density-extrapolated
  approximations**, not independent measurements (see "OSDI host
  constraint" above) — `i_ld` and the block's own switching behaviour carry
  that approximation's uncertainty.
- **Part B's divider is behavioural** (an ideal divide-by-64), not the real
  `divider_chain` — Part B's own non-convergence is therefore NOT evidence
  about the real divider; it isolates the filter/loop-dynamics question from
  the divider defect, and finds a *second*, unexplained non-convergence
  even with the divider set aside.
- **The root cause of Part B's own non-convergence is not determined** —
  the polarity-swap experiment above rules out the simplest hypothesis but
  does not identify the actual cause. Filed as follow-up issue #50 (Part of
  #16) rather than resolved here.
- **Row 11's whole-PLL total is not a locked-operating-point figure** — the
  as-drawn loop does not lock (row 7), so "one consistent operating point"
  here means "measured simultaneously in one deck," not "the design's
  intended steady-state." See the caveat in "Row-by-row disposition" above.
- #36 (divider chain N-range/retiming) has not yet landed as of this
  record — see "Divider chain caveat" below.

## Divider chain caveat (issue #36, open as of this record)

Issue #36 (divider chain N-range/retiming) was "strongly recommended to
land first" per issue #37's own dependency note, but had not merged as of
this record (still `loom:building`). This record's Part A therefore
integrates whatever `divider_chain.spice` is committed at the frozen
snapshot commit (`fbebbdbdd5...`), **not** any retiming fix #36 may
eventually land. Part A's own observation of the divider's behaviour (see
above) is consistent with — and does not newly discover — the defect
`sim/README.md`'s own deferred-rows table already describes for row 3
("the chain's first ÷2 stage divides correctly ... the inner stages do not
toggle"): if #36 lands a fix, this record's Part A conclusion about the
as-drawn loop's non-acquisition should be re-run against the fixed chain
before being treated as a permanent finding about the *filter*'s own
stability margin in isolation (the phase-margin failure from
`sg13cmos5l-loop-bandwidth-pm` is independent of the divider and stands on
its own regardless of #36's outcome).
