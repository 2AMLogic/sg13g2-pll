# RECORD-002: `vco` Kvco-vs-band-code table, same-bench fleet rerun on the pinned PDK

- **Slug**: `sg13cmos5l-vco-kvco-table`
- **Issue**: #318 (child of #216, Part of #199 — item 9 provenance migration).
  Append-only. This record reruns `RECORD-001-kvco-band-code-table.md` (sha256
  `dc3f74cbea6d8e923e343d00799572bd9cb22c8c46ef924a0ddaca7b355c4f7f`, verified
  byte-identical to implementation base `a05e4de`) and is the `ADDENDUM-RERUN`
  target of `ADDENDUM-001-record-001-superseded.md`. It edits no earlier
  record and no committed `corners/` file. **Nothing here asserts
  RECORD-001's own run environment**; it replaces RECORD-001's evidence
  claim with a measurement whose environment is recorded below.
- **What was rerun**: RECORD-001's whole claim set — 3 PVT bundles
  (`typ`/`slow`/`fast`) x 4 band codes (`00`/`10`/`01`/`11`) x 5 `VCTRL`
  points (0.3/0.9/1.5/2.1/2.7 V) = **60 transient runs**, one fleet job.
  Same `.tran 20p 40n`, same `.ic`, same `.meas` rising-edge pair.

## DUT — the original, not today's design

`../netlist-snapshots/vco.spice` (sha256
`2d4433cedb12fd3888a0ba8825651de07097d301c410307c9db1173e2704b68b`,
unchanged from base), with `XCDECAP` commented out exactly as
`../testbench/run.sh` does and for the reason its header gives; the stripped
copy that shipped with the job has sha256
`0a465b267c1601a6b573949386db9d101f511874ca340ff5cc88f82376ed267e`. The
frozen snapshot itself is untouched.

## Why this run is on the pinned tree, and how

The fleet image's own `/opt/pdk/ihp-sg13cmos5l` is the post-2026-10-15
`f7bca326...` install, **not** `sim/README.md`'s
`PDK-PIN ihp-sg13cmos5l 607e18d4...`; the two differ in model content this
DUT reads (`cornerRES.lib`, `resistors_mod.lib`, `sg13g2_moshv_mod.lib` and
all four OSDI objects all hash differently). A deck writing
`.lib $PDK_ROOT/ihp-sg13cmos5l/...` is resolved on the worker and would
therefore have run on the unpinned revision — which is why the sibling
attempt under #320 could not honestly cite the pin, and `sim/README.md`'s
"Provenance addenda" contract requires a superseding rerun to cite it.

`klt sim`'s deck-list preservation contract is the way out: a
`.include` / `.lib <file> <section>` / `pre_osdi` target written as a path
**relative to the deck** is staged from the *submitting* host at that same
relative path inside each unit's directory, with its own closure followed
recursively, and the deck bytes still ship verbatim. So
`../testbench/gen_rerun318.py` copies the pinned tree's corner-library
closure and its four OSDI objects beside the decks and references them
relatively. The grid therefore ran **on fleet capacity but on pinned model
bytes**, and `klt` attests that per unit rather than leaving it to be
trusted:

- every unit's `host_resolved` list is **empty** (`../corners/rerun318/units.jsonl`,
  `../corners/fleet_report_rerun318.json`) — not one directive was left for
  the worker's own PDK to resolve;
- all 60 units carry **one identical** staged-include sha256 set (17
  entries: the 16 pinned PDK files — 12 model libraries and 4 OSDI objects —
  plus the stripped DUT copy), recorded per unit in `units.jsonl` and against
  their source paths in `../corners/staged_pdk_rerun318.sha256.csv`;
- ngspice read no ambient OSDI list: the availability probe below shows the
  worker has neither a unit-directory `.spiceinit` nor `/root/.spiceinit`
  (the only one present, `/opt/pdk/ihp-sg13cmos5l/libs.tech/ngspice/.spiceinit`,
  is in neither place ngspice looks), so the deck's own `pre_osdi` lines are
  the whole model-loading story.

## PDK revisions

- **PDK `ihp-sg13cmos5l` revision `607e18d4bd9214a52575c194b4181ef449f9252f`**
  — `sim/README.md`'s pin. The tree staged from is the clean git checkout of
  exactly that commit preserved on `loom-worker-4` at
  `~/share/pdk/ihp-sg13cmos5l.bak-20261015T153923Z` (`git rev-parse HEAD` =
  the pin, `git status --porcelain` empty, reflog: one clone 2026-08-25, no
  later checkout — the same tree and provenance `sim/README.md` describes,
  renamed aside when the fleet PDK sync installed `f7bca326` on 2026-10-15).
- **PDK `ihp-sg13g2` revision `5cccb161f7492697cfa52eb14dc03beb00bdca9e`**
  — `sim/README.md`'s pin. This is not decorative: **all 12 staged model
  libraries resolve, through the pinned CMOS5L checkout's own symlinks, into
  the sibling `ihp-sg13g2` tree** (see the `source_path` column of
  `staged_pdk_rerun318.sha256.csv`), so every model byte this grid read is
  that tree's. Its `libs.tech/ngspice` subtree is byte-identical
  (`diff -rq`, 0 differing files) between the pre- and post-2026-10-15
  installs on this host, so the 2026-10-15 sync did not move it; the pin
  itself was established in `sim/README.md` § "Cold start" by diffing a
  separate clone of that commit against the installed tree.
- **What is *not* established by a commit**: the four OSDI binaries
  (`psp103`, `psp103_nqs`, `mosvar`, `r3_cmc`) are host-local build products
  of the `ihp-sg13g2` tree's Verilog-A, which neither commit tracks
  (`sim/README.md` install step 3). They are identified here only by sha256
  (`2e4299c4...`, `839b1644...`, `25e64a37...`, `4fead17b...`, full values in
  `staged_pdk_rerun318.sha256.csv`), and those are the bytes that ran.

## Tools, host and fleet job

- **Engine**: `ngspice-47` on the worker (`/usr/local/bin/ngspice`, KLU
  build, banner creation date 2026-11-12), reported as
  `environment.engine_version` `47`, `engine_host: worker`. RECORD-001 also
  cites `ngspice-47`, but that was a different binary on a different host and
  no identity between the two is claimed.
- **Runner / client**: runner `klt 0.9.0`, client
  `klt 0.9.2.dev915+g513f88f6836d`, `runner_compatibility: match`,
  `runner_request_features: {required: [decks], missing: [], status: supported}`.
- **Grid job**: `klt-sim-9c012bb4ecf5`, `aws-batch-fleet`, `us-east-1f`, spot
  `c7i.8xlarge` instance `i-094f5fa3617142113` (ami `ami-0f6bb304291339ed0`,
  Intel Xeon Platinum 8488C, 16 physical cores, concurrency 2), state `done`,
  exit 0, **60/60 units passed**, 0 errored, 0 timed out, 35 s elapsed on the
  instance (sum of unit durations 60.8 s). Submitted from `loom-worker-4`.
- **Single-unit fleet probe before the grid** (same staging, `typ`/band `00`/
  `VCTRL=1.5 V`): job `klt-sim-58490b6bd691`, `us-east-1a`, `c7i.8xlarge`
  `i-0f2ebbea9fb69fdae`, pass, `per1 = 1.526759e-09` s.
- **Submit history, nothing hidden**: the grid and its probe each launched
  once and passed. The `cap_cmom*` availability probe below took three
  submits: `klt-sim-87c7e78d80d7` passed but two `shell` lines in my deck
  used `$( )`, which ngspice's own `shell` mangled, so the deck was corrected
  and resubmitted; `klt-sim-857ab3ddbc12` was refused `batch_no_capacity`
  after the full 600 s `--wait-for-capacity` ("272 vCPU already running …
  exceeds BATCH_MAX_VCPU=224") and nothing ran; `klt-sim-a8b56f40dc7e` is the
  result quoted. **No part of any grid was run locally.** One single-corner
  debug run was done locally before the first submit (host policy allows a
  single unit): `ngspice-47`, `/home/ubuntu/.local/bin/ngspice`, same staged
  pinned bytes, `per1 = 1.526759e-09` s — the same value the fleet returned.
- **Solver note, disclosed**: 14 of the 60 units emitted
  `Note: Starting dynamic gmin stepping` / `… completed` on stderr while
  finding the operating point (`fast_b00_v0p3`, `fast_b00_v2p1`,
  `fast_b01_v0p3`, `fast_b01_v0p9`, `fast_b01_v2p7`, `fast_b10_v0p3`,
  `fast_b10_v0p9`, `fast_b10_v2p7`, `fast_b11_v0p3`, `fast_b11_v0p9`,
  `typ_b00_v1p5`, `typ_b00_v2p1`, `typ_b01_v1p5`, `typ_b11_v0p9`; the files
  are in `../corners/rerun318/raw/*.err`). All 14 still exited 0 and all 14
  reproduce RECORD-001's `period_s` to the last digit. No unit needed a
  tolerance change and none was retried.

## Command

From the repository root (`KLT_SIM_BACKEND=batch` is exported by the host
daemon; `OUT` is a scratch directory, `PINNED` the checkout named above):

```
python3 -I sim/sg13cmos5l-vco-kvco-table/testbench/gen_rerun318.py OUT \
    --pinned-pdk PINNED
klt sim OUT/request.json --backend batch --wait-for-capacity 600 \
    -o OUT/out --format json --report-out OUT/report.json
python3 -I sim/sg13cmos5l-vco-kvco-table/testbench/collect_rerun318.py \
    OUT/out OUT/decks.sha256.csv results_rerun318.csv
```

Request sha256
`c626e7837aeeeb2563193e294b3bc5a52d2f4f7c847a84413fef046b495a5c3c`. The
`--probe` and `--cap-probe` modes of `gen_rerun318.py` emit the two
single-unit requests above. `../corners/fleet_report_rerun318.json` is the
`klt` report verbatim except that its absolute `outdir` was replaced by the
literal `OUTDIR` (a scratch path); nothing else was edited.

### Same bench: how the decks differ from `run.sh`'s, exhaustively

`run.sh` is untouched and still the bench's entry point. The decks are
`../testbench/tb_vco_kvco.sp.tmpl` rendered with `run.sh`'s own
substitutions; the only differences, all mechanical, are:

1. the two `.lib` paths read `models/corner*.lib` instead of
   `$PDK_ROOT/$PDK/libs.tech/ngspice/models/corner*.lib` — the staging
   mechanism above, which is what puts the run on the pinned revision;
2. the four OSDI objects are preloaded by `pre_osdi osdi/<n>.osdi` lines
   inside the template's existing `.control` block, because a deck-list unit
   has no `.spiceinit` (`run.sh` writes one with the same four objects, in
   the same order);
3. `run.sh` extracts `per1` from ngspice stdout and computes
   `freq_hz = 1.0/period`; `collect_rerun318.py` applies the identical
   extraction to each unit's `stdout.bin`, so `results_rerun318.csv` has
   `results.csv`'s schema and number formatting.

Decks are not committed; `gen_rerun318.py` reproduces all 60 and each one's
sha256 is in `../corners/decks_rerun318.sha256.csv` (re-verified against the
per-unit `deck_sha256` the runner recorded).

## Outputs (beside the originals, which are unchanged)

- `../corners/results_rerun318.csv` — 60 rows, no `NA`.
- `../corners/rerun318/raw/<unit>.out` — all 60 units' raw ngspice stdout,
  plus `<unit>.err` for the 14 that wrote to stderr.
- `../corners/rerun318/units.jsonl` — per unit: status, exit code, duration,
  engine version, `deck_sha256`, `host_resolved`, and the sha256 of every
  staged model/OSDI file that unit read.
- `../corners/fleet_report_rerun318.json`, `../corners/decks_rerun318.sha256.csv`,
  `../corners/staged_pdk_rerun318.sha256.csv`,
  `../corners/cap_cmom_probe_rerun318.txt`.

## Result: the rerun reproduces RECORD-001 exactly, on the pin

**All 60 `period_s` values are byte-identical to `../corners/results.csv`**
(`collect_rerun318.py` prints
`rows 60  identical-period-to-RECORD-001 60  differing 0  NA 0  keys-not-in-RECORD-001 0`).
60/60 oscillate; there is no `NA` row and no missing axis. Re-deriving
RECORD-001's own table from `results_rerun318.csv` reproduces **every
printed cell** of it, including:

| Quantity | RECORD-001 | This rerun |
|---|---|---|
| rows, all oscillating | 60, no `NA` | 60, no `NA` |
| `period_s`, all rows | — | identical to the last digit, 60/60 |
| band floor (`slow`, `VCTRL`=0.3 V) | 445.3 MHz | 445.26 MHz (same row) |
| top-of-band (`fast`, band `11`, 2.7 V) | **1562.0 MHz** | **1562.0 MHz** |
| `typ`/`00` Kvco avg / peak local | 173.8 / 206.0 MHz/V | 173.8 / 206.0 MHz/V |
| `fast`/`11` Kvco avg / peak local | 422.4 / 379.9 MHz/V | 422.4 / 379.9 MHz/V |
| band-code spread at `VCTRL`=0.3 V | identical to 6 s.f. within a bundle | identical, 494.0 / 445.3 / 548.2 MHz |
| peak local > average, every row | yes, 12/12 | yes, 12/12 |

So RECORD-001's results table, its band-selection finding (band code inert
at low `VCTRL`, dominant at high `VCTRL`), its Kvco-is-not-constant finding,
and the 1562.0 MHz top-of-band figure RECORD-001 supplies to
`spec/porting-plan.md` row 3 all stand, now measured on the pinned revision
with a recorded environment.
**No figure is replaced, so no consumer's citation is re-pointed.** Every
consumer the inventory names for this bench still cites RECORD-001 and its
numbers: `docs/chipalooza/challenge-6-proposal.md` (rows 1, 4/5, 18),
`spec/porting-plan.md` row 2, `spec/decision-records/DR-005-*` (445.3-1562.0
MHz, and an inline snippet over `corners/results.csv` whose 1561.9721 MHz
maximum this rerun returns unchanged) and
`sim/sg13cmos5l-divider-nrange-retiming/testbench/tb_div_retime.sp.tmpl`
(1562.0 MHz top-of-band). The only consumer edits in this change are
registration, not re-pointing: `characterization/sources.json` gains a
`vco-kvco-table-rerun-pinned` dataset for this record because
`characterization/check_records.py` requires every new record to be listed,
and `characterization/SUMMARY.md` is its regenerated rendering. That dataset
declares no new coverage — its extrema (445.26 MHz / 1561.97 MHz) and its
3-bundle PVT subset are RECORD-001's own.

## Device coverage is NOT identical to the original run — it is wider

RECORD-001 records that on its **arm64** build host the installed PDK's
`cap_cmomi.osdi` / `cap_cmomf.osdi` were x86-64 ELF objects that failed
`dlopen` ("slice is not valid mach-o file"), so **no `cap_cmom` device could
be instantiated there at all**; `psp103`/`psp103_nqs`/`mosvar`/`r3_cmc` were
native arm64 and loaded. This rerun ran on **x86-64 Linux**, where that
limitation does not exist, and the difference is measured rather than
asserted — `../testbench/probe_cap_cmom_rerun318.sp`, batch job
`klt-sim-a8b56f40dc7e` (`m6i.4xlarge`, `us-east-1d`), output in
`../corners/cap_cmom_probe_rerun318.txt`:

- the worker reports `Linux … x86_64`, and `file` on the two staged pinned
  objects reports `ELF 64-bit LSB shared object, x86-64` for both;
- both load, and the frozen snapshot's own decap device — `cap_cmomi
  w=70u l=70u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1`, the exact
  `XCDECAP` line — instantiates and simulates, measuring
  **5.315078 pF** at 1 GHz.

**What this does and does not mean.** The *simulated* device sets of the two
runs are the same, because this rerun keeps `XCDECAP` stripped exactly as
`run.sh` does: neither run contains a `cap_cmom` instance, so neither the
original's nor this record's 60 numbers depend on a MOM-cap model. What
changed is *why* the strip is there. In RECORD-001 it was both a
provably-safe simplification **and** what let that record run at all on its
host; here only the first half applies — the device was available and was
still left out, deliberately, to rerun the original's claim rather than a
different one. This record therefore does **not** claim identical device
coverage with the original run, and it still makes no claim about
`XCDECAP`'s own MOM-cap sensitivity (that remains
`sg13cmos5l-vco-decap-momcap`'s claim). The 5.315078 pF figure above is
availability evidence for this provenance record, not a characterization
result, and nothing in the repository consumes it.

## What this does not bound

Everything RECORD-001 lists stays out of scope here — closed-loop
lock/settling, duty cycle, `XSWB0`/`XSWB1` mismatch, and the absolute
loop-bandwidth/phase-margin, lock-time, spur, power and Icp-trim figures.
In addition:

- It does **not** establish RECORD-001's own environment. RECORD-001 names
  only `ngspice-47` and an install path (`ReleaseNote.md` `v0.2.0`); no PDK
  commit is recoverable from it, which is why its disposition is
  `superseded` and not `recovered`.
- It does **not** reproduce RECORD-001's `#43` post-fix note, which checked
  two points on a then-current host; that note stays as written.
- It does **not** measure anything on the fleet image's own
  `f7bca326...` tree. The grid deliberately bypassed it, so this record says
  nothing about whether RECORD-001's numbers survive that revision — the
  pinned-vs-current comparison is #250/#218's scope, not this record's.
- The four OSDI binaries are identified by hash only; no commit pins them
  (above).
