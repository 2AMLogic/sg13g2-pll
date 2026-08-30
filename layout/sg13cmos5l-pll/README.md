# layout/sg13cmos5l-pll/ — the PLL layout on SG13CMOS5L

Issues #24 (device-level layout) and #29 (routing + LVS closure), both part of
#16, the SG13CMOS5L Chipalooza port: a **routed, DRC-clean, LVS-compared
layout of every block the committed SG13CMOS5L netlists declare**
(`design/sg13cmos5l/netlist/*.spice`, from #22), drawn headlessly by
`layout/bin/run-pll-cmos5l-layout-flow.sh` and checked in as an append-only
evidence record under `reports/<record-id>/`.

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

## Status: routed, DRC-clean, and **LVS `match` on every block whose reference netlist converts**

Per the current record (`reports/LATEST`):

| Block | Devices (schematic) | Drawn | Group DRC clean | Group re-extract matches | Composed + routed | Terminals routed | Nets | Block DRC | Block re-extract matches | **`klt lvs`** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pfd` | 64 | 64 | 64 | 64 | yes | 196 | 36 | clean | yes | **`match`** — devices 64/64, nets 36/36 |
| `cp` | 14 | 14 | 14 | 14 | yes | 50 | 16 | clean | yes | **`match`** — devices 14/14, nets 16/16 |
| `loop_filter` | 3 | 1 | 1 | 1 | yes | 2 | 2 (3 incomplete) | clean | yes | not converted (#1463) |
| `vco` | 45 | 44 | 44 | 44 | yes | 137 | 33 (2 incomplete) | clean | yes | not converted (#1463) |
| `divider_chain` | 316 | 316 | 316 | 316 | yes | 950 | 142 | clean | yes | **`match`** — devices 316/316, nets 142/142 |
| `lock_detector` | 40 | 38 | 38 | 38 | yes | 115 | 23 (3 incomplete) | clean | yes | not converted (#1463) |
| **Total** | **482** | **477** | **477** | **477** | **6/6** | **1450** | **252** | **6/6 clean** | **6/6** | **3 `match`, 3 not converted** |

Three claims in that table are worth stating in words, because they are the
ones a reviewer would otherwise have to take on trust:

- **Every block whose reference netlist `klt lvs` can convert reports
  `status: "match"`, with every device *and every net* matched.** Not "device
  counts agree" — `pfd` matches 36 of 36 nets, `cp` 16 of 16, `divider_chain`
  142 of 142, against the schematic's own net names. The one `mismatch_count`
  entry on each is the `topology.flattened` **warning** `options.flatten_reference`
  always emits; it is a note about the compare, not an unmatched object.
- **The other three cannot be converted at all**, because their reference
  netlists instantiate `cap_cmomi` and the curated deck declares no capacitor
  device class to map it to (klayout-tools#1463). Recorded as `not converted`
  with `klt lvs`'s own message — never as "clean", never waived. Each also
  carries a clearly-labelled *secondary* probe; see "LVS" below.
- **DRC survived routing.** The #24 record's placement-only pack cleared every
  rule with large margins; routing is where spacing rules actually bite, and
  the routed cells are still `klt drc --deck sg13cmos5l` clean at zero
  violations. The four rules the interconnect newly exercises
  (`metal2.width/space`, `via1`/`via2` size, spacing and `metal1.enclosing.via1`)
  are what `cmos5l_devices.py`'s `ROUTE_W_UM`/`ROUTE_PITCH_UM` are sized from,
  each citing the rule id it satisfies.

The 5-device shortfall is exactly this port's five `cap_cmomi`
metal-oxide-metal capacitors (`loop_filter` ×2, `vco` ×1, `lock_detector` ×2)
— **never silently dropped**: every one is recorded in `plan.json` with
`kind: "capacitor"` and its own `blocked_reason`, and every *net* those
capacitors touch is listed in the record as **incomplete**, routed between the
terminals that do exist and reported with the undrawn device's reason
attached.

Two verification results carried over from #24 and re-confirmed by this
record:

- **The HV (thick-oxide) flavour round-trips.** `klt extract --deck
  sg13cmos5l --pdk ihp-sg13cmos5l` binds every drawn MOS to
  `sg13_hv_nmos`/`sg13_hv_pmos` — the exact models the schematic
  instantiates (DR-002 Decision 0) — because the curated deck models the
  `ThickGateOx` (44/0) split for real (klayout-tools#1416).
- **No unbiased PMOS bodies.** `unbiased_pmos_body_nets[]` is empty in every
  extraction. Since #29 the shared `NWell` is labelled with the *schematic's*
  own body net (`VDD`, `VDD_DIV`, `VDD_VCO`) rather than an invented
  `<group>_B`, and both taps are wired into the routing — which is also what
  makes the layout's substrate global and the schematic's ground net the one
  node LVS compares.

**Non-regression at issue #31's own pin bump.** `layout/requirements.txt` was
re-bumped to `fdf04f71ab39159838acb86e63a92d6fa0c714fa` for the *SG13G2*
side's `cap_array`/`cap_cmim` fix (klayout-tools#1461 — see
`layout/pll/README.md`). `layout/bin/run-pll-cmos5l-layout-flow.sh` was
re-run in full as this port's own non-regression check, per this repo's own
bump discipline, and reproduces the identical result: 477 / 482 drawn, 6 / 6
DRC-clean, 3 / 6 LVS `match` — this table is unchanged. One thing *did*
change: the `gen-compose` routing probe (see "Routing" below) now reports
both placement-only and `routing` accepted, because this pin also happens to
carry klayout-tools#1462's fix (merge commit `b10fa3c6e`, closed
2026-08-30T04:31Z) — see the friction log's #1462 row for what that does and
does not mean for this module.

## What it is

- A **complete, schematic-derived device plan** for all six blocks, produced
  by the *same* code the SG13G2 flow uses: `pll_cmos5l_layout.py` imports
  `pll_layout.build_plan`/`_match_group_extraction`/`_match_block_extraction`
  rather than re-deriving them, so the two ports cannot drift on what "the
  schematic's device set" means.
- A **real, reproduced build**: every `mos_array`/`res_array` group is drawn,
  DRC'd, re-extracted, and compared against its own schematic-derived
  `(class, W, L, count)` expectation.
- A **composed and routed cell per block**: groups placed in one row, then
  every device terminal wired to its schematic net (see "Routing"), then
  DRC'd, re-extracted and LVS'd as a whole.
- A **per-block `klt lvs` run** against that block's own committed schematic
  netlist — see "LVS" below.

## Routing: how, and why not `klt gen-compose`

**How.** `layout/bin/cmos5l_route.py` is a per-net-track channel router:

- every device terminal is brought up on its own vertical **Metal2 riser**,
  at its own x column;
- every net gets one horizontal **Metal3 trunk** on its own y track, in a
  channel above the whole block, dropping a `Via2` onto each of its risers;
- the net's name is written on the trunk, on **`Metal3.pin` (30/2)** — the
  layer this deck's `EXTRACTION_DECK.metal_labels` actually reads, *not* the
  `.text` datatype 25 the `sg13g2` deck reads. That distinction is not
  cosmetic: labelling the wrong layer extracts every net as an anonymous
  `$N`, and LVS then compares a correctly-drawn layout against the schematic
  with every net name missing — a silently useless run.

Nothing in it decides *what* connects to what. Every net, and every
terminal's membership in one, is read out of `plan.json`'s own
`groups[].members[].ports` map, which `pll_layout.build_plan` derives from the
committed schematic netlist. Two structural properties follow: riser columns
are unique by construction and the invariant is *checked* (a shared column is
a fatal `RouteError`, never a quietly-dropped net), and trunks never share a
track — so the router cannot draw a short. That is the property that makes an
LVS result off it mean something.

To keep those properties, groups are drawn **one device tall** and placed in a
**single left-to-right row**: a second row, or a shelf wrap, would put two
devices' terminals in one riser column. The cost is width — `divider_chain` is
~1.7 mm across — and 167 mm of total drawn wire. That is a floorplan cost, and
it is a bad floorplan; see "What it is not".

**Why not `klt gen-compose --routing`.** `klt gen-compose` has a router, and
this repo's SG13G2 flow already drives that verb for placement. Two separate,
independently-measured reasons; issue #31's own re-bump changed the status of
the first:

1. **At an earlier pin it could not route on this PDK at all** (routing
   resolves `routing.layer_role` through the same per-PDK-family role→layer
   table every `klt gen` generator uses, and that table had no `sg13cmos5l`
   entry — klayout-tools#1462). **That closed upstream 2026-08-30T04:31Z and
   is present at the current pin**: this repo's own throwaway two-pad probe
   (re-taken on every run, committed as `gen-compose.probe.*.json`) now
   accepts both placement-only and a `routing` block. So this reason no
   longer holds today — see the friction log's #1462 row.
2. **Past that fix, `klt gen-compose`'s router was separately measured
   routing only 1 of 13 nets on a block this design's size** (klayout-tools#1467,
   measured once at `b10fa3c`, *not* re-measured against the current pin by
   this repo's own throwaway two-pad probe, which is too small a cell to
   exercise it). This reason is the one this module still stands on, and it
   is why a pin bump alone does not retire it — a real re-measurement of
   #1467 against a multi-net block at the current pin, and the
   generator-vs-local-footprint decision that would follow from it, is
   tracked separately as **#35** (not this issue's own scope).

## LVS

`klt lvs` is run per composed block against that block's own committed
schematic netlist (copied into each record as `<block>.reference.spice`, so
the evidence is self-contained). Three blocks report `status: "match"` with
every device and every net matched; three cannot be converted, for the
capacitor reason above.

Two caller-side declarations are in the request and are deliberately visible:

- **`reference.device_map` re-declares `rppd`/`rhigh` as resistors**, because
  `reference.deck`'s own subckt-call conversion table is MOS-only even for a
  deck that recognises those resistors for extraction — filed as
  **[klayout-tools#1464](https://github.com/2AMLogic/klayout-tools/issues/1464)**.
  `REFERENCE_DEVICE_MAP` in `pll_cmos5l_layout.py` says so at its definition,
  so it can be deleted when that lands.
- **A clearly-labelled *secondary* probe** runs on each block that fails to
  convert, mapping `cap_cmomi` on the reference side so the comparison runs
  anyway (`lvs.<block>.cap-probe.json`). This corrects a stale premise in
  #24's own record, which said there was "no class to map a MoM capacitor to":
  `device_map`'s `kind` vocabulary is caller-side and *does* accept
  `"capacitor"` on a deck whose `EXTRACTION_DECK.capacitors` is empty. What
  #1463 actually blocks is the **layout** half — a drawn MoM capacitor
  extracts as no device at all — so mapping the reference side alone converts
  the netlist and reports the missing capacitors as `device.unmatched` rather
  than refusing to compare. It is never the headline result: a mismatch this
  flow induced by declaring a device the layout provably cannot carry is a
  diagnostic, not a verdict.

One probe finding is **not** capacitor-attributable and the record calls it
out rather than absorbing it: those blocks' poly resistors declare their bulk
terminal on the schematic's own floating `sub!` global, while the layout puts
every drawn resistor's bulk on the deck's real substrate net (`vsubs`) — which
the NMOS body ties also land on. So the layout has one substrate node where
the reference has two, and the resistors come back unmatched with a
`net.merged` alongside them. That is a schematic-netlist property, not a
routing or deck defect, and it is recorded rather than resolved: changing
which node a device's bulk is declared on is a schematic change, and this
increment does not make one. It affects only the three blocks that already
cannot convert.

## What it is not

- **Not fully drawn.** The five MoM capacitors are not drawn; see "Friction".
  Ten net→pin connections are therefore incomplete, each listed by name in the
  record with the undrawn device that owns the missing pin.
- **Not LVS-clean on all six blocks.** Three are `match`; three cannot be
  converted at all. That is reported as an attributed gap naming
  klayout-tools#1463, never rounded up.
- **Not a considered floorplan — and now visibly so.** Groups are packed one
  device tall in a single row with generous spacing, and every net gets a
  private Metal3 track whether it needs one or not. `divider_chain` is ~1.7 mm
  wide and the six blocks draw 167 mm of wire between them. It is DRC-clean and
  it is electrically the schematic; it is not an area-, parasitic- or
  matching-aware layout, and no claim here should be read as one. In
  particular the matched-device intent the plan records
  (`topology: "common_centroid"`) is **not** realised: a single row is a
  linear array, not a common-centroid one.
- **Not a top-level assembly.** Six separate block cells; nothing composes
  them into one PLL.
- **Not post-layout-simulated.** No parasitic extraction, no post-layout PVT
  re-simulation. See below.

## Post-layout PVT: still scoped out, with a reason

Tracked as **#30** on this repo (post-layout PEX + PVT re-simulation). #29
removed the first of that issue's two blockers — there *is* now real
interconnect to extract parasitics from — but the second stands: `klt extract
--parasitics` rejects the `sg13cmos5l` deck as unknown
([klayout-tools#1440](https://github.com/2AMLogic/klayout-tools/issues/1440),
re-verified open by this pass). Worth stating plainly for whoever picks up
#30: the wire this layout draws is *not* a plausible parasitic model of a real
PLL. 147 mm of Metal3 on `divider_chain` alone would dominate any post-layout
result, and that number is an artifact of the routing style (see "What it is
not"), not of the circuit. A meaningful post-layout PVT run needs a real
floorplan first, not just PEX support.

## Friction: `klt`/deck gaps found on this port

Per the root `CLAUDE.md` friction protocol, every gap below was checked
against [`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools)
first and filed there — generic tool-gap description only, no design content.

| Gap | Filed | Status | Effect here |
| --- | --- | --- | --- |
| `klt gen-compose`'s router has **no track or layer assignment between nets**: every net's backbone lands on one shared layer, and the first net accepted rejects the rest with `crosses already-routed net`. Measured on `cp` — 8 groups, 14 devices, 13 multi-pin nets, ~180 µm × 16 µm — at `klt` `b10fa3c`: **1 of 13 nets routes**, independent of placement spacing. **Not re-measured against the current pin** (issue #31's own re-bump only re-probes a throwaway two-pad cell, too small to exercise this) — tracked as part of **#35**. | [klayout-tools#1467](https://github.com/2AMLogic/klayout-tools/issues/1467) (new, filed by #29's pass) | open | This flow draws its own interconnect (`cmos5l_route.py`). This is the reason a pin bump past #1462 does *not* retire it. |
| Every `klt gen` generator (`mos_array`, `res_array`, `diff_pair`, `cap_array`) rejected the `ihp-sg13cmos5l` PDK family outright, so a technology `klt` could *verify* it could not *draw*. `gen.py`'s `_PDK_ROLE_LAYERS` had no `sg13cmos5l` entry. | [klayout-tools#1462](https://github.com/2AMLogic/klayout-tools/issues/1462) (filed by #24's pass) | **closed 2026-08-30T04:31Z, and now present at this repo's pin** (issue #31's own re-bump — `layout/requirements.txt` pins past its merge commit `b10fa3c6e`) | This flow still draws its own footprints: `klt gen mos_array --pdk ihp-sg13cmos5l` now draws, and this run's own `gen-compose.probe.*.json` shows both placement-only *and* `routing` accepted, but #1467 above (not re-measured against this pin) is the reason this module is not retired yet. **The re-evaluation of the local footprints against generator output remains a real follow-up — tracked as #35**, not this issue's own scope. |
| The curated `sg13cmos5l` deck's `EXTRACTION_DECK.capacitors` is empty — and CMOS5L has **no MIM at all**, so MoM is the only capacitor the technology offers and there is no fallback class. | [klayout-tools#1463](https://github.com/2AMLogic/klayout-tools/issues/1463) (filed by #24's pass) | open ([#1466](https://github.com/2AMLogic/klayout-tools/issues/1466) is its follow-on on what recognition shape a MoM plate pair needs) | The 5 `cap_cmomi` devices are recorded and never drawn; 3 blocks' LVS cannot convert; 10 net→pin connections are incomplete. **Unaffected by issue #31's bump** — that bump gave `sg13g2`'s `cap_cmim` a generator (klayout-tools#1461), not `sg13cmos5l`'s `cap_cmomi`; re-verified this pass: `klt gen cap_array --pdk ihp-sg13cmos5l` still rejects with `"PDK family 'sg13cmos5l' has no MiM capacitor plate layers configured -- supported families: sky130, sg13g2"`. |
| `klt lvs`'s `reference.deck` subckt-call conversion table is MOS-only, so a deck's own recognised `rppd`/`rhigh` resistors still need an explicit `reference.device_map`. | [klayout-tools#1464](https://github.com/2AMLogic/klayout-tools/issues/1464) | open | `REFERENCE_DEVICE_MAP` in `pll_cmos5l_layout.py`, deletable when this lands. |
| `klt extract --parasitics` rejects the `sg13cmos5l` deck as "unknown" despite its own `PARASITICS` being defined. | [klayout-tools#1440](https://github.com/2AMLogic/klayout-tools/issues/1440) | open (re-verified by this pass) | Half the reason post-layout PVT is still scoped out above. |

**Also confirmed, not a gap** (checked rather than assumed):

- `klt gen cap_array --pdk ihp-sg13cmos5l` now fails with *"PDK family
  sg13cmos5l has no MiM capacitor plate layers configured -- supported
  families: sky130, sg13g2"* (the family list grew by one entry once issue
  #31's own bump gave `sg13g2` a working `cap_array` configuration) rather
  than the old family rejection. That is still #1463's territory (CMOS5L has
  no MIM), not a new generator gap, so the capacitor's `blocked_reason`
  stays re-attributed to #1462/#1463 rather than pointing at a stale message.
- `klt lvs`'s refusal to convert a `cap_cmomi` card with `m=2`
  (`lock_detector`) is a **documented, deliberate** limitation, not a gap:
  the curated plain-element form models one device per drawn gate, and the
  error says so and names the fix. Recorded, not filed.
- `klt deck info --deck sg13cmos5l` reports `nfet, pfet, resistor` — every
  class this port's drawn devices need is covered; only the capacitor class
  is missing.

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
                                   #   compose/route/DRC/extract/LVS results
      <group>.gds                  # each matched group's own drawn cell
      drc.<group>.json             # ...its `klt drc --deck sg13cmos5l` result
      extract.<group>.json         # ...and its `klt extract` result
      <group>.extracted.spice      # ...and the netlist that extraction wrote
      compose.<block>.json         # each block's placement *and* its routing:
                                   #   per-net track, trunk extent, pin list,
                                   #   wire length, and every incomplete net
      pll_<block>.gds              # the composed, routed block cell
      drc.pll_<block>.json         # its DRC result
      extract.pll_<block>.json     # its extraction result
      <block>.reference.spice      # the schematic netlist LVS compared against
      lvs.<block>.request.json     # the `klt lvs` request as sent
      lvs.<block>.json             # ...and the response as received
      lvs.<block>.cap-probe.*.json # the secondary, capacitor-mapped probe,
                                   #   only for blocks that did not convert
      gencompose_probe.gds         # the throwaway cell the router re-probe uses
      gen-compose.probe.*.json     # ...and both probe requests + responses
```

`<record-id>` mirrors `sim/`'s own `<YYYYMMDD>-<HHMMSS>-<short-git-sha>`
(UTC) convention, including the `-dirty` suffix's meaning: *the flow that
produced this evidence differed from the named commit*. Every `klt` response
inside a record is committed unedited but for one rewrite: the record
directory's own absolute path is replaced with `.`, so a record is a
reproducible artifact rather than a transcript of one machine.
