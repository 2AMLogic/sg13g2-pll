# Work Log

Chronological record of recently merged pull requests and closed issues. This file is maintained by the Loom Guide role.

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
