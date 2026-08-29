# layout/ — the klayout-tools (`klt`) layout flow

[`pll/`](pll/) is the PLL's **device-level layout** work: start at
[`pll/README.md`](pll/README.md), then the current record's `record.md`
(`pll/reports/LATEST`). This is T1 checklist item 2 for the block tracked by
`2AMLogic/sg13g2-pll#6` (this repo's own T1 tracker), issue #13.

As of #13's own record, this is a **schematic-derived device plan**, not yet
a drawn layout — every one of the 482 devices the six committed block
netlists (`design/netlist/*.spice`) declare fails to draw against the
current `klt` + `ihp-sg13g2` PDK, for reasons that are reproduced and cited
in `pll/README.md`'s own "Status"/"Friction" sections rather than assumed.
Routing, DRC-clean closure, and LVS-clean closure are later, separate T1
checklist items once a device set actually draws.

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
#    and why it is exactly the commit that merged klayout-tools#1449)
layout/bin/setup-venv.sh

# 2. sanity-check the SG13G2 PDK resolves
layout/.venv/bin/klt pdk find --pdk ihp-sg13g2

# 3. derive the plan and attempt to draw it
layout/bin/run-pll-layout-flow.sh
```

The last command writes a fresh, timestamped record under
`pll/reports/<record-id>/` and updates `pll/reports/LATEST` to point at it.

## Directory layout

```
layout/
  README.md                  # this file
  requirements.txt           # pinned klt install (git commit; see its own header)
  bin/
    pll_layout.py             # schematic -> device plan -> klt gen build attempt
    run-pll-layout-flow.sh    # the driver: plan -> build attempt -> record.md
    render-pll-record.py      # renders a record's record.md from plan/build json
    setup-venv.sh              # create/refresh layout/.venv from requirements.txt
  tests/                      # PDK-free unit coverage (the "plan" half only)
  .venv/                      # gitignored -- klt install, created by setup-venv.sh
  pll/                        # the PLL device-level layout + its records (see pll/README.md)
```
