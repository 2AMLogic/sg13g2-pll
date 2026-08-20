# sg13g2-pll

An integer-N phase-locked loop on
[IHP SG13G2](https://github.com/IHP-GmbH/IHP-Open-PDK), a 130 nm SiGe BiCMOS
open PDK — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: just opened.** Nothing is designed yet. The first task is a porting
plan (issue #1): what carries over from the sibling PLLs, and what SG13G2
changes.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using SG13G2, not just this repo.

## Why this block, on this PDK

This is a **port**, on purpose. The fleet has already designed this block
twice: [gf180-pll](https://github.com/2AMLogic/gf180-pll) carried an
integer-N, ring-oscillator PLL through schematic design and a large PVT
verification campaign on gf180mcu, and its sky130 port (`sky130-pll`, not yet
public) repeated the exercise on a second PDK. Those repos hold the
schematics, the ratified specs, and the decision records this one starts
from. If the design is one we understand well, then anything that breaks here
is the PDK, the deck, or the tools — not the circuit. **The PDK is the
variable, not the design.**

SG13G2 being a **BiCMOS** process makes a PLL a particularly interesting
port: real SiGe bipolar devices change the option space exactly where a PLL
is sensitive — the VCO's device class and topology, the charge pump, the
dividers — and hand extraction and LVS a device class the young SG13G2 decks
have barely met.

## Tooling — new deck, expect friction

`klt` resolves SG13G2, and klayout-tools ships a curated SG13G2 DRC/LVS
starter deck. That deck is **new and starter-grade**: it has met almost no
real blocks, and this repo is one of its first forcing functions. Deck gaps
are expected; the canary's job is to find them and file them upstream at
[klayout-tools](https://github.com/2AMLogic/klayout-tools), not to route
around them.

## Target specification

Not drafted yet. The porting plan (issue #1) produces the DRAFT spec by
carrying the sibling PLLs' spec structure — output band, reference input,
multiplication ratio, jitter, spurs, loop dynamics, lock time, power, area —
onto SG13G2, deciding per row what ports over, what must be re-derived on
this process, and what the supply/device flavor choice (1.2 V core CMOS,
3.3 V thick-oxide, or bipolar where it earns its place) does to the numbers.
No value is binding until it is ratified through a decision record, and no
value is ever edited to match a simulation result.

Maturity ladder: porting plan → spec ratified → schematic simulated across
PVT → layout DRC/LVS-clean → post-layout re-verification → shuttle seat →
measured silicon. **Current position: just opened, pre-plan.**

## Repo layout

```
spec/          ratified spec + decision records
design/        schematics / netlists (xschem)
sim/           testbenches + PVT corner results (ngspice)
layout/        GDS + DRC/LVS reports (klayout-tools driven)
measurements/  silicon characterization (empty until tape-out)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
