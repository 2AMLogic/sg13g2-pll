# Corner matrix — `sg13g2-vco-kvco-table`

**Claim under test**: `spec/porting-plan.md` rows 1/4/5 (output band / Kvco
bound / band-selection rule) obligate a re-derived output frequency band and
"a per-band, per-corner Kvco table" for the SG13G2 `vco` — the *original*
design this repo's SG13CMOS5L port (`sg13cmos5l-vco-kvco-table`, issue #23)
is itself a port *of* (`spec/decision-records/DR-005-fref-n-vco-band-
reconciliation.md` reconciled `f_ref`/`N` against the SG13CMOS5L-measured
band, 445.3–1562.0 MHz, because no SG13G2 measurement existed). This record
measures the SG13G2 table directly with a real open-loop transient sweep,
rather than continuing to borrow the port's own reconciliation for the
design it was ported from.

| Axis | Values | Why |
|---|---|---|
| MOS process corner | `mos_tt`, `mos_ss`, `mos_ff` (`cornerMOShv.lib`) | The ring/bias core's own dominant speed axis (`sg13_hv_nmos`/`sg13_hv_pmos`, PSP103). The installed deck also offers `mos_sf`/`mos_fs` (NMOS/PMOS split corners); this record does not sweep those two independently — see "Why 3 bundles, not the full cross product" below |
| Resistor process corner | `res_typ`, `res_wcs`, `res_bcs` (`cornerRES.lib`) | `rppd`/`rhigh`'s (the V-I converter's degeneration/bias resistors) own corner axis, paired 1:1 with the MOS corner into a single bundle rather than crossed independently — see below |
| Capacitor process corner | `cap_typ`, `cap_wcs`, `cap_bcs` (`cornerCAP.lib`) | New relative to the SG13CMOS5L campaign: `vco.XCDECAP` is a `cap_cmim` MIM decap, and `sg13g2-lock-detector-window`'s own campaign already established that `cap_cmim` (unlike SG13CMOS5L's `cap_cmomi`) has a real characterised process corner (±10% area+perimeter, `cornerCAP.lib`'s own `.LIB cap_typ/cap_bcs/cap_wcs` sections). Bundled 1:1 with the MOS/RES corner rather than crossed independently, same convention as the other two axes — see "Why XCDECAP is kept, not stripped, here" below for why this axis is swept at all despite provably not moving this testbench's own measured node |
| Temperature | 27C, 125C, -40C | Standard PVT bracket, one value per bundle (paired with the MOS/RES/CAP corner it plausibly co-occurs with, not crossed independently) |
| Band select (`B0`,`B1`) | `00`, `10`, `01`, `11` (each bit 0V or 3.3V) | The VCO's full 2-bit coarse band-select code — every code, not a subset, since the whole point of rows 4/5 is a *per-band* table |
| `VCTRL` | 0.3, 0.9, 1.5, 2.1, 2.7 V | 5 points spanning most of the 0–3.3V rail, identical to the SG13CMOS5L sibling's own points, for direct cross-PDK comparability (kept off the two rail extremes, where the V-I converter's own degeneration devices approach cutoff/triode edges that are a separate characterization question from the table's own slope) |
| Supply (`VDD_VCO`) | 3.3V only, not swept | `spec/decision-records/DR-002-supply-device-flavor.md` Decision 0 ratifies 3.3V thick-oxide CMOS throughout this design (VCO included) — there is no 1.2V corner for an internal block like the VCO itself. Stated explicitly here rather than silently omitted, per this issue's own instruction |

Total: 3 bundles x 4 band codes x 5 `VCTRL` points = **60 transient runs**,
`../corners/results.csv`.

## Why 3 bundles, not the full cross product

The installed deck's own corner libraries offer 5 MOS process corners
(`mos_tt/ss/ff/sf/fs`) x 3 resistor corners (`res_typ/bcs/wcs`) x 3
capacitor corners (`cap_typ/bcs/wcs`) x an unbounded temperature choice — a
full cross product (even at just 3 temperatures) is 135 MOS/RES/CAP corner
triples x 3 temps x 4 bands x 5 `VCTRL` points, which does not fit this
issue's own one-session budget, same reasoning the SG13CMOS5L sibling's
`matrix.md` already gives for its own (smaller, 2-axis) cross product.

This record instead uses the same **3-bundle PVT convention** (typical /
slow / fast) the SG13CMOS5L sibling and `sg13g2-lock-detector-window`'s own
main grid both use: each bundle pairs the MOS corner with the resistor and
capacitor corner and temperature most plausibly correlated with it (not an
independent, uncorrelated axis combination), covering the dominant speed
variation with a tractable run count. **`mos_sf`/`mos_fs`** (the NMOS/PMOS-
split corners, where one device type is fast and the other slow) are **not
swept** in this record — mirroring the SG13CMOS5L sibling's own disposition,
they are a *duty-cycle* risk (`spec/porting-plan.md` row 13's carried-forward
"matched PMOS-head/NMOS-tail" concern), not primarily a frequency/Kvco one,
and are named here as an explicitly open corner for a future SG13G2
duty-cycle sweep (the SG13G2 twin of `sg13cmos5l-vco-duty-cycle`, not
attempted by this issue), not silently dropped.

| Bundle | MOS corner | RES corner | CAP corner | Temp | Rationale |
|---|---|---|---|---|---|
| `typ` | `mos_tt` | `res_typ` | `cap_typ` | 27C | Nominal / typical-mean corner |
| `slow` | `mos_ss` | `res_wcs` | `cap_wcs` | 125C | Slow transistors + high resistance + high MIM-cap corner + high temp: the design's own slowest, worst-case-frequency-floor corner |
| `fast` | `mos_ff` | `res_bcs` | `cap_bcs` | -40C | Fast transistors + low resistance + low MIM-cap corner + low temp: the design's own fastest, worst-case-frequency-ceiling corner |

## Why `XCDECAP` is kept, not stripped, here

The SG13CMOS5L sibling's testbench derives a local, `XCDECAP`-commented-out
copy of its frozen netlist snapshot before simulating it, and gives two
reasons: (1) `VDD_VCO`/`GND_VCO` are driven by ideal, zero-impedance DC
voltage sources in that testbench (as they are in this one too), so
`XCDECAP`'s own value cannot affect any node voltage either testbench
measures — an ideal voltage source enforces the node voltage regardless of
any capacitance in parallel with it; and (2) on that campaign's build host,
`cap_cmomi.osdi`/`cap_cmomf.osdi` are x86-64-only tracked binaries that fail
to load on arm64, so stripping `XCDECAP` was also what let that record run
on an arm64 host at all.

Reason (1) applies identically here — this testbench also drives
`VDD_VCO`/`GND_VCO` with ideal DC sources, so `XCDECAP`'s capacitance value
is just as provably inconsequential to the measured `CLK` period. **Reason
(2) does not apply to this PDK**: `vco.XCDECAP` is a `cap_cmim` MIM decap,
which (per `sim/sg13g2-lock-detector-window/testbench/run.sh`'s own header
note, confirmed directly against the installed `ihp-sg13g2` tree before
writing this deck) has **no OSDI object at all** — it is a plain SPICE
`.subckt` resolved via `cornerCAP.lib`'s `.include capacitors_mod.lib`, so
there is no cross-architecture, prebuilt-binary risk for it to begin with.

With the arm64 motivation gone, this record `.include`s the frozen
`../netlist-snapshots/vco.spice` **directly, unmodified** — simpler than the
SG13CMOS5L sibling's derived-copy step, and it is what lets `CORNER_CAP` be
swept as a first-class bundled axis above (mirroring
`sg13g2-lock-detector-window`'s own precedent for `cap_cmim`) even though
this specific `CLK`-period measurement does not depend on which section is
selected. This record makes **no claim whatsoever** about `XCDECAP`'s own
decap-value / supply-decoupling sensitivity — measuring that (the SG13G2
twin of `sg13cmos5l-vco-decap-momcap`) is out of this record's own scope.

## Axes deliberately not swept, and why

- **Supply** (`VDD_VCO`) — fixed at 3.3V, not a corner. See the matrix table
  above (`DR-002` Decision 0).
- **`mos_sf`/`mos_fs`** (split MOS corners) — named above as an explicitly
  open axis for a future duty-cycle-focused record, not this one.
- **`cap_cmim` mismatch/statistical sections** (`cap_typ_mismatch`,
  `cap_typ_stat`, etc., also present in `cornerCAP.lib`) — this record uses
  only the plain process-corner sections (`cap_typ`/`cap_bcs`/`cap_wcs`);
  mismatch between the ring's own five `vco_stage` instances or within
  `XSWB0`/`XSWB1` (the band-select switches) is not modeled, same
  disposition the SG13CMOS5L sibling's own record states for
  `sg13_hv_nmos` mismatch.
- **Temperature independent of the corner bundle** — this record follows the
  same 3-bundle (not full cross-product) convention as every axis above;
  temperature is not swept independently of its paired MOS/RES/CAP corner.
