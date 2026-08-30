# DR-006: `cp` carries its own high-swing cascode bias replica; `IBP`/`ICP`/`IBN`/`ICN` become current inputs

- **Status**: proposed
- **Date**: 2026-08-30
- **Decided by**: Builder agent, issue #72
- **Related**: #16 (parent, epic), #72 (this issue), #70 / `RECORD-004`
  (the diagnostic that bounded the mechanism and asked for this mitigation),
  #56 / `RECORD-003` (the closed-loop run whose ≈9.18% static phase error
  this addresses), #27 / `RECORD-001` (the Icp-trim/mismatch baseline),
  DR-001 Decision 1 and DR-002 Decision 2 (the CMOS wide-swing cascode this
  record makes actually operate), DR-002 Decision 1 (bias *reference*
  deferral — **not** reopened, see "Relationship to DR-002 Decision 1")
- **Consumes**: `spec/porting-plan.md` §1.4 row "Charge pump" ("Wide-swing
  cascode output stage for compliance-range headroom" — ported as-is, not
  amended here); `sim/sg13cmos5l-cp-icp-trim/records/RECORD-001-…` and
  `RECORD-002-…`; `sim/sg13cmos5l-closed-loop-lock/records/RECORD-003-…`,
  `RECORD-004-…` and `RECORD-005-…`;
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-…`;
  `2AMLogic/gf180-pll` `design/cp.sch` (the sibling design this ports from)

---

## Context

`spec/porting-plan.md` §1.4 ratifies a **wide-swing cascode** charge-pump
output stage as a technique that ports as-is, and `design/sg13cmos5l/`'s
`cp_leg_p.sch` / `cp_leg_n.sch` headers both claim it. **The port did not
actually deliver it.** `gf180-pll`'s own `cp.sch` contains four in-block
bias diodes (`MBN`/`MCN`/`MBP`/`MCP`) that generate the two *distinct* gate
voltages a wide-swing cascode needs; the SG13CMOS5L port dropped them and
exposed `IBP`/`ICP`/`IBN`/`ICN` as bare **voltage**-input pins with nothing
behind them.

A voltage-input pin pair driven from one reference can only be tied
together, and every testbench in this repo does exactly that
(`IBP` = `ICP`, `IBN` = `ICN`). Two same-size devices in series with a
common gate cannot both saturate — the one nearer the rail is forced into
triode — so each leg silently degenerates into a **simple** mirror of
effective length `L1 + L2`, with no cascode and no output-impedance benefit.
`sim/sg13cmos5l-cp-icp-trim/records/RECORD-002` measures that directly (the
leg's `tail` node and the reference stack's own mid-node land 0.31 mV
apart), and measures the consequence: per-leg output resistance of 19.2 MΩ
(P) against 2.39 MΩ (N), an 8× asymmetry, so the two legs' plain
channel-length-modulation copy errors (+0.46% and +3.69%) do not cancel.

That is the ≈3% up/dn magnitude mismatch `RECORD-001` recorded, and — via
`sim/sg13cmos5l-closed-loop-lock/records/RECORD-004`'s ideal-substitution
diagnostic — the **confirmed dominant mechanism** behind the ≈9.18%-of-`T_ref`
static phase error that fails `spec/porting-plan.md` row 7's own 5%
threshold. RECORD-004's own Decision was that this warrants a design-level
mitigation rather than acceptance. This record is that decision.

## Decision

**`design/sg13cmos5l/cp.sch` instantiates its own high-swing cascode bias
replica, one per polarity, and `IBP`/`ICP`/`IBN`/`ICN` become
current-input pins.**

Per polarity (P shown; N is the complement):

| Device | Size | Role |
|---|---|---|
| `MBP` | 24 µm / 1 µm (= leg `M1`) | replica mirror device; gate tied to `IBP`, the **top** of its own stack |
| `MBPC` | 24 µm / 1 µm (= leg `M2`) | replica cascode; gate tied to `ICP`; drain is `IBP` |
| `MCP` | 6 µm / 3 µm (= leg `W/L` ÷ 12) | cascode-bias diode; gate = drain = `ICP` |

N side: `MBN` / `MBNC` 8 µm / 1 µm, `MCN` 2 µm / 3 µm (again leg `W/L` ÷ 12).

Two properties are load-bearing and are stated as part of the decision, not
left to implementation taste:

1. **The bias branch is a true replica of the leg stack, with the bottom
   device's gate on the top of its own stack.** This holds the *reference's*
   bottom device at the same `V_ds` the *cascoded leg's* bottom device sits
   at, so the systematic copy error is nulled by construction rather than
   cancelled by tuning. Measured residual: 0.17–0.96 mV (P) and 7.3–12.1 mV
   (N) between reference and leg, against 767–811 mV before.
2. **The cascode-bias diode ratio is `W/L` ÷ 12, not the textbook ÷ 4.**
   The ÷4 device (`V_th + 2·V_ov`) was built and measured first: on this
   PDK's PSP103 devices it leaves the leg's bottom device in triode
   (`nxn` = 186 mV) and delivers only a 2.5× mismatch improvement. ÷12
   (`V_th + ≈3.5·V_ov`) delivers ~20×. The number is a measured margin, not a
   textbook one, and ÷12 is a measured **knee**, not "as large as possible":
   over the swept ratios ÷4 / ÷8 / ÷12 / ÷16 / ÷24 the mismatch at the loop's
   own operating point (`VOUT` = 2.40 V, `mos_tt`/27 C) improves
   −2.562% / −0.505% / −0.298% / −0.242% / −0.212%, while the bottom of the
   compliance window (`VOUT` = 0.75 V) degrades monotonically
   −0.088% / −0.539% / −0.696% / −0.807% / −0.963% as the cascode step eats
   P-side headroom. Past ÷12 the gain where the loop actually sits is small
   and the cost at the low end is not.

Consequential wiring change, ratified with it: **`cp_dumpbuf`'s `IBIAS`
moves from `ICN` to `IBN`.** `ICN` is now a ≈3.5·`V_ov`-overdriven
cascode-bias node; biasing the dump follower's 4 µm/1 µm tail from it more
than doubles the block's supply current (measured 103 µA vs 46 µA total at
`VOUT` = 2.4 V). `IBN` is the mirror-bias node and is the correct node for a
1× tail — the same node `gf180-pll`'s own `cp_dumpbuf` takes (`VBN`/`VBP`).

**No device in `cp_leg_p.sch` or `cp_leg_n.sch` changes.** The legs were
never the defect.

### Relationship to DR-002 Decision 1

DR-002 Decision 1 defers the **bias reference** — a bandgap-style current
reference — out of this block's scope. **That deferral is unchanged and not
reopened.** What moves in-block here is the charge pump's own mirror/cascode
*diode replica*, which is part of the current mirror it biases, not a
reference: the block still needs an external current source, and now needs
**four** matched ones per trim code (mirror-bias and cascode-bias branches,
per polarity) instead of two. `gf180-pll` draws exactly this line — its own
`cp.sch` carries `MBN`/`MCN`/`MBP`/`MCP` while its `design/README.md` still
states "bias generation is out of scope for this block".

## Alternatives considered

- **Resize the legs to make the two output conductances match** (the
  "resizing to reduce the PMOS/NMOS mobility-ratio-driven asymmetry"
  candidate RECORD-004 named). Measured to require ≈8× more channel length
  on the N leg (8 µm/1 µm → ~64 µm/8 µm at constant `W/L`) to bring λ_N down
  to λ_P — a ~20× area asymmetry between the two legs for a result that is
  still a *cancellation*: it nulls the mismatch at one `VOUT` and one corner
  and lets it re-emerge elsewhere, because both legs would still have a
  strong `V_ds` dependence. Rejected: it treats the symptom (unequal errors)
  rather than the cause (no cascode), and it costs more area than the six
  small bias devices this record adds.
- **Lengthen both legs moderately** (e.g. `L` 1 µm → 2–4 µm on both).
  Reduces both copy errors proportionally, so the *ratio* — and therefore
  the mismatch — barely improves. Rejected on measurement.
- **Leave `cp` alone and fix the bias in the testbenches** (drive
  `IBP` ≠ `ICP` from a testbench-local wide-swing bias network). Rejected on
  charter grounds: it would make every recorded result depend on a bias
  network that does not exist in the design, which is exactly the gap
  `RECORD-001` already flagged as real rather than papered over. It also
  would not be a design-level mitigation, which is what issue #72 asks for.
- **Relax row 7's 5% static-phase-error threshold.** Rejected outright —
  `CLAUDE.md`: "agents do not relax the ratified spec to make results pass".
- **A bipolar (HBT) current source instead of the CMOS cascode**, per
  `spec/porting-plan.md` §1.4's own "what SG13G2's bipolar devices add"
  note. Not chosen *here*: that is a topology change to a ratified
  architecture decision (DR-001 Decision 1 / DR-002 Decision 2), it needs its
  own device-characterisation evidence, and the CMOS wide-swing cascode was
  never actually tried before — this record makes the already-ratified
  technique work at a cost of six small devices. The HBT option remains open
  and un-prejudiced by this record.

## Consequences

**What becomes possible / better** (all measured, see
`sim/sg13cmos5l-cp-icp-trim/records/RECORD-002` and
`sim/sg13cmos5l-closed-loop-lock/records/RECORD-005`):

- Worst-case up/dn magnitude mismatch over 0.90–2.90 V × the full 15-point
  PVT matrix at the 10 µA code: **10.28% → 0.72%.** At the loop's own
  operating point (`VOUT` ≈ 2.39 V): −5.24…−7.49% → −0.240…−0.364%.
- Per-leg output resistance: P 19.2 MΩ → 2908 MΩ; N 2.39 MΩ → 49.5 MΩ.
- Mirror fidelity `I_up`/`I_ref` within 0.02% of unity at the four lowest
  trim codes at every PVT point (was 0.4–0.8%).
- Dual-leg ±5% compliance window widens at both ends at every corner (worst
  case 0.70–2.75 V → 0.25–3.15 V), which incidentally closes
  `RECORD-001`'s own finding that the cold-corner window did not cover the
  bottom of the VCO's `VCTRL` sweep.

**What gets harder / worse:**

- **The block now needs four matched reference currents per trim code**, not
  two. The still-undesigned `Iref` generator's requirement grows
  accordingly, and any mismatch *between* those four is a new error term
  this record does not bound.
- **Supply current rises.** In the DC deck: +4.6…+5.7 µA on the block's own
  `VDD` at the 10 µA code. In the closed-loop deck the measured `i_cp` rises
  further because the P-side replica moved out of the testbench's own
  `vddrep` supply and into the block's `vdd_cp` domain — `RECORD-005`
  reports the number. `spec/porting-plan.md` row 11's `cp` domain figure is
  superseded accordingly.
- **Six more devices and two more nets in `cp`** (14 → 20 devices, 16 → 18
  nets). Re-verified: `klt lvs` on the composed `pll_cp` block reports
  `match`, devices 20/20, nets 18/18, block DRC clean, and both new
  geometries (`pfet w=6u l=3u`, `nfet w=2u l=3u`) draw and re-extract
  matching their schematic `(class, W, L)` — see
  `layout/sg13cmos5l-pll/reports/LATEST`.
- **Below ≈0.85 V the up/dn mismatch is marginally worse than as-drawn**
  (−11.10% vs −8.69% worst case over 0.30–0.85 V × 15 PVT). The mechanism is
  measured and is *not* the mirror: the P-side steering switch's own
  `|V_gs|` equals `V(sw)` ≈ `VOUT`, so it saturates and becomes the limiting
  device there. Pre-existing and untouched by this record; the as-drawn
  design partly masked it with its own +0.46% over-delivery. Recorded, not
  fixed.

**What must be re-run / is invalidated:**

- `sim/sg13cmos5l-cp-icp-trim` — re-run in full (306/3111 rows) against the
  mitigated block; `RECORD-002` supersedes `RECORD-001`'s *numbers* (not its
  method or its record).
- `sim/sg13cmos5l-loop-bandwidth-pm` — its `run.sh` reads the Icp table at
  runtime, so it was re-run; `RECORD-002` there records max deltas of 0.70%
  (`fc_hz`) / 0.43% (`pm_deg`) across 252 rows and **zero verdict flips**,
  so row 6/6a's conclusion stands unchanged.
- `sim/sg13cmos5l-closed-loop-lock` — a new Part B deck against the real
  mitigated `cp` (`testbench/run_closed_loop_cascbias.sh`,
  `RECORD-005`). The as-drawn `cp.spice` snapshot and every existing script
  there are deliberately left untouched, so `RECORD-001`…`RECORD-004`
  reproduce unchanged.
- `layout/sg13cmos5l-pll` — re-run; totals move 484 → 490 planned devices,
  479 → 485 drawn, 253 → 255 nets.

**What is explicitly NOT settled here:** the reference-current generator
(DR-002 Decision 1, still deferred), random device mismatch (no per-instance
mismatch model exists for `sg13_hv_nmos`/`sg13_hv_pmos` in this campaign, so
every number above is the nominal matched-device result), switching-transient
charge mismatch, and `cp_dumpbuf`'s own ~1 V follower offset — that dump node
still does not track `VOUT`, which `gf180-pll`'s own `cp.sch` argues is a
separate per-cycle charge-skew mechanism. None of those is made worse by this
record; none is closed by it either.
