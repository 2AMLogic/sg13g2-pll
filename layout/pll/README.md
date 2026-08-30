# layout/pll/ — the PLL device-level layout

Issue #13's deliverable: a **device-level layout of every block the
committed netlist declares** (`design/netlist/*.spice`, from #7), drawn
headlessly from those netlists by `layout/bin/run-pll-layout-flow.sh` and
checked in as an append-only evidence record under `reports/<record-id>/`.
Mirrors `2AMLogic/sky130-pll` issue #16's own scope and directory shape for
the identical T1 checklist rung (`#6` item 2 on this repo).

**Read the current record's `record.md` first** — it is the actual
pass/fail evidence this issue produces, not this file. `reports/LATEST`
names it.

```bash
layout/bin/setup-venv.sh            # once, or after bumping requirements.txt
layout/bin/run-pll-layout-flow.sh   # writes a fresh record
```

## Status: 482 / 482 planned devices draw, extract, and match the schematic — every block composes

**This is the honest headline, and it is a full pass.** `layout/bin/pll_layout.py`
derives a complete, schematic-accurate device plan (every device every
block's netlist declares, grouped by `(class, W, L)` into `klt gen`
requests) and then, for every device class `klt gen` can draw on `sg13g2`
today (`mos_array`, `res_array`, and — as of issue #31's re-bump —
`cap_array` for this design's `cap_cmim` MiM capacitors), draws each group,
re-extracts it (`klt extract --deck sg13g2`), and compares the extraction
against the schematic's own expectation — then composes every block's own
drawn groups into one `pll_<block>` cell (`klt gen-compose`, placement
only) and re-extracts *that* composed cell too, cross-checking its
device-count multiset against the block's schematic-derived totals:

| Block | Devices (schematic) | Devices drawn + matched | Composed | Block re-extract matches schematic |
| --- | --- | --- | --- | --- |
| `pfd` | 64 | 64 | yes | yes |
| `cp` | 14 | 14 | yes | yes |
| `loop_filter` | 3 | 3 | yes | yes |
| `vco` | 45 | 45 | yes | yes |
| `divider_chain` | 316 | 316 | yes | yes |
| `lock_detector` | 40 | 40 | yes | yes |
| **Total** | **482** | **482** | **6/6** | **6/6** |

**Every device this design's schematic declares now draws, re-extracts, and
matches** — every MOSFET, every resistor, and every MiM capacitor. The two
`cap_cmim` shunt caps in `loop_filter` and the three MiM/decap capacitor
instances in `vco`/`lock_detector` (`vco_XCDECAP`, `lock_detector_XCW`,
`lock_detector_XDW.XC1`) — the 5-device shortfall every prior record on this
issue carried — now draw via `klt gen cap_array` and re-extract as `class:
"cap_cmim"`, matched on `(area_um2, perimeter_um)` (the two-plate device's
own dimension pair — see "What changed" below for why that differs from the
`(w_um, l_um)` pair a MOS/resistor group matches on).

This is not a stale-install artifact or a config mistake in this flow.
`layout/requirements.txt` pins the exact commit
(`fdf04f71ab39159838acb86e63a92d6fa0c714fa`, `main` HEAD as of this record)
that carries `klayout-tools#1461` (closing #1455): `klt gen cap_array` now
has a real `sg13g2` MiM-capacitor plate-layer configuration. Re-verifying
*end-to-end* against the bumped pin, per this issue's own instruction to
confirm rather than assume a closed tracker issue means a clean run, found
the fix real: `klt gen cap_array --pdk ihp-sg13g2 --params '{"plate_w_um":
40, "plate_h_um": 40, "num": 1}'` now draws real MIM-capacitor geometry, and
`klt extract --deck sg13g2` re-recognises it as `cap_cmim` with the exact
drawn area/perimeter.

### What changed (issue #31)

`layout/bin/pll_layout.py`'s capacitor handling used to be unconditional:
every `kind: "capacitor"` group had `generator: None` and was never
attempted, because no `klt` release drew a MIM capacitor on any PDK family.
That is no longer true for `cap_cmim` specifically, so the plan/build code
now branches **per model** (`CAP_GENERATORS`), not per `kind`:

- `cap_cmim` (SG13G2's own MIM capacitor) plans a `cap_array` request
  (`plate_w_um`/`plate_h_um`/`num`) and an `expected` shaped
  `{class, area_um2, perimeter_um, count}` — a MiM cap's extraction reports
  its two-plate geometric overlap (`devices[].params.area_um2`/
  `perimeter_um`), not a single `w_um`/`l_um` the way a MOS/resistor
  extraction does, so `_match_group_extraction` now branches on which
  dimension keys `expected` carries.
- `cap_cmomi` (the SG13CMOS5L port's own MoM capacitor, DR-004 / issue #22)
  still has no generator on any `klt` release and stays exactly as before:
  recorded in the plan, `generator: None`, never attempted — see
  `layout/sg13cmos5l-pll/README.md`'s own friction log, unaffected by this
  bump (re-verified as a non-regression check below).

`attempt_build`/`_match_block_extraction` now key "was this group drawn" off
each group's own `generator` field rather than `kind in ("mos_array",
"res_array")`, since `kind == "capacitor"` now covers both a drawable model
and a blocked one.

## What it is

- A **complete, schematic-derived device plan** for all six blocks
  (`spec/porting-plan.md` §1.4), grouped exactly the way a drawable design
  would be. `layout/tests/test_pll_layout_plan.py` covers the derivation
  (device-set-from-netlist correctness, per-block grouping, the DR-002
  device-flavor assertion, the schematic-vs-extraction match logic) with no
  PDK and no `klt`.
- A **real, reproduced build**: every `mos_array`/`res_array`/`cap_array`
  group is drawn (`klt gen`), re-extracted (`klt extract --deck sg13g2`),
  and compared against its own schematic-derived expectation —
  `gen.<group>.json`/`extract.<group>.json` under the current record carry
  the actual `klt` responses, not an assumption. No group's `match` result
  is hand-typed; `pll_layout.py`'s `_match_group_extraction` derives it from
  the extraction report alone (`(class, w_um, l_um, count)` for a
  MOS/resistor group, `(class, area_um2, perimeter_um, count)` for a
  capacitor group — see "What changed (issue #31)" above).
- A **composed cell per block**: every block's own successfully-drawn
  groups are placed into one `pll_<block>` cell (`klt gen-compose`,
  `placement.strategy: "explicit"`, a deterministic shelf-packed floorplan)
  — `compose.<block>.request.json`/`compose.<block>.response.json` under
  the current record. **Placement only, no `connectivity[]`/`routing`** —
  routing is a later, separate T1 checklist item (#6 item 3), explicitly
  out of scope per this issue's own Non-goals, so no net is drawn between
  two groups' pins here.
- A **block-level re-extraction cross-check**: each composed `pll_<block>`
  cell is itself re-extracted and its `device_counts` compared against the
  block's own schematic-derived per-class totals (`extract.pll_<block>.json`,
  `_match_block_extraction`) — the composition did not silently drop or
  duplicate a device on the way from per-group GDS to per-block GDS.
- **Not** a `pll_top` cell. Unlike sky130-pll's own #16 record, this design
  has no top-level netlist tying the six blocks together yet
  (`spec/porting-plan.md` §3.3 "Top-level integration" is future work), so
  this flow composes each block's own groups but nothing above the
  per-block level.

## What it is not

Stated plainly, mirroring `2AMLogic/sky130-pll`'s own `layout/pll/README.md`
"What it is not" section:

- **Not routed.** Block composition here is placement only; even the
  plan's own declared port/net map (`plan.json`, every group member's
  `ports`) is not fed to any router or declared as `gen-compose`
  `connectivity[]`. There is no top-level (`pll_top`) composition either
  (see "What it is" above).
- **Not DRC-clean, not LVS-clean, not a considered floorplan, not a
  verified circuit.** All strictly out of scope per issue #13's own
  Non-goals. The composed floorplan (`shelf_pack`) is a deterministic
  left-to-right pack with generous spacing, not a real floorplanner, and
  is not itself checked against any spacing rule (`klt drc` is a later,
  separate T1 checklist item).

## Friction: `klt`/deck gaps found drawing this

Per the root `CLAUDE.md` friction protocol, every gap below was checked
against [`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools)
first and filed (or cross-confirmed if already tracked) — generic tool-gap
description only, no design-specific content beyond the device classes
involved, per this repo's own audit-before-filing discipline.

**Resolved since PR #14's own record** (re-verified directly against the
bumped pin, not assumed from the closed tracker issues alone):

| Gap | Filed | Fixed by | Re-verified against |
| --- | --- | --- | --- |
| `klt gen mos_array`/`diff_pair` rejected the `sg13g2` PDK family outright — the unit device's shared gate-poly landing pad tripped `sg13g2`'s real `gatpoly.separation.activ.1` DRC rule. | [klayout-tools#1450](https://github.com/2AMLogic/klayout-tools/issues/1450) | [PR #1453](https://github.com/2AMLogic/klayout-tools/pull/1453) (narrowed unit-device gate-poly landing pad) | `klt 0.3.0+g5482cfe1c67e` (`5482cfe1c67eacf9d2f27d750a11a37ec14b1984`) against a real `ihp-sg13g2` install |
| `klt gen res_array` exposed only the `"generic"` (`rsil`, 7 Ω/□) `sg13g2` poly-resistor flavour; `rppd` (260 Ω/□) and `rhigh` (1360 Ω/□) — the two flavours this design actually uses — were rejected with `supported flavours: generic`. | [klayout-tools#1451](https://github.com/2AMLogic/klayout-tools/issues/1451) | [PR #1452](https://github.com/2AMLogic/klayout-tools/pull/1452) (widened `res_array`'s `sg13g2` flavour mechanism to a 3/4-slot `requires` set) | same |

**Resolved by issue #24's own pin bump** (`5482cfe…` → `04c0fa9…`;
re-verified directly at the new pin, not assumed from the closed tracker
issue alone):

| Gap | Filed | Fixed by | Re-verified against |
| --- | --- | --- | --- |
| The curated `sg13g2` extraction deck had no `capacitor` device class, so this design's `cap_cmim` shunt caps could not be recognised even once drawn. **This is a gap this repo itself filed and this repo's own bump retired.** | [klayout-tools#1454](https://github.com/2AMLogic/klayout-tools/issues/1454) | [PR #1456](https://github.com/2AMLogic/klayout-tools/pull/1456) (`04c0fa9…`, the current pin itself) | `klt 0.3.0+g04c0fa912213`: `klt deck info --deck sg13g2` now reports `nfet, pfet, cap_cmim, rfcmim, resistor, dantenna, dpantenna` |

**Resolved by issue #31's own pin bump** (`04c0fa9…` → `fdf04f71…`;
re-verified directly at the new pin, not assumed from the closed tracker
issue alone — this is the gap that took the SG13G2 record from 477 / 482 to
482 / 482):

| Gap | Filed | Fixed by | Re-verified against |
| --- | --- | --- | --- |
| `klt gen cap_array` rejected the `sg13g2` PDK family outright (`"PDK family 'sg13g2' has no MiM capacitor plate layers configured -- supported families: sky130"`), so this design's two `cap_cmim` shunt caps (`loop_filter.sch`) could not be drawn via `klt gen`. **This is a gap this repo itself filed (from issue #13's own pass) and this repo's own bump retired.** | [klayout-tools#1455](https://github.com/2AMLogic/klayout-tools/issues/1455) (filed by #13's pass; not the same gap as #1117, which added `cap_array` for `sky130` only and never covered `sg13g2`) | [PR #1461](https://github.com/2AMLogic/klayout-tools/pull/1461) (`25c52af27f5518959f8afa2e11c5449741886c9c`) | `klt 0.3.0+gfdf04f71ab39` (`fdf04f71ab39159838acb86e63a92d6fa0c714fa`): `klt gen cap_array --pdk ihp-sg13g2 --params '{"plate_w_um": 40, "plate_h_um": 40, "num": 1}'` draws real geometry, and `klt extract --deck sg13g2` re-recognises it as `cap_cmim` with `area_um2: 1600.0`, `perimeter_um: 160.0` — exactly the drawn 40×40 µm plate. All five of this design's `cap_cmim` instances (`loop_filter` ×2, `vco` ×1, `lock_detector` ×2) drew and matched in the same run — see `reports/LATEST`. |

**Not re-filed** (closed, cited for completeness — the deferral chain the
now-resolved gap above builds on): [klayout-tools#1233](https://github.com/2AMLogic/klayout-tools/issues/1233)
(closed — investigated `cap_cmim`/`rfcmim` recognition, made a deliberate
"defer until the metals/vias stack reaches Metal5/TopMetal1" call, filed
#1243 as that prerequisite) and [klayout-tools#1243](https://github.com/2AMLogic/klayout-tools/issues/1243)
(closed — landed the `metals`/`vias` stack extension itself, via PR #1247;
does **not** itself declare `capacitors=`, which is exactly the gap #1454
tracked).

**No open gaps at the current pin.** Every device class this design's
schematic needs — `nfet`/`pfet` (`mos_array`), `rppd`/`rhigh` (`res_array`),
`cap_cmim` (`cap_array`) — draws on `sg13g2` and is recognised on
re-extraction. `klt deck info --deck sg13g2` reports `nfet, pfet, cap_cmim,
rfcmim, resistor, dantenna, dpantenna` as recognised *extraction* device
classes, and every one this design uses now also has a working *generator*.

**Non-regression on the MOS/resistor side, re-verified at the current pin.**
`mos_array`/`res_array` continue to draw, extract, and match exactly as
they did after issue #24's own pin bump — this bump did not touch that
code path or its own upstream fixes (klayout-tools#1450/#1451).

## Directory layout

```
layout/pll/
  README.md                  # this file
  reports/
    LATEST                   # plain-text pointer to the newest record id
    <record-id>/             # <YYYYMMDD-HHMMSS>-<short-git-sha>[-dirty]
      record.md              # verdict + per-block table + friction (read first)
      plan.json               # the schematic-derived plan: every group's klt gen
                               # request + full port/net map, for every block
      build.json               # per-group draw/extract/match + per-block
                                # compose/extract results (this run)
      gen.<group>.json         # each group's raw `klt gen` attempt + response
      extract.<group>.json     # each drawn group's own `klt extract` result
      compose.<block>.request.json   # each block's `klt gen-compose` request
      compose.<block>.response.json  # ...and its response
      extract.pll_<block>.json       # the composed block cell's own `klt extract` result
      <group>.gds / pll_<block>.gds  # the drawn/composed streams themselves
```

`<record-id>` mirrors `sim/`'s `<YYYYMMDD>-<HHMMSS>-<short-git-sha>` (UTC)
convention (see `sim/README.md`) — including the `-dirty` suffix's meaning:
*the flow that produced this evidence differed from the named commit*
(tracked-file changes outside `layout/pll/reports/` itself, which a run
always creates).
