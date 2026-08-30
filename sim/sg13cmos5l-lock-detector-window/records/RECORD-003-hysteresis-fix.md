# RECORD-003: lock-detector window, hysteresis and chatter, **after** the `schmitt_hv` feedback rewiring and the `XMPD` re-size

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #66 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L PVT
  campaign). Supersedes nothing. `RECORD-001` measured the pre-resize block
  and `RECORD-002` the block after issue #52's `XRPU`/`XCW`/`XDW.XC1` resize;
  both stand unedited, each with its own frozen netlist snapshot and its own
  `../corners/*.csv` suffix. This record measures the **same claim** against
  the block after the two changes #52 identified but was out of scope to make.
- **DUT**: `../netlist-snapshots/lock_detector_hystfix.spice`, frozen from
  `design/sg13cmos5l/netlist/lock_detector.spice` at this record's own branch.
  It differs from RECORD-002's snapshot in **exactly three netlist lines** and
  is byte-identical everywhere else:

  | Line | RECORD-002 (was) | RECORD-003 (now) |
  |---|---|---|
  | `XMPD` (`sg13_hv_nmos`, `WIDE`-gated pull-down) | `w=2u l=0.5u` (`L/W` = 0.25) | **`w=0.25u l=16u`** (`L/W` = 64) |
  | `schmitt_hv.XMP3` (feedback PMOS) | `np OUT VDD VDD` | **`VSS OUT np VDD`** |
  | `schmitt_hv.XMN3` (feedback NMOS) | `nn OUT VSS VSS` | **`VDD OUT nn VSS`** |

  **`XRPU` (`rhigh w=0.5u l=700u`), `XCW` and `XDW.XC1` (`cap_cmomi`
  40 µm × 40 µm) are untouched**, so nothing issue #52 bought is spent here —
  and both of #52's passing criteria are **re-measured below rather than
  assumed**.
- **Claim under test**: `spec/porting-plan.md` row 16 (assert window ≥ 2.5 ns
  / ≥ 2× worst static phase offset, hysteresis ≥ 25% of window, no chatter),
  plus row 11's `lock_detector` power domain. Same claim RECORD-001 and
  RECORD-002 measured.
- **Reference range**: `spec/porting-plan.md` row 2 **as amended by DR-005**
  (PR #46) — `f_ref` ≈ **3.5–24.4 MHz**, i.e. `T_ref` ≈ 41–286 ns. **No spec
  row was relaxed to make anything here pass**; the device sizing was moved to
  meet row 16, not the other way round.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, **x86-64
  Linux** host. `set num_threads=1` (see `../testbench/run.sh`'s tooling note).
  Two ngspice `.options` were added to this slug's four transient templates
  (`itl4=5000 gmin=1e-11`) and one recorded retry to `run.sh`; both are
  measured, neither is an accuracy relaxation, and the whole story is under
  "Tool friction" below.
- **This host is x86-64, so `cap_cmomi.osdi` loads and the `real` DUT variant
  is back.** RECORD-002 ran on arm64, where that object could not be loaded at
  all, and listed the resulting gap under "What this does not bound". This
  record closes it — see "What RECORD-002 could not bound and this record
  does" below.
- **Reproduce**:
  `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh` writes
  `../corners/rc_extract_hystfix.csv` (15 rows),
  `../corners/window_hystfix.csv` (102), `../corners/schmitt_hystfix.csv`
  (45), `../corners/ladder_hystfix.csv` (21),
  `../corners/ladder_raw_hystfix.csv` (441),
  `../corners/tstep_convergence_hystfix.csv` (12) and
  `../corners/solver_retries.txt`.
  `PDK_ROOT=... ./testbench/run_schmitt_rewire.sh` writes
  `../corners/schmitt_rewire.csv` (108 rows, **both PDKs**).
  `PDK_ROOT=... PDK=... ./testbench/run_xmpd_sizing.sh` writes
  `../corners/xmpd_sizing.csv` (126 rows).

## Headline result

**All three of `spec/porting-plan.md` row 16's measurable criteria now pass,
at every corner measured.** This is the first record in this slug for which
that is true.

| Row 16 criterion | RECORD-001 (pre-resize) | RECORD-002 (post-#52) | **RECORD-003 (post-#66)** | Verdict |
|---|---|---|---|---|
| Assert window ≥ 2.5 ns | 0.219–0.409 ns, **6–11× short** at 92/92 | 3.688–11.24 ns, 0 of 81 below the floor | **3.688–11.24 ns, 0 of 102 below the floor**, worst case **1.475×** margin | **met — re-confirmed, unchanged** |
| Hysteresis ≥ 25% of window | 0 resolvable at a 0.15×-window step, 0/92 | 0 resolvable at a 0.20×-window step, 0/18 | **50 – 800% of window, 0 of 21 corners below 25%**; worst case **50% = 2.0×** the criterion | **now met** |
| No chatter | **chatter at 92/92** | `steady` at 18/18 at a 10×-window static phase error | **`steady` at 21/21** at a **20×**-window static phase error | **met — re-confirmed at twice the phase error** |
| Assert window ≥ 2× worst static phase offset | `insufficient-evidence` | `insufficient-evidence` | `insufficient-evidence` (unchanged — still needs a PFD/CP static-phase-offset record that does not exist) | unchanged |

And the two things issue #52 bought, re-measured rather than assumed:

| #52 result | RECORD-002 | **RECORD-003** |
|---|---|---|
| `XRPU` resistance, 9 corner points | 1.351–3.297 MΩ | **byte-identical**, on a different host and ngspice build |
| `R·C` at the integrating node | 2.285–5.576 µs = **8.0–19.5×** `T_ref` at 3.5 MHz (6.4–23.4× incl. the ±20% MOM band) | **2.285–5.576 µs = 8.0–19.5× (6.4–23.4×)** — identical; `XRPU`/`XCW` are untouched and the extraction confirms it |
| Assert window `twin_r` | 3.688–11.24 ns | **3.688–11.24 ns**, now over 102 points instead of 81 |
| Worst-case window corner | `mos_ff`/`res_bcs`/−40 °C/3.63 V/`ideal−0.20` | same corner, same 3.688 ns |


## The two changes, and why each one is necessary but not sufficient

RECORD-002 factored row 16's hysteresis criterion into two independent terms
and measured both:

```
H_tau  ≈  H_volts(schmitt_hv)  /  |dVWIN/dtau|
```

and found *both* degenerate — `H_volts` ≈ 1 mV from a wiring defect, and
`|dVWIN/dtau|` so steep that the entire settled-`VWIN` transition was
≤ 0.05× the window wide. It also measured, by control, that fixing either one
alone changes nothing: rewiring `schmitt_hv` on the as-drawn `XMPD` moved the
settled `VWIN` curve by less than a millivolt at every phase-error point.
This record fixes both.

### Term 1 — `schmitt_hv`'s feedback devices, measured before and after, on both PDKs

A six-transistor CMOS Schmitt trigger gets its hysteresis from two feedback
devices that pull the internal stack nodes toward the **opposite** rail from
their own series stack. Both were tied to the **same** rail, which leaves the
cell with no state memory at all — functionally a plain inverter with a
manufacturing tolerance.

`../testbench/run_schmitt_rewire.sh` measures the committed cell against an
as-drawn control rebuilt by *reversing* the landed substitution (the mirror
image of RECORD-002's own scratch control), on **both** PDKs, over 3 MOS
corners × 3 temperatures × 3 supplies:

| PDK | DUT | Input-referred hysteresis | % of `VDD` | `V_TH,rising` | `V_TH,falling` |
|---|---|---|---|---|---|
| `ihp-sg13cmos5l` | as drawn | **0.88 – 1.58 mV** | 0.025 – 0.053% | 1.298 – 1.706 V | 1.297 – 1.705 V |
| `ihp-sg13cmos5l` | **as committed** | **804 mV – 1.058 V** | **26.3 – 30.3%** | 1.856 – 2.286 V | 0.991 – 1.307 V |
| `ihp-sg13g2` | as drawn | 0.88 – 1.58 mV | 0.025 – 0.053% | 1.298 – 1.706 V | 1.297 – 1.705 V |
| `ihp-sg13g2` | **as committed** | **804 mV – 1.058 V** | **26.3 – 30.3%** | 1.856 – 2.286 V | 0.991 – 1.307 V |

The two PDKs' 54 measured trip-point pairs are **identical field for field**,
which is the expected consequence of DR-003 Finding 1 (`sg13_hv_nmos` /
`sg13_hv_pmos` are the same models on both) — but it is measured here rather
than assumed, because it is the evidence for fixing the SG13G2 sibling in the
same change (see "SG13G2 sibling decision").

At the nominal 3.3 V supply alone (the 9 points issue #66 quoted from
RECORD-002's arm64 / `ngspice-47` diagnostic) this run gives **0.89 – 1.55 mV
→ 879 – 979 mV**, against RECORD-002's 0.89–1.55 mV → 881–979 mV. The
before column reproduces exactly and the after column to 2 mV, across a
different host, a different ngspice build and a `real` rather than
ideal-substituted `cap_cmomi`.

`../corners/schmitt_hystfix.csv` re-measures the committed cell on `run.sh`'s
own wider grid (5 MOS corners × 3 temperatures × 3 supplies, 45 rows).

| | Range over 45 corner points (5 MOS × 3 temperatures × 3 supplies) |
|---|---|
| `V_TH,rising` | 1.845 – 2.295 V |
| `V_TH,falling` | 0.985 – 1.313 V |
| **Hysteresis** | **804 mV – 1.058 V** (**26.3 – 30.3% of `VDD`**) |

RECORD-001 and RECORD-002 measured 0.88–1.58 mV on this same grid. The
mechanism row 16's hysteresis criterion depends on now exists.

### Term 2 — `XMPD`, and why the fast end of the `f_ref` range is the binding one

The settled integrating-node voltage is the balance between `XRPU`'s charge
over one **reference period** and `XMPD`'s discharge over one `WIDE` pulse:

```
VWIN  ≈  VDD  −  I_sat(XMPD) · R(XRPU) · (τ − t_win) / T_ref
```

Three consequences, all of which this record measures rather than argues:

1. **`R·C` does not appear.** The transition width is set by the
   `XRPU`/`XMPD` *strength* ratio, so `XMPD` is the one device in the
   expression that is not already spoken for by #52's `R·C ≫ T_ref`
   requirement. That is why it is the knob.
2. **`T_ref` is in the numerator**, so the phase-error hysteresis — and the
   assert/de-assert thresholds — are **proportional to `T_ref`**. The **fast**
   end of row 2's range (24.4 MHz) has ~7× less of it and is therefore the
   binding end for row 16's hysteresis criterion. This is the *opposite* end
   from the one that bound #52's `R·C` criterion, and RECORD-002's
   3.5 MHz-only diagnostic could not see it.
3. **`mos_corner` now reaches the ladder by a second path.** RECORD-002 could
   spot-check it because it only entered through `twin_r`; it now also enters
   through `I_sat(XMPD)`. Hence the fast-end ladder extension described under
   "Coverage".

#### The sizing is a two-sided measured bound

`../testbench/run_xmpd_sizing.sh` sweeps seven candidate geometries —
including the as-drawn `w=2u l=0.5u` — at the two corners that bound the
choice from opposite sides, reporting settled `VWIN` (not just the thresholded
`LOCK` pin) so the two trip points can be interpolated against the *same*
corner's measured Schmitt trip voltages rather than read off a ladder step.

**Lower bound — how strong `XMPD` may be.** `mos_ff`/`res_wcs`/−40 °C at
24.4 MHz: fastest MOS, highest `R`, coldest, shortest window — the corner that
maximises `I_sat·R` and minimises the hysteresis.

| `XMPD` | `L/W` | assert (× window) | de-assert (× window) | **hysteresis (× window)** | vs. row 16's ≥ 0.25× |
|---|---|---|---|---|---|
| `w=2u l=0.5u` (as drawn) | 0.25 | < 1.00 | < 1.00 | **unresolvable** — `VWIN` is already at 39 mV at τ = 1.00× | fails |
| `w=0.5u l=8u` | 16 | 1.068 | 1.209 | 0.141 | fails |
| `w=0.25u l=8u` | 32 | 1.140 | 1.331 | 0.190 | fails |
| `w=0.5u l=16u` | 32 | 1.175 | 1.414 | 0.239 | fails |
| `w=0.35u l=16u` | 45.7 | 1.252 | 1.623 | 0.371 | 1.48× |
| **`w=0.25u l=16u`** (landed) | **64** | **1.332** | **1.828** | **0.495** | **1.98×** |
| `w=0.25u l=32u` | 128 | 1.702 | > 2.50 | > 0.80 | passes |

**Upper bound — how weak `XMPD` may be.** `mos_tt`/`res_bcs`/125 °C at
3.5 MHz: lowest `R`, hottest — the corner whose thresholds sit furthest out.
`twin_r` = 7.959 ns and `T_ref` = 285.7 ns here, so one window is 2.8% of a
reference period and the ladder's own reach is 20× the window = 159 ns = 56%
of `T_ref`.

| `XMPD` | `L/W` | assert (× window) | de-assert (× window) | de-assert as % of `T_ref` |
|---|---|---|---|---|
| `w=2u l=0.5u` (as drawn) | 0.25 | 1.375 | 1.671 | 4.7% |
| `w=0.5u l=8u` | 16 | 3.367 | 6.397 | 17.8% |
| `w=0.25u l=8u` | 32 | 4.730 | 9.498 | 26.5% |
| `w=0.5u l=16u` | 32 | 5.645 | 11.398 | 31.8% |
| `w=0.35u l=16u` | 45.7 | 7.337 | 15.107 | 42.1% |
| **`w=0.25u l=16u`** (landed) | **64** | **8.888** | **18.239** | **50.8%** |
| `w=0.25u l=32u` | 128 | 16.478 | **> 24.0** | **> 66.9%** — off the end of the sweep |

`w=0.25u l=16u` is the only swept geometry that clears both: **1.98× margin on
row 16's hysteresis criterion at the corner that minimises it**, while its
de-assert threshold at the corner that maximises it is still inside one
reference period *and* inside the ladder that measures it. One step stronger
(`w=0.35u l=16u`) drops the margin to 1.48×; one step weaker
(`w=0.25u l=32u`) pushes de-assert past two-thirds of a reference period and
off the end of the ladder.

Two honest notes on that table:

- **The as-drawn `XMPD` row is itself the control that shows Term 1 alone is
  not enough.** Those two rows are computed against the *fixed* Schmitt's trip
  points, i.e. they are "what the as-drawn `XMPD` would give if only
  `schmitt_hv` had been rewired": 0.297× the window at the most favourable
  corner, and **unresolvable at the binding corner**. Rewiring `schmitt_hv`
  without re-sizing `XMPD` would not have passed row 16. This reproduces, by a
  second and independent route, RECORD-002's own "rewiring the Schmitt alone
  changes nothing measurable".
- **`w=0.15u` geometries were explored and deliberately excluded, and that
  exploration is *not* in the committed CSV.** `sg13_hv_nmos`'s own `wmin` is
  0.15 µm, and at that width the discharge current stops scaling with `W`:
  scratch runs at `mos_tt`/`res_typ`/27 °C/24.4 MHz gave 0.36× window for
  `0.25u/8u` (`L/W` = 32) and only 0.41× for `0.15u/8u` (`L/W` = 53) — a 1.7×
  weaker device buying 1.13× more hysteresis, i.e. narrow-width effects are
  already dominant. Those points are stated here as the *reason* the committed
  sweep stops at `w=0.25u`, not as evidence: they were run against a scratch
  variant and are not in `../corners/xmpd_sizing.csv`. The design conclusion —
  do not put a PVT margin claim on a device sitting at the model's
  narrow-width edge — does not depend on their exact values.

#### What the re-size costs, stated rather than hidden

The block's phase-error thresholds move a long way out. Measured on the
committed block at the same MOS/RES/temperature corner
(`mos_tt`/`res_typ`/27 °C), at both ends of the `f_ref` range:

| | 3.5 MHz (`T_ref` = 285.7 ns) | 24.4 MHz (`T_ref` = 41.0 ns) |
|---|---|---|
| `twin_r` | 6.668 ns | 6.668 ns |
| Assert threshold | 5.00× window = 33.3 ns = **11.7% of `T_ref`** | 1.50× window = 10.0 ns = **24.4% of `T_ref`** |
| De-assert threshold | 8.00× window = 53.3 ns = **18.7% of `T_ref`** | 2.25× window = 15.0 ns = **36.6% of `T_ref`** |
| Hysteresis | 3.00× window = 20.0 ns = 7.0% of `T_ref` | 0.75× window = 5.0 ns = 12.2% of `T_ref` |

Expressed **in units of the window** the thresholds vary ~5× across the range,
which looks alarming; expressed as a **fraction of a reference period** —
which is what a phase error actually is — they vary about 2×, because the
`T_ref` proportionality is the topology's own. Both framings are given because
only the second is a statement about the detector's behaviour in a PLL, and
neither is a criterion row 16 states. **Row 16's "assert window" is `twin_r`,
`delaywin_hv`'s own propagation delay, which `XMPD` does not touch at all**
and which is re-measured unchanged below.

The residual — that this topology's lock threshold is `f_ref`-dependent by
construction, because it integrates a per-cycle coincidence pulse against a
continuous pull-up — is **not** something `XMPD` sizing can remove, and it is
filed as its own follow-up rather than absorbed here.

## Results — R/C extraction (`../corners/rc_extract_hystfix.csv`, 15 rows)

| Device | Corner axis | Range | Source |
|---|---|---|---|
| `XRPU` (`rhigh`, `w=0.5u l=700u`) | 3 resistor corners × 3 temperatures | **1.351 MΩ** (`res_bcs`/125 °C) – **3.297 MΩ** (`res_wcs`/−40 °C) | real `r3_cmc` model |
| `XCW` (`cap_cmomi`, `w=40u l=40u m=1`) | temperature only (the model has no temperature or corner term) | **1.691196 pF**, flat | **real `cap_cmomi` OSDI model** (RECORD-002 had to use the closed form) |
| `XDW.XC1` (`cap_cmomi`, `w=40u l=40u m=2`) | temperature only | **3.382393 pF**, flat | **real `cap_cmomi` OSDI model** |

Every one of these 15 rows is **byte-identical to RECORD-002's**, on a
different host, a different ngspice build, and — for the two capacitors — a
different extraction path. `R·C` = **2.285 – 5.576 µs**, i.e. **8.0 – 19.5×**
the slowest reference period (`T_ref` ≤ 286 ns), **6.4 – 23.4×** including the
±20% MOM band. **Issue #52's `R·C` margin is intact and re-measured, not
assumed.**

## Results — comparator window (`../corners/window_hystfix.csv`, 102 rows)

| | Value |
|---|---|
| Full matrix range | **3.688 – 11.24 ns** |
| Nominal (`mos_tt`/`res_typ`/27 °C/3.3 V, `real`) | 6.668 ns |
| Worst case (`mos_ff`/`res_bcs`/−40 °C/**3.63 V**, `ideal−0.20`) | **3.688 ns** = **1.475×** the floor |
| Ported target (row 16) | ≥ 2.5 ns |
| Points below the floor | **0 / 102** |
| `real` vs. `ideal0.00`, same corner | ≤ **0.057%** of `twin_r` across all 21 shared corner bundles |

Identical to RECORD-002's range and worst-case corner, which is the expected
result — neither `XMPD` nor `schmitt_hv` is inside `delaywin_hv` — and it is
measured rather than assumed. **Timestep convergence**
(`../corners/tstep_convergence_hystfix.csv`): `twin_r` at 4 representative
corners at 20 ps / 5 ps / 1.25 ps maximum internal timestep changes by
**≤ 0.034%** end to end.

## Results — phase-error ladder (`../corners/ladder_hystfix.csv`, 21 rows)

Ladder: 21 points per corner, 0.25× window through 1.0–2.5× and then out to
20× (`gen_ladder.py --fracs-set hystfix`). Copy A starts fully **discharged**
(the largest τ at which it still reaches the in-window state is the **assert**
threshold); copy B starts fully **charged** (the largest at which it still
holds it is the **de-assert** threshold). Chatter is judged at the deepest
point, now **20×** the window rather than RECORD-002's 10×, so that it lies
beyond the de-assert threshold at every corner.

| corner (`mos`/`res`/temp, 3.3 V unless noted) | `f_ref` | `twin_r` | assert | de-assert | **hysteresis** | chatter @ 20× |
|---|---|---|---|---|---|---|
| `mos_tt_res_typ_-40c` | 3.5 MHz | 5.855 ns | 4.00× | 7.00× | **3.00× = 300%** | `steady` |
| `mos_tt_res_typ_27c` | 3.5 MHz | 6.668 ns | 5.00× | 8.00× | **3.00× = 300%** | `steady` |
| `mos_tt_res_typ_125c` | 3.5 MHz | 7.959 ns | 7.00× | 12.00× | **5.00× = 500%** | `steady` |
| `mos_tt_res_bcs_-40c` | 3.5 MHz | 5.855 ns | 5.00× | 8.00× | **3.00× = 300%** | `steady` |
| `mos_tt_res_bcs_27c` | 3.5 MHz | 6.668 ns | 6.00× | 12.00× | **6.00× = 600%** | `steady` |
| `mos_tt_res_bcs_125c` | 3.5 MHz | 7.959 ns | 8.00× | 16.00× | **8.00× = 800%** | `steady` |
| `mos_tt_res_wcs_-40c` | 3.5 MHz | 5.855 ns | 3.00× | 6.00× | **3.00× = 300%** | `steady` |
| `mos_tt_res_wcs_27c` | 3.5 MHz | 6.668 ns | 4.00× | 8.00× | **4.00× = 400%** | `steady` |
| `mos_tt_res_wcs_125c` | 3.5 MHz | 7.959 ns | 6.00× | 10.00× | **4.00× = 400%** | `steady` |
| `mos_tt_res_typ_27c` | 24.4 MHz | 6.668 ns | 1.50× | 2.25× | **0.75× = 75%** | `steady` |
| `mos_tt_res_bcs_125c` | 24.4 MHz | 7.959 ns | 2.00× | 3.00× | **1.00× = 100%** | `steady` |
| `mos_tt_res_wcs_-40c` | 24.4 MHz | 5.855 ns | 1.25× | 1.75× | **0.50× = 50%** | `steady` |
| `mos_ff_res_wcs_-40c` | 24.4 MHz | 5.007 ns | 1.25× | 1.75× | **0.50× = 50%** | `steady` |
| `mos_ss_res_bcs_125c` | 24.4 MHz | 9.423 ns | 2.00× | 2.50× | **0.50× = 50%** | `steady` |
| `mos_tt_res_typ_27c/3.63 V` | 24.4 MHz | 6.101 ns | 1.50× | 2.25× | **0.75× = 75%** | `steady` |
| `mos_tt_res_typ_27c/MOM −20%` | 3.5 MHz | 5.384 ns | 6.00× | 10.00× | **4.00× = 400%** | `steady` |
| `mos_tt_res_typ_27c/MOM +20%` | 3.5 MHz | 7.954 ns | 4.00× | 8.00× | **4.00× = 400%** | `steady` |
| `mos_ff_res_typ_27c` | 3.5 MHz | 5.736 ns | 5.00× | 10.00× | **5.00× = 500%** | `steady` |
| `mos_ss_res_typ_27c` | 3.5 MHz | 7.980 ns | 4.00× | 8.00× | **4.00× = 400%** | `steady` |
| `mos_tt_res_typ_27c/2.97 V` | 3.5 MHz | 7.425 ns | 5.00× | 8.00× | **3.00× = 300%** | `steady` |
| `mos_tt_res_typ_27c/3.63 V` | 3.5 MHz | 6.101 ns | 5.00× | 8.00× | **3.00× = 300%** | `steady` |

**Hysteresis: 0 of 21 corners below row 16's ≥ 25% criterion. Worst case 50%
of the window — 2.0× the criterion — at all three of the 24.4 MHz corners that
stress it (`mos_tt`/`res_wcs`/−40 °C, `mos_ff`/`res_wcs`/−40 °C,
`mos_ss`/`res_bcs`/125 °C).** The 3.5 MHz corners are 6–16× the criterion, for
the `T_ref` reason above. The two 24.4 MHz `mos_ff`/`mos_ss` corners are the
ones RECORD-002's coverage reduction would have omitted, and they are exactly
the binding ones — which is why the reduction was reversed.

**Chatter: `steady` at 21/21**, at twice the static phase error RECORD-002
used. No corner reports `chatter` or `intermediate`.

**`trec` (discharged → mid-rail at zero phase error): 1.644 – 4.017 µs**,
against RECORD-002's 1.651 – 4.030 µs. Unchanged, as it must be — recovery is
`XRPU` charging `XCW` and `XMPD` is off.

## Results — supply current, and a real consequence of the fix (row 11)

| | RECORD-002 | **RECORD-003** |
|---|---|---|
| In-lock (`idd_inlock`) | 2.48 – 21.9 µA | **2.47 – 24.2 µA** |
| Out-of-lock (`idd_outlock`, probe at 10× window) | 39.1 – 95.1 µA | **47.0 – 234 µA** |

The in-lock figure is unchanged. **The out-of-lock figure rose up to ~2.5×,
and the cause is measured, not guessed.** `idd_outlock` is taken with one copy
held at a *fixed* 10× window phase error. With the hysteresis restored, 10×
the window is **no longer unambiguously out of window**: at
`mos_tt`/`res_bcs`/27 °C/3.5 MHz this block asserts at 6× and de-asserts at
12×, so the probe sits **inside the hysteresis band**, where `VWIN` settles
between `schmitt_hv`'s two trip points — `../corners/ladder_raw_hystfix.csv`
reads **`VWIN` = 1.483 V** at that point, against measured trip points of
1.14 V and 2.07 V — and the readout conducts crowbar current.

Measured by control, same corner, same deck (`tb_lock_recovery.sp.tmpl`;
reproduce with `TAUBIG_XWIN=20 ./testbench/run.sh`):

| DUT | probe at 10× window | probe at 20× window |
|---|---|---|
| RECORD-002's block (`lock_detector_resized.spice`) | 46.6 µA | 46.7 µA |
| **This block** (`lock_detector_hystfix.spice`) | **233.8 µA** | **57.9 µA** |

The old block's figure does not depend on the probe point because it has
essentially no hysteresis band to land in; the new block's does. At 20× the
window — beyond de-assert at every corner — the new block draws 57.9 µA
against the old block's 46.7 µA, i.e. the *genuinely* out-of-lock current rose
by ~24%, not by 2.5×.

**Row 11's `lock_detector` domain is therefore re-bounded at 2.47 – 234 µA
for this block**, superseding RECORD-002's 2.48–95.1 µA, with the caveat that
the top of that range is a static crowbar condition that only occurs while the
phase error sits inside the hysteresis band. That is a genuine design residual
of restoring the hysteresis — the readout has no output stage and its input is
now *designed* to dwell between the rails — and it is filed as a follow-up
rather than absorbed here.

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 16 — assert window ≥ 2.5 ns**: **bounded, MEETS the criterion.**
  3.688–11.24 ns at 102/102 points including an explicit worst-case stack and
  the −20% MOM band; worst-case margin 1.475×. Re-confirmed against the
  changed block, not carried over.
- **Row 16 — hysteresis ≥ 25% of window**: **bounded, and for the first time
  it MEETS the criterion.** 50–800% of the window at 21/21 corners; worst case
  50%, i.e. 2.0× the criterion, at the 24.4 MHz corners that bind it.
  Supersedes RECORD-001's and RECORD-002's failures for this block.
- **Row 16 — no chatter**: **bounded, MEETS the criterion.** `steady` at 21/21
  at a **20×**-window static phase error (RECORD-002 used 10×), at both ends
  of the DR-005-amended `f_ref` range.
- **Row 16 — static phase offset comparison**: **`insufficient-evidence`**,
  unchanged.
- **Row 16 — `XCW`/`XDW.XC1` MOM-uncertainty sensitivity**: **unchanged from
  RECORD-002** — the ±20% band still moves `twin_r` by ~38% of the nominal
  window and does not change any ladder verdict (both MOM spot checks report
  400% hysteresis and `steady`). The `real`-vs-`ideal0.00` control that
  RECORD-002 could not run is now measured at ≤ 0.057%.
- **Row 11 — power (`lock_detector` domain)**: **re-bounded at 2.47–234 µA**,
  see above; the rise is attributed by control.
- **Row 2 — `f_ref` range**: **not touched, and does not need to be.** One
  fixed sizing meets all three row-16 criteria at both ends of 3.5–24.4 MHz.
  No decision record is owed by this record.

## SG13G2 sibling decision (issue #66 scope item 1)

**Decision: the `schmitt_hv` feedback rewiring is landed on the SG13G2 sibling
`design/schmitt_hv.sch` in this same change. The `XMPD` re-size is not.**

Reasons, in order:

1. **It is a connectivity defect in a cell both PDKs share, not a port
   artifact and not a sizing choice.** The as-drawn cell cannot produce
   hysteresis on either PDK; it is a Schmitt trigger in name only. Leaving a
   known-dead cell in a hierarchy because "that PDK has no campaign yet" makes
   the next SG13G2 campaign start from a circuit this repo already knows is
   wrong.
2. **It is measured on SG13G2, not argued across from SG13CMOS5L.**
   `run_schmitt_rewire.sh` runs the identical deck against
   `design/netlist/lock_detector.spice` on `ihp-sg13g2` — 54 rows — and the
   results are identical field for field to the CMOS5L ones. This satisfies
   this repo's "no claim without a testbench" for the SG13G2 change itself;
   the deck instantiates only `schmitt_hv` and includes no capacitor model,
   which is what makes one file cover both PDKs (SG13G2 has no `cap_cmomi`,
   CMOS5L has no `cap_cmim`).
3. **`design/netlist.sh --check` passes on all six SG13G2 netlists**, so the
   SG13G2 hierarchy stays self-consistent.

Why the `XMPD` re-size is **not** ported: its value is derived from
`I_sat(XMPD)·R(XRPU)/T_ref` using the SG13CMOS5L block's measured `R`
(`rhigh w=0.5u l=700u`, 1.35–3.30 MΩ) and its `cap_cmomi` `C`. **The SG13G2
`lock_detector` still carries the pre-#52 devices** — `XRPU` at `l=6u` and
`XCW` as a 6 µm × 6 µm `cap_cmim` — so `w=0.25u l=16u` would be a number with
no derivation on that PDK, dropped into a block whose `R·C` is still three
orders of magnitude too small (RECORD-001's own finding). The SG13G2
`lock_detector` needs the whole `XRPU`/`XCW`/`XDW.XC1`/`XMPD` re-derivation as
one campaign against SG13G2's own extracted `R` and `C`, which is a separate
PDK campaign with no `sim/` slug today. That is filed as a follow-up, and
`design/README.md` records the divergence explicitly so it cannot be mistaken
for an oversight.

## Tool friction — three ngspice convergence aborts, and what was done about them

Recorded here because this repo's CLAUDE.md asks for tool friction to be
surfaced rather than routed around, and because a solver setting that changes
a committed number would be a serious thing to leave implicit.

Making `XMPD` weak is exactly what makes the block hard to simulate: the
integrating node now **sits at intermediate voltages for the whole run**
instead of railing, which holds `schmitt_hv`'s input in its own high-gain
region and keeps the coincidence gate's nodes near their switching points for
tens of microseconds of simulated time. Three decks aborted outright with
`Timestep too small` and ngspice exit 1 — a whole-campaign abort under
`run.sh`'s `run_ngspice_or_die`:

| # | Corner / point | Node |
|---|---|---|
| 1 | `mos_ff`/`res_wcs`/−40 °C, 24.4 MHz, τ = 1.4× window | `xa.xxor.n1` |
| 2 | `mos_ff`/`res_wcs`/−40 °C, 24.4 MHz, τ = 1.6× window | `xa.wide` |
| 3 | `mos_tt`/`res_wcs`/27 °C, 3.5 MHz, τ = 2.0× window | `xa5.xxor.xn2.mid1` |

Node (3) is worth naming: `mid1` is `nand2_hv`'s own **series-stack internal
node**, which has no DC path to any rail whenever both stacked NMOS are off.
A floating node is exactly what `gmin` exists for, and ngspice's 1e-12 default
is not enough for it over a 16 µs transient.

**Settings landed** (`../testbench/tb_lock_ladder.sp.tmpl`,
`tb_lock_ladder_point.sp.tmpl`, `tb_lock_recovery.sp.tmpl`,
`tb_hyst_diag.sp.tmpl`): `itl4=5000 gmin=1e-11`. Neither is an accuracy
relaxation — `reltol`/`abstol`/`vntol`/`chgtol` are untouched — and both were
measured to be inert where the default already converged:

| Change | Measured effect |
|---|---|
| `itl4` 10 → 500, at already-converging points | 2.41949 → 2.41919 V (0.012%), 1.46963 → 1.46963 V (0.000%) |
| `itl4` 500 → 5000, at failing point (1) | 1.84852 → 1.84980 V (0.07%) |
| adding `gmin=1e-11` on top of `itl4=5000` | 1.84980 → 1.84980 V, 0.444269 → 0.444269 V, 3.15340 → 3.15340 V — **no change to six digits at any point checked** |

`gmin` = 1e-11 S is a 100 GΩ shunt, i.e. ~3 × 10⁴ times weaker than `XRPU`'s
own 1.35–3.30 MΩ pull-up on the one high-impedance node this block cares
about. **Measured and rejected**: `method=gear` cleared (1) but moves the
answer materially (1.849 → 1.733 V) and did not clear (2); `gmin=1e-9`,
`gmin=1e-15` and `reltol=5e-4` cleared nothing extra; `trtol=1` cleared (2)
and (3) but is a truncation-error knob, i.e. a genuine accuracy relaxation.

**`trtol=1` is nevertheless kept as a one-shot, recorded retry** in
`run.sh`/`run_xmpd_sizing.sh`: a 21-corner × 22-deck run is hours long and
"every abort observed" is not "every abort possible". A deck that fails is
retried once with `trtol=1` appended, the retry is announced on stderr, **and
the deck is named in `../corners/solver_retries.txt`**, which is committed
next to the CSVs. An empty file is the claim that no point needed it; a
non-empty one is a list this record has to disclose. A deck that fails the
retry too still aborts the campaign.

`../corners/solver_retries.txt` for this record lists **8 decks** — 5 ladder
points and 3 sizing-sweep points, out of 21 × 22 + 126 ≈ 590 transient decks,
i.e. **1.4%**. Named in full:

```
ladder mos_tt_res_typ_27c_3.3v_3p5MHz_real  (pt.sp)
ladder mos_tt_res_wcs_-40c_3.3v_24p4MHz_real (pt.sp)
ladder mos_ff_res_wcs_-40c_3.3v_24p4MHz_real (pt.sp)   x2
ladder mos_tt_res_typ_27c_3.63v_3p5MHz_real  (pt.sp)
sizing min_hysteresis 0.25u/16u tau=1.60x
sizing min_hysteresis 0.25u/16u tau=2.00x
sizing max_threshold  0.25u/16u tau=14.00x
```

The bias `trtol=1` could introduce is toward *larger* accepted timesteps and
therefore a slightly less-resolved transient; the affected quantity in every
case is a settled average over the last two reference periods of a 32–391-cycle
run, and every one of those decks resolved to an unambiguous rail-level state.
The `mos_tt`/`res_typ`/27 °C/3.5 MHz ladder corner was additionally measured
**twice** across this issue's runs — once with `itl4=5000` alone and once with
`itl4=5000 gmin=1e-11` plus a `trtol=1` retry — and produced **identical**
assert (5.00×), de-assert (8.00×) and hysteresis (3.00×) values both times.

This is a general ngspice/circuit-interaction property (a floating series-stack
node plus a deliberately high-impedance integrator), not an SG13G2 or
klayout-tools deck gap, so it is recorded here rather than filed at
`2AMLogic/klayout-tools` — that tracker is scoped to the layout tool.

## What RECORD-002 could not bound and this record does

RECORD-002 ran on **arm64 macOS**, where `cap_cmomi.osdi` ships as x86-64 ELF
and cannot be loaded at all; its `real` DUT variant was absent and both
`cap_cmomi` instances were ideal linear capacitors at a closed-form nominal.
It listed the consequences under "What this does not bound". This record ran
on **x86-64 Linux**, where the object loads, so `run.sh` restored `real`
automatically — no script change, which is exactly what that fallback was
built for (issue #67).

| RECORD-002 open item | What this record measures |
|---|---|
| The `real` `cap_cmomi` compact model at the new 40 µm × 40 µm geometries | **Measured.** `../corners/rc_extract_hystfix.csv` carries `source=ngspice-osdi` on every capacitor row. `XCW` = **1.691196 pF**, `XDW.XC1` = **3.382393 pF**, flat over −40/27/125 °C |
| Whether `cmomi_nominal.py`'s closed form is right at those geometries | **Confirmed to every printed digit.** The `.va`-transcribed formula gives 1.691196e-12 F and the real OSDI model gives 1.691196e-12 F. RECORD-002's substitution was sound |
| Whether the ideal-cap substitution biases `twin_r` at the new geometries | **Bounded.** `real` vs. `ideal0.00` differ by at most **0.057%** of `twin_r` across the 21 corner bundles they share (RECORD-001 measured 0.0057% at ~60× smaller geometries) |
| `XRPU`'s extracted resistance | **Byte-identical** to RECORD-002's 9 rows on a different host and ngspice build |

Still not bounded, unchanged from RECORD-002: `cap_cmomi`'s RF branches and
substrate shunt are exercised by the `real` variant here but not
*characterised*; random device mismatch has no model in this flow; and
post-layout parasitics are out of scope — see "What this does not bound".

## Coverage, and how it changed (explicit, per `sim/README.md`)

| Axis | RECORD-002 | RECORD-003 | Why |
|---|---|---|---|
| `rc_extract` | 15 rows, capacitors from the closed form | **15 rows, capacitors from the real OSDI model** | this host can load `cap_cmomi` |
| `window` | 81 rows | **102 rows** (same structure + the `real` variant) | same |
| `schmitt` | 45 rows | **45 rows** + **108** before/after rows on **both PDKs** | `schmitt_hv` is one of the two things this issue changes |
| `tstep_convergence` | 12 rows | **12 rows** | unchanged |
| ladder — corners | 18 | **21** (+`mos_ff`/`res_wcs`/−40 °C, +`mos_ss`/`res_bcs`/125 °C, +3.63 V, all at 24.4 MHz) | the fast end is the binding end for hysteresis, and `mos_corner` now reaches the ladder through `I_sat(XMPD)` as well as through `twin_r` |
| ladder — step | 9 points, 0.20× window, reach 2.5× (+ one 10× point) | **21 points, 0.25× window through 1.0–2.5×, reach 20×** | the restored hysteresis separates and displaces both thresholds; a ladder that stops at 2.5× cannot see a de-assert threshold at 16× |
| ladder — chatter probe | 10× window | **20× window** | so the chatter point is beyond de-assert at every corner |
| ladder — MOS corner at 3.5 MHz | 2 spot checks | **2 spot checks** (unchanged) | the slow end has 6–16× margin on the criterion; the fast end is where `mos_corner` matters |
| ladder — MOM band, supply | 2 spot checks each | **2 spot checks each at 3.5 MHz + 1 supply point at 24.4 MHz** | as above |

**Nothing was reduced relative to RECORD-002.** The one methodological
difference to flag is the resume path: the ladder ran as two invocations
(12 corners, then the remaining 9 under `LADDER_RESUME=1`) because the first
run's terminal was killed part-way. Every ladder corner is an independent
ngspice invocation against the same frozen snapshot, the same templates and
the same host, so this is concatenation rather than continuation — but it is
stated here rather than implied, and `LADDER_RESUME` is off by default
precisely so a plain `./run.sh` still means "regenerate one self-consistent
set".

## What this does not bound

- **Random device mismatch.** Unchanged from RECORD-001/002: no per-instance
  mismatch model is exercised for `sg13_hv_nmos`/`sg13_hv_pmos` here, and
  `cap_cmomi` has none at all. This matters more than it did: `XMPD` is now a
  0.25 µm × 16 µm device whose `I_sat` sets the transition width directly, and
  a narrow device's `V_th` spread passes straight into the hysteresis. The
  `mos_ff`/`mos_ss` corners bound the *systematic* skew; within-die random
  mismatch stays open.
- **Post-layout parasitics, and the layout itself.** Schematic level only.
  `VWIN` is a very high-impedance node (1.35–3.30 MΩ pull-up) and is now
  discharged by a device sourcing single-digit microamps, so layout leakage and
  junction leakage at 125 °C — neither modelled here — are a larger fraction of
  the balance than they were for RECORD-002. **The `lock_detector` layout that
  landed in PR #39 predates both #52's and #66's device changes and does not
  implement either.**
- **The `f_ref` dependence of the lock threshold itself.** This record measures
  it and states it; it is a property of the topology (a continuous pull-up
  integrating an event-gated pull-down), not of the sizing, and removing it
  would mean a reference-gated integrator, i.e. a different block. Filed as a
  follow-up.
- **Row 16's "≥ 2× worst static phase offset" half.** Still
  `insufficient-evidence`, unchanged from RECORD-001 and RECORD-002 — it needs
  a PFD/CP static-phase-offset record. `sg13cmos5l-closed-loop-lock`
  RECORD-003/004 have since bounded a static phase error for the *loop*, but
  attribute it to a `cp` current-mirror mismatch that is itself unfixed
  (issue #72), so the number that half of row 16 needs still does not exist.
- **Anything about the SG13G2 `lock_detector` beyond `schmitt_hv`.** Its
  `XRPU`/`XCW`/`XMPD` are still pre-#52 and there is no `sim/` slug for that
  PDK. See "SG13G2 sibling decision".
