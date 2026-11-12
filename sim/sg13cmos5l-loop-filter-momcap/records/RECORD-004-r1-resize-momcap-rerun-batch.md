# RECORD-004: rerun of RECORD-002's post-resize R1/C1/C2 sensitivity on the batch fleet (issue #321)

- **Slug**: `sg13cmos5l-loop-filter-momcap`
- **Issue**: #321 (split from #214, item 9 provenance migration, Part of #199). Append-only. Reruns the bench of `RECORD-002-r1-resize-momcap.md` and is the `ADDENDUM-RERUN` target of `ADDENDUM-002-record-002-superseded.md`. It edits neither the original nor its CSVs; new data is `../corners/results_resized_rerun321.csv`.
- **DUT**: ``loop_filter` as resized at `ffec56a`: `XR1` rppd `w=0.6u l=810u`, C1/C2 unchanged (`../netlist-snapshots/loop_filter_resized.spice`, unmodified)`. Corner coverage: the original's full grid, 3 process (`res_typ`/`res_bcs`/`res_wcs`) x 3 temperature (-40/27/125 C) x 3 uniform MOM-cap fractions (-20/0/+20 %) = 27 rows (R1 measured per process x temperature = 9 decks; C1/C2 measured at 27 C and checked at -40/125 C; the MOM band is applied analytically exactly as in `run.sh`). Supply is not swept (the DUT has no active device), as in the original.
- **Not rerun**: `testbench/tb_composite_ac_crosscheck.sp` (RECORD-001's composite AC cross-check) was not part of this grid.
- **Tool / host**: `klt sim --backend batch --wait-for-capacity 600` (client `klt 0.9.2.dev868+g937ab1c98ca5`, runner klt 0.9.0) on the Spot batch fleet; ngspice-46 (`/usr/local/bin/ngspice` on the runner). Submitted from `loom-worker-1`. The originals state no host or ngspice build beyond "ngspice-46, x86-64 Linux" (RECORD-001 Tooling line), so host equivalence is unknown.
- **Batch jobs**: single-corner probe `klt-sim-ace9d0bf810c` (as-drawn R1, `res_typ`, 27 C; `c7i.8xlarge` spot, exit 0, `rval = 7.805817e+03`), then the grid `klt-sim-c165c43bf163` (24 decks shared by this record and its sibling, `m7i.4xlarge` spot, exit 0, 24/24 pass). A previous attempt's grid submit failed with `batch_no_capacity` (job `klt-sim-b25621d67592`, `BATCH_MAX_VCPU=224`, quota shared with `ci-spot`) and was never run locally; this is the retry. No local grid was run.
- **Command**: `python3 -I testbench/gen_rerun321.py`; from `testbench/`: `klt sim rerun321.request.json --backend batch --wait-for-capacity 600 -o <outdir> --format json` (probe: the same with `probe.request.json`); `python3 -I testbench/collect_rerun321.py <outdir>` writes the CSVs.
- **PDK revisions (limitation, read first)**: the request names `models.pdk: ihp-sg13cmos5l`; the runner resolves it from its own image (`/opt/pdk`) and exposes no git revision or stamp (`pdk stamp unreadable`, comparison `not_comparable`). `cornerRES.lib` and the `cap_cmomi`/`cap_cmomf`/`r3_cmc` OSDI objects all resolved on the runner: every unit exits 0 with real values and each unit's `host_resolved` lists the four `$PDK_ROOT/...` paths. The tree the run is attributed to is the unified-repository fleet bundle, store version `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14` (not a `git rev-parse`; bundle sha256 `3195ba7f3a74e91fc4eced64102c9d61b00d8eadcf5e795d36d926d40ab4ad31`, `.pdk-store.json` of this host's `~/share/pdk/ihp-sg13cmos5l`, no `.git`). That attribution is **inferred**, not read from the runner: one local single-deck `ngspice -b` of the probe deck against that tree gives the identical `rval = 7.805817e+03`. It is **not** the legacy split-repository commit that `PDK-PIN` in `sim/README.md` still names (re-stamp is #250, out of scope). The ihp-sg13g2 tree (CMOS5L model cards/OSDI are symlinks into it) is a release install, `.fetched-version` `0.3.0`, i.e.
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e as established in `sim/provenance-migration.md` (the host tree is not a git checkout, so this rests on the version marker, not a `git rev-parse`; the runner's own tree is not independently established). Host-tree sha256: `cornerRES.lib` `c6d749e72cfa2e06e4a14fac3f5662541bf6197b89265ecbedd632fd3503c425`; `cap_cmomi.osdi` `972ff31c1dd8658f7399f2ec9212d0220344c356a77570b5b3ee925155119a83`; `cap_cmomf.osdi` `d44927b3dbcc9a0906125da35fbb9cb23d9abdf20f6dddda0394e81fb165ac18`; `r3_cmc.osdi` `746f86fd1b89c309cbec7b23e661a66ee80b2d897ea229bc8e3fcc3757a673c3`.
- **Reproduction is not byte-identical, and the cause is PDK content**: the pre-migration tree (607e18d4) reproduces the originals' `7.794170e+03` for the probe corner; the current tree's own `cornerRES.lib` (no longer a symlink into ihp-sg13g2) gives `7.805817e+03`. The shift below is real PDK content, not noise. C1/C2 are identical to the original (`cap_cmomi` unchanged, no tempco).
- **Rebuilt DUT**: the benches measure standalone `rppd`/`cap_cmomi` instances (`testbench/tb_extract_r.sp.tmpl`, `tb_extract_c.sp.tmpl`, unchanged since `ffec56a`; the `$PDK_ROOT`/`$PDK` tokens are the #43 fix, which RECORD-001 records as byte-identical to the pre-fix numbers), with the geometry of the frozen snapshots `netlist-snapshots/loop_filter.spice` / `loop_filter_resized.spice`. Decks differ from `run.sh`'s only in `pre_osdi` lines inside `.control` (hoisted by ngspice) instead of a `.spiceinit`, and in the PDK path being the runner's `$PDK_ROOT`.

## Result vs the original

| Metric | Original | Rerun |
|---|---|---|
| R1 nominal (`res_typ`, 27 C) | 3.442341e+05 ohm | 3.476412e+05 ohm |
| R1 full PVT range | 306.858 - 386.395 kOhm | 295.284 - 410.538 kOhm |
| fz nominal (mom_frac 0) | 0.2734 MHz | 0.2707 MHz |
| fp nominal (mom_frac 0) | 4.89 MHz | 4.84 MHz |
| fz full matrix (27 rows) | 0.203 - 0.383 MHz (x1.889) | 0.191 - 0.398 MHz (x2.085) |
| fp full matrix | 3.63 - 6.86 MHz | 3.42 - 7.13 MHz |
| fz process+temp only (mom_frac 0) | x1.259 | x1.390 |
| fz MOM band only (`res_typ`, 27 C) | x1.500 | x1.500 |
| C1 / C2 nominal | 1.691196 pF / 100.1529 fF | 1.691196 pF / 100.1529 fF (identical) |

Per-row maximum relative difference from `../corners/results_resized.csv`: R1 0.99 % - 6.25 %, fz/fp 0.98 % - 5.88 %; C1/C2 exactly 0.

The resized R1 moves more than the as-drawn one: the nominal scale vs the as-drawn rerun is 44.54x (original record: 44.17x; DR-006 settled on ~x44.2), and the full-PVT R1 range is 295.3 - 410.5 kOhm against the original 306.9 - 386.4 kOhm, i.e. a wider process/temperature spread (fz process+temp x1.390 vs x1.259). The headline "R1 lands at 44.15x-44.18x the as-drawn value across every PVT corner" in RECORD-002 does not reproduce on the current PDK content: the rerun's per-row ratio of resized to as-drawn R1 is 42.74x - 46.52x. This is a finding to carry to the consumers (spec, design/README.md, loop-bandwidth models), not something this record changes; per the ratified spec rule, no spec value was edited here.

## What this does not bound

Everything the original did not (mismatch, the loop-bandwidth/phase-margin figure, other blocks), and anything about silicon. This record replaces the original's *evidence claim* for the numbers above only; it does not restore the original run's host or PDK provenance, which is unrecoverable.
