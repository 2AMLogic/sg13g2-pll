# RECORD-001: top-level `pfd` reset-chain parity (3-stage) restores lead/lag discrimination across PVT

- **Slug**: `sg13g2-pfd-reset-parity`
- **Issue**: #283 (sibling of #56 / PR #71, which fixed `design/sg13cmos5l/pfd.sch`)
- **Claim under test**: with an even number of inverters after `reset_raw = NAND(UP,DN)`
  (as-drawn `XI1`, `XI2`) `reset` is `NAND(UP,DN)`, so the SR latches stay transparent and
  UP/DN collapse to symmetric blips; adding `XI1B` (odd parity, `reset = AND(UP,DN)`)
  restores UP/DN dependence on lead/lag direction.
- **Tooling**: `ngspice-46` on the batch runner (`/usr/local/bin/ngspice`, from the job
  `environment.worker_environment`); `klt` client 0.7.1.dev (runner 0.7.0, `runner_compatibility: match`).
  Jobs `klt-sim-844b97f9f07c`, `klt-sim-1fa584943aa1`, `klt-sim-8cfae86a511c`, `klt-sim-0dbc8d1682f1`
  (aws-batch-fleet, spot). The local host's ngspice is 42 and cannot load the v0.4 PSP103 OSDI, so no
  local run was possible; every number here is fleet output.
- **PDK revision**: `IHP-Open-PDK` commit `5cccb161f7492697cfa52eb14dc03beb00bdca9e` (the repo pin,
  `sim/README.md` `PDK-PIN ihp-sg13g2`). **Not independently confirmed for this run:** the runner reported
  `pdk stamp unreadable: FileNotFoundError` (`pdk_stamp_comparison: not_comparable`), so the fleet-side
  `/opt/pdk` tree's revision is taken from the repo pin, not observed.
- **Device under test**: `netlist-snapshots/pfd_before.spice` = `design/netlist/pfd.spice` at
  `origin/main` `26247c1`; `pfd_after.spice` = the regenerated `design/netlist/pfd.spice` of this change.
  The after netlist differs from before only by `XI1B` and the `reset_d2` net (`klt netlist` output,
  banner/`.subckt` post-processing as in `design/lib/netlist-export.sh`).
- **Method**: PFD-only (no cp/filter/vco). REF and FB are 20 MHz, 3.3 V pulse trains with a fixed 5 ns
  offset every cycle (`reflead`: REF first; `fblead`: FB first). UP/DN are averaged over 200-500 ns and
  reported as a fraction of VDD. Grid: `mos_tt/ss/ff` x -40/27/125 degC, VDD 3.3 V, per variant per case
  (36 corner runs). Verdict "textbook" requires the expected output to exceed the other by > 0.05 VDD.
  Reports: `corners/reports/*.klt-report.json`; reduction: `testbench/analyze.py` -> `corners/pfd_parity.csv`.

## Result

| variant | case | corners textbook | UP duty / DN duty (tt, 27 C) |
|---|---|---|---|
| before | reflead | 0 / 9 | 0.0070 / 0.0071 |
| before | fblead | 0 / 9 | 0.0070 / 0.0071 |
| after | reflead | 9 / 9 | 0.1135 / 0.0134 |
| after | fblead | 9 / 9 | 0.0135 / 0.1135 |

- **Before**: UP and DN are equal to within 0.0001 VDD in every corner for both directions (no lead/lag
  discrimination); at `mos_ss`/125 C both outputs are stuck at 1.0000 VDD. This reproduces the issue's defect.
- **After**: UP dominates when REF leads and DN dominates when FB leads in all 9 PVT corners, with the lagging
  output at roughly the reset-pulse width (0.010-0.019 VDD) and the leading output at ~0.11 VDD (the 10 %
  offset plus the reset pulse).
- **Parity alone was sufficient** for this PFD-only check at every corner run. The issue flagged "other
  corners" as untraced; none of the 9 corners here needed anything beyond `XI1B`.

## What this does not bound

- Closed-loop lock at the top level was not re-run (out of scope for #283; the issue asks for the PFD-only check).
- No VDD variation (3.3 V only), no Monte Carlo, no post-layout PEX (#102 is separate).
- The reset pulse width is a placeholder per the `pfd.sch` note; no claim about CP turn-on margin.
- Fleet-side PDK revision not observed (see above).

## Tool friction

- `options.osdi_preload` with host paths is refused for `backend: batch`; the same request with
  `$PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/osdi/*.osdi` (image-baked) is accepted and runs. This differs from
  `sim/sg13g2-hbt-characterization` RECORD-001, which concluded PSP103 grids could not go to the fleet.
- `design/netlist.sh` (raw `xschem`, no hang guard) cannot be used on dispatch workers; `klt netlist` was
  used instead, with the script's post-processing applied by hand. The CI check `netlist.yml`
  (`design/netlist.sh --check`, xschem 3.4.7) is the regeneration gate; the local `klt netlist` ran xschem 3.4.4
  and the committed banner line (`XSCHEM V3.4.7`) was preserved.
