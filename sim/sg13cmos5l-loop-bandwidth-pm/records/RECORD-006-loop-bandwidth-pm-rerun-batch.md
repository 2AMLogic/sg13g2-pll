# RECORD-006: rerun of RECORD-001's as-drawn loop-bandwidth / phase-margin matrix on the batch fleet (issue #319)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #319 (split from #214, item 9 provenance migration, Part of #199). Append-only. Reruns the bench of `RECORD-001-loop-bandwidth-phase-margin.md` and is the `ADDENDUM-RERUN` target of `ADDENDUM-001-record-001-superseded.md`. It edits neither the original nor its CSVs; new data is `../corners/results_rerun319.csv`, `../corners/mom_band_rerun319.csv`, `../corners/proposal_rerun319.csv` and `../corners/crosscheck_rerun319.txt`.
- **DUT**: the historical DUT of commit `b37918d`, not today's design — the type-II charge-pump loop around the **as-drawn** `loop_filter` subckt from that commit's frozen `../netlist-snapshots/loop_filter.spice` (`XR1` rppd `w=4u l=120u`, `XC1` cap_cmomi `40u/40u`, `XC2` `10u/10u`), with the phase detector / charge pump, VCO and divider as the same linearised stand-ins the original used, each fed from that commit's own measured input tables (`sg13cmos5l-vco-kvco-table`, `sg13cmos5l-loop-filter-momcap`, `sg13cmos5l-cp-icp-trim` `corners/results.csv` **as of `b37918d`**).
- **Corner coverage**: the original's full matrix, unchanged — Part A, 3 PVT bundles (`typ`/`slow`/`fast`, each binding a `cornerRES.lib` section, a temperature and a MOS corner) x 2 band codes x 2 `Kvco` intervals x the admissible `f_ref`/`N` scenarios x 6 trim codes = **90 real-subckt rows**; Part A' the 2-deck real-vs-lumped cross-check; Part B the +/-20 % MOM band, **54 rows**; Part C the `R1`-resizing proposal sweep, **108 rows**. 254 decks total. Supply is not swept, as in the original.
- **Not rerun**: nothing of `run.sh`'s own output at `b37918d`. Parts of this bench added after `b37918d` (`results_resized*`, the issue-79/83 fine-trim grids, the issue-196 `cout`/`ccp` campaigns) are other records' evidence and out of scope here.
- **Tool / host**: `klt sim --backend batch --wait-for-capacity 600` (client `klt 0.9.3.dev256+g59096013d161`, runner klt 0.9.0) on the Spot batch fleet; **ngspice-47** (`/usr/local/bin/ngspice` on the runner). Submitted from `loom-worker-1` (probe from `loom-worker-2`). The original states "ngspice-46, x86-64 Linux" and no host, so neither host nor engine build is reproduced — bounded to zero at the committed precision by the byte-identical result below.
- **Batch jobs**: two-deck probe `klt-sim-e183a39e0aa7` (the original's own Part A' cross-check decks `X_real`/`X_lump`, staged on the same pinned closure; exit 0), then this arm as four 64-deck chunk jobs — `klt-sim-997eb4944388`, `klt-sim-7f10e2c88d6f`, `klt-sim-21533b443486`, `klt-sim-9bcc4d50231a` — 254/254 units pass. The chunking splits only the S3 upload (klayout-tools#5539); same decks, same bytes. No local grid was run.
- **Command**: `python3 -I testbench/gen_rerun319.py render --pinned-pdk <ihp-sg13cmos5l checkout at the PDK-PIN> --chunk-size 64`; from `testbench/`: `klt sim probe319.request.json --backend batch --wait-for-capacity 600 -o <probe-outdir>` for the probe, then `klt sim --batch-set rerun319_b37918d.chunk0*.request.json --max-in-flight 6 --capacity-retries 3 --wait-for-capacity 600 -o <outdir>`; `python3 -I testbench/gen_rerun319.py probe-check <probe-outdir>` and `python3 -I testbench/gen_rerun319.py collect <outdir-per-arm> ...` write/verify the CSVs.
- **PDK revisions (pinned, staged with the decks — read first)**: the grid runs on the **pinned** trees via the #374 staging route. `render --pinned-pdk DIR` stages the model closure beside the decks and rewrites every PDK reference in every deck deck-relative (`.lib models/cornerRES.lib <section>`, `.include models/cap_cmomi.lib`, `pre_osdi osdi/<n>.osdi`), so klt ships those bytes with each deck and nothing resolves on the runner — `klt sim --dry-run` reports `host_resolved: []`. The staged tree is a clean checkout of
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  — `sim/README.md`'s `PDK-PIN` (verified on the submitting host: `git rev-parse HEAD` equals the pin, `git status --porcelain` empty). That checkout tracks `cornerRES.lib`, `resistors_mod*.lib` and `resistors_stat.lib` as symlinks into the sibling ihp-sg13g2 tree (dereferenced when staged), so those staged bytes are that tree's, and its `r3_cmc.osdi` likewise:
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  as pinned in `sim/README.md` and established in `sim/provenance-migration.md` (release install, `.fetched-version` `0.3.0`; the host's live and 2026-10-15 `bak` g2 `libs.tech/ngspice` subtrees were diffed on the submitting host — zero differing files). All 8 staged files, identical across the four arms of this campaign, are manifested with sha256 in `../corners/staged_pdk_rerun319.sha256.csv`; 5 of them (`cornerRES.lib`, `resistors_mod.lib`, `resistors_mod_mismatch.lib`, `resistors_stat.lib`, `r3_cmc.osdi`) are the same files `sg13cmos5l-vco-kvco-table` RECORD-002 staged from a different worker, and every sha256 agrees. Every deck's sha256 is manifested in `../corners/decks_rerun319.sha256.csv`.
- **Rebuilt harness**: `testbench/gen_rerun319.py` extracts `b37918d`'s own `run.sh` from git and executes the Python embedded in it verbatim, replacing **only** the body of `run_ac()` — the function that shells out to ngspice — so the matrix, the `crossover()` log-log interpolation and every CSV writer are the historical ones. Decks differ from `run.sh`'s only in `pre_osdi` lines at the top of `.control` (hoisted by ngspice) instead of a `.spiceinit`, and in the PDK references being the deck-relative staged closure above. An earlier attempt in this PR (commit `156716f`) ran the same matrix on the fleet image's own `/opt/pdk` tree and did **not** reproduce the original (`f_c` within 0.067 %, PM within 0.177 deg); that data was replaced wholesale by this pinned run — the residual PDK-drift observation it motivated is recorded in `RECORD-008-r1-resize-full-fref-range-rerun-batch.md`.

## Result vs the original

Every output of this arm is **byte-identical** to the original's committed artifact — same sha256, CRLF line endings included (the historical writers' `csv.writer(..., newline="")` form):

| Output | Rows | sha256 (rerun == original) |
|---|---|---|
| `results_rerun319.csv` | 90 | `5ce739c56dd651c37f0acb2c5399a4e19dae94e83c4dca7190293d1387887a74` |
| `mom_band_rerun319.csv` | 54 | `47d504caf0afdff8d470ee386aa6c1e63e48ac13d8490e2cae8450c06875f0aa` |
| `proposal_rerun319.csv` | 108 | `8c49992021bdf71c53a878f396bb3c9ea767bcae8a3b364846085cbbb5021895` |
| `crosscheck_rerun319.txt` | — | `824b7555eb39b7e8ca9cde28ef0f51df5ccc84ee517293d2be1a700dd3820540` |

| Metric (Part A, as-drawn filter, real subckt) | Original (`b37918d`) | Rerun |
|---|---|---|
| Rows | 90 | 90 |
| `f_c` range | 0.3318 - 4.6387 MHz | identical |
| PM range | 1.550 - 20.331 deg | identical |
| Rows meeting PM >= 45 deg | **0 of 90** | **0 of 90** |
| Rows meeting both criteria | **0 of 90** | **0 of 90** |
| Verdict flips (`meets_ceiling`, `meets_pm45`) | — | **0 of 90** |

Part A' cross-check at the nominal point (`typ`, band 11, `top` interval, `f_ref` = 25 MHz, N = 50, 10 uA): real subckt `f_c` 954.6166 kHz / PM 4.275 deg and lumped 967.7821 kHz / 4.326 deg — the original's published digits, every one. The probe job alone reproduces this point before any grid runs (`probe-check` on `klt-sim-e183a39e0aa7`), which is what gates the other three arms.

### What the byte-identity establishes

The rerun differs from the original in every controllable degree of freedom it could not avoid — engine build (ngspice-47 vs the stated ngspice-46), host (a fleet Spot instance vs the original's unnamed worker), and transport (batch deck shipping vs a local `ngspice -b` loop) — and in none it could: same decks modulo the two forced transport edits, same pinned PDK bytes, same historical program. Byte-identity across all four outputs therefore bounds the aggregate of engine-build, host and transport effects at **zero** for these decks at the committed three-decimal precision, and confirms the originals were produced on PDK content equal to the pinned trees. (The earlier unpinned attempt of this PR — same grids on the fleet image's newer tree — moved the real-subckt rows by up to 0.067 % / 0.177 deg while its 162 lumped rows stayed byte-identical, which is what pinned the blame on `cornerRES.lib` content and motivated the pinned re-run; see RECORD-008 for the amplified effect at the resized geometry.)

### What this means for the original's conclusions

Both of `RECORD-001-loop-bandwidth-phase-margin.md`'s headline findings are reproduced without qualification and now byte-for-byte: **no trim code closes the loop with the as-drawn filter** (0 of 90), and the `R1` x20 / 10 uA pair remains in the proposal's identical 18-row `meets_both` set. Consumers that quote "PM 1.55 - 20.33 deg, 0 of 90" (`design/README.md`, `docs/chipalooza/challenge-6-proposal.md`) quote the pinned-basis values exactly and are **not** repointed: the original stands as the historical statement it was, and this record carries the replacement evidence claim.

## What this does not bound

Everything the original did not — large-signal and acquisition behaviour, sampled-loop (z-domain) effects, reference spur / jitter / phase noise, the `f_ref`-to-trim-code keying rule, and anything about silicon. The original run's own host and ngspice build remain unknown and unrecoverable; what this run adds is the demonstration that those unknowns do not affect the committed artifacts' values on the pinned PDK bytes.
