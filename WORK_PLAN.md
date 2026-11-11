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

- **#328**: sim: rerun lock-detector-window RECORD-002-resized-window-hysteresis-chatter on batch fleet (provenance migration)

## In Progress

Issues currently being built (`loom:building`).

- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close
- **#230**: Item 9 campaign (#212 part 1/4): supersede cp-icp-trim RECORD-001/002 (historical Icp-trim grids)
- **#231**: Item 9 campaign (#212 part 2/4): supersede cp-icp-trim RECORD-003/004 (fine-trim grids)
- **#232**: Item 9 campaign (#212 part 3/4): supersede divider-nrange-retiming RECORD-001/002 (pre-repair divider)
- **#233**: Item 9 campaign (#212 part 4/4): supersede divider-nrange-retiming RECORD-003 (repaired divider re-verification)
- **#235**: Item 9: supersede SG13G2 divider repair RECORD-001
- **#236**: Item 9: supersede SG13G2 lock detector RECORD-001
- **#237**: Item 9: supersede SG13G2 VCO Kvco RECORD-001
- **#317**: Item 9: supersede sg13cmos5l-vco-duty-cycle provenance (child of #216)
- **#323**: Item 9 campaign (#215 part 1/4): supersede postlayout-pex-pvt RECORD-001 (VCO + CP)
- **#324**: Item 9 campaign (#215 part 2/4): supersede postlayout-pex-pvt RECORD-002 (floorplan-aware VCO route)
- **#325**: Item 9 campaign (#215 part 3/4): supersede postlayout-pex-pvt RECORD-003 (PFD + lock detector)
- **#326**: Item 9 campaign (#215 part 4/4): supersede postlayout-pex-pvt RECORD-004 (loop filter + divider chain)
- **#329**: sim: rerun lock-detector-window RECORD-003-hysteresis-fix on batch fleet (provenance migration)
- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap
- **#331**: sim: rerun lock-detector-window RECORD-004-crowbar-current-mitigation on batch fleet (provenance migration)

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#333**: sim: rerun sg13g2 VCO Kvco table on batch fleet, supersede RECORD-001
- **#335**: sim: attribute fast/slow anchor offset to PDK cornerRES drift (RECORD-007)
- **#338**: sim: re-measure SG13G2 divider repair opconv/hold/func on batch fleet; superseded addendum

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#304**: docs(spec): DR-011 lock_detector 50 MHz range, trip band, active-low LOCK
- **#337**: sim: rerun RECORD-003 schmitt_rewire grid on batch fleet with pinned provenance

## Proposed

Issues carrying `loom:curated`.

- **#16**: [Epic #542] 5A — Port to SG13CMOS5L for Chipalooza Challenge #6 brief *(curated)*
- **#157**: pex: re-extract lock_detector from the post-#136 GDS and run klt pex (withheld from T1 item 7 in #152) *(curated)*
- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9) *(curated)*
- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close *(curated)*
- **#212**: Item 9 campaign: charge-pump and divider-retiming provenance *(curated)*
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance *(curated)*
- **#230**: Item 9 campaign (#212 part 1/4): supersede cp-icp-trim RECORD-001/002 (historical Icp-trim grids) *(curated)*
- **#231**: Item 9 campaign (#212 part 2/4): supersede cp-icp-trim RECORD-003/004 (fine-trim grids) *(curated)*
- **#232**: Item 9 campaign (#212 part 3/4): supersede divider-nrange-retiming RECORD-001/002 (pre-repair divider) *(curated)*
- **#233**: Item 9 campaign (#212 part 4/4): supersede divider-nrange-retiming RECORD-003 (repaired divider re-verification) *(curated)*
- **#235**: Item 9: supersede SG13G2 divider repair RECORD-001 *(curated)*
- **#236**: Item 9: supersede SG13G2 lock detector RECORD-001 *(curated)*
- **#237**: Item 9: supersede SG13G2 VCO Kvco RECORD-001 *(curated)*
- **#257**: Item 9 (#213 child): supersede lock-detector-window RECORD-001..004 (historical grids; needs batch route) *(curated)*
- **#301**: DR: extend f_ref to 50 MHz, state LOCK polarity and trip band for lock_detector (amends DR-005; part of #296) *(curated)*
- **#309**: design/sg13cmos5l: committed netlists stale vs installed PDK (mm_ok=1 missing); netlist.sh --check fails on main *(curated)*
- **#316**: Item 9: supersede sg13cmos5l-vco-decap-momcap provenance (child of #216) *(curated)*
- **#317**: Item 9: supersede sg13cmos5l-vco-duty-cycle provenance (child of #216) *(curated)*
- **#318**: Item 9: supersede sg13cmos5l-vco-kvco-table provenance (child of #216) *(curated)*
- **#319**: Item 9 campaign (#214 part 1/3): supersede loop-bandwidth-pm RECORD-001/002/002b *(curated)*
- **#320**: Item 9 campaign (#214 part 2/3): supersede loop-bandwidth-pm RECORD-003/004 (close-gap grids) *(curated)*
- **#321**: Item 9 campaign (#214 part 3/3): supersede loop-filter-momcap RECORD-001/002 *(curated)*
- **#323**: Item 9 campaign (#215 part 1/4): supersede postlayout-pex-pvt RECORD-001 (VCO + CP) *(curated)*
- **#324**: Item 9 campaign (#215 part 2/4): supersede postlayout-pex-pvt RECORD-002 (floorplan-aware VCO route) *(curated)*
- **#325**: Item 9 campaign (#215 part 3/4): supersede postlayout-pex-pvt RECORD-003 (PFD + lock detector) *(curated)*
- **#326**: Item 9 campaign (#215 part 4/4): supersede postlayout-pex-pvt RECORD-004 (loop filter + divider chain) *(curated)*
- **#328**: sim: rerun lock-detector-window RECORD-002-resized-window-hysteresis-chatter on batch fleet (provenance migration) *(curated)*
- **#329**: sim: rerun lock-detector-window RECORD-003-hysteresis-fix on batch fleet (provenance migration) *(curated)*
- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap *(curated)*
- **#331**: sim: rerun lock-detector-window RECORD-004-crowbar-current-mitigation on batch fleet (provenance migration) *(curated)*

## Proposed (Architect / Hermit)

- **#187**: sim: supply-range 3.0/3.3/3.6 V sweep beyond cp for spec row 18 (T1 item 5) *(architect)*
- **#188**: vco: close spec row 13 duty-cycle shortfall at -40 C by sizing (R-8, T1 item 5) *(architect)*
- **#189**: divider_chain: size to close row 3 retiming at 1562 MHz (R-3, T1 item 5) *(architect)*
- **#190**: sim: SG13CMOS5L vco output-levels bench for spec row 14 (T1 item 5) *(architect)*

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
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 16 |
| PRs awaiting review | 3 |
| Approved PRs awaiting merge | 2 |
| Curated | 30 |
| Architect / Hermit proposals | 4 |
| Active epics | 5 |
<!-- guide:plan-body:end -->
