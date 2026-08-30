# RECORD-001: `divider_chain` functional N range + retiming margin (SG13CMOS5L)

- **Slug**: `sg13cmos5l-divider-nrange-retiming`
- **Issue**: #36 (Part of #16, Chipalooza Challenge #6), split out of #27
  (which built an exploratory testbench and deliberately published
  nothing — see #36's own "Breadcrumbs from #27").
- **DUT**: `divider_chain` (SG13CMOS5L port, PR #26/#39) — the full
  6-cell `div23_cell` Vaucher chain plus the `XFRT` VCO-clocked retiming
  flop, and (for the OP-convergence / hold / setup probes) a single
  isolated `dff_tg_hv` instance, the flop type every state element in the
  chain is built from. See `../netlist-snapshots/divider_chain.spice`
  (frozen at commit `fbebbdbdd57637b8dae0c1dabaf75d3be5411edb`, unchanged
  since PR #26).
- **Two DUT variants, and why the second one exists**: `divider_chain.spice`
  is the committed design, simulated as-is (`asdrawn`). `divider_chain_fbfix.spice`
  is a **proposal variant**, derived locally by `../testbench/run.sh` from
  the same frozen snapshot — **not** the committed design, not written back
  to `design/`, nothing here proposes committing it. It exists because
  Finding 1 below shows the committed `dff_tg_hv`'s own hold path is not a
  real latch; once that is established, the useful next datum is whether
  the failure is the topology or the sizing, and that question can only be
  answered by simulating a repaired variant alongside the committed one —
  the same reason `sim/sg13cmos5l-loop-bandwidth-pm/corners/proposal.csv`
  exists for a different block. See `../testbench/run.sh`'s own header for
  the exact 3-line derivation (inserting the second inverter each hold path
  was missing, with a deliberately weak keeper sizing).
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh
  [stage...]` (stages: `opconv hold setup func retime`; default is all
  five). Writes `../corners/*.csv`.

## Corner matrix

See `../corners/matrix.md` for the full reduced 9-point matrix and its
explicit subset rationale (this record's own compute-budget finding, not a
methodology default), and for why `setup` uses a further-reduced 3-bundle
bracket. Summary: 9 PVT points (one-factor-at-a-time from nominal) × 2
DUT variants for `opconv`/`hold`/`func`-baseline/`retime`; 3 PVT points ×
6 `TSU` values × 2 variants for `setup`.

## Finding 1 — the block has no reset, and the as-drawn design's DC
## operating point does not converge

`divider_chain` has no reset pin (`design/README.md` confirms: 6
`div23_cell` instances, always active, no mux/termination, and no reset
port on any leaf cell). Its 13 `dff_tg_hv` state elements (12 inside the 6
`div23_cell`s, plus `XFRT`) therefore have no defined power-up state.

`../corners/opconv.csv` bounds this directly: a bare `.op` analysis on the
whole chain, both with **and** without the `.ic` symmetry-break workaround
issue #27's breadcrumbs describe, **does not converge within 150 real
seconds** in either case, for either DUT variant (4/4 rows: `converged=no`).
Independently confirmed by hand outside the matrix (not part of the
150 s-bounded sweep): the `asdrawn`/`ic=applied` case was left running for
a full 5 real minutes (`Note: Transient op started`, then no further
output) without resolving. This is the same qualitative failure #27's
breadcrumbs reported (`gmin` stepping, true `gmin` stepping, and source
stepping all fail, then a stall/failure in the final transient-op
fallback) — now bounded with real timing data rather than left anecdotal.

**Consequence for every other stage in this record**: every `hold`,
`setup`, `func`, and `retime` deck below uses the same `.ic v(...m)=0
v(...s)=0` symmetry-break on every `dff_tg_hv` instance's master/slave
storage nodes that #27's breadcrumbs describe — a **testbench workaround
for a design gap**, not a property of the block, and not silently routed
around: it is this record's Finding 1, stated plainly, and it is why every
downstream result below is conditioned on an artificial initial condition
the real chip will not have without an added reset path.

## Finding 2 — the committed `dff_tg_hv`'s hold path is not a real latch

`../corners/hold.csv` (9 corners × 2 variants, 18 rows) isolates one
`dff_tg_hv`, writes a `1` through a single clock pulse, then holds the
clock low and asks whether `Q` stays at the rail.

**As-drawn, 0/9 corners hold**: `q_end` (and the slave storage node `s_end`
directly) settles to **1.38–1.69 V** in every one of the 9 corners — a
process/temperature/supply-dependent **mid-rail** voltage, not a `0` or a
`1`. Reading the netlist explains why: the hold-path feedback around each
storage node is `M → XIM (inverting) → MB → XTGFBM (pass gate, non-inverting)
→ M` — **one** inversion in the loop. A pass-gate-closed feedback loop with
an odd number of inversions is not a bistable latch; it is a self-biased
inverter, whose only DC equilibrium is its own trip voltage. The corner
spread of the measured `q_end` (1.38–1.69 V, tracking `VDD` and process)
is exactly the signature of an inverter trip point, not of a stuck logic
level.

**`fbfix`, 9/9 corners hold cleanly at the rail**: `q_end` = `VDD` (3.30,
2.97, or 3.63 V matching the corner's own supply) in every one of the 9
corners, confirming the 3-line fix (a second, weak, non-inverting stage in
the feedback path — see the DUT-variant note above) repairs the DC
bistability question specifically.

## Finding 3 — even with a repaired hold path, `fbfix`'s own settling is
## slow relative to the measured top-of-band period

`../corners/setup.csv` (3-bundle bracket × 6 `TSU` values × 2 variants, 36
rows) measures how much setup time one `dff_tg_hv` needs at the measured
top-of-band frequency (1562.0 MHz, 640.2 ps period, from
`sim/sg13cmos5l-vco-kvco-table/records/RECORD-001`).

**As-drawn** shows a real, monotonic setup-time curve at every one of its 3
tested corners (e.g. nominal: `q_sample` = 3.05 V at `TSU=300 ps`, falling
smoothly to 0.55 V at `TSU=0 ps`) — informative about *this specific write
path's* transient response even though Finding 2 already rules the cell
out as a working latch.

**`fbfix` fails to cleanly capture a `1` at *every* tested `TSU` up to
300 ps, at all 3 corners** — `q_sample` stays within ±30 mV of `0 V`
regardless of `TSU`, the opposite of the as-drawn curve's clean approach to
`VDD`. A by-hand trace of one such run (`mos_tt`/27 °C/3.3 V, `TSU=300 ps`,
raw waveform in this record's own scratch — not committed, see
"What this does not bound") shows why: the master node `M` **does** rise to
within numerical noise of `VDD` by the capture edge (a real, successful
write), but the *feedback loop itself* (now two series stages plus a
transmission gate, per the 3-line fix) takes on the order of 150–200 ps to
settle after the write path releases — comparable to the 640.2 ps
top-of-band period's own hold phase (`TON` = 0.44×period ≈ 282 ps) — so `M`
overshoots past `VDD`, then decays toward an intermediate ~1.8 V over the
next several tens of ps before the sample point, and the slave/output chain
never catches up within the quarter-period sample window. **This is a
sizing property of this record's own deliberately-weak keeper**, not a
structural limit of the repaired topology — a faster (stronger) keeper
would settle sooner — but as sized here (the minimum 3-line fix, sized only
for DC correctness, not for speed), the retiming margin at the measured
top-of-band frequency is **not adequate**.

## Finding 4 — the measured functional `N` range (low-frequency baseline)

Per issue #36's own scope ("establish a low-frequency functional baseline
first ... before making any claim about high-frequency behaviour"),
`../corners/func.csv`'s `baseline` rows run the whole 6-cell chain at
100 MHz — 15.6× below the measured top-of-band VCO frequency, so speed is
provably not the limiting factor here.

**As-drawn, 9/9 corners baseline (word `000000`, structural `N=64`)**:
7 of 9 corners show every internal node (`ck1`–`ck5`, `DIVOUT`, `FB`) flat
at exactly `0 V` for the whole measurement window, with `idd=0` — the whole
chain settles into a **fully static, dead state** once its `.ic`-forced
start relaxes; it does not divide at all. The remaining 2 corners
(`mos_ss`/27 °C and `mos_tt`/125 °C) show *some* internal voltage
excursion, but the implied "divide ratio" from the two measured `DIVOUT`
crossings is ≈2.0 and ≈0.4 CKIN cycles respectively — **not** 64, and not
any other clean integer. This is not evidence of partial function; it is
the same near-metastable single-inversion dynamics Finding 2 already
explains, now visible as noise inside a clocked chain rather than as a
settle-to-mid-rail DC point. **The as-drawn design does not divide, at any
tested corner, at any tested frequency in this record.**

**`fbfix`, confirmed functional at the nominal corner (word `000000`,
`N=64`)**: all five internal stages (`ck1`–`ck5`) and both outputs
(`DIVOUT`, `FB`) swing rail-to-rail (`ck1_max`=3.361 V down to
`ck5_max`=3.318 V, all with `_min` within ~150 mV of ground). The measured
`DIVOUT` period, from two widely-separated rising 50%-crossings
(`tdiv_a`=654.319 ns, `tdiv_b`=1294.331 ns), is **640.012 ns** —
`640.012 ns / 10.000 ns = 64.00` (to 4 significant figures), an **exact**
match to the structural formula's `N=64` prediction for the all-`0` program
word. Average supply current over the measurement window: **`idd` =
−165.76 µA** (sign convention: current flowing out of the `VDD` source into
the circuit) — a real, measured data point toward
`spec/porting-plan.md` row 11 ("Power ... re-derive").

**A tooling/reproducibility finding, stated plainly**: this specific
result (`fbfix`, nominal corner, 100 MHz baseline) was **not reliably
reproducible** in this session's environment. The value above is a real,
complete ngspice run (raw log preserved at
`../corners/manual-probes/func-baseline-fbfix-nominal.log`) — but repeated
re-runs of the *identical* deck, both under concurrent system load and in
isolation, sometimes converged within a few real minutes and sometimes did
not complete within a 400–700 real-second budget. `../corners/func.csv`'s
own `baseline-manual` tag on this row (rather than the plain `baseline` tag
the scripted sweep uses) records that provenance difference honestly: this
number is real, but this specific deck's convergence time in this
environment is not itself a stable, repeatable quantity, and should not be
read as "this configuration reliably completes in N seconds." The other 8
`fbfix` baseline corners, and the word-code sweep (`N` values 65–127) that
would have independently exercised every other bit of the structural
formula, could not be completed to the same standard inside this session's
compute budget and are **not claimed** — see "What this does not bound."

**Structural N range** (read from the schematic, `design/README.md` §
"SG13CMOS5L port", independently re-derived here from
`../netlist-snapshots/divider_chain.spice` and already the basis of
`spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md`): for a
`k`-cell chain of this family with each cell's own ÷2/÷3 modulus bit `p_i`,
`N = 2^k + Σ_{i=0}^{k-1} p_i·2^i`, ranging with **no holes** over every
integer from `2^k` to `2^{k+1}-1`. For `k=6`: **`N ∈ [64, 127]`**. The one
simulated calibration point above (word `000000` → measured `N=64.00`,
exact) is consistent with this formula at its floor; the ceiling (`N=127`,
all cells ÷3) and every intermediate code were **not** independently
confirmed by simulation in this session (see above) — the range is stated
on the combination of the structural derivation (which does not depend on
this record's own simulation) and the one exact calibration point, not on
a full code sweep.

## Finding 5 — retiming margin at the measured top-of-band frequency:
## `insufficient-evidence` for a numeric bound, but Finding 3 already
## answers the underlying question

`../corners/retime.csv` targets the deliverable issue #36 itself asks for:
the setup window `DIVOUT` gets before the next VCO edge, and `XFRT`'s own
clk→Q, at 1562.0 MHz.

**As-drawn, 4/9 corners attempted, 0/4 functional** — `tdiv`/`tfb` (and
every other measured quantity) are `NA` at every corner: consistent with
Findings 1/2/4, the as-drawn chain does not produce a `DIVOUT` edge to
retime in the first place. (The remaining 5 corners were not run — see
"What this does not bound" — but nothing in Findings 1/2/4 suggests they
would differ.)

**`fbfix`, nominal corner, `insufficient-evidence` for a clean two-edge
number** — repeated attempts (6 real ngspice runs, window sizes from 65 ns
to 246 µs-equivalent, `rise=1` through `rise=4` measurement variants, run
both in isolation and under concurrent load, individual budgets from 350 to
900 real seconds) did **not** reliably produce a clean `DIVOUT`-to-next-VCO-edge
/ `XFRT`-clk→Q pair. One completed run (raw log at
`../corners/manual-probes/retime-fbfix-tob-nominal-2p5x.log`, `idd` =
−1.287 mA) does show `DIVOUT` reaching `dvo_max`=3.598 V and `FB` reaching
`fb_max`=3.424 V within the transient — confirming `fbfix` **does** produce
at least one real, near-rail toggle at the top-of-band frequency — but the
specific 50%-crossing timestamps ngspice's own `meas ... rise=N` needs for
a defensible margin number were not obtainable within this session's
compute budget at any window size tried (`../corners/retime.csv`'s own
`fbfix-manual` row records `tdiv_s`/`tfb_s` as `NA` for exactly this
reason, while still recording the real `dvo_max`/`fb_max`/`idd` data that
*was* obtained).

A further, smaller-scale probe sharpens why: even isolating the very first
`DIVOUT` rising 50%-crossing is not a clean single-event question here. In a
65 ns window (chosen to comfortably include the real, near-rail excursion
`dvo_max`=3.598 V at 55.75 ns from the run cited above), `meas ... rise=1`
finds a crossing at just **5.25 ns** — far too early to be a genuine
divide-by-64 edge (64 CKIN cycles at 640.2 ps each is 41.0 ns, the earliest
any real edge could occur) — and `meas ... rise=2` then fails to find a
*second* crossing anywhere in the same 65 ns window, even though the signal
demonstrably reaches 3.598 V at 55.75 ns. The only self-consistent reading:
`DIVOUT` does not present two clean, separated threshold crossings in this
window at all — it is undergoing one slow, non-monotonic, extended
transition from its `.ic`-forced start, not the crisp two-edge shape a
settled periodic divider would show. This is consistent with, and adds
color to, Finding 3's own "the feedback loop's own propagation delay is
comparable to the top-of-band period" explanation, rather than being an
independent new finding.

**This does not leave the underlying question unanswered.** Finding 3 — a
much lighter-weight, *reliably reproducible* measurement (single-flop
transients, seconds each, not the 316-device whole-chain transient) — already
gives a direct, repeatable answer at the same frequency: `fbfix`'s own
capture reliability fails at every tested setup time up to 300 ps (nearly
half the 640.2 ps period), at all 3 tested corners. **The retiming margin
at the measured top-of-band frequency is therefore judged inadequate for
this specific weak-keeper sizing** — a qualitative conclusion drawn from
Finding 3's clean, reproducible data, not from the whole-chain transient's
own unreliable convergence. No numeric "X ps of margin" figure is claimed;
that specific number stays `insufficient-evidence`, with this record's own
attempts and their real cost stated as the reason, not silently omitted.

## Results tables

### Hold (Finding 2) — `q_end` (`s_end` identical to the last significant figure at every point)

| Corner | as-drawn `q_end` (V) | `fbfix` `q_end` (V) |
|---|---|---|
| `mos_tt`/27 °C/3.3 V | 1.531 | 3.300 |
| `mos_ss`/27 °C/3.3 V | 1.535 | 3.300 |
| `mos_ff`/27 °C/3.3 V | 1.528 | 3.300 |
| `mos_sf`/27 °C/3.3 V | 1.581 | 3.300 |
| `mos_fs`/27 °C/3.3 V | 1.482 | 3.300 |
| `mos_tt`/−40 °C/3.3 V | 1.495 | 3.300 |
| `mos_tt`/125 °C/3.3 V | 1.579 | 3.300 |
| `mos_tt`/27 °C/2.97 V | 1.378 | 2.970 |
| `mos_tt`/27 °C/3.63 V | 1.687 | 3.630 |

### Setup (Finding 3) — `fbfix` `q_sample` (V) vs. `TSU`, all 3 corners

| `TSU` | `mos_tt`/27 °C | `mos_ss`/125 °C | `mos_ff`/−40 °C |
|---|---|---|---|
| 300 ps | −0.016 | −0.009 | −0.031 |
| 200 ps | −0.016 | −0.009 | −0.030 |
| 130 ps | −0.013 | −0.007 | −0.027 |
| 80 ps | −0.007 | −0.003 | −0.014 |
| 40 ps | −0.0001 | −0.0001 | 0.0006 |
| 0 ps | 0.0004 | 0.0008 | 0.0002 |

(As-drawn's own setup curve, for contrast, at `mos_tt`/27 °C: 3.05, 3.05,
3.00, 2.81, 2.72, 0.55 V for the same `TSU` list — a real, monotonic
approach to `VDD`, the opposite shape.)

### Func baseline (Finding 4), 100 MHz, word `000000` (`N=64` structural)

| Variant | Corner | Chain state | Measured `N` |
|---|---|---|---|
| as-drawn | 7 of 9 corners | dead (`0 V` everywhere, `idd=0`) | — (no division) |
| as-drawn | `mos_ss`/27 °C, `mos_tt`/125 °C | anomalous partial toggling | ≈2.0, ≈0.4 (not a clean ratio) |
| `fbfix` | `mos_tt`/27 °C/3.3 V (manual, see Finding 4) | full rail-to-rail, all 5 stages + outputs | **64.00** (exact) |

## Spec-row disposition (per this repo's own CLAUDE.md — no claim without a testbench)

`spec/porting-plan.md` row 3 (multiplication ratio): the ported `N ∈
[4,64]` has already been amended by `spec/decision-records/DR-005-...` to
`N ∈ [64,127]` on structural grounds, noting explicitly that this record
(#36) was tasked with the *functional* confirmation DR-005 itself does not
supply. **This record confirms the structural floor is real and
functional** (one exact simulated calibration point, `N=64.00`, on the
`fbfix` proposal variant) but does **not** independently confirm the
ceiling or intermediate codes by simulation, and does **not** confirm the
*committed* (`asdrawn`) design divides at all — it does not, at any tested
corner. The retiming-margin closure DR-005 explicitly deferred to this
record (its own "What remains open") is answered qualitatively (Finding
5): inadequate, for the specific proposal-variant sizing tested, at the
measured top-of-band frequency — not closed with a numeric bound.

`spec/porting-plan.md` row 11 (power): this record adds one real,
corroborated average-supply-current data point for the `divider_chain`
domain — `idd` ≈ −166 µA at the `fbfix` proposal's 100 MHz/nominal-corner
baseline — alongside the already-measured `vdd_vco` (3.09–8.88 mW,
`sg13cmos5l-vco-duty-cycle`) and `cp` (≈66 µW,
`sg13cmos5l-cp-icp-trim`) domains. The remaining `pfd` and `lock_detector`
domains have since been measured too — `sg13cmos5l-closed-loop-lock` (#37)
at one combined operating point and `sg13cmos5l-lock-detector-window` (#38)
per-domain — both of which landed on `main` while this record was in
review, so row 11 is no longer `insufficient-evidence` for want of an
unmeasured domain. It still has no *clean* whole-PLL total: the
`divider_chain` figure in `sg13cmos5l-closed-loop-lock` (7.653 mA) was
flagged there as very likely inflated by this block's own malfunction, and
this record's ≈166 µA on the repaired `fbfix` variant — ~46× lower, though
at a different variant and operating frequency — corroborates that flag
rather than substituting a like-for-like number. A clean total waits on the
design fixes (issue #56).

## What this does not bound

- **The committed (`asdrawn`) design's own functional N range or retiming
  margin** — it does not function as a divider at any tested corner or
  frequency; Findings 1/2/4 make this a design-level finding, not a
  parameter to characterize.
- **A numeric retiming-margin bound** (e.g. "X ps of margin") for the
  `fbfix` proposal at the top-of-band frequency — `insufficient-evidence`,
  per Finding 5, though the qualitative "inadequate" conclusion is drawn
  from Finding 3's own reliable data.
- **8 of the `fbfix` baseline's 9 corners**, and the word-code sweep
  spanning `N`=65–127 — not completed to a standard this record is willing
  to claim, given the reproducibility finding in Finding 4. The structural
  formula (independent of this record's own simulation) and the one exact
  calibration point are the basis for the stated `N` range instead.
- **5 of the as-drawn `retime` stage's 9 corners** — not run; nothing in
  the 4 corners that were run, or in Findings 1/2/4, suggests a different
  qualitative outcome, but this is stated as a scope limit, not asserted
  as redundant.
- **A repaired, speed-tuned keeper** — the `fbfix` variant is sized only
  for DC correctness (the minimum 3-line fix), not for the top-of-band
  frequency's own settling-time budget. Finding 3's own "sizing property,
  not a structural limit" framing means a faster keeper is a plausible
  future direction, not evidence that no fix exists.
- **Mismatch, layout parasitics, or any post-layout timing** — this record
  is schematic-level only, ideal sources, no parasitic extraction.
- **Reliability/aging** — out of scope for this record as for every sibling
  record in this campaign.
- **The reltol sensitivity cross-check** (`../testbench/run.sh`'s own
  `tol_convergence.csv` output, comparing `reltol=5e-3` against ngspice's
  `1e-3` default) — the script implements it, but it was not reached before
  this session's compute budget for the `func` stage ran out; no
  `../corners/tol_convergence.csv` is committed. Every result in this record
  was run at `reltol=5e-3` (looser than default, for wall-clock reasons, the
  same tradeoff `sg13cmos5l-loop-bandwidth-pm` and other siblings make) and
  is not independently cross-checked against a tighter tolerance.
