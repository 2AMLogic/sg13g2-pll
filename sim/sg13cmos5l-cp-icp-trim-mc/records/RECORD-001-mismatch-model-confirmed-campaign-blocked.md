# RECORD-001: SG13CMOS5L hv MOS mismatch model confirmed; `cp` Monte Carlo campaign blocked on the batch fleet

- **Slug**: `sg13cmos5l-cp-icp-trim-mc`
- **Issue**: #178 (T1 item 6). This record **does not state a yield estimate**:
  the campaign has not run. A later `RECORD-002` carries the estimate.
- **DUT**: `cp`, `netlist-snapshots/cp.spice` (identical to the sibling
  bench's snapshot), Iref = 10 uA, VDD = 3.3 V, VOUT = 2.40 V.
- **Tooling**: `klt 0.7.0+g5c94de0ebbfe`, `ngspice-46`, `~/share/pdk/ihp-sg13cmos5l`,
  x86-64 Linux worker.
- **PDK revision**: `ihp-sg13cmos5l` commit `607e18d4bd9214a52575c194b4181ef449f9252f`
  (clean git checkout at `~/share/pdk/ihp-sg13cmos5l` on the worker; matches
  the `PDK-PIN` in `sim/README.md`).
- **Reproduce**: `README.md` "Cold start".

## Finding 1: the mismatch model exists and is live

`cornerMOShv.lib` provides `mos_{tt,ss,ff,sf,fs}_mismatch`. Those sections
include `sg13g2_moshv_mismatch.lib` (PDK-supplied one-sigma values) and
`sg13g2_moshv_mod_mismatch.lib` (`agauss` draws on `w`, `l`, `delvto`,
`factuo`, gated by the instance parameter `mm_ok`, default 1). Under
`klt sim` `monte_carlo.vary = "mismatch"` the draws vary per sample.

This supersedes, without editing, the statement in
`../../sg13cmos5l-cp-icp-trim/records/RECORD-002` ("What this does not
bound"): "no per-instance mismatch model is available for
`sg13_hv_nmos`/`sg13_hv_pmos`". The model is available; it was not selected.

## Finding 2: controls behave

| Run | Section | N | `mismatch_pct` | Result |
|---|---|---|---|---|
| Negative control (`reports/sim.negative_control.json`) | `mos_tt`, 27 C | 20 | -0.298464807648 for all 20 samples | stddev = 0.0 exactly (also for `iup_a`, `idn_a`); status pass |
| Positive probe (`reports/sim.positive_probe.json`) | `mos_tt_mismatch`, 27 C | 3 | 2.855, 6.269, 7.983 % | stddev 2.61 %, nonzero; fails the +/-3.5 % screening limit, exit 3 |

The control value equals the corner bench's -0.298 % at VOUT = 2.40 V
(sibling `RECORD-002`). The probe has N = 3 at one corner: it shows the
mismatch section is live and the spread is the same order as or larger than
the limit. It is **not** a yield estimate and must not be read as one.

## Finding 3: the campaign cannot run on this fleet today

- `mc.request.json` (15 corners x N = 100) on the `batch` backend: refused
  for `models.pdk = ihp-sg13cmos5l` (klayout-tools#2727); without it, the
  fleet runner (klt 0.5.0) ignored `osdi_preload` and every sample died with
  `Unable to find definition of model ...sg13g2_hv_pmos_psp`
  (klayout-tools#2851, #2901).
- `klt yield` cannot run here (`klt_yield_native` missing).
- No local fallback was used, per the worker's host rules.

## What this does not bound

Everything about the distribution: yield, CI, per-corner sigma, whether the
+/-3.5 % screening limit is met. The limit itself is an evidence-derived
screening value, not a ratified spec number (README "Limit").
