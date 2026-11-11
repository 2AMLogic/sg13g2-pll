# RECORD-002: batch-fleet rerun of RECORD-001's resized lock-detector window, hysteresis and chatter measurement (issue #236)

- **Slug**: `sg13g2-lock-detector-window`
- **Issue**: #236 (execution child of #217, item 9 provenance migration;
  inventory row 36 of `../../provenance-migration.md`). Append-only. This
  record reruns `RECORD-001-resized-window-hysteresis-chatter.md` (sha256
  `9bc950952a2aa07444e24d4d341b52afff17dedf6daaca8b17fcd4707027e8eb`,
  verified unchanged at the Builder base commit `6bab68d`) and is the
  `ADDENDUM-RERUN` target of `ADDENDUM-001-record-001-superseded.md`. It
  edits neither RECORD-001, any snapshot, nor any committed `corners/` file.
- **What was rerun**: the measurement RECORD-001 *reports* — `rc_extract`
  (27 rows), `window` (37), `schmitt` (45), `tstep_convergence` (12),
  `ladder` (21 corners) + `ladder_raw` (483 points) + the recovery/power
  columns, and `hysteresis_diag` (26 points) — at RECORD-001's own matrices
  and scope: `f_ref` 3.5 and 24.4 MHz (plus 12 MHz in the window matrix),
  the sizing variant `w=0.5u l=500u` / `cap_cmim 45u x 45u` / `XMPD
  w=0.25u l=12u`, the 23-point `resized` ladder out to 24x window with the
  20x chatter probe, in-lock and out-of-lock supply current, and solver
  retries.
- **Scope narrowing, stated plainly**: the four *sizing* sweeps that
  *selected* the geometry — `run_rc_sizing.sh` (`rc_sizing.csv`,
  `rc_pairing.csv`, `window_sizing.csv`) and `run_xmpd_sizing.sh`
  (`xmpd_sizing.csv`) — were **not** rerun. RECORD-001's claims about row 16
  are made on the frozen snapshot, which is what is re-measured here; the
  sizing tables remain RECORD-001's evidence for *why* those four numbers,
  grandfathered with it and not re-established by this record. Nothing in the
  rerun's data bears on them. A consumer citing the "narrow-pulse knee" or
  the "two-sided `XMPD` bound" *tables* is citing unreplaced evidence; the
  `hysteresis_diag` rerun below does reproduce the knee's two data points.
- **DUT — the original, not today's design**:
  `../netlist-snapshots/lock_detector_resized.spice` (sha256
  `fc7bcf69b85b387d2f77dd357ac4ff4966f07f82e086481d29e307e0d116afee`),
  byte-identical to the producing commit `40b020e`
  (`git diff 40b020e HEAD -- <snapshot>` empty), as are all seven
  `testbench/tb_*.sp.tmpl` templates. One drift, disclosed:
  `gen_ladder.py` moved verbatim to the shared `sim/tools/gen_lock_ladder.py`
  after `40b020e`; the byte-identical outputs below are the measurement of
  that relocation. Today's `design/netlist/lock_detector.spice` was **not**
  substituted.
- **Testbench**: new file `../testbench/run_batch.py` (the original
  `run.sh` / `run_hysteresis_diag.sh` are untouched). It renders the same
  templates over copies of the same matrices, ships every deck as a
  `klt sim` deck-list request, and reduces with the unchanged
  `gen_lock_ladder.py reduce`. Deck-list requests execute decks verbatim, so
  the snapshot is inlined into each deck in place of `.include` and the OSDI
  objects load through a declared `.spiceinit` input (the same four `osdi`
  lines and `set num_threads=1` that `run.sh` writes). Outputs: new suffix
  `_resized_rerun236` (`hysteresis_diag_resized_rerun236.csv` is the
  rerun of the unsuffixed `hysteresis_diag.csv`).
- **PDK revision**: PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e (upstream `v0.3.0`; the repo pin
  of `sim/README.md`). **Evidence and its limit**: the fleet image carries
  `ihp-sg13g2` at `/opt/pdk/ihp-sg13g2` without a version marker file, so the
  revision is *not* read off the image. What was checked is that seven files
  the decks load — `psp103.osdi` `2e4299c4…`, `psp103_nqs.osdi` `839b1644…`,
  `mosvar.osdi` `25e64a37…`, `r3_cmc.osdi` `4fead17b…`, `cornerMOShv.lib`
  `5a1f862d…`, `cornerRES.lib` `2c185021…`, `cornerCAP.lib` `4fc4a0f1…` —
  hash identically on the fleet image (job `klt-sim-903cfa91445c`) and in
  the `0.3.0` release-tarball tree on the submitting host
  (`.fetched-version` = `0.3.0`, bundle sha256 `b3943b57…`), and that tree is
  the repo's pin per `../../provenance-migration.md`. That ties the loaded
  model cards and OSDI objects to the pin; it does not prove the image's
  *other* files match.
- **Tools**: `ngspice-46` on the fleet (banner from job
  `klt-sim-903cfa91445c`: "ngspice-46 … Creation Date: Thu Oct 1 23:51:59
  UTC 2026"; `engine_version` 46 in every report); runner `klt` 0.9.0 on the
  image (`runner_compatibility: match`), client `klt`
  0.9.2.dev661+g1de5c0432aad; host `Linux x86_64`. Fleet instances varied
  per job (`m7i.4xlarge`, `m6i.4xlarge`, `c7i.8xlarge`, `c6i.8xlarge`; Spot).
  Image `ami-095c25ae241a4d360`, region `us-east-1`.
- **Command** (run on `loom-worker-2`, 2026-11-11; `KLT_SIM_BACKEND=batch`,
  `PDK_ROOT=~/share/pdk`):
  ```
  python3 testbench/run_batch.py stage1 --work W   # 144 decks, one job
  klt sim W/stage1/request/request.json --backend batch --wait-for-capacity 600 -o W/stage1/out --format json
  python3 testbench/run_batch.py stage2 --work W   # 21 ladder + 2 diag requests
  klt sim <each request> --backend batch --wait-for-capacity 600 ...
  python3 testbench/run_batch.py retry --work W    # failed decks only, trtol=1
  python3 testbench/run_batch.py reduce --work W
  ```
- **Host / job ids**: submitted from `loom-worker-2`; every job id, status and
  instance type is in `../corners/batch_rerun236/jobs.tsv` (31 evidence jobs:
  stage 1 `klt-sim-17256b9c02b8`; 23 stage-2 requests; 7 retry requests).
  Per-job reports: `../corners/batch_rerun236/reports.tgz`; raw per-deck
  stdout (first-pass failures included): `stdout.tgz` in the same
  directory. Single-corner probe (required first by the issue, nominal
  `mos_tt/res_typ/cap_typ`, 27 °C, 3.3 V window deck): job
  `klt-sim-1d430fb173e8`, `twin_r` = 6.02712e-09 s, the value RECORD-001
  reports for that corner; repeat `klt-sim-431afe42817c`.
- **Failed submissions — not evidence, listed so they are not mistaken for
  any**: `klt-sim-f03814db1085` (probe 1; PSP models ignored because a
  deck-list request does not apply `options.osdi_preload` — my request
  error, fixed with the `.spiceinit` input); `klt-sim-f63df2eb3cfe` and
  `klt-sim-0dcd5814b07e` (stage 1 with `options.max_workers: 8`; stayed
  `pending` with no status file for 40+ minutes, never started; the identical
  request without that option ran in 26 s); `klt-sim-7360c775281f`
  (ladder corner `mos_tt/res_typ/cap_wcs/27C/3.5MHz`; Spot instance
  `interrupted`, no results; resubmitted as `klt-sim-32dc03c12d56`);
  `klt-sim-360dde875585` (provenance probe 1, ngspice mangled the shell
  quoting). None contributed a number. Tool gaps met are filed upstream:
  `2AMLogic/klayout-tools#5332` (the `max_workers` stall, new),
  `#5317` (`--batch-set` crashes on deck-list requests, so each request was
  submitted as its own `klt sim`), `#5328` (no PDK identity in a deck-list
  report, hence the hash comparison above).
- **Convergence**: 10 of 684 decks exited non-zero on the first pass
  ("Timestep too small"), all ladder points; each was resubmitted once with
  ` trtol=1` appended to the `.options reltol=` line (the edit `run.sh`
  makes) and passed. They are listed in
  `../corners/batch_rerun236/solver_retries.txt` — the same count (10) as
  RECORD-001's `solver_retries_resized.txt`. No point is missing and no cell
  is `NA`.

## Result

Every committed output reproduces RECORD-001's, from fresh runs of the
unmodified DUT on a different host, ngspice build and execution path:

| Rerun output | Original | Rows | Comparison |
|---|---|---|---|
| `rc_extract_resized_rerun236.csv` | `rc_extract_resized.csv` | 27 | byte-identical |
| `window_resized_rerun236.csv` | `window_resized.csv` | 37 | byte-identical |
| `schmitt_resized_rerun236.csv` | `schmitt_resized.csv` | 45 | byte-identical |
| `ladder_resized_rerun236.csv` | `ladder_resized.csv` | 21 | byte-identical |
| `tstep_convergence_resized_rerun236.csv` | `tstep_convergence_resized.csv` | 12 | byte-identical |
| `hysteresis_diag_resized_rerun236.csv` | `hysteresis_diag.csv` | 26 | byte-identical |
| `ladder_raw_resized_rerun236.csv` | `ladder_raw_resized.csv` | 483 | identical except line endings: the original's data rows end CRLF (the `csv` writer in the generator), the rerun's LF; `cmp` after stripping CR is clean |

So RECORD-001's headline — assert window 3.732–10.249 ns (0/37 below 2.5 ns,
worst case 1.493x), `steady` at 21/21 ladder corners at the 20x-window probe,
hysteresis 25–800% of window with 0/21 below 25%, the 25.0% corner resolving
to 43.0% on the fine sweep, `R·C/T_ref` 9.26x worst case, recovery time
2.125–5.194 µs, in-lock 2.44–22.60 µA and out-of-lock 38.3–100.5 µA — is
**re-measured and holds as stated**, at the scope listed above. The
unchanged limitations carry over verbatim: the criterion "assert window ≥ 2×
worst static phase offset" stays `insufficient-evidence` (no PFD/CP
static-phase-offset record exists for this PDK), the fast-end out-of-lock
probe is a saturated-stimulus switching figure, and the 20x probe is not
comparable with RECORD-001's predecessor ladder.

That the files are bit-identical is itself a finding, recorded rather than
assumed benign: it says the result is deterministic across the two hosts and
ngspice builds, and it is also what one would see if the runs failed to
exercise the batch image's own models. The probe argues against the latter:
the first probe attempt, without OSDI loading, failed outright with
"Unknown model type psp103va", so the image's PSP objects are what produced
these numbers.

## Consumers

No figure was replaced: every rerun value equals the original, so no
`characterization/`, `spec/` or summary consumer needed re-pointing, and
none was touched (integration remains #218). Item 9 stays unmet while any
other grandfathered record is unresolved.

## Reproduce

```
cd sim/sg13g2-lock-detector-window
PDK_ROOT=<pdk-root> python3 testbench/run_batch.py stage1 --work <W>
# submit as above, then stage2, retry, reduce
```
