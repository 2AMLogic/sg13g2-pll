# RECORD-008: rerun of RECORD-002's resized-filter amended-`f_ref` sweep on the batch fleet (issue #319)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #319 (split from #214, item 9 provenance migration, Part of #199). Append-only. Reruns the bench of `RECORD-002-r1-resize-full-fref-range.md` and is the `ADDENDUM-RERUN` target of `ADDENDUM-003-record-002-r1-superseded.md`. It edits neither the original nor its CSVs; new data is `../corners/results_resized_rerun319.csv`, `../corners/crosscheck_resized_rerun319.txt` and the control arm `../corners/results_resized_origicp_rerun319.csv` / `../corners/crosscheck_resized_origicp_rerun319.txt`.
- **Read this first — the rerun reproduces the original exactly.** The control arm (the `Icp` table the original actually consumed) is **byte-identical** to the original's committed `results_resized.csv` and `crosscheck_resized.txt`, sha256 for sha256, and the primary arm (that commit's own refreshed table) differs from it only through that input: max `dPM` 0.128 deg, **0 verdict flips of 426**, same 16-of-17 headline. An earlier attempt in this PR (commit `156716f`, same grids on the fleet image's newer `/opt/pdk` tree) had shown 14 flips and 14-of-17; that non-reproduction was the fleet image's PDK content, not the design basis, and is decomposed below as a PDK-drift observation.
- **DUT**: the historical DUT of commit `ffec56a`, not today's design — the type-II loop around the **resized** `loop_filter` subckt from that commit's frozen `../netlist-snapshots/loop_filter_resized.spice` (`XR1` rppd `w=0.6u l=810u`, ~x44.2; `XC1`/`XC2` untouched), with the same linearised phase-detector/charge-pump, VCO and divider stand-ins, fed from that commit's own measured input tables.
- **Corner coverage**: the original's Part D matrix, unchanged — 3 PVT bundles x 2 band codes x **3** `Kvco` intervals (`low`/`mid`/`top`) x the 12-point amended `f_ref` grid (3.6 - 24.4 MHz, admitted only where `N` lands in [64, 127]) x 6 trim codes = **426 rows** spanning 30 distinct (band, interval, `f_ref`) combinations, of which 17 have all 3 PVT bundles present and 13 have only 1 - 2; plus Part D' the 2-deck cross-check. 682 decks per arm, two arms. Supply is not swept, as in the original. Parts A - C of the same `run.sh` are `RECORD-006`/`RECORD-007`'s scope and were rerun there.
- **Not rerun**: the exploratory lumped-model `R1`-scale search the original describes under "Why x44.2, not x20" is not part of `run.sh` and was never committed evidence; it is not reproduced here. The issue-79/83 fine-trim grids are separate records (#231 / #320 scope).
- **Tool / host**: `klt sim --backend batch --wait-for-capacity 600` (client `klt 0.9.3.dev256+g59096013d161`, runner klt 0.9.0) on the Spot batch fleet; **ngspice-47** (`/usr/local/bin/ngspice` on the runner). Submitted from `loom-worker-1` (probe from `loom-worker-2`). The original states "ngspice-46, x86-64 Linux" and no host, so neither host nor engine build is reproduced — bounded to zero at the committed precision by the control arm's byte-identity.
- **Batch jobs**: two-deck probe `klt-sim-e183a39e0aa7` (exit 0), then each arm as eleven 64-deck chunk jobs (682 units, all pass). Primary (`ffec56a`): `klt-sim-5c63d6471cca`, `klt-sim-10073b77b747`, `klt-sim-f5e6e68c7e7b`, `klt-sim-5f481e46ee98`, `klt-sim-b3fd7c953d85`, `klt-sim-a5d2ec9277cb`, `klt-sim-a8952e50b873`, `klt-sim-2cff71f6470b`, `klt-sim-86d005f14a3e`, `klt-sim-efe5a8229ab3`, `klt-sim-1ab47aedb683`. Control (`ffec56a_origicp`): `klt-sim-e3604db52aa7`, `klt-sim-bffcf3d34a69`, `klt-sim-f565bc66faa6`, `klt-sim-3b18a858c827`, `klt-sim-8bffdcec381e`, `klt-sim-3609f404052c`, `klt-sim-4cbfba7a0127`, `klt-sim-c52c42ace734`, `klt-sim-3f4e79cd539c`, `klt-sim-eeb21e531242`, `klt-sim-42fb1c480e33`. The chunking splits only the S3 upload (klayout-tools#5539); same decks, same bytes. No local grid was run.
- **Command**: `python3 -I testbench/gen_rerun319.py render --pinned-pdk <ihp-sg13cmos5l checkout at the PDK-PIN> --chunk-size 64`; from `testbench/`: `klt sim --batch-set rerun319_ffec56a.chunk*.request.json rerun319_ffec56a_origicp.chunk*.request.json --max-in-flight 6 --capacity-retries 3 --wait-for-capacity 600 -o <outdir>`; `python3 -I testbench/gen_rerun319.py collect <outdir-per-arm> ...` writes the CSVs.
- **PDK revisions (pinned, staged with the decks — read first)**: identical to `RECORD-006-loop-bandwidth-pm-rerun-batch.md`'s, staged from the same clean checkout of
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  with the symlinked resistor cards and `r3_cmc.osdi` bytes of
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (both `sim/README.md` `PDK-PIN`s; manifest `../corners/staged_pdk_rerun319.sha256.csv`, decks `../corners/decks_rerun319.sha256.csv`; nothing host-resolved on the runner).
- **Rebuilt harness**: `testbench/gen_rerun319.py` executes `ffec56a`'s own `run.sh` Python verbatim with only `run_ac()`'s body replaced; the matrix, `crossover()` and every CSV writer are the historical ones. Decks differ only in `pre_osdi` inside `.control` instead of a `.spiceinit`, and in the PDK references being the deck-relative staged pinned closure.

## A provenance defect in the original, found while rebuilding its inputs — and now proven

`ffec56a`'s **committed** `results_resized.csv` carries `icp_a` values of 1.005123e-05 / 1.004412e-05 / 1.004607e-05 (fast / slow / typ at the 10 uA code) — the **`b37918d` Icp table**, not the DR-006-refreshed one already present in `ffec56a`'s own tree (1.000046e-05 / 1.000072e-05 / 1.000047e-05). `run.sh` reads that table at runtime, so the committed Part D artifacts are **not what that commit's own `run.sh` reproduces** with its own tree: the original Part D ran before the #72 / #85 input refresh merged and was never regenerated against it. This record turns that inference into a measurement: the control arm below, fed the `b37918d` table, reproduces the original **byte-for-byte**, which is only possible if the original consumed exactly that table. This is recorded, not corrected — the original stays unedited.

The rerun therefore runs **two arms**, which also isolates every deviation:

| Arm | Icp table fed in | CSV |
|---|---|---|
| **Primary** | `ffec56a`'s own tree (refreshed) — the faithful "rerun at the original's commit" | `results_resized_rerun319.csv` |
| **Control** | `b37918d`'s table — the one the original actually consumed | `results_resized_origicp_rerun319.csv` |

## Result vs the original

| Metric (Part D, resized filter, real subckt) | Original (`ffec56a`) | Rerun (primary) | Rerun (control) |
|---|---|---|---|
| Rows | 426 | 426 | 426 |
| `f_c` range | 0.1482 - 10.3836 MHz | 0.1476 - 10.3767 MHz | identical to original |
| PM range | 17.609 - 59.199 deg | 17.611 - 59.199 deg | identical to original |
| Rows meeting PM >= 45 deg | 260 of 426 | 260 of 426 | 260 of 426 |
| **Full-3-bundle regions meeting both criteria** | **16 of 17** | **16 of 17** | **16 of 17** |
| Partial-coverage (1 - 2 bundle) regions meeting both | 12 of 13 | 12 of 13 | 12 of 13 |
| Verdict flips vs the original | — | **0 of 426** | **0 of 426** |
| Bytes vs the original | — | differ only through the `Icp` input (max `d fc_hz` 0.683 %, `d pm_deg` 0.368 % rel., 0.128 deg abs.) | **byte-identical** (`a2397a8ac202820ac380b898b0d4543cdd41bcd0e4f17f6cdbd0ba7db29f5370`, cross-check `034d6942e03be5a4f003d58d9cff214a4799ff44f22940f53429f48426e7f093`) |

Part D' cross-check: the control arm reproduces the original's digits exactly (real subckt `f_c` 2.170869e+06 Hz / PM 51.299 deg, lumped 2.347968e+06 Hz / 57.709 deg); the primary arm's real subckt moves only as much as the `Icp` refresh moves it (2.163236e+06 Hz / 51.365 deg; lumped 2.339084e+06 Hz / 57.769 deg).

### The decomposition

Running the same 426-row grid twice — once on each `Icp` table, everything else held fixed on the pinned bytes — separates the candidate causes exactly:

| Change isolated | Max \|dPM\| | Verdict flips (of 426) |
|---|---|---|
| `Icp` refresh alone (control -> primary; same pinned bytes, engine, harness) | **0.128 deg** | **0** |
| Pinned trees vs the original's environment (control arm vs original) | **0.000 deg — byte-identical** | **0** |
| *(for contrast)* fleet image vs pinned trees (this PR's superseded first attempt, commit `156716f`) | *(1.973 deg)* | *(14)* |

So on the pinned design basis the original's numbers stand exactly, and the input refresh the original missed is irrelevant to its conclusions — as the original's own text assumed. The third row is kept as a **PDK-drift observation**, clearly separated from this record's evidence: the same grids, harness and engine on the fleet image's newer `/opt/pdk` tree (`f7bca326…` store bundle) moved Part D's PM by up to 1.997 deg and flipped 14 verdicts while its lumped decks stayed byte-identical — the same signature `sg13cmos5l-loop-filter-momcap` RECORD-003 / RECORD-004 measured directly on that bundle (`rppd` R1 shifted 0.15 - 0.90 % at the as-drawn geometry, **0.99 - 6.25 %** at this record's `w=0.6u l=810u` geometry, which is why Part D amplifies what `RECORD-006`'s as-drawn Part A showed at 0.177 deg). The superseded CSVs of that attempt remain readable at commit `156716f` for anyone quantifying fleet-image drift; nothing in this record or its addendum depends on them.

### Regions: nothing changed

The only full-3-bundle region failing both criteria is the original's own failing region, `band=00, low, f_ref=4.5 MHz` (#79), with the original's exact digits in the control arm (best code 10 uA: PM 44.127 / 47.624 / 52.226 deg fast / typ / slow, **0.873 deg** short at fast; primary: 44.045 / 47.552 / 52.166 deg, 0.955 deg short — the `Icp` refresh's whole effect). The partial-coverage (#83) region `band=00, mid, f_ref=4.5 MHz` (`slow` bundle only) likewise still fails exactly as the original recorded: best ceiling-compliant code 2.5 uA at PM 43.639 deg control (primary 43.531 deg), 1.36 deg short. Every other region's verdict is identical in both arms and the original.

### What this means for consumers

`RECORD-002-r1-resize-full-fref-range.md`'s conclusions are reproduced **wholesale and byte-for-byte on the pinned design basis**: 16 of 17 full-coverage regions meet both criteria, the near-floor `band=00` region remains the binding one, and the qualitative story is untouched. The two decision-record consequences the superseded in-PR version of this record raised from the unpinned data — that DR-008's 0.87 deg shortfall had grown to 2.21 deg and that DR-007's sizing gap had vanished — were artifacts of the fleet image's PDK content and are **withdrawn**: on the pinned trees both decision records' sizing bases stand exactly as originally recorded. `DR-007`, `DR-008`, `spec/target-spec.md`, `docs/chipalooza/challenge-6-proposal.md`, `design/README.md` and the `sg13cmos5l-cp-icp-trim` records continue to cite the original by name and are **not** repointed: the addendum resolves that citation, and re-deriving a ratified decision record from a new PDK revision is a spec question (the `PDK-PIN` re-stamp is #250), not this record's to settle. `sg13cmos5l-loop-bandwidth-pm` RECORD-003 / RECORD-004 — the records that closed #83 and #79 — are #320's rerun scope.

## What this does not bound

Everything the original did not — large-signal and acquisition behaviour, sampled-loop (z-domain) effects beyond the `f_c < f_ref/10` guard, reference spur / jitter / phase noise, a full per-`f_ref` trim-code keying table, the 13 partial-PVT-coverage regions' missing bundles (unchanged here: this rerun reproduces the original's grid, it does not extend it), and anything about silicon. The original run's own host and ngspice build remain unknown and unrecoverable; what this run adds is the demonstration that those unknowns do not affect the committed artifacts' values on the pinned PDK bytes.
