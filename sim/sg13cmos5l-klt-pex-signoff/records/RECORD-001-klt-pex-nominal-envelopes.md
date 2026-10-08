# RECORD-001: `klt pex` nominal-corner envelopes for five blocks (issue #152)

- **Tool**: `klt 0.6.0+g1eb3e4bfd0f5`, KLayout 0.30.12, ngspice-46,
  deck `sg13cmos5l` (hash in each envelope's `provenance.deck`).
- **Layout**: `layout/sg13cmos5l-pll/reports/20261003-183059-dc5644a/pll_<block>.gds`.
- **Corner**: `mos_tt` (+ `res_typ`, `cap_typ` where the block has R/C), 27 C,
  3.3 V, `--backend local`. One corner per block; no grid was launched.
- **Schematic leg**: `design/sg13cmos5l/netlist/<block>.spice`, flattened by
  `../flatten-schematic.py`.

| Block | Row | Schematic | Extracted | delta | `body_bias` |
| --- | --- | --- | --- | --- | --- |
| `pfd` | `up_avg` (V) | 0.04447 | 0.07909 | +77.85 % | biased |
| `pfd` | `dn_avg` (V) | 0.37440 | 0.40903 | +9.25 % | biased |
| `cp` | `icp_up_a` (A) | 1.000047e-5 | 1.001774e-5 | +0.173 % | biased |
| `cp` | `icp_dn_a` (A) | -1.00175e-5 | -1.00226e-5 | -0.051 % | biased |
| `loop_filter` | `t63_nz_s` (s) | 6.8243e-7 | 8.84742e-7 | +29.65 % | biased |
| `vco` | `clk_period_s` (s) | 1.45372e-9 | 3.64896e-9 | +151.0 % | biased |
| `divider_chain` | `div_period_s` (s) | 6.40003e-7 | 6.39989e-7 | -0.002 % | biased |
| `divider_chain` | `ck_period_s` (s) | 1.0e-8 | 1.0e-8 | 0.0 % | biased |

Divider ratio is 64.0 on both legs (programming word 000000).

## Limits of this record

- No request declares `limits`, so `status: pass` means "ran and compared",
  not "met a spec". The vco/pfd/loop_filter deltas are large and real.
- `pfd` `up_avg`/`dn_avg` are averages of a pulsed output at one fixed REF
  lead (5 ns); the large `up_avg` delta is a small-number effect on a narrow
  UP pulse and is not decomposed here.
- The vco was kicked with `.ic` on the ring nodes; period measured on
  rising edges 8-9.
- Not run: `lock_detector` (stale committed PEX, see #157), any PVT grid.
