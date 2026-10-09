# spec

- [`porting-plan.md`](porting-plan.md) — what carries over from
  `2AMLogic/gf180-pll` and `2AMLogic/sky130-pll`, what SG13G2's BiCMOS
  devices change, and what the starter-grade SG13G2 klayout-tools deck can't
  check yet. The first document in this directory (issue #1).
- [`decision-records/`](decision-records/) — the ratified decision history
  the porting plan's own closing Summary names as prerequisites for design
  work:
  - [`DR-001-pll-architecture.md`](decision-records/DR-001-pll-architecture.md)
    — loop type, VCO topology (current-starved CMOS ring vs. an HBT-based
    LC-tank oscillator), and feedback divider architecture (gf180-pll's
    cascaded ÷2/3 chain vs. sky130-pll's synchronous down-counter).
  - [`DR-002-supply-device-flavor.md`](decision-records/DR-002-supply-device-flavor.md)
    — the CMOS supply/device-flavor choice (1.2 V thin-oxide vs. 3.3 V
    thick-oxide vs. a per-element mix) porting-plan.md §2.4 names as the
    prerequisite both sibling repos settled first, plus the remaining
    per-element bipolar questions (bias reference, charge-pump cascode,
    divider first stage).
  - [`DR-003-sg13cmos5l-port-readiness.md`](decision-records/DR-003-sg13cmos5l-port-readiness.md)
    — readiness audit for the SG13CMOS5L port (issue #16, Chipalooza
    Challenge #6): this design's own device inventory against the installed
    SG13CMOS5L PDK (MOSFETs/resistors port unchanged; MIM caps do not exist
    and must become MoM caps in three of six blocks), a rail-interpretation
    recommendation for the brief's 1.2 V/3.3 V split, and the
    `klayout-tools` deck-support gate the layout phase will need. Proposed,
    not ratified — no SG13CMOS5L schematic exists yet.
  - [`DR-004-sg13cmos5l-rail-boundary-ratification.md`](decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md)
    — ratifies DR-003 Finding 3 (issue #22, the SG13CMOS5L schematic port):
    the design's internal domains stay all-3.3 V per DR-002, Challenge #6's
    1.2 V digital rail governs only a future wrapper's own I/O boundary, not
    any node inside the six ported blocks — checked directly against the
    now-drawn `design/sg13cmos5l/*.sch` boundary pins rather than a literal
    (not-yet-scoped) pad-ring wrapper cell.

- [`target-spec.md`](target-spec.md) — the **DRAFT** target spec (issue
  #148): one row per `porting-plan.md` §1.2 row, each marked measured /
  proposed / not specified / open with its gate, classified deterministic or
  statistical and by partition (analog loop path or `divider_chain`), with a
  "Needs a ruling" section for the ratifiers. Not ratified: ratification is
  the separate two-key act (`ratification/ee-key`, `ratification/market-key`).
  Playing the role `2AMLogic/gf180-pll`'s `pll.md` and
  `2AMLogic/sky130-pll`'s `target-spec.md` play in the siblings.

See the repo README for scope.
