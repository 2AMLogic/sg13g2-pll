# RECORD-013: partial rerun of RECORD-006's cp dump-node diagnostic (control_probe and ideal_dump) on the pinned dual-tree environment (issue #239)

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #239 (Part of #211 / #199, item 9 provenance migration).
  Append-only. This record reruns two of the variants of
  `RECORD-006-cp-dynamic-charge-term-diagnostic.md` on the same bench and is
  the `ADDENDUM-RERUN` target of
  `ADDENDUM-006-record-006-superseded.md`. It does not edit
  `RECORD-006-cp-dynamic-charge-term-diagnostic.md` (sha256
  `ea0486cd13decec6872febf2a08b321d0617c917ce9d6a84d461a252d361b5f6`,
  verified unchanged), any historical `corners/cpdiag_*`, `cppulse_*` or
  `lock_trace_cpdiag_*` file, or any snapshot. Every new output carries the
  suffix `_rerun239`.
- **Scope, stated plainly: PARTIAL.** RECORD-006 is a 9-closed-loop-run plus
  open-loop-pulse campaign. This record reruns only the two variants the
  issue names as required, because together they bound the record's central
  claim: `control_probe` (closed loop and open-loop pulse bench, the
  -41.30 fC / 8.204% headline) and `ideal_dump` (closed loop and open-loop
  pulse bench, the -8.10 fC / 1.048% claim). **Every other variant is NOT
  RERUN** (table below), so this record makes no claim about them. Nominal
  point only (`mos_tt`/`res_typ`, 27 C, 3.3 V), pre-layout, proposal deck
  (behavioural divide-by-64, `R1` 2400u, ideal MOM-cap substitutions, ideal
  `IREF`). **Every number is a proposal-deck diagnostic number, not
  committed-PLL performance and not sign-off evidence**, exactly as
  RECORD-006 says of its own.
- **DUT**: the historical one. `cpdiag_build.py` builds the variants from the
  frozen `../netlist-snapshots/cp_cascbias.spice` (sha256
  `7b07391852d5686a3aec2eaff2ef9e158ddd69d29adc1d1304514c52284f35ff`) and
  `pfd.spice` (`cc9657043b755854e86d11aef6d13a9ee3301fa0df19373e543d461d6138c483`),
  not today's DR-010 `cp`. The bench scripts and templates are the committed
  ones (unchanged since `41699d8`, the commit that added RECORD-006); the
  generated bundle hash (`cc23bff45279c7b929526f3e720fb21851402ffe0f9f2dc8c7e776b0d2a74689`)
  equals the one recorded in RECORD-006's own summaries. No runner
  adaptation.
- **PDK revisions** (checked on the run host, 2026-10-11):
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  (`git rev-parse HEAD` of `~/share/pdk/ihp-sg13cmos5l`, `git status
  --porcelain` empty), and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (upstream `v0.3.0`; the host tree is a release-tarball install,
  `.fetched-version` = `0.3.0`, not a git checkout; the revision is the pin
  verified in `sim/provenance-migration.md`). Both trees are read: the four
  OSDI objects the runner's `.spiceinit` loads and the `cornerMOShv.lib` /
  `cornerRES.lib` model cards are symlinks from the cmos5l tree into the
  sg13g2 tree. OSDI sha256: `psp103.osdi` `2e4299c4683997e2...`,
  `psp103_nqs.osdi` `839b164483205601...`, `mosvar.osdi`
  `25e64a374ab523dd...`, `r3_cmc.osdi` `4fead17bc2e9cbfe...` (identical to the
  prefixes RECORD-006 cites). `cornerMOShv.lib` sha256
  `5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a`.
- **Tools**: ngspice-46, x86-64 Linux, the scratch build
  `/tmp/i195-ngspice/bin/ngspice` (sha256
  `f8c03b87208fab0622e6d06e57647ea5cea4153a4e3bfe5de0ded088b3acc87a`) first on
  `PATH` via a symlink; the provisioned `/usr/bin/ngspice` is ngspice-42 and
  cannot load the PSP OSDI objects (OSDI v0.3 vs v0.4). The scratch build's
  recipe was not verified here (limitation, same as RECORD-012).
  RECORD-006 ran on ngspice-47, so the simulator build differs.
  `klt 0.7.0+g122d607d5c52` (recorded; used only for the batch submit
  attempts below), Python 3.12.3 (stdlib only), `set num_threads=1` in the
  generated `.spiceinit`.
- **Host**: `loom-worker-3` (8 vCPU, x86-64 Linux, shared dispatch worker).
  RECORD-006 names only "an x86-64 Linux shared worker".
- **Repo base**: `82fdfdf`.

## Per-variant status

| RECORD-006 variant | Closed loop | Open-loop pulse bench | How |
|---|---|---|---|
| `control_probe` | **rerun** | **rerun** | local, single unit each |
| `ideal_dump` | **rerun** | **rerun** | local, single unit each |
| `control_hist` | not rerun | n/a | batch submit refused (below) |
| `control_hist_rep` | not rerun | n/a | batch submit refused; also a repeat-determinism check |
| `control_probe_rep` | n/a | not rerun | repeat-determinism check; not required |
| `ideal_dump_rep` | not rerun | n/a | repeat-determinism check; not required |
| `ideal_sw` | not rerun | not rerun | closed loop: batch submit refused; pulse bench: not attempted |
| `ideal_dump_ofs` | not rerun | not rerun | closed loop: batch submit refused; pulse bench: not attempted |
| `ideal_both` | n/a (open-loop only) | not rerun | not attempted |
| `reset_narrow` | not rerun | n/a | batch submit refused |
| `reset_wide` | not rerun | n/a | batch submit refused |
| `otabuf` (named in the issue) | n/a | n/a | not a RECORD-006 variant: `cpdiag_build.py` and RECORD-006 have no `otabuf`; nothing to rerun |

"Not rerun" means no new measurement exists in this record. RECORD-006's
claims that rest only on those variants -- that ideal switches alone leave
5.183% (a), that restoring only the 0.937 V level gives 7.395% (b'), that the
PFD reset window moves the error by <= 0.012 pp (c), the 89% / 0.8 pp
level-versus-dynamics split, the `control_hist` reproduction of RECORD-005
and the byte-identical repeat checks -- are **not** re-measured here and are
not superseded by this record.

## Batch attempt for the remaining closed-loop grid (verbatim)

The five remaining closed-loop variants were expressed as `klt sim`
requests (`../testbench/gen_rerun239_requests.py`; one request per variant,
nominal corner, `backend: batch`, no `models.pdk`, `stage_model_inputs`
true, following the workaround documented in
`sim/sg13cmos5l-cp-icp-trim-mc/`) and submitted to the Spot batch fleet with
`klt sim request.json --backend batch --format json`, 2026-10-11, from
`loom-worker-3`. None ran locally and there was no local fallback. The
requests were accepted past the PDK check (the earlier
`unsupported PDK 'ihp-sg13cmos5l'` refusal, klayout-tools#2727, was not
returned) but every submit failed at provisioning (full text in
`../corners/log_batch_submit_rerun239.txt`):

```
batch backend failed: batch-fleet-provision.sh launch failed (exit 1): error: 10 instance(s) already running + 1 requested exceeds BATCH_MAX_CONCURRENT_INSTANCES=8
```

(four submits; the fifth, `reset_wide`, reported `8 instance(s)` instead of
`10`). That is a fleet-capacity limit on the day, not a deck error, so it
does not make the variants unrunnable in principle -- they are simply
unrun. The requests also declare only the quantities a `klt sim` report can
return (the template's supply-current and `vc_avg` `.meas` values); the lock
and phase-error metrics need the raw `wrdata` trace and
`cpdiag_post.py`, so even a successful batch run would not by itself have
reproduced RECORD-006's phase-error columns. The open-loop pulse benches for
`ideal_sw`, `ideal_dump_ofs` and `ideal_both` are about 2 s each but were
not run: they are part of the same grid, and the issue scopes only
`control_probe` and `ideal_dump` to local execution.

## Command

```
export PATH=/tmp/r239/bin:$PATH      # /tmp/r239/bin/ngspice -> /tmp/i195-ngspice/bin/ngspice (ngspice-46)
export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l OUT_PREFIX=/tmp/r239/out
cd sim/sg13cmos5l-closed-loop-lock/testbench
VARIANT=control_probe RUN_TAG=_rerun239 ./run_cp_dynamic_diag.sh   # 20:40:13Z .. 20:47:56Z, 7 m 43 s wall
VARIANT=control_probe RUN_TAG=_rerun239 ./run_cp_pulse_charge.sh   # ~2 s
VARIANT=ideal_dump    RUN_TAG=_rerun239 ./run_cp_dynamic_diag.sh   # 20:48:10Z .. 20:55:58Z, 7 m 48 s wall
VARIANT=ideal_dump    RUN_TAG=_rerun239 ./run_cp_pulse_charge.sh   # ~2 s
```

Run one at a time on the shared worker (no loop, no parallelism). The
scripts were run directly rather than through `klt sim --backend local`
because this bench is a templated `.tran` deck whose lock metrics come from
`wrdata` post-processing; a `klt sim` request cannot return those traces.
`OUT_PREFIX` pointed at a fresh scratch directory so the unsuffixed
`cpdiag_variant_<variant>.diff` files the harness always writes could not
overwrite the historical ones; the generated diffs are byte-identical to the
committed `corners/cpdiag_variant_control_probe.diff` and
`..._ideal_dump.diff`, so they are not duplicated. Outputs (sha256) in
`../corners/`:

| File | sha256 |
|---|---|
| `lock_trace_cpdiag_control_probe_rerun239.csv` | `9bd585d1be43c25898d83563d3c40882c5020b69b2adb96a35496d73f82b25c2` |
| `lock_trace_cpdiag_ideal_dump_rerun239.csv` | `85ed0f3e1c2d9db5c5924498518d8240b7e19c91b0f2a911023458ca89ef9d38` |
| `cpdiag_cycles_control_probe_rerun239.csv` | `9b4d9437586b3dab32abd6b797262e1306e1c8eece3c8efbc7ef212c7f377a85` |
| `cpdiag_cycles_ideal_dump_rerun239.csv` | `a8b13a484edc2b6552fb0542333f6f6a7f84c217a6f3851aeee0d501c84bdc97` |
| `cpdiag_summary_control_probe_rerun239.json` | `6a99d665c11b47ed9a0e332be2f6641850c02343d1863f7543773c660a85de12` |
| `cpdiag_summary_ideal_dump_rerun239.json` | `99459043527e7bcc2c13a4be587311f3c930a382e3f61b1d30ae1a7d6e528a66` |
| `cppulse_events_control_probe_rerun239.csv` | `1a5cfefb2876091e93464d2f89f7282a919d3a0c03c103a6a19d3a76c86e1e20` |
| `cppulse_events_ideal_dump_rerun239.csv` | `e9457697422715f9e2d873b4832925e0031b917af10322b54fba29555388ab81` |
| `cppulse_summary_control_probe_rerun239.json` | `410fec91531526e3b8749201c4475ace35d72ec2b683d693c45c36f026be4a94` |
| `cppulse_summary_ideal_dump_rerun239.json` | `2602a2ea5cb6e6baf7fa5054b8abba101de122f10ad1dcd23e7d4e0481875a15` |
| `log_cpdiag_*_rerun239.txt`, `log_cppulse_*_rerun239.txt`, `log_batch_submit_rerun239.txt` | console output of each run / of the batch attempts |

Simulator exit status 0 for all four runs; all `vctrl` samples finite; 50 REF
and 50 FB rising edges per closed-loop run (49 cycles); 49 complete UP/DN
pulse-pair rows per cycle CSV.

## Result: RECORD-006's claims for these two variants reproduce

### Open-loop charge bench: identical to every printed digit

The `cppulse` fits and `.meas` values are exactly equal (not merely close)
to the committed `corners/cppulse_summary_*.json` for both variants, and the
event CSVs are byte-identical to the historical ones:

| Quantity | RECORD-006 | Rerun (both variants) |
|---|---|---|
| `control_probe` Q0 UP / DN / UP+DN | -19.976 / -22.822 / -41.302 fC | -19.976 / -22.822 / -41.302 fC |
| `control_probe` plateau I UP / DN / UP+DN | 10.0493 / -10.1373 / 0.0620 uA | 10.0493 / -10.1373 / 0.0620 uA |
| `control_probe` superposition residual | 1.497 fC | 1.497 fC |
| `control_probe` `VDUMP` quiet; `sw_p`/`sw_n` quiet | 1.4496 V; 1.4787 / 1.4476 V | 1.449604 V; 1.478668 / 1.447591 V |
| `ideal_dump` Q0 UP / DN / UP+DN | -4.394 / -3.515 / -8.099 fC | -4.394 / -3.515 / -8.099 fC |
| `ideal_dump` plateau I UP / DN / UP+DN | 10.0002 / -10.0266 / -0.0263 uA | 10.0002 / -10.0266 / -0.0263 uA |
| predicted phase error -Q0_both/(I_up T_ref) | 8.220% (probe), 1.620% (dump) | 8.220%, 1.620% (same inputs) |

The open-loop bench holds `VOUT` with an ideal source and uses ideal pulse
sources, so it contains no free-running oscillator or loop and is
reproducible bit-for-bit across ngspice 46/47 here.

### Closed loop: outcome reproduced, numbers not byte-identical

The two closed-loop traces differ from the committed ones in the last few
digits. Largest per-cycle differences (whole 49-cycle trace): `control_probe`
phase 0.030 pp / `delta f` 0.023 pp (both during settling, `t` = 1.25-1.30
us); `ideal_dump` phase and `delta f` 0.030 pp (at `t` = 0.90 us). Edge
timestamps agree to 1.5e-19 s. This is the cross-build integration noise
RECORD-006 itself saw between ngspice-46 and -47 for `control_hist`
(0.042 pp), and it is the expected cause here (simulator build differs); it
cannot be separated from any PDK-tree effect.

| Quantity | RECORD-006 | Rerun | Difference |
|---|---|---|---|
| **`control_probe`** phase error, final-20 mean [min, max] (% T_ref) | 8.204 [8.200, 8.221] | 8.2034 [8.200, 8.212] | -0.0006 pp (mean); max -0.009 pp |
| `control_probe` `delta f/f_ref` final-20 mean [min, max] (%) | -0.00030 [-0.0080, 0.0105] | -0.00010 [-0.0084, 0.0058] | mean +0.0002 pp; max -0.0047 pp |
| `control_probe` longest dual-lock / freq-lock run, lock time | 4 / 42, None | 4 / 42, None | identical |
| `control_probe` `vc_avg` (V), `i_cp` (uA) | 2.387048, -39.26 | 2.387071, -39.2579 | +23 uV; -0.0003 uA |
| `control_probe` `t_lead` / `t_ovl` (ns) | 4.116 / 0.805 | 4.1177 / 0.8051 | +0.0016 ns / +0.0000 ns |
| `control_probe` `q_cycle` (fC) | +0.0024 | +0.0203 | +0.018 fC |
| `control_probe` `q_lead` / `q_ovl` / `q_rest` (fC) | +17.52 / -23.18 / +5.67 | +17.53 / -23.17 / +5.67 | <= +0.011 fC |
| `control_probe` `i_off` (nA); `VDUMP` last 20% (V) | -26.444; 1.4953 | -26.421; 1.4953 | +0.023 nA; 0 |
| **`ideal_dump`** phase error, final-20 mean [min, max] (% T_ref) | 1.048 [1.010, 1.071] | 1.0478 [1.001, 1.077] | -0.0002 pp (mean); min -0.009, max +0.006 pp |
| `ideal_dump` `delta f/f_ref` final-20 mean [min, max] (%) | -0.00256 [-0.0185, 0.0164] | -0.00162 [-0.0222, 0.0150] | mean +0.0009 pp |
| `ideal_dump` longest dual-lock / freq-lock run, lock time | 45 / 45, 250.0 ns | 45 / 45, 250.05 ns | identical (250.0 ns rounded) |
| `ideal_dump` `vc_avg` (V), `i_cp` (uA) | 2.387105, -33.13 | 2.387117, -33.1272 | +12 uV; 0.00 uA |
| `ideal_dump` `t_lead` / `t_ovl` (ns) | 0.535 / 0.806 | 0.5375 / 0.8060 | +0.0025 ns / 0.0000 ns |
| `ideal_dump` `q_cycle` (fC) | -0.0097 | **+0.0137** | +0.023 fC; **sign flips**, both are zero within noise |
| `ideal_dump` `q_lead` / `q_ovl` / `q_rest` (fC) | -3.67 / -2.59 / +6.24 | -3.65 / -2.58 / +6.24 | <= +0.024 fC |
| `ideal_dump` `i_off` (nA); `VDUMP` last 20% (V) | -0.115; 2.3870 | -0.405; 2.3870 | **-0.29 nA** (both ~0 against control's -26 nA) |

Disagreements, stated plainly: none changes a pass/fail state or a claim.
The only entries that are not at the 1e-4 relative level are the two
steady-state "should be zero" quantities (`q_cycle`: sign flips between
-0.0097 and +0.0137 fC, a spread of 0.023 fC against the 41.3 fC and 8.1 fC
effects the record is about; `i_off` of `ideal_dump`: -0.115 vs -0.405 nA
against `control_probe`'s -26.4 nA). `ideal_dump`'s per-cycle minimum phase
(1.001%) is 0.009 pp below RECORD-006's 1.010%, and its per-cycle maximum
(1.077%) is 0.006 pp above, i.e. the final-20 spread widens from 0.061 to
0.076 pp; the mean agrees to 0.0002 pp.

Consequently, for these two variants:

- the headline stands: the mitigated `cp` leaves a width-independent
  -41.30 fC per UP+DN pair, predicting 8.220% of T_ref, and the closed loop
  measures 8.2034% (RECORD-006: 8.204%) with no dual lock (longest run 4
  cycles, lock time None) -- row 7 still fails on this historical DUT;
- with `VDUMP = VOUT` (ideal unity VCVS) the open-loop charge is -8.10 fC and
  the closed loop settles to 1.0478% (RECORD-006: 1.048%) with a 45-cycle
  dual-lock run and lock time 250 ns, i.e. it meets row 7's 5% threshold in
  this idealised substitution only;
- the open-loop prediction over-counts `ideal_dump` (1.620% vs 1.0478%) by
  the same 0.57 pp as before.

## What this does not bound

- **Partial coverage.** Only `control_probe` and `ideal_dump` were rerun;
  see the table. In particular the level-versus-dynamics separation
  (`ideal_dump_ofs`), the ideal-switch and reset-window variants, the
  `control_hist` link to RECORD-005 and the repeat-determinism checks are
  neither reproduced nor contradicted. This record is not a full-grid claim
  and not a sign-off claim.
- **One PVT point** (`mos_tt`/`res_typ`/27 C/3.3 V), as RECORD-006. No
  corner or Monte Carlo result exists here; the source-follower `V_GS`
  varies with corner and temperature.
- **Proposal deck only**, historical frozen `cp_cascbias`/`pfd` snapshots;
  nothing here says anything about today's DR-010 `cp`, the committed
  `divider_chain` loop or the layout.
- **Not byte-identical** in the closed-loop traces, and the difference
  cannot be attributed between ngspice 46-vs-47, host and PDK tree. The
  addendum is therefore `superseded`, not `recovered`.
- The ngspice-46 binary is a scratch build whose provenance is only its
  hash.
- The spec is not changed. Nothing in this record relaxes a ratified
  criterion; the design change RECORD-006 proposes (make the dump node track
  `VOUT`) still needs its own issue and decision record.
- Item 9 stays unmet for other grandfathered records.
