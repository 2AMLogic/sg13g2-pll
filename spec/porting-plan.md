# Porting plan: sg13g2-pll from gf180-pll and sky130-pll

- **Status**: planning document, produced by issue #1. It is not itself a
  ratified spec and it binds no numeric value — it recommends what to carry,
  what to swap, and what must be re-derived, so that a future SG13G2-specific
  spec/architecture decision record (`spec/decision-records/DR-001-...`, the
  sg13g2 equivalent of the sibling repos' first decision records) has a
  starting point instead of a blank page.
- **Date**: 2026-08-20
- **Written by**: Builder agent, issue #1
- **Sources reviewed in full**: `2AMLogic/gf180-pll` `spec/pll.md` +
  `spec/decision-records/DR-001` through `DR-007`; `2AMLogic/sky130-pll`
  `spec/target-spec.md` + `spec/decision-records/DR-001`; both repos'
  `design/README.md` (gf180-pll) and `design/*/DESIGN.md` (sky130-pll);
  `2AMLogic/klayout-tools` issue #524 and `src/klayout_tools/decks/sg13g2.py`
  (the current state of the SG13G2 DRC/LVS deck, read directly from source).
- **Consumes**: nothing yet ratified in this repo (this is the first
  document in `spec/`). Cites gf180-pll and sky130-pll spec rows and decision
  records throughout; every citation below names the specific file and
  section it came from.
- **Does not**: size any circuit, ratify any spec number, or commit to any
  device choice. Per the issue: "No design work in this issue — the plan is
  the product."

---

## How to read this document

Three parts, matching the issue's three questions:

1. [What carries over](#1-what-carries-over) — per block, what ports as-is,
   what ports with a device swap, and what must be re-derived from scratch on
   SG13G2, citing the sibling repo's spec row or decision record each item
   traces to.
2. [What SG13G2's BiCMOS devices change](#2-what-sg13g2s-bicmos-devices-change)
   — per block, whether SiGe bipolar devices widen the option space, plus the
   supply/device-flavor question every port has had to settle first.
3. [What the starter-grade SG13G2 deck can't check yet](#3-what-the-starter-grade-sg13g2-deck-cant-check-yet)
   — read directly from the deck's own source, not guessed at, so gaps can be
   filed at `2AMLogic/klayout-tools` before they are discovered mid-layout.

### The two sibling repos are at very different maturities, and that matters for how much weight each carries

**gf180-pll** is the mature reference: a ratified-with-amendments spec
(`spec/pll.md`, DR-007 "ratify-with-amendments" verdict), 7 decision records
covering architecture through a spec-review verdict, a complete schematic set
in `design/`, and dozens of PVT-swept `sim/` campaigns. Its numbers are
**measured**, not aspirational, and its decision records show their own
alternatives-considered reasoning, which is exactly the reasoning this
document needs to re-run against SG13G2's devices rather than blindly copy.

**sky130-pll** is a first-generation *port* of gf180-pll, one process node
in and still pre-schematic-ratification: only its own `DR-001` (supply-flavor
scope) is ratified, its `spec/target-spec.md` carries every other row as
"DRAFT — to be ratified," and its `design/*/DESIGN.md` files are explicitly
un-testbenched forward designs, not evidence. What sky130-pll is valuable for
here is not its numbers (none are measured yet) but its **method**: it is the
one existing precedent for how a fleet PLL port states "carried from gf180-pll
and NOT assumed to hold" per row, and its `DR-001` is the direct template for
this repo's own forthcoming supply-flavor decision record. This document
follows the sky130-pll stance throughout: **default to re-derive, not to
port**, and state the re-derivation condition explicitly per row rather than
silently assuming parity.

---

## 1. What carries over

The frame for every row below is the same three-way split sky130-pll's spec
already uses (`target-spec.md`, "How to read this file"): **as-is** (the
number or structure ports with no process-dependent change), **device swap**
(the structure ports, but every number sizing it must be re-derived against
SG13G2's own device data), or **re-derive** (the number itself is
process/supply-dependent and cannot be assumed to hold at all).

### 1.1 Architecture decisions

| Item | Carries over | Basis | Citation |
|---|---|---|---|
| Loop type: type-II charge-pump PLL, tri-state PFD → charge pump → passive 2nd-order filter → ring VCO → feedback divider, no active filter | **As-is, as a starting hypothesis** | Both siblings converged here independently at very different maturities; the coupling argument (`ω_c ∝ Icp·R·f_ref`, invariant across output band and N when the VCO is current-starved) is a topology property, not a device-flavor property | gf180-pll `DR-001` Decision 1 + "Why these three are one decision"; sky130-pll's own `design/pfd-cp/DESIGN.md` and `design/loop-filter/DESIGN.md` independently reach the same tri-state-PFD / passive-filter shape (uncited from gf180-pll's numbers per their own "Forward design, not reverse-engineered" sections, but the same topology) |
| VCO topology: single-ended, current-starved CMOS inverter ring, odd stage count, coarse band select + fine analog Vctrl | **Device swap — topology as-is, sizing re-derived** *if* SG13G2 stays CMOS-only for the ring. **Re-derive the decision itself** if SG13G2's SiGe HBTs change the calculus — see [§2.1](#21-the-vco--the-block-bicmos-changes-most) | The `f_osc ∝ I_ctrl` / `Kvco ∝ f_osc` self-compensation property (§"Why these three are one decision") is what makes a fixed passive filter viable across a wide N/output-band range, and that property is a current-starved-ring property, not a gf180-specific one | gf180-pll `DR-001` Decision 2; sky130-pll `design/vco/DESIGN.md` "Topology choice" section independently re-derives (not ports) the same choice for the same reasons |
| Feedback divider: cascaded ÷2/3 (Vaucher) chain, static CMOS, VCO-clocked retiming flop | **Re-derive the architecture choice, not just the sizing** — the two siblings disagree here, and SG13G2 must pick between them on its own N-range/logic-family merits, not by majority vote | gf180-pll's ÷2/3 chain was chosen specifically to hit **N = 4** (a pulse-swallow prescaler floors around N ≈ 12–16, DR-001 Decision 3, "Alternatives considered"); sky130-pll instead built a synchronous down-counter with programmable reload (`design/divider/DESIGN.md`), a different family entirely, without a decision record arguing the choice against N = 4. **This is a live disagreement between the two ported references**, not something to average — SG13G2's own N-range and top-of-band frequency choice (§1.2, re-derive) settles it | gf180-pll `DR-001` Decision 3; sky130-pll `design/divider/DESIGN.md` "Architecture choice" section |
| Retiming discipline: feedback edge is a single flop's clk→Q after a VCO edge, independent of N | **As-is, as an interface requirement** — this is what keeps the PFD's static phase offset from moving when N is reprogrammed, and the argument for it is topology-independent | gf180-pll `DR-001` Decision 3 Consequences; consumed by DR-006 §"Consequences" | gf180-pll `DR-001` Decision 3 |
| No active filter, no opamp in the loop path (but a *bias buffer* that never carries loop signal charge is compatible) | **As-is, as a scoping principle** — re-derive whether SG13G2's charge pump needs the equivalent of gf180-pll's dump-node buffer, since that need was discovered empirically (charge-pump tail-node charge exchange), not architected in from the start | gf180-pll `DR-001` Decision 1 ("no opamp in the loop path") refined by `DR-005` (the four conditions an internal bias element must meet to not count as "in the loop path") | gf180-pll `DR-001` Decision 1, `DR-005` |
| Band-select and N are **static** configuration inputs; no auto-calibration FSM in v1 | **As-is** — this is a scope decision independent of device flavor, made twice (once per sibling, implicitly for sky130) for the same reason: an auto-cal FSM is a second, larger design problem with no matching digital library to lean on | gf180-pll `DR-001` Decision 2 Consequences, `DR-003` Decision 4's Alternatives; sky130-pll's `target-spec.md` row 8/16 carries the same lock-detector-without-FSM framing | gf180-pll `DR-001`, `DR-003`; sky130-pll `target-spec.md` rows 8, 16 |
| Lock detector: passive phase-error window comparator, no FSM, digital `lock` output | **As-is as a scope decision, device-swap on sizing** | gf180-pll `DR-002` Decision 4 rules this in-scope explicitly; the implementation (window comparator on PFD UP/DN, hysteresis via Schmitt trigger) is process-independent digital logic | gf180-pll `DR-002` Decision 4; `design/README.md` § "`lock_detector`" |
| Output ceiling: design margin budgeted to the *target* frequency, not a stretch ceiling; no post-VCO output divider unless the VCO's own band plan can't reach the floor | **As-is as a *methodology*, re-derive the actual floor/ceiling numbers** — SG13G2's own output band is unknown until a VCO tuning-range campaign runs (§1.2) | gf180-pll `DR-002` Decision 2, with its own explicit conditional trigger ("no divider by default; the trigger is the VCO's own low-band floor coming up short") | gf180-pll `DR-002` Decision 2 |

**A structural note the sky130 port already teaches**: gf180-pll's decision
records were written *in order* (architecture → scope ratification → VCO
extraction → leaf-cell naming → dump-node buffer → loop-filter sizing → spec
review), each refining or being consumed by the next, and each states
explicitly which of its own numbers are "disposition only" hand calculations
versus real extracted data. SG13G2's own decision-record sequence should
follow the same order and the same "disposition vs. real" labeling
discipline — sky130-pll's `DR-001` already does this correctly (it argues a
*scope* question, names the numeric consequences without settling them, and
explicitly defers the numbers to design). **Recommendation**: SG13G2's first
decision record should mirror gf180-pll's `DR-001` shape (architecture survey
covering loop type / VCO delay-cell or device-class style / divider
architecture, argued together because they are mutually constraining) but
must additionally settle the bipolar-device question (§2 below) as a fourth,
coupled decision — gf180 and sky130 never had that fourth axis to argue.

### 1.2 Spec rows

Every row below follows sky130-pll's own table shape: **source** (the
sibling row this starts from) and **what SG13G2 must settle**
(port-and-verify / re-derive / not yet knowable). Numbers from gf180-pll are
cited for calibration only — none is a SG13G2 target.

| # | Parameter | Source | SG13G2 disposition |
|---|---|---|---|
| 0 | **Supply / device flavor** | gf180-pll: 3.3 V thick-oxide only (`DR-002` Decision 3). sky130-pll: 1.8 V core, ratified (`DR-001`) | **Re-derive — the single prerequisite gate, see [§2.4](#24-the-supply--device-flavor-decision-the-prerequisite-both-siblings-settled-first)**. SG13G2 offers a *third* menu shape neither sibling had: 1.2 V core CMOS, 3.3 V thick-oxide CMOS, *and* SiGe HBTs, so this is not a two-way choice the way it was for either sibling |
| 1 | Output band | gf180-pll: 10–200 MHz continuous (measured, `pll.md` row 1). sky130-pll: same numbers carried as a **starting point only**, "NOT assumed to hold" (`target-spec.md` row 2) | **Re-derive.** Neither prior number transfers: gf180-pll's is a 180 nm-class ring at 3.3 V, sky130-pll's own draft explicitly declines to assume its 130 nm/1.8 V ring reaches the same band. SG13G2 is a *third* combination (130 nm-class SiGe BiCMOS, candidate 1.2 V core) with no existing data point at all |
| 2 | Reference input | gf180-pll: 1–25 MHz CMOS square wave, rising-edge trigger, 30–70% duty (`pll.md` row 2, partly budget) | **Port the interface contract as-is; re-derive the electrical levels** once the supply flavor is settled (V_IL/V_IH scale with VDD) |
| 3 | Multiplication ratio | gf180-pll: N = 4–64, every integer (measured, `pll.md` row 3) | **Port the *requirement* (N ⊇ 4–64, no holes) as-is; re-derive the divider architecture and its retiming-margin closure** against SG13G2's own top-of-band frequency — this is exactly the item DR-001 Decision 3 (gf180-pll) sized against N = 4 specifically, so whichever divider family SG13G2 chooses (§1.1) must clear the same floor |
| 4/5 | Kvco bound / band-selection rule | gf180-pll: ≤ 150 MHz/V under a normative "lowest band that reaches the target" rule (`pll.md` rows 17, band-selection rule; derived from `DR-003` Decision 4's real extracted data, not the `DR-001` hand calc it withdrew) | **Port the *rule structure* (a per-band, per-corner Kvco table, plus a normative lowest-band-first selection rule) as-is; the numeric bound is 100% re-derive** — sky130-pll's own row 5 explicitly says "do not port 150" for the same reason this applies doubly on SG13G2: different process, different device class is even on the table (§2.1) |
| 6/6a | Loop bandwidth / phase margin | gf180-pll: f_c = 26–430 kHz, `f_c < f_ref/10` hard ceiling, ≥45° phase margin, closed by a per-f_ref Icp-trim rule (`pll.md` rows 8/8a, `DR-006` Decisions 3–5) | **Port the *sampled-loop stability criteria* (`f_c < f_ref/10`, ≥45° PM) and the *mechanism* (a coarse Icp trim keyed to f_ref, not a filter redesign) as-is; re-derive every kHz number and the trim-code table** — these depend on the re-derived Kvco table and the SG13G2-specific charge-pump/filter sizing |
| 7 | Lock time | gf180-pll: < 100 µs to a stated lock criterion (measured settling, budget for cold start; the < 20 µs stretch was **dropped**, not carried, because it is structurally unreachable with a fixed filter — `pll.md` row 9, `DR-006` Decision 7) | **Port the lock criterion's *structure* (a Δf + static-phase-error dual threshold held for N reference cycles) as-is; re-derive the numeric target** — and inherit gf180-pll's own finding as a warning, not a target: dropping an unreachable stretch value from a ratified table is the correct move if SG13G2's fixed-filter settling floor makes the same tradeoff, rather than silently carrying an aspirational number |
| 8 | Period jitter | gf180-pll: ≤ 1.0% of period RMS, conditional on ≤ 20 mV pp `vdd_vco` ripple (measured sensitivity + derived condition, `pll.md` row 5) | **Port the *percentage-of-period* framing and the *ripple-conditional* structure as-is; re-derive the ripple budget itself, smaller not larger** — sky130-pll's `DR-001` names exactly this risk: a fixed absolute ripple consumes a larger fraction of a smaller Vctrl window on a lower-voltage rail. SG13G2's 1.2 V candidate core is tighter still than sky130's 1.8 V — see [§2.4](#24-the-supply--device-flavor-decision-the-prerequisite-both-siblings-settled-first) |
| 9 | Integrated RMS jitter / phase noise | gf180-pll: **deliberately not spec'd**, derived-only (`DR-002` Decision 5) — because ngspice has no direct AC `.noise` path for a free-running oscillator's phase noise | **Port the omission as-is.** This is a flow limitation (ngspice, not the PDK), so it applies identically on SG13G2 unless a transient-noise/ISF pipeline is built independently of this port. Confirm rather than re-litigate |
| 10 | Reference spur | gf180-pll: ≤ −55 dBc (measured at 5 corners + derived from charge-pump charge asymmetry, `pll.md` row 7) | **Re-derive entirely from SG13G2's own charge-pump mismatch data.** The gf180-pll number is a direct function of that design's specific charge-pump topology (`cp_dumpbuf`) and its measured femtocoulomb-level asymmetry — not portable without the equivalent SG13G2 charge pump existing first |
| 11 | Power | gf180-pll: < 5 mW at 100 MHz, 3.3 V, all domains (derived, `pll.md` row 10) | **Re-derive — do not scale by V².** sky130-pll's `DR-001` explicitly warns against a rule-of-thumb V² rescale because the process's own capacitance also changed; the same warning applies at least as strongly to SG13G2 (a different node, and possibly a different device class for part of the loop) |
| 12 | Supply sensitivity | gf180-pll: ripple ≤ 20 mV pp budget + DC-excursion ≤ 0.6 V of Vctrl window (measured pushing + derived budgets, `pll.md` row 12) | **Port the *two-budget structure* (AC ripple ceiling + DC Vctrl-window consumption ceiling) as-is; re-derive both numbers.** This is the row gf180-pll's own `DR-003` calls "the block's dominant risk, and it is structural" for *any* current-starved ring on an unregulated rail — expect it to bind on SG13G2 too if the ring topology carries over |
| 13 | Output duty cycle | gf180-pll: 45–55%, measured 90/90 points, **7 points below the 45% floor** at the `lo` edge / `fs` corner bundle (`pll.md` row 13) | **Port the target and the measurement methodology as-is; re-derive.** Carry gf180-pll's own finding forward as a design flag, not a target: matched PMOS-head/NMOS-tail starving devices are necessary but were not, alone, sufficient to clear the floor at every corner on gf180 — SG13G2's delay-cell design should budget margin against this known failure mode from the start |
| 14 | Output levels/drive | gf180-pll: rail-to-rail CMOS, V_OH ≥ 0.9·VDD / V_OL ≤ 0.1·VDD into ≤ 50 fF (measured 90/90 pass, `pll.md` row 14) | **Port as-is** — this is a generic CMOS output-stage requirement, independent of process, once the output rail is fixed |
| 15 | Area | gf180-pll: ≤ 0.15 mm² budget (no layout yet; loop-filter allocation ≈21.4% is measured area, `pll.md` row 15) | **Re-derive entirely.** sky130-pll's row 18 already states gf180-pll's 180 nm-class figure "is not portable" to a 130 nm geometry; SG13G2 is a different 130 nm process with its own device/passive densities (and if any bipolar device lands in the block, its own area is a different multiple of a CMOS transistor's than any of these devices) |
| 16 | Lock detector targets | gf180-pll: assert window ≥ 2.5 ns / ≥ 2× worst static phase offset, hysteresis ≥ 25% of window, no chatter — **measured as not met today** (`pll.md` row 16) | **Port the target structure as-is; re-derive the numbers, and budget margin from the start against the specific failure gf180-pll already found** — its own static phase offset ended up comparable to its own comparator window, at exactly the high-f_ref/low-Icp corner. That is a sizing-margin lesson to carry forward, not a number |
| 17 | Standby / power-down | gf180-pll: **no power-down mode in v1**, waived (`pll.md` row 11) | **Port the scope call as-is**, unless a new requirement specifically motivates adding one — this was a deliberate v1-scope decision on both siblings, not an oversight |
| 18 | Supply range | gf180-pll: 3.3 V ±10% (`pll.md` row 18) | **Fully gated on [§2.4](#24-the-supply--device-flavor-decision-the-prerequisite-both-siblings-settled-first)** |

### 1.3 Testbench / corner-harness structure

This is the highest-confidence "as-is" category in the whole document — it
is methodology, not circuit data, and both siblings already converged on it
independently (sky130-pll explicitly reuses the gf180-pll/gf180-bandgap
convention rather than re-inventing it).

| Item | Carries over | Citation |
|---|---|---|
| Append-only evidence records: `sim/<slug>/{testbench,netlist-snapshots,corners,records}/`, a new `<record-id>` per run, records never edited in place | **As-is** | gf180-pll `sim/README.md` (itself copied from `2AMLogic/gf180-bandgap`, per its own "Provenance of this convention" section) |
| One experiment directory per distinct **claim under test**, not per run; splitting into sibling slugs when sub-testbenches are genuinely different DUTs | **As-is** | gf180-pll `sim/README.md` "Directory / naming convention" |
| Full PVT corner matrix (−40/27/125 °C × supply ±10% × process corners) as the default sweep, with an explicit stated reason for any subset | **As-is as a policy; the actual corner *count* is process-specific** (SG13G2's own PDK corner model set may not mirror gf180mcu's or sky130's 5-bundle/27-corner shape) | gf180-pll `sim/README.md` |
| Netlist provenance discipline: every record freezes the exact netlist it simulated under `netlist-snapshots/`, independent of the live `design/netlist/*.spice` export | **As-is** | gf180-pll `design/README.md` § "Netlist export"; `sim/README.md` |
| Per-block file organization: one `.sch`/`.sym` per cell, matching `tb_<block>` testbenches, so each block's evidence is independently re-runnable | **As-is** — both siblings converged here, and gf180-pll's own `DR-001` explicitly cites the (private, pre-existing) sky130 prior art for this pattern | gf180-pll `DR-001` §"What transfers to xschem + ngspice, concretely" item 1; gf180-pll `design/README.md` |
| Leaf-cell ownership/naming convention (`<block-prefix>_<cellname>` for block-owned cells, a closed shared-cell list for genuinely canonical ones) | **As-is as a convention** | gf180-pll `DR-004`, `design/README.md` § "Leaf-cell ownership and naming" |
| Closed-loop internal-timestep bound: a narrow internal pulse (gf180-pll's PFD `edgedet`, 0.33–0.39 ns) sets the ngspice transient ceiling for *any* closed-loop sim containing it, independent of the loop's own output frequency | **As-is as a methodology warning** — SG13G2's own PFD/edge-detector implementation will have its own narrowest internal node, and it must be found and bounded the same way, whatever its numeric value turns out to be | gf180-pll `design/README.md` § "PFD (`pfd.sch`)"; `sim/README.md` § "Closed-loop internal-timestep bound" |
| Charge-domain (not just waveform-level) dead-zone/mismatch characterization for the PFD + charge pump | **As-is as a methodology** — gf180-pll's own history (a logic-correct-looking PFD that measurably failed 9/45 corners in the *charge* domain while its waveforms looked perfect) is the argument for why this matters, independent of device flavor | gf180-pll `design/README.md` § "PFD (`pfd.sch`)" items 1–3; `sim/pfd-deadzone` |

### 1.4 Block schematics — what physically ports

None of the transistor-level schematics port unmodified (every device is
process-specific), but the **block decomposition and hierarchy** carries over
completely, and several **circuit techniques** carry over as design patterns
to re-derive against SG13G2 devices rather than reinvent:

| Block | Technique that carries over (device-swap, re-derive sizing) | Citation |
|---|---|---|
| VCO | Constant-gm (beta-multiplier) bias core; source-degenerated V→I converter (`∂I/∂Vctrl ≈ 1/R_deg` rather than raw `g_m`, to bound Kvco); geometric (not binary-weighted) coarse mirror cascade for uniform band overlap; matched PMOS-head/NMOS-tail starving devices for duty-cycle symmetry; dedicated supply domain + on-chip decap | gf180-pll `DR-001` Decision 2, `DR-003`, `design/README.md` § "The VCO" |
| PFD | Tri-state edge-detect + SR-latch PFD with a delay-chain reset sized in the **charge domain**, not the logic domain (reset delay > charge-pump turn-on time, not just > logic race margin) | gf180-pll `design/README.md` § "PFD (`pfd.sch`)" |
| Charge pump | Wide-swing cascode output stage for compliance-range headroom; unit-element (not binary-weighted) current trim so per-leg overdrive doesn't move with the trim code; shared, buffered ("tracking") dump node to null idle-leg tail-charge exchange rather than balance it with a fixed clamp | gf180-pll `design/README.md` § "Charge pump (`cp.sch`)"; `DR-005` |
| Loop filter | Passive series-R + shunt-C1 + shunt-C2 topology; a coarse Icp trim as the mechanism that adapts one fixed filter across a wide reference-frequency range (not R/C trim banks — switches on the highest-impedance node are themselves a spur mechanism) | gf180-pll `DR-001` Decision 1 Alternatives, `DR-006` |
| Feedback divider | VCO-clocked final retiming flop, independent of N, as the PFD's interface contract — **the one technique both siblings kept even though their divider *architectures* diverge** (§1.1) | gf180-pll `DR-001` Decision 3; sky130-pll `design/top/DESIGN.md` |
| Lock detector | Phase-error window comparator (XOR of UP/DN, delayed-AND for a width check) with asymmetric assert-slow/deassert-fast dynamics, as a passive monitor with no FSM | gf180-pll `design/README.md` § "`lock_detector`" |

---

## 2. What SG13G2's BiCMOS devices change

SG13G2 is IHP's 130 nm SiGe BiCMOS process: real high-speed SiGe
heterojunction bipolar transistors (HBTs) alongside CMOS, plus a CMOS device
menu organized like SG13G2's own thin-/thick-oxide split (visible directly in
the DRC/LVS deck source reviewed for §3 below — `sg13_lv_nmos`/`sg13_lv_pmos`
default-flavor devices vs. a `ThickGateOx`-marked `sg13_hv_nmos`/`sg13_hv_pmos`
pair). **Neither gf180mcu (pure CMOS, one 3.3 V thick-oxide flavor) nor
sky130 (pure CMOS, 1.8 V core + a deferred I/O-class flavor) had a bipolar
option at all** — this is the axis this port adds that neither sibling's
architecture survey had to weigh.

### 2.1 The VCO — the block BiCMOS changes most

Both siblings' `DR-001`-equivalent chose a **single-ended, current-starved
CMOS ring** and rejected every other CMOS topology considered (supply-regulated
ring, fully differential ring, pseudo-differential ring) primarily on **tuning
range**: gf180-pll's own rejection of the supply-regulated ring is explicit —
"frequency is roughly proportional to `(V_reg − V_th)^~1.3`, so a 20:1 range
would need V_reg to span from just above threshold to the rail" (`DR-001`
Decision 2, "Alternatives considered"). Neither survey considered a
**bipolar-based oscillator** at all, because neither PDK had bipolar devices
to consider.

**What must be decided, and named as a decision, not assumed away:**

- **Whether a tank-based (LC) oscillator using SG13G2's SiGe HBTs becomes
  worth considering against the ported current-starved CMOS ring.** SiGe HBTs
  are the textbook enabling device for negative-gm LC-tank VCOs (an HBT
  cross-coupled pair or Colpitts topology) at frequencies well above what a
  ring of the same process typically reaches cleanly, with materially better
  phase-noise potential — the same phase-noise advantage that made both
  siblings' `DR-001`s reject sub-sampling/injection-locked *architectures*
  specifically because "the flow cannot substantiate a phase-noise number"
  (gf180-pll `DR-001` Decision 1, "Alternatives considered" — sub-sampling
  rejected on exactly this evidentiary ground, not on feasibility). **That
  same evidentiary objection applies to an LC-tank VCO argument for SG13G2 as
  much as it did to sub-sampling on gf180mcu**: this repo's own CLAUDE.md
  commits to "no claim without a testbench," and ngspice's phase-noise
  limitation (no direct `.noise` result for a free-running oscillator,
  `DR-002` Decision 5) is a flow limitation independent of which device class
  the oscillator uses. An LC-tank VCO's headline advantage is therefore
  **exactly the number this flow still cannot evidence directly** — so
  choosing it purely for phase noise reproduces the argument both siblings'
  architecture surveys already rejected once, on a different justification.
  What *does* differ, and is worth weighing on its own separate merits: an
  LC-tank oscillator's **tuning range** is typically much narrower than a
  20:1 current-starved-ring span (a varactor-tuned tank commonly reaches
  1.3–2:1 before quality/linearity degrade badly), which cuts directly
  against the 20:1-continuous-band requirement (gf180-pll `pll.md` row 1)
  every carried-over spec row in §1.2 assumes. **Recommendation for the first
  SG13G2 architecture decision record**: name the LC-tank option explicitly,
  disposition it against (a) the flow's phase-noise-evidence gap — same
  objection as sub-sampling/ILCM, not new — and (b) the tuning-range
  requirement, rather than silently defaulting to the ported ring without
  having named the alternative SG13G2 uniquely makes available.
- **Whether an HBT-based bias/reference element (not the oscillator core
  itself) is worth using inside an otherwise-CMOS ring.** A SiGe HBT's `V_be`
  is a well-behaved, low-tempco bandgap-reference building block — this is
  the device class the fleet's own `gf180-bandgap`/`sky130-bandgap` canaries
  are presumably built around on their own processes, and SG13G2's version of
  that same building block is directly reusable inside this block's own
  constant-gm bias core (gf180-pll `design/README.md` § "Bias generator") if
  a bipolar-grade reference improves on the CMOS beta-multiplier's own
  tempco. This is a smaller, lower-risk question than the oscillator-topology
  one above and does not by itself reopen the ring-vs-tank decision.
- **If the ring is retained (the default, absent a decision to the
  contrary): confirm the same current-starved topology and geometric
  band-cascade technique (§1.4) transfer**, and re-derive stage count and
  Kvco table from a SG13G2-specific tuning-range campaign — gf180-pll's own
  `DR-003` found its stage count (5, not the hand-calculated fallback of 3 or
  7) and its Kvco-vs-band-code shape (geometric, not the originally-sketched
  binary-weighted legs) only from real extracted data, and expressly
  disclaims either as portable without that data (`DR-003` Decision 1/3).

### 2.2 The charge pump — device choices for matching/compliance

Neither sibling's charge pump used anything but CMOS current mirrors and
switches, and gf180-pll's own multi-generation charge-pump history
(§1.4/`design/README.md` §"Charge-error mechanism") is a record of
CMOS-specific matching problems (tail-node charge exchange, mirror finite
output resistance) solved with CMOS-specific fixes (a tracking bias buffer,
wide-swing cascode, unit-element trim). **What SG13G2's bipolar devices add
to this block's option space:**

- **A BJT-based bandgap-style current reference** (again, the fleet's
  bandgap-canary building block) as the source the charge pump's four
  matched current legs (`IBN`/`IBP`/`ICN`/`ICP` in gf180-pll's naming,
  explicitly out of scope for the PLL block itself — `design/README.md` §
  "Bias generation is out of scope for this block") mirror from. This is a
  system-integration question more than a PLL-block one, but SG13G2's own
  answer to it may differ from either sibling's implicit "some external CMOS
  reference" assumption, and should be named in the SG13G2 architecture
  decision record rather than left implicit as it was for both siblings.
- **HBT current mirrors/cascodes as an alternative to the CMOS wide-swing
  cascode**, for the specific matching/compliance problem gf180-pll's own
  device-characterization campaign (`sim/devchar-cp`, feeding `DR-001`
  Decision 1 and the cascode choice in `design/README.md`) picked a CMOS
  wide-swing cascode to solve: an order of magnitude more output resistance
  than a simple mirror, at materially less headroom cost than a self-biased
  cascode. A bipolar current source's own output resistance (`r_o = V_A /
  I_C`, set by Early voltage) and matching characteristics are a genuinely
  different tradeoff surface than a MOSFET mirror's, and are worth a
  disposition-level comparison once SG13G2's own device-characterization
  campaign (the `#4`-equivalent on this repo) runs — not assumed superior or
  inferior without that data.
- **Headroom is the constraint that decides this, not device availability
  alone.** Whichever device class wins, the charge pump's compliance range
  is set by the ratified Vctrl window (§2.4), and both a CMOS cascode and a
  bipolar current source have their own headroom floor (saturation margin vs.
  `V_CE,sat`) that must be checked against whatever that window turns out to
  be — this is the same headroom-analysis obligation sky130-pll's `DR-001`
  already names as "owed work, not an open question" for its own 1.8 V core
  choice (`DR-001` "Consequences," "Reduced Vctrl headroom for the charge
  pump").

### 2.3 The dividers — device/logic-family choice at the target speeds

Both siblings' dividers are static CMOS, chosen specifically because **static
CMOS has no minimum operating frequency** (gf180-pll `DR-001` Decision 3,
"Alternatives considered" rejects TSPC/E-TSPC dynamic logic on exactly this
ground: the divider must keep dividing at the *bottom* of a wide output band,
and slower still during acquisition transients). **What SG13G2's bipolar
devices could change here, weighed against that same constraint:**

- **ECL/CML (emitter-coupled / current-mode logic) dividers**, built from
  SiGe HBTs, are the textbook high-speed divider family in a BiCMOS process
  — used specifically where a target toggle frequency is out of comfortable
  CMOS reach. This only becomes relevant if the re-derived output band
  (§1.2 row 1) pushes the *feedback divider's first stage* toggle frequency
  materially higher than SG13G2's CMOS can close timing at with margin —
  which is not yet known (no SG13G2 output-band data exists) and should not
  be assumed. If it does become relevant, ECL/CML's own **minimum operating
  frequency** floor (current-mode logic typically needs enough tail current
  to keep the differential pair from starving, and a fully static topology
  is not automatic the way it is for CMOS) must be checked against the
  bottom of the re-derived output band and the acquisition-transient
  slow-frequency excursions **before** it is adopted, or SG13G2 would
  reproduce exactly the failure mode gf180-pll's own `DR-001` rejected TSPC
  for.
- **The pragmatic reading, absent a demonstrated speed problem**: keep static
  CMOS as the default for the divider chain (as both siblings did), and treat
  a bipolar/ECL first-stage swap as the same kind of targeted, swappable
  fallback gf180-pll's own `DR-001` already reserves for its "400 MHz
  stretch" contingency (Decision 3 Consequences: "lay out the first ÷2/3 cell
  so it is separately swappable"). SG13G2's re-derived architecture decision
  record should state this as the default and name the specific frequency
  threshold (once known) that would trigger revisiting it — not commit to
  ECL/CML pre-emptively without a demonstrated need, the same discipline
  §2.1 applies to the LC-tank VCO question.

### 2.4 The supply / device-flavor decision: the prerequisite both siblings settled first

Both ports treat this as the **first** decision record, gating every other
row, and this document follows that precedent explicitly rather than
reordering it:

- **gf180-pll**: settled to gf180mcu's 3.3 V thick-oxide flavor exclusively,
  no dual-flavor design, with the 1.8 V core variant formally deferred as "a
  different block, not a variant" (`DR-002` Decision 3).
- **sky130-pll**: settled (ratified, `DR-001`) to the 1.8 V core
  (`nfet_01v8`/`pfet_01v8`), with a medium-/high-voltage I/O-class flavor
  named and explicitly deferred rather than rejected. sky130-pll's own
  framing is directly reusable: "sky130 does not have that same flavor [as
  gf180's 3.3 V core], so porting the flavor was never an available option" —
  the same sentence applies to SG13G2 verbatim, since SG13G2's own menu is
  organized differently again from both.

**SG13G2's own menu, read directly from the DRC/LVS deck source reviewed for
§3 below** (`klayout-tools` `src/klayout_tools/decks/sg13g2.py`, itself
transcribed from IHP-Open-PDK's `general_derivations.lvs`), confirms the
process exposes (at minimum — the deck's own coverage is a curated starter
subset, not a full device menu, §3):

- **A thin-gate-oxide CMOS flavor** (`sg13_lv_nmos`/`sg13_lv_pmos` in
  IHP-Open-PDK's own naming — the deck's *default*, unmarked treatment),
  consistent with SG13G2's documented 1.2 V core logic voltage.
- **A thick-gate-oxide CMOS flavor** (`sg13_hv_nmos`/`sg13_hv_pmos`, keyed
  off the `ThickGateOx` (44/0) marker layer in IHP-Open-PDK's own
  `general_derivations.lvs`), consistent with SG13G2's documented 3.3 V
  I/O-class devices — the same 1.2 V-core/3.3 V-I/O split IHP's own published
  process documentation describes, and structurally the same *shape* of
  two-flavor CMOS menu gf180mcu has (3.3 V thick-oxide only) and sky130
  effectively has (1.8 V core + a deferred medium-voltage flavor), just at a
  third set of voltage points.
- **SiGe HBTs**, which is the axis genuinely new to this port (§2.1–2.3) —
  not modeled at all in the current deck's `EXTRACTION_DECK` (§3.2), so their
  exact device menu (NPN flavor(s), any PNP option, breakdown-voltage
  variants) is not yet independently confirmed from this repo's own toolchain
  and should be pulled from IHP-Open-PDK's own device documentation directly
  as part of ratifying the SG13G2 architecture decision record — this
  document does not assert specific bipolar device names it has not
  independently verified through this repo's own tooling.

**What must be decided, following the same three-way framing both siblings
used:**

1. **1.2 V core CMOS** — the natural default for the digital majority of the
   design (PFD logic, divider, lock detector) on the same reasoning
   sky130-pll's `DR-001` used for its own 1.8 V-core choice: it is where the
   fastest, smallest-geometry devices live, and it is the flavor SG13G2's own
   standard-digital flow is built around. **Costs to weigh explicitly, following
   sky130-pll's own honesty about its analogous 1.8 V costs**: at 1.2 V the
   Vctrl headroom for the charge pump and loop filter is narrower still than
   sky130's already-tightened 1.8 V window — sky130-pll's `DR-001` already
   flags "roughly a third of gf180-pll's 3.3 V window" at 1.8 V; 1.2 V is
   narrower again, proportionally. **This is the single sharpest quantified
   risk this port carries forward from the sky130 precedent** and should be
   named as such in SG13G2's own decision record, not merely inherited by
   implication.
2. **3.3 V thick-oxide CMOS** — the flavor structurally closest to gf180-pll's
   own choice, and the one that would give the charge pump/loop filter the
   most Vctrl headroom of the three CMOS-adjacent options, at the cost of the
   slower device speed and larger area a thick-oxide device carries relative
   to the thin-oxide 1.2 V option, mirroring exactly the tradeoff sky130-pll's
   `DR-001` weighed (and deferred, not rejected) for its own medium-/
   high-voltage I/O-class alternative.
3. **Bipolar, where it earns its place** — not a whole-block flavor choice
   the way (1) and (2) are (nothing in either sibling's block set, or in this
   document's own §2.1–2.3 analysis, argues for an *all-bipolar* PLL), but a
   **per-element** decision: the VCO core (§2.1, only if the LC-tank
   comparison in that section resolves in its favor), a bandgap-style bias
   reference feeding the charge pump (§2.2), and a possible ECL/CML divider
   first stage (§2.3, only if a demonstrated speed need arises) are each
   independently arguable bipolar insertions into an otherwise-CMOS block,
   not a device-flavor commitment for the whole design.

**Recommendation for the eventual decision record**: frame this explicitly as
"which CMOS core flavor, plus which specific bipolar insertions, and why,"
rather than as a single three-way pick the way both siblings' simpler
CMOS-only menus allowed — SG13G2's menu does not collapse to one axis the way
gf180mcu's and sky130's each did.

---

## 3. What the starter-grade SG13G2 deck can't check yet

This section is read **directly from the deck's current source**
(`2AMLogic/klayout-tools` `src/klayout_tools/decks/sg13g2.py`, as of the
commit reviewed for this document — see that file's own module docstring for
its exact provenance pin) and from the open tracking issue for the
full-scope deck (`2AMLogic/klayout-tools` **#524**, still open as of this
writing). It is not a guess about what a "starter-grade" deck might be
missing — the gaps below are stated in the deck's own source comments.

### 3.1 Why the deck is starter-grade, structurally

Unlike sky130 and gf180mcu (both of which already had a hand-curated deck
before klayout-tools' provenance-first deck-compiler epic existed, so that
epic's work was to backfill citations onto an already-shipping deck), **no
hand-written `sg13g2.py` deck existed in klayout-tools before the
deck-compiler epic reached it** (issue #905, per the module's own docstring).
The traditional hand-curation issue for this deck, **#524**, was filed and
twice rejected by Champion review as an oversized single-PR scope (a
full sky130/gf180mcu-sized deck, hundreds of rules, attempted in one pass
rather than grown rule-group-by-rule-group the way both existing decks
actually were) and **remains open, unmerged**. What exists today is a
narrower, compiler-generated "curated starter subset" (issue #905) covering
one connected FEOL-to-BEOL2 stack, wide enough to draw and route a two-terminal
CMOS device and nothing more.

### 3.2 What is covered today

- **DRC**: Activ, GatPoly, Cont, Metal1, Via1, Metal2, Via2 — general-case
  minimum-width/spacing/enclosure rules only, each transcribed with a cited
  `RuleProvenance` (IHP-Open-PDK source file + rule id).
- **LVS / device extraction**: MOSFET recognition only, and specifically
  **only the thin-oxide ("-LV") NMOS/PMOS pair** (`sg13_lv_nmos`,
  `sg13_lv_pmos`).

### 3.3 What is explicitly *not* covered — the deck gaps this port will hit

Named directly from the deck module's own "Scope guard," "No #524
cross-check," and inline field-level comments:

| Gap | What breaks for this port | Where the block is planned |
|---|---|---|
| **No thick-gate-oxide ("-HV") MOS device recognition.** The deck's own comment states plainly: geometry drawn entirely inside the `ThickGateOx` (44/0) marker "extracts with the *wrong* (thin-oxide) device-class provenance rather than being recognised as the real `sg13_hv_nmos`/`sg13_hv_pmos` device or rejected outright." | **Directly blocks the 3.3 V thick-oxide CMOS option named in §2.4** — if that flavor is chosen for any element (or for the whole design), LVS will silently misclassify every thick-oxide device as thin-oxide, which is a wrong-netlist failure, not merely a missing-coverage one. This is the sharpest gap in the whole document, because it fails *silently* rather than by refusing to extract | Loop filter / VCO / charge pump / dividers — any block, if the 3.3 V-flavor branch of §2.4 is chosen |
| **No bipolar device recognition of any kind.** The `EXTRACTION_DECK`'s own docstring and field set cover only `nfet_class`/`pfet_class`; there is no HBT/BJT device-recognition path in the module at all. | **Blocks any bipolar insertion named in §2.1–2.3 from reaching LVS at all** — an HBT in a schematic would extract as unrecognized geometry, not as a matched device with the wrong class (worse than the thick-oxide case: at least that one runs to a wrong answer; this one likely doesn't run) | VCO core (if LC-tank, §2.1), bias reference (§2.2), divider first stage (if ECL/CML, §2.3) |
| **No resistor or capacitor device recognition.** Not named as covered anywhere in the module — the deck models MOS devices and the routing stack (Metal1/Via1/Metal2/Via2) only. | **Directly blocks the loop filter** — every sibling's loop filter is a precision R + C1 + C2 network (gf180-pll: `ppolyf_u` resistor + `cap_nmos_03v3_b`/`cap_mim_2f0_m2m3` caps, §1.4), and none of those device *classes* (precision poly resistor, MOS cap, MIM cap) has an LVS recognition rule in the current deck | Loop filter — the single highest-priority classic-analog device gap, since every carried-over architecture (§1.1) needs this block in some form |
| **No metal levels above Metal2 / vias above Via2.** | **Limits floorplanning and routing options** for anything that needs more than a two-metal stack — likely to matter for the top-level assembly (§1.1's `pll_top`-equivalent) more than any single block, since gf180-pll's own top level routes 5+ blocks together | Top-level integration |
| **No area/density/antenna checks** (sg13g2's own `density.drc`/`antenna.drc` files, out of the deck-compiler epic's stated scope entirely, not merely deferred). | **A tapeout-readiness gap, not a schematic/pre-layout gap** — will not block early design work, but should be tracked before this repo reaches a layout-signoff milestone | Whole-chip, layout stage |
| **No matching-sensitive-structure checks** (interdigitation, common-centroid, dummy-fill-for-matching rules) — not named at all in the deck, consistent with sky130.py's/gf180mcu.py's own documented "no compound/derived-layer evaluation" limits for this class of rule. | **Matters most for exactly the blocks this port is most exposed on**: the charge pump's current mirrors (§2.2, where gf180-pll's own multi-generation history shows matching dominates the error budget) and any bipolar current mirror/reference (§2.1–2.2, where HBT `V_be` matching is the whole point of using the device class) | Charge pump, bias/reference elements |
| **No compound-derivation refinements** (`Gat.a1`/`Gat.a2` channel-length-specific poly width scoped to `ngate`/`pgate`, `Cnt.c`/`Cnt.d`/`Cnt.e`-family contact-enclosure refinements scoped to SRAM/DigiBnd carve-outs, wide-metal 45°-bend spacing rules) — named explicitly in the deck's own "Scope guard" as deferred, with the general-case rule this deck *does* carry standing in as a conservative (not exact) floor. | Lower-priority than the gaps above (each has a conservative general-case rule already covering it), but means a DRC-clean result today is not a guarantee against the *real*, more-refined foundry rule at layout time | Any block, at layout signoff |

### 3.4 What to file, and when

Per this repo's own CLAUDE.md ("Deck gaps ... are *expected* friction here,
not a surprise. When you hit one, file it upstream rather than routing around
it"), the gaps above should be filed at `2AMLogic/klayout-tools` **as each
block's design work actually reaches the point of needing the corresponding
device class** — not all at once here, and not speculatively for gaps a
chosen architecture might never touch:

- **File early, once §2.4's supply-flavor decision record lands**: if the
  3.3 V thick-oxide flavor is chosen for *any* element, the missing `-HV`
  MOS recognition gap should be filed immediately, since it fails silently
  (wrong device class, not a hard error) and is the kind of gap this repo's
  CLAUDE.md specifically warns is dangerous to discover mid-layout rather
  than up front.
- **File once the loop-filter block's own device choice is made** (the
  §1.4-carried R+C1+C2 topology, sized against whichever SG13G2 resistor/cap
  primitives the device-characterization campaign — this repo's own
  `#4`-equivalent — identifies): the missing resistor/capacitor LVS
  recognition gap, naming the specific device class(es) chosen (analogous to
  gf180-pll's `ppolyf_u`/`cap_nmos_03v3_b`/`cap_mim_2f0_m2m3` picks) so the
  filed issue is concrete rather than generic, per this repo's own CLAUDE.md
  instruction to "describe the gap, not the design" — i.e. name the missing
  device-recognition capability itself (e.g. "LVS cannot recognize precision
  poly resistors" / "LVS cannot recognize MIM capacitors"), not this block's
  internal sizing.
- **File only if §2.1's or §2.2's bipolar-insertion questions resolve toward
  actually using an HBT anywhere**: the missing bipolar device-recognition
  gap. Filing this speculatively, before any bipolar element is actually
  chosen, would front-load tool work against a design decision that may not
  land that way (§2.1's LC-tank VCO question in particular is framed to
  default toward the ported ring, not toward bipolar, absent a specific
  reason).
- **File once a design genuinely needs more than two metal levels or exceeds
  Via2** (most likely at top-level integration, per §3.3), and separately,
  **once this repo approaches its own layout-signoff milestone**, for the
  area/density/antenna gap named as explicitly out of the deck-compiler
  epic's scope rather than merely unaddressed yet.

None of the above is filed by this document — per the issue's own scope
("No design work in this issue"), no block's device choice is final enough
yet to file a concrete, non-speculative gap report. This section exists so
that when each block's work does reach that point, the filing is a lookup
against this table rather than a fresh discovery.

---

## Summary: what this hands to the next decision record

1. **Architecture**: survey the same four questions gf180-pll's `DR-001`
   surveyed (loop type, VCO delay-cell/device-class style, divider
   architecture) plus a **fourth, new** question neither sibling had — which
   specific bipolar insertions, if any (§2.1–2.3) — and settle them together,
   since SG13G2's bipolar option genuinely couples into the VCO-topology
   question in a way neither sibling's survey needed to consider.
2. **Supply / device flavor**: settle 1.2 V core vs. 3.3 V thick-oxide vs.
   per-element bipolar (§2.4) as the first, prerequisite decision record,
   following both siblings' precedent of settling this before any block's
   sizing work starts.
3. **Spec draft**: once flavor is settled, draft `spec/target-spec.md` (or
   this repo's equivalent) using sky130-pll's own row shape — DRAFT target,
   source citation, explicit re-derive/confirm/port-and-verify stance per row
   — seeded from §1.2 above rather than from a blank table.
4. **Deck gaps**: file the specific, concrete gaps named in §3.4 at
   `2AMLogic/klayout-tools`, gated on each block's own design decision
   actually landing, not speculatively.
