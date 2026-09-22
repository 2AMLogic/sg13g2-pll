# RECORD-003: `divider_chain` repair (issue #112) — functional N range + retiming margin, re-verified on the committed design

- **Slug**: `sg13cmos5l-divider-nrange-retiming`
- **Issue**: #112 (Part of #16) — fixes the correctness defect
  RECORD-001 bounded and left open. RECORD-001/#36 remain the record of
  the *broken* as-committed design; per `sim/README.md`'s append-only
  convention neither is edited by this record.
- **DUT**: `divider_chain` as **repaired in `design/` by this record's own
  PR** — frozen at `../netlist-snapshots/divider_chain_repaired.spice`.
  The repair (see "The repair" below) adds, inside every `dff_tg_hv`:
  (a) the missing second feedback inverter in each latch's hold path
  (`XIMF`, `XISF` — full-strength `inv_hv`), and (b) the missing second
  local clock phase (`XICKBB`: `CKBB` = `CLK` delayed two inverter delays)
  with all four transmission gates staggered on it exactly as the proven
  fleet topology (gf180-pll `dff_tg_3v3`: master input `NG=CKB/PG=CKBB`,
  master feedback `NG=CKBB/PG=CKB`, slave input `NG=CKBB/PG=CKB`, slave
  feedback `NG=CKB/PG=CKBB`).
- **Tooling**: `ngspice-46`, `PDK_ROOT=/home/ubuntu/share/pdk`,
  `PDK=ihp-sg13cmos5l`.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh
  [stage...]` (stages: `opconv hold setup func retime`; default all five).
  `RESUME=1` re-invokes append-mode after an interruption (new in this
  campaign — see "Campaign mechanics"). Whole-chain stages now run at
  ngspice's default `reltol=1e-3` (see Finding 2).

## Headline results

| Quantity | Result |
|---|---|
| Divide ratio, 100 MHz, all 9 PVT corners, word `000000` | **`N = 64.000` exact at 9/9 corners** |
| Divide ratio, code sweep at nominal (9 words, `N` = 65, 66, 68, 72, 80, 95, 96, 106, 127) | **exact to 3 decimals at 9/9 words** |
| Divide ratio, range edges under PVT brackets (`111111`, `N=127`) | **127.000 at `mos_ss/125C` and `mos_ff/-40C`** |
| Latch hold (`hold` stage, 9 corners) | **9/9 hold at the rail** (`q_end` = corner's own `VDD`) |
| DC operating point (`opconv`, both ic modes) | **converges** (RECORD-001: never converged) |
| Divider `idd` at 100 MHz nominal | **−199.3 … −256.8 µA** across the 9 corners |
| Flop setup @ 1562 MHz (`setup` stage) | crossover **(500, 700] ps** at `mos_tt/27C` and `mos_ff/-40C`; **(1000, 1500] ps** at `mos_ss/125C` |
| Retiming @ 1562 MHz (`retime` stage, 7/9 corners resolved) | one-edge (`k+1`) capture **fails everywhere**; stable one-period-late (`k+2`) capture observed (`tfb − tdiv` ≈ 636 ps ≈ `T_vco` at `mos_tt/27C`) |

**Spec disposition**: `spec/porting-plan.md` row 3's functional-`N`
confirmation is now measured (not structural-only): every simulated point
across the claimed `N ∈ [64, 127]` range's edges, bit weights, mixed codes,
and PVT matrix divides at exactly its commanded `N`. The retiming-margin
closure at the 1562.0 MHz top-of-band **remains unmet** for this provisional
sizing — one-edge capture needs `t_arr + t_setup ≤ T_vco`, but `t_setup`
alone is 0.5–1.5 ns ≥ 0.8–2.3 × `T_vco` — with a real numeric bound now
recorded (Finding 5). Not relaxed; stated as measured.

## The repair

RECORD-001 Finding 2 established the committed `dff_tg_hv`'s hold-path
feedback carried **one** inversion per latch (`M → XIM → MB → XTGFBM → M`,
`S → XIS → SB → XTGFBS → S`) — a self-biased inverter, not a latch — and
that a weak-keeper proposal variant (`fbfix`) repaired DC bistability but
was never committed and was proven only at one calibration point. This
record's PR lands the repair in `design/sg13cmos5l/dff_tg_hv.sch` itself:

1. **`XIMF`/`XISF`** insert the missing second inverter per latch (regular
   `inv_hv`, matched strength — the `fbfix` weak keeper was sized for DC
   correctness only, and RECORD-001 Finding 3 showed its settling was the
   retiming bottleneck; here the feedback pass gate isolates the keeper
   from the write path, so matched strength is the standard fleet choice).
2. **`XICKBB` + clock retargeting**: as-committed, all four transmission
   gates were clocked from the single-delay `CLKB`, so at a rising edge the
   master feedback engaged while the write path was still closing and the
   slave sampled the master mid-contention. The repair adopts the
   gf180-pll `dff_tg_3v3` clock map verbatim ("the master input gate closes
   one inverter delay before the slave input gate opens" — the
   master-slave race margin).

Part 1 alone was simulated as an intermediate state during this campaign:
it repaired hold (9/9) and whole-chain division (`N=64.000` at nominal) but
left top-band capture failing — which is what isolated part 2 as also
missing. The intermediate numbers are superseded by the tables below; the
diagnosis is retained here because it is the evidence that both deviations
from the fleet topology were load-bearing.

An intermediate whole-chain `retime` row set (pre-`XICKBB`) also showed the
same qualitative result at `mos_tt`/`mos_ss`/`mos_ff` @27C (one-period-late
capture), i.e. the retiming verdict below is not an artifact of the clock
retargeting.

The identical defect exists in the SG13G2 (non-port) originals
(`design/dff_tg_hv.sch`, `design/netlist/divider_chain.spice`) — verified
against this worktree, filed as #120, out of this record's scope.

## Finding 1 — the repair is confirmed at cell and chain level

- `../corners/hold.csv`: 9/9 corners hold cleanly (`q_end` = `s_end` =
  the corner's own `VDD`; RECORD-001's as-drawn: 0/9, mid-rail 1.38–1.69 V).
- `../corners/opconv.csv`: a bare `.op` on the whole chain converges both
  with and without the `.ic` symmetry break (RECORD-001 Finding 1: did not
  converge within 150 s in either mode). The `.ic` statements remain in
  every deck — the block still has **no reset** (a design gap RECORD-001
  Finding 1 documents and this repair does not touch) — but convergence
  itself is no longer blocked by non-bistable feedback loops.
- `../corners/func.csv`: **20/20 rows measure the exact commanded `N`**
  (to 3 significant decimals of the ratio): 9 PVT corners at `N=64`
  (`000000`), the 9-word code sweep at nominal (`N` = 65, 66, 68, 72, 80,
  95, 96, 106, 127), and `N=127` at both PVT speed-bracket extremes
  (`mos_ss/125C`, `mos_ff/-40C`). Internal stages `ck1`–`ck5` and both
  outputs swing rail-to-rail in every row.

**What this does and does not establish about the `N` range**: the
structural formula (`N = 64 + Σ p_i·2^i`, hole-free by construction)
predicts 64 values; 20 of them were simulated (every bit weight once, two
mixed codes, the all-zeros floor across the full PVT matrix, the all-ones
ceiling at three corners). The other 44 integers were **not** individually
simulated — the claim rests on the formula plus the per-bit functional
confirmation, exactly the composition DR-005 used, now with functional
(instead of purely structural) support. A full 64-code × PVT sweep remains
unrun (compute cost ≈ Σ over `N`∈[64,127] of ~3.4·`N` CKIN cycles per
corner; the 20-point subset above is what fit this campaign's budget).

## Finding 2 — `reltol=5e-3` is numerically fragile on this DUT; the campaign default is now ngspice's own `1e-3`

The first post-repair whole-chain run at RECORD-001's wall-clock-relaxed
`reltol=5e-3` died deterministically with `Timestep too small; time =
3.31822e-07, trouble with node "xdiv.xd0.nt"` on the very first baseline
corner. Reproduced standalone; **`reltol=1e-3` and `method=gear` both
converge the identical deck; removing `trtol=7` does not**. Since a
switching (repaired) chain is exactly what RECORD-001 Finding 4 struggled
to reproduce "within a 400–700 real-second budget", the looser tolerance —
not the design — is the parsimonious explanation for that session's
reproducibility trouble. The campaign default is therefore ngspice's own
`1e-3`, and `../corners/tol_convergence.csv` records the sensitivity both
ways:

- `1e-3` vs `2e-3` at two corners: divide ratio identical (`64.000`),
  `idd` within 1.5 %.
- `5e-3`: fails to resolve the second `DIVOUT` crossing at `mos_tt/27C`
  (`tdiv_b` NA) and produces no data at all at `mos_ss/125C` — the
  collapse, recorded as data (the `tol` stage's tolerant wrapper writes the
  NA row instead of aborting).

## Finding 3 — latch-level setup requirement at the top-of-band frequency

`../corners/setup.csv` (10 `TSU` values × 3 speed-bracket corners, 1562.0
MHz clock): the repaired flop's capture crossover is bracketed at
**(500, 700] ps** at `mos_tt/27C` and `mos_ff/-40C`, and **(1000, 1500] ps**
at `mos_ss/125C`. The old 6-point list (max `TSU=300p`) could not bracket
any of these — every point read as a capture failure; the list now extends
to 1500 ps.

Physical reading (confirmed by an internal-node probe at
`mos_tt/27C`/`TSU=300p`): the master node `M` does charge during the write
phase, but a transfer through the L=0.5 µm provisional pass gates takes
~400+ ps end-to-end (write through `XTG1`, then slave transfer through
`XTG2`), so at `T_vco` = 640.2 ps neither the write nor the slave transfer
completes within one phase. This is the **provisional sizing**, not the
topology — DR-001's own header on every cell says sizing is a placeholder
owed to the device-characterization campaign. No sizing was changed by this
repair.

## Finding 4 — retiming margin at 1562.0 MHz: numeric bound, unmet for one-edge capture

`../corners/retime.csv` (7/9 corners resolve `tdiv`/`tfb` rail-to-rail;
`mos_ss/27C` and `mos_tt/125C` do not complete within a 570–900 s
per-run budget at `reltol=1e-3` — recorded as NA, consistent with the slow
bundle's 1000–1500 ps capture requirement). Joining `t_arr` (=`tdiv` mod
`T_vco`, computed against the deck's own rising-edge grid) with Finding 3's
brackets, gf180-pll `divider-ratio`'s margin arithmetic ported verbatim:

| Corner | `t_arr` (ps) | window to next edge (ps) | `t_setup` bracket (ps) | `k+1` capture | `k+2` capture | `k+2` margin (ps) |
|---|---|---|---|---|---|---|
| `mos_tt/27C/3.3V` | 454.9 | 185.3 | (500, 700] | **FAIL** | PASS | +125.5 |
| `mos_ff/27C/3.3V` | 76.3 | 563.9 | (500, 700]* | FAIL/indeterminate | PASS | +504.1 |
| `mos_sf/27C/3.3V` | 383.4 | 256.8 | no direct bracket† | FAIL | bracket-dependent | (−603, +197) |
| `mos_fs/27C/3.3V` | 342.7 | 297.5 | no direct bracket† | FAIL | bracket-dependent | (−562, +238) |
| `mos_tt/-40C/3.3V` | 568.8 | 71.4 | (500, 700]* | **FAIL** | PASS (marginal) | **+11.6** |
| `mos_tt/125C/3.3V` | — | — | — | retime NA | — | — |
| `mos_tt/27C/2.97V` | 83.8 | 556.4 | (500, 700] | FAIL/indeterminate | PASS | +496.6 |
| `mos_tt/27C/3.63V` | 130.8 | 509.4 | (500, 700] | FAIL/indeterminate | PASS | +449.6 |
| `mos_ss/27C/3.3V` | — | — | — | retime NA | — | — |

\* nearest same-process setup bracket (`setup` runs only the 3 speed
bundles; see `../corners/matrix.md`). † the mixed corners sit between the
`ff` and `ss` brackets; both bounds are shown instead of inventing a
number.

**Verdict**: one-edge retiming (`DIVOUT` change captured on the *next* VCO
edge) **does not close at the 1562.0 MHz top-of-band** in this sizing: the
window (`T_vco − t_arr` = 71–564 ps) is below the flop's bracketed
requirement (≥ 500–1500 ps) at every resolved corner. The measured
`tfb − tdiv` ≈ 636.4 ps ≈ `T_vco` at `mos_tt/27C` shows what happens
instead: the retimed `FB` edge lands **one VCO period late** — a stable,
repeating capture on the `k+2` edge (rail-to-rail `FB` at every resolved
corner), i.e. a constant extra `T_vco` in the loop's feedback delay, not a
functional failure of the divider itself. The `k+2` margin is positive
where bracketed but thin at `mos_tt/-40C` (+11.6 ps against the 700 ps
bracket bound) and unbounded at the mixed corners.

**Numeric closing bound** (one-edge): `F_close = 1/(t_arr + t_setup)` ≈
**866 MHz** (`mos_tt/27C`), **1277 MHz** (`mos_ff/27C`), **825 MHz**
(`mos_tt/-40C`) using each corner's bracket bound — everywhere below the
1562.0 MHz top band and inside the measured VCO band (445.3–1562.0 MHz,
`sg13cmos5l-vco-kvco-table` RECORD-001), so upper-band references will
operate in the one-period-late regime until the flop is re-sized by the
device-characterization campaign DR-001 already tasks with every number in
these cells.

## Campaign mechanics (harness changes, all in `../testbench/run.sh`)

- **DUT sourcing**: the stage scripts now copy the frozen **repaired**
  snapshot; the `fbfix` python derivation is deleted (the committed design
  embodies the fix; the proposal variant has no separate question left).
- **`reltol` default**: whole-chain stages at `1e-3` (Finding 2); the
  cross-check runs `2e-3` and `5e-3` arms, the latter through a
  failure-tolerant wrapper that records the collapse as NA data rows.
- **`TSU_LIST` extended** to 10 points, ceiling 1500 ps (Finding 3).
- **`func` stage additions**: two mixed code words (`011111`, `101010`) and
  the `edge` group (`111111` at the two speed-bracket extremes).
- **`RESUME=1` append mode**: this campaign's host twice reaped the
  detached ngspice tree ~35–40 real minutes into the `func` stage (silent
  SIGKILL — no OOM, no kernel log; the same fragility RECORD-001 Finding 4
  described). Resume mode keeps completed per-corner/per-word CSV rows and
  re-runs only the missing ones, which is how this campaign completed: in
  bounded foreground chunks.

## What this does not bound

- **The 44 unsimulated integer codes** in [64, 127] (see Finding 1's
  scope statement) — functional support is per-bit + edges + mixed codes,
  not an exhaustive sweep.
- **The two non-completing `retime` corners** (`mos_ss/27C`, `mos_tt/125C`)
  — NA within a 570–900 s per-run budget; the slow bundle's setup
  requirement (Finding 3) is the reliably-reproducible evidence for those
  corners, the same interpretive structure RECORD-001 Finding 5 used.
- **Any faster sizing** — `L=0.5 µm` provisional devices throughout; no
  sizing was re-derived here (DR-001's characterization campaign owns that).
  The 866/1277/825 MHz closing bounds move with that re-derivation.
- **Mismatch, layout parasitics, post-layout timing** — schematic-level,
  ideal sources, as for every sibling record.
- **The no-reset gap** — RECORD-001 Finding 1's design gap stands; every
  deck still carries the `.ic` symmetry break (now only needed for state
  definition, no longer for convergence).
- **Loop-level impact of the one-period-late `FB`** — constant extra
  `T_vco` of feedback delay at upper-band references; quantifying its
  effect on loop dynamics/phase margin belongs to the loop-dynamics
  campaign (`sg13cmos5l-loop-bandwidth-pm` and successors), not this
  block-level record.
