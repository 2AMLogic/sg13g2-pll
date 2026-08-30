# Corner matrix — `sg13cmos5l-lock-detector-window`

**Claim under test**: `spec/porting-plan.md` row 16 (lock-detector targets —
assert window ≥ 2.5 ns / ≥ 2× worst static phase offset, hysteresis ≥ 25% of
window, no chatter). That row's disposition is "port the target structure
as-is; re-derive the numbers, and budget margin from the start against the
specific failure gf180-pll already found". Nothing in `sim/` measured
`lock_detector` before this record; `sim/README.md`'s deferred-rows table
named issue #38 as the follow-up that would.

**Second claim, carried in the same record**: the two `cap_cmomi` instances
`lock_detector.XCW` (`w=8u l=8u m=1`) and `lock_detector.XDW.XC1` (in
`delaywin_hv`, `w=4u l=4u m=2`) are outside
`spec/decision-records/DR-003-sg13cmos5l-port-readiness.md` Finding 2's own
three-instance list (`loop_filter.XC1`/`XC2`, `vco.XCDECAP`), and
`design/README.md` records them as "not covered by this update; their
hysteresis-window sensitivity remains open". This record's ±20%
MOM-model-uncertainty band closes that.

**Third**: `spec/porting-plan.md` row 11 (power) needs a `lock_detector`
supply-current domain; `sim/README.md`'s own deferred table names
`lock_detector` as one of the three unmeasured domains. Measured here.

## Axes

| Axis | Values | Why |
|---|---|---|
| MOS process corner | `mos_tt`, `mos_ss`, `mos_ff`, `mos_sf`, `mos_fs` (`cornerMOShv.lib`) | All five. The block is a delay chain read out by a threshold, so the NMOS-vs-PMOS skew corners (`mos_sf`/`mos_fs`) move the window and the trip point in opposite directions and cannot be inferred from the symmetric bundles |
| Resistor process corner | bundled `res_typ`/`res_wcs`/`res_bcs` with `mos_tt`/`mos_ss`/`mos_ff`, **plus `mos_tt`×`res_wcs` and `mos_tt`×`res_bcs` as an explicit resistor-only axis** | Unlike `sg13cmos5l-cp-icp-trim`'s all-MOS DUT, this block genuinely has a resistor: `XRPU` (`rhigh`, `w=0.5u l=6u`) is the integrating node's only pull-up. `cornerRES.lib`'s own `rsh_rhigh` is 1020 / 1360 / 1700 Ω/sq at `res_bcs` / `res_typ` / `res_wcs` — a ±25% spread landing directly on the node's time constant — so the resistor corner is isolated at fixed MOS as well as bundled |
| Temperature | −40, 27, 125 °C | Full bracket at **every** corner bundle, not one temperature per bundle |
| DUT variant (MOM band) | `real`, `ideal-0.20`, `ideal0.00`, `ideal0.20` | See "MOM-uncertainty band" below |
| Supply | 3.3 V on the main grid; **2.97 / 3.63 V sub-axis** at `mos_tt`/`res_typ` × 3 temperatures | DR-004 ratifies the internal domains as all-3.3 V; `spec/porting-plan.md` row 18 carries gf180-pll's 3.3 V ±10%. Same structure the `sg13cmos5l-cp-icp-trim` record used (main grid at nominal + an explicit ±10% sub-axis) |
| Reference frequency | 25 MHz on the main grid; **1 MHz and 5 MHz sub-axis** at `mos_tt`/`res_typ`/27 °C | 25 MHz is the top of the ported `f_ref` range (row 2, 1–25 MHz) and the frequency gf180-pll characterised its own lock detector at. gf180-pll's record explicitly declined to claim anything at 1 MHz ("that extrapolation is a hand argument, not a measured result"); this record measures it instead of extrapolating |

**Main grid**: 7 MOS/RES bundles × 3 temperatures × 4 DUT variants = **84**
phase-error-ladder runs, each preceded by its own comparator-window run.
**Supply sub-axis**: 3 temperatures × 2 supplies = **6**. **Reference-frequency
sub-axis**: **2**. Total **92** ladder runs and 92 window runs
(`../corners/ladder.csv`, `../corners/window.csv`).

Each ladder run itself instantiates **14 phase-error points × 2 initial
states + 3 auxiliary copies = 31 `lock_detector` copies** in one transient,
so the 92 rows summarise **2 576 independent DUT evaluations**.

## The phase-error ladder, and why it is in units of the window

Row 16 states its hysteresis criterion as a *fraction of the window*
("hysteresis ≥ 25% of window"). A ladder in absolute picoseconds would
resolve a different fraction of the window at every corner. So `run.sh`
measures this corner's own comparator window `twin_r` first
(`tb_window.sp.tmpl`, a bare `delaywin_hv` with an ideal step in), and then
scales the ladder by it:

```
tau / twin_r  =  0.25  0.50  1.00  1.15  1.30  1.45  1.60  1.75
                 1.90  2.05  2.20  2.35  2.50  10.00
```

The 0.15 × window spacing through 1.00–2.50 is the resolution on both
thresholds, and therefore the resolution on their difference. It is
deliberately finer than the 0.25 × window criterion, so "hysteresis ≥ 25% of
window" is *resolvable* by this ladder rather than merely bracketed by it.

Each ladder point instantiates the DUT twice from one stimulus pair: copy A
starting fully **discharged** (`VWIN` = 0 — "just saw a wide error") and copy
B starting fully **charged** (`VWIN` = VDD — "has been clean a long time").
The largest τ at which A still reaches the in-window state is the **assert**
threshold; the largest at which B still holds it is the **de-assert**
threshold.

## MOM-uncertainty band on `XCW` and `XDW.XC1`

`cap_cmomi` has no corner, mismatch or statistical spread in the installed
PDK — `cornerCAP.lib`'s own header states every corner/mismatch/stat section
maps to the **same** nominal model, and `cap_cmomi.lib`'s header states the
coefficients are transferred from SG13G2 and "NOT YET VALIDATED ON
ihp-sg13cmos5l SILICON". There is no knob to sweep. This record therefore
follows the methodology precedent
`sim/sg13cmos5l-loop-bandwidth-pm/testbench/tb_loop_ac_lumped.sp.tmpl`
documents — *extract the real value, re-inject it as an ideal element scaled
by the band, and cross-check the nominal point against the real subckt* — in
four DUT variants:

| Variant | What it is | What it is for |
|---|---|---|
| `real` | the frozen snapshot, byte for byte | the committed design; every row 16 / row 11 number quoted for the design comes from these runs |
| `ideal0.00` | both `cap_cmomi` instances replaced by ideal linear caps at their measured nominal value | the control point that separates ideal-vs-real modelling error from the band |
| `ideal-0.20` / `ideal0.20` | the same, at 0.8× / 1.2× nominal | the ±20% MOM-model-uncertainty band |

The band is applied with the **same sign and magnitude to both instances**,
i.e. it models a *systematic* coefficient/density bias (the kind of error a
wrong layer-count transfer would cause), not independent per-instance
mismatch — which `cap_cmomi` does not characterise either, and which this
record does **not** bound.

**Why not a parallel delta capacitor**, which is what
`sim/sg13cmos5l-loop-filter-momcap/` used for the same band. That record's
DUT is a passive AC network where a negative delta capacitor is numerically
harmless. Here the caps sit on switching nodes inside an inverter chain, and
a negative delta capacitor on `delaywin_hv`'s output makes ngspice's
transient abort — *"Timestep too small … trouble with node xw.d2"* at a
quiescent time point, i.e. a solver instability rather than a circuit result.
Replacing the instance wholesale keeps every capacitance positive at every
band point; the price is that the ideal element drops `cap_cmomi`'s substrate
shunt and RF network, which is exactly what the `ideal0.00` control point
measures (and it comes out at 0.004% on the window — see RECORD-001).

## Sub-measurements, and the axes that do NOT apply to them

- **`rc_extract.csv`** — `XRPU` (`rhigh`) DC resistance over 3 resistor
  corners × 3 temperatures, and both `cap_cmomi` geometries' AC capacitance
  over 3 temperatures. No MOS-corner axis (neither device is a transistor);
  no resistor-corner axis on the capacitors; no MOM band (this deck is what
  *measures* the nominal the band is built from).
- **`schmitt.csv`** — the readout Schmitt's own V_TH+ / V_TH− over 5 MOS
  corners × 3 temperatures × 3 supplies. `schmitt_hv` contains **no resistor
  and no `cap_cmomi` instance**, so neither the RES-corner nor the MOM axis
  applies to it; that is stated here rather than silently dropped, per this
  repo's `sim/README.md` convention.
- **`tstep_convergence.csv`** — `twin_r` at 20 ps / 5 ps / 1.25 ps maximum
  internal timestep at four representative corners. `twin_r` is an
  interpolated difference of two threshold crossings *and* the scale factor
  every phase-error threshold in `ladder.csv` is expressed in, so it is the
  one measurement here whose value could plausibly be a discretisation
  artifact.

## What is NOT swept, and why

- **Random device mismatch.** No per-instance mismatch model is exercised for
  `sg13_hv_nmos`/`sg13_hv_pmos` here, and `cap_cmomi` has none at all. The
  `mos_sf`/`mos_fs` corners bound the *systematic* NMOS-vs-PMOS skew; they
  say nothing about within-die random mismatch — which matters for a
  threshold detector and is left explicitly open.
- **Post-layout parasitics.** Schematic-level only. `VWIN` is a
  high-impedance node whose own capacitance and leakage move both the
  threshold and the recovery time, so a post-layout pass must re-take this
  record. (The block's layout landed in PR #39 but no extracted netlist is
  exported yet.)
- **The static phase offset this window should be compared against.** Row
  16's target is "≥ 2.5 ns **/ ≥ 2× worst static phase offset**". The second
  half needs the PFD/CP static offset, which no record in `sim/` bounds yet
  (`sg13cmos5l-cp-icp-trim` characterises the charge pump's *static current
  mismatch* at DC with the switches held, explicitly not the switching
  charge-domain behaviour a static phase offset comes out of, and `pfd` has
  no record at all). That half of the comparison is marked
  `insufficient-evidence` in RECORD-001 rather than silently dropped.

---

# Corner matrix — the issue #52 re-run (RECORD-002)

Everything above describes the campaign **as issue #38 ran it against the
pre-resize block**, and it is left unedited: `RECORD-001` is the record of
that matrix, and `ladder.csv` / `window.csv` / `rc_extract.csv` /
`schmitt.csv` / `ladder_raw.csv` / `tstep_convergence.csv` (all unsuffixed)
are its raw results.

Issue #52 re-sized three devices in the DUT (`XRPU` `l=6u`→`l=700u`, `XCW`
`w=8u l=8u`→`w=40u l=40u`, `XDW.XC1` `w=4u l=4u`→`w=40u l=40u`) and re-ran
the same campaign against `../netlist-snapshots/lock_detector_resized.spice`,
writing a parallel set of `*_resized.csv` files plus two new diagnostic
CSVs. This section describes **that** matrix. Same convention as
`../../sg13cmos5l-closed-loop-lock/corners/` (`results_as_drawn.csv` vs.
`results_proposal.csv`).

## What changed in the matrix, and why

| Axis | #38 / RECORD-001 | #52 / RECORD-002 | Reason |
|---|---|---|---|
| Reference frequency | 25 MHz main grid + 1 / 5 MHz sub-axis (row 2 as then written: 1–25 MHz) | **24.4 MHz** main grid + **3.5 MHz** and 12 MHz; the ladder runs its full res × temp grid at **3.5 MHz** and spot-checks **24.4 MHz** | Row 2 was amended by **DR-005** (PR #46) to ≈3.5–24.4 MHz. The binding end for an `R·C ≫ T_ref` claim is the SLOWEST reference, so that end carries the full grid |
| DUT variant | `real`, `ideal−0.20`, `ideal0.00`, `ideal0.20` | **`ideal−0.20`, `ideal0.00`, `ideal0.20`** — `real` unavailable on the run host | `cap_cmomi.osdi` ships as x86-64 ELF and cannot load on an arm64 host; `run.sh` probes for it and promotes `ideal0.00` to primary when it is missing. See RECORD-002 "Host limitation" |
| `cap_cmomi` nominal C | measured by `tb_extract_c.sp.tmpl` | `../testbench/cmomi_nominal.py` (the model's own closed form), self-tested against RECORD-001's two measured geometries to 0.004% / 0.014% | same cause; `rc_extract_resized.csv` records which path was used per row in its `source` column |
| Window matrix | 92 rows | **81 rows** — same 7 bundles × 3 temperatures × the available variants, plus supply sub-axis at two variants, plus an explicit **worst-case stack** (`mos_ff`/`res_bcs`/−40 °C/3.63 V at the −20% MOM band) | A ≥2.5 ns *floor* is a worst-case claim. RECORD-001's grid never stacked all the fast-direction axes at once, so its own minimum was not the true worst case |
| Ladder matrix | 92 corner points | **18 corner points** (full res × temp at 3.5 MHz; 24.4 MHz at typ + both `R·C` extremes; ±20% MOM, `mos_ff`/`mos_ss`, ±10% supply as 2-point spot checks each) | Runtime. See "Run length" below |
| Ladder step | 14 points, 0.15× window | **9 points, 0.20× window** | Runtime. Still below row 16's own 25%-of-window criterion, so the criterion would still resolve; the resulting bound is weaker (< 20% vs < 15%) and RECORD-002 says so |
| Schmitt / `tstep_convergence` | 45 / 12 rows | **45 / 12 rows** (unchanged) | cheap, and `schmitt_hv` is untouched by the resize |

## Run length — why the ladder had to be split and shortened

The resize is exactly what makes the old ladder deck impractical. An
integrator whose `R·C` is ~10 reference periods needs a transient tens to
hundreds of reference periods long before anything has settled, where
RECORD-001 ran 4. Measured at `mos_tt`/`res_typ`/27 °C/3.3 V/3.5 MHz with a
54-cycle `tstop`: the merged 21-copy deck did **not** complete in 400 s,
while the same corner run as 1 recovery deck + 9 independent 2-copy
ladder-point decks completed in about **200 s**. `../testbench/run.sh`
therefore runs each ladder point as its own ngspice invocation
(`tb_lock_ladder_point.sp.tmpl`) alongside one recovery/current deck
(`tb_lock_recovery.sp.tmpl`) and concatenates their logs before reduction.

Per corner, `tstop` = `min(4·R·C, 16 µs)` rounded up to a whole number of
reference periods (41–391 cycles across the matrix), with the achieved
settling fraction `1 − e^(−tstop/RC)` written to `ladder_resized.csv`'s own
`settle_frac` column (0.943–0.983) rather than assumed.

`SKIP_LADDER=1 ./run.sh` regenerates everything **except** the ladder,
leaving `ladder_resized.csv` / `ladder_raw_resized.csv` untouched — the
ladder is ~99% of the runtime and nothing else feeds it, so adding a window
or Schmitt corner does not cost a full re-run. A plain `./run.sh` still
regenerates the whole set consistently.

## The two diagnostic CSVs (`hysteresis_diag*.csv`)

Written by `../testbench/run_hysteresis_diag.sh`, not by `run.sh`. They exist
because row 16's hysteresis criterion still fails after the resize, and
RECORD-002 attributes that to a mechanism rather than leaving it
unexplained. Both are single-corner
(`mos_tt`/`res_typ`/27 °C/3.3 V/3.5 MHz for the phase sweep; 3 MOS corners ×
3 temperatures for the Schmitt sweep) — they are *attribution* measurements
for a failure the full matrix above already bounds, not claims in their own
right, so they are deliberately not swept over PVT.

- `hysteresis_diag.csv` — settled `VWIN` (not just the thresholded `LOCK`
  pin) vs. phase error, finely swept across the transition, for three DUTs:
  the block as drawn, a **scratch** control with `schmitt_hv`'s two feedback
  devices re-tied to the classic connection, and a **scratch** control with
  `XMPD` weakened ~64× at unchanged `XRPU`/`XCW`/`R·C`. Neither scratch
  variant is written back into `design/` or `../netlist-snapshots/`.
- `hysteresis_diag_schmitt.csv` — `schmitt_hv`'s own input-referred
  hysteresis, as drawn vs. the rewired control, over 3 MOS corners × 3
  temperatures.
