# Work Log

Chronological record of recently merged pull requests and closed issues. This file is maintained by the Loom Guide role.

## Archives

- [2026-09](work_log/WORK_LOG_2026-09.md)

### 2026-11-24

- **PR #567**: refactor: return only the error list from check_hash_bound
- **PR #566**: sim: land #518 seeded-campaign machinery, per-op fleet calibration; park the grid on the runner re-bake
- **PR #564**: refactor(manifests): one envelope-open and hash-bound check for all four gates
- **Issue #565** (closed): manifests/_common.py: check_hash_bound's recorded-hash return is unused while ERC/PEX recompute it
- **Issue #410** (closed): Deduplicate the manifests/ gate envelope checks: four spellings of hash-bound-to-adjacent-GDS, plus one unexercised fallback
- **PR #560**: fix: fail closed on .noise/.ac frequency join loss in VCO jitter extractor
- **Issue #559** (closed): sim: vco-period-jitter extractor still drops .noise rows whose .ac frequency is absent or zero, without a diagnostic
- **PR #555**: fix: fail extract on unparseable trip point and commit per-device noise rows
- **PR #554**: docs: measure item-10 envelope merge exposure and record decision
- **Issue #553** (closed): sim: two evidence-hygiene gaps in the vco-period-jitter extractor (silent trip-point fallback; per-device noise split not committed)

### 2026-11-23

- **PR #557**: refactor: route remaining pinned-PDK closure and resolver copies through stage_pinned_pdk
- **Issue #556** (closed): Consolidate the three remaining pinned-PDK model-closure and resolver copies into sim/tools/stage_pinned_pdk.py
- **PR #552**: docs: cite RECORD-003's 16/17-corner PVT lock in ROADMAP, narrow item 4 to the ss/125C divider miscount
- **Issue #551** (closed): docs: ROADMAP.md lines 38/72/74 still cite #516 as unmeasured now that RECORD-003 is on main
- **PR #548**: docs: cite RECORD-003 PVT lock in chipalooza proposal
- **Issue #547** (closed): docs: three chipalooza 'PVT campaign tracked in #516' passages are stale now that RECORD-003 is on main
- **PR #546**: docs: record RECORD-003's 16/17-corner PVT lock in R-2 and manifests
- **PR #545**: sim: consolidate pinned-PDK deck staging into sim/tools/stage_pinned_pdk.py
- **Issue #544** (closed): Consolidate the four per-bench copies of pinned-PDK model and OSDI deck staging into sim/tools
- **PR #542**: refactor: collapse lock-detector run_rerun256.sh into an OUT_TAG wrapper
- **Issue #541** (closed): WORK_PLAN 'In Progress' section omitted a loom:building issue (#398) that predated generation by 2h36m
- **PR #539**: sim: ignore .klt/ scratch caches and annotate the rerun-324 klt cache as not evidence
- **PR #533**: sim(closed-loop-real-divider): RECORD-003 PVT campaign — 19/20 dual-lock, ss/125C fails in the divider
- **Issue #531** (closed): docs: R-2 evidence paragraph and manifests/README 'does not acquire' sentence still describe RECORD-001
- **PR #523**: sim: transient-noise period-jitter method bench for the free-running vco (steps 1-3; campaign parked on klayout-tools#5772)
- **Issue #516** (closed): sim: closed-loop PVT campaign on the real blocks at the divider-compatible operating point (lock, static phase error, per-domain current; rows 7, 11, 16, R-2)
- **Issue #398** (closed): Gitignore .klt/ and annotate committed rerun-324 klt scratch cache as non-evidence
- **Issue #384** (closed): Collapse run_rerun256.sh (921-line copy of the lock-detector run.sh, one functional line differs) into a thin wrapper
- **Issue #396** (closed): Collapse run_rerun256.sh into a run.sh output-suffix knob: 906 duplicated lines, one line of real difference

### 2026-11-22

- **PR #535**: docs(chipalooza): disclose the DR-010 cp delta and drop single-axis attribution in the RECORD-002 update notes
- **PR #532**: docs(chipalooza): qualify the remaining two 'does not acquire' passages per RECORD-002
- **Issue #534** (closed): docs: three chipalooza RECORD-002 notes say 'the same N = 64 loop' and attribute the lock to the operating point; RECORD-002 discloses a cp delta and declines that attribution
- **Issue #530** (closed): docs: two more pre-RECORD-002 'does not acquire' passages in the chipalooza proposal (:316 sign-off row, :429 unmet list)

### 2026-11-21

- **PR #528**: docs: restate the real-divider nominal lock per RECORD-002 in ROADMAP, chipalooza and spec row 7
- **Issue #525** (closed): docs: three more 'real-divider loop does not acquire' texts outside #521's scope (ROADMAP, chipalooza proposal, spec row-7 evidence cell)
- **PR #522**: docs: cite RECORD-002's nominal real-divider lock in the R-2, manifests and sim README passages
- **Issue #521** (closed): docs: refresh the stale 'loop does not acquire' texts that RECORD-002/#516 supersede (R-2 paragraph, manifests README, sim README bench row

### 2026-11-18

- **PR #510**: manifests: attest scripts/run_gates.py in item-10's hygiene inventory
- **Issue #507** (closed): Decide whether scripts/run_gates.py belongs in item-10's hygiene list (the osdi-arch gate's invocation left an attested file in #503)
- **PR #508**: docs: complete the item-10 audit-command enumeration (24 checks, was 22)
- **Issue #506** (closed): manifests/README.md: the item-10 "Twenty-four audit commands" enumeration lists only 22
- **PR #505**: ci: single-source the item-10 gate list — signoff.yml runs run_gates.py
- **Issue #503** (closed): Single-source the item-10 gate list: signoff.yml and the item-10 inventory share one list

### 2026-11-17

- **PR #501**: sim: report an unresolved stdout as NOT COLLECTED, not a measured NA
- **PR #500**: manifests: attest artifact-manifests.yml in item-10's hygiene inventory
- **Issue #498** (closed): manifests/README.md item-10 defers the artifact-manifests.yml hygiene gap to "its own issue" that was never filed
- **PR #497**: ci: drop the xschem banner exclusion from the netlist drift gate
- **PR #496**: manifests: attest the xschem pin script in item-10's hygiene inventory
- **Issue #495** (closed): item-10 hygiene inventory does not cover .github/scripts/install-xschem, so the xschem pin is no longer hash-attested
- **Issue #494** (closed): netlist gate: the `-I'^* xschem XSCHEM V'` banner exclusion is redundant once the gate is pinned to 3.4.7
- **Issue #453** (closed): sim: the 125 C VCO collector's NA diagnostic reports a missing stdout file as "no per1 line"
- **Issue #117** (closed): renovate.json5: drop invalid 'uv' matchManagers entry and deprecated fetchReleaseNotes key
- **PR #491**: ci: install fleet-pinned xschem 3.4.7 in the netlist gate
- **Issue #490** (closed): xschem pin migration: migrate sg13g2-pll to the fleet 3.4.7
- **PR #489**: docs: state only measured facts for the osdi-arch TAIL reason in run_gates.py
- **PR #375**: sim: supersede loop-bandwidth-pm RECORD-001/002/002-r1 with batch-fleet reruns
- **Issue #488** (closed): ci: consider widening the signoff inventory parity gate to require the bash osdi-arch gate (klt attest proven capable)
- **Issue #486** (closed): ci: run_gates.py's TAIL reason asserts `klt signoff --attest` cannot attest a non-python3 argv — unmeasured
- **PR #485**: run_gates: mirror signoff.yml's bash osdi-arch self-test via a TAIL entry
- **PR #482**: ci: run check-osdi-arch.sh self-test in signoff workflow
- **Issue #483** (closed): ci: run_gates.py's local/CI mirror invariant covers python3 gates only — the new bash self-test is outside it
- **Issue #464** (closed): ci: check-osdi-arch.sh --self-test (27 assertions) is not run by any workflow
- **Issue #319** (closed): Item 9 campaign (#214 part 1/3): supersede loop-bandwidth-pm RECORD-001/002/002b
- **PR #481**: feat: gate docs/ROADMAP.md's accounting sentence against the spec Row table
- **PR #480**: docs: annotate landed postlayout-pex-pvt reruns and past-tense the #221 gate bullet in provenance-migration.md
- **PR #475**: fix: strip unquoted inline comments before scanning signoff.yml gates
- **Issue #466** (closed): check_signoff_inventory_parity.py: an *inline* trailing comment containing python3 still produces a false FAIL
- **Issue #449** (closed): docs: gate docs/ROADMAP.md's spec-accounting figures against spec/target-spec.md §Accounting
- **Issue #447** (closed): Two residual stale statements in sim/provenance-migration.md left by #429's nine-site scope

### 2026-11-16

- **PR #476**: fix: classify python3 value flags (-X, -W, --check-hash-based-pycs) by arity in run_gates script_token
- **Issue #470** (closed): run_gates.py: script_token() drops the gate file after a value-taking interpreter flag (-X/-W), silently excluding such a gate from `--tests`
- **PR #472**: fix(sim): disclose pfd-input-threshold's never-applied res_corner column
- **PR #471**: docs: cite the landed NWell-rule PRs in the sg13cmos5l friction row
- **PR #467**: fix: reject non-plain PEX_SNAP_SUBDIR values in run-pex.sh
- **PR #441**: build: derive package.json's stdlib gate chains from item-10.json
- **PR #465**: fix: guard accounting status row width in check_accounting
- **PR #469**: docs: correct ROADMAP decision-record count to sixteen
- **Issue #454** (closed): sim: pfd-input-threshold publishes a res_corner column its decks never apply
- **Issue #460** (closed): Friction table cites klayout-tools#3573 (closed not_planned) as the source of the NW.c/d/e/f rules; name the landed PRs
- **Issue #458** (closed): run-pex.sh: PEX_SNAP_SUBDIR="." (or "..") still reaches the subset in-place roll-up the #438 guard blocks
- **Issue #393** (closed): Nothing guards package.json's stdlib gate chain against drift from .github/workflows/
- **Issue #462** (closed): run_gates.py pin test: retire the one-shot pre-rewrite snapshot when the next gate lands
- **Issue #457** (closed): check_spec_citations.py: check_accounting() raises IndexError instead of a clean error on a short §Accounting table row
- **Issue #456** (closed): docs/ROADMAP.md:42 says "fifteen decision records" but there are sixteen DR-*.md files
- **PR #463**: spec: name row 6/6a, row 16 and R-2's row 2-derived figures in R-13
- **PR #461**: fix: stop the backslash-continuation join at a shell comment line
- **PR #455**: docs: correct closed klayout-tools#3012/#2726 gap status to the 0.8.0 pin
- **PR #452**: sim: resolve flat <id>.out stdout layout in the 125C acquisition collector
- **PR #451**: sim: send check-osdi-arch.sh usage() to stderr and add retired-flag self-test guard
- **PR #450**: fix: hard-fail PEX_BLOCKS without PEX_SNAP_SUBDIR in run-pex.sh
- **PR #448**: spec: reconcile Accounting total to 18 rows and gate it
- **PR #446**: bench: pfd REF-input switching thresholds across the row-2 operating box
- **PR #445**: docs: mark closed klt#2727/#221/#139 blockers resolved in provenance-migration
- **PR #430**: refactor: dedupe the two layout-flow drivers onto layout/bin/layout-flow.sh, fix the cross-flow -dirty record-id stamp
- **Issue #444** (closed): spec: rows 6/6a and 16 still derive their figures from row 2's union range — name them in R-13
- **Issue #439** (closed): sim: RECORD-015's offline reproduce path for the 125 C VCO CSV needs a layout the committed raw files do not have
- **Issue #438** (closed): run-pex.sh: PEX_BLOCKS without PEX_SNAP_SUBDIR truncates the committed snapshot roll-up
- **Issue #436** (closed): check_signoff_inventory_parity.py: a comment line joined by a \-continuation can produce a false FAIL
- **Issue #432** (closed): Correct stale klayout-tools#3012 / #2726 'open' status in sg13cmos5l README, manifests/README.md and challenge-6 proposal
- **Issue #429** (closed): Correct stale klayout-tools#2727 'open/blocking' status in provenance-migration.md and characterization/SUMMARY.md
- **Issue #419** (closed): check-osdi-arch.sh: usage() prints the USAGE block to stdout, blocking an rc-only self-test guard for retired flags
- **Issue #415** (closed): Dedupe the two layout-flow drivers onto a shared lib (28 of 33 lines identical), and fix the cross-flow -dirty stamp they both carry
- **Issue #407** (closed): spec: target-spec.md Accounting says "17 rows" but its own status table lists 18
- **Issue #403** (closed): sim: reference-input switching-threshold bench for pfd (target-spec R-5)

### 2026-11-15

- **PR #443**: sim: remove dead klt() submit helper and stale transport claims from sg13g2 run_batch
- **PR #440**: spec: restate row 2's f_ref window as the PVT intersection (DR-014)
- **PR #437**: sim: bound divider_chain max exact-N input frequency per corner (880-1328 MHz, N=64)
- **PR #434**: fix: cite klayout-tools#1962 as the live block-routing gap in the cmos5l record renderer
- **PR #433**: fix: see backslash-continued and -X/-W-flagged python3 gates in signoff parity parser
- **PR #428**: sim: lock the real-divider loop at a divider-compatible operating point (RECORD-002)
- **Issue #426** (closed): spec: row 2's f_ref window is a corner union on a worst-case row — supersede DR-005's derivation (found by the band-11 125 C shortfall)
- **Issue #414** (closed): Remove the dead klt() transport from the sg13g2 lock-detector-window batch driver
- **Issue #409** (closed): check_signoff_inventory_parity.py misses backtick-continued and -X-flagged python3 gates (false pass)
- **Issue #402** (closed): sim: divider_chain maximum input frequency per corner (the untracked "Divider speed evidence" gap)
- **Issue #401** (closed): sim: real-divider closed loop at a VCO frequency inside the divider's measured exact-N range
- **Issue #397** (closed): render-pll-cmos5l-record.py still blames klayout-tools#1467 for the block-routing gap, which closed upstream and is fixed at this pin (the live gap is #1962)
- **PR #424**: docs: mark klayout-tools #1157/#2145/#2355 closed at the 0.8.0 pin
- **PR #423**: layout: retire the mom_cap lift/splice workaround for klayout-tools#2327
- **PR #427**: sim: 125C non-acquisition is the vco band-11 range ceiling; seeded mm_p12 negative control reads detected at both yield limit sets
- **PR #435**: pex: re-extract lock_detector from the post-#136 GDS, add its klt pex envelope, re-measure on batch
- **PR #425**: docs: align manifests item 6 / item 8 and summary gap rows with RECORD-011, DR-013 and open trackers
- **PR #413**: fix: derive the record's second-routing-plane sentence from its own probe
- **Issue #422** (closed): Correct stale 'open' status for klayout-tools#1157/#2145/#2355: all closed and fixed at the 0.8.0 pin
- **Issue #421** (closed): Retire the klayout-tools#2327 lift/splice workaround in mom_cap_reference: the gap closed and is at this repo's pin
- **Issue #389** (closed): sim: the closed-loop proposal deck does not acquire lock at 125 C, and the cp mismatch campaign still has no negative control (follow-ups from #385)
- **Issue #412** (closed): Verify epic #6 deliverable before closing: tracker reads 14/22 T1 items met, tier null
- **Issue #157** (closed): pex: re-extract lock_detector from the post-#136 GDS and run klt pex (withheld from T1 item 7 in #152)
- **Issue #404** (closed): docs: bring manifests/README.md item 6 and item 8 text and the summary gap table in line with DR-013 and closed trackers
- **Issue #381** (closed): render-pll-cmos5l-record.py asserts the second routing plane "cannot be selected" regardless of the two-layer probe result
- **PR #408**: refactor(manifests): share the record resolver, sha256_file and JSON loader across the four signoff gates
- **Issue #405** (closed): Deduplicate manifests/ gate helpers: one record resolver, one sha256_file, one JSON loader

### 2026-11-14

- **PR #399**: ci: guard item-10's checks inventory against signoff.yml gate drift
- **PR #418**: refactor: drop check-osdi-arch.sh --warn-only, the blanket exit-0 downgrade
- **Issue #395** (closed): item-10 hygiene inventory's `checks` list has drifted from signoff.yml's actual gate set (5 gates missing)
- **Issue #417** (closed): render-pll-cmos5l-record.py: a two-layer attempt with both an error and a nonzero routed count renders a bullet and a paragraph that contradict each other
- **Issue #406** (closed): Remove check-osdi-arch.sh --warn-only: a never-called flag that downgrades a known-unloadable deck to exit 0
- **Issue #411** (closed): Remove the dead klt() transport and consolidate the duplicated klt-sim deck-list machinery in the two lock-detector-window batch drivers
- **PR #400**: docs: roadmap as of 2026-11-13
- **PR #394**: ci: gate the two testbench metric-extraction self-tests
- **PR #377**: refactor: split the SG13CMOS5L record renderer into per-section helpers
- **Issue #376** (closed): Split render-pll-cmos5l-record.py's 525-line main() into testable section renderers
- **PR #392**: build: run the repo's stdlib test and check gates from package.json
- **Issue #388** (closed): Wire package.json test/check:ci to the real checks: the stubs exit 0 without running anything

### 2026-11-13

- **PR #390**: sim+spec: measure the cp mismatch-to-phase-error gain on the DR-010 cp and retire the +/-3.5% screening limit
- **Issue #385** (closed): spec+sim: re-measure the cp mismatch-to-phase-error gain on the DR-010 cp and propose a cp mismatch limit (T1 item 6 follow-up to #178)
- **PR #387**: feat(probes): tally each gen-compose attempt's own Metal1/Via1/Metal2 shapes
- **Issue #383** (closed): Measure whether the two-layer gen-compose route draws on a second metal (klayout-tools#1474 no longer rejects 'metal2')
- **PR #386**: sim: run the cp mismatch Monte Carlo campaign and wire T1 item 6
- **Issue #178** (closed): sim: Monte Carlo bench for cp up/dn mirror mismatch with klt yield report (T1 item 6)
- **PR #382**: docs: cite the LATEST record for cp's gen-compose probe figures
- **Issue #379** (closed): Stale `cp` block counts quoted in cmos5l layout prose (8 groups / 14 devices vs 13 / 28 in the latest record)
- **PR #378**: refactor: move the klt-gen capability probes into cmos5l_probes.py
- **Issue #372** (closed): Split the klt-gen capability probes out of pll_cmos5l_layout.py into a sibling module
- **PR #374**: sim: supersede vco-kvco-table RECORD-001 with a fleet rerun on the pinned PDK
- **Issue #318** (closed): Item 9: supersede sg13cmos5l-vco-kvco-table provenance (child of #216)
- **Issue #360** (closed): Migrate three pre-#261 layout records into the objects dedupe store (~100 MB)

### 2026-11-12

- **PR #370**: sim: rerun loop_filter momcap records on batch fleet, add superseded addenda
- **Issue #321** (closed): Item 9 campaign (#214 part 3/3): supersede loop-filter-momcap RECORD-001/002
- **Issue #215** (closed): Item 9 campaign: post-layout PEX/PVT provenance
- **PR #367**: sim: rerun RECORD-004 loop-filter and divider-chain arms on the batch fleet
- **PR #366**: sim: run retry2 tier in run_rerun328.sh and tolerate all-tier failure
- **PR #363**: sim: waveform check of retimed XFRT capture edge at 1562 MHz (RECORD-003)
- **Issue #362** (closed): divider_chain: waveform-level check of retimed capture edge at 1562 MHz (RECORD-002 Finding 4)
- **Issue #350** (closed): run_rerun328.sh does not invoke the retry2 tier its record relies on
- **Issue #326** (closed): Item 9 campaign (#215 part 4/4): supersede postlayout-pex-pvt RECORD-004 (loop filter + divider chain)
- **Issue #213** (closed): Item 9 campaign: PEX-signoff and lock-detector provenance
- **PR #361**: sim: 9-corner retime and opposite-edge retiming evidence for row-3 closure (RECORD-002)
- **Issue #189** (closed): divider_chain: size to close row 3 retiming at 1562 MHz (R-3, T1 item 5)

### 2026-11-11

- **PR #359**: sim: add 3.0/3.3/3.6 V supply-range sweep for vco, lock_detector, divider_chain
- **PR #358**: docs: reword bodyfix-pvt gap to point at RECORD-011 full-grid evidence
- **PR #357**: sim: dff_tg_hv sizing sweep vs row-3 retiming closure (partial)
- **PR #353**: sim: add SG13CMOS5L vco output-levels bench for spec row 14
- **PR #352**: sim: full-grid batch rerun of XRPU-bulk-on-VSS lock detector vs RECORD-004 (RECORD-009)
- **PR #351**: sim: batch-fleet rerun of SG13G2 lock-detector RECORD-001 with superseded addendum
- **PR #349**: sim: rerun RECORD-001 92-point lock_detector grid via klt sim batch on db36732 files
- **PR #348**: sim: rerun RECORD-002 resized lock-detector grid on batch fleet at 07e1866; superseded addendum
- **PR #347**: sim: rerun RECORD-003 pfd and lock-detector arms on the batch fleet; superseded addendum
- **PR #346**: sim: rerun postlayout-pex-pvt RECORD-002 on pinned dual-tree PDK; superseded addendum
- **PR #345**: sim: fleet rerun of vco-duty-cycle RECORD-001 grid; superseded addendum
- **PR #344**: sim: rerun pre-repair divider RECORD-001/002 on batch fleet, superseded addenda
- **PR #343**: sim: rerun RECORD-001 post-layout PEX PVT matrices on batch fleet; superseded addendum
- **PR #342**: sim: rerun RECORD-004 crowbar grid on the batch fleet at the pinned PDK revisions; superseded addendum
- **PR #341**: sim: rerun historical cp Icp-trim grids on batch fleet and supersede RECORD-001/002
- **PR #340**: sim: rerun RECORD-003 divider repair re-verification on the batch fleet; superseded addendum
- **PR #338**: sim: re-measure SG13G2 divider repair opconv/hold/func on batch fleet; superseded addendum
- **PR #337**: sim: rerun RECORD-003 schmitt_rewire grid on batch fleet with pinned provenance
- **PR #333**: sim: rerun sg13g2 VCO Kvco table on batch fleet, supersede RECORD-001
- **Issue #355** (closed): Follow-on from PR #352: refresh stale text in RECORD-011 and sources.json bodyfix-pvt gap
- **Issue #331** (closed): sim: rerun lock-detector-window RECORD-004-crowbar-current-mitigation on batch fleet (provenance migration)
- **Issue #329** (closed): sim: rerun lock-detector-window RECORD-003-hysteresis-fix on batch fleet (provenance migration)
- **Issue #328** (closed): sim: rerun lock-detector-window RECORD-002-resized-window-hysteresis-chatter on batch fleet (provenance migration)
- **Issue #327** (closed): sim: rerun lock-detector-window RECORD-001-window-hysteresis-chatter on batch fleet (provenance migration)
- **Issue #325** (closed): Item 9 campaign (#215 part 3/4): supersede postlayout-pex-pvt RECORD-003 (PFD + lock detector)
- **Issue #324** (closed): Item 9 campaign (#215 part 2/4): supersede postlayout-pex-pvt RECORD-002 (floorplan-aware VCO route)
- **Issue #323** (closed): Item 9 campaign (#215 part 1/4): supersede postlayout-pex-pvt RECORD-001 (VCO + CP)
- **Issue #317** (closed): Item 9: supersede sg13cmos5l-vco-duty-cycle provenance (child of #216)
- **Issue #257** (closed): Item 9 (#213 child): supersede lock-detector-window RECORD-001..004 (historical grids; needs batch route)
- **Issue #237** (closed): Item 9: supersede SG13G2 VCO Kvco RECORD-001
- **Issue #236** (closed): Item 9: supersede SG13G2 lock detector RECORD-001
- **Issue #235** (closed): Item 9: supersede SG13G2 divider repair RECORD-001
- **Issue #233** (closed): Item 9 campaign (#212 part 4/4): supersede divider-nrange-retiming RECORD-003 (repaired divider re-verification)
- **Issue #232** (closed): Item 9 campaign (#212 part 3/4): supersede divider-nrange-retiming RECORD-001/002 (pre-repair divider)
- **Issue #230** (closed): Item 9 campaign (#212 part 1/4): supersede cp-icp-trim RECORD-001/002 (historical Icp-trim grids)
- **Issue #190** (closed): sim: SG13CMOS5L vco output-levels bench for spec row 14 (T1 item 5)
- **Issue #187** (closed): sim: supply-range 3.0/3.3/3.6 V sweep beyond cp for spec row 18 (T1 item 5)
- **Issue #139** (closed): sim: run the owed full-PVT lock_detector grid for the #136 bodyfix DUT (RECORD-005 is nominal-only)
- **PR #336**: sim: add klt sim batch deck-list driver for the lock_detector grid
- **Issue #322** (closed): sim: batch-request driver for the sg13cmos5l lock_detector full grid (klt sim route)

### 2026-11-10

- **PR #313**: docs(spec): state row 14 output swing as single-ended per node, add DR-011
- **Issue #312** (closed): spec: state clock output swing and load for a downstream TX mux
- **PR #308**: docs(design): annotate LOCK opin as active-low in lock_detector schematics
- **Issue #307** (closed): lock_detector: add (active-low) note to source schematic LOCK pin

### 2026-11-06

- **PR #298**: test: add static pfd reset-chain parity guard
- **Issue #297** (closed): Add a static netlist guard for pfd reset-chain parity in both committed pfd netlists

### 2026-10-29

- **Issue #122** (closed): README: embed the fleet burndown chart (one line)

### 2026-10-27

- **PR #293**: build: pin klayout-tools to 0.8.0 and regenerate signoff evidence
- **Issue #292** (closed): Bump klayout-tools pin daf06a51afaf → 0.8.0

### 2026-10-24

- **PR #289**: chore(layout): prune superseded flow records, document retention policy
- **Issue #286** (closed): Prune unreferenced superseded layout flow records (~70 MB)

### 2026-10-23

- **PR #284**: fix: add third reset-chain inverter to top-level pfd for AND(UP,DN) reset
- **Issue #283** (closed): Fix pfd self-reset inverter-parity defect in top-level design/pfd.sch (sibling of #56)
- **PR #281**: characterization: repoint or drop gap rows citing closed trackers
- **Issue #279** (closed): characterization: re-audit the SUMMARY.md open-gaps table; five gap rows cite closed trackers (#148, #165, #168, #195, #196)
- **PR #280**: feat: keep new evidence bytes in the artifact store, commit manifests
- **Issue #278** (closed): Adopt the common artifact store for sim evidence (manifests in git, bytes via klt artifact)

### 2026-10-22

- **Issue #273** (closed): Remove unreferenced layout report dirs (~76 MB of superseded run records)

### 2026-10-20

- **PR #270**: feat(signoff): attest T1 item 1 with klt signoff --attest 1
- **Issue #267** (closed): T1 item 1: attest design sources with klt signoff --attest 1 (both partitions)

### 2026-10-17

- **PR #268**: feat(signoff): attest T1 item 10 with klt signoff --attest and bump the grading pin
- **Issue #266** (closed): T1 item 10: attest repo hygiene with klt signoff --attest (both partitions)
- **PR #263**: feat(layout): dedupe future layout report artifacts via content-addressed store
- **Issue #261** (closed): Prepare future layout-output deduplication while preserving historical runs and per-run provenance

### 2026-10-13

- **PR #259**: sim: rerun RECORD-005 nominal lock-detector window on pinned dual-tree PDK; superseded addendum
- **PR #258**: sim: supersede klt-pex-signoff RECORD-001 with pinned nominal rerun (Closes #255)
- **Issue #256** (closed): Item 9 (#213 child): supersede lock-detector-window RECORD-005 (nominal body-on-VSS)
- **Issue #255** (closed): Item 9 (#213 child): supersede klt-pex-signoff RECORD-001 (nominal 5-block PEX)

### 2026-10-12

- **PR #253**: chore(ci): adopt unified IHP-Open-PDK SG13CMOS5L pin for install and netlist CI
- **Issue #252** (closed): Adopt the unified IHP-Open-PDK SG13CMOS5L pin in install and netlist CI
- **Issue #211** (closed): Item 9 campaign: closed-loop lock and real-divider provenance

### 2026-10-11

- **PR #247**: sim: partial rerun of RECORD-006 (control_probe, ideal_dump) on pinned dual-tree PDK; superseded addendum (Closes #239)
- **PR #246**: sim: rerun RECORD-004 ideal-cp diagnostic on pinned dual-tree PDK; superseded addendum (Closes #228)
- **PR #245**: sim: supersede RECORD-005 provenance by pinned dual-tree nominal rerun (Closes #229)
- **PR #244**: sim: supersede closed-loop RECORD-001 provenance by pinned dual-tree rerun (Closes #225)
- **Issue #239** (closed): Item 9: supersede closed-loop RECORD-006 provenance by rerun
- **Issue #229** (closed): Item 9: supersede closed-loop RECORD-005 provenance by rerun
- **Issue #228** (closed): Item 9: supersede closed-loop RECORD-004 provenance by rerun
- **Issue #225** (closed): Item 9: supersede closed-loop RECORD-001 provenance by rerun
- **PR #242**: sim: supersede RECORD-003 provenance by pinned dual-tree rerun (Closes #227)
- **PR #241**: sim: supersede RECORD-002 provenance by dual-tree rerun (Closes #226)
- **PR #240**: sim: recover real-divider RECORD-001 provenance; RECORD-006 fails validation
- **PR #238**: manifests: multi-tree PDK revision citations in records (Closes #221)
- **Issue #227** (closed): Item 9: supersede closed-loop RECORD-003 provenance by rerun
- **Issue #226** (closed): Item 9: supersede closed-loop RECORD-002 provenance by rerun
- **Issue #224** (closed): Item 9: recover provenance for closed-loop RECORD-006 and real-divider RECORD-001
- **Issue #221** (closed): Item 9 gate: rerun records in sg13cmos5l benches cannot cite the ihp-sg13g2 revision their symlinked models resolve to
- **Issue #220** (closed): Item 9 campaign: integrate resolved provenance and regenerate tier evidence
- **Issue #219** (closed): Item 9 campaign: SG13G2 divider, lock-detector, and VCO provenance

### 2026-10-10

- **PR #222**: sim: inventory 37 grandfathered records and pin ihp-sg13g2 (item 9 campaign phase 1)
- **Issue #210** (closed): Item 9 campaign: inventory 37 grandfathered records and pin ihp-sg13g2

- **PR #208**: Item 9: validate append-only provenance addenda and superseding reruns
- **Issue #198** (closed): Item 9: validate append-only provenance addenda and superseding reruns
- **PR #205**: layout: redraw pll_cp for DR-010; refresh cp LVS/ERC/PEX evidence and re-pin the manifest (#195)
- **PR #204**: loop-bandwidth-pm: real idle cp on VCTRL in PM bench; re-check DR-007/DR-008 tuples (#196)
- **PR #202**: Burn down records_baseline.json: cite 5 historical records (19 -> 14)
- **Issue #196** (closed): loop-bandwidth-pm: PM bench omits cp's VOUT capacitance on the 100 fF C2 node; re-check the sub-1-degree PM tuples
- **Issue #195** (closed): layout: redraw pll_cp for the DR-010 tracking dump buffer; refresh cp LVS/ERC/PEX evidence
- **Issue #185** (closed): Burn down characterization/records_baseline.json grandfathered exceptions

### 2026-10-09

- **PR #197**: cp_dumpbuf: VDUMP tracks VOUT via unity-gain 5T OTA pair (DR-010); row 7 0.78% at nominal
- **Issue #165** (closed): cp: make VDUMP track VOUT at DC to remove dump-node charge sharing (row 7 static phase error)
- **Issue #161** (closed): Auditor guard review: worktree-write-confinement-unresolved-var (retain safety pending replay)
- **PR #193**: manifests: spec row-table citation gate
- **PR #192**: sim: npn13G2 r_o/matching vs cp CMOS cascode, klt bipolar extract/LVS probe, DR-009 (Closes #181)
- **PR #191**: sim: Monte Carlo bench for cp up/dn mismatch (controls; campaign blocked) (Part of #178)
- **PR #183**: ci: validate sim evidence records and enforce append-only
- **PR #184**: signoff: gate testbench coverage and PDK-revision pinning (T1 item 9)
- **PR #177**: spec: draft target-spec.md from porting plan and DR-005 to DR-008
- **Issue #186** (closed): spec: CI gate resolving target-spec.md row citations (T1 item 5)
- **Issue #181** (closed): sim: SG13G2 npn13G2 characterization to test DR-002's deferred HBT cascode trigger, plus klt bipolar extract/LVS probe
- **Issue #180** (closed): ci: validate sim evidence records and enforce append-only (T1 item 10)
- **Issue #179** (closed): signoff: gate testbench coverage and PDK-revision pinning across sim benches (T1 item 9)
- **Issue #148** (closed): spec: draft spec/target-spec.md from the porting plan and DR-005 to DR-008 (prerequisite for T1 item 5, both partitions)
- **PR #175**: signoff: validate DRC coverage and freshness for all six composed PLL blocks
- **PR #174**: characterization: generated, CI-checked summary of committed sim evidence (#171)
- **PR #173**: signoff: gate sibling PEX reports and flattened schematic provenance
- **PR #172**: sim: retain divider-speed evidence, index real-divider bench, fix extract window end (#168)
- **Issue #171** (closed): characterization: derive a revision-qualified PLL evidence summary for T1 item 8
- **Issue #170** (closed): signoff: gate sibling PEX reports and flattened schematic provenance
- **Issue #169** (closed): signoff: validate DRC coverage and freshness for all six composed PLL blocks
- **Issue #168** (closed): Follow-on from PR #167: retain divider-speed evidence and index the nominal bench
- **PR #167**: sim: nominal closed-loop with repaired divider_chain does not acquire (#159)
- **Issue #159** (closed): sim: verify nominal closed-loop acquisition with the repaired transistor-level divider

### 2026-10-08

- **PR #164**: sim: RECORD-006 -- isolate cp dump-node charge sharing as row 7's 8.2% static phase error
- **PR #163**: docs: refresh README status to match landed design, layout and evidence
- **PR #162**: signoff: klt erc supply evidence for the five analog blocks; T1 item 11.analog met (#147)
- **PR #158**: signoff: audit PEX body-bias and cite T1 item 7 (post-layout) (#152)
- **PR #156**: ci: run layout generator unit tests (layout-tests job)
- **PR #155**: signoff: cite T1 items 1 and 2 and gate netlist regeneration in CI
- **Issue #150** (closed): Close spec row 7: isolate the dynamic charge-mismatch cause of the 8.2% static phase error
- **Issue #160** (closed): docs: reconcile README pre-plan status with landed PLL design and verification evidence
- **Issue #147** (closed): layout: klt erc supply specs and reports for the five analog blocks (T1 item 11, analog partition)
- **Issue #152** (closed): signoff: audit PEX body-bias binding and cite T1 item 7 (post-layout) per block
- **Issue #153** (closed): ci: run the layout generator unit tests in a workflow (T1 item 10)
- **Issue #151** (closed): signoff: cite T1 items 1 and 2 (design sources, layout) and gate netlist regeneration in CI
- **PR #149**: signoff: cite T1 item 4 (LVS clean) for both partitions (record 20261003-183059-dc5644a)
- **Issue #146** (closed): signoff: cite T1 item 4 (LVS clean) for both partitions now that all six blocks match (record 20261003-183059-dc5644a)
- **Issue #100** (closed): Post-layout PVT needs a representative floorplan (and post-layout arms for pfd/lock_detector) — the open risk #30 recorded and left unowned

### 2026-10-07

- **PR #143**: Consolidate gen_ladder.py copies into sim/tools/gen_lock_ladder.py
- **Issue #127** (closed): Consolidate the two gen_ladder.py copies (sg13g2 / sg13cmos5l lock-detector-window) into one shared sim/tools script

### 2026-10-03

- **PR #142**: docs: refresh stale layout/sim README sections to LATEST record (#140)
- **PR #141**: docs: refresh Challenge 6 proposal against closed #112-#115/#136 evidence
- **PR #138**: fix: close SG13CMOS5L lock_detector LVS (RPU body on VSS + contact the w=0.25u XMPD)
- **Issue #140** (closed): layout README + postlayout sim README carry pre-#114/#136 stale sections contradicting their own LATEST records
- **Issue #137** (closed): Refresh Challenge 6 proposal against completed port follow-ups and final LVS evidence
- **Issue #136** (closed): Fix SG13CMOS5L lock_detector LVS substrate-split mismatch
- **Issue #63** (closed): chore: report the tracked-x86-64-ELF cap_cmomi/cap_cmomf OSDI packaging gap upstream to IHP-GmbH/ihp-sg13cmos5l

### 2026-09-24

- **PR #135**: test: fix cap_cmomi blocked_reason assertion after #119 rewording
- **PR #133**: test: realign the SG13CMOS5L layout tests with #119's local MoM-cap promotion
- **PR #131**: refactor: route group_size_um's capacitor branch through mom_cap_size
- **Issue #134** (closed): dep-recheck-fingerprint.sh named-dependency: cross-repo owner/repo#N Dependencies refs silently parse as VERDICT=clear
- **Issue #132** (closed): test_pll_layout_plan.py: test_plan_block_records_but_never_attempts_cap_cmomi asserts a 'never drawn' substring #119 removed from BLOCKED_REASONS
- **Issue #130** (closed): test_pll_cmos5l_layout.py: 3 failing + 5 erroring tests after #119 (REFERENCE_DEVICE_MAP/CAPACITOR_PROBE_DEVICE_MAP removed, vco_composed crashes on promoted capacitor group)
- **Issue #126** (closed): Simplify: mom_cap_size() is dead and its rule is restated inline in group_size_um — keep one

### 2026-09-23

- **PR #129**: sim: add post-layout PVT arms for loop_filter and divider_chain (RECORD-004)
- **PR #128**: fix: add dual-inversion dff feedback and staggered CKBB clocking
- **PR #125**: fix: splice --pdk-root after find subcommand in PDK record renderers
- **PR #123**: fix: declare vco's XBIAS resistor bodies on VSS, close the vco LVS mismatch
- **Issue #115** (closed): Add post-layout PVT arms for loop_filter and divider_chain in the SG13CMOS5L PLL port (Part of #16)
- **Issue #120** (closed): Fix design/dff_tg_hv.sch — same one-inversion hold-path defect as the SG13CMOS5L port (#112): feedback is not a bistable latch
- **Issue #124** (closed): layout: render-pll-cmos5l-record.py inserts --pdk-root at the wrong argv index, so PDK resolution silently fails and records render 'not resolved (plan-only run)'
- **Issue #113** (closed): Root-cause vco's unmatched 6-resistor + 1-merged-net LVS mismatch in the SG13CMOS5L PLL port (Part of #16)

### 2026-09-22

- **PR #121**: fix: repair dff_tg_hv hold-path feedback + clock staggering; re-verify divider N range and retiming margin
- **PR #119**: layout: draw cap_cmomi MoM caps locally on SG13CMOS5L, close loop_filter LVS
- **PR #118**: docs: re-derive challenge-6-proposal.md against current sim/layout evidence
- **Issue #112** (closed): Fix design/sg13cmos5l/divider_chain.sch — committed schematic does not function as a divider at any tested corner (Part of #16)
- **Issue #114** (closed): Draw cap_cmomi MoM-capacitor instances for SG13CMOS5L PLL loop_filter/vco/lock_detector layout, close LVS (Part of #16)
- **Issue #116** (closed): Rewrite docs/chipalooza/challenge-6-proposal.md against current sim/layout evidence (Part of #16)

### 2026-09-21

- **PR #110**: sim: re-measure lock_detector PVT arms against c44fa68 extraction
- **PR #107**: sim: add post-layout PVT arms for pfd and lock_detector (RECORD-003)
- **PR #108**: feat: add klt signoff block manifest, graded tier report, and CI grade gate
- **PR #106**: layout: locality floorplan pass for pll_vco with PVT re-run
- **PR #105**: feat: add divider-chain klt erc supply spec and T1 item-11 evidence
- **Issue #109** (closed): Re-run lock_detector post-layout PVT arms against the c44fa68 extraction (RECORD-003 / PR #107 blocker)
- **Issue #102** (closed): Add post-layout PVT arms for pfd and lock_detector (sg13cmos5l)
- **Issue #104** (closed): Commit a klt signoff block manifest so this block's T1 state is graded, not hand-read
- **Issue #101** (closed): Floorplan-aware routing for post-layout pll_vco PVT re-simulation (sg13cmos5l)
- **Issue #103** (closed): T1 item 11 (power delivery, structural): no klt erc supply spec or report in this repo

### 2026-09-19

- **PR #99**: [Part of #16] Post-layout PEX + PVT re-simulation for the SG13CMOS5L PLL port
- **Issue #30** (closed): [Part of #16] Post-layout PEX + PVT re-simulation for the SG13CMOS5L PLL port

