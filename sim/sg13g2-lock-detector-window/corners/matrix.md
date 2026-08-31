# Corner matrix — `sg13g2-lock-detector-window`

**Claim under test (this issue, #81)**: does not test `spec/porting-plan.md`
row 16's criteria yet — it stands up the slug and extracts `lock_detector`'s
own `R` (`rhigh`, `XRPU`) and `C` (`cap_cmim`, `XCW`/`XDW.XC1`) over a real
PVT grid, per issue #78's own decomposition plan ("stand up the slug +
extract R/C" then "re-derive and re-measure"). No device is resized here and
no pass/fail verdict is drawn — that is issue #82's job, using
`rc_extract.csv` below as its own re-derivation's input.

## Why this campaign's axes differ from the SG13CMOS5L sibling's

The SG13CMOS5L sibling (`sim/sg13cmos5l-lock-detector-window/`) sweeps a
**MOM-model-uncertainty band** (`ideal-0.20`/`ideal0.00`/`ideal0.20`, built by
`mom_inject.py`/`cmomi_nominal.py`) instead of a real capacitor process
corner, because that PDK's `cap_cmomi` has none — `cornerCAP.lib`'s own
header there states every corner/mismatch/stat section maps to the SAME
nominal model.

**This PDK's `cap_cmim` is different**, confirmed directly against the
installed `ihp-sg13g2` tree before writing any deck here:

- `cornerCAP.lib` defines real `cap_typ` / `cap_bcs` / `cap_wcs` sections,
  each scaling `cmim_core`'s area/perimeter coefficients by a real ±10%
  (`cap_carea`/`cap_cpara`).
- `cmim_core` is a plain `.model … C (TC1=3.6E-6 TC2=2E-9 TNOM=27 …)` —  a
  genuine temperature coefficient, unlike `cap_cmomi`'s flat-with-temperature
  model (measured directly by the SG13CMOS5L sibling's own RECORD-001/002:
  59.82 fF / 27.29 fF, identical at −40/27/125 °C).
- `cap_cmim` has **no OSDI object at all** — it is a plain SPICE `.subckt`
  (`capacitors_mod.lib`), so there is no host-architecture risk
  (`sim/PORTING-osdi-host-arch.md`) for it the way there was for
  `cap_cmomi`'s prebuilt x86-64 ELF.

So this campaign sweeps `cap_cmim`'s own real corner as a first-class axis
(`@CORNER_CAP@`, mirroring `@CORNER_RES@`) instead of re-injecting a synthetic
band, and needs no `--soft`/OSDI-fallback branch in `run.sh` at all — simpler,
not a workaround, matching issue #81's own prediction.

## Axes

| Axis | Values | Why |
|---|---|---|
| MOS process corner | `mos_tt`, `mos_ss`, `mos_ff`, `mos_sf`, `mos_fs` (`cornerMOShv.lib`) | Same reasoning as the SG13CMOS5L sibling: the block is a delay chain read out by a threshold, so the NMOS-vs-PMOS skew corners move the window and the trip point in opposite directions |
| Resistor process corner | bundled `res_typ`/`res_wcs`/`res_bcs` with `mos_tt`/`mos_ss`/`mos_ff`, plus `mos_tt`×`res_wcs` and `mos_tt`×`res_bcs` as an explicit resistor-only isolation axis | `XRPU` (`rhigh`, `w=0.5u l=6u`) is the integrating node's only pull-up. `cornerRES.lib`'s own `rsh_rhigh` is 1020/1360/1700 Ω/sq at `res_bcs`/`res_typ`/`res_wcs` — identical values to the SG13CMOS5L sibling's, confirmed directly (both trees share this model file) |
| Capacitor process corner (**new axis, this PDK only**) | bundled `cap_typ`/`cap_wcs`/`cap_bcs` with the MOS/RES bundles, plus `mos_tt`/`res_typ`×`cap_wcs`/`cap_bcs` as an explicit capacitor-only isolation axis | `cap_cmim`'s own real ±10% corner — see "Why this campaign's axes differ" above |
| Temperature | −40, 27, 125 °C | Full bracket at every corner bundle |
| Supply | 3.3 V on the main grid; 2.97/3.63 V sub-axis at `mos_tt`/`res_typ`/`cap_typ` × 3 temperatures | Same convention as the SG13CMOS5L sibling |
| Reference frequency | 24.4 MHz (fast end) on the main window/ladder grid; 3.5 MHz (slow end, full resistor-corner × temperature grid) for the ladder's `R·C`-vs-`T_ref` comparison; 12 MHz spot check for `window.csv` | `spec/porting-plan.md` row 2, DR-005-amended range (≈3.5–24.4 MHz) — the same range the SG13CMOS5L sibling's own RECORD-002/003 use, since this is a design/spec-level number, not a PDK-specific one |

**Window matrix**: 9 bundles (5 main + 2 RES-isolation + 2 CAP-isolation) × 3
temperatures = 27, plus the supply sub-axis (6) and the reference-frequency
sub-axis (2) = **35 rows** (`window.csv`).

**Ladder matrix**: the same 9 bundles × 3 temperatures at the fast end (27),
plus the full resistor-corner × temperature grid at the slow end (9,
`mos_tt`/`cap_typ`) = **36 rows** (`ladder.csv`), each instantiating the DUT
twice per ladder point (9 points × 2 + 3 auxiliary copies = 21
`lock_detector` copies) via the one-point-at-a-time split (see
`../testbench/tb_lock_recovery.sp.tmpl`'s header).

## Why a 4-reference-period ladder transient (not a many-cycle settling budget)

The SG13CMOS5L sibling's `RECORD-002`/`RECORD-003` needed a settling-duration
formula (`K_SETTLE·R·C`, tens to hundreds of reference periods) because that
PDK's `XRPU`/`XCW` were re-sized (issue #52) to make `R·C` many multiples of
`T_ref` — by design, since that is what makes the block an integrator. **This
PDK's `lock_detector` has not been resized yet** (this issue does not resize
anything — see #82): `rc_extract.csv` below measures `R·C` at 0.65–1.57 ns,
the same order of magnitude as the SG13CMOS5L sibling's own **pre-resize**
`RECORD-001` (0.71–1.71 ns). A fixed `tstop = 4·T_ref` (the SG13CMOS5L
sibling's own original, issue #38 convention) is therefore ample margin here,
and the campaign completed in well under 15 minutes end-to-end with **zero**
solver retries.

## Sub-measurements, and the axes that do NOT apply to them

- **`rc_extract.csv`** — `XRPU` (`rhigh`) DC resistance over 3 resistor
  corners × 3 temperatures (9 rows); both `cap_cmim` geometries' AC
  capacitance over 3 capacitor corners × 3 temperatures (18 rows). No
  MOS-corner axis on either device (neither is a transistor); no
  resistor-corner axis on the capacitors and no capacitor-corner axis on the
  resistor (independent devices, independent corner mechanisms).
- **`schmitt.csv`** — the readout Schmitt's own V_TH+/V_TH− over 5 MOS
  corners × 3 temperatures × 3 supplies (45 rows). `schmitt_hv` contains no
  resistor and no capacitor instance, so neither the RES-corner nor the
  (new) CAP-corner axis applies to it — fixed at `res_typ`/`cap_typ`.
- **`tstep_convergence.csv`** — `twin_r` at 20 ps / 5 ps / 1.25 ps maximum
  internal timestep at four representative corners (12 rows), same
  convention as the SG13CMOS5L sibling.

## What is NOT swept, and why (carried over from the SG13CMOS5L sibling)

- **Random device mismatch.** No per-instance mismatch model is exercised for
  `sg13_hv_nmos`/`sg13_hv_pmos`, `rhigh`, or `cap_cmim` here (all three have a
  `*_mismatch.lib` variant installed, but exercising it is out of this
  issue's scope — same "systematic corner, not random mismatch" scoping the
  SG13CMOS5L sibling used).
- **Post-layout parasitics.** Schematic-level only.
- **Pass/fail against row 16's targets.** Explicitly deferred to issue #82,
  which re-derives `XRPU`/`XCW`/`XDW.XC1`/`XMPD` from this record's
  `rc_extract.csv` and re-runs this same `run.sh` against the resized block.

## Solver settings

`itl4=5000 gmin=1e-11` on the two transient templates
(`tb_lock_ladder_point.sp.tmpl`, `tb_lock_recovery.sp.tmpl`), reused verbatim
from the SG13CMOS5L sibling (issue #66) per issue #81's own Scope item 1 —
`nand2_hv`'s floating series-stack node `mid1` and the high-impedance
integrating node are the same topology on both PDKs. Zero decks needed the
`trtol=1` retry in this run (`solver_retries.txt` is empty).


---

# Issue #82 (Phase 2/2) — what the matrix became, and why

Everything above describes the matrix **issue #81** ran against the
pre-resize block, and is left unedited: it is the definition the unsuffixed
`*.csv` files in this directory were produced from. Issue #82 re-derived
`XRPU`/`XCW`/`XDW.XC1`/`XMPD` and re-ran `../testbench/run.sh` against the
resized block, writing the `*_resized.csv` set. Four axes changed, and the
`records/RECORD-001-resized-window-hysteresis-chatter.md` §"Coverage, and how
it was reduced" table is the full accounting; this section is the matrix
definition itself.

## Window matrix — 35 → **37 rows** (`window_resized.csv`)

Unchanged in structure, plus **two explicit worst-case axis stacks**:

| Added point | Why |
|---|---|
| `mos_ff`/`res_bcs`/`cap_bcs`/−40 °C/**3.63 V** | Row 16's "assert window ≥ 2.5 ns" is a **floor**, and a floor is a worst-case claim. The grid above holds the supply at nominal while sweeping bundles and holds the bundle at typ while sweeping supply, so the point that actually *minimises* `twin_r` — every fast-direction axis at once — is in neither sub-sweep. This point *is* the reported 3.7320 ns minimum. |
| `mos_ss`/`res_wcs`/`cap_wcs`/125 °C/**2.97 V** | The other end, so the reported range is the measured envelope rather than an interpolation. |

## Ladder matrix — 36 → **21 rows** (`ladder_resized.csv`)

The ladder is now ~99% of `run.sh`'s runtime (an integrator whose `R·C` is
9–28 reference periods needs a transient hundreds of cycles long before
anything has settled), so it is reduced — but **not uniformly**, because the
binding end moved:

| Sub-grid | Rows | Why |
|---|---|---|
| `mos_tt` × full 3 res-corners × 3 temperatures at **3.5 MHz** | 9 | the slow end is the binding end for `R·C ≫ T_ref`; that axis is not reduced there |
| `mos_tt` × {`res_typ`/27 °C, `res_bcs`/125 °C, `res_wcs`/−40 °C} at **24.4 MHz** | 3 | typ plus both `R·C` extremes |
| `mos_ff`/`res_wcs`/−40 °C, `mos_ss`/`res_bcs`/125 °C, `mos_tt`/`res_typ`/27 °C @ 3.63 V — all at **24.4 MHz** | 3 | the fast end is the binding end for row 16's **hysteresis** criterion (the settled `VWIN` is `VDD − I_sat(XMPD)·R(XRPU)·(τ − twin_r)/T_ref`, so the hysteresis in units of the window is proportional to `T_ref`), and it depends on `mos_corner` through `I_sat(XMPD)` and on supply through both `I_sat` and `schmitt_hv`'s trip points. So the fast end is **extended** along its own worst directions rather than reduced to a token spot check. |
| `cap_bcs` / `cap_wcs` spot checks at `mos_tt`/`res_typ`/27 °C, 3.5 MHz | 2 | `window_resized.csv` carries the cap corner at full density |
| 2.97 V / 3.63 V spot checks at `mos_tt`/`res_typ`/27 °C, 3.5 MHz | 2 | |
| `mos_ff` / `mos_ss` spot checks at `res_typ`/27 °C, 3.5 MHz | 2 | `R` and `C` have no `mos_corner` dependence at all |

**Ladder set**: `resized` (23 points, `gen_ladder.py`) — 0.25×-window steps
from 1.00× to 2.50×, reaching **24×** the window, against issue #81's 9
points at a 0.20× step reaching 10×. Both changes are forced: a 0.20× step
can only bound a ≥25%-of-window criterion from below, and the restored
hysteresis pushes the slow end's de-assert threshold to 18× the window.
**Chatter probe** (`TAUBIG_XWIN`) at **20×**, not 10×, so it is beyond
de-assert at every corner.

## Settling budget — new, and it is the axis that matters most

`tstop = K_SETTLE·R·C` (`K_SETTLE` = 4 ⇒ 1 − e⁻⁴ = 98.2%), capped at
`TSTOP_MAX` = **32 µs**, rounded up to a whole number of reference periods;
`tstep` = `T_ref`/25. The achieved `1 − e^(−tstop/R·C)` is written to
`ladder_resized.csv`'s own `settle_frac` column rather than assumed:
**0.9817–0.9831 at all 21 corners**. Issue #81's flat `tstop = 4·T_ref` is
meaningless post-resize.

**32 µs, not 16 µs, and the difference is not cosmetic.** At 16 µs the
`res_wcs`/−40 °C corner (`R·C` = 7.17 µs) settles only to 0.893, and **an
under-settled two-start-state ladder manufactures hysteresis** — the two
copies simply have not converged yet. Measured at
`mos_tt`/`res_wcs`/−40 °C/24.4 MHz, τ = 1.25× window: the discharged- and
charged-start `VWIN` differ by 0.317 V at 391 cycles and by 0.037 V at 782.
See RECORD-001 §"Settling budget — a measurement error this record made and
corrected".

## New sub-measurements (issue #82 only)

- **`rc_sizing.csv` / `rc_pairing.csv`** (`../testbench/run_rc_sizing.sh`) —
  6 candidate `XRPU` lengths × 3 res-corners × 3 temperatures, and 8
  candidate `cap_cmim` geometries × 3 cap-corners × 3 temperatures, plus the
  worst-case `R·C` over the joint grid for each of the 48 length × geometry
  pairs. Sizing evidence, not a pass/fail claim.
- **`window_sizing.csv`** (same script) — `twin_r` for each of those 8
  capacitor geometries at 3 window stacks (fast worst case, nominal, slow
  worst case). The `XDW.XC1` choice is read off its `fast_stack` column.
- **`xmpd_sizing.csv`** (`../testbench/run_xmpd_sizing.sh`) — 7 candidate
  `XMPD` geometries at the two bound corners: `mos_tt`/`res_wcs`/`cap_typ`/
  −40 °C at 24.4 MHz (13 phase-error points, the lower bound) and
  `mos_ss`/`res_bcs`/`cap_typ`/125 °C at 3.5 MHz (13 points, the upper). Both
  report the **settled integrating-node voltage**, not just the thresholded
  `LOCK` pin, so the trip points are interpolated against `schmitt.csv`'s own
  measured Schmitt voltages instead of being read at ladder resolution. The
  `cap_corner` is fixed at `cap_typ` there: `C` does not appear in the
  `XRPU`/`XMPD` balance at all, only in the settling budget.
- **`hysteresis_diag.csv`** (`../testbench/run_hysteresis_diag.sh`) — the
  same fine method applied to the **landed** block at two fast-end corners:
  `mos_tt`/`res_wcs`/−40 °C (the corner `ladder_resized.csv` reports exactly
  one ladder quantum at) and `mos_ff`/`res_wcs`/−40 °C (a cross-check against
  the sizing sweep's own selection row). 13 phase-error points each, 0.05×
  window through the transition.

## Solver settings (unchanged), and this run's retries

`itl4=5000 gmin=1e-11` on the two transient templates, unchanged. **10 of the
~500 ladder decks** needed one recorded `trtol=1` retry
(`solver_retries_resized.txt`); all 10 are ladder points, none is a window,
Schmitt or extraction deck, and none changed a verdict. Issue #81's run needed
zero — the weaker `XMPD` and the much longer transients are the difference.
