# DR-003: SG13CMOS5L port readiness — device audit, rail interpretation, tooling gate

- **Status**: proposed
- **Date**: 2026-08-29
- **Decided by**: Builder agent, issue #16
- **Related**: #16 ([Epic 2AMLogic/2am#542] Phase 5A — port to SG13CMOS5L
  for Chipalooza Challenge #6), DR-001 (PLL architecture — loop type, VCO
  topology, feedback divider; carries over unmodified, see "What this does
  NOT decide" below), DR-002 (supply/device flavor — the record this one
  audits against SG13CMOS5L's real device library)
- **Consumes**: `docs/pdk/sg13cmos5l.md` (2AMLogic/2am, the Phase 2A
  go/no-go verdict and SG13G2→SG13CMOS5L diff notes), 2AMLogic/2am#542 (the
  Chipalooza epic), 2AMLogic/2am#547 (Phase 2A, the doc above's own tracking
  issue), 2AMLogic/sg13g2-bandgap#63 (the fleet's one prior SG13CMOS5L port,
  cited throughout as precedent for scope and evidence shape)

---

## Context

Issue #16 asks this repo to port the whole PLL — schematic, layout,
verification — from IHP SG13G2 to IHP SG13CMOS5L against the Chipalooza
Challenge #6 brief (1.2 V digital / 3.3 V analog rails, the slot budget in
`docs/pdk/sg13cmos5l.md`), at the brief's full sign-off bar (post-layout PVT
simulation, DRC/LVS-clean GDS, a `docs/chipalooza/challenge-6-proposal.md`
with every spec row re-derived from real `sim/` results).

That is not a single-session scope. The one fleet precedent for this exact
kind of port — `sg13g2-bandgap`'s own SG13CMOS5L port (issue #63) — took
**four planned phase issues plus five unplanned follow-ons** (#64, #65, #66,
#67, then #73, #74, #76, #81, #84) across several days to reach DRC-clean
layout, and its post-layout PVT-simulation phase (#84) is still open as of
this record. That was for a bandgap: one composite cell, three sub-blocks,
no closed-loop dynamics. This repo's PLL has six blocks (`pfd`, `cp`,
`loop_filter`, `vco`, `divider_chain`, `lock_detector`) with closed-loop
timing sensitivity DR-001/DR-002 already flag as the design's dominant risk
on SG13G2 itself — and SG13G2's own maturity is not there yet either: `sim/`
has no committed PVT results for this design at all yet (only a scope
`README.md`), and `layout/pll/README.md`'s own current record composes each
block's devices but has no `pll_top` netlist or routed connectivity. A
same-session full port, sign-off included, is not achievable honestly.

Per this repo's own CLAUDE.md ("the PDK is the variable, not the design")
and the builder complexity-assessment discipline, this record does the
**readiness-audit** work a same-session pass can respond to genuine
evidence for — reading the installed SG13CMOS5L PDK directly (not assumed
from the bandgap port's own findings) against *this* design's actual
committed netlist — and hands the schematic-port / sim / layout / proposal
phases to separately-scoped follow-up issues, mirroring #63's own
decomposition shape.

## What was actually checked (not assumed from the bandgap precedent)

- **PDK install, independently confirmed on this host**: `~/share/pdk/ihp-sg13cmos5l`
  present, `klt pdk find --pdk ihp-sg13cmos5l --pdk-root ~/share/pdk`
  resolves `ngspice`/`xschem`/`klayout`/`magic`/`netgen` asset directories.
  `ReleaseNote.md` in the installed tree reads `v0.2.0`.
- **This design's own device inventory**, read directly from the five
  committed netlists (`design/netlist/{cp,divider_chain,lock_detector,
  loop_filter,pfd,vco}.spice`, `grep`'d for every device-class token, not
  guessed from the schematics): `sg13_hv_nmos`, `sg13_hv_pmos`, `rppd`,
  `rhigh`, `cap_cmim`. **No bipolar device appears anywhere in this
  design** — DR-002 Decisions 1–3 already deferred every per-element
  bipolar option (bias reference, charge-pump cascode, divider first
  stage), so this design has no `npn13G2` (or any HBT) instance to port at
  all.
- **The installed SG13CMOS5L PDK's own device library**, read directly from
  `libs.tech/xschem/sg13cmos5l_pr/*.sym` and
  `libs.tech/ngspice/models/{sg13g2_moshv_mod,resistors_mod,cap_cmomi,
  cap_cmomf}.lib` — not from `ReleaseNote.md`'s prose summary alone.
- **The installed layout tool's current deck coverage**: `klt drc --help`
  (installed system `klt`, `0.3.0+g3f98b441bf2f`) and the version this
  repo's own `layout/requirements.txt` pins for the SG13G2 layout flow
  (`klayout-tools@5482cfe1c67eacf9d2f27d750a11a37ec14b1984`, issue #13/#14).
- **klayout-tools#1398** (SG13CMOS5L tech-map registration), fetched via
  `gh issue view` directly against `2AMLogic/klayout-tools` — confirmed
  `CLOSED`, not assumed from `docs/pdk/sg13cmos5l.md`'s own (now-stale, as
  of that doc's writing) "no SG13CMOS5L DRC/LVS deck exists yet" note.
- **`sg13g2-bandgap`'s own SG13CMOS5L layout evidence**
  (`layout/sg13cmos5l-bandgap_core/drc_report.json`), fetched via `gh api`
  directly against that repo — confirms a real `"deck": "sg13cmos5l"` DRC
  run exists and passed clean, i.e. #1398's fix is not just closed but
  exercised successfully by a sibling repo.

## Finding 1 — MOSFETs and poly resistors need no device-name change

`sg13cmos5l_pr/sg13_hv_nmos.sym`, `sg13_hv_pmos.sym`, `rppd.sym`, `rhigh.sym`
exist in the installed SG13CMOS5L xschem symbol library **under the exact
same names** this design's netlists already use, and the corresponding
`.subckt sg13_hv_nmos d g s b`, `.subckt sg13_hv_pmos d g s b`,
`.subckt rppd 1 2 bn`, `.subckt rhigh 1 2 bn` definitions in
`sg13g2_moshv_mod.lib`/`resistors_mod.lib` are the same subcircuit
signatures this design's `Xnnn ... sg13_hv_nmos w=.. l=.. ng=.. m=..` /
`Xnnn ... rppd w=.. l=.. m=.. b=..` instance lines already call. (The model
library files themselves are literally named `sg13g2_moshv_*.lib` inside
the `ihp-sg13cmos5l` distribution — SG13CMOS5L ships SG13G2's own CMOS
device models directly, consistent with it being documented as SG13G2's
CMOS-only sibling process rather than an independent device library.)

**Consequence**: every MOSFET and every poly resistor in this design's six
netlists — the large majority of every block's device count (477/482 of the
device-level layout record in `layout/pll/reports/LATEST`) — needs **no
device-name or subcircuit-signature change** to port to SG13CMOS5L. This is
a materially smaller device-swap surface than `sg13g2-bandgap#63` faced (its
own Phase 1, #64, had to replace SG13G2's real `npn13G2` HBT with a
parasitic-PNP topology because SG13CMOS5L has no HBT at all — this design
has no HBT to begin with, so that risk does not apply here). What DR-002's
per-row "re-derive, not port" numeric discipline (`spec/porting-plan.md`
still governs every extracted number) still applies: SIZE/W/L values are
not assumed to hold just because the device *names* are unchanged — actual
extracted SPICE parameters (`sg13g2_moshv_mod.lib`'s specific model card)
must still be re-verified once schematics are actually re-simulated on
SG13CMOS5L, since a shared model file name is not proof of an identical
model card end to end.

## Finding 2 — MIM capacitors do not exist on SG13CMOS5L; this hits three of six blocks

Every capacitor this design's netlists declare is `cap_cmim` (a MIM
capacitor): `loop_filter`'s `XC1`/`XC2` (the filter's shunt caps, `pll.md`
row 6/6a's carried loop-dynamics mechanism), `vco`'s `XCDECAP` (the VCO
supply decap DR-001/DR-002 flag as load-bearing for the design's dominant
supply-noise/jitter risk), and `lock_detector`'s `XCW`/`XDW.XC1` (the
window-comparator hysteresis caps).

SG13CMOS5L has **no MIM capacitor at all** — `ReleaseNote.md`'s own
"Supported Devices" section states plainly "The MIM capacitors are not
available, they need the forbidden MIM layer," and no `cap_cmim`-named
symbol or model exists anywhere in the installed tree (confirmed by listing
`sg13cmos5l_pr/*.sym`: only `cap_cmomi.sym`/`cap_cmomf.sym` are present).
The available substitutes are `cap_cmomi` (interdigitated MOM,
`.subckt cap_cmomi PLUS MINUS w=.. l=.. mmin=.. mmax=.. feed=.. subblock=..
mm_ok=..`) and `cap_cmomf` (metal-fringe MOM, same parameter shape minus
`feed`) — both read directly from `cap_cmomi.lib`/`cap_cmomf.lib`.

**This is the single largest schematic-port risk in this design**, larger
than the bandgap's own equivalent finding, because it hits three of six
blocks rather than one:

- The parameter interface does not match `cap_cmim`'s `w=.. l=.. m=..`
  1:1 — `mmin`/`mmax`/`feed`/`subblock`/`mm_ok` have no `cap_cmim`
  equivalent and must be worked out per-instance when the schematics are
  actually redrawn, not assumed here.
- `docs/pdk/sg13cmos5l.md`'s own analog-caveats section (echoing the
  operator's Phase 2A ruling, `2AMLogic/2am#542`) states MOM caps on this
  PDK are **"not validated on CMOS5L silicon"** and carry **no corner or
  mismatch model** — the exact same caveat `sg13g2-bandgap#63` already had
  to carry for its own MoM-dependent rows. Per this repo's own CLAUDE.md
  ("no claim without a testbench") and the operator's ruling ("any
  MoM-cap-dependent spec row is `insufficient-evidence` until a sensitivity
  sweep bounds it"), the SG13CMOS5L port must mark every spec row whose
  numeric value is sensitive to these three caps' precision —
  loop-bandwidth/phase-margin (`pll.md`-equivalent row 6/6a, sized off
  `loop_filter`'s `C1`/`C2`), and VCO supply-noise/jitter margin (sized off
  `vco`'s `XCDECAP`) — as `insufficient-evidence` rather than a clean pass,
  until a sensitivity sweep across a plausible MOM-model-uncertainty band
  bounds the exposure. **This record does not perform that sweep** — it
  names the obligation for the sim-campaign follow-up issue.

## Finding 3 — the brief's 1.2 V/3.3 V rail split does not have to reopen DR-002's own domain-mixing rejection

DR-002 Decision 0 chose 3.3 V thick-oxide CMOS **throughout** the design —
including the entirely-digital PFD, divider, and lock detector — and
explicitly rejected a mixed-flavor split specifically to avoid a new
level-shifter in the PFD→charge-pump path, calling that path's
charge-domain sensitivity too well-documented a risk (gf180-pll's own
"logic-correct-looking PFD that measurably failed 9/45 corners in the
charge domain") to reopen without a demonstrated need.

Challenge #6's brief states "1.2 V digital / 3.3 V analog" rails. Read
literally as an internal-domain mandate, this would force exactly the
split DR-002 rejected. `docs/pdk/sg13cmos5l.md` itself frames this rail
pairing as **"a brief constraint, not a PDK-imposed rail"** — i.e. it
describes the *harness's* own supply convention, not a requirement that
every internal node of every accepted design must cross both rails.
Read that way, the natural interpretation is that the brief's 1.2 V rail
governs the wrapper's digital **I/O boundary** — the 24 digital control
inputs and 12 digital test outputs the slot budget in `docs/pdk/
sg13cmos5l.md`/`2am#542` specifies — while a design's own internal domains
remain its own choice, so long as the pins presented to the harness meet
the harness's 1.2 V logic levels.

**Recommendation, not yet ratified by this record**: keep DR-002's
all-3.3-V internal design (VCO, charge pump, loop filter, PFD, divider,
lock detector unchanged), and confine any level-shifting strictly to the
wrapper boundary — the N-select/band-select control inputs and the `lock`
digital test output — rather than reopening the PFD→charge-pump interface
DR-002 already argued should stay single-domain. This keeps the
charge-domain risk DR-002 named as the reason to avoid a mixed flavor from
recurring, and turns "port the rails" into a boundary-only interface
question instead of a redesign of the loop's own digital majority. This is
a **recommendation for the schematic-port follow-up issue to ratify (or
supersede) once it actually draws the wrapper**, not a ratified decision
here — this record's own scope is the device/tooling audit, and the
wrapper/harness interface is partly outside this block's own boundary the
same way DR-002 Decision 1 already scoped bias-current generation as "not
this block's problem."

## Finding 4 — the layout venv's pinned klayout-tools commit predates SG13CMOS5L deck support

This repo's `layout/requirements.txt` pins
`klayout-tools@5482cfe1c67eacf9d2f27d750a11a37ec14b1984` for the SG13G2
device-level layout flow (issues #13/#14). The installed system `klt`
(`0.3.0+g3f98b441bf2f`) lists only `sky130, gf180mcu, sg13g2` for
`klt drc --deck`. Independently confirmed via `gh issue view` against
`2AMLogic/klayout-tools`: **issue #1398** ("Add IHP SG13CMOS5L... as a
supported technology") is **closed**, and `2AMLogic/sg13g2-bandgap`'s own
committed `layout/sg13cmos5l-bandgap_core/drc_report.json` shows a real
`"deck": "sg13cmos5l"` clean DRC run — i.e. the deck genuinely exists
upstream and has been exercised successfully by a sibling repo, this is not
a stale doc note. **Consequence for the layout follow-up issue**: it must
bump (or add a second, SG13CMOS5L-specific) `klayout-tools` pin to a commit
at or after #1398's merge before `klt drc --deck sg13cmos5l` /
`klt extract` calls against SG13CMOS5L layouts will resolve, mirroring this
repo's own bump discipline already documented in `layout/requirements.txt`'s
header for the SG13G2 pin.

## What this does NOT decide

- **No schematic is redrawn by this record.** DR-001's architecture
  (loop type, VCO topology, divider family) is unchanged and is not
  reopened — nothing above depends on it.
- **No numeric spec row is re-derived here.** Every "re-derive" disposition
  in `spec/porting-plan.md`/DR-001/DR-002 stays open; this record only
  narrows *which* device-level substitutions the re-derivation will need to
  carry (Findings 1–2) and flags a tooling gate (Finding 4).
- **The rail-boundary recommendation (Finding 3) is not ratified.** It is
  handed to the schematic-port follow-up issue to ratify, amend, or
  supersede once the wrapper is actually drawn.
- **No `docs/chipalooza/challenge-6-proposal.md` is created by this
  record.** Per `sg13g2-bandgap#63`'s own precedent, that document is
  written once real `sim/`-derived numbers (or explicit "not started"
  placeholders backed by a genuine attempt) exist to populate its spec
  table — writing it now, before any SG13CMOS5L schematic or simulation
  exists, would not meet this repo's own CLAUDE.md evidence discipline.

## Alternatives considered

- **Attempt the full port (schematic + sim + layout + proposal) in this
  same session/PR.** Rejected: the one fleet precedent for a comparable,
  *smaller* port (`sg13g2-bandgap#63`, one composite cell vs. this design's
  six blocks with closed-loop dynamics) took nine issues across multiple
  sessions and its own post-layout PVT phase is still open. Attempting the
  same scope here in one pass would either produce an unverified/unevidenced
  claim (against CLAUDE.md's "no claim without a testbench") or silently
  relax the sign-off bar — both excluded by this repo's own discipline.
- **Do nothing and immediately decompose without auditing the PDK
  first.** Rejected per this repo's own builder audit-before-decompose
  discipline: decomposing "port the schematics" without first checking
  which devices actually need to change would hand the next issue a
  guess (mirroring the bandgap port's own device-flavor and MoM-cap
  findings as a template) instead of a verified starting point. This
  record's Findings 1–4 are exactly the audit that discipline calls for.
- **Assume the bandgap port's own findings (npn13G2 gap, MoM-cap caveat)
  transfer unchanged.** Rejected as insufficiently verified for this
  design specifically: Finding 1 (no device-name change needed for MOS/
  resistors) and the "no bipolar device in this design at all" fact are
  new findings this record makes independently, not carried from the
  bandgap port — and they materially change the schematic-port risk
  profile (smaller than the bandgap's own, not the same).

## Consequences

**What this makes possible**: the schematic-port follow-up issue starts
from a verified device-substitution list (MOS/resistors: no change;
capacitors: `cap_cmim` → `cap_cmomi`/`cap_cmomf`, parameter interface to be
worked out per instance) and a boundary-only rail-interpretation
recommendation, instead of a blank audit.

**What this defers, and to where**:

- Schematic redraw + wrapper/rail ratification + MoM-cap parameter mapping
  → schematic-port follow-up issue (Part of #16).
- PVT-cornered `sim/` campaign at 1.2 V/3.3 V, including the MoM-cap
  sensitivity sweep Finding 2 obligates → sim-campaign follow-up issue
  (Part of #16, depends on schematic-port).
- Layout + DRC/LVS-clean GDS on SG13CMOS5L, including the
  `layout/requirements.txt` klayout-tools pin bump Finding 4 identifies →
  layout follow-up issue (Part of #16, depends on schematic-port).
- `docs/chipalooza/challenge-6-proposal.md` → proposal follow-up issue
  (Part of #16, depends on sim-campaign and layout).

**What remains true regardless of this record**: issue #16's own
acceptance criteria are not met by this record alone, and are not claimed
to be — this record is scoped as the readiness audit + decomposition basis
per this repo's own complexity-assessment discipline, not a partial
sign-off.
