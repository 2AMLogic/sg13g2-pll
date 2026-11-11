# Corner matrix — `sg13cmos5l-supply-range`

**Claim under test**: `spec/target-spec.md` row 18 (supply range 3.0 to 3.6 V)
and risk R-9. Row 18 was measured on `cp` only; this bench runs `vco`,
`lock_detector` and `divider_chain` at the two endpoints plus nominal.

| Axis | Values | Why |
|---|---|---|
| VDD | 3.0, 3.3, 3.6 V | Row 18 bounds. 3.3 V is run in the same job as a same-tool control. Other benches' ±10% sub-axes use 2.97/3.63 V; this bench uses the row's own 3.0/3.6 |
| PVT bundle | `typ` = `mos_tt`/`res_typ`/27 C; `slow` = `mos_ss`/`res_wcs`/125 C; `fast` = `mos_ff`/`res_bcs`/-40 C | The `sg13cmos5l-vco-kvco-table` 3-bundle convention, reused for all three blocks (the divider has no resistor, so only MOS corner and temperature apply there) |

| Block | Template (read from the sibling bench, never copied) | Per bundle x VDD | Decks |
|---|---|---|---|
| `vco` | `sg13cmos5l-vco-kvco-table/testbench/tb_vco_kvco.sp.tmpl` | 4 band codes x 5 `VCTRL` (0.3 to 2.7 V); `B0`/`B1` high level and the period-measure threshold scale with VDD | 180 |
| `lock_detector` | `sg13cmos5l-lock-detector-window/testbench/{tb_window,tb_schmitt_hyst}.sp.tmpl`, `real` DUT (`cap_cmomi`) | comparator window `twin_r`/`twin_f`; bare `schmitt_hv` thresholds | 18 |
| `divider_chain` | `sg13cmos5l-divider-nrange-retiming/testbench/{tb_div_func,tb_div_retime}.sp.tmpl`, repaired DUT | N=64 and N=127 at 100 MHz; retiming deck at 1562.0 MHz / 64 | 27 |

Total 225 decks, submitted as three `klt sim --backend batch` deck-list
requests (`testbench/run_batch.sh`).

## Not measured (stated, not hidden)

* **Time-domain hysteresis (>= 25 % of window) and no-chatter** for
  `lock_detector` are NOT re-measured at 3.0/3.6 V. They need the phase-error
  ladder, whose inputs (R and C extraction, per-corner recovery decks) are the
  full-grid campaign still owed by the lock-detector bench. Only the window
  (row 16 floor) and the bare Schmitt thresholds are covered here.
* `mos_sf`/`mos_fs`, the resistor-only axis and the MOM-uncertainty band are not
  swept (3-bundle subset, as in the VCO bench).
* No Monte Carlo; row 18 is Det.
