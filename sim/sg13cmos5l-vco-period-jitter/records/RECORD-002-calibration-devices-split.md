# RECORD-002: calibration extractor trip-point fail-closed guard and committed per-device `.noise` split

- **Slug**: `sg13cmos5l-vco-period-jitter`
- **Issue**: #553 (evidence-hygiene follow-up to #518 / `RECORD-001-period-jitter-method.md`).
- **Append-only**: `RECORD-001-period-jitter-method.md` and every previously committed `../corners/*.csv` (`calibration_fit.csv`, `calibration_noise.csv`, `calibration_psd.csv`, `period_jitter.csv`, `controls.csv`, `crossing_digest.csv`) are unedited and byte-identical on re-run. No bound is proposed for row 8 or row 12, and no row status changes.
- **DUT**: unchanged from `RECORD-001` — `../netlist-snapshots/vco.spice` (commit `c62d98c9`, file sha256 `1b99c6dee825b3d8b7c19b39a8a204f6a253e726999e7d3aab7c30b8aa81d519`), single linear-biased `vco_stage` calibration deck (`cal_noise`, `cal_dcsweep`).
- **Tools**: `klt 0.9.3.dev2575+g6bd18bbc8637` (local backend, single calibration corner), `ngspice-47`.
- **PDK revisions**: PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f and PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e — the repo pins (`sim/README.md`), unchanged from `RECORD-001`.
- **Corner coverage**: **one corner** (`mos_tt`/`res_typ`, 27 C, 3.3 V, band `00`, `VCTRL` = 1.5 V), matching `RECORD-001`'s calibration point (`../corners/matrix.md`).

## Calibration extractor and per-device noise split

1. **Fail-closed DC trip-point parse (`../testbench/extract.py`)**: removed the `or 1.361047` fallback on `scalar(nz, "v(sout)")`. If `v(sout)` cannot be parsed from `cal_noise` stdout, `extract.py` exits non-zero (`rc=1`) with an explicit diagnostic rather than substituting a hard-coded voltage. Re-running `bias_op` + `cal_*` locally reproduces `../corners/calibration_fit.csv` byte-identically (`trip_v = 1.361047e+00`, `ss_gain_v_per_v = 15.6075`).
2. **Committed per-device `.noise` rows (`../corners/calibration_devices.csv`)**: `extract.py` now writes all 68 `onoise_total_*` entries across the four `vco_stage` transistors (`xmn`, `xmnt`, `xmp`, `xmph`) with their `flicker` / `thermal` / `other` / `excluded_aggregate` classification so the bucket regexes behind `RECORD-001` ("Calibration", step 1) are auditable offline:
   - `flicker` (8 rows): `3.282752e-04` V rms (0.328 mV rms)
   - `thermal` (16 rows): `2.726355e-03` V rms (2.726 mV rms)
   - `other` (40 rows — gate, junction, well, and bulk resistive/leakage terms): `8.856060e-04` V rms (0.886 mV rms)
   - `excluded_aggregate` (4 rows): bare per-device totals (`nsg13_hv_nmos` / `nsg13_hv_pmos`), listed for completeness and excluded from the quadrature sum (double-count guard).

   In quadrature, `flicker + thermal + other` = `2.885320e-03` V rms, closing on the `2.885321e-03` V rms sub-component total in `../corners/calibration_fit.csv` (to 6-digit CSV precision) against `onoise_total = 2.885483e-03` V rms.
