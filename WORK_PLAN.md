# Work Plan

Current backlog state maintained by the Loom Guide role.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#304**: docs(spec): DR-015 lock_detector 50 MHz range, trip band, active-low LOCK

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

_None._

## Important

`loom:important`; taken before unlabelled work.

- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9)
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance
- **#250**: Re-stamp SG13CMOS5L PDK pin from klayout-tools (IHP-Open-PDK dev f7bca326) *(held)*
- **#301**: DR: extend f_ref to 50 MHz, state LOCK polarity and trip band for lock_detector (amends DR-005; part of #296)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#188**: vco: close spec row 13 duty-cycle shortfall at -40 C by sizing (R-8, T1 item 5)
- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close
- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap
- **#503**: Single-source the item-10 gate list: signoff.yml and the item-10 inventory share one list

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#335**: sim: attribute fast/slow anchor offset to PDK cornerRES drift (RECORD-007)

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#304**: docs(spec): DR-015 lock_detector 50 MHz range, trip band, active-low LOCK — closes #301

## Proposed

Issues carrying `loom:curated`.

- **#16**: [Epic #542] 5A — Port to SG13CMOS5L for Chipalooza Challenge #6 brief *(curated)* *(held)*
- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9) *(curated)*
- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close *(curated)*
- **#212**: Item 9 campaign: charge-pump and divider-retiming provenance *(curated)* *(held)*
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance *(curated)*
- **#231**: Item 9 campaign (#212 part 2/4): supersede cp-icp-trim RECORD-003/004 (fine-trim grids) *(curated)* *(held)*
- **#301**: DR: extend f_ref to 50 MHz, state LOCK polarity and trip band for lock_detector (amends DR-005; part of #296) *(curated)*
- **#309**: design/sg13cmos5l: committed netlists stale vs installed PDK (mm_ok=1 missing); netlist.sh --check fails on main *(curated)* *(held)*
- **#316**: Item 9: supersede sg13cmos5l-vco-decap-momcap provenance (child of #216) *(curated)* *(held)*
- **#320**: Item 9 campaign (#214 part 2/3): supersede loop-bandwidth-pm RECORD-003/004 (close-gap grids) *(curated)* *(held)*
- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap *(curated)*
- **#391**: test_cpdiag_metrics.py is a stdlib test no workflow runs *(curated)* *(held)*
- **#503**: Single-source the item-10 gate list: signoff.yml and the item-10 inventory share one list *(curated)*

## Proposed (Architect / Hermit)

- **#384**: Collapse run_rerun256.sh (921-line copy of the lock-detector run.sh, one functional line differs) into a thin wrapper *(hermit)* *(held)*
- **#396**: Collapse run_rerun256.sh into a run.sh output-suffix knob: 906 duplicated lines, one line of real difference *(hermit)* *(held)*
- **#398**: Remove committed klt scratch cache under sim/ and gitignore .klt/ *(hermit)* *(held)*
- **#410**: Deduplicate the manifests/ gate envelope checks: four spellings of hash-bound-to-adjacent-GDS, plus one unexercised fallback *(hermit)* *(held)*
- **#416**: Artifact-store writer from #278 is inert: zero manifests in 3 weeks while 75.7 MB of raw evidence went to git *(hermit)* *(held)*

## Epics

- **#6**: Track the gap to T1 sim-validated / bronze (klayout-tools design-evidence tiers) *(held)*
- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9)
- **#199**: Item 9: campaign to recover or replace unpinned measurement evidence
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance
- **#250**: Re-stamp SG13CMOS5L PDK pin from klayout-tools (IHP-Open-PDK dev f7bca326) *(held)*

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Very important | 0 |
| Important | 4 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 4 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 1 |
| Curated | 13 |
| Architect / Hermit proposals | 5 |
| Active epics | 5 |
<!-- guide:plan-body:end -->
