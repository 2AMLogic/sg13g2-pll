# RECORD-011: rerun of RECORD-005's cascode-bias real-`cp` Part B deck on the pinned dual-tree environment (issue #229)

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #229 (Part of #211 / #199, item 9 provenance migration).
  Append-only. This record reruns the single nominal deck of
  `RECORD-005-cascbias-real-cp-static-phase-error-rerun.md` and is the
  `ADDENDUM-RERUN` target of
  `ADDENDUM-004-cascbias-real-cp-superseded.md`. It neither edits
  `RECORD-005-cascbias-real-cp-static-phase-error-rerun.md` (sha256
  `112d3a800b576be4c2392767f4c22cba8d3cc150178d352e32fd4d0d2aec890e`,
  unchanged) nor any historical CSV. It supersedes only that record's
  *evidence claim* for the nominal Part B measurement below. It is not
  evidence for RECORD-001 through -004 or -006 through -010.
- **Scope (exact)**: ONE nominal point (`mos_tt`/`res_typ`, 27 C, 3.3 V,
  `VC0` = 2.46 V, `IREF` = 10 uA, 20 MHz reference), pre-layout, Part B
  proposal deck only (R1 x20 filter, behavioural divide-by-64, mitigated
  transistor-level `cp`), 2.5 us, one local `ngspice -b` run. RECORD-005 has
  no Part A and no corner grid; none was run. Nothing went to the batch
  fleet because there is no grid. This rerun adds no corner and no coverage
  beyond RECORD-005's. The full-PVT grid for this DUT (#139) is not
  addressed here.
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
- **Host**: `loom-worker-3` (8 vCPU, x86_64, shared; load average ~4 at
  start). RECORD-005 names ngspice-46 and an x86-64 Linux host but not the
  worker; this rerun does not prove the original environment.

## Reconstruction of the historical bench

The bench was extracted unmodified with `git archive f54b9ef` (full commit
`f54b9efb889c3693783c730d1d686874ee8b78b7`, the only commit that introduced
`RECORD-005-cascbias-real-cp-static-phase-error-rerun.md`, together with the
`cp_cascbias.spice` snapshot, the deck template and the runner) into an
isolated scratch directory (`/tmp/r229/hist`). Inputs as extracted, sha256:

| File at `f54b9ef` | sha256 |
|---|---|
| `netlist-snapshots/cp_cascbias.spice` | `7b07391852d5686a3aec2eaff2ef9e158ddd69d29adc1d1304514c52284f35ff` |
| `netlist-snapshots/pfd.spice` (repaired, #56) | `cc9657043b755854e86d11aef6d13a9ee3301fa0df19373e543d461d6138c483` |
| `netlist-snapshots/loop_filter.spice` | `89af2391d684073fdce198dbaab3632766cb4f9d93b00d1801ef4ebdbd33fd2e` |
| `netlist-snapshots/vco.spice` | `9d61ae66b60c87609ccd52bf7b1845153564170ae5b537f9b7ec83e3c2460f6c` |
| `netlist-snapshots/lock_detector.spice` | `66f683ef6c66ff50aa2fa34597eb8bbc8c44c85d5d808cb521a6cf4dc86c68bf` |
| `testbench/run_closed_loop_cascbias.sh` | `003dcb57b90b6d49dc3c623fa51a9cab31893c3a3068f8e8f336c91bdca0123d` |
| `testbench/tb_pll_proposal_cascbias.sp.tmpl` | `a773be528261e73cb4f9510bc9183319dcefd305e73f93ca8aa9f5c995b29739` |
| `corners/lock_trace_proposal_cascbias.csv` (the original result) | `fda199af313678f6a36f552f1594a6b73ff8e9997a7337dd34169f318cc437f7` |

(The runner at `f54b9ef` is self-contained; it predates the shared
`testbench-preamble.sh` that later commits source. `divider_chain.spice` is
not read by this deck: its feedback divider is behavioural.)

**Runner adaptations: none.** The runner ran byte-for-byte as committed, full
duration (no `TSTOP_OVERRIDE`/`TAVG0_OVERRIDE`), with the committed
ideal-capacitor and `XCDECAP` substitutions it always applies (disclosed in
RECORD-005/RECORD-001). Its generated deck lives in its own `mktemp`
directory, which it deletes on exit; the deck is derived deterministically
from the hashed inputs above. The original CSV was copied aside before the
run because the runner writes to its historical filename inside the scratch
tree; the repository's historical CSV was never written.

## Command

```
git archive f54b9ef | tar -x -C /tmp/r229/hist
export PATH=/tmp/r229/bin:$PATH   # /tmp/r229/bin/ngspice -> /tmp/i195-ngspice/bin/ngspice (ngspice-46)
export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l
cd /tmp/r229/hist && sim/sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_cascbias.sh   # 2026-10-11T19:21:34Z .. 19:27:28Z, 5 m 54 s wall, exit 0
```

(RECORD-005 reported ~7.4 minutes on its host; wall time is host-load
dependent and is not a result.) Retained fresh outputs in `corners/` under
new names; the historical filename was not written (sha256 in parentheses):

- `lock_trace_proposal_cascbias_rerun229.csv` (`fda199af313678f6a36f552f1594a6b73ff8e9997a7337dd34169f318cc437f7`)
- `log_run_rerun229.txt` (`7cd878e299fc8b729b5e07b07c95281b66294242978363b26841046b8e482c32`, runner console output with the `.meas` values and the per-cycle trace rows)

## Result: reproduced

The 49-row trace is **byte-identical** to the version committed at
`f54b9ef` (same sha256; the identical hash is the evidence, not a
tolerance). RECORD-005's tabulated values are therefore reproduced exactly:

| Quantity | RECORD-005 | Rerun |
|---|---|---|
| `vctrl`: IC -> final | 2.46 V -> 2.38712 V | 2.46 V -> 2.38712103 V |
| `vc_avg` (2.0-2.5 us) / range | 2.386934 V / 2.350095-2.416685 V | 2.38693 V / 2.35009-2.41669 V |
| `i_cp` (2.0-2.5 us) | -39.26 uA | -39.2565 uA |
| `i_pfd` / `i_vco` / `i_ld` (2.0-2.5 us) | not tabulated | -57.549 uA / -2.01228 mA / -44.468 uA |
| Reference cycles observed | 49 | 49 |
| `Delta f/f_ref`, final 20 cycles | -0.00900% to +0.01250%, mean -0.00020% | -0.00900% to +0.01250%, mean -0.00020% |
| Static phase error, final 20 cycles | 8.200% to 8.221%, mean 8.203% | 8.200% to 8.221%, mean 8.203% |
| Longest dual-lock run | 4 cycles (`t` = 100-250 ns) | 4 cycles (`t` = 100-250 ns) |
| Longest freq-lock-only run | 42 cycles, `t` = 400 ns to 2.45 us | 42 cycles, `t` = 400 ns to 2.45 us |
| `lock_time` | `None` | `None` |

Every limitation and failure of RECORD-005 therefore stands unchanged and is
retained: the loop is frequency-locked but settles at an 8.203% static phase
error against the 5% criterion; the dual-lock run stays at 4 cycles;
`lock_time = None`; row 7 still fails for the mitigated design. The
switching/dynamic charge-mismatch explanation RECORD-005 offers is the
original's untested candidate, not something this rerun tests (RECORD-006
and later records address it).

## What this does not bound

- Single nominal point only; no corner or Monte Carlo result exists in this
  record, same as RECORD-005. It does not imply coverage of the full-PVT
  grid owed under #139.
- Part B proposal deck only (behavioural divider); no repaired-divider,
  committed-design or post-layout claim.
- It does not recover the original's PDK revision, tool build or host: the
  addendum is `superseded`, not `recovered`. A byte-identical outcome on the
  pinned trees is consistent with, but does not prove, the original
  environment.
- ngspice-46 here is a scratch build whose provenance is only its hash.
- Item 9 stays unmet: other grandfathered records remain unresolved.
- No consumer citation changed numerically: every number cited from
  RECORD-005 (8.203% static phase error, 4-cycle dual-lock run,
  `lock_time = None`, `i_cp` -39.26 uA) is reproduced exactly, so none is
  replaced. `characterization/records_baseline.json` is unchanged because
  RECORD-005 stays a cited historical record; this record is added to
  `characterization/sources.json` as required for new records.
