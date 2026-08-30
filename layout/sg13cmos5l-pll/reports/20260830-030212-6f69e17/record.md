# PLL SG13CMOS5L layout record — `20260830-030212-6f69e17`

- **klt**: `klt 0.3.0+g04c0fa912213`
- **PDK variant requested**: `ihp-sg13cmos5l`
- **PDK resolved**: `ihp-sg13cmos5l` at `/home/ubuntu/share/pdk` (via search root: ~/share/pdk)
- **Deck**: `sg13cmos5l` (`sha256:3a7a3bb0ef9533e0f5bff10e84ee26c3df1c56c13cea4048412f686944d917f9`), device classes: nfet, pfet, resistor

## Verdict: **477 / 482 devices drawn**, **477 / 482 DRC-clean**, **477 / 482 re-extracted matching the schematic**; 6 / 6 blocks composed, 6 DRC-clean, 6 device-count-matched

Drawn by this repo's own `cmos5l_devices.py` footprints (every `klt gen` generator rejects the `ihp-sg13cmos5l` PDK family — klayout-tools#1462); **verified entirely by `klt`**: `klt drc --deck sg13cmos5l` and `klt extract --deck sg13cmos5l --pdk ihp-sg13cmos5l`. Every device not drawn is a recorded, tracked upstream gap — see `layout/sg13cmos5l-pll/README.md`'s friction log, never a silent drop.

### Per-block

| Block | Groups drawn | Devices drawn | Devices | Group DRC clean | Group re-extract matches | Composed | Block DRC | Block re-extract matches schematic | Block LVS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pfd` | 4/4 | 64 | 64 | 64 | 64 | yes | clean | yes | mismatch (devices 64/64, nets matched 0) |
| `cp` | 8/8 | 14 | 14 | 14 | 14 | yes | clean | yes | mismatch (devices 14/14, nets matched 0) |
| `loop_filter` | 1/3 | 1 | 3 | 1 | 1 | yes | clean | yes | not converted |
| `vco` | 14/15 | 44 | 45 | 44 | 44 | yes | clean | yes | not converted |
| `divider_chain` | 2/2 | 316 | 316 | 316 | 316 | yes | clean | yes | mismatch (devices 316/316, nets matched 0) |
| `lock_detector` | 3/5 | 38 | 40 | 38 | 38 | yes | clean | yes | not converted |

### Devices recorded but never drawn

- `lock_detector_XCW`, `lock_detector_XDW.XC1`, `loop_filter_XC1`, `loop_filter_XC2`, `vco_XCDECAP` — SG13CMOS5L has no MIM capacitor at all (its plate layers are on cmos5l's own DRC/LVS forbidden-layer lists), so this design's MIM->MoM swap (DR-004 / issue #22) lands on cap_cmomi -- and neither half of the tooling covers it: every klt gen generator rejects the ihp-sg13cmos5l PDK family outright (klayout-tools#1462, filed by issue #24's pass), and the curated sg13cmos5l extraction deck's EXTRACTION_DECK.capacitors is empty, so a hand-drawn MoM capacitor would extract as no device at all (klayout-tools#1463, also filed by that pass). Recorded here, never drawn, never silently dropped

### LVS status

`klt lvs` is run per composed block against that block's own committed schematic netlist (copied into this record as `<block>.reference.spice`). **A `mismatch` verdict here is expected and is this increment's own scope, not a deck defect**: composition is placement only — no net is drawn between two devices — so the device sets match in count and class while zero nets match. Blocks whose reference netlist instantiates a MoM capacitor cannot be converted at all (klayout-tools#1463: the curated deck declares no capacitor device class, so there is nothing to map it to). Routing and LVS closure are a separate T1 checklist rung.

### Device flavor

sg13_hv_nmos/sg13_hv_pmos (3.3V thick-oxide CMOS) throughout, per spec/decision-records/DR-002-supply-device-flavor.md Decision 0

See `plan.json` for the full derived device plan, `build.json` for the per-group and per-block results, and `drc.<cell>.json` / `extract.<cell>.json` / `lvs.<block>.json` for the raw `klt` responses each claim above was read out of.
