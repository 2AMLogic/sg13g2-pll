# RECORD-001: `vco` output duty cycle and average supply current (PVT-cornered)

- **Slug**: `sg13cmos5l-vco-duty-cycle`
- **Issue**: #27 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L
  closed-loop PVT campaign)
- **DUT**: `vco` (SG13CMOS5L port, PR #26) — the full block, open-loop, from
  `../netlist-snapshots/vco.spice` (frozen at commit
  `db5ec6afaf79a04aeb13b9a43a4b5905472ff37a`; byte-identical to the copy the
  `sg13cmos5l-vco-kvco-table` record froze, verified by diff).
- **Claim under test**: `spec/porting-plan.md` row 13 (output duty cycle,
  45–55%). Secondary: a real measured input to row 11 (power), recorded in
  the same CSV.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  writes `../corners/results.csv` (300 rows) and
  `../corners/tstep_convergence.csv` (8 rows).
- **Reproducibility fix (issue #44)**: `../testbench/tb_vco_duty.sp.tmpl`
  used literal `.lib $PDK_ROOT/$PDK/...cornerMOShv.lib` and
  `.lib $PDK_ROOT/$PDK/...cornerRES.lib` lines. Env-var expansion inside
  ngspice's `.lib`/`.include` parser is not portable across builds (see the
  identical finding on the sibling `sg13cmos5l-cp-icp-trim` and
  `sg13cmos5l-loop-bandwidth-pm` records); a reproduction attempt on a
  different ngspice build hit a fatal "library file not found" error on
  every run, which `run.sh`'s `2>/dev/null` silently turned into a false
  `NA` result. Fixed by substituting `@PDK_ROOT@`/`@PDK@` tokens via
  `run.sh`'s own `sed` line (matching the `@CORNER_MOS@`-style convention
  already in use), and `run.sh`'s `2>/dev/null` was replaced with an
  explicit ngspice exit-code check that surfaces stderr on failure.
  **Re-ran the full 300-row campaign plus the 8-row tstep-convergence check
  after the fix** (`ngspice-46`, the same `~/share/pdk/ihp-sg13cmos5l`
  install this record already named): zero `NA` rows, zero fatal errors,
  and both `results.csv` and `tstep_convergence.csv` reproduce
  **byte-for-byte identical** to the values already committed here — the
  original numbers were real, not fabricated; only the template's env-var
  portability was broken.

## Methodology

Same open-loop drive as the Kvco record (ideal DC sources on
`VCTRL`/`B0`/`B1`/`VDD_VCO`, `.ic` symmetry break on `ring1`, `XCDECAP`
stripped from the local netlist copy for the same provably-inconsequential
reason). The measurement differs: this deck measures the **falling** as well
as the rising 1.65 V (50%-of-rail) crossings, and reports
`t_high / T` at **two different cycles** (edges 4→5 and 6→7) so
cycle-to-cycle consistency is visible in the data rather than asserted.
Each run also records the ring's own average supply current over the
settled window (10–25 ns).

## Results — duty cycle

Across all 300 runs (`../corners/results.csv`):

- **Range: 43.74% – 51.56%.**
- **30 of 300 points fall below the 45% floor.** None exceeds the 55%
  ceiling.
- Cycle-to-cycle spread within a run (`duty` vs. `duty2`): **≤ 0.30
  percentage points**, so each reported value is a settled steady-state
  number, not a transient artifact.

**Temperature is the dominant axis, not process:**

| Temperature | duty range | mean |
|---|---|---|
| −40 C | 43.74 – 49.24% | 45.90% |
| 27 C | 46.35 – 48.86% | 47.23% |
| 125 C | 48.46 – 51.56% | 50.23% |

Every one of the 30 sub-45% points is at **−40 C**. Duty cycle rises
monotonically with temperature across the whole matrix — the ring's PMOS
head and NMOS tail do not track each other over temperature.

**Which corners fail the floor:**

| MOS corner | sub-45% points (of 60) | min duty |
|---|---|---|
| mos_fs | 13 | **43.74%** (−40 C, `VCTRL` = 0.3 V) |
| mos_ff | 9 | 44.40% |
| mos_tt | 8 | 44.75% |
| mos_sf | 0 | 45.84% |
| mos_ss | 0 | 45.67% |

The worst corner is **`mos_fs`** (fast NMOS / slow PMOS) at cold — the
NMOS-tail-favouring split corner, exactly the axis
`sg13cmos5l-vco-kvco-table/corners/matrix.md` flagged as open and unswept.
Note `mos_tt` also fails: this is **not** a split-corner-only problem, it is
a cold-temperature problem that the split corner makes worse.

**Which operating points fail:** 24 of the 30 sub-45% points are at
`VCTRL` ≤ 0.9 V, i.e. the bottom of the tuning range where the starving
current is smallest. Band code is essentially irrelevant to the failure
(9/7/7/7 across `00`/`10`/`01`/`11`) — consistent with the Kvco record's own
finding that band select is nearly inert at low `VCTRL`.

**This reproduces gf180-pll's own finding on a different process.**
`spec/porting-plan.md` row 13 records gf180-pll measuring "7 points below the
45% floor at the `lo` edge / `fs` corner bundle" and carries that forward as
a design flag rather than a target. SG13CMOS5L shows the *same failure mode
at the same place* — low control voltage, `fs`-flavoured corner — with 30
failing points out of a 300-point matrix. The flag was correct and it has
now bitten twice.

## Numerical convergence of the duty-cycle measurement

`../corners/tstep_convergence.csv`, four representative points re-run at a
4x finer maximum timestep:

| Point | 20 ps | 5 ps | Δ |
|---|---|---|---|
| mos_tt / 27 C / band 00 / 1.5 V | 46.7146% | 46.7809% | +0.066 pp |
| mos_sf / 27 C / band 11 / 2.7 V | 48.3853% | 48.3907% | +0.005 pp |
| mos_fs / 27 C / band 11 / 2.7 V | 46.7695% | 46.9190% | +0.150 pp |
| mos_ss / 125 C / band 00 / 0.9 V | 49.8565% | 49.8840% | +0.028 pp |

Worst-case discretisation sensitivity is **0.15 percentage points**, an
order of magnitude smaller than the 1.26 pp by which the worst measured
point misses the 45% floor. The floor violations are circuit behaviour, not
a timestep artifact.

## Results — VCO average supply current (input to row 11)

Measured in the same runs, over the settled 10–25 ns window, at 3.3 V:

- **Full range across the matrix: 0.937 – 2.690 mA**, i.e. **3.09 – 8.88 mW
  for the VCO block alone.**
- At the top of band `11` (`VCTRL` = 2.7 V), where the loop would sit for
  the highest output frequencies:

| MOS corner | −40 C | 27 C | 125 C |
|---|---|---|---|
| mos_tt | 2.295 mA / 1428.7 MHz | 2.108 mA / 1359.5 MHz | 1.790 mA / 1213.7 MHz |
| mos_ss | 1.966 mA / 1286.6 MHz | 1.816 mA / 1241.3 MHz | 1.585 mA / 1114.0 MHz |
| mos_ff | **2.690 mA / 1563.0 MHz** | 2.393 mA / 1485.5 MHz | 2.025 mA / 1316.8 MHz |
| mos_sf | 2.275 mA / 1407.7 MHz | 2.093 mA / 1349.0 MHz | 1.797 mA / 1210.8 MHz |
| mos_fs | 2.311 mA / 1443.3 MHz | 2.093 mA / 1366.0 MHz | 1.774 mA / 1210.1 MHz |

**The VCO alone already exceeds gf180-pll's whole-PLL power figure at the
top of its band.** `spec/porting-plan.md` row 11 cites gf180-pll's
"< 5 mW at 100 MHz, 3.3 V, all domains"; this ring draws 5.9 – 8.9 mW at
`VCTRL` = 2.7 V before any other block is counted. That row's own
disposition ("re-derive — do not scale by V²") is vindicated in the
strongest possible way: the gf180-pll number is not a starting point here,
because this VCO runs at 12–15x the frequency gf180-pll's number was quoted
at. See "Spec-row disposition" for why this record still does not close
row 11.

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 13 — output duty cycle**: **bounded by this record.** Measured
  43.74 – 51.56% over a 300-point PVT x band x `VCTRL` matrix; the 45–55%
  target is **not met** at 30 of 300 points, all at −40 C, concentrated at
  low `VCTRL` and at the `mos_fs` corner. The row's carried-forward design
  flag is confirmed on SG13CMOS5L. This record does not relax the target to
  make the result pass.
- **Row 11 — power**: **partially bounded — one domain, measured.** The
  `vdd_vco` domain's own average current is real, PVT-cornered data. A
  whole-PLL number additionally needs the `cp`, `pfd`, `divider_chain` and
  `lock_detector` domains at a *consistent* operating point, and ideally a
  closed-loop one. The `cp` domain's own DC current is separately bounded
  by `../../sg13cmos5l-cp-icp-trim/` (at the 10 µA trim code the pump
  contributes ≈2 × 10 µA × 3.3 V ≈ 66 µW, three orders of magnitude below
  the ring). The `pfd`, `divider_chain` and `lock_detector` domains are not
  measured by any record yet, so **the row as a whole stays
  `insufficient-evidence`** and is deferred to issue #37 (Part of #16) —
  explicitly, rather than by summing the two domains that happen to exist
  and calling the sum a total.
- **Row 8 — period jitter**: not addressed. This record measures a
  deterministic waveform property, not jitter; the
  `sg13cmos5l-vco-decap-momcap` record's own disposition on that row is
  unchanged.

## What this does not bound

- **Duty cycle in closed loop.** This is an open-loop measurement with an
  ideal DC `VCTRL`. In a real loop `VCTRL` carries reference-frequency
  ripple, which modulates the ring's starving current within a single
  reference cycle. Whether that widens or narrows the measured spread is not
  determined here.
- **Duty cycle after the (not yet drawn) output path.** `CLK` here is the
  block's own `inv2x_hv` buffer output with no external load; row 14's
  ≤ 50 fF load condition is untested.
- **Random mismatch between the five ring stages.** No mismatch model is
  available (same limitation as every other record in this campaign).
- **Whether the 30 failing points are recoverable by sizing.** That is a
  design question. The data localises the failure precisely (cold, low
  `VCTRL`, NMOS-favouring corner), which is what a sizing pass needs, but
  this record proposes no fix.
