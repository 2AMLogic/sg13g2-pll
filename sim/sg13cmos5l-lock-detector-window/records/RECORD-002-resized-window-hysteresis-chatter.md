# RECORD-002: lock-detector window, hysteresis and chatter, **after** the `XRPU`/`XCW`/`XDW.XC1` resize

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #52 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L PVT
  campaign). Supersedes nothing: `RECORD-001` measured the **pre-resize**
  block and stands unedited, with its own frozen netlist snapshot and its own
  unsuffixed `../corners/*.csv`. This record measures the **post-resize**
  block against the same claim.
- **DUT**: `../netlist-snapshots/lock_detector_resized.spice`, frozen from
  `design/sg13cmos5l/netlist/lock_detector.spice` at this record's own branch
  (parent commit `65e2cb6`). It differs from RECORD-001's own snapshot in
  **exactly three instance values** and is byte-identical everywhere else:

  | Instance | RECORD-001 (was) | RECORD-002 (now) | Nominal value |
  |---|---|---|---|
  | `XRPU` (`rhigh`, integrating pull-up) | `w=0.5u l=6u` | `w=0.5u` **`l=700u`** | 1.35–3.30 MΩ (was 11.8–28.6 kΩ) |
  | `XCW` (`cap_cmomi`, integrating node) | `w=8u l=8u m=1` | **`w=40u l=40u`** `m=1` | 1.691 pF (was 59.82 fF) |
  | `XDW.XC1` (`cap_cmomi`, in `delaywin_hv`) | `w=4u l=4u m=2` | **`w=40u l=40u`** `m=2` | 3.382 pF (was 27.29 fF) |

  `XMPD`, `schmitt_hv`, `xor2_hv`, `nand2_hv`, `inv_hv` and the four-inverter
  chain's own drive are **untouched**. That matters for reading the
  hysteresis result below.
- **Claim under test**: `spec/porting-plan.md` row 16 (assert window ≥ 2.5 ns
  / ≥ 2× worst static phase offset, hysteresis ≥ 25% of window, no chatter),
  plus row 11's `lock_detector` power domain. Same claim RECORD-001 measured;
  this record re-measures it against the resized block.
- **Reference range**: `spec/porting-plan.md` row 2 **as amended by DR-005**
  (merged in PR #46) — `f_ref` ≈ **3.5–24.4 MHz**, i.e. `T_ref` ≈ 41–286 ns.
  RECORD-001 was written against the pre-DR-005 1–25 MHz text and its
  "1000 ns worst case" figure is stale; every margin below is re-derived
  against 286 ns, the amended range's own slowest period. **No spec row was
  relaxed to make anything here pass** — the sizing was moved to meet row 16,
  not the other way round, and row 2 is used exactly as DR-005 left it.
- **Tooling**: `ngspice-47`, installed `~/share/pdk/ihp-sg13cmos5l`,
  **arm64 macOS** host (RECORD-001 ran on x86-64 Linux / `ngspice-46` — see
  "Host limitation" below, which is the one methodological difference between
  the two records). `set num_threads=1` (see `../testbench/run.sh`'s tooling
  note). The version is `47`, not `46`: `ngspice-46` was never installed on
  this host, and the re-run under "Re-verification after the rebase onto
  `main`" below reproduces every non-ladder CSV byte-for-byte under
  `ngspice-47`, which is what actually produced the committed data.
- **Reproduce**:
  `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh` writes
  `../corners/rc_extract_resized.csv` (15 rows),
  `../corners/window_resized.csv` (81), `../corners/schmitt_resized.csv`
  (45), `../corners/ladder_resized.csv` (18),
  `../corners/ladder_raw_resized.csv` (162),
  `../corners/tstep_convergence_resized.csv` (12).
  `PDK_ROOT=... PDK=... ./testbench/run_hysteresis_diag.sh` writes
  `../corners/hysteresis_diag.csv` (30) and
  `../corners/hysteresis_diag_schmitt.csv` (18).
  Run time on this host: ~2 h for `run.sh` (dominated by the three 24.4 MHz
  ladder corners, which need ~390 reference periods each to settle a
  microsecond-scale `R·C`), ~12 min for the diagnostic.

## Headline result

**Two of row 16's three measurable criteria now pass at every corner
re-measured; the third still fails, and this record identifies why — the
cause is outside the three devices issue #52 resized.**

| Row 16 criterion | RECORD-001 (pre-resize) | RECORD-002 (post-resize) | Verdict |
|---|---|---|---|
| Assert window ≥ 2.5 ns | 0.219–0.409 ns, **6–11× short** at 92/92 points | **3.688–11.24 ns**, 0 of 81 points below the floor, worst case **1.475×** margin | **now met** |
| No chatter | **chatter at 92/92** points, including at a 10×-window static phase error | **`steady` at 18/18** ladder corners at the same 10×-window point | **now met** |
| Hysteresis ≥ 25% of window | 0 resolvable at a 0.15×-window step, 0/92 | 0 resolvable at a 0.20×-window step, **0/18** | **still fails** |
| Assert window ≥ 2× worst static phase offset | `insufficient-evidence` | `insufficient-evidence` (unchanged — still needs a PFD/CP static-phase-offset record that does not exist) | unchanged |

The hysteresis failure is **not** a residual of under-sizing `XRPU`/`XCW`/
`XDW.XC1`, and pushing those three further will not close it. Two separate
controls, both measured here, show why (see "Why the hysteresis criterion
still fails" below): `schmitt_hv`'s feedback devices are tied to the wrong
rails, and — more fundamentally — the settled-`VWIN`-vs-phase-error
characteristic is a near-step, so **no** Schmitt hysteresis, however large,
can map onto a ≥25%-of-window *phase-error* width at the present
`XRPU`/`XMPD` strength ratio.

## Host limitation — `cap_cmomi` could not be simulated on this host

This is stated up front because it changes which DUT variant is the primary
one, and RECORD-001's own primary (`real`) is **not** available here.

`$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/` holds six OSDI objects.
Four (`psp103`, `psp103_nqs`, `mosvar`, `r3_cmc`) are gitignored build
products symlinked from the sibling `ihp-sg13g2` tree and are rebuilt for
whatever host the PDK is installed on — they are arm64 Mach-O here and load
correctly, so **every MOS device and the `rhigh` resistor in this record are
real compact-model simulations**. The two MoM-capacitor objects
(`cap_cmomi`, `cap_cmomf`) are instead *tracked files shipped prebuilt*
(`$PDK_ROOT/ihp-sg13cmos5l/Makefile`'s own `test-gnucap` guard says so
explicitly: *"unlike the OSDI above these two are tracked files, so a pull is
the fix rather than a build"*), and the shipped binaries are **x86-64 ELF**.
On arm64 ngspice reports `slice is not valid mach-o file` and every
`cap_cmomi` instance then fails with `Unable to find definition of model
xcap:cap_cmomi_mod`. Rebuilding needs `openvaf`/`openvaf-r`, which has no
arm64-macOS release binary (checked: the one Homebrew tap that packages it
points at a release asset that 404s, and no upstream release carries an
arm64-macOS artifact).

Consequences, all of which are recorded rather than worked around:

1. **The `real` DUT variant is absent from this record.** `../testbench/run.sh`
   calls the repo's shared OSDI preflight `../../tools/check-osdi-arch.sh`
   (issue #59) at start-up, and when that preflight reports `cap_cmomi` as the
   only unloadable object it drops `real` and promotes `ideal0.00` — the *same*
   ideal-linear-cap substitution `../testbench/mom_inject.py` has always built
   — to primary. On a host where `cap_cmomi` loads, the identical script
   restores `real` automatically; nothing about this is baked into the
   committed testbench.

   The preflight's **default is a hard abort**, and that default is unchanged
   for every other campaign and for every other object here: `psp103`,
   `psp103_nqs`, `mosvar` and `r3_cmc` still abort the run, because there is no
   substitute for a MOS or `rhigh` model and a campaign without them would be
   meaningless. This campaign declares exactly one object soft
   (`--soft cap_cmomi.osdi`, issue #52) because it is the one object for which
   a *validated* substitute exists (item 3 below) and for which every derived
   number is attributed in the committed CSV rather than only in prose. The
   preflight still names the object, still prints its rebuild command, and
   exits `3` with the object's basename on stdout — `run.sh` asserts that the
   soft-unloadable set is exactly `cap_cmomi.osdi` before taking the fallback
   branch, so a future `--soft` addition cannot silently reroute it. See
   `../../PORTING-osdi-host-arch.md` § "`--soft`".
2. **The substitution is not a new assumption; RECORD-001 bounded it.** That
   record's own `real` vs. `ideal0.00` cross-check found `twin_r` differing by
   at most **0.0057%** across all 21 corner bundles, and its chatter /
   no-hysteresis verdict identical across all four DUT variants at all 92
   points. What the ideal element drops is `cap_cmomi`'s RF branches and its
   substrate shunt, neither of which is engaged at the sub-GHz rates here.
3. **The nominal capacitance is computed from the model's own closed form,
   not guessed.** `../testbench/cmomi_nominal.py` transcribes `cap_cmomi.va`'s
   low-frequency `Cmain` expression term for term
   (`density[N]·active_area + Cfeed`, with the unit-cell tiling and pad-length
   rules the model uses) and **self-tests against the two geometries
   RECORD-001 measured on the real OSDI model**: 59.818 fF vs. 59.82 fF
   measured (0.004%) and 27.286 fF vs. 27.29 fF measured (0.014%).
   `run.sh` runs that selftest before using any value from it, and
   `rc_extract_resized.csv` carries a `source` column recording
   `va-formula` (this run) vs. `ngspice-osdi` (a host where the model loads).
4. **The RF/substrate-shunt terms of `cap_cmomi` are therefore not exercised
   at the new, much larger geometries.** That is a real gap in this record and
   is listed under "What this does not bound".

This is a host/PDK-packaging defect, not a circuit finding, and it is filed
separately rather than being absorbed into this issue's scope.

## Re-verification after the rebase onto `main`

Between this record's campaign and this branch's merge, `main` merged #58, #62
and #65, which rewrote the same `../testbench/run.sh` this record runs:
`@PDK_ROOT@`/`@PDK@` template substitution, a hard-failing `run_ngspice_or_die`
wrapper, and the `../../tools/check-osdi-arch.sh` OSDI preflight described
under "Host limitation". Reconciling those with this campaign's own `--soft`
fallback changed the script, so the numbers below were **re-measured under the
reconciled script on this same host**, not assumed to carry over. `ngspice-47`,
`~/share/pdk`, `PDK=ihp-sg13cmos5l`, arm64 macOS.

| Re-run | Result |
|---|---|
| `rc_extract_resized.csv` (15 rows) | **byte-identical** |
| `window_resized.csv` (81 rows) | **byte-identical** — including the 3.688 ns worst-case point and the 11.24 ns maximum |
| `schmitt_resized.csv` (45 rows) | **byte-identical** |
| `tstep_convergence_resized.csv` (12 rows) | **byte-identical** |
| `ladder_resized.csv` — 4 of 18 corners re-run | **byte-identical**, including both `R·C/T_ref` extremes (`res_bcs`/125 °C = 7.999×, `res_wcs`/−40 °C = 19.516×), the nominal 3.5 MHz corner (13.419×) and the 24.4 MHz fast-end corner (93.547×, 375 reference periods). `chatter` = `steady` at all four |
| `ladder_raw_resized.csv` — the same 4 corners (36 of 162 rows) | **byte-identical** |

The four ladder corners were chosen as a runtime-bounded subset rather than a
full 18-corner re-run (the fast-end corner alone is ~20 min); they cover both
ends of the amended `f_ref` range and both ends of the measured `R·C/T_ref`
spread, which are the two axes the reconciliation could plausibly have
disturbed. The remaining 14 corners were not re-simulated and are carried
forward from the original campaign — stated here rather than implied.

Two mechanical notes, neither of which moves a number:

- `csv.writer`'s default `\r\n` line terminator means a freshly generated
  `ladder_raw_resized.csv` carries CRLF, which this repo's
  `core.autocrlf=input` normalises to LF on `git add`. The comparison above is
  after that normalisation; the field values are identical byte for byte.
- On a host where `cap_cmomi.osdi` cannot load, `run.sh` now omits its `osdi`
  line from the generated `.spiceinit` entirely instead of asking ngspice to
  dlopen an object the preflight has just established is unloadable. That is
  required for `run_ngspice_or_die` to be usable at all here, and it is
  numerically inert: the model was never available to those decks either way.

## Results — R/C extraction (`../corners/rc_extract_resized.csv`)

| Device | Corner axis | Range |
|---|---|---|
| `XRPU` (`rhigh`, `w=0.5u l=700u`) | `res_bcs`/`res_typ`/`res_wcs` × −40/27/125 °C | **1.351 MΩ** (`res_bcs`/125 °C) – **3.297 MΩ** (`res_wcs`/−40 °C) — measured, real `r3_cmc` model |
| `XCW` (`cap_cmomi`, `w=40u l=40u m=1`) | temperature only (model has no temperature or corner term) | 1.6912 pF, flat |
| `XDW.XC1` (`cap_cmomi`, `w=40u l=40u m=2`) | temperature only | 3.3824 pF, flat |

**`R·C` at the integrating node**: **2.285 µs** (`res_bcs`/125 °C, fastest) –
**5.576 µs** (`res_wcs`/−40 °C, slowest); **1.828 – 6.691 µs** once the ±20%
MOM-model-uncertainty band on `XCW` is included.

Against row 2's DR-005-amended reference range:

| | `T_ref` | `R·C / T_ref`, nominal | `R·C / T_ref`, incl. ±20% MOM band |
|---|---|---|---|
| `f_ref` = 3.5 MHz (**binding**, slowest reference) | 285.7 ns | **8.0 – 19.5×** | **6.4 – 23.4×** |
| `f_ref` = 24.4 MHz (fastest reference) | 41.0 ns | 55.8 – 136× | 44.6 – 163× |

RECORD-001 measured the same quantity at **0.708–1.713 ns**, i.e. 23–1412×
*below* `T_ref`. The resize moves it from ~1/300 of a reference period to
~10 reference periods at the binding end — the sign of the inequality
`R·C ≫ T_ref` that the topology requires is now correct at every
resistor-corner × temperature × MOM-band point, with the **worst case (6.4×,
`res_bcs`/125 °C at the −20% MOM band) still comfortably above 1**.

**Is one fixed sizing enough for the whole amended `f_ref` range?** — **Yes,
and it is measured rather than argued.** This was the open design question
issue #52 asked to be surfaced either way. The requirement is one-sided
(`R·C` must *exceed* `T_ref` by a healthy factor), and `T_ref` only shrinks
as `f_ref` rises, so a sizing that clears the slowest reference clears the
whole range by construction; the fast end is 7× *further* clear, not closer.
The ladder was run at both ends of the range to confirm the behaviour, not
only the ratio, and both ends give the same verdicts (below). **Row 2 does
not need to narrow, and this record does not propose narrowing it** — no
decision record is owed here.

## Results — comparator window (`../corners/window_resized.csv`, 81 rows)

`twin_r`, the `delaywin_hv` chain's low→high propagation delay measured on a
bare `delaywin_hv` with an ideal step in — the quantity row 16's "assert
window" applies to:

| | Value |
|---|---|
| Full matrix range | **3.688 – 11.24 ns** |
| Nominal (`mos_tt`/`res_typ`/27 °C/3.3 V, `ideal0.00`) | 6.669 ns |
| Worst case (`mos_ff`/`res_bcs`/−40 °C/**3.63 V**, `ideal−0.20`) | **3.688 ns** = **1.475×** the floor |
| Ported target (row 16) | ≥ 2.5 ns |
| Points below the floor | **0 / 81** |
| RECORD-001, same measurement, pre-resize | 0.219 – 0.409 ns (6–11× short at 92/92) |

**Worst-case stacking is in the matrix, not interpolated.** RECORD-001's grid
held the supply at nominal while sweeping the MOM band, and held the MOS/RES
bundle at typ while sweeping supply, so the corner that actually minimises
`twin_r` — every fast-direction axis at once — was in neither sub-sweep. A
floor is a worst-case claim, so `run.sh` now includes an explicit worst-case
stack (`mos_ff`/`res_bcs`/−40 °C/3.63 V at the −20% MOM band). That point
*is* the 3.688 ns minimum above; without it the matrix would have reported a
1.62× margin instead of the true 1.475×.

**The MOM band is now the dominant uncertainty on the window, which it was
not before.** A ±20% band on `XDW.XC1` moves `twin_r` peak-to-peak by
**38.4–38.7% of the nominal window** across all 21 corner bundles, against
7.0–8.2% in RECORD-001. That is the expected consequence of the fix, not a
regression: the pre-resize window was dominated by the four inverters' own
intrinsic delay (27 fF of load barely mattered), whereas the post-resize
window is deliberately load-dominated (3.38 pF), so the load's uncertainty
now passes through nearly one-for-one. The 1.475× worst-case margin above
**already includes** the low edge of that band; a MOM band wider than about
±47% would be needed to reach the floor.

**Timestep-convergence check**
(`../corners/tstep_convergence_resized.csv`): `twin_r` at 4 representative
corners at 20 ps / 5 ps / 1.25 ps maximum internal timestep changes by
**≤ 0.034%** end to end. `twin_r` is not a discretisation artifact.

## Results — phase-error ladder: assert / de-assert / chatter (`../corners/ladder_resized.csv`, 18 rows)

Ladder methodology is RECORD-001's, with two stated changes (both in
`../corners/matrix.md`): 9 ladder points at a **0.20×-window** step instead
of 14 at 0.15×, and 18 corner points instead of 92. Both reductions are
runtime-driven and both are quantified in "Coverage, and how it was reduced"
below.

| Metric | RECORD-002 (18 points) | RECORD-001 (92 points) |
|---|---|---|
| **Chatter verdict at the deepest (10×-window) phase error** | **`steady` at 18/18** | `chatter` at 92/92 |
| **Resolvable hysteresis** | **0/18** — assert and de-assert land on the same ladder point at every corner | 0/92 |
| Assert / de-assert threshold | 0.50× window (7/18) or 1.00× window (11/18) | 1.15× (88/92) or 1.30× (4/92) |
| In-window `LOCK` rail (read from the block, not assumed) | `lo` at 18/18 | `lo` at 92/92 |
| Recovery time `trec` (discharged → mid-rail, zero phase error) | **1.651 – 4.030 µs** | 0.70 – 2.19 ns |
| Supply current, in-lock (`idd_inlock`) | 2.48 – 21.9 µA | 0.79 – 23.2 µA |
| Supply current, out-of-lock (`idd_outlock`) | **39.1 – 95.1 µA** | 2.0 – 60.3 µA |
| Settling fraction achieved within the run (`settle_frac`) | 0.943 – 0.983 | n/a (RECORD-001 ran 4 reference periods total) |

**Reading the chatter result.** `steady` here means the `LOCK` pin sat at one
rail across the whole settle window (the last two reference periods of a
41–391-cycle transient) at a 10×-window static phase error — exactly the
condition RECORD-001 found the block toggling through at every point it
swept. The mechanism is the one RECORD-001 predicted would follow from
fixing `R·C`: `VWIN` no longer re-settles to its rail between error pulses,
so the readout is no longer being driven across its trip point once per
reference cycle.

**`trec` is now three orders of magnitude longer, and that is the point.**
1.65–4.03 µs is 6–14 reference periods at 3.5 MHz (40–98 at 24.4 MHz), i.e.
the block now averages the coincidence gate over many cycles instead of
following it. RECORD-001's 0.70–2.19 ns was the measured symptom of the
defect this issue fixes.

**Out-of-lock supply current rose ~1.6× at the top of its range** (60.3 →
95.1 µA), the direct cost of switching 3.38 pF at `delaywin_hv`'s output
every reference cycle. The in-lock range is comparable at the top
(21.9 µA vs. 23.2 µA) and about 3× higher at the bottom (2.48 µA vs.
0.79 µA); this record does not attribute that low-end shift to a mechanism,
because the in-lock corner set is not the same one RECORD-001 swept (18
points vs. 92) and no measurement here isolates it. Recorded rather than
glossed:
row 11's `lock_detector` domain is re-bounded at **2.48–95.1 µA** by this
record, superseding RECORD-001's 0.79–60.3 µA for the resized block.

**Threshold behaviour at exactly `tau = 1.0× twin_r`.** At 4 of the 18
corners the discharged-start copy sits at an intermediate level (`TOG`) at
that one ladder point, rather than at either rail. That is the block sitting
*on* its own threshold, which is where an intermediate level is the correct
answer; every other ladder point at every corner resolves to a rail. It is
recorded here rather than rounded away because `TOG` and `chatter` are
different failures and `gen_ladder.py` deliberately keeps them apart.

## Why the hysteresis criterion still fails — two measured controls

`../testbench/run_hysteresis_diag.sh` exists to answer this with
measurements rather than an argument. In this topology the phase-error
hysteresis row 16 asks for is the product of two independent quantities:

```
H_tau  ≈  H_volts(schmitt_hv)  /  |dVWIN/dtau|
```

so it is zero if *either* term is degenerate. Both were measured, at
`mos_tt`/`res_typ`/27 °C/3.3 V/3.5 MHz.

### Term 1 — `schmitt_hv`'s own hysteresis is ~1 mV, and the netlist says why

`../corners/schmitt_resized.csv` (45 rows, the full MOS × temperature ×
supply grid) reproduces RECORD-001 exactly, as it must — `schmitt_hv` is
untouched by this issue:

| | Range |
|---|---|
| `V_TH,rising` | 1.255 – 1.764 V |
| `V_TH,falling` | 1.254 – 1.763 V |
| Hysteresis | **0.88 – 1.58 mV** (0.025 – 0.053% of `VDD`) |

A six-transistor CMOS Schmitt trigger gets its hysteresis from two *feedback*
devices that pull the internal stack nodes toward the **opposite** rail from
their series stack. In the committed `schmitt_hv` both feedback devices are
tied to the **same** rail as their stack:

```
XMP3 np  OUT VDD VDD sg13_hv_pmos     <-- drain np, source VDD  (same rail as XMP1/XMP2's stack)
XMN3 nn  OUT VSS VSS sg13_hv_nmos     <-- drain nn, source VSS  (same rail as XMN1/XMN2's stack)
```

`../corners/hysteresis_diag_schmitt.csv` measures the block as drawn against
a **scratch control** in which only those two lines are changed to the
classic connection (`XMP3 VSS OUT np VDD`, `XMN3 VDD OUT nn VSS`), across
3 MOS corners × 3 temperatures:

| DUT | Hysteresis, 9 corner points |
|---|---|
| as drawn | **0.89 – 1.55 mV** (0.027 – 0.047% of `VDD`) |
| feedback rewired (control only, **not landed**) | **881 – 979 mV** (26.7 – 29.7% of `VDD`) |

That is a ~600× difference from two net connections, and it is a real defect
in the drawn cell — **but it is not the binding term**, as the next control
shows.

### Term 2 — `dVWIN/dtau` is a near-step, and *that* is the binding term

`../corners/hysteresis_diag.csv` sweeps the phase error finely across the
transition and reports the **settled integrating-node voltage** (not just
the thresholded `LOCK` pin), for three DUTs. `twin_r` = 6.669 ns at this
corner; `VWIN` is the discharged-start copy's settled average:

| `tau` / `twin_r` | as drawn | schmitt feedback rewired | XMPD weakened (64× `Ron`, `R·C` unchanged) |
|---|---|---|---|
| 0.60× | 3.227 V | 3.226 V | 3.227 V |
| 0.80× | 3.227 V | 3.226 V | 3.227 V |
| 0.95× | 3.227 V | 3.226 V | 3.227 V |
| 1.00× | 3.096 V | 3.095 V | 3.226 V |
| **1.05×** | **0.328 V** | **0.328 V** | 3.094 V |
| 1.10× | 0.290 V | 0.290 V | 3.040 V |
| 1.20× | 0.266 V | 0.266 V | 3.011 V |
| 1.40× | 0.183 V | 0.183 V | 2.899 V |
| 1.80× | 0.115 V | 0.115 V | 2.491 V |
| 2.50× | 0.105 V | 0.105 V | 1.834 V |

Three things are measured here:

1. **The as-drawn transition is ≤ 0.05× the window wide.** `VWIN` goes from
   3.10 V to 0.33 V between `tau` = 1.00× and 1.05× `twin_r`. Row 16 asks for
   a hysteresis of ≥ 0.25× the window. Even a *rail-to-rail* Schmitt
   hysteresis could only spread the two trip points across the phase-error
   interval over which `VWIN` actually moves — which is **five times too
   narrow**. This is a hard upper bound on `H_tau` for the block as drawn,
   and it is independent of `schmitt_hv` entirely.
2. **Rewiring `schmitt_hv` changes nothing about it.** The rewired column is
   the as-drawn column to three digits, and `LOCK` flips between the same two
   ladder points. Restoring 930 mV of *voltage* hysteresis buys ~0 *phase-error*
   hysteresis, because there is no phase-error interval for it to land in.
   **Fixing `schmitt_hv` alone would not make row 16's hysteresis criterion
   pass.**
3. **Weakening `XMPD` — at completely unchanged `XRPU`, `XCW` and `R·C` — is
   what widens the transition.** With `XMPD` at `w=0.5u l=8u` instead of
   `w=2u l=0.5u` (~64× its on-resistance), `VWIN` moves gradually across
   *more than 1.5× the window* instead of jumping inside 0.05×. This
   identifies the mechanism by control rather than by algebra: the settled
   `VWIN` is set by the balance between `XRPU`'s charge over one reference
   period and `XMPD`'s discharge over one `WIDE` pulse, so it is the
   **`XRPU`/`XMPD` strength ratio** — not `R·C`, and not `schmitt_hv` — that
   sets how wide, in phase error, the transition is.

**Why this is not something issue #52 could have fixed by sizing `XRPU`/`XCW`
differently.** The two requirements pull the same ratio in opposite
directions. `R·C ≫ T_ref` (the chatter fix) wants `R` large. A transition
wide enough to hold ≥ 25% of a window of hysteresis wants `R/R_on(XMPD)`
*small* — of order `T_ref/twin_r` ≈ 43 rather than the ~10³ it is now.
Holding `R·C` while cutting `R` by ~10³ means growing `XCW` by ~10³, i.e.
from 1.7 pF to nanofarads of MOM array, which is not a sizing choice, it is a
different block. The tractable knob is `XMPD` (measured above), possibly with
`schmitt_hv` fixed alongside it so the restored transition width has voltage
hysteresis to sit in. **That is a design change to devices this issue does not
scope, needing its own re-verification, and it is filed as a follow-up rather
than smuggled in here.**

## Coverage, and how it was reduced (explicit, per `sim/README.md`)

RECORD-001's ladder ran 92 corner points, each a single ngspice transient
containing 31 `lock_detector` copies over 4 reference periods. That is not
reachable for the resized block, and the reason is the fix itself: an
integrator whose `R·C` is ~10 reference periods needs a transient tens to
hundreds of reference periods long before anything has settled. Measured
directly at `mos_tt`/`res_typ`/27 °C/3.3 V/3.5 MHz with a 54-cycle `tstop`:
the merged 21-copy deck **did not complete in 400 s**, while the same corner
run as 1 recovery deck + 9 independent 2-copy ladder-point decks completed in
about **200 s**. (Per-timestep cost does not scale linearly with copy count:
every copy's independently-timed pulse edges are breakpoints shared by the
whole transient's adaptive step control.) `../testbench/run.sh` therefore
splits each corner into independent invocations and reduces the matrix:

| Axis | RECORD-001 | RECORD-002 | Why the reduction is defensible |
|---|---|---|---|
| `rc_extract` | full | **full** (15 rows) | cheap |
| `window` | 92 rows | **81 rows, full density + a worst-case stack RECORD-001 lacked** | cheap; this is the row-16 floor's own evidence |
| `schmitt` | 45 rows | **full** (45 rows) | cheap; `schmitt_hv` untouched |
| `tstep_convergence` | 12 rows | **full** (12 rows) | cheap |
| ladder — MOS corner | 5 corners in the main grid | `mos_tt` grid + `mos_ff`/`mos_ss` spot checks | `R` and `C` — the quantities this fix moves — have **no** `mos_corner` dependence. `mos_corner` reaches the ladder only through `twin_r`, which `window_resized.csv` still measures at full density |
| ladder — RES corner × temperature | full 3 × 3 | **full 3 × 3** at 3.5 MHz | this is the axis `R·C` actually depends on, so it is not reduced at the binding reference frequency |
| ladder — reference frequency | 25 MHz grid + 1/5 MHz sub-axis | **3.5 MHz (full res×temp grid) + 24.4 MHz (3 points: typ and both `R·C` extremes)** | both ends of the DR-005-amended range are covered; the slow end is the binding one and keeps the full grid. A 24.4 MHz point costs ~7× a 3.5 MHz point (7× the reference periods for the same absolute `tstop`) |
| ladder — MOM band | swept in the main grid | 2 spot checks (±20%) at typ | window carries the band at full density; the ladder verdicts are rail-level and the band moves `R·C` by ±20%, well inside the 6.4× worst-case margin |
| ladder — supply | 6 points | 2 spot checks (2.97 / 3.63 V) | same |
| ladder — ladder step | 0.15× window, 14 points | **0.20× window, 9 points** | still strictly **below** row 16's own 25%-of-window criterion, so a hysteresis that met the criterion would have to resolve at this step. The resulting bound is correspondingly weaker: **< 20% of window** here vs. < 15% in RECORD-001 |
| ladder — total | 92 corner points | **18 corner points** | |

**What the reduction costs, stated plainly**: the hysteresis bound is weaker
(< 20% of window, vs. < 15% in RECORD-001), and the ladder's `mos_corner`,
MOM-band and supply axes are spot-checked rather than swept. It costs nothing
on the window criterion (full density, plus a worst-case point RECORD-001 did
not have) or on the `R·C` claim (full resistor × temperature grid at the
binding reference frequency). The `settle_frac` column records, per corner,
how far the integrating node actually got (0.943–0.983) rather than assuming
the runs were asymptotically settled.

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 16 — assert window ≥ 2.5 ns**: **bounded, and the bound now MEETS the
  criterion.** 3.688–11.24 ns at 81/81 points including an explicit
  worst-case stack and the −20% MOM band; worst-case margin 1.475×.
  Supersedes RECORD-001's failure for the resized block.
- **Row 16 — no chatter**: **bounded, and the bound now MEETS the criterion.**
  `steady` at 18/18 ladder corners at a 10×-window static phase error, at
  both ends of the DR-005-amended `f_ref` range. Supersedes RECORD-001's
  92/92 chatter for the resized block.
- **Row 16 — hysteresis ≥ 25% of window**: **bounded, and the bound is still a
  failure.** 0 resolvable at a 0.20×-window step at 18/18 corners, so
  hysteresis is confirmed < 20% of the window against a ≥ 25% target. Unlike
  RECORD-001, the cause is now separated into two measured terms:
  `schmitt_hv`'s 0.9–1.6 mV of voltage hysteresis (a two-net wiring defect —
  the classic connection measures 881–979 mV) and, binding over it, a
  settled-`VWIN`-vs-phase-error transition ≤ 0.05× the window wide set by the
  `XRPU`/`XMPD` strength ratio. **Neither is fixable by resizing `XRPU`,
  `XCW` or `XDW.XC1`**, which is this issue's whole scope; both are filed as
  a follow-up.
- **Row 16 — static phase offset comparison**: **`insufficient-evidence`**,
  unchanged from RECORD-001 — still needs a PFD/CP static-phase-offset record
  that does not exist. (`sg13cmos5l-closed-loop-lock` RECORD-002 has since
  found a separate `pfd` self-reset parity defect, issue #56, which has to
  land before that number can be trusted.)
- **Row 16 — `XCW`/`XDW.XC1` MOM-uncertainty sensitivity**: **bounded, and the
  answer changed.** The ±20% band now moves `twin_r` by **38.4–38.7%** of the
  nominal window (RECORD-001: 7.0–8.2%), because the window is now
  deliberately load-dominated. The band is inside the window criterion's
  1.475× worst-case margin and does not change any ladder verdict, but it is
  no longer a negligible term and future window claims must carry it.
- **Row 11 — power (`lock_detector` domain)**: **re-bounded for the resized
  block.** In-lock 2.48–21.9 µA, out-of-lock 39.1–95.1 µA (RECORD-001,
  pre-resize: 0.79–23.2 / 2.0–60.3 µA). The out-of-lock rise is the switching
  cost of the enlarged `XDW.XC1`.
- **Row 2 — `f_ref` range**: **not touched, and does not need to be.** One
  fixed sizing covers 3.5–24.4 MHz with 6.4× worst-case margin at the binding
  slow end (see the R/C section). No decision record is owed by this record.

## What this does not bound

- **The `real` `cap_cmomi` compact model at the new geometries.** See "Host
  limitation". Every MOS and `rhigh` result here is a real compact-model
  simulation; both `cap_cmomi` instances are ideal linear caps at the model's
  own closed-form nominal value, a substitution RECORD-001 measured at
  ≤ 0.0057% on this same quantity but at ~60× smaller geometries. Re-running
  `./testbench/run.sh` unchanged on a host where `cap_cmomi.osdi` loads
  restores the `real` variant automatically and would close this (issue #67).
- **`cap_cmomi`'s RF branches and substrate shunt at 1.7 pF / 3.4 pF.** The
  ideal substitution drops them. The model's own header warns that the
  two-sided feed inductance self-resonates in-band for large `feed=double`
  devices (`l ≈ 60 µm ⇒ ~30 GHz`); at 40 × 40 µm and sub-GHz operation that
  is far away, but it is not measured here.
- **Random device mismatch.** Unchanged from RECORD-001: no per-instance
  mismatch model exists for `sg13_hv_nmos`/`sg13_hv_pmos` in this flow, and
  `cap_cmomi` has none at all.
- **Post-layout parasitics, and the layout itself.** `VWIN` is now a
  *far* higher-impedance node than it was (1.35–3.30 MΩ pull-up instead of
  11.8–28.6 kΩ), which makes it correspondingly more sensitive to layout
  leakage and coupling than RECORD-001's version was — junction leakage at
  125 °C in particular is not modelled here and is not negligible against a
  ~1 µA pull-up current. **The `lock_detector` layout that landed in PR #39
  predates this resize and does not implement it** (a 700 µm `rhigh` strip
  needs snaking; `XCW` grows 64 → 1600 µm² and `XDW.XC1` 2 × 16 → 2 × 1600 µm²).
  Re-drawing it and extracting it is not in this issue's scope.
- **The hysteresis fix.** This record measures and attributes the remaining
  failure; it does not implement it. Changing `XMPD` and/or `schmitt_hv` is a
  design change to devices outside issue #52's stated scope
  (`XRPU`/`XCW`/`XDW.XC1`), and is filed as its own follow-up — the same
  discipline RECORD-001 used when it filed this issue rather than resizing
  inside a measurement-only scope.
- **Anything about SG13G2 (the non-CMOS5L sibling).** Untouched. Note only
  that `design/netlist/lock_detector.spice` carries the *identical*
  `schmitt_hv` wiring, so the Term-1 defect above is not CMOS5L-specific —
  which is one more reason it belongs in its own issue rather than in this
  one.
