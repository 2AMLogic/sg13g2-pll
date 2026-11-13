# RECORD-007: rerun of RECORD-002's post-DR-006 Icp-input re-derivation on the batch fleet (issue #319)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #319 (split from #214, item 9 provenance migration, Part of #199). Append-only. Reruns the bench of `RECORD-002-icp-input-refresh.md` and is the `ADDENDUM-RERUN` target of `ADDENDUM-002-record-002-superseded.md`. It edits neither the original nor its CSVs; new data is `../corners/results_icp_refresh_rerun319.csv`, `../corners/mom_band_icp_refresh_rerun319.csv`, `../corners/proposal_icp_refresh_rerun319.csv` and `../corners/crosscheck_icp_refresh_rerun319.txt`.
- **DUT**: the historical DUT of commit `f54b9ef`, not today's design. Structurally identical to `RECORD-006`'s (the same as-drawn `loop_filter` snapshot, the same templates and matrix): the original was a *mechanical re-derivation* after DR-006 changed one measured **input**, so the only thing that differs is the `Icp` table it consumes — `sg13cmos5l-cp-icp-trim/corners/results.csv` **as of `f54b9ef`** (the post-DR-006 cascode-bias-replica measurement), against `RECORD-006`'s `b37918d` table.
- **Corner coverage**: the original's full matrix, unchanged — Part A **90 real-subckt rows** (3 PVT bundles x 2 band codes x 2 `Kvco` intervals x admissible `f_ref`/`N` x 6 trim codes), Part A' the 2-deck cross-check, Part B **54 rows**, Part C **108 rows**; 254 decks total. Supply is not swept, as in the original.
- **Not rerun**: the upstream `sg13cmos5l-cp-icp-trim` measurement that produced the refreshed `Icp` table is this bench's *input*, not its DUT; replacing it is #231's scope, not this record's. This record consumes it exactly as the original did.
- **Tool / host**: `klt sim --backend batch --wait-for-capacity 600` (client `klt 0.9.2.dev915+g513f88f6836d`, runner klt 0.9.0) on the Spot batch fleet; **ngspice-47** (`/usr/local/bin/ngspice` on the runner). Submitted from `loom-worker-4`. The original states "ngspice-46, x86-64 Linux" and no host, so neither host nor engine build is reproduced.
- **Batch jobs**: single-deck probe `klt-sim-db5a6d5ee4ae` (shared with `RECORD-006`; exit 0), then the grid `klt-sim-f17f617026e2` (254 decks, exit 0, 254/254 pass). No local grid was run.
- **Command**: as in `RECORD-006-loop-bandwidth-pm-rerun-batch.md` — the three snapshots were rendered by one `gen_rerun319.py render` and submitted in one `klt sim --batch-set` invocation.
- **PDK revisions (limitation, read first)**: identical to `RECORD-006-loop-bandwidth-pm-rerun-batch.md`'s, and subject to the same limitation — the runner exposes no stamp (`pdk stamp unreadable`, `not_comparable`), so the cmos5l tree is **inferred** as the fleet bundle, store version `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14` (bundle sha256 `3195ba7f3a74e91fc4eced64102c9d61b00d8eadcf5e795d36d926d40ab4ad31`), **not** the legacy commit `PDK-PIN` in `sim/README.md` still names (re-stamp is #250, out of scope). The ihp-sg13g2 tree is a release install, `.fetched-version` `0.3.0`, i.e.
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e as established in `sim/provenance-migration.md` (version marker, not a `git rev-parse`).
- **Rebuilt harness**: `testbench/gen_rerun319.py` executes `f54b9ef`'s own `run.sh` Python verbatim with only `run_ac()`'s body replaced; matrix, `crossover()` and CSV writers are the historical ones. Decks differ only in `pre_osdi` inside `.control` instead of a `.spiceinit`, and in the PDK path being the runner's `$PDK_ROOT`.

## Result vs the original

| Metric (Part A, real subckt) | Original (`f54b9ef`) | Rerun |
|---|---|---|
| Rows | 90 | 90 |
| `f_c` range | 0.3307 - 4.6356 MHz | 0.3307 - 4.6341 MHz |
| PM range | 1.545 - 20.345 deg | 1.547 - 20.523 deg |
| Rows meeting PM >= 45 deg | **0 of 90** | **0 of 90** |
| Verdict flips (`meets_ceiling`, `meets_pm45`) | — | **0 of 90** |

Per-row maximum difference: `f_c` **0.068 %**, PM **0.178 deg**. Part B (`mom_band`, 54 rows) and Part C (`proposal`, 108 rows) are **byte-identical** to the original, including the same 18-row `meets_both` set. Cross-check at the nominal point: real subckt `f_c` 952.4408 kHz / PM 4.265 deg original vs **952.4453 kHz / 4.272 deg** rerun; lumped arm bit-identical at 965.5761 kHz / 4.316 deg.

### The original's own claim, re-tested

`RECORD-002-icp-input-refresh.md`'s claim is a *differential* one: refreshing `Icp` moves every output by well under 1 % and flips no verdict. Running `RECORD-006`'s `b37918d` arm and this `f54b9ef` arm through the **same** fleet, engine and PDK isolates that input change from everything else, and reproduces it:

| Output | Rows | Max d `icp_a` | Max d `fc_hz` | Max d `pm_deg` | Verdict flips |
|---|---|---|---|---|---|
| `results` (rerun `b37918d` -> rerun `f54b9ef`) | 90 | 0.782 % | 0.392 % | 0.431 % | **0** |

against the original’s own 0.782 % / 0.392 % / 0.428 % — the same `icp_a` and `fc_hz` figures, and 0.431 % against 0.428 % on `pm_deg`. Both of `RECORD-001`'s findings, restated by the original with refreshed numbers, hold here too: **0 of 90** rows close the loop with the as-drawn filter, and the `R1` x20 / 10 uA pair is still the widest-margin proposal pair.

### Why the real-subckt half moves and the lumped half does not

Parts B and C read no PDK file (ideal `R`/`C` from the input CSVs) and reproduce byte-identically on ngspice-47; only the real `rppd`/`cap_cmomi` decks move, by <= 0.068 % / <= 0.178 deg. The difference is `cornerRES.lib` content, not the engine build, the batch transport or the harness — the same conclusion `RECORD-006-loop-bandwidth-pm-rerun-batch.md` reaches, and consistent with `sg13cmos5l-loop-filter-momcap` RECORD-003's independently measured R1 shift.

## What this does not bound

Everything the original did not — it adds no new measurement beyond a refreshed evaluation of the same model against one changed input, and inherits `RECORD-001`'s whole "What this does not bound" list. It does not restore the original run's host or PDK provenance (ngspice-47 here against the stated ngspice-46; a fleet Spot instance rather than the original's unnamed worker; cmos5l revision inferred, not read).
