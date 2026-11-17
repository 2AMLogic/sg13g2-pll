# RECORD-009: `lock_detector` re-extraction from the post-#136 GDS and its post-layout (PEX) re-measurement on the batch fleet (issue #157)

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #157 (the withhold RECORD-003 disclosed in T1 item 7's audit,
  #152). Append-only. This record re-measures the lock_detector arms of
  `RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` against the
  **current** layout; it neither edits that record nor any historical CSV,
  and its CSVs are new paths (`corners/*-rerun157.*`). It supersedes only
  RECORD-003's *evidence claim* for `pll_lock_detector` (the `pfd` arm is
  NOT re-measured here; RECORD-003 and its migration rerun RECORD-006 remain
  the pfd evidence).
- **Corner coverage**: RECORD-003's own lock_detector matrices, unchanged and
  uncut: the committed-window control reproduction (102 points), the device
  R/C extraction (15 rows), the whole-cell window grid (as-layout 56 +
  post-layout 29 rows), the ladder/recovery set (32 corner rows, 288 raw
  ladder-point rows) and the timestep-convergence check (6 rows). All
  units came back with a measurement; one ladder-point unit needed the
  runner's one recorded `trtol=1` retry (`ld_solver_retries-rerun157.txt`).
- **DUT**: `netlist-snapshots/rerun-157/pll_lock_detector.pex.spice`, sha256
  `a74e82c1490ac6cd5cde99ed15620a640e0c5e98e754c091a3ec14c772a00d24` — the
  `klt extract --deck sg13cmos5l --parasitics --pdk ihp-sg13cmos5l`
  extraction of `pll_lock_detector.gds` from layout record
  `20261010-012952-a4ca1b8` (the manifest's authoritative `4.analog` record;
  its GDS sha256 `54bea524f81541c7c3be3fdad14423acf47eb7a0972c07932701c3e691ac2afc`
  is byte-identical in `20261003-183059-dc5644a` — the #136 substrate-split
  record the issue was filed against — and in the `LATEST` record
  `20261027-175228-74cf8d0-dirty`, so "the current layout" is unambiguous).
  41 devices (19 `sg13_hv_nmos` + 18 `sg13_hv_pmos`, bodies `VSS`/`VDD`;
  1 `rhigh`, bulk `VSS` — the #136 `XRPU` repair; 3 `cap_cmomi` cards: the
  drawn `XCW` plus `XDW.XC1`'s m=2 as two cards), 23 nets, 157 parasitic
  resistors (ΣR 21926.19 Ω), 23 substrate + 175 coupling capacitors
  (ΣC 3904.30 fF, ΣCC 3.58 fF), no metal without a coefficient. The
  committed top-level snapshot (`klt 0.6.0` of the **pre-#136** GDS
  `61a18fc1…`) is untouched, per the `rerun-324` append-only precedent; its
  own roll-up `provenance.json` counts (149 R / 1926.21 Ω / 465.89 fF —
  RECORD-003's c44fa68-era extraction) do not describe the snapshot file
  beside them (which its own `provenance.input` pins to `61a18fc1…` with
  155 R / 21817.26 Ω / 3904.09 fF); this record's rerun-157 provenance is
  the current-layout roll-up and supersedes both as the lock_detector
  evidence pointer.
- **Reproduce**:
  - `PEX_BLOCKS="lock_detector" PEX_SNAP_SUBDIR="rerun-157"
    PEX_LAYOUT_RECORD=20261010-012952-a4ca1b8 PDK_ROOT=<pdk-root>
    ./extraction/run-pex.sh` (byte-reproduces the rerun-157 snapshot;
    verified deterministic — two runs produced the identical sha256 above).
  - The re-measurement: the `rerun157/tools/` bridge cycle —
    `runpass.sh` renders the **unmodified** `testbench/run_lock_detector.sh`
    through an `ngspice` shim that records every deck instead of running it
    locally, `passdeck.py convert` turns the pending set into a `klt sim`
    deck-list request, `submit.sh` runs
    `klt sim --backend batch --wait-for-capacity 600` (never local), the
    reports are ingested back into the shim's cache, and the next pass
    replays them; cycles repeat until a pass renders nothing new (here:
    pass 10), and that pass reduces the CSVs exactly as the runner does
    locally. Same protocol as the #325 rerun (`rerun325/tools`); this
    rerun's copies are parameterized by environment instead of hardcoded
    scratch paths.

## 1. Environment and provenance

- **PDK revisions.** The request names `models.pdk: ihp-sg13cmos5l`; both
  trees are involved because the `cmos5l` models are symlinks into
  `ihp-sg13g2`. `sim/README.md` pins `ihp-sg13cmos5l`
  607e18d4bd9214a52575c194b4181ef449f9252f and `ihp-sg13g2`
  5cccb161f7492697cfa52eb14dc03beb00bdca9e. **They are the pins, not a
  claim about what ran.** The batch worker's PDK root `/opt/pdk` carries no
  revision stamp (`environment.remote.worker_environment.pdk.stamp_scheme:
  null`, diagnostics `pdk stamp unreadable`), so the worker's
  `ihp-sg13cmos5l` revision is **unknown** — the same unattributed-worker
  situation RECORD-006 and RECORD-011 disclosed. What IS evidenced: the
  control rows below reproduce committed values where the resistor content
  is not involved (see §2), which ties the worker's *capacitor and MOS*
  content to the content the committed controls were measured with.
- **Tool.** Client `klt 0.9.3.dev3+gd5d57daf9a14`; batch runner
  `klt 0.9.0` (`runner_compatibility: match`); ngspice-47 (KLU) on both the
  submitting host (`~/.local/bin/ngspice`) and the worker
  (`/usr/local/bin/ngspice`, banner in the report's
  `worker_environment.simulator.version_banner`). RECORD-003's original ran
  ngspice-46; the committed envelope evidence of the sibling signoff slug
  pins ngspice-46 too. No byte-identity claim against ngspice-46 outputs is
  made; the controls that ARE byte-compared below reproduce under -47.
- **Fleet jobs** (all `aws-batch-fleet`, us-east-1 spot; every unit went
  through `klt sim --backend batch --wait-for-capacity 600`; no capacity
  refusal occurred and nothing fell back to local). One submit errored
  wholesale (cycle 8, the recovery/ladder decks generated before the
  `cap_cmomi.lib` include fix of §4 — their errored results are dead cache
  entries that no committed number reads; the same decks were re-rendered
  and re-submitted as cycle 9):

  | cycle | decks | result | job id | instance / AMI |
  |---|---|---|---|---|
  | 1 (R extraction) | 9 | pass 9/0 | `klt-sim-a69f8d84a1ae` | m7i.4xlarge |
  | 2 (C extraction) | 6 | pass 6/0 | `klt-sim-df4c68845d59` | m7i.4xlarge |
  | 3 (window control + window rows) | 98 | pass 98/0 | `klt-sim-5bfa26bd8cd5` | c7i.4xlarge, ami-095c25ae241a4d360 |
  | 4 (wholecell + ladder pts) | 89 | 58 pass / 31 errored (unknown-subckt, §4; 1 timestep) | `klt-sim-f32a659a69b8` | c7i.4xlarge |
  | 5 (+ trtol=1 retries) | 191 | 159 pass / 32 errored (§4) | `klt-sim-5440abb4d2c3` | c7i.4xlarge |
  | 7 (fixed wholecell template) | 35 | pass 35/0 | `klt-sim-de0b02db214c` | c7i.4xlarge |
  | 8 (recovery/ladder, pre-fix) | 160 | **0 pass / 160 errored** (§4; superseded by cycle 9) | `klt-sim-3e4d049c83fd` | c7i.4xlarge, ami-09c14f55df4958cbd |
  | 9 (recovery/ladder, fixed) | 160 | pass 160/0 | `klt-sim-c21727166f92` | c7i.4xlarge, ami-09c14f55df4958cbd |

  The committed evidence is the pass-10 reduction: every deck a replay hit;
  nothing pending.

## 2. Controls: the harness reproduces the committed campaign

- **Window control: 101/102 points byte-identical** to the committed
  `window_crowbarfix.csv` via the runner's own
  `ld_window_control_delta.csv` path (`ld_window_control-rerun157.csv`,
  `ld_window_control_delta-rerun157.csv`). The single non-identical row
  (`mos_ff_res_bcs_-40c_3.3v_24p4MHz_ideal0.20`) carries the SAME value to
  every printed digit's worth of precision — committed `5.96879e-09`, this
  host `5.96879e-09`, delta `0.000000e+00` — a last-printed-digit
  formatting difference only (the RECORD-006 pattern), not a measurement
  difference. 102/102 control points therefore reproduce the committed
  crowbarfix campaign numerically, on ngspice-47 and the unattributed
  worker PDK tree.
- **R/C device extraction: 6/15 rows byte-identical** — exactly the 6
  `cap_cmomi` C rows; all 9 `rhigh` R rows differ by the resistor-library
  content drift RECORD-008 already isolated: this run's XRPU `res_typ`/27 C
  is `2.069878e+06` Ω against the committed control's `2.266979e+06` Ω
  (−8.69 % at every temperature — the current-tree value RECORD-011's
  nominal parity check measured on the host-local tree). The R drift is PDK
  content, not design or harness; the committed
  `rc_extract_crowbarfix.csv` remains the R-value evidence for its era.
- The window control's 102-point reproduction is R-independent by
  construction (the bare `delaywin_hv` chain contains no `rhigh`), which is
  why it reproduces byte-identically despite the R drift — the same
  attribution RECORD-011 made for its window rows.

## 3. Results — `pll_lock_detector`, the post-#136 PEX DUT

- **Whole-cell window grid** (`ld_window-rerun157.csv`, 85 rows):
  as-layout twin twin_r 1.787e-10 – 3.554e-10 s (56 rows); post-layout
  twin_r 4.341e-09 – 1.026e-08 s (29 rows). The post-layout-vs-as-layout
  deviation (`ld_deviation-rerun157.csv`, 29 rows) is **+1971 % to
  +2785 %** (median +2356 %) — against RECORD-003's +62.9 % to +68.9 %.
- **Attribution of that 14x move (the record's central finding): the layout
  re-route is NOT what moved the window; the extraction-model generation
  is.** At the SAME tool (klt 0.9.3.dev3), the old GDS (`61a18fc1…`) and
  the current GDS (`54bea524…`) extract nearly identical parasitics —
  155 R / 21925.43 Ω / 3904.09 fF vs 157 R / 21926.19 Ω / 3904.30 fF, the
  device-set delta being the #136 repair itself (`XMPD`'s gate moved off
  the stray net `$28` onto `VWIN`, diffusions 0.1P → 0.115P, nets 25 → 23,
  +2 R, +0.2 fF). The committed RECORD-003-era DUT measured 466 fF
  (klt 0.2.0-era extraction of the c44fa68 GDS); the klt 0.6.0-era
  re-extraction of the SAME a95a887 GDS already carried 3904 fF. So the
  capacitance model grew ~8.4x between klt 0.2.0 and 0.6.0 (net-to-ground
  plus unconditional vertical-overlap coupling — the extracted header's own
  model statement), and the whole-cell window, an edge-rate measurement on
  the ERR/ERRD/VWIN nodes, scales with it. The as-layout twin (no
  parasitics) is unchanged across eras (0.34–0.60 ns was never its number:
  the committed aslayout rows sit at 0.21–0.36 ns in both eras), which is
  what makes the A/B a parasitic effect and not a device change. The
  old-GDS whole-cell window was NOT re-measured at the current tool — the
  R/C identity above is the isolation evidence; measuring the old-GDS
  window itself would be a diagnostic campaign outside this issue's scope.
- **Ladder/recovery** (`ld_ladder-rerun157.csv`, 32 rows;
  `ld_ladder_raw-rerun157.csv`, 288 rows): 16 aslayout + 16 post-layout
  corners, same `hystfix`-era schema and run-length tails as RECORD-003's
  set. Chatter: 26 corners `steady`, 6 `intermediate` (all post-layout:
  `mos_tt_res_typ_125c`, `mos_tt_res_bcs_-40c`, `mos_tt_res_bcs_27c`,
  `mos_tt_res_wcs_125c`, `mos_ff_res_typ_27c` at 3.5 MHz and
  `mos_tt_res_typ_27c` at 3.63 V), **zero `chatter`** — against the
  committed set's 14 steady / 17 chatter / 1 intermediate. The bigger
  extracted window slows the discharge path relative to the window, and the
  ladder states resolve further from the re-trigger boundary; the committed
  set's NA hysteresis cells do not recur (none here).
- **Timestep convergence** (`ld_tstep_convergence-rerun157.csv`): the
  post-layout whole-cell window is converged — 6.48525 / 6.48481 /
  6.48471 ns at tstep 20p / 5p / 1.25p (< 0.01 % spread); aslayout likewise
  (2.640 / 2.621 / 2.620e-10).
- **Solver retry** (`ld_solver_retries-rerun157.txt`, 1 entry):
  `pt_aslayout_mos_tt_res_wcs_-40c_3.3v_24p4MHz` point 8 needed the runner's
  one `trtol=1` retry (timestep failure at node `xa8.xxor.xn2.mid1`); the
  retry passed. RECORD-011's bodyfix grid needed 3 such retries on the
  schematic DUT — same order of magnitude, different DUT and grid.

## 4. Testbench changes this rerun had to make (disclosed)

The runner and both campaign template sets are otherwise used unmodified;
two files in THIS slug gained one line each, because the current extraction
carries devices the templates were written without:

- `testbench/tb_ld_wholecell_win.sp.tmpl` and `testbench/gen_pex_ladder.py`
  now `.include …/models/cap_cmomi.lib` (the sibling campaign's own
  templates always did). RECORD-003's extraction reported **zero**
  `cap_cmomi` devices, so the whole-cell/ladder deck skeletons never
  carried the subckt definition; the current GDS extraction emits three
  `cap_cmomi` cards. Locally the `.spiceinit` `osdi` lines mask the gap
  (ngspice resolves the X-card against the loaded OSDI device), but on the
  batch fleet `pre_osdi` registers inside `.control` — after netlist parse —
  so the card must resolve as a subckt at parse time. Cycle 8's 160-unit
  error is this exact failure (`unknown subckt: … cap_cmomi`); cycle 9
  re-ran the identical decks with the include and passed 160/0.

## 5. What this record does not claim

- Not a spec pass: no `spec/porting-plan.md` row is graded here; row 16's
  ratified window criterion is measured on the schematic campaign's bare
  chain (RECORD-004/011 evidence), not on this slug's whole-cell A/B.
- The `pfd` arm of RECORD-003 is not re-measured; its RECORD-006 migration
  rerun remains the latest pfd evidence.
- The worker PDK revision is unknown (unattributed image); the controls in
  §2 are what tie the run to committed-era capacitor/MOS content, not a
  revision stamp.
- The nominal-only `klt pex` envelope for this block is the signoff slug's
  evidence (its RECORD-004), not this record; the two slugs stay separate
  per their READMEs.
