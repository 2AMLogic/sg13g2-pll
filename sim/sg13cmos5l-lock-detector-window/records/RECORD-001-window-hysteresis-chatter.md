# RECORD-001: lock-detector assert window, hysteresis, chatter, and power

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #38 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L PVT
  campaign)
- **DUT**: the real, unmodified `lock_detector` subckt
  (`../netlist-snapshots/lock_detector.spice`, frozen from
  `design/sg13cmos5l/netlist/lock_detector.spice` at commit `fbebbdb`
  (main, after PR #39); content unchanged since PR #26, and still identical
  at this record's own HEAD, `6bc843c`) — `XOR(UP,DN)` &rarr; `delaywin_hv`
  coincidence gate &rarr; `rhigh`/`cap_cmomi` integrator &rarr; `schmitt_hv`
  readout. Every measurement below is transistor-level, real-subckt; there
  is no linearised or behavioural stand-in anywhere in this record.
- **Claim under test**: `spec/porting-plan.md` row 16 (assert window
  &ge; 2.5 ns / &ge; 2&times; worst static phase offset, hysteresis &ge; 25%
  of window, no chatter — "port the target structure as-is; re-derive the
  numbers, and budget margin from the start against the specific failure
  gf180-pll already found"). Also closes the `lock_detector.XCW` /
  `XDW.XC1` MOM-uncertainty gap `design/README.md` records as "remains
  open" (neither instance is in DR-003 Finding 2's own three-instance list),
  and adds `lock_detector`'s own supply current to row 11 (power).
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host. `set num_threads=1` (see `../testbench/run.sh`'s own tooling
  note — ngspice's OpenMP matrix solve spins on its barriers on a deck this
  small, ~100x slower with the default thread count on this host).
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  writes `../corners/rc_extract.csv` (15 rows), `../corners/window.csv` (92),
  `../corners/schmitt.csv` (45), `../corners/ladder.csv` (92),
  `../corners/ladder_raw.csv` (1288), `../corners/tstep_convergence.csv`
  (12). Full run time on this host: ~65 minutes (dominated by the 92
  phase-error-ladder transients, each instantiating 31 `lock_detector`
  copies).

## Headline result

**At every one of the 92 (PVT &times; resistor-corner &times; MOM-band
&times; supply &times; reference-frequency) points swept, the block
chatters and no hysteresis is resolvable.** The measured comparator window
(0.219–0.409 ns) is also 6–11&times; below the ported 2.5 ns floor. Both
failures trace to a single, specific, measured cause: the integrating
node's own `R&middot;C` time constant (`XRPU`&middot;`XCW`, 0.71–1.71 ns
across the full R/C corner range) is **23–56&times; shorter than the
fastest reference period tested (40 ns @ 25 MHz), and 584–1412&times;
shorter than the slowest (1000 ns @ 1 MHz)**. `VWIN` therefore recovers to
within a few mV of its rail in well under one reference period regardless
of the phase error's size, so the detector cannot integrate a persistent
"wide" condition across reference cycles at all — it re-derives, on this
process, the same shape of failure gf180-pll's own port flagged
(`spec/porting-plan.md` row 16's disposition text), but the SG13CMOS5L
manifestation is a structural R/C sizing shortfall present at **every**
corner tested, not a marginal shortfall at one extreme corner.

This is measured, not argued: the recovery-copy transient (`trec`,
0.70–2.19 ns to cross mid-rail from a full discharge) and the direct R/C
extraction (`rc_extract.csv`) both independently show the same one-to-two
order-of-magnitude gap to the reference period, and the phase-error ladder
shows the behavioural consequence (100% chatter) that follows from it.

## Mechanism, read from the netlist

`../netlist-snapshots/lock_detector.spice`: `XRPU` (`rhigh`, weak pull-up)
charges `VWIN` toward `VDD` between error pulses; `XMPD` (an NMOS switch
gated by `WIDE`) discharges `VWIN` to `VSS` whenever the coincidence gate
fires. `XCW` is the only capacitance at that node in the schematic (plus
whatever parasitic load `schmitt_hv`'s input adds, not separately
extracted here). This is a leaky integrator by construction — its entire
job is to average `WIDE` pulses over *many* reference cycles so that a
single spurious wide-error pulse does not, by itself, toggle `LOCK`. That
only works if `R&middot;C &gg; T_ref`. The measured values are the reverse:
`R&middot;C` &ll; `T_ref` at every corner and every reference frequency in
the ported 1–25 MHz range (row 2), so the "integrator" instead tracks
`WIDE` almost combinationally, cycle by cycle.

## Post-fix verification (issue #54)

**What changed.** All five `../testbench/*.sp.tmpl` files carried the PDK
path into their `.lib`/`.include` lines as a literal `$PDK_ROOT/$PDK`;
issue #54 switched them to `@PDK_ROOT@`/`@PDK@` tokens that
`../testbench/run.sh` (and, for the ladder skeleton,
`../testbench/gen_ladder.py`'s new `--pdk-root`/`--pdk`) substitute with the
resolved filesystem path before ngspice sees the deck — the convention
PR #55 landed for the sibling issue #43. Every `ngspice -b` call in
`run.sh` also now goes through `run_ngspice_or_die`, which keeps ngspice's
stderr and stops on a non-zero exit instead of discarding it with
`2>/dev/null` (two of the five call sites additionally had `|| true`).

**The failure mode this removes, demonstrated directly.** ngspice resolves a
`$VAR` inside a `.lib`/`.include` line only if that variable is in ngspice's
*own process environment*. Running the pre-fix `tb_window` deck with
`PDK_ROOT`/`PDK` merely unexported (`env -u PDK_ROOT -u PDK ngspice -b
wpre.sp`) gives `Error: Cannot read environmental variable PDK_ROOT` and
`ERROR: fatal error in ngspice, exit(1)`; the patched deck, generated with
the same tokens substituted, runs to completion under the identical stripped
environment and prints `twin_r = 2.894635e-10`. The committed results in
this record were **not** produced through that failure path — they were run
with both variables exported, which is why no row here is `NA` — but the
deck's correctness no longer depends on that.

**Silent absorption, also demonstrated.** On the verification host (below),
`cap_cmomi.osdi` fails to load, which is fatal for any deck instantiating it.
The *pre-fix* `run.sh` reacts by exiting 1 after the `[R]` block with **no
diagnostic whatsoever** (`set -o pipefail` propagates the failure, but
`2>/dev/null` had already thrown away the reason); the patched `run.sh`
prints `ERROR: ngspice exited non-zero for c.sp:` followed by ngspice's
actual `Error opening osdi lib …` text. Same abort, a stated cause instead
of a blank one.

**What was re-run, and what reproduced.** Verification host for this fix:
macOS 26.6.2 / arm64, `ngspice-47`, same `~/share/pdk`, `PDK=ihp-sg13cmos5l` —
**not** the x86-64 Linux / `ngspice-46` host that produced the committed
data (see "Tooling" above).

- `rc_extract.csv`'s **9 `XRPU` rows re-ran end-to-end through the patched
  `run.sh` and are byte-for-byte identical** to the committed file.
- `tb_window.sp.tmpl` at `mos_tt`/`res_typ`/27 °C/3.3 V/`ideal0.00`
  reproduces `window.csv`'s committed row **exactly**: `twin_r =
  2.89463e-10`, `twin_f = 2.97452e-10`.
- The full phase-error ladder at that same point (through the patched
  `gen_ladder.py gen --pdk-root/--pdk`, 31 `lock_detector` copies, ~2 min)
  reproduces the committed `ladder.csv` row **exactly in every column except
  the two supply-current columns**, which come out 0.08% higher
  (`idd_inlock` 1.964260e-05 vs 1.962670e-05 A; `idd_outlock` 4.949770e-05
  vs 4.945770e-05 A). Both settled-state strings (`IIIITTTTTTTTTT`), the
  assert/de-assert thresholds, the zero hysteresis, the `chatter` verdict and
  `trec` are bit-identical, so **no conclusion in this record moves**.
- That 0.08% delta is **not** caused by the fix: re-running the *pre-fix*
  ladder deck (literal `$PDK_ROOT/$PDK`, both variables exported so ngspice
  resolves them) on this host produces a row bit-identical to the patched
  run's. The residual is a host/ngspice-version difference (47 vs 46), which
  is the expected place for an averaged branch current to move.

**What could not be re-run here, stated plainly.** The full 92-point campaign
did **not** complete on this host. `ihp-sg13cmos5l` ships
`libs.tech/ngspice/osdi/cap_cmomi.osdi` (and `cap_cmomf.osdi`) as prebuilt
**x86-64 ELF** objects, while the neighbouring `psp103`/`mosvar`/`r3_cmc`
OSDI files in this install are arm64 Mach-O; `dlopen` therefore refuses
`cap_cmomi.osdi` ("slice is not valid mach-o file") on an arm64 macOS host,
and no `openvaf` is available locally to rebuild it. Every deck that
instantiates `cap_cmomi` — the `C` half of `rc_extract.csv`, and all
`real`-variant window/ladder/Schmitt runs — is therefore unrunnable here and
was not re-derived. The `ideal`-variant decks above are runnable precisely
because `mom_inject.py` replaces those instances with ideal linear
capacitors. Reproducing the whole matrix requires an x86-64 Linux host (or a
locally rebuilt arm64 `cap_cmomi.osdi`); tracked as its own follow-up rather
than silently claimed here.

**Net**: the committed numbers below stand as-is. Nothing in this record was
re-derived; the subset that could be re-run on this host reproduces exactly
(or, for two averaged current columns, to 0.08% for a reason shown to be
independent of the fix).

## Results — R/C extraction (`../corners/rc_extract.csv`)

| Device | Corner axis | Range |
|---|---|---|
| `XRPU` (`rhigh`, w=0.5u l=6u) | `res_bcs`/`res_typ`/`res_wcs` &times; −40/27/125 °C | 11.84 kΩ (`res_bcs`/125 °C) – 28.63 kΩ (`res_wcs`/−40 °C) |
| `XCW` (`cap_cmomi`, w=8u l=8u m=1) | temperature only (no corner/mismatch spread — see below) | 59.82 fF, constant across −40/27/125 °C |
| `XDW.XC1` (`cap_cmomi`, w=4u l=4u m=2, inside `delaywin_hv`) | temperature only | 27.29 fF, constant across −40/27/125 °C |

Both `cap_cmomi` extractions land within 0.3% of `design/README.md`'s own
placeholder-sizing estimate (60 fF / 27 fF), and are **exactly** flat across
temperature — direct, measured confirmation of `cornerCAP.lib`'s own header
claim that every corner/mismatch/stat section maps to the same nominal
model (also confirmed independently by `sg13cmos5l-loop-filter-momcap` and
`sg13cmos5l-vco-decap-momcap` at their own geometries).

`R&middot;C` (`XRPU`&middot;`XCW`) at each resistor-corner/temperature
combination: **0.708 ns** (`res_bcs`/125 °C, fastest) **– 1.713 ns**
(`res_wcs`/−40 °C, slowest). For comparison, `spec/porting-plan.md` row 2's
ported reference range is 1–25 MHz, i.e. `T_ref` = 40 ns – 1000 ns — the
R·C time constant sits **23–1412&times;** below `T_ref` across the full
matrix, never approaching it.

## Results — comparator window (`../corners/window.csv`, 92 rows)

`twin_r` (the `delaywin_hv` chain's own low&rarr;high propagation delay,
which is the quantity row 16's "assert window" target applies to,
measured directly on a bare `delaywin_hv` with an ideal step in):

| | Value |
|---|---|
| Full matrix range | **0.219 – 0.409 ns** |
| Nominal (`mos_tt`/`res_typ`/27 °C/3.3 V/25 MHz, `real`) | 0.289 ns |
| Ported target (row 16) | &ge; 2.5 ns |

**The window itself is 6.1–11.4&times; below the ported 2.5 ns floor at
every corner tested**, independent of the chatter finding below — even a
hypothetically perfect integrator built around this comparator window
would still fail row 16's absolute-window criterion as drawn.

**Cross-check (`ideal0.00` vs. `real`)**: replacing both `cap_cmomi`
instances with an ideal linear cap at their own measured nominal value
changes `twin_r` by at most **0.0057%** across all 21 corner bundles —
confirms the MOM-band injection method (below) is not itself distorting
the window.

**Timestep-convergence check (`../corners/tstep_convergence.csv`)**: `twin_r`
at 4 representative corners, at 20 ps / 5 ps / 1.25 ps maximum internal
timestep, changes by &le; 0.6% end to end (e.g. `mos_tt`/`res_typ`/27 °C/
`real`: 289.45 ps &rarr; 287.82 ps). `twin_r` is not a discretisation
artifact.

## Results — MOM-uncertainty band on `XCW` / `XDW.XC1`

Following the `tb_loop_ac_lumped.sp.tmpl` precedent (extract the real
value, re-inject as an ideal element scaled by the band, cross-check
against the real subckt — see `../testbench/mom_inject.py`'s own header for
why a parallel delta capacitor was rejected here specifically, unlike the
loop-filter record: a negative delta cap on `delaywin_hv`'s switching
output node aborts the transient with "Timestep too small").

| | `ideal−0.20` | `ideal0.00` | `ideal+0.20` | pk-pk spread |
|---|---|---|---|---|
| `twin_r`, at fixed corner (typ example) | 277.8 ps | 289.5 ps | 300.1 ps | ~7.7% of window |
| pk-pk spread across all 21 corner bundles | | | | **7.0 – 8.2%** of window |

The band moves the window by less than a tenth — it is not the dominant
term against the 2.5 ns floor (the floor is missed by 6–11&times;, the MOM
band alone accounts for <10%). **The chatter/hysteresis finding above is
unchanged across all four DUT variants (`real`, `ideal−0.20`, `ideal0.00`,
`ideal+0.20`) at every one of the 92 corner points** — this is not a
MOM-model-uncertainty-driven marginal result; it reproduces identically
with the two un-swept instances replaced entirely.

**`design/README.md` update**: this record closes the "not covered by this
update; their hysteresis-window sensitivity remains open" note on
`lock_detector.XCW`/`XDW.XC1` — see the design/README.md edit accompanying
this record.

## Results — Schmitt-readout hysteresis (`../corners/schmitt.csv`, 45 rows)

`schmitt_hv`'s own trip points, measured on the isolated sub-block with a
quasi-static triangular ramp (5 MOS corners &times; 3 temperatures &times;
3 supplies; no resistor and no `cap_cmomi` instance inside `schmitt_hv`, so
neither the RES-corner nor the MOM axis applies — stated, not silently
dropped):

| | Range |
|---|---|
| `V_TH,rising` | 1.255 – 1.764 V |
| `V_TH,falling` | 1.254 – 1.763 V |
| Hysteresis (`V_TH,rising` − `V_TH,falling`) | **0.88 – 1.58 mV** |
| Hysteresis as % of `VDD` | **0.025% – 0.053%** |

The Schmitt trigger's *own* input-referred hysteresis is a small fraction
of a percent of `VDD` at every corner. That is not, on its own, why row
16's 25%-of-window hysteresis criterion is missed — the phase-error
hysteresis criterion is stated on `VWIN`'s *dynamics*, and with
`R&middot;C &ll; T_ref` the node fully re-settles every cycle regardless of
how sharp the Schmitt trip is. Recorded here so the mechanism is
attributable: the readout element is not the bottleneck; the integrating
node's time constant is.

## Results — phase-error ladder: assert / de-assert / chatter (`../corners/ladder.csv`, 92 rows)

Ladder methodology: each corner's own measured `twin_r` scales a
14-point phase-error ladder (0.25&times;–10&times; the window, dense at
1.00–2.50&times; in 0.15&times; steps); each point instantiates the DUT
twice — once starting fully discharged (assert candidate), once fully
charged (de-assert candidate) — see `../corners/matrix.md` for the full
axis table and rationale.

| Metric | Result |
|---|---|
| Chatter verdict | **`chatter` at 92/92 points** (LOCK swings &gt;80% of `VDD` inside the settle window even at the deepest, 10&times;-window, unambiguous out-of-lock phase error) |
| Resolvable hysteresis | **0/92** — the assert and de-assert thresholds land on the *exact same* ladder point (same `tau/twin_r` fraction) at every single corner; no point resolved any difference at the ladder's 0.15&times;-window step |
| Assert/de-assert threshold fraction observed | 1.15&times; window (88/92 points) or 1.30&times; window (4/92, all at the `ideal+0.20` MOM variant) |
| In-window `LOCK` rail | `lo` at all 92 points (the block's own zero-phase-error copy settles `LOCK` low; read from the block itself, not assumed — see `../testbench/tb_lock_ladder.sp.tmpl`'s polarity note) |
| Recovery time `trec` (discharged &rarr; mid-rail, zero-phase-error stimulus) | **0.70 – 2.19 ns** |
| Supply current, in-lock steady state (`idd_inlock`) | **0.79 – 23.2 µA** |
| Supply current, out-of-lock steady state (`idd_outlock`) | **2.0 – 60.3 µA** |
| 1 MHz / 5 MHz reference sub-axis (`mos_tt`/`res_typ`/27 °C) | Same `chatter` verdict, same 0-hysteresis result — **the finding does not depend on the 25 MHz main-grid frequency**; row 2's whole 1–25 MHz ported range is covered by the same failure |
| Supply sub-axis (2.97 V / 3.63 V, `mos_tt`/`res_typ`) | Same `chatter` verdict at every temperature |

**Reading "0/92 resolvable hysteresis"**: the ladder's step size is
0.15&times; the window, well below the 25%-of-window criterion, so this is
a real bound, not a resolution artifact — true hysteresis is confirmed
below 15% of the window (and most likely far below it, given assert and
de-assert never once diverged even at the finest step tested) at every
corner, against a &ge;25% target.

## Static phase offset comparison — `insufficient-evidence`

Row 16's second criterion ("assert window &ge; 2&times; worst static phase
offset") needs the PFD/CP's own static phase offset. No record in `sim/`
bounds that today: `sg13cmos5l-cp-icp-trim` characterises the charge
pump's *static current mismatch* at DC with the switches held, explicitly
not the switching/charge-domain behaviour a static phase offset comes out
of (`sim/README.md`'s own deferred-rows table, row 10), and `pfd` has no
record at all. This half of row 16's criterion is marked
`insufficient-evidence`, per this repo's CLAUDE.md ("no claim without a
testbench") — not silently assumed either way. The first half of the
criterion (the 2.5 ns absolute floor) needs no such dependency and **is**
bounded above (missed, by 6–11&times;).

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 16 — lock-detector assert window**: **bounded, and the bound is a
  failure to meet the criterion.** Window = 0.219–0.409 ns against a
  &ge;2.5 ns floor, at every one of 92 corner points, including the MOM
  band and the full 1–25 MHz reference range. `insufficient-evidence` is
  **not** applicable here — this half of the row is fully measured.
- **Row 16 — hysteresis &ge; 25% of window**: **bounded, and the bound is a
  failure to meet the criterion.** No hysteresis resolves at the ladder's
  0.15&times;-window step at any of 92 points; true hysteresis is confirmed
  &lt;15% of window (likely far less) against the 25% target.
- **Row 16 — no chatter**: **bounded, and the bound is a failure to meet
  the criterion.** 92/92 points chatter, including at the deepest
  (10&times;-window) static phase error, where a functioning detector
  should sit steady at the out-of-lock rail.
- **Row 16 — static phase offset comparison**: **`insufficient-evidence`**
  — needs a PFD/CP static-phase-offset record that does not exist yet
  (see above). Does not block the three bounds above, which are
  independent of it.
- **Row 16 — `XCW`/`XDW.XC1` MOM-uncertainty sensitivity**: **bounded.**
  ±20% band moves the window by 7.0–8.2% (not the dominant term); the
  chatter/no-hysteresis finding is unchanged across all four DUT variants.
  `design/README.md`'s "remains open" note is updated by this record.
- **Row 11 — power (`lock_detector` domain)**: **bounded.** In-lock
  0.79–23.2 µA, out-of-lock 2.0–60.3 µA across the full PVT/MOM/supply/
  reference-frequency matrix. `pfd` and `divider_chain` remain unmeasured,
  so `sim/README.md`'s whole-PLL power total stays `insufficient-evidence`
  pending those (row 11's own follow-up, #37).

## What this does not bound

- **Random device mismatch.** No per-instance mismatch model is exercised
  for `sg13_hv_nmos`/`sg13_hv_pmos`, and `cap_cmomi` has none at all in the
  installed PDK. The `mos_sf`/`mos_fs` corners bound *systematic*
  NMOS-vs-PMOS skew only.
- **Post-layout parasitics.** Schematic-level only. `VWIN` is a
  high-impedance node whose own layout capacitance and leakage would move
  both the time constant and the recovery time — the block's layout landed
  in PR #39 but no extracted netlist is exported yet.
- **The static phase offset half of row 16's criterion** — see above.
- **A fix.** This record measures and attributes the cause (`R&middot;C
  &ll; T_ref` by 1–3 orders of magnitude); it does not resize `XRPU` or
  `XCW`, which is a design decision outside this issue's own scope
  (measurement, per `spec/porting-plan.md` row 16's "re-derive the numbers"
  disposition, is exactly what this record delivers). The sizing fix is
  filed as issue #52 (Part of #16), mirroring how
  `sg13cmos5l-loop-bandwidth-pm`'s own filter-resize proposal was filed as
  a separate issue (#41) rather than folded into that record's own scope.
