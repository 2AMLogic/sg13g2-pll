# RECORD-004: post-layout (PEX) arms for `loop_filter` and `divider_chain`

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #115 (Part of #16) — the two blocks RECORD-001 declared
  "unanswerable" (and RECORD-003's matrix restated), now measurable
  because both prerequisites landed: #112's `divider_chain` functional
  repair (merged via #121, re-verified by
  `../sg13cmos5l-divider-nrange-retiming` RECORD-003 — the schematic-level
  result this arm deviates from) and #114's drawn `cap_cmomi` pair with
  LVS closed (merged via #119).
- **DUT**: `pll_loop_filter` and `pll_divider_chain`, the subcircuits
  `klt extract --deck sg13cmos5l --parasitics --pdk ihp-sg13cmos5l`
  produced from the routed GDS of layout record
  `20260923-020931-a95a887-dirty` (the committed flow record carrying
  #121's `dff_tg_hv` fix and #114/#119's drawn MoM caps). Extraction basis
  per block (`netlist-snapshots/provenance.json`, repo-pinned
  `klt 0.6.0+gdaf06a51afaf`, no metal level without a coefficient):
  - `pll_loop_filter`: 3 devices — the committed resized `rppd`
    (`w=0.6u l=810u`, DR-006) and both `cap_cmomi` exactly as committed
    (`w=40u l=40u`, `w=10u l=10u`) — plus 6 parasitic series resistors
    (ΣR 6 874.5 Ω), 3 substrate capacitors (ΣC 1 175.1 fF) and one
    6.05 fF coupling capacitor. **LVS `match`, 3/3 devices, 4/4 nets**
    (`lvs-recheck/summary.json`).
  - `pll_divider_chain`: 394 devices — the repaired 13-flop chain — plus
    1 576 parasitic resistors (ΣR 70 937 Ω), 181 substrate capacitors
    (ΣC 16 343.6 fF) and 13 517 coupling capacitors (ΣC 246.9 fF).
    **LVS `match`, 394/394 devices, 181/181 nets** (same summary).
- **Tooling**: `ngspice-46` on an 8-core x86-64 Linux host;
  `klt 0.6.0+gdaf06a51afaf` (the `layout/requirements.txt` pin, installed
  from the pinned commit for the re-extraction; the six re-extracted
  netlists are byte-identical, sha256-verified, to the ones this record's
  simulations ran on).
- **Reproduce**:
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_loop_filter.sh`
    → `corners/lf_results.csv` (54 rows), `corners/lf_control.csv` (27)
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_divider_chain.sh`
    → `corners/div_results.csv` (34 rows), `corners/div_control.csv` (20)
  - `python3 ./testbench/analyze_lf_div.py`
    → every roll-up number quoted below

---

## 1. What was re-simulated, and the controls that make it a measurement

Real extracted parasitics on both new blocks, same extraction discipline
as RECORD-001 §1 (no fallback anywhere; provenance.json is
machine-readable evidence, never assertion). Both new arms are
LVS-matched cells, so a measured deviation is attributable to the
extracted interconnect, not to a layout-vs-schematic topology difference —
the statement RECORD-001 could not make for either block and RECORD-003
could make for only one of its two.

Controls, one per matrix, both reproductions of the committed campaigns
the arms deviate from:

1. **Matrix F's schematic control arm re-runs the committed
   `sg13cmos5l-loop-filter-momcap` campaign's own resized-R1 matrix**
   (27 rows) on this host — with this record's composite driving-point AC
   method rather than that campaign's device-level DC/AC extractions,
   because the post-layout arm's R1'/C1'/C2' only exist as a composite.
   The control column (`lf_control.csv`) therefore quantifies the method
   difference, and it is identical on both arms, so the A/B deviation
   below excludes it: r1 −5.70 % … −6.76 % (the rppd r3_cmc model's
   AC small-signal resistance vs its DC value, compounded with the
   squeezed-plateau reading — see §2's caveat), c1 −1.26 % … −1.28 %
   (wholly inherited from c2's dispersion by the subtraction), c2
   +21.36 % … +21.69 % (the cap_cmomi model's own frequency dispersion:
   its density is characterised flat only through that campaign's
   1k–100k check; this record measures C2′ at the fixed 50 MHz rule).
2. **Matrix G's schematic control arm re-runs the whole committed 20-row
   `func` matrix** of `sg13cmos5l-divider-nrange-retiming` (the #112
   re-verification campaign) via that campaign's own deck, unmodified:
   **20/20 rows reproduce byte-identically** — every divide ratio to all
   six printed digits (max |Δn| 0.0 ppm) and every average supply current
   (max |Δidd| 0.0000 %). This is the RECORD-003 `ld_window_control`
   class of control at full committed-matrix density.

---

## 2. Results — `pll_loop_filter`, Matrix F (issue #115)

The 27-row corner × MOM-band matrix, both arms, mom_frac=0 rows first
(`corners/lf_results.csv`; every number below from
`testbench/analyze_lf_div.py`). The post-layout deviation is
**capacitance-dominated and essentially corner-flat** — consistent across
all 9 res_corner × temp combinations to within ±0.15 %:

| Quantity (frac=0) | Schematic control | Post-layout (PEX) | Deviation |
|---|---|---|---|
| Ctot′ = C1′+C2′ (100 Hz) | 1.7914 pF | 2.5009 pF | **+39.6 %** |
| C2′ (50 MHz) | 121.7 fF | 234.2 fF | **+92.4 %** |
| R1′ (plateau max-Re) | 322.7 kΩ (typ/27C) | 294.0 kΩ | −8.9 % (see caveat) |
| fz′ (typ/27C) | 295.4 kHz | 238.8 kHz | **−19.1 %** |
| fp′ (typ/27C) | 4.348 MHz | 2.550 MHz | **−41.4 %** |

The capacitance deltas are the expected physics, quantified: the
extraction carries 1 175 fF of substrate capacitance plus a 6 fF coupling
capacitor on the block's stub nets (NZ 533.9 fF, VCTRL 91.3 fF, VSS
549.9 fF — VSS is AC-grounded, so the driving point sees the NZ and VCTRL
shares), against C1+C2 = 1 791 fF of device capacitance. The measured
+709 fF (Ctot′) and +112 fF (C2′, the VCTRL-side share) sit within the
extraction's own lumped-star rounding of those numbers — this is the
interconnect's capacitive share, the same composition finding RECORD-001
measured on `vco` (≈99 % capacitance) arriving at the loop filter.

**R1′ caveat, stated not buried:** the −8.9 % arm-to-arm reading is a
measurement-compression artifact, not a physical resistance reduction —
extraction can only ADD series resistance (ΣR = 6 874 Ω, +2.0 % on
R1 = 344 kΩ at typ/27C). The fixed max-Re(Z) plateau rule reads low on a
squeezed plateau: the post-layout fp′ (2.55 MHz) sits only 1.7× above
fz′ (239 kHz), so the C2′ shoulder erodes the resistive top the same way
it erodes the control arm's (−6.3 % vs the committed DC-device value,
quantified above). The honest statement is a bound: **R1′_true lies in
[R1_model(corner,temp), R1_model + 6.9 kΩ]**, the band's fz/fp rows are
computed from the same fixed rule on both arms, and the physical
resistance change the extraction introduces is ≤ +2.0 % — an order below
the capacitance terms that dominate this arm.

**Temperature-flatness holds on both arms** (this campaign's own
cap-invariance finding, re-asserted through the extraction): Ctot′ spread
over −40/27/125 °C is 0.0000 % on both arms; C2′ spread 0.022 %
(schematic) / 0.010 % (post-layout).

**The band (res_typ/27C, frac −20 %…+20 %):** schematic fz 246.2 –
369.3 kHz, fp 3.624 – 5.436 MHz; post-layout fz 199.0 – 298.6 kHz
(MIN/MAX across the band), fp 2.125 – 3.188 MHz. The ±20 % rows scale
the arm's own composite capacitance (matrix.md states the post-layout
bracket is therefore an upper bound on the MOM-uncertainty effect).

**Conclusion for `loop_filter`:** the drawn MoM pair turns the routed
cell into the committed filter (LVS 3/3), and its post-layout deviation
is a pure capacitance story — the loop's fz moves −19 % and fp −41 % at
nominal, both in the direction that slows loop settling, bounded by
routing style exactly as the other five blocks' numbers are, with no
corner in the 27-row grid where the sign or the composition changes.

---

## 3. Results — `pll_divider_chain`, Matrix G (issue #115)

14 post-layout points (`corners/div_results.csv`; roll-ups from
`testbench/analyze_lf_div.py`). The headline: **the extracted chain
divides correctly at every measured point** — the #112/#121 repair's
functionality survives the real interconnect intact:

| Point set | Post-layout n vs schematic control |
|---|---|
| baseline 000000, 3-bundle bracket (tt/27, ss/125, ff/−40) | 64.0005 / 63.9998 / 64.0004 — **≤10.9 ppm** from the control (and inside the same 6-digit quantization band the control itself reproduces the committed rows in) |
| full 9-word sweep at nominal (65…127, incl. both mixed words and the 111111 ceiling) | every word **exact**: 65.000, 66.000, 68.000, 72.000, 80.000, 96.000, 95.000, 106.000, 127.000 — max deviation 4.6 ppm |
| ceiling 111111 at both bracket extremes (ss/125, ff/−40) | 127.000000 at both, 0.0 ppm |

Stage liveness is unbroken: every internal stage clock ck1…ck5, DIVOUT and
FB swings full rail on every post-layout point (worst global excursions
−6.9 … 3 313.6 mV on ck1; DIVOUT −20.2 … 3 318.7 mV) — no stage stops
toggbling at any measured corner, the failure mode RECORD-001's
schematic-level Finding 2 used to bound the broken design.

**The cost of the 147 mm: average supply current ×3.7.** idd moves from
~226 µA (schematic control, every point) to 809–862 µA (post-layout,
every point) — **+262 % … +276 %**, uniform across words and brackets. The
composition is the expected one: the extraction carries 16.34 pF of
substrate capacitance plus 247 fF of coupling on the chain's 181 nets
(provenance.json); at 100 MHz and 3.3 V a full-rail swing of all of it
would draw C·V²·f/V ≈ 5.4 mA — the measured ~0.83 mA corresponds to
roughly a third of the extracted capacitance effectively swinging
full-rail per cycle (internal nodes swing at divided rates and
fractionally), the same order-of-magnitude consistency check RECORD-001
applied to the VCO's −49 % frequency finding. This is the floorplan bound
made concrete for the block that RECORD-002 explicitly could not move:
**the routed divider chain's ratio is parasitic-immune at every measured
point, and its power is not.**

**Conclusion for `divider_chain`:** with the functional repair in, the
post-layout arm finds no functional penalty anywhere in the measured
bracket — the divide ratio, the programming-word formula and the N=127
ceiling all hold to measurement precision — while the dynamic current
triples on the extracted interconnect. Retiming margin at top-of-band
(the one #112 criterion this matrix deliberately does not carry
post-layout) remains a named compute-shaped gap (§5).

---

## 4. Friction encountered (the canary's log)

- **klayout-tools#2355 (filed from this run):** `klt extract --parasitics`
  emits drawn `cap_cmomi` device cards as `PARAMS: W=40 L=40` — bare
  micron numbers behind a `PARAMS:` keyword — against the PDK subckt
  interface whose own defaults are SI meters (`w=5e-6`). With
  `.option scale=1` ngspice reads `W=40` as 40 metres: a capacitance
  1e12× oversize that is **silent at DC** (a capacitor blocks DC at any
  value) and surfaces only as an effectively-shorted capacitor in AC —
  the extracted loop_filter's driving impedance measured a flat 1.6 kΩ
  until the card was respelled. The same extractor's resistor cards
  carry proper unit suffixes (`L=810U W=0.6U`), which is what makes the
  cap form look like an oversight rather than a convention.
  `testbench/pex-to-ngspice.py` gained a third documented, self-checked
  mechanical transform (bare → `u`-suffixed, geometry verbatim) until the
  upstream fix lands.
- **ngspice `vp()` prints wrapped phase whose radians/degrees convention
  is easy to misread** (observed while building Matrix F's extraction:
  the printed values were neither −90 ° nor −π/2 in any readable
  convention). The deck now prints `real(v)`/`imag(v)` explicitly and the
  extraction derives capacitance from Im, the momcap campaign's own
  idiom.
- **Bash argv is not a data channel:** this script's first draft passed
  ngspice's print-vector stdout (hundreds of KB) as a python argv and hit
  `Argument list too long` — three completed transients' results were
  lost to it before the fix (results now go through a file). Recorded
  here because the failure mode is silent until it isn't.

---

## 5. What this record leaves open

- `divider_chain`'s `hold`/`setup`/`retime` stages have **no post-layout
  arm** (a single 1 562 MHz top-of-band post-layout transient exceeds
  this record's whole-session compute budget several times over). The
  functional-N result above is the ratified comparison; the retiming
  margin's post-layout bound is a named, compute-shaped gap for a
  follow-up.
- Matrix G's post-layout arm carries the stated 14-point reduction, not
  the full 20-row set (matrix.md names the dropped OFAT points; every
  dropped axis is still covered on the schematic control arm).
- `lock_detector` remains the one block without an LVS match — untouched
  by this record, unchanged from RECORD-003.
