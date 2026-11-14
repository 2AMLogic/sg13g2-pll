# Work Plan

Current backlog state maintained by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#304**: docs(spec): DR-011 lock_detector 50 MHz range, trip band, active-low LOCK

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#301**: DR: extend f_ref to 50 MHz, state LOCK polarity and trip band for lock_detector (amends DR-005; part of #296)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#188**: vco: close spec row 13 duty-cycle shortfall at -40 C by sizing (R-8, T1 item 5)
- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close
- **#319**: Item 9 campaign (#214 part 1/3): supersede loop-bandwidth-pm RECORD-001/002/002b
- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap
- **#376**: Split render-pll-cmos5l-record.py's 525-line main() into testable section renderers

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#335**: sim: attribute fast/slow anchor offset to PDK cornerRES drift (RECORD-007)

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#304**: docs(spec): DR-011 lock_detector 50 MHz range, trip band, active-low LOCK
- **#377**: refactor: split the SG13CMOS5L record renderer into per-section helpers

## Proposed

Issues carrying `loom:curated`.

- **#16**: [Epic #542] 5A — Port to SG13CMOS5L for Chipalooza Challenge #6 brief *(curated)*
- **#157**: pex: re-extract lock_detector from the post-#136 GDS and run klt pex (withheld from T1 item 7 in #152) *(curated)*
- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9) *(curated)*
- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close *(curated)*
- **#212**: Item 9 campaign: charge-pump and divider-retiming provenance *(curated)*
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance *(curated)*
- **#231**: Item 9 campaign (#212 part 2/4): supersede cp-icp-trim RECORD-003/004 (fine-trim grids) *(curated)*
- **#301**: DR: extend f_ref to 50 MHz, state LOCK polarity and trip band for lock_detector (amends DR-005; part of #296) *(curated)*
- **#309**: design/sg13cmos5l: committed netlists stale vs installed PDK (mm_ok=1 missing); netlist.sh --check fails on main *(curated)*
- **#316**: Item 9: supersede sg13cmos5l-vco-decap-momcap provenance (child of #216) *(curated)*
- **#319**: Item 9 campaign (#214 part 1/3): supersede loop-bandwidth-pm RECORD-001/002/002b *(curated)*
- **#320**: Item 9 campaign (#214 part 2/3): supersede loop-bandwidth-pm RECORD-003/004 (close-gap grids) *(curated)*
- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap *(curated)*

## Proposed (Architect / Hermit)

_None._

## Epics

- **#6**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers)
- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9)
- **#199**: Item 9: campaign to recover or replace unpinned measurement evidence
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance
- **#250**: Re-stamp SG13CMOS5L PDK pin from klayout-tools (IHP-Open-PDK dev f7bca326)

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Very important | 0 |
| Important | 1 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 5 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 2 |
| Curated | 13 |
| Architect / Hermit proposals | 0 |
| Active epics | 5 |
<!-- guide:plan-body:end -->
