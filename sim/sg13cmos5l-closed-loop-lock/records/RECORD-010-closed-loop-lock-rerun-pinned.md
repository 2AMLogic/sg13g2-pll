# RECORD-010: rerun of RECORD-001's closed-loop decks on the pinned dual-tree environment (issue #225)

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #225 (Part of #211 / #199, item 9 provenance migration).
  Append-only. This record reruns the two full-duration decks of
  `RECORD-001-closed-loop-lock-spur-power.md` and is the `ADDENDUM-RERUN`
  target of `ADDENDUM-003-closed-loop-lock-superseded.md`. It neither edits
  `RECORD-001-closed-loop-lock-spur-power.md` nor any historical CSV. It
  supersedes only that record's *evidence claim* for the Part A and Part B
  measurements below. It is not evidence for RECORD-002 through -008.
- **Scope**: single PVT point (`mos_tt`/`res_typ`, 27 C, 3.3 V), pre-layout,
  two sequential local `ngspice -b` runs (Part A 500 ns, Part B 2.5 us). The
  PVT point is the original's explicit single-point subset
  (`../corners/matrix.md`); no grid exists, so nothing went to the batch
  fleet. The rerun adds no corner and no coverage beyond RECORD-001's.
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
- **Tool**: ngspice-46, x86-64 Linux, the scratch build
  `/tmp/i195-ngspice/bin/ngspice` (sha256
  `f8c03b87208fab0622e6d06e57647ea5cea4153a4e3bfe5de0ded088b3acc87a`) placed
  first on `PATH` (the host's `/usr/bin/ngspice` is ngspice-42). Its build
  recipe/configuration was not verified here (limitation).
- **Host**: `loom-worker-3` (8 vCPU, x86_64, shared; load average ~6.8 at
  start). The original ran on arm64 macOS with ngspice-47 (RECORD-001's own
  "Tooling" line). Host, architecture and ngspice version therefore all
  differ from the original; this rerun does not prove the original's
  environment.

## Reconstruction of the historical bench

The bench was extracted unmodified with `git archive 1da08d7` (the commit
that introduced `RECORD-001-closed-loop-lock-spur-power.md`) into an
isolated scratch directory (`/tmp/r225/hist`). The `pfd.spice` snapshot is
the original, pre-repair one (no `XI1B`), and the `divider_chain.spice`
snapshot is the pre-repair, non-dividing one. Inputs as extracted, sha256:

| File at `1da08d7` | sha256 |
|---|---|
| `netlist-snapshots/pfd.spice` (pre-repair) | `1eddb8b866459e64be9fb405e191fe2f9a5b012d0f3ce2ef8c267000180c32a4` |
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
substitutions it always applies (disclosed in RECORD-001). Part A is the
as-drawn loop with the real (broken, issue #36) `divider_chain`; Part B is the
proposal deck (R1 x20 filter, behavioural divide-by-64). Neither is the
repaired divider or a committed-design lock result. (The `run.sh`/`extract.py`
/ templates hashes equal those of the `d633b9d` bench used by RECORD-009; only
`pfd.spice` differs, as RECORD-003 repaired it.)

## Command

```
git archive 1da08d7 | tar -x -C /tmp/r225/hist
export PATH=/tmp/r225/bin:$PATH   # /tmp/r225/bin/ngspice -> /tmp/i195-ngspice/bin/ngspice (ngspice-46)
export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l
cd /tmp/r225/hist && sim/sg13cmos5l-closed-loop-lock/testbench/run.sh   # 2026-10-11T19:00:04Z .. 19:07:39Z, 7 m 35 s wall
```

(RECORD-001 reported ~50 min on its host; wall time is host dependent and is
not a result.) Retained fresh outputs in `corners/` under new names; the
historical filenames were not written (sha256 in parentheses):

- `results_as_drawn_rerun225.csv` (`53c491b96bb9e7ff65077b7e9ab112e53fbd7fb5ae9df3f58fcb78b9d427939e`)
- `results_proposal_rerun225.csv` (`c95ead03283fd5075f7b194f4f92940b328cebfd37337df1984b6872e3a67ae1`)
- `lock_trace_as_drawn_rerun225.csv` (`c7ba84dc478cc7692249e81682de10dd87652f3001005626a9162f6de167aaa5`)
- `lock_trace_proposal_rerun225.csv` (`a31381e37265bbb23d109516792b7dac7692b1adf53b9306bc35ed0e5d7f63d1`)
- `log_run_rerun225.txt` (`9726104072d5462d075f6a2ad830063fb934915a14d8c7019d140718dc7f40d6`, runner console output with the `.meas` values)

## Result: outcome reproduced, numbers NOT byte-identical

Unlike RECORD-009 (rerun of RECORD-003 on the same x86-64 host class), this
rerun is **not** byte-identical to the 1da08d7 outputs. The original ran on a
different architecture and ngspice version, and a transient over ~10^4
timesteps of six switching blocks does not reproduce bit-for-bit across them.
The differences are small and are reported, not hidden (original = 1da08d7 CSVs;
`lock_trace_as_drawn` is header-only in both, differing only in the line
terminator, `\n` original vs `\r\n` rerun):

| Quantity | RECORD-001 (original) | Rerun |
|---|---|---|
| Part A `pfd` current (300-500 ns avg) | -18.83 uA | -18.811 uA |
| Part A `cp` current | -22.56 uA | -22.556 uA |
| Part A `vco` current | -2.431 mA | -2.43096 mA |
| Part A `divider_chain` current | -7.653 mA | -7.65327 mA |
| Part A `lock_detector` current | -10.97 uA | -11.183 uA |
| Part A four-domain total (`pfd`+`cp`+`vco`+`lock_detector`) | 2.483 mA (8.20 mW) | 2.4836 mA (8.196 mW) |
| Part A whole-PLL total (five domains) | 10.137 mA (33.45 mW) | 10.1369 mA (33.45 mW) |
| Part A `vctrl` avg / range / end | 2.401 V / 2.265-2.422 V / 2.393 V | 2.4013 V / 2.264-2.422 V / 2.3937 V |
| Part A `n_ref_cycles_observed`, `lock_time` | 0, None | 0, None |
| Part A Goertzel spur (context only) | -39.71 dBc | -39.65 dBc |
| Part B `vctrl` avg (2.0-2.5 us) / end | 1.782 V / 1.7197 V | 1.7817 V / 1.7192 V |
| Part B `cp` / `pfd` / `vco` / `lock_detector` current | -22.64 uA / -31.69 uA / -1.737 mA / -12.74 uA | -22.64 uA / -31.69 uA / -1.737 mA / -12.65 uA |
| Part B reference cycles observed | 49 | 49 |
| Part B `delta_f/f_ref` first / last cycle | +0.84% / -22.88% | +0.84% / -22.94% |
| Part B final-20-cycle `delta_f/f_ref` range | -22.88% to -12.94% | -22.94% to -13.03% |
| Part B longest dual-lock run, `lock_time` | 4 cycles, None | 4 cycles, None |
| Part B Goertzel spur (context only) | -36.00 dBc | -36.00 dBc |

(RECORD-001's prose gives rounded values; the original-column entries not
stated in its text are read from its committed `results_*.csv`.)

The largest relative deviation among the currents is `lock_detector`
(about 2 percent on Part A), consistent with it being the lowest-current,
most switching-sensitive domain; the others agree to better than 0.2 percent.
Every conclusion RECORD-001 drew therefore stands, and every failure and
limitation it records is retained: Part A does not lock (`fb` never toggles,
railed/drifting `vctrl`, defective `divider_chain` drawing 7.65 mA); Part B
(proposal, behavioural divider) diverges monotonically in frequency (about
-23 percent at 2.5 us) with repeated cycle slips, `lock_time = None`; row 7
and row 10 stay `insufficient-evidence`; row 11 remains a non-locked,
divider-inflated figure. The reference-spur numbers are not row-10
measurements.

## What this does not bound

- Single PVT point only; no corner or Monte Carlo result exists in this
  record, same as RECORD-001.
- The rerun is a different host class (x86-64, ngspice-46) from the original
  (arm64 macOS, ngspice-47); because the result is not byte-identical, the
  residual differences cannot be attributed between PDK tree, tool version
  and architecture. The addendum is `superseded`, not `recovered`.
- It does not cover the polarity-swap diagnostic experiment RECORD-001
  describes (not part of its committed testbench; its root cause was
  addressed by the later RECORD-002/-003 records).
- The `lock_detector` `cap_cmomi` density-extrapolation and the stripped
  `vco.XCDECAP` of RECORD-001 are retained unchanged by the unmodified runner;
  note that the OSDI constraint motivating them was arm64-specific and the
  rerun host could have used the real OSDI caps, but the unmodified runner was
  deliberately not altered.
- ngspice-46 here is a scratch build whose provenance is only its hash.
- Item 9 stays unmet: other grandfathered records remain unresolved.
- Consumer citations: only the figures the rerun measurably replaces were
  updated (spec four-domain figure 2.483 -> 2.484 mA; challenge-6 row 10
  context spur figure ~-39.7 -> ~-39.6 dBc). The whole-PLL 10.137 mA /
  7.653 mA / 8.20 mW row-11 figures agree at their cited precision and are
  unchanged. `characterization/records_baseline.json` is unchanged because
  RECORD-001 stays an uncited historical record; the new record is added to
  `characterization/sources.json` as required for new records.
