# layout/ — the klayout-tools (`klt`) layout flow

Two ports, two evidence trails:

- [`pll/`](pll/) — the **SG13G2** device-level layout (issue #13). Start at
  [`pll/README.md`](pll/README.md), then the current record's `record.md`
  (`pll/reports/LATEST`). T1 checklist item 2 for the block tracked by
  `2AMLogic/sg13g2-pll#6` (this repo's own T1 tracker).
- [`sg13cmos5l-pll/`](sg13cmos5l-pll/) — the **SG13CMOS5L** layout (issues #24
  and #29, part of the #16 Chipalooza port). Start at
  [`sg13cmos5l-pll/README.md`](sg13cmos5l-pll/README.md), then
  `sg13cmos5l-pll/reports/LATEST`. Unlike the SG13G2 side this one is
  **routed and LVS-compared**: 485 / 490 devices draw, all six blocks compose,
  route (1476 terminals, 255 nets) and pass `klt drc --deck sg13cmos5l` with
  zero violations, and `klt lvs` reports **`match` — every device and every
  net — on all three blocks whose reference netlist can be converted**. The
  other three cannot be converted at all, for a named, open upstream reason
  (klayout-tools#1463).

Both flows share one pinned `klt` install (`requirements.txt`) and one plan
half (`bin/pll_layout.py`), so what "the schematic's device set" means cannot
drift between them.

As of #13's own record, every device the six committed block netlists
(`design/netlist/*.spice`) declare that has a `klt gen` generator on
`sg13g2` today **draws, re-extracts, and matches the schematic's own
`(class, W, L)`**, per block (composed into one `pll_<block>` cell per
block, placement only — no routing). The one exception is this design's two
MiM capacitors (`loop_filter.sch`'s `cap_cmim` shunt caps): no `klt gen`
generator draws a MIM capacitor for `sg13g2` at the current pin — a real,
tracked upstream gap, not a silently dropped device; see `pll/README.md`'s
own "Status"/"Friction" sections. Routing, DRC-clean closure, and LVS-clean
closure are later, separate T1 checklist items on this side. (The
SG13CMOS5L side reached DRC-clean and then LVS-`match` first, because it
draws its own footprints *and* its own interconnect rather than waiting on a
generator — see `sg13cmos5l-pll/README.md` for why both are filed upstream
tool gaps rather than deck work-arounds. The footprint half of that
(klayout-tools#1462) has since closed upstream; issue #35 re-measured
generator output against it and **kept the local footprints**, because the
generator draws the thin-oxide device class and leaves the PMOS body
unbiased on this family — klayout-tools#1472/#1473. The interconnect half,
klayout-tools#1467, reproduces unchanged at the current pin.)

Two rules from the root `CLAUDE.md` shape this directory:

- **Verification is the product.** Every claim here — drawn, blocked, or
  otherwise — ships with the actual `klt` output it came from, not an
  assertion.
- **Friction protocol.** Every `klt`/deck gap hit while standing this flow
  up is checked against the public
  [`2AMLogic/klayout-tools`](https://github.com/2AMLogic/klayout-tools)
  tracker and filed (or cross-confirmed if already tracked) there —
  tool-gap description only, never this repo's own design/spec content.

## Quick start (cold machine)

```bash
# 1. install the pinned klt build (see layout/requirements.txt for the pin
#    and its own bump history)
layout/bin/setup-venv.sh

# 2. sanity-check both PDKs resolve (setup-venv.sh already checks both)
layout/.venv/bin/klt pdk find --pdk ihp-sg13g2
layout/.venv/bin/klt pdk find --pdk ihp-sg13cmos5l

# 3a. SG13G2: derive the plan, draw it, extract + compose every block
layout/bin/run-pll-layout-flow.sh

# 3b. SG13CMOS5L: the same, plus DRC and LVS on every group and block
layout/bin/run-pll-cmos5l-layout-flow.sh
```

Each command writes a fresh, timestamped record under its own port's
`reports/<record-id>/` and updates that port's `reports/LATEST` to point at
it.

## Directory layout

```
layout/
  README.md                  # this file
  requirements.txt           # pinned klt install (git commit; see its own header)
  bin/
    pll_layout.py                  # schematic -> device plan -> klt gen/extract/gen-compose (SG13G2)
    run-pll-layout-flow.sh         # SG13G2 driver: plan -> draw/extract/compose -> record.md
    render-pll-record.py           # renders a SG13G2 record's record.md
    cmos5l_devices.py              # SG13CMOS5L device footprints (klayout.db)
    pll_cmos5l_layout.py           # SG13CMOS5L: plan -> draw -> klt drc/extract/lvs -> compose
    run-pll-cmos5l-layout-flow.sh  # SG13CMOS5L driver
    render-pll-cmos5l-record.py    # renders a SG13CMOS5L record's record.md
    setup-venv.sh                  # create/refresh layout/.venv from requirements.txt
  tests/                           # PDK-free unit coverage (plan + geometry, no klt subprocess)
  .venv/                           # gitignored -- klt install, created by setup-venv.sh
  pll/                             # SG13G2 layout + records (see pll/README.md)
  sg13cmos5l-pll/                  # SG13CMOS5L layout + records (see its README.md)
```
