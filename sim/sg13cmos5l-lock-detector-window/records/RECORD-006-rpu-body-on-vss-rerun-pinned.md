# RECORD-006: rerun of RECORD-005's nominal `*_bodyfix_nominal` campaign on the pinned dual-tree PDK (issue #256)

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #256 (child of #213, Part of #199, item 9 provenance migration).
  Append-only. This record reruns `RECORD-005-rpu-body-on-vss.md`
  (sha256 `15313f19b3bb3d73e0ef5f9687eb0a016901f58fb578d7f79e6821a93ffa03a6`,
  verified unchanged) and is the `ADDENDUM-RERUN` target of
  `ADDENDUM-001-record-005-superseded.md`. It does not edit RECORD-005, any
  earlier record, or any committed `corners/` file.
- **What was rerun**: exactly RECORD-005's claim — the **nominal single
  corner** (mos_tt / res_typ / 27 °C / 3.3 V, primary `real` DUT variant,
  3.5 MHz ladder, 20 ps timestep check) of the `lock_detector` bodyfix DUT
  (`XRPU` bulk re-declared on `VSS`, issue #136), through the same six
  nominal decks that produced RECORD-005's
  `corners/*_bodyfix_nominal.csv` set. Nominal only: the full-PVT grid
  stays owed as **#139** and is **not** satisfied or claimed here.
- **DUT — the original, not today's design**:
  `../netlist-snapshots/lock_detector_bodyfix.spice` (sha256
  `3fa570b22d3bbdb7f91092048dc6961cee4412646352d6474952da06b34abbe1`) is
  byte-identical to the same path at `3fd7967`, the commit that added
  RECORD-005 (`git diff 3fd7967 HEAD -- <snapshot>` is empty), and equals
  today's `design/sg13cmos5l/netlist/lock_detector.spice` modulo comments.
  No reconstruction was needed: the frozen snapshot RECORD-005 measured is
  still the one in the tree, so the rerun measured the original DUT bytes.
- **Testbench — one new file, disclosed**:
  `../testbench/run_rerun256.sh` is a copy of this tree's
  `../testbench/run.sh` with exactly two changes, so the rerun can never
  overwrite the outputs RECORD-005 committed: (1) the header block, and
  (2) the output suffix — `NOMINAL_ONLY=1` writes
  `*_bodyfix_nominal_rerun256` instead of `*_bodyfix_nominal` (the full-grid
  arm writes `*_bodyfix_rerun256` and stays refused on batch-backend hosts,
  exactly as in `run.sh`). Everything below the header — matrices,
  templates, thresholds, DUT snapshot, preflight, retry logic — is
  byte-identical to `run.sh` (`diff run.sh run_rerun256.sh`: the header
  block and the one `OUT=` line only). `run.sh` itself is untouched and
  remains the bench's entry point.
  One drift against the producing revision is disclosed:
  `run.sh` at `3fd7967` sourced the per-bench `testbench/gen_ladder.py`,
  which has since moved verbatim to the shared
  `sim/tools/gen_lock_ladder.py`; today's `run.sh` (and therefore
  `run_rerun256.sh`) imports the shared copy. That is a file relocation,
  not a behavioural change, and the byte-identical outputs below are the
  measurement of it.
- **PDK revisions** (checked on the run host, 2026-10-13):
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  (`git -C ~/share/pdk/ihp-sg13cmos5l rev-parse HEAD`, clean checkout), and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (upstream `v0.3.0`; the host tree is a release-tarball install,
  `.fetched-version` = `0.3.0`, not a git checkout; the revision is the pin
  established in `sim/provenance-migration.md`). Both trees are read: the
  `cornerMOShv.lib` model card and the PSP/mosvar/r3_cmc OSDI objects are
  symlinks from the cmos5l tree into the sg13g2 tree.
- **Tools**: ngspice-46, run through the same scratch binary
  (`/tmp/issue-584-ngspice/prefix/bin/ngspice`, sha256
  `cc3ad3951c86155806229a8a2257be60d2db01d090f5a160c401632791fd82b7`)
  RECORD-003 of `sg13cmos5l-klt-pex-signoff` used and disclosed (a
  user-space build left on this host by another sweep; its build recipe was
  not verified here either). The host's provisioned `/usr/bin/ngspice`
  (ngspice-42) cannot load the PSP OSDI objects ("NGSPICE only supports
  OSDI v0.3 but ... targets v0.4") — probed and confirmed before the run,
  same host-spec gap RECORD-003 retained. `klt 0.7.1.dev256+gaf7a43de415a`
  (fleet gate on this host; not used by the decks), python3 3.12.3.
  `sim/tools/check-osdi-arch.sh` exits 0 (`cap_cmomi.osdi` loads, x86-64),
  so the primary DUT variant is `real` and the nominal C values come from
  the OSDI model (`source` column `ngspice-osdi`), exactly as in RECORD-005.
- **Host**: `loom-worker-3`, x86-64 Linux, 8-vCPU shared dispatch worker.
  `KLT_SIM_BACKEND=batch` is exported by the daemon; this is one nominal
  corner, run locally as a single unit — no corner loops, no grid, no batch
  submission.
- **Command** (from the repository root):

  ```
  NOMINAL_ONLY=1 PDK_ROOT=$HOME/share/pdk PDK=ihp-sg13cmos5l \
    PATH=/tmp/ngs46-256:$PATH \
    bash sim/sg13cmos5l-lock-detector-window/testbench/run_rerun256.sh
  ```

  where `/tmp/ngs46-256` is a one-line wrapper directory whose `ngspice`
  execs the scratch ngspice-46 under `taskset -c 0,1` (2-core pin, host
  budget). Sequential, `LADDER_JOBS` unset; ~2.5 min wall.

## Result: every output byte-identical to RECORD-005's

All seven outputs match RECORD-005's committed files byte for byte
(`diff`-verified; `solver_retries` is empty on both sides — no deck needed
the `trtol=1` retry):

| Output (`corners/`) | vs RECORD-005's `*_bodyfix_nominal.*` |
|---|---|
| `rc_extract_bodyfix_nominal_rerun256.csv` (3 rows) | **byte-identical** — `R(XRPU)` 2.266979 MΩ; `C(XCW)` 1.691196 pF; `C(XDW.XC1)` 3.382393 pF |
| `window_bodyfix_nominal_rerun256.csv` (1) | **byte-identical** — `twin_r`/`twin_f` 6.66809 / 5.66503 ns (≥ 2.5 ns floor: met) |
| `schmitt_bodyfix_nominal_rerun256.csv` (1) | **byte-identical** — `V_TH+`/`V_TH−`/hyst 2.07836 / 1.13657 / 0.94179 V (28.5391 % VDD) |
| `ladder_bodyfix_nominal_rerun256.csv` (1) | **byte-identical** — assert/de-assert 5.00× / 8.00× window; hysteresis 20.00427 ns = 300 % of window (≥ 25 %: met); chatter `steady`; `trec` 2.88224 µs; `idd_inlock`/`idd_outlock` (10× probe) 2.87678 µA / 62.2499 µA; settled states `IIIIIIIIIIIIOOOOOOOOO` / `IIIIIIIIIIIIIIIOOOOOO`; R·C/T_ref = 13.419, 54 cycles, settle_frac 0.9821 |
| `ladder_raw_bodyfix_nominal_rerun256.csv` (21) | **byte-identical** (all 21 rows, levels included) |
| `tstep_convergence_bodyfix_nominal_rerun256.csv` (1) | **byte-identical** — `twin_r` at 20 ps 6.66809 ns |
| `solver_retries_bodyfix_nominal_rerun256.txt` (empty) | **byte-identical** |

So the pinned-PDK rerun reproduces RECORD-005's nominal corner **exactly**,
down to the last written digit, including the 21-row raw ladder that
RECORD-005 had disclosed at 6th-significant-digit solver-noise level
against RECORD-004: at this corner, on this toolchain, the noise is not
merely below reporting threshold — it is absent.

## Coverage and scope (unchanged from RECORD-005)

This record measures **one corner** of the bodyfix DUT and nothing more.
The MOS-corner, resistor-corner, temperature, supply, f_ref and MOM-band
axes are **not swept**; the coverage table in RECORD-005 (and the reason
each axis is owed) carries over verbatim. The full-PVT row-16/row-11
verdicts remain RECORD-004's, carried on RECORD-005's nominal-corner
identity — now itself reproduced at the pinned dual-tree PDK revisions.
**#139 stays open and owed.**

## What this does not bound

- **Any non-nominal corner of the changed DUT** — owed as #139, not run.
- **Post-layout behaviour** — schematic-level only; #157 is a different
  scope (layout extraction) and is not touched.
- **The SG13G2 `lock_detector`** — `design/netlist/lock_detector.spice` is
  a different DUT in a different campaign; not measured here.
- **The original run's environment** — a rerun does not prove what
  RECORD-005's 2026-10-03 session ran against; that remains unproven by
  design (`ADDENDUM-KIND: superseded`, no `ADDENDUM-PDK`/`ADDENDUM-TOOL`).
- **No failed attempts to retain**: one run, no retries, no
  interruptions. (An earlier dispatch of the same issue within this claim
  had left the same-named output files uncommitted in the worktree; the
  recorded run regenerated them and they are the files committed here.)
