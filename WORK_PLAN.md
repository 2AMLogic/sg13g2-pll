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

- **#157**: pex: re-extract lock_detector from the post-#136 GDS and run klt pex (withheld from T1 item 7 in #152)
- **#182**: sim records: backfill PDK revision for pre-gate records and pin ihp-sg13g2 (T1 item 9)
- **#217**: Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance
- **#250**: Re-stamp SG13CMOS5L PDK pin from klayout-tools (IHP-Open-PDK dev f7bca326)
- **#301**: DR: extend f_ref to 50 MHz, state LOCK polarity and trip band for lock_detector (amends DR-005; part of #296)
- **#389**: sim: the closed-loop proposal deck does not acquire lock at 125 C, and the cp mismatch campaign still has no negative control (follow-ups from #385)
- **#395**: item-10 hygiene inventory's `checks` list has drifted from signoff.yml's actual gate set (5 gates missing)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#389**: sim: the closed-loop proposal deck does not acquire lock at 125 C, and the cp mismatch campaign still has no negative control (follow-ups from #385)
- **#402**: sim: divider_chain maximum input frequency per corner (the untracked "Divider speed evidence" gap)
- **#403**: sim: reference-input switching-threshold bench for pfd (target-spec R-5)
- **#404**: docs: bring manifests/README.md item 6 and item 8 text and the summary gap table in line with DR-013 and closed trackers
- **#415**: Dedupe the two layout-flow drivers onto a shared lib (28 of 33 lines identical), and fix the cross-flow -dirty stamp they both carry

## In Progress

Issues currently being built (`loom:building`).

- **#188**: vco: close spec row 13 duty-cycle shortfall at -40 C by sizing (R-8, T1 item 5)
- **#203**: loop-bandwidth-pm: DR-008 fast tuple projected below 45 deg PM once the real cp VOUT capacitance is in the loop; run the fast/slow grid and re-close
- **#319**: Item 9 campaign (#214 part 1/3): supersede loop-bandwidth-pm RECORD-001/002/002b
- **#330**: sim: reconcile fast/slow PM anchor with RECORD-004 before closing the DR-008 fast gap
- **#381**: render-pll-cmos5l-record.py asserts the second routing plane "cannot be selected" regardless of the two-layer probe result
- **#395**: item-10 hygiene inventory's `checks` list has drifted from signoff.yml's actual gate set (5 gates missing)
- **#401**: sim: real-divider closed loop at a VCO frequency inside the divider's measured exact-N range
- **#405**: Deduplicate manifests/ gate helpers: one record resolver, one sha256_file, one JSON loader
- **#406**: Remove check-osdi-arch.sh --warn-only: a never-called flag that downgrades a known-unloadable deck to exit 0

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#335**: sim: attribute fast/slow anchor offset to PDK cornerRES drift (RECORD-007)

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#304**: docs(spec): DR-011 lock_detector 50 MHz range, trip band, active-low LOCK
- **#399**: ci: guard item-10's checks inventory against signoff.yml gate drift
- **#408**: refactor(manifests): share the record resolver, sha256_file and JSON loader across the four signoff gates
- **#413**: fix: derive the record's second-routing-plane sentence from its own probe
- **#418**: refactor: drop check-osdi-arch.sh --warn-only, the blanket exit-0 downgrade

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
- **#381**: render-pll-cmos5l-record.py asserts the second routing plane "cannot be selected" regardless of the two-layer probe result *(curated)*
- **#389**: sim: the closed-loop proposal deck does not acquire lock at 125 C, and the cp mismatch campaign still has no negative control (follow-ups from #385) *(curated)*
- **#391**: test_cpdiag_metrics.py is a stdlib test no workflow runs *(curated)*
- **#395**: item-10 hygiene inventory's `checks` list has drifted from signoff.yml's actual gate set (5 gates missing) *(curated)*
- **#401**: sim: real-divider closed loop at a VCO frequency inside the divider's measured exact-N range *(curated)*
- **#402**: sim: divider_chain maximum input frequency per corner (the untracked "Divider speed evidence" gap) *(curated)*
- **#403**: sim: reference-input switching-threshold bench for pfd (target-spec R-5) *(curated)*
- **#404**: docs: bring manifests/README.md item 6 and item 8 text and the summary gap table in line with DR-013 and closed trackers *(curated)*

## Proposed (Architect / Hermit)

- **#384**: Collapse run_rerun256.sh (921-line copy of the lock-detector run.sh, one functional line differs) into a thin wrapper *(hermit)*
- **#396**: Collapse run_rerun256.sh into a run.sh output-suffix knob: 906 duplicated lines, one line of real difference *(hermit)*
- **#398**: Remove committed klt scratch cache under sim/ and gitignore .klt/ *(hermit)*
- **#410**: Deduplicate the manifests/ gate envelope checks: four spellings of hash-bound-to-adjacent-GDS, plus one unexercised fallback *(hermit)*
- **#414**: Remove the dead klt() transport from the sg13g2 lock-detector-window batch driver *(hermit)*
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
| Important | 7 |
| Ready (`loom:issue`) | 5 |
| In Progress (`loom:building`) | 9 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 5 |
| Curated | 21 |
| Architect / Hermit proposals | 6 |
| Active epics | 5 |
<!-- guide:plan-body:end -->
