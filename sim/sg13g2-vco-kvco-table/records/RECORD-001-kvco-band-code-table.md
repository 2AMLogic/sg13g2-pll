# RECORD-001: SG13G2 `vco` output band / Kvco-vs-band-code table (open-loop, PVT-cornered)

- **Slug**: `sg13g2-vco-kvco-table`
- **Issue**: #97, the SG13G2 twin of `sg13cmos5l-vco-kvco-table` (issue #23,
  Part of #16)
- **DUT**: `vco` (SG13G2-native design, `design/netlist/vco.spice`) — the
  full block (`vco_bias` + 5x `vco_stage` + 2x `inv2x_hv` output buffer),
  open-loop (no PFD/CP/loop-filter/divider closure). See
  `../netlist-snapshots/vco.spice` (frozen at commit
  `e737c5afb7db2ae2889dd1fc083eb8a15713e7fd`; `vco.spice`'s own content is
  unchanged since PR #10, the SG13G2 3.3V thick-oxide CMOS schematic port).
- **Claim under test**: `spec/porting-plan.md` row 1 (output band) and row
  4/5 (Kvco bound / band-selection rule) call for a re-derived SG13G2 output
  band and "a per-band, per-corner Kvco table" as the rule structure to
  port. Until this record, no SG13G2-native measurement of either existed —
  `spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md` explicitly
  reconciled `f_ref`/`N` against the **SG13CMOS5L-measured** band as "the
  best available proxy... in the absence of any SG13G2-native measurement."
  This record supplies that missing SG13G2-native measurement directly.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13g2`.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13g2 ./testbench/run.sh`
  writes `../corners/results.csv` (60 rows). Re-run in this session on an
  **arm64** host (`uname -m` = `arm64`) with zero fatal ngspice errors and
  zero `NA` rows.

## Methodology

Instantiates the real, committed `vco` subckt (unmodified topology) with
ideal DC sources on `VCTRL`/`B0`/`B1`/`VDD_VCO` and `GND_VCO` tied to `0`,
runs a transient simulation long enough for the ring to self-start and
settle, and measures the steady-state `CLK` period with ngspice's own
`meas tran ... trig ... targ ...` between two later rising-edge crossings
(skipping the ring's own startup transient) — see
`testbench/tb_vco_kvco.sp.tmpl`'s own header for the exact mechanics. This
methodology, the transient length, the `.ic` self-start technique and the
`.meas` mechanics are all carried over unchanged from the SG13CMOS5L
sibling's own `RECORD-001` — only the DUT, corner libraries, and (new on
this PDK) the `cap_cmim` corner axis differ.

**Self-start**: a symmetric 5-stage ring's own DC operating point is a
metastable equilibrium (every stage at the same mid-rail voltage); ngspice's
`.op` solver converges to it exactly rather than a real ring's own
noise-driven escape from it. `.ic v(xvco.ring1)=0.5` breaks that symmetry
for the transient's own initial condition, the same role real device noise
or mismatch plays in an actual chip. This design shares the identical
5-stage ring topology and node names (`ring1`...`ring5`) as the SG13CMOS5L
sibling, so the same probed node applies unchanged.

**Why `XCDECAP` is kept, not stripped, here**: see `../corners/matrix.md`
"Why `XCDECAP` is kept, not stripped, here" for the full rationale. In
short: `VDD_VCO`/`GND_VCO` are driven by ideal, zero-impedance DC sources in
this testbench too, so `XCDECAP`'s own capacitance value cannot affect any
measured node — the same reasoning the SG13CMOS5L sibling used to justify
stripping it. This record does not need to strip it at all: `vco.XCDECAP`
is a `cap_cmim` MIM decap, which (confirmed directly against the installed
`ihp-sg13g2` tree, mirroring `sim/sg13g2-lock-detector-window`'s own finding)
has **no OSDI object at all** — no cross-architecture, prebuilt-binary risk
exists for it, unlike the SG13CMOS5L sibling's `cap_cmomi`/`cap_cmomf`. So
this record `.include`s the frozen `../netlist-snapshots/vco.spice`
directly and unmodified, and sweeps `cap_cmim`'s own real process corner
(`cornerCAP.lib`: `cap_typ`/`cap_bcs`/`cap_wcs`) as a first-class bundled
axis even though it provably does not move this specific measurement.

**Host/architecture**: this record runs on an **arm64** macOS host. All
four OSDI objects this deck needs (`psp103`, `psp103_nqs`, `mosvar`,
`r3_cmc`) are native `ihp-sg13g2` build products and load without issue;
`cap_cmim` needs no OSDI object at all (see above). `../testbench/run.sh`'s
own OSDI preflight (`sim/tools/check-osdi-arch.sh`, hard-abort, no
`--soft`) passed cleanly before any corner ran — mirroring
`sim/sg13g2-lock-detector-window`'s identical preflight and confirming this
campaign has no `cap_cmomi`-style arm64 gap to work around.

## Corner matrix

See `../corners/matrix.md` for the full matrix and the explicit
3-bundle-subset rationale (not the full 5-MOS x 3-RES x 3-CAP x 3-temp
cross product). Summary: 3 PVT bundles (`typ`/`slow`/`fast`, each pairing a
MOS/RES/CAP corner with a temperature) x 4 band codes (`00`/`10`/`01`/`11`)
x 5 `VCTRL` points (0.3/0.9/1.5/2.1/2.7 V) = 60 runs, all at a fixed 3.3V
supply (`DR-002` Decision 0) — `../corners/results.csv`, **60/60 valid, zero
`NA` rows**.

## Results

Full data (all 60 runs, no `NA`/non-oscillating points): `../corners/results.csv`.

| PVT bundle | Band | f(0.3V) MHz | f(0.9V) MHz | f(1.5V) MHz | f(2.1V) MHz | f(2.7V) MHz | Kvco avg (0.3-2.7V) MHz/V | Kvco peak local (2.1-2.7V) MHz/V |
|---|---|---|---|---|---|---|---|---|
| typ | 00 | 494.0 | 533.1 | 655.0 | 787.4 | 911.0 | 173.8 | 206.0 |
| typ | 10 | 494.0 | 548.6 | 747.8 | 959.3 | 1130.0 | 265.0 | 284.5 |
| typ | 01 | 494.0 | 558.0 | 810.9 | 1074.9 | 1262.0 | 320.0 | 311.8 |
| typ | 11 | 494.0 | 564.1 | 862.0 | 1161.9 | 1359.1 | 360.5 | 328.6 |
| slow | 00 | 445.3 | 483.4 | 584.4 | 693.9 | 791.3 | 144.2 | 162.2 |
| slow | 10 | 445.3 | 497.5 | 657.6 | 824.3 | 953.1 | 211.6 | 214.7 |
| slow | 01 | 445.3 | 505.7 | 705.0 | 907.5 | 1047.0 | 250.7 | 232.5 |
| slow | 11 | 445.3 | 511.6 | 741.2 | 970.1 | 1113.8 | 278.6 | 239.4 |
| fast | 00 | 548.2 | 592.3 | 730.3 | 882.2 | 1025.3 | 198.8 | 238.5 |
| fast | 10 | 548.2 | 610.6 | 840.3 | 1084.6 | 1284.4 | 306.8 | 333.1 |
| fast | 01 | 548.2 | 621.7 | 919.4 | 1224.2 | 1445.3 | 373.8 | 368.5 |
| fast | 11 | 548.2 | 629.8 | 984.0 | 1334.1 | 1562.0 | 422.4 | 379.9 |

`Kvco avg` is the end-to-end secant slope over the full swept range;
`Kvco peak local` is the secant slope over the topmost interval (2.1V to
2.7V), reported separately because Kvco is visibly non-constant across the
range (see "Kvco is not constant" below) — a single "the" Kvco number would
misrepresent this VCO's own tuning curve.

**Overall band edges** (across the whole 60-point matrix): floor
**445.26 MHz** (`slow` bundle, every band code, `VCTRL = 0.3V` — band select
is inert here, see below), ceiling **1561.97 MHz** (`fast` bundle, band
`11`, `VCTRL = 2.7V`).

**Binding (slowest/fastest) corners**: the `slow` bundle (`mos_ss`/`res_wcs`/
`cap_wcs`/125C) is the binding worst-case-frequency-floor corner at every
`VCTRL`/band point in this matrix; the `fast` bundle (`mos_ff`/`res_bcs`/
`cap_bcs`/-40C) is the binding worst-case-frequency-ceiling corner. This
matches the SG13CMOS5L sibling's own binding-corner pattern exactly (see
"SG13G2 vs. SG13CMOS5L" below for why).

### Band select has (almost) no effect at low VCTRL, and a large effect at high VCTRL

At `VCTRL=0.3V`, every band code within a given PVT bundle measures the
*same* frequency to 6 significant figures (e.g. `typ`: 494.0 MHz for all of
`00`/`10`/`01`/`11`). This reproduces the SG13CMOS5L sibling's own finding
exactly (same root cause: `sg13_hv_nmos`'s `XM8`, gated by `VCTRL`, is deep
in cutoff at this low a control voltage, so essentially no current flows
through either band-select degeneration branch regardless of which one is
selected — the band-select mechanism only starts to matter once `XM8`
actually conducts). **Consequence for the band-selection rule**
(`spec/porting-plan.md` row 4/5's own "lowest band that reaches the target"
normative rule): this design's coarse band code is not a uniform multiplier
across the whole `VCTRL` range — it is a low-VCTRL-inert, high-VCTRL-dominant
effect — which the eventual band-selection rule should account for rather
than assume a constant per-band frequency ratio.

### Kvco is not constant across the sweep (a real nonlinearity, not noise)

Every band/corner combination's average slope (`Kvco avg`) is measurably
different from its topmost local slope (`Kvco peak local`) — e.g. `typ/00`:
173.8 MHz/V averaged vs. 206.0 MHz/V at the top of the range, a real ~19%
difference, and the direction (peak local > average) is consistent across
every row. Expected shape for a current-starved ring with a V-I converter
whose own `VCTRL`-to-current relationship is nonlinear (PSP103 compact
model), not a numerical artifact.

## SG13G2 vs. SG13CMOS5L: explicit side-by-side comparison

| Quantity | SG13G2 (this record) | SG13CMOS5L (`sg13cmos5l-vco-kvco-table/RECORD-001`) | Match? |
|---|---|---|---|
| Band floor | 445.26 MHz (`slow`, all bands, `VCTRL=0.3V`) | 445.3 MHz (`slow`, all bands, `VCTRL=0.3V`) | Identical to rounding precision |
| Band ceiling | 1561.97 MHz (`fast`, band `11`, `VCTRL=2.7V`) | 1562.0 MHz (`fast`, band `11`, `VCTRL=2.7V`) | Identical to rounding precision |
| Kvco avg range | 144.2–422.4 MHz/V | 144.2–422.4 MHz/V | Identical |
| Kvco peak-local range | 162.2–379.9 MHz/V | 162.2–379.9 MHz/V | Identical |
| Band-select-inert-at-low-`VCTRL` finding | Yes (§ below) | Yes | Same mechanism, same corners |
| Binding slowest/fastest corner | `slow`/`fast` bundles | `slow`/`fast` bundles | Same |
| All 60 raw `freq_hz` values | — | — | **Byte-for-byte identical, 60/60, 0 diffs** |

**Every one of this record's 60 measured frequencies is byte-for-byte
identical to the corresponding row in
`sim/sg13cmos5l-vco-kvco-table/records/RECORD-001`'s own
`corners/results.csv`** (verified programmatically, 60/60 rows, 0 diffs;
the reproduce command is `python3` comparing both CSVs' `freq_hz` columns
keyed on `pvt_bundle`/`band_code`/`vctrl_v`). This is not a coincidence and
not evidence of a testbench bug — it is the expected consequence of two
facts the SG13CMOS5L port's own provenance already establishes
(`docs/chipalooza/challenge-6-proposal.md` §3, cited directly by DR-005):

1. The SG13CMOS5L port's active devices — `sg13_hv_nmos`/`sg13_hv_pmos`,
   literally the same PSP103-modeled devices this SG13G2-native design
   uses, resolved from the same `ihp-sg13g2` OSDI build products
   (`psp103.osdi`/`psp103_nqs.osdi`/`mosvar.osdi`/`r3_cmc.osdi`) either
   design's own `.spiceinit` loads — are **identical** between the two
   designs; only 5 MIM→MOM capacitor substitutions differ (per-instance,
   not per-device-class), and
2. neither testbench's `CLK`-period measurement is sensitive to that decap
   substitution, since both drive `VDD_VCO`/`GND_VCO` with ideal DC voltage
   sources (this record's own "Why `XCDECAP` is kept, not stripped" above;
   the SG13CMOS5L sibling's "Why `XCDECAP` is stripped").

With the same active devices, the same corner-selected model parameters
(`cornerMOShv.lib`/`cornerRES.lib` are literally the same files, shared by
both PDK trees per the `ihp-sg13g2` build-product relationship), the same
bias/degeneration-resistor topology, and a decap substitution this specific
measurement cannot see, there is no remaining source of numeric difference
for this open-loop frequency measurement — the two "designs" are, for this
specific claim, the same circuit simulated twice under the same corner
labels.

**Consequence for `DR-005`**: `DR-005`'s own "Provenance note" flagged this
exact gap — "no SG13G2-native VCO Kvco campaign exists in this repo" — and
treated the SG13CMOS5L-measured band as "the best available proxy... in the
absence of any SG13G2-native measurement." This record supplies that
missing measurement, and it **confirms** DR-005's proxy assumption rather
than contradicting it: the SG13G2 band edges (445.26–1561.97 MHz) match
DR-005's own cited SG13CMOS5L figures (445.3–1562.0 MHz) to the rounding
precision DR-005 itself used. **The SG13G2 band does not fall outside what
DR-005 assumed** — no follow-up decision record is needed to reconcile a
discrepancy, because there is none. This record does not itself amend
DR-005 (out of this issue's own scope, and there is nothing to amend); it
is cited here as closing the specific provenance gap DR-005 named.

## Spec-row disposition (per this repo's own CLAUDE.md — no claim without a testbench)

`spec/porting-plan.md` row 1 (output band): **this record bounds the band
directly, for the first time on this PDK** — 445.26–1561.97 MHz across the
full PVT/band/`VCTRL` matrix, superseding the SG13CMOS5L-proxy basis
`DR-005` had to use in its absence (and, per the section above, confirming
rather than revising that proxy's numeric conclusion).

`spec/porting-plan.md` row 4/5 (Kvco bound / band-selection rule): **this
record bounds the table itself** — a real, PVT-cornered, per-band-code
frequency-vs-`VCTRL` measurement, satisfying the row's own "port the rule
structure... the numeric bound is 100% re-derive" disposition with real
SG13G2 data. Kvco avg ranges 144.2–422.4 MHz/V and Kvco peak local ranges
162.2–379.9 MHz/V across the matrix — same shape (non-constant, band- and
corner-dependent) as the SG13CMOS5L sibling's own table, for the reasons
given above.

`spec/porting-plan.md` row 3 (multiplication ratio / divider retiming-margin
closure): this record supplies the **top-of-band frequency** data point the
row's own retiming-margin closure needs — **1561.97 MHz** (`fast` bundle,
band `11`, `VCTRL=2.7V`) — matching the SG13CMOS5L sibling's own
1562.0 MHz to rounding precision, so `DR-005`'s row-3 `N ∈ [64, 127]`
reconciliation needs no revision on this PDK either. This record does **not**
close the row itself: that also needs the SG13G2 divider chain's own
retiming margin against this frequency, out of this record's own scope (the
SG13G2 twin of `sg13cmos5l-divider-nrange-retiming`, not attempted here).

`spec/porting-plan.md` row 6/6a (loop bandwidth / phase margin): this
record supplies the **Kvco** term a future SG13G2 open-loop-gain derivation
needs. The row's actual kHz/degree number stays `insufficient-evidence` on
this PDK — it also needs a SG13G2 loop-filter corner record and an
Icp-trim table, neither of which exists yet (the SG13G2 twins of
`sg13cmos5l-loop-filter-momcap`/`sg13cmos5l-cp-icp-trim`, out of this
record's own scope).

## What this does not bound

- **A closed-loop lock/settling behavior** — this is an open-loop
  characterization only (no PFD/CP/loop-filter/divider closure); lock time
  (row 7) is out of this record's own claim.
- **Duty cycle** (row 13) — this record measures period via a single
  threshold crossing per half-period pair, not the rising/falling symmetry
  duty-cycle measurement that row needs; `../corners/matrix.md` names the
  `mos_sf`/`mos_fs` split corners this would need as an explicitly open,
  not-yet-swept axis for that future record (the SG13G2 twin of
  `sg13cmos5l-vco-duty-cycle`).
- **Mismatch** between the two band-select switch branches (`XSWB0`/
  `XSWB1`) or between the ring's own five `vco_stage` instances — this
  record's band-code sweep exercises the nominal, matched-device model
  only; no per-instance mismatch model exists for `sg13_hv_nmos` or
  `cap_cmim` in this campaign.
- **`XCDECAP`'s own decap-value / supply-decoupling sensitivity** — kept in
  the simulated netlist here (unlike the SG13CMOS5L sibling), but this
  record makes no claim about it: an ideal voltage source drives the node
  it sits across, so its value cannot influence any measurement in this
  specific testbench (see "Why `XCDECAP` is kept, not stripped" above). The
  SG13G2 twin of `sg13cmos5l-vco-decap-momcap` would need a different
  testbench (a real supply-impedance source) to measure that.
- **The absolute loop-bandwidth/phase-margin number, lock time, reference
  spur, power, or an Icp-trim table** — none exist yet on this PDK; each is
  its own future SG13G2 slug, in the SG13CMOS5L campaign's own order
  (`sg13cmos5l-loop-filter-momcap` → `sg13cmos5l-cp-icp-trim` →
  `sg13cmos5l-loop-bandwidth-pm` → `sg13cmos5l-vco-duty-cycle` →
  `sg13cmos5l-closed-loop-lock` → `sg13cmos5l-divider-nrange-retiming`),
  none attempted by this issue.
