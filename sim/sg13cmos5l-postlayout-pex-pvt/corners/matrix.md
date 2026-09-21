# Corner matrix — `sg13cmos5l-postlayout-pex-pvt`

**Claim under test**: not a new spec row. This harness re-runs **ratified
corner matrices, unchanged**, against parasitic-annotated netlists
extracted from the routed layout, and analyses the difference against the
schematic-level result. Issue #30 (Part of #16) is the named follow-up
issue #24 deferred post-layout PVT to; issue #102 (Part of #16) extends it
from `vco`/`cp` (Matrices A–C, RECORD-001) to `pfd` and `lock_detector`
(Matrices D–E, RECORD-003).

Because the whole point is a controlled comparison, **this record invents
no axis of its own**. Both matrices below are copied verbatim from the
campaign whose numbers they are being compared against, and each is run
**twice** — once against the extracted netlist (`arm=postlayout`) and once
against the frozen schematic netlist (`arm=schematic`).

## Why both arms, rather than comparing against the committed CSV

The committed numbers were produced months earlier on a different session.
Comparing a fresh post-layout number directly against them would confound
"what the extracted interconnect did" with "what a different host/ngspice
did". Re-running the schematic arm here makes the comparison controlled,
and the agreement between that control arm and the committed CSV is itself
measured and reported rather than assumed — `control.csv` for the VCO
(60/60 points byte-identical), the `cp` roll-up in `../records/RECORD-001`
(max |delta| 4.9e-5 %), and — for the two matrices added by issue #102 —
`ld_window_control_delta.csv` (102/102 committed window points
byte-identical), `ld_rc_control.csv` (15/15 device-extraction rows
byte-identical) and `pfd_control.csv` (the pfd's schematic control arm vs
the committed `fixed` rows: −0.52 % on both averages, with the two known
causes — reset-chain gate composition and host — named in the record).

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

## Matrix D — `pll_pfd`, UP/DN duty-space transient (issue #102, RECORD-003)

Copied from the campaign whose numbers the comparison is made against:
`../../sg13cmos5l-closed-loop-lock`, whose ratified PVT coverage is its own
corners/matrix.md's **single `mos_tt`/`res_typ`/27 °C/3.3 V point**
("typ" — the six-block closed-loop transient's cost is the stated reason
that campaign gives), and whose PFD-relevant measurement is the standalone
PFD-polarity diagnostic (`tb_pfd_only.sp.tmpl` + `run_pfd_diag.sh`,
RECORD-002/RECORD-003 evidence).

| Axis | Values |
|---|---|
| PVT | `typ` only, verbatim from that campaign — the comparison target has no other ratified point |
| Phase case | `reflead` (REF edge first each cycle), `fblead` (FB edge first) |
| Lead/lag offset | 5 ns (ratified: 10 % of the reference period), 10 ns and 20 ns as **this record's own diagnostic** |
| `f_ref` | 20 MHz, the campaign's own diagnostic value |
| Averaging | UP/DN averaged over [200 ns, 500 ns], skipping 4 startup cycles |

The offset axis is to Matrix D what Matrix C is to Matrices A/B: a
diagnostic this record adds because its ratified-point finding (the
fblead polarity inversion) needs bounding to be interpretable at all. The
schematic arm runs it too, so every offset row stays a controlled A/B.

1 PVT point × 2 cases × 3 offsets × 2 arms = **12 runs**
→ `pfd_results.csv`, `pfd_control.csv`.

## Matrix E — `pll_lock_detector`, window / ladder / supply current (issue #102, RECORD-003)

Copied from the campaign being compared against:
`../../sg13cmos5l-lock-detector-window` (RECORD-004's committed crowbarfix
set being the current ratified design whose rows must reproduce first).
The control reproduction is that campaign's **entire** committed window
matrix — 102 points including its MOM-band variants, supply and
reference-frequency sub-axes, and worst-case stack — plus its 15-row
device extraction, re-run via that campaign's own templates unmodified.

The comparison arms (as-layout schematic twin and post-layout extraction)
run that campaign's own grids and machinery:

| Sub-measurement | Axis set | Arms |
|---|---|---|
| Window (whole-cell ERR→ERRD) | 7 MOS/RES bundles × 3 temperatures at 3.3 V + ±10 % supply sub-axis = 30 points | `aslayout`, `postlayout` |
| Window (bare `delaywin_hv`) | same 27-point primary grid | `aslayout` only — the flat extraction has no isolated chain to run bare (stated) |
| Device extraction (R/C) | 3 resistor corners × 3 temperatures, both `cap_cmomi` geometries × 3 temperatures | control (byte-compared to committed) |
| Ladder + recovery (row-16 criteria + row-11 currents) | RECORD-002's own reduced corner grid minus its 2 MOM-band spots (meaningless here: `→` no caps in either arm), `record002` 9-point ladder | `aslayout`, `postlayout` |
| Timestep convergence | typ whole-cell window at 20 p/5 p/1.25 p max timestep | both |

→ `ld_window.csv`, `ld_window_control.csv`, `ld_window_control_delta.csv`,
`ld_rc_extract.csv`, `ld_rc_control.csv`, `ld_ladder.csv`,
`ld_ladder_raw.csv`, `ld_deviation.csv`, `ld_tstep_convergence.csv`.

**Why a whole-cell window deck at all, and why an `aslayout` twin.** The
extraction is one flat subckt, so it has no isolated `delaywin_hv` to
measure bare; it exposes the chain's input/output as the ERR/ERRD pins, so
the window is measured driving ERR and thresholding ERRD with the rest of
the block loading the rails (`tb_ld_wholecell_win.sp.tmpl`, both arms).
The as-layout arm is the frozen #52 resize snapshot with exactly its two
`cap_cmomi` cards removed — the device set the routed layout actually
carries (its extraction has zero `cap_cmomi` instances, and its
XMPD/schmitt geometry matches the pre-#66 resize revision, not the
committed crowbarfix design). It exists so the post-layout-vs-schematic
window deviation isolates the **interconnect** on a common device set,
with the missing-cap and revision-lag effects measured separately against
the committed control. Derived programmatically by
`../testbench/derive_ld_as_layout.py`; never a committed design.

The ladder's run-length basis (RC, n_cycles, settle_frac) is computed on
the **same extracted-VWIN-capacitance basis for both arms** (the basis
over-estimates the as-layout arm's true RC, which can only add settling;
the recovery deck's measured `trec` is the direct cross-check) — the
columns carrying it say `on_cwin_basis` in their names.

## Axes this record does NOT sweep, and why

- **`loop_filter` and `divider_chain` remain not re-simulated**, exactly
  as RECORD-001 left them: `loop_filter`'s routed cell is not the loop
  filter as drawn (both MoM capacitors undrawn; LVS matches 0 of 3), and
  `divider_chain`'s committed design does not function as a divider at any
  corner (`sg13cmos5l-divider-nrange-retiming`) so there is no
  schematic-level result to deviate from. Both are "unanswerable", not
  deferred — the same statement `../records/RECORD-001` §5 makes.
- **The lock_detector's schmitt-hysteresis sub-measurement has no
  post-layout arm, stated rather than silently dropped**: the campaign
  measures a bare `schmitt_hv` subckt, and the flat extraction exposes no
  isolated schmitt instance. Its committed rows (schmitt.csv) are not
  reproduced or re-run here.
- **The lock_detector ladder's corner grid follows RECORD-002's reduction,
  not the full 92-point RECORD-001 grid** — the campaign's own stated
  runtime reduction, minus the two MOM-band spot checks that are
  unrepresentable with zero caps in either arm. The row-16 criteria are
  evaluated on it as that record did.
- **The pfd has one PVT point** because its comparison target ratified one
  point; this harness deliberately adds no PVT axes of its own to Matrix D.
- **The MOM-uncertainty band** does not apply to either new matrix: no
  `cap_cmomi` instance exists on any arm of Matrix D (all-MOS `pfd`) or on
  the as-layout/post-layout arms of Matrix E (the layout carries none —
  that absence is one of Matrix E's results). The control reproduction of
  course runs the committed band points, because they are committed rows.
- **1.2 V / wrapper-boundary supply corners** — DR-004 already settled that
  every internal domain is 3.3 V.
