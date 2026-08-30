# RECORD-003: closed-loop re-run against the corrected `pfd` (issue #56)

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #56 (Part of #16) — the design-level fix `RECORD-002` (issue
  #50) identified but deliberately did not apply: `design/sg13cmos5l/pfd.sch`'s
  self-reset chain handed `reset` back as `NAND(UP,DN)` (even inverter count
  after `reset_raw`) instead of `AND(UP,DN)` (odd count), forcing both SR
  latches into an always-transparent mode with no phase-error memory. Fixed
  at commit `881d538` (adds a third `inv_hv` stage, `XI1B`, to the reset
  chain — `design/sg13cmos5l/pfd.sch`, netlist re-exported via
  `design/lib/netlist-export.sh`), LVS re-verified at `7fdf4cf` (`pfd`
  66/66 devices, 37/37 nets, `match`), netlist snapshot re-frozen at
  `002975e`.
- **This record does not edit `RECORD-001` or `RECORD-002`** (append-only,
  per this directory's own convention) — it is the full-duration re-run
  issue #56's own Scope item 4 asked for, against the corrected `pfd`.
- **DUT**: the same six real subckts as `RECORD-001`/`RECORD-002`, wired at
  the testbench level exactly as `RECORD-001` describes, with ONE change:
  `pfd` is now the corrected netlist (frozen at
  `../netlist-snapshots/pfd.spice`, commit `4cbf817` per that file's own
  provenance header). `cp`, `loop_filter`, `vco`, `divider_chain`,
  `lock_detector` are byte-identical to `RECORD-001`'s own frozen snapshots.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host — a **different host/arch from `RECORD-001`/`RECORD-002`**
  (both arm64 macOS). No OSDI host constraint applies here either way: this
  host's `cap_cmomi.osdi`/`cap_cmomf.osdi` were not tested directly (the
  substitutions `../testbench/run.sh` already applies for the arm64-macOS
  constraint are reused unconditionally, so this record makes no new claim
  about this host's own OSDI compatibility — see issue #59 for that
  separate, since-resolved question).
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  (no `--quick`, full duration). Writes `../corners/results_as_drawn.csv`,
  `../corners/results_proposal.csv`, `../corners/lock_trace_as_drawn.csv`,
  `../corners/lock_trace_proposal.csv` (all four overwritten in place by
  this record's run — this directory's own convention is that these four
  files hold the LATEST run's numbers, and each dated record quotes the
  specific values it observed rather than relying on the mutable file
  continuing to match). **Runtime on this host, this session**: ~35 minutes
  wall end-to-end (Part A ~9 min, Part B ~26 min) at a host-contention-eased
  rate of ~0.95 ns/s — close to `RECORD-001`'s own ~1 ns/s arm64-macOS
  figure. An earlier attempt in this same session, under heavy concurrent
  host load from other agents' simulations (`uptime` 15-min load average
  14.2 on an 8-core host), ran at ~0.25 ns/s and was terminated by the
  session's own background-task time limit before completing — noted here
  because it is why this record's reproduce command may cost anywhere from
  ~35 minutes to well over an hour depending on concurrent host load, not
  because either number is wrong.

## Results — Part A (as-drawn, committed design)

500 ns simulated, currents averaged over the settled 300–500 ns window
(identical window convention to `RECORD-001`):

| Domain | Current | Power @ 3.3 V |
|---|---|---|
| `pfd` | −13.80 µA | 45.5 µW |
| `cp` | −22.26 µA | 73.5 µW |
| `vco` | −2.628 mA | 8.671 mW |
| `divider_chain` | **−7.698 mA** | **25.40 mW** |
| `lock_detector` | −160.3 µA | 529 µW |

`vctrl`: 2.46 V (IC) → **3.300 V at 500 ns** (avg 3.300 V, range 3.296–3.302 V,
essentially railed at `VDD` = 3.3 V) — `n_ref_cycles_observed = 0`,
`lock_time = None`.

**This is a materially different Part A trajectory from `RECORD-001`'s own
2.401 V-average slow drift** (`RECORD-001`'s Part A, pre-fix `pfd`), and the
difference is exactly what the fix predicts, not a new anomaly: `fb` still
never crosses the logic threshold in this window (the `divider_chain` defect,
issue #36, is untouched by this fix and remains present in the frozen
`divider_chain` snapshot) — but now that `pfd` actually encodes phase
information instead of producing symmetric edge blips, a permanently
low/non-toggling `fb` against a toggling `REF` reads as "`FB` perpetually
late," so the corrected `pfd` asserts `UP` (charge, not discharge) almost
continuously. `vctrl` is driven to the `VDD` rail rather than drifting slowly,
because the loop is now trying (correctly, given its inputs) to correct an
error it structurally cannot close. **Part A's own non-lock stays
independently over-determined by the `divider_chain` defect (#36)**, exactly
as issue #56's own Scope anticipated — this is not evidence the `pfd` fix
is wrong; it is evidence the `pfd` fix is *working*, applied to a loop whose
feedback path is still broken elsewhere.

## Results — Part B (proposal, NOT the committed design)

2.5 µs simulated, currents averaged over the 2.0–2.5 µs window:

| Domain | Current | Power @ 3.3 V |
|---|---|---|
| `pfd` | −57.54 µA | 189.9 µW |
| `cp` | −24.66 µA | 81.4 µW |
| `vco` | −2.012 mA | 6.641 mW |
| `divider_chain` | N/A (behavioural, no real current) | — |
| `lock_detector` | −46.00 µA | 151.8 µW |

`vctrl`: 2.46 V (IC) → 2.387 V at 2.5 µs (avg 2.387 V, range 2.349–2.420 V in
the final 500 ns window). **This is a qualitatively different trajectory from
`RECORD-001`'s own Part B** (2.46 V → 1.720 V, monotonic runaway divergence,
`Δf`/`f_ref` reaching −22.9% with repeated cycle slips): here `vctrl` settles
into a small, bounded, essentially flat range after the first few hundred ns
and stays there for the remaining ~2 µs — no divergence, no cycle slips.

**Frequency lock is achieved; a static phase error remains, outside this
record's own 5% threshold.** Full per-cycle trace:
`../corners/lock_trace_proposal.csv`, 49 reference cycles observed. Over the
final 20 cycles (the last 1 µs, `t` > 1.5 µs — the same window size the row-7
hold criterion itself requires):

| Quantity | Range | Mean |
|---|---|---|
| `Δf/f_ref` | −0.0293% to +0.0068% | −0.0049% |
| Static phase error (fraction of `T_ref`) | 9.110% to 9.196% | 9.176% |

`Δf/f_ref` is comfortably inside the record's own 1% frequency-lock
threshold for the entire final microsecond (peak-to-peak spread 0.036%) —
**the loop is frequency-locked**, a first for this campaign's closed-loop
decks. The static phase error, however, is stable and flat (peak-to-peak
spread across the final 20 cycles: 0.086% of `T_ref`, i.e. ≈43 ps at
`f_ref` = 20 MHz) at **≈9.18% of a reference period (≈4.6 ns)**, roughly
1.8× this record's own 5% threshold (`RECORD-001`'s "Why these durations":
"this record's own re-derivation, stated as one, not a carried-over number"
— 5% was not revisited or loosened here to make this pass; the criterion is
unchanged from `RECORD-001`). **`lock_time = None`** — the row-7 dual
threshold is never held simultaneously for 20 consecutive cycles; the
longest run achieved is 4 cycles, at the very start of the trace (`t` =
50–200 ns), when the initial-condition `VC0` guess is still close and phase
error has not yet grown past 5%.

**This is not a residual convergence tail — the flatness of the final
microsecond is itself the evidence.** `Δf` and phase error are both
essentially constant (not still trending) from ~1.25 µs onward; extending
`TSTOP` further is very unlikely to change this specific outcome (a longer
run is not attempted here on that basis, not because it was too costly to
try). This looks like a genuine converged steady state with a nonzero static
phase offset, not a loop still in the process of acquiring lock.

### Why a static phase offset, not zero: a hypothesis, not a second measurement

A charge-pump PFD-based loop's classic behaviour is zero *static* phase
error at DC (the loop filter's own integrator term should null any constant
phase offset in steady state) — so ≈9.18% is worth a candidate explanation,
stated as a hypothesis this record does not independently confirm:

- **`cp` `UP`/`DN` current mismatch.** `../../sg13cmos5l-cp-icp-trim/corners/results.csv`
  already measured a small but nonzero mismatch between the charge pump's
  `up`- and `dn`-state currents at this same 10 µA trim code (`up`: +10.05 µA,
  `dn`: −10.37 µA at `mos_tt`/27 C — a ≈3% magnitude mismatch,
  `RECORD-001`'s own citation). For the loop to hold zero *net* charge per
  reference cycle with mismatched `Icp_up`/`Icp_dn` magnitudes, the `UP` and
  `DN` pulse widths cannot be equal — which, given how this `pfd` generates
  `UP`/`DN` width from the `REF`-to-`FB` (or `FB`-to-`REF`) edge separation,
  requires a nonzero steady-state phase offset between `REF` and `FB`. A
  ≈3% current mismatch producing a ≈9% phase-offset response is the right
  order of magnitude for this mechanism (the exact gain from current
  mismatch to phase offset depends on loop parameters this record does not
  re-derive here), making it the leading candidate.
- **The reset chain's own added delay (this very fix).** The corrected reset
  chain is one `inv_hv` stage longer (3 gates vs. 2) than the as-drawn
  chain, which widens the minimum `UP`/`DN` pulse width the self-reset loop
  allows before both latches release. A wider minimum pulse changes the
  PFD's own dead-zone/blind-time behaviour but, applied symmetrically to
  both `UP` and `DN` paths (the fix adds one stage to the shared `reset`
  path, not to the `UP` or `DN` path individually), would not by itself
  produce an asymmetric offset — listed for completeness, not as the leading
  candidate.

Neither hypothesis is tested further in this record (would need a dedicated
diagnostic, e.g. re-running Part B with `cp`'s `up`/`dn` currents forced
exactly equal) — flagged as the natural next step if a tighter row-7 pass is
wanted, not undertaken here since it is a new investigation beyond issue
#56's own re-run scope. Filed as follow-up issue #70.

Reference-spur extraction on this deck's own `vctrl` (~−44.4 dBc, computed
the same Goertzel-DFT way as `RECORD-001`) is **not reported as a row-10
measurement** — row 10's own requirement is a stable, *locked* carrier, and
this deck is frequency-locked but not phase-locked within the stated
criterion, so "no stable carrier to define a spur around" still applies,
even though the number itself (−44.4 dBc, vs. `RECORD-001`'s −36.0 dBc) is
directionally consistent with a much quieter `vctrl` than before.

## Row-by-row disposition (updates `RECORD-001`'s/`RECORD-002`'s own call, does not edit them)

- **Row 7 (lock time)**: still `insufficient-evidence` — the row-7 dual
  criterion (`RECORD-001`'s own definition, unchanged here) is not met for
  20 consecutive cycles by either deck. **The finding has changed
  materially, though**: Part B now achieves genuine frequency lock (`Δf`
  within 0.03% of `f_ref` for the full final microsecond, zero cycle slips)
  with a stable, converged static phase error of ≈9.18% of `T_ref` — a
  qualitatively different and much closer outcome than `RECORD-001`'s own
  monotonic ≈23%-and-diverging `Δf` trajectory. The root cause `RECORD-002`
  identified (the `pfd` self-reset parity defect) is confirmed fixed by this
  record's own evidence: it was the mechanism blocking frequency lock
  entirely, not the mechanism responsible for the residual static phase
  offset, which appears (hypothesis, not confirmed) to be a separate,
  smaller effect from `cp`'s own already-measured `up`/`dn` current
  mismatch.
- **Row 10 (reference spur)**: still `insufficient-evidence` — no deck
  reaches a stable, locked carrier per this record's own criterion. The
  computed Goertzel-DFT number for Part B (−44.4 dBc) is reported here for
  context only, not as a row-10 measurement.
- **Row 11 (power)**: not the focus of this record (`RECORD-001` already
  bounded row 11); the domain currents reported above for completeness are
  broadly consistent with `RECORD-001`'s own figures (same order of
  magnitude per domain), with Part A's `vco`/`lock_detector` currents
  somewhat higher here — plausibly downstream of `vctrl` sitting at a
  different operating point (`VDD` rail vs. `RECORD-001`'s 2.40 V average)
  rather than a new finding about either block.

## What this does not bound

- **Single PVT point only** (`mos_tt`/`res_typ`/27 C/3.3 V), same as
  `RECORD-001`/`RECORD-002` — see `../corners/matrix.md`. No corner sweep of
  any number in this record exists.
- **The static-phase-error hypothesis above is not independently tested** —
  stated as the leading candidate, not confirmed. A dedicated diagnostic
  (forcing `cp`'s `up`/`dn` currents equal, or re-deriving the
  current-mismatch-to-phase-offset gain analytically) would be needed to
  close this out; out of this issue's own re-run scope.
- **Part A's own non-lock remains independently over-determined by the
  `divider_chain` defect (issue #36, still open as of this record)** — this
  record's Part A does not newly characterise that defect, only observes
  that a correctly-functioning `pfd` now drives `vctrl` to the rail rather
  than drifting slowly, given `divider_chain`'s still-non-toggling `fb`.
- **Whether row 7's own 5% static-phase-error threshold is the "right"
  number is not revisited here** — `RECORD-001` already stated it as this
  record's own re-derivation, not a carried-over industry figure; this
  record neither loosens nor re-justifies it, even though the observed
  ≈9.18% offset is within a factor of ~2 of it.
- **Whether fixing `divider_chain` (issue #36) changes Part A's own
  disposition** — not re-tested here; `RECORD-001`'s own "Divider chain
  caveat" note about needing a re-run once #36 lands still applies, now
  against the corrected `pfd` as well.
- **No other committed `sim/` record instantiates `pfd`** (re-verified for
  this record, not just trusted from `RECORD-002`'s own claim): a fresh
  `grep -rl pfd sim` (excluding this directory and `sim/README.md`) finds
  only prose mentions in four other records' own "not measured here" notes
  (`sg13cmos5l-vco-duty-cycle`, `sg13cmos5l-loop-filter-momcap`,
  `sg13cmos5l-divider-nrange-retiming`, `sg13cmos5l-lock-detector-window`),
  none of which instantiate the `pfd` subckt. No other record needs
  re-evaluation as a result of this fix.

## Follow-up

Filed as issue #70: a dedicated diagnostic to test the static-phase-error
hypothesis above (`cp` `up`/`dn` current mismatch as the likely
residual-offset mechanism), out of this issue's (#56) own re-run scope.
