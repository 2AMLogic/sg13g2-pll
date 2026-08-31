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
