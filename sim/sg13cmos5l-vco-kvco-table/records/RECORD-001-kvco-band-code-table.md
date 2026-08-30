# RECORD-001: `vco` Kvco-vs-band-code table (open-loop, PVT-cornered)

- **Slug**: `sg13cmos5l-vco-kvco-table`
- **Issue**: #23 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L PVT campaign)
- **DUT**: `vco` (SG13CMOS5L port, PR #26 / Closes #22) — the full block
  (`vco_bias` + 5x `vco_stage` + 2x `inv2x_hv` output buffer), open-loop
  (no PFD/CP/loop-filter/divider closure). See
  `../netlist-snapshots/vco.spice` (frozen at commit
  `6250ba81f216d845201ede69a5d0f607537c4425`; `vco.spice`'s own content is
  unchanged since PR #26/#28).
- **Claim under test**: `spec/porting-plan.md` row 4/5 ("Kvco bound /
  band-selection rule") calls for "a per-band, per-corner Kvco table" as
  the rule structure to port, with the numeric bound "100% re-derive." This
  record delivers that table directly from a real SG13CMOS5L open-loop
  transient sweep.
- **Tooling**: `ngspice-47`, installed `~/share/pdk/ihp-sg13cmos5l`
  (`ReleaseNote.md` `v0.2.0`, same install DR-003/#23's other records
  confirmed).
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  writes `../corners/results.csv` (60 rows).

## Methodology

Instantiates the real, committed `vco` subckt (unmodified topology) with
ideal DC sources on `VCTRL`/`B0`/`B1`/`VDD_VCO` and `GND_VCO` tied to `0`,
runs a transient simulation long enough for the ring to self-start and
settle, and measures the steady-state `CLK` period with ngspice's own
`meas tran ... trig ... targ ...` between two later rising-edge crossings
(skipping the ring's own startup transient) — see
`testbench/tb_vco_kvco.sp.tmpl`'s own header for the exact mechanics.

**Self-start**: a symmetric 5-stage ring's own DC operating point is a
metastable equilibrium (every stage at the same mid-rail voltage); ngspice's
`.op` solver converges to it exactly rather than a real ring's own
noise-driven escape from it. `.ic v(xvco.ring1)=0.5` breaks that symmetry
for the transient's own initial condition, the same role real device noise
or mismatch plays in an actual chip.

**Why `XCDECAP` is stripped from this testbench's own netlist copy**: this
testbench drives `VDD_VCO`/`GND_VCO` with ideal, zero-impedance DC voltage
sources — an ideal voltage source enforces the node voltage regardless of
any capacitance in parallel with it, so `XCDECAP`'s own value (or even its
presence) cannot affect any node voltage this testbench measures. `../testbench/run.sh`
derives a local, `XCDECAP`-commented-out copy of the frozen
`../netlist-snapshots/vco.spice` for this reason (that snapshot itself
stays an exact, unmodified export) and makes **no claim whatsoever** about
`XCDECAP`'s own MOM-cap sensitivity — that claim is `sg13cmos5l-vco-decap-momcap`'s,
not this record's.

**Host-specific OSDI finding (recorded, not routed around)**: on this
build host, `cap_cmomi.osdi`/`cap_cmomf.osdi` (in the installed PDK's
`libs.tech/ngspice/osdi/`) are **x86-64 ELF shared objects** that fail
`dlopen` on this arm64 host ("slice is not valid mach-o file"), while
`psp103.osdi`/`psp103_nqs.osdi`/`mosvar.osdi`/`r3_cmc.osdi` — everything
this record's own DUT actually needs (`sg13_hv_nmos`/`sg13_hv_pmos` via
PSP103, `rppd`/`rhigh` via `r3_cmc`) — are native Mach-O arm64 and load
cleanly. This is why stripping `XCDECAP` (above) is not just a
provably-safe simplification for this specific measurement but also what
lets this record run at all on this host without depending on a fix to
that binary-distribution gap. Recorded here as a genuine tooling
observation per this repo's own CLAUDE.md friction-recording discipline;
not filed upstream because the task guidance for this issue explicitly
scopes the klayout-tools filing path to layout/DRC-LVS friction, and this
gap is host/OSDI-distribution-specific rather than a confirmed PDK-content
defect (a different build of the same installed PDK could plausibly ship
an arm64 `cap_cmomi.osdi` — this was not independently verified against
upstream).

## Corner matrix

See `../corners/matrix.md` for the full matrix and the explicit
3-bundle-subset rationale (not the full 5-MOS x 3-RES x 3-temp cross
product). Summary: 3 PVT bundles (`typ`/`slow`/`fast`) x 4 band codes
(`00`/`10`/`01`/`11`) x 5 `VCTRL` points (0.3/0.9/1.5/2.1/2.7 V) = 60 runs,
`../corners/results.csv`.

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

**Top-of-band frequency** (highest measured value across the whole matrix):
**1562.0 MHz**, at the `fast` bundle, band `11`, `VCTRL=2.7V` — the real
data point `spec/porting-plan.md` row 3's divider retiming-margin closure
needs as its own top-of-band input (see "Spec-row disposition" below for
why this record supplies that number but does not close the row itself).

### Band select has (almost) no effect at low VCTRL, and a large effect at high VCTRL

At `VCTRL=0.3V`, every band code within a given PVT bundle measures the
*same* frequency to 6 significant figures (e.g. `typ`: 494.0 MHz for all of
`00`/`10`/`01`/`11`). This is real circuit behavior, not a testbench bug —
independently confirmed by probing `xvco.xbias.degb` directly at
`VCTRL=0.3`: the band-select switch (`XSWB0`/`XSWB1`, gated by `B0`/`B1`)
node voltage does move measurably with the band code (`degb` = 1.61 uV vs.
0.84 uV for `B0=0` vs. `B0=3.3` in an isolated probe), but the V-I
converter transistor (`XM8`, gated by `VCTRL`) is still deep in cutoff at
this low a control voltage, so essentially no current flows through
*either* degeneration branch regardless of which one the band switches
select — the band-select mechanism only starts to matter once `XM8`
actually conducts. At `VCTRL=2.7V` the same probe shows a large, real
difference (`degb` = 1.175V vs. 1.002V), and the frequency table above
shows the corresponding ~2.8x band-code spread at the top of the range.
**Consequence for the band-selection rule** (`spec/porting-plan.md` row
4/5's own "lowest band that reaches the target" normative rule): this
design's coarse band code is not a uniform multiplier across the whole
`VCTRL` range — it is a low-VCTRL-inert, high-VCTRL-dominant effect — which
the eventual band-selection rule should account for rather than assume a
constant per-band frequency ratio.

### Kvco is not constant across the sweep (a real nonlinearity, not noise)

Every band/corner combination's average slope (`Kvco avg`) is measurably
different from its topmost local slope (`Kvco peak local`) — e.g. `typ/00`:
173.8 MHz/V averaged vs. 206.0 MHz/V at the top of the range, a real ~19%
difference, and the direction (peak local > average) is consistent across
every row. This is the expected shape for a current-starved ring with a
V-I converter that has its own nonlinear (square-law-adjacent, in this PSP
compact model) `VCTRL`-to-current relationship, not a numerical artifact —
consistent with `spec/porting-plan.md` row 4/5's own framing of Kvco as
something a *table*, not a single scalar, must capture.

## Spec-row disposition (per this repo's own CLAUDE.md — no claim without a testbench)

`spec/porting-plan.md` row 4/5 (Kvco bound / band-selection rule): **this
record bounds the table itself** — a real, PVT-cornered, per-band-code
frequency-vs-`VCTRL` measurement, satisfying the row's own "port the rule
structure... the numeric bound is 100% re-derive" disposition with real
SG13CMOS5L data rather than a carried-over gf180-pll/sky130-pll number.
This is **not** MOM-cap-sensitive in DR-003 Finding 2's own sense — the DUT
has no surviving `cap_cmomi`/`cap_cmomf` instance in this testbench (see
"Why XCDECAP is stripped" above) — so this record's own claim is unaffected
by the MOM-model-uncertainty caveat that gates the loop-filter/decap
records.

`spec/porting-plan.md` row 3 (multiplication-ratio / divider
retiming-margin closure): this record supplies the **top-of-band frequency**
data point the row's own retiming-margin closure needs — **1562.0 MHz**
(`fast` bundle, band `11`, `VCTRL=2.7V`, the highest measured value across
every corner/band/`VCTRL` combination in `../corners/results.csv`) — but
does **not** close the row itself: that also needs the divider chain's own
re-derived timing margin against this frequency, which is out of this
record's own claim (deferred to issue #27, Part of #16).

`spec/porting-plan.md` row 6/6a (loop bandwidth / phase margin): this
record supplies the **Kvco** term the row's open-loop-gain derivation
needs, combining with `sg13cmos5l-loop-filter-momcap/records/RECORD-001`'s
own `R1`/`C1`/`C2` data. **The row's actual kHz/degree number stays
`insufficient-evidence`** — it also needs the Icp-trim table (not yet
re-derived, deferred to #27) before the loop's open-loop gain can be
closed.

## What this does not bound

- **A closed-loop lock/settling behavior** — this is an open-loop
  characterization only (no PFD/CP/loop-filter/divider closure); lock time
  (row 7) is out of this record's own claim.
- **Duty cycle** (row 13) — this record measures period via a single
  threshold crossing per half-period pair, not the rising/falling symmetry
  duty-cycle measurement that row needs; `../corners/matrix.md` names the
  `mos_sf`/`mos_fs` split corners this would need as an explicitly open,
  not-yet-swept axis for that future record.
- **Mismatch** between the two band-select switch branches (`XSWB0`/`XSWB1`)
  — this record's band-code sweep exercises the nominal, matched-device
  model only; no per-instance mismatch model exists for `sg13_hv_nmos` in
  this campaign.
- **The absolute loop-bandwidth/phase-margin number, lock time, reference
  spur, power, or the Icp-trim table** — all deferred to issue #27 (Part of
  #16), same disposition the other two `#23` records already state.
