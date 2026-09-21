# RECORD-003: post-layout (PEX) arms for `pfd` and `lock_detector`

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #102 (Part of #16) — sub-issue B of the #100 split of #30's
  post-layout follow-on; the two blocks RECORD-001 deferred for runtime
  budget and this record now measures.
- **DUT**: `pll_pfd` and `pll_lock_detector`, the subcircuits `klt extract
  --deck sg13cmos5l --parasitics --pdk ihp-sg13cmos5l` produced from the
  **routed** GDS of layout record `20260830-204105-457cf5b` (the same six
  committed extractions RECORD-001 verified and re-reproduced
  byte-identically), plus — as control arms — the frozen schematic netlists
  the campaigns being compared against already simulated, and one
  diagnostic-only derived variant (see §3.1).
- **Tooling**: `ngspice-46`; `klt 0.4.0+g729ee531e176` (the committed
  extraction pin; not re-run here — RECORD-001 §1.1 already re-verified all
  twelve `netlist-snapshots/*.{spice,json}` byte-identically); installed
  `~/share/pdk/ihp-sg13cmos5l` equivalent at `/home/ubuntu/share/pdk/`;
  x86-64 Linux host (`cap_cmomi.osdi` loadable — the arm64 constraint that
  forced ideal-cap substitutions into the sibling
  `sg13cmos5l-lock-detector-window` RECORD-002's host does not apply here).
- **Reproduce**:
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_pfd.sh`
    → `corners/pfd_results.csv` (12 rows), `corners/pfd_control.csv`
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_lock_detector.sh`
    → `corners/ld_rc_extract.csv` (15 rows),
      `corners/ld_rc_control.csv` (15 rows),
      `corners/ld_window_control.csv` (102 rows),
      `corners/ld_window_control_delta.csv` (102 rows),
      `corners/ld_window.csv` (85 rows),
      `corners/ld_ladder.csv` (32 rows),
      `corners/ld_ladder_raw.csv` (288 rows),
      `corners/ld_tstep_convergence.csv` (6 rows),
      `corners/ld_solver_retries.txt` (empty — no deck needed the
      `trtol=1` retry)
  - `python3 ./testbench/analyze_pfd_ld.py`
    → `corners/ld_deviation.csv` (29 rows) and every roll-up number
      quoted below

---

## 1. What was re-simulated, and the controls that make it a measurement

Real extracted parasitics are the inherited state RECORD-001 §1 established
and re-verified live — same extraction commit, same per-block reports, no
fallback anywhere: `pfd` carries 264 extracted resistors and 37 substrate
+ 543 coupling capacitors (680.65 fF total) over 8 651 µm of routed wire;
`lock_detector` carries 151 resistors and 23 + 161 capacitors (305.12 fF)
over 3 727 µm. This record adds no extraction of its own.

What this record ADDS is the control discipline the two new blocks need,
because neither is a `cp`-style one-arm story:

1. **The committed campaigns reproduce byte-identically here, in full.**
   This host re-ran the *entire* committed lock-detector window matrix —
   102 points, including the committed MOM-band variants, supply and
   reference-frequency sub-axes, and the worst-case stack — plus all 15
   committed device-extraction rows, via the sibling campaign's own
   templates and helpers used unmodified:
   **102/102 window points and 15/15 R/C rows byte-identical**
   (`ld_window_control_delta.csv`, `ld_rc_control.csv`, zero deltas).
   The harness, host and method are therefore provably identical to the
   machinery that produced the numbers this record deviates from. This is
   this record's `control.csv` equivalent, at full committed-matrix
   density.
2. **The pfd's schematic control arm reproduces the committed campaign to
   −0.52%** — `pfd_control.csv`: this host measures 0.374470 V / 0.044328 V
   (reflead UP/DN) against the committed `fixed` rows 0.376443 /
   0.046307, and the mirrored fblead pair to the same deltas. Not
   byte-identical, and the two causes are named and bounded: the committed
   `fixed` rows were measured (a) with the diagnostic patch's reset chain
   (a literal third `inv_hv`) rather than the productionised XI1B +
   `inv2x_hv` chain now frozen in the snapshot, and (b) on the campaign's
   own host. Both arms below use the productionised snapshot — the
   netlist the routed cell LVS-matches 66/66 — so the A/B deviation is
   attributable to the extraction.
3. **`pfd` is one of the three LVS-matched blocks** (66/66 devices, 37/37
   nets, 0 errors — `lvs-recheck/summary.json`, §5), so its post-layout
   deviation cannot hide a topology difference.
   **`lock_detector` still has no LVS at all**, so this record does not
   paper over it: §3.1 replaces it with measured device-set evidence, and
   the deviation analysis is structured so the interconnect effect is
   isolated on a common device set regardless.

---

## 2. Results — `pll_pfd`, the ratified polarity-diagnostic point

Matrix D (§corners/matrix.md): the campaign's single ratified PVT point
(`mos_tt`/27 °C/3.3 V), its stimulus (20 MHz, fixed per-cycle lead/lag),
both arms, plus this record's own offset axis (10 %, 20 %, 40 % of the
reference period) because the ratified-offset result below needs bounding
to be interpretable. `corners/pfd_results.csv`. 12 runs, no NA.

### 2.1 REF leads: textbook, uniformly widened by +0.53 ns

| Offset | Schematic UP hold | Post-layout UP hold | Δ |
|---|---|---|---|
| 5 ns (ratified) | 5.674 ns (11.35 % duty) | 6.199 ns (12.40 %) | **+0.525 ns** |
| 10 ns | 10.674 ns | 11.199 ns | **+0.525 ns** |
| 20 ns | 20.674 ns | 21.199 ns | **+0.525 ns** |

The UP hold is `offset + reset-arc`; the post-layout arm adds a flat
+0.525 ns at every offset — the extracted interconnect stretches the
self-reset arc (the DN-side blip that ends UP's assertion widens 0.67 →
1.20 ns, the same +0.53 ns). The relative duty error falls from +9.3 % at
the ratified 10 %-of-period offset to +2.5 % at 40 %, exactly as a
constant additive delay should.

### 2.2 FB leads: the detector reads the COMPLEMENTARY phase

The schematic arm is textbook at every offset (DN-dominant: 11.3 %, 21.3 %,
41.3 % duty). The post-layout arm **inverts the steady state**: UP holds
`(T_ref − τ + 0.2 ns)` and DN never holds at all —

| Offset | Schematic UP / DN duty | Post-layout UP / DN duty |
|---|---|---|
| 5 ns (ratified) | 1.35 % / 11.35 % | **92.40 % / 2.39 %** |
| 10 ns | 1.35 % / 21.35 % | **82.40 % / 2.39 %** |
| 20 ns | 1.35 % / 41.35 % | **62.40 % / 2.39 %** |

This is a genuine steady mode, not a startup transient: the averages are
bit-identical in every 100 ns window across a 800 ns extended check
(six digits), and the offset sweep scales exactly as `(T_ref − τ)/T_ref`.
The mechanism was traced at the node level (a 296–358 ns window of
`up/dn/reset_raw/reset_d1/reset_d2/reset/ref/fb`): the reset chain is
not broken — every reset pulse fires, correctly, on every both-asserted
event. What the parasitics do is slow the input→latch edges (DN's
assertion is ~1.4 ns behind FB's edge at 100 ps stimulus edges; ~0.65 ns
rise times), and in the FB-lead orientation that inverts the race: DN
sets while the previous cycle's UP is *still held*, so the both-up event
kills DN ~1.2 ns after its birth — DN never survives the 5 ns to the next
REF edge — and every following REF edge re-asserts UP with no DN present.
The latch pair consequently settles into the complementary branch and
reports "REF leads by T_ref − τ". At 20 MHz reference and a 5 ns (10 %)
lead, **the routed PFD's phase discrimination is inverted on the
FB-leading side.**

**Conclusion for `pfd`:** extracted interconnect parasitics do not
threaten the reset architecture (the chain pulses and re-arms every
cycle) but add ~+0.5 ns to every internal arc, which widens the
REF-leading pulse by a benign +9.3 % at the ratified offset — and, on
the FB-leading side at this reference frequency, flips a textbook
discriminator into reporting the complementary phase. The schematic
control arm distinguishes the two.

---

## 3. Results — `pll_lock_detector`, and the three-way attribution

### 3.1 What the routed cell actually is (measured, not assumed)

LVS remains unrunnable for this block — the committed limitation RECORD-001
§5 reports (`m=2` multi-finger `cap_cmomi` reference conversion) is
unchanged — so the device-set evidence is stated geometrically, from the
extraction itself:

| Device/group | Committed crowbarfix | Extraction of the routed cell | Match |
|---|---|---|---|
| `XRPU` (rhigh) | `w=0.5u l=700u` | `L=700U W=0.5U` | ✓ (#52 resize) |
| `XMPD` | `w=0.25u l=16u` | `L=0.5U W=2U` | **no — #52-era** |
| `schmitt_hv` (6 devices, wiring + lengths) | rewired, `l=2u` | classic wiring, `l=0.5u` | **no — pre-#66** |
| `XCW` (`cap_cmomi` 40 µm × 40 µm, m=1) | 1.691 pF (measured here, byte-identical to the campaign) | **absent** | — |
| `XDW.XC1` (`cap_cmomi` 40 µm × 40 µm, m=2) | 3.382 pF | **absent** | — |

`netlist-snapshots/pll_lock_detector.pex.json`: `device_counts` =
19 nfet + 18 pfet + 1 rhigh — **zero `cap_cmomi`**, while `device_classes`
lists the class, so the caps are absent from the layout, not unrecognised.
**The routed device set is the #52-resize revision minus exactly its two
MOM capacitors** — the same defect class as `loop_filter`'s undrawn caps
(RECORD-001 §5), and additionally two revisions behind the committed
design (#66's XMPD resize and rewiring, #76's channel-length change).
Neither the committed crowbarfix snapshot nor any other committed
snapshot is the routed cell's schematic.

The comparison is therefore built three-way, and `corners/matrix.md`
Matrix E records the reasoning:

- **control** (committed crowbarfix): byte-identical reproduction of the
  entire committed window matrix + device extraction, §1 — anchors the
  committed design's numbers as measured;
- **`aslayout`** (the diagnostic-only twin): the frozen resize snapshot
  with exactly the two `cap_cmomi` cards removed
  (`testbench/derive_ld_as_layout.py`, programmatic, asserted, never
  written back) — the device set the layout carries;
- **`postlayout`** (the extraction). `postlayout` vs `aslayout` then
  isolates the interconnect on a common device set; `aslayout` vs the
  committed control isolates the missing-cap + revision-lag effect.

### 3.2 The comparator window: a 29× collapse, then a uniform +46 %

The chain-element window (the campaign's bare `delaywin_hv`
measurement — runnable on the as-layout twin, which keeps the subckt
definitions; not runnable on the flat extraction, which is why the
whole-cell deck below exists):

| | Committed crowbarfix (102-point control, byte-identical) | As-layout bare chain |
|---|---|---|
| `twin_r` across the PVT grid | 5.007 – 9.423 ns | **0.197 – 0.305 ns** |

Point for point across 21 shared primary-grid corners the as-layout
window is **3.1 – 3.7 % of the committed design's** (`ld_deviation.csv`
section 2 of the analyze roll-up; typ 0.2269 ns vs 6.668 ns). The
layout's two absent MOM caps — 1.691 pF and 3.382 pF against the extracted
60.2 fF of VWIN parasitic capacitance the extraction does model — ARE the
window; the physical block without them has, element-wise, the fast
unloaded inverter chain the pre-resize design had, not the µs-scale
integrator the #52 commit was.

On the common device set (whole-cell ERR→ERRD window, both arms,
identical stimulus — §corners/matrix.md states the deck's provenance),
the extracted interconnect's own effect is uniform and small in spread:

| `twin_r` postlayout vs aslayout | min | mean | max |
|---|---|---|---|
| 29 PVT points | **+44.20 %** | **+46.49 %** | **+48.56 %** |

This is the same signature RECORD-001 §4.3 found for the VCO: a
nearly-constant multiplicative delay change across corner and temperature
(the deviation tracks the driven-node capacitance ratio, in which the
drive current and the intrinsic node caps largely cancel). The
timestep-convergence cross-check brackets discretization at −0.78 %
(as-layout) and −0.34 % (post-layout) between the committed 20 p and a
16× finer maximum timestep (`ld_tstep_convergence.csv`) — two orders of
magnitude below the effect.

### 3.3 Row-16 criteria: the as-built block fails all three, on both arms

The ladder (that campaign's frozen `record002` 9-point set, consumed via
its own `gen_ladder.py` for both arms; the reduced corner grid is
RECORD-002's own, minus its 2 MOM-band spots which are unrepresentable
with no caps in either arm — `corners/matrix.md` states the subset)
`corners/ld_ladder.csv`, 32 rows:

- **At 3.5 MHz** (the amended range's slow end — the binding end for an
  R·C ≫ T_ref claim): **both arms chatter at every ladder point up to
  10× the window.** The states are `TTTTTTTTT` — LOCK toggles within the
  settle window at every τ — and the zero-phase-error recovery copy's
  LOCK is rail-`unresolved` in most corners. On the common capacitance
  basis the integrating node's R·C ≈ 0.38 – 0.70 × T_ref: without the
  MOM caps the block is not an integrator at the slow end, and LOCK is a
  pass-through of every error pulse — the exact pre-resize pathology
  RECORD-002 of the sibling campaign measured and #52 was filed to fix.
- **At 24.4 MHz** (R·C ≈ 2.0 – 4.8 × T_ref): both arms behave like a
  working detector — in-window for τ ≤ 1.0 × window, steady out beyond,
  rail resolved — with **0.00 % hysteresis** at every fast-end corner
  (assert and de-assert thresholds coincide at 1.0 × window on both
  arms; the post-layout arm shows a 1.2× de-assert / 20 % hysteresis
  at two slow-end corners that still chatter).
- **The ≥ 2.5 ns window floor**: the as-built window is 0.21 – 0.39 ns
  (whole-cell, across PVT). The committed design's floor-compliant
  6.4 – 9.4 ns window exists only with the two caps the layout does not
  carry.

`spec/porting-plan.md` row 16 therefore **fails for the as-routed block on
all three counts — window, hysteresis, chatter — and neither the failure
nor the 24.4 MHz partial pass is an interconnect effect: the as-layout
schematic twin fails identically** (`ld_ladder.csv`, both arms side by
side). Per this repo's rule that agents do not relax a ratified spec, no
spec row is proposed here; the failure is the layout's, and this record
records it as evidence for whoever re-draws the block.

### 3.4 Supply current and recovery, post-layout vs as-layout (row 11)

The recovered deck measures in-lock / out-of-window supply current at
every ladder corner:

| | 3.5 MHz | 24.4 MHz |
|---|---|---|
| in-lock, as-layout | 1.2 – 2.8 µA | 19.1 – 20.8 µA |
| in-lock, post-layout | **21 – 43 µA** | **87.4 – 93.1 µA** |
| recovery time `trec` | 67 – 165 ns → **124 – 302 ns** (≈ ×1.85) | same trend |

The ~×4.5 in-lock rise at 24.4 MHz is consistent with dynamic charging of
the extracted 305 fF node set at that frequency (C·V²·f ≈ 80 µA); the
3.5 MHz rise (×15 – 25) is mostly the chatter power — the same
back-and-forth-switching cost a correlating unlocked loop would pay. Even
the as-layout steady value (~20 µA) is itself an order above the
committed crowbarfix design's µA-scale schmitt readout, because the
as-built block holds its schmitt in the high-gain region; the integrated
current is a symptom, not an independent defect.

---

## 4. Deviation analysis — how the three results fit the harness's

The two pages bound the SAME parasitic mechanism from both sides.
For `pfd` (LVS-matched, all-MOS, stateful at ns scale), the extracted
RC stretches every internal arc by ~+0.5 ns — a *pulse-width* effect that
is benign while the stimulus period is 50 ns (reflead) and
mode-inverting when the circuit's own race margins are of the same order
as the added delay (fblead). For `lock_detector`, the same
~+46 % multiplicative element delay appears on the window (the +46.49 %
mean of §3.2 matches the ≈ +0.5 ns/twin_s additive scale of a ~0.26 ns
chain element × ~3.77), inside a block whose layout is missing the caps
that defined its committed behavior — so the deviation analysis has to be
and is three-way rather than two-way.

**What this does NOT do to the ratified spec**: nothing. Grid A/B/C of
RECORD-001 stand untouched; row 16's as-routed failure (§3.3) is recorded
as open risk for the layout pipeline, not as a spec input — the same
posture RECORD-001 §4.5 takes for the VCO's non-floorplan slowdown.

---

## 5. LVS status, and what carries the load for each block

| Block | Verdict (`lvs-recheck/summary.json`, unchanged from RECORD-001 §5) | What this record relies on instead |
|---|---|---|
| `pfd` | **match** — 66/66 devices, 37/37 nets, 0 errors | nothing needed; §2's deviations are attributable to parasitics on a confirmed-identical circuit |
| `lock_detector` | **not compared** — `cap_cmomi` `m=2` multi-finger reference conversion (documented, deliberate deck limitation; `layout/sg13cmos5l-pll/README.md`) | §3.1's geometric device-set table: the routed cell IS the #52 resize minus its two caps — the deviation analysis isolates interconnect (aslayout A/B) from the topology/revision gap (committed-crowbarfix three-way), so no claim below rests on an unverified layout-schematic identity |

---

## 6. What this record does not bound

- **Any sub-block measurement of the post-layout `lock_detector` beyond
  ERR→ERRD.** The extraction is flat, so the campaign's bare
  `schmitt_hv` hysteresis rows (45 committed rows, `schmitt.*.csv`) have
  no post-layout counterpart at all — stated in `corners/matrix.md`, not
  silently dropped. Filed upstream as
  [klayout-tools#2245](https://github.com/2AMLogic/klayout-tools/issues/2245)
  (**open**, new this pass): `klt extract`'s flat-only output makes
  sub-block isolation from a parasitic-annotated netlist impossible; the
  generic gap, not this block's details.
- **The pfd at any PVT point other than `typ`.** The comparison target
  ratified one point (its own `corners/matrix.md` states the runtime
  reason); this record adds the offset axis it needs and no PVT axes
  (Matrix D, `corners/matrix.md`).
- **The lock_detector ladder's MOM-band and reference-frequency
  ladders of the committed crowbarfix campaign** — no caps exist on
  either arm of this block, and the window matrix already carries the
  supply and PVT axes the row-16 claims need. The 24.4 MHz fast-end
  extension #66 added for its weak-XMPD hysteresis does not transfer:
  the as-built XMPD is the strong #52 device.
- **Closed-loop consequences of either result.** fblead inversion in the
  PFD is a fixed-10 %-offset standalone finding; what it does to lock
  time or spur power through a real second-order loop is
  `sg13cmos5l-closed-loop-lock`'s question, not this record's — and that
  campaign's closed-loop transient still has no post-layout arm.
- **Anything about the missing caps in silicon.** Absence from the
  extraction means absence from the drawn GDS the committed flow
  extracted; whether a respin draws them is a layout-pipeline decision
  this record informs, not one it makes.

## 7. Friction encountered (and where it went)

Per the repo's friction protocol, each item was checked for an existing
upstream issue before being called a gap:

- **A flat `klt extract --parasitics` netlist cannot be measured
  sub-block-wise** — the root cause behind the whole-cell window deck
  (§3.2), the missing post-layout schmitt rows (§6), and the
  ladder-window-inline detours in `run_lock_detector.sh`. Verified
  non-duplicate (#1085 is the LVS side, solved by PR #1108's flatten
  options; #1878 is combine_devices): filed as
  **[klayout-tools#2245](https://github.com/2AMLogic/klayout-tools/issues/2245)**
  (**open**, new this pass). Worked around here; the workaround is the
  record.
- **The m=2 `cap_cmomi` reference-conversion LVS blocker** for
  `lock_detector` (and so the whole §3.1 device-set exercise) is
  *not* re-filed: `layout/sg13cmos5l-pll/README.md` already records it
  as deliberate deck limitation, and RECORD-001 §5 reported it; nothing
  about it moved.
- **A fully cap-stripped extraction of a stateful block is not
  DC-solvable**, so the rc-attribution `none` variant that isolated
  device-vs-interconnect so cleanly for the VCO is not available for the
  `pfd` (isolated latch-internal gate nodes: singular matrix). Not filed
  upstream — this is a property of the stripped netlist, not a `klt`
  gap; recorded here so the next post-layout record does not rediscover
  it. The pfd's attribution instead rests on the LVS match plus the
  schematic control arm.
- **Not a tool gap, a mistake this record made and corrected**: the first
  offset-sweep debugging batch re-ran an already-substituted deck (the
  `@REF_DELAY@` / `@FB_DELAY@` sed had nothing left to replace), producing
  rows that looked like new offsets but were the same stimulus. Caught
  the way every such catch in this harness has been caught: the schematic
  control arm produced textbook numbers at every offset, so the
  suspicious rows contradicted a control; all committed rows come from
  re-substituted-from-template decks, and `run_pfd.sh` regenerates each
  deck from the template per point.
