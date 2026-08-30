# layout/sg13cmos5l-pll/ — the PLL device-level layout on SG13CMOS5L

Issue #24's deliverable (part of #16, the SG13CMOS5L Chipalooza port): a
**device-level layout of every block the committed SG13CMOS5L netlists
declare** (`design/sg13cmos5l/netlist/*.spice`, from #22), drawn headlessly
by `layout/bin/run-pll-cmos5l-layout-flow.sh` and checked in as an
append-only evidence record under `reports/<record-id>/`.

**Read the current record's `record.md` first** — it is the actual pass/fail
evidence, not this file. `reports/LATEST` names it.

```bash
layout/bin/setup-venv.sh                    # once, or after bumping requirements.txt
layout/bin/run-pll-cmos5l-layout-flow.sh    # writes a fresh record
```

**Directory naming.** `layout/sg13cmos5l-pll/`, a sibling of the SG13G2
port's `layout/pll/` rather than a subdirectory of it — mirroring
`2AMLogic/sg13g2-bandgap`'s own `layout/sg13cmos5l-<cell>/` convention and
this repo's `sim/` per-PDK prefixes. The two ports' records are separate
evidence trails with separate `LATEST` pointers on purpose: they are
different PDKs, different decks, and different device sets.

## Status: 477 / 482 devices drawn, **DRC-clean**, and re-extracted matching the schematic — every block composes and re-extracts clean

Per the current record (`reports/LATEST`):

| Block | Devices (schematic) | Drawn | Group DRC clean | Group re-extract matches | Composed | Block DRC | Block re-extract matches schematic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pfd` | 64 | 64 | 64 | 64 | yes | clean | yes |
| `cp` | 14 | 14 | 14 | 14 | yes | clean | yes |
| `loop_filter` | 3 | 1 | 1 | 1 | yes | clean | yes |
| `vco` | 45 | 44 | 44 | 44 | yes | clean | yes |
| `divider_chain` | 316 | 316 | 316 | 316 | yes | clean | yes |
| `lock_detector` | 40 | 38 | 38 | 38 | yes | clean | yes |
| **Total** | **482** | **477** | **477** | **477** | **6/6** | **6/6 clean** | **6/6** |

The 5-device shortfall is exactly this port's five `cap_cmomi` metal-oxide-metal
capacitors (`loop_filter` ×2, `vco` ×1, `lock_detector` ×2) — **never silently
dropped**: every one is recorded in `plan.json` with `kind: "capacitor"` and
carries its own `blocked_reason` naming the two tracked upstream gaps
(see "Friction" below). Every other device this port's schematic declares —
every MOSFET, every poly resistor — draws, passes `klt drc --deck sg13cmos5l`
with zero violations, and re-extracts to the right device class and W/L.

Two verification results worth stating explicitly, because they are the ones
a reviewer would otherwise have to take on trust:

- **The HV (thick-oxide) flavour round-trips.** `klt extract --deck
  sg13cmos5l --pdk ihp-sg13cmos5l` binds every drawn MOS to
  `sg13_hv_nmos`/`sg13_hv_pmos` — the exact models the schematic
  instantiates (DR-002 Decision 0) — not to their LV counterparts, because
  the curated deck models the `ThickGateOx` (44/0) split for real
  (klayout-tools#1416) and this flow draws that marker.
- **No unbiased PMOS bodies.** `unbiased_pmos_body_nets[]` is empty in every
  extraction, because each matched PMOS group gets one shared `NWell` with an
  n+ well tap inside it (`nSD & Activ & NWell`, the tie the deck derives per
  klayout-tools#1414) and an `NWell.pin` (31/2) label naming it. Each NMOS
  group gets the p+ substrate tie (`pSD & (Activ - NWell)`); its body
  terminal extracts onto the deck's own `vsubs` global.

## What it is

- A **complete, schematic-derived device plan** for all six blocks, produced
  by the *same* code the SG13G2 flow uses: `pll_cmos5l_layout.py` imports
  `pll_layout.build_plan`/`shelf_pack`/`_match_group_extraction`/
  `_match_block_extraction` rather than re-deriving them, so the two ports
  cannot drift on what "the schematic's device set" means.
- A **real, reproduced build**: every `mos_array`/`res_array` group is drawn,
  DRC'd, re-extracted, and compared against its own schematic-derived
  `(class, W, L, count)` expectation. `drc.<group>.json`/
  `extract.<group>.json` under the current record carry the actual `klt`
  responses.
- A **composed cell per block**: every block's drawn groups are placed into
  one `pll_<block>` cell (shelf-packed, deterministic), then DRC'd and
  re-extracted as a whole, cross-checking the composed cell's device-count
  multiset against the block's schematic-derived totals.
- A **per-block `klt lvs` run** against that block's own committed schematic
  netlist — see "LVS: what the mismatch means" below.

## What it is not

- **Not fully drawn.** The five MoM capacitors are not drawn; see "Friction".
- **Not routed, and therefore not LVS-clean.** Composition is placement only.
  No net is drawn between two devices, no `connectivity`/routing request is
  made, and the plan's own port/net map is not fed to any router. This is the
  same Non-goal the SG13G2 side's `layout/pll/README.md` records for its own
  rung; routing and LVS closure are a later, separate T1 checklist item.
- **Not a considered floorplan.** `shelf_pack` is a deterministic
  left-to-right pack with generous spacing, not a floorplanner. It *is* now
  DRC-checked (which the SG13G2 side's composition never was), but a
  DRC-clean pack is not a good pack.
- **Not post-layout-simulated.** No parasitic extraction, no post-layout PVT
  re-simulation. See "Post-layout PVT: explicitly scoped out" below.

## Why this flow draws its own geometry (and why that is not routing around a deck gap)

The SG13G2 flow never draws anything itself — it drives `klt gen mos_array` /
`klt gen res_array`. That route does not exist on SG13CMOS5L:

```
$ klt gen mos_array --pdk ihp-sg13cmos5l --params '{"flavor":"nfet",...}'
PDK variant 'ihp-sg13cmos5l' is not supported by this generator --
supported families: gf180mcu, sg13g2, sky130
```

…identically for `res_array`, `diff_pair` and `cap_array`. Filed upstream as
**[klayout-tools#1462](https://github.com/2AMLogic/klayout-tools/issues/1462)**.

Drawing the footprints locally (`layout/bin/cmos5l_devices.py`) is the route
`2AMLogic/sg13g2-bandgap` already took for the fleet's first SG13CMOS5L
layout, and that module is an adaptation of its `layout/common_sg13cmos5l.py`
with every constant's PDK source cited. Crucially, **the deck is not routed
around**: the entire verification half — DRC, extraction, device recognition,
LVS — is still `klt`'s, run unmodified against the curated `sg13cmos5l` deck.
The generator gap stays filed and open.

## LVS: what the `mismatch` means

`klt lvs` is run per composed block against that block's own committed
schematic netlist (copied into each record as `<block>.reference.spice`, so
the evidence is self-contained). The result is reported honestly and is
**not** clean, for two separately-attributable reasons:

1. **Three blocks (`pfd`, `cp`, `divider_chain`) convert and compare, and
   report `mismatch` with the device sets matching in count and class
   (64/64, 14/14, 316/316) and *zero* nets matched.** That is this
   increment's own scope showing up, not a deck defect: nothing is routed, so
   there is no net topology to match. It is the expected reading, and it is
   reported rather than suppressed.
2. **Three blocks (`loop_filter`, `vco`, `lock_detector`) cannot be
   converted at all**, because their reference netlists instantiate
   `cap_cmomi` and the curated deck declares no capacitor device class to map
   it to (klayout-tools#1463). Recorded as `not converted`, never as
   "clean".

One caller-side workaround is in the request and is deliberately visible:
`reference.device_map` re-declares `rppd`/`rhigh` as resistors, because
`reference.deck`'s own subckt-call conversion table is MOS-only even for a
deck that recognises those resistors for extraction — filed as
**[klayout-tools#1464](https://github.com/2AMLogic/klayout-tools/issues/1464)**.
`REFERENCE_DEVICE_MAP` in `pll_cmos5l_layout.py` says so at its definition,
so it can be deleted when that lands.

## Post-layout PVT: explicitly scoped out, with a reason

Issue #24's acceptance criteria require post-layout PVT simulation to be
"either delivered, **or** explicitly scoped out with a stated reason and a
named follow-up". It is scoped out. The reason:

- **There is nothing meaningful to re-simulate yet.** Post-layout PVT means
  re-running the corner matrix against a *parasitic-annotated* netlist of the
  real layout. This increment's layout is placement-only — no interconnect
  exists to extract parasitics from — so a "post-layout" PVT run here would
  re-simulate the schematic with extra steps and report a result that looks
  like validation but is not.
- **The PEX half is independently unproven on this deck.** `klt extract
  --parasitics` rejects the `sg13cmos5l` deck as unknown
  ([klayout-tools#1440](https://github.com/2AMLogic/klayout-tools/issues/1440),
  re-verified open by this pass), and no full post-layout PEX + PVT loop has
  been demonstrated anywhere in this fleet for SG13CMOS5L — the sibling
  `2AMLogic/sg13g2-bandgap#84` is the closest attempt and its own README
  records that no real parasitics were modelled.

Both are tracked as named follow-ups on this repo: **#30** (post-layout PEX
+ PVT re-simulation, itself blocked on klayout-tools#1440) and **#29**
(routing + LVS closure), which #30 depends on. Routing must land first; PEX +
PVT is downstream of it.

## Friction: `klt`/deck gaps found on this port

Per the root `CLAUDE.md` friction protocol, every gap below was checked
against [`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools)
first and filed there — generic tool-gap description only, no design content.

| Gap | Filed | Status | Effect here |
| --- | --- | --- | --- |
| Every `klt gen` generator (`mos_array`, `res_array`, `diff_pair`, `cap_array`) rejects the `ihp-sg13cmos5l` PDK family outright, so a technology `klt` can *verify* it cannot *draw*. `gen.py`'s `_PDK_ROLE_LAYERS` has `sky130`/`gf180mcu`/`sg13g2` entries and no `sg13cmos5l` one. | [klayout-tools#1462](https://github.com/2AMLogic/klayout-tools/issues/1462) (new, filed by this pass) | open | This flow draws its own footprints (see above). |
| The curated `sg13cmos5l` deck's `EXTRACTION_DECK.capacitors` is empty — and CMOS5L has **no MIM at all**, so MoM is the only capacitor the technology offers and there is no fallback class. The deck's own docstring lists this as a follow-on, but no open issue tracked it. | [klayout-tools#1463](https://github.com/2AMLogic/klayout-tools/issues/1463) (new, filed by this pass) | open | The 5 `cap_cmomi` devices are recorded and never drawn; 3 blocks' LVS cannot convert. |
| `klt lvs`'s `reference.deck` subckt-call conversion table is MOS-only, so a deck's own recognised `rppd`/`rhigh` resistors still need an explicit `reference.device_map` — a round-trip asymmetry inside one deck (`klt extract --pdk` emits exactly those subcircuit names). | [klayout-tools#1464](https://github.com/2AMLogic/klayout-tools/issues/1464) (new, filed by this pass) | open | `REFERENCE_DEVICE_MAP` in `pll_cmos5l_layout.py`, deletable when this lands. |
| `klt extract --parasitics` rejects the `sg13cmos5l` deck as "unknown" despite its own `PARASITICS` being defined. | [klayout-tools#1440](https://github.com/2AMLogic/klayout-tools/issues/1440) | open (re-verified by this pass) | Half the reason post-layout PVT is scoped out above. |

**Also confirmed, not a gap** (checked rather than assumed):

- `klt deck info --deck sg13cmos5l` reports `nfet, pfet, resistor` — every
  class this port's drawn devices need is covered; only the capacitor class
  is missing.
- The `sg13cmos5l` deck's `mos_flavours` genuinely models the HV split, its
  `tap_nplus`/`tap_pplus` genuinely derive both tie polarities, and its
  `resistors` genuinely recognise `rppd`/`rhigh` — all three verified by real
  extraction output in this record, not inferred from the deck source.
- **Issue #24's own stated premise was stale.** It assumed
  `layout/requirements.txt`'s previous pin predated SG13CMOS5L deck support.
  It did not: klayout-tools#1398 closed 2026-08-25, the previous pin
  (`5482cfe…`) is dated 2026-08-29 and already carried
  `decks/sg13cmos5l.py`. The pin was bumped anyway (for #1456/#1458 — see
  `layout/requirements.txt`'s header), but the bump was never what unblocked
  this port.

## Directory layout

```
layout/sg13cmos5l-pll/
  README.md                        # this file
  reports/
    LATEST                         # plain-text pointer to the newest record id
    <record-id>/                   # <YYYYMMDD-HHMMSS>-<short-git-sha>[-dirty]
      record.md                    # verdict + per-block table (read first)
      plan.json                    # the schematic-derived plan, every group
      build.json                   # per-group draw/DRC/extract/match + per-block
                                   #   compose/DRC/extract/LVS results
      <group>.gds                  # each matched group's own drawn cell
      drc.<group>.json             # ...its `klt drc --deck sg13cmos5l` result
      extract.<group>.json         # ...and its `klt extract` result
      <group>.extracted.spice      # ...and the netlist that extraction wrote
      compose.<block>.json         # each block's own placement (no routing)
      pll_<block>.gds              # the composed block cell
      drc.pll_<block>.json         # its DRC result
      extract.pll_<block>.json     # its extraction result
      <block>.reference.spice      # the schematic netlist LVS compared against
      lvs.<block>.request.json     # the `klt lvs` request as sent
      lvs.<block>.json             # ...and the response as received
```

`<record-id>` mirrors `sim/`'s own `<YYYYMMDD>-<HHMMSS>-<short-git-sha>`
(UTC) convention, including the `-dirty` suffix's meaning: *the flow that
produced this evidence differed from the named commit*.
