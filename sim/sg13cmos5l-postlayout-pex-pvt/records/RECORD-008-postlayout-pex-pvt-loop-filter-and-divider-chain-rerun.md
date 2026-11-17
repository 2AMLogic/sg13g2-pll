# RECORD-008: rerun of RECORD-004's post-layout (PEX) `loop_filter` and `divider_chain` arms on the batch fleet (issue #326)

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #326 (part 4/4 of #215, item 9 provenance migration). Append-only.
  This record reruns the two runners of
  `RECORD-004-postlayout-pex-pvt-loop-filter-and-divider-chain.md` and is the
  `ADDENDUM-RERUN` target of `ADDENDUM-004-record-004-superseded.md`. It
  neither edits that record nor any historical CSV; its CSVs are new paths
  (`corners/*-rerun326.csv`). It supersedes only that record's *evidence
  claim* for `pll_loop_filter` and `pll_divider_chain`.
- **Headline.** Mixed reproduction. The divider chain reproduces (division
  ratio N identical on all 36 rows; the schematic control arm and the
  post-layout arm). The loop filter's capacitances (<= 0.06 %) and its
  post-layout-vs-schematic deviations (R1 -8.88 % / fz -19.16 % / fp -41.37 %
  vs the original -8.89 / -19.15 / -41.36) reproduce; its **absolute `R1`
  does not** (-3.6 % at `res_bcs`, +1.0 % at `res_typ`, +6.0 % at `res_wcs`,
  both arms), so every `R1`-derived `fz`/`fp` moves with it. Section 3 shows
  a single deck gives the original `R1` exactly on the pinned
  `ihp-sg13cmos5l` git checkout and the batch value on the fleet image's
  tree: the shift is PDK content, not the design. The rerun therefore
  reports what the batch image produced; it does not show that the pinned
  environment reproduces the whole grid.
- **Corner coverage**: the original's own matrices, uncut. `pll_loop_filter`:
  2 arms x 3 `res_*` corners x 3 temperatures = 18 AC units, expanded
  analytically to the 54-row x 3 `mom_frac` matrix (`lf_results`) and the
  27-row control (`lf_control`). `pll_divider_chain`: 36 transient units
  (post-layout 14, schematic 22), `div_results` 36 rows, `div_control` 20
  rows. All 54 units returned exit code 0 and a measured row; **no `NA` row**
  in either CSV (the original has none either).
- **DUT**: the *historical* layout, not today's design: the `pll_loop_filter`
  (layout record `20260923-020931-a95a887-dirty`) and `pll_divider_chain`
  extractions as committed at `bd62f15` (the commit that introduced
  RECORD-004), with the testbench, templates and the two sibling campaigns'
  frozen schematics (`sg13cmos5l-loop-filter-momcap`,
  `sg13cmos5l-divider-nrange-retiming`) read unmodified from a
  `git archive bd62f15` in a scratch directory. No re-extraction was done.
  Per the migration table, recovered provenance does not make stale layout
  evidence current; item 9 stays `unmet` until #218. One batch host class
  (x86-64); the original does not name its host.

## 1. Environment and provenance

- **PDK revisions.** The request names `models.pdk: ihp-sg13cmos5l`; both
  trees are involved because the `cmos5l` models are symlinks into
  `ihp-sg13g2`. The migration pins are `ihp-sg13cmos5l`
  607e18d4bd9214a52575c194b4181ef449f9252f and `ihp-sg13g2`
  5cccb161f7492697cfa52eb14dc03beb00bdca9e (the second is the `0.3.0` release
  tarball install on the submitting host, `.fetched-version` = `0.3.0`, not a
  git checkout). **They are the migration targets, not a claim about what
  ran.** A probe deck (`rerun326/pdk-probe/`, job `klt-sim-9777fe1427c3`)
  hashed the worker's files and reproduces the #325 finding:
  - `ihp-sg13cmos5l` on the worker (`/opt/pdk/ihp-sg13cmos5l`, no `.git`, no
    version stamp) is **not the pinned git checkout**: `cornerRES.lib` is a
    regular 8899-byte file, sha256 `c6d749e7...` (the pinned checkout carries
    it as a symlink into `ihp-sg13g2`, sha256 `2c185021...`), `psp103.osdi`
    `dba873bc...` (the pin's is the g2 file `2e4299c4...`). Other worker
    hashes: `cornerMOShv.lib` `5a1f862d...`, `psp103_nqs.osdi` `ad99ea64...`,
    `mosvar.osdi` `cded61b1...`, `r3_cmc.osdi` `746f86fd...`, `cap_cmomi.osdi`
    `972ff31c...`. **The worker's `ihp-sg13cmos5l` revision is unknown.**
    The loop filter loads `cap_cmomi` and `r3_cmc` from this tree, the divider
    chain loads `psp103`/`psp103_nqs`/`mosvar` from it.
  - `ihp-sg13g2` on the worker (`/opt/pdk/ihp-sg13g2`, no stamp): file hashes
    equal the submitting host's `0.3.0` tree and its pre-2026-10-15 backup
    (`cornerRES.lib` `2c185021...`, `psp103.osdi` `2e4299c4...`,
    `psp103_nqs.osdi` `839b1644...`, `mosvar.osdi` `25e64a37...`,
    `r3_cmc.osdi` `4fead17b...`). File identity, not a revision.
  - The pinned `ihp-sg13cmos5l` checkout used for the control is
    `~/share/pdk/ihp-sg13cmos5l.bak-20261015T153923Z` (`git rev-parse HEAD` =
    607e18d4bd9214a52575c194b4181ef449f9252f, `git status --porcelain` empty,
    read 2026-11-12), paired with `ihp-sg13g2.bak-20261015T153923Z`
    (`.fetched-version` `0.3.0`).
  - `klt` envelopes carry `provenance.pdk.version: null` (upstream
    2AMLogic/klayout-tools#3070); deck-list reports here carry a
    `worker_environment` block whose `pdk` section reports
    `pdk stamp unreadable` and `worker_stamp_unavailable` (the open
    2AMLogic/klayout-tools#5328 covers the missing worker PDK identity).
    The probe is the hand-recorded substitute.
- **Tool.** Client `klt 0.9.2.dev699+gbfb96f18cb1b`; batch runner `klt 0.9.0`
  (`runner_compatibility: match`); ngspice-46 on the worker
  (`/usr/local/bin/ngspice`) and on the submitting host
  (`~/.local/bin/ngspice`, sha256
  `dc859418bedd0478ff439a2d3e2e09f4386a7f4d5e3f17671953e101a000cc60`, used
  only for the local control). The original cites `ngspice-46`, `klt 0.2.0`;
  no extraction was rerun.
- **Where it ran.** `aws-batch-fleet`, us-east-1, Spot, `m7i.4xlarge`,
  AMI `ami-095c25ae241a4d360`, x86-64.
- **Inputs, sha256 as extracted from `bd62f15`**:

  | File | sha256 |
  |---|---|
  | `netlist-snapshots/pll_loop_filter.pex.spice` | `802299f919fe24f28bac6d8b58b35e9b815fe763dc5a4a54538b40b334af0a8c` |
  | `netlist-snapshots/pll_divider_chain.pex.spice` | `9f81e60e87a8bad026d9063e6dc5301e045e7d9386e28a47cc7ecbc5565bcca8` |
  | `sg13cmos5l-loop-filter-momcap/netlist-snapshots/loop_filter_resized.spice` | `8dabfb693f3ed8ff47875a50883998530b38b26013abebe16bc367a31c8494b6` |
  | `sg13cmos5l-divider-nrange-retiming/netlist-snapshots/divider_chain_repaired.spice` | `d7f864889ab9fcfbce591bb64acbc3191a1bf781b280851d6a2ce1fdca6f4cfb` |
  | `testbench/run_loop_filter.sh` | `d27dcc47275dcab2a1523af60918d990efb5dfaa8018c16118d7a1784ee4b0a1` |
  | `testbench/run_divider_chain.sh` | `7c2d60da56707761aa7b44f0bfc07b186750b9c0089e451d41063cc4b502fd17` |
  | `testbench/tb_lf_ac.sp.tmpl` | `592c11b474781110e5d6c98f142038767cab6d377d05889c8d610b3d0ccf066b` |
  | `testbench/tb_div_func_pex.sp.tmpl` | `048ffe880d58e225f89b66fa2a638a1aa5e3451675988fda9f4a54a83a00554e` |
  | `sg13cmos5l-divider-nrange-retiming/testbench/tb_div_func.sp.tmpl` | `09cfb2b3bd893d1ba977ea12a70da7f63fdaf053e0d411a2bae013d222626968` |
  | `testbench/pex-to-ngspice.py` | `952077458be90a1180e56acdfce7f581782431f00b44e3f8df39a885cc562fd3` |
  | `testbench/make-inst.py` | `a89d85622d213a74e67437b71b1ba20b258e991c37ce23f19e4e034e75a581a2` |

## 2. Method and what was adapted

Same method as RECORD-006 (issue #325): the two historical runners loop
`ngspice -b` and parse stdout; hand-launching that loop is not allowed on the
dispatch host, and rewriting them into corner requests would mint a different
artifact. So the runners ran **byte-for-byte as committed**, with only their
`ngspice` replaced by a record/replay bridge
(`rerun326/tools/ngspice-bridge`, `passdeck.py`): on a miss it records the
exact deck the runner rendered (and its includes) and returns nothing; the
recorded decks become one `klt sim` **`decks`** request (`backend: batch`,
`--wait-for-capacity 600`); on replay the bridge feeds each unit's stdout to
the runner, which parses it as it would a local run. Both runners' decks are
independent of one another, so each needed one record pass and one replay
pass.

**Adaptations, all mechanical and disclosed:** absolute work-directory
includes became relative; absolute `<pdk root>/...` paths became
`$PDK_ROOT/...` (expanded on the worker); the runners' `.spiceinit` `osdi`
lines became `pre_osdi` lines at the top of each deck's first `.control` block,
and the divider runner's `set num_threads=1` was carried over the same way.
For the *record* pass only, the loop-filter bridge printed 181 placeholder
rows per missed deck so the runner would not abort before rendering all 18
decks (`BRIDGE_FAKE_ROWS`, see the bridge); the placeholders never reach a
committed CSV, which come from the replay pass over real batch output.

Commands (scratch paths as used; scripts under `rerun326/tools/`, requests
under `rerun326/requests/`, reports under `rerun326/reports/`):

```
git archive bd62f15 | tar -x -C /tmp/r326/hist
# record: PATH=<bridge shim> BRIDGE_FAKE_ROWS=181 LF_WORK=... run_loop_filter.sh ; DIV_WORK=... DIV_JOBS=1 run_divider_chain.sh
python3 rerun326/tools/passdeck.py convert <req dir> $HOME/share/pdk ihp-sg13cmos5l <work>/.spiceinit <work>
python3 rerun326/tools/split_div.py        # 36 divider decks -> 9 requests of 4
klt sim request.json --backend batch --wait-for-capacity 600 -o <out> --report-out <report> --format json
python3 rerun326/tools/passdeck.py ingest <out>
# replay: same runners, same bridge, results from the cache
bash rerun326/tools/ctl.sh                 # section 3 local control (single deck)
```

| Run | Units | Batch job | Result |
|---|---:|---|---|
| probe (1 loop-filter deck) | 1 | `klt-sim-f04550f45a71` | pass |
| loop filter | 18 | `klt-sim-bf8d98d51465` | 18 pass (8 s) |
| divider chain, one 36-deck job (attempt 1) | 36 | `klt-sim-951e040a0b54` | **failed**: `state: timeout`, `job exceeded 3600s`, nothing collected |
| divider chain, one 36-deck job (attempt 2) | 36 | `klt-sim-b01008b669e6` | **abandoned by me** after ~15 min: `--max-units-per-job 6` did not split the `decks` request (one job was submitted), so it would have hit the same fleet ceiling |
| divider chain p0..p8 | 4 each | `klt-sim-dd3541eb2aec`, `-edc7077eeb9c`, `-b57eb0e9fc3b`, `-ac6587d80691`, `-1d7bb8434a9b`, `-ee6fad6d22e7`, `-62a5a02e2d19`, `-9e1e4931602a`, `-85461c80ec2d` | 36 pass (934-1710 s each) |
| PDK probe | 1 | `klt-sim-9777fe1427c3` | pass |

"pass" is `klt`'s own meaning: the engine exited 0. It says nothing about the
electrical result. The two divider failures are retained here, not hidden; the
fleet's whole-job ceiling (3600 s) against the 36-deck runtime is a tool gap
filed upstream as 2AMLogic/klayout-tools#5377 (section 6).

## 3. Attribution control (local, one deck, the pinned git checkout)

One deck (post-layout `res_typ`, 27 C, `lf_ac_postlayout_res_typ_27.sp`) was
run with one local `ngspice -b` against (a) the submitting host's current
`ihp-sg13cmos5l` tree (= the worker's content) and (b) a scratch PDK root
whose `ihp-sg13cmos5l`/`ihp-sg13g2` link to the pinned checkout pair named in
section 1, with the runner's own `.spiceinit`. `R1` by the runner's rule
(max `Re Z`, 1 kHz..100 MHz):

| Source | `R1` (ohm) |
|---|---|
| Original (`lf_results.csv`, RECORD-004) | 2.939850e5 |
| Batch rerun (`lf_results-rerun326.csv`) | 2.967860e5 |
| Local, current tree | 2.967860e5 |
| Local, pinned checkout | **2.939850e5** |

So the `R1` shift is caused by the `ihp-sg13cmos5l` tree content (`cornerRES`
and `r3_cmc`), the batch bridge is faithful (local current tree = batch to every
printed digit), and the original value is reproduced on the pinned checkout.
Outputs are in `rerun326/pdk-probe/ctl-lf-*.out`. The control covers one of
18 loop-filter decks; the other `res_*` corners are attributed by the same
mechanism but **not** separately controlled. The divider chain, which has no
resistor, was not controlled (it reproduces without one).

## 4. Results: `pll_loop_filter` (`corners/lf_results-rerun326.csv`, 54 rows; `lf_control-rerun326.csv`, 27)

Nominal rows (27 C, `mom_frac` 0), original `lf_results.csv` vs rerun:

| Arm | `res_*` | `R1` orig -> rerun | `C1` | `C2` | `fz` (Hz) orig -> rerun | `fp` (Hz) orig -> rerun |
|---|---|---|---|---|---|---|
| post-layout | typ | 2.940e5 -> 2.968e5 (+1.0 %) | 2.267e-12 (same) | 2.342e-13 (same) | 2.388e5 -> 2.366e5 | 2.550e6 -> 2.526e6 |
| post-layout | bcs | 2.657e5 -> 2.561e5 (-3.6 %) | same | same | 2.643e5 -> 2.742e5 | 2.820e6 -> 2.925e6 |
| post-layout | wcs | 3.223e5 -> 3.417e5 (+6.0 %) | same | same | 2.179e5 -> 2.055e5 | 2.327e6 -> 2.195e6 |
| schematic | typ | 3.227e5 -> 3.257e5 (+0.9 %) | 1.670e-12 (same) | 1.217e-13 (same) | 2.954e5 -> 2.926e5 | 4.348e6 -> 4.308e6 |
| schematic | bcs | 2.920e5 -> 2.816e5 (-3.6 %) | same | same | 3.265e5 -> 3.385e5 | 4.799e6 -> 4.974e6 |
| schematic | wcs | 3.534e5 -> 3.744e5 (+6.0 %) | same | same | 2.697e5 -> 2.545e5 | 3.975e6 -> 3.753e6 |

- **Reproduced**: `C1` (largest change over all 54 rows 0.004 %), `C2`
  (0.06 %); the post-layout-vs-schematic deviation at `res_typ`, 27 C:
  `R1` -8.88 % (original -8.89 %), `fz` -19.16 % (-19.15 %), `fp` -41.37 %
  (-41.36 %), i.e. the original's headline that the extracted parasitics
  pull the pole/zero pair down, with the same factor.
- **Not reproduced**: absolute `R1`, over all 54 rows -3.62 % to +6.04 %
  (post-layout) and -3.57 % to +5.97 % (schematic), monotone in the
  resistor corner (bcs lowest, wcs highest); `fz` and `fp` follow
  (`fz` up to 5.7 %, `fp` up to 5.7 % per row). Section 3 attributes this to
  the resistor-model tree content.
- **Control (`lf_control`, schematic arm vs the loop-filter campaign's
  committed `results_resized.csv`)**: the original reports `R1` deltas
  -6.76 % to -5.70 %, `fz` +7.42 % to +8.63 %, `fp` -11.72 % to -10.49 %;
  the rerun reports `R1` -9.21 % to -1.07 %, `fz` +2.37 % to +11.58 %, `fp`
  -15.62 % to -8.32 %. `C1`/`C2` deltas are unchanged (-1.29 % to -1.26 %,
  +21.29 % to +21.76 %). The committed campaign values were measured on a
  different resistor model, so the batch image moves this control's deltas
  across zero at `res_wcs`; the control is not clean on the fleet image.

## 5. Results: `pll_divider_chain` (`corners/div_results-rerun326.csv`, 36 rows; `div_control-rerun326.csv`, 20)

Division ratio `N = (tdiv_b - tdiv_a) / (tck_b - tck_a)`, per row, original
`div_results.csv` vs rerun:

- **Reproduced**: N is identical on all 36 rows to the printed digits (64.000
  baseline, 65 / 66 / 68 / 72 / 80 / 95 / 96 / 106 / 127 for the programmed
  words, both arms, all PVT points). The 22 schematic rows agree with the
  original in every measured column to <= 2.3e-5 relative (`idd_a`, 20 of 22
  rows differ in the last printed digit, <= 8.9e-6). The 14 post-layout rows
  agree to <= 1.5e-4 relative on `ck1_max`, `fb_*`, `dvo_*`, `ck1/2_min`.
- **Differs, post-layout arm only**: `ck3_min`/`ck4_min`/`ck5_min`
  (millivolt-scale undershoot, e.g. `ck5_min` -5.457e-3 -> -5.284e-3 V) by up
  to 4.2 % / 2.8 % / 3.2 %, and the average supply current `idd_a` by up to
  0.51 % (-8.1976e-4 -> -8.2395e-4 A), 13 of 14 rows. These are the columns a
  tiny change in the model tree moves; none feeds N.
- **Differs, no effect on N**: the first-edge times `tdiv_a_s`/`tdiv_b_s` on
  two post-layout rows (`mos_ff`, -40 C: word `000000`, `tdiv_a` 6.50115e-7 ->
  6.60115e-7 s; word `111111`, `tdiv_a` 1.65011e-6 -> 1.29011e-6 s). On each
  row `tdiv_a` and `tdiv_b` shift by the same amount (10 ns and 360 ns), i.e.
  the measurement window opened at a different divider output edge, so
  `tdiv_b - tdiv_a` and N are unchanged. The original's `tdiv_a` at these two
  corners is where the measurement started, not a property of the divider.
- `div_control` (schematic arm vs the campaign's committed `func.csv`): the
  committed-vs-control N delta stays 0.0 ppm on every row; `idd` deltas move
  from 0.0000 % to at most 0.0009 % in magnitude.
- Corner coverage is the original's: post-layout at `mos_tt` 27 C (baseline +
  9 programmed words) plus `mos_ss` 125 C and `mos_ff` -40 C (baseline + the
  `111111` edge word); no point was dropped, none returned `NA`.

## 6. What this does and does not support

- It supports: the divider chain's division ratio across the programmed range
  and the PVT edges is reproducible on the fleet (36/36), post-layout and
  schematic; the loop filter's capacitances and the post-layout-vs-schematic
  deviation ratios are reproducible; the 8.9 % `R1` / 19 % `fz` / 41 % `fp`
  post-layout shifts stand.
- It does **not** support, as measured on the fleet image, the loop filter's
  absolute `R1`, `fz`, `fp` (PDK-content shift, section 3), nor the original
  control deltas against the campaign's committed CSV. The pinned-tree
  behaviour of the full 18-deck grid was not rerun (no batch image carries the
  pin; the dispatch host does not allow a hand-run grid); only one deck was.
- It is not a lock, loop-bandwidth or repaired-design result. The DUT is the
  `bd62f15` extraction (RECORD-004's own); the current layout is not measured.
- **Consumers were not re-pointed.** `sum`, `src`, `prop`, the bench README
  and the spec still cite RECORD-004. No figure is *replaced* by this rerun:
  the loop filter's differing values are on a PDK tree that is not the pinned
  one, and the divider chain's reproduced values are identical to the original
  to the digits the consumers cite. The gate-visible link is the addendum.
- **Gaps (upstream)**: 2AMLogic/klayout-tools#5328 (worker PDK identity) and
  #3070 (null `provenance.pdk.version`) are existing issues; this run adds one
  new tool gap (`--max-units-per-job` ignores `decks` requests, and a 36-deck
  job exceeds the fleet's 3600 s ceiling with nothing collected), filed as
  2AMLogic/klayout-tools#5377. The pinned-revision worker image is a worker/fleet-spec
  change, not this repo's.
