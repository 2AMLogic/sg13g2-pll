# Chipalooza Challenge #6 — sign-off proposal: SG13CMOS5L integer-N PLL

**Status: schematic + routed layout + pre-layout closed-loop campaign +
post-layout PEX/PVT arms on all six blocks + DRC/LVS `match` on all six
blocks landed — and the measured result is *still* not a finished
sign-off.** This document covers the SG13CMOS5L port of
the fleet's integer-N charge-pump PLL (issue #16, Epic
[2AMLogic/2am#542](https://github.com/2AMLogic/2am/issues/542) Phase 5A):
schematic capture for all six blocks (#22, PR #26, since revised by nine
measured-evidence passes — `pfd` reset-parity fix #56, `loop_filter` R1
resize #41, `cp` cascode-bias replica #72, `lock_detector`
window/hysteresis/crowbar fixes #52/#66/#76, `divider_chain` functional
repair #112, `vco`/`lock_detector` LVS body-tie fixes #113/#136), a **routed, DRC-clean, LVS-`match`** layout
for all six blocks — 569/569 devices drawn, 6/6 `klt lvs` `match`
(#24 → #29 → #114 → #136; layout record `20261003-183059-dc5644a`), a real
post-layout PEX+PVT campaign re-running ratified matrices on **all six**
blocks (#30, refined by #101/#102; the `loop_filter` and `divider_chain`
arms landed as #115/RECORD-004), and a real transistor-level closed-loop
campaign (#37, five records) that **measured** the rows the
original proposal could only defer — and found row 7 (lock time) failing:
as of those records the committed `divider_chain` did not function as a
divider at any tested corner (#36 — since **repaired and re-verified** by
#112; the closed loop re-run against the repaired chain by #159 — nominal
corner only — **does not acquire**: the in-loop divider counts 128 VCO edges
per FB period instead of 64, `sg13cmos5l-closed-loop-real-divider` RECORD-001),
and even the mitigated proposal loop
holds a static phase error of 8.203% of a reference period against this
campaign's own 5% threshold. Challenge #6's full sign-off bar (schematic +
pre-layout sim → layout + post-layout sim over PVT → DRC/LVS-clean GDS,
open-source-EDA-verifiable) is **not met**, on measured evidence rather
than on missing testbenches. Every spec row below is re-derived directly
from the `sim/`/`layout/` evidence that exists today, as of
`origin/main @ 8769948` (2026-10-03); any row that
evidence cannot bound is marked `insufficient-evidence` rather than
relaxed to pass, per this repo's own `CLAUDE.md`. **This is the
post-siblings re-derivation pass** (#112 divider fix, #113 `vco` LVS
root-cause, #114 MOM-cap layout, #115 remaining post-layout arms and #136
final LVS repair are all closed as of this writing; the still-open items —
#100 representative floorplan, #139 owed full-PVT lock-detector grid, the
post-layout retiming margin and the post-repair closed loop (#159: no lock at the nominal corner) — are named in
the rows they bound). Older records that predate those landings are cited
below as dated historical observations, with the later changes that
supersede or bound them stated each time.

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
  DR-005). **As originally ported it was functionally defective — and is
  now repaired**: `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-001`
  (issue #36) measured the as-committed chain failing to function as a
  divider at **any of 9 tested corners** (its `dff_tg_hv` hold path is a
  self-biased inverter, not a real latch). #112 (merged via PR #121)
  repaired `dff_tg_hv.sch` against the proven fleet topology — the missing
  second feedback inverter per latch (`XIMF`/`XISF`) and the missing second
  local clock phase (`XICKBB`) with the gf180-pll `dff_tg_3v3` gate
  staggering — and `RECORD-003` re-verified the committed repair:
  `N = 64.000` exact at 9/9 PVT corners, every code-sweep word exact to
  three decimals, `N = 127.000` at both bracket extremes, latch hold 9/9
  at the rail. The top-of-band retiming margin at 1562.0 MHz remains
  unmet for this sizing (one-edge capture fails; `t_setup` alone is
  0.8–2.3× `T_vco`) — see section 4 row 3.
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
signature change** — the bulk of the design's devices — because
SG13CMOS5L ships the identical SG13G2 CMOS device models under a
differently-named symbol-library path only. The five `cap_cmim` → MOM-cap
substitutions (`loop_filter` ×2, `vco` ×1, `lock_detector` ×2) are the
single largest schematic-port risk, because the PDK's own `cap_cmomi`/
`cap_cmomf` models are **not validated on CMOS5L silicon** and carry no
characterized process-corner or mismatch spread — every spec row sensitive
to these five instances' precision is flagged `insufficient-evidence`
below unless a real sensitivity sweep bounds it (section 4). As of
#114/#119 all five MOM caps are **drawn** in the layout (DRC-clean,
extracting as `cap_cmomi` at the schematic's own `w`/`l`), so the current
layout record reports **569/569 devices drawn** where the pre-#114 records
reported 485/490 — but the *model*-validation risk is unchanged by
drawing them: it is a PDK characterization gap, not a layout gap.

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
| 1 | Output band | **Insufficient-evidence for a ratified target — and now bounded from both sides.** Schematic level: an open-loop `vco` transient sweep measures oscillation from 445.3 MHz (`slow` bundle, any band, `VCTRL=0.3V`) to 1562.0 MHz (`fast` bundle, band `11`, `VCTRL=2.7V`) across the swept 60-point matrix (open-loop only). Post-layout (#30/#101): re-extracted PEX netlists of the *routed* `vco` measure **347.6–1182.8 MHz** (mean per-point deviation −22.6%; −49.3% / 223.7–789.5 MHz before #101's floorplan pass cut that block's routed wire 7178 → 3913 µm), ~99% of the original deviation attributed by a 7-variant diagnostic to parasitic *capacitance*. Every post-layout number here is an **upper bound set by routing style, not a floorplan prediction** (the coefficients are uncalibrated public-data starter values). Two dated caveats: those numbers were measured on the RECORD-002-era layout, whose `vco` LVS stood at 44/45 with the MoM decap undrawn; #113 has since closed the topology match (45/45 devices, 33/33 nets, schematic-side body-tie fix, `pll_vco.gds` byte-identical) and #114/#119 drew the decap — but **no PEX/PVT re-run of the `vco` arm against the cap-complete layout exists**, so the quoted band remains the pre-decap measurement | `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md`; `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md`, `RECORD-002-floorplan-aware-vco-route.md`; `layout/sg13cmos5l-pll/reports/20261003-183059-dc5644a/record.md` |
| 2 | Reference input | **Insufficient-evidence for the electrical levels; the frequency range is re-derived and amended.** DR-005 (issue #40) reconciled the ported `f_ref = 1–25 MHz` with the measured VCO band and amended row 2 to **`f_ref ≈ 3.51–24.4 MHz`** (floor 445.3 MHz/127, ceiling 1562.0 MHz/64) alongside row 3's `N ∈ [64,127]`; the interface *shape* (CMOS square wave, rising-edge, 30–70% duty) is unchanged. No dedicated `V_IL`/`V_IH` duty-cycle testbench exists for the `pfd` itself. What *is* now measured: the as-drawn `pfd` carried a real functional defect (self-reset inverter parity, #50/#56 — found in the closed loop, fixed, LVS re-verified); and the post-layout PEX `pfd` (LVS-matched, #102) stretches every internal arc by a flat **+0.53 ns** (benign, +9.3% duty at the ratified 10%-of-period REF-lead offset) but **inverts its phase discrimination on the FB-leading side at 20 MHz** (UP holds `(T_ref − τ + 0.2 ns)`, DN never holds — a genuine steady mode, node-level traced to slowed input→latch edges) | `spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md`; `sim/sg13cmos5l-closed-loop-lock/records/RECORD-002-pfd-reset-parity-root-cause.md`, `RECORD-003-pfd-reset-fix-closed-loop-rerun.md`; `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` §2 |
| 3 | Multiplication ratio (N) | **Functional-N: now met, measured, after repair. Top-of-band retiming margin: still unmet, with a numeric bound.** The as-committed chain originally **failed functionally**: `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-001` (issue #36, closed) measured the as-ported chain not functioning as a divider at any of 9 tested corners — its `dff_tg_hv` hold path was a self-biased inverter, not a real latch (0/9 corners hold at the rail; DC operating point never converged). **#112 (closed, merged via PR #121) repaired `dff_tg_hv.sch`** — the missing second feedback inverter per latch plus the missing second local clock phase, both deviations from the gf180-pll `dff_tg_3v3` topology — and `RECORD-003` re-verified the committed repair: `N = 64.000` exact at 9/9 PVT corners, all 9 code-sweep words exact to 3 decimals (65…127, mixed words included), `N = 127.000` at both bracket extremes (`mos_ss`/125 °C, `mos_ff`/−40 °C), latch hold 9/9 at the rail, operating point converging. DR-005's amended **`N ∈ [64,127]`, no holes** is therefore now measured, not structural-only. **Post-layout (RECORD-004, Matrix G): the extracted chain divides correctly at every measured point** — baseline `000000` 64.0005/63.9998/64.0004 across the 3-bundle bracket (≤10.9 ppm from the schematic control), every word of the 9-word sweep exact (max 4.6 ppm), ceiling `111111` exact at both bracket extremes — on an LVS-matched 394/394-device extraction (14-point reduction of the 20-row matrix; dropped OFAT axes still covered on the control arm). **Retiming margin at the measured top-of-band 1562.0 MHz remains unmet for this sizing**: one-edge (`k+1`) capture fails at every resolved corner (7/9), stable one-period-late (`k+2`) capture is observed, and `t_setup` alone is 0.5–1.5 ns = 0.8–2.3× `T_vco`; no post-layout retiming arm exists (a single 1562 MHz post-layout transient exceeds the session compute budget several times over — RECORD-004 §5) | `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-001-nrange-retiming-margin.md`, `RECORD-003-divider-repair-reverification.md`; `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-004-postlayout-pex-pvt-loop-filter-and-divider-chain.md` §3; `spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md` |
| 4/5 | Kvco bound / band-selection rule | **Met (bounded), pre-layout; post-layout re-measured (an upper bound).** A real, PVT-cornered (3 process×temperature bundles × 4 band codes × 5 `VCTRL` points, 60 runs), per-band, open-loop Kvco table exists; `Kvco` is measurably non-constant across the sweep (e.g. `typ`/band `00`: 173.8 MHz/V averaged vs. 206.0 MHz/V at the top of the range, ~19% difference) — a real nonlinearity, not noise, consistent with the row's own "table, not a scalar" framing. Band select is inert at low `VCTRL` (all four band codes read the identical frequency at `VCTRL=0.3V`) and dominant at high `VCTRL` (~2.8× spread at `VCTRL=2.7V`). Post-layout (#30): the PEX `vco` runs at 0.4768–0.5312× its schematic frequency at 60/60 points (band 223.7–789.5 MHz as first routed; 347.6–1182.8 MHz after #101's floorplan pass) — the Kvco *table's shape* survives, its absolute numbers do not, bounded by routing style (row 1's caveats). The `cp` trim ladder that would re-anchor the loop's gain post-layout survives to +0.055..+0.632% (UP) / +0.017..+0.211% (DN) over its full 306-point PVT matrix | `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md` (full 12-row table below); `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-001` §vco, `RECORD-002` |
| 6/6a | Loop bandwidth / phase margin | **Measured, and the story is a fix chain with a residual coverage gap — not a pass as first drawn.** The row's own kHz/degree numbers now exist end-to-end: with the **as-drawn** filter, `f_c` = 0.33–4.64 MHz and PM = 1.55–20.33° across 90 real-subckt AC runs — **0 of 90 meet the ≥45° criterion**, and no trim code trades one criterion against the other (`sg13cmos5l-loop-bandwidth-pm` RECORD-001). #41 therefore resized `R1` ×44.2 (DR-006, committed); against the **full DR-005-amended `f_ref` range** (both bands, three Kvco intervals, 426 runs) the resized filter meets both criteria (`f_c < f_ref/10`, PM ≥ 45°) at 16 of 30 (band, interval, `f_ref`) combinations with full 3-bundle coverage, at 12 more with only 1–2 of 3 PVT bundles simulated (a *coverage* gap, passing at every bundle actually run), and failed 2 outright — both since **closed by fine Icp-trim codes** (#83: 3.75 µA, DR-007; #79: 11 µA, DR-008, PM 45.6°/49.0°/53.5° at fast/typ/slow with `f_c` ≤ 435 kHz against the 450 kHz ceiling). The 12 partial-PVT-coverage combinations remain open as future work. **The post-layout `loop_filter` arm now exists** (#115 closed; `sg13cmos5l-postlayout-pex-pvt` RECORD-004, Matrix F, on the LVS-matched 3/3-device extraction): the deviation is capacitance-dominated and corner-flat (±0.15% across all 9 res-corner × temp combinations) — `Ctot′` +39.6% (1.7914 → 2.5009 pF), `C2′` +92.4%, `fz′` **−19.1%** (295.4 → 238.8 kHz) and `fp′` **−41.4%** (4.348 → 2.550 MHz) at typ/27 °C, both shifts in the direction that slows loop settling; the extraction's physical series-R addition is ≤ +2.0% (the −8.9% plateau reading is a measurement-compression artifact the record bounds), and temperature flatness holds on both arms (Ctot′ spread 0.0000%). Over the ±20% MOM band at typ/27 °C the schematic control spans `fz` 246.2–369.3 kHz / `fp` 3.624–5.436 MHz, the post-layout arm `fz` 199.0–298.6 kHz / `fp` 2.125–3.188 MHz. (An earlier sentence here quoted "nominal `fz` = 12.07 MHz, 27-corner 8.97–16.92 MHz" — that was the **pre-#41-resize** filter's spread from `sg13cmos5l-loop-filter-momcap` RECORD-001, measured at the as-drawn `R1` ≈ 7.79 kΩ; it never described the committed resized filter and is retained here only as the historical observation it was. The committed filter's own spread is the resized-R1 set above; no row-6a `f_c`/PM re-derivation against the post-layout `fz′`/`fp′` has been run, so the 426-run AC numbers remain pre-layout) | `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-001-loop-bandwidth-phase-margin.md`, `RECORD-002-r1-resize-full-fref-range.md`, `RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`, `RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`; `sim/sg13cmos5l-loop-filter-momcap/records/RECORD-001-rc-corner-momcap-sensitivity.md`; `sim/sg13cmos5l-cp-icp-trim/records/RECORD-003-issue83-finetrim-icp.md`, `RECORD-004-issue79-finetrim-icp.md`; `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-004-postlayout-pex-pvt-loop-filter-and-divider-chain.md` §2; DR-006/DR-007/DR-008 |
| 7 | Lock time | **Fails — measured, not merely missing; the failing evidence is the Part B deck, whose divider is behavioural and therefore unaffected by #112's repair.** A real transistor-level closed loop (all six subckts, testbench-local wiring — no `pll_top` exists; single PVT point `mos_tt`/`res_typ`/27 °C, 20 MHz/`N`=64/band `11`, runtime-cost subset) exists with five records, all run 2026-08-30 or earlier — before #112's divider repair merged (PR #121, 2026-09-22) — and every record's frozen `divider_chain` snapshot is the pre-repair one. Part A (as-committed blocks, pre-repair) never locked: `FB` never crossed the logic threshold (the row-3 divider defect, since repaired by #112), `n_ref_cycles_observed = 0`, `lock_time = None` — **a historical observation now; a nominal-corner re-run against the repaired chain now exists (#159, `sg13cmos5l-closed-loop-real-divider` RECORD-001) and it does not lock**: the repaired `divider_chain` in the loop counts 128 VCO edges per FB period (not 64; `vctrl` rails at ~3.24–3.31 V, `f_vco` ≈ 1.405 GHz, `f_fb` ≈ 10.98 MHz, dual-lock run 0), while the unchanged behavioural-divider control reproduces the ~8.3% static phase error. A divider-alone check with an ideal clock gives 64 edges at 200 and 640 MHz but 96 at 1.28 GHz, so the exact-N result measured at 100 MHz does not carry to the loop's operating frequency (nominal, pre-layout, 3-point bracket; root cause not isolated; no PVT). Part B (a *proposal* deck — resized filter + behavioural divide-by-64, both then-known defects deliberately set aside) **frequency-locks** after the #56 `pfd` fix (`Δf`/`f_ref` within 0.03% held for a full microsecond, zero cycle slips) but settles at a stable static phase error of **9.176%** of a reference period — 1.8× this campaign's own 5% dual-lock threshold (`|Δf/f_ref| < 1%` AND phase error < 5%, ≥20 consecutive cycles); longest dual-lock run 4 cycles. An ideal-cp diagnostic (#70) collapses the residual to −0.00235% (numerical noise) and extends the dual-lock run to 41 cycles (lock_time 450 ns) — confirming current mismatch as *a* dominant mechanism — and the real mitigated `cp` (#72) then cuts the DC mismatch 20× but the closed-loop residual only to **8.203%**, with the longest dual-lock run still 4 cycles and `lock_time = None`: the best-fitting remaining candidate is switching/dynamic charge mismatch, which no diagnostic has yet isolated. **Row 7 therefore still fails for the mitigated design — on Part B evidence that does not depend on the divider, and now also with the repaired divider in the loop (#159, nominal only)** | `sim/sg13cmos5l-closed-loop-lock/records/RECORD-001-closed-loop-lock-spur-power.md` … `RECORD-005-cascbias-real-cp-static-phase-error-rerun.md` (all five) |
| 8 | Period jitter | **Insufficient-evidence for the absolute number.** `vco.XCDECAP`'s own capacitance is bounded (nominal **5.2862 pF**, matching `design/README.md`'s "~5.29 pF" placeholder to 4 figures) and its fractional supply-decoupling pole-frequency sensitivity to the ±20% MOM band is bounded (illustrative `R_src=3kΩ`: 12.54 MHz / 10.03 MHz / 8.35 MHz at −20%/0%/+20%, a 1.502× span matching the exact analytic `1/0.8 : 1/1.2` prediction). A post-layout parasitic source impedance **now exists** (routed layout + `klt extract --parasitics` with real curated metal R/C coefficients, #30) — retiring the original "no post-layout parasitic source impedance" half of this row's caveat — but it is an upper bound set by the un-representative floorplan with uncalibrated coefficients, and the absolute jitter-as-percent-of-period number still cannot be computed: ngspice has no direct phase-noise computation for a free-running oscillator (a pre-existing flow limitation, not an SG13CMOS5L-specific one — see row 9) | `sim/sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md`; `sim/sg13cmos5l-postlayout-pex-pvt/` (extraction provenance) |
| 9 | Integrated RMS jitter / phase noise | **N/A, carried as-is** — deliberately not spec'd. This is a flow limitation (ngspice has no `.noise` path for a free-running oscillator), sourced from gf180-pll's own `DR-002` Decision 5, not this repo's own DR-002 (which has no Decision 5) — applies identically on SG13CMOS5L since it is tool-, not PDK-, dependent | `spec/porting-plan.md` row 9 (citing gf180-pll `DR-002` Decision 5) |
| 10 | Reference spur | **Insufficient-evidence — for a different, now-measured reason: the loop never phase-locks, so there is no stable locked carrier to define a spur around.** The original deferral (no charge-pump mismatch data, no closed-loop steady state) is retired: the DC mismatch data is real (`sg13cmos5l-cp-icp-trim` RECORD-001/RECORD-002: −3.17% at `mos_tt`/27 °C as drawn; worst-case 10.28% → 0.72% over the full PVT/`VOUT` matrix after #72's mitigation), and the closed-loop decks ran Goertzel-DFT spur extraction on their own `vctrl` waveforms (~−39.7/−36.0 dBc) — **deliberately not reported as row-10 measurements**, because a frequency-locked-but-not-phase-locked loop (row 7's 8.2–9.2% static phase error) has no settled carrier for a dBc figure to reference. A real spur number additionally needs the switching charge mismatch and PFD reset window, both still unmeasured | `sim/sg13cmos5l-closed-loop-lock/records/RECORD-001` ("Row-by-row disposition"), `RECORD-003`, `RECORD-005`; `sim/sg13cmos5l-cp-icp-trim/records/RECORD-001-icp-trim-and-mismatch.md`, `RECORD-002-cascode-bias-mismatch-remeasure.md` |
| 11 | Power | **Bounded — real, simultaneous, explicitly non-clean numbers; the divider inflation is now historical, and the repaired divider has its own measured (post-layout ×3.7) cost.** The five-domain whole-PLL figure — **≈ 10.137 mA (33.45 mW at 3.3 V), of which the `divider_chain` domain alone was 7.653 mA (25.26 mW)** — was measured in one closed-loop deck at one (non-locked) operating point, `mos_tt`/27 °C, against the **pre-#112 defective divider** (gf180-pll's *entire* PLL draws under 5 mW); the record itself flagged it as very likely inflated by that block's malfunction. Excluding the defective divider, the other four domains totalled **2.483 mA (8.20 mW)**. **The repaired divider's own numbers are now measured** (#112 re-verification + RECORD-004): schematic-level `idd` ≈ 226 µA at the 100 MHz baseline (control arm, 20/20 committed rows reproduced byte-identically), and **post-layout 809–862 µA (+262…+276%)** on the LVS-matched extraction — 16.34 pF of extracted substrate capacitance on the chain's 181 nets makes the routed block's dynamic current ≈3.7× its schematic value, a routing-style bound, not a prediction. **No whole-PLL re-run with the repaired chain exists** — the closed-loop records all predate PR #121 — so a clean simultaneous total remains unmeasured. Per-domain: `vco` 3.09–8.88 mW standalone across PVT (`sg13cmos5l-vco-duty-cycle`) — the VCO **alone already exceeds gf180-pll's whole-PLL figure**, reaffirming row 11's "no V² rescale" disposition; mitigated `cp` −39.26 µA in-loop (up from −24.66 µA, a supply-bookkeeping change DR-006 itself predicted); `lock_detector` 2.48–113 µA (10×-window probe) post-#76 per `sg13cmos5l-lock-detector-window` RECORD-004, whose full-PVT bound **remains that record's** — RECORD-005 (#136's body-tie fix) re-measured only the nominal corner, byte-identically (2.877/62.25 µA in-lock/out-lock), with the changed-DUT full grid owed (#139) — and 6.8–15.7 µA in-lock @3.5 MHz / 93.3–99.7 µA @24.4 MHz as-routed post-layout (#102, measured on the pre-#114/pre-#136 layout) | `sim/sg13cmos5l-closed-loop-lock/records/RECORD-001` (row-11 disposition), `RECORD-003`, `RECORD-005`; `sim/sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md`; `sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-003-divider-repair-reverification.md`; `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-003` §3.4, `RECORD-004` §3; `sim/sg13cmos5l-lock-detector-window/records/RECORD-005-rpu-body-on-vss.md` |
| 12 | Supply sensitivity | **Insufficient-evidence for the absolute mV-ripple/dB-attenuation budget.** A post-layout parasitic source impedance now exists (row 8's update — real extracted R/C, #30) but is bounded by routing style and uncalibrated coefficients, and there is still no direct small-signal method for the ring's own unstable DC operating point. The fractional MOM-band-to-pole-frequency sensitivity is bounded (row 8's own 1.502× span) | `sim/sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md`; `sim/sg13cmos5l-postlayout-pex-pvt/` (extraction provenance) |
| 13 | Output duty cycle | **Measured — and the 45% floor is not met at the cold corner.** The original gap (the Kvco record's single-edge methodology, `mos_sf`/`mos_fs` corners unswept) is retired by a dedicated 300-run campaign (5 MOS corners *including* the split corners × 3 temps × 4 band codes × 5 `VCTRL` points, rising *and* falling 50%-of-rail crossings): duty cycle spans **43.74–51.56%**, with **30 of 300 points below the 45% floor — every one at −40 °C** (worst 43.74%, `mos_fs`, `VCTRL=0.3 V`). No point exceeds the 55% ceiling. The record carries this forward as a real design flag reproducing gf180-pll's own duty-cycle finding on a different process, not as a measurement artifact | `sim/sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md` |
| 14 | Output levels / drive | **Insufficient-evidence** — no waveform-into-a-defined-load (V_OH/V_OL vs. ≤50 fF) measurement has been run against any SG13CMOS5L block yet (the post-layout `pfd` duty-space arm of #102 measures pulse widths, not output levels into a specified load) | none |
| 15 | Area | **Insufficient-evidence** — no top-level layout, floorplan, or composed `pll_top` exists to measure an area figure from. The device-level layout is now **routed and complete** (6/6 blocks composed and wired, **569/569 devices drawn** since #114/#119 drew the five MOM caps, 295 nets, ≈269.7 mm of drawn routing wire of which `divider_chain` alone is 234.5 mm — layout record `20261003-183059-dc5644a`; the pre-#114/#121 records' "485/490 drawn, 167 mm" figures are their own era's, kept only as history), and the composition is explicitly *not* a considered floorplan (single-row placement, no matching, no folding; a representative analog floorplan is unowned — #100, operator-blocked) | `layout/sg13cmos5l-pll/reports/20261003-183059-dc5644a/record.md`; `layout/sg13cmos5l-pll/README.md` ("What it is not") |
| 16 | Lock-detector targets | **Schematic: all three measurable criteria PASS — after three design passes, with the #136 body-tie fix re-verified at the nominal corner only (full grid owed, #139). As-routed: the historical fail-all-three measurement predates the drawn caps and the #136 footprint repair; the current layout LVS-matches 41/41 but its row-16 criteria have not been re-measured post-layout.** The original campaign (#38) measured the as-drawn block failing window (0.219–0.409 ns vs ≥2.5 ns), hysteresis (none resolvable vs ≥25% of window) and chatter (92/92 points) at every corner — root cause: the integrating node's R·C was 23–1412× *below* the reference period. #52 resized `XRPU`/`XCW`/`XDW.XC1` (window and no-chatter now pass); #66 re-tied `schmitt_hv`'s feedback devices and resized `XMPD` (hysteresis now passes: **50–800% of window, 0 of 21 corners below the ≥25% criterion**); #76 lengthened `schmitt_hv`'s channels for crowbar current (3.2–4.3× lower, criteria re-verified unchanged in substance). Final schematic state per `sg13cmos5l-lock-detector-window` RECORD-004 (the full-PVT evidence): window **3.688–11.24 ns at 102/102 points** (worst case 1.475× the floor), `steady` at **21/21** ladder corners at a 20×-window static phase error, R·C = 8.0–19.5× the slowest reference period (6.4–23.4× with the ±20% MOM band). #136's LVS body-tie repair (`XRPU` bulk on `VSS`) changed exactly one netlist line; RECORD-005 re-measured it at the **nominal corner only** — every reduced row byte-identical to RECORD-004 — on the argument that both bulk nodes are an ideal 0 V in every deck (an argument, not measured evidence); the changed-DUT **full-PVT grid is owed (#139, open)**, blocked on `klt sim`'s batch backend refusing the `sg13cmos5l` family (klayout-tools#2727), so the full-PVT verdicts remain RECORD-004's, carried over, **not re-measured**. The "≥ 2× worst static phase offset" half stays `insufficient-evidence` (needs the phase-error distribution a locked loop would produce — row 7). Post-layout (#102, RECORD-003 §3 — a **dated observation on the pre-#114/pre-#136 layout**): the then-as-routed cell **failed all three criteria on both arms** — window 0.21–0.36 ns as-layout / 0.34–0.60 ns post-layout across 29 PVT points, chatter at every 3.5 MHz ladder point up to 10× the window — because its two MOM caps were then undrawn (1.691 pF + 3.382 pF vs ~71 fF of extracted VWIN parasitic capacitance) and `XMPD`'s contacts were then missing. Since then #114/#119 drew and matched all three capacitor units and #136 fixed the footprint; the current record reports `lock_detector` **`match` 41/41 devices, 23/23 nets** — but **no post-layout PEX re-run of the row-16 criteria exists against the cap-complete, contacted layout**, so the as-routed row-16 status is *unmeasured*, not pass | `sim/sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md` … `RECORD-005-rpu-body-on-vss.md` (all five); `sim/sg13cmos5l-postlayout-pex-pvt/records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` §3; `layout/sg13cmos5l-pll/reports/20261003-183059-dc5644a/record.md` |
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
| Schematic + pre-layout sim | **Partial — the missing testbenches now exist, and two of the rows they measure fail.** Schematic captured for all six blocks (#22, PR #26, DR-003/DR-004 ratified) and since revised on measured evidence (`pfd` #56, `loop_filter` R1 #41, `cp` #72, `lock_detector` #52/#66/#76, `divider_chain` #112, `vco`/`lock_detector` body ties #113/#136). The originally-deferred pre-layout campaign has run in full: a real PVT-cornered Icp-trim/mismatch table (#27), loop bandwidth/phase margin across the amended `f_ref` range (#27/#41/#83/#79 — criteria met at the resized filter with named trim codes, 12 of 30 combinations with partial PVT coverage), duty cycle (#27 — 45% floor fails at −40 °C), lock-detector window/hysteresis/chatter (#38/#52/#66/#76 — all three schematic criteria pass; #136's body-tie re-verified nominal-only, full grid owed #139), divider N-range (#36 measured the as-ported chain failing at every tested corner — **repaired by #112 and re-verified exact across `N ∈ [64,127]`**, top-of-band retiming margin still unmet), and a real transistor-level closed loop (#37 + #50/#56/#70/#72, five records — **row 7 fails**: no deck acquires the campaign's dual lock criterion; the mitigated proposal loop holds an 8.203% static phase error, and the nominal-corner closed loop with the repaired divider does not acquire — #159). |
| Layout + post-layout sim over PVT | **Partial — routed and post-layout-simulated on all six blocks, every number bounded by routing style.** All six blocks are composed **and routed**, `klt drc --deck sg13cmos5l` clean at zero violations on every routed cell (#24 → #29; re-run after each design revision, #56/#72/#112/#114/#136). `klt extract --parasitics` works with real curated metal R/C coefficients (klayout-tools#1440 closed via #2012; #2113 closed via #2126), and the ratified PVT matrices were re-run against parasitic-annotated netlists with schematic-level control arms for `vco` and `cp` (#30, PR #99), `vco` again after a floorplan-aware re-route that cut its wire 7178 → 3913 µm and its frequency deviation −49.3% → −22.6% (#101), `pfd` + `lock_detector` (#102), and — closing the set — `loop_filter` + `divider_chain` (#115, RECORD-004, both on LVS-matched extractions). Headline post-layout findings: `vco` runs at ~0.48–0.53× its schematic frequency (~99% parasitic capacitance; upper bound set by routing style, not a floorplan prediction; measured pre-drawn-decap — row 1); the `cp` trim ladder survives to ≤0.632%; the `pfd` gains +0.53 ns on every internal arc and **inverts its FB-leading phase discrimination at 20 MHz**; the `loop_filter`'s `fz′`/`fp′` shift −19.1%/−41.4% (capacitance-dominated, corner-flat); the repaired `divider_chain` divides **exactly at every measured post-layout point** (≤10.9 ppm) while its dynamic current triples (+262…+276%); the `lock_detector`'s row-16 fail-all-three measurement is a pre-#114/#136 historical observation whose re-run is still missing (row 16). A representative analog floorplan remains unowned (#100, operator-blocked) — the bound every one of these numbers still carries. |
| DRC/LVS-clean GDS, in-repo, open-source-EDA-verifiable | **DRC-clean on all six routed blocks; LVS `match` on all six, as of layout record `20261003-183059-dc5644a` (2026-10-03, #136's re-run): 569/569 devices drawn, 569/569 DRC-clean, 6/6 composed and routed (295 nets), 6/6 `klt lvs` `match` — `pfd` 66/66+37/37, `cp` 20/20+18/18, `loop_filter` 3/3+4/4, `vco` 45/45+33/33, `divider_chain` 394/394+181/181, `lock_detector` 41/41+23/23.** This was not always so, and the history is load-bearing: three blocks originally could not be converted at all (klayout-tools#1463, `cap_cmomi` had no capacitor device class in the reference conversion path), and #30's separately-recorded LVS re-check then showed `loop_filter` mismatching 0/3 (both MOM caps undrawn) and `vco` mismatching 38/45. #114/#119 closed the capacitor half end to end (all five `cap_cmomi` drawn, DRC-clean, extracting at the schematic's own `w`/`l`, LVS-matched through the caller-side reference rewrite that also retired the `m=2` plain-element limitation); #113 closed `vco`'s remaining six-resistor + one-merged-net mismatch as a **schematic** body-tie defect (`XBIAS` resistor bodies re-declared on `VSS`, `pll_vco.gds` byte-identical); #136 closed the last residual, `lock_detector`'s, which its own diagnosis showed was **two independent defects** — the `PU`/`SUB!` schematic substrate split (`XRPU` bulk re-declared on `VSS`, nominal-corner functional re-check byte-identical per `sg13cmos5l-lock-detector-window` RECORD-005, full grid owed #139) and an open `XMPD` device in this flow's own narrow-MOS footprint (both diffusion terminals uncontacted below `w=0.3 µm`; fixed with dog-bone heads, filed upstream as klayout-tools#2726 because DRC could not see it). Block-level LVS is therefore clean; what LVS-clean does *not* establish: no composed top-level `pll_top` exists (section 2), the composition is not a considered floorplan (#100), and the whole-PLL rows 7/8/9/10/12/14 above remain unmet or `insufficient-evidence` on their own evidence. |

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
capacitor device class — **closed and retired for this port by
#114/#119**: the deck now carries `mom_capacitors` for `cap_cmomi`/
`cap_cmomf`, all five devices draw, extract at the schematic's own `w`/`l`
and LVS-match through the reference rewrite; the successor gap is
[#2327](https://github.com/2AMLogic/klayout-tools/issues/2327) — a
custom-device-class `X … PARAMS:` card still cannot pass through
`reference.form: "subckt-call"` in one request, worked around caller-side
— open; and
[#1464](https://github.com/2AMLogic/klayout-tools/issues/1464) (resistor
device_map — **closed and retired** by #114's run, whose references pass
no `device_map`),
[#1467](https://github.com/2AMLogic/klayout-tools/issues/1467)
(`gen-compose` routes 1 of 13 nets on a block this size — open, re-probed
every run; the current record's own probe measures **2 of 18** multi-pin
nets on `cp` at this repo's pin),
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
`pex-to-ngspice.py`),
[#2145](https://github.com/2AMLogic/klayout-tools/issues/2145)
(hierarchical net names joined with `.` collide with ngspice's own
separator — open, same workaround),
[#2355](https://github.com/2AMLogic/klayout-tools/issues/2355)
(extracted `cap_cmomi` cards carry bare-micron `PARAMS: W= L=` values
against the PDK subckt interface's SI-meter defaults — silent at DC, an
effectively-shorted capacitor at AC; worked around in `pex-to-ngspice.py`
— filed from RECORD-004),
[#2726](https://github.com/2AMLogic/klayout-tools/issues/2726)
(DRC cannot see a `Via1` landing on no `Metal1` at all, and the deck
reads no `Cont` rule — this hid #136's uncontacted 0.25 µm `XMPD` for
three records; the footprint now raises on uncontacted terminals), and
[#2727](https://github.com/2AMLogic/klayout-tools/issues/2727)
(`klt sim`'s batch/remote backends refuse the `sg13cmos5l` family, so a
full-PVT SPICE grid cannot be submitted to the batch fleet — the reason
the owed #139 changed-DUT grid has not simply been run — filed from
`sg13cmos5l-lock-detector-window` RECORD-005).

The brief's full sign-off bar requires all three stages, unconditionally
clean. None of the three is fully met today. This document should be read
as reporting real, PVT-cornered (explicitly subsetted where runtime cost
forced it — each record's own `corners/matrix.md` says where) verification
evidence with every gap disclosed, not as a completed Challenge #6
submission.

### Parent issue #16 — criterion-by-criterion review (recorded per #137)

#16's three original acceptance criteria, reviewed separately. Closing
this and the other children does **not** imply parent sign-off; #16 stays
open — its sign-off bar is criterion 2, and criterion 2 is unmet.

1. **Proposal document with block type, slot-budget I/O mapping,
   functional description, and a spec table re-derived from `sim/` at the
   ratified rails, unmet rows explicitly marked and never relaxed —**
   **met** as of this refresh (this document, re-derived against
   `origin/main @ 8769948`, 2026-10-03). The never-relaxed property is
   load-bearing and intact: rows 7 (lock time) and 13 (duty cycle at the
   cold corner) are recorded as failing, and every unbound row carries
   `insufficient-evidence` rather than a guess. The document has needed
   two refresh passes (#116, then #137) to stay current — a living
   obligation, not a one-time deliverable.
2. **Design at the brief's sign-off bar — post-layout PVT simulation and
   DRC/LVS-clean GDS in-repo, open-source-EDA-verifiable —**
   **partial, and the gap is now sharply bounded.** Met in its parts:
   DRC clean on all six routed blocks; LVS `match` on all six (record
   `20261003-183059-dc5644a`, 569/569 devices, closing the chain
   #114 → #113 → #136); post-layout PEX+PVT arms with control arms exist
   for all six blocks (RECORD-001/002/003/004). Unmet in its whole: the
   composition is not a representative floorplan, so every post-layout
   number is an upper bound by routing style, not a sign-off prediction
   (#100 open, operator-blocked); no composed `pll_top` exists at all;
   row 7 fails on measured evidence (8.203% static phase error; and with the repaired divider in the loop,
   nominal corner, the loop does not acquire — #159); the lock-detector's
   changed-DUT full-PVT grid is owed (#139, blocked upstream on
   klayout-tools#2727); the divider's top-of-band retiming margin has no
   post-layout arm; rows 8/9/10/12/14 remain `insufficient-evidence`.
   Block-clean is not chip-clean.
3. **Cross-links to `docs/pdk/sg13cmos5l.md` and 2am#542 —** **met**
   (section 1 and References; preserved through this refresh, along with
   the DR-001…DR-008 ratified rail/I/O/spec decisions).

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
   whole-PLL simulated proxy (10.137 mA, 7.653 mA of it the then-defective
   divider) predates the #112 repair and has not been re-run: the repaired
   chain's own measured cost is ≈226 µA schematic / 809–862 µA post-layout
   at the 100 MHz baseline, and a clean simultaneous whole-PLL total
   remains unmeasured.
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
  #40, #41, #50, #52, #56, #66, #70, #72, #76, #79, #83, #101, #102 —
  and the siblings this pass re-derives against, all now closed:
  **#112** (divider fix, PR #121), **#113** (`vco` LVS mismatch
  root-cause, PR #123), **#114** (MOM-cap layout, PR #119), **#115**
  (`loop_filter` + `divider_chain` post-layout arms, RECORD-004),
  **#136** (`lock_detector` LVS repair, PR #138). Still open and bounding
  rows above: **#100** (representative floorplan, operator-blocked) and
  **#139** (the owed changed-DUT full-PVT lock-detector grid,
  `loom:triage`, blocked upstream on klayout-tools#2727).
