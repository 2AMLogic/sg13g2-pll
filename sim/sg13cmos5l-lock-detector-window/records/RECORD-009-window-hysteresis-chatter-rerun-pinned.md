# RECORD-009: rerun of RECORD-001's 92-point lock_detector grid via `klt sim` on the batch fleet (issue #327)

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #327 (split from #257, child of #213, Part of #199, item 9 provenance
  migration). Append-only. Reruns the grid behind
  `RECORD-001-window-hysteresis-chatter.md` (sha256
  `ed6fdea23c59985b55e6f82fc320c62939c7a3f075881c1ca9a9c1a48e8714f5`, verified unchanged) and is
  the `ADDENDUM-RERUN` target of `ADDENDUM-004-record-001-superseded.md`. No earlier record or
  committed `corners/` / `netlist-snapshots/` file was edited.
- **What was rerun**: the whole `testbench/run.sh` grid at `db36732`: 15 R/C extractions,
  92 comparator-window decks (one per ladder point), 45 Schmitt decks, 12 tstep-convergence
  decks, 92 phase-error ladder decks (31 DUT copies each).
- **DUT at its producing commit, not today's design**: `lock_detector.spice`, the five
  `tb_*.sp.tmpl`, `gen_ladder.py`, `mom_inject.py` and `run.sh` are taken with
  `git show db36732:<path>` by `../testbench/batch_grid_db36732.py src` (nothing copied into the
  repo). Today's `run.sh`/body-fix DUT is not used.
- **Entry point / deviations, disclosed**: `db36732`'s `run.sh` is a serial local ngspice loop
  and was **not** run. Its grid (matrix, geometry, f_ref 25/5/1 MHz, one ladder deck per
  point) differs from #322's `batch_grid.py` (24.4/12/3.5 MHz, XRPU l=700u, 21 points), so a
  separate driver, `../testbench/batch_grid_db36732.py` + `run_batch_db36732.sh`, holds the
  db36732 matrix and imports `batch_grid.py` for the generic parts (init block, request
  writer, `trtol=1` retry). Decks are `run.sh`'s templates with its substitutions; path-only
  differences: `$PDK` -> `ihp-sg13cmos5l`, `@DUT@` -> sibling file name, and a `.control`
  block with `pre_osdi` x5 + `num_threads=1` in place of `.spiceinit`. Reduction uses
  `db36732`'s own `gen_ladder.py reduce` and run.sh's own parsers. No `trtol=1` retry was
  needed (`solver_retries_rerun327.txt` empty). Outputs: `../corners/*_rerun327.*`.
- **Probe first**: R_res_typ_27 + C_XCW_27 decks, job `klt-sim-1a2d7ff81cdd` (m6i.4xlarge
  Spot, runner klt `0.9.0`, ngspice-46): C = 5.981816e-14 F (identical to RECORD-001), R =
  18059.13 ohm (RECORD-001: 19748.57).
- **Grid command** (three `klt sim --backend batch --wait-for-capacity 600` deck-list calls):

  ```
  WORKDIR=<dir> sim/sg13cmos5l-lock-detector-window/testbench/run_batch_db36732.sh
  ```

  | Phase | Content | Job id | Instance (Spot) | Elapsed |
  |---|---|---|---|---|
  | phase0 | 9 R + 6 C extractions | klt-sim-4eabb71843d1 | c7i.8xlarge | 10 s |
  | phase1 | 92 window + 45 Schmitt + 12 tstep | klt-sim-e3ddde64ce5f | m6i.4xlarge | 39 s |
  | phase2 | 92 ladder decks | klt-sim-b8b42124a998 | m7i.4xlarge | 1727 s |

  All status `pass`, exit 0, no refused submit.
- **Tools**: client `klt 0.9.2.dev661+g1de5c0432aad`; runner klt `0.9.0` (`runner_compatibility:
  match`), ngspice-46, AWS Batch Spot fleet `us-east-1`. Submitted from a `loom-worker` host.
- **PDK revisions (pin, NOT independently verified on the runner)**: PDK ihp-sg13cmos5l revision
  607e18d4bd9214a52575c194b4181ef449f9252f and PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e, the pins in `sim/provenance-migration.md`. The
  runner's PDK stamp was not comparable (see RECORD-007; klayout-tools#5318, #3462). The
  resistor results below show the runner's `ihp-sg13cmos5l` `cornerRES.lib` is **not** the tree
  RECORD-001 ran on: `rhigh` sheet resistance moved after RECORD-005/006 (`testbench/BATCH.md`),
  so the cited pin cannot describe both.

## Results vs RECORD-001

| Output | Result |
|---|---|
| `window` (92 rows), `schmitt` (45), `tstep_convergence` (12) | byte-identical to `corners/*.csv` |
| `rc_extract` C rows (6) | byte-identical (XCW 59.82 fF) |
| `rc_extract` R(XRPU) | **differs**: res_typ -8.6 %, res_bcs -4.4 %, res_wcs -8.1 % (e.g. 27 C typ 18059 vs 19749 ohm), same at all temperatures |
| `ladder` verdicts | 92/92 `chatter`, rail `lo`, hysteresis 0.0 % of window at every point (as RECORD-001); 91/92 assert/de-assert thresholds and state strings identical |
| `ladder` deviation | `mos_tt_res_typ_125c_3.3v_25MHz_ideal0.20`: tau_assert 4.754e-10 s vs 4.206e-10 s (state string `IIIIITTT...` vs `IIIITTTT...`, one ladder step) |
| `ladder` analog columns | lock_min/max_deep within 0.65 % / 0.15 %, idd_outlock within 2.2 %, trec within 9.5 % (median 8.2 %), idd_inlock within 0.006 % (R-driven, not the batch route) |
| Headline window | 0.219-0.409 ns (min/max `twin_r_s`, identical to RECORD-001) |

RECORD-001's conclusions are reproduced at the verdict level: window 6-11x below the 2.5 ns
floor, no resolvable hysteresis, 92/92 chatter. The measured R values differ because of PDK
drift, so the rerun is not byte-comparable to RECORD-001 and is not claimed to be.

## What this does not bound

- The original run's environment (superseded, not recovered); the runner's actual PDK revision.
- The one-ladder-step shift above was not isolated to R drift vs solver noise; no extra runs.
- RECORD-002..007, PEX, the post-body-fix full-PVT grid (#139), local ngspice grids.
- `run.sh`'s per-call run-time trtol retry is replaced by a per-unit resubmit (never triggered).
- No consumer figure was replaced; `characterization/sources.json` only gains a `historical` dataset entry for this rerun (required by `check_records.py`).
- No failed attempts: one probe, three phase jobs, no retries.
