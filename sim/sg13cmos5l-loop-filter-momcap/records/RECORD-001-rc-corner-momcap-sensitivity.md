# RECORD-001: `loop_filter` R1/C1/C2 process+temperature corner and MOM-cap-uncertainty sensitivity

- **Slug**: `sg13cmos5l-loop-filter-momcap`
- **Issue**: #23 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L PVT campaign)
- **DUT**: `loop_filter` (SG13CMOS5L port, PR #26 / Closes #22) — `XR1` (rppd,
  `w=4u l=120u`), `XC1` (cap_cmomi, `w=40u l=40u`), `XC2` (cap_cmomi,
  `w=10u l=10u`). See `../netlist-snapshots/loop_filter.spice` (frozen at
  commit `b7165f9c992581e295b536e782655e83799ca309`).
- **Claim under test**: `spec/decision-records/DR-003-sg13cmos5l-port-readiness.md`
  Finding 2 obligates a sweep of `loop_filter.XC1`/`XC2` across a plausible
  MOM-model-uncertainty band, because the installed `cap_cmomi` model carries
  no characterised corner/mismatch spread. This record delivers that sweep
  for the filter's own zero/pole location (`spec/porting-plan.md` row 6/6a's
  filter-side half — see "What this does not bound" for the row's other,
  still-open half).
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`
  (`ReleaseNote.md` `v0.2.0`, same install DR-003 confirmed).
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  writes `../corners/results.csv`; `ngspice -b
  testbench/tb_composite_ac_crosscheck.sp` reproduces the cross-check below.

## Methodology

`loop_filter` has **no DC path to ground at all** (both the `R1+C1` branch
and the `C2` branch are capacitor-terminated) — this matches a real
charge-pump loop filter, whose only DC path is through the active loop, not
the filter itself. That rules out a direct `.op` resistance/capacitance
read on the composite two-port, so this record uses two complementary
techniques:

1. **Single-device extraction** (`testbench/tb_extract_r.sp.tmpl`,
   `tb_extract_c.sp.tmpl`, driven by `testbench/run.sh`): `R1` is measured by
   forcing 1 uA through the standalone `rppd` instance and reading `V/I` at
   `.op`. `C1`/`C2` are each measured by driving the standalone `cap_cmomi`
   instance with a 1 A AC current source (a 1e14 ohm parallel bleed resistor
   gives the floating node a well-posed DC operating point without
   perturbing the AC result — a 1e9 ohm bleed, tried first, was *not*
   negligible at these frequencies and corrupted the sub-100kHz points; see
   "What went wrong first" below) and computing `C = 1/(2*pi*f*|Im(Z)|)`.
   `R1`, `C1`, `C2` measured this way then feed the closed-form
   `fz = 1/(2*pi*R1*C1)`, `fp = (C1+C2)/(2*pi*R1*C1*C2)` for the filter's
   zero/pole (standard passive-PI-filter transfer impedance
   `Z(s) = (1+sR1C1) / (s(C1+C2)(1+sR1C1C2/(C1+C2)))`).
2. **Composite cross-check** (`testbench/tb_composite_ac_crosscheck.sp`, run
   once, nominal corner only): an AC impedance sweep of the *actual*
   `loop_filter` subckt exactly as instantiated (not the individual-device
   extraction), 10 Hz to 1 GHz. Confirms the closed-form values above land at
   the real magnitude-slope knee of the real, fully-elaborated compact
   models — not just a textbook formula.

### What went wrong first (kept for the next testbench author)

The first AC-extraction attempt used a `1G` (1e9 ohm) bleed resistor for
every floating-node op-point. This matched the nominal `cap_cmomi` value to
~1% at a single-device 1kHz probe (close enough to look right in isolation),
but on the *composite* `loop_filter` AC sweep the same 1G bleed produced a
completely wrong low-frequency slope (flat instead of the expected -1
slope/decade, because the filter's own real impedance below ~100kHz is
comparable to or larger than 1e9 ohm, so the bleed resistor dominated
instead of being negligible). Raising the bleed to `1e14` ohm (5+ orders of
magnitude above the circuit impedance anywhere in the swept band) fixed it.
**Lesson for future device-extraction testbenches on this PDK: size the
convergence-only bleed resistor against the actual circuit impedance in the
swept band, not a single round number reused from another testbench.**

Separately, `cap_cmomi`/`cap_cmomi`-adjacent OSDI models (and `rppd`'s
`r3_cmc` OSDI resistor model) only resolve when their `osdi <path>` load
commands run from a `.spiceinit` auto-sourced at ngspice startup — an
identical `osdi` line placed inside the netlist's own `.control` block
fails with `Unable to find definition of model`, because netlist model
elaboration already ran by the time `.control` executes. `run.sh` writes a
`.spiceinit` into its own scratch work directory and runs every ngspice
invocation with that directory as `cwd` for this reason.

## Corner matrix

| Axis | Values | Why |
|---|---|---|
| Process (R1 only) | `res_typ`, `res_bcs`, `res_wcs` (`cornerRES.lib`) | `rppd`'s only PDK-provided corner axis |
| Temperature | -40C, 27C, 125C | Standard PVT bracket; `R1` (rppd) has a real, small tempco (confirmed below); `C1`/`C2` do not (confirmed below) |
| MOM-cap uncertainty | -20%, 0%, +20% | See "MOM-cap-uncertainty band, and why 20%" below. Applied **uniformly** to both `C1` and `C2` in a given run (a systematic model/coefficient bias, not independent per-instance mismatch — see the rationale in `testbench/tb_extract_c.sp.tmpl`'s header) |
| Supply | **not swept** | `loop_filter` has no active device and no `VDD`/`VSS` pin dependent on supply value — only the floating `VCTRL`/`VSS` two-port DR-004 already confirms (all-3.3V internal design) — so a supply-corner axis does not apply to this specific DUT. (The design's other blocks do have real supply dependence and are out of this record's scope — see `sim/README.md`'s campaign table.) |

27 total rows (3 process x 3 temp x 3 MOM-frac); `../corners/results.csv`.

### MOM-cap-uncertainty band, and why 20%

`cap_cmomi.lib`'s own header (read directly, quoted in full):

> *** APPROXIMATE MODEL -- NOT YET VALIDATED ON ihp-sg13cmos5l SILICON ***
> Coefficients are TRANSFERRED from the sg13g2 characterisation (thin metals
> M1..M5) and re-used on the cmos5l M1..M4 stack BY LAYER COUNT N =
> mmax-mmin+1. NONE are measured on cmos5l silicon...

and `cornerCAP.lib`'s own header confirms **no corner or mismatch spread is
modelled at all** — every `.LIB cap_typ`/`cap_bcs`/`cap_wcs`/`*_mismatch`
section `.include`s the identical `cap_cmomi.lib`/`cap_cmomf.lib` (verified
directly: `grep cap_cmomi cornerCAP.lib` shows the same two `.include` lines
repeated in all seven sections). This record's own C1/C2/XCDECAP
measurements (below) independently confirm the model returns the exact same
capacitance at -40C/27C/125C — no tempco either.

No PDK-provided number exists to size the uncertainty band (this is
precisely DR-003 Finding 2's point). Both `loop_filter.XC1` and
`loop_filter.XC2` use `mmin=1 mmax=4` (`N=4`), which the header's own text
places on the *more*-trusted side ("N=2 extrapolated, N=3,4
g2-measured-transferred") — still transferred from a different process's
characterisation onto a different (reduced M1..M4 vs. SG13G2's M1..M5)
metal stack, not measured on this silicon at all. **+/-20% is this record's
own engineering placeholder**, chosen as a round, conservative bound for a
"characterised on a different process, transferred by layer count, not yet
measured here" capacitor model — consistent with the general order of
process-to-process MOM-cap density spread reported for comparable
open/MPW-class PDKs elsewhere, but **not itself a measured or PDK-cited
number**. This band should be revisited (tightened or widened) once
`cap_cmomi.lib`'s own promised re-fit against cmos5l silicon lands ("a
re-fit is pending silicon (~3-6 months)" per the same header).

## Results

Full data: `../corners/results.csv`. Nominal corner (`res_typ`, 27C,
mom_frac=0): **R1 = 7.794 kOhm, C1 = 1.6912 pF, C2 = 100.15 fF, fz = 12.07
MHz, fp = 216.0 MHz.**

| Spread source (fz) | Range | Ratio (max/min) |
|---|---|---|
| Process + temperature only (mom_frac=0 fixed) | 10.76 MHz -- 13.54 MHz | 1.258 (+/-13% around nominal) |
| MOM-cap band only (`res_typ`, 27C fixed) | 10.06 MHz -- 15.09 MHz | 1.500 (exactly the analytic +/-20% cap swing: `fz ~ 1/C1`, so `1/0.8 : 1/1.2 = 1.5`) |
| Full matrix (all 27 rows) | 8.97 MHz -- 16.92 MHz | 1.887 |

`fp` moves proportionally (`fp` and `fz` share the same `1/(R*C)`-family
scaling here, confirmed directly in `results.csv`: every row's `fp/fz`
ratio is constant at `(C1+C2)/C2`, independent of R and the MOM band).

**Process+temperature alone already produces a real +/-13% swing** even
before the MOM band is applied — a genuine PVT result independent of the
MOM-cap question, and itself new evidence for the not-yet-re-derived row
6/6a. **The MOM-cap band alone dominates the process+temperature spread**
(50% vs. 26%), directly substantiating DR-003 Finding 2's premise that this
uncertainty is not a rounding error against process variation, but the
single largest lever on this filter's own pole/zero location.

### Cross-check

`testbench/tb_composite_ac_crosscheck.sp`'s full-subckt AC sweep (nominal
corner) shows the expected single -1-slope-per-decade region below ~1 MHz
(pure `1/(s*(C1+C2))` integrator behavior — no DC path, as expected), a
knee starting around 6--16 MHz (bracketing the closed-form `fz = 12.07
MHz`), and continued rolloff toward the `fp` region. This confirms the
closed-form values above are not just a textbook approximation but track
the real, fully-elaborated compact-model impedance. (The op-point solver
emits benign `singular matrix: check node xlf.sub!` warnings before falling
back to gmin/source stepping and a transient-op start — expected for a
purely capacitor-terminated network with no other DC path, and the run
still converges to the correct AC result, cross-checked against the
single-device extraction above.)

## Spec-row disposition (per this repo's own CLAUDE.md — no claim without a testbench)

`spec/porting-plan.md` row 6/6a (loop bandwidth / phase margin): **this
record bounds the filter's own zero/pole contribution** (table above) —
that half of the row is no longer `insufficient-evidence`. **The row's
actual numeric claim (a loop-bandwidth-in-kHz / phase-margin-in-degrees
figure) stays `insufficient-evidence`**: computing it needs the loop's
open-loop gain, which needs the Kvco table (row 4/5) and the Icp-trim table
(both explicitly deferred, `spec/porting-plan.md`/DR-003, not this record's
scope) combined with the R1/C1/C2 data above. This record supplies real,
PVT-and-MOM-bounded evidence for its own half of that derivation; it does
not — and does not claim to — close the row by itself.

## What this does not bound

- **Mismatch** between `C1` and `C2` (as opposed to a shared systematic
  bias) — `cap_cmomi`'s own model explicitly has no characterised mismatch
  either, and this record's uniform-MOM-frac choice deliberately does not
  model an independent per-instance error. A future record could add that
  axis if a plausible mismatch bound becomes available.
- **The final loop-bandwidth/phase-margin number** — see "Spec-row
  disposition" above.
- **Anything about `pfd`, `cp`, `divider_chain`, `lock_detector`,** or the
  full closed loop — out of this record's own claim ("`loop_filter`
  R1/C1/C2... sensitivity"), see `sim/README.md`'s campaign table for what
  those need.
