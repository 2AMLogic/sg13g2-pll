# RECORD-007: rerun of RECORD-002's post-DR-006 Icp-input re-derivation on the batch fleet (issue #319)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #319 (split from #214, item 9 provenance migration, Part of #199). Append-only. Reruns the bench of `RECORD-002-icp-input-refresh.md` and is the `ADDENDUM-RERUN` target of `ADDENDUM-002-record-002-superseded.md`. It edits neither the original nor its CSVs; new data is `../corners/results_icp_refresh_rerun319.csv`, `../corners/mom_band_icp_refresh_rerun319.csv`, `../corners/proposal_icp_refresh_rerun319.csv` and `../corners/crosscheck_icp_refresh_rerun319.txt`.
- **DUT**: the historical DUT of commit `f54b9ef`, not today's design. Structurally identical to `RECORD-006`'s (the same as-drawn `loop_filter` snapshot, the same templates and matrix): the original was a *mechanical re-derivation* after DR-006 changed one measured **input**, so the only thing that differs is the `Icp` table it consumes — `sg13cmos5l-cp-icp-trim/corners/results.csv` **as of `f54b9ef`** (the post-DR-006 cascode-bias-replica measurement), against `RECORD-006`'s `b37918d` table.
- **Corner coverage**: the original's full matrix, unchanged — Part A **90 real-subckt rows** (3 PVT bundles x 2 band codes x 2 `Kvco` intervals x admissible `f_ref`/`N` x 6 trim codes), Part A' the 2-deck cross-check, Part B **54 rows**, Part C **108 rows**; 254 decks total. Supply is not swept, as in the original.
- **Not rerun**: the upstream `sg13cmos5l-cp-icp-trim` measurement that produced the refreshed `Icp` table is this bench's *input*, not its DUT; replacing it is #231's scope, not this record's. This record consumes it exactly as the original did.
- **Tool / host**: `klt sim --backend batch --wait-for-capacity 600` (client `klt 0.9.3.dev256+g59096013d161`, runner klt 0.9.0) on the Spot batch fleet; **ngspice-47** (`/usr/local/bin/ngspice` on the runner). Submitted from `loom-worker-1` (probe from `loom-worker-2`). The original states "ngspice-46, x86-64 Linux" and no host, so neither host nor engine build is reproduced — bounded to zero at the committed precision by the byte-identical result below.
- **Batch jobs**: two-deck probe `klt-sim-e183a39e0aa7` (shared with `RECORD-006`; exit 0), then this arm as four 64-deck chunk jobs — `klt-sim-d2360b2b6ca5`, `klt-sim-22334b66be5c`, `klt-sim-db47ac78080f`, `klt-sim-80a15f762b4a` — 254/254 units pass. No local grid was run.
- **Command**: as in `RECORD-006-loop-bandwidth-pm-rerun-batch.md` — the four snapshots were rendered by one `gen_rerun319.py render --pinned-pdk DIR --chunk-size 64` and submitted as chunked `klt sim --batch-set` invocations.
- **PDK revisions (pinned, staged with the decks — read first)**: identical to `RECORD-006-loop-bandwidth-pm-rerun-batch.md`'s, staged from the same clean checkout of
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  with the symlinked resistor cards and `r3_cmc.osdi` bytes of
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (both `sim/README.md` `PDK-PIN`s; manifest `../corners/staged_pdk_rerun319.sha256.csv`, decks `../corners/decks_rerun319.sha256.csv`; nothing host-resolved on the runner).
- **Rebuilt harness**: `testbench/gen_rerun319.py` executes `f54b9ef`'s own `run.sh` Python verbatim with only `run_ac()`'s body replaced; matrix, `crossover()` and CSV writers are the historical ones. Decks differ only in `pre_osdi` inside `.control` instead of a `.spiceinit`, and in the PDK references being the deck-relative staged pinned closure.

## Result vs the original

Every output of this arm is **byte-identical** to the original's committed artifact: `results_icp_refresh_rerun319.csv` (`6d9ec4448ddff62afc1e69fd47525455d33ec7e7b4f60c7285621642693ccb17`), `mom_band_icp_refresh_rerun319.csv` (`4dc969f6e29ee2be28147caf07fdb2f642670a44b3caad80b08e1c901f327798`), `proposal_icp_refresh_rerun319.csv` (`118ace4cc6ac6392466b94506c7bd0894365b75f30f6c30e6b52dbe4214ea197`) and `crosscheck_icp_refresh_rerun319.txt` (`bf372dcf8f1b29659ef0c93db0995fc97e985a56d7f4c91d6a7f68a9767a871a`).

| Metric (Part A, real subckt) | Original (`f54b9ef`) | Rerun |
|---|---|---|
| Rows | 90 | 90 |
| `f_c` range | 0.3307 - 4.6356 MHz | identical |
| PM range | 1.545 - 20.345 deg | identical |
| Rows meeting PM >= 45 deg | **0 of 90** | **0 of 90** |
| Verdict flips (`meets_ceiling`, `meets_pm45`) | — | **0 of 90** |

Cross-check at the nominal point: real subckt `f_c` 952.4408 kHz / PM 4.265 deg, lumped 965.5761 kHz / 4.316 deg — the original's published digits exactly.

### The original's own claim, re-tested

`RECORD-002-icp-input-refresh.md`'s claim is a *differential* one: refreshing `Icp` moves every output by well under 1 % and flips no verdict. Running `RECORD-006`'s `b37918d` arm and this `f54b9ef` arm through the **same** fleet, engine and pinned PDK bytes isolates that input change from everything else — and both arms being byte-identical to their originals' committed CSVs, the differential this record measures **is** the original's own committed differential:

| Output | Rows | Max d `icp_a` | Max d `fc_hz` | Max d `pm_deg` | Verdict flips |
|---|---|---|---|---|---|
| `results` (rerun `b37918d` -> rerun `f54b9ef`) | 90 | 0.788 % | 0.394 % | 0.430 % | **0** |

(recomputed from the byte-identical committed CSVs; the original's prose table quotes 0.782 % / 0.392 % / 0.428 % from its own unrounded in-memory values). Both of `RECORD-001`'s findings, restated by the original with refreshed numbers, hold exactly: **0 of 90** rows close the loop with the as-drawn filter, and the `R1` x20 / 10 uA pair is still the widest-margin proposal pair, in an identical 18-row `meets_both` set.

### What the byte-identity establishes

Same as `RECORD-006`'s: engine build (ngspice-47 vs 46), host and transport are bounded at zero for these decks at the committed precision, and the original's refreshed-`Icp` evaluation is confirmed to have run on PDK content equal to the pinned trees.

## What this does not bound

Everything the original did not — it adds no new measurement beyond a refreshed evaluation of the same model against one changed input, and inherits `RECORD-001`'s whole "What this does not bound" list. The original run's own host and ngspice build remain unknown; what this run adds is the demonstration that those unknowns do not affect the committed artifacts' values on the pinned PDK bytes.
