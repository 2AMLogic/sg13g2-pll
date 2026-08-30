# Chipalooza Challenge #6 — sign-off proposal: SG13CMOS5L integer-N PLL

**Status: schematic port + device-level layout landed; PVT sim campaign
partial. Not a finished sign-off.** This document covers the SG13CMOS5L
port of the fleet's integer-N charge-pump PLL (issue #16, Epic
[2AMLogic/2am#542](https://github.com/2AMLogic/2am/issues/542) Phase 5A):
schematic capture for all six blocks (#22, PR #26), a device-level layout
pass for all six blocks (#24, PR #32), and an intentionally partial PVT
sim campaign (#23, PRs #28/#33) that bounds the design's MOM-cap
uncertainty exposure and the VCO's open-loop tuning curve but does **not**
yet close the loop — the remaining closed-loop re-derivation (Kvco-driven
loop bandwidth/phase margin, Icp-trim table, lock time, duty cycle,
lock-detector window, reference spur, power) is tracked separately as
issue #27 (open as of this writing). Challenge #6's full sign-off bar
(schematic + pre-layout sim → layout + post-layout sim over PVT →
DRC/LVS-clean GDS, open-source-EDA-verifiable) is **not met**. Every spec
row below is re-derived directly from the `sim/`/`layout/` evidence that
exists today; any row that evidence cannot bound is marked
`insufficient-evidence` rather than relaxed to pass, per this repo's own
`CLAUDE.md`.

Block-only document: no personal or institutional detail below, per the
epic's ([2AMLogic/2am#542](https://github.com/2AMLogic/2am/issues/542))
Tier 1 disclosure scope.

## 1. Block type and positioning

An **integer-N, charge-pump PLL**: tri-state PFD → charge pump → passive
2nd-order loop filter → current-starved CMOS ring VCO → cascaded ÷2/3
feedback divider → passive window-comparator lock detector, no active
filter and no auto-calibration FSM in v1 (`spec/decision-records/
DR-001-pll-architecture.md`, carried unmodified onto SG13CMOS5L). This is
the fleet's second SG13CMOS5L Chipalooza entry — after the Challenge #2
bandgap (`2AMLogic/sg13g2-bandgap`'s `docs/chipalooza/
challenge-2-proposal.md`) — and its first **closed-loop, mixed-signal**
one: a bandgap is a single composite cell with a stable DC operating
point, while this design is six blocks with real charge-domain and
tuning-loop dynamics, which is exactly why its own SG13CMOS5L readiness
audit (`spec/decision-records/DR-003-sg13cmos5l-port-readiness.md`) scoped
the port across four separate follow-up issues rather than one pass.

**No bipolar device appears anywhere in this design.** SG13CMOS5L has no
SiGe HBT equivalent to SG13G2's `npn13G2` (`docs/pdk/sg13cmos5l.md`,
2AMLogic/2am), but DR-002 (`spec/decision-records/
DR-002-supply-device-flavor.md` Decisions 1–3) already deferred every
per-element bipolar option (bias reference, charge-pump cascode, divider
first stage) on SG13G2 itself, so the HBT gap that forced
`sg13g2-bandgap#63`'s own Phase 1 rework never applies to this port
(DR-003's own Context).

## 2. I/O mapped to the Challenge #6 slot budget

**No chip-level `pll_top`/pad-ring wrapper is drawn yet** (DR-004,
`spec/decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md`,
"no chip-level `pll_top`/pad-ring wrapper is drawn by this port") — issue
#22's own scope was the six named blocks plus their leaf cells, not a
composed top. The table below is therefore a **proposed** mapping read
directly off the six blocks' own already-drawn boundary pins (DR-004's own
enumeration), not a claim that a wrapper exists, has been simulated, or
has been laid out.

Every block-boundary pin, as drawn (`design/sg13cmos5l/*.sch`, DR-004):

| Block | Pins | Boundary role once composed |
|---|---|---|
| `pfd` | `REF`, `FB`, `UP`, `DN`, `VDD`, `VSS` | `REF` external; `FB`/`UP`/`DN` internal (to `divider_chain`/`cp`) |
| `cp` | `UP`, `DN`, `IBP`, `ICP`, `IBN`, `ICN`, `VOUT`, `VDD`, `VSS` | `UP`/`DN` internal (from `pfd`); `IBP`/`ICP`/`IBN`/`ICN` bias-current inputs, external; `VOUT` internal (to `loop_filter`) |
| `loop_filter` | `VCTRL`, `VSS` | `VCTRL` internal (shared net: `cp.VOUT` ↔ `loop_filter.VCTRL` ↔ `vco.VCTRL`) |
| `vco` | `VCTRL`, `B0`, `B1`, `CLK`, `VDD_VCO`, `GND_VCO` | `B0`/`B1` external control; `CLK` internal (to `divider_chain`); dedicated supply domain |
| `divider_chain` | `CKIN`, `CKIN_VCO`, `P0`–`P5`, `FB`, `DIVOUT`, `VDD_DIV`, `VSS` | `P0`–`P5` external control; `DIVOUT` external test output; `CKIN`/`CKIN_VCO`/`FB` internal |
| `lock_detector` | `UP`, `DN`, `LOCK`, `VDD`, `VSS` | `UP`/`DN` internal (shared with `pfd`); `LOCK` external test output |

Proposed external mapping, against the brief's slot budget (≤24 digital
control inputs, ≤12 digital test outputs, ≤4 shared analog lines, 0–4
dedicated pads):

| Budget category | Used | Notes |
|---|---|---|
| Digital control inputs | **9 / 24** | `REF` (reference clock, 1), `vco.B0`/`B1` (coarse band select, 2), `divider_chain.P0`–`P5` (N-select, 6 — a 6-bit code covers 64 states, structurally consistent with `spec/porting-plan.md` row 3's `N ⊇ 4–64` requirement, but the code has not been electrically verified — see section 4 row 3). `cp.IBP`/`ICP`/`IBN`/`ICN` are **not** counted here — see the bias-current note below. |
| Digital test outputs | **2 / 12** | `lock_detector.LOCK` and `divider_chain.DIVOUT` (the divided, post-`N` output clock — lower-bandwidth and easier to route digitally than the raw VCO edge). |
| Shared analog lines (fallback) | **1 / 4** | `vco.VCTRL` (the loop's control-voltage node), offered as a debug/calibration tap only — not required for functional operation, and see the caveat below before treating it as realized. |
| Dedicated pads (preferred) | **1 / 4** | `vco.CLK` (the raw, pre-divider VCO edge), preferred as a dedicated pad rather than the shared analog bus for a phase-noise/duty-cycle bring-up bench, where added mux-bus loading capacitance would itself perturb the measurement. |

**Caveats, stated rather than assumed away:**

- **`VCTRL`/`CLK` are internal nets today, not pins with a buffer already
  designed to drive an off-chip load.** Exposing either without perturbing
  the loop (`VCTRL` is a high-impedance node; `CLK` is the ring's own
  output before the divider's own retiming/buffering) needs a dedicated
  buffer stage that does not exist in any committed schematic — this is a
  proposed use for a future wrapper issue to design, not a claim that the
  tap already exists.
- **`cp.IBP`/`ICP`/`IBN`/`ICN` (all four declared as inputs in `cp.sch`)
  are assumed to map onto the harness's own shared bias infrastructure**
  (the common harness supplies "≤2 bandgap-referenced current sources" per
  the program runbook), consistent with `spec/porting-plan.md`'s carried-
  over "bias-current generation is not this block's own problem" scoping
  (DR-001-equivalent). This is an **assumption**, not verified against a
  harness spec this repo does not have access to — flagged as an open
  wrapper-integration question, the same way the Challenge #2 bandgap
  proposal flagged its own `vdd`/`vss` supply-sourcing assumption.
- **`VDD`/`VSS`/`VDD_VCO`/`GND_VCO`/`VDD_DIV` supply pins are assumed
  supplied from the harness's shared global rails**, not counted against
  either digital or analog slot budgets, matching the Challenge #2
  proposal's own convention. `vco`'s dedicated `VDD_VCO`/`GND_VCO` domain
  is worth flagging to a wrapper designer specifically: `spec/
  porting-plan.md` row 12 and DR-001/DR-002 already name supply-noise
  sensitivity as this design's dominant structural risk for *any*
  current-starved ring on an unregulated rail, so a low-impedance,
  low-noise routing for this specific domain is a real (if unquantified)
  requirement, not a generic power pin.

Total proposed slot-budget usage: **9 digital control inputs, 2 digital
test outputs, 1 shared analog line (fallback), 1 dedicated pad** — well
inside every ceiling the brief sets, with 15/24, 10/12, 3/4, and 3/4
headroom respectively.

## 3. Functional description

`design/sg13cmos5l/{pfd,cp,loop_filter,vco,divider_chain,lock_detector}.sch`
(PR #26, `Closes #22`) is a topology-for-topology port of this repo's own
SG13G2 schematics (`design/*.sch`), which are themselves ported from the
fleet's ratified gf180-pll/sky130-pll references per `spec/
decision-records/DR-001-pll-architecture.md`:

- **`pfd`** — a tri-state edge-detect + SR-latch phase/frequency detector,
  reset delay sized in the charge domain (reset delay > charge-pump
  turn-on time), not just the logic domain.
- **`cp`** — a wide-swing cascode charge pump with unit-element (not
  binary-weighted) current trim and a shared, buffered ("tracking") dump
  node to null idle-leg tail-charge exchange.
- **`loop_filter`** — a passive series-R + shunt-C1 + shunt-C2 network. Its
  two SG13G2 `cap_cmim` (MIM) instances (`XC1`, `XC2`) do not port
  as-is — SG13CMOS5L has **no MIM capacitor at all**
  (`docs/pdk/sg13cmos5l.md`, 2AMLogic/2am) — and are replaced by
  `cap_cmomi` (interdigitated MOM) instances, `w=40u l=40u` and
  `w=10u l=10u` respectively, sized so the PDK's own display-capacitance
  formula lands close to the original nominal value (a provisional
  placeholder, not a re-derived size — `design/README.md` "SG13CMOS5L
  port").
- **`vco`** — `vco_bias` (constant-gm beta-multiplier core) + 5×
  `vco_stage` (current-starved inverter ring, source-degenerated V→I
  converter, geometric coarse mirror cascade for the `B0`/`B1` band
  select) + 2× `inv2x_hv` output buffer, with a dedicated `VDD_VCO`/
  `GND_VCO` supply domain and an on-chip decap (`XCDECAP`, also a
  `cap_cmomi` MOM-cap substitution for the original `cap_cmim`,
  `w=70u l=70u`).
- **`divider_chain`** — a cascaded ÷2/3 (Vaucher) chain, static CMOS, with
  a VCO-clocked final retiming flop independent of `N`, and a 6-bit
  `P0`–`P5` divide-ratio select.
- **`lock_detector`** — a passive phase-error window comparator (XOR of
  `UP`/`DN`, delayed-AND width check) with asymmetric assert-slow/
  deassert-fast dynamics via a Schmitt trigger, no FSM. Two more
  `cap_cmim` → `cap_cmomi` substitutions land here (`XCW`, `w=8u l=8u`;
  `XDW.XC1` inside `delaywin_hv`, `w=4u l=4u m=2`).

**Device substitution, in full** (`design/README.md`, "SG13CMOS5L port",
DR-003 Findings 1–2): `sg13_hv_nmos`/`sg13_hv_pmos` (MOSFETs) and
`rppd`/`rhigh` (poly resistors) need **no device-name or subcircuit-
signature change** — 477 of this design's 482 devices — because
SG13CMOS5L ships the identical SG13G2 CMOS device models under a
differently-named symbol-library path only. All five `cap_cmim` → MOM-cap
substitutions (`loop_filter` ×2, `vco` ×1, `lock_detector` ×2) are the
single largest schematic-port risk, because the PDK's own `cap_cmomi`/
`cap_cmomf` models are **not validated on CMOS5L silicon** and carry no
characterized process-corner or mismatch spread — every spec row sensitive
to these five instances' precision is flagged `insufficient-evidence`
below unless a real sensitivity sweep bounds it (section 4).

**Rail interpretation**: DR-004 ratifies DR-003 Finding 3 — Challenge #6's
"1.2V digital / 3.3V analog" brief is read as the *wrapper's* I/O-boundary
convention, not an internal-domain mandate. Every device in all six blocks
stays 3.3V thick-oxide CMOS (`sg13_hv_nmos`/`sg13_hv_pmos`, DR-002
Decision 0, unchanged), avoiding a new level-shifter in the PFD→charge-pump
charge-domain path that DR-002 already rejected reopening (citing
gf180-pll's own "logic-correct-looking PFD that measurably failed 9/45
corners in the charge domain"). Any 1.2V-side level-shifting is scoped to
a not-yet-designed wrapper boundary, confined to the control/test pins in
section 2's table.

## 4. Spec table

Every row is `spec/porting-plan.md` §1.2's own row, re-derived against
real SG13CMOS5L `sim/` evidence where it exists, and marked
`insufficient-evidence` (not silently omitted, not relaxed to pass) where
it does not. Both brief rails are addressed explicitly: this design's
internal devices are **all 3.3V** (DR-002/DR-004, unchanged by the port);
no 1.2V corner applies to any of the six blocks themselves, because a
1.2V rail would only ever reach a not-yet-drawn wrapper boundary (each
cited record's own "Corner matrix"/"Supply" row states this explicitly,
not silently).

| # | Parameter | Status | Evidence |
|---|---|---|---|
| 0 | Supply / device flavor | **Met (ratified)** — all-3.3V thick-oxide CMOS internal design, 1.2V read as a wrapper-boundary convention only | DR-002 Decision 0, DR-003 Finding 1/3, DR-004 |
| 1 | Output band | **Insufficient-evidence** for a ratified target. Partial, real data exists: an open-loop `vco` transient sweep measures oscillation from 445.3 MHz (`slow` bundle, any band, `VCTRL=0.3V`) to 1562.0 MHz (`fast` bundle, band `11`, `VCTRL=2.7V`) across the swept matrix — but this is open-loop only (no PFD/CP/filter/divider closure), not post-layout, and the divider's own retiming-margin closure against this frequency (row 3) is not yet done | `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md` |
| 2 | Reference input | **Insufficient-evidence** — no PFD-level electrical-level (V_IL/V_IH) or duty-cycle testbench has been run against the SG13CMOS5L `pfd` yet | none |
| 3 | Multiplication ratio (N) | **Insufficient-evidence** for the retiming-margin closure itself. The Kvco record supplies the real top-of-band input the closure needs (**1562.0 MHz**, `fast`/band `11`/`VCTRL=2.7V`), and the `P0`–`P5` 6-bit select structurally covers `N` codes ⊇ 4–64, but the divider chain's own timing margin against that frequency is not yet re-derived (deferred to #27) | `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md` (top-of-band data point only) |
| 4/5 | Kvco bound / band-selection rule | **Met (bounded)** — a real, PVT-cornered (3 process×temperature bundles × 4 band codes × 5 `VCTRL` points, 60 runs), per-band, open-loop Kvco table exists. `Kvco` is measurably non-constant across the sweep (e.g. `typ`/band `00`: 173.8 MHz/V averaged vs. 206.0 MHz/V at the top of the range, ~19% difference) — a real nonlinearity, not noise, consistent with the row's own "table, not a scalar" framing. Band select is also found to be inert at low `VCTRL` (all four band codes read the identical frequency at `VCTRL=0.3V`) and dominant at high `VCTRL` (~2.8× spread at `VCTRL=2.7V`) — a real circuit finding for a future band-selection rule to account for | `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md`, full 12-row table below |
| 6/6a | Loop bandwidth / phase margin | **Insufficient-evidence** for the row's own kHz/degree number. The `loop_filter`'s own zero/pole location *is* bounded: nominal `fz = 12.07 MHz`, `fp = 216.0 MHz` (`res_typ`, 27°C, MOM band 0%); process+temperature alone moves `fz` ±13% (10.76–13.54 MHz); the MOM-cap uncertainty band alone moves it further, 1.5× (10.06–15.09 MHz); the full 27-corner matrix spans 8.97–16.92 MHz. Closing the row's own bandwidth/phase-margin number still needs the not-yet-re-derived Icp-trim table (deferred to #27) combined with the Kvco table above | `sim/sg13cmos5l-loop-filter-momcap/records/RECORD-001-rc-corner-momcap-sensitivity.md` |
| 7 | Lock time | **Insufficient-evidence** — no closed-loop (PFD+CP+filter+VCO+divider) testbench exists yet; deferred to #27 | none |
| 8 | Period jitter | **Insufficient-evidence** for the absolute number. `vco.XCDECAP`'s own capacitance is bounded (nominal **5.2862 pF**, matching `design/README.md`'s "~5.29 pF" placeholder to 4 figures) and its fractional supply-decoupling pole-frequency sensitivity to the ±20% MOM band is bounded (illustrative `R_src=3kΩ`: 12.54 MHz / 10.03 MHz / 8.35 MHz at −20%/0%/+20%, a 1.502× span matching the exact analytic `1/0.8 : 1/1.2` prediction). The absolute jitter-as-percent-of-period number cannot be computed: no post-layout parasitic source impedance exists (layout is placement-only, no routing — section 5), and ngspice has no direct phase-noise computation for a free-running oscillator (a pre-existing flow limitation, not an SG13CMOS5L-specific one — see row 9) | `sim/sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md` |
| 9 | Integrated RMS jitter / phase noise | **N/A, carried as-is** — deliberately not spec'd. This is a flow limitation (ngspice has no `.noise` path for a free-running oscillator), sourced from gf180-pll's own `DR-002` Decision 5, not this repo's own DR-002 (which has no Decision 5) — applies identically on SG13CMOS5L since it is tool-, not PDK-, dependent | `spec/porting-plan.md` row 9 (citing gf180-pll `DR-002` Decision 5) |
| 10 | Reference spur | **Insufficient-evidence** — needs SG13CMOS5L's own charge-pump mismatch data via a closed-loop steady-state spectral measurement; not yet run, deferred to #27 | none |
| 11 | Power | **Insufficient-evidence** — needs a closed-loop DC/average current measurement across all domains; not yet run, deferred to #27 (and per `spec/porting-plan.md` row 11, must not be a V² rescale of gf180-pll's number even once it is) | none |
| 12 | Supply sensitivity | **Insufficient-evidence** for the absolute mV-ripple/dB-attenuation budget, for the same two reasons as row 8 (no post-layout source impedance; no direct small-signal method for the ring's own unstable DC operating point). The fractional MOM-band-to-pole-frequency sensitivity is bounded (row 8's own 1.502× span) | `sim/sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md` |
| 13 | Output duty cycle | **Insufficient-evidence** — the Kvco record's own methodology explicitly measures period via a single rising-edge-to-rising-edge crossing, not the rising/falling symmetry a duty-cycle measurement needs, and it explicitly leaves the `mos_sf`/`mos_fs` (NMOS/PMOS-split) corners — the corners most relevant to duty-cycle skew — as an open, not-yet-swept axis. Deferred to #27 | `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md` ("What this does not bound") |
| 14 | Output levels / drive | **Insufficient-evidence** — no waveform-into-a-defined-load (V_OH/V_OL vs. ≤50 fF) measurement has been run against any SG13CMOS5L block yet | none |
| 15 | Area | **Insufficient-evidence** — no top-level layout, floorplan, or composed `pll_top` exists to measure an area figure from; the device-level layout that does exist (section 5) is 477/482 devices across six separately-composed, unrouted blocks, not a single measurable die area | `layout/sg13cmos5l-pll/README.md` |
| 16 | Lock-detector targets | **Insufficient-evidence** — needs the `lock_detector` block's own closed-loop timing behavior (assert window, hysteresis, no chatter); not yet run, deferred to #27. Note: `lock_detector.XCW`/`XDW.XC1`'s own two `cap_cmomi` instances are **not** among the three DR-003 Finding 2 named for the sensitivity sweep already run (rows 6/6a, 8, 12 above), so this row's own MOM-cap exposure is additionally open, not covered by the existing sweep | `design/README.md` "SG13CMOS5L port" (update note) |
| 17 | Standby / power-down | **N/A, carried as-is** — no power-down mode in v1, a deliberate scope decision on both sibling repos, not a testbench claim | `spec/porting-plan.md` row 17 |
| 18 | Supply range | **Insufficient-evidence** for a numeric ±10%-style supply-corner result. DR-002/DR-004 ratify the qualitative all-3.3V internal design, but every SG13CMOS5L `sim/` record to date explicitly does not sweep a supply-voltage axis for its own DUT (`loop_filter` and `vco.XCDECAP` have no active-device supply dependence; the Kvco record fixes `VDD_VCO=3.3V` throughout, stating "no 1.2V corner applies to an internal block like the VCO itself") | `sim/sg13cmos5l-vco-kvco-table/corners/matrix.md`; `sim/sg13cmos5l-loop-filter-momcap/records/RECORD-001-rc-corner-momcap-sensitivity.md`; `sim/sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md` |

**Full Kvco-vs-band-code table** (row 4/5's own evidence, all 60 measured
points condensed to the per-bundle/per-band summary;
`sim/sg13cmos5l-vco-kvco-table/corners/results.csv` has every raw point):

| PVT bundle | Band | f(0.3V) MHz | f(0.9V) MHz | f(1.5V) MHz | f(2.1V) MHz | f(2.7V) MHz | Kvco avg (0.3–2.7V) MHz/V | Kvco peak local (2.1–2.7V) MHz/V |
|---|---|---|---|---|---|---|---|---|
| typ | 00 | 494.0 | 533.1 | 655.0 | 787.4 | 911.0 | 173.8 | 206.0 |
| typ | 10 | 494.0 | 548.6 | 747.8 | 959.3 | 1130.0 | 265.0 | 284.5 |
| typ | 01 | 494.0 | 558.0 | 810.9 | 1074.9 | 1262.0 | 320.0 | 311.8 |
| typ | 11 | 494.0 | 564.1 | 862.0 | 1161.9 | 1359.1 | 360.5 | 328.6 |
| slow | 00 | 445.3 | 483.4 | 584.4 | 693.9 | 791.3 | 144.2 | 162.2 |
| slow | 10 | 445.3 | 497.5 | 657.6 | 824.3 | 953.1 | 211.6 | 214.7 |
| slow | 01 | 445.3 | 505.7 | 705.0 | 907.5 | 1047.0 | 250.7 | 232.5 |
| slow | 11 | 445.3 | 511.6 | 741.2 | 970.1 | 1113.8 | 278.6 | 239.4 |
| fast | 00 | 548.2 | 592.3 | 730.3 | 882.2 | 1025.3 | 198.8 | 238.5 |
| fast | 10 | 548.2 | 610.6 | 840.3 | 1084.6 | 1284.4 | 306.8 | 333.1 |
| fast | 01 | 548.2 | 621.7 | 919.4 | 1224.2 | 1445.3 | 373.8 | 368.5 |
| fast | 11 | 548.2 | 629.8 | 984.0 | 1334.1 | 1562.0 | 422.4 | 379.9 |

(`typ` = `mos_tt`/`res_typ`/27°C, `slow` = `mos_ss`/`res_wcs`/125°C,
`fast` = `mos_ff`/`res_bcs`/−40°C, per `sim/sg13cmos5l-vco-kvco-table/
corners/matrix.md`.)

## 5. Sign-off status against the brief

| Brief stage | Status |
|---|---|
| Schematic + pre-layout sim | **Partial.** Schematic captured for all six blocks (#22, PR #26, DR-003/DR-004 ratified). Pre-layout PVT sim exists only for a targeted subset: the MOM-cap-uncertainty sensitivity of three of the design's five `cap_cmomi` instances (`loop_filter.XC1`/`XC2`, `vco.XCDECAP`) and a real open-loop `vco` Kvco-vs-band-code table (#23, PRs #28/#33). No closed-loop pre-layout simulation of any kind exists yet — deferred to #27 (open as of this writing). |
| Layout + post-layout sim over PVT | **Partial.** Device-level layout landed for all six blocks (#24, PR #32): **477 / 482 devices drawn**, every drawn device/group `klt drc --deck sg13cmos5l` **clean, zero violations** (24/24 groups, 6/6 composed blocks), and every drawn device/group re-extracts matching its schematic-derived `(class, W, L)`. The 5-device shortfall is exactly this port's five `cap_cmomi` instances, which cannot be drawn — the curated `sg13cmos5l` deck declares no capacitor device class at all ([klayout-tools#1463](https://github.com/2AMLogic/klayout-tools/issues/1463), filed by #24's own pass), never silently dropped from the record. Composition is placement-only — no routing, no floorplan — so there is no post-layout parasitic-annotated netlist to re-simulate; post-layout PVT is explicitly scoped out (`layout/sg13cmos5l-pll/README.md`), tracked as issue #30 (blocked on #29, routing/LVS closure, and on `klt extract --parasitics` rejecting the `sg13cmos5l` deck outright — [klayout-tools#1440](https://github.com/2AMLogic/klayout-tools/issues/1440), open). |
| DRC/LVS-clean GDS, in-repo, open-source-EDA-verifiable | **DRC-clean; LVS is not clean, and this document does not claim it is.** All 6 composed blocks: `klt drc --deck sg13cmos5l` reports `status: "clean"`, `violation_count: 0`. LVS reports two separately-attributable, non-clean outcomes: (1) three blocks (`pfd`, `cp`, `divider_chain`) convert and compare with matching device counts/classes (64/64, 14/14, 316/316) but **zero nets matched** — expected, since composition here is placement only and no net is actually routed, not a deck defect; (2) three blocks (`loop_filter`, `vco`, `lock_detector`) **cannot be converted to LVS at all**, because their reference netlists instantiate `cap_cmomi` and the curated deck declares no capacitor device class to map it to (klayout-tools#1463 again). Neither outcome is reported as "clean." |

**Upstream `klayout-tools` gaps filed by this port** (friction protocol,
`CLAUDE.md`): [#1462](https://github.com/2AMLogic/klayout-tools/issues/1462)
(every `klt gen` generator rejects the `ihp-sg13cmos5l` PDK family, so this
port draws its own device footprints rather than routing around the deck),
[#1463](https://github.com/2AMLogic/klayout-tools/issues/1463) (the curated
`sg13cmos5l` deck has no capacitor device class at all — the root cause of
both the 5-device layout shortfall above and the 3-block LVS non-conversion
above), [#1464](https://github.com/2AMLogic/klayout-tools/issues/1464)
(`klt lvs`'s `reference.deck` subckt-call conversion table is MOS-only, so
this port's own recognised `rppd`/`rhigh` resistors still need an explicit
caller-side `device_map`), and the pre-existing, re-verified-open
[#1440](https://github.com/2AMLogic/klayout-tools/issues/1440) (`klt extract
--parasitics` rejects the `sg13cmos5l` deck outright).

The brief's full sign-off bar requires all three stages, unconditionally
clean. None of the three is fully met today. This document should be read
as reporting real, partially-PVT-cornered verification evidence with every
gap disclosed, not as a completed Challenge #6 submission.

## 6. Bench test plan (for measured silicon, if/when it returns)

None of the rows below exist yet — this is a plan for what a bring-up
bench would need to run, not a report of results:

1. **Open-loop VCO tuning curve vs. band code** — apply the four `B0`/`B1`
   codes and a swept `VCTRL` via precision source-measure units, log
   frequency at `divider_chain.DIVOUT` (or `vco.CLK` if the dedicated debug
   pad from section 2 is realized) with a frequency counter or precision
   timer/counter card; repeat across temperature (thermal chamber/stream)
   to cross-check the simulated Kvco table in section 4 against silicon.
2. **Closed-loop lock acquisition** — apply a reference clock at `REF`,
   sweep `N` (`P0`–`P5`), and capture `LOCK` transition time plus
   `divider_chain.DIVOUT`'s settled frequency on an oscilloscope/frequency
   counter, across supply and temperature corners — the first real
   measurement of the lock-time/settling behavior section 4 row 7 marks
   `insufficient-evidence` in simulation.
3. **Reference spur** — spectrum analyzer on `divider_chain.DIVOUT` (or the
   dedicated `vco.CLK` pad), phase-locked and settled, looking for a spur
   at the reference frequency offset — the row 10 measurement no simulation
   evidence exists for yet.
4. **Period jitter / phase noise** — a phase-noise analyzer or a
   high-bandwidth real-time oscilloscope with jitter-analysis firmware on
   the raw `vco.CLK` tap, both free-running (open-loop) and locked, to
   supply the row 8/9 numbers ngspice cannot compute in simulation at all.
5. **Duty cycle** — high-bandwidth oscilloscope on `vco.CLK`/`DIVOUT`,
   measuring rising/falling-edge symmetry across the full band-code and
   temperature range, targeting the corners (`mos_sf`/`mos_fs`-equivalent
   process spread) the Kvco simulation record explicitly left unswept.
6. **Power** — precision current-sense path (shunt + multimeter, or a
   supply with built-in current metering) on each supply domain
   (`VDD`/`VSS`, `VDD_VCO`/`GND_VCO`, `VDD_DIV`/`VSS`) independently, locked
   and unlocked, across temperature — the row 11 measurement no closed-loop
   simulation exists for yet.
7. **Supply sensitivity / ripple rejection** — inject a calibrated AC
   ripple on `VDD_VCO` (network analyzer or a dedicated ripple-injection
   fixture) and measure the resulting `vco.CLK`/`DIVOUT` frequency
   modulation, to ground section 4 row 12's real but only fractionally
   simulated `XCDECAP` MOM-cap sensitivity against a real supply source
   impedance for the first time.
8. **Output levels / drive** — standard 90/90-style V_OH/V_OL measurement
   into a defined external load at `DIVOUT`/`LOCK`, across PVT — the row 14
   measurement no simulation evidence exists for yet.

## References

- `spec/decision-records/DR-001-pll-architecture.md`,
  `DR-002-supply-device-flavor.md` — architecture and supply/device-flavor
  decisions this port carries unmodified.
- `spec/decision-records/DR-003-sg13cmos5l-port-readiness.md` — the
  readiness audit this whole port traces from (device inventory, MoM-cap
  risk, rail-boundary recommendation, tooling gate).
- `spec/decision-records/DR-004-sg13cmos5l-rail-boundary-ratification.md`
  — ratifies DR-003 Finding 3's rail-boundary reading against the actual
  ported schematics' boundary pins.
- `spec/porting-plan.md` — the fleet-wide porting plan (§1.2's spec-row
  table is the table this document's own section 4 re-derives row by row).
- `design/README.md` — "SG13CMOS5L port" section: full device-substitution
  table, per-instance capacitor sizing, and netlisting verification.
- [`docs/pdk/sg13cmos5l.md`](https://github.com/2AMLogic/2am/blob/main/docs/pdk/sg13cmos5l.md)
  (2AMLogic/2am) — PDK go/no-go verdict, install path, SG13G2→SG13CMOS5L
  device/deck differences, and the analog caveats (no MIM, unvalidated MoM
  models) this document's `insufficient-evidence` rows carry forward.
- [2AMLogic/2am#542](https://github.com/2AMLogic/2am/issues/542) — the
  Chipalooza program epic; its `runbooks/chipalooza.md` is the source of
  the slot-budget numbers section 2 maps against.
- `sim/README.md`, `sim/sg13cmos5l-loop-filter-momcap/`,
  `sim/sg13cmos5l-vco-decap-momcap/`, `sim/sg13cmos5l-vco-kvco-table/` — the
  three PVT-cornered evidence records section 4's spec table draws from.
- `layout/sg13cmos5l-pll/README.md` — the device-level layout record
  section 5's sign-off status draws from.
- Issues #16 (parent, tracks all four phases), #21/PR #21, #22/PR #26,
  #23/PRs #28+#33, #24/PR #32, #27 (deferred closed-loop campaign, open).
