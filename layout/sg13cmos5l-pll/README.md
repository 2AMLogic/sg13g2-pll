# layout/sg13cmos5l-pll/ — the PLL layout on SG13CMOS5L

Issues #24 (device-level layout), #29 (routing + LVS closure) and #35
(generator-vs-local footprints), all part of
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
| `pfd` | 66 | 66 | 66 | 66 | yes | 202 | 37 | clean | yes | **`match`** — devices 66/66, nets 37/37 |
| `cp` | 20 | 20 | 20 | 20 | yes | 70 | 18 | clean | yes | **`match`** — devices 20/20, nets 18/18 |
| `loop_filter` | 3 | 1 | 1 | 1 | yes | 2 | 2 (3 incomplete) | clean | yes | not converted (#1463) |
| `vco` | 45 | 44 | 44 | 44 | yes | 137 | 33 (2 incomplete) | clean | yes | not converted (#1463) |
| `divider_chain` | 316 | 316 | 316 | 316 | yes | 950 | 142 | clean | yes | **`match`** — devices 316/316, nets 142/142 |
| `lock_detector` | 40 | 38 | 38 | 38 | yes | 115 | 23 (3 incomplete) | clean | yes | not converted (#1463) |
| **Total** | **490** | **485** | **485** | **485** | **6/6** | **1476** | **255** | **6/6 clean** | **6/6** | **3 `match`, 3 not converted** |

**Re-run for issue #72** (record `20260830-204105-457cf5b`), after `cp.sch`
gained its own high-swing cascode bias replica (six new devices — see
`spec/decision-records/DR-006-…` for the decision and
`sim/sg13cmos5l-cp-icp-trim/records/RECORD-002-…` for what it fixed). `cp`'s
own device/net counts move by exactly the six devices and two nets (`nxp`,
`nxn`) the replica adds — 20/20 devices, 18/18 nets, still `match`, block DRC
clean, and both new geometries (`pfet w=6u l=3u`, `nfet w=2u l=3u`) draw,
DRC-clean and re-extract matching their schematic `(class, W, L)` at the first
attempt. Every other block is unchanged from the prior record
(`20260830-105633-4cbf817`). The table above reflects this re-run.

**Re-run for issue #56** (record `20260830-105633-4cbf817`), after `pfd.sch`'s
self-reset chain gained a third inverter stage to fix its inverter-parity
defect (see `design/README.md` / `sim/sg13cmos5l-closed-loop-lock/records/RECORD-002-…`
for the defect and `RECORD-003-…` for the closed-loop re-run this layout
change was verified alongside). `pfd`'s own device/net counts move by exactly
the two devices (+1 `inv_hv`) and one net (`reset_d2`) the new stage adds —
66/66 devices, 37/37 nets, still `match`. Every other block is byte-for-byte
unchanged from the prior record (`20260830-070704-4520159`): 479/484 drawn,
6/6 DRC-clean, 3/6 LVS `match`. This table's per-block rows and totals above
already reflect both re-runs.

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

**Re-run again for issue #35** (record `20260830-070704-4520159`), carrying
the two per-run probes that decision needed, with the same result: 477 / 482
drawn, 6 / 6 DRC-clean, 3 / 3 convertible blocks `match`. See
"Generator-vs-local footprints" below.

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
the first, and issue #35 re-measured the second:

1. **At an earlier pin it could not route on this PDK at all** (routing
   resolves `routing.layer_role` through the same per-PDK-family role→layer
   table every `klt gen` generator uses, and that table had no `sg13cmos5l`
   entry — klayout-tools#1462). **That closed upstream 2026-08-30T04:31Z and
   is present at the current pin**: this repo's own throwaway two-pad probe
   (re-taken on every run, committed as `gen-compose.probe.*.json`) now
   accepts both placement-only and a `routing` block. So this reason no
   longer holds today — see the friction log's #1462 row.
2. **Past that fix it still routes 1 of 13 nets on a block this design's
   size** (klayout-tools#1467). First measured at `b10fa3c`; **re-measured at
   the current pin by issue #35, and unchanged**. Since #35 that measurement
   is no longer a remembered fact: `pll_cmos5l_layout.probe_gen_compose_block_routing`
   rebuilds `cp` — this design's smallest composed block, 8 groups, 14
   devices, 50 declared ports, 13 multi-pin nets — as a real `gen-compose`
   request from the run's own drawn group cells and schematic-derived
   port→net map, and commits the raw responses as
   `gen-compose.probe.block-*.json` on **every** run. At the current pin:

   | Attempt | Result |
   | --- | --- |
   | declare-only (no `routing`) | exit 3, all 13 nets validated — the request is well-formed |
   | with `routing` (`layer_role: "metal"`) | exit 3, **1 of 13 nets routed**; 24 legs `crosses already-routed net 'DN'`, 2 `…'VDD'`, 1 `…'VDUMP'` |
   | with `routing.cross_block_layer_role` | exit 1 — `'metal2' is not a known layer role for PDK family 'sg13cmos5l'` |

   The third row is the part that was not known before #35: the one escape
   `gen-compose` offers from *crosses already-routed net* — putting the
   rejected net on a second metal — **cannot be selected on this PDK family
   at all**. Its role table exposes exactly one routing metal (`metal`, i.e.
   `Metal1`, the same layer the device pads are on), where sky130 and
   gf180mcu each expose `metal`/`metal2`/`metal3` plus `via1`/`via2`. Filed
   upstream as **klayout-tools#1474**; the re-measurement itself is recorded
   on **klayout-tools#1467**. Even if #1467's own resource-allocation work
   lands, this family would have nothing to allocate until #1474 does too.

## Generator-vs-local footprints: measured, and kept local (#35)

`cmos5l_devices.py` exists because at issue #24's pin **no `klt gen`
generator would accept this PDK family at all** (klayout-tools#1462). That
gap closed upstream on 2026-08-30 and the current pin carries it, so the
premise the local footprints were built on has genuinely changed — and
klayout-tools#1462's own text names per-repo re-transcription of process
constants like `Cnt_c`/`NW_c1` as a correctness risk, which is exactly what
`cmos5l_devices.py` does. Issue #35 is the call that follows, made against
measurement rather than either habit or the fixed-gap headline.

**Decision: keep the local footprints.** Not because the generator does not
draw — it does, and cleanly — but because on all three axes this flow's
verified result actually depends on, generator output would *regress* a
result that is passing today. Measured on this design's own group parameters
(never a synthetic device), re-taken on **every** run by
`pll_cmos5l_layout.probe_generator_footprints`, raw responses committed as
`gen.probe.*.json` / `drc.genprobe_*.json` / `extract.genprobe_*.json`:

| What a swapped-in footprint must clear | `klt gen mos_array` at this pin | Local footprint |
| --- | --- | --- |
| Draws at all, DRC-clean | **yes** — `klt drc --deck sg13cmos5l` clean, 0 violations, on both flavours | yes |
| Ratified **thick-oxide** device (DR-002 Decision 0) | **no** — extracts as `sg13_lv_nmos`/`sg13_lv_pmos`. `drc_hints.notes[]`: *"params.voltage_flavor 'thick_oxide' has no marker layer resolved for the resolved PDK family ('sg13cmos5l') -- no marker was drawn"*; no `ThickGateOx` (44/0) in the output | `sg13_hv_nmos`/`sg13_hv_pmos`, the models the committed netlists instantiate |
| Biased, schematic-named PMOS body | **no** — draws the `NWell` but no well tap and no `NWell.pin`; `unbiased_pmos_body_nets[]` reports 2 of 2 devices, body on an anonymous `\$7`. No body port in `ports[]` to route one to, either | `unbiased_pmos_body_nets[]` empty; well named with the *schematic's* own body net, which is the node LVS matches on |
| Riser columns ≥ `ROUTE_PITCH_UM` (0.60 µm) apart | **no** — `ports[]` does give one x per terminal and (with `gate_contact`) a contacted gate pad, but they are **0.46 µm** apart on this design's narrowest device: under 0.60 µm, and under the 0.51 µm `metal2.width.1` + `metal2.space.1` alone require. `cmos5l_route.check_riser_columns` raises on it | built to 0.60 µm by construction |

Rows 2 and 3 are the disqualifying ones, and they are not stylistic. Row 2
would flip all **469** drawn MOS devices to the thin-oxide model, against
reference netlists that instantiate the thick-oxide one — a device-class
mismatch on `pfd`, `cp` and `divider_chain`, the three blocks that are LVS
`match` today. Row 3 would put every PMOS body on a net the schematic has
never heard of. Either one alone fails the bar this decision was held to:
*all six blocks DRC-clean and the three convertible blocks still `match`*.
Both are filed upstream — **klayout-tools#1472** (no thick-oxide marker layer
for the IHP families) and **klayout-tools#1473** (`mos_array --flavor pfet`
draws an untied, unnamed well) — so this is a deferral pending upstream work,
not a rejection of generator output on principle.

**`res_array` is the exception, and is deliberately still not swapped.** It
clears every row above: it draws, it is DRC-clean, it extracts as `rppd` with
the right value, and its terminals are hundreds of microns apart. The reason
to leave it alone is that it would move nothing: this design's **8** poly
resistors live entirely in `loop_filter`, `vco` and `lock_detector` — the
three blocks that cannot be LVS-converted at all for the capacitor reason
below — so the swap buys no verified result while splitting one flow across
two footprint sources with two different sets of process constants. It is
recorded here as the place a future swap should *start*, on the day
klayout-tools#1472/#1473 make the MOS side swappable too, so both halves move
together.

None of this is a claim that will quietly go stale: the three measurements
above and the `gen-compose` block-routing re-probe are taken on every run and
reported in `record.md`, so the day any of them flips, the record says so
without anyone remembering to re-check.

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
| `klt gen-compose`'s router has **no track or layer assignment between nets**: every net's backbone lands on one shared layer, and the first net accepted rejects the rest with `crosses already-routed net`. Measured on `cp` — 8 groups, 14 devices, 13 multi-pin nets, ~180 µm × 16 µm — at `klt` `b10fa3c`: **1 of 13 nets routes**, independent of placement spacing. **Re-measured at the current pin by #35 and unchanged** — 1 of 13, 24 legs rejected `crosses already-routed net 'DN'` — and re-taken on every run since (`gen-compose.probe.block-*.json`). | [klayout-tools#1467](https://github.com/2AMLogic/klayout-tools/issues/1467) (filed by #29's pass; re-measurement recorded on it by #35) | open | This flow draws its own interconnect (`cmos5l_route.py`). This is the reason a pin bump past #1462 does *not* retire it. |
| `gen.py`'s `_PDK_ROLE_LAYERS` gives both IHP families **exactly one routing metal role** (`metal` = `Metal1`, the device-pad layer), where sky130 and gf180mcu each get `metal`/`metal2`/`metal3` + `via1`/`via2`. So `gen-compose`'s `routing.cross_block_layer_role` — the only escape it offers from *crosses already-routed net* — cannot be named at all: the request is rejected with *"'metal2' is not a known layer role for PDK family 'sg13cmos5l'"*. | [klayout-tools#1474](https://github.com/2AMLogic/klayout-tools/issues/1474) (new, filed by #35's pass; the IHP sibling of the closed sky130/gf180mcu #433/#1058) | open | Compounds #1467: even if that issue's per-net layer assignment lands, this family has no second plane to assign. Both must land before `gen-compose` can route a block this size here. |
| Every `klt gen` generator (`mos_array`, `res_array`, `diff_pair`, `cap_array`) rejected the `ihp-sg13cmos5l` PDK family outright, so a technology `klt` could *verify* it could not *draw*. `gen.py`'s `_PDK_ROLE_LAYERS` had no `sg13cmos5l` entry. | [klayout-tools#1462](https://github.com/2AMLogic/klayout-tools/issues/1462) (filed by #24's pass) | **closed 2026-08-30T04:31Z, and now present at this repo's pin** (issue #31's own re-bump — `layout/requirements.txt` pins past its merge commit `b10fa3c6e`) | `klt gen mos_array`/`res_array` do now draw here, DRC-clean. **#35 re-evaluated the local footprints against that output and kept them** — see "Generator-vs-local footprints" above for the three measurements and the two upstream issues (#1472/#1473) that would have to land first. The `res_array` half already clears the bar and is the place a future swap starts. |
| `mos_array`'s `voltage_flavor` param resolves to **no marker layer on either IHP family** (`_PDK_VOLTAGE_FLAVOR_LAYERS` has entries for gf180mcu and sky130 only), so a generated unit device carries no `ThickGateOx` (44/0) and extracts as the *thin*-oxide `sg13_lv_*` class. Reported honestly in `drc_hints.notes[]`, but with no params-level override to recover from. | [klayout-tools#1472](https://github.com/2AMLogic/klayout-tools/issues/1472) (new, filed by #35's pass; the family-coverage tail of the closed #1054) | open | One of the two reasons `cmos5l_devices.py` still draws the MOS footprints: this design's devices are the ratified HV flavour (DR-002 Decision 0), and generator output would extract as the wrong device class against every reference netlist. |
| `klt gen mos_array --flavor pfet` draws the shared `NWell` but **no well tap and no `NWell.pin`**, and declares no body port, so every generated PMOS body extracts onto an anonymous net — `klt extract` reports it in `unbiased_pmos_body_nets[]`. Distinct from the closed deck-side #1414: the deck's tie derivation works fine, the generator just draws nothing for it to recognise. | [klayout-tools#1473](https://github.com/2AMLogic/klayout-tools/issues/1473) (new, filed by #35's pass) | open | The other reason the MOS footprints stay local: `draw_pfet_array_well` draws the tap and names the well with the *schematic's* own body net, which is what keeps `unbiased_pmos_body_nets[]` empty and gives LVS a body net to match. |
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
      gen-compose.probe.block-*.json  # the same probe against a REAL block
                                   #   (`cp`) — declare-only, routed, and
                                   #   routed-with-a-second-plane: the
                                   #   klayout-tools#1467 re-measurement
      gen.probe.<probe>.json       # `klt gen mos_array`/`res_array` run on
                                   #   this design's own group params
      genprobe_<probe>.gds         # ...the cell each of those drew
      drc.genprobe_<probe>.json    # ...its DRC result
      extract.genprobe_<probe>.json    # ...its extraction result
      genprobe_<probe>.extracted.spice # ...and the netlist it extracted to,
                                   #   which is where `sg13_hv_*` vs
                                   #   `sg13_lv_*` is actually visible
```

The `gen-compose.probe.block-*` and `gen.probe.*`/`genprobe_*` artifacts are
**evidence about the tools, not part of the layout**: nothing they draw is
composed, routed, LVS'd, or counted in this record's verdict. See
"Generator-vs-local footprints" above for what they measure and why.

`<record-id>` mirrors `sim/`'s own `<YYYYMMDD>-<HHMMSS>-<short-git-sha>`
(UTC) convention, including the `-dirty` suffix's meaning: *the flow that
produced this evidence differed from the named commit*. Every `klt` response
inside a record is committed unedited but for one rewrite: the record
directory's own absolute path is replaced with `.`, so a record is a
reproducible artifact rather than a transcript of one machine.
