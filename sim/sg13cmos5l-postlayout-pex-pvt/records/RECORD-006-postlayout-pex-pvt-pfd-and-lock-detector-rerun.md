# RECORD-006: rerun of RECORD-003's post-layout (PEX) `pfd` and `lock_detector` arms on the batch fleet (issue #325)

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #325 (part 3/4 of #215, item 9 provenance migration). Append-only.
  This record reruns the two runners of
  `RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` and is the
  `ADDENDUM-RERUN` target of `ADDENDUM-002-record-003-superseded.md`. It
  neither edits `RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` nor
  any historical CSV; its CSVs are new paths (`corners/*-rerun325.*`). It
  supersedes only that record's *evidence claim* for `pll_pfd` and
  `pll_lock_detector`; it is not evidence for RECORD-001, -002 or -004.
- **Headline, stated first because it changes how this record may be used.**
  The rerun did **not** run against the pinned PDK content, and a large part of
  RECORD-003's measurements **did not reproduce**. Two controls (section 3)
  attribute the non-reproduction that was checked to the fleet image's
  `ihp-sg13cmos5l` tree, not to the design: the same decks run locally against
  the pinned `ihp-sg13cmos5l` git checkout reproduce the original values
  exactly. This record therefore reports what the batch image produced; it
  does not show that the pinned environment reproduces, nor that it fails.
- **Corner coverage**: the original's own matrices, unchanged and uncut.
  `pll_pfd`: 1 PVT point (`mos_tt`, 27 C, 3.3 V) x 2 cases x 3 offsets x 2 arms
  = 12 units. `pll_lock_detector`: 522 units (R/C extraction 15, committed
  window control 102 of which 98 were distinct decks, post-layout and as-layout
  window points, the ladder/recovery set and the timestep check). All 534 units
  returned stdout and exit code 0; none needed the `trtol=1` retry
  (`corners/ld_solver_retries-rerun325.txt` is empty, as in the original). Some
  *outputs* are `NA` where the original's were not, see section 2.2.
- **DUT**: the *historical* layout, not today's design: the `pll_pfd` and
  `pll_lock_detector` extractions of layout record `20260921-155747-c44fa68`
  as committed at `07751ca` (the commit that introduced RECORD-003), with the
  testbench, templates and the two sibling campaigns' decks
  (`sg13cmos5l-closed-loop-lock`, `sg13cmos5l-lock-detector-window`) read
  unmodified from a `git archive 07751ca` in a scratch directory. No
  re-extraction was done. Per the migration table, recovered provenance does
  not make stale layout evidence current; item 9 stays `unmet` until #218.
  Single batch host class: the original's two-host (x86-64 Linux and arm64
  macOS) cross-check is **not** reproduced.

## 1. Environment and provenance

- **PDK revisions.** The request names `models.pdk: ihp-sg13cmos5l`; both
  trees are involved because the `cmos5l` models are symlinks into
  `ihp-sg13g2`. The pins this migration uses are `ihp-sg13cmos5l`
  607e18d4bd9214a52575c194b4181ef449f9252f and `ihp-sg13g2`
  5cccb161f7492697cfa52eb14dc03beb00bdca9e. **They are the migration targets,
  not a claim about what ran. What this run can show is weaker for
  `ihp-sg13g2` and, for `ihp-sg13cmos5l`, is evidence that the batch image did
  not run the pin:**
  - `ihp-sg13g2`: the submitting host's `~/share/pdk/ihp-sg13g2` is a
    release-tarball install (`.fetched-version` = `0.3.0`, not a git
    checkout). The worker's `/opt/pdk/ihp-sg13g2` has no revision stamp. A
    probe deck (`rerun325/pdk-probe/`, job `klt-sim-11b2a47361c4`) hashed the
    worker's files: `cornerMOShv.lib` `5a1f862d...`, `cornerRES.lib`
    `2c185021...`, `psp103.osdi` `2e4299c4...`, `psp103_nqs.osdi` `839b1644...`,
    `mosvar.osdi` `25e64a37...`, `r3_cmc.osdi` `4fead17b...`. These equal the
    submitting host's `ihp-sg13g2` files and the files in the pre-2026-10-15
    backup of that tree (`~/share/pdk/ihp-sg13g2.bak-20261015T153636Z`). That
    is file identity, not a revision: it supports the `0.3.0` pin but does not
    establish it.
  - `ihp-sg13cmos5l`: **the worker's tree is not the pinned git checkout.**
    `/opt/pdk/ihp-sg13cmos5l` has no `.git` and no version stamp; its
    `cornerRES.lib` is a regular 8899-byte file, sha256
    `c6d749e72cfa2e06e4a14fac3f5662541bf6197b89265ecbedd632fd3503c425`, and its
    `psp103.osdi` is `dba873bc...` (871 968 B). The pinned git checkout
    (`~/share/pdk/ihp-sg13cmos5l.bak-20261015T153636Z`, `git rev-parse HEAD` =
    607e18d4bd9214a52575c194b4181ef449f9252f, `git status --porcelain` empty,
    read 2026-11-11) carries `cornerRES.lib` as a symlink into `ihp-sg13g2`
    (sha256 `2c185021...`) and the g2 `psp103.osdi` (`2e4299c4...`). The
    submitting host's *current* `~/share/pdk/ihp-sg13cmos5l` (reprovisioned
    2026-10-15, no `.git`) has the same hashes as the worker's, so the local
    unattributed reruns below used the same non-pinned content as the fleet. How
    the non-pinned tree relates to any upstream revision was not established
    (upstream `f7bca326...` also carries `cornerRES.lib` as a symlink, so it
    does not obviously match either). **The worker's `ihp-sg13cmos5l` revision
    is unknown.**
  - `klt` envelopes carry `provenance.pdk.version: null` (upstream
    2AMLogic/klayout-tools#3070), and deck-list batch reports carry no
    `worker_environment` at all (upstream 2AMLogic/klayout-tools#5328, to
    which the probe evidence above was added). The probe is the hand-recorded
    substitute.
- **Tool.** Client `klt 0.9.2.dev661+g1de5c0432aad`; batch runner `klt 0.9.0`
  (`runner_compatibility: match`); ngspice-46 on the worker
  (`/usr/local/bin/ngspice`, sha256
  `2f7937bfd8aa02f7494167b2cc9166b6303a6252f8cb34258b12395eb125acef`) and on
  the submitting host (`~/.local/bin/ngspice`, sha256
  `dc859418bedd0478ff439a2d3e2e09f4386a7f4d5e3f17671953e101a000cc60`, used only
  for the local controls). The original cites `ngspice-46`, `klt 0.2.0` for the
  extraction it measured; no extraction was rerun here.
- **Where it ran.** `aws-batch-fleet`, us-east-1, Spot (instance types
  `m6i.4xlarge`, `m7i.4xlarge`, `c7i.8xlarge`; AMI `ami-095c25ae241a4d360`,
  x86-64). The original ran on an x86-64 Linux host and an arm64 macOS host,
  neither named in the record; this does not prove either.
- **Inputs, sha256 as extracted from `07751ca`**:

  | File | sha256 |
  |---|---|
  | `netlist-snapshots/pll_pfd.pex.spice` | `4533ebf1a61f3b97a4ec2e1cc82d3ea01064801193fbf34ca1d4b13011a30382` |
  | `netlist-snapshots/pll_lock_detector.pex.spice` | `5b320941526db4acb70f64d8811231f2ac830fac8f2be13a2989881d621086ba` |
  | `sg13cmos5l-closed-loop-lock/netlist-snapshots/pfd.spice` | `cc9657043b755854e86d11aef6d13a9ee3301fa0df19373e543d461d6138c483` |
  | `testbench/run_pfd.sh` | `0f4d346b9d471880a1c317b0f6b36187bd8459c850b19d005e90a09987e284a5` |
  | `testbench/run_lock_detector.sh` | `e3058449ce4f1ce16ae8e68892d8a54b3c918998e9fdd961b934928c7ba86fc9` |
  | `testbench/tb_pfd_pex.sp.tmpl` | `8fad443d9795d6d5554b7324b70f0a52c6bf05792482f615321b64b5bd7f0571` |
  | `testbench/tb_ld_wholecell_win.sp.tmpl` | `653d5e9bb603007e266f6e02e21eca00a816cffa24197b10ebf8b62faa2562a6` |
  | `testbench/pex-to-ngspice.py` | `ddda79d8ca9471d7c5a93c1628a3355325628c963157005215e12a1ba00fe179` |
  | `testbench/make-inst.py` | `a89d85622d213a74e67437b71b1ba20b258e991c37ce23f19e4e034e75a581a2` |
  | `testbench/derive_ld_as_layout.py` | `09d317545a87d3b358e9ecd943028f01861c1fe0b8976e8ae68db705c0ca741f` |
  | `testbench/gen_pex_ladder.py` | `ad7afc3b11f200c0f35fe44bea2c24b6665c5b9615f4f07710e0d7e6e2295ba4` |
  | `testbench/analyze_pfd_ld.py` | `1afad83b551dc25123d07a52c7b504ee9db0dd62176c5c22789e9f0a2deca0a9` |

## 2. Method and what was adapted

The two historical runners are shell scripts that loop `ngspice -b` and parse
its stdout, and the lock detector's later decks depend on earlier measured
values (the extracted `R`/`C` feed the ladder). Hand-launching that loop is
not allowed on the dispatch host, and rewriting 700 lines of runner into
`klt sim` corner requests would mint a different artifact than the one the
original evidence came from (the argument `klt sim`'s "Pre-composed decks"
section makes). So the **runners ran byte-for-byte as committed**, with only
their `ngspice` replaced by a replay/record bridge
(`rerun325/tools/ngspice-bridge`):

- on a cache **miss** the bridge records the exact deck the runner rendered
  (plus the files it includes) and returns empty output;
- `rerun325/tools/passdeck.py convert` turns the recorded decks into one
  `klt sim` **`decks`** request (`backend: batch`, `--wait-for-capacity 600`),
  `ingest` stores each unit's stdout and exit code; on a **hit** the bridge
  replays them to the runner, which parses them as it would a local run;
- the runner is rerun until no deck is pending. It took five lock-detector
  passes (9, 6, 98, 89, 320 decks; the stages depend on one another) and one
  PFD pass (12 decks).

**Adaptations, all mechanical and disclosed:** absolute work-directory
includes became relative; absolute `<pdk root>/...` model paths became
`$PDK_ROOT/...` (which the fleet expands on the worker); and the runner's
`.spiceinit` `osdi` lines became `pre_osdi` lines at the top of the deck's
first `.control` block. Nothing else in any deck changed. Because the OSDI load
mechanism changed, one deck of each kind was also run locally with the
runner's own `.spiceinit`: the PFD post-layout decks and the resistor
extraction deck gave results identical to the batch values to all printed
digits (section 3). A failed first PFD submission
(`klt-sim-911ba2235875`, request staged the same file as both an input and an
include, rejected by the runner) is retained in the log below, not hidden.

Commands (scratch paths as used; the scripts are committed under
`rerun325/tools/`, requests under `rerun325/requests/`, reports under
`rerun325/reports/`):

```
git archive 07751ca | tar -x -C /tmp/r325/hist
# PFD: PATH=<shim ngspice> PDK_ROOT=$HOME/share/pdk PDK=ihp-sg13cmos5l PFD_WORK=/tmp/r325/pfdwork run_pfd.sh   (record decks)
python3 rerun325/tools/mkdecks.py ...; klt sim request.json --backend batch --wait-for-capacity 600 ...
python3 rerun325/tools/fillres_pfd.py ...; run_pfd.sh again (replay)
# lock detector: rerun325/tools/runpass.sh N -> cycle.sh N -> (batch) -> passdeck.py ingest, N = 1..6
python3 testbench/analyze_pfd_ld.py
```

| Pass | Units | Batch job | Instance | Result |
|---|---:|---|---|---|
| PFD (attempt 1) | 12 | `klt-sim-911ba2235875` | `m6i.4xlarge`-class | **failed**, 12 `batch_job_failed` (my request staged a file twice) |
| PFD | 12 | `klt-sim-a723ec482c45` | `m6i.4xlarge` | 12 pass |
| LD 1 (R extract) | 9 | `klt-sim-bd879ac1d98a` | `m7i.4xlarge` | 9 pass |
| LD 2 (C extract) | 6 | `klt-sim-b6e198603abc` | `c7i.8xlarge` | 6 pass |
| LD 3 (window control) | 98 | `klt-sim-504580e1d3e1` | `m7i.4xlarge` | 98 pass |
| LD 4 (window, tstep) | 89 | `klt-sim-35ad882c8c08` | `m6i.4xlarge` | 89 pass |
| LD 5 (ladder) | 320 | `klt-sim-0ddf1e1a3fc9` | `c7i.8xlarge` | 320 pass |
| PDK probe | 1 | `klt-sim-11b2a47361c4` | `c7i.8xlarge` | pass |

"pass" is `klt`'s own meaning: the engine exited 0. It says nothing about the
electrical result.

## 3. Attribution controls (local, single decks, the pinned git checkout)

Two single-deck controls separate "the design changed" from "the PDK content
changed". Each ran one local `ngspice -b` of a deck the rerun used, once
against the submitting host's current tree (= the worker's content) and once
against the pinned `ihp-sg13cmos5l` git checkout (`...bak-20261015T153636Z`,
`ihp-sg13g2` sibling unchanged), with the runner's own `.spiceinit`:

| Deck | Original (RECORD-003 CSV) | Batch rerun | Local, current tree | Local, pinned checkout |
|---|---|---|---|---|
| `XRPU` rhigh, `res_typ`, 27 C: R (ohm) | 2.266979e6 | 2.069878e6 | 2.069878e6 | **2.266979e6** |
| post-layout `fblead`, 5 ns: `up_avg` / `dn_avg` (V) | 3.04913 / 0.0788793 | 0.0790796 / 0.409033 | 0.0790796 / 0.409033 | **3.049125 / 0.07887925** |
| post-layout `reflead`, 5 ns: `up_avg` / `dn_avg` (V) | 0.409110 / 0.0789217 | 0.409111 / 0.0789219 | n/a | 0.4091099 / 0.07892173 |

So the resistor-model shift and the `fblead` mode flip are caused by the
`ihp-sg13cmos5l` tree content, and the batch bridge is faithful (local current
tree = batch to every printed digit). These two controls do **not** attribute
every other difference below; they make it likely, not proven, that the ladder
and window differences (which depend on the same resistor) share the cause.

## 4. Results: `pll_pfd` (`corners/pfd_results-rerun325.csv`, 12 rows; `pfd_control-rerun325.csv`)

Duty fractions (average / 3.3 V) at the ratified 5 ns offset, original
`pfd_results.csv` at `07751ca` vs this rerun:

| Arm | Case | `up` original | `up` rerun | `dn` original | `dn` rerun |
|---|---|---|---|---|---|
| schematic | `reflead` | 11.35% | 11.35% | 1.34% | 1.34% |
| schematic | `fblead` | 1.35% | 1.35% | 11.35% | 11.35% |
| post-layout | `reflead` | 12.40% | 12.40% | 2.39% | 2.39% |
| post-layout | `fblead` | **92.40%** | **2.40%** | 2.39% | **12.39%** |

- **Reproduced (9 of 12 rows)**: the whole schematic arm (6 rows, one
  last-digit difference in a printed average), the post-layout `reflead` rows
  at all three offsets, and `pfd_control` (byte-identical, 2 rows: the
  schematic arm is -0.52 % from the committed `fixed` diagnostic, the same
  figure and causes the original discloses). The post-layout `reflead` result
  (UP duty +9.3 % / +4.9 % / +2.5 % vs schematic, DN +78 %) is the original's.
- **NOT reproduced (3 of 12 rows)**: the post-layout `fblead` rows at 5, 10 and
  20 ns. The original reports a *mode inversion* (UP holds, 92.4 % / 82.4 % /
  62.4 %, DN 2.39 %: the original's RECORD-003 section 2 finding). The batch
  rerun reads textbook `DN`-dominant (12.39 % / 22.39 % / 42.40 %, `up` 2.40 %),
  i.e. no inversion. Section 3 shows the pinned `ihp-sg13cmos5l` checkout
  gives the original's inverted values (`up_avg` 3.049125 V), so the inversion
  is reproduced **there** and absent on the fleet image's OSDI/model build. The
  fleet-image result must not be read as the post-layout `pfd` being fixed;
  RECORD-003's finding stands, as measured on the pinned tree, for a single
  deck.

## 5. Results: `pll_lock_detector`

Rerun vs original, per CSV (row alignment is by position; the files have equal
shapes). `max rel` is the largest relative difference of any numeric cell in
a differing row (`rerun325/tools/cmp.py`).

| CSV (`-rerun325`) | Rows | Rows differing | Largest relative difference |
|---|---:|---:|---|
| `ld_rc_extract` | 15 | 9 (all 9 `R` rows; the 6 `C` rows are byte-identical) | 8.7 % |
| `ld_rc_control` | 15 | 9 | (delta column) |
| `ld_window_control` | 102 | 1 | 1.9e-6 (`twin_f_s`, last printed digit) |
| `ld_window_control_delta` | 102 | 1 | byte-identical flag `yes` -> `no` for that row |
| `ld_window` | 85 | 40 | 12 % (`twin_r_s`) |
| `ld_ladder` | 32 | 32 | rail/chatter class identical for 7 of 32 |
| `ld_ladder_raw` | 288 | 288 | not summarised |
| `ld_tstep_convergence` | 6 | 4 | 11.8 % (`twin_r_s`) |
| `ld_deviation` | 29 | 29 | 30 % |

- **Control arm: mostly reproduces.** 101 of 102 committed-window points are
  byte-identical (the original reports 102/102), so the harness and the
  MOS-only window decks behave as before. The one difference is a last-digit
  change in a `twin_f_s` (5.39166e-09 vs 5.39165e-09 s). The R/C extraction
  control reproduces 6 of 15 rows (original 15/15): all six `cap_cmomi` `C`
  rows reproduce; all nine `XRPU` rhigh `R` rows differ, by up to 8.7 %, and
  section 3 attributes that to the `cornerRES.lib` content.
- **Post-layout vs as-layout window `twin_r` deviation** (RECORD-003
  section 3.2): original +44.20 % / +46.49 % / +48.56 % (min / mean / max, 29
  PVT points); rerun **+62.89 % / +66.02 % / +68.97 %**. The *direction and the
  collapse* reproduce (the as-layout window is still 3.1-3.7 % of the committed
  design's at every point; post-layout is still longer than as-layout at all 29
  points), the *magnitude* does not.
- **Ladder / recovery class counts** (32 points; rail and chatter class,
  RECORD-003 section 3.3): original post-layout 2 `lo`/chatter, 3 `lo`/steady,
  11 `unresolved`/chatter; rerun post-layout 4 `lo`/steady, 4 `unresolved`/
  chatter, 2 `unresolved`/`intermediate`, 6 `unresolved`/steady. The
  as-layout counts changed too (original 3 `lo`/chatter, 3 `lo`/steady, 10
  `unresolved`/chatter; rerun 9 `lo`/chatter, 3 `lo`/steady, 4 `unresolved`/
  chatter). RECORD-003's claim that "both arms chatter at every ladder point
  up to ..." (its section 3.3) is **not** supported by this rerun: eight
  post-layout points read `steady` and two `intermediate`. No cause beyond the
  shared resistor-model difference was established, and section 3 did not
  rerun the ladder on the pinned tree, so this is unattributed.
- **Timestep convergence** (`ld_tstep_convergence-rerun325.csv`): post-layout
  `twin_r` at 20 / 5 / 1.25 ps = 438.4 / 437.5 / 437.4 ps, i.e. -0.2 % and
  -0.23 % between the committed 20 ps and 1.25 ps (original: -0.34 %). The
  discretisation conclusion holds; the absolute `twin_r` differs from the
  original's, consistently with the window rows.
- Not rerun: nothing from the runner was skipped (`LD_SKIP_CONTROL` was not
  set). The stage that reads the retries file saw it empty.

## 6. What this does and does not support

- It supports: the harness and the lock-detector's MOS window decks are
  reproducible on the fleet (101/102 control points byte-identical, 6/6
  capacitor rows identical, 9/12 PFD rows); the post-layout `reflead` result;
  the as-layout window collapse and the post-layout > as-layout ordering.
- It does **not** support, as measured on the fleet image: the post-layout
  `fblead` mode inversion, the ladder chatter classes, or the +44-49 %
  magnitude. Section 3 shows two of those differences come from the PDK tree.
  The pinned-tree behaviour of the full grid was not rerun, because no batch
  image carries it and the dispatch host does not allow a hand-run grid.
- It is not a lock, reference-spur, loop-bandwidth or repaired-design result.
  The DUT is the pre-#136 `lock_detector` extraction and the 2026-09-21 `pfd`
  extraction (RECORD-003's own DUT); the current layout is not measured.
- The original's cross-host (x86-64 and arm64) agreement is not reproduced:
  this is one image class, x86-64, ngspice-46.
- **Consumers were not re-pointed.** `sum`, `src`, `prop`, the bench README
  and the spec still cite RECORD-003. No figure is *replaced* by this rerun:
  the replacing measurement is on a PDK tree that is not the pinned one, and
  the differing rows are attributed, at best, to that tree. The gate-visible
  link is the addendum.
- **Gaps filed upstream**: 2AMLogic/klayout-tools#5328 (deck-list batch
  reports carry no worker PDK identity; this run added the worker file hashes
  and the unpinned-tree evidence there), and #3070 (null `provenance.pdk.version`)
  already open. The missing piece on the worker side is an image that carries the
  pinned `ihp-sg13cmos5l` revision (a worker/fleet-spec change, not this repo's).
