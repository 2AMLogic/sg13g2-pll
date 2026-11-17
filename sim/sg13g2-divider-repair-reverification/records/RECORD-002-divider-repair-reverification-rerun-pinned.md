# RECORD-002: SG13G2 `divider_chain` repair — hold, division and OP convergence re-measured on the batch fleet (supersedes RECORD-001's evidence claim)

- **Slug**: `sg13g2-divider-repair-reverification`
- **Issue**: #235 (execution child of #217, item 9). Same-bench rerun of
  `RECORD-001-divider-repair-reverification.md` (unchanged, original file
  name cited as required by the addendum contract; see
  `ADDENDUM-001-record-001-superseded.md`).
- **DUT**: `../netlist-snapshots/divider_chain_repaired.spice`, the frozen
  RECORD-001 snapshot, byte-for-byte unchanged (frozen from `design/` at
  `8cced83`, issue #120). The design was not regenerated.
- **Claim re-measured**: the repair holds, divides exactly, and has a DC
  operating point on `ihp-sg13g2`, at RECORD-001's own scope (`opconv`, `hold`,
  `func`; same 9-point reduced PVT matrix, same word sweep, same reltol arms).
- **PDK revision**: `ihp-sg13g2` revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (the `sim/README.md` pin). **Not independently observed on the fleet:** the
  runner reported `pdk stamp unreadable: FileNotFoundError`
  (`pdk_stamp_comparison` unavailable) and `variant: ihp-sg13g2`, root
  `/opt/pdk`, so the revision is taken from the repo pin, as in
  `sg13g2-pfd-reset-parity` RECORD-001. This all-MOS DUT reads only
  `ihp-sg13g2` model cards (no CMOS5L tree involved).
- **Tool**: `ngspice-46` (runner `/usr/local/bin/ngspice`, from each report's
  `environment.worker_environment`); runner `klt` 0.9.0, client `klt`
  0.9.2.dev661 (`1de5c0432aad`), `runner_compatibility: match`. OSDI:
  `psp103`, `psp103_nqs`, `mosvar`, `r3_cmc` baked on the image
  (`options.osdi_preload`).
- **Host / runner**: batch fleet (`aws-batch-fleet`, `us-east-1`, spot;
  m6i/m7i/c6i/c7i instances), requested from `loom-worker-1`. Job ids below.
- **Command**: `python3 testbench/gen_batch.py` then
  `klt sim requests/probe_func_tt27.request.json --backend batch --wait-for-capacity 600 --format json`
  (probe), then
  `klt sim --batch-set <22 requests> --max-in-flight 4 --capacity-retries 3 --wait-for-capacity 600 --format json`
  (`testbench/run_batch.sh`); reduction `python3 testbench/analyze_batch.py`.
  Raw reports: `corners/reports/*.klt-report.json`, reduced CSVs
  `corners/*_r002.csv` (new paths; RECORD-001's CSVs untouched).

## Probe first

One corner (`mos_tt`, 27 C, 3.3 V, word 000000, `tb_div_func`) as job
`klt-sim-1bf42451d437`: pass, and its 19 values equal RECORD-001's
`baseline,mos_tt,27,3.3` row. Only then was the grid submitted.

## Jobs (23)

| Request | Units | Job id | Status |
|---|---|---|---|
| probe_func_tt27 | 1 | klt-sim-1bf42451d437 | pass |
| func_baseline_mos5 / _temp / _vdd | 5 / 2 / 2 | klt-sim-39eb1a712c06 / -329b9e6b87c3 / -074c624f9a42 | pass |
| func_code_000001 | 1 | klt-sim-4ba06c72e4a9 | pass |
| func_code_000010 | 1 | klt-sim-84aa868d81e9 | pass |
| func_code_000100 | 1 | klt-sim-6343275cf416 | pass |
| func_code_001000 | 1 | klt-sim-9b6e4c51fcf3 | pass |
| func_code_010000 | 1 | klt-sim-b97cce982ad7 | pass |
| func_code_011111 | 1 | klt-sim-5ceb8ba1c33b | pass |
| func_code_100000 | 1 | klt-sim-911c9cb5837d | pass |
| func_code_101010 | 1 | klt-sim-f709ac487d44 | pass |
| func_code_111111 | 1 | klt-sim-f3e577c0e033 | pass |
| func_edge_mos_ss_125 / _mos_ff_-40 | 1 / 1 | klt-sim-3dea2bdeeed7 / -eebb8c74ffe2 | pass |
| func_tol_0.001 / 0.002 | 2 / 2 | klt-sim-472c8afb18e5 / -fdcbe34b5bcd | pass |
| func_tol_0.005 | 2 | klt-sim-627506245f55 | **error** (both corners) |
| hold_mos5 / _temp / _vdd | 5 / 2 / 2 | klt-sim-f98be984313f / -c3614257f0a5 / -832035bf2d29 | **error** (see below) |
| opconv_none / opconv_ic | 1 / 1 | klt-sim-436ce60f1fcf / -0fd63f9c7c51 | pass |

## Results

| Quantity | Result |
|---|---|
| DC operating point (`opconv`), both ic modes | converges in both (`opconv_r002.csv`) |
| Latch hold, 9 PVT corners | `q_end` = `s_end` = the corner's own VDD at 9/9 corners (`hold_r002.csv`); `t_decay` has no value at any corner (Q never leaves the rail) |
| Division ratio, 9 baseline corners (N=64) | measured ratio 64.00 at 9/9 |
| Programming-word sweep (mos_tt/27 C/3.3 V) | measured ratio equals N = 64 + word for all nine words: 65, 66, 68, 72, 80, 96, 95, 106, 127 |
| Ceiling word 111111 (N=127) at mos_ss/125 C and mos_ff/-40 C | 127.00 at both |
| Average supply current | -1.99e-4 A (2.97 V) .. -2.57e-4 A (3.63 V) across the 9 corners; -2.28e-4 A nominal |
| `reltol` 0.001 / 0.002 at mos_tt/27 C and mos_ss/125 C | ratio 64.00 at all four; idd shifts by +1.5 % / +0.9 % (tt / ss) from 0.001 to 0.002 |
| `reltol` 0.005 at the same two corners | **both fail** (`timestep too small`, node `xdiv.xd0.nt`, at 1.21 us tt and 0.125 us ss); all measurements NA |

### Agreement with RECORD-001

`testbench/analyze_batch.py` compares by key against RECORD-001's CSVs
(read-only): all 6 rows present in `corners/func.csv`, all 9 in
`corners/hold.csv` and both in `corners/opconv.csv` reproduce, max relative
difference 0 at the printed 5 significant digits. RECORD-001's `func.csv`
holds only 6 of the 20 `func` rows its harness defines (and no tolerance
CSV), so the other 14 func rows and all six tolerance rows are first
measurements, not reproductions.

## Failed corners and limitations (kept, not hidden)

- **`hold_*` jobs report `error` to klt**, solely because the `t_decay`
  measurement ("`when v(q)=0.9*VDD fall=1`") finds no crossing ("out of
  interval"). That is the intended outcome (Q never decays), the same NA
  RECORD-001 wrote; `q_end`/`s_end` measured `pass` at all 9 corners. It is a
  harness semantic (an expected-absent measurement counted as an error by
  the runner), not a hold failure.
- **`reltol=0.005`: both corners aborted** with `timestep too small`. This
  reproduces the fragility RECORD-001 attributed to the port campaign's
  RECORD-003 Finding 2; it is retained as evidence, and no reading depends on
  it.
- **Transferred CMOS5L `setup`/`retime` evidence is excluded.** RECORD-001's
  top-of-band setup/retime claims were transferred from the CMOS5L port and
  are not re-measured here. They are not part of this record's claim and
  remain a non-fresh number until #233 delivers validated replacement
  evidence (with both tree revisions).
- The reduced one-factor 9-point matrix is unchanged (no cross-corners; see
  `../corners/matrix.md`). No Monte Carlo, no post-layout parasitics.
- The runner's PDK stamp was unreadable, so the PDK revision is the repo pin
  and not an observed fleet fact. Packing `reltol` via `ngspice_options` and
  the supply/bit values via `corners.params` reproduces the original decks'
  numbers, but the batch request bodies are new files, not the original
  templates.
- Solver-level determinism between local and batch runs was not separately
  tested beyond the matching rows above.

## What this does not bound

Same as RECORD-001: no claim at top-of-band VCO frequency (setup/retime), no
closed-loop behaviour, no layout parasitics. No existing consumer
figure was replaced or re-pointed; `characterization/sources.json` only gains
a listing of this record as a new dataset (required by `check_records.py`),
and RECORD-001's dataset is marked superseded; integration is #218's. Item 9
stays unmet while any grandfathered record is unresolved.
