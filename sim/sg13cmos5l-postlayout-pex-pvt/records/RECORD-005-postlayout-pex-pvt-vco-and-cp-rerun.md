# RECORD-005: rerun of RECORD-001's post-layout (PEX) PVT matrices (`vco`, `cp`, RC attribution) on the batch fleet (issue #323)

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #323 (part 1/4 of #215, item 9 provenance migration). Append-only.
  This record reruns the three matrices of `RECORD-001-postlayout-pex-pvt-vco-and-cp.md`
  and is the `ADDENDUM-RERUN` target of `ADDENDUM-001-record-001-superseded.md`.
  It neither edits `RECORD-001-postlayout-pex-pvt-vco-and-cp.md` nor any
  historical CSV; its CSVs are new paths (`corners/*-rerun323.csv`). It
  supersedes only that record's *evidence claim* for `pll_vco` and `pll_cp`;
  it is not evidence for RECORD-002, -003 or -004.
- **Corner coverage**: the original's own matrices, unchanged and uncut.
  `pll_vco`: 3 PVT bundles (typ `mos_tt/res_typ/27 C`, slow `mos_ss/res_wcs/125 C`,
  fast `mos_ff/res_bcs/-40 C`) x 4 band codes x 5 VCTRL points x 2 arms = 120
  units. `pll_cp`: 17 PVT points (5 MOS corners x 3 temperatures at 3.3 V, plus
  `mos_tt` 27 C at 3.0 V and 3.6 V) x 6 trim currents x 3 switch states x 2 arms
  = 612 units. RC attribution: 7 netlist variants x 3 bundles x band codes
  00/11 x 5 VCTRL = 210 units. All 942 units returned a measurement; none `NA`.
- **DUT**: the *historical* layout, not today's design: the routed GDS of layout
  record `20260830-204105-457cf5b` as committed at `d5355e1` (the commit that
  introduced RECORD-001), the schematic snapshots and testbench templates at
  that same commit, all read unmodified from a `git archive d5355e1` in a
  scratch directory. Per the migration table, evidence of a stale layout is not
  made current by recovered provenance; item 9 stays `unmet` until #218.
- **Reproduce**: see "Commands" below.

## 1. Environment and provenance

- **PDK revisions.** The request names `models.pdk: ihp-sg13cmos5l`; both trees
  are involved because the `cmos5l` models are symlinks into `ihp-sg13g2`.
  The pins this migration uses are `ihp-sg13cmos5l`
  607e18d4bd9214a52575c194b4181ef449f9252f and `ihp-sg13g2`
  5cccb161f7492697cfa52eb14dc03beb00bdca9e. **What this run could actually
  verify is weaker, and is stated rather than papered over:**
  - Submitting host (`loom-worker-2`, x86-64): `~/share/pdk/ihp-sg13g2/.fetched-version`
    reads `0.3.0`. `~/share/pdk/ihp-sg13cmos5l` is **not a git checkout** on this
    host; its `.pdk-store.json` records store version
    `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14`, bundle sha256
    `3195ba7f3a74e91fc4eced64102c9d61b00d8eadcf5e795d36d926d40ab4ad31`, synced
    2026-10-15. That identifier is not the `607e18d4` pin, and this run did not
    establish how the two relate, so **the `cmos5l` pin is not independently
    verified here**.
  - Batch worker: the worker image PDK is `/opt/pdk` and reports
    `stamp_scheme: null` (`environment.remote.worker_environment.pdk`), i.e. it
    carries no revision stamp, so **the worker's own PDK revision is unknown**.
    What is evidenced: `klt` staged this host's `cornerMOShv.lib` (source sha256
    `5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a`) and
    `cornerRES.lib` (`c6d749e72cfa2e06e4a14fac3f5662541bf6197b89265ecbedd632fd3503c425`)
    to the worker (`staged_model_inputs`, `rewritten: true`); the four OSDI
    objects (`psp103`, `psp103_nqs`, `mosvar`, `r3_cmc`) were resolved from the
    worker's `$PDK_ROOT` (`osdi_preload_runner_resolved`), and their worker-side
    hashes are **not** reported. Local copies are sha256 `dba873bc...` (psp103),
    `ad99ea64...` (psp103_nqs), `cded61b1...` (mosvar).
  - `klt` envelopes carry `provenance.pdk.version: null` (upstream
    2AMLogic/klayout-tools#3070), hence the hand-recorded values above.
- **Tool.** Client `klt 0.9.2.dev661+g1de5c0432aad` (commit
  `1de5c0432aadd774f1d0088b9d3169df8f39766d`); batch runner `klt 0.9.0`
  (`runner_compatibility: match`); ngspice-46 on both the submitting host
  (`~/.local/bin/ngspice`, sha256 `dc859418bedd0478ff439a2d3e2e09f4386a7f4d5e3f17671953e101a000cc60`)
  and the worker (`/usr/local/bin/ngspice`, same banner and creation date; its
  binary hash is not reported). The original used `ngspice-46`, `klt 0.4.0`.
- **Where it ran.** `aws-batch-fleet`, us-east-1, Spot `c7i.8xlarge`
  (Intel Xeon Platinum 8488C), AMI `ami-095c25ae241a4d360`. The original ran
  on an x86-64 Linux host that is not named; this does not prove that host.
- **Extraction rerun.** `extraction/run-pex.sh` was rerun unmodified from the
  `d5355e1` archive with the client `klt` above. Element counts are identical
  to RECORD-001 sec 1.3 for every block, but the extracted R totals are 0.6-2.4 %
  lower than the originals while C totals reproduce. The cause was not
  investigated (the client `klt` moved from `0.4.0` to `0.9.2`); it is a
  candidate contributor to the small `pll_vco` shift in sec 2.

  | Block | R count | C count | sum R, original (ohm) | sum R, rerun (ohm) | sum C (fF), original = rerun |
  |---|---:|---:|---:|---:|---:|
  | `pll_pfd` | 264 | 37 | 2 900.36 | 2 847.952 | 680.65 |
  | `pll_cp` | 80 | 18 | 914.86 | 899.765 | 219.40 |
  | `pll_loop_filter` | 2 | 2 | 4.84 | 4.840 | 1.74 |
  | `pll_vco` | 170 | 33 | 2 393.04 | 2 358.986 | 558.81 |
  | `pll_divider_chain` | 1 264 | 142 | 44 894.26 | 44 608.799 | 10 389.76 |
  | `pll_lock_detector` | 151 | 23 | 1 292.67 | 1 262.174 | 305.12 |

  The new netlists are in `rerun323/netlist-snapshots/`. Only `pll_vco` and
  `pll_cp` were simulated; the other four are extracted for completeness.

## 2. Results

Original values referred to below are RECORD-001's own run, i.e. the
`d5355e1` copy of the CSVs (`git show d5355e1:sim/sg13cmos5l-postlayout-pex-pvt/corners/...`).

### 2.1 `pll_vco` Kvco matrix (`corners/results-rerun323.csv`, 120 rows)

- Post-layout arm: 217.2 - 795.6 MHz over the matrix (60 units). Schematic
  control arm: 431.6 - 1575.6 MHz.
- Post-layout / schematic frequency ratio: 0.477 - 0.531, mean 0.508. At
  `d5355e1` the same ratio was 0.477 - 0.531, mean 0.507. The headline finding
  of RECORD-001 (the extracted VCO runs at about half its schematic
  frequency) **reproduces**.
- Point-by-point against the `d5355e1` CSV: post-layout arm max |deviation|
  2.91 %, mean -0.32 %; schematic arm max 3.08 %, mean -0.34 %. The schematic
  control arm (no extracted R/C) moves by a similar amount, so most of the
  shift is the host/ngspice/PDK-staging difference rather than the
  re-extraction; this was not separated further.

### 2.2 `pll_cp` DC matrix (`corners/cp_results-rerun323.csv`, 612 rows)

- The original's `.dc Vout 0.15..VDD-0.15 step 0.05` sweep plus nearest-VDD/2
  selection is replaced by an operating point at `Vout = VDD/2`
  (1.5 / 1.65 / 1.8 V), which lies exactly on the original sweep grid, so the
  same point is measured. This is a method change, disclosed here.
- Schematic arm vs original `cp_results.csv`: max |deviation| 0.096 %, mean -0.011 %.
- Post-layout arm, `up` and `dn` states: max |deviation| 8.3e-5 and 6.1e-5
  (relative), i.e. reproduces.
- **Post-layout arm, `both` state: 43 of 102 units deviate by more than 5 %,
  worst +107 % (`mos_tt` 125 C, iref 20u: original -7.82e-10 A, rerun +5.70e-11 A).**
  With UP and DN both asserted the delivered current is the difference of two
  near-equal currents, so the values are nA-scale or smaller and the sign can
  flip; the original `.dc` sweep and this operating point need not agree
  there. This is retained, not corrected, and it is not a reproduction of
  those rows. The `up`/`dn` rows that carry the trim-table claim reproduce.

### 2.3 RC attribution (`corners/rc_attribution-rerun323.csv`, 210 rows)

Max |deviation| against the `d5355e1` CSV 3.08 %, mean -0.34 %, consistent with
sec 2.1: the attribution conclusion of RECORD-001 does not move.

## 3. Discrepancy found in the base tree (not fixed here)

On the base, `corners/results.csv` and `corners/rc_attribution.csv` are **not**
the `d5355e1` values that RECORD-001's text describes: commit `ff8b653` (#106)
overwrote both with a rerun on the locality-routed `pll_vco` (layout record
`20260921-155747-c44fa68`), while RECORD-001's text, and `corners/cp_results.csv`,
are unchanged since `d5355e1`. This rerun follows the issue and measures the
`d5355e1` layout, so against the *current* `results.csv` it differs by a
mean of -34.7 % (post-layout arm; ratio to schematic 0.739 - 0.789 there vs
0.477 - 0.531 here). The original is left untouched as required; the
overwrite is an existing append-only gap in RECORD-001's evidence trail, for
the #215 owner to rule on. RECORD-002 documents the later layout and is a
separate sibling.

## 4. Batch jobs

Everything went through `klt sim --batch-set ... --backend batch` (default
`KLT_SIM_BACKEND=batch`) with `--wait-for-capacity 600 --capacity-retries 3
--max-in-flight 4`; no ngspice grid was hand-launched. A single-unit local
probe (`vco_postlayout`, typ / 00 / VCTRL 0.3, 3.9197 ns vs 3.9000 ns
original) validated the request shape first. No job needed a retry or a
resume. `klt` warned that the default `options.timeout_s` (3600 s) times the
unit count exceeds the fleet's 3600 s job ceiling; the jobs' reported worker
elapsed time was 7-90 s each.

| Request | Batch job id | Status | Passed/units |
|---|---|---|---:|
| `cp_postlayout_iref10u` | `klt-sim-848212cc5ef9` | pass | 51/51 |
| `cp_postlayout_iref2.5u` | `klt-sim-438f8bcd7287` | pass | 51/51 |
| `cp_postlayout_iref20u` | `klt-sim-f8f3e80167e0` | pass | 51/51 |
| `cp_postlayout_iref40u` | `klt-sim-8ad618e5bb3e` | pass | 51/51 |
| `cp_postlayout_iref5u` | `klt-sim-9ad7fa802dee` | pass | 51/51 |
| `cp_postlayout_iref80u` | `klt-sim-5b08fc45b7c4` | pass | 51/51 |
| `cp_schematic_iref10u` | `klt-sim-aa3e360c92ca` | pass | 51/51 |
| `cp_schematic_iref2.5u` | `klt-sim-be24aea928a7` | pass | 51/51 |
| `cp_schematic_iref20u` | `klt-sim-8b36b0834b76` | pass | 51/51 |
| `cp_schematic_iref40u` | `klt-sim-23b3dee18156` | pass | 51/51 |
| `cp_schematic_iref5u` | `klt-sim-2ec13f78b3f4` | pass | 51/51 |
| `cp_schematic_iref80u` | `klt-sim-c6730f0059fa` | pass | 51/51 |
| `rc_c_only` | `klt-sim-81f12c2637ed` | pass | 30/30 |
| `rc_cscale05` | `klt-sim-a0eab3f53e85` | pass | 30/30 |
| `rc_cscale10` | `klt-sim-69a9f0879d77` | pass | 30/30 |
| `rc_cscale25` | `klt-sim-896587a2f508` | pass | 30/30 |
| `rc_full` | `klt-sim-c07eb84ba9a1` | pass | 30/30 |
| `rc_none` | `klt-sim-8268f74e1d4b` | pass | 30/30 |
| `rc_r_only` | `klt-sim-81d61dd8f65a` | pass | 30/30 |
| `vco_postlayout` | `klt-sim-1897f990de3c` | pass | 60/60 |
| `vco_schematic` | `klt-sim-1a93b62f3efe` | pass | 60/60 |

Per-unit status and the job table are in `corners/jobs-rerun323.csv`.

## 5. Limitations

- Worker PDK revision unstamped; `cmos5l` pin unverified on this host (sec 1).
- Extraction is `klt 0.9.2`, not `0.4.0`; R totals differ 0.6-2.4 % from the original.
- `cp` method change (operating point instead of a DC sweep) and the `both`
  state disagreement above.
- The post-layout numbers inherit RECORD-001's own caveats: curated
  uncalibrated metal coefficients, lumped-star R model, stale layout
  (item 9 remains `unmet`, #218).
- No `klt` tool gap blocked this rerun; the only friction was that
  `--batch-set` refuses `--pdk-root` (the request's `models.pdk` and the
  environment resolve the tree instead).

## Commands

```
git archive d5355e1 | tar -x -C /tmp/r323/hist
(cd /tmp/r323/hist/sim/sg13cmos5l-postlayout-pex-pvt && \
  PDK_ROOT=~/share/pdk PDK=ihp-sg13cmos5l ./extraction/run-pex.sh)
python3 -I rerun323/gen_requests.py /tmp/r323/hist /tmp/r323/req
klt sim --batch-set /tmp/r323/req/*/request.json --max-in-flight 4 \
  --capacity-retries 3 --wait-for-capacity 600 --format json -o /tmp/r323/out
python3 -I rerun323/collect.py /tmp/r323/req /tmp/r323/batch.json corners
```
