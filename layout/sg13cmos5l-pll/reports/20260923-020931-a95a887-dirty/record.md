# PLL SG13CMOS5L layout record — `20260923-020931-a95a887-dirty`

- **klt**: `klt 0.6.0+gdaf06a51afaf`
- **PDK variant requested**: `ihp-sg13cmos5l`
- **PDK resolved**: `ihp-sg13cmos5l` at `/home/ubuntu/share/pdk` (via search root: ~/share/pdk)
- **Deck**: `sg13cmos5l` (`sha256:1912f17486e78de5259aab5d68533488ebbd239a05018f096217aa62ddee2909`), device classes: nfet, pfet, cap_cmomi, cap_cmomf, resistor

## Verdict: **569 / 569 devices drawn**, **569 / 569 DRC-clean**, **569 / 569 re-extracted matching the schematic**; 6 / 6 blocks composed and routed (295 nets), 6 DRC-clean, 6 device-count-matched, **5 / 6 LVS `match`**

Drawn *and routed* by this repo's own `cmos5l_devices.py` / `cmos5l_route.py` — at an earlier pin, every `klt gen` generator and `klt gen-compose`'s router rejected the `ihp-sg13cmos5l` PDK family (klayout-tools#1462); **this run's own re-probe (below) shows that gap fixed at the current pin**, and this run *also* re-measured `klt gen-compose`'s router against a real multi-net block (`cp`, 18 multi-pin nets), where it routes **2 of 18** nets — klayout-tools#1467, reproduced at this pin, and the reason this flow keeps drawing and routing via this repo's own `cmos5l_devices.py`/`cmos5l_route.py`. **Verified entirely by `klt`**: `klt drc --deck sg13cmos5l`, `klt extract --deck sg13cmos5l --pdk ihp-sg13cmos5l` and `klt lvs`. Every device not drawn is a recorded, tracked upstream gap — see `layout/sg13cmos5l-pll/README.md`'s friction log, never a silent drop.

### Per-block

| Block | Groups drawn | Devices drawn | Devices | Group DRC clean | Group re-extract matches | Composed | Nets routed | Block DRC | Block re-extract matches schematic | Block LVS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pfd` | 4/4 | 66 | 66 | 66 | 66 | yes | 37 | clean | yes | **match** (devices 66/66, nets 37/37) |
| `cp` | 10/10 | 20 | 20 | 20 | 20 | yes | 18 | clean | yes | **match** (devices 20/20, nets 18/18) |
| `loop_filter` | 3/3 | 3 | 3 | 3 | 3 | yes | 3 | clean | yes | **match** (devices 3/3, nets 4/4) |
| `vco` | 15/15 | 45 | 45 | 45 | 45 | yes | 33 | clean | yes | **match** (devices 45/45, nets 33/33) |
| `divider_chain` | 2/2 | 394 | 394 | 394 | 394 | yes | 181 | clean | yes | **match** (devices 394/394, nets 181/181) |
| `lock_detector` | 9/9 | 41 | 41 | 41 | 41 | yes | 23 | clean | yes | **mismatch** (devices 39/41, nets 19/24) |

### Floorplan

- `vco` is composed through the locality floorplan pass (issue #101): total routed wire **12994.65 um** vs **16304.91 um** for the same groups in the pre-#101 single-row order with by-name tracks (of which the track axis alone is worth `15930.51 um`). Per-net lengths, the chosen group order, the member->slot assignment and the track order are in `compose.vco.json` -> `floorplan`.

### Routing

`klt gen-compose` was re-probed this run against a throwaway two-pad cell on this same PDK, once placement-only and once with `routing` — the raw responses are `gen-compose.probe.*.json`:

- placement-only: exit 0 (accepted)
- with `routing`: exit 0 (accepted)

**Both probes above are now accepted.** That rejection was the gap **klayout-tools#1462** tracked, and it **closed upstream on 2026-08-30T04:31Z**; the current pin (see `layout/requirements.txt`) is on or after that fix, so `klt gen-compose`'s router no longer rejects the `ihp-sg13cmos5l` PDK family outright on this throwaway two-pad probe cell. That is **not**, by itself, confirmation that `gen-compose`'s router handles a real multi-net block — which is what the next probe measures.

#### Re-measured against a real block (klayout-tools#1467)

The two-pad probe above is far too small to exercise the finding that actually decides whether this flow's own router can be retired. So `klt gen-compose` is *also* re-probed every run against **`cp`**, this design's smallest composed block — 10 already-drawn group cells, 20 devices, 70 declared ports and 18 multi-pin `connectivity[]` nets, all taken straight from this run's own `plan.json` port→net map and drawn group geometry (never a synthetic case). Raw requests and responses are `gen-compose.probe.block-*.json`:

- declare-only (no `routing`): exit 3, 18 nets validated
- with `routing` (`layer_role: "metal"`): exit 3 — **2 of 18 nets routed**
- with a second routing plane (`routing.cross_block_layer_role`): exit 3

Per-leg rejection reasons on the routed attempt, most frequent first (the full strings are in the committed response):

- 22 × `crosses already-routed net 'DN'`
- 5 × `leg's drawn 0.3um metal overlaps 0.54um^2 of block 'cp_nfet_w2_l0p5''s own drawn geometry on the route layer (port 'BODY`
- 5 × `leg's drawn 0.3um metal overlaps 1.728um^2 of block 'cp_nfet_w2_l0p5''s own drawn geometry on the route layer (port 'BOD`
- 5 × `backbone's 0.3um-wide drawn path crosses 7.43um of block 'cp_nfet_w2_l0p5''s interior on the side *away* from its own pi`
- 5 × `leg's drawn 0.3um metal overlaps 0.5038um^2 of block 'cp_nfet_w8_l1''s own drawn geometry on the route layer (port 'BODY`
- 5 × `leg's drawn 0.3um metal overlaps 6.48um^2 of block 'cp_nfet_w8_l1''s own drawn geometry on the route layer (port 'BODY')`

**klayout-tools#1467 reproduces at this pin.** The first net accepted rejects the rest, and the second routing plane that would let a rejected net move out of the way cannot be selected on this PDK family at all — the error above lists the roles that family *does* expose, and `metal` is the only routing metal among them. That is why a pin bump past klayout-tools#1462 does not retire `cmos5l_route.py`.

#### Generator-drawn footprints, re-measured

klayout-tools#1462 — the gap that made this flow draw its own footprints — is closed, and `klt gen mos_array`/`res_array` do now draw on `ihp-sg13cmos5l`. Drawing is not the bar, though: a generator-drawn footprint has to carry the **ratified thick-oxide flavour** (DR-002 Decision 0), put a **biased, schematic-named body** under every PMOS, and report **terminal columns at least 0.6 µm apart** so `cmos5l_route.py`'s riser scheme can escape them. Each is measured below on this design's own group parameters, with the raw responses in `gen.probe.*.json` / `drc.genprobe_*.json` / `extract.genprobe_*.json`:

| Generator probe | Source group | Draws | DRC | Extracts as | Riser column pitch | Body port | Unbiased PMOS bodies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mos_array` (`mos_nfet`) | `cp_nfet_w2_l0p5` | yes | clean | `nfet`×2 → `sg13_lv_nmos` | 0.46 µm ❌ under 0.6 µm | **no** | 0 |
| `mos_array` (`mos_pfet`) | `cp_pfet_w5_l0p5` | yes | clean | `pfet`×2 → `sg13_lv_pmos` | 0.46 µm ❌ under 0.6 µm | **no** | 0 |
| `res_array` (`res`) | `loop_filter_resrppd_w0p6_l810` | yes | clean | `rppd`×1 | 810.42 µm ✅ | **no** | 0 |

`drc_hints.notes[]` the generator itself reported on these requests:

- `params.voltage_flavor 'thick_oxide' has no marker layer resolved for the resolved PDK family ('sg13cmos5l') -- no marker was drawn`

Interconnect is therefore drawn by `cmos5l_route.py`: one vertical `Metal2` riser per device terminal, one horizontal `Metal3` trunk per net in a channel above the row, `Via1`/`Via2` between them, and the net name written on `Metal3.pin` (30/2) — the layer this deck's own `EXTRACTION_DECK.metal_labels` reads. Every net and every terminal's net membership comes from `plan.json`'s own `groups[].members[].ports` map, which is derived from the committed schematic netlist rather than typed in.

| Block | Terminals routed | Nets | Wire length (µm) | Nets the layout cannot complete |
| --- | --- | --- | --- | --- |
| `pfd` | 202 | 37 | 8650.82 | — |
| `cp` | 70 | 18 | 2336.15 | — |
| `loop_filter` | 6 | 3 | 1090.2 | — |
| `vco` | 139 | 33 | 12994.65 | — |
| `divider_chain` | 1184 | 181 | 234509.06 | — |
| `lock_detector` | 124 | 23 | 10076.41 | — |

### Devices recorded but never drawn

- none: every planned device was drawn.

### LVS status

`klt lvs` is run per composed block against that block's own committed schematic netlist (derived into the plain-element reference form and committed as `<block>.reference.spice`, so this evidence is self-contained). Per-block, read out of `lvs.<block>.json` rather than asserted:

- `pfd` — **match**, devices 66/66, nets 37/37, pins 37/6; `mismatch_count` 1 (topology.flattened: 1)
- `cp` — **match**, devices 20/20, nets 18/18, pins 18/9; `mismatch_count` 1 (topology.flattened: 1)
- `loop_filter` — **match**, devices 3/3, nets 4/4, pins 4/2; `mismatch_count` 2 (topology: 2)
- `vco` — **match**, devices 45/45, nets 33/33, pins 33/6; `mismatch_count` 1 (topology.flattened: 1)
- `divider_chain` — **match**, devices 394/394, nets 181/181, pins 181/12; `mismatch_count` 1 (topology.flattened: 1)
- `lock_detector` — **mismatch**, devices 39/41, nets 19/24, pins 23/5; `mismatch_count` 6 (device.unmatched: 2, net.unmatched: 3, topology.flattened: 1)

The reference for every block is the plain-element text this run itself derived from the committed schematic netlist and committed as `<block>.reference.spice`: MOS/resistor `X` cards converted by `klayout_tools.netlist_normalize` (the same conversion `reference.form: "subckt-call"` performs), and each `cap_cmomi` card rewritten into the `X ... PARAMS: W= L=` shape `klt lvs`'s custom-device-class reader (klayout-tools#1942/#1944, carried at this repo's pin) recognises, with `m=` expanded one card per unit to match the one-marker-per-unit footprint. The two-step rewrite is caller-side because `subckt-call`'s converter and that reader cannot yet be selected together in one request -- see the README's friction log for the filed gap.

### Device flavor

sg13_hv_nmos/sg13_hv_pmos (3.3V thick-oxide CMOS) throughout, per spec/decision-records/DR-002-supply-device-flavor.md Decision 0

See `plan.json` for the full derived device plan, `build.json` for the per-group and per-block results, and `drc.<cell>.json` / `extract.<cell>.json` / `lvs.<block>.json` for the raw `klt` responses each claim above was read out of.
