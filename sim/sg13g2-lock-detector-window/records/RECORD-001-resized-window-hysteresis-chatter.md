# RECORD-001: SG13G2 lock-detector window, hysteresis and chatter, after the `XRPU`/`XCW`/`XDW.XC1`/`XMPD` re-derivation

- **Slug**: `sg13g2-lock-detector-window`
- **Issue**: #82 (Part of #16 via #78 — SG13G2 PVT campaign, Phase 2/2).
  Supersedes nothing. Issue #81 (Phase 1) stood this slug up and extracted
  `R`/`C` against the **pre-resize** block, deliberately drawing no pass/fail
  conclusion and writing no record; its unsuffixed `../corners/*.csv` and its
  `../netlist-snapshots/lock_detector.spice` stand unedited as append-only
  evidence and are cited below as the "before" column.
- **DUT**: `../netlist-snapshots/lock_detector_resized.spice`, frozen from
  `design/netlist/lock_detector.spice` on this issue's own branch. It differs
  from issue #81's snapshot in **exactly four instance values** and is
  byte-identical everywhere else:

  | Instance | Before (#81) | Now (#82) | Nominal (`*_typ`/27 °C) | Sized against |
  |---|---|---|---|---|
  | `XRPU` (`rhigh`, integrating pull-up) | `w=0.5u l=6u` | `w=0.5u` **`l=500u`** | 1.619 MΩ (was 19.75 kΩ) | `R·C ≫ T_ref` |
  | `XCW` (`cap_cmim`, integrating node) | `w=6u l=6u m=1` | **`w=45u l=45u`** `m=1` | 3.0447 pF (was 54.96 fF) | `R·C ≫ T_ref` |
  | `XDW.XC1` (`cap_cmim`, in `delaywin_hv`) | `w=4u l=4u m=1` | **`w=45u l=45u`** `m=1` | 3.0447 pF (was 24.64 fF) | row 16's ≥ 2.5 ns assert-window floor |
  | `XMPD` (`sg13_hv_nmos`, `WIDE`-gated pull-down) | `w=2u l=0.5u` | **`w=0.25u l=12u`** | `L/W` = 48 (was 0.25) | row 16's ≥ 25%-of-window hysteresis, two-sided against de-assert reach |

  `schmitt_hv`, `xor2_hv`, `nand2_hv`, `inv_hv` and the four-inverter chain's
  own drive are **untouched**. `schmitt_hv` in particular already carries the
  classic cross-coupled feedback connection on this PDK (issue #66 landed that
  fix on both PDKs at once), which is why this record has no rewired-Schmitt
  control the way the SG13CMOS5L sibling's RECORD-002/RECORD-003 needed one.
- **Claim under test**: `spec/porting-plan.md` row 16 (assert window ≥ 2.5 ns
  / ≥ 2× worst static phase offset, hysteresis ≥ 25% of window, no chatter),
  plus row 11's `lock_detector` power domain.
- **Reference range**: `spec/porting-plan.md` row 2 **as amended by DR-005** —
  `f_ref` ≈ **3.5–24.4 MHz**, i.e. `T_ref` ≈ 41–286 ns. **No spec row was
  relaxed to make anything here pass**; the sizing was moved to meet row 16,
  not the other way round, and row 2 is used exactly as DR-005 left it.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13g2`, **x86-64
  Linux** host, 8 cores. `set num_threads=1` (see `../testbench/run.sh`'s
  tooling note). All four OSDI objects this campaign loads (`psp103`,
  `psp103_nqs`, `mosvar`, `r3_cmc`) are native build products of the installed
  tree; `cap_cmim` is a plain `.subckt` with no OSDI object at all, so this
  campaign has none of the SG13CMOS5L sibling's `--soft cap_cmomi.osdi`
  host-architecture machinery (see `../testbench/run.sh`'s own note).
- **Concurrency**: the committed data was produced with `LADDER_JOBS=4`
  (`run.sh`), `XMPD_JOBS=4` (`run_xmpd_sizing.sh`) and `DIAG_JOBS=4`
  (`run_hysteresis_diag.sh`) — stated because each script's header requires a
  record produced with them > 1 to say so. Each is a set of independent
  ngspice invocations against the same frozen snapshot, concatenated in sweep
  order, so the CSVs are byte-comparable with a serial run's; the wall times
  quoted below are therefore **not** serial per-point times.
- **Reproduce**:
  ```
  PDK_ROOT=<pdk-root> PDK=ihp-sg13g2 ./testbench/run_rc_sizing.sh
  PDK_ROOT=<pdk-root> PDK=ihp-sg13g2 XMPD_JOBS=4 ./testbench/run_xmpd_sizing.sh
  PDK_ROOT=<pdk-root> PDK=ihp-sg13g2 LADDER_JOBS=4 ./testbench/run.sh
  PDK_ROOT=<pdk-root> PDK=ihp-sg13g2 DIAG_JOBS=4 ./testbench/run_hysteresis_diag.sh
  ```
  writing, respectively (line counts include the header row):
  `../corners/rc_sizing.csv` (127), `rc_pairing.csv` (49),
  `window_sizing.csv` (25); `xmpd_sizing.csv` (183);
  `rc_extract_resized.csv` (28), `window_resized.csv` (38),
  `schmitt_resized.csv` (46), `ladder_resized.csv` (22),
  `ladder_raw_resized.csv` (484), `tstep_convergence_resized.csv` (13),
  `solver_retries_resized.txt` (10 lines, no header);
  `hysteresis_diag.csv` (27).
  Wall time on this host at the concurrency above: ~2 min / ~1 h / ~1.5 h /
  ~15 min.

## Headline result

**All three of row 16's measurable criteria now pass, at every corner
measured — and the campaign found two things about *how* they pass that are
more interesting than the pass itself.**

| Row 16 criterion | Issue #81 (pre-resize) | This record (post-resize) | Verdict |
|---|---|---|---|
| Assert window ≥ 2.5 ns | 0.2193–0.3925 ns, **6–11× short** at 35/35 points | **3.732–10.249 ns**, 0 of 37 points below the floor, worst case **1.493×** margin | **now met** |
| No chatter | **chatter at 36/36** ladder corners | **`steady` at 21/21** ladder corners, at a **20×**-window static phase error | **now met** |
| Hysteresis ≥ 25% of window | **0.0% at 36/36** — assert and de-assert on the same ladder point everywhere | **25–800% of window, 0 of 21 corners below 25%**; the one 25.0% corner is ladder quantisation and resolves to **43.0%** on a fine sweep | **now met** |
| Assert window ≥ 2× worst static phase offset | `insufficient-evidence` | `insufficient-evidence` (unchanged — still needs a PFD/CP static-phase-offset record that does not exist for this PDK) | unchanged |

The two findings, both recorded because a future reader sizing this block
again will hit them:

1. **The settled-`VWIN`-vs-phase-error characteristic has a narrow-pulse
   knee**, and row 16's hysteresis criterion is consequently **non-monotonic
   in `XMPD`'s channel length**. `w=0.25u l=8u` measures *worse* (13.0% of
   window) than the shorter, stronger `w=0.35u l=6u` (20.3%) at the binding
   corner. See "The narrow-pulse knee" below.
2. **The admissible `XMPD` band is narrow**, because row 16's hysteresis
   criterion and the de-assert threshold's reach are in direct tension across
   row 2's 7× `f_ref` span. At `w=0.25u` it runs from about `l=9.7u` (where
   the fast end reaches 25% of window) to about `l=16u` (where the slow end's
   de-assert leaves the measurable range) — a factor of ~1.6 — and collapses
   to about `9.7u`–`10u`, a factor of ~1.03, if the de-assert threshold is
   required to stay inside **half** a reference period rather than a whole
   one. The landed geometry sits inside it with 1.72× margin on the criterion
   and the de-assert threshold at 62.3% of a reference period at the corner
   that maximises it. See "The two-sided `XMPD` bound".

## This is a re-derivation, not a port

Issue #78's objection to simply copying the SG13CMOS5L numbers ("four numbers
with no derivation on that PDK") is answered device by device, and the
resulting sizing is **not** the sibling's:

| Instance | SG13G2 (here) | SG13CMOS5L (#52/#66) | Why |
|---|---|---|---|
| `XRPU` | `w=0.5u l=500u`, 0.965–2.355 MΩ | `w=0.5u l=700u`, 1.351–3.297 MΩ | `rhigh` **is** the same device on both PDKs — same `cornerRES.lib`, same 1360/1020/1700 Ω/sq, and `../corners/rc_sizing.csv` re-measures it here rather than citing it (`l=700u`/`res_typ`/27 °C extracts to 2.266979 MΩ on this tree, identical to the sibling's). So the difference is a **choice**: `cap_cmim`'s higher density lets the same `R·C` be reached at a **lower node impedance**, which is the direction that reduces leakage/coupling sensitivity on a node that is otherwise megohm-scale. |
| `XCW` | `cap_cmim w=45u l=45u m=1`, 3.045 pF | `cap_cmomi w=40u l=40u m=1`, 1.691 pF | different device entirely. `../corners/rc_sizing.csv` measures `cap_cmim` at ≈1.5 fF/µm² of area plus ≈0.04 fF/µm of perimeter, against `cap_cmomi`'s ≈1.06 fF/µm². Dropping the sibling's geometry here would have landed ≈1.4× the intended capacitance at both instance sites. |
| `XDW.XC1` | `cap_cmim w=45u l=45u m=1`, 3.045 pF | `cap_cmomi w=40u l=40u m=2`, 3.382 pF | same. SG13G2 reaches a near-identical window delay from **2025 µm²** of MIM against 2 × 1600 µm² of MoM. |
| `XMPD` | `w=0.25u l=12u` | `w=0.25u l=16u` | the two-sided bound is a function of `R(XRPU)`, `twin_r` and `T_ref`, all of which differ above. Measured here, not scaled. |

`w=0.25u` is legal on this PDK: the installed DRC decks give minimum
diffusion width `Act.a` = 0.15 µm (`libs.tech/magic/ihp-sg13g2-drc.tech`
line 125) and minimum HV-FET length `Gat.a3` = 0.45 µm, and the model card's
own `wmin` parameter is `0.15e-6`. The 0.3 µm figure in
`sg13g2_pr/sg13_hv_nmos.sym` is the symbol's default, not a floor.

## Results — R/C and the `R·C ≫ T_ref` criterion (`../corners/rc_extract_resized.csv`, 27 rows)

| Device | Corner axis | Range |
|---|---|---|
| `XRPU` (`rhigh`, `w=0.5u l=500u`) | `res_bcs`/`res_typ`/`res_wcs` × −40/27/125 °C | **0.9653 MΩ** (`res_bcs`/125 °C) – **2.3551 MΩ** (`res_wcs`/−40 °C) |
| `XCW` (`cap_cmim`, `w=45u l=45u m=1`) | `cap_bcs`/`cap_typ`/`cap_wcs` × −40/27/125 °C | **2.7403 – 3.3497 pF** (nominal 3.0447 pF) |
| `XDW.XC1` (`cap_cmim`, same geometry) | same | **2.7403 – 3.3497 pF** |

`cap_cmim` has a **real** ±10% process corner and a real (if tiny, ≈6e-4 over
165 °C) temperature coefficient on this PDK — unlike SG13CMOS5L's
`cap_cmomi`, whose installed corner library maps every section to the same
nominal model. That is why this campaign sweeps it as a first-class axis
instead of re-injecting a synthetic ±20% band (see
`../testbench/tb_extract_c.sp.tmpl`'s header, issue #81).

**`R·C` at the integrating node**, over the joint resistor-corner ×
cap-corner × temperature grid (paired at matching temperature — one die, one
temperature):

| | `T_ref` | `R·C / T_ref` |
|---|---|---|
| `R·C` itself | — | **2.6469 µs** (`res_bcs`/`cap_bcs`/125 °C) – **7.8842 µs** (`res_wcs`/`cap_wcs`/−40 °C) |
| `f_ref` = 3.5 MHz (**binding**, slowest reference) | 285.7 ns | **9.26 – 27.59×** |
| `f_ref` = 24.4 MHz (fastest reference) | 41.0 ns | 64.6 – 192.4× |

Issue #81 measured the same quantity at **0.65–1.57 ns**, i.e.
**0.0023–0.0384×** `T_ref` (`../corners/ladder.csv`'s own `rc_over_tref`
column), which is why that block chattered at 36/36 corners. The re-size
moves it from ~1/300 of a reference period to ~9–28 reference periods at the
binding end. **The sign of the inequality `R·C ≫ T_ref` is now correct at
every point of the grid, worst case 9.26×.**

**How the split between `R` and `C` was chosen** (`../corners/rc_pairing.csv`,
48 candidate `XRPU`-length × `XCW`-geometry pairs, each reporting the
worst-case `R·C` over the full corner grid): the criterion applied was
`R·C ≥ 8× T_ref` at the binding slow end, and among the pairs meeting it, the
one with the **lowest** `XRPU` resistance whose `XCW` geometry is no larger
than `XDW.XC1`'s (which is independently pinned by the window criterion
below). `l=500u` + `w=45u l=45u` is that pair: 9.26× worst case, 2.355 MΩ
maximum node impedance, and one single MIM geometry used at both capacitor
sites. `l=700u` + `w=36u l=36u` also clears 8× (at 8.31×) but at 3.297 MΩ,
and `l=1000u` + `w=30u l=30u` at 4.710 MΩ — both trade node impedance for
MIM area in the direction this record did not want.

**Is one fixed sizing enough for the whole amended `f_ref` range?** Yes, and
it is measured rather than argued: the requirement is one-sided (`R·C` must
*exceed* `T_ref`), `T_ref` only shrinks as `f_ref` rises, and the ladder was
run at **both** ends of the range with the same verdicts. **Row 2 does not
need to narrow and this record does not propose narrowing it** — no decision
record is owed.

## Results — comparator window (`../corners/window_resized.csv`, 37 rows)

`twin_r`, the `delaywin_hv` chain's low→high propagation delay measured on a
bare `delaywin_hv` with an ideal step in — the quantity row 16's "assert
window" applies to:

| | Value |
|---|---|
| Full matrix range | **3.7320 – 10.2487 ns** |
| Nominal (`mos_tt`/`res_typ`/`cap_typ`/27 °C/3.3 V) | 6.0271 ns |
| Worst case (`mos_ff`/`res_bcs`/**`cap_bcs`**/−40 °C/**3.63 V**) | **3.7320 ns** = **1.493×** the floor |
| Best case (`mos_ss`/`res_wcs`/`cap_wcs`/125 °C/2.97 V) | 10.2487 ns |
| Ported target (row 16) | ≥ 2.5 ns |
| Points below the floor | **0 / 37** |
| Issue #81, same measurement, pre-resize | 0.2193 – 0.3925 ns (6–11× short at 35/35) |

**Worst-case stacking is in the matrix, not interpolated.** Issue #81's grid
held the supply at nominal while sweeping the corner bundles and held the
bundle at typ while sweeping supply, so the point that actually *minimises*
`twin_r` — every fast-direction axis at once — was in neither sub-sweep. This
issue adds both explicit stacks (fast and slow) to `run.sh`'s window matrix;
the 3.7320 ns figure above is one of them. The same gap the SG13CMOS5L
sibling's RECORD-002 had to close after its own RECORD-001 missed it.

**How `w=45u l=45u` was chosen** (`../corners/window_sizing.csv`, 8 candidate
geometries × 3 window stacks): the smallest `cap_cmim` geometry swept whose
worst-case (fast-stack) `twin_r` clears the 2.5 ns floor with ≥ 1.4× margin.

| `XDW.XC1` | fast stack `twin_r` | vs. 2.5 ns floor |
|---|---|---|
| `w=4u l=4u` (as drawn) | 0.2061 ns | 0.082× — fails |
| `w=30u l=30u` | 1.7608 ns | 0.704× — fails |
| `w=36u l=36u` | 2.4548 ns | 0.982× — fails |
| `w=40u l=40u` | 2.9875 ns | 1.195× — passes, thin |
| **`w=45u l=45u`** (landed) | **3.7320 ns** | **1.493×** |
| `w=50u l=50u` | 4.5639 ns | 1.826× — more area for margin already had |

**Timestep-convergence check**
(`../corners/tstep_convergence_resized.csv`, 12 rows): `twin_r` at 4
representative corners at 20 ps / 5 ps / 1.25 ps maximum internal timestep
changes by **≤ 0.033%** end to end. `twin_r` is not a discretisation artifact.

## Results — the readout Schmitt (`../corners/schmitt_resized.csv`, 45 rows)

`schmitt_hv` is **untouched by this issue**, and this matrix is here because
its input-referred hysteresis is one of the two factors row 16's phase-error
hysteresis is built from (see the next section):

| | Range over the full MOS × temperature × supply grid |
|---|---|
| `V_TH,rising` | 1.8656 – 2.2901 V |
| `V_TH,falling` | 0.9904 – 1.2974 V |
| Hysteresis | **0.8331 – 1.0347 V** (27.05 – 30.28% of `VDD`) |

That is the *fixed* cell — issue #66's classic cross-coupled feedback
connection, already landed on this PDK before this issue started. There is no
"as drawn vs. rewired" control here because there is nothing left to rewire;
the SG13CMOS5L sibling's RECORD-002 measured the broken version at
0.9–1.6 mV, and this repo's SG13G2 `schmitt_hv.sch` has never carried it
since #66.

## The two-sided `XMPD` bound (`../corners/xmpd_sizing.csv`, 182 rows)

In this topology row 16's hysteresis criterion is a **phase-error** width and
factors as

```
H_tau  ≈  H_volts(schmitt_hv)  /  |dVWIN/dtau|
```

with the settled integrating-node voltage set by the balance between `XRPU`'s
charge over one reference period and `XMPD`'s discharge over one `WIDE`
pulse,

```
VWIN  ≈  VDD  −  I_sat(XMPD) · R(XRPU) · (tau − twin_r) / T_ref
```

— topology, established by control on the SG13CMOS5L sibling
(RECORD-002/RECORD-003) and reused here per issue #78's own "Reusable facts",
not re-derived. `R·C` does not appear in it at all, so `XMPD` is the knob that
buys transition width **without** spending the `R·C` margin above. `H_volts`
is measured and healthy on this PDK (previous section), so the only unknown
is `|dVWIN/dtau|`.

`T_ref` is in the numerator, so the **fast** end of row 2's range (24.4 MHz)
has ~7× less hysteresis in units of the window and is the **binding** end for
row 16 — while the same factor pushes the **de-assert threshold** out at the
**slow** end (3.5 MHz), where it must stay inside one reference period or the
block stops being able to de-assert at all. Hence a two-sided sweep.

**Lower bound — how strong `XMPD` may be.** `mos_tt`/`res_wcs`/`cap_typ`/
−40 °C at 24.4 MHz; `twin_r` = 5.2907 ns, `V_TH+` = 2.0785 V,
`V_TH−` = 1.1313 V. Trip points interpolated from the settled `VWIN` curve,
not read off the quantised `LOCK` pin:

| `XMPD` | `L/W` | assert (× window) | de-assert (× window) | **hysteresis (× window)** | vs. row 16's ≥ 0.25× |
|---|---|---|---|---|---|
| `w=2u l=0.5u` (as drawn) | 0.25 | < 1.00 | < 1.00 | **unresolvable** — `VWIN` is already at 20 mV at τ = 1.00× window | fails |
| `w=0.5u l=4u` | 8 | 1.027 | 1.090 | 0.063 | fails |
| `w=0.35u l=6u` | 17.14 | 1.076 | 1.279 | 0.203 | fails |
| `w=0.25u l=8u` | 32 | 1.257 | 1.387 | **0.130** | fails — **and worse than the stronger `l=6u` above**, see the knee |
| `w=0.25u l=10u` | 40 | 1.271 | 1.552 | 0.281 | 1.12× |
| **`w=0.25u l=12u`** (landed) | **48** | **1.285** | **1.712** | **0.428** | **1.71×** |
| `w=0.25u l=16u` | 64 | 1.577 | 2.255 | 0.678 | 2.71× |

**Upper bound — how weak `XMPD` may be.** `mos_ss`/`res_bcs`/`cap_typ`/
125 °C at 3.5 MHz; `twin_r` = 8.5167 ns and `T_ref` = 285.7 ns, so one window
is 3.0% of a reference period:

| `XMPD` | `L/W` | assert (× window) | de-assert (× window) | de-assert as % of `T_ref` |
|---|---|---|---|---|
| `w=2u l=0.5u` (as drawn) | 0.25 | 1.374 | 1.682 | 5.0% |
| `w=0.5u l=4u` | 8 | 2.751 | 4.971 | 14.8% |
| `w=0.35u l=6u` | 17.14 | 4.354 | 8.770 | 26.2% |
| `w=0.25u l=8u` | 32 | 6.458 | 13.629 | 40.6% |
| `w=0.25u l=10u` | 40 | 7.794 | 16.799 | 50.1% |
| **`w=0.25u l=12u`** (landed) | **48** | **9.150** | **19.912** | **59.4%** |
| `w=0.25u l=16u` | 64 | 11.827 | **> 24.0** | **> 71.6%** — off the end of the sweep |

`w=0.25u l=12u` is the geometry this record lands: **1.71× margin on row 16's
hysteresis criterion at the corner that minimises it**, with the de-assert
threshold at the corner that maximises it still inside one reference period
(59.4%) *and* inside the 24×-window ladder that measures it. One step weaker
(`l=16u`) pushes de-assert past 71.6% of a reference period and off the end of
the ladder; two steps stronger (`l=8u`) drops the hysteresis to 0.130×.

**The binding corners are not the obvious ones, and a first pass got them
wrong.** That pass used `mos_ff` for the lower bound (strongest `I_sat`, hence
steepest transition) and `mos_tt` for the upper. Both are wrong here, and the
correction is recorded rather than quietly applied:

- The **lower** bound's criterion is a fraction *of the window*, and `twin_r`
  moves with `mos_corner` too. At `res_wcs`/−40 °C/24.4 MHz with the landed
  block, `mos_ff` gives `twin_r` = 4.524 ns and **58.8%** of window while
  `mos_tt` gives 5.291 ns and **43.0%** — `mos_tt` is the worse corner
  (`../corners/hysteresis_diag.csv`, both measured). `run.sh`'s ladder carries
  `mos_ff`/`res_wcs`/−40 °C at the fast end as the control that keeps this
  visible.
- The **upper** bound's ceiling is one reference period expressed in units of
  that corner's *own* window, so the **largest** `twin_r` tightens it:
  `mos_ss`/`res_bcs`/125 °C has `twin_r` = 8.517 ns against `mos_tt`'s
  7.197 ns, and `mos_ss` also has the weakest `I_sat`, which pushes the
  threshold itself further out. Both effects point the same way.

### The narrow-pulse knee, and why the criterion is non-monotonic in `L`

`WIDE = ERR AND delaywin_hv(ERR)`, so for `tau` only slightly above `twin_r`
the `WIDE` pulse is very short and the `nand2_hv` + `inv_hv` pair does not
drive `XMPD`'s gate to a full rail. The settled `VWIN` therefore has a **knee**
a few percent of a window above `tau = twin_r`, across which it falls much
faster than the one-line model predicts. Measured at the binding corner with
the landed `XMPD` (`../corners/hysteresis_diag.csv`): `VWIN` = 2.557 V at
`tau` = 1.25× window and 1.865 V at 1.30× — a 0.69 V step across 0.05× the
window, against ≈1.9 V per unit window either side of it.

Whether row 16's criterion passes depends on **whether `schmitt_hv`'s two trip
points straddle that knee**, which is a property of the `XRPU`/`XMPD` ratio
and not a monotone function of it. That is exactly what the `w=0.25u l=8u` row
in the lower-bound table shows: it measures 0.130× the window, *worse* than
the shorter and stronger `w=0.35u l=6u`'s 0.203×, because at `l=8u` the knee
lands between `V_TH+` and `V_TH−` and at `l=12u` both trip points sit on the
gentle side of it. **A sizing pass that assumed monotonicity and bisected on
`L` would have converged to the wrong answer**, which is the practical reason
this record's method is a swept CSV rather than a solved inequality.

### The band is narrow, and that is a real result

Reading the two tables together, the admissible interval for `L` (at
`w=0.25u`) runs from about `9.7u` — where the fast end reaches 25% of window —
to about `16u`, where the slow end's de-assert leaves the measurable range;
and if one demands the de-assert threshold stay inside **half** a reference
period rather than a whole one (the largest phase error a simple XOR can
represent, as opposed to a PFD's full ±2π), the upper end drops to about
`10u` and the interval is a factor of ~1.03 wide.

The tension is structural, not a sizing mistake, and cannot be widened with
the four devices in this issue's scope: both bounds scale as `1/(I_sat·R)`,
so changing `XRPU` moves them together and leaves their ratio fixed; the ratio
is set by row 2's 7× `f_ref` span, by `twin_r` at each binding corner, and by
`R`'s own 2.44× corner spread between `res_wcs`/−40 °C and `res_bcs`/125 °C.
The one lever inside this scope is `XDW.XC1` — shrinking it shortens `twin_r`
and widens the band roughly in proportion — but it is pinned from below by
row 16's own 2.5 ns floor, and `w=40u l=40u` (the next step down) would trade
the window's 1.493× worst-case margin for 1.195× to buy ~1.25× on the `XMPD`
band. **This record does not make that trade** — it spends margin on a hard
ratified floor to buy margin on a criterion that already passes at 1.71× — but
it records the trade explicitly so a future pass can revisit it deliberately.

## Results — phase-error ladder (`../corners/ladder_resized.csv`, 21 rows)

Ladder set `resized`: 23 points, 0.25×-window steps from 1.00× to 2.50×,
reaching **24×** the window; chatter probe (`TAUBIG_XWIN`) at **20×**.

| Metric | This record (21 corners) | Issue #81 (36 corners, pre-resize) |
|---|---|---|
| **Chatter verdict at the 20×-window static phase error** | **`steady` at 21/21** | `chatter` at 36/36 (at a 10× probe) |
| **Hysteresis** | **25.0 – 800.0% of window; 0 of 21 below the 25% criterion** | **0.0% at 36/36** |
| Assert threshold | 1.25× – 10.00× window | 1.00× – 1.40× |
| De-assert threshold | 1.50× – 18.00× window = **11.1 – 62.3% of `T_ref`** | equal to assert everywhere |
| In-window `LOCK` rail (read from the block, not assumed) | `lo` at 21/21 | `lo` at 36/36 |
| Recovery time `trec` (discharged → mid-rail, zero phase error) | **2.125 – 5.194 µs** | 0.683 – 1.834 ns |
| Supply current, in-lock | 2.44 – 22.60 µA | 2.84 – 21.62 µA |
| Supply current, out-of-lock (20×-window probe) | **38.3 – 100.5 µA** | 7.6 – 61.0 µA (10× probe) |
| `R·C / T_ref` | 10.3 – 174.9× | 0.0023 – 0.0384× |
| Settling fraction achieved within the run (`settle_frac`) | **0.9817 – 0.9831** | n/a (#81 ran a flat 4 reference periods) |

**`trec` is now three orders of magnitude longer, and that is the point.**
2.13–5.19 µs is 7–18 reference periods at 3.5 MHz (52–127 at 24.4 MHz): the
block now averages the coincidence gate over many cycles instead of following
it. Issue #81's 0.68–1.83 ns was the measured symptom of the defect this
issue fixes.

**The 25.0% corner is ladder quantisation, not the block's margin.** At
`mos_tt`/`res_wcs`/`cap_typ`/−40 °C/24.4 MHz the ladder puts assert at 1.25×
and de-assert at 1.50× — adjacent points on a 0.25×-window ladder, so 25.0% is
the *smallest non-zero value the ladder can report*, and a "1.00× margin"
there is a statement about the measurement, not the circuit.
`../testbench/run_hysteresis_diag.sh` re-measures that exact corner on a
0.05×-window grid, and interpolates the two trip points against the same
corner's own `schmitt_resized.csv` trip voltages:

| corner (24.4 MHz, 3.3 V) | `twin_r` | assert | de-assert | **hysteresis** | vs. ≥ 0.25× |
|---|---|---|---|---|---|
| `mos_tt`/`res_wcs`/`cap_typ`/−40 °C (the ladder's 25.0% corner) | 5.2907 ns | 1.2846× | 1.7142× | **0.4297× = 43.0%** | **1.72×** |
| `mos_ff`/`res_wcs`/`cap_typ`/−40 °C (the sizing sweep's own stack) | 4.5242 ns | 1.2953× | 1.8829× | **0.5876× = 58.8%** | 2.35× |

The first row is a genuine correction of the ladder's own number for that
corner; the second is a **cross-check** — the sizing sweep ran the
intermediate `lock_detector_rc_resized.spice` snapshot with `XMPD`
substituted in and got 0.428× at the `mos_tt` corner, against 0.4297× here
from the committed `lock_detector_resized.spice`, a 0.4% difference. The two
snapshots therefore differ in nothing that matters, and the sizing sweep's
selection row is reproducible against the landed block.

**The hysteresis is `schmitt_hv`'s, not a bistable integrator.** The two
ladder/diagnostic copies start from opposite `VWIN` rails, and at every
diagnostic point their *settled* `VWIN` agrees to within **71 mV** — so the
integrating node itself has one fixed point per phase error, and the
phase-error hysteresis is entirely `H_volts` divided by the local
`|dVWIN/dtau|`, exactly as the factorisation says.

**Row 11 — power.** In-lock 2.44–22.60 µA, out-of-lock 38.3–100.5 µA. The
in-lock range is essentially unchanged from issue #81's 2.84–21.62 µA; the
out-of-lock top rises from 61.0 µA to 100.5 µA, the direct switching cost of
driving 3.04 pF at `delaywin_hv`'s output every reference cycle. **The two
out-of-lock figures are not directly comparable**: #81 probed at 10× the
window and this record probes at 20×, a change forced rather than cosmetic
(see below). Row 11's `lock_detector` domain is re-bounded at
**2.44–100.5 µA** for the resized SG13G2 block.

## Settling budget — a measurement error this record made and corrected

A first pass of this campaign capped each ladder/diagnostic transient at
`TSTOP_MAX` = 16 µs, which at the `res_wcs`/−40 °C corner (where `R·C`
reaches 7.17 µs) left `settle_frac` = 0.893. **At 89% settled the two
start-state copies have not converged, and the residual difference reads out
as a spurious hysteresis.** Measured directly at
`mos_tt`/`res_wcs`/−40 °C/24.4 MHz, `tau` = 1.25× window, `XMPD` still at
`w=0.25u l=8u`:

| | `VWIN` (discharged start) | `VWIN` (charged start) | difference |
|---|---|---|---|
| 391 cycles (`settle_frac` 0.893) | 2.017 V | 2.334 V | **0.317 V** |
| 782 cycles (`settle_frac` 0.989) | 2.197 V | 2.234 V | **0.037 V** |

Under the 16 µs cap that corner reported an apparent 25.0% hysteresis (one
ladder step) which was **entirely** the unconverged transient; the real value
for `l=8u` there is 13.0%. `TSTOP_MAX` is 32 µs in the committed scripts, and
`settle_frac` is **0.9817–0.9831 at every one of the 21 ladder corners** above.
This is recorded rather than silently fixed because the failure mode is
specific and repeatable: *an under-settled two-start-state measurement
manufactures hysteresis*, and a reader re-running this campaign on a slower
host will be tempted to lower exactly that cap.

## Coverage, and how it was reduced (explicit, per `sim/README.md`)

The `rc_extract`, `window`, `schmitt` and `tstep_convergence` matrices stay at
full density (each is a single-device solve or a 60 ns bare-`delaywin_hv`
transient, ~1 s regardless of the resize) — and the **window matrix gains two
worst-case stacks** issue #81's grid did not contain. The ladder is reduced
from 36 corners to 21:

| Axis | Issue #81 | This record | Why the reduction is defensible |
|---|---|---|---|
| `rc_extract` | full (27 rows) | **full** (27 rows) | cheap |
| `window` | 35 rows | **37 rows — full density + two explicit worst-case stacks** | cheap; this is the row-16 floor's own evidence |
| `schmitt` | 45 rows | **full** (45 rows) | cheap; `schmitt_hv` untouched |
| `tstep_convergence` | 12 rows | **full** (12 rows) | cheap |
| ladder — MOS corner | 5 corners in the main grid | `mos_tt` grid + `mos_ff`/`mos_ss` at both `f_ref` ends | `R` and `C` have **no** `mos_corner` dependence at all; it reaches the ladder through `twin_r` (full density in `window_resized.csv`) and through `I_sat(XMPD)` — the latter is why `mos_ff`/`mos_ss` appear at the **fast** end rather than only as slow-end spot checks |
| ladder — RES corner × temperature | 3 × 3 at the fast end + 3 × 3 at the slow end | **full 3 × 3 at the slow end** | the slow end is the binding one for `R·C ≫ T_ref`, and that axis is not reduced there |
| ladder — reference frequency | 27 fast + 9 slow | **9 slow (full res × temp) + 6 fast** | a 24.4 MHz corner costs ~8× a 3.5 MHz one for the same absolute `tstop`; the fast end is *extended* beyond a token spot check because it is the binding end for row 16's hysteresis |
| ladder — cap corner | swept in the main grid | 2 spot checks (`cap_bcs`/`cap_wcs`) at the slow end | `window_resized.csv` carries the cap corner at full density; on the ladder it moves `R·C` by ±10%, well inside the 9.26× worst-case margin |
| ladder — supply | 1 point (nominal) | 2 spot checks (2.97 / 3.63 V) slow + 1 (3.63 V) fast | supply moves both `I_sat` and `schmitt_hv`'s trip points, so it gets a fast-end point too |
| ladder — ladder step / reach | 9 points, 0.20× step, reach 10× | **23 points, 0.25× step through 1.00–2.50×, reach 24×** | the restored hysteresis separates and displaces both thresholds; a ladder stopping at 2.5× would report "hysteresis = 0" at the slow end for the same reason a ruler too short to reach reports "length = end of ruler" |
| ladder — chatter probe | 10× window | **20× window** | so the chatter point is beyond de-assert at every corner; a 10× probe now lands *inside* the hysteresis band at several slow-end corners |
| ladder — total | 36 corner points | **21 corner points** | |

**What the reduction costs, stated plainly**: the ladder's `mos_corner`, cap
and supply axes are spot-checked rather than swept, and the fast end carries 6
of the 21 corners rather than a full grid. It costs nothing on the window
criterion (full density, plus two worst-case stacks issue #81 did not have) or
on the `R·C` claim (full resistor × temperature grid at the binding reference
frequency), and the hysteresis criterion's own binding corner is separately
re-measured without ladder quantisation (`hysteresis_diag.csv`).

**Solver retries**: 10 of ~500 ladder decks needed one recorded `trtol=1`
retry (`../corners/solver_retries_resized.txt`); all 10 are slow-end or
fast-end ladder *points*, none is a window, Schmitt or extraction deck, and
none changed a verdict. `trtol=1` is a genuine truncation-error relaxation, so
it is never in the committed templates and is only ever applied after a deck
has already failed outright — see `run.sh`'s `run_ngspice_or_die` header.

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 16 — assert window ≥ 2.5 ns**: **bounded, and the bound MEETS the
  criterion.** 3.732–10.249 ns at 37/37 points including two explicit
  worst-case stacks and `cap_cmim`'s own ±10% corner; worst-case margin
  1.493×.
- **Row 16 — no chatter**: **bounded, and the bound MEETS the criterion.**
  `steady` at 21/21 ladder corners at a **20×**-window static phase error, at
  both ends of the DR-005-amended `f_ref` range.
- **Row 16 — hysteresis ≥ 25% of window**: **bounded, and the bound MEETS the
  criterion.** 25–800% of the window at 21/21 ladder corners, and the single
  25.0% corner (which is the ladder's own quantum) resolves to **43.0%** —
  1.72× the criterion — on a 0.05×-window sweep interpolated against the same
  corner's measured Schmitt trip points. The margin is real but the
  *admissible sizing band* around it is narrow; see "The band is narrow".
- **Row 16 — static phase offset comparison**: **`insufficient-evidence`**,
  unchanged — still needs a PFD/CP static-phase-offset record, which does not
  exist for SG13G2 (the SG13CMOS5L sibling's `sg13cmos5l-closed-loop-lock`
  RECORD-003/005 has one, and it is a different PDK and a different `cp`).
- **Row 16 — `XCW`/`XDW.XC1` capacitor-corner sensitivity**: **bounded.**
  `cap_cmim`'s own ±10% process corner is swept at full density in the window
  matrix and spot-checked on the ladder; it moves `twin_r` by −9.58%/+9.58% at
  the nominal MOS/RES/temperature/supply point (6.0271 ns → 5.4500 / 6.6043 ns) and does not change any ladder verdict. Unlike the SG13CMOS5L
  sibling, this is a **real characterised corner**, not a synthetic
  model-uncertainty band.
- **Row 11 — power (`lock_detector` domain)**: **bounded for the resized
  SG13G2 block at 2.44–100.5 µA** (in-lock 2.44–22.60, out-of-lock
  38.3–100.5 at a 20×-window probe). Not directly comparable with issue #81's
  own 2.84–61.0 µA, which probed out-of-lock at 10× the window.
- **Row 2 — `f_ref` range**: **not touched, and does not need to be.** One
  fixed sizing covers 3.5–24.4 MHz, verified at both ends. No decision record
  is owed by this record.

## What this does not bound

- **`XMPD`'s sizing margin against process spread.** The admissible band is
  narrow (see "The band is narrow"), and this record measures it only at the
  characterised process corners — there is no per-instance mismatch model for
  `sg13_hv_nmos` in this flow, so a device that lands off-corner is not
  covered. The band's narrowness, not the landed value, is the risk.
- **Random device mismatch**, generally. No per-instance mismatch model is
  used for any device here; `cap_cmim` has a mismatch library section but this
  campaign sweeps only the process corners.
- **The out-of-lock supply current at the fast end.** The `TAUBIG_XWIN` = 20×
  probe is 106 ns at the fast end's own window against a 41 ns `T_ref`, so at
  24.4 MHz the XIU copy's stimulus is a saturated one rather than a
  phase-error one, and its `idd_outlock` figure there is an upper-bound
  switching number, not a phase-error measurement. The same limitation issue
  #81's own 10× probe already had; carried from the SG13CMOS5L sibling's
  method and not fixed here.
- **Post-layout parasitics, and the layout itself.** `VWIN` is now a far
  higher-impedance node than it was (0.97–2.36 MΩ pull-up instead of
  11.8–28.6 kΩ), which makes it correspondingly more sensitive to layout
  leakage and coupling — junction leakage at 125 °C in particular is not
  modelled here and is not negligible against a ~1.4 µA pull-up current. **Any
  existing SG13G2 `lock_detector` layout predates this resize and does not
  implement it** (a 500 µm `rhigh` strip needs snaking; `XCW` grows
  36 → 2025 µm² and `XDW.XC1` 16 → 2025 µm²). Re-drawing and extracting it is
  not in this issue's scope.
- **Closed-loop behaviour.** Everything here is an open-loop, stimulus-driven
  measurement of the block in isolation. Whether the block's now-wide
  hysteresis band is ever *entered* during a real acquisition is the question
  the SG13CMOS5L sibling answered with a closed-loop dwell deck
  (`sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_vwin_dwell.sh`,
  issue #76); there is no SG13G2 closed-loop deck, so the equivalent question
  is open here, and with it the `schmitt_hv` crowbar-current question that
  deck was built to settle.
- **Anything under `sim/sg13cmos5l-*/`.** Untouched by this issue, per its own
  scope.
