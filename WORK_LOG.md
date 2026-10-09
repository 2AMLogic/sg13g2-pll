# Work Log

Chronological record of recently merged pull requests and closed issues. This file is maintained by the Loom Guide role.

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

### 2026-09-09

- **PR #98**: sim: stand up sg13g2-vco-kvco-table (SG13G2 twin of sg13cmos5l-vco-kvco-table)
- **Issue #97** (closed): sim: stand up `sim/sg13g2-vco-kvco-table/` — open-loop VCO band / Kvco-vs-band-code table for the SG13G2 design across its PVT grid (rows 1/4/5; the SG13G2 twin of `sg13cmos5l-vco-kvco-table`)
