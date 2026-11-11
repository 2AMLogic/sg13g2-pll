# RECORD-006: rerun of RECORD-002's `$PDK_ROOT` token-fix re-verification on the batch fleet (issue #232)

- **Slug**: `sg13cmos5l-divider-nrange-retiming`
- **Issue**: #232 (Part of #212 / #199, item 9 provenance migration).
  Append-only. This record reruns the *measurements* RECORD-002 reported and
  is the `ADDENDUM-RERUN` target of
  `ADDENDUM-003-pdk-root-token-fix-superseded.md`. It neither edits
  `RECORD-002-pdk-root-token-fix-reverification.md` nor any historical CSV. It
  supersedes only that record's *evidence claim* for the measurements below.
  RECORD-002's harness fix itself (the `@PDK_ROOT@`/`@PDK@` substitution and the
  `runsp` wrappers) is a change to `run.sh`, which is not rerun here; the batch
  requests carry resolved model paths, so the token bug cannot occur and this
  record says nothing about that fix.
- **Tool**: ngspice-46 via `klt sim --backend batch` (client
  `klt 0.9.2.dev661+g1de5c0432aad`, runner `klt 0.9.0`). RECORD-002 used
  `ngspice-46` on an unnamed, CPU-contended Linux worker.
- **Scope and backend**: every measurement below ran on the Spot batch
  fleet through `klt sim --backend batch --wait-for-capacity 600` (single
  requests or `--batch-set`), never as a hand-launched local grid. One
  nominal-corner probe (`hold_fbfix`, job `klt-sim-747f443dfa8e`, before the
  grids) confirmed the route first. Workers: AWS spot `m6i/m7i/c7i` instances,
  runner `klt 0.9.0` (client `klt 0.9.2.dev661+g1de5c0432aad`,
  `runner_compatibility: match`), `ngspice-46` (`/usr/local/bin/ngspice`,
  sha256 `dc859418bedd0478ff439a2d3e2e09f4386a7f4d5e3f17671953e101a000cc60`),
  x86-64 Linux. Job ids are in the table under "Jobs". One request
  (`retime_asdrawn`) was refused once with `batch_no_capacity` after its 600 s
  wait budget and was resubmitted unchanged; it is the only retry.
- **PDK trees** (read 2026-11-11 from the dispatching host and from the
  worker's reported model inputs): `ihp-sg13g2` tree is upstream `v0.3.0`
  (`.fetched-version` = `0.3.0`, store key `pdk/ihp-sg13g2/0.3.0`), i.e.
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e as
  established in `sim/provenance-migration.md`. The `ihp-sg13cmos5l` tree on
  the dispatching host is the unified-repository install pin of
  `sim/README.md` "Cold start" step 1: `.pdk-store.json` version
  `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14` (an `IHP-Open-PDK` commit), NOT
  the legacy split-repository commit that `PDK-PIN` in `sim/README.md` still
  names. The host tree is not a git checkout, so that revision is the store
  version, not a `git rev-parse`. The batch worker reported its PDK as image
  `/opt/pdk` with no stamp (`pdk.stamp_*` null), so the worker's tree
  revision is **not independently established**; the run reads these model
  files, whose sha256 the worker reported and which equal the dispatching
  host's files: `psp103.osdi` `dba873bcef3f1978b30d66a4dcb661f79c6f6386c29da8841712d84399e13f1a`,
  `psp103_nqs.osdi` `ad99ea641e0b88b29125a786e77f3dcb3b206b5e116e23c2a265783658e69754`,
  `mosvar.osdi` `cded61b14fbe50f74453e995a00f4876664328fd477badf672e5b2405cae5973`,
  `cornerMOShv.lib` source `5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a`.
  The cmos5l tree reads those models through symlinks into the sg13g2 tree.
  **Pin discrepancy, stated rather than hidden**: the legacy `PDK-PIN`
  (`607e18d4...`) is not the revision this rerun used; the repository's own
  switch of that pin is owned by #213-#218 (`sim/README.md`, install note).

## Reconstruction

The DUT, decks, requests, jobs and CSVs are shared with
`RECORD-005-nrange-retiming-margin-rerun-pinned.md` (same `1d824d3`/`b8a14c8`
snapshot, which is byte-identical; see its "Reconstruction" and "Jobs"
sections, which are not repeated). RECORD-002 ran the then-current
`../testbench/run.sh` at `b8a14c8`; the decks are the same templates, ported
to `klt sim` requests as described there. The rows below are the subset of
those jobs that answer RECORD-002's claims.

## Coverage

| RECORD-002 claim | Rerun |
|---|---|
| `opconv` corrected: as-drawn still fails at 150 s (`gmin stepping failed`); `fbfix` converges | 4 rows rerun |
| `hold`: full 18 rows byte-identical to RECORD-001 | 18 rows rerun |
| `retime`: 18-row campaign (all-`NA` for as-drawn; `fbfix` `NA` under load); isolated `fbfix` nominal run converged in about 100 s with `tdiv` 1.077436e-07, `tfb` 1.086840e-07, `dvo_max` 3.601253, `fb_max` 3.424144, `idd` -1.3076e-03 | nominal corner of both variants only |
| `setup`, `func` not rerun by RECORD-002 | not applicable (see RECORD-005 for their rerun) |
| the `PRE-fix` / `POST-fix` `.lib` demonstration | not rerun (not a measurement; applies to `run.sh`) |

## Results

- **`opconv`** (`../corners/rerun232-opconv.csv`): `fbfix` converges at both
  `.ic` settings (`v(divout)` 3.30000 V, no solver warning): **reproduced**.
  As-drawn does **not** reproduce RECORD-002's "still times out at 150 s": it
  converged in 4-5 s to `v(divout)` = 1.84696 V after the warning
  `Dynamic gmin stepping failed`, at both settings. That warning is the
  message RECORD-002 attributes to as-drawn (`gmin stepping failed`), so the
  diagnostic text matches while the outcome does not. No cause is established.
- **`hold`** (`../corners/rerun232-hold.csv`, 18 rows): all 18 rows agree with
  RECORD-001's committed `hold.csv` to the original's printed precision (as-drawn
  `mos_tt` 1.53085 V, `fbfix` 3.30000 V), which is RECORD-002's reproducibility
  claim: **reproduced**. `t_decay` is `NA`, graded by `klt` as a measurement
  `error` (see RECORD-005).
- **`retime`, `fbfix` nominal** (`../corners/rerun232-retime.csv`): `tdiv`
  1.07744e-07, `tfb` 1.08684e-07, `dvo_max` 3.60125, `fb_max` 3.42414, `idd`
  -1.3076e-03: **reproduced** against RECORD-002's isolated-host figures to 6
  significant figures (`tdiv` 1.077436e-07 vs 1.07744e-07; `fb_max` 3.424144 vs
  3.42414; `idd` -1.3076e-03 vs -1.3076e-03). It ran in 66 s on the batch
  worker with no timeout, in line with RECORD-002's "isolated, about 100 s" and
  unlike its contended-campaign `NA`. RECORD-002 deliberately computed no numeric
  margin from these and neither does this record.
- **`retime`, as-drawn nominal**: RECORD-002 reports all-`NA` for as-drawn.
  The rerun returns `tdiv` 5.765e-09 and `tfb` 3.946e-09 (below the 41 ns
  earliest possible divide-by-64 edge, so not a genuine edge), `dvo_max` 1.752
  V. **Not reproduced as `NA`.**

## Limitations retained

- RECORD-002 ran 18 `retime` rows; only the 2 nominal rows are rerun. The other
  16 stay unsupported by new evidence.
- RECORD-002's CPU-contention observation is a property of its host and is not
  reproduced or tested here; the batch workers run one unit at a time.
- The worker's PDK tree revision is not stamped (see the environment section).
- The original host was not named and no log exists; nothing here proves the
  original's environment.
- Ported harness, not the historical `run.sh` (see RECORD-005).
