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

- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9)
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance
- **#250**: Re-stamp SG13CMOS5L PDK pin from klayout-tools (IHP-Open-PDK dev f7bca326)
- **#301**: DR: extend f_ref to 50 MHz, state LOCK polarity and trip band for lock_detector (amends DR-005; part of #296)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#436**: check_signoff_inventory_parity.py: a comment line joined by a \\-continuation can produce a false FAIL

## In Progress

Issues currently being built (`loom:building`).

- **#188**: vco: close spec row 13 duty-cycle shortfall at -40 C by sizing (R-8, T1 item 5)
- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close
- **#319**: Item 9 campaign (#214 part 1/3): supersede loop-bandwidth-pm RECORD-001/002/002b
- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap
- **#393**: Nothing guards package.json's stdlib gate chain against drift from .github/workflows/
- **#403**: sim: reference-input switching-threshold bench for pfd (target-spec R-5)
- **#407**: spec: target-spec.md Accounting says "17 rows" but its own status table lists 18
- **#415**: Dedupe the two layout-flow drivers onto a shared lib (28 of 33 lines identical), and fix the cross-flow -dirty stamp they both carry
- **#419**: check-osdi-arch.sh: usage() prints the USAGE block to stdout, blocking an rc-only self-test guard for retired flags
- **#429**: Correct stale klayout-tools#2727 'open/blocking' status in provenance-migration.md and characterization/SUMMARY.md
- **#432**: Correct stale klayout-tools#3012 / #2726 'open' status in sg13cmos5l README, manifests/README.md and challenge-6 proposal
- **#438**: run-pex.sh: PEX_BLOCKS without PEX_SNAP_SUBDIR truncates the committed snapshot roll-up
- **#439**: sim: RECORD-015's offline reproduce path for the 125 C VCO CSV needs a layout the committed raw files do not have

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#335**: sim: attribute fast/slow anchor offset to PDK cornerRES drift (RECORD-007)
- **#441**: build: derive package.json's stdlib gate chains from item-10.json
- **#451**: sim: send check-osdi-arch.sh usage() to stderr and add retired-flag self-test guard
- **#455**: docs: correct closed klayout-tools#3012/#2726 gap status to the 0.8.0 pin

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#304**: docs(spec): DR-011 lock_detector 50 MHz range, trip band, active-low LOCK
- **#430**: refactor: dedupe the two layout-flow drivers onto layout/bin/layout-flow.sh, fix the cross-flow -dirty record-id stamp
- **#445**: docs: mark closed klt#2727/#221/#139 blockers resolved in provenance-migration
- **#446**: bench: pfd REF-input switching thresholds across the row-2 operating box
- **#448**: spec: reconcile Accounting total to 18 rows and gate it
- **#450**: fix: hard-fail PEX_BLOCKS without PEX_SNAP_SUBDIR in run-pex.sh
- **#452**: sim: resolve flat <id>.out stdout layout in the 125C acquisition collector

## Proposed

Issues carrying `loom:curated`.

- **#16**: [Epic #542] 5A — Port to SG13CMOS5L for Chipalooza Challenge #6 brief *(curated)*
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
- **#391**: test_cpdiag_metrics.py is a stdlib test no workflow runs *(curated)*
- **#393**: Nothing guards package.json's stdlib gate chain against drift from .github/workflows/ *(curated)*
- **#403**: sim: reference-input switching-threshold bench for pfd (target-spec R-5) *(curated)*
- **#407**: spec: target-spec.md Accounting says "17 rows" but its own status table lists 18 *(curated)*
- **#419**: check-osdi-arch.sh: usage() prints the USAGE block to stdout, blocking an rc-only self-test guard for retired flags *(curated)*
- **#429**: Correct stale klayout-tools#2727 'open/blocking' status in provenance-migration.md and characterization/SUMMARY.md *(curated)*
- **#436**: check_signoff_inventory_parity.py: a comment line joined by a \\-continuation can produce a false FAIL *(curated)*
- **#438**: run-pex.sh: PEX_BLOCKS without PEX_SNAP_SUBDIR truncates the committed snapshot roll-up *(curated)*
- **#439**: sim: RECORD-015's offline reproduce path for the 125 C VCO CSV needs a layout the committed raw files do not have *(curated)*
- **#444**: spec: rows 6/6a and 16 still derive their figures from row 2's union range — name them in R-13 *(curated)*

## Proposed (Architect / Hermit)

- **#384**: Collapse run_rerun256.sh (921-line copy of the lock-detector run.sh, one functional line differs) into a thin wrapper *(hermit)*
- **#396**: Collapse run_rerun256.sh into a run.sh output-suffix knob: 906 duplicated lines, one line of real difference *(hermit)*
- **#398**: Remove committed klt scratch cache under sim/ and gitignore .klt/ *(hermit)*
- **#410**: Deduplicate the manifests/ gate envelope checks: four spellings of hash-bound-to-adjacent-GDS, plus one unexercised fallback *(hermit)*
- **#416**: Artifact-store writer from #278 is inert: zero manifests in 3 weeks while 75.7 MB of raw evidence went to git *(hermit)*

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
| Important | 4 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 13 |
| PRs awaiting review | 4 |
| Approved PRs awaiting merge | 7 |
| Curated | 22 |
| Architect / Hermit proposals | 5 |
| Active epics | 5 |
<!-- guide:plan-body:end -->
