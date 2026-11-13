# RECORD-002: `cp` up/dn mirror mismatch, 1500-sample Monte Carlo campaign and `klt yield` estimate

- **Slug**: `sg13cmos5l-cp-icp-trim-mc`
- **Issue**: #178 (T1 item 6). This is the campaign `RECORD-001` said a later
  record would carry. `RECORD-001` is not edited; it remains the account of
  the bench as it stood in PR #191, on the pre-DR-010 `cp`.
- **DUT**: `cp`, `netlist-snapshots/cp.spice` — the **DR-010** `cp`, frozen
  from `design/sg13cmos5l/netlist/cp.spice` at commit `093ab2c`
  (sha256 `063450257a9b3ab22e73dd3ec812d589d5d86d7ea8ba4b74e6487db4ee63288d`).
  This is **not** the snapshot `RECORD-001` measured; that one is preserved
  beside it as `netlist-snapshots/cp-f54b9ef.spice`. Iref = 10 uA,
  VDD = 3.3 V, VOUT = 2.40 V.
- **Testbench**: `testbench/tb_cp_mc.sp`
  (sha256 `7e2efcf584bfb9df1c49890ebe334df28ade4f882fa31e15878b825f9798d871`),
  unchanged from `RECORD-001` — the top-level `.subckt cp UP DN IBP ICP IBN
  ICN VOUT VDD VSS` interface is identical in both snapshots, so the `XCP`
  instance line needed no edit. DR-010 changed only the internal
  `cp_dumpbuf`.
- **Corner coverage**: 5 mismatch-enabled MOS process sections
  (`mos_{tt,ss,ff,sf,fs}_mismatch`) x {-40, 27, 125} C = 15 corners, each
  re-run N = 100 times = **1500 samples**. Supply is fixed at 3.3 V in the
  netlist, so there is no supply axis; `cp` has no resistor, so no resistor
  corner applies (same statement as the sibling bench). Monte Carlo is
  **combined with** the process corners, not substituted for them.
- **Reproduce**: `../README.md` "Cold start".

## Headline result

Against the bench's `+/-3.5 %` screening limit (see "The limit is not
ratified" below), pooled over all 15 corners, N = 1500, 0 errored samples:

| Quantity | Value |
|---|---|
| Yield estimate (Clopper-Pearson, empirical) | **63.47 %**, 95 % CI **[60.97 %, 65.91 %]** |
| Yield estimate (normal-delta) | 63.17 %, 95 % CI [61.46 %, 64.89 %] |
| `mismatch_pct` mean / sigma | **-0.3201 % / 3.8769 %** |
| `mismatch_pct` min / max | -13.6157 % / +14.0069 % |
| Quantiles p0.5 / p5 / p50 / p95 / p99.5 | -10.773 / -6.568 / -0.364 / +5.920 / +9.288 % |
| Cp / Cpk | 0.3009 / 0.2734 (95 % CI [0.2539, 0.2929]) |
| Sigma-to-spec | 0.820 (95 % CI [0.762, 0.879]), limiting side **lower** |
| Normality (Anderson-Darling) | statistic 0.524 vs critical 0.787 at 0.05 — **consistent** with normal |
| **Sample-size verdict** | **`insufficient`** — see below |

Source: `../reports/yield.mc.json`, produced from `../reports/sim.mc.json`.
Every number above is read from that envelope; none is recomputed by hand.

## The sample-size verdict is `insufficient`, and this record does not hide it

`klt yield`'s own self-report:

```
n = 1500, observed_ci_halfwidth = 0.024682, target_ci_halfwidth = 0.010000,
required_n = 8907, verdict = "insufficient", method = "normal-approximation"
```

N = 1500 resolves the yield to **+/-2.47 percentage points** at 95 %
confidence. `klt yield`'s default target is +/-1 pp, which would need
**8907** samples at this yield. The campaign size (N = 100 per corner) is the
one issue #178's acceptance criteria specify, so it was run as specified
rather than resized to clear the default.

Consequence, stated plainly: `klt signoff` grades
**T1 item 6, analog = `unmet`, reason `undersized_sample`** — the grader
treats an `insufficient` sample-size verdict on any measurement as
disqualifying, by design (klayout-tools#2467). The row moves off
`no_evidence`, not to `met`. The digital partition is untouched and stays
`unmet / no_evidence`: `divider_chain` has no statistical spec row, and
`manifests/README.md` says so rather than citing anything here.

Resizing the campaign to N >= 8907 is tracked separately, and is deliberately
**not** the first thing to do: the `+/-3.5 %` limit the yield is measured
against is itself unratified, so its uncertainty dominates +/-2.47 pp of
sampling noise. A ratified `cp` mismatch limit should land first, since it
also determines whether a `target_yield` can be declared at all.

Two further `klt yield` warnings are part of the result, not footnotes:

- *"no measurement declared a `target_yield`, so no yield claim was checked
  — the estimates below are reported, never failed"*. Deliberate: declaring
  one would be a pass/fail claim against a number nobody ratified.
- *"samples were pooled across 15 originating corners; each corner is its own
  population, so the pooled estimate is a worst-case envelope rather than a
  distribution anyone sampled"*. Also deliberate, and the reason the
  per-corner table below exists. Read the pooled 63.47 % as an envelope over
  the corner set, not as a manufacturing yield.
- No `negative_control` is declared **inside the yield envelope** (a third
  warning). The campaign does have one — see "Controls" — but it is a
  bench-level control recorded here, not a `klt yield` seeded-degradation
  declaration, which this PDK cannot express (see "Mismatch is
  PDK-revision sensitive").

## Per corner

Each row is N = 100, so a per-corner yield carries roughly +/-10 pp of
sampling noise at 95 % confidence; read the **trend**, not the individual
numbers. Computed from `../corners/mc-samples.csv`; the per-corner mean,
sigma and quantiles `klt sim` itself reported are in
`../corners/mc-per-corner.csv`.

| Corner | mean % | sigma % | min % | max % | within +/-3.5 % | yield % |
|---|---|---|---|---|---|---|
| `mos_ff_mismatch` / -40 C | -1.001 | 4.561 | -12.214 | 7.818 | 56/100 | 56.0 |
| `mos_ff_mismatch` / 27 C | -0.091 | 3.958 | -11.224 | 9.086 | 61/100 | 61.0 |
| `mos_ff_mismatch` / 125 C | -0.730 | 3.289 | -10.368 | 8.054 | 71/100 | 71.0 |
| `mos_fs_mismatch` / -40 C | -0.281 | 4.718 | -9.900 | 9.360 | 47/100 | **47.0** |
| `mos_fs_mismatch` / 27 C | -0.200 | 4.310 | -9.708 | 9.999 | 54/100 | 54.0 |
| `mos_fs_mismatch` / 125 C | -0.367 | 3.159 | -9.113 | 6.622 | 72/100 | 72.0 |
| `mos_sf_mismatch` / -40 C | -1.017 | 4.765 | -13.616 | 12.933 | 47/100 | **47.0** |
| `mos_sf_mismatch` / 27 C | 0.550 | 3.757 | -10.231 | 10.129 | 63/100 | 63.0 |
| `mos_sf_mismatch` / 125 C | -0.357 | 3.448 | -9.746 | 7.036 | 73/100 | 73.0 |
| `mos_ss_mismatch` / -40 C | -0.602 | 4.141 | -10.661 | 10.544 | 61/100 | 61.0 |
| `mos_ss_mismatch` / 27 C | -0.201 | 3.195 | -6.436 | 8.516 | 73/100 | 73.0 |
| `mos_ss_mismatch` / 125 C | -0.645 | 3.078 | -8.670 | 8.211 | 72/100 | 72.0 |
| `mos_tt_mismatch` / -40 C | 0.025 | 3.963 | -12.187 | 6.967 | 61/100 | 61.0 |
| `mos_tt_mismatch` / 27 C | -0.198 | 3.973 | -9.273 | 14.007 | 67/100 | 67.0 |
| `mos_tt_mismatch` / 125 C | 0.313 | 3.121 | -7.304 | 8.254 | 74/100 | 74.0 |

- **Worst corners**: `mos_fs_mismatch` / -40 C and `mos_sf_mismatch` / -40 C,
  both 47/100 within the limit. `mos_sf_mismatch` / -40 C also carries the
  largest sigma, 4.765 %.
- **Best corner**: `mos_tt_mismatch` / 125 C, 74/100, sigma 3.121 %.
- **The dominant axis is temperature, not process corner.** Sigma falls
  monotonically with temperature in every one of the five process sections
  (-40 C: 3.96-4.77 %; 27 C: 3.20-4.31 %; 125 C: 3.08-3.45 %), while the
  five process sections at a fixed temperature spread much less. The mean
  stays within +/-1.02 % everywhere, so this is a spread effect, not an
  offset effect.
- No corner's mean is anywhere near the limit; the shortfall is entirely
  distribution width. Cpk 0.273 and sigma-to-spec 0.820 say the same thing:
  the limit sits well under one sigma from the mean.

## Controls, re-run on this DUT

Both controls were re-run on the refreshed DR-010 snapshot and the pinned
model bytes before the campaign. New files; the PR #191 reports are not
overwritten.

| Run | Section | N | Result |
|---|---|---|---|
| Negative control (`../reports/sim.negative_control.dr010-pinned.json`) | `mos_tt` (no mismatch library), 27 C | 20 | `mismatch_pct` = **-0.298465212079 for all 20 samples**; stddev exactly **0.0** for `iup_a`, `idn_a` and `mismatch_pct`; status pass, exit 0 |
| Positive probe (`../reports/sim.positive_probe.dr010-pinned.json`) | `mos_tt_mismatch`, 27 C | 3 | `mismatch_pct` -2.940 / +5.837 / +4.753 %; stddev 4.785 %, non-zero; 2 of 3 outside the screening limit, exit 3 |

The negative control's single value, -0.298465 %, reproduces the sibling
corner bench's nominal at VOUT = 2.40 V (`../../sg13cmos5l-cp-icp-trim/records/RECORD-002`:
-0.298 %), so the refreshed deck lands on the corner bench's number before
any mismatch is added. The negative control is the guarantee that the axis
nobody asked to vary is provably pinned: under `monte_carlo.vary:
"mismatch"` with a section that has no mismatch library, every sigma must
come back exactly 0, and it does.

The positive probe's three samples ran **twice**: once locally and once as a
3-unit fleet job (`klt-sim-9a3a4248b18b`). Both returned
`mean 2.5496033046243336`, `stddev 4.7853132491072055` — bit-identical. That
is the cross-check that the fleet is executing the same staged model bytes
as the local control, not the image's own PDK.

## Mismatch is PDK-revision sensitive — why this ran on the pin

IHP moved the per-instance mismatch enable between the two
`ihp-sg13cmos5l` revisions `../../README.md` names. In the pin
(`607e18d4...`) the HV MOS mismatch subcircuits declare
`.subckt sg13_hv_[np]mos ... mm_ok=1`, so the `agauss(w, sigma, (mm_ok != 1
? 0 : 1))` terms draw for every instance. In the newer install
(`f7bca326...`, which is what `$PDK_ROOT` and the fleet image carry today)
that default is **`mm_ok=0`**, and the enable moved to the xschem symbol,
whose netlist format string became `... m=@m mm_ok=@mm_ok` with the symbol
default `mm_ok=1`.

`design/sg13cmos5l/netlist/cp.spice` was netlisted with the **older**
symbols, so no MOS instance line in it carries `mm_ok=`. Measured, not
inferred: running this bench's positive probe against the newer tree returns
`stddev = 0.0` on all three measurements and `status: pass` — the same
numbers as the negative control, with no error and no warning. A campaign
run that way would have reported a flawless 100 % yield from a circuit that
was never perturbed.

Three consequences recorded here:

1. **This campaign ran on the pinned tree's model bytes**, staged with the
   job (see "PDK revisions"). That is also what `../../README.md`'s
   provenance contract requires of a record, and what
   `manifests/check_testbench_coverage.py` enforces.
2. **`testbench/gen_requests.py` now refuses to emit a request it cannot
   prove will draw**: `--pinned-pdk` is mandatory (no `$PDK_ROOT` fallback)
   and the generator reads the resolved mismatch library's `.subckt`
   defaults, aborting unless both HV MOS devices default to `mm_ok=1`.
3. **`klt sim` cannot catch this itself.** Its per-family mismatch-activity
   report returns `active: null` — "mismatch activity for the 'mosfet'
   family is not independently verified for PDK family `sg13cmos5l`" — with
   or without `models.pdk`, so it is silent whether mismatch is live or
   dead. Filed upstream as 2AMLogic/klayout-tools#5486, which describes
   this exact instance-parameter shape; no new issue was filed, and the
   generator guard is the local stand-in until it lands.

This does not contradict `RECORD-001`'s Finding 1 ("gated by the instance
parameter `mm_ok`, default 1"): that was true of the tree installed at
`~/share/pdk/ihp-sg13cmos5l` when it was written, which was the pin. The
default changed under the 2026-10-15 fleet PDK sync, not in the record.

## PDK revisions

- **PDK `ihp-sg13cmos5l` revision `607e18d4bd9214a52575c194b4181ef449f9252f`**
  — `../../README.md`'s `PDK-PIN`. Staged from the clean git checkout of
  exactly that commit preserved on `loom-worker-2` at
  `~/share/pdk/ihp-sg13cmos5l.bak-20261015T153727Z` (`git rev-parse HEAD` =
  the pin, `git status --porcelain` empty, reflog: one clone from
  `https://github.com/IHP-GmbH/ihp-sg13cmos5l.git`, no later checkout —
  renamed aside when the fleet PDK sync installed `f7bca326` on 2026-10-15).
  The newer `f7bca326...` install was **not** read by this campaign.
- **PDK `ihp-sg13g2` revision `5cccb161f7492697cfa52eb14dc03beb00bdca9e`**
  — `../../README.md`'s pin, and not decorative: **all 11 staged files
  resolve, through the pinned CMOS5L checkout's own symlinks, into the
  sibling `ihp-sg13g2` tree**, so every model byte this campaign read is
  that tree's.
- **What is *not* established by a commit**: the three OSDI binaries
  (`psp103`, `psp103_nqs`, `mosvar`) are host-local build products of the
  `ihp-sg13g2` tree's Verilog-A, which neither commit tracks
  (`../../README.md` install step 3). They are identified here only by
  sha256, and those are the bytes that ran.

### The bytes that actually ran

`options.stage_model_inputs` ships the model closure with the job, so the
executed bytes are the submitting host's, not the fleet image's. All 13
shards reported the **same 11 staged-input digests**, and that set is
**identical to the client's** — the campaign did not silently fall back to
`/opt/pdk` on any shard. `source_sha256` is the byte on this host;
`rewritten: true` marks a staged copy whose `.include` lines were
path-rewritten for the unit directory (a path rewrite only, which is why its
staged hash differs).

| Staged name | Kind | `source_sha256` | rewritten |
|---|---|---|---|
| `cornerMOShv.lib` | library (`models.lib`) | `5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a` | yes |
| `sg13g2_moshv_mod.lib` | dependency | `d4b348b494998d7057bdde6fb111c60153d8b86175fafcfc6de461737e7a644b` | yes |
| `sg13g2_moshv_mod_mismatch.lib` | dependency | `be170c9619bed19215f7f7b55141e0869344874e3fcf7f30b2d2aa37659b1a0e` | yes |
| `sg13g2_moshv_mismatch.lib` | dependency | `2e9612bdb8252c281f422511039dc9b3ea983892aec89f8ef3361592e68fed09` | no |
| `sg13g2_moshv_stat.lib` | dependency | `cd30f22637e41fdbbaba506ebe0f17746b8438027e4651a7a87b241a39d68903` | no |
| `sg13g2_moshv_parm.lib` | dependency | `eea5bbed39184cb1e2654ae29425a9ed6ee2f2341d6cb76c472591c75237bd35` | no |
| `sg13g2_svaricaphv_mod.lib` | dependency | `1462f67e80da7f5fa6f6b51efb0eb0e4dc7ef2da28d8bfde95a19ce2a780580a` | no |
| `sg13g2_svaricaphv_mod_mismatch.lib` | dependency | `16da7669ee7e963645a604f64770d2f8d871fa8483c34e3dddaa9fcf01c51f50` | no |
| `psp103.osdi` | osdi | `2e4299c4683997e26469410dc1ab36b02ced924b1ac0972d6c4eae360e1fc796` | no |
| `psp103_nqs.osdi` | osdi | `839b164483205601c09032951f6c41d3580f15e506dc40a7202950d3afbdfc7d` | no |
| `mosvar.osdi` | osdi | `25e64a374ab523dbfeb7ffed75dcb8b086ee10f06120a9074bd68b92d7b0fb41` | no |

The three OSDI digests are the same objects the sibling bench's #318 fleet
rerun staged (`../../sg13cmos5l-vco-kvco-table/records/RECORD-002`), which
is the independent cross-check that this is the pinned closure.

## Tools, host and fleet jobs

- **Engine**: `ngspice-47` on the workers (`/usr/local/bin/ngspice`, KLU
  build, banner creation date 2026-11-12), reported as
  `environment.engine_version` `47`. `RECORD-001` ran `ngspice-46` on a
  different host; no identity between the two builds is claimed, and the
  seed contract does not promise identical draws across engine builds — the
  `RECORD-001` probe numbers and this record's are therefore not comparable
  sample for sample.
- **Client / runner**: client `klt 0.9.2.dev930+g37dbc2458b5a`
  (KLayout 0.30.13) on `loom-worker-2`; runner `klt 0.9.0` on every shard;
  `runner_compatibility: match`;
  `runner_request_features: {required: [measurements[].expr,
  options.ngspice_init, options.osdi_preload, options.stage_model_inputs],
  missing: [], status: supported}`.
- **Yield tool**: `klt 0.9.1` in a throwaway `uvx --from
  "klayout-tools[yield]"` environment. The host `klt` has the `yield`
  subcommand but not the `klt_yield_native` extension; nothing was installed
  host-wide. Exact command, from `../reports/`:
  `uvx --from "klayout-tools[yield]" klt yield sim.mc.json --measurement mismatch_pct --format json > yield.mc.json`
  (run from that directory so the envelope's `samples` field stays the
  relative `sim.mc.json` the manifest citation hashes).
- **Fleet**: `aws-batch-fleet`, `us-east-1`, all spot, AMI
  `ami-0f6bb304291339ed0`, instance types `m7i.4xlarge`, `m6i.4xlarge`,
  `c7i.4xlarge`, `c6i.8xlarge`, `c7i.8xlarge` across AZs `us-east-1a/b/c/f`.
  Submitted with `--wait-for-capacity 600`; several shards were refused
  `batch_no_capacity` first and re-launched with backoff, as intended. No
  grid was ever run locally.
- **Sharding**: 1500 units do not fit one job. klt's conservative
  fully-serial bound (`timeout_s` 30 s x 1500 + 120 s = 45120 s) exceeds the
  fleet's `max_job_seconds` = 3600 s, so `batch.job_ceiling_check: "split"`
  packed the run into **13 jobs of 115-116 units**, at most 4 in flight
  (`batch.max_concurrent_jobs: 4`). All 13 carry the same
  `request_sha256 ab16b7002c79867882e392e2b092d3d79b629a8aca8a749cc1ecf52b5986dd0f`.
  Per-sample Monte Carlo seeds are `sample_index`-derived and resolved
  client-side, so slicing the unit list changes no draw; the dry-run's
  per-unit seed list and the report's per-sample seeds agree.
- **Jobs** (all `state: failed`, `exit_code: 3` — that is `klt sim`'s
  *limits* verdict, 548 of 1500 samples outside `+/-3.5 %`, not an
  infrastructure failure; `errored` is 0 and no shard was lost, timed out or
  interrupted): `klt-sim-9dbd59a9288d`, `klt-sim-c4155db991f8`,
  `klt-sim-fd6dc2e058fa`, `klt-sim-a0636a2960aa`, `klt-sim-80123ddb5e4f`,
  `klt-sim-2566440851d7`, `klt-sim-31428426db02`, `klt-sim-ae4235b332a4`,
  `klt-sim-184168802f03`, `klt-sim-4188fd74d25f`, `klt-sim-ef5099eee7eb`,
  `klt-sim-f51e98ebcb70`, `klt-sim-31b7782d7399`. Receipts (job id, region,
  launch/completion time, unit count, request hash) are committed under
  `../reports/mc-batch-receipts/`. First launch 2026-11-13T16:01:08Z, last
  completion 2026-11-13T16:07:35Z; per-shard engine time 9-44 s.
- **Seeds**: `monte_carlo.seed = 178`, `vary = "mismatch"`, default
  `seed_scope` (`per_corner`) and `seed_mode` (`derived`). Every sample's
  `rndseed`, `process_seed` and `mismatch_seed` are in
  `../corners/mc-samples.csv` and in `../reports/sim.mc.json`.

## The limit is not ratified

`spec/target-spec.md` proposes **no** `cp` mismatch number, and this record
does not propose one. The `+/-3.5 %` the samples are graded against is the
bench's own screening limit: 5 % (the closed-loop dual-lock static
phase-error criterion, `../../sg13cmos5l-closed-loop-lock/records/RECORD-003`
to `-005`) divided by 9.176 % phase error per 6.42 % mismatch at
VOUT = 2.40 V (`RECORD-003` and the sibling bench's `RECORD-002`) = 3.50 %.

Three caveats that belong with any use of the 63.47 % number:

1. It is an **empirical, single-point, linear-through-origin** screening
   limit. `RECORD-004` of the sibling bench states the analytic gain is not
   derived.
2. Its derivation used closed-loop records measured on the **pre-DR-010**
   `cp`. The mismatch-to-phase-error gain has not been re-measured on the
   DR-010 `cp`.
3. No `target_yield` is declared, so nothing here is a pass/fail claim.

### Recomputing this against a different limit

`../corners/mc-samples.csv` carries all 1500 samples with their seeds, so a
later ratified limit needs no re-simulation:

```bash
python3 -I - <<'PY' > /tmp/samples.json
import csv, json
rows = list(csv.DictReader(open("sim/sg13cmos5l-cp-icp-trim-mc/corners/mc-samples.csv")))
json.dump({"measurements": [{"name": "mismatch_pct",
                             "samples": [float(r["mismatch_pct"]) for r in rows],
                             "limits": {"min": -X, "max": X}}]}, open("/dev/stdout", "w"))
PY
uvx --from "klayout-tools[yield]" klt yield /tmp/samples.json \
    --measurement mismatch_pct --format json
```

or, against the committed campaign report directly, with a limits file:
`klt yield reports/sim.mc.json --limits <limits.json> --measurement mismatch_pct`.

## What this does not bound

- **Not a manufacturing yield.** The pooled figure is an envelope over a
  corner set, graded against an unratified screening limit, with the
  sample-size verdict `insufficient` for the default +/-1 pp target.
- **Switching behaviour.** This is DC with the UP/DN switches held static,
  exactly like the sibling corner bench. The charge-domain
  (per-reference-cycle) part of `spec/porting-plan.md` §1.3's PFD/CP
  methodology is still not exercised.
- **Closed-loop impact.** Row 7 static phase error is not re-measured here;
  the mismatch-to-phase-error gain used to derive the limit is the
  pre-DR-010 one.
- **Supply and layout.** One supply (3.3 V), schematic only. No PEX
  mismatch; post-layout statistical behaviour is untouched.
- **Process variation.** `vary: "mismatch"` draws per-instance mismatch
  only. Global process variation is represented by the five discrete corner
  sections, not sampled.
- **Other blocks.** `vco` duty cycle (row 13) and `lock_detector` threshold
  offset (row 16) have no Monte Carlo evidence; they are #178's named
  follow-ups.
