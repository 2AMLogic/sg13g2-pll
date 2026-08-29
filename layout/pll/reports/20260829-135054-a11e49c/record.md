# PLL layout record — `20260829-135054-a11e49c`

- **klt**: `klt 0.3.0+g6d2028a32bfd`
- **PDK variant requested**: `ihp-sg13g2`
- **PDK resolved**: `ihp-sg13g2` at `/home/ubuntu/share/pdk` (via search root: ~/share/pdk)

## Verdict: **0 / 482 devices drawn**

**Every planned device group failed to draw.** This is a real, reproduced upstream tool gap, not a config mistake in this flow — see "Friction" below and `layout/pll/README.md`'s own friction log for the full citations (klayout-tools#1450, #1451).

### Per-block

| Block | Groups drawn | Devices drawn | Device count |
| --- | --- | --- | --- |
| `pfd` | 0/4 | 0 | 64 |
| `cp` | 0/8 | 0 | 14 |
| `loop_filter` | 0/3 | 0 | 3 |
| `vco` | 0/15 | 0 | 45 |
| `divider_chain` | 0/2 | 0 | 316 |
| `lock_detector` | 0/5 | 0 | 40 |

### Friction — captured `klt` responses, one per distinct failure

- (e.g. `pfd_nfet_w2_l0p5`): generator 'mos_array': PDK family 'sg13g2' is not yet supported by this generator -- the unit device's gate-poly landing pad trips this family's gatpoly.separation.activ.1 DRC rule (see docs/cli/gen.md's 'PDK-family support' section)
- (e.g. `loop_filter_resrppd_w4_l120`): generator 'res_array': params.flavor 'rppd' is not a recognised poly-resistor flavour for PDK family 'sg13g2' -- supported flavours: generic
- (e.g. `loop_filter_XC1`): no klt gen generator draws a MIM capacitor for sg13g2 on any family (cap_array is sky130-only), and the curated sg13g2 extraction deck has no capacitor device class either (klayout-tools#1233, already tracked) -- out of scope per this issue's own Non-goals, never attempted
- (e.g. `vco_resrhigh_w0p5_l8`): generator 'res_array': params.flavor 'rhigh' is not a recognised poly-resistor flavour for PDK family 'sg13g2' -- supported flavours: generic

### Device flavor

sg13_hv_nmos/sg13_hv_pmos (3.3V thick-oxide CMOS) throughout, per spec/decision-records/DR-002-supply-device-flavor.md Decision 0

See `plan.json` for the full derived device plan (every group's `klt gen` request + schematic port/net map) and, if this run attempted a build, `build.json` / `gen.<group>.json` for the per-group results.
