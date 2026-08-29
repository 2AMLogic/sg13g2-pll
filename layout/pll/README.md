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

## Status: 477 / 482 planned devices draw, extract, and match the schematic — every block composes

**This is the honest headline.** `layout/bin/pll_layout.py` derives a
complete, schematic-accurate device plan (every device every block's
netlist declares, grouped by `(class, W, L)` into `klt gen` requests) and
then, for the two device classes `klt gen` can draw on `sg13g2`
(`mos_array`/`res_array`), draws each group, re-extracts it
(`klt extract --deck sg13g2`), and compares the extracted `(class, W, L,
count)` against the schematic's own — then composes every block's own
drawn groups into one `pll_<block>` cell (`klt gen-compose`, placement
only) and re-extracts *that* composed cell too, cross-checking its
device-count multiset against the block's schematic-derived totals:

| Block | Devices (schematic) | Devices drawn + matched | Composed | Block re-extract matches schematic |
| --- | --- | --- | --- | --- |
| `pfd` | 64 | 64 | yes | yes |
| `cp` | 14 | 14 | yes | yes |
| `loop_filter` | 3 | 1 | yes | yes |
| `vco` | 45 | 44 | yes | yes |
| `divider_chain` | 316 | 316 | yes | yes |
| `lock_detector` | 40 | 38 | yes | yes |
| **Total** | **482** | **477** | **6/6** | **6/6** |

The 5-device shortfall is exactly this design's two `cap_cmim` MiM
capacitors in `loop_filter` and the three MiM/decap capacitor instances in
`vco`/`lock_detector` (`vco_XCDECAP`, `lock_detector_XCW`,
`lock_detector_XDW.XC1`) — **never silently dropped**: every one is
recorded in `plan.json` with `kind: "capacitor"`, and the reason it is
never attempted is cited on that group itself (`blocked_reason`) and below
under "Friction". Every other device this design's schematic declares —
every MOSFET, every resistor — draws, re-extracts, and matches.

This is not a stale-install artifact or a config mistake in this flow.
`layout/requirements.txt` pins the exact commit
(`5482cfe1c67eacf9d2f27d750a11a37ec14b1984`, `main` HEAD as of this record)
that carries both the fix for `klayout-tools#1450` (`mos_array`/`diff_pair`
rejecting `sg13g2` outright) and `klayout-tools#1451` (`res_array` only
exposing the `"generic"` flavour) — the two gaps a prior pass at this issue
(PR #14) filed after re-verifying `klayout-tools#1448`'s own closure did
*not*, by itself, unblock drawing this design. Re-verifying *end-to-end*
against the bumped pin, per this issue's own instruction to confirm rather
than assume a closed tracker issue means a clean run, found both gaps
fixed: `klt gen mos_array --pdk ihp-sg13g2 --params '{"flavor": "nfet", ...}'`
and `klt gen res_array --pdk ihp-sg13g2 --params '{"flavor": "rppd", ...}'`
(and `"rhigh"`) now draw real geometry, and `klt extract --deck sg13g2`
re-recognises exactly the requested device class and dimensions back.

## What it is

- A **complete, schematic-derived device plan** for all six blocks
  (`spec/porting-plan.md` §1.4), grouped exactly the way a drawable design
  would be. `layout/tests/test_pll_layout_plan.py` covers the derivation
  (device-set-from-netlist correctness, per-block grouping, the DR-002
  device-flavor assertion, the schematic-vs-extraction match logic) with no
  PDK and no `klt`.
- A **real, reproduced build**: every `mos_array`/`res_array` group is
  drawn (`klt gen`), re-extracted (`klt extract --deck sg13g2`), and
  compared against its own schematic-derived `(class, W, L, count)`
  expectation — `gen.<group>.json`/`extract.<group>.json` under the current
  record carry the actual `klt` responses, not an assumption. No group's
  `match` result is hand-typed; `pll_layout.py`'s `_match_group_extraction`
  derives it from the extraction report alone.
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

- **Not fully drawn.** Every device this design's schematic declares that
  has a `klt gen` generator on `sg13g2` draws — this design's two MiM
  capacitors do not, for the tracked upstream reason under "Friction".
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

**Still open**, found/re-confirmed by this pass:

| Gap | Filed | Status |
| --- | --- | --- |
| `klt gen cap_array` rejects the `sg13g2` PDK family outright (`"PDK family 'sg13g2' has no MiM capacitor plate layers configured -- supported families: sky130"`) — reproduced directly this pass, not inferred from #1117 (which added `cap_array` for `sky130` only and never covered `sg13g2`, so is not the same gap). This design's two `cap_cmim` shunt caps (`loop_filter.sch`) cannot be drawn via `klt gen` as a result. | [klayout-tools#1455](https://github.com/2AMLogic/klayout-tools/issues/1455) (new, filed by this pass) | tracked, open |
| The curated `sg13g2` extraction deck still has no `capacitor` device class — confirmed directly this pass via `klt deck info --deck sg13g2` (`device_classes: nfet, pfet, resistor, dantenna, dpantenna`, no `capacitor` entry) — even though the Metal2-stack limit issue #1233 originally deferred `cap_cmim`/`rfcmim` recognition on (issue #1243) has since landed. The deck's own current source comment (`sg13g2.py`'s "MIM capacitors" section) says recognition is "now a standalone follow-on (issue #1233, reopened against the extended stack)", but #1233 is still closed with no open successor — filed fresh as [klayout-tools#1454](https://github.com/2AMLogic/klayout-tools/issues/1454) rather than assuming push/reopen access to #1233. | [klayout-tools#1454](https://github.com/2AMLogic/klayout-tools/issues/1454) (new, filed by this pass) | tracked, open |

**Not re-filed** (closed, cited for completeness — the deferral chain the
still-open gap above builds on): [klayout-tools#1233](https://github.com/2AMLogic/klayout-tools/issues/1233)
(closed — investigated `cap_cmim`/`rfcmim` recognition, made a deliberate
"defer until the metals/vias stack reaches Metal5/TopMetal1" call, filed
#1243 as that prerequisite) and [klayout-tools#1243](https://github.com/2AMLogic/klayout-tools/issues/1243)
(closed — landed the `metals`/`vias` stack extension itself, via PR #1247;
does **not** itself declare `capacitors=`, which is exactly the gap #1454
now tracks).

**Also confirmed, not a gap**: `klt deck info --deck sg13g2` reports
`nfet, pfet, resistor, dantenna, dpantenna` as recognised *extraction*
device classes — every class this design's drawn devices (MOSFETs,
resistors) need is covered; only the capacitor class remains missing.

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
