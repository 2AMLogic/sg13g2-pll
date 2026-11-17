# RECORD-006: rerun of RECORD-001 (Icp trim table and up/down mismatch) on the historical `cp`, batch fleet (issue #230)

- **Slug**: `sg13cmos5l-cp-icp-trim`
- **Issue**: #230 (Part of #212 / #199, item 9 provenance migration).
  Append-only. This record is the `ADDENDUM-RERUN` target of
  `ADDENDUM-001-record-001-superseded.md`. It reruns
  `RECORD-001-icp-trim-and-mismatch.md` and edits neither that record nor any
  historical CSV. It supersedes only that record's *evidence claim*. It is not
  evidence for the other records of this bench (`RECORD-003`/`-004` are #231;
  `RECORD-005` measures the current DR-010 `cp`).
- **DUT (historical, NOT today's `cp`)**: `../netlist-snapshots/cp-b37918d.spice`
  (sha256 `a1bd45eae5827820a790ed7ea854b3df4b06c969322b3552b08f89e4cf645724`), extracted byte-for-byte with
  `git show b37918d:sim/sg13cmos5l-cp-icp-trim/netlist-snapshots/cp.spice`.
  Pre-DR-006 `cp`: no on-chip cascode bias replica; IBP=ICP and IBN=ICN are tied and driven by the testbench-local diode-connected cascode mirror replicas (`XMREF*`, 24u/1u PMOS, 8u/1u NMOS) exactly as `b37918d`'s `tb_cp_dc.sp.tmpl`.
- **Scope**: the original's full grid, 17 PVT points x 6 trim codes x 3 UP/DN
  states = 306 DC sweeps of VOUT (0.15 V to VDD-0.15 V, 50 mV), pre-layout,
  ideal reference currents. Same row schema as the original CSVs. Bias: testbench-local mirror replica per instance, ideal `Iref` = trim code.
- **PDK**: the run staged the model library and OSDI objects from this
  worker's `~/share/pdk` (`options.stage_model_inputs`; `models.pdk` is omitted
  because the fleet bundle is client-staged, see the request files).
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e are the
  `sim/README.md` pins. **Limitation (read before relying on the cmos5l
  citation):** on this host `~/share/pdk/ihp-sg13cmos5l` is no longer a git
  checkout (no `.git`); it carries `.pdk-store.json` naming version
  `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14` (bundle sha256
  `3195ba7f3a74e91fc4eced64102c9d61b00d8eadcf5e795d36d926d40ab4ad31`, synced
  2026-10-15) and `ihp-sg13g2` carries `.fetched-version` `0.3.0`. I could not
  read a commit hash from either tree, so the 607e18d4 citation rests on the
  pin and on one measurable equivalence: the staged `cornerMOShv.lib` sha256
  (`5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a`) is
  identical to the one in RECORD-005's local report, run on the 607e18d4
  checkout. OSDI sha256 (reports): `psp103.osdi`
  `dba873bcef3f1978b30d66a4dcb661f79c6f6386c29da8841712d84399e13f1a`,
  `psp103_nqs.osdi`
  `ad99ea641e0b88b29125a786e77f3dcb3b206b5e116e23c2a265783658e69754`,
  `mosvar.osdi`
  `cded61b14fbe50f74453e995a00f4876664328fd477badf672e5b2405cae5973`.
  Both trees are cited because CMOS5L model cards/OSDI are symlinks into
  `ihp-sg13g2`.
- **Tool**: client `klt 0.9.2.dev661+g1de5c0432aad`; fleet runner
  `klt 0.9.0` (`runner_compatibility: match`); `ngspice-46` on the runner
  (`/usr/local/bin/ngspice`, binary sha256
  `dc859418bedd0478ff439a2d3e2e09f4386a7f4d5e3f17671953e101a000cc60`,
  `numdgt=12`, `num_threads=1`). The original ran `ngspice-46` on an unnamed
  x86-64 worker; this rerun does not prove that environment.
- **Host**: AWS Spot batch fleet, us-east-1 (job ids and instance types below);
  submitted from `loom-worker-1`.

## Commands

Probe first (one corner, as the dispatch rule asks), then the six requests as
one `--batch-set`:

```
python3 testbench/gen_rerun_requests.py          # writes the decks and requests
klt sim testbench/rerun1_v30.request.json --backend batch --wait-for-capacity 600 \
    -o reports/rerun/probe --report-out reports/rerun/probe-rerun1_v30.json
klt sim --batch-set testbench/rerun{1,2}_{pvt33,v30,v36}.request.json \
    --wait-for-capacity 600 --capacity-retries 2 --max-in-flight 2 -o reports/rerun/full
python3 testbench/collect_rerun.py               # reports -> corners/rerun-record-00N-*.csv
```

Probe: job `klt-sim-f7c0c650a241` (`rerun1_v30`, 1 corner) passed
(`reports/rerun/probe-rerun1_v30.json`).

## What ran

| Request | Corners | Job id | Outcome |
|---|---|---|---|
| `rerun1_pvt33.request.json` | 5 MOS x -40/27/125 C, 3.3 V (15) | `klt-sim-255a83825e11` (m7i.4xlarge) | 15/15 pass |
| `rerun1_v30.request.json` | mos_tt/27 C, 3.0 V (1) | `klt-sim-524fdf6ad61d` (m6i.4xlarge) | 1/1 pass |
| `rerun1_v36.request.json` | mos_tt/27 C, 3.6 V (1) | `klt-sim-c976a950861b` (c7i.8xlarge) | 1/1 pass |



All 6 requests: every corner `pass`, 0 failed, 0 errored. No local ngspice grid
was run. The requests carry no limits, so `pass` means "ran and returned every
measurement", not "met a spec". Reports: `../reports/rerun/full/<request>/report.json`
(+ `batch-receipt.json`); the batch-set console log is
`../reports/rerun/batch-set.stderr`. The batch-set wrapper was killed by the
tool time limit before it wrote its aggregate JSON; the per-job reports and
receipts above were already on disk and are the evidence.

## Result

Retained CSVs (new paths; the bench's `corners/results.csv` and
`corners/compliance.csv` are untouched):

- `../corners/rerun-record-001-results.csv` (306 rows, sha256 `716fbe0d73dd31bdb8e368ed8b4c79e9232985f62962893f5bdd494a045d0879`)
- `../corners/rerun-record-001-compliance.csv` (3111 rows, sha256 `9b1e067830edff7964e0fd2e441677f20a72fd5ae1d4ecb6475d211e4af5218c`)

Zero `NA` rows. Comparison with the original data (the original CSVs as committed in `b37918d`, recovered with `git show`; `corners/results.csv` on main is RECORD-002's overwrite): every
(corner, temperature, supply, code, state, VOUT) key is present in both.
Icp at VDD/2 agrees to a maximum relative difference of 9.0e-4; the
compliance curves to 3.7e-3 relative (largest absolute difference
not separately computed, at the 10 uA code). Reference point `mos_tt`/27 C/3.3 V/10 uA:
UP/DN/both Icp = +10.04605 / -10.36921 / -0.32316 uA vs original +10.04607 / -10.36930 / -0.32323 uA. The reproduced values are therefore what the original claimed to
within solver/tool-version noise; this record asserts nothing beyond that and
does not restate the original's conclusions.

## What this does not establish

- The original's host, PDK trees and tool revision (see the PDK limitation
  above); only the claim "the historical DUT, rerun, gives these numbers".
- Nothing about today's `cp` (DR-010, RECORD-005) or the loop records that
  consume this table beyond the rows replaced here.
- `testbench/run.sh` and `tb_cp_dc.sp.tmpl` (current revision) were not run;
  the rerun used a regenerated 18-instance deck per PVT point
  (`gen_rerun_requests.py`) rather than 306 separate decks. The decks are
  electrically the same bench; this is a new harness, not the original script.
