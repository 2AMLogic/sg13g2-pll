# RECORD-011: full-grid rerun of the `XRPU`-bulk-on-`VSS` DUT on the batch fleet, compared with RECORD-004 (issue #139)

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #139 (Part of #16; #16 stays open, this record does not declare
  the phase complete). Append-only. Closes the "full grid owed" item of
  `RECORD-005-rpu-body-on-vss.md` for everything the batch driver runs, with
  the two disclosed gaps below (20x probe not run; PDK-confounded ladder).
  Nothing in RECORD-001..008, ADDENDUM-001..003, the snapshots or any
  committed CSV was edited (`git diff --stat` shows additions only).
- **DUT**: `../netlist-snapshots/lock_detector_bodyfix.spice`, sha256
  `3fa570b22d3bbdb7f91092048dc6961cee4412646352d6474952da06b34abbe1`
  (frozen input). Source commit of the run: `6698ee3`.
- **Command** (no local `ngspice`; every unit went through
  `klt sim --backend batch --wait-for-capacity 600` inside `run_batch.sh`,
  `WAIT_FOR_CAPACITY` default 600, `NOMINAL_ONLY` unset):

  ```
  WORKDIR=/tmp/lockdet-batch-139 sim/sg13cmos5l-lock-detector-window/testbench/run_batch.sh
  python3 -I sim/sg13cmos5l-lock-detector-window/testbench/compare_bodyfix_batch.py
  ```

  No capacity refusal occurred; nothing fell back to local.
- **Fleet jobs** (all `aws-batch-fleet`, us-east-1, spot, ami
  `ami-095c25ae241a4d360`, ngspice-46, runner `klt 0.9.0`, client
  `klt 0.9.2.dev661+g1de5c0432aad`, `runner_compatibility: match`):

  | Phase | Job id (`environment.remote.job_id`) | Instance | Result |
  |---|---|---|---|
  | phase0 (R/C extraction, 15 decks) | `klt-sim-4cd2688193ce` | m7i.4xlarge | pass, 7 s |
  | phase1 (window, Schmitt, tstep, 159 decks) | `klt-sim-b42084f0bd7f` | m7i.4xlarge | pass, 34 s |
  | phase2 (ladder recovery + points, 462 decks) | `klt-sim-c47978accdd4` | m7i.4xlarge | exit 4: **3 units errored**, 2229 s |
  | phase2 retry, `trtol=1` (3 decks) | `klt-sim-91d00c2cba7d` | m6i.4xlarge | pass, 78 s |

  Reports: `../corners/bodyfix_batch_reports/report_*.json`. The fleet
  completed the full grid in this session (observed, not inferred).
- **Solver retries (disclosed)**: 3 ladder-point units needed `trtol=1`
  (`../corners/solver_retries_bodyfix_batch.txt`): `mos_ff_res_wcs_-40c_3.3v_24p4MHz_real`
  `pt05`, and `mos_tt_res_wcs_-40c_3.3v_3p5MHz_real` `pt14`, `pt15`. Retry
  granularity is the unit, not the ngspice call as in `run.sh`
  (`../testbench/BATCH.md`). RECORD-004's own retry list is
  `../corners/solver_retries.txt`; it is not claimed to be the same set.
- **Artifacts** (all non-empty, headers identical to RECORD-004's):
  `window` 102 rows, `schmitt` 45, `tstep_convergence` 12, `rc_extract` 15,
  `ladder` 21, `ladder_raw` 441 (`../corners/*_bodyfix_batch.csv`), plus the
  full comparison output `../corners/compare_bodyfix_batch_vs_crowbarfix.txt`.
- **PDK revisions (this is the confound)**:
  - `sim/README.md` pins: `ihp-sg13cmos5l` `607e18d4bd9214a52575c194b4181ef449f9252f`,
    `ihp-sg13g2` `5cccb161f7492697cfa52eb14dc03beb00bdca9e`. RECORD-004's
    outputs were produced on that pre-2026-10-15 tree.
  - The tree on the submitting host (`~/share/pdk/ihp-sg13cmos5l`, store
    `.pdk-store.json`) is `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14`
    (bundle sha256 `3195ba7f...`, synced 2026-10-15), **not** the pin.
    `cornerRES.lib` sha256 differs: current `c6d749e7...`, pinned
    `2c185021...`. The fleet worker reports the PDK root as unknown (it
    attests staged files, not a revision), so **this run's ran-on revision
    is inferred as `f7bca326`** from the nominal parity check in
    `../testbench/BATCH.md` (host-local current-tree deck = fleet value
    2.069878 MOhm; pinned tree = 2.266979 MOhm), not independently attested.
    The ran-on revision is therefore not the pinned one.

## Comparison with RECORD-004's `*_crowbarfix` outputs

Keyed join (`../testbench/compare_bodyfix_batch.py`), unchanged thresholds and
corner matrices. Every row is accounted for on both sides: **0 missing, 0
extra rows, headers identical** in all six files. Duplicate keys: `window` has
two keys that appear twice (`mos_ff_res_bcs_-40c_3.3v_24p4MHz_real` and
`..._ideal-0.20`), **identically on both sides**, joined by occurrence index.

| File | Rows | Exact rows | Changed rows (cells) | Class |
|---|---|---|---|---|
| `window` | 102 | 101 | 1 (1) | R-independent |
| `schmitt` | 45 | 44 | 1 (3) | R-independent |
| `tstep_convergence` | 12 | 12 | 0 | R-independent |
| `rc_extract` C rows | 6 | 6 | 0 | R-independent |
| `rc_extract` R(XRPU) rows | 9 | 0 | 9 (9) | **PDK card** |
| `ladder` | 21 | 0 | 21 (270) | R-dependent |
| `ladder_raw` | 441 | 0 | 441 (3626) | R-dependent |

- **R-independent rows (the evidence about the DUT change)**: 163 of 165
  rows are string-identical to RECORD-004; the other two differ in the last
  printed digit only: `window` `mos_ff_res_bcs_-40c_3.3v_24p4MHz_ideal0.20`
  `twin_f_s` 5.39166e-09 -> 5.39165e-09, and `schmitt` `mos_fs`/27 C/2.97 V
  `vth_falling_v` 0.995550 -> 0.995551 (with its derived hysteresis columns
  moving by 1 LSB). These are solver-noise-level, not deviations of
  substance. Bulk of `XRPU` does not enter these decks, as RECORD-005 argued;
  here it is measured over the full matrix.
- **`rc_extract` R(XRPU)**: all 9 values drop, -4.470 % (`res_bcs`),
  -8.694 % (`res_typ`), -8.234 % (`res_wcs`), uniform across temperature.
  This is the PDK `rhigh` card change, not the DUT (the extraction deck is a
  bare device with no DUT in it; `BATCH.md` reproduces the same value on the
  host with the current tree and RECORD-005's value with the pinned tree).
- **Ladder rows**: every one of 21 corners changes, because `rc_s` is
  0.913-0.955 x RECORD-004's (the R shift) and the ladder's timing scales
  with R*C. Columns changed: `rc_s`, `rc_over_tref`, `trec_s`, `idd_*`,
  `vwin_*`, `lock_*` at 21/21; `settle_frac` 17, `n_cycles` 15,
  `hysteresis_s`/`hysteresis_pct_of_window` 10, `tau_deassert_*` 7,
  `tau_assert_*` 3. Largest single move:
  `mos_ff_res_typ_27c_3.3v_3p5MHz_real` hysteresis 300 % -> 500 % of window,
  `tau_deassert` 8x -> 10x window, `idd_outlock` +10.7 %. **These deviations
  are explained by the R shift and are not attributed to the bodyfix DUT; a
  DUT-only attribution for them is not claimed.** Separating the two needs
  RECORD-004's grid rerun on the current PDK (the same-PDK control, owned by
  #257), which was not run here.

## Spec-row dispositions

Thresholds unchanged (row 16: assert window >= 2.5 ns, hysteresis >= 25 % of
window, no chatter; row 11: `lock_detector` domain current).

| Criterion | RECORD-004 | This run (PDK `f7bca326`, inferred) | Disposition |
|---|---|---|---|
| Row 16 assert window >= 2.5 ns | 3.687 ns min, 0/102 below | 3.687 ns min, 0/102 below (R-independent, 101/102 exact) | **met; unaffected by the DUT change** (strong evidence: identical rows) |
| Row 16 hysteresis >= 25 % of window | 50-800 %, 0/21 below | 50-800 %, 0/21 below | **met on this PDK. PDK-confounded**: 10/21 corners moved for R reasons; not a DUT-only attribution |
| Row 16 no chatter | `steady` 21/21 | `steady` 21/21 | **met on this PDK. PDK-confounded**, same caveat |
| Row 16 window >= 2x worst static phase offset | `insufficient-evidence` | unchanged | unchanged |
| Row 11 in-lock `idd_inlock` | 2.48-24.20 uA | 2.49-23.05 uA | measured on this PDK; PDK-confounded |
| Row 11 out-of-lock, 10x probe | 44.56-112.90 uA | 47.58-115.96 uA (peak +2.7 %) | measured on this PDK; PDK-confounded |
| Row 11 out-of-lock, **20x probe** | 40.75-103.29 uA (21 corners) | **not run** (see below) | **owed**: RECORD-004's figure stands unreplicated |

Plain reading: the DUT change itself shows **no effect** wherever it can be
isolated (all R-independent rows). The ladder-derived criteria hold on the
current PDK, but this run cannot say they hold for the DUT change alone, so
neither row 16 nor row 11 is stamped passed on the strength of the ladder.
No threshold, matrix or spec row was relaxed.

## Not covered

- **The 20x-window `idd_outlock` probe** (`TAUBIG_XWIN=20` in `run.sh`) is
  not run by `run_batch.sh`; its deck sets the probe at 10x (`batch_grid.py`
  line 382). The batch driver (#322) would need a 20x mode; that is
  driver work, outside this issue. Row 11's 20x bound is still RECORD-004's.
- **The same-PDK control** (RECORD-004's grid on `f7bca326`) is #257's scope.
- Out-of-band: the fleet run itself is recorded above (job ids); no human
  `loom:ac-verified` stamp is added by this record.
