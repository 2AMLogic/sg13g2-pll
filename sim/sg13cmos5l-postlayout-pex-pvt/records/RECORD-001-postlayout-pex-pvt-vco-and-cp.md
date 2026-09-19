# RECORD-001: post-layout (PEX) PVT re-simulation of `vco` and `cp`

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #30 (Part of #16) — the named follow-up #24's acceptance
  criteria required when #24 scoped post-layout PVT out.
- **DUT**: `pll_vco` and `pll_cp`, the subcircuits `klt extract --deck
  sg13cmos5l --parasitics --pdk ihp-sg13cmos5l` produced from the **routed**
  GDS of layout record `20260830-204105-457cf5b`, plus — as a control arm —
  the frozen schematic netlists the two campaigns being compared against
  already simulated.
- **Tooling**: `ngspice-46`; `klt 0.4.0` (`klayout-tools` at a pin carrying
  both #2012 and #2126); installed `~/share/pdk/ihp-sg13cmos5l`; x86-64 Linux
  host.
- **Reproduce**:
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./extraction/run-pex.sh`
    → `netlist-snapshots/*.pex.{spice,json}`, `provenance.json`
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
    → `corners/results.csv` (120 rows)
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_cp.sh`
    → `corners/cp_results.csv` (612 rows)
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_rc_attribution.sh`
    → `corners/rc_attribution.csv` (210 rows)
  - `./testbench/analyze.py`
    → `corners/deviation.csv`, `corners/control.csv`, and every roll-up
      number quoted below
  - `LVS_KLT_PYTHONPATH=<klayout-tools>/src ./lvs-recheck/run-lvs-recheck.sh`
    → `lvs-recheck/summary.json`

---

## 1. Were real extracted parasitics modelled? — **Yes. Stated in as many words.**

Issue #30's acceptance criterion 3 requires this to be said explicitly and
never implied, so:

> **Real, extracted, curated-coefficient interconnect parasitics were
> modelled.** Every number in `corners/results.csv`'s `postlayout` arm and
> `corners/cp_results.csv`'s `postlayout` arm was simulated against a netlist
> carrying klt-extracted parasitic resistors and capacitors derived from the
> routed layout's own drawn geometry, using the curated `sg13cmos5l` metal
> R/C coefficient table. **No metal level fell back to a zero coefficient**,
> on any block: `metals_without_coefficient` and
> `overlap_pairs_without_coefficient` are **empty lists** for all six blocks
> in `netlist-snapshots/provenance.json`, and `warnings[]` is empty in every
> per-block report. The extracted **device** geometry (drawn W/L plus
> junction `AS`/`AD`/`PS`/`PD`) is likewise real, and is also present on the
> post-layout arm.

### 1.1 Why this is a different answer than the issue text expects

Issue #30's own body (and the Curator pass that wrote it) records that
`klt extract --deck sg13cmos5l --parasitics` succeeded but reported
`r_count`/`c_count` of **0**, with all five metal levels listed in
`parasitics.metals_without_coefficient` — tracked upstream as
**klayout-tools#2113**, open at the time that pass ran, and it explicitly
instructed this record to disclose that zero-wire-parasitics gap.

**That is no longer the state of the tool, and this record re-verified it
live rather than trusting either the issue text or the prior extraction
commit.** klayout-tools#2113 was **closed 2026-09-19T05:12:15Z** via
**klayout-tools#2126** ("populate sg13cmos5l nominal metal parasitics"),
which lands a curated five-level `LayerRC` table (Metal1 through TopMetal1)
plus four adjacent-level overlap coefficients, each transcribed from the
PDK's own public magic tech file with the source line cited per entry. The
verification done here:

1. Re-read klayout-tools#1440 / #2012 / #2113 / #2126 / #1463 / #1466 live —
   all six closed.
2. Probed a fresh `klt extract --deck sg13cmos5l --parasitics` on
   `pll_loop_filter.gds`: `r_count=2`, `c_count=2`,
   `total_resistance_ohm=4.84`, `total_capacitance_ff=1.742548`,
   `metals_without_coefficient=[]`, `warnings=[]`.
3. Re-ran `extraction/run-pex.sh` end-to-end on all six blocks from a clean
   checkout of `klayout-tools` `origin/main`. **All twelve
   `netlist-snapshots/*.pex.{spice,json}` files reproduce byte-identically**
   to the ones already committed; the only textual difference anywhere is the
   `klt_version` string in `provenance.json` (`0.4.0+g729ee531e176` vs. this
   session's `0.4.0+unknown`, an artifact of running from a `git archive`
   export with no `.git`). The prior Builder's extraction is therefore
   independently reproduced, not taken on trust.

`extraction/run-pex.sh` additionally **hard-fails** rather than producing a
netlist that would be labelled "post-layout" without being one: its preflight
aborts if `metals_without_coefficient` is non-empty or if `r_count`/`c_count`
is zero.

### 1.2 What the coefficients are, and are not

klayout-tools' own `LayerRC` docstring is explicit that these are
"**representative, uncalibrated, order-of-magnitude starter values**" from
public process data, with silicon calibration an explicit non-goal. They are
real numbers with a cited public source, not placeholders — but nobody should
read a post-layout number here as silicon-correlated. The extraction model is
also first-order by construction (from the extracted netlists' own header):
one lumped series resistance per net distributed as a star across that net's
device terminals (not a distributed RC ladder — `--distributed-rc` was not
requested), quasi-static frequency behaviour, vertical-overlap coupling
modelled, lateral same-layer coupling modelled only for declared
`--critical-net` nets (none were declared here), and no fringe shielding.

### 1.3 Per-block extraction totals (`netlist-snapshots/provenance.json`)

| Block | Devices | Nets | R | C | C_couple | ΣR (Ω) | ΣC (fF) | metals w/o coeff |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `pll_pfd` | 66 | 37 | 264 | 37 | 543 | 2 900.36 | 680.65 | — (none) |
| `pll_cp` | 20 | 18 | 80 | 18 | 88 | 914.86 | 219.40 | — (none) |
| `pll_loop_filter` | 1 | 3 | 2 | 2 | 0 | 4.84 | 1.74 | — (none) |
| `pll_vco` | 44 | 33 | 170 | 33 | 311 | 2 393.04 | 558.81 | — (none) |
| `pll_divider_chain` | 316 | 142 | 1 264 | 142 | 7 850 | 44 894.26 | 10 389.76 | — (none) |
| `pll_lock_detector` | 38 | 23 | 151 | 23 | 161 | 1 292.67 | 305.12 | — (none) |

Deck content hash `sha256:1912f174…` (`released: false`), PDK variant
`ihp-sg13cmos5l`, layout record `20260830-204105-457cf5b`.

---

## 2. Results — `pll_vco`, the ratified Kvco matrix

120 transient runs (60 per arm), **0 `NA`**. `corners/results.csv`.

### 2.1 The control arm reproduces the original campaign exactly

Before any deviation can be attributed to layout, the control has to be
shown to be a control. It is:

> The schematic arm reproduces **60 of 60** committed
> `sg13cmos5l-vco-kvco-table/corners/results.csv` frequencies with **max
> |delta| = 0.000000%** (`corners/control.csv`).

This also retires the only methodological difference between this record and
that one: the 30 ns transient window used in place of the original 40 ns
moves **no** committed number.

### 2.2 Headline deviation

| | Schematic (control) | Post-layout (PEX) |
|---|---|---|
| Output band, all 60 points | 445.26 – 1561.97 MHz | **223.68 – 789.50 MHz** |
| Kvco average, per bundle×band | 144.2 – 422.4 MHz/V | **67.6 – 207.6 MHz/V** |
| Kvco peak local | 182.6 – 590.2 MHz/V | **85.2 – 293.4 MHz/V** |

Per-point ratio (`corners/deviation.csv`), **60 of 60 points**:

| | min | mean | max |
|---|---|---|---|
| f_postlayout / f_schematic | 0.4768 (−52.32%) | 0.5074 (−49.26%) | 0.5312 (−46.88%) |

Broken out — the spread is small and the trends are weak, which matters for
the analysis in §4:

| Axis | value | min Δ | mean Δ | max Δ |
|---|---|---|---|---|
| bundle | `fast` | −49.46% | −47.84% | −46.88% |
| bundle | `typ` | −50.78% | −49.17% | −48.09% |
| bundle | `slow` | −52.32% | −50.77% | −49.76% |
| band | `00` | −51.22% | −48.90% | −46.88% |
| band | `11` | −52.32% | −49.53% | −46.88% |
| `VCTRL` | 0.3 V | −49.76% | −48.25% | −46.88% |
| `VCTRL` | 2.7 V | −52.32% | −50.37% | −48.24% |

---

## 3. Results — `pll_cp`, the ratified Icp-trim matrix

612 DC sweeps (306 per arm), **0 `NA`**. `corners/cp_results.csv`.

`cp` was chosen as the second DUT for one specific reason: it is one of the
three blocks whose LVS **matches** (§5), so a deviation measured here is
attributable to the extracted parasitics and not to an unverified topology.

Control arm vs. the committed `sg13cmos5l-cp-icp-trim/corners/results.csv`:
**max |delta| = 0.000049%** over all 306 points (not byte-identical only
because this record's CSV writer uses a different float precision).

| Switch state | n | max abs. ΔIcp | ratio range |
|---|---:|---|---|
| `up` | 102 | 0.506 µA | **+0.0547% … +0.6323%** |
| `dn` | 102 | 0.169 µA | **+0.0170% … +0.2107%** |
| `both` | 102 | 0.339 µA | **≤ 0.424% of the trim code** |

(`both` is reported in absolute terms because it is a near-cancellation of
two nearly-equal currents — its schematic |Icp| falls to 7 nA, so a ratio
there divides by the mismatch under test and says nothing about loading.)

Up/down mismatch, the quantity `sg13cmos5l-cp-icp-trim` actually tracks,
is essentially unmoved: schematic −0.888% … −0.081%, post-layout −0.575% …
+0.341%; at the nominal `mos_tt`/27 °C/3.3 V/10 µA point, −0.170% (schematic)
vs. −0.052% (post-layout).

**Conclusion for `cp`: extracted interconnect parasitics change the ratified
Icp-trim table by less than 0.7% at every one of 306 PVT points.** The trim
table stands post-layout.

---

## 4. Deviation analysis — not just reported

### 4.1 The `cp` and `vco` results are not in tension; together they are the analysis

The same extraction flow, the same host, the same ngspice, the same
PEX-to-ngspice transform, applied to two blocks from the same layout record,
moves a **DC** measurement by <0.7% and a **ring-oscillator frequency** by
~50%. That is the expected signature of a purely capacitive loading effect:
a DC operating point is blind to capacitance (the parasitic resistance —
914.9 Ω total across `cp`'s 18 nets — is negligible against a cascoded
current source's output impedance), while a self-timed oscillator's period is
almost exactly linear in the capacitance it has to charge.

It also rules out the most likely *artifact* explanation for the VCO number:
if the `pex-to-ngspice.py` transform, the `make-inst.py` port derivation, or
the substrate tie were introducing an error, the `cp` arm would not agree
with its own control to five decimal places.

### 4.2 Which parasitic caused it — measured, not argued

`corners/rc_attribution.csv`: 30 points of the same matrix against seven
variants of the *same* extracted netlist, touching only parasitic R/C cards
(the device-card count is asserted identical across all seven, and the script
refuses to write a variant where it moved).

| Variant | What it isolates | Δ vs. schematic control (min / mean / max) |
|---|---|---|
| `none` | extracted **devices** only, zero interconnect | −0.95% / **−0.69%** / −0.52% |
| `r_only` | + parasitic resistance | −2.17% / **−1.40%** / −1.04% |
| `c_only` | parasitic capacitance, resistors shorted | −51.73% / **−48.83%** / −46.55% |
| `full` | everything (reproduces §2.2) | −52.32% / **−49.21%** / −46.88% |

Reading, in order:

1. **The extracted devices are not the cause.** `none` — the extracted
   netlist's own drawn W/L and junction `AS`/`AD`/`PS`/`PD`, with every
   interconnect parasitic removed — sits within **0.95%** of the schematic
   arm at every point. The layout's devices are, electrically, the
   schematic's devices. This is a load-bearing negative result: without it,
   this record could not distinguish "the wires did this" from "the extracted
   junctions did this".
2. **Parasitic resistance is not the cause either.** `r_only` adds at most a
   further **1.2 percentage points**. Despite 2 393 Ω of total extracted
   resistance, the per-net values (2.5 Ω on `VCTRL` up to 128 Ω on `ring1`)
   are small against the current-starved ring's own multi-kΩ effective drive
   impedance.
3. **Parasitic capacitance is essentially the whole effect** — `c_only`
   reproduces `full` to within 1.6 percentage points, i.e. **≈99% of the
   deviation**.

### 4.3 Why the deviation is so nearly constant across PVT

A ring oscillator's period is `N · C_node · ΔV / I_drive`. Adding a
PVT-independent `C_par` in parallel with the intrinsic `C_int` multiplies the
period by `(C_int + C_par)/C_int` — a ratio in which the drive current,
process corner, temperature and band code all cancel. That is exactly what is
observed: a −46.9% … −52.3% band, i.e. ±2.7 percentage points of spread
across a 3-bundle PVT sweep, 4 band codes and the matrix's own 3.5×
schematic frequency span (445.3 → 1562.0 MHz).

The residual trends are consistent and second-order:

- **More deviation at the `slow` bundle than at `fast`** (−50.8% vs. −47.8%
  mean). `C_int` is dominated by device junction/overlap capacitance, which
  is itself process- and temperature-dependent, so the `C_par/C_int` ratio is
  not perfectly constant.
- **More deviation at high `VCTRL`** (−50.4% at 2.7 V vs. −48.3% at 0.3 V).
  At high `VCTRL` the ring is faster and the `r_only` term (an RC pole on the
  same nodes) becomes a larger fraction of the shrinking stage delay.

Inverting the mean ratio: `C_par ≈ 0.97 · C_int`, i.e. **the routed
interconnect roughly doubles every ring node's capacitance**. That is directly
corroborated by the per-net extraction: `ring1`…`ring5` carry 18.8–29.4 fF
each, of which 11.3–18.6 fF is on **Metal2** — the layer this flow's router
puts its backbones on.

### 4.4 The floorplan caveat, quantified

**This 2× slowdown is an upper bound set by routing style, not a property of
the circuit, and must not be read as a post-layout prediction for a real
floorplan.** The caveat is not rhetorical; it is measurable in the layout
record's own `compose.*.json`:

| Block | Routed wire length (0.3 µm wide) |
|---|---|
| `pll_divider_chain` | **147 145 µm** (147 mm) |
| `pll_pfd` | 8 651 µm |
| `pll_vco` | **7 178 µm** |
| `pll_lock_detector` | 3 727 µm |
| `pll_cp` | 2 336 µm |
| `pll_loop_filter` | 9 µm |

7.18 mm of wire for a ~45-device ring VCO is not a floorplan; it is an
artifact of `layout/bin/cmos5l_route.py`'s single-channel routing style
(already recorded in `layout/sg13cmos5l-pll/README.md` § "What it is not").
Per net, `ring1` alone is routed **413.1 µm** — a node a compact ring layout
closes in single-digit microns.

To say how much of the headline number that artifact is worth, the same 30
points were re-run with every parasitic capacitance scaled by k
(`cscale*` in `corners/rc_attribution.csv`). **This is a parametric
sensitivity bracket, not a prediction** — a uniform scalar also scales
device-adjacent and via capacitance, which a shorter route would not:

| Parasitic C scale | mean Δ vs. schematic |
|---|---|
| ×1.00 (as routed) | −49.21% |
| ×0.25 | −20.74% |
| ×0.10 | −10.29% |
| ×0.05 | −6.09% |

So the conclusion a reader should take is **not** "this VCO runs at half
speed post-layout". It is: *on this non-representative floorplan the ring
loses half its frequency, and the loss is ~99% capacitive and roughly linear
in routed wire length, so a floorplan with an order of magnitude less wire on
the ring nodes would land in the −6% … −10% region.* A real number requires a
real floorplan, which this port does not have and which no upstream issue
currently tracks.

### 4.5 What this does NOT do to the ratified spec

The post-layout band (223.7 – 789.5 MHz) sits roughly a factor of two below
the measured schematic band (445.3 – 1562.0 MHz) that
`spec/decision-records/DR-005` used to amend row 2 (`f_ref` → 3.5–24.4 MHz)
and row 3 (`N` → 64–127). **This record does not propose amending either
row**, and deliberately so: per the repo's own rule that agents do not relax
the ratified spec to make results pass — and equally do not tighten it on
evidence that is known non-representative — a band derived from a floorplan
whose ring node carries 413 µm of routed Metal2 is not a basis for moving a
ratified row. It is recorded here as an open risk for whoever builds the
first real floorplan, not as a spec input.

---

## 5. LVS status — re-verified live, and it changed

Issue #30 required re-checking LVS before writing any deviation analysis,
because a "deviation" on a block whose layout was never confirmed to be the
same circuit as its schematic could be the topology difference talking.

The committed layout record's own artifacts show `pfd`/`cp`/`divider_chain`
compared (exit 0) and `loop_filter`/`vco`/`lock_detector` **never compared at
all** — `klt lvs` refused to convert their subckt-call reference netlists
because `cap_cmomi` was not a known device for the deck. That is not "LVS
failed"; it is "LVS did not run", and it is exactly the three blocks whose
schematics instantiate a MoM capacitor.

`lvs-recheck/run-lvs-recheck.sh` re-runs all six at the current klt, changing
**one** thing: it adds the `reference.device_map` entry klt's own error
message names (`cap_cmomi` → `{"kind": "capacitor"}`) for the blocks whose
reference netlists actually instantiate it. Same GDS, same reference netlist,
same deck, same flatten options. Results (`lvs-recheck/summary.json`):

| Block | Verdict | Devices matched | Notes |
|---|---|---|---|
| `pll_pfd` | **match** | 66/66, nets 37/37 | 0 errors |
| `pll_cp` | **match** | 20/20, nets 18/18 | 0 errors |
| `pll_divider_chain` | **match** | 316/316, nets 142/142 | 0 errors |
| `pll_loop_filter` | **mismatch** | **0/3**, nets 1/4 | newly comparable |
| `pll_vco` | **mismatch** | 38/45, nets 25/34 | newly comparable |
| `pll_lock_detector` | **not compared** | — | `cap_cmomi` with `m=2` |

Three things follow, and the record states each rather than implying it:

1. **`cp`'s post-layout numbers (§3) rest on a confirmed
   layout↔schematic topology match.** 20/20 devices, 18/18 nets, 0 errors.
2. **`pll_vco`'s post-layout numbers (§2) do NOT.** There is no clean
   topology match to compare against. Its mismatch is 7 unmatched reference
   devices — the undrawn `DECAP` (`cap_cmomi`; the routed cell has 44 of the
   schematic's 45 devices, the missing one being the MoM decap the deck
   cannot draw) plus the six `XBIAS` `rppd`/`rhigh` resistors, alongside one
   `net.merged` error collapsing the reference's `BIAS.SUB!` into a single
   layout net. The resistor non-pairing most plausibly follows from that
   substrate-net merge in a flattened compare rather than from a miswire —
   but **this record did not root-cause it, and does not claim to**. The
   honest statement is: *the VCO deviation in §2 could in principle contain a
   contribution from an unverified topology difference, and §4.2's
   attribution bounds how large that contribution can be — the `none` variant
   shows the extracted device network by itself reproduces the schematic
   frequency to within 0.95%, which is as close to an electrical topology
   cross-check as this record can get without a clean LVS.*
3. **`pll_lock_detector` still cannot be compared at all.** The blocker is no
   longer the missing device class but a different, documented limitation:
   `m=2` on a `cap_cmomi` card "describes a multi-finger/multiplied device the
   curated plain-element form cannot represent". `layout/sg13cmos5l-pll/
   README.md` already records this as deliberate, not a gap — unchanged here.

`loop_filter` deserves one more sentence, because it explains why this record
does not re-simulate it: its routed cell contains **one** device (the `rppd`
resistor) against the schematic's three, both `cap_cmomi` capacitors being
undrawn, and LVS matches **0 of 3**. Its extracted netlist is real (2 R, 2 C,
1.74 fF) but it is not a loop filter, so a "post-layout loop filter" result
would be a fiction regardless of how well the parasitics were extracted.

---

## 6. What this record does not bound

- **Any block other than `vco` and `cp`.** Every routed block has a committed
  parasitic-annotated netlist (AC 1), but only these two were re-simulated.
  See `corners/matrix.md` § "Axes this record does NOT sweep".
- **Anything on a plausible floorplan.** See §4.4. Every post-layout number
  here is an upper bound on parasitic loading for this routing style.
- **Silicon correlation.** The coefficients are the deck's own uncalibrated
  public-data starter values (§1.2).
- **Coupling between blocks, or any top-level.** Each block was extracted
  standalone; there is no `pll_top` layout.
- **Distributed RC.** One lumped star per net; `--distributed-rc` and
  `--critical-net` were not used, so no per-segment ladder and no lateral
  same-layer coupling was modelled on any net.
- **Closed-loop behaviour.** Lock time, spur, jitter — none of the
  `sg13cmos5l-closed-loop-lock` rows are re-run here.

## 7. Friction encountered (and where it went)

Per the repo's friction protocol, each item was checked before being called
a gap:

- **`klt extract --parasitics` emits three-terminal `R` cards for deck-
  recognised `rppd`/`rhigh` resistors**, which ngspice cannot parse (an `R`
  card takes two nodes). `testbench/pex-to-ngspice.py` rebinds them to the
  PDK's own resistor subcircuit call — the identical binding the schematic
  netlist uses — and self-checks that no parasitic R/C card count changes.
  This is a real tool gap, and it is already filed as
  **[klayout-tools#1157](https://github.com/2AMLogic/klayout-tools/issues/1157)**
  (*"klt extract's bare (non-`--pdk`) output for a 3-terminal drawn-resistor
  class is not ngspice-simulatable"*, **open**). Rather than open a duplicate,
  this pass recorded a
  [confirmation comment](https://github.com/2AMLogic/klayout-tools/issues/1157#issuecomment-5740464634)
  on it (2026-09-19) that **narrows that issue's own scope condition**: the
  3-node `R` card is emitted *with* `--pdk` supplied too — MOS devices bind to
  the PDK subcircuits, the resistor still does not — so the gap is not limited
  to bare mode as the title says. The comment also records the exact rewrite
  used here and its cost (the extractor's own resistance value is discarded,
  because the PDK subcircuit recomputes R from W/L).
- **`klt extract` writes hierarchical net names joined with a `.`** — a net
  that came from a sub-instance is written `XBIAS.n2s`. `.` is ngspice's own
  hierarchy separator, so `v(xvco.XBIAS.n2s)` is parsed as a path through an
  instance that does not exist in the flattened cell: the node cannot be
  probed, `.meas`'d or `.ic`'d by its written name, which for a `--parasitics`
  netlist is exactly the set of internal nodes a post-layout run wants to look
  at. `testbench/pex-to-ngspice.py` (transform 1) rewrites `A.b` → `A_b`,
  matched only where the dot sits between two identifier characters, so
  numeric literals (`L=0.28U`) and dot commands (`.SUBCKT`/`.ENDS`/`.GLOBAL`)
  are never touched. Filed upstream as
  **[klayout-tools#2145](https://github.com/2AMLogic/klayout-tools/issues/2145)**
  (**open**, new this pass; the net-name sibling of #1157's device-card gap).
  The workaround is not free and the issue says so: the simulated net names
  diverge from the names in the extraction JSON report and the SPEF, so
  cross-referencing any result in this record back to those artifacts is a
  manual mapping step.
- **ngspice's OpenMP fan-out is a large pessimization on these netlists.** One
  post-layout point costs 10.9 s wall / 64 s CPU at the default thread count
  and **0.87 s wall / 0.86 s CPU** at `set num_threads=1`, returning the
  identical `per1 = 3.900038e-09`. Both `run.sh` and `run_cp.sh` now pin it.
  Not filed upstream — this is an ngspice build/tuning property, not a
  klayout-tools gap.
- **Not a tool gap, a mistake this record made and corrected**: the first
  `run_cp.sh` pass omitted `VSS=0` from the `make-inst.py` pin mapping,
  leaving the extracted cell's ground pin floating at the top level. It
  produced Icp ratios from +200% to −362 253% against the schematic arm — an
  obviously non-physical result, caught because the control arm existed.
  Recorded in `run_cp.sh`'s own header so the next reader does not rediscover
  it, and named here because "a post-layout arm that silently miswires a
  surfaced pin" is the most likely way this whole method produces a confident
  wrong answer.
