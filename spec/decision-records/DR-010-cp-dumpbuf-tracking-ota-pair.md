# DR-010: `cp_dumpbuf` becomes a complementary pair of unity-gain 5T OTAs so `VDUMP` tracks `VOUT` at DC

- **Status**: proposed
- **Date**: 2026-10-09
- **Decided by**: Builder agent, issue #165
- **Related**: #16 (parent epic), #165 (this issue), #150 /
  `sim/sg13cmos5l-closed-loop-lock/records/RECORD-006` (the diagnostic that
  isolated the mechanism and proposed this change), #72 / DR-006 (the
  cascode-bias fix whose DC-matching win this record's mechanism had masked),
  DR-001 Decision 1 (no opamp in the loop path, with gf180-pll DR-005's
  four-condition test adopted for any bias element touching the loop-filter
  node), DR-004 (the 3.3 V rail box), #195 (layout/PEX follow-up), #196
  (PM-bench follow-up)
- **Consumes**: `2AMLogic/gf180-pll` `design/cp_dumpbuf.sch` and its DR-005
  (the sibling design and compatibility test this ports);
  `sim/sg13cmos5l-closed-loop-lock/records/RECORD-005`, `RECORD-006`;
  `sim/sg13cmos5l-cp-icp-trim/records/RECORD-002`; spec row 1 (`VCTRL`
  0.3-2.7 V)
- **Evidence**: `sim/sg13cmos5l-cp-icp-trim/records/RECORD-005`,
  `sim/sg13cmos5l-closed-loop-lock/records/RECORD-007`

---

## Context

RECORD-006 isolated row 7's remaining 8.2% static phase error to
**dump-node charge sharing** in `cp`. `cp_dumpbuf` was an NMOS source
follower, so it held `VDUMP` one V_GS (0.937 V) below `VOUT`. Each idle
leg's switch-common node therefore sat about 0.94 V below `VOUT`. Every UP
and every DN turn-on pulled 20-23 fC out of the loop filter, the same sign
for both legs (-41.3 fC per cycle). The loop cancels that with a 4.1 ns UP
lead, which is 8.2% of `T_ref`. An ideal `VDUMP = VOUT` closed the nominal
error to 1.05%; an ideal follower that kept the shift gave 7.40%. The term is
set by a DC level, not by switch timing or up/dn matching, so the fix is to
make `VDUMP` track `VOUT` at DC.

**The `VOUT` range the buffer must cover, inside the 3.3 V rail box
(DR-004).** The required range is **0.3-2.7 V**, the `VCTRL` range the
committed VCO is characterised over (spec row 1). It is also reported to
2.9 V. For context: the mitigated `cp`'s own dual-leg compliance window is
0.25-3.10 V (cp-icp-trim RECORD-002), and the proposal-deck closed loop
settles at `VOUT` = 2.387 V at nominal. No band-selection rule places lock
inside a narrower window yet (spec R-4), so the whole characterised `VCTRL`
range is required. The supply is the single 3.3 V domain, with a +/-10%
sub-axis (3.0-3.6 V).

## Decision

**`design/sg13cmos5l/cp_dumpbuf.sch` is a complementary pair of
five-transistor OTAs, each in unity-gain feedback, with outputs tied on
`VDUMP`.** This is ported from `gf180-pll`'s `cp_dumpbuf` (its #24), which
solved the identical tail-charge term this way:

- `MTN/MN1/MN2/MN3/MN4`: NMOS input pair with a PMOS mirror load. It covers
  the top of the range.
- `MTP/MP1/MP2/MP3/MP4`: PMOS input pair (bulk on its own common source
  `PSRC`) with an NMOS mirror load. It covers the bottom of the range.
- `MN1`/`MP1` sense `VOUT`. `MN2`/`MP2` sense `VDUMP`, and their drains are
  `VDUMP`. Outside its range, an OTA's tail collapses and its output device
  turns off, so the two OTAs do not fight.

Sizing (all `sg13_hv_*`, DR-002 Decision 0):

| Device | W/L | Why |
|---|---|---|
| `MTN` (gate `IBN`) | 12u/1u | 1.5x the 8u/1u NMOS mirror device, so about 1.5x `Icp`. The tail scales with the trim code and exceeds `Icp` at every code, so a one-sided PFD state (acquisition) cannot collapse `VDUMP` |
| `MTP` (gate `IBP`) | 36u/1u | 1.5x the 24u/1u PMOS mirror device, same reason |
| `MN1`/`MN2` | 2u/1u | Small on purpose; see "Loading" below |
| `MP1`/`MP2` | 6u/0.5u | Small on purpose. Bulk is on `PSRC` (no body effect) |
| `MN3`/`MN4` (PMOS) | 24u/1u | 1:1 mirror load. A ratioed load adds systematic offset |
| `MP3`/`MP4` (NMOS) | 16u/1u | 1:1 mirror load |

**Interface change**: `cp_dumpbuf`'s `IBIAS` pin is replaced by `IBN`, and a
new `IBP` pin is added. `cp.sch` wires them to its own mirror-bias nodes
`IBN`/`IBP`, not to the cascode-bias nodes `ICN`/`ICP`. `cp`'s own pinout is
unchanged.

**Pass bounds this design is held to** (graded in
`sim/sg13cmos5l-cp-icp-trim/records/RECORD-005`):

1. **Tracking**: |`VDUMP` - `VOUT`| <= **100 mV** in the idle state
   (UP = DN = 0, the state every turn-on starts from), over `VOUT` 0.3-2.7 V,
   at every trim code. Derivation: RECORD-006's level term was 33.2 fC per
   0.937 V. At the 10 uA code and 20 MHz, 1 fC is 0.199% of `T_ref`, so
   100 mV adds about 3.5 fC, or about 0.7 percentage points. Row 7 has 5%
   available. RECORD-006's ideal-tracker floor is 1.05%, which already
   includes about 8 fC of switch injection. Reserving its 0.8 pp
   buffer-dynamics term on top, an offset of up to about 0.44 V would still
   close at 5%. 100 mV keeps a 4x margin. The charge per volt does not depend
   on `Icp` but the phase per fC scales as 1/(`Icp`*`T_ref`), so the margin is
   smaller at low codes and low `f_ref` (see Consequences).
2. **Loading** (condition 2 below): the capacitance the buffer adds to the
   loop-filter node is <= **1% of C1**, which is 16.9 fF for this loop's
   C1 = 1.691 pF. This applies over `VOUT` 0.3-2.9 V.
3. **Stability** (condition 4 below): the buffer's own unity-feedback loop
   has a phase margin of at least 45 deg at every `VOUT` point measured.

**DR-001 / gf180-pll DR-005 four-condition test, applied:**

1. *Not in the signal path*: met. The buffer's only connection to `VOUT`
   is two MOS gates (`MN1`, `MP1`). Loop charge goes through the legs'
   steering switches exactly as before.
2. *Control-node loading <= 1% of the smallest C1, declared*: met at
   nominal. The buffer adds 3.7-10.5 fF over 0.3-2.9 V (at most 0.62% of
   C1). The PVT grid is pending (RECORD-005).
3. *Static current declared*: +25.6 uA at the 10 uA code (61.56 uA against
   35.97 uA whole-`cp` current, idle, `VOUT` = 2.4 V, nominal). That is about
   84 uW. It scales with the trim code. No whole-PLL power number is proposed
   (row 11), so this is declared rather than graded.
4. *No nested stability problem*: met at nominal. Each OTA is single-stage
   with one high-impedance node and no compensation capacitor. The in-situ
   loop gain is 32-36 dB DC, UGF 116-243 MHz, PM 73.5-77.1 deg over `VOUT`
   0.5-2.7 V. Settling is set against the reference period, not the PLL
   bandwidth. The closed-loop re-run (RECORD-007) is the end-to-end check.

## Alternatives considered

- **Level-shift-compensated follower** (keep a source follower and cancel
  its V_GS with a matched level shifter). Rejected on headroom inside the
  3.3 V box. An NMOS follower producing `VDUMP` = `VOUT` needs its gate at
  `VOUT` + V_GS, about 0.94 V above `VOUT`. That reaches the 3.3 V rail at
  `VOUT` of about 2.35 V, which is below the closed loop's own 2.387 V
  operating point and well short of 2.7 V. The PMOS mirror image fails the
  same way at the bottom (gate at `VOUT` - V_SG, below ground under about
  0.9 V). A complementary pair of shifted followers is two open-loop circuits
  whose accuracy is the V_GS matching between devices at different `V_SB`
  across PVT, with no feedback to remove it. That costs about the same
  devices as the OTA pair and is less accurate.
- **A single unity-gain OTA (one input polarity)**. Rejected on range. An
  NMOS-input pair runs out of tail headroom below `VOUT` of about 0.9-1.0 V,
  where `VDUMP` becomes degenerate (gf180-pll's measured failure). A
  PMOS-input pair runs out near 2.2-2.4 V, which is where this loop operates.
  Neither covers 0.3-2.7 V. That is the same headroom result gf180-pll
  recorded.
- **gf180-pll's sizing as-is (16u/1u NMOS and 48u/1u PMOS input pairs)**.
  Built and measured first (nominal: idle offset at most 7.2 mV; closed loop
  0.897% with a 45-cycle dual lock). Rejected on loading. It adds 28-112 fF
  to `VOUT`, worst at 2.5-2.9 V where the PMOS pair's tail runs out and its
  C_gs stops being bootstrapped. That is up to 6.6% of C1 and 1.1x C2. It
  fails condition 2 for this loop, because C1 is 1.69 pF here against about
  130 pF in gf180-pll. The small pairs trade about 2x the offset (still about
  15 mV) for 10x less loading.
- **An ideal `VDUMP = VOUT` (RECORD-006 variant (b))**. A diagnostic bound,
  not a design.
- **An HBT-based buffer**. Not available: SG13CMOS5L is the CMOS-only
  sibling process, so this port has no SiGe HBT (DR-003, DR-009).
- **Switch-charge cancellation (dummies) first**. Rejected as the *first*
  step. RECORD-006 measures the switches' own injection at about 8 fC against
  33 fC for the level term. It is a possible second step after this one.
- **Relax row 7's 5%**. Not available: the ratified criterion is not relaxed
  to make a result pass (CLAUDE.md).

## Consequences

- **Row 7 at nominal on the proposal deck.** RECORD-007 reports the measured
  value. This record does not decide row 7. The proposal deck (behavioural
  divide-by-64, R1 2400u, ideal caps, ideal `IREF`) is still not the
  committed PLL.
- **DC trim/mismatch unchanged.** The buffer only sets the idle legs' dump
  level, so the Icp trim table and up/dn mismatch are identical at nominal
  to RECORD-002's printed digits (cp-icp-trim RECORD-005).
- **More supply current**: +25.6 uA at the 10 uA code, scaling with the
  code.
- **More loading on the loop-filter node**: the buffer adds at most 10.5 fF
  (nominal); the old follower added 4.2-7.0 fF. The PM bench has never
  modelled any `cp` output capacitance (ideal transconductor), and this
  loop's C2 is only 100 fF. An analytic estimate puts the total `cp` term at
  -1 to -4 deg of PM for fc = 1-5 MHz. That matters for the sub-1-degree
  DR-007/DR-008 tuples and is filed as #196, not hidden here.
- **Offset margin shrinks at low codes and low `f_ref`.** Charge per volt of
  offset is fixed, but phase per fC grows as 1/(`Icp`*`T_ref`). The same is
  true of the about 8 fC switch-injection floor, which no dump buffer
  removes. Row 7 at low `Icp`*`T_ref` products is not bounded by any record
  yet.
- **Random offset is not bounded.** The 2u/1u and 6u/0.5u input devices are
  small, and no Monte Carlo of the buffer's input offset exists. The
  `sg13cmos5l-cp-icp-trim-mc` bench pattern (mismatch sections, `klt sim`
  Monte Carlo on the batch fleet) is the route. It is blocked for this PDK
  like every grid (klayout-tools#2727).
- **Layout and PEX evidence for `pll_cp` is stale** until #195 redraws it.
  `manifests/check_pex_coverage.py` carries `cp` as an explicit,
  issue-tracked `STALE_PENDING` entry, and the manifest may not cite `cp`'s
  PEX envelope meanwhile.
- **Full-PVT verification is owed.** The DC, loading and stability grids are
  committed as `klt sim` batch requests. Whatever ran, and what did not and
  why, is stated in the two evidence records. No local corner grid was run
  (host policy).
- **SG13G2 is untouched.** `design/cp_dumpbuf.sch` (the SG13G2 original) is
  still the source follower. Porting this change there is a separate
  decision.
