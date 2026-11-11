# RECORD-003: first output-buffer PMOS widened 10u -> 8.5u; 300-point duty-cycle grid rerun (issue #188)

- **Slug**: `sg13cmos5l-vco-duty-cycle`
- **Issue**: #188 (spec row 13, R-8, T1 item 5). Append-only. Edits no earlier
  record and no earlier `corners/` file. Baseline is RECORD-002 (the fleet rerun
  of RECORD-001; sha256 `2d307256d877c8083871752cba091628346dbc399ebf10d5e4ca74e499bfe54e`
  for the file as of base `ab1a643`), because it ran on the same fleet image
  this record ran on.
- **Design change (one)**: in `design/sg13cmos5l/vco.sch`, `XBUF1` (an
  `inv2x_hv`, P 10u / N 4u, L 0.5u) is replaced by two discrete devices
  `MBP1` (`sg13_hv_pmos`, **w = 8.5u**, l = 0.5u) and `MBN1` (`sg13_hv_nmos`,
  w = 4u, l = 0.5u). Nothing else moves: `XBUF2` stays `inv2x_hv` and the
  shared `inv2x_hv` cell is untouched (the `pfd` also instantiates it, so a
  cell edit would have changed the PFD).
- **Why that device (diagnosis)**: `CLK` is high while `ring1` is above
  `XBUF1`'s switching threshold, so the output duty is set by that threshold.
  A lower threshold (weaker PMOS) lengthens the high time. Single-corner
  probes at the worst point (`mos_fs`, -40 C, band 00, `VCTRL` 0.3 V, local
  ngspice, one run each) gave duty 43.71 % (P 10u), 46.80 % (8u), 48.51 %
  (7u), 50.2 % (6u), 54.4 % (4u); at the opposite extreme (`mos_ff`, 125 C,
  band 11, 2.7 V; baseline 51.50 %) 54.77 % (8u) and 56.98 % (7u). Hot gains
  as much as cold, so the window is centred, not just lifted: 8.5u was chosen
  to leave roughly 1 pp at each end. Only P width was swept (N fixed at 4u, plus
  one 10u/8u point for ratio sensitivity); the 8.5u choice is not an optimum.
  The ring-stage inverters were not varied, so this record does not say whether
  the cold skew originates in the ring or the buffer, only that the buffer
  threshold corrects it.
- **DUT**: `../netlist-snapshots/vco_issue188.spice` (sha256
  `5345ab5ebae0353eb148b5723385b535ccb80ce91713d9339a62ad4f21cb22cf`) is
  RECORD-001's frozen `vco.spice` with exactly the `XBUF1` edit above
  (the file header says so). It is **not** today's `design/sg13cmos5l/netlist/vco.spice`
  (which has moved on elsewhere, e.g. `sub!` bulk nets); keeping the rest equal
  to the baseline isolates the buffer change. `design/sg13cmos5l/netlist/vco.spice`
  carries the same two lines, hand-patched in the committed style: the local
  `xschem`/`klt netlist` appends `mm_ok=1` to every device, which would have
  rewritten the whole file, so the CI netlist gate (`netlist.yml`) is
  **not confirmed locally** and is left to CI.
- **Testbench**: `run.sh` and `tb_vco_duty.sp.tmpl` untouched. The grid is
  `../testbench/gen_issue188_requests.py` (a copy of `gen_rerun317_requests.py`
  that reads the new snapshot) and `../testbench/extract_issue188.py` (a copy of
  the rerun extractor). 308 decks: 300 grid + 8 timestep-convergence.
- **Host / fleet job**: batch job `klt-sim-b48072a41655`, `us-east-1c`,
  spot `m7i.4xlarge` `i-00b713bb01ba96194`, ami `ami-095c25ae241a4d360` (same
  image as RECORD-002), state `done`, 120 s, **308/308 passed, 0 errored**.
  Runner `klt 0.9.0`, client `klt 0.9.2.dev661+g1de5c0432aad`,
  `runner_compatibility: match`. A 2-unit probe (`klt-sim-407d160a904e`)
  ran first and passed. One grid submit; nothing run locally except the
  single-corner diagnosis probes above. Request sha256
  `3557b5c560c74420c6a20bed71ca0410d5ea3e0fccfe37faa4a8784a745c006f`.
  PDK pins and the worker-PDK observation are as RECORD-002 (same image); this
  record did not re-probe the worker PDK.
- **Command** (repository root, `KLT_SIM_BACKEND=batch`):

  ```
  python3 -I sim/sg13cmos5l-vco-duty-cycle/testbench/gen_issue188_requests.py OUT
  klt sim OUT/request.json --backend batch --wait-for-capacity 600 \
      -o OUT/out --format json --report-out OUT/report.json
  python3 -I sim/sg13cmos5l-vco-duty-cycle/testbench/extract_issue188.py \
      OUT/out OUT/decks.sha256.csv results_issue188.csv tstep_convergence_issue188.csv
  ```

## Outputs

`../corners/results_issue188.csv` (300 rows, no `NA`),
`../corners/tstep_convergence_issue188.csv` (8 rows),
`../corners/decks_issue188.sha256.csv`, `../corners/fleet_report_issue188.json`
(absolute `outdir` replaced by `OUTDIR`, nothing else edited).

## Result

| Quantity | RECORD-002 (baseline) | This record |
|---|---|---|
| duty range, 300 points | 43.71 - 51.50 % | **46.02 - 53.87 %** |
| points below 45 % | 31 | **0** |
| points above 55 % | 0 | **0** |
| worst low point | `mos_fs`, -40 C, band 00, 0.3 V: 43.71 % | same point: **46.02 %** |
| worst high point | `mos_ff`, 125 C, band 11, 2.7 V: 51.50 % | same point: **53.87 %** |
| `duty2` (second cycle) range | 43.78 - 51.42 % | 46.00 - 53.87 % |
| VCO supply current | 0.927 - 2.712 mA | 0.914 - 2.698 mA |
| period-derived frequency, all 300 | 431.5 - 1575.6 MHz | 444.0 - 1611.9 MHz |

Duty by corner and temperature (min - max, %), -40 / 27 / 125 C:
tt 46.97-50.16 / 48.73-49.77 / 52.20-52.51; ss 47.81-50.54 / 49.38-49.82 /
51.08-51.92; ff 46.44-50.24 / 49.30-51.18 / 52.91-53.87; sf 47.83-51.20 /
49.32-50.73 / 52.28-52.72; fs 46.02-48.88 / 48.56-49.45 / 52.16-52.32.

**Row 13: 0 of 300 points below 45 % and 0 above 55 %** at this grid, pre-layout,
open loop, no load, no mismatch (same limits as RECORD-001). The margin is thin
at both ends: 1.02 pp to the 45 % floor and 1.13 pp to the 55 % ceiling.

Timestep check (`tstep_convergence_issue188.csv`), 20 ps -> 5 ps: tt +0.064,
sf +0.010, fs +0.083, ss +0.017 pp. Largest 0.083 pp, against 1.02 pp margin.

## Regressions and side effects

- **Row 1 (output band) moves.** Changing the buffer's input device changes the
  load on `ring1`, and the period-derived frequency shifts: floor 431.5 -> 444.0 MHz (+2.9 %), ceiling
  1575.6 -> 1611.9 MHz (+2.3 %), same 300 points. The spec's row-1 figures
  (445.3 - 1562.0 MHz) are from the Kvco record's 3-bundle table, not this
  grid, so they are **not re-derived here**; the Kvco band table (rows 1, 4/5)
  is not rerun and should be rerun before it is cited with this buffer. The
  lighter `ring1` load (8.5u PMOS in place of 10u) is the likely cause; this
  record did not isolate it.
- **Row 11 (power, VCO domain)**: current is 1.4 - 1.5 % lower at the bounds
  (0.914 - 2.698 mA vs 0.927 - 2.712 mA); no regression.
- **Row 14 (output levels)** not measured here; the buffer's drive of the
  `CLK` pin is from `XBUF2`, unchanged, but `XBUF1`'s slew changed.
- **Layout**: `layout/sg13cmos5l-pll/` `vco` is out of scope. A layout
  follow-up is owed: `XBUF1` is now two discrete devices instead of an
  `inv2x_hv` instance, so the layout cell and its LVS reference differ.

## What this does not bound

Not tested: post-layout parasitics, closed-loop behaviour, random mismatch
(no Monte Carlo), output load other than the next stage. The 8.5u value is
not optimised against the full spec; row 1 and the Kvco table need a
re-baseline with this DUT. Ratification of the change is DR-012 (proposed).
