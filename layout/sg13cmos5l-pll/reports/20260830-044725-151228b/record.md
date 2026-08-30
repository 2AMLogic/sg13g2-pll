# PLL SG13CMOS5L layout record — `20260830-044725-151228b`

- **klt**: `klt 0.3.0+g04c0fa912213`
- **PDK variant requested**: `ihp-sg13cmos5l`
- **PDK resolved**: `ihp-sg13cmos5l` at `/Users/rwalters/share/pdk` (via search root: ~/share/pdk)
- **Deck**: `sg13cmos5l` (`sha256:3a7a3bb0ef9533e0f5bff10e84ee26c3df1c56c13cea4048412f686944d917f9`), device classes: nfet, pfet, resistor

## Verdict: **477 / 482 devices drawn**, **477 / 482 DRC-clean**, **477 / 482 re-extracted matching the schematic**; 6 / 6 blocks composed and routed (252 nets), 6 DRC-clean, 6 device-count-matched, **3 / 6 LVS `match`**

Drawn *and routed* by this repo's own `cmos5l_devices.py` / `cmos5l_route.py` — at this repo's pin every `klt gen` generator, and `klt gen-compose`'s router, rejects the `ihp-sg13cmos5l` PDK family (the gap klayout-tools#1462 tracked, **closed upstream 2026-08-30, after this pin**; re-probed below), and past that fix `gen-compose` still routes 1 of 13 nets on this design's smallest block (klayout-tools#1467). **Verified entirely by `klt`**: `klt drc --deck sg13cmos5l`, `klt extract --deck sg13cmos5l --pdk ihp-sg13cmos5l` and `klt lvs`. Every device not drawn is a recorded, tracked upstream gap — see `layout/sg13cmos5l-pll/README.md`'s friction log, never a silent drop.

### Per-block

| Block | Groups drawn | Devices drawn | Devices | Group DRC clean | Group re-extract matches | Composed | Nets routed | Block DRC | Block re-extract matches schematic | Block LVS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pfd` | 4/4 | 64 | 64 | 64 | 64 | yes | 36 | clean | yes | **match** (devices 64/64, nets 36/36) |
| `cp` | 8/8 | 14 | 14 | 14 | 14 | yes | 16 | clean | yes | **match** (devices 14/14, nets 16/16) |
| `loop_filter` | 1/3 | 1 | 3 | 1 | 1 | yes | 2 (3 incomplete) | clean | yes | not converted |
| `vco` | 14/15 | 44 | 45 | 44 | 44 | yes | 33 (2 incomplete) | clean | yes | not converted |
| `divider_chain` | 2/2 | 316 | 316 | 316 | 316 | yes | 142 | clean | yes | **match** (devices 316/316, nets 142/142) |
| `lock_detector` | 3/5 | 38 | 40 | 38 | 38 | yes | 23 (3 incomplete) | clean | yes | not converted |

### Routing

`klt gen-compose` was re-probed this run against a throwaway two-pad cell on this same PDK, once placement-only and once with `routing` — the raw responses are `gen-compose.probe.*.json`:

- placement-only: exit 0 (accepted)
- with `routing`: exit 1 (rejected) — `PDK variant 'ihp-sg13cmos5l' is not supported by this generator -- supported families: gf180mcu, sg13g2, sky130`

That rejection is the gap **klayout-tools#1462** tracked, and it **closed upstream on 2026-08-30T04:31Z** — after this repo's `layout/requirements.txt` pin, which is why the probe above still rejects. Measured separately at that fix's own merge commit (`b10fa3c`), `klt gen mos_array --pdk ihp-sg13cmos5l` does now draw and `gen-compose` does accept a `routing` block — but on `cp`, the smallest block here, it routes **1 of 13 nets**, rejecting the rest with `crosses already-routed net`, because it has no track or layer assignment between nets. Filed upstream as **klayout-tools#1467**. A pin bump therefore does not retire this flow's own router; see `layout/sg13cmos5l-pll/README.md`'s friction log.

Interconnect is therefore drawn by `cmos5l_route.py`: one vertical `Metal2` riser per device terminal, one horizontal `Metal3` trunk per net in a channel above the row, `Via1`/`Via2` between them, and the net name written on `Metal3.pin` (30/2) — the layer this deck's own `EXTRACTION_DECK.metal_labels` reads. Every net and every terminal's net membership comes from `plan.json`'s own `groups[].members[].ports` map, which is derived from the committed schematic netlist rather than typed in.

| Block | Terminals routed | Nets | Wire length (µm) | Nets the layout cannot complete |
| --- | --- | --- | --- | --- |
| `pfd` | 196 | 36 | 8167.52 | — |
| `cp` | 50 | 16 | 1414.17 | — |
| `loop_filter` | 2 | 2 | 9.0 | `NZ`, `VCTRL`, `VSS` |
| `vco` | 137 | 33 | 7177.91 | `GND_VCO`, `VDD_VCO` |
| `divider_chain` | 950 | 142 | 147145.24 | — |
| `lock_detector` | 115 | 23 | 3033.21 | `ERRD`, `VSS`, `VWIN` |

A net listed as incomplete is routed between the terminals that *do* exist and reported here with the undrawn device's own blocked reason — never dropped, never counted as fully routed. Grouped by reason (the full text is in each block's own `compose.<block>.json` and in `plan.json`'s `blocked_reason`):

- `NZ` (missing `loop_filter_XC1.TOP`), `VSS` (missing `loop_filter_XC1.BOT`), `VCTRL` (missing `loop_filter_XC2.TOP`), `VSS` (missing `loop_filter_XC2.BOT`), `VDD_VCO` (missing `vco_XCDECAP.TOP`), `GND_VCO` (missing `vco_XCDECAP.BOT`), `VWIN` (missing `lock_detector_XCW.TOP`), `VSS` (missing `lock_detector_XCW.BOT`), `ERRD` (missing `lock_detector_XDW.XC1.TOP`), `VSS` (missing `lock_detector_XDW.XC1.BOT`)
  - reason: SG13CMOS5L has no MIM capacitor at all (its plate layers are on cmos5l's own DRC/LVS forbidden-layer lists), so this design's MIM->MoM swap (DR-004 / issue #22) lands on cap_cmomi -- and neither half of the tooling covers it. Draw side: klt gen cap_array reports 'PDK family sg13cmos5l has no MiM capacitor plate layers configured' -- re-measured for issue #29 at klayout-tools main (b10fa3c), i.e. *after* klayout-tools#1462 closed and gave the family its role-layer table, so the family gap #1462 tracked is no longer the reason; what remains is that MoM has no generator on any family. Verify side: the curated sg13cmos5l extraction deck's EXTRACTION_DECK.capacitors is still empty, so a hand-drawn MoM capacitor extracts as no device at all (klayout-tools#1463, open, filed by issue #24's pass; klayout-tools#1466 is the follow-on it spawned on what device-recognition shape a MoM plate pair actually needs). Recorded here, never drawn, never silently dropped

### Devices recorded but never drawn

- `lock_detector_XCW`, `lock_detector_XDW.XC1`, `loop_filter_XC1`, `loop_filter_XC2`, `vco_XCDECAP` — SG13CMOS5L has no MIM capacitor at all (its plate layers are on cmos5l's own DRC/LVS forbidden-layer lists), so this design's MIM->MoM swap (DR-004 / issue #22) lands on cap_cmomi -- and neither half of the tooling covers it. Draw side: klt gen cap_array reports 'PDK family sg13cmos5l has no MiM capacitor plate layers configured' -- re-measured for issue #29 at klayout-tools main (b10fa3c), i.e. *after* klayout-tools#1462 closed and gave the family its role-layer table, so the family gap #1462 tracked is no longer the reason; what remains is that MoM has no generator on any family. Verify side: the curated sg13cmos5l extraction deck's EXTRACTION_DECK.capacitors is still empty, so a hand-drawn MoM capacitor extracts as no device at all (klayout-tools#1463, open, filed by issue #24's pass; klayout-tools#1466 is the follow-on it spawned on what device-recognition shape a MoM plate pair actually needs). Recorded here, never drawn, never silently dropped

### LVS status

`klt lvs` is run per composed block against that block's own committed schematic netlist (copied into this record as `<block>.reference.spice`, so this evidence is self-contained). Per-block, read out of `lvs.<block>.json` rather than asserted:

- `pfd` — **match**, devices 64/64, nets 36/36, pins 36/6; `mismatch_count` 1 (topology.flattened: 1)
- `cp` — **match**, devices 14/14, nets 16/16, pins 16/9; `mismatch_count` 1 (topology.flattened: 1)
- `loop_filter` — **not converted**: could not convert subckt-call reference netlist './loop_filter.reference.spice' to plain-element form: subcircuit 'cap_cmomi' is not a known device for the requested deck (known: rhigh, rppd, sg13_hv_nmos, sg13_hv_pmos, sg13_lv_nmos, sg13_lv_pmos); if it is a real device, pass reference.device_map to map it explicitly
  - secondary probe (`lvs.loop_filter.cap-probe.json`), reference-side `cap_cmomi` mapped so the compare runs anyway: **mismatch**, devices 0/3, nets 0/4, pins 5/2; `mismatch_count` 14 (device.unmatched: 4, net.unmatched: 7, topology: 3)
    unmatched devices: 2 x `CAP_CMOMI (reference)`, 1 x `RPPD (reference)`, 1 x `rppd (layout)`
- `vco` — **not converted**: could not convert subckt-call reference netlist './vco.reference.spice' to plain-element form: subcircuit 'cap_cmomi' is not a known device for the requested deck (known: rhigh, rppd, sg13_hv_nmos, sg13_hv_pmos, sg13_lv_nmos, sg13_lv_pmos); if it is a real device, pass reference.device_map to map it explicitly
  - secondary probe (`lvs.vco.cap-probe.json`), reference-side `cap_cmomi` mapped so the compare runs anyway: **mismatch**, devices 38/45, nets 25/34, pins 33/6; `mismatch_count` 16 (device.unmatched: 13, net.merged: 1, topology: 1, topology.flattened: 1)
    unmatched devices: 1 x `CAP_CMOMI (reference)`, 1 x `RHIGH (reference)`, 5 x `RPPD (reference)`, 1 x `rhigh (layout)`, 5 x `rppd (layout)`
- `divider_chain` — **match**, devices 316/316, nets 142/142, pins 142/12; `mismatch_count` 1 (topology.flattened: 1)
- `lock_detector` — **not converted**: could not convert subckt-call reference netlist './lock_detector.reference.spice' to plain-element form: subcircuit 'cap_cmomi' is not a known device for the requested deck (known: rhigh, rppd, sg13_hv_nmos, sg13_hv_pmos, sg13_lv_nmos, sg13_lv_pmos); if it is a real device, pass reference.device_map to map it explicitly
  - secondary probe also could not convert: could not convert subckt-call reference netlist './lock_detector.reference.spice' to plain-element form: device 'C1' (subcircuit 'cap_cmomi'): m=2 describes a multi-finger/multiplied device the curated plain-element form cannot represent; flatten it in the schematic netlist (one device per drawn gate) before comparing

A block whose reference netlist instantiates a MoM capacitor does not convert: `klt lvs`'s `subckt-call` converter has no `cap_cmomi` entry for this deck, because the deck declares no capacitor device class at all (klayout-tools#1463). That is recorded above as `not converted` with `klt lvs`'s own message, never as "clean" and never waived. The secondary probe under each such block maps the capacitor on the *reference* side only — which converts, since `device_map`'s `kind` vocabulary is caller-side — so the comparison runs and the undrawn capacitors show up as `device.unmatched` instead of hiding behind a conversion failure. It is a diagnostic, not a verdict: a layout that provably cannot carry the device cannot match a reference that declares it.

One probe result above is **not** capacitor-attributable and is called out rather than absorbed: the `net.merged` entry, and the poly resistors unmatched on *both* sides alongside it. Those blocks' resistors declare their bulk terminal on the schematic's own floating `sub!` global, while the layout puts every drawn resistor's bulk on the curated deck's real substrate net (`vsubs`) — which the NMOS body ties also land on, so the layout has one substrate node where the reference has two. That is a schematic-netlist property, not a routing or deck defect, and it only shows up on the three blocks that carry both a resistor and a capacitor. It is recorded here rather than resolved: changing which node a device's bulk is declared on is a schematic change, and this increment does not make one.

### Device flavor

sg13_hv_nmos/sg13_hv_pmos (3.3V thick-oxide CMOS) throughout, per spec/decision-records/DR-002-supply-device-flavor.md Decision 0

See `plan.json` for the full derived device plan, `build.json` for the per-group and per-block results, and `drc.<cell>.json` / `extract.<cell>.json` / `lvs.<block>.json` for the raw `klt` responses each claim above was read out of.
