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
                          (thin wrapper over lib/netlist-export.sh, shared
                          with sg13cmos5l/netlist.sh -- issue #45)
  netlist/*.spice          committed exports (checked by `netlist.sh --check`)
  lib/netlist-export.sh   shared xschem-export pipeline sourced by both
                          netlist.sh and sg13cmos5l/netlist.sh

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
  from the architecture. It *does* carry gf180-pll's other in-block bias
  content: since issue #72 / `spec/decision-records/DR-006-*.md`, `cp.sch`
  instantiates a **high-swing cascode bias replica per polarity**
  (`MBP`/`MBPC`/`MCP`, `MBN`/`MBNC`/`MCN` — gf180-pll's `MBP`/`MCP`/`MBN`/`MCN`
  plus a replica cascode device each), so `IBP`/`ICP`/`IBN`/`ICN` are
  **current**-input pins carrying the trim-code reference current, not the
  voltage-input pins the first port pass left them as. The off-block current
  reference itself (a bandgap-referenced `Iref`) is still not part of this
  design.
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
  disposition as everywhere else in this pass. **On the SG13CMOS5L port this
  is no longer true**: `XRPU`/`XCW`/`XDW.XC1` were re-derived from measurement
  by issue #52 and `XMPD` by issue #66 (see the SG13CMOS5L section below).
  The SG13G2 hierarchy here still carries the pre-#52 numbers.

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
  `cap_cmim` instance's nominal capacitance — **originally a provisional
  placeholder size, not a re-derived one** (issue #22's own scope explicitly
  excluded numeric sizing; a real characterization/tuning pass was owed to
  the sim-campaign follow-up issues, same as every other numeric value in
  this repo per "Sizing is provisional throughout" above). **Two of the five
  are no longer provisional**: `lock_detector.XCW` and
  `lock_detector.XDW.XC1` were re-derived from measurement by issue #52 (see
  the "Re-derived, no longer provisional" note below the table); the other
  three are still placeholders.

  | Instance                      | `cap_cmim` (was)      | `cap_cmomi` (now)                                   | ~C (cmim → cmomi)   | Basis |
  |--------------------------------|-----------------------|------------------------------------------------------|----------------------|-------|
  | `loop_filter.XC1`              | `w=40u l=40u m=1`     | `w=40u l=40u mmin=1 mmax=4 feed=double m=1`           | 2.41 pF → 1.69 pF    | provisional placeholder (#22) |
  | `loop_filter.XC2`               | `w=8u l=8u m=1`       | `w=10u l=10u mmin=1 mmax=4 feed=double m=1`           | 97 fF → 100 fF       | provisional placeholder (#22) |
  | `vco.XCDECAP`                  | `w=60u l=60u m=1`     | `w=70u l=70u mmin=1 mmax=4 feed=double m=1`           | 5.41 pF → 5.29 pF    | provisional placeholder (#22) |
  | `lock_detector.XCW`             | `w=6u l=6u m=1`       | `w=40u l=40u mmin=1 mmax=4 feed=double m=1`           | 55 fF → **1.69 pF**  | **re-derived (#52)**, was `w=8u l=8u` → 60 fF |
  | `lock_detector.XDW.XC1` (in `delaywin_hv`) | `w=4u l=4u m=1` | `w=40u l=40u mmin=1 mmax=4 feed=double m=2`  | 25 fF → **3.38 pF**  | **re-derived (#52)**, was `w=4u l=4u m=2` → 27 fF |

  **Re-derived, no longer provisional (issue #52, Part of #16)**: the two
  `lock_detector` instances above, together with `lock_detector.XRPU`
  (`rhigh`, `w=0.5u` `l=6u` → **`l=700u`**, which is not a `cap_cmomi`
  instance and so is not in the table), were re-sized against
  `spec/porting-plan.md` row 16 from the PVT-cornered measurements in
  `sim/sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md`
  and re-verified in
  `sim/sg13cmos5l-lock-detector-window/records/RECORD-002-resized-window-hysteresis-chatter.md`.
  The two sizings answer two independent criteria:

  - `XRPU`·`XCW` sets the integrating node's `R·C`. RECORD-001 measured it at
    0.71–1.71 ns, i.e. 23–1412× *below* the reference period, which is why
    the block chattered at all 92 corner points it swept. `l=700u` +
    `w=40u l=40u` puts `R·C` at **2.29–5.58 µs**, i.e. **8.0–19.5×** the
    *slowest* reference period in row 2's DR-005-amended 3.5–24.4 MHz range
    (`T_ref` ≤ 286 ns) at every resistor-corner × temperature point.
  - `XDW.XC1` sets the comparator window `twin_r` (`delaywin_hv`'s own
    low→high propagation delay), which RECORD-001 measured at 0.219–0.409 ns
    against row 16's ported ≥2.5 ns floor. `w=40u l=40u m=2` puts `twin_r` at
    **3.68–13.66 ns**, clearing the floor at every corner including the
    −20% MOM-uncertainty band.

  These are the *first* two `cap_cmomi` instances in this design whose size
  comes from a measured spec criterion rather than from matching the
  displaced `cap_cmim` instance's nominal value. The area cost is real and
  is stated rather than hidden: `XCW` grows from 64 µm² to 1 600 µm² of
  drawn MOM array and `XDW.XC1` from 2 × 16 µm² to 2 × 1 600 µm², and
  `XRPU`'s `rhigh` strip grows from 6 µm to 700 µm of drawn length (it will
  need snaking in layout). The `lock_detector` layout that landed in PR #39
  predates all three and does not reflect them.

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

  **Update (issue #23, Part of #16)**: the sim-campaign follow-up issue has
  now run that sweep for the three instances DR-003 Finding 2 names by name
  (`loop_filter.XC1`/`XC2`, `vco.XCDECAP`) — see
  `sim/sg13cmos5l-loop-filter-momcap/records/RECORD-001-rc-corner-momcap-sensitivity.md`
  and
  `sim/sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md`.
  Each instance's own capacitance-value sensitivity to a +/-20% MOM-model-
  uncertainty band is now bounded by a real PVT-cornered testbench; the
  downstream spec rows' *final numeric values* (an actual loop-bandwidth-in-
  kHz / phase-margin-in-degrees figure, an actual jitter/ripple-attenuation
  figure) still need the not-yet-re-derived Kvco and Icp-trim tables plus
  post-layout parasitics, and stay `insufficient-evidence` until those land
  — see each record's own "Spec-row disposition" section.
  **Update (issue #27, Part of #16)**: the Kvco table
  (`sim/sg13cmos5l-vco-kvco-table/`) and the Icp-trim table
  (`sim/sg13cmos5l-cp-icp-trim/`) have both now landed, and
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-001-loop-bandwidth-phase-margin.md`
  combines them with the loop-filter R/C data above to produce the actual
  loop-bandwidth/phase-margin numbers — **clearing** the
  `insufficient-evidence` marking on that row. The result is that the
  as-drawn filter meets neither stability criterion at any trim code
  (phase margin 1.55–20.33° against a ≥45° requirement, 0 of 90 corner
  combinations passing), and that record's own proposal section quantifies
  the `R1` resizing that would close it. The MOM band turns out to
  contribute ≈0.9° of that ~40° shortfall, so MOM-model uncertainty is not
  the binding term here. The jitter / ripple-attenuation figures are
  unaffected by that work and remain `insufficient-evidence` pending
  post-layout parasitics.
  `lock_detector.XCW`/`XDW.XC1` are not named by DR-003 Finding 2's own
  three-instance list and were not covered by this update.
  **Update (issue #38, Part of #16)**: their hysteresis-window sensitivity
  is now closed —
  `sim/sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md`
  runs the same ±20% MOM-model-uncertainty sweep on both instances at every
  PVT/resistor-corner point. The band moves the measured comparator window
  by 7–8% (not the dominant term). That record also finds, independent of
  the MOM band, that the block's assert window (0.219–0.409 ns) misses the
  ported ≥2.5 ns floor by 6–11×, that no hysteresis resolves against the
  ≥25%-of-window target at any of 92 corner points, and that the block
  chatters at all 92 — traced to the integrating node's own `XRPU`·`XCW`
  time constant (0.71–1.71 ns) sitting 1–3 orders of magnitude below the
  ported 1–25 MHz reference period at every corner, not to `cap_cmomi`'s
  MOM-model uncertainty specifically. The re-sizing this implies for
  `XRPU`/`XCW` (and possibly `XDW.XC1`, which also sets the comparator
  window) is filed as issue #52 (Part of #16), same discipline as the
  loop-filter `R1` resize proposal above.
  **Update (issue #52, Part of #16)**: that re-sizing has now landed and been
  re-verified —
  `sim/sg13cmos5l-lock-detector-window/records/RECORD-002-resized-window-hysteresis-chatter.md`.
  `XRPU` `l=6u`→`l=700u`, `XCW` `w=8u l=8u`→`w=40u l=40u`, `XDW.XC1`
  `w=4u l=4u`→`w=40u l=40u` (all three tabulated above). Two of row 16's
  three measurable criteria that RECORD-001 found failing are now **met at
  every corner re-measured**: the comparator window is 3.68–13.66 ns against
  the ≥2.5 ns floor (was 0.219–0.409 ns), and the block is **steady at the
  deep out-of-lock phase error at every ladder corner** (RECORD-001:
  chatter at 92/92). The **hysteresis criterion still fails**, and
  RECORD-002 root-causes it to two mechanisms that are both *outside* the
  three instances issue #52 resized — `schmitt_hv`'s two feedback devices
  are tied to the wrong rails (measured 1.1 mV of input-referred hysteresis
  as drawn vs. 932 mV for the classic connection), and the settled-`VWIN`
  vs. phase-error characteristic is far too steep for any Schmitt hysteresis
  to map onto a ≥25%-of-window phase-error width, which is set by the
  `XRPU`/`XMPD` strength ratio rather than by `R·C`. Both are filed as issue #66,
  not silently fixed here.
  **Update (issue #66, Part of #16)**: both terms are now fixed and
  re-measured —
  `sim/sg13cmos5l-lock-detector-window/records/RECORD-003-hysteresis-fix.md`.
  **All three of row 16's measurable criteria now pass**, and neither fix
  spends anything issue #52 bought (`XRPU`, `XCW` and `XDW.XC1` are untouched
  by #66; `R·C` and the assert window were re-measured rather than assumed):

  - **`schmitt_hv`'s two feedback devices are on the classic connection.** A
    six-transistor CMOS Schmitt gets its hysteresis from feedback devices
    pulling the internal stack nodes toward the *opposite* rail from their own
    stack; both were tied to the same rail, leaving the cell with no state
    memory at all. `XMP3` `np OUT VDD VDD` → `VSS OUT np VDD` and `XMN3`
    `nn OUT VSS VSS` → `VDD OUT nn VSS`. Measured input-referred hysteresis
    **0.88–1.58 mV → 804 mV–1.058 V** (26.3–30.3% of `VDD`) over 3 MOS corners
    × 3 temperatures × 3 supplies. **The identical defect was in the SG13G2
    sibling `design/schmitt_hv.sch` and is fixed in the same change**, and
    measured there too rather than argued across — see "SG13G2 sibling" below.
  - **`XMPD` re-sized `w=2u l=0.5u` → `w=0.25u l=16u`** (`L/W` 0.25 → 64).
    The settled integrating-node voltage is the balance between `XRPU`'s
    charge over one *reference period* and `XMPD`'s discharge over one `WIDE`
    pulse, `VWIN ≈ VDD − I_sat(XMPD)·R(XRPU)·(τ − t_win)/T_ref`, so the
    `XRPU`/`XMPD` strength ratio — not `R·C` — sets how wide *in phase error*
    the `VWIN` transition is, and therefore how much phase-error hysteresis a
    given Schmitt voltage hysteresis buys. `XMPD` is the only device in that
    expression that is not already spoken for by #52's `R·C` requirement,
    which is why it is the knob.

  `XMPD`'s value is a **two-sided measured bound**, not a pick
  (`sim/sg13cmos5l-lock-detector-window/corners/xmpd_sizing.csv`). `T_ref` is
  in the numerator above, so the hysteresis in units of the window is
  *proportional to* `T_ref` and the **fast** end of row 2's range is the
  binding one for row 16's hysteresis criterion — the opposite end from the
  one that bound #52's `R·C` criterion. Weakening `XMPD` raises hysteresis but
  simultaneously pushes the assert/de-assert thresholds out; `w=0.25u l=16u`
  is the sizing that clears both bounds at once:

  | Bound, both measured | Corner | `w=0.5u l=16u` | **`w=0.25u l=16u`** | `w=0.25u l=32u` |
  |---|---|---|---|---|
  | Hysteresis ≥ 0.25× window (row 16) | `mos_ff`/`res_wcs`/−40 °C, 24.4 MHz | 0.239× — **fails** | **0.495× — 1.98×** | passes |
  | De-assert threshold inside one reference period | `mos_tt`/`res_bcs`/125 °C, 3.5 MHz | 11.4× window = 32% of `T_ref` | **18.2× window = 51% of `T_ref`** | **> 24× window = > 67% — off the end of the sweep** |

  Measured against the changed block, all three of row 16's criteria pass:
  assert window **3.688–11.24 ns** at 102/102 points (worst-case margin
  1.475×, unchanged — `XMPD` is not inside `delaywin_hv`); hysteresis
  **50–800% of the window, 0 of 21 corners below the ≥25% criterion**, worst
  case 50% at the 24.4 MHz corners; **`steady` at 21/21** at a **20×**-window
  static phase error (RECORD-002 probed 10×). `R·C` re-extracts **byte-identical**
  to RECORD-002 at 8.0–19.5× `T_ref`, so #52's margin is confirmed spent by
  nothing.

  **One real cost, measured and attributed rather than hidden.** The
  out-of-lock supply current in row 11's `lock_detector` domain re-bounds from
  2.48–95.1 µA to **2.47–234 µA**. The top of that range is *not* a switching
  cost: it is `schmitt_hv` crowbar current while `VWIN` rests **between** the
  now-widely-separated trip points, which the fixed 10×-window probe lands
  inside at slow-end corners. Controlled directly — the same deck at a 20×
  probe (beyond de-assert everywhere) gives 57.9 µA for this block against
  46.7 µA for RECORD-002's, i.e. the genuinely out-of-lock current rose ~24%,
  not 2.5×. The readout has no output stage and its input is now *designed* to
  dwell between the rails; that residual is filed as a follow-up.

  **Usable phase-error threshold bound — `f_ref`-dependent by construction,
  accepted (issue #77, Part of #16):** `VWIN` settles to the balance between
  `XRPU`'s continuous charge over one *reference period* and `XMPD`'s
  discharge over one `WIDE` pulse, so `T_ref` sits in the denominator of the
  settling slope and the assert/de-assert phase-error thresholds scale with
  `1/f_ref`. At the DR-005-amended 3.5–24.4 MHz `f_ref` range, RECORD-003
  measures the assert threshold at **11.7–24.4% of `T_ref`** and the
  de-assert threshold at **18.7–36.6% of `T_ref`** (both at
  `mos_tt`/`res_typ`/27 °C; see RECORD-003 "What the re-size costs" for the
  full corner table). **[DR-006](../spec/decision-records/DR-006-lock-detector-fref-dependent-threshold.md)
  ratifies accepting this as intended topology behaviour rather than
  redesigning it**: `2AMLogic/gf180-pll`'s own `lock_detector` uses the
  identical continuous-pull-up / event-gated-pull-down integrator and has
  already disclosed the same `T_ref`-proportional limitation across three of
  its own records without a topology change. A consumer gating logic on
  `LOCK` should treat the phase-error threshold as a `T_ref`-relative
  quantity in this range, not a fixed number; DR-006 leaves open what happens
  below the ported 3.5 MHz floor, where gf180-pll's own (unmeasured) hand
  argument predicts chatter — this repo has not measured that regime either.

**Rail boundary**: DR-003 Finding 3's recommendation (Challenge #6's "1.2V
digital / 3.3V analog" is the wrapper's I/O-boundary convention only,
internal design stays all-3.3V per DR-002) is ratified by
[`spec/decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md`](../spec/decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md),
using the now-drawn SG13CMOS5L block boundary pins (`vco`'s `B0`/`B1`
band-select, `divider_chain`'s `P0`–`P5` N-select, `lock_detector`'s `LOCK`)
as evidence — see that record for the full reasoning and its own scope
boundary (no chip-level `pll_top`/pad-ring wrapper is drawn by this port).

**Netlist export**: `design/sg13cmos5l/netlist.sh` and `design/netlist.sh`
are both thin wrappers over the same shared pipeline,
`design/lib/netlist-export.sh` (issue #45) -- same `--top`/`--check`
interface, same six blocks, same expected-`.subckt` connectivity guard --
each wrapper just parameterizes the shared script with its own design
directory (`design/sg13cmos5l/` vs `design/`) and PDK label
(`ihp-sg13cmos5l` vs `ihp-sg13g2`):

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
