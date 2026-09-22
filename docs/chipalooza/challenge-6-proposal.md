# Chipalooza Challenge #6 — sign-off proposal: SG13CMOS5L integer-N PLL

**Status: schematic + routed layout + pre-layout closed-loop campaign +
post-layout PEX/PVT on 4 of 6 blocks landed — and the measured result is
*not* a finished sign-off.** This document covers the SG13CMOS5L port of
the fleet's integer-N charge-pump PLL (issue #16, Epic
[2AMLogic/2am#542](https://github.com/2AMLogic/2am/issues/542) Phase 5A):
schematic capture for all six blocks (#22, PR #26, since revised four
times — `pfd` reset-parity fix #56, `loop_filter` R1 resize #41, `cp`
cascode-bias replica #72, `lock_detector` window/hysteresis/crowbar fixes
#52/#66/#76), a **routed, DRC-clean** layout for all six blocks (#24 →
#29), a real post-layout PEX+PVT campaign re-running ratified matrices on
4 of the 6 blocks (#30, refined by #101/#102; the `loop_filter` and
`divider_chain` arms are #115, open), and a real transistor-level
closed-loop campaign (#37, five records) that **measured** the rows the
original proposal could only defer — and found row 7 (lock time) failing:
the committed `divider_chain` does not function as a divider at any tested
corner (#36; fix in flight as #112), and even the mitigated proposal loop
holds a static phase error of 8.203% of a reference period against this
campaign's own 5% threshold. Challenge #6's full sign-off bar (schematic +
pre-layout sim → layout + post-layout sim over PVT → DRC/LVS-clean GDS,
open-source-EDA-verifiable) is **not met**, now on measured evidence rather
than on missing testbenches. Every spec row below is re-derived directly
from the `sim/`/`layout/` evidence that exists today; any row that
evidence cannot bound is marked `insufficient-evidence` rather than
relaxed to pass, per this repo's own `CLAUDE.md`. **This is a partial
re-derivation pass, deliberately run before its siblings close** (#112
divider fix, #113 `vco` LVS root-cause, #114 MOM-cap layout, #115
remaining post-layout arms are all open as of this writing); a final pass
should re-derive the affected rows again once those land.

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
| Digital control inputs | **9 / 24** | `REF` (reference clock, 1), `vco.B0`/`B1` (coarse band select, 2), `divider_chain.P0`–`P5` (N-select, 6 — the 6-bit code's structural range is `N ∈ [64, 127]` after DR-005's reconciliation with the measured VCO band, but the committed chain has not been electrically verified to divide at all — see section 4 row 3). `cp.IBP`/`ICP`/`IBN`/`ICN` are **not** counted here — see the bias-current note below. |
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
- **`cp.IBP`/`ICP`/`IBN`/`ICN` — current-input pins since issue #72's
  on-chip cascode bias replica (DR-006) — are assumed to map onto the
  harness's own shared bias infrastructure** (the common harness supplies
  "≤2 bandgap-referenced current sources" per the program runbook),
  consistent with `spec/porting-plan.md`'s carried-over "bias-current
  generation is not this block's own problem" scoping (DR-001-equivalent).
  This is an **assumption**, not verified against a harness spec this repo
  does not have access to — flagged as an open wrapper-integration
  question, the same way the Challenge #2 bandgap proposal flagged its own
  `vdd`/`vss` supply-sourcing assumption.
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
(PR #26, `Closes #22`, subsequently revised by #41/#52/#56/#66/#72/#76 as
named below) is a topology-for-topology port of this repo's own SG13G2
schematics (`design/*.sch`), which are themselves ported from the fleet's
ratified gf180-pll/sky130-pll references per `spec/
decision-records/DR-001-pll-architecture.md`:

- **`pfd`** — a tri-state edge-detect + SR-latch phase/frequency detector,
  reset delay sized in the charge domain (reset delay > charge-pump
  turn-on time), not just the logic domain. **Revised by #56** after the
  closed-loop campaign root-caused the as-drawn self-reset chain's
  even-inverter parity (reset = `NAND(UP,DN)` instead of `AND(UP,DN)`,
  leaving both SR latches permanently transparent with no phase-error
  memory — `sim/sg13cmos5l-closed-loop-lock/records/RECORD-002`, issue
  #50); a third `inv_hv` stage (`XI1B`) restores odd parity, LVS
  re-verified 66/66 devices, 37/37 nets `match`.
- **`cp`** — a wide-swing cascode charge pump with unit-element (not
  binary-weighted) current trim and a shared, buffered ("tracking") dump
  node to null idle-leg tail-charge exchange. **Revised by #72** after the
  closed-loop campaign confirmed `up`/`dn` current-magnitude mismatch as
  *a* dominant mechanism behind its static phase error: each polarity now
  carries its own on-chip high-swing cascode bias replica (`MBP`/`MBPC`/
  `MCP`, `MBN`/`MBNC`/`MCN`, DR-006), making `IBP`/`ICP`/`IBN`/`ICN`
  current-input pins and cutting the DC-measured worst-case mismatch 20×
  (`sim/sg13cmos5l-cp-icp-trim/records/RECORD-002`: 10.28% → 0.72%; at
  the loop's own operating point −6.42% → −0.298%).
- **`loop_filter`** — a passive series-R + shunt-C1 + shunt-C2 network. Its
  two SG13G2 `cap_cmim` (MIM) instances (`XC1`, `XC2`) do not port
  as-is — SG13CMOS5L has **no MIM capacitor at all**
  (`docs/pdk/sg13cmos5l.md`, 2AMLogic/2am) — and are replaced by
  `cap_cmomi` (interdigitated MOM) instances, `w=40u l=40u` and
  `w=10u l=10u` respectively (unchanged since the original port).
  **`R1` was resized by #41** (DR-006) from `w=4u l=120u` (~7.79 kΩ) to
  `w=0.6u l=810u` (~344.2 kΩ, ~44.2×) after
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-001` measured **0 of
  90** PVT combinations meeting the ≥45° phase-margin criterion with the
  as-drawn value and RECORD-002 showed the initially-proposed ×20 scale
  still fails near the DR-005-amended `f_ref` floor (worst case ~22.6°
  short at `band=00`, low `VCTRL`, `f_ref=4.5 MHz`).
- **`vco`** — `vco_bias` (constant-gm beta-multiplier core) + 5×
  `vco_stage` (current-starved inverter ring, source-degenerated V→I
  converter, geometric coarse mirror cascade for the `B0`/`B1` band
  select) + 2× `inv2x_hv` output buffer, with a dedicated `VDD_VCO`/
  `GND_VCO` supply domain and an on-chip decap (`XCDECAP`, also a
  `cap_cmomi` MOM-cap substitution for the original `cap_cmim`,
  `w=70u l=70u`). Unrevised to date.
- **`divider_chain`** — a cascaded ÷2/3 (Vaucher) chain, static CMOS, with
  a VCO-clocked final retiming flop independent of `N`, and a 6-bit
  `P0`–`P5` divide-ratio select (structural range `N ∈ [64, 127]` after
  DR-005). **Still as originally ported — and now known defective**:
  `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-001` (issue #36)
  measured the committed chain failing to function as a divider at **any
  of 9 tested corners** (its `dff_tg_hv` hold path is a self-biased
  inverter, not a real latch). A minimal proposal fix (`fbfix`, not
  committed) holds at the rail in 9/9 corners; committing a fix is issue
  #112 (open).
- **`lock_detector`** — a passive phase-error window comparator (XOR of
  `UP`/`DN`, delayed-AND width check) with asymmetric assert-slow/
  deassert-fast dynamics via a Schmitt trigger, no FSM. Two more
  `cap_cmim` → `cap_cmomi` substitutions land here — **both since resized
  by #52** to `w=40u l=40u` (`XCW`, m=1; `XDW.XC1`, m=2) after the
  `sg13cmos5l-lock-detector-window` campaign measured the as-drawn
  integrating-node R·C 23–1412× *below* the reference period at every
  corner. #66 then re-tied `schmitt_hv`'s two feedback devices to the
  classic connection and resized `XMPD` (`w=2u l=0.5u` → `w=0.25u
  l=16u`), and #76 lengthened `schmitt_hv`'s six channels (`l=0.5u` →
  `l=2u`) to cut its crowbar current 3.2–4.3×.

**Device substitution, in full** (`design/README.md`, "SG13CMOS5L port",
DR-003 Findings 1–2): `sg13_hv_nmos`/`sg13_hv_pmos` (MOSFETs) and
`rppd`/`rhigh` (poly resistors) need **no device-name or subcircuit-
signature change** — 485 of the design's current 490 devices — because
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
real SG13CMOS5L `sim/`/`layout/` evidence where it exists, and marked
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
| 1 | Output band | **Insufficient-evidence for a ratified target — and now bounded from both sides.** Schematic level: an open-loop `vco` transient sweep measures oscillation from 445.3 MHz (`slow` bundle, any band, `VCTRL=0.3V`) to 1562.0 MHz (`fast` bundle, band `11`, `VCTRL=2.7V`) across the swept 60-point matrix (open-loop only). Post-layout (#30/#101): re-extracted PEX netlists of the *routed* `vco` measure **347.6–1182.8 MHz** (mean per-point deviation −22.6%; −49.3% / 223.7–789.5 MHz before #101's floorplan pass cut that block's routed wire 7178 → 3913 µm), ~99% of the original deviation attributed by a 7-variant diagnostic to parasitic *capacitance*. Every post-layout number here is an **upper bound set by routing style, not a floorplan prediction** (the coefficients are uncalibrated public-data starter values, and `vco` has no confirmed layout↔schematic topology match — see row 15/LVS below) | `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md`; `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md`, `RECORD-002-floorplan-aware-vco-route.md` |
| 2 | Reference input | **Insufficient-evidence for the electrical levels; the frequency range is re-derived and amended.** DR-005 (issue #40) reconciled the ported `f_ref = 1–25 MHz` with the measured VCO band and amended row 2 to **`f_ref ≈ 3.51–24.4 MHz`** (floor 445.3 MHz/127, ceiling 1562.0 MHz/64) alongside row 3's `N ∈ [64,127]`; the interface *shape* (CMOS square wave, rising-edge, 30–70% duty) is unchanged. No dedicated `V_IL`/`V_IH` duty-cycle testbench exists for the `pfd` itself. What *is* now measured: the as-drawn `pfd` carried a real functional defect (self-reset inverter parity, #50/#56 — found in the closed loop, fixed, LVS re-verified); and the post-layout PEX `pfd` (LVS-matched, #102) stretches every internal arc by a flat **+0.53 ns** (benign, +9.3% duty at the ratified 10%-of-period REF-lead offset) but **inverts its phase discrimination on the FB-leading side at 20 MHz** (UP holds `(T_ref − τ + 0.2 ns)`, DN never holds — a genuine steady mode, node-level traced to slowed input→latch edges) | `spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md`; `sim/sg13cmos5l-closed-loop-lock/records/RECORD-002-pfd-reset-parity-root-cause.md`, `RECORD-003-pfd-reset-fix-closed-loop-rerun.md`; `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` §2 |
| 3 | Multiplication ratio (N) | **Fails, functionally, as committed.** `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-001` (issue #36, closed) measured the **committed `divider_chain` not functioning as a divider at any of 9 tested corners** — its `dff_tg_hv` hold path is a self-biased inverter, not a real latch (0/9 corners hold at the rail; settles to a process/supply-dependent mid-rail voltage). This is the block-level root cause of the same non-toggling `FB` node the closed-loop campaign's Part A observed independently (row 7). A proposal variant (`fbfix`, **not committed**) with a minimal 3-line hold-path fix holds cleanly at the rail in 9/9 corners and divides by exactly `N=64` at a 100 MHz baseline, matching the structural range's floor; DR-005 amended the ported `N ∈ [4,64]` to **`N ∈ [64,127]`, no holes**, matching the 6-cell ÷2/3 chain's structural range against the measured VCO band. Retiming margin at the measured top-of-band 1562.0 MHz is judged **inadequate for the proposal sizing** (its single-flop setup sweep fails to capture at every tested `TSU` up to 300 ps, 3 corners); no numeric margin bound is claimed — the whole-chain transient there was not reliably reproducible in-session. Committing the fix is **issue #112 (open, in flight)** | `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-001-nrange-retiming-margin.md`, `RECORD-002-pdk-root-token-fix-reverification.md`; `spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md`; `sim/sg13cmos5l-closed-loop-lock/records/RECORD-001-closed-loop-lock-spur-power.md` ("Divider chain caveat") |
| 4/5 | Kvco bound / band-selection rule | **Met (bounded), pre-layout; post-layout re-measured (an upper bound).** A real, PVT-cornered (3 process×temperature bundles × 4 band codes × 5 `VCTRL` points, 60 runs), per-band, open-loop Kvco table exists; `Kvco` is measurably non-constant across the sweep (e.g. `typ`/band `00`: 173.8 MHz/V averaged vs. 206.0 MHz/V at the top of the range, ~19% difference) — a real nonlinearity, not noise, consistent with the row's own "table, not a scalar" framing. Band select is inert at low `VCTRL` (all four band codes read the identical frequency at `VCTRL=0.3V`) and dominant at high `VCTRL` (~2.8× spread at `VCTRL=2.7V`). Post-layout (#30): the PEX `vco` runs at 0.4768–0.5312× its schematic frequency at 60/60 points (band 223.7–789.5 MHz as first routed; 347.6–1182.8 MHz after #101's floorplan pass) — the Kvco *table's shape* survives, its absolute numbers do not, bounded by routing style (row 1's caveats). The `cp` trim ladder that would re-anchor the loop's gain post-layout survives to +0.055..+0.632% (UP) / +0.017..+0.211% (DN) over its full 306-point PVT matrix | `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md` (full 12-row table below); `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-001` §vco, `RECORD-002` |
| 6/6a | Loop bandwidth / phase margin | **Measured, and the story is a fix chain with a residual coverage gap — not a pass as first drawn.** The row's own kHz/degree numbers now exist end-to-end: with the **as-drawn** filter, `f_c` = 0.33–4.64 MHz and PM = 1.55–20.33° across 90 real-subckt AC runs — **0 of 90 meet the ≥45° criterion**, and no trim code trades one criterion against the other (`sg13cmos5l-loop-bandwidth-pm` RECORD-001). #41 therefore resized `R1` ×44.2 (DR-006, committed); against the **full DR-005-amended `f_ref` range** (both bands, three Kvco intervals, 426 runs) the resized filter meets both criteria (`f_c < f_ref/10`, PM ≥ 45°) at 16 of 30 (band, interval, `f_ref`) combinations with full 3-bundle coverage, at 12 more with only 1–2 of 3 PVT bundles simulated (a *coverage* gap, passing at every bundle actually run), and failed 2 outright — both since **closed by fine Icp-trim codes** (#83: 3.75 µA, DR-007; #79: 11 µA, DR-008, PM 45.6°/49.0°/53.5° at fast/typ/slow with `f_c` ≤ 435 kHz against the 450 kHz ceiling). The 12 partial-PVT-coverage combinations remain open as future work. All numbers are pre-layout (real `loop_filter` subckt, linearised stand-ins for PFD/CP/VCO/divider whose values come from the measured records); a post-layout `loop_filter` arm is #115 (open). The filter's own zero/pole spread under process+temperature+MOM uncertainty stands as originally bounded (nominal `fz = 12.07 MHz`, 27-corner 8.97–16.92 MHz) | `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-001-loop-bandwidth-phase-margin.md`, `RECORD-002-r1-resize-full-fref-range.md`, `RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`, `RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`; `sim/sg13cmos5l-loop-filter-momcap/records/RECORD-001-rc-corner-momcap-sensitivity.md`; `sim/sg13cmos5l-cp-icp-trim/records/RECORD-003-issue83-finetrim-icp.md`, `RECORD-004-issue79-finetrim-icp.md`; DR-006/DR-007/DR-008 |
| 7 | Lock time | **Fails — measured, not merely missing.** A real transistor-level closed loop (all six subckts, testbench-local wiring — no `pll_top` exists; single PVT point `mos_tt`/`res_typ`/27 °C, 20 MHz/`N`=64/band `11`, runtime-cost subset) now exists with five records. Part A (as-committed blocks) never locks: `FB` never crosses the logic threshold (the row-3 divider defect), `n_ref_cycles_observed = 0`, `lock_time = None`. Part B (a *proposal* deck — resized filter + behavioural divide-by-64, both known defects deliberately set aside) **frequency-locks** after the #56 `pfd` fix (`Δf`/`f_ref` within 0.03% held for a full microsecond, zero cycle slips) but settles at a stable static phase error of **9.176%** of a reference period — 1.8× this campaign's own 5% dual-lock threshold (`|Δf/f_ref| < 1%` AND phase error < 5%, ≥20 consecutive cycles); longest dual-lock run 4 cycles. An ideal-cp diagnostic (#70) collapses the residual to −0.00235% (numerical noise) and extends the dual-lock run to 41 cycles (lock_time 450 ns) — confirming current mismatch as *a* dominant mechanism — and the real mitigated `cp` (#72) then cuts the DC mismatch 20× but the closed-loop residual only to **8.203%**, with the longest dual-lock run still 4 cycles and `lock_time = None`: the best-fitting remaining candidate is switching/dynamic charge mismatch, which no diagnostic has yet isolated. **Row 7 fails for the mitigated design, not just the as-drawn one** | `sim/sg13cmos5l-closed-loop-lock/records/RECORD-001-closed-loop-lock-spur-power.md` … `RECORD-005-cascbias-real-cp-static-phase-error-rerun.md` (all five) |
| 8 | Period jitter | **Insufficient-evidence for the absolute number.** `vco.XCDECAP`'s own capacitance is bounded (nominal **5.2862 pF**, matching `design/README.md`'s "~5.29 pF" placeholder to 4 figures) and its fractional supply-decoupling pole-frequency sensitivity to the ±20% MOM band is bounded (illustrative `R_src=3kΩ`: 12.54 MHz / 10.03 MHz / 8.35 MHz at −20%/0%/+20%, a 1.502× span matching the exact analytic `1/0.8 : 1/1.2` prediction). A post-layout parasitic source impedance **now exists** (routed layout + `klt extract --parasitics` with real curated metal R/C coefficients, #30) — retiring the original "no post-layout parasitic source impedance" half of this row's caveat — but it is an upper bound set by the un-representative floorplan with uncalibrated coefficients, and the absolute jitter-as-percent-of-period number still cannot be computed: ngspice has no direct phase-noise computation for a free-running oscillator (a pre-existing flow limitation, not an SG13CMOS5L-specific one — see row 9) | `sim/sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md`; `sim/sg13cmos5l-postlayout-pex-pvt/` (extraction provenance) |
| 9 | Integrated RMS jitter / phase noise | **N/A, carried as-is** — deliberately not spec'd. This is a flow limitation (ngspice has no `.noise` path for a free-running oscillator), sourced from gf180-pll's own `DR-002` Decision 5, not this repo's own DR-002 (which has no Decision 5) — applies identically on SG13CMOS5L since it is tool-, not PDK-, dependent | `spec/porting-plan.md` row 9 (citing gf180-pll `DR-002` Decision 5) |
| 10 | Reference spur | **Insufficient-evidence — for a different, now-measured reason: the loop never phase-locks, so there is no stable locked carrier to define a spur around.** The original deferral (no charge-pump mismatch data, no closed-loop steady state) is retired: the DC mismatch data is real (`sg13cmos5l-cp-icp-trim` RECORD-001/RECORD-002: −3.17% at `mos_tt`/27 °C as drawn; worst-case 10.28% → 0.72% over the full PVT/`VOUT` matrix after #72's mitigation), and the closed-loop decks ran Goertzel-DFT spur extraction on their own `vctrl` waveforms (~−39.7/−36.0 dBc) — **deliberately not reported as row-10 measurements**, because a frequency-locked-but-not-phase-locked loop (row 7's 8.2–9.2% static phase error) has no settled carrier for a dBc figure to reference. A real spur number additionally needs the switching charge mismatch and PFD reset window, both still unmeasured | `sim/sg13cmos5l-closed-loop-lock/records/RECORD-001` ("Row-by-row disposition"), `RECORD-003`, `RECORD-005`; `sim/sg13cmos5l-cp-icp-trim/records/RECORD-001-icp-trim-and-mismatch.md`, `RECORD-002-cascode-bias-mismatch-remeasure.md` |
| 11 | Power | **Bounded — real, simultaneous, explicitly non-clean numbers.** All five domains measured together in one closed-loop deck at one (non-locked) operating point, `mos_tt`/27 °C: **whole-PLL ≈ 10.137 mA (33.45 mW at 3.3 V), of which the `divider_chain` domain alone is 7.653 mA (25.26 mW)** — flagged by the record itself as very likely inflated by that block's row-3 malfunction (gf180-pll's *entire* PLL draws under 5 mW). Excluding the defective divider, the other four domains total **2.483 mA (8.20 mW)**; the functional `fbfix` divider variant's ≈166 µA at a 100 MHz baseline corroborates the inflation (~46× below, different variant/frequency). Per-domain: `vco` 3.09–8.88 mW standalone across PVT (`sg13cmos5l-vco-duty-cycle`) — the VCO **alone already exceeds gf180-pll's whole-PLL figure**, reaffirming row 11's "no V² rescale" disposition; mitigated `cp` −39.26 µA in-loop (up from −24.66 µA, a supply-bookkeeping change DR-006 itself predicted); `lock_detector` 2.48–113 µA (10×-window probe) post-#76, and 6.8–15.7 µA in-lock @3.5 MHz / 93.3–99.7 µA @24.4 MHz as-routed post-layout (#102). A clean whole-PLL total still waits on the divider fix (#112) | `sim/sg13cmos5l-closed-loop-lock/records/RECORD-001` (row-11 disposition), `RECORD-003`, `RECORD-005`; `sim/sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md`; `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-001`; `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-003` §3.4 |
| 12 | Supply sensitivity | **Insufficient-evidence for the absolute mV-ripple/dB-attenuation budget.** A post-layout parasitic source impedance now exists (row 8's update — real extracted R/C, #30) but is bounded by routing style and uncalibrated coefficients, and there is still no direct small-signal method for the ring's own unstable DC operating point. The fractional MOM-band-to-pole-frequency sensitivity is bounded (row 8's own 1.502× span) | `sim/sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md`; `sim/sg13cmos5l-postlayout-pex-pvt/` (extraction provenance) |
| 13 | Output duty cycle | **Measured — and the 45% floor is not met at the cold corner.** The original gap (the Kvco record's single-edge methodology, `mos_sf`/`mos_fs` corners unswept) is retired by a dedicated 300-run campaign (5 MOS corners *including* the split corners × 3 temps × 4 band codes × 5 `VCTRL` points, rising *and* falling 50%-of-rail crossings): duty cycle spans **43.74–51.56%**, with **30 of 300 points below the 45% floor — every one at −40 °C** (worst 43.74%, `mos_fs`, `VCTRL=0.3 V`). No point exceeds the 55% ceiling. The record carries this forward as a real design flag reproducing gf180-pll's own duty-cycle finding on a different process, not as a measurement artifact | `sim/sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md` |
| 14 | Output levels / drive | **Insufficient-evidence** — no waveform-into-a-defined-load (V_OH/V_OL vs. ≤50 fF) measurement has been run against any SG13CMOS5L block yet (the post-layout `pfd` duty-space arm of #102 measures pulse widths, not output levels into a specified load) | none |
| 15 | Area | **Insufficient-evidence** — no top-level layout, floorplan, or composed `pll_top` exists to measure an area figure from. The device-level layout is now **routed** (6/6 blocks composed and wired, 485/490 devices drawn, 167 mm of drawn routing wire, `divider_chain` ~1.7 mm wide — `layout/sg13cmos5l-pll/README.md`), and the composition is explicitly *not* a considered floorplan (single-row placement, no matching, no folding; a representative analog floorplan is unowned — #100, operator-blocked) | `layout/sg13cmos5l-pll/README.md` ("What it is not") |
| 16 | Lock-detector targets | **Schematic: all three measurable criteria now PASS — after three design passes. As-routed: all three FAIL, because the layout does not carry the block's two MOM caps.** The original campaign (#38) measured the as-drawn block failing window (0.219–0.409 ns vs ≥2.5 ns), hysteresis (none resolvable vs ≥25% of window) and chatter (92/92 points) at every corner — root cause: the integrating node's R·C was 23–1412× *below* the reference period. #52 resized `XRPU`/`XCW`/`XDW.XC1` (window and no-chatter now pass); #66 re-tied `schmitt_hv`'s feedback devices and resized `XMPD` (hysteresis now passes: **50–800% of window, 0 of 21 corners below the ≥25% criterion**); #76 lengthened `schmitt_hv`'s channels for crowbar current (3.2–4.3× lower, criteria re-verified unchanged in substance). Final schematic state: window **3.688–11.24 ns at 102/102 points** (worst case 1.475× the floor), `steady` at **21/21** ladder corners at a 20×-window static phase error, R·C = 8.0–19.5× the slowest reference period (6.4–23.4× with the ±20% MOM band). The "≥ 2× worst static phase offset" half stays `insufficient-evidence` (needs the phase-error distribution a locked loop would produce — row 7). Post-layout (#102): the as-routed cell **fails all three criteria on both arms** — window 0.21–0.36 ns as-layout / 0.34–0.60 ns post-layout across 29 PVT points, chatter at every 3.5 MHz ladder point up to 10× the window — because the two undrawn MOM caps (1.691 pF + 3.382 pF vs ~71 fF of extracted VWIN parasitic capacitance) *are* the window; drawing them is issue #114 (open). The "static-phase-offset ≥ 2×" comparison additionally stays open | `sim/sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md` … `RECORD-004-crowbar-current-mitigation.md` (all four); `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` §3 |
| 17 | Standby / power-down | **N/A, carried as-is** — no power-down mode in v1, a deliberate scope decision on both sibling repos, not a testbench claim | `spec/porting-plan.md` row 17 |
| 18 | Supply range | **Insufficient-evidence for a numeric ±10%-style whole-design supply-corner result.** DR-002/DR-004 ratify the qualitative all-3.3V internal design; the one real supply axis in the campaign is the `cp` block's own ±10% supply sub-axis inside its 306-point DC matrix (`sg13cmos5l-cp-icp-trim` RECORD-001/002); the Kvco record fixes `VDD_VCO=3.3V` throughout ("no 1.2V corner applies to an internal block like the VCO itself"), and the post-layout arms likewise run at 3.3 V | `sim/sg13cmos5l-cp-icp-trim/records/RECORD-001-icp-trim-and-mismatch.md`; `sim/sg13cmos5l-vco-kvco-table/corners/matrix.md`; `sim/sg13cmos5l-postlayout-pex-pvt/corners/matrix.md` |

**Full Kvco-vs-band-code table** (row 4/5's own pre-layout evidence, all 60
measured points condensed to the per-bundle/per-band summary;
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
| Schematic + pre-layout sim | **Partial — the missing testbenches now exist, and two of the rows they measure fail.** Schematic captured for all six blocks (#22, PR #26, DR-003/DR-004 ratified) and since revised on measured evidence (`pfd` #56, `loop_filter` R1 #41, `cp` #72, `lock_detector` #52/#66/#76). The originally-deferred pre-layout campaign has run in full: a real PVT-cornered Icp-trim/mismatch table (#27), loop bandwidth/phase margin across the amended `f_ref` range (#27/#41/#83/#79 — criteria met at the resized filter with named trim codes, 12 of 30 combinations with partial PVT coverage), duty cycle (#27 — 45% floor fails at −40 °C), lock-detector window/hysteresis/chatter (#38/#52/#66/#76 — all three schematic criteria pass), divider N-range (#36 — **committed chain does not divide at any tested corner**, fix in flight #112), and a real transistor-level closed loop (#37 + #50/#56/#70/#72, five records — **row 7 fails**: no deck acquires the campaign's dual lock criterion; the mitigated proposal loop holds an 8.203% static phase error). |
| Layout + post-layout sim over PVT | **Partial — routed and post-layout-simulated on 4 of 6 blocks, every number bounded by routing style.** All six blocks are composed **and routed**, `klt drc --deck sg13cmos5l` clean at zero violations on every routed cell (#24 → #29; re-run after each design revision, #56/#72). `klt extract --parasitics` now works with real curated metal R/C coefficients (klayout-tools#1440 closed via #2012; #2113 closed via #2126), and the ratified PVT matrices were re-run against parasitic-annotated netlists with schematic-level control arms for `vco` and `cp` (#30, PR #99), `vco` again after a floorplan-aware re-route that cut its wire 7178 → 3913 µm and its frequency deviation −49.3% → −22.6% (#101), and `pfd` + `lock_detector` (#102). Headline post-layout findings: `vco` runs at ~0.48–0.53× its schematic frequency (~99% parasitic capacitance; upper bound set by routing style, not a floorplan prediction); the `cp` trim ladder survives to ≤0.632%; the `pfd` gains +0.53 ns on every internal arc and **inverts its FB-leading phase discrimination at 20 MHz**; the as-routed `lock_detector` fails all three row-16 criteria (its two MOM caps are undrawn). The `loop_filter` and `divider_chain` post-layout arms are **#115 (open, blocked)**, and a representative analog floorplan is unowned (#100). |
| DRC/LVS-clean GDS, in-repo, open-source-EDA-verifiable | **DRC-clean on all six routed blocks; LVS is not clean on all six, and this document does not claim it is.** `klt lvs` on the committed flow: three blocks **`match`** with every device *and* net matched — `pfd` 66/66 devices, 37/37 nets; `cp` 20/20 devices, 18/18 nets (both re-verified after the #56/#72 design revisions); `divider_chain` 316/316 devices, 142/142 nets. Three blocks could not be converted at all by the committed flow (klayout-tools#1463, `cap_cmomi` has no capacitor device class in the reference conversion path). #30's separately-recorded LVS re-check — same GDS, same deck, plus the one `reference.device_map` entry klt's own error message names — makes the picture sharper, not cleaner: `loop_filter` now compares and reports **`mismatch` (0/3 devices)** — the routed cell carries only its `rppd`; both MOM caps are undrawn, so it is not a loop filter; `vco` compares and reports **`mismatch` (38/45)** — unmatched: the undrawn `DECAP` cap, six `XBIAS` resistors, and one `net.merged` on `BIAS.SUB!`, not root-caused (#113, open); `lock_detector` remains **not compared**, its blocker *changed* from the missing device class to the deck's documented plain-element `m=2` limitation. The 5-device shortfall (the design's five `cap_cmomi` instances, 485/490 drawn) is recorded with per-instance `blocked_reason`s, never silently dropped; drawing them is #114 (open, in flight). |

**Upstream `klayout-tools` gaps filed by this port** (friction protocol,
`CLAUDE.md`): [#1462](https://github.com/2AMLogic/klayout-tools/issues/1462)
(every `klt gen` generator rejected the `ihp-sg13cmos5l` family — **closed
2026-08-30 and present at this repo's pin**; #35 re-measured the generator
output against the local footprints and kept the local ones, filing
[#1472](https://github.com/2AMLogic/klayout-tools/issues/1472) (no
thick-oxide marker layer for the IHP families) and
[#1473](https://github.com/2AMLogic/klayout-tools/issues/1473) (generated
PFET wells are untied/unnamed) as the two upstream fixes a swap would need),
[#1463](https://github.com/2AMLogic/klayout-tools/issues/1463) (no
capacitor device class — **closed** for the extraction half, but the
reference-netlist conversion half still needs the explicit
`reference.device_map` entry, which is
[#1464](https://github.com/2AMLogic/klayout-tools/issues/1464) territory —
closed as completed but not yet re-tested/droppable here),
[#1467](https://github.com/2AMLogic/klayout-tools/issues/1467)
(`gen-compose` routes 1 of 13 nets on a block this size — open, re-probed
every run),
[#1474](https://github.com/2AMLogic/klayout-tools/issues/1474) (the IHP
families expose exactly one routing-metal role, so `gen-compose`'s escape
hatch cannot be named — open), the pre-existing
[#1440](https://github.com/2AMLogic/klayout-tools/issues/1440)
(`klt extract --parasitics` rejected the deck — **closed via #2012**),
[#2113](https://github.com/2AMLogic/klayout-tools/issues/2113)
(parasitics extraction silently zero — **closed via #2126**, curated
Metal1–TopMetal1 R/C coefficients),
[#1157](https://github.com/2AMLogic/klayout-tools/issues/1157)
(three-terminal `R` cards are not ngspice-simulatable — open; #30 narrowed
its scope condition and this repo works around it in
`pex-to-ngspice.py`), and
[#2145](https://github.com/2AMLogic/klayout-tools/issues/2145)
(hierarchical net names joined with `.` collide with ngspice's own
separator — open, same workaround).

The brief's full sign-off bar requires all three stages, unconditionally
clean. None of the three is fully met today. This document should be read
as reporting real, PVT-cornered (explicitly subsetted where runtime cost
forced it — each record's own `corners/matrix.md` says where) verification
evidence with every gap disclosed, not as a completed Challenge #6
submission.

## 6. Bench test plan (for measured silicon, if/when it returns)

None of the rows below exist as silicon measurements — this is a plan for
what a bring-up bench would need to run, cross-checked against the
simulation evidence that now exists per row:

1. **Open-loop VCO tuning curve vs. band code** — apply the four `B0`/`B1`
   codes and a swept `VCTRL` via precision source-measure units, log
   frequency at `divider_chain.DIVOUT` (or `vco.CLK` if the dedicated debug
   pad from section 2 is realized) with a frequency counter or precision
   timer/counter card; repeat across temperature (thermal chamber/stream)
   to cross-check the simulated Kvco table in section 4 against silicon —
   and against the post-layout PEX prediction that routing alone costs the
   ring roughly half its frequency (row 1's upper bound).
2. **Closed-loop lock acquisition** — apply a reference clock at `REF`,
   sweep `N` (`P0`–`P5`), and capture `LOCK` transition time plus
   `divider_chain.DIVOUT`'s settled frequency on an oscilloscope/frequency
   counter, across supply and temperature corners — the row 7 measurement
   every closed-loop deck so far has failed to acquire (section 4).
3. **Reference spur** — spectrum analyzer on `divider_chain.DIVOUT` (or the
   dedicated `vco.CLK` pad), phase-locked and settled, looking for a spur
   at the reference frequency offset — the row 10 measurement that still
   has no valid simulated carrier to reference (section 4).
4. **Period jitter / phase noise** — a phase-noise analyzer or a
   high-bandwidth real-time oscilloscope with jitter-analysis firmware on
   the raw `vco.CLK` tap, both free-running (open-loop) and locked, to
   supply the row 8/9 numbers ngspice cannot compute in simulation at all.
5. **Duty cycle** — high-bandwidth oscilloscope on `vco.CLK`/`DIVOUT`,
   measuring rising/falling-edge symmetry across the full band-code and
   temperature range — the split process corners and the −40 °C regime
   where the 300-point simulation matrix already predicts 43.74% duty
   cycles below the 45% floor (row 13).
6. **Power** — precision current-sense path (shunt + multimeter, or a
   supply with built-in current metering) on each supply domain
   (`VDD`/`VSS`, `VDD_VCO`/`GND_VCO`, `VDD_DIV`/`VSS`) independently,
   locked and unlocked, across temperature — the row 11 measurement whose
   simulated proxy (10.137 mA whole-PLL, 7.653 mA of it a defective
   divider) is explicitly non-clean until #112 lands.
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
- `spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md` —
  amends row 2's `f_ref` to ≈3.51–24.4 MHz and row 3's `N` to [64, 127]
  against the measured VCO band.
- `spec/decision-records/DR-006-cp-cascode-bias-replica.md`,
  `DR-006-loop-filter-r1-resize.md`,
  `DR-006-lock-detector-fref-dependent-threshold.md`,
  `DR-007-cp-icp-trim-fine-code-band00-mid-fref4p5.md`,
  `DR-008-cp-icp-trim-fine-code-band00-low-fref4p5.md` — the design-change
  decisions this document's row dispositions trace to.
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
- `sim/README.md` plus the SG13CMOS5L evidence slugs section 4 draws from:
  `sg13cmos5l-loop-filter-momcap/`, `sg13cmos5l-vco-decap-momcap/`,
  `sg13cmos5l-vco-kvco-table/`, `sg13cmos5l-cp-icp-trim/`,
  `sg13cmos5l-loop-bandwidth-pm/`, `sg13cmos5l-vco-duty-cycle/`,
  `sg13cmos5l-divider-nrange-retiming/`,
  `sg13cmos5l-lock-detector-window/`, `sg13cmos5l-closed-loop-lock/`,
  `sg13cmos5l-postlayout-pex-pvt/`.
- `layout/sg13cmos5l-pll/README.md` — the routed-layout record section 5's
  sign-off status draws from (per-block table, LVS re-check, friction
  log).
- Issues #16 (parent epic, open), #21/PR #21, #22/PR #26, #23/PRs #28+#33,
  #24/PR #32, #27 (**closed** — delivered the Icp-trim, loop-bandwidth/PM
  and duty-cycle campaigns; its closed-loop/lock-detector/divider scope
  was split to #37/#38/#36, all closed), #29, #30/PR #99, #36, #37, #38,
  #40, #41, #50, #52, #56, #66, #70, #72, #76, #79, #83, #101, #102 — and
  the still-open follow-ups this partial pass deliberately runs ahead of:
  **#112** (divider fix, in flight), **#113** (`vco` LVS mismatch
  root-cause), **#114** (MOM-cap layout), **#115** (`loop_filter` +
  `divider_chain` post-layout arms), **#100** (representative floorplan,
  operator-blocked).
