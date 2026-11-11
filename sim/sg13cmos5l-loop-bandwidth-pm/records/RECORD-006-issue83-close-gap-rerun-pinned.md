# RECORD-006: rerun of `RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md` on the current PDK (issue #320)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #320 (child of #214, Part of #199, item 9 provenance migration).
  Append-only. This record reruns `RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md` (sha256 `b30578ffffb25e93d3461f77da3e3d87bedb334b9dd348986a12ac2d51d65fbf`, verified
  unchanged) and is the `ADDENDUM-RERUN` target of `ADDENDUM-001-record-003-superseded.md`. It edits no
  earlier record and no committed `corners/` file; the originals' CSVs and
  `RECORD-001`/`002`/`005` are untouched.
- **DUT — the original, not today's design**:
  `../netlist-snapshots/loop_filter_resized.spice` (sha256
  `5c8293087b5867fbeec32552a57ce54aa4e5a1b3572e7da86cacc874f921843a`),
  whose only commit is `ffec56a`, which predates `e54bd37` (the commit that added
  the original): `git diff e54bd37 HEAD -- <snapshot>` is empty. Scenario:
  `../testbench/tb_loop_ac_real_resized.sp.tmpl` (ideal Gcp, ideal VCO
  integrator, 1/N, real resized `rppd`/`cap_cmomi` filter), unchanged.
  `Kvco`/`fvco`/`n_div` and `Icp` are the original's own committed inputs.
  **`Icp` is not remeasured here**: it is read from the original's
  cp-icp-trim CSV (`../../sg13cmos5l-cp-icp-trim/corners/results_issue83_finetrim.csv`); replacing it is #231's scope. This
  record therefore reruns the loop-filter/PM half of the claim only.
- **Testbench**: `../testbench/gen_rerun320_requests.py` writes
  `tb_loop_ac_rerun320.sp` plus `rerun320_{probe,bundles}.request.json`
  (four loops sharing one deck; each loop's result is taken only from its own
  bundle by `summarize_rerun320.py`). Same `ac dec 200 10 1e9` sweep. Crossover
  comes from klt `.meas ... when vdb=0` (linear) instead of the originals'
  log-log interpolation; a local one-off `ngspice -b` with the originals'
  own interpolation on the slow and fast low-interval loops reproduced klt to
  5 digits (451930.7 Hz / 54.953 deg; 362845.0 Hz / 44.345 deg), so the
  method is not the cause of any difference below.
- **PDK revisions** (run host `loom-worker`, staged to the batch fleet by
  `options.stage_model_inputs`; fleet and host model-file sha256 agree,
  `pdk_stamp_comparison.status` = `match`):
  PDK ihp-sg13cmos5l revision f7bca32694fe3d58be0cc7d9df4b9f5db7161a14
  (`~/share/pdk/ihp-sg13cmos5l/.pdk-store.json`, synced 2026-10-15; the
  installed tree is a bundle, not a git checkout), and PDK ihp-sg13g2
  revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e (upstream `v0.3.0`,
  `.fetched-version` = `0.3.0`). Both trees are read: `cornerRES.lib`,
  `resistors_*.lib` and `r3_cmc.osdi` are symlinks from the cmos5l tree into
  the sg13g2 tree. The cmos5l revision is **not** `sim/README.md`'s
  `PDK-PIN` (607e18d4): that pin is re-stamped by #250 (open) and is not
  changed here.
- **Tools**: `klt 0.9.2.dev661+g1de5c0432aad` (client), batch runner
  `klt 0.9.0`, `ngspice-46` on the fleet worker (`/usr/local/bin/ngspice`,
  Creation Date 2026-10-01), `aws-batch-fleet` spot `c6i.8xlarge`.
- **Commands** (repo root; `PDK_ROOT=$HOME/share/pdk`):
  ```
  python3 sim/sg13cmos5l-loop-bandwidth-pm/testbench/gen_rerun320_requests.py
  klt sim .../rerun320_probe.request.json   --backend batch --wait-for-capacity 600   # job klt-sim-6ccf414a19e7 (1 corner, probe, pass)
  klt sim .../rerun320_bundles.request.json --backend batch --wait-for-capacity 600   # job klt-sim-8682d469bfe8 (3 corners, pass)
  python3 sim/sg13cmos5l-loop-bandwidth-pm/testbench/summarize_rerun320.py
  ```
  Envelopes: `../reports/sim.rerun320_probe.json`,
  `../reports/sim.rerun320_bundles.batch.json` (`environment.remote`).
  Outputs: `../corners/results_resized_issue83_finetrim_rerun320.csv`.

## Result (band 00, mid interval, f_ref 4.5 MHz, slow bundle, 3.75 uA)

| | `fc_hz` | `pm_deg` | `meets_ceiling` | `meets_pm45` |
|---|---|---|---|---|
| RECORD-003 (original) | 3.592385e+05 | 49.973 | yes | yes |
| **This rerun** | 3.711740e+05 | 51.751 | **yes** | **yes** |

Both criteria still clear on the rerun (fc 17.5 % under the 450 kHz ceiling,
PM 6.75 deg over the floor), but the figures differ from the original by
+3.3 % (fc) and +1.78 deg (PM). The measured numbers in RECORD-003 are not
reproduced, only its pass/fail verdict.

## Scope and limits

- **One tuple, one bundle** (the only bundle reachable at it), as in
  RECORD-003. The 29 other `(band, interval, f_ref)` combinations and the
  RECORD-003 sensitivity table were not rerun.
- **The original environment is not reproduced** and nothing here proves
  what RECORD-003 ran against; it named only `ngspice-46`, the installed
  PDK path and an x86-64 Linux host (`superseded`, no `ADDENDUM-PDK`).
  The numeric difference is consistent with a PDK/model change but the cause
  was not isolated (no contemporaneous revision exists to diff against).
- **Icp is the original input, not a remeasurement** (see DUT above); #231
  owns that.
- **No consumer was re-pointed.** DR-007, the spec and the summaries still
  cite RECORD-003's numbers; their verdict (pass) is unchanged by this rerun.
- No failed attempts: one probe, one 3-corner job, no retries.
