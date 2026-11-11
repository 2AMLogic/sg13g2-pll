# RECORD-007: rerun of `RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md` on the current PDK (issue #320)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #320 (child of #214, Part of #199, item 9 provenance migration).
  Append-only. This record reruns `RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md` (sha256 `372d1e4c99234dfa7357c6e608b95d6dc130461109f58a0400465d997785f060`, verified
  unchanged) and is the `ADDENDUM-RERUN` target of `ADDENDUM-002-record-004-superseded.md`. It edits no
  earlier record and no committed `corners/` file; the originals' CSVs and
  `RECORD-001`/`002`/`005` are untouched.
- **DUT — the original, not today's design**:
  `../netlist-snapshots/loop_filter_resized.spice` (sha256
  `5c8293087b5867fbeec32552a57ce54aa4e5a1b3572e7da86cacc874f921843a`),
  whose only commit is `ffec56a`, which predates `a724ddd` (the commit that added
  the original): `git diff a724ddd HEAD -- <snapshot>` is empty. Scenario:
  `../testbench/tb_loop_ac_real_resized.sp.tmpl` (ideal Gcp, ideal VCO
  integrator, 1/N, real resized `rppd`/`cap_cmomi` filter), unchanged.
  `Kvco`/`fvco`/`n_div` and `Icp` are the original's own committed inputs.
  **`Icp` is not remeasured here**: it is read from the original's
  cp-icp-trim CSV (`../../sg13cmos5l-cp-icp-trim/corners/results_issue79_finetrim.csv`); replacing it is #231's scope. This
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
  Outputs: `../corners/results_resized_issue79_finetrim_rerun320.csv`.

## Result (band 00, low interval, f_ref 4.5 MHz, 11 uA, all three bundles)

| bundle | | `fc_hz` | `pm_deg` | `meets_ceiling` | `meets_pm45` |
|---|---|---|---|---|---|
| fast | RECORD-004 | 3.686111e+05 | 45.592 | yes | yes |
| fast | **rerun** | 3.628460e+05 | **44.345** | yes | **no** |
| typ | RECORD-004 | 3.851478e+05 | 49.043 | yes | yes |
| typ | **rerun** | 3.870580e+05 | 49.346 | yes | yes |
| slow | RECORD-004 | 4.352370e+05 | 53.454 | yes | yes |
| slow | **rerun** | 4.519310e+05 | 54.953 | **no** | yes |

**The rerun does not reproduce RECORD-004's all-pass claim.** On the
rerun, the fast bundle is 0.655 deg *under* the 45 deg PM floor and the slow
bundle is 1.93 kHz (0.43 %) *over* the 450 kHz ceiling, so the 11 uA code
that DR-008 records as closing both criteria at all three bundles does not,
at these inputs, on this PDK. Only `typ` passes both. This is reported as
measured; the spec ceiling/floor were not relaxed.

## Scope and limits

- **Same limits as RECORD-006**: original environment not reproduced and not
  claimed (RECORD-004 was produced on an arm64 macOS host, tree and revisions
  unknown, with `cap_cmomi.osdi`/`cap_cmomf.osdi` rebuilt locally; this rerun
  is x86-64 Linux with the PDK's own OSDI objects); `Icp` is the original
  cp-icp-trim input, not remeasured (#231); one tuple only; the
  intermediate-code scan in RECORD-004 was not rerun. The cause of the shift
  (PDK revision, host OSDI build, or both) was not isolated.
- **No consumer was re-pointed.** DR-008, the spec and the summaries still
  cite RECORD-004. Whether DR-008's 11 uA code must be revisited (the
  window between fast PM and slow fc is narrow) is a spec/decision-record
  question left to a follow-up issue; this PR does not change the spec.
- No failed attempts: one probe, one 3-corner job, no retries.
