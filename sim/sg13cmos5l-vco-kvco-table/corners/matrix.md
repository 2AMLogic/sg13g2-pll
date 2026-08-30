# Corner matrix — `sg13cmos5l-vco-kvco-table`

**Claim under test**: `spec/porting-plan.md` row 4/5 (Kvco bound / band-
selection rule) obligates "a per-band, per-corner Kvco table" for the
SG13CMOS5L `vco`. This record measures that table directly with a real
open-loop transient sweep, rather than assuming any prior PDK's numbers.

| Axis | Values | Why |
|---|---|---|
| MOS process corner | `mos_tt`, `mos_ss`, `mos_ff` (`cornerMOShv.lib`) | The ring/bias core's own dominant speed axis (`sg13_hv_nmos`/`sg13_hv_pmos`, PSP103). The installed deck also offers `mos_sf`/`mos_fs` (NMOS/PMOS split corners); this record does not sweep those two independently — see "Why 3 bundles, not the full cross product" below |
| Resistor process corner | `res_typ`, `res_wcs`, `res_bcs` (`cornerRES.lib`) | `rppd`'s (the V-I converter's degeneration resistors) own corner axis, paired 1:1 with the MOS corner into a single bundle rather than crossed independently — see below |
| Temperature | 27C, 125C, -40C | Standard PVT bracket, one value per bundle (paired with the MOS/RES corner it plausibly co-occurs with, not crossed independently) |
| Band select (`B0`,`B1`) | `00`, `10`, `01`, `11` (each bit 0V or 3.3V) | The VCO's full 2-bit coarse band-select code — every code, not a subset, since the whole point of this row is a *per-band* table |
| `VCTRL` | 0.3, 0.9, 1.5, 2.1, 2.7 V | 5 points spanning most of the 0-3.3V rail (kept off the two rail extremes, where the V-I converter's own degeneration devices approach cutoff/triode edges that are a separate characterization question from the table's own slope) |
| Supply | 3.3V only, not swept | DR-004 (already ratified) confirms this design's internal domains are all-3.3V; no 1.2V corner applies to an internal block like the VCO itself (only the not-yet-drawn wrapper boundary would see 1.2V) |

Total: 3 bundles x 4 band codes x 5 VCTRL points = **60 transient runs**,
`../corners/results.csv`.

## Why 3 bundles, not the full cross product

The installed deck's own corner libraries offer 5 MOS process corners
(`mos_tt/ss/ff/sf/fs`) x 3 resistor corners (`res_typ/bcs/wcs`) x an
unbounded temperature choice — a full cross product (even at just 3
temperatures) is 45 MOS/RES corner pairs x 3 temps x 4 bands x 5 VCTRL
points = 2700 transient runs, which does not fit this issue's own
one-session budget (`spec/decision-records/DR-003-sg13cmos5l-port-
readiness.md`'s own Context section already names exactly this kind of
scope explosion as the reason the full campaign is decomposed across
issues #23/#27).

This record instead uses the same **3-bundle PVT convention** (typical /
slow / fast) common to first-pass ring-oscillator characterization: each
bundle pairs the MOS corner with the resistor corner and temperature most
plausibly correlated with it (not an independent, uncorrelated axis
combination), covering the dominant speed variation with a tractable run
count. **`mos_sf`/`mos_fs`** (the NMOS/PMOS-split corners, where one device
type is fast and the other slow) are **not swept** in this record — they
are a *duty-cycle* risk (`spec/porting-plan.md` row 13's own carried-forward
"matched PMOS-head/NMOS-tail" concern), not primarily a frequency/Kvco one,
and are named here as an explicitly open corner for a future duty-cycle
sweep, not silently dropped.

| Bundle | MOS corner | RES corner | Temp | Rationale |
|---|---|---|---|---|
| `typ` | `mos_tt` | `res_typ` | 27C | Nominal / typical-mean corner |
| `slow` | `mos_ss` | `res_wcs` | 125C | Slow transistors + high resistance + high temp: the design's own slowest, worst-case-frequency-floor corner |
| `fast` | `mos_ff` | `res_bcs` | -40C | Fast transistors + low resistance + low temp: the design's own fastest, worst-case-frequency-ceiling corner |

## Tooling note: XCDECAP is stripped from this testbench's own netlist copy

See `../testbench/run.sh`'s own header comment for the full rationale
(ideal-voltage-source drive makes XCDECAP's value provably inconsequential
to this specific measurement) and a host-specific OSDI-loading finding
recorded there. `../netlist-snapshots/vco.spice` itself is the exact,
unmodified frozen export — nothing about the committed design changes.
