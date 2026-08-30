# `design/` — schematic capture

xschem schematics and symbols for the PLL's blocks, plus the export step that
turns them into the SPICE the (future) `sim/` testbenches will simulate.
Layout is `layout/`, measured silicon is `measurements/`, and every claim
about any of these will live in `sim/` under the append-only record format a
future issue establishes (`spec/porting-plan.md` §1.3).

This is **T1 item 1 (design sources)** for the block tracked by #6 — see
issue #7. Per that issue's own Non-goals, this pass commits schematics +
symbols + the derived netlist export only; layout, DRC/LVS, PVT corners, and
testbenches are explicitly out of scope and land in later T1 increments.

```
design/
  xschemrc               project-local xschem config (resolves the SG13G2
                          PDK, adds this repo's own design/ to the symbol path)
  netlist.sh              batch netlist exporter -- every block, one script
  netlist/*.spice          committed exports (checked by `netlist.sh --check`)

  # The six blocks spec/porting-plan.md Sec1.4 names (issue #7 Test Plan:
  # every one of these must be represented, not a partial subset)
  pfd.sch / .sym            tri-state phase-frequency detector
  cp.sch / .sym              charge pump
  loop_filter.sch / .sym    passive fixed 2nd-order filter
  vco.sch / .sym             current-starved ring VCO
  divider_chain.sch / .sym  feedback divider
  lock_detector.sch / .sym  phase-error window comparator

  # PFD-owned leaf cells
  srlatch.sch/.sym          NAND cross-coupled SR latch (active-high S/R)
  edgedet.sch/.sym          rising-edge pulse generator (5-stage delay chain)

  # Charge-pump-owned leaf cells
  cp_leg_n.sch/.sym         NMOS sink leg: mirror + cascode + steering switches
  cp_leg_p.sch/.sym         PMOS source leg: mirror + cascode + steering switches
  cp_dumpbuf.sch/.sym       VDUMP tracking buffer (simplified, see below)

  # VCO-owned leaf cells
  vco_bias.sch/.sym         beta-multiplier core + V-I converter + band select
  vco_stage.sch/.sym        current-starved delay cell (PMOS head + inv + NMOS tail)

  # Feedback-divider-owned leaf cells
  div23_cell.sch/.sym       one /2//3 divider cell (Vaucher-style)

  # Shared static-CMOS logic library (used by 2+ blocks)
  inv_hv, inv2x_hv, nand2_hv, nand3_hv, nor2_hv, xor2_hv,
  tgate_hv, schmitt_hv, delaywin_hv, dff_tg_hv
```

## Device flavour and architecture

Every device in every schematic here is SG13G2 3.3 V thick-oxide CMOS
(`sg13_hv_nmos` / `sg13_hv_pmos`), per
[`spec/decision-records/DR-002-supply-device-flavor.md`](../spec/decision-records/DR-002-supply-device-flavor.md)
Decision 0 — no thin-oxide (1.2 V) devices and no bipolar (SiGe HBT) devices
anywhere in this pass, matching DR-002's Decisions 1–3 (bias reference,
charge-pump cascode, and divider first stage are all explicitly deferred
CMOS-only in v1). The block decomposition, loop type, VCO topology and
divider architecture follow
[`spec/decision-records/DR-001-pll-architecture.md`](../spec/decision-records/DR-001-pll-architecture.md).

**Sizing is provisional throughout.** Every device width/length here is a
first-pass placeholder, not simulation-grounded against real SG13G2 device
data — consistent with `spec/porting-plan.md`'s own per-row disposition table
(almost every numeric row is "re-derive," not "port"). A future
device-characterization and tuning-range campaign (T1 items 8–9, tracked
under #6) re-derives every number here; this issue's own Non-goals exclude
that work.

**File organization**: one `.sch` + `.sym` pair per cell, in a single flat
`design/` namespace — matching gf180-pll's own convention (`design/README.md`
"File organization"), which this repo verified directly against that repo's
tree rather than assuming the directory-per-block layout the curator's
initial (explicitly unverified) issue text speculated. A leaf cell used by
only one block is still named without a block prefix in this first pass
(e.g. `srlatch`, `vco_bias`) since there is no cross-block naming collision
yet; if a future block needs a same-named cell sized differently, that is
the trigger for gf180-pll's own `<block-prefix>_<cellname>` leaf-cell
ownership convention (DR-004 in that repo) — not adopted pre-emptively here.

**Connectivity is label-driven**: every device terminal carries a `lab_pin`
(or `ipin`/`opin`/`iopin` at a block's own boundary) placed exactly on the
terminal's coordinate, rather than a drawn wire — the same convention
gf180-pll's and sky130-pll's own schematics use. One consequence worth
recording for anyone editing these by hand: xschem treats a wire that
directly joins two *differently-labeled* pins as a short (two names
claiming one net), not as a rename — so a single net has exactly one
canonical label everywhere it is touched, including at a block's own
external port (e.g. `divider_chain`'s `DIVOUT` pin is the literal label on
the last divider cell's own `Q` output, not a second name bridged to it).

## What's simplified in this first pass, and why

This is a structural, first-pass port whose job is to get every named block's
*topology* committed and netlisting cleanly against real SG13G2 devices —
not a simulation-verified design (no testbenches exist yet; see issue #7
Non-goals). Several blocks simplify gf180-pll's own, more evolved reference
design in ways that are documented here and in each schematic's own header
comment, not silently:

- **VCO band select** (`vco_bias.sch`) uses two switched parallel
  degeneration resistors on the V-I converter's control branch (2-bit,
  `B0`/`B1`) rather than gf180-pll's 3-stage *geometric mirror cascade*
  (`design/README.md` "Band map" in that repo). This is structurally
  simpler and topologically unambiguous to hand-verify; DR-001 Decision 2's
  own Consequences already state stage count and band-overlap plan are not
  decided by that record, so the exact band-select mechanism is re-derive
  work, not an architecture commitment this issue must get exactly right.
- **Charge pump** (`cp.sch`) has a single fixed-current leg per polarity, no
  2-bit unit-element Icp trim (gf180-pll's `cp.sch` has one) — DR-001's own
  trim mechanism is preserved as a documented future addition, not dropped
  from the architecture.
- **`cp_dumpbuf.sch`** is a single NMOS source-follower tracking buffer, not
  gf180-pll's closed-loop complementary 5T-OTA pair. It still satisfies
  DR-005's (gf180-pll) no-loop-signal-charge compatibility test in spirit
  (it only senses `VOUT`, never drives loop charge back into it) but is an
  offset follower, not a unity-gain buffer.
- **`divider_chain.sch`** hardwires all 6 `div23_cell` instances always
  active (a fixed-length chain) rather than gf180-pll's chain-length
  termination + one-hot output mux, which is the mechanism that covers the
  full N = 4–64 range with *no holes* using a variably-active shorter chain.
  This v1 gives continuous N coverage over the fixed chain's own natural
  range instead. DR-001 Decision 3's own Consequences already state chain
  length and per-cell sizing are open until real divider-ratio design/sim
  work runs (out of this issue's scope).
- **`lock_detector.sch`**'s integrating window (`VWIN`) uses a fixed
  `rhigh` pull-up + `WIDE`-gated NMOS pull-down + `cap_cmim` load, rather
  than a sized, corner-swept RC — same "topology now, numbers later"
  disposition as everywhere else in this pass.

None of these simplifications changes a DR-001/DR-002 architecture decision;
each is a sizing/implementation-detail reduction explicitly flagged here and
in the affected schematic's own header, consistent with `spec/porting-plan.md`'s
own "re-derive, not port" stance for anything numeric.

## Device choices and the LVS deck (informational only — no DRC/LVS in this issue)

Per this repo's CLAUDE.md friction protocol, this section names the
concrete device classes chosen so a future layout/LVS pass (out of this
issue's scope) knows what it will need, and cites the upstream
`klayout-tools` gaps those choices already trigger — **no new gap is filed
here**; both are already tracked, per the audit-before-filing discipline:

- **`loop_filter.sch`** uses `rppd` (LVS-recognized per `klayout-tools`
  PR #1236) for the series resistor, and `cap_cmim` (MIM) for both shunt
  caps. MIM capacitor LVS recognition is **not yet covered** by the starter
  deck — already tracked at `2AMLogic/klayout-tools` **#1233** ("no MIM
  capacitor recognition (cap_cmim/rfcmim)"), filed before this issue and
  naming the exact device class chosen here. This is exactly the trigger
  `spec/decision-records/DR-002-supply-device-flavor.md`'s "Deck-gap check"
  section anticipates ("file once the loop-filter block's own device choice
  is made") — the filing already exists and is concrete, so no duplicate is
  opened.
- **`sg13_hv_nmos`/`sg13_hv_pmos`** (used throughout) are LVS-recognized as
  of `klayout-tools` PR #1236 (closed issue #1231) — DR-002's own
  "Deck-gap check" section confirms this directly.
- No bipolar (HBT) device appears anywhere in this pass (DR-002 Decisions
  1–3 all defer bipolar insertion), so the open bipolar-recognition gap
  (`klayout-tools` #1232) is not triggered by this issue's schematics.

## Netlist export

`netlist.sh` is the one exporter for every block here:

```bash
export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
export PDK=ihp-sg13g2

./design/netlist.sh                        # rewrite design/netlist/*.spice
./design/netlist.sh --check                # fail if any committed export is stale
./design/netlist.sh --top vco              # regenerate one block only
```

Each of the six named blocks is netlisted with its full hierarchy into one
self-contained, `.include`-able file under `design/netlist/` — this is the
"presence AND reproducibility" pass condition issue #7's own Ask cites from
`docs/design-evidence-tiers.md`: committed design sources **plus** a derived
netlist that regenerates from them, not a one-off hand export. `--check`
regenerates into a temp directory and diffs against the committed copy
without writing, so a schematic edited without re-running the exporter is
caught rather than silently drifting.

Every export is self-checked for the expected `.subckt` set, for
auto-generated `netN` names in a `.subckt` port list (the signature of an
unresolved label — almost always a missing `XSCHEM_LIBRARY_PATH` entry), and
for `IS MISSING` pin reports, and fails loudly on any of them before writing
anything — the same discipline gf180-pll's own `netlist.sh` uses, adapted to
this repo's simpler flat namespace (no cross-block leaf-cell collision check
yet, since no block currently redefines another's leaf cell under the same
name).

`design/xschemrc` resolves the SG13G2 PDK the same way `klt pdk find` does
(`PDK_ROOT`/`PDK` env vars, falling back to the usual open_pdks install
prefixes), sources the PDK's own xschemrc so the `sg13g2_pr` device symbols
are on the library path, and adds `design/` itself (for this repo's own
symbols) and every `sim/<experiment-slug>/testbench/` (once any exist, out
of this issue's scope) to the library path.

## Regenerating and editing

The cells were emitted programmatically to keep placement and the label
convention uniform (the same practice gf180-pll's own `design/README.md`
notes for its own schematics), but the committed `.sch`/`.sym` files are
ordinary xschem files: open, edit, and save them in xschem as normal —

```bash
cd design && xschem --rcfile ./xschemrc vco.sch   # interactive
```

— then re-run `./design/netlist.sh --top <block>` to refresh the committed
netlist. A future testbench under `sim/` will `.include` the exported
netlist, so a schematic change is picked up automatically once that
convention lands.

## SG13CMOS5L port

Issue #22 (Part of #16, Chipalooza Challenge #6) ports every schematic here
to IHP SG13CMOS5L, SG13G2's CMOS-only sibling process, per the readiness
audit in
[`spec/decision-records/DR-003-sg13cmos5l-port-readiness.md`](../spec/decision-records/DR-003-sg13cmos5l-port-readiness.md).
**This is a parallel target, not a replacement**: every file directly under
`design/` (this directory) is the SG13G2 original, unmodified and still the
default; the SG13CMOS5L port lives entirely under `design/sg13cmos5l/` as a
second, self-contained flat namespace mirroring this directory's own file
organization (24 `.sch`/`.sym` pairs — six named blocks plus the same
leaf-cell set) — the directory-convention choice named in issue #22's own
scope, since DR-003 does not pin down `sg13g2-bandgap`'s own schematic-port
directory convention beyond its `layout/sg13cmos5l-bandgap_core/` naming
pattern for its *layout* phase.

**Device substitution (DR-003 Findings 1–2)**:

- `sg13_hv_nmos`, `sg13_hv_pmos`, `rppd`, `rhigh` — no device-name or
  subcircuit-signature change (DR-003 Finding 1 confirmed this directly
  against the installed PDK's model library). The only edit every instance
  of these needed was the xschem symbol-library *path* prefix
  (`sg13g2_pr/foo.sym` → `sg13cmos5l_pr/foo.sym`), since SG13CMOS5L ships its
  device symbols under a differently-named library directory even though the
  underlying `.subckt` definitions are identical.
- `cap_cmim` (MIM, does not exist on SG13CMOS5L) → `cap_cmomi`
  (interdigitated MOM) in all four instances. The parameter interface does
  not map 1:1 (`w`/`l`/`m` → `w`/`l`/`mmin`/`mmax`/`feed`/`subblock`/`m`/
  `mm_ok`); `mmin=1`/`mmax=4` (full M1–M4 metal stack)/`feed=double`/
  `subblock=0`/`mm_ok=1` are the PDK's own documented symbol-template
  defaults, used unchanged for every instance. Per-instance `w`/`l` (and, for
  `delaywin_hv`, an `m` multiplier) were chosen so the PDK's own
  `cap_cmomi.tcl` display-capacitance formula lands close to the original
  `cap_cmim` instance's nominal capacitance — **a provisional placeholder
  size, not a re-derived one** (this issue's own scope explicitly excludes
  numeric sizing; a real characterization/tuning pass is owed to the
  sim-campaign follow-up issue, same as every other numeric value in this
  repo per "Sizing is provisional throughout" above):

  | Instance                      | `cap_cmim` (was)      | `cap_cmomi` (now)                                   | ~C (cmim → cmomi)   |
  |--------------------------------|-----------------------|------------------------------------------------------|----------------------|
  | `loop_filter.XC1`              | `w=40u l=40u m=1`     | `w=40u l=40u mmin=1 mmax=4 feed=double m=1`           | 2.41 pF → 1.69 pF    |
  | `loop_filter.XC2`               | `w=8u l=8u m=1`       | `w=10u l=10u mmin=1 mmax=4 feed=double m=1`           | 97 fF → 100 fF       |
  | `vco.XCDECAP`                  | `w=60u l=60u m=1`     | `w=70u l=70u mmin=1 mmax=4 feed=double m=1`           | 5.41 pF → 5.29 pF    |
  | `lock_detector.XCW`             | `w=6u l=6u m=1`       | `w=8u l=8u mmin=1 mmax=4 feed=double m=1`             | 55 fF → 60 fF        |
  | `lock_detector.XDW.XC1` (in `delaywin_hv`) | `w=4u l=4u m=1` | `w=4u l=4u mmin=1 mmax=4 feed=double m=2`      | 25 fF → 27 fF        |

  Per DR-003 Finding 2 and this repo's own CLAUDE.md ("no claim without a
  testbench"), `cap_cmomi`'s vendor model is explicitly **not validated on
  CMOS5L silicon** and carries no corner/mismatch spread — every spec row
  sensitive to these four instances' precision (loop-bandwidth/phase-margin,
  VCO supply-noise/jitter margin) stays `insufficient-evidence` until the
  sim-campaign follow-up issue runs the MoM-model-uncertainty sensitivity
  sweep DR-003 obligates. No bipolar device appears anywhere in this design
  (DR-002 Decisions 1–3), so the SG13CMOS5L HBT gap that drove
  `sg13g2-bandgap#63`'s own rework never applies here (DR-003's own
  Context).

**Rail boundary**: DR-003 Finding 3's recommendation (Challenge #6's "1.2V
digital / 3.3V analog" is the wrapper's I/O-boundary convention only,
internal design stays all-3.3V per DR-002) is ratified by
[`spec/decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md`](../spec/decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md),
using the now-drawn SG13CMOS5L block boundary pins (`vco`'s `B0`/`B1`
band-select, `divider_chain`'s `P0`–`P5` N-select, `lock_detector`'s `LOCK`)
as evidence — see that record for the full reasoning and its own scope
boundary (no chip-level `pll_top`/pad-ring wrapper is drawn by this port).

**Netlist export**: `design/sg13cmos5l/netlist.sh` mirrors `design/
netlist.sh` exactly (same `--top`/`--check` interface, same six blocks, same
expected-`.subckt` connectivity guard), pointed at `design/sg13cmos5l/` and
`ihp-sg13cmos5l` instead of `design/` and `ihp-sg13g2`:

```bash
export PDK_ROOT=/path/to/pdk/root
export PDK=ihp-sg13cmos5l

./design/sg13cmos5l/netlist.sh                 # rewrite design/sg13cmos5l/netlist/*.spice
./design/sg13cmos5l/netlist.sh --check         # fail if any committed export is stale
```

All six blocks net-list cleanly against the installed SG13CMOS5L PDK, with
zero `Symbol not found` errors, zero `IS MISSING` pin reports, zero
auto-generated `netN` names, and zero remaining `cap_cmim` instances in any
export (`grep -rL cap_cmim design/sg13cmos5l/netlist/*.spice` — all six
files). `design/netlist.sh --check` (the original SG13G2 target) was
re-verified to still pass unchanged after this port — SG13G2's own six
committed netlists are byte-identical to before this issue.

A full `ngspice` DC operating-point run on the cap-swap-bearing blocks
(`loop_filter`, `vco`, `lock_detector`) was attempted beyond the netlisting
acceptance bar above, and blocked on undefined process-corner parameters
(e.g. `rz`) that this repo's own `sim/` scaffolding — which does not exist
yet even for SG13G2 (DR-003's own Context) — would normally resolve via a
committed testbench's corner-library `.include`. Building that scaffolding
is the sim-campaign follow-up issue's job, not this schematic-port issue's;
recorded here per this repo's own "no claim without a testbench" discipline
so this is a documented attempt, not a silent gap.

## Tooling/PDK friction encountered in this issue

None rising to the friction protocol's bar beyond what "Device choices and
the LVS deck" above already cites (both gaps pre-existing and already
tracked). `xschem -n -x -q -r` netlisted every one of the 24 schematics
committed here (18 leaf cells + the 6 named top-level blocks) cleanly
against a real, fetched SG13G2 PDK install, with zero `Symbol not found`
errors, zero `IS MISSING` pin reports, and zero auto-generated `netN` names
in any `.subckt` port list.

**SG13CMOS5L port (issue #22)**: same clean result — `xschem` netlisted all
24 SG13CMOS5L schematics against the installed `ihp-sg13cmos5l` PDK with the
same three zero counts above, so no new `klayout-tools`/tool gap is filed by
this issue (this is a schematic/netlist-only pass; no layout or LVS deck was
exercised here to surface one).
