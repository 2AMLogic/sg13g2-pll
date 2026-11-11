# RECORD-002: SG13G2 `vco` Kvco-vs-band-code table, same-bench rerun on the batch fleet

- **Slug**: `sg13g2-vco-kvco-table`
- **Issue**: #237 (execution child of #217; supersedes `RECORD-001-kvco-band-code-table.md`,
  inventory row 37 in `sim/provenance-migration.md`)
- **Original**: `RECORD-001-kvco-band-code-table.md` (see `ADDENDUM-001-superseded.md`).
- **Claim under test**: the same as RECORD-001: the SG13G2-native output band and
  per-band, per-corner Kvco table (`spec/porting-plan.md` rows 1/4/5) for the frozen
  `../netlist-snapshots/vco.spice`. This is an independent SG13G2 rerun. It is not
  compared with CMOS5L measurements for provenance.
- **PDK revision**: `ihp-sg13g2` `IHP-Open-PDK` commit `5cccb161f7492697cfa52eb14dc03beb00bdca9e`
  (the repo pin, `sim/README.md` `PDK-PIN ihp-sg13g2`). **Not independently confirmed for
  this run:** the batch report carries no `worker_environment` PDK stamp, so the fleet image's
  `ihp-sg13g2` revision is taken from the repo pin, not observed. The job selected the image
  through `models.pdk: ihp-sg13g2`.
- **Tooling**: `ngspice-46` on the batch worker (report `environment.engine_version` `46`,
  `engine_host: worker`); `klt` client `0.9.2.dev661+g1de5c0432aad`, runner `klt 0.9.0`
  (`runner_compatibility: match`); fleet `aws-batch-fleet`, `c7i.8xlarge` spot, `us-east-1`,
  `ami-095c25ae241a4d360`. Submitted from `loom-worker-2`.
- **Probe (one unit, before the grid)**: job `klt-sim-b0522cef1561`
  (`typ`/band `00`/`VCTRL=1.5 V`): `per1 = 1.526759e-09` s, status `pass`. This is the
  first `ihp-sg13g2` PSP/OSDI batch job on record for this repo.
- **Grid**: job `klt-sim-a102ccafc592`, one `decks` request of 60 units, `klt sim
  --backend batch --wait-for-capacity 600`: 60 passed, 0 errored, 0 timed out
  (25 s on the instance).
- **Command**: from `../testbench/`: `python3 gen_rerun.py` (renders `rerun/decks/` and
  `rerun/rerun.request.json`), then from `rerun/`:
  `klt sim rerun.request.json --backend batch --wait-for-capacity 600 -o out --format json`,
  then `python3 collect_rerun.py rerun/out`. The probe is `gen_rerun.py --probe` and
  `probe.request.json`. No local `ngspice` loop was run.
- **Same bench**: the decks are rendered from the unchanged `tb_vco_kvco.sp.tmpl` with the
  same substitutions as `run.sh` (`@PDK_ROOT@` becomes `$PDK_ROOT`, expanded by the runner;
  `@DUT@` becomes `vco.spice`, a byte-identical copy of `../netlist-snapshots/vco.spice`).
  The only deck difference is OSDI loading through `pre_osdi` lines in `.control`, in place of
  the local `.spiceinit`. Same 3-bundle matrix, `.tran 20p 40n`, and `.meas` as RECORD-001.

## Result

`../corners/results-rerun.csv` (60 rows, header `pvt_bundle,mos_corner,res_corner,cap_corner,temp_c,band_code,vctrl_v,period_s,freq_hz`).

- **Coverage**: 60/60 oscillating, **0 `NA` rows**, 0 non-converging units, no missing axes.
  Every unit exited 0 and carried a `per1` measurement.
- **Comparison with RECORD-001** (`results.csv`): the `period_s` of all 60 rows is
  **identical**, 0 differences (`python3 testbench/collect_rerun.py` prints
  `identical-period-to-RECORD-001 60, differing 0`). The RECORD-001 results table, band edges
  (floor 445.26 MHz `slow` VCTRL=0.3 V; ceiling 1561.97 MHz `fast` band `11` VCTRL=2.7 V) and
  Kvco figures therefore stand unchanged as measured by this independent run.
- Raw evidence: `../testbench/rerun/out/<unit>/{stdout.bin,stderr.bin,<unit>.sp,unit.json}` and
  `../testbench/rerun/out/report.json`; probe under `rerun/out-probe/`.

## Limitations

- The fleet-side PDK revision is the repo pin, not observed (see above).
- Original `RECORD-001`, its snapshot, `results.csv` and `matrix.md` are unchanged.
- No consumer was changed: no figure was replaced (identical values), so #218 integration has
  nothing to take from this record. Item 9 of the provenance migration stays unmet until every
  grandfathered record is resolved.
