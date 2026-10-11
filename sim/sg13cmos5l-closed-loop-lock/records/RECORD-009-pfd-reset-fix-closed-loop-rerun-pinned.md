# RECORD-009: rerun of RECORD-003's closed-loop decks on the pinned dual-tree environment (issue #227)

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #227 (Part of #211 / #199, item 9 provenance migration).
  Append-only. This record reruns the two full-duration decks of
  `RECORD-003-pfd-reset-fix-closed-loop-rerun.md` and is the `ADDENDUM-RERUN`
  target of `ADDENDUM-002-pfd-reset-fix-rerun-superseded.md`. It neither
  edits `RECORD-003-pfd-reset-fix-closed-loop-rerun.md` nor any historical
  CSV. It supersedes only that record's *evidence claim* for the Part A and
  Part B measurements below. It is not evidence for RECORD-001, -002, -004,
  -005, -006, -007 or -008.
- **Scope**: single PVT point (`mos_tt`/`res_typ`, 27 C, 3.3 V), pre-layout,
  two sequential local `ngspice -b` runs (Part A 500 ns, Part B 2.5 us). The
  PVT point is the original's explicit single-point subset
  (`../corners/matrix.md`); no grid exists, so nothing went to the batch
  fleet. The rerun adds no corner and no coverage beyond RECORD-003's.
- **PDK revisions** (checked on the run host, read 2026-10-11):
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  (`git rev-parse HEAD` of `~/share/pdk/ihp-sg13cmos5l`, `git status
  --porcelain` empty), and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (upstream `v0.3.0`; the host tree is a release-tarball install,
  `.fetched-version` = `0.3.0`; the sg13g2 revision is the pin supported by
  the version marker and the OSDI hash verification in
  `sim/provenance-migration.md`, not by a git checkout on this host). The
  cmos5l tree reads its `psp103` models and OSDI objects through symlinks
  into the sg13g2 tree, so both trees are cited.
- **Tool**: ngspice-46, x86-64 Linux. The host's `/usr/bin/ngspice` is
  ngspice-42, so the run used the scratch ngspice-46 build
  `/tmp/i195-ngspice/bin/ngspice` (sha256
  `f8c03b87208fab0622e6d06e57647ea5cea4153a4e3bfe5de0ded088b3acc87a`)
  placed first on `PATH`. Its build recipe/configuration was not verified
  here (limitation).
- **Host**: `loom-worker-3` (8 vCPU, x86_64, shared; load average ~6.7 at
  start). The original ran on an x86-64 Linux host whose worker is not named
  (RECORD-003's own "Tooling" line); this rerun does not prove that
  environment.

## Reconstruction of the historical bench

The bench was extracted unmodified with `git archive d633b9d` (full commit
`d633b9d5d33b2b403bc1fd43b449c5a1abdbd1db`, the commit that introduced
`RECORD-003-pfd-reset-fix-closed-loop-rerun.md` together with the #56 `pfd`
repair) into an isolated scratch directory (`/tmp/r227/hist`). The extracted
`pfd.spice` snapshot is the repaired one (contains the `XI1B` third reset
inverter). Inputs as extracted, sha256:

| File at `d633b9d` | sha256 |
|---|---|
| `netlist-snapshots/pfd.spice` (repaired) | `cc9657043b755854e86d11aef6d13a9ee3301fa0df19373e543d461d6138c483` |
| `netlist-snapshots/cp.spice` | `05303ffe364a3ac569f7d6330209c2f97e93e14c1da034ee76e0a550e1bce271` |
| `netlist-snapshots/loop_filter.spice` | `89af2391d684073fdce198dbaab3632766cb4f9d93b00d1801ef4ebdbd33fd2e` |
| `netlist-snapshots/vco.spice` | `9d61ae66b60c87609ccd52bf7b1845153564170ae5b537f9b7ec83e3c2460f6c` |
| `netlist-snapshots/divider_chain.spice` | `89315a6cd6f373ec28067ee0ca01dd9d135052ef3b0f34bba53882d0f4a458a6` |
| `netlist-snapshots/lock_detector.spice` | `66f683ef6c66ff50aa2fa34597eb8bbc8c44c85d5d808cb521a6cf4dc86c68bf` |
| `testbench/run.sh` | `5113eb0376c262a9a99b0edf5aaaaf4862580a2c6526f9b4cd368d91d88aad5d` |
| `testbench/extract.py` | `0e0a92669188ec5159ed70bde6c0de92faeb8aff0fbe3d5a49a484ed55b7f1b9` |
| `testbench/tb_pll_closed.sp.tmpl` | `6f7e0cf085e7f90479bbf1f172b46978241d877b3ee905d350fb1fe71aa99cb1` |
| `testbench/tb_pll_proposal.sp.tmpl` | `99b4347cf37b5c14d2c973ca3f98671e4ff61377a905bba8f578dae8db7898d6` |

**Runner adaptations: none.** `run.sh` ran byte-for-byte as committed, full
duration (no `--quick`), with the committed ideal-capacitor and `XCDECAP`
substitutions it always applies (disclosed in RECORD-003/RECORD-001). Its
generated decks live in its own `mktemp` directory, which it deletes on exit;
they are derived deterministically from the hashed inputs above. Part A is the
as-drawn loop with the real (broken, issue #36) `divider_chain`; Part B is the
proposal deck (R1 x20 filter, behavioural divide-by-64). Neither is the
repaired divider or a committed-design lock result.

## Command

```
git archive d633b9d | tar -x -C /tmp/r227/hist
export PATH=/tmp/r227/bin:$PATH   # /tmp/r227/bin/ngspice -> /tmp/i195-ngspice/bin/ngspice (ngspice-46)
export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l
cd /tmp/r227/hist && sim/sg13cmos5l-closed-loop-lock/testbench/run.sh   # 2026-10-11T16:55:56Z .. 17:04:31Z, 8 m 34 s wall
```

(RECORD-003 reported ~35 min on a loaded host; wall time is host-load
dependent and is not a result.) Retained fresh outputs in `corners/` under new
names; the historical filenames were not written (sha256 in parentheses):

- `results_as_drawn_rerun227.csv` (`8128ce363ba58176e1600b84f3bde9a798ebf3a249e0dc7e4db3e9dd54f58297`)
- `results_proposal_rerun227.csv` (`08f2f33f404f7c6962271f0ef025b02ecca13f25a4891283d74df426c808349c`)
- `lock_trace_as_drawn_rerun227.csv` (`c7ba84dc478cc7692249e81682de10dd87652f3001005626a9162f6de167aaa5`)
- `lock_trace_proposal_rerun227.csv` (`93d320d06b2337d55de5ac30edfa6872ff61fe82721d9fa9972d8a33c35532b4`)
- `log_run_rerun227.txt` (`3cb75d195f34749918b3726226d98945ac4335df6d263e9b7f61fad4cbca0ff0`, runner console output with the `.meas` values)

## Result: reproduced

All four result files are **byte-identical** to the versions committed at
`d633b9d` (compared by sha256; the identical hashes are the evidence, not a
tolerance). RECORD-003's tabulated values are therefore reproduced exactly:

| Quantity | RECORD-003 | Rerun |
|---|---|---|
| Part A `divider_chain` current (300-500 ns avg) | -7.698 mA | -7.69846 mA |
| Part A `vctrl` end / average | 3.300 V / 3.300 V | 3.29976 V / 3.299524 V |
| Part A `n_ref_cycles_observed`, `lock_time` | 0, None | 0, None |
| Part B `vctrl` end (2.5 us) | 2.387 V | 2.38733 V |
| Part B `cp` / `pfd` / `vco` / `lock_detector` current | -24.66 uA / -57.54 uA / -2.012 mA / -46.00 uA | -24.6643 uA / -57.5362 uA / -2.01234 mA / -45.9949 uA |
| Part B reference cycles observed | 49 | 49 |
| Part B final 20 cycles `delta_f/f_ref` | -0.0293% to +0.0068% (mean -0.0049%) | -0.0293% to +0.0068% (mean -0.0049%) |
| Part B final 20 cycles static phase error | 9.110% to 9.196% (mean 9.176%) | 9.110% to 9.196% (mean 9.176%) |
| Part B `lock_time` | None (longest dual-lock run 4 cycles) | None |
| Part B reference-spur Goertzel figure | ~-44.4 dBc (context only) | -44.425 dBc (context only) |

Every limitation and failure of RECORD-003 therefore stands unchanged and is
retained: Part A does not lock (railed `vctrl`, defective `divider_chain`);
Part B is frequency-locked with a 9.176% static phase error, 1.8x the 5%
criterion, `lock_time = None`; row 7 and row 10 stay `insufficient-evidence`.
The reference-spur number is not a row-10 measurement.

## What this does not bound

- Single PVT point only; no corner or Monte Carlo result exists in this
  record, same as RECORD-003.
- It does not test RECORD-003's static-phase-error hypotheses (the later
  RECORD-004/-005/-006/-007 and #70/#72/#165 diagnostics address those).
- It does not recover the original's PDK revision, tool build or host: the
  addendum is `superseded`, not `recovered`. A byte-identical outcome on the
  pinned trees is consistent with, but does not prove, the original
  environment.
- ngspice-46 here is a scratch build whose provenance is only its hash.
- Item 9 stays unmet: other grandfathered records remain unresolved.
- No consumer citation changed numerically: every number cited by
  `docs/chipalooza/challenge-6-proposal.md` from RECORD-003 (Part B 9.176%,
  frequency lock within 0.03%, dual-lock run of 4 cycles, domain currents) is
  reproduced exactly, so none is replaced. `characterization/records_baseline.json`
  is unchanged because RECORD-003 stays an uncited historical record; the new
  record is added to `characterization/sources.json` as required for new
  records.
