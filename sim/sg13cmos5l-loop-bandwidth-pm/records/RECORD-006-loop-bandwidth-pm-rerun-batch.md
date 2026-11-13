# RECORD-006: rerun of RECORD-001's as-drawn loop-bandwidth / phase-margin matrix on the batch fleet (issue #319)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #319 (split from #214, item 9 provenance migration, Part of #199). Append-only. Reruns the bench of `RECORD-001-loop-bandwidth-phase-margin.md` and is the `ADDENDUM-RERUN` target of `ADDENDUM-001-record-001-superseded.md`. It edits neither the original nor its CSVs; new data is `../corners/results_rerun319.csv`, `../corners/mom_band_rerun319.csv`, `../corners/proposal_rerun319.csv` and `../corners/crosscheck_rerun319.txt`.
- **DUT**: the historical DUT of commit `b37918d`, not today's design — the type-II charge-pump loop around the **as-drawn** `loop_filter` subckt from that commit's frozen `../netlist-snapshots/loop_filter.spice` (`XR1` rppd `w=4u l=120u`, `XC1` cap_cmomi `40u/40u`, `XC2` `10u/10u`), with the phase detector / charge pump, VCO and divider as the same linearised stand-ins the original used, each fed from that commit's own measured input tables (`sg13cmos5l-vco-kvco-table`, `sg13cmos5l-loop-filter-momcap`, `sg13cmos5l-cp-icp-trim` `corners/results.csv` **as of `b37918d`**).
- **Corner coverage**: the original's full matrix, unchanged — Part A, 3 PVT bundles (`typ`/`slow`/`fast`, each binding a `cornerRES.lib` section, a temperature and a MOS corner) x 2 band codes x 2 `Kvco` intervals x the admissible `f_ref`/`N` scenarios x 6 trim codes = **90 real-subckt rows**; Part A' the 2-deck real-vs-lumped cross-check; Part B the +/-20 % MOM band, **54 rows**; Part C the `R1`-resizing proposal sweep, **108 rows**. 254 decks total. Supply is not swept, as in the original.
- **Not rerun**: nothing of `run.sh`'s own output at `b37918d`. Parts of this bench added after `b37918d` (`results_resized*`, the issue-79/83 fine-trim grids, the issue-196 `cout`/`ccp` campaigns) are other records' evidence and out of scope here.
- **Tool / host**: `klt sim --backend batch --wait-for-capacity 600` (client `klt 0.9.2.dev915+g513f88f6836d`, runner klt 0.9.0) on the Spot batch fleet; **ngspice-47** (`/usr/local/bin/ngspice` on the runner). Submitted from `loom-worker-4`. The original states "ngspice-46, x86-64 Linux" and no host, so neither host nor engine build is reproduced — see "Not byte-identical" below.
- **Batch jobs**: single-deck probe `klt-sim-db5a6d5ee4ae` (`A_typ_11_top_25_10u`, the original's own cross-check point; `c7i.8xlarge` spot, exit 0, 17 s), then the grid `klt-sim-2d7f64aa6964` (254 decks, exit 0, 254/254 pass). No local grid was run.
- **Command**: `python3 -I testbench/gen_rerun319.py render`; from `testbench/`: `klt sim probe319.request.json --backend batch --wait-for-capacity 600 -o <outdir>` for the probe, then `klt sim --batch-set rerun319_b37918d.request.json rerun319_f54b9ef.request.json rerun319_ffec56a.request.json --wait-for-capacity 600 --capacity-retries 3 -o <outdir>`; `python3 -I testbench/gen_rerun319.py collect <outdir> ...` writes the CSVs.
- **PDK revisions (limitation, read first)**: the request names `models.pdk: ihp-sg13cmos5l`; the runner resolves it from its own image (`/opt/pdk`) and exposes no git revision or stamp (`pdk stamp unreadable`, comparison `not_comparable`). `cornerRES.lib` and the `cap_cmomi`/`cap_cmomf`/`r3_cmc` OSDI objects all resolved on the runner: every unit exits 0 with real values and each unit's `host_resolved` lists those `$PDK_ROOT/...` paths. The tree the run is attributed to is the unified-repository fleet bundle, store version `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14` (not a `git rev-parse`; bundle sha256 `3195ba7f3a74e91fc4eced64102c9d61b00d8eadcf5e795d36d926d40ab4ad31`, `.pdk-store.json` of this host's `~/share/pdk/ihp-sg13cmos5l`, no `.git`). That attribution is **inferred**, not read from the runner: it is the same bundle `sg13cmos5l-loop-filter-momcap` RECORD-003 established by a local single-deck cross-check against this host's tree. It is **not** the legacy split-repository commit that `PDK-PIN` in `sim/README.md` still names (re-stamp is #250, out of scope). The ihp-sg13g2 tree (CMOS5L model cards/OSDI are symlinks into it) is a release install, `.fetched-version` `0.3.0`, i.e.
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e as established in `sim/provenance-migration.md` (the host tree is not a git checkout, so this rests on the version marker, not a `git rev-parse`; the runner's own tree is not independently established). Host-tree sha256: `cornerRES.lib` `c6d749e72cfa2e06e4a14fac3f5662541bf6197b89265ecbedd632fd3503c425`; `cap_cmomi.osdi` `972ff31c1dd8658f7399f2ec9212d0220344c356a77570b5b3ee925155119a83`; `cap_cmomf.osdi` `d44927b3dbcc9a0906125da35fbb9cb23d9abdf20f6dddda0394e81fb165ac18`; `r3_cmc.osdi` `746f86fd1b89c309cbec7b23e661a66ee80b2d897ea229bc8e3fcc3757a673c3`.
- **Rebuilt harness**: `testbench/gen_rerun319.py` extracts `b37918d`'s own `run.sh` from git and executes the Python embedded in it verbatim, replacing **only** the body of `run_ac()` — the function that shells out to ngspice — so the matrix, the `crossover()` log-log interpolation and every CSV writer are the historical ones. Decks differ from `run.sh`'s only in `pre_osdi` lines at the top of `.control` (hoisted by ngspice) instead of a `.spiceinit`, and in the PDK path being the runner's `$PDK_ROOT`.

## Result vs the original

| Metric (Part A, as-drawn filter, real subckt) | Original (`b37918d`) | Rerun |
|---|---|---|
| Rows | 90 | 90 |
| `f_c` range | 0.3318 - 4.6387 MHz | 0.3318 - 4.6371 MHz |
| PM range | 1.550 - 20.331 deg | 1.552 - 20.508 deg |
| Rows meeting PM >= 45 deg | **0 of 90** | **0 of 90** |
| Rows meeting both criteria | **0 of 90** | **0 of 90** |
| Verdict flips (`meets_ceiling`, `meets_pm45`) | — | **0 of 90** |

Per-row maximum difference: `f_c` **0.067 %**, PM **0.177 deg**.

| Metric (lumped-element parts) | Original | Rerun |
|---|---|---|
| Part B `mom_band.csv`, 54 rows | — | **byte-identical** |
| Part C `proposal.csv`, 108 rows | — | **byte-identical** |
| Part C `meets_both` rows | 18 | 18, the **same** (filter, trim code, bundle) set |

Part A' cross-check at the nominal point (`typ`, band 11, `top` interval, `f_ref` = 25 MHz, N = 50, 10 uA): real subckt `f_c` 954.6166 kHz / PM 4.275 deg in the original, **954.6212 kHz / 4.281 deg** in the rerun; the lumped arm is bit-identical at 967.7821 kHz / 4.326 deg.

### The drift is PDK content, and the lumped parts prove it

Parts B and C, and the lumped half of the cross-check, are ideal `R`/`C` decks that read **no PDK file at all** — their R/C values come from the input CSVs. Those 162 rows reproduce **byte-identically** on ngspice-47 on the fleet. Only the decks that instantiate the real `rppd`/`cap_cmomi` compact models move, and they move by <= 0.067 % in `f_c` and <= 0.177 deg in PM. So the difference is not the engine build, the batch transport or the harness: it is `cornerRES.lib` content, consistent in direction and size with `sg13cmos5l-loop-filter-momcap` RECORD-003's independently measured R1 shift of 0.15 - 0.90 % on the same bundle.

### What this means for the original's conclusions

Both of `RECORD-001-loop-bandwidth-phase-margin.md`'s headline findings are reproduced without qualification: **no trim code closes the loop with the as-drawn filter** (0 of 90, unchanged), and the `R1` x20 / 10 uA pair remains in the proposal's passing set — which is byte-identical. The quoted PM ceiling moves from 20.33 deg to 20.51 deg and the `f_c` ceiling from 4.639 MHz to 4.637 MHz; both are third-significant-digit shifts that change no verdict and no spec-row disposition. Consumers that quote "PM 1.55 - 20.33 deg, 0 of 90" (`design/README.md`, `docs/chipalooza/challenge-6-proposal.md`) are therefore **not** repointed: the original stands as the historical statement it was, and this record carries the replacement evidence claim.

## What this does not bound

Everything the original did not — large-signal and acquisition behaviour, sampled-loop (z-domain) effects, reference spur / jitter / phase noise, the `f_ref`-to-trim-code keying rule, and anything about silicon. It also does **not** restore the original run's host or PDK provenance, which is unrecoverable: the engine build differs (ngspice-47 here against the original's stated ngspice-46), the host is a fleet Spot instance rather than the original's unnamed x86-64 Linux worker, and the cmos5l revision is inferred from this host's bundle rather than read from the runner.
