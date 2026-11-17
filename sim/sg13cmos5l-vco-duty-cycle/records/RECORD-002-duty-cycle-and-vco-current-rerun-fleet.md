# RECORD-002: fleet rerun of RECORD-001's 300-point duty-cycle / VCO-current grid and its timestep check (issue #317)

- **Slug**: `sg13cmos5l-vco-duty-cycle`
- **Issue**: #317 (child of #216, Part of #199, item 9 provenance migration).
  Append-only. This record reruns `RECORD-001-duty-cycle-and-vco-current.md`
  (sha256 `87edf592929efe37eb5588c5c2577f89d952a2a2623070c69422d825853fa009`,
  verified unchanged against base `6bab68d`) and is the `ADDENDUM-RERUN`
  target of `ADDENDUM-001-record-001-superseded.md`. It edits no earlier
  record and no committed `corners/` file. Nothing here asserts the original
  run's environment.
- **What was rerun**: RECORD-001's whole claim set: 5 MOS corners x 3
  temperatures x 4 band codes x 5 `VCTRL` points = 300 transient runs, plus
  the 4-point x 2-timestep convergence check (8 runs). 308 decks, one fleet
  job.
- **DUT — the original, not today's design**:
  `../netlist-snapshots/vco.spice` (sha256
  `8bba6938bfb86c98b545e63960f717bf325321c7f2093f9e1bfd322a8be8ae04`, last
  touched by `b37918d`, the commit that added RECORD-001), `XCDECAP` stripped
  exactly as `run.sh` does (the stripped copy shipped with the job has sha256
  `3bfa515efa6f451f8967bcb320257ba7e99c1ad812b3bebef979eaeeece1d93f`).
- **Testbench — new files, disclosed**: `run.sh` is untouched. The grid was
  expressed as a `klt sim` deck-list request (host policy: no local loops)
  by `../testbench/gen_rerun317_requests.py`, which renders
  `tb_vco_duty.sp.tmpl` with the same substitutions as `run.sh`. Differences
  from `run.sh`'s decks, all mechanical: (1) `.lib` paths are
  `$PDK_ROOT/ihp-sg13cmos5l/...` (expanded by the runner); (2) the four
  `pre_osdi` lines `run.sh` puts in `.spiceinit` sit in a `.control` block
  after the title line (a deck-list unit has no `.spiceinit`); nothing else
  in the deck changed. `../testbench/extract_rerun317.py` applies `run.sh`'s
  own extractor to each unit's `stdout.bin`. Decks are not committed; the
  generator reproduces all 308 byte-for-byte (`corners/decks_rerun317.sha256.csv`
  holds each deck's sha256, re-verified after the run).
- **PDK revisions**: PDK ihp-sg13cmos5l revision
  607e18d4bd9214a52575c194b4181ef449f9252f and PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e (the repo pins; see
  `sim/README.md`). **What was and was not observed on the worker**: the
  fleet image's `/opt/pdk` carries no `SOURCES` stamp and is not a git
  checkout I could query, so klt reports `pdk stamp unreadable` and the two
  commits were **not read off the worker**. What was observed is a sha256 of
  the six OSDI objects and of `cornerMOShv.lib` / `cornerRES.lib` as seen by
  a probe deck on the same fleet image
  (`../corners/worker_pdk_probe_rerun317.txt`, deck
  `../testbench/probe_worker_pdk_rerun317.sp`): all eight are **identical**
  to the same files in the pinned local install
  (`~/share/pdk/ihp-sg13cmos5l`, which resolves the sg13g2 symlinks into
  `~/share/pdk/ihp-sg13g2`), e.g. `psp103.osdi` `dba873bc...13f1a`,
  `cornerMOShv.lib` `5a1f862d...3481a`. So the model bytes that ran are the
  pinned tree's; the commit numbers above are the pins those bytes belong to,
  not a worker-side `rev-parse`. Other files of the worker tree were not
  compared.
- **Tools**: ngspice-46 (`/usr/local/bin/ngspice` on the worker, build date
  2026-10-01, KLU), runner `klt 0.9.0`, client `klt 0.9.2.dev661+g1de5c0432aad`
  (`runner_compatibility: match`).
- **Host / fleet job**: batch job `klt-sim-2ce90b38ce36`, `us-east-1d`, spot
  `m6i.4xlarge` instance `i-01d3e6a725fbdfb76` (ami `ami-095c25ae241a4d360`,
  Xeon Platinum 8375C), job state `done`, 108 s elapsed, 308/308 units
  passed (sum of unit durations 186.8 s over 2 workers). Submitted from
  `loom-worker-1`. The worker PDK probe ran as job `klt-sim-bf97be292fad` on the same
  image (only its stdout is retained).
- **Submit history, nothing hidden**: three grid submits. (a) job
  `klt-sim-d34db9447280`: `batch_no_capacity` after the full 600 s
  `--wait-for-capacity` ("256 vCPU already running ... BATCH_MAX_VCPU=224");
  nothing ran. (b) job `klt-sim-ba3a14737e39`: ran, **308/308 units errored**
  (my generator put `pre_osdi` on netlist line 2 outside `.control`;
  ngspice: `Error on line 2 ... model name is not found`); no result used.
  (c) job `klt-sim-2ce90b38ce36`: the result here. Nothing was run locally;
  there was no local fallback. One more single-unit corner request (job `klt-sim-5e466326b0b7`) was
  submitted to look for a worker PDK stamp (it failed on a request error of
  mine, `analysis requires 'kind' and 'args'`, after returning the
  `worker_environment` block quoted above).
- **Command** (from the repository root, `KLT_SIM_BACKEND=batch`):

  ```
  python3 -I sim/sg13cmos5l-vco-duty-cycle/testbench/gen_rerun317_requests.py OUT
  klt sim OUT/request.json --backend batch --wait-for-capacity 600 \
      -o OUT/out --format json --report-out OUT/report.json
  python3 -I sim/sg13cmos5l-vco-duty-cycle/testbench/extract_rerun317.py \
      OUT/out OUT/decks.sha256.csv results_rerun317.csv tstep_convergence_rerun317.csv
  ```

  Request sha256 `3557b5c560c74420c6a20bed71ca0410d5ea3e0fccfe37faa4a8784a745c006f`.
  `../corners/fleet_report_rerun317.json` is the klt report; its absolute
  `outdir` was replaced by the literal `OUTDIR` (a scratch path) and nothing
  else was edited.

## Outputs (beside the originals, which are unchanged)

- `../corners/results_rerun317.csv` (300 rows, no `NA`),
  `../corners/tstep_convergence_rerun317.csv` (8 rows),
  `../corners/decks_rerun317.sha256.csv`, `../corners/fleet_report_rerun317.json`,
  `../corners/worker_pdk_probe_rerun317.txt`.

## Result: the rerun does NOT reproduce RECORD-001 byte-for-byte, and one more point fails the floor

All 300 rows differ from `results.csv` in the last digits. Signed duty
difference (rerun - original) lies in **-0.289 .. +0.279 pp**; supply current
differs by up to **2.2 %**. RECORD-001's own statement that its numbers
reproduced byte-for-byte (issue #44) was for a different ngspice build and
host; the cause of the present difference is **not determined** here (candidates: a different
host CPU and numeric libraries, runner image build, thread settings —
none isolated). Consequences for the claims:

| Quantity | RECORD-001 | This rerun |
|---|---|---|
| duty range, 300 points | 43.74 – 51.56 % | **43.71 – 51.50 %** |
| points below the 45 % floor | 30 | **31** |
| points above 55 % | 0 | 0 |
| temperature of every sub-45 % point | -40 C | -40 C (all 31) |
| worst point | `mos_fs`, -40 C, band 00, `VCTRL` 0.3 V: 43.74 % | same point: **43.71 %** |
| sub-45 % by corner (tt/ss/ff/sf/fs) | 8/0/9/0/13 | 8/0/9/0/**14** |
| sub-45 % at `VCTRL` <= 0.9 V | 24 | 24 |
| max within-run spread (`duty` vs `duty2`) | <= 0.30 pp | <= 0.314 pp |
| duty by temperature, min–max | 43.74–49.24 / 46.35–48.86 / 48.46–51.56 | 43.71–49.05 / 46.40–48.78 / 48.47–51.50 (-40/27/125 C) |
| VCO supply current, all points | 0.937 – 2.690 mA | 0.927 – 2.712 mA |
| `mos_ff` -40 C, band 11, 2.7 V | 2.690 mA / 1563.0 MHz | 2.712 mA / 1575.6 MHz |

The extra failing point is `mos_fs`, -40 C, band `00`, `VCTRL` = 2.7 V (the
original sat just under the line the other way). **The failing duty-cycle
result is retained and not repaired**; the 45–55 % bound is not relaxed. The
qualitative finding of RECORD-001 (cold is the dominant axis; `mos_fs` worst;
no point above 55 %) holds, but its **count and extremes are not**
reproduced exactly.

Timestep check (`tstep_convergence_rerun317.csv`): 20 ps -> 5 ps moves duty by
+0.029 (tt), +0.063 (sf), -0.060 (fs), +0.039 (ss) pp — all <= 0.063 pp,
same order as RECORD-001's <= 0.150 pp. The `mos_fs` point moves in the
opposite direction to RECORD-001's (+0.150 pp), so the sign of the
discretisation effect there is not stable across the two runs; the magnitude
stays far below the 1.29 pp by which the worst point misses 45 %.

## What this does not bound

Same limits as RECORD-001 (open loop, no external load, no random mismatch).
It also does not establish the original run's environment, and it does not
identify why the numbers moved slightly. No consumer was changed: the spec
(`spec/target-spec.md` rows/lines citing 43.74–51.56 % and 30 of 300) and
`docs/chipalooza/challenge-6-proposal.md` still cite RECORD-001's figures,
which this record disagrees with in the last digits; re-pointing them is a
spec change and is left to a decision record, not done here.
