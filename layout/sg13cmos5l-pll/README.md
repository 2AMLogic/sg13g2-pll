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

## Status: routed, DRC-clean, **every device drawn**, and LVS `match` on every block whose schematic's substrate split matches the layout

Per the current record (`reports/LATEST`):

| Block | Devices (schematic) | Drawn | Group DRC clean | Group re-extract matches | Composed + routed | Terminals routed | Nets | Block DRC | Block re-extract matches | **`klt lvs`** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pfd` | 66 | 66 | 66 | 66 | yes | 202 | 37 | clean | yes | **`match`** — devices 66/66, nets 37/37 |
| `cp` | 20 | 20 | 20 | 20 | yes | 70 | 18 | clean | yes | **`match`** — devices 20/20, nets 18/18 |
| `loop_filter` | 3 | 3 | 3 | 3 | yes | 6 | 3 | clean | yes | **`match`** — devices 3/3, nets 4/4 (#114) |
| `vco` | 45 | 45 | 45 | 45 | yes | 139 | 33 | clean | yes | `mismatch` — residual is #113's six `XBIAS` resistors + `BIAS.SUB!` net-merge; the drawn `DECAP` matches (#114) |
| `divider_chain` | 316 | 316 | 316 | 316 | yes | 950 | 142 | clean | yes | **`match`** — devices 316/316, nets 142/142 |
| `lock_detector` | 41 | 41 | 41 | 41 | yes | 124 | 23 | clean | yes | `mismatch` — residual is the `SUB!` substrate split (`PU`/`PD`); all three `cap_cmomi` units match (#114) |
| **Total** | **491** | **491** | **491** | **491** | **6/6** | **1491** | **256** | **6/6 clean** | **6/6** | **4 `match`, 2 mismatch (non-capacitor residuals)** |

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

- **Every block reports a real LVS verdict** — no `not converted` row is
  left. `pfd`/`cp`/`divider_chain` match as before, and `loop_filter` now
  matches too (3/3 devices, 4/4 nets, #114): its two `cap_cmomi`
  capacitors are drawn, DRC-clean, extract as `cap_cmomi` with the
  schematic's own declared `w`/`l`, and LVS against a reference that now
  converts them. The one `mismatch_count` entry on each matching block is
  the `topology.flattened` **warning** `options.flatten_reference` always
  emits; it is a note about the compare, not an unmatched object.
- **The two remaining mismatches contain no capacitor.** `vco`'s unmatched
  set is exactly #113's six `XBIAS` resistors plus the `BIAS.SUB!`
  `net.merged` — that issue's own scope, which this issue's AC explicitly
  leaves to it. `lock_detector`'s is the same substrate-split family
  (`SUB!` vs the layout's one `vsubs` node, stranding `PU`/`PD`), which
  predates the capacitors and is a schematic-netlist property, not a
  routing or deck defect. Every drawn `cap_cmomi` — including
  `lock_detector`'s `m=2` unit, drawn as two markers and both matched —
  pairs on both sides.
- **DRC survived the capacitors.** The interdigitated Metal1–Metal4 finger
  lattice (`cmos5l_devices.draw_mom_cap`) clears every deck rule at every
  instantiated size (40×40, 10×10, 70×70 µm) with zero violations, both as
  standalone cells and inside the routed blocks — on a young deck, at the
  foundry-reference finger lattice's own minimum spacings.

The device count moved 490 → 491 because the planner now expands a
capacitor card's `m=` multiplier into unit devices (#114):
`lock_detector`'s `XC1 w=40u l=40u m=2` is drawn, extracted and compared as
two 40×40 µm markers — the honest rendering of "two unit capacitors in
parallel", and the reason its LVS reference carries two `X ... PARAMS:`
cards.

The former 5-device shortfall — this port's five `cap_cmomi`
metal-oxide-metal capacitors (`loop_filter` ×2, `vco` ×1, `lock_detector`
×2, one of them `m=2`) — is closed: every one is drawn by the local MoM
footprint, and every net they touch now routes complete (zero incomplete
nets on every block).

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
  DRC'd, re-extracted and LVS'd as a whole. For `vco` the row order, the
  member->slot order inside each group cell and the track order are first
  permuted by the net-affinity floorplan pass
  (`layout/bin/cmos5l_floorplan.py`, issue #101 — 7 178 -> 3 913 um of
  routed wire on that block; every net, device and footprint unchanged).
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
~1.7 mm across — and wire length: 167 mm of total drawn wire across the six
blocks in the issue-#29-style composition. That is a floorplan cost, and for
five of the six blocks it is still a bad floorplan; see "What it is not".
`vco` is the exception since issue #101: the locality pass
(`layout/bin/cmos5l_floorplan.py`) permutes the row order, the member->slot
order inside each matched group cell, and the track order — under the *same*
structural invariants, since a permutation adds no net, no footprint and no
spacing — and cuts that block's routed wire from 7 178 to 3 913 um
(`ring1`: 413 -> 126 um) with its DRC, extraction and LVS verdicts unchanged.
The measured PVT consequence lives in
[`sim/sg13cmos5l-postlayout-pex-pvt/records/`](../../sim/sg13cmos5l-postlayout-pex-pvt/records/)
— RECORD-002.

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
three blocks whose LVS residuals are the `sub!`/`vsubs` substrate split (and,
on `vco`, #113's resistors), none of them footprint-attributable — so the
swap buys no verified result while splitting one flow across two footprint
sources with two different sets of process constants. It is recorded here as
the place a future swap should *start*, on the day
klayout-tools#1472/#1473 make the MOS side swappable too, so both halves move
together.

None of this is a claim that will quietly go stale: the three measurements
above and the `gen-compose` block-routing re-probe are taken on every run and
reported in `record.md`, so the day any of them flips, the record says so
without anyone remembering to re-check.

## LVS

`klt lvs` is run per composed block against that block's own committed
schematic netlist, derived into a plain-element reference this flow itself
produces and commits as `<block>.reference.spice` (so the evidence is
self-contained). Four of six blocks report `status: "match"`; the two
mismatches and their non-capacitor residuals are in the status table above.

The reference derivation (`mom_cap_reference` in `pll_cmos5l_layout.py`,
#114) is two caller-side rewrites, both recorded in each record's
`lvs.<block>.request.json`:

- **MOS/resistor `X` cards → plain-element `M`/`R` cards** via
  `klayout_tools.netlist_normalize` — the identical conversion
  `reference.form: "subckt-call"` performs, run by the caller so the cap
  cards (below) can ride along. At this repo's pin the deck's own curated
  conversion table resolves `sg13_hv_nmos`/`sg13_hv_pmos` **and**
  `rppd`/`rhigh`, so the per-deck `device_map` this flow used to carry
  (`REFERENCE_DEVICE_MAP`, filed against klayout-tools#1464) is deleted —
  retired by this very run, which passes no `device_map` and converts
  cleanly.
- **Converted resistor cards get real values, not placeholders.** The
  converter writes a literal `0` for a resistor's value because it carries
  no PDK sheet-resistance table; `klt lvs`'s own subckt-call path then has
  to *exclude* that parameter from the compare (issue #1907's
  `device.placeholder_value` disclosure). This flow instead recomputes the
  value from the deck's own curated `sheet_rho_ohm_sq`/`fixed_offset_ohm`
  coefficients — the same numbers `klt extract` derives a drawn resistor's
  reported resistance from — and carries `A`/`P` alongside, so the compare
  verifies the resistance dimension rather than disclosing that it skipped
  it. (`loop_filter`'s `rppd` now matches on `r`/`a`/`p` as well as
  topology and geometry.)
- **`cap_cmomi` cards → `X <name> <a> <b> cap_cmomi PARAMS: W=<um> L=<um>`**
  — the exact card shape `klt lvs`'s custom-device-class reader
  (klayout-tools#1942, merged as #1944, carried at this repo's pin)
  recognises when `reference.deck` is given. `W`/`L` are bare micron
  numbers (the extractor reports the recognition marker's bbox in µm), and
  an `m=` multiplier expands one card per unit to match the
  one-marker-per-unit footprint. This rewrite retires what used to be the
  `m=2` "documented, deliberate limitation" on `lock_detector`.

The whole derivation is caller-side because no single `klt lvs` request can
express it yet: `reference.form: "subckt-call"`'s converter rejects the
`PARAMS:` card it must leave to the custom-class reader — filed upstream as
**[klayout-tools#2327](https://github.com/2AMLogic/klayout-tools/issues/2327)**.

One compare finding is **not** capacitor-attributable and the records call
it out rather than absorbing it: the resistor-carrying blocks' poly
resistors declare their bulk terminal on the schematic's own floating
`sub!` global, while the layout puts every drawn resistor's bulk on the
deck's real substrate net (`vsubs`) — which the NMOS body ties also land
on. So the layout has one substrate node where the reference has two. On
`vco` this is #113's territory (its six `XBIAS` resistors plus
`BIAS.SUB!`); on `lock_detector` it strands `PU`/`PD` the same way. It is a
schematic-netlist property, not a routing or deck defect, and it is
recorded rather than resolved: changing which node a device's bulk is
declared on is a schematic change, and this increment does not make one.

## ERC: T1 item 11 power-delivery (structural) — done for `divider_chain`

`klt erc` reads now back the divider chain's supply structure [#103]:
`erc-supply-spec.json` (the item-11 artifact, `ties[]` deliberately
omitted per the recorded klayout-tools#2169 workaround) and
`erc-welltie-check-spec.json` (a supplementary checked-tie probe, run after
that issue closed upstream on 2026-09-20). Both live next to this README;
their committed reports and the standing-in well-tie evidence are frozen in
`reports/20260921-155144-00b0094/` — read that record's `record.md` first.
Both reads report `erc_status: "clean"`: **one island per declared supply**
(`VDD_DIV`, `VSS`), zero `erc.unconnected_net`, zero `erc.supply_short`, and
the n-well tie graded **checked** with zero `erc.missing_tie` in the probe
run. The antenna half honestly reports `not_checked` — `klt erc`'s
antenna-limit table is sky130-only today, an untranscribed upstream gap —
which is exactly why item 11 grades the `erc_findings` rules, never the
report's overall `status` (klayout-tools#1994). `erc.missing_tie` remains
**not computed by the item-11 artifact itself** (`no_ties_declared`, an
absence of evidence, not evidence of absence); what stands in for the
well-tie verdict is named in the spec's comment block and the record: the
same-GDS LVS `match` carrying both supplies in its `net_correspondence`,
the compose route records pinning `nwell_tap`/`substrate_tap` into their
supply nets, and the checked-tie probe above.

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
  wide and the six blocks draw 167 mm of wire between them (vco's share is
  down from 7 178 to 3 913 um since issue #101's locality pass — see
  "Routing" — but the other five blocks' compositions are unchanged). It is
  DRC-clean and it is electrically the schematic; it is not an area-,
  parasitic- or matching-aware layout, and no claim here should be read as
  one. In particular the matched-device intent the plan records
  (`topology: "common_centroid"`) is **not** realised — not even on `vco`,
  whose locality pass reorders cells and slots for wire length alone: a
  single row is a linear array, not a common-centroid one.
- **Not a top-level assembly.** Six separate block cells; nothing composes
  them into one PLL.
- **~~Not post-layout-simulated.~~ Superseded by #30** — all six blocks now
  have a parasitic-annotated netlist and two (`vco`, `cp`) have had their
  ratified PVT matrices re-run against it. What stays true is the *reason*
  this bullet used to be here: the routing is not a plausible floorplan, so
  those results are an upper bound on parasitic loading rather than a
  prediction. See "Post-layout PVT" below.

## Post-layout PVT: **done** (#30), with three caveats that must travel with it

Both of the blockers this section used to record are gone. #29 landed the
routing, and `klt extract --deck sg13cmos5l --parasitics` now works with
**real curated metal R/C coefficients**:
[klayout-tools#1440](https://github.com/2AMLogic/klayout-tools/issues/1440)
closed via #2012 (deck registered in the parasitics registry), and the
follow-on gap where the deck registered but reported zero R/C
([#2113](https://github.com/2AMLogic/klayout-tools/issues/2113)) closed via
#2126 (curated Metal1–TopMetal1 coefficients plus four overlap pairs).

The work lives in [`sim/sg13cmos5l-postlayout-pex-pvt/`](../../sim/sg13cmos5l-postlayout-pex-pvt/)
— all six routed blocks have a committed parasitic-annotated netlist, and two
of them (`vco`, `cp`) had their ratified PVT matrices re-run against those
netlists with a schematic-level control arm. **Real extracted parasitics were
modelled** — `metals_without_coefficient` is empty for every block; nothing
fell back to a zero coefficient.

Three caveats belong with every number that campaign produced, and are
repeated here because this file is where a layout reader arrives first:

1. **The floorplan is still not representative, so every post-layout number
   remains an upper bound on parasitic loading, not a prediction — but less
   of one on `vco` since issue #101.** As routed at the RECORD-001 layout,
   the wire was not a plausible parasitic model of a real PLL: 147 mm of
   Metal3 on `divider_chain`, and 7 178 µm on `vco` — 413 µm of it on
   `ring1` alone, a node a compact ring closes in single-digit microns — an
   artifact of the routing style (see "What it is not"), not of the circuit;
   the `vco` lost ~50% of its frequency, ~99% of it parasitic *capacitance*,
   and a C-scaling bracket put a floorplan with an order of magnitude less
   wire nearer −6 … −10%. Issue #101's locality pass then cut `vco`'s wire
   to 3 913 µm (126 µm on `ring1`) with DRC/extraction/LVS verdicts
   unchanged, and RECORD-002
   ([`sim/sg13cmos5l-postlayout-pex-pvt/records/`](../../sim/sg13cmos5l-postlayout-pex-pvt/records/))
   measures the consequence rather than leaving it bracketed: the mean
   per-point deviation narrows from −49.3% to −22.6% (band 223.7 – 789.5 →
   347.6 – 1182.8 MHz), of which < 1 pp is the shared device floor and
   ~1.4 pp parasitic R. `divider_chain`'s 147 mm is untouched, and all the
   matching/area caveats below still apply to every block including `vco`.
2. **Only three of six blocks have a confirmed layout↔schematic topology
   match.** See the next section — `pfd`/`cp`/`divider_chain` match;
   `loop_filter`/`vco` now compare and **mismatch**; `lock_detector` still
   cannot be compared. `cp`'s post-layout numbers rest on a confirmed match;
   `vco`'s do not, and the record says so instead of presenting its deviation
   as a clean parasitic effect.
3. **The coefficients are uncalibrated.** klayout-tools' own `LayerRC`
   docstring calls them "representative, uncalibrated, order-of-magnitude
   starter values" from public process data, with silicon calibration an
   explicit non-goal. Real numbers with a cited source — not silicon-correlated.

**Still open, and not tracked anywhere upstream**: a *representative* analog
floorplan — matching, supply grid, folding. Issue #101 addressed the wire
axis on `vco` (see "Routing" and RECORD-002); it did not make any block's
composition a representative analog floorplan, the other five blocks' rows
are untouched, and no issue currently owns that step. It is the one
prerequisite a *meaningful* (rather than upper-bound, or less-upper-bound)
post-layout PVT result still needs.

## LVS: three blocks were never compared; they are now

The per-record `lvs.<block>.json` artifacts show `pfd`/`cp`/`divider_chain`
comparing cleanly and `loop_filter`/`vco`/`lock_detector` failing with *"could
not convert subckt-call reference netlist … `cap_cmomi` is not a known
device"*. That is **not** "LVS failed" — it is *LVS never ran*, on exactly the
three blocks whose schematics instantiate a MoM capacitor.

Issue #30 re-ran all six at the current `klt`, changing one thing: adding the
`reference.device_map` entry klt's own error message names (`cap_cmomi` →
`{"kind": "capacitor"}`). Same GDS, same reference netlist, same deck, same
options. Evidence and the script are in
[`sim/sg13cmos5l-postlayout-pex-pvt/lvs-recheck/`](../../sim/sg13cmos5l-postlayout-pex-pvt/lvs-recheck/).

| Block | Verdict | Devices | Note |
| --- | --- | --- | --- |
| `pfd` | **match** | 66/66 | 0 errors |
| `cp` | **match** | 20/20 | 0 errors |
| `divider_chain` | **match** | 316/316 | 0 errors |
| `loop_filter` | **mismatch** | **0/3** | newly comparable. The routed cell has only the `rppd`; both `cap_cmomi` capacitors are undrawn, so it is not a loop filter |
| `vco` | **mismatch** | 38/45 | newly comparable. Unmatched: the undrawn `DECAP` (`cap_cmomi`) and the six `XBIAS` resistors, plus one `net.merged` on `BIAS.SUB!`. Not root-caused |
| `lock_detector` | **not compared** | — | blocker has *changed*: no longer the missing device class but `m=2` on a `cap_cmomi` card, the documented plain-element limitation recorded below |

This does not update the committed layout records (they are append-only
evidence of what that run produced); it is a later, separately-recorded
re-check.

**Issue #114 closed the capacitor half end to end.** The devices are drawn
(`cmos5l_devices.draw_mom_cap`), extract as `cap_cmomi` at the schematic's
own `w`/`l`, and LVS through the caller-side reference rewrite
(`mom_cap_reference`, see "LVS" above) — which also retires the `m=2`
limitation by expanding the multiplier one card per drawn marker. Verdicts
in the current record's own table (top of this README): `loop_filter`
**match** (3/3), `vco` mismatch with the `DECAP` matched and exactly #113's
residual left, `lock_detector` mismatch with all three capacitor units
matched and the pre-existing `SUB!` split left.

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
| The curated `sg13cmos5l` deck's `EXTRACTION_DECK.capacitors` is empty — and CMOS5L has **no MIM at all**, so MoM is the only capacitor the technology offers and there is no fallback class. | [klayout-tools#1463](https://github.com/2AMLogic/klayout-tools/issues/1463) (filed by #24's pass) | **closed 2026-08-30**, with [#1466](https://github.com/2AMLogic/klayout-tools/issues/1466) closed by [#1475](https://github.com/2AMLogic/klayout-tools/pull/1475): the deck now carries a `mom_capacitors` entry for `cap_cmomi`/`cap_cmomf`. The LVS half closed with [#1942](https://github.com/2AMLogic/klayout-tools/issues/1942) (merged as #1944): a round-tripped `X ... PARAMS:` card is read as a real device of that class | **Retired for this port by issue #114's pin bump + local footprint.** All five `cap_cmomi` devices draw (`cmos5l_devices.draw_mom_cap`, DRC-clean at every instantiated size), extract as `cap_cmomi` with the schematic's own `w`/`l`, and LVS-match through `mom_cap_reference`'s reference rewrite. What remains local *by decision*, not by gap: no `klt gen` MoM generator exists on any family — `cap_array` still rejects `ihp-sg13cmos5l` with *"PDK family 'sg13cmos5l' has no MiM capacitor plate layers configured -- supported families: sky130, gf180mcu, sg13g2"*, re-verified at `klt 0.6.0+gdaf06a51a` for #114's bump |
| `klt lvs`'s `reference.deck` subckt-call conversion table is MOS-only, so a deck's own recognised `rppd`/`rhigh` resistors still need an explicit `reference.device_map`. | [klayout-tools#1464](https://github.com/2AMLogic/klayout-tools/issues/1464) | **closed 2026-08-30 as completed** (status corrected by #30's pass — the row said `open`) | **Retired by #114's run.** The deck's own curated table resolves `rppd`/`rhigh` (and the MOS subcircuits) at this repo's pin, verified live by the #114 record's references, which pass **no** `device_map` — `REFERENCE_DEVICE_MAP`/`CAPACITOR_PROBE_DEVICE_MAP` are deleted from `pll_cmos5l_layout.py`. The successor gap that made the deletion non-trivial is the #2327 row below |
| `klt lvs` cannot carry a custom-device-class `X ... PARAMS:` card through `reference.form: "subckt-call"`: the converter tokenizes `PARAMS:` as the subcircuit name and rejects the card, while the custom-class reader (#1942/#1944) only runs on the plain-element form — so a netlist mixing curated subckt devices *and* a `mom_capacitors` device has no single-request LVS shape. Reproduced at `klt 0.6.0+gdaf06a51a` on `sg13cmos5l`. | [klayout-tools#2327](https://github.com/2AMLogic/klayout-tools/issues/2327) (new, filed by #114's pass) | open | `mom_cap_reference` in `pll_cmos5l_layout.py` works around it caller-side: lift the cap cards, normalize the rest, splice `X ... PARAMS:` cards back, submit `form: "plain-element"` + `reference.deck`. Also computes converted resistor cards' real values from the deck's own sheet-rho coefficients, so no compare rests on the #1907 placeholder-value disclosure. Delete the workaround when #2327 lands |
| `klt extract --parasitics` rejects the `sg13cmos5l` deck as "unknown" despite its own `PARASITICS` being defined. | [klayout-tools#1440](https://github.com/2AMLogic/klayout-tools/issues/1440) | **closed 2026-09-19 via #2012** (deck registered in the parasitics registry) | Was half the reason post-layout PVT was scoped out. Retired — see "Post-layout PVT" above. |
| Registering the deck was necessary but not sufficient: `--parasitics` then *succeeded* while reporting `r_count`/`c_count` of 0 and listing all five metal levels in `metals_without_coefficient` — a "post-layout" netlist with no wire parasitics in it, disclosed but easy to miss. | [klayout-tools#2113](https://github.com/2AMLogic/klayout-tools/issues/2113) (filed by #30's Curator pass) | **closed 2026-09-19 via #2126** (curated Metal1–TopMetal1 `LayerRC` + 4 overlap pairs, each citing its public source line) | The reason `sim/sg13cmos5l-postlayout-pex-pvt/` can say real parasitics were modelled. Its `extraction/run-pex.sh` still hard-fails on a `klt` without them, so a silently-zero extraction cannot be produced by accident. |
| `klt extract --parasitics` emits **three-terminal `R` cards** for deck-recognised `rppd`/`rhigh` resistors (`R$39 a b bulk 7800 rppd L=30U W=1U`). ngspice's `R` card takes two nodes, so the extracted netlist is unparseable as written. | the already-filed [klayout-tools#1157](https://github.com/2AMLogic/klayout-tools/issues/1157) (*"klt extract's bare (non-`--pdk`) output for a 3-terminal drawn-resistor class is not ngspice-simulatable"*) — #30's pass recorded a [confirmation comment](https://github.com/2AMLogic/klayout-tools/issues/1157#issuecomment-5740464634) on it (2026-09-19) rather than opening a duplicate, **narrowing that issue's own scope condition**: the 3-node `R` card is emitted *with* `--pdk` supplied too, so it is not limited to bare mode | open | `sim/sg13cmos5l-postlayout-pex-pvt/testbench/pex-to-ngspice.py` (transform 2) rebinds them to the PDK's own resistor subcircuit call — the identical binding the schematic netlist uses — and self-checks that no parasitic R/C card count changes. |
| `klt extract` writes hierarchical net names joined with a **`.`** (`XBIAS.n2s` for a net that came from a sub-instance). `.` is ngspice's own hierarchy separator, so such a node cannot be probed, `.meas`'d or `.ic`'d by its written name, and the same token parses as a path expression wherever a node reference is read. | [klayout-tools#2145](https://github.com/2AMLogic/klayout-tools/issues/2145) (new, filed by #30's pass; the net-name sibling of #1157's device-card gap) | open | `pex-to-ngspice.py` (transform 1) rewrites `A.b` → `A_b`, matched only between two identifier characters so numeric literals (`L=0.28U`) and dot commands (`.SUBCKT`/`.ENDS`/`.GLOBAL`) are never touched. Cost: the simulated net names diverge from the names in the extraction JSON report and the SPEF, so cross-referencing a result back to the report is a manual mapping step. |

**Also confirmed, not a gap** (checked rather than assumed):

- `klt gen cap_array --pdk ihp-sg13cmos5l` still fails with *"PDK family
  sg13cmos5l has no MiM capacitor plate layers configured -- supported
  families: sky130, gf180mcu, sg13g2"* at `klt 0.6.0+gdaf06a51a`
  (re-verified for #114's pin bump; the family list grew by `gf180mcu`
  since the last check). That is still #1463's territory (CMOS5L has
  no MIM), not a new generator gap, and it is not a MoM generator either —
  the capacitor's drawing side stays local, exactly as the #1463 row above
  records.
- ~~`klt lvs`'s refusal to convert a `cap_cmomi` card with `m=2`~~ —
  **retired by #114**: the caller-side reference rewrite expands `m=`
  one `X ... PARAMS:` card per drawn marker, and `lock_detector`'s `m=2`
  unit now compares (both units matched). The refusal itself was a
  documented, deliberate limitation of the plain-element conversion, never
  filed; the new `PARAMS:`-card path makes it moot.
- `klt deck info --deck sg13cmos5l` reports `nfet, pfet, resistor,
  cap_cmomi, cap_cmomf` — every class this port's drawn devices need is
  covered, capacitors included as of #1466/#1475.

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
