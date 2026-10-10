# Work Plan

Current backlog state maintained by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs stuck under a `loom:operator` merge-risk hold — implementation work is done, only a human merge decision is missing.

_None._

## Operator Priority

Issues the operator starred (`loom:operator-priority`); land these first.

_None._

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#198**: Item 9: validate append-only provenance addenda and superseding reruns

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#16**: [Epic #542] 5A — Port to SG13CMOS5L for Chipalooza Challenge #6 brief *(curated)*
- **#157**: pex: re-extract lock_detector from the post-#136 GDS and run klt pex (withheld from T1 item 7 in #152) *(curated)*
- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9) *(curated)*
- **#198**: Item 9: validate append-only provenance addenda and superseding reruns *(curated)*

## Proposed (Architect / Hermit)

- **#187**: sim: supply-range 3.0/3.3/3.6 V sweep beyond cp for spec row 18 (T1 item 5) *(architect)*
- **#188**: vco: close spec row 13 duty-cycle shortfall at -40 C by sizing (R-8, T1 item 5) *(architect)*
- **#189**: divider_chain: size to close row 3 retiming at 1562 MHz (R-3, T1 item 5) *(architect)*
- **#190**: sim: SG13CMOS5L vco output-levels bench for spec row 14 (T1 item 5) *(architect)*

## Epics

- **#6**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)
- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9)

## Backlog Balance

| Tier | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Operator priority | 0 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 1 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 4 |
| Architect / Hermit proposals | 4 |
| Active epics | 2 |
<!-- guide:plan-body:end -->
