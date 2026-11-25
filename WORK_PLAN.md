# Work Plan

Current backlog state maintained by the Loom Guide role.

<!-- guide:plan-body:start -->
_Generated: 2026-11-25T10:55:12Z (snapshot; compare against live labels)_
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#558**: chore: remove inert artifact-store writer and record evidence-storage decision

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#301**: DR: extend f_ref to 50 MHz, state LOCK polarity and trip band for lock_detector (amends DR-005; part of #296)

## Important

`loom:important`; taken before unlabelled work.

- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9)
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance
- **#250**: Re-stamp SG13CMOS5L PDK pin from klayout-tools (IHP-Open-PDK dev f7bca326) *(held)*
- **#514**: divider_chain: structural redesign of the high-speed front end (XD0 first) so the chain divides exactly at 1562 MHz across the 9-corner star (row 3, R-3, DR-012 follow-up) *(held)*
- **#515**: divider_chain divides by 126 instead of 127 at mos_tt/125 C from 640 MHz (bottom of band): isolate the stage and fix the modulus path (row 3) *(held)*
- **#524**: batch-fleet launches refused from loom-worker-4: IAM UnauthorizedOperation on ec2:RunInstances (blocks #514 divider campaign) *(held)*

## Ready

Human-approved issues (`loom:issue`) ready for implementation — excluding held (`loom:blocked`/`loom:operator`/`loom:frozen`), `loom:building`, and issues closed by an open `loom:pr` PR (listed under Approved).

- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap

## In Progress

Issues currently being built (`loom:building`).

- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close
- **#416**: Artifact-store writer from #278 is inert: zero manifests in 3 weeks while 75.7 MB of raw evidence went to git

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#335**: sim: attribute fast/slow anchor offset to PDK cornerRES drift (RECORD-007) *(held)*

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#304**: docs(spec): DR-015 lock_detector 50 MHz range, trip band, active-low LOCK — closes #301
- **#558**: chore: remove inert artifact-store writer and record evidence-storage decision — closes #416

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
- **#416**: Artifact-store writer from #278 is inert: zero manifests in 3 weeks while 75.7 MB of raw evidence went to git *(curated)*
- **#514**: divider_chain: structural redesign of the high-speed front end (XD0 first) so the chain divides exactly at 1562 MHz across the 9-corner star (row 3, R-3, DR-012 follow-up) *(curated)* *(held)*
- **#515**: divider_chain divides by 126 instead of 127 at mos_tt/125 C from 640 MHz (bottom of band): isolate the stage and fix the modulus path (row 3) *(curated)* *(held)*
- **#518**: sim: transient-noise period-jitter method bench for the free-running vco (row 8 method gap, R-7; depends on klayout-tools#5772) *(curated)* *(held)*
- **#550**: Committed envelope content_hash for spec/target-spec.md serializes every open spec PR against main *(curated)* *(held)*

## Proposed (Architect / Hermit)

_None._

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
| Very important | 1 |
| Important | 6 |
| Ready (`loom:issue`, net of holds/building/merge-pending) | 1 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 2 |
| Curated | 17 |
| Architect / Hermit proposals | 0 |
| Active epics | 5 |
<!-- guide:plan-body:end -->
