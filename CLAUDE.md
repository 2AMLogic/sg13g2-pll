# sg13g2-pll — agent instructions

Open-source canary block: an integer-N phase-locked loop on IHP SG13G2, a
130 nm SiGe BiCMOS open PDK, designed and verified by AI agents.

- **PDK**: IHP SG13G2 (open PDK, IHP-GmbH/IHP-Open-PDK). Open-source flow:
  xschem + ngspice for design/sim, klayout-tools (`klt`) for layout work.
- **The SG13G2 deck is new — starter-grade.** `klt` resolves this PDK and a
  curated SG13G2 DRC/LVS starter deck ships with klayout-tools, but that deck
  is young and has met almost no real blocks. Deck gaps — missing rules,
  devices extraction can't recognize, checks that are wrong for BiCMOS
  structures — are *expected* friction here, not a surprise. When you hit
  one, file it upstream rather than routing around it: working around a deck
  gap silently destroys the reason this repo was opened.
- **The PDK is the variable, not the design.** This block is a port of the
  fleet's proven PLLs (`2AMLogic/gf180-pll`, `2AMLogic/sky130-pll`) *on
  purpose*. Anything that breaks should be assumed to be the PDK, the deck,
  or the tools before it is assumed to be the circuit. Start from the sibling
  repos' schematics, ratified specs, and decision records rather than from a
  blank page.
- **BiCMOS is a real difference.** SG13G2 offers actual SiGe bipolar devices,
  not just CMOS. That widens the circuit's device choices exactly where a PLL
  is sensitive — the VCO (device class and topology options the CMOS ports
  never had), the charge pump, and the dividers — and gives extraction and
  LVS a device class the decks have barely handled. Expect friction there
  specifically, and record device-choice decisions as decision records.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design.
- **Verification is the product**: no claim without a testbench. PVT corners
  on every recorded result; `sim/` results are append-only evidence.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass.

<!-- BEGIN LOOM ORCHESTRATION -->
This repository uses [Loom](https://github.com/rjwalters/loom) for AI-powered development orchestration — see the Loom repository for the full guide (roles, labels, worktrees, configuration). When installed, Loom also writes a locally-substituted copy of that guide to `.loom/CLAUDE.md`.
<!-- END LOOM ORCHESTRATION -->
