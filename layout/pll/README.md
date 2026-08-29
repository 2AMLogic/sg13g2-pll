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

## Status: blocked — 0 of 482 planned devices draw today

**This is the honest headline.** `layout/bin/pll_layout.py` derives a
complete, schematic-accurate device plan (every device every block's
netlist declares, grouped by `(class, W, L)` into `klt gen` requests) — that
half is real, tested, and PDK-free (`layout/tests/test_pll_layout_plan.py`).
But **every one of those requests fails against the current `klt` +
`ihp-sg13g2` PDK**, for three distinct, first-hand-reproduced reasons (see
"Friction" below):

| Block | Devices (schematic) | Devices drawn |
| --- | --- | --- |
| `pfd` | 64 | 0 |
| `cp` | 14 | 0 |
| `loop_filter` | 3 | 0 |
| `vco` | 45 | 0 |
| `divider_chain` | 316 | 0 |
| `lock_detector` | 40 | 0 |
| **Total** | **482** | **0** |

This is not a stale-install artifact or a config mistake in this flow.
`layout/requirements.txt` pins the exact commit
(`6d2028a32bfd385724498941572f3976783ae720`) that merged
`klayout-tools#1449` — the PR that closed this issue's own former
dependency, `klayout-tools#1448` ("no sg13g2 entry in the analog-primitive
generators' PDK-family role-layer table"). Re-verifying *end-to-end*
against that exact commit and a real `ihp-sg13g2` install, per this issue's
own instruction ("confirm `klt gen --pdk sg13g2` actually works end-to-end
for this design's device classes before relying on this note alone"), found
that closing #1448 did **not**, in practice, unblock drawing this design:

- `mos_array` (and `diff_pair`) reject the `sg13g2` PDK family **outright**,
  by design — the fix PR's own body documents a real, verified DRC rejection
  (the unit device's shared gate-poly landing pad trips `sg13g2`'s
  `gatpoly.separation.activ.1` rule), not a missing table entry. This alone
  blocks every MOSFET in every block — **469 of this design's 482 devices**.
- `res_array`'s `sg13g2` support exposes only the `"generic"` (`rsil`)
  poly-resistor flavour. This design's own resistors are `rppd`/`rhigh`
  (`design/README.md` "Device choices and the LVS deck"), both rejected.
- `cap_array` has no `sg13g2` MiM-capacitor plate layers on any family — the
  same known gap already named in `spec/porting-plan.md` §3.3 and this
  issue's own Non-goals (no capacitor-class device is in scope here).

## What it is

Given the above, this deliverable today is:

- A **complete, schematic-derived device plan** for all six blocks
  (`spec/porting-plan.md` §1.4), grouped exactly the way a drawable design
  would be — real evidence of what the layout *would* contain, not a
  placeholder. `layout/tests/test_pll_layout_plan.py` covers the derivation
  (device-set-from-netlist correctness, per-block grouping, the DR-002
  device-flavor assertion) with no PDK and no `klt`.
- A **real, reproduced build attempt** against the current `klt` + PDK: the
  flow does not hardcode "blocked" — it runs every planned `klt gen` request
  and records the actual result. If a future `klt` release resolves either
  upstream gap, re-running `layout/bin/run-pll-layout-flow.sh` picks that up
  automatically with **no code change** here; `devices_drawn_total` in the
  refreshed `build.json` is the signal to watch.
- **Not** a drawn GDS. `reports/<record-id>/` carries no `.gds` file this
  run, because no group succeeded — `klt gen` never produces one on a
  failed request.

There is also no `pll_top` composed cell (unlike sky130-pll's own #16
record): this design has no top-level netlist tying the six blocks together
yet (`spec/porting-plan.md` §3.3 "Top-level integration" is future work), so
this flow composes nothing above the per-block level even once/if a block's
groups draw.

## What it is not

Stated plainly, mirroring `2AMLogic/sky130-pll`'s own `layout/pll/README.md`
"What it is not" section:

- **Not drawn.** Zero devices, in any block, today — see "Status" above.
- **Not routed.** Even the plan's own declared port/net map (`plan.json`,
  every group member's `ports`) is not fed to any router; there is nothing
  to route without drawn geometry to route between.
- **Not DRC-clean, not LVS-clean, not a considered floorplan, not a
  verified circuit.** All strictly out of scope per issue #13's own
  Non-goals even before the blocker above, and unreachable without a drawn
  stream regardless.

## Friction: `klt`/deck gaps found drawing this

Per the root `CLAUDE.md` friction protocol, every gap below was checked
against [`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools)
first (no existing tracking issue matched either search) and filed —
generic tool-gap description only, no design-specific content beyond the
device classes involved, per this repo's own audit-before-filing
discipline.

| Gap | Filed | Reproduced against |
| --- | --- | --- |
| `klt gen mos_array`/`diff_pair` reject the `sg13g2` PDK family outright — the unit device's shared gate-poly landing pad trips `sg13g2`'s real `gatpoly.separation.activ.1` DRC rule. Blocks every MOSFET (469/482 of this design's devices) on every block. | [klayout-tools#1450](https://github.com/2AMLogic/klayout-tools/issues/1450) | `klt 0.3.0+g6d2028a32bfd` (`6d2028a32bfd385724498941572f3976783ae720`) against a real `ihp-sg13g2` install |
| `klt gen res_array` exposes only the `"generic"` (`rsil`, 7 Ω/□) `sg13g2` poly-resistor flavour; `rppd` (260 Ω/□) and `rhigh` (1360 Ω/□) — the two flavours this design actually uses — are rejected with `supported flavours: generic`, even though both are real, separately-recognised `klt deck info --deck sg13g2` device classes. | [klayout-tools#1451](https://github.com/2AMLogic/klayout-tools/issues/1451) | same |

**Not re-filed** (already tracked, cited for completeness): `klt gen
cap_array` has no `sg13g2` MiM-capacitor support on any family, and the
underlying extraction-deck gap (no MIM capacitor device class in the
curated `sg13g2` deck at all) is `klayout-tools#1233`, filed before this
issue and already naming the exact device class this design's loop filter
uses (`design/README.md` "Device choices and the LVS deck"). This design's
capacitors are recorded in `plan.json` (never silently dropped) but never
attempted in the build step — capacitor devices are explicitly out of
scope per issue #13's own Non-goals regardless of the extraction-deck gap.

**Also confirmed, not a gap**: `klt deck info --deck sg13g2` reports
`nfet, pfet, resistor, dantenna, dpantenna` as recognised *extraction*
device classes — the deck (check) side is real. The gap is specifically on
the generator (draw) side, exactly as `klayout-tools#1448`'s own original
description (before it closed) already distinguished.

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
      build.json               # per-group build-attempt results (this run)
      gen.<group>.json         # each group's raw klt gen attempt + response
```

No `.gds` file exists in the current record — see "Status" above. Once a
group draws successfully (either from an upstream fix or a future re-run),
its own `<group>.gds` lands alongside `gen.<group>.json`, matching
sky130-pll's own convention.

`<record-id>` mirrors `sim/`'s `<YYYYMMDD>-<HHMMSS>-<short-git-sha>` (UTC)
convention (see `sim/README.md`) — including the `-dirty` suffix's meaning:
*the flow that produced this evidence differed from the named commit*
(tracked-file changes outside `layout/pll/reports/` itself, which a run
always creates).
