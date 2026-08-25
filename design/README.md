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

## Tooling/PDK friction encountered in this issue

None rising to the friction protocol's bar beyond what "Device choices and
the LVS deck" above already cites (both gaps pre-existing and already
tracked). `xschem -n -x -q -r` netlisted every one of the 24 schematics
committed here (18 leaf cells + the 6 named top-level blocks) cleanly
against a real, fetched SG13G2 PDK install, with zero `Symbol not found`
errors, zero `IS MISSING` pin reports, and zero auto-generated `netN` names
in any `.subckt` port list.
