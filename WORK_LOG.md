# Work Log

Chronological record of recently merged pull requests and closed issues. This file is maintained by the Loom Guide role.

## Archives

- [2026-09](work_log/WORK_LOG_2026-09.md)

### 2026-11-14

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

