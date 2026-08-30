# DR-004: SG13CMOS5L rail-boundary ratification — DR-003 Finding 3 stands

- **Status**: ratified
- **Date**: 2026-08-30
- **Decided by**: Builder agent, issue #22
- **Related**: #22 ([Part of #16] Port PLL schematics to SG13CMOS5L), #16
  ([Epic 2AMLogic/2am#542] Phase 5A — port to SG13CMOS5L for Chipalooza
  Challenge #6), DR-002 (supply/device flavor — the all-3.3V internal
  decision this record keeps intact), DR-003 (SG13CMOS5L port readiness —
  Finding 3 is the recommendation this record ratifies)
- **Consumes**: `design/sg13cmos5l/*.sch` (the ported block schematics this
  record reads the boundary pins of directly — issue #22's own schematic
  port, committed alongside this record)

## Context

DR-003 Finding 3 read Chipalooza Challenge #6's brief ("1.2V digital / 3.3V
analog" rails) as the wrapper's I/O-boundary convention rather than an
internal-domain mandate, and recommended keeping DR-002's all-3.3V internal
design intact — confining any level-shifting to the wrapper boundary (the
digital control inputs and digital test outputs a harness would drive/read)
rather than reopening the PFD→charge-pump interface DR-002 explicitly
rejected splitting. DR-003 explicitly left that recommendation unratified,
handing it to "the schematic-port follow-up issue to ratify (or supersede)
once it actually draws the wrapper."

Issue #22 is that schematic-port follow-up issue. Its own scope (six named
blocks — `pfd`, `cp`, `loop_filter`, `vco`, `divider_chain`,
`lock_detector` — plus their leaf cells) does not include drawing a
chip-level `pll_top`/pad-ring wrapper — no such cell exists yet even on
SG13G2, and composing one is a separate, larger scope (real 24-input/
12-output pad assignment, ESD, pad-ring DRC) that belongs to a future
wrapper/harness-integration issue, not a schematic-port pass. What issue #22
*does* newly provide is the actual SG13CMOS5L-side boundary pins DR-003
Finding 3 named by function — `vco`'s `B0`/`B1` band-select inputs,
`divider_chain`'s `P0`–`P5` N-select inputs, and `lock_detector`'s `LOCK`
digital output — now drawn and net-listing cleanly, plus every other block
boundary pin in the design (see `design/sg13cmos5l/*.sch`, ported
byte-for-byte in topology from the SG13G2 originals per DR-003 Finding 1).
This record treats that pin-level evidence as sufficient to close DR-003's
open recommendation, rather than waiting on a full wrapper cell that is out
of every currently-filed issue's scope.

## Decision

**Ratify DR-003 Finding 3 as written, with no supersession**: the design's
internal domains stay all-3.3V thick-oxide CMOS end to end (DR-002 Decision
0, unchanged by the SG13CMOS5L port — DR-003 Finding 1 confirms the same
`sg13_hv_nmos`/`sg13_hv_pmos` devices are available and un-renamed on
SG13CMOS5L). Challenge #6's "1.2V digital" rail is read as governing only a
future wrapper's own chip-level I/O ring, not any node inside `pfd`, `cp`,
`loop_filter`, `vco`, `divider_chain`, or `lock_detector`.

Evidence this record checked directly against the actual ported schematics
(`design/sg13cmos5l/*.sch`, issue #22), not assumed from DR-003's own
audit-time reasoning:

- Every block-boundary pin across all six top-level SG13CMOS5L schematics
  (`pfd`: `REF`/`FB`/`UP`/`DN`/`VDD`/`VSS`; `cp`: `UP`/`DN`/`IBP`/`ICP`/
  `IBN`/`ICN`/`VOUT`/`VDD`/`VSS`; `loop_filter`: `VCTRL`/`VSS`; `vco`:
  `VCTRL`/`B0`/`B1`/`CLK`/`VDD_VCO`/`GND_VCO`; `divider_chain`: `CKIN`/
  `CKIN_VCO`/`P0`–`P5`/`FB`/`DIVOUT`/`VDD_DIV`/`VSS`; `lock_detector`:
  `UP`/`DN`/`LOCK`/`VDD`/`VSS`) is a single-domain 3.3V CMOS logic or analog
  signal — no pin, in any block, crosses into a second declared voltage
  domain, and no level-shifter cell exists anywhere in the design's 18
  leaf-cell library.
- The specific pins DR-003 Finding 3 named as the wrapper's likely
  level-shift boundary — `vco.B0`/`vco.B1` (band-select), `divider_chain.
  P0`–`P5` (N-select), `lock_detector.LOCK` (digital test output) — are
  exactly the pins a future wrapper would need to drive or read from a
  1.2V-domain pad ring. They are ordinary 3.3V CMOS inputs/outputs at this
  design's own boundary today, consistent with DR-003's reading that any
  1.2V-side level-shifting is the wrapper's own responsibility, not this
  design's.
- The PFD→charge-pump interface (`pfd.UP`/`pfd.DN` → `cp.UP`/`cp.DN`) DR-002
  already rejected splitting stays single-domain in the SG13CMOS5L port,
  confirming this record does not reopen that decision.

## Alternatives considered

- **Wait for a literal `pll_top`/pad-ring wrapper cell before ratifying.**
  Rejected: no issue currently in flight scopes drawing that cell (issue
  #22's own scope is six blocks + leaf cells; a wrapper is a materially
  larger, separately-scoped deliverable — real pad assignment, ESD, ring
  DRC). Deferring ratification indefinitely on a precondition no filed issue
  satisfies would leave DR-003 Finding 3 permanently "proposed," blocking
  every future block-level design decision on an unscheduled dependency for
  no evidentiary gain — the boundary-pin evidence this record actually
  checked (above) already answers the question DR-003 Finding 3 asked.
- **Supersede DR-003 Finding 3 with a mixed-flavor (1.2V digital / 3.3V
  analog) internal split**, reading Challenge #6's brief literally as an
  internal-domain mandate. Rejected for the same reason DR-002 rejected it
  originally: it would force a new level-shifter into the PFD→charge-pump
  path, the exact charge-domain risk DR-002's Decision 0 named as too
  well-documented (gf180-pll's own 9/45-corner PFD failure) to reopen
  without a demonstrated need — and nothing in issue #22's own schematic
  port demonstrates one; every block ported cleanly as a single-domain
  design.
- **Split only the identified wrapper-facing pins (`B0`/`B1`, `P0`–`P5`,
  `LOCK`) into a mixed-flavor domain now, inside the block schematics
  themselves.** Rejected: DR-003 Finding 3's own framing treats
  level-shifting as the *wrapper's* job, structurally analogous to DR-002
  Decision 1's "bias-current generation is not this block's problem"
  scoping — adding partial level-shift logic inside `vco`/`divider_chain`/
  `lock_detector` now would blur that boundary and could not be verified
  against a real pad-ring spec that does not exist yet.

## Consequences

**What this makes possible**: the SG13CMOS5L port's block-level schematics
(issue #22) are the design's final say on internal rail domains — no future
schematic-level issue needs to revisit DR-002's all-3.3V decision to satisfy
Challenge #6's rail brief. A future wrapper/harness-integration issue can
proceed directly to composing the pad ring, level-shifters, and ESD
structures around these six blocks' existing 3.3V boundary pins, rather than
first re-deciding an internal-domain split.

**What this defers, and to where**:

- The actual wrapper/`pll_top`/pad-ring composition (24 digital control
  inputs, 12 digital test outputs, real pad cells, level-shifters at the
  1.2V/3.3V crossing, ESD) → a future wrapper/harness-integration follow-up
  issue (Part of #16), not yet filed as of this record.
- Any spec-row numeric consequence of the rail choice (e.g. a level-shifter's
  own propagation delay affecting N-select settling time) → that same future
  wrapper issue, since no level-shifter exists in this design yet to have a
  numeric delay.

**What remains true regardless of this record**: this is a schematic-level
ratification only — it does not claim a wrapper exists, has been simulated,
or has been laid out; those remain open per DR-003's own "What this does NOT
decide" and are not reopened or advanced by this record beyond closing out
Finding 3's own open question.
