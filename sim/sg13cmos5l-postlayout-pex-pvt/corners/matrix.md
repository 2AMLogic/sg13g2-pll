# Corner matrix — `sg13cmos5l-postlayout-pex-pvt`

**Claim under test**: not a new spec row. This record re-runs **two already-
ratified corner matrices, unchanged**, against parasitic-annotated netlists
extracted from the routed layout, and analyses the difference against the
schematic-level result. Issue #30 (Part of #16) is the named follow-up
issue #24 deferred post-layout PVT to.

Because the whole point is a controlled comparison, **this record invents no
axis of its own**. Both matrices below are copied verbatim from the campaign
whose numbers they are being compared against, and each is run **twice** —
once against the extracted netlist (`arm=postlayout`) and once against the
frozen schematic netlist (`arm=schematic`).

## Why both arms, rather than comparing against the committed CSV

The committed numbers were produced months earlier on a different session.
Comparing a fresh post-layout number directly against them would confound
"what the extracted interconnect did" with "what a different host/ngspice
did". Re-running the schematic arm here makes the comparison controlled,
and the agreement between that control arm and the committed CSV is itself
measured and reported rather than assumed — `control.csv` for the VCO
(60/60 points byte-identical) and the `cp` roll-up in `../records/RECORD-001`
(max |delta| 4.9e-5 %).

## Matrix A — `pll_vco`, open-loop frequency vs. `VCTRL`

Copied from [`../../sg13cmos5l-vco-kvco-table/corners/matrix.md`](../../sg13cmos5l-vco-kvco-table/corners/matrix.md),
including that record's own rationale for each axis and for the 3-bundle
(rather than full cross-product) PVT convention.

| Axis | Values |
|---|---|
| PVT bundle | `typ` = `mos_tt`/`res_typ`/27 °C, `slow` = `mos_ss`/`res_wcs`/125 °C, `fast` = `mos_ff`/`res_bcs`/−40 °C |
| Band select (`B0`,`B1`) | `00`, `10`, `01`, `11` |
| `VCTRL` | 0.3, 0.9, 1.5, 2.1, 2.7 V |
| Supply | 3.3 V only (DR-004: all-3.3 V internal domains) |

3 bundles × 4 band codes × 5 `VCTRL` points = **60 runs per arm, 120 total**
→ `results.csv`, `deviation.csv`, `control.csv`.

**One deliberate difference from the original campaign, applied to BOTH
arms**: `.tran`'s stop time is 30 ns rather than 40 ns, a runtime measure for
the far more expensive post-layout arm. Applying it to both arms means it
cannot bias the comparison, and `control.csv` shows it does not move a single
committed number.

## Matrix B — `pll_cp`, delivered current vs. output voltage

Copied from [`../../sg13cmos5l-cp-icp-trim/corners/matrix.md`](../../sg13cmos5l-cp-icp-trim/corners/matrix.md).

| Axis | Values |
|---|---|
| MOS corner × temperature | 5 corners (`mos_tt/ss/ff/sf/fs`) × 3 temps (27/125/−40 °C) at 3.3 V |
| Supply sub-axis | 3.0 V and 3.6 V (±10%) at `mos_tt`/27 °C |
| Trim code (`Iref`) | 2.5, 5, 10, 20, 40, 80 µA |
| UP/DN switch state | `up`, `dn`, `both` |
| Resistor corner | not applicable — `cp` contains no resistor (stated, not silently dropped) |

17 PVT points × 6 trim codes × 3 states = **306 runs per arm, 612 total**
→ `cp_results.csv`.

## Matrix C — R/C attribution (diagnostic, not a design measurement)

A subset of Matrix A (3 bundles × band codes `00`/`11` × 5 `VCTRL` = 30
points) re-run against **seven variants of the same extracted netlist**, to
answer "which parasitic caused the deviation". Only parasitic R/C cards are
touched; the device-card count is asserted identical across all seven.

| Variant | What it is |
|---|---|
| `full` | every extracted element (reproduces Matrix A's post-layout arm) |
| `c_only` | every parasitic resistor shorted (1 µΩ), capacitors kept |
| `r_only` | every parasitic capacitor removed, resistors kept |
| `none` | neither — the extracted **devices** with no interconnect at all |
| `cscale25` / `cscale10` / `cscale05` | every parasitic capacitance × 0.25 / 0.10 / 0.05 |

→ `rc_attribution.csv` (210 runs).

`cscale*` is a **floorplan sensitivity bracket, not a prediction** — see
`../testbench/run_rc_attribution.sh`'s header and `../records/RECORD-001`
§"The floorplan caveat, quantified".

## Axes this record does NOT sweep, and why

- **The other four blocks** (`pfd`, `loop_filter`, `divider_chain`,
  `lock_detector`) have parasitic-annotated netlists committed under
  `../netlist-snapshots/` — acceptance criterion 1 is "every routed block has
  one" — but are not re-simulated here. `loop_filter`'s routed cell is not
  the loop filter at all (both MoM capacitors are undrawn; LVS matches 0 of 3
  devices), `divider_chain`'s committed design does not function as a divider
  at any corner (`sg13cmos5l-divider-nrange-retiming`) so there is no
  schematic-level result to deviate from, and `pfd`/`lock_detector` are
  transient campaigns whose post-layout arms are a larger increment than this
  issue's own budget. Named as open, not silently dropped.
- **The MOM-uncertainty axis** several `sg13cmos5l-*` records carry does not
  apply: no `cap_cmomi` instance exists in *either* DUT on *either* arm here.
- **1.2 V / wrapper-boundary supply corners** — DR-004 already settled that
  every internal domain is 3.3 V.
