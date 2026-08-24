# DR-002: Supply / device flavor, and the remaining per-element bipolar questions

- **Status**: proposed
- **Date**: 2026-08-24
- **Decided by**: Builder agent, issue #8
- **Related**: #1 (porting plan this record consumes), #6 (T1 checklist —
  this record and DR-001 satisfy item 1), #7 (commit design sources — blocked
  on this record per #8's own problem statement: "the supply/device-flavor
  choice this record settles directly determines which device library the
  schematics in #7 are drawn against"), #8 (this issue), DR-001 (architecture
  — loop type / VCO topology / divider family this record's flavor choice
  applies to)
- **Consumes**: `spec/porting-plan.md` §1.2 row 0 (supply/device flavor) and
  row 18 (supply range), §2.2 ("The charge pump — device choices for
  matching/compliance"), §2.3 ("The dividers"), §2.4 ("The supply /
  device-flavor decision: the prerequisite both siblings settled first"),
  §3 ("What the starter-grade SG13G2 deck can't check yet") and its §3.4
  filing guidance, and the "Summary" section's item 2
- **Sibling precedent cited throughout**: `2AMLogic/gf180-pll`
  `spec/decision-records/DR-002-draft-spec-scope-ratification.md` Decision 3
  (cited by porting-plan.md, not independently re-fetched — porting-plan.md's
  own citation of "settled to gf180mcu's 3.3 V thick-oxide flavor
  exclusively... with the 1.8 V core variant formally deferred as 'a
  different block, not a variant'" is taken as accurate to that record);
  `2AMLogic/sky130-pll` `spec/decision-records/DR-001-supply-flavor-scope.md`
  (fetched via `gh api` from that repo directly — the byte-for-byte source,
  not a from-memory reconstruction) for the supply-flavor decision-record
  framing this record follows most closely

---

## Decision summary

| # | Question | Decision | Trigger to revisit |
|---|---|---|---|
| 0 | CMOS supply / device flavor | **3.3 V thick-oxide CMOS throughout** (`sg13_hv_nmos`/`sg13_hv_pmos`) — VCO, charge pump, loop filter, PFD, feedback divider, lock detector all drawn on the same flavor. 1.2 V thin-oxide CMOS core (`sg13_lv_nmos`/`sg13_lv_pmos`) formally **deferred**, not adopted, for any element in v1. | A demonstrated power/area finding that the 3.3 V digital majority (PFD/divider/lock-detector) cannot meet a future power or area budget with margin — see "Alternatives considered" |
| 1 | Bias reference (porting-plan §2.2) | **Deferred, out of this block's scope** — no HBT bandgap-style reference designed as part of this PLL | A system-level SG13G2 bias/reference block is designed (this repo's own bandgap-canary-class work, if one exists) and is shown, with extracted data, to beat a CMOS beta-multiplier's tempco for this block's own current legs |
| 2 | Charge-pump current-source/cascode device class (porting-plan §2.2) | **Default: CMOS wide-swing cascode**, matching gf180-pll's own device/technique table (porting-plan §1.4). HBT current mirror/cascode **deferred**, not adopted. | SG13G2's own device-characterization campaign (this repo's forthcoming `#4`-class issue) produces extracted `r_o`/matching data showing an HBT current source clears the ratified Vctrl-headroom floor with a real compliance-range or matching advantage over the CMOS cascode |
| 3 | Divider first-stage logic family (porting-plan §2.3) | **Default: static CMOS throughout** the ÷2/3 chain (DR-001 Decision 3). ECL/CML HBT first stage **deferred**, not adopted. | The re-derived output band (porting-plan §1.2 row 1) pushes the first ÷2/3 cell's toggle frequency materially above what 3.3 V thick-oxide static CMOS closes with margin at the slow corner |

---

## Context

Porting-plan §2.4 names this the prerequisite decision both sibling repos
settled first, gating every other spec row (porting-plan §1.2 row 0: "the
single prerequisite gate"). SG13G2's own device menu, read directly from
`2AMLogic/klayout-tools` `src/klayout_tools/decks/sg13g2.py` as of the
porting plan's review, offers a three-way menu neither sibling had:

- **1.2 V thin-oxide CMOS** (`sg13_lv_nmos`/`sg13_lv_pmos`) — SG13G2's
  default-flavor, fastest/smallest-geometry devices, matching the process's
  documented 1.2 V core logic voltage and its native `sg13g2_stdcell`
  standard-digital-cell library's operating point.
- **3.3 V thick-oxide CMOS** (`sg13_hv_nmos`/`sg13_hv_pmos`, keyed off the
  `ThickGateOx` (44/0) marker layer) — matching SG13G2's documented 3.3 V
  I/O-class devices.
- **SiGe HBTs**, the axis genuinely new to this port (porting-plan §2.1–2.3),
  not modeled at all in the LVS deck as reviewed for the porting plan.

Neither sibling repo had a literal counterpart to this three-way split.
gf180mcu has only the one 3.3 V thick-oxide flavor it built on exclusively.
sky130 has no 3.3 V-*core* flavor at all — its own `DR-001` states plainly
"sky130 simply does not have a 3.3 V core device family the way gf180
does... 'port the flavor' is not an available option" — so sky130-pll had to
choose between two options that were each, in their own way, a departure
from gf180-pll's device class (1.8 V core vs. a 5 V-tolerant I/O class).
**SG13G2 is different: its thick-oxide `sg13_hv_nmos`/`sg13_hv_pmos` pair is
the same 3.3 V voltage class as gf180-pll's `nfet_03v3`/`pfet_03v3`.** This
is, for the first time in this fleet, a case where the device *flavor*
itself — not merely the circuit topology — can be ported essentially as-is
from the most mature, measured reference design, rather than re-derived from
a mismatched menu the way sky130-pll had to.

## Decision 0 — CMOS supply / device flavor

### Decision

**3.3 V thick-oxide CMOS throughout the design** — the VCO (ring core,
bias/starving mirror, V→I converter), the charge pump, the loop filter's
active-adjacent elements, the PFD, the feedback divider chain (including its
final VCO-clocked retiming flop), and the lock detector are all drawn on
`sg13_hv_nmos`/`sg13_hv_pmos`. No dual-flavor split and no per-element CMOS
flavor mix in v1.

### Alternatives considered

- **1.2 V thin-oxide CMOS core throughout.** This is the natural default for
  the digital majority on the same reasoning sky130-pll's `DR-001` used for
  its own 1.8 V-core choice: fastest, smallest-geometry devices, matching the
  process's native `sg13g2_stdcell` digital-flow operating point. **Rejected
  as the primary flavor** on the Vctrl-headroom cost porting-plan §2.4 names
  as "the single sharpest quantified risk this port carries forward from the
  sky130 precedent": sky130-pll's own `DR-001` already flags a 1.8 V rail as
  giving the charge pump/loop filter "roughly a third of gf180-pll's 3.3 V
  window"; a 1.2 V rail is narrower again, proportionally. Reduced Vctrl
  headroom directly tightens the charge-pump current-source compliance
  range, the switch overdrive, and the usable fraction of the Vctrl window
  for linear VCO tuning — exactly the risk both siblings flag as the
  dominant one for this block (porting-plan §1.2 row 12, "the block's
  dominant risk, and it is structural"). A 1.2 V flavor would make that risk
  worse than either prior design accepted, not merely as bad.
- **A per-element mix** (e.g., 3.3 V thick-oxide for the Vctrl-sensitive
  analog core — VCO, charge pump, loop filter — and 1.2 V thin-oxide for the
  purely digital blocks that never touch the Vctrl node — PFD logic,
  divider, lock detector). **Considered seriously and rejected for v1**,
  for two reasons:
  1. **It introduces an interface cost neither sibling design needed.** A
     split-domain design requires level-shifting every dynamic signal that
     crosses the boundary at PLL operating rates — most critically the
     PFD's UP/DN outputs driving the charge pump's switches, which toggle
     every reference cycle and sit directly in the phase-detection path.
     Getting that level shifter's delay and matching wrong reopens exactly
     the charge-domain dead-zone/mismatch risk porting-plan §1.3 flags as a
     methodology this port must characterize carefully ("a logic-correct-
     looking PFD that measurably failed 9/45 corners in the *charge* domain
     while its waveforms looked perfect," gf180-pll's own history). Adding a
     new, unproven interface element directly in that path is exactly the
     kind of invented complexity this repo's own porting-plan discipline
     argues against absent a demonstrated need (the same "do not commit
     pre-emptively without a demonstrated need" reasoning porting-plan §2.3
     applies to the ECL/CML divider question below).
  2. **The native-library argument for 1.2 V is weaker here than it was for
     sky130-pll.** sky130-pll's own choice of a synchronous-counter divider
     (rather than gf180-pll's ÷2/3 cascade) is best explained by its 1.8 V
     core flavor matching `sky130_fd_sc_hd`'s own stdcell flops, making
     reuse cheap. But per DR-001 Decision 3, this design's own PFD logic,
     ÷2/3 modulus cells, and lock detector are **custom-drawn transistor-level
     cells regardless of flavor** (matching both siblings' leaf-cell-ownership
     convention, porting-plan §1.3/§1.4) — none of them is a generic
     synthesizable stdcell instance this design would otherwise get "for
     free" from `sg13g2_stdcell` at 1.2 V. The digital-library-reuse argument
     that would favor a mixed flavor does not actually apply to this design's
     own cell set.
  3. At 130 nm-class geometry, the speed/area difference between thick- and
     thin-oxide devices does not bind at this block's own operating rates
     (kHz to a few hundred MHz, per the carried-over spec shape) the way it
     would at multi-GHz digital clock rates — so the 1.2 V flavor's headline
     speed advantage buys little here, while its headroom cost (above) is
     real and immediate.
  A mixed flavor remains a legitimate future optimization if a later finding
  demonstrates the 3.3 V digital blocks cannot meet a specific power or area
  target with margin (see Decision-summary trigger column) — this record
  defers it rather than rejecting it outright, mirroring how sky130-pll's own
  `DR-001` deferred (not rejected) its medium-/high-voltage alternative.
- **Port gf180-pll's exact device names unchanged.** Rejected outright as
  stated — SG13G2 has no literal `nfet_03v3`/`pfet_03v3`; `sg13_hv_nmos`/
  `sg13_hv_pmos` is the same *voltage class*, not the same device, and every
  number (Kvco, Icp, filter R/C, area) must still be re-derived against
  SG13G2's own device data per porting-plan §1.2's per-row disposition.

### Consequences

**What this fixes:**

- **Maximum Vctrl headroom of the three CMOS-adjacent options**, directly
  addressing the sharpest risk porting-plan §2.4 names, and putting this
  design in the same headroom regime gf180-pll's own measured design already
  operates in (Vctrl usable over roughly 0.9–2.4 V of gf180-pll's 3.3 V rail,
  per that record — SG13G2's own equivalent window is re-derived, not
  assumed, but starts from the same voltage class rather than a tighter one).
- **The closest-to-literal device-flavor port available in this fleet.**
  Unlike sky130-pll, which had no 3.3 V-class device to port to at all, this
  choice lets DR-001's ported-topology decisions (loop type, VCO family,
  divider family) carry over with the *same* voltage-class assumptions
  gf180-pll's own decisions were reasoned against, rather than requiring a
  fresh headroom re-argument the way sky130-pll's 1.8 V choice did.
- **No new interface element** (level shifter) in the PFD-to-charge-pump
  path, and no new supply-domain-crossing risk beyond what both siblings
  already carry (their own `vdd_ref`/`vdd_vco`/`vdd_div` domain split,
  porting-plan §1.1, is a *domain* separation for noise isolation, not a
  *device-flavor* separation — this design keeps that same domain split,
  all domains at the same 3.3 V-class flavor).

**What this costs, and hands to design:**

- **Forgoes the 1.2 V flavor's speed/area/power advantage** for the digital
  majority. If a later finding shows this binds against a real budget, the
  mixed-flavor alternative above is the documented fallback, not a
  from-scratch redesign.
- **Every number is still re-derive, not port.** This decision fixes the
  device *class*; Kvco, Icp, filter R/C, area, and power (porting-plan §1.2
  rows 4/5, 6/6a, 11, 15) are all "re-derive" regardless of flavor choice,
  because SG13G2's own device models differ from gf180mcu's even at the same
  nominal voltage class.
- **LVS coverage**, addressed directly below.

### Deck-gap check (porting-plan §3.4: "file early, once §2.4's supply-flavor
decision record lands")

Porting-plan §3.3/§3.4, as written at the time the plan was drafted
(2026-08-20), states the SG13G2 LVS deck recognized **only** the thin-oxide
MOS pair and would silently mis-classify any thick-oxide device drawn inside
`ThickGateOx` as the thin-oxide device — "the sharpest gap in the whole
document, because it fails *silently*." Per porting-plan §3.4's own
instruction, this gap should be "filed immediately" if the 3.3 V thick-oxide
flavor is chosen for any element.

**This gap has already been closed upstream, independent of this record.**
`2AMLogic/klayout-tools` issue #1231 ("SG13G2 extraction deck... only
recognizes thin-oxide MOS — no HV-MOS, bipolar, resistor, capacitor, or
diode device classes," filed 2026-08-20, the same day the porting plan was
reviewed) tracked exactly this gap, and its linked PR #1236 ("feat: recognize
sg13g2 thick-oxide MOS and rsil/rppd poly resistors") landed a `mos_flavours`
mechanism that recognizes `ThickGateOx`-scoped geometry as the real
`sg13_hv_nmos`/`sg13_hv_pmos` device, with a golden-pair positive test and a
negative-control test proving the prior silent mis-classification is fixed
(`tests/test_sg13g2_deck.py::test_golden_pair_sg13g2_thick_oxide_nmos_binds_sg13_hv_nmos`
and `..._was_misclassified_before_mos_flavours`). Issue #1231 is **closed**
and PR #1236 is **merged** as of this record.

**Verified before deciding not to file a duplicate** (per this repo's own
"audit before filing" discipline): confirmed directly via `gh api`/`gh issue
view`/`gh pr view` against `2AMLogic/klayout-tools` at the time this record
was written — issue #1231's state is `CLOSED`, its `closedByPullRequestsReferences`
field points to PR #1236, and PR #1236's own body itemizes the golden-pair
and negative-control test names verifying the fix. This is not assumed from
the porting plan's (now-stale, as of the deck-gap section specifically)
description — it is independently re-checked against the tool repo's current
state. **No new gap issue is filed by this record.** Filing one would be a
duplicate of already-resolved upstream work, which the audit-before-filing
discipline this repo's own builder conventions apply exists specifically to
avoid.

(The porting plan's remaining §3.3 gaps — bipolar device recognition, MIM
capacitor recognition, resistor coverage beyond `rsil`/`rppd`, metal levels
above Metal2 — were separately split into `2AMLogic/klayout-tools` issues
#1232, #1233, #1235 respectively, also already filed independent of this
record. None of those gaps binds this record's decisions: no bipolar device
is adopted below, and the loop filter's own resistor/capacitor device choice
is out of this record's scope per porting-plan §3.4's own sequencing — "file
once the loop-filter block's own device choice is made.")

---

## Decision 1 — Bias reference (porting-plan §2.2)

### Decision

**Deferred, out of this PLL block's scope.** No HBT bandgap-style current
reference is designed as part of this repository's PLL block. The charge
pump's matched current legs are sourced from whatever bias reference an
eventual system integration provides, exactly as gf180-pll's own
`design/README.md` states for its own design ("Bias generation is out of
scope for this block").

### Alternatives considered

- **Design an HBT-based bandgap-style reference as part of this block.**
  Rejected as out of scope, following gf180-pll's own precedent directly:
  neither sibling design owns bias generation, and nothing about SG13G2's
  bipolar option changes that scope boundary — it changes what device class
  a *future, separately-scoped* bias-generator block (this fleet's own
  bandgap-canary pattern, e.g. `gf180-bandgap`/`sky130-bandgap`) might use,
  which is a different repository's decision, not this one's.
- **Name it and defer, rather than omit it silently** — chosen, per this
  issue's own acceptance criterion that bipolar insertions be "named
  explicitly... or explicitly deferred with a stated trigger condition, not
  silently omitted." Trigger: if/when a system-level SG13G2 bias/reference
  block is designed (in this repo or a sibling bandgap-canary-class repo)
  and demonstrates, with real extracted device data, that an HBT-based
  reference improves on a CMOS beta-multiplier's tempco for the specific
  current legs this charge pump needs.

### Consequences

None to this block's own design work — the charge pump's bias-current
interface contract (four matched legs, magnitude and matching tolerance) is
unchanged by this decision; it only states that *generating* those currents
is not this block's problem, matching both siblings' own scope boundary.

---

## Decision 2 — Charge-pump current-source/cascode device class (porting-plan §2.2)

### Decision

**Default: CMOS wide-swing cascode**, directly porting the device/technique
carried in porting-plan §1.4 ("wide-swing cascode output stage for
compliance-range headroom... shared, buffered ('tracking') dump node"),
drawn on the 3.3 V thick-oxide flavor decided above. **HBT current
mirrors/cascodes as an alternative are named explicitly and deferred, not
adopted.**

### Alternatives considered

- **HBT current mirror/cascode**, per porting-plan §2.2's own framing: "a
  bipolar current source's own output resistance (`r_o = V_A/I_C`, set by
  Early voltage) and matching characteristics are a genuinely different
  tradeoff surface than a MOSFET mirror's, and are worth a
  disposition-level comparison once SG13G2's own device-characterization
  campaign... runs — not assumed superior or inferior without that data."
  This record adopts that framing directly: no device-characterization data
  exists yet for SG13G2's HBTs from this repo's own tooling (porting-plan
  §2.4's own caveat: bipolar device menu details "not yet independently
  confirmed from this repo's own toolchain"), so there is nothing to compare
  the CMOS cascode against yet. Deferred, trigger: SG13G2's device-
  characterization campaign (this repo's forthcoming `#4`-class issue)
  produces extracted `r_o`/matching data for an available HBT flavor showing
  a real compliance-range or matching advantage over the CMOS wide-swing
  cascode at the ratified Vctrl-headroom window (Decision 0 above).
- **CMOS wide-swing cascode** — chosen as the default, matching gf180-pll's
  own precedent directly (its own device-characterization campaign,
  `sim/devchar-cp`, already picked this specific device/technique for the
  matching/compliance problem an order of magnitude better than a simple
  mirror). Since this design shares gf180-pll's own 3.3 V-class flavor
  (Decision 0), that precedent transfers with more confidence than it would
  have to a 1.2 V or mixed-flavor design.

### Consequences

- The charge pump's headroom analysis (owed work per Decision 0's own
  Consequences, and per sky130-pll `DR-001`'s framing of this as "owed work,
  not an open question") is scoped against a CMOS cascode's saturation-margin
  floor, not a bipolar `V_CE,sat` floor, until/unless the trigger above fires.
- No bipolar device appears in the charge pump schematic committed in #7.

---

## Decision 3 — Divider first-stage logic family (porting-plan §2.3)

### Decision

**Default: static CMOS throughout the ÷2/3 chain**, per DR-001 Decision 3 —
no dynamic logic, no ECL/CML in v1. **An HBT-based ECL/CML first stage is
named explicitly and deferred, not adopted**, exactly as porting-plan §2.3
recommends ("state this as the default and name the specific frequency
threshold... that would trigger revisiting it — not commit to ECL/CML
pre-emptively without a demonstrated need").

### Alternatives considered

- **ECL/CML first-stage divider** — the textbook high-speed BiCMOS divider
  family, but its own minimum-operating-frequency floor (current-mode logic
  needs enough tail current to keep the differential pair from starving) is
  exactly the same failure mode DR-001 Decision 3 already rejected TSPC/
  E-TSPC dynamic CMOS logic for: a divider that stops dividing at the bottom
  of the band or during acquisition transients cannot acquire. Adopting it
  without a demonstrated speed need would reproduce that rejected failure
  mode on different logic, not avoid it. Deferred, trigger: the re-derived
  output band (porting-plan §1.2 row 1, currently unknown) pushes the first
  ÷2/3 cell's toggle-frequency requirement materially above what 3.3 V
  thick-oxide static CMOS can close with margin at the slow corner — the
  same condition gf180-pll's own `DR-001` names for its documented
  TSPC/E-TSPC fallback, generalized to a BiCMOS alternative.
- **Static CMOS throughout** — chosen as the default, per DR-001 Decision 3
  and this record's Decision 0 (no matching-library shortcut changes the
  economics here either).

### Consequences

- The first ÷2/3 cell should be laid out as separately swappable (gf180-pll
  `DR-001` Decision 3 Consequences: "lay out the first ÷2/3 cell so it is
  separately swappable"), so that if the trigger above fires, an ECL/CML
  replacement is a targeted cell swap, not a chain redesign.
- No bipolar device appears in the divider schematic committed in #7 unless
  and until the trigger fires and a superseding record is written.

---

## Status notes

This record and DR-001 together satisfy #8's acceptance criteria and are the
two prerequisite decision records `spec/porting-plan.md`'s own closing
Summary names before #7 (commit design sources) or any further T1 checklist
item in #6 can proceed. Per this repo's own decision-record discipline
(`spec/decision-records/TEMPLATE.md`), this record stays `proposed` until
reviewed and merged through this repo's normal PR lifecycle (Judge/Champion
review, per `.loom/CLAUDE.md`); merge of the PR that lands this record is
what makes it binding on #7's own schematic work, since this repo has no
separate operator-ratification issue the way `2AMLogic/gf180-pll`'s #1 or
`2AMLogic/sky130-pll`'s #1 served that role. If a future finding overturns
any decision here, supersede this record with a new `DR-NNN` rather than
editing it in place, per this repo's append-only decision-record convention.
