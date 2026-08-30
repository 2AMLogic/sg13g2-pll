# sim/ — append-only PVT evidence records

This is the first work to land here (previously "Empty until the first work
lands here" — see the repo README's "Repo layout" and `spec/porting-plan.md`
§1.3, "Testbench / corner-harness structure"). The convention below is
carried over **as-is** from `gf180-pll`'s own `sim/README.md` (itself copied
from `2AMLogic/gf180-bandgap`) per that section's own disposition table — it
is methodology, not circuit data, so it needs no per-PDK re-derivation.

## Directory / naming convention

```
sim/
  <slug>/
    testbench/            ngspice deck(s) + any generator script that builds
                           per-corner netlists from them
    netlist-snapshots/    the exact design/**/netlist/*.spice this record
                           simulated, frozen at commit time -- independent of
                           whatever the live export says today
    corners/               the PVT/sensitivity matrix definition and the raw
                           per-corner results (a CSV or equivalent)
    records/               one Markdown file per run, `RECORD-NNN-<title>.md`,
                           numbered and never edited in place
```

One directory per **claim under test**, not per run — `<slug>` names the
claim (e.g. `sg13cmos5l-loop-filter-momcap`), and every new run against that
same claim adds a new `RECORD-NNN` file, not a rewrite of an old one. A
genuinely different DUT (a different block, a different question) gets its
own sibling slug rather than being folded into an existing one.

**Records are append-only.** A record's conclusion can be superseded by a
later record (e.g. a re-run against an updated netlist), but the old record
stays in place, unedited — the evidence trail is the history, not just the
latest answer.

**Netlist provenance.** Every record's `netlist-snapshots/` freezes the
exact `.spice` export it simulated, plus the commit SHA it was frozen at (in
each snapshot's own header comment) — independent of whatever
`design/**/netlist/*.spice` says by the time someone reads the record later.

**PVT corner matrix.** The default sweep is the full process x supply x temp
matrix; any subset (e.g. a passive network with no supply-dependent device,
so "supply corner" does not apply) must state the reason explicitly in the
record, not silently drop an axis. The corner *count* is PDK-specific — see
each record for the axes it actually swept and why.

**Host requirement — `cap_cmomi`-bearing decks need an x86-64 host, unless
the two MOM-capacitor OSDI models are rebuilt locally first.** The installed
`ihp-sg13cmos5l` tree ships `cap_cmomi.osdi` and `cap_cmomf.osdi` as
**prebuilt x86-64 ELF binaries tracked in upstream git** — unlike
`psp103`/`psp103_nqs`/`mosvar`/`r3_cmc`, which are host-local build products
of the sibling `ihp-sg13g2` tree. On an arm64 macOS host the two therefore
fail `dlopen` ("slice is not valid mach-o file") and every deck that
*instantiates* a `cap_cmomi` device aborts with `Unable to find definition of
model xcap:cap_cmomi_mod`. **That failure is a host/PDK-provisioning gap, not
a broken testbench.** The PDK ships its own fix —
`ihp-sg13cmos5l/libs.tech/verilog-a/openvaf-compile-va.sh` recompiles exactly
those two models from the Verilog-A sources in the same tree — and issue #59
verified on x86-64 that a locally rebuilt model reproduces two whole committed
campaigns byte-identically. What is *not* verified is the arm64 build itself
(OpenVAF-Reloaded publishes no macOS binary, so `openvaf-r` has to be built
from source there first). Read
[`PORTING-osdi-host-arch.md`](PORTING-osdi-host-arch.md) before running any
`sim/` campaign on a non-x86-64 host: it carries the rebuild command, what
stays unverified, and the numeric cross-check a rebuilt model must pass before
it is trusted for a **new** record. `sim/tools/check-osdi-arch.sh` is the
preflight the `cap_cmomi`-loading campaigns call, so they abort with that
diagnosis instead of with ngspice's message. One campaign
(`sg13cmos5l-lock-detector-window`) opts that single object out of the abort
with the preflight's `--soft` flag, because it has a validated closed-form
substitute for it and records which source produced every affected number in
the CSV's own `source` column — see `PORTING-osdi-host-arch.md` § "`--soft`".
Every other object stays a hard abort in every campaign, including that one.

**Closed-loop internal-timestep bound** and **charge-domain PFD/CP
characterization** (the other two `spec/porting-plan.md` §1.3 methodology
items carried over as-is) apply once a closed-loop or PFD/CP testbench
exists. **No record below is a transistor-level closed-loop testbench**, so
the internal-timestep bound still does not apply. The charge-domain PFD/CP
characterization is *partially* engaged as of issue #27:
`sg13cmos5l-cp-icp-trim` characterises the charge pump's own delivered
current and up/down mismatch, but at DC with the switches held static —
the *charge*-domain (per-reference-cycle, switching) part of that
methodology item is still not exercised, and that record says so in its own
"What this does not bound".

## PDK scope — two independent campaigns, one convention

This repo targets two PDKs in parallel (`design/README.md` "SG13CMOS5L
port"): the original SG13G2 design directly under `design/`, and the
SG13CMOS5L port under `design/sg13cmos5l/`. Both campaigns use the directory
convention above, distinguished by the `<slug>` prefix (`sg13cmos5l-*` here;
an unprefixed or `sg13g2-*` slug for the original PDK once that campaign
starts). **SG13G2 still has no `sim/` results of its own** — both campaign
issues to date (#23 and #27, each Part of #16) are scoped to the SG13CMOS5L
port only, and neither adds, edits, or touches any SG13G2 result (there are
none to touch).

## SG13CMOS5L campaign status

Tracks issues #23, #27, #36, #37, #38 and #52 (all Part of #16). #23 owns the
specific obligation `spec/decision-records/DR-003-sg13cmos5l-port-readiness.md`
Finding 2 names: every spec row sensitive to the design's three `cap_cmomi`
MOM-cap instance sites (`loop_filter.XC1`/`XC2`, `vco.XCDECAP`) must be swept
across a plausible MOM-model-uncertainty band, because the installed PDK's
own `cap_cmomi`/`cap_cmomf` models carry **no characterised process-corner
or mismatch spread** (`cornerCAP.lib`'s own header, confirmed directly by
this campaign — see records below) and are "not validated on CMOS5L
silicon." #27 picks up the rows #23 explicitly deferred: the ones needing a
charge-pump characterisation, a loop-level combination of the three
measured block records, or a longer/edge-resolved transient. #36 (split out
of #27) takes row 3 — the `divider_chain`'s own functional N range and
retiming margin — which #27 built an exploratory testbench for but
deliberately never published. #37 (also split out of #27) picks up the
three rows that specifically need a real transistor-level closed loop, none
of which #27's own three records is. #38 measures `lock_detector` (row 16),
never attempted in #27, and closes the MOM-uncertainty gap on its own two
`cap_cmomi` instances (`XCW`/`XDW.XC1`), which are outside DR-003 Finding
2's three-instance list. #52 is the first issue in this campaign to
**change the design and re-measure it**: it re-sizes the three
`lock_detector` devices #38's own record root-caused (`XRPU`, `XCW`,
`XDW.XC1`) and re-runs #38's campaign against the resized block, appending
`RECORD-002` beside `RECORD-001` rather than replacing it. #66 then fixes the
two mechanisms RECORD-002 measured but was out of scope to change
(`schmitt_hv`'s feedback wiring and the `XRPU`/`XMPD` strength ratio) and
runs the campaign a third time, appending `RECORD-003` — closing row 16's
last measurable criterion. The table below is the whole campaign, in the
order the records landed.

| Slug | Claim under test | Spec row(s) (`spec/porting-plan.md` §1.2) | Status |
|---|---|---|---|
| [`sg13cmos5l-loop-filter-momcap`](sg13cmos5l-loop-filter-momcap/) | `loop_filter` R1/C1/C2 corner + MOM-cap-uncertainty sensitivity (zero/pole location) | 6/6a (loop bandwidth / phase margin) | Zero/pole location **bounded** by a real PVT+MOM sweep; the row's own kHz/degree numbers stay `insufficient-evidence` (needed the not-yet-re-derived Kvco table and Icp-trim table; both landed, and `sg13cmos5l-loop-bandwidth-pm` below now closes the row) |
| [`sg13cmos5l-vco-decap-momcap`](sg13cmos5l-vco-decap-momcap/) | `vco.XCDECAP` capacitance value + supply-decoupling pole sensitivity | 8 (period jitter), 12 (supply sensitivity) | Capacitance value **bounded** by a real MOM sweep; the absolute jitter-ps / dB-attenuation numbers stay `insufficient-evidence` (need a post-layout parasitic source impedance and a closed-loop phase-noise method ngspice cannot run today — DR-002 Decision 5) |
| [`sg13cmos5l-vco-kvco-table`](sg13cmos5l-vco-kvco-table/) | Open-loop `vco` frequency vs. `VCTRL` vs. 2-bit band code, real transient sweep (not MOM-cap-sensitive — no `cap_cmomi` instance survives this testbench's own XCDECAP-strip, see that record's "Tooling note") | 4/5 (Kvco bound / band-selection rule) | Kvco-vs-band-code table **bounded** by a real PVT-cornered open-loop sweep (3 corner bundles x 4 band codes x 5 `VCTRL` points); row 6/6a's own loop-bandwidth number is now closed by `sg13cmos5l-loop-bandwidth-pm` below, and row 3 (divider retiming margin) still needs the divider chain's own re-derivation |
| [`sg13cmos5l-cp-icp-trim`](sg13cmos5l-cp-icp-trim/) | `cp` delivered current vs. mirror trim code, and up/down mismatch vs. output voltage (all-MOS DUT — no resistor and no `cap_cmomi` instance, so neither the RES-corner nor the MOM axis applies) | 6/6a (Icp-trim table), 10 (reference spur, mismatch input) | Icp-trim table **bounded** by 306 real DC sweeps (5 MOS corners x 3 temps + a ±10% supply sub-axis x 6 trim codes x 3 switch states): the mirror-referenced ladder tracks its reference to within 0.14% across the whole PVT matrix. Row 10's own dBc number stays `insufficient-evidence` — the *static* mismatch is now real, but a spur level additionally needs switching charge mismatch, the PFD reset window, and a stable loop to define a carrier |
| [`sg13cmos5l-loop-bandwidth-pm`](sg13cmos5l-loop-bandwidth-pm/) | Linearised open-loop gain around the **real** `loop_filter` subckt, with `Icp` and `Kvco` taken from the two measured records above | 6/6a (loop bandwidth / phase margin) | **`insufficient-evidence` CLEARED — and the bound is a failure to meet the criteria.** `f_c` = 0.33–4.64 MHz, PM = 1.55–20.33° across 90 real-subckt AC runs; **0 of 90 meet the ≥45° criterion** with the as-drawn filter, and `Icp` cannot trade one criterion against the other. A separate proposal sweep (`corners/proposal.csv`, explicitly *not* the committed design) shows `R1` ×20 with the 10 µA trim code meets both criteria at every PVT bundle. Also records that the ported `f_ref` = 1–25 MHz / `N` = 4–64 rows are mutually inconsistent with the measured VCO band |
| [`sg13cmos5l-vco-duty-cycle`](sg13cmos5l-vco-duty-cycle/) | Open-loop `vco` output duty cycle (rising *and* falling 50%-of-rail crossings), plus the ring's own average supply current | 13 (output duty cycle), 11 (power, one domain) | Duty cycle **bounded** by 300 real transient runs (5 MOS corners — including the `mos_sf`/`mos_fs` split corners the Kvco record left open — x 3 temps x 4 band codes x 5 `VCTRL` points): 43.74–51.56%, with **30 of 300 points below the 45% floor**, all at −40 C. Reproduces gf180-pll's own carried-forward duty-cycle design flag on a different process. Row 11 stays `insufficient-evidence` (only the `vdd_vco` and `cp` domains are measured) |
| [`sg13cmos5l-closed-loop-lock`](sg13cmos5l-closed-loop-lock/) | Transistor-level closed loop (`pfd`+`cp`+`loop_filter`+`vco`+`divider_chain`+`lock_detector`, testbench-local wiring — no `pll_top` schematic exists), single PVT point (runtime-cost subset, see that record's own `corners/matrix.md`) | 7 (lock time), 10 (reference spur), 11 (power, remaining domains) | **Row 11 bounded** (with caveats): all five remaining domains measured simultaneously at one operating point — `pfd`+`cp`+`vco`+`lock_detector` = 2.483 mA (8.20 mW); `divider_chain` alone = 7.653 mA (25.26 mW), but flagged as very likely inflated by that block's own known malfunction (see below), not a clean design figure. **Rows 7 and 10 stay `insufficient-evidence`**, but the `pfd` self-reset inverter-parity defect `records/RECORD-002` (issue #50) root-caused is now **fixed and re-verified** (`records/RECORD-003`, issue #56): with the corrected `pfd`, the proposal loop (Part B) achieves genuine **frequency lock** (`Δf`/`f_ref` within 0.03% of `f_ref` for a full microsecond, zero cycle slips — vs. `RECORD-001`'s own monotonically-diverging ≈23% `Δf`) but settles at a stable **static phase error of ≈9.18% of a reference period**, ~1.8× this record's own 5% row-7 threshold, so the dual lock criterion is still not met. **`records/RECORD-004` (issue #70) then confirms the mechanism**: an ideal, diagnostic-only substitution forcing `cp`'s `up`/`dn` currents to be exactly equal (NOT a change to the committed `cp`) collapses the static phase error to a mean of −0.00235% (from 9.176%, `RECORD-003`'s own final-20-cycle window) and to simulator floating-point noise in the fully-settled tail, while also extending the longest continuous dual-lock run from 4 cycles to 41. RECORD-004's own decision: this is a design-level `cp` current-mirror-matching defect worth mitigating, not an acceptable residual — filed as issue #72. The as-drawn loop (Part A) still does not lock, independently over-determined by the separate `divider_chain` defect (#36) |
| [`sg13cmos5l-lock-detector-window`](sg13cmos5l-lock-detector-window/) | Real-subckt `lock_detector` assert window, hysteresis, chatter and supply current, plus the `XCW`/`XDW.XC1` MOM-uncertainty sensitivity | 16 (lock-detector targets), 11 (power, one more domain) | **`RECORD-001` (#38, pre-resize): window, hysteresis and no-chatter all bounded, and all three fail the ported criteria at every corner.** Window = 0.219–0.409 ns (target ≥2.5 ns); no hysteresis resolves at the ladder's 0.15×-window step at any of 92 points (target ≥25% of window); **92/92 points chatter**, including at a 10×-window static phase error. Cause is measured directly: the integrating node's own `XRPU`·`XCW` time constant (0.71–1.71 ns) is 23–1412× shorter than the reference period across the whole ported 1–25 MHz range, so `VWIN` fully re-settles every cycle regardless of phase-error size. The ±20% MOM band moves the window 7–8% (not the dominant term) and does not change the chatter/no-hysteresis verdict at any point. Static-phase-offset comparison stays `insufficient-evidence` (needs an unmeasured PFD/CP record); `lock_detector`'s own supply current (0.79–60.3 µA) is bounded, corroborating the combined figure in the `sg13cmos5l-closed-loop-lock` row above with a dedicated per-domain measurement.<br><br>**`RECORD-002` (#52, post-resize): `XRPU` `l=6u`→`l=700u`, `XCW` `w=8u l=8u`→`w=40u l=40u`, `XDW.XC1` `w=4u l=4u`→`w=40u l=40u` — the window and no-chatter criteria now PASS.** Window = 3.688–11.24 ns against the ≥2.5 ns floor at 81/81 points (worst-case margin 1.475×, including an explicit worst-case axis stack RECORD-001's grid did not contain); `steady` at 18/18 ladder corners at a 10×-window static phase error, at both ends of row 2's DR-005-amended 3.5–24.4 MHz range; `R·C` = 2.29–5.58 µs = **8.0–19.5×** the slowest reference period (6.4–23.4× including the ±20% MOM band), against 23–1412× *below* it before. **Hysteresis still fails** (<20% of window vs ≥25%), and RECORD-002 separates the cause into two measured terms that are both outside the three devices #52 resized: `schmitt_hv`'s feedback devices are tied to the wrong rails (0.9–1.6 mV measured, vs 881–979 mV for the classic connection) and — binding over that — the settled-`VWIN`-vs-phase-error transition is ≤0.05× the window wide, set by the `XRPU`/`XMPD` strength ratio, so rewiring the Schmitt alone measurably changes nothing. Row 11's `lock_detector` domain re-bounded at 2.48–95.1 µA for the resized block. One fixed sizing covers the whole amended `f_ref` range, so **row 2 needs no narrowing and no decision record is owed** |
| [`sg13cmos5l-divider-nrange-retiming`](sg13cmos5l-divider-nrange-retiming/) | `divider_chain` functional N range + `XFRT` retiming margin at the measured top-of-band frequency, plus the chain's own average supply current | 3 (multiplication ratio / retiming margin), 11 (power, one more domain) | **The committed (as-drawn) design does not function as a divider at any of 9 tested corners** — its `dff_tg_hv` hold path is a self-biased inverter, not a real latch (0/9 corners hold at the rail; settles to a process/supply-dependent mid-rail voltage instead). This is the block-level root cause of the same non-toggling feedback node `sg13cmos5l-closed-loop-lock`'s Part A independently observed in a real closed loop. A proposal variant (`fbfix`, not committed) with a minimal 3-line hold-path fix holds cleanly at the rail in 9/9 corners and divides by exactly `N=64` (one exact simulated calibration point) at a 100 MHz low-frequency baseline, matching the structural `N ∈ [64,127]` formula's floor. Retiming margin at the measured top-of-band frequency (1562.0 MHz) is judged **inadequate** for this specific proposal sizing (its own single-flop setup-time sweep fails to capture at every tested `TSU` up to 300 ps, at all 3 tested corners) — no numeric margin bound is claimed (`insufficient-evidence`, whole-chain transient convergence was not reliably reproducible in this session). The missing-reset / OP-convergence gap is recorded as its own design finding, not routed around. On row 11: the functional `fbfix` variant draws ≈166 µA average at the 100 MHz baseline, ~46× below the 7.653 mA the closed-loop record measured for the as-drawn `divider_chain` — corroborating that row's own flag that its figure is inflated by the malfunction rather than a clean design number (different variant and operating frequency, so corroboration, not a like-for-like substitute) |

**Still deferred, and explicitly `insufficient-evidence`** (follow-up issues
filed off #27, each Part of #16):

| Spec row | Why it is still open |
|---|---|
| 3 — divider retiming margin, numeric bound only (#36) | The functional half of this row is now **closed** by `sg13cmos5l-divider-nrange-retiming` (above): the committed design does not divide at any tested corner (root cause: a `dff_tg_hv` hold path that is a single inversion loop, not a bistable latch — the same defect `sg13cmos5l-closed-loop-lock`'s Part A saw as a non-toggling feedback node), and a proposal variant's low-frequency `N=64` behaviour is bounded against the structural `N ∈ [64,127]` range. What remains open is the narrower gap: the specific top-of-band (1562.0 MHz) retiming-margin *number* stays `insufficient-evidence` — the whole-chain transient there was not reliably reproducible within that session's compute budget, so the qualitative "inadequate margin" conclusion rests on a lighter-weight single-flop setup-time sweep instead |
| 7 — lock time (#37) | `sg13cmos5l-closed-loop-lock` attempted this directly. `records/RECORD-001` found neither loop acquiring lock; `records/RECORD-002` (issue #50) root-caused Part B's own non-convergence to a `pfd` self-reset inverter-parity defect; `records/RECORD-003` (issue #56) fixes that defect and re-runs both decks. Part B now **frequency-locks** (zero cycle slips, `Δf`/`f_ref` within 0.03% of `f_ref` held for the full final microsecond) but settles at a stable ≈9.18%-of-`T_ref` static phase error, above the 5% threshold this record's own row-7 criterion uses. `records/RECORD-004` (issue #70) then **confirms** the previously-stated-but-unconfirmed hypothesis: a diagnostic-only substitution forcing `cp`'s `up`/`dn` currents exactly equal collapses that residual to noise-level (mean −0.00235%, vs. 9.176%) and extends the longest dual-lock-holding run from 4 to 41 cycles, with the reset-chain delay-symmetry candidate correspondingly ruled out as a material contributor. Still `insufficient-evidence` for the COMMITTED design (no mitigated `cp` has been built or verified yet — that is issue #72's own scope), but the causal chain is now bounded rather than merely plausible, and a specific design-level mitigation path (tighten `cp`'s current-mirror matching) is identified. Part A still does not lock, independently over-determined by the separate `divider_chain` defect (#36) |
| 10 — reference spur (#37) | `sg13cmos5l-closed-loop-lock` attempted this directly; stays `insufficient-evidence` — even post-`pfd`-fix (`records/RECORD-003`, issue #56), Part B is frequency-locked but not phase-locked within row 7's own criterion, so there is still no stable, locked carrier to define a spur around per this row's own requirement |

Row 16 (lock-detector window/hysteresis/chatter) is no longer deferred —
`sg13cmos5l-lock-detector-window` (#38) bounds it, and the bound is a
failure to meet the ported criteria at every corner; (#52) then re-sizes
the block and re-measures it — the assert-window and no-chatter criteria
now pass at every corner re-measured, the hysteresis criterion still fails
with its cause now separated into two measured terms outside that resize's
own scope, and the "≥ 2× worst static phase offset" half of the row stays
`insufficient-evidence` (see the campaign table
above). Row 11 (power) is likewise no longer deferred as a whole: every
domain has now been measured somewhere in the campaign table — `vdd_vco`
(#27), `cp` (#27), the five remaining domains simultaneously at one
operating point (#37), `lock_detector` per-domain (#38) and
`divider_chain` per-domain (#36) — though the as-drawn `divider_chain`
figure carries the malfunction caveat noted in both of those rows, so a
clean whole-PLL total still waits on the design fixes (#56). Row 3 is the
only row above whose *functional* question is answered while a numeric
sub-bound stays open. None of the remaining deferred rows is
MOM-cap-sensitive in DR-003 Finding 2's own sense, so they remain outside
that record's specific obligation even though they are open
`spec/porting-plan.md` "re-derive" rows.

## Provenance of this convention

Per `spec/porting-plan.md` §1.3: this directory structure and its
append-only discipline are carried over from `2AMLogic/gf180-pll`'s own
`sim/README.md` (itself copied from `2AMLogic/gf180-bandgap`) — a
methodology convention, not circuit data, so no SG13G2/SG13CMOS5L
re-derivation applies to the convention itself.
