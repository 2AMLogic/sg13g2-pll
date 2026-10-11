# RECORD-012: rerun of RECORD-004's ideal-cp diagnostic on the pinned dual-tree environment (issue #228)

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #228 (Part of #211 / #199, item 9 provenance migration).
  Append-only. This record reruns the single deck of
  `RECORD-004-icp-mismatch-phase-error-diagnostic.md` and is the
  `ADDENDUM-RERUN` target of
  `ADDENDUM-005-icp-mismatch-diagnostic-superseded.md`. It neither edits
  `RECORD-004-icp-mismatch-phase-error-diagnostic.md` nor any historical
  CSV. It supersedes only that record's *evidence claim* for the
  diagnostic measurement below. It is not evidence for RECORD-001 through
  RECORD-010, and it makes no claim about the real, transistor-level
  `cp`: the substituted block is the same ideal, exactly-symmetric
  behavioural charge pump the original diagnostic built inline
  (NOT `../netlist-snapshots/cp.spice`, NOT `design/sg13cmos5l/cp.sch`).
- **Scope**: single PVT point (`mos_tt`/`res_typ`, 27 C, 3.3 V),
  pre-layout, one local `ngspice -b` run of Part B's proposal deck
  (R1 x20 filter, behavioural divide-by-64) with `cp` replaced by the
  ideal exactly-symmetric substitution (IMAG = 10.208 uA in both
  directions, 1.65 V comparators), 2.5 us simulated, TAVG0 2.0-2.5 us,
  49 reference cycles -- the original's exact duration and window, so the
  final-20-cycle comparison below is apples-to-apples against
  RECORD-004's own table. The PVT point is the original's explicit
  single-point subset (`../corners/matrix.md`); no grid exists, so nothing
  went to the batch fleet. The rerun adds no corner and no coverage
  beyond RECORD-004's.
- **PDK revisions** (checked on the run host, read 2026-10-11):
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  (`git rev-parse HEAD` of `~/share/pdk/ihp-sg13cmos5l`, `git status
  --porcelain` empty), and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (upstream `v0.3.0`; the host tree is a release-tarball install,
  `.fetched-version` = `0.3.0`; the sg13g2 revision is the pin supported by
  the version marker and the OSDI hash verification in
  `sim/provenance-migration.md`, not by a git checkout on this host). Both
  trees are cited because the deck reads sg13g2 content through the
  upstream symlinks: the four OSDI objects the runner's `.spiceinit`
  loads (`psp103`, `psp103_nqs`, `mosvar`, `r3_cmc`) and the
  `cornerMOShv.lib` model card the template includes all resolve into the
  sg13g2 tree, while `cornerRES.lib` and the block netlists are
  cmos5l-owned.
- **Tool**: ngspice-46, x86-64 Linux, the scratch build
  `/tmp/i195-ngspice/bin/ngspice` (sha256
  `f8c03b87208fab0622e6d06e57647ea5cea4153a4e3bfe5de0ded088b3acc87a`) placed
  first on `PATH` (the host's `/usr/bin/ngspice` is ngspice-42). Its build
  recipe/configuration was not verified here (limitation). RECORD-004 ran
  on ngspice-47, arm64 macOS.
- **Host**: `loom-worker-3` (8 vCPU, x86_64, shared). Same host class as
  RECORD-009/RECORD-010; host, architecture and ngspice version all differ
  from RECORD-004's original, so this rerun does not prove the original's
  environment.

## Reconstruction of the historical bench

The bench was extracted unmodified with `git archive f38b0ee` (short form
of the commit that introduced
`RECORD-004-icp-mismatch-phase-error-diagnostic.md`) into an isolated
scratch directory (`/tmp/r228/hist`). The `pfd.spice` snapshot is the
`#56`-corrected one (with `XI1B`), identical to the one RECORD-003/-009
used; `cp.spice` is present in the extraction but is by construction NOT
read by this runner (the ideal substitution is built inline), and
`divider_chain.spice` is not read either (Part B's divider is behavioural
in the template). Inputs the runner actually reads, as extracted, sha256:

| File at `f38b0ee` | sha256 |
|---|---|
| `testbench/run_closed_loop_icp_eq_diag.sh` | `df760d0ff0afb6236cbc84c84b27e74361d4d4d5c3b5c4a05f98ddff80675e78` |
| `netlist-snapshots/pfd.spice` | `cc9657043b755854e86d11aef6d13a9ee3301fa0df19373e543d461d6138c483` |
| `netlist-snapshots/vco.spice` | `9d61ae66b60c87609ccd52bf7b1845153564170ae5b537f9b7ec83e3c2460f6c` |
| `netlist-snapshots/loop_filter.spice` | `89af2391d684073fdce198dbaab3632766cb4f9d93b00d1801ef4ebdbd33fd2e` |
| `netlist-snapshots/lock_detector.spice` | `66f683ef6c66ff50aa2fa34597eb8bbc8c44c85d5d808cb521a6cf4dc86c68bf` |
| `testbench/tb_pll_proposal.sp.tmpl` | `99b4347cf37b5c14d2c973ca3f98671e4ff61377a905bba8f578dae8db7898d6` |

**Runner adaptations: none.** The script ran byte-for-byte as committed,
full duration (no `TSTOP_OVERRIDE`/`TAVG0_OVERRIDE`), including the
substitutions it has always applied itself and RECORD-004 discloses
(`vco.XCDECAP` strip; `loop_filter` XC1/XC2 to ideal caps at the same
measured nominals; R1 x20; `lock_detector` XCW/XC1 to ideal caps at the
same density extrapolation). The committed-design netlists were not
touched.

## Command

```
git archive f38b0eee013149803a16569896d299b35bac6b7c | tar -x -C /tmp/r228/hist
export PATH=/tmp/r228/bin:$PATH   # /tmp/r228/bin/ngspice -> /tmp/i195-ngspice/bin/ngspice (ngspice-46)
export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l
cd /tmp/r228/hist && sim/sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_icp_eq_diag.sh
  # 2026-10-11T19:21:39Z .. 19:26:58Z, 5 m 19 s wall
```

(RECORD-004 reported ~24 minutes wall on its arm64 macOS host; wall time
is host dependent and is not a result.) Retained fresh outputs in
`corners/` under new names; the historical filename was not written
(sha256 in parentheses):

- `lock_trace_proposal_icpeq_rerun228.csv`
  (`a8987a4ead9822e907f9882a4c4b08710bdb05ec0d5a2b9004023acca038dbd6`)
- `log_run_icpeq_rerun228.txt`
  (`13d3524b6fd5d6ae79a1279cdf9ac24ef25ea7e9edc61e64090bf4faad6a29d2`,
  runner console output with the `.meas` values)

## Result: outcome reproduced exactly, numbers not byte-identical

As with RECORD-010, the transient over ~10^4 timesteps of six switching
blocks does not reproduce bit-for-bit across different host, architecture
and ngspice build. The differences are at the 1e-5..1e-4-of-`T_ref` noise
level and are reported, not hidden (original = RECORD-004's own table,
cross-checked against its committed
`../corners/lock_trace_proposal_icpeq.csv`; the original's per-domain
supply currents other than `i_cp` were not retained by RECORD-004, so no
current rows besides `i_cp` are claimed):

| Quantity | RECORD-004 (original) | Rerun |
|---|---|---|
| `vctrl`: IC -> final | 2.46 V -> 2.387 V (2.38696 V) | 2.46 V -> 2.38700561 V |
| `vc_avg` (2.0-2.5 us) / range | 2.387128 V / 2.386795-2.387481 V | 2.387157 V / 2.386784-2.387544 V |
| Reference cycles observed | 49 | 49 |
| `i_cp` (2.0-2.5 us avg) | 0 (by construction) | 0.000000e+00 |
| `delta_f/f_ref`, final 20 cycles (`t` > 1.5 us) | -0.01317% to +0.00054%, mean -0.0016% | -0.01165% to +0.00307%, mean -0.00091% |
| final-20 `delta_f` peak-to-peak spread | 0.0137% | 0.0147% |
| Static phase error, final 20 cycles (`t` > 1.5 us) | -0.02784% to +0.00054%, **mean -0.00235%** | -0.01175% to +0.00307%, **mean -0.00044%** |
| Longest continuous run meeting the dual lock criterion | 41 cycles, `t` = 450 ns to end of run (2.45 us), continuous, zero drop-outs | 41 cycles, `t` = 450 ns to end of run (2.45 us), continuous, zero drop-outs -- identical |
| `lock_time` (first cycle of a >=20-consecutive-cycle run) | 450 ns | 450 ns |
| Settled-tail max `|delta_f|`, `|phase|` (`t` > 1.65 us) | 5.11e-5 (`delta_f` at 1.65 us) | 3.07e-5 (single blip at 2.0/2.05 us) |
| Deepest-tail max (`t` > 2.05 us) | 9.1e-12 | 9.1e-12 |

Every qualitative and run-length quantity RECORD-004 tabulated reproduces
exactly: the static phase error collapses from `RECORD-003`'s 9.176%
baseline (re-measured byte-identically by RECORD-009) to a final-20-cycle
mean four orders of magnitude below row 7's 5% threshold (here -0.00044%
vs. the original's -0.00235% -- both simulator-noise-level, with the
deepest tail at <=9.1e-12 in both), the dual lock criterion holds
continuously for 41 cycles from 450 ns through the end of the window with
zero drop-outs, `lock_time` = 450 ns, the ideal `cp` draws exactly zero
supply current, and `vc_avg` agrees to 2.9e-5 V (about 5e-4 relative) --
the substitution perturbs neither the operating point nor, per the
identical run lengths, the conclusion. The hypothesis-CONFIRMED verdict,
the design-level-mitigation Decision, the row-7/row-10/row-11
dispositions and every limitation RECORD-004 records therefore stand
unchanged; this rerun supports no new claim and adds no coverage.

## What this does not bound

- Single PVT point only (`mos_tt`/`res_typ`/27 C/3.3 V); no corner or
  Monte Carlo result exists in this record, same as RECORD-004.
- Not a claim about the real `cp`: the substitution is the original's
  ideal, exactly-symmetric behavioural model, unchanged. RECORD-004's own
  "What this does not bound" list (no mitigated-`cp` claim, no analytic
  mismatch-to-offset gain, Part A non-lock over-determined by the
  pre-repair `divider_chain`, row-7 5% threshold not revisited) is
  retained verbatim in effect.
- Not byte-identical: the residual differences cannot be attributed
  between PDK tree, tool version and architecture; the addendum is
  `superseded`, not `recovered`.
- The diagnostic's Part-B-only scope is unchanged: no Part A, no repaired
  divider, no reference-spur claim.
- ngspice-46 here is a scratch build whose provenance is only its hash.
- Item 9 stays unmet: other grandfathered records remain unresolved.
- Consumer citations: only the figures the rerun measurably replaces were
  updated -- the final-20-cycle mean static phase error, -0.00235% ->
  -0.00044%, in `sim/README.md`'s bench and row-7 entries and in
  `docs/chipalooza/challenge-6-proposal.md` row 7, each now citing both
  values. The 41-cycle run, `lock_time` 450 ns, 9.176% `RECORD-003`
  baseline and `i_cp` = 0 figures are identical in both runs and are
  unchanged. `characterization/records_baseline.json` is unchanged
  because RECORD-004 stays an uncited historical record; this record is
  added to `characterization/sources.json` as required for new records.
