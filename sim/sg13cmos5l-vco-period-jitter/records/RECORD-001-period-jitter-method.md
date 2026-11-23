# RECORD-001: transient-noise period-jitter method — injected calibrated `trrandom` sources on the free-running ring

- **Slug**: `sg13cmos5l-vco-period-jitter`
- **Issue**: #518 (Part of #16; the row 8 / row 12 method gap, R-7 in
  `spec/target-spec.md`). Append-only first record of this bench.
- **Claim under test**: R-7's first gate — "a transient-noise or ISF method
  for the free-running ring" — as a *method*, at one corner, with the four
  validation controls the issue demands. **No bound is proposed for row 8
  or row 12**, and no row status changes; the numbers below are a method
  demonstration and a white-thermal floor, not spec figures.
- **DUT**: the frozen `../netlist-snapshots/vco.spice` (commit `c62d98c9`,
  file sha256 `1b99c6dee825b3d8b7c19b39a8a204f6a253e726999e7d3aab7c30b8aa81d519`),
  `XCDECAP`-stripped into every deck as `vco_open.spice` by
  `../testbench/gen_decks.py` — the identical derivation and justification
  as the duty-cycle bench (ideal, zero-impedance `VDD_VCO`/`GND_VCO` drive
  makes `XCDECAP`'s value inconsequential to any node voltage here; the
  ring decks then instantiate the `vco` snapshot's own `.subckt` body at
  top level, unchanged, so the internal ring nodes are reachable for noise
  injection). A later `vco` change (#188/#356 lineage) makes the numbers
  stale but not the method; the record binds to the snapshot above.
- **Tools**: `klt 0.9.3.dev2575+g6bd18bbc8637` (deck-list requests, local
  backend, `max_workers: 1`), `ngspice-47` (KLU build;
  `/home/ubuntu/.local/bin/ngspice` → `~/.local/opt/ngspice-47p1`).
  11/11 units `pass` (`../corners/local_report.json`, scratch paths
  redacted to `OUTDIR`).
- **PDK revisions**: PDK ihp-sg13cmos5l revision
  607e18d4bd9214a52575c194b4181ef449f9252f and PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e — the repo pins (`sim/README.md`);
  every deck's `.lib`/`pre_osdi` line is `$PDK_ROOT`-relative and the local
  runner expanded them against this host's pinned install (`~/share/pdk`,
  where the cmos5l tree resolves its model symlinks into the sibling
  ihp-sg13g2 tree, so transistor-level runs read both trees — same
  convention as the duty-cycle bench's fleet rerun).
- **Reproduce** (single corner, ~35 min local + one fleet probe):

  ```
  PDK_ROOT=$PDK_ROOT PDK=ihp-sg13cmos5l \
      sim/sg13cmos5l-vco-period-jitter/testbench/run.sh
  ```

  writes the committed CSVs beside this record. Corner coverage: **one
  corner** (`mos_tt`/`res_typ`, 27 C, 3.3 V, band `00`, `VCTRL` = 1.5 V) —
  see `../corners/matrix.md` for why the PVT axes are deliberately absent
  and why that is not a silent drop.

## Noise injection model

ngspice has **no intrinsic device noise in a transient** (measured
upstream; `klt sim`'s own `environment.transient_noise.intrinsic_device_noise:
false` disclosure) — time-domain noise exists only where the deck declares
explicit sources. This bench therefore injects, per ring stage, **one
aggregate equivalent noise-current source from the stage output node to
GND**, standing for the white thermal channel noise of that stage's four
transistors (`vco_stage`'s `XMP`, `XMN`, `XMPH`, `XMNT` — `w=5u/2u/10u/4u`
on the 0.28 um/0.5 um lengths). Source form:

```
inj<K> ring<K> 0 dc 0 trrandom(2, 1e-11, 0, 7.68923e-07)
```

- `trrandom` type 2 (Gaussian), zero mean, `sigma` = 768.923 fA rms, sample
  interval `ts` = **10 ps** (a *source* parameter on its own sample clock,
  not tied to the solver step — the timestep control below varies `.tran`
  step at fixed `ts`; the ZOH sinc^2 rolloff at the 10 GHz calibration band
  edge is -0.14 dB).
- `trrandom` streams are **replayable** through a `.control` `setseed N`
  placed before `run` (verified for this build below, matching the
  upstream measurement in 2AMLogic/klayout-tools#5772). **No `trnoise`
  unit exists in this bench** — a 1/f term would need one and would not be
  replayable; flicker is excluded from the model and quantified in the
  calibration below instead.
- One-sided PSD convention (verified end-to-end by the PSD check below): a
  ZOH Gaussian stream with rms `sigma` held for `ts` has one-sided density
  `S_i = 2 sigma^2 ts` at low frequency; `sigma = sqrt(S_i/(2 ts))`.

**What the model leaves out** (so every number below reads as a floor, not
the row 8 figure): flicker noise (excluded by construction; see
calibration), the `vco_bias` network's own noise (`rppd` resistor thermal
and bias-transistor noise on `VBP`/`VBN` — common to all stages), the
output buffer pair `XBUF1`/`XBUF2` (post-ring; would add crossing-comparator
jitter), substrate and supply noise, and device mismatch. The aggregation
at the stage output itself is an approximation: it replaces the true
per-device transfer of each noise contribution to the output node by the
measured aggregate output density, and it is calibrated at a linear-region
DC bias rather than the ring's large-signal switching trajectory.

## Calibration

Stable-DC-operating-point calibration circuit: **one** `vco_stage` from the
snapshot, `VBP`/`VBN` held by ideal sources at the values the snapshot's
own `vco_bias` generates at this operating point (VBP = 1.771692 V,
VBN = 1.341321 V, from `bias_op`), input self-biased to its DC trip point
through `Rfb` = 1e12 (the `XMP`/`XMN` currents balance exactly; the op
point is the circuit's own solution: `V(in)` = `V(out)` = **1.361047 V**;
small-signal DC gain at that point, from the DC-transfer sweep:
**15.61 V/V** — the high-gain linear region, not a hand-picked bias).

1. `.noise` at the stage output, 100 kHz–100 GHz (`cal_noise`): integrated
   output noise 2.885 mV rms over that band. ngspice's per-device
   integrated sub-components quadrature-sum to 2.8853 mV vs the 2.8855 mV
   total (0.006 % closure — the split is self-consistent); of that,
   channel-thermal sub-components contribute 2.726 mV rms and flicker
   0.328 mV rms — **flicker is 11 % of the rms even integrated from
   100 kHz**, and the equivalent-current density below is flat from
   ~100 MHz up, so the white-only model is calibrated in a band where
   flicker has already died away.
2. `.ac` with 1 A injected into the stage output (`cal_ac`) gives
   `|Z_out(f)|`; the equivalent injected density
   `S_i,eff(f) = S_v(f)/|Z_out(f)|^2` is **flat to within x1.22 over the
   whole 100 MHz–10 GHz fit band** (3.462 pA/sqrtHz at 100 MHz, 3.365 at
   1 GHz, 3.720 at 10 GHz) — which is what licenses modelling the stage
   noise as ONE white current source at the output node.
3. Fit: mean `S_i` = 1.1825e-23 A^2/Hz (3.439 pA/sqrtHz) over
   [100 MHz, 10 GHz] (the band brackets the ring's 652 MHz and its low
   harmonics; the flat fit makes the exact band edges uncritical) →
   `sigma` = 7.68923e-07 A at `ts` = 10 ps. Raw table:
   `../corners/calibration_noise.csv`; fit row: `../corners/calibration_fit.csv`.
4. **End-to-end PSD validation** (the injected source actually reproduces
   the `.noise` density, not just the analytic fit): the same DC-stable
   stage with the same `trrandom` source form/sigma/`ts` injected, 2 us
   transient, Welch PSD of the output (`cal_tran_s42`, `cal_tran_s43`,
   `wrdata` waveform; extractor `../testbench/extract.py`). At all 41
   in-band (100 MHz–10 GHz) table points, transient-PSD / `.noise`-density
   = **0.831–1.198** (seed 42) and **0.786–1.144** (seed 43) — inside the
   stated ±(0.7, 1.4) band. Below 100 MHz the injected white source
   deliberately *under*-models the rising 1/f density (excluded term).
   Raw rows: `../corners/calibration_psd.csv`.

## Validation controls

From `../corners/controls.csv` (verdicts recomputed from
`../corners/period_jitter.csv`; `n` = 1000 periods per unit throughout):

| Control | Expectation | Measured | Verdict |
|---|---|---|---|
| noise-off | rms(sigma=0) < 1 % of rms(sigma=cal) | 3.34 fs vs 464.3 fs (0.72 %) — the discretization/timestep floor | PASS |
| noise-off, halved step | floor stays < 1 % at `.tran` 5p | 3.54 fs (0.76 %) | PASS |
| timestep convergence | \|rms(tstep=5p)/rms(tstep=10p) − 1\| < 10 % | ratio **0.9989** (463.8 fs vs 464.3 fs); `ts` fixed at 10 ps across both, so the source sample interval is demonstrably not the solver step | PASS |
| amplitude scaling ×2 | rms within 10 % of 2× | ratio **2.0006** (928.9 fs) | PASS |
| amplitude scaling ×0.5 | rms within 10 % of 0.5× | ratio **0.5001** (232.2 fs) | PASS |
| seed repeat | same seed, separate process → bit-identical | crossing-table sha256 **equal** (`../corners/crossing_digest.csv`) | PASS |
| seed scatter | three seeds consistent with a common sigma | 464.3 / 444.7 / 471.4 fs; pooled 460.1 fs; chi-square(2) = 3.61 vs 5.99 (p ≈ 0.16) | PASS |
| calibration PSD | every in-band ratio within (0.7, 1.4) | 0.786–1.198 over 82 point-checks (2 seeds) | PASS |

**Statistical-note disclosure (append-only honesty):** the first-pass seed
scatter criterion shipped by the initial `extract.py` was statistically
wrong — it tested each seed's rms against the 95 % CI *of the pooled mean*
(drawing the 3 samples against the mean's tighter band), and seed 43
(444.7 fs vs a [448.8, 472.1] fs band) failed it. The correct test — the
chi-square consistency of the three draws with a common sigma, which is
what "different seeds scatter within the stated confidence interval" asks —
passes (3.61 vs the 5.99 95th percentile; each seed's own 95 % CI, ±4.5 %,
also contains the pooled value). `extract.py` in this commit carries the
corrected test; both the wrong criterion's numbers and the correction are
recorded here rather than silently replaced.

The seed controls used deck-declared `.control setseed` values **locally,
as the control itself** (the control measures replay behaviour of this
ngspice build: within one process a second `run` does *not* replay; across
processes — the shape of every klt unit — the same seed is bit-identical
and different seeds differ). This is not a campaign seeding mechanism and
none is added to the bench: see "Park".

## First measurement (single corner, floor reading)

Free-running ring, `mos_tt`/`res_typ`, 27 C, 3.3 V, band `00`,
`VCTRL` = 1.5 V: mean period **1.533008707 ns** (652.30 MHz; first-vs-second
500-period means differ by 7.2 ppm — startup excluded by skipping the first
50 crossings), 1000 periods, rising 50 %-of-rail crossings of the buffered
`clk` output, `measureprec=15`:

| Unit (seed, sigma) | rms jitter | peak-to-peak | % of period | 95 % CI (rms) |
|---|---|---|---|---|
| ring_s42_t10p (42, sigma) | **464.3 fs** | 2694 fs | **0.03029 %** | [444.8, 485.6] fs |
| ring_s42_t10p_rep (42, sigma) | 464.3 fs (bit-identical) | 2694 fs | 0.03029 % | identical |
| ring_s43_t10p (43, sigma) | 444.7 fs | 2659 fs | 0.02901 % | [426.0, 465.1] fs |
| ring_s44_t10p (44, sigma) | 471.4 fs | 3275 fs | 0.03075 % | [451.6, 493.0] fs |

Pooled across the three independent seeds: **≈ 460 fs rms ≈ 0.030 % of
period** at this corner and operating point, for the calibrated
white-thermal-only model. Raw per-unit rows (including the noise-off,
timestep and amplitude units): `../corners/period_jitter.csv`.

## What this does not bound

- **Not a row 8 figure.** One corner, one band code, one `VCTRL` point; a
  white-thermal-only, bias/buffer/resistor/substrate/supply-noise-free,
  mismatch-free model calibrated at a linear-region bias and applied to a
  switching ring. Every exclusion above pushes the true figure *up* from
  this floor; the calibrated white-ZOH source also injects a small
  out-of-band (> 10 GHz) excess relative to the devices' own density
  (visible as the integrated transient variance exceeding the `.noise`
  band integral), which the ring's per-stage bandwidth suppresses but
  which is not separately quantified here.
- **Not a row 12 figure.** The issue's step-5 supply-ripple unit (sinusoid
  on VDD, one frequency either side of the decap record's illustrative
  ~10 MHz pole, deterministic modulation reported separately from random
  jitter) is part of the parked campaign and was not run.
- No PVT spread, no Monte Carlo, no integrated phase noise (row 9 is
  deliberately not specified), no closed-loop jitter, no ISF decomposition.

## Park: the seed contract gap (steps 4–5 not run)

The campaign (nominal corner + three PVT bundles x two band codes x two
`VCTRL`, seeds recorded per report) and the row-12 supply-ripple unit
require `options.transient_noise_seed` (or equivalent) in the pinned klt —
**it does not exist in `klt 0.9.3.dev2575+g6bd18bbc8637`**: the field is
absent from its bundled request/response contract, and a request carrying
`options.transient_noise_seed: 42` is **silently accepted and ignored**
(`--dry-run` passes; nothing lands in any report — evidence in
`../corners/seedgap_probe.txt`). The committed local report contains zero
occurrences of a seed. No local seeding workaround was added to the bench
and no unseeded campaign was run; issue #518 is parked on
2AMLogic/klayout-tools#5772 (comment posted there with this record's
local replay measurements).

Batch probe, recorded for the park trail: the primary seed-42 deck in
fleet form was submitted twice with `--backend batch --wait-for-capacity
600`; both launches were refused by **fleet IAM** (`UnauthorizedOperation`
on `ec2:RunInstances` for the image — "this is IAM, not capacity" per
klt's own classification), staging jobs `klt-sim-f52a99f47c45` and
`klt-sim-5f28aab43af8` (complete on S3, re-launchable once the role is
repaired). Reported in the #518 PR; the park does not depend on it — a
working fleet would still have no seed contract to pin/report.
