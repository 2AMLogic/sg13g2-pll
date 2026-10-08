# sg13g2-pll

An integer-N phase-locked loop on
[IHP SG13G2](https://github.com/IHP-GmbH/IHP-Open-PDK), a 130 nm SiGe BiCMOS
open PDK — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: design and layout landed; verification partial; not sign-off-ready.**
The porting plan ([`spec/porting-plan.md`](spec/porting-plan.md)) and
architecture/device-flavor decision records
([`spec/decision-records/`](spec/decision-records/)) are written. Both a
SG13G2 and an SG13CMOS5L port of the block exist as xschem schematics
([`design/`](design/)) with device-level layout ([`layout/`](layout/)), and
simulation evidence is on file under [`sim/`](sim/). No whole-PLL, full-PVT or
tape-out sign-off is claimed; the graded verdict of record is in
[`manifests/README.md`](manifests/README.md).

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

## Two PDK targets

The two targets have separate evidence trails; a result on one does not carry
to the other.

- **IHP SG13G2** (BiCMOS) is the repo's origin. Its schematics are the
  top-level [`design/`](design/) blocks and its device-level layout is
  [`layout/pll/`](layout/pll/README.md). Evidence is thinner here than on
  the port; see [`sim/`](sim/README.md) for what exists.
- **IHP SG13CMOS5L** is a later port for Chipalooza Challenge #6 (see below):
  [`design/sg13cmos5l/`](design/sg13cmos5l/),
  [`layout/sg13cmos5l-pll/`](layout/sg13cmos5l-pll/README.md) and the
  `sim/sg13cmos5l-*` campaigns. Readiness and rail decisions are
  [DR-003](spec/decision-records/DR-003-sg13cmos5l-port-readiness.md) and
  [DR-004](spec/decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md).

## Target specification

The target specification is **still a draft in progress**: no ratified
target-spec table exists, and none should be inferred from the decision
records. The porting plan carries the sibling PLLs' spec structure onto
SG13G2 and binds no numeric value; drafting the spec is tracked in issue
[#148](https://github.com/2AMLogic/sg13g2-pll/issues/148). See
[`spec/README.md`](spec/README.md) for the index. No value is binding until
ratified through a decision record, and no value is ever edited to match a
simulation result. Open measured gaps (for example lock-time row 7, issue
[#150](https://github.com/2AMLogic/sg13g2-pll/issues/150)) stay visible in
the proposal and tier report rather than being relaxed.

Maturity ladder: porting plan → spec ratified → schematic simulated across
PVT → layout DRC/LVS-clean → post-layout re-verification → shuttle seat →
measured silicon. **Current position:** porting plan and architecture
decisions done; spec not ratified; schematics and layout drawn with partial
simulation and post-layout evidence; later rungs not reached. For the
current graded count see
[`manifests/README.md`](manifests/README.md) and the committed
[tier report](manifests/sg13g2-pll.tier-report.json) rather than a number
copied here.

## Chipalooza

This design is also entered against [Chipalooza Challenge #6](https://opencircuitdesign.com/chipalooza/challenge-6.html)
(IHP SG13CMOS5L), part of the fleet's own program epic
([2AMLogic/2am#542](https://github.com/2AMLogic/2am/issues/542)). The
submission document — block type, I/O mapped to the challenge's slot
budget, functional description, and a spec table re-derived from real
SG13CMOS5L `sim/`/`layout/` evidence, with every unmet or
insufficient-evidence row stated explicitly — is
[`docs/chipalooza/challenge-6-proposal.md`](docs/chipalooza/challenge-6-proposal.md).
**Status: not sign-off-ready.** Schematic port and layout have landed; the
PVT sim campaign is intentionally partial (see the document's own "Status"
line for what is and is not yet evidenced).

## Repo layout

```
spec/          ratified spec + decision records
design/        schematics / netlists (xschem)
sim/           testbenches + PVT corner results (ngspice)
layout/        GDS + DRC/LVS reports (klayout-tools driven)
manifests/     klt signoff block manifest + graded tier report (the T1 verdict of record)
measurements/  silicon characterization (empty until tape-out)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
