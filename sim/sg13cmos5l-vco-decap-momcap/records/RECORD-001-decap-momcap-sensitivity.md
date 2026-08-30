# RECORD-001: `vco.XCDECAP` MOM-cap-uncertainty sensitivity

- **Slug**: `sg13cmos5l-vco-decap-momcap`
- **Issue**: #23 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L PVT campaign)
- **DUT**: `vco.XCDECAP` (SG13CMOS5L port, PR #26 / Closes #22) — `cap_cmomi`,
  `w=70u l=70u`, the VCO's own supply decoupling cap across
  `VDD_VCO`/`GND_VCO`. See `../netlist-snapshots/vco.spice` (frozen at commit
  `b7165f9c992581e295b536e782655e83799ca309`).
- **Claim under test**: `spec/decision-records/DR-003-sg13cmos5l-port-readiness.md`
  Finding 2 names `vco.XCDECAP` as one of the three MOM-cap instances a
  sensitivity sweep must bound (the other two, `loop_filter.XC1`/`XC2`, are
  `../../sg13cmos5l-loop-filter-momcap/records/RECORD-001`'s own claim).
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`
  (`ReleaseNote.md` `v0.2.0`).
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  writes `../corners/results.csv`.

## Methodology

Same single-device AC-extraction technique as the loop-filter record (see
that record's own "Methodology" for the full rationale, not repeated here):
drive the standalone `cap_cmomi` instance (`w=70u l=70u`, matching the
netlist snapshot) with a 1 A AC current source, a `1e14` ohm bleed resistor
for a well-posed DC operating point, and read
`C = 1/(2*pi*f*|Im(Z)|)` in the flat (capacitive) region.

This record adds one further step the loop-filter record does not need: a
**pole-frequency demonstration**. `XCDECAP` alone has no meaning as a
"sensitive spec row" without something it's decoupling *against* — the row
this bounds (`spec/porting-plan.md` row 8/12, jitter / supply sensitivity)
is really a statement about how well the decap filters supply ripple before
it reaches the VCO core. That filtering is set by `1/(2*pi*R_src*C_decap)`,
where `R_src` is the supply network's own source impedance looking into
`VDD_VCO` — a **post-layout parasitic-extraction quantity that does not
exist yet** (no layout has been drawn for this port; issue #24, Part of #16,
owns that). `testbench/tb_decap_pole_ac.sp.tmpl` demonstrates the pole with
an explicitly **illustrative** `R_src = 3000 ohm` (chosen only so the
resulting pole lands inside a convenient sweep band, ~10 MHz) driving the
real `cap_cmomi` compact model (not an idealized linear capacitor), and
extracts the -3dB corner frequency directly from a real ngspice AC sweep
(linear interpolation in log-frequency between the two grid points
bracketing the -3.0103 dB crossing).

**Why the illustrative `R_src` choice does not undermine the sensitivity
result**: for a single-pole network, `f_pole = 1/(2*pi*R*C)` is exactly
inversely proportional to `C` for *any* fixed `R`. A `+/-20%` fractional
change in `C_decap` therefore produces the *same* `-16.7%/+25%` fractional
change in `f_pole` regardless of what `R_src` turns out to be once real
parasitics exist — the demonstration below (with `R_src=3000`) numerically
confirms this exact 1.5x span-ratio prediction against the real compact
model, which is the part that could plausibly have differed from the ideal
formula (a nonlinear compact model, unlike an ideal capacitor, is not
guaranteed to preserve exact inverse proportionality) but was confirmed to.

## Corner matrix

| Axis | Values | Why |
|---|---|---|
| Temperature | -40C, 27C, 125C | Confirms (does not assume) `cap_cmomi` temperature-invariance for this instance too, same finding as the loop-filter record |
| Process | **not swept** | `cornerCAP.lib`'s own header states every corner section maps to the identical nominal `cap_cmomi.lib`/`cap_cmomf.lib` include (verified directly, same finding cited in the loop-filter record) — no PDK process-corner axis exists for this device |
| MOM-cap uncertainty | -20%, 0%, +20% | Same band and same rationale as the loop-filter record — see that record's "MOM-cap-uncertainty band, and why 20%" (not re-derived here; same PDK, same unvalidated model, same `N=4` layer-count case: `mmin=1 mmax=4`) |
| Supply | **not swept** | This DUT is the decoupling capacitor itself, a two-terminal passive device with no supply-dependent behavior of its own; the VCO block it decouples *does* have real supply/PVT dependence (Kvco, oscillation), which is out of this record's own claim (`XCDECAP`'s own capacitance and pole-shift sensitivity) — see `sim/README.md`'s campaign table for that deferred work |

`../corners/results.csv`: 3 temperature-invariance rows + 3 MOM-frac rows.

## Results

Nominal `XCDECAP` (27C, mom_frac=0): **5.2862 pF** — matches
`design/README.md`'s own device-substitution table ("~5.29 pF") to 4
figures. Confirmed identical at -40C and 125C (no measurable tempco, same
finding as `loop_filter`'s `cap_cmomi` instances).

Illustrative pole-frequency demonstration (`R_src = 3000 ohm`):

| MOM frac | C_decap | -3dB pole frequency |
|---|---|---|
| -20% | 4.229 pF | 12.54 MHz |
| 0% (nominal) | 5.286 pF | 10.03 MHz |
| +20% | 6.343 pF | 8.349 MHz |

Span ratio (max/min) = **1.502** — matches the exact analytic
`1/0.8 : 1/1.2 = 1.5` prediction to 3 figures, confirming the real
`cap_cmomi` compact model preserves simple inverse proportionality across
this band (i.e. the MOM-band-to-pole-frequency sensitivity claim above does
not depend on the illustrative `R_src` value chosen).

## Spec-row disposition (per this repo's own CLAUDE.md — no claim without a testbench)

`spec/porting-plan.md` rows 8 (period jitter) and 12 (supply sensitivity):
**this record bounds `XCDECAP`'s own capacitance value and the exact
fractional pole-frequency sensitivity that value implies** (a real,
PVT-and-MOM-bounded result). **The rows' own absolute numbers
(jitter-as-percent-of-period, an mV ripple budget, a dB attenuation figure)
stay `insufficient-evidence`**, for two independent reasons neither of
which this record can resolve:

1. **No post-layout `R_src`/parasitic source impedance exists yet** (no
   layout has been drawn for this port — issue #24, Part of #16), so the
   *absolute* pole frequency (as opposed to its fractional MOM-band
   sensitivity) is not knowable yet.
2. **ngspice cannot compute phase noise / jitter for a free-running
   oscillator directly** — a pre-existing flow limitation this repo's own
   `spec/decision-records/DR-002-supply-device-flavor.md` Decision 5 already
   names, independent of SG13CMOS5L or the MOM-cap question. A ring
   oscillator's own DC operating point is also an unstable equilibrium
   (metastable, all inverters near threshold), so a linear small-signal
   `.AC` transfer function around that point is not a well-posed analysis
   the way it is for `vco_bias`'s own stable bias network — this record
   deliberately does not attempt it (see "What this does not bound").

## What this does not bound

- **The absolute jitter or supply-ripple-attenuation number** — see
  "Spec-row disposition" above; needs post-layout parasitics and a
  closed-loop/phase-noise method this flow does not have.
- **A full-ring-oscillator small-signal PSRR measurement** — considered and
  rejected for this record specifically because the ring's own DC operating
  point is an unstable equilibrium, not because it is out of scope in
  principle. `vco_bias` alone (the VCO's bias generator, which *does* have a
  stable DC operating point) is a more tractable target for a future record
  if a `VDD_VCO`-to-`VBP`/`VBN` supply-rejection transfer function becomes
  useful evidence — not attempted here.
- **Mismatch** (as opposed to a shared systematic MOM-model bias) — same
  caveat as the loop-filter record.
