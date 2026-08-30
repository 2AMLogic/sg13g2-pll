# Corner matrix — `sg13cmos5l-vco-duty-cycle`

**Claim under test**: `spec/porting-plan.md` row 13 (output duty cycle,
45–55% target). That row's disposition is "port the target and the
measurement methodology as-is; re-derive", and it carries gf180-pll's own
finding forward as a design flag: *matched PMOS-head/NMOS-tail starving
devices were not, alone, sufficient to clear the 45% floor at every corner
on gf180*. This record measures the SG13CMOS5L ring's own duty cycle
directly.

| Axis | Values | Why |
|---|---|---|
| MOS process corner | `mos_tt`, `mos_ss`, `mos_ff`, **`mos_sf`, `mos_fs`** (`cornerMOShv.lib`) | All five. `sg13cmos5l-vco-kvco-table/corners/matrix.md` explicitly named `mos_sf`/`mos_fs` as "a *duty-cycle* risk ... named here as an explicitly open corner for a future duty-cycle sweep, not silently dropped" — this record is that sweep, so skipping them would defeat its purpose. They are the corners where the PMOS head and NMOS tail of the starved inverter are *deliberately* mismatched |
| Resistor process corner | paired: `res_typ` with `mos_tt`/`mos_sf`/`mos_fs`, `res_wcs` with `mos_ss`, `res_bcs` with `mos_ff` | The three bundled pairs match the Kvco record's own bundles. `mos_sf`/`mos_fs` are a device-symmetry axis, not a resistor axis, so they run against `res_typ` — the bias `rppd` sets the ring's current, not its rise/fall symmetry |
| Temperature | -40, 27, 125 C | Full bracket at **every** MOS corner (15 PVT points), not one temperature per bundle. Duty cycle turned out to be strongly temperature-dependent (see RECORD-001), so a one-temperature-per-bundle subset would have hidden the dominant axis |
| Band select (`B0`,`B1`) | `00`, `10`, `01`, `11` | All four codes, as row 13's target applies at every band |
| `VCTRL` | 0.3, 0.9, 1.5, 2.1, 2.7 V | The same five points the Kvco record swept, so the two records' operating points line up exactly |
| Supply | 3.3 V only | DR-004 ratifies the internal domains as all-3.3 V; consistent with the Kvco record's own stance |

Total: 5 MOS corners x 3 temperatures x 4 band codes x 5 `VCTRL` points =
**300 transient runs** (`../corners/results.csv`, 300 valid rows, no `NA`).

## Timestep-convergence sub-sweep

Duty cycle is a *difference* of two interpolated threshold crossings, which
makes it the one measurement in this record that could plausibly be a
discretisation artifact rather than circuit behaviour. Four representative
points (including both split corners at their extremes) are re-run at 5 ps
instead of 20 ps — a 4x finer maximum internal timestep — and both values
are recorded in `../corners/tstep_convergence.csv` so the record can state
the observed sensitivity instead of asserting it is small.

## What is NOT swept, and why

- **`XCDECAP`'s MOM-cap value.** Stripped from this testbench's own local
  netlist copy for exactly the reason the Kvco record documents: `VDD_VCO`
  and `GND_VCO` are driven by ideal zero-impedance sources here too, so no
  capacitance in parallel with them can affect any node voltage or supply
  current measured. The frozen snapshot itself is unmodified.
- **Random device mismatch.** No per-instance mismatch model exists for
  `sg13_hv_nmos`/`sg13_hv_pmos` in this campaign. The `mos_sf`/`mos_fs`
  corners bound the *systematic* NMOS-vs-PMOS skew; they say nothing about
  within-die random mismatch between the five ring stages.
- **Loading.** The `CLK` output drives only the block's own two `inv2x_hv`
  output buffers; no external load capacitance is applied.
  `spec/porting-plan.md` row 14's "≤ 50 fF" load condition is a separate
  row this record does not address.
