# RECORD-004: rerun of RECORD-003's `divider_chain` repair re-verification on the batch fleet, pinned PDK (issue #233)

- **Slug**: `sg13cmos5l-divider-nrange-retiming`
- **Issue**: #233 (child of #212, Part of #199, item 9 provenance
  migration). Append-only. This record reruns
  `RECORD-003-divider-repair-reverification.md` (sha256
  `5812315e4dfd1f466bf4774cced691aa8f8d9b5dc23cf8c5fc2ed7072c9458a4`,
  verified unchanged) and is the `ADDENDUM-RERUN` target of
  `ADDENDUM-001-record-003-superseded.md`. It does not edit RECORD-001,
  RECORD-002, RECORD-003 or any committed `corners/*.csv`. RECORD-001 and
  RECORD-002 (the broken as-committed DUT) are **not** rerun and stay
  grandfathered; they belong to no part of this issue.
- **What was rerun**: all five RECORD-003 stages with RECORD-003's own
  matrices — `opconv` (2 rows), `hold` (9 PVT corners), `setup` (3 speed-bracket
  corners × 10 `TSU`), `func` (9 PVT baselines at `N = 64`, 9 programming
  words at nominal, `N = 127` at the two speed brackets, and the 6-row
  `reltol` cross-check) and `retime` (9 PVT corners). 76 decks in total, plus
  one probe deck and one worker-provenance deck (below).
- **DUT — the original, not today's design**:
  `../netlist-snapshots/divider_chain_repaired.spice` (sha256
  `d7f864889ab9fcfbce591bb64acbc3191a1bf781b280851d6a2ce1fdca6f4cfb`) is
  byte-identical to the same path at `a95a887`, the commit that added
  RECORD-003 (`git diff a95a887 HEAD -- <snapshot>` is empty). No
  reconstruction was needed: the frozen snapshot RECORD-003 measured is the
  one in the tree, so the rerun measured the original DUT bytes.
- **Testbench — new files only, disclosed**: `run.sh` is unchanged and still
  ngspice-local, which dispatch hosts must not use for grids. The rerun is
  `../testbench/gen_rerun233_requests.py`, which renders the **same four
  templates** with **the same matrices, word list, time/step arithmetic and
  `.ic` symmetry break** as `run.sh` into 76 pre-composed decks under
  `../testbench/rerun233/decks/` and five `decks[]` requests
  (`../testbench/{opconv,hold,setup,func,retime}.request.json`).
  `../testbench/collect_rerun233.py` applies `run.sh`'s own extractor and
  column layout to each unit's `stdout.bin` and writes
  `../corners/rerun-*.csv`. Deliberate differences from `run.sh`, none of
  which changes a circuit quantity: (1) PDK paths are `$PDK_ROOT/...` (the
  runner's tree) instead of the host path; (2) `pre_osdi` lines sit in each
  deck's `.control` block instead of a `.spiceinit` (ngspice hoists
  `pre_` commands before circuit parse); (3) the per-deck timeout is 1800 s
  (`opconv`/`hold`/`setup`) or 7200 s (`func`/`retime`) instead of
  `run.sh`'s 150 s default; (4) no `RESUME=1` — each stage ran once, whole.
  The rendered decks were not diffed against decks produced by `run.sh`
  (running it would mean a local ngspice grid); their equivalence is
  supported by the measured results matching RECORD-003 (below), not by a
  byte comparison.
- **PDK**: PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  and PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e are
  the pins of `sim/provenance-migration.md`. **What was and was not
  observed on the fleet worker**: the worker's tree is `/opt/pdk` with no git
  metadata, no `.fetched-version` and no `SOURCES`, so its own revision could
  **not** be read (`../corners/rerun-worker-probe.txt`, produced by
  `../testbench/rerun233/worker_probe.sp`, job `klt-sim-e305836c8388`).
  What was observed: the sha256 of the three OSDI objects the DUT loads
  (`psp103` `dba873bc…`, `psp103_nqs` `ad99ea64…`, `mosvar` `cded61b1…`) and
  of `cornerMOShv.lib` (`5a1f862d…`) on the worker equal, byte for byte,
  those in the pinned host trees (`~/share/pdk/ihp-sg13cmos5l`, clean checkout
  at 607e18d4; OSDI objects are symlinked from the `ihp-sg13g2` tree at
  `5cccb161`). The revision claim here is therefore "the files executed are
  byte-identical to the pinned trees' files", not "the worker reports that
  revision". The other model files in the tree were not hashed.
- **Tools**: ngspice-46 on the worker (banner from the probe job;
  `engine_version` `46` in all five reports), `klt` runner 0.9.0, submitting
  client klt 0.9.2.dev661. Worker CPU `Intel(R) Xeon(R) Platinum 8488C`.
  The submitting host's own ngspice was not used for any result.
- **Host and commands** (submitted 2026-11-11 from `loom-worker-2`, all
  `--backend batch --wait-for-capacity 600`, `ihp-sg13cmos5l` image,
  AMI `ami-095c25ae241a4d360`, Spot):

  | Stage | Command | Batch job | Instance | Units |
  |---|---|---|---|---|
  | probe (1 hold deck) | `klt sim probe.request.json …` | `klt-sim-d31896d51311` | m7i.4xlarge | 1/1 pass |
  | `opconv` | `klt sim opconv.request.json …` | `klt-sim-a78e8e3b623f` | m6i.4xlarge | 2/2 pass |
  | `hold` | `klt sim hold.request.json …` | `klt-sim-83c2aa507d64` | m6i.4xlarge | 9/9 pass |
  | `setup` | `klt sim setup.request.json …` | `klt-sim-83279cacd753` | m7i.4xlarge | 30/30 pass |
  | `func` | `klt sim func.request.json …` | `klt-sim-54b56d42f020` | c7i.8xlarge | 24/26 pass, 2 expected errors |
  | `retime` | `klt sim retime.request.json …` | `klt-sim-c38ff179299b` | c7i.8xlarge | 9/9 pass |

  Per-unit status, duration and deck sha256:
  `../corners/rerun-batch-provenance.json`. The first `hold` submit
  (`klt-sim-990e315a74be`) was refused with `batch_no_capacity` after the
  600 s wait (fleet vCPU budget exhausted by concurrent sweeps) and was
  resubmitted unchanged; nothing ran locally.
  `klt sim --batch-set` could not carry the five requests: it crashes on
  `decks[]` members (`KeyError: 'netlist'`), filed upstream as
  `2AMLogic/klayout-tools#5317`, so each stage was submitted on its own.

## Result: RECORD-003's claims reproduce, within last-digit print noise

Comparison of `corners/rerun-*.csv` with the committed originals
(same row keys, 1:1):

| File | Rows | Fields byte-identical | Worst relative difference |
|---|---|---|---|
| `opconv` | 2 | 4/4 | 0 |
| `hold` | 9 | 27/27 | 0 |
| `setup` | 30 | 24/30 | 4.5e-6 (in a ~mV off-state sample) |
| `func` | 20 | 379/420 | 2.3e-5 |
| `tol_convergence` | 6 | 116/126 | 3.1e-5 |
| `retime` | 9 | 70/81 | 3.9e-5 |

Every difference is in the last printed digit of an analog quantity
(`ck*_min`, `fb_min`, `idd`, off-state `q_sample`), consistent with a
different ngspice build and CPU than the original run. **No logic outcome
differs.**

- **Divide ratio**: 20/20 `func` rows measure the exact commanded `N`
  (`tdiv_b − tdiv_a` over `tck_b − tck_a`, 3 decimals): `N = 64` at all
  9 PVT corners, `N` = 65, 66, 68, 72, 80, 95, 96, 106, 127 at nominal, and
  `N = 127` at `mos_ss/125C` and `mos_ff/-40C`. Same values as RECORD-003.
- **Hold**: 9/9 corners hold at the rail (`q_end` = `s_end` = the corner's
  own `VDD`); `t_decay` does not fire (`NA`), as originally.
- **`opconv`**: `.op` converges with and without the `.ic` symmetry break,
  as originally.
- **Supply current**: baseline `idd` −199.3 … −256.8 µA across the 9 corners
  (the same range as RECORD-003).
- **Setup @ 1562 MHz**: crossover is in (500, 700] ps at `mos_tt/27C` — the
  rail at ≥700 ps, off-state at ≤500 ps — and `mos_ff/-40C`, and in
  (1000, 1500] ps at `mos_ss/125C`, unchanged.
- **Retiming**: 7/9 corners resolve; `mos_ss/27C` and `mos_tt/125C` still
  do not complete a clean rail-to-rail `tdiv`/`tfb` (`NA`), the same two
  as RECORD-003. The one-period-late (`k+2`) capture structure RECORD-003
  inferred is therefore reproduced, not newly established.
- **Failures and limitations retained** (not hidden):
  - Both `reltol = 5e-3` arms of the tolerance cross-check ended with ngspice
    exit 1 (`klt` unit status `error`, durations 34 s and 6 s), the
    collapse RECORD-003 Finding 2 records as the reason the campaign runs at
    `1e-3`. They are kept as the same `NA` data rows.
  - The reduced 9-point PVT matrix, the 3-corner `setup` matrix and the
    20-point `func` subset are RECORD-003's own and are **not** widened: 44 of
    the 64 division integers are still not individually simulated; mixed
    process/temperature/supply cross-products stay unswept.
  - This reruns the **repaired** DUT at the original numbers; it makes no
    claim about the present `design/` netlist.
- **Consumers**: no figure changed, so no consumer (`sum`, `src`, `prop`,
  `spec`, `characterization/`) was re-pointed. #217, which consumes
  RECORD-003's numbers, is unaffected: nothing it transfers changed.
