# RECORD-008: rerun of RECORD-002's PFD parity diagnostics on the pinned dual-tree environment (issue #226)

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #226 (Part of #211 / #199, item 9 provenance migration).
  Append-only. This record reruns the diagnostics of
  `RECORD-002-pfd-reset-parity-root-cause.md` and is the `ADDENDUM-RERUN`
  target of `ADDENDUM-001-pfd-parity-superseded.md`. It neither edits
  `RECORD-002-pfd-reset-parity-root-cause.md` nor any historical CSV.
  It supersedes only that record's *evidence claim* for the two diagnostics
  below. It is not evidence for RECORD-001, -003, -004, -005, -006 or -007.
- **Scope**: single-corner diagnostics (`mos_tt`, 27 C, 3.3 V), pre-layout,
  one local `ngspice -b` per case, sequential. No PVT grid, so none went to
  the batch fleet. Not a lock, reference-spur or repaired-divider result.
- **PDK revisions** (checked on the run host, read 2026-10-11):
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  (`git rev-parse HEAD` of `~/share/pdk/ihp-sg13cmos5l`, `git status
  --porcelain` empty), and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (upstream `v0.3.0`; the host tree is a release-tarball install,
  `.fetched-version` = `0.3.0`, and its `psp103/psp103_nqs/mosvar/r3_cmc`
  OSDI objects have the same sha256 as the ones `sim/README.md`'s pin
  verification covers). The sg13g2 revision is therefore the pin, supported by
  the version marker and OSDI hashes, not by a git checkout on this host.
  The cmos5l tree reads its `psp103` models and OSDI objects through
  symlinks into the sg13g2 tree, so both trees are cited.
- **Tool**: ngspice-46 (`** ngspice-46 : Circuit level simulation program`),
  x86-64 Linux. The host's `/usr/bin/ngspice` is ngspice-42 and
  `~/.local/bin` has no ngspice, so the run used a scratch ngspice-46 build
  from another sweep: `/tmp/i195-ngspice/bin/ngspice`, sha256
  `f8c03b87208fab0622e6d06e57647ea5cea4153a4e3bfe5de0ded088b3acc87a`.
  Its build recipe/configuration was not verified here (limitation).
- **Host**: `loom-worker-3` (8 vCPU, x86_64). The original ran on an
  arm64 macOS host with unknown trees; this rerun does not prove that
  environment.

## Reconstruction of the historical bench

The complete bench was extracted unmodified with `git archive 65e2cb6` (full
commit `65e2cb6b38f2d89243cee1d48127f820da463bbb`, the commit that
introduced `RECORD-002-pfd-reset-parity-root-cause.md`) into an isolated
scratch directory (`/tmp/r226/hist`). Current snapshots are not used: the
live `netlist-snapshots/pfd.spice` already contains the #56 repair, so a
current-design rerun could not reproduce the defect. sha256 of the inputs as
extracted:

| File at `65e2cb6` | sha256 |
|---|---|
| `netlist-snapshots/pfd.spice` (as-drawn, defective) | `1eddb8b866459e64be9fb405e191fe2f9a5b012d0f3ce2ef8c267000180c32a4` |
| `netlist-snapshots/cp.spice` | `05303ffe364a3ac569f7d6330209c2f97e93e14c1da034ee76e0a550e1bce271` |
| `netlist-snapshots/loop_filter.spice` | `89af2391d684073fdce198dbaab3632766cb4f9d93b00d1801ef4ebdbd33fd2e` |
| `netlist-snapshots/vco.spice` | `9d61ae66b60c87609ccd52bf7b1845153564170ae5b537f9b7ec83e3c2460f6c` |
| `netlist-snapshots/divider_chain.spice` | `89315a6cd6f373ec28067ee0ca01dd9d135052ef3b0f34bba53882d0f4a458a6` |
| `netlist-snapshots/lock_detector.spice` | `66f683ef6c66ff50aa2fa34597eb8bbc8c44c85d5d808cb521a6cf4dc86c68bf` |
| `testbench/run_pfd_diag.sh` | `f2a9976a428d568126a1a89d52d3aa7a5e211cf70a4e056dc63e08876ce6a5e2` |
| `testbench/run_closed_loop_pfdfix_diag.sh` | `601d8b7bc3e926c1835d0e217ea7222d728d1d706b003fc847d3146d11074f35` |
| `testbench/tb_pfd_only.sp.tmpl` | `81d05071e29b045fc48edbc2730b6bb6d47194b41ab16ce17c4a5f6e63e36ab3` |
| `testbench/tb_pll_proposal.sp.tmpl` | `99b4347cf37b5c14d2c973ca3f98671e4ff61377a905bba8f578dae8db7898d6` |
| `testbench/extract.py` | `0e0a92669188ec5159ed70bde6c0de92faeb8aff0fbe3d5a49a484ed55b7f1b9` |

**Runner adaptations: none.** Both historical runners ran byte-for-byte as
committed; the only difference is the output location (they write into the
scratch checkout's `corners/`, from which the files below were copied under
new names). The generated decks live in the runners' own `mktemp` work
directory, which they delete on exit, so they are not retained; they are
derived deterministically from the hashed inputs above. The OSDI list the
runners load (`psp103`, `psp103_nqs`, `mosvar`, and `r3_cmc` for the
closed-loop run) is from the installed tree; no model substitution was made
beyond the ideal-cap and `XCDECAP` substitutions the historical runner already
makes and `RECORD-002-pfd-reset-parity-root-cause.md` already discloses.

## Commands (run sequentially, one `ngspice -b` at a time)

```
git archive 65e2cb6 | tar -x -C /tmp/r226/hist
export PATH=/tmp/r226/bin:$PATH   # /tmp/r226/bin/ngspice -> /tmp/i195-ngspice/bin/ngspice (ngspice-46)
export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l
cd /tmp/r226/hist && sim/sg13cmos5l-closed-loop-lock/testbench/run_pfd_diag.sh              # 10.7 s wall
cd /tmp/r226/hist && sim/sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_pfdfix_diag.sh  # 56 s wall
```

The PFD diagnostic was run a second time; its CSV was byte-identical to the
first (deterministic on this host). Retained fresh outputs, all in
`corners/` with new names (sha256 in parentheses):

- `pfd_polarity_diag_rerun226.csv` (`bc12c5ad07af0295fc8d2ad35966f53ddde822a700301f9ccd82f72b109d3fe2`)
- `lock_trace_proposal_pfdfix_rerun226.csv` (`65fa88478be18d3fa5104ecff17f47ac195f0dd1bf18d7527714f9dd3031848d`)
- `log_pfd_diag_rerun226.txt`, `log_closed_loop_pfdfix_rerun226.txt` (runner console output, including the `.meas` values)

## Result 1: standalone PFD (as-drawn and diagnostic-patched, lead and lag)

Duty fractions (average / 3.3 V), historical `pfd_polarity_diag.csv` vs this
rerun:

| Variant | Case | `up` hist | `up` rerun | `dn` hist | `dn` rerun |
|---|---|---|---|---|---|
| as-drawn | REF leads FB | 0.70% | 0.70% | 0.71% | 0.71% |
| as-drawn | FB leads REF | 0.70% | 0.70% | 0.71% | 0.71% |
| patched | REF leads FB | 11.41% | **1.41%** | 1.40% | **91.41%** |
| patched | FB leads REF | 1.41% | 1.41% | 11.41% | 11.41% |

- **Reproduced (3 of 4 cases)**: both as-drawn cases are identical to the
  historical values to all printed digits, and are identical to each other, so
  the as-drawn PFD again does not distinguish REF-leads from FB-leads. The
  patched FB-leads case reproduces exactly (`dn` 11.41%, `up` 1.41%).
- **NOT reproduced (1 of 4)**: the patched REF-leads case. The historical run
  read `UP`-dominant (11.41% / 1.40%); this rerun reads `DN` at 91.41% and
  `UP` at 1.41%, which is not the textbook `UP`-dominant result and is not a
  mirror of the historical number either. The runner's own verdict column
  prints `DN-dominant/symmetric (no tristate hold)` for it. No cause has been
  established: the historical environment is unknown, so a simulator, model
  or initial-state difference cannot be separated from a real sensitivity of
  the patched circuit. The patched PFD's lead/lag discrimination is therefore
  confirmed only in the FB-leads direction by this rerun, and the historical
  claim that the patched PFD restores textbook behaviour for both directions
  is **not** supported by this rerun. What the rerun still supports is the
  defect itself: the as-drawn PFD is phase-blind (identical `UP`/`DN` duty
  for both lead/lag cases), and the patch changes that behaviour.
- The runner's `verdict` text in the as-drawn FB-leads row is the script's own
  heuristic and was not changed.

## Result 2: 400 ns closed-loop control with the patched PFD

`vctrl` 2.46 V to 2.3595 V (historical 2.360 V), `vc_min` 2.3203 V,
`vc_max` 2.3727 V. Normalised frequency error `delta_f_frac`:

| `t` | historical `lock_trace_proposal_pfdfix.csv` | rerun |
|---|---|---|
| 50 ns | +0.009982 | +0.009975 |
| 100 ns | +0.001985 | +0.001982 |
| 150 ns | -0.004019 | -0.004012 |
| 200 ns | -0.008544 | -0.008512 |
| 250 ns | -0.011254 | -0.011284 |
| 300 ns | -0.011864 | -0.011868 |
| 350 ns | -0.011852 | -0.011848 |

The rerun trajectory matches the historical one to within 3.3e-5 (absolute,
fraction of `f_ref`) at all seven points, including the deceleration and the
flat segment after 250 ns (-0.011868 to -0.011848). This reproduces
`RECORD-002-pfd-reset-parity-root-cause.md`'s bounded, qualitative closed-loop
claim. The comparison column "Part B, as-drawn PFD" in that record is the
unchanged `lock_trace_proposal.csv` and was not re-measured here.

Note that Result 2 reproduces even though Result 1 did not reproduce the
patched REF-leads case; the closed loop does not exercise a fixed lead
direction, so the two are not contradictory, but this record does not explain
the Result 1 discrepancy.

## What this does not bound

- It is not a lock demonstration: 400 ns is far short of the ~2.5 us
  `RECORD-001` needs, `delta_f` has not reversed sign, and no consecutive-cycle
  lock criterion is evaluated. No claim is made about full lock, reference
  spur, or the repaired divider.
- It does not re-measure the as-drawn closed-loop trace
  (`lock_trace_proposal.csv`), Part A, or the root-cause reasoning in the
  original (gate-level derivation), which remains the original's text.
- It does not recover the original's PDK revision or host; the addendum is
  `superseded`, not `recovered`.
- Item 9 stays unmet: other grandfathered records are unresolved, and the
  ngspice-46 binary used here is a scratch build whose provenance is only its
  hash.
- No consumer citation changed: `design/sg13cmos5l/pfd.sch`,
  `docs/chipalooza/challenge-6-proposal.md` and `characterization/` cite
  RECORD-002 for the defect's root cause (confirmed here) and the #56 repair,
  not for the patched REF-leads number that failed to reproduce, so nothing they
  state is replaced by this rerun.
