# RECORD-003: waveform-level check of the retimed capture edge at 1562 MHz (issue #362, follow-up of RECORD-002 Finding 4)

- **Slug**: `sg13cmos5l-divider-retiming-sizing`. Append-only; RECORD-001 and RECORD-002 are not edited.
  Consumes `../sg13cmos5l-divider-nrange-retiming/testbench/tb_div_retime.sp.tmpl` unchanged (the saved
  nodes and extra `meas`/`wrdata` are added only to the rendered deck copy by `gen_sizing_requests.py --waves`).
- **Issue**: #362 (gating follow-up of DR-012 / spec R-3). Spec not changed; no variant adopted; no sizing change.
- **Tool / backend**: ngspice-46 via `klt sim --backend batch --wait-for-capacity 600` (client
  `klt 0.9.2.dev683+g2b617f6dcc7e`, runner `klt 0.9.0`, compatibility `match`), PDK `ihp-sg13cmos5l`.
  Probe job `klt-sim-e39d15c09011` (1 unit, tt/27 C, 58 s), full request `klt-sim-d2cb22cab69c` (2 units,
  59 s), both Spot fleet, both `pass`, no local `ngspice`. The probe and the full request's tt/27 C unit give
  identical edge tables. The batch backend **does** return a `wrdata` output file (`waves.dat`), so no
  in-deck-`meas` fallback was needed for the conclusion.
- **PDK revision**: `sim/README.md` pins `ihp-sg13cmos5l` `607e18d4bd9214a52575c194b4181ef449f9252f`. The
  batch reports carry no PDK identity, so the ran-on revision is **inferred, not measured**, exactly as in
  RECORD-001/002: `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14` (the `.pdk-store.json` version), which is NOT the
  README pin. The same PDK-confound caveat applies. Not re-established here.
- **Reproduce**: `python3 -I testbench/gen_sizing_requests.py retime b:b --corners tt2 --waves` then
  `klt sim testbench/retime_b-b_tt2_waves.request.json --backend batch --wait-for-capacity 600 -o <dir>`;
  `python3 -I testbench/analyze_waves.py <dir>/<unit>/waves.dat 3.3` reproduces the table
  (`corners/capture-edge-waveform.csv` is its `--csv` output; checked from the committed tarball).
  Raw outputs `corners/raw-retime-waves-tt27-ttm40.tar.gz`, batch report `corners/report-retime-waves-tt27-ttm40.json.gz`.

## Method and corner coverage

Base chain (`b:b`, unmodified `dff_tg_hv` in `XFRT`), N=64 (`P0..P5` = 0), 1562.0 MHz (`T_vco` = 640.20 ps),
**corners: mos_tt/27 C/3.3 V and mos_tt/-40 C/3.3 V** (the two RECORD-002 Finding 4 corners; the other
resolved corners and the ss/27 C and tt/125 C non-dividing corners were not re-run). Saved nodes (`.save`):
`v(ck)` (= `CKIN_VCO`), `v(divout)` (= `XFRT` D), `v(fb)` (= `XFRT` Q), `i(vdd)`, and the `XFRT` internals
`v(xdiv.xfrt.clkb)`, `.m` (master), `.s` (slave), `.sb`; time step 0.02 T, 0 to 4N T; `wrdata` of the seven
voltages. Edges are 50% (`VDD/2`) linear-interpolated crossings. A capture is attributed to the **last CK
rising edge before the FB edge** (`ck_rises_between` counts CK rises strictly between the `DIVOUT` and the
`FB` edge). Both polarities were read; RECORD-002 and RECORD-003 (nrange) read only the rising pair.

## Finding 1: the rising edge is captured at k+1 with a stretched clk->Q; the falling edge is captured at k+2

`corners/capture-edge-waveform.csv` (settled edges, #2 of each polarity; #1 is start-up and agrees):

| Corner | edge | `DIVOUT` to next CK rise (ps) | `FB` after `DIVOUT` (ps) | CK rises between | capture | clk->Q (ps) |
|---|---|---|---|---|---|---|
| tt/27 C | rise | 185.3 | 636.4 | 1 | k+1 | 451.1 |
| tt/27 C | fall | 122.9 | 1251.3 | 2 | k+2 | 488.2 |
| tt/-40 C | rise | 71.4 | 458.8 | 1 | k+1 | 387.4 |
| tt/-40 C | fall | 75.1 | 1121.5 | 2 | k+2 | 406.3 |

- **Rising `DIVOUT` (the pair RECORD-002/RECORD-003 measured as `tfb - tdiv`)**: `FB` rises after exactly one CK
  rise, i.e. next-edge (k+1) capture. This confirms RECORD-002 Finding 4 and **excludes the k+2 reading of
  nrange RECORD-003 Finding 4 for the rising edge**. At tt/27 C the master `m` crosses 50% at 86.4494 ns, 8 ps
  before the CK rise at 86.4577 ns, then stalls at about 2.4 V (73% of VDD) while the master closes (`clkb`
  falls 86.5446 ns); the slave regenerates from that marginal level, `sb` falls at 86.8656 ns and `FB` rises at
  86.9088 ns, **451 ps after the capturing CK edge**. Unambiguously the capture is k+1 and the clk->Q is
  stretched by a near-setup master level, not by a one-period-late capture.
- **Falling `DIVOUT`**: the first CK rise after the edge (+122.9 ps at tt/27 C, +75.1 ps at tt/-40 C) is **not**
  a clean capture. At tt/27 C `m` falls at 45.4873 ns, rises again at 45.6347 ns (back toward the old value
  while the master is closed) and only falls for good at 46.0395 ns once the master reopens (`clkb` rises
  45.9273 ns); `s` falls at 46.4098 ns and `FB` at 46.6129 ns, 488 ps after the **second** CK rise. The
  falling edge is therefore taken one `T_vco` later (k+2); the flop recovered after the first edge's marginal
  capture, it did not fail permanently. tt/-40 C shows the same `m` fall-rise-fall pattern (44.839, 44.992,
  45.057 ns ...) and `s` falling in the second slave window (45.727 ns).
- **Consequence**: the retimed `FB` has a rising delay of `T - t_arr + clk->Q` and a falling delay about one
  `T_vco` longer (636 vs 1251 ps at tt/27 C; 459 vs 1122 ps at tt/-40 C), so the 1562 MHz in-situ output is
  duty-distorted by about one VCO period. RECORD-002's `tfb - tdiv` pairs only the rising edges, so that
  figure alone does not show this. (Not assessed here: whether a PFD/lock loop tolerates that distortion.)

## Finding 2: why the isolated setup deck disagrees (resolved in part)

- `t_arr` convention: the in-situ `DIVOUT` rise is 185.3 ps (tt/27 C) / 71.4 ps (tt/-40 C) before the next CK
  rise at the 50% points, 30 ps more than RECORD-002's `T - t_arr` (155.3 / 41.4 ps), because the CK source
  is `pulse(0 VDD 0 60p ...)`: its 50% crossing is 30 ps after `t = 0`, which `tdiv mod T` does not include.
  Finding 1 is waveform-direct and does not depend on it.
- The isolated setup deck counts a capture only if `Q` is correct at `t_cap + T/4` (160 ps). The in-situ
  captures resolve 387 to 488 ps after the capturing edge, which that criterion would score as a failure for
  every one of them. The 500 to 600 ps setup bracket is thus a bound for **fast** (<160 ps) clk->Q, not for
  a logically correct capture with a stretched clk->Q; the in-situ flop produces a correct rising capture at
  185 ps / 71 ps of data-before-clock because it is allowed 450 / 390 ps to resolve.
- Also different: the isolated deck drives `D` with an ideal edge, the in-situ `DIVOUT` has a slow edge
  (50% to 90% about 330 ps at tt/27 C). **Not done**: an isolated deck with the in-situ `D` edge and a
  relaxed `Q` sample time to reproduce 451 ps; so this explanation is from the waveforms, not a reproduced
  isolated clk->Q.

## What this does and does not decide

- Narrows nrange RECORD-003 Finding 4: rising edge k+1 (not k+2); the k+2 behaviour appears on the falling
  edge. RECORD-002 Finding 4's k+1 reading is confirmed for the rising edge.
- The deck-arithmetic bounds in RECORD-002 Findings 1 and 3 (isolated brackets) are **not** a statement of
  logical correctness at 1562 MHz; the waveform shows logically correct, duty-distorted retiming at the two
  corners here. Whether that suffices for R-3 is a decision, not shown here; ratifiers also lack the other
  seven corners' waveforms. R-3 is unchanged.

## Not done (stated, not hidden)

- Other corners (ff, fs, sf, 2.97/3.63 V, ss/27 C, tt/125 C) and N=127 were not re-run with waveforms; only
  tt/27 C and tt/-40 C. `@neg` and resized variants were not run. Duty-cycle effect on PFD/lock not simulated.
- Offline ngspice only; spec, `design/` and the nrange template untouched. Live verification is not applicable
  beyond ngspice.

## Proposed decision

`spec/decision-records/DR-012-row3-retiming-sizing-limit.md` (still proposed) is updated: the Finding 4
check is done for two corners, the rising capture is k+1 and the falling capture k+2; R-3 stays open.
