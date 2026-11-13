# RECORD-008: rerun of RECORD-002's resized-filter amended-`f_ref` sweep on the batch fleet (issue #319)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #319 (split from #214, item 9 provenance migration, Part of #199). Append-only. Reruns the bench of `RECORD-002-r1-resize-full-fref-range.md` and is the `ADDENDUM-RERUN` target of `ADDENDUM-003-record-002-r1-superseded.md`. It edits neither the original nor its CSVs; new data is `../corners/results_resized_rerun319.csv`, `../corners/crosscheck_resized_rerun319.txt` and the control arm `../corners/results_resized_origicp_rerun319.csv` / `../corners/crosscheck_resized_origicp_rerun319.txt`.
- **Read this first — the rerun does not reproduce the original's headline count.** The original reports 16 of 17 full-3-bundle-coverage operating regions meeting both criteria with one failure (#79); the rerun gets **14 of 17 with three failures**. The cause is isolated below and is **PDK content**, not the harness, the engine or an input refresh.
- **DUT**: the historical DUT of commit `ffec56a`, not today's design — the type-II loop around the **resized** `loop_filter` subckt from that commit's frozen `../netlist-snapshots/loop_filter_resized.spice` (`XR1` rppd `w=0.6u l=810u`, ~x44.2; `XC1`/`XC2` untouched), with the same linearised phase-detector/charge-pump, VCO and divider stand-ins, fed from that commit's own measured input tables.
- **Corner coverage**: the original's Part D matrix, unchanged — 3 PVT bundles x 2 band codes x **3** `Kvco` intervals (`low`/`mid`/`top`) x the 12-point amended `f_ref` grid (3.6 - 24.4 MHz, admitted only where `N` lands in [64, 127]) x 6 trim codes = **426 rows** spanning 30 distinct (band, interval, `f_ref`) combinations, of which 17 have all 3 PVT bundles present and 13 have only 1 - 2; plus Part D' the 2-deck cross-check. 682 decks per arm, two arms. Supply is not swept, as in the original. Parts A - C of the same `run.sh` are `RECORD-006`/`RECORD-007`'s scope and were rerun there.
- **Not rerun**: the exploratory lumped-model `R1`-scale search the original describes under "Why x44.2, not x20" is not part of `run.sh` and was never committed evidence; it is not reproduced here. The issue-79/83 fine-trim grids are separate records (#231 / #320 scope).
- **Tool / host**: `klt sim --backend batch --wait-for-capacity 600` (client `klt 0.9.2.dev915+g513f88f6836d`, runner klt 0.9.0) on the Spot batch fleet; **ngspice-47** (`/usr/local/bin/ngspice` on the runner). Submitted from `loom-worker-4`. The original states "ngspice-46, x86-64 Linux" and no host, so neither host nor engine build is reproduced.
- **Batch jobs**: single-deck probe `klt-sim-db5a6d5ee4ae` (exit 0), the primary grid `klt-sim-d87790059a38` (682 decks, exit 0, 682/682 pass), and the control grid `klt-sim-8b5077b2aa9f` (682 decks, exit 0, 682/682 pass). One earlier control submit, `klt-sim-7a5b761270d4`, was refused with `batch_no_capacity` (`BATCH_MAX_VCPU=224`, quota shared with `ci-spot`) after its 600 s capacity-wait budget; it was resubmitted with a 1800 s budget, not run locally. No local grid was run.
- **Command**: `python3 -I testbench/gen_rerun319.py render`; from `testbench/`: `klt sim --batch-set rerun319_b37918d.request.json rerun319_f54b9ef.request.json rerun319_ffec56a.request.json --wait-for-capacity 600 --capacity-retries 3 -o <outdir>` and `klt sim rerun319_ffec56a_origicp.request.json --backend batch --wait-for-capacity 1800 -o <outdir2>`; `python3 -I testbench/gen_rerun319.py collect <outdir>/rerun319_b37918d.request <outdir>/rerun319_f54b9ef.request <outdir>/rerun319_ffec56a.request <outdir2>` writes the CSVs.
- **PDK revisions (limitation, read first)**: identical to `RECORD-006-loop-bandwidth-pm-rerun-batch.md`'s, and subject to the same limitation — the runner exposes no stamp (`pdk stamp unreadable`, `not_comparable`), so the cmos5l tree is **inferred** as the fleet bundle, store version `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14` (bundle sha256 `3195ba7f3a74e91fc4eced64102c9d61b00d8eadcf5e795d36d926d40ab4ad31`), **not** the legacy commit `PDK-PIN` in `sim/README.md` still names (re-stamp is #250, out of scope). The ihp-sg13g2 tree is a release install, `.fetched-version` `0.3.0`, i.e.
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e as established in `sim/provenance-migration.md` (version marker, not a `git rev-parse`).
- **Rebuilt harness**: `testbench/gen_rerun319.py` executes `ffec56a`'s own `run.sh` Python verbatim with only `run_ac()`'s body replaced; the matrix, `crossover()` and every CSV writer are the historical ones. Decks differ only in `pre_osdi` inside `.control` instead of a `.spiceinit`, and in the PDK path being the runner's `$PDK_ROOT`.

## A provenance defect in the original, found while rebuilding its inputs

`ffec56a`'s **committed** `results_resized.csv` carries `icp_a` values of 1.005123e-05 / 1.004412e-05 / 1.004607e-05 (fast / slow / typ at the 10 uA code) — the **`b37918d` Icp table**, not the DR-006-refreshed one already present in `ffec56a`'s own tree (1.000046e-05 / 1.000072e-05 / 1.000047e-05). `run.sh` reads that table at runtime, so the committed Part D artifacts are **not what that commit's own `run.sh` reproduces**: the original Part D ran before the #72 / #85 input refresh merged and was never regenerated against it. This is recorded, not corrected — the original stays unedited.

The rerun therefore runs **two arms**, which also isolates the cause of every deviation below:

| Arm | Icp table fed in | CSV |
|---|---|---|
| **Primary** | `ffec56a`'s own tree (refreshed) — the faithful "rerun at the original's commit" | `results_resized_rerun319.csv` |
| **Control** | `b37918d`'s table — the one the original actually consumed | `results_resized_origicp_rerun319.csv` |

## Result vs the original

| Metric (Part D, resized filter, real subckt) | Original (`ffec56a`) | Rerun (primary) | Rerun (control) |
|---|---|---|---|
| Rows | 426 | 426 | 426 |
| `f_c` range | 0.1482 - 10.384 MHz | 0.1470 - 10.349 MHz | 0.1476 - 10.356 MHz |
| PM range | 17.609 - 59.199 deg | 17.443 - 59.199 deg | 17.441 - 59.199 deg |
| Rows meeting PM >= 45 deg | 260 of 426 | 263 of 426 | 263 of 426 |
| **Full-3-bundle regions meeting both criteria** | **16 of 17** | **14 of 17** | **14 of 17** |
| Partial-coverage (1 - 2 bundle) regions meeting both | 12 of 13 | 13 of 13 | 13 of 13 |
| Verdict flips vs the original | — | 14 of 426 | 14 of 426 |

Per-row maximum PM difference against the original: **1.997 deg** (primary), **1.973 deg** (control).

### The cause is PDK content, decomposed

Running the same 426-row grid twice — once on each Icp table, everything else held fixed — separates the two candidate causes exactly:

| Change isolated | Max \|dPM\| | Verdict flips (of 426) |
|---|---|---|
| Icp refresh alone (control -> primary; same PDK, engine, harness) | **0.128 deg** | **0** |
| PDK + engine alone (original -> control; same Icp table the original consumed) | **1.973 deg** | **14** |

So the input refresh the original missed is irrelevant to its conclusions, and the entire deviation is the environment. Two further facts place it on the PDK rather than on ngspice-47 or the batch transport:

- The Part D' cross-check's **lumped** arm — an ideal `R`/`C` deck that reads no PDK file — reproduces **bit-identically** in both arms (`f_c` 2.347968e+06 Hz, PM 57.709 deg, the original's exact digits), while the **real-subckt** arm moves (2.170869e+06 / 51.299 deg original, 2.182573e+06 / 51.012 deg control). The same split is seen across the whole of `RECORD-006`/`RECORD-007`, where all 162 lumped rows per snapshot are byte-identical.
- `sg13cmos5l-loop-filter-momcap` RECORD-003 / RECORD-004 measured this directly on the same fleet: the current tree's `cornerRES.lib` shifts `rppd` R1 by 0.15 - 0.90 % at the as-drawn geometry and by **0.99 - 6.25 %** at this record's resized `w=0.6u l=810u` geometry. A resize that amplifies the R1 shift roughly sevenfold is exactly why Part D's PM moves by up to 2 deg where `RECORD-006`'s as-drawn Part A moves by 0.18 deg.

### Which regions changed, and by how much

| Region | Original | Rerun (primary) |
|---|---|---|
| `band=00, low, f_ref=4.5 MHz` (#79) | **fails**; best code 10 uA, PM 44.13 / 47.62 / 52.23 deg (fast / typ / slow), 0.87 deg short at fast | **still fails**, and by more: PM **42.79** / 47.86 / 53.79 deg, **2.21 deg** short at fast |
| `band=00, mid, f_ref=4.5 MHz` (#83, `slow` bundle only) | **fails**; best ceiling-compliant code 2.5 uA, PM 43.639 deg, 1.36 deg short | **passes**; 2.5 uA gives PM **45.500** deg (control: 45.607 deg) |
| `band=00, mid, f_ref=5.5 MHz` | passes (5 uA, worst-bundle PM 51.96 deg) | **fails**: at 5 uA the `slow` bundle's `f_c` rises 535.0 -> 555.3 kHz and crosses the 550 kHz `f_ref/10` ceiling (by 0.96 %), which removes that code; the next compliant code, 2.5 uA, gives only 39.72 deg at `fast` |
| `band=11, low, f_ref=5.5 MHz` | passes (5 uA, worst-bundle PM 45.665 deg — 0.67 deg of margin) | **fails**: the same code gives **44.314** deg at `fast`, 0.69 deg short |

All 14 flips are rows within about 2 deg of the 45 deg criterion or (in one case) within 1 % of the `f_c` ceiling: 7 flip to passing, 6 to failing on PM, 1 on the ceiling. Nothing with real margin moved — the original's own comfortable region (`band=11, top`, PM 51.3 - 58.3 deg) is unaffected.

### What this means for consumers — flagged, not repointed

`RECORD-002-r1-resize-full-fref-range.md`'s **qualitative** conclusion survives: the x44.2 resize is a large, real improvement over x20 and closes the great majority of the amended envelope, with the near-floor `band=00` region still the binding one. Its **counts** do not: 14 of 17, not 16 of 17, with full 3-bundle coverage on the current PDK.

Two consequences are for the owner to rule on, and this record deliberately does **not** act on either:

- **DR-008** (`#79`, 11 uA fine code) was sized against a 0.87 deg shortfall; on the current PDK that shortfall is 2.21 deg. The code may no longer close the gap.
- **DR-007** (`#83`, 3.75 uA fine code) was sized against a gap that on the current PDK **does not appear** — that region passes at the standard 2.5 uA code.

Both decision records, `spec/target-spec.md`, `docs/chipalooza/challenge-6-proposal.md` and the `sg13cmos5l-cp-icp-trim` records continue to cite the original by name and are **not** repointed here: the addendum resolves that citation, and re-deriving a ratified decision record from a new PDK revision is a spec question (the `PDK-PIN` re-stamp is #250), not this record's to settle. `sg13cmos5l-loop-bandwidth-pm` RECORD-003 / RECORD-004 — the records that closed #83 and #79 — are #320's rerun scope, and #320 reached the same conclusion about DR-008 independently.

## What this does not bound

Everything the original did not — large-signal and acquisition behaviour, sampled-loop (z-domain) effects beyond the `f_c < f_ref/10` guard, reference spur / jitter / phase noise, a full per-`f_ref` trim-code keying table, the 13 partial-PVT-coverage regions' missing bundles (unchanged here: this rerun reproduces the original's grid, it does not extend it), and anything about silicon. It also does **not** restore the original run's host or PDK provenance, which is unrecoverable: ngspice-47 here against the stated ngspice-46, a fleet Spot instance rather than the original's unnamed x86-64 Linux worker, and a cmos5l revision inferred from this host's bundle rather than read from the runner.
