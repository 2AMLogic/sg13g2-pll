# RECORD-001: reference-input switching thresholds for `pfd` (spec row 2 / R-5)

- **Slug**: `sg13cmos5l-pfd-input-threshold`
- **Issue**: #403 (target-spec row 2 electrical levels, risk R-5). Append-only.
  **This record proposes no V_IL / V_IH spec value.** R-5's gate is DR-002
  ratification plus this bench; the numbers below are the measurement the
  ratifiers look at, not a proposal. No spec row or decision record is edited
  by this record.
- **Reproduce**:
  `sim/sg13cmos5l-pfd-input-threshold/testbench/run_batch.sh`
  (writes `../corners/results.csv`). Axes, ladder geometry and the explicit
  not-measured list: `../corners/matrix.md`.
- **Tool**: ngspice-47 via `klt sim --backend batch --wait-for-capacity 600`
  (client `klt 0.9.3.dev3+gd5d57daf9a14`), deck-list requests submitted from
  the dispatching host in 6 shards. No ngspice ran on the dispatching host.
- **PDK**: PDK ihp-sg13cmos5l revision
  607e18d4bd9214a52575c194b4181ef449f9252f — the `sim/README.md` pin for that
  tree, which is what every deck here loads (`cornerMOShv.lib`, `psp103`/
  `psp103_nqs` OSDI; the reports' `host_resolved` paths are all under
  `$PDK_ROOT/ihp-sg13cmos5l/`). The fleet image's working copy of the tree is
  unstamped, so this run does not independently re-establish the installed
  revision — the same disclosure
  `sg13cmos5l-supply-range/RECORD-001` makes, and the two prior records that
  already caught the working tree drifting from the pin
  (`sg13cmos5l-lock-detector-window/RECORD-011`: the `rhigh` card moved)
  stand. Absolute cross-record comparison to pre-drift records is therefore
  not established; the fractions-of-VDD readings below are the
  tree-drift-robust form.

## DUT

`netlist-snapshots/pfd.spice` — byte-identical to
`design/sg13cmos5l/netlist/pfd.spice` as committed at run time
(sha256 `c4a848e83ceeb1f8440609b629575b4266bf72eb1c3f2a308882ed7a99597587`),
staged verbatim into every request. The SG13G2 sibling `pfd`
(`design/netlist/pfd.spice`) is a different circuit and is **not** measured
(out of scope, issue #403).

## Jobs

| Block | Job | Instance | Units |
|---|---|---|---|
| probe (`typ`, 3.3 V, bring-up before the grid) | `klt-sim-bf86a2a483fd` | i-0b414e38382241ec2 | 3/3 pass |
| shard 0 (`typ` 3.0 + 3.3 V) | `klt-sim-e6ec6f2d1470` | i-0059fdbcaf84a3749 | 18/18 pass |
| shard 1 (`typ` 3.6 + `slow` 3.0 V) | `klt-sim-d800e0393412` | i-07623886981adc551 | 18/18 pass |
| shard 2 (`slow` 3.3 + 3.6 V) | `klt-sim-ab25a5d47a1c` | i-05549e74cd7f065e6 | 18/18 pass |
| shard 3 (`fast` 3.0 V) | `klt-sim-552b2862abb8` | i-085b78553a4795683 | 9/9 pass |
| shard 4 (`fast` 3.3 V) | `klt-sim-86b3376e7497` | i-0af09fc27ce4d17a4 | 9/9 pass |
| shard 5 (`fast` 3.6 V) | `klt-sim-8825bb7ea162` | i-03a21cf1e6c3605d3 | 9/9 pass |

81/81 units pass (9 DC + 72 edge decks). The first shard-3 submit
(`klt-sim-540de68da722`) was refused by the fleet with `batch_no_capacity`
after the 600 s capacity-wait budget; it was resubmitted unchanged ~12 min
later and is the job tabled above. Slowest single deck: 283 s
(`ih_fast_3p6_3p5_d30`).

## Method

Two deck families per corner (templates in `../testbench/`, geometry
regenerated from one set of constants by `threshold_grid.py`):

- **DC** (`tb_pfd_dc.sp.tmpl`): `.dc` sweep of REF 0 -> VDD at VDD/2048 step,
  FB held low so the reset path is inert and only the REF edgedet
  (`XED_UP`) is exercised. Reported on the named internal nodes: `d1` (the
  input inverter `XD1`'s own trip), `xd5` (the 5-inverter delayed leg the
  NAND compares against), `ntmp` (the `XN1` nand2 output — see Results for
  why it never crosses mid-rail and `ntmp_min` is reported instead). REF
  fans out to two different gates inside `edgedet` (`XD1` inv_hv and the
  `XN1` nand2_hv A-input), so "the threshold" is a composite; each number
  below is named for its node.
- **Edge ladders** (`tb_pfd_edge.sp.tmpl`): 32-segment ladder, 16 identical
  REF cycles per segment. `il` decks raise the REF low level 0 -> 0.90·VDD
  (high fixed at VDD); `ih` decks lower the high level VDD -> 0.10·VDD (low
  fixed at 0). Segment 1 is the full-swing control in both directions.
  Registration is counted on edgedet's OUT — the `set_up` net — as the
  rising 50 %-of-rail crossing of every cycle's pulse; `meas` lines sample
  the last edge of each segment, and the boundary is the last segment whose
  sampled crossing exists and lands in its expected window (contiguity
  checked from segment 1; `reduce` flags any non-contiguous deck, of which
  there were none).

**FB is driven, not held.** Inside `pfd`, reset is `XNR UP DN reset_raw …`
and asserts only when UP and DN are both high, so a static FB latches UP on
the first REF edge and every later edge-count reads 1-of-N at *every* level
(a threshold measurement made this way is pure artifact). FB is therefore a
clean full-rail copy of REF at a fixed 5 ns offset (as
`sg13g2-pfd-reset-parity` drives it), identical across the whole ladder so
it is never a second confounding variable. The segment-1 control makes the
artifact cheap to catch: with full-swing REF, **72/72 edge decks** register
their first edge and their full segment 1 — a 1-of-N result here would have
been the bench bug, not a finding.

**Corner reduction (9, not 27).** `spec/target-spec.md` defines the process
bundles as correlated process+temperature *pairs* (fast = `mos_ff`/−40 °C,
typ = `mos_tt`/27 °C, slow = `mos_ss`/125 °C), each carrying its own resistor
corner (`res_bcs`/`res_typ`/`res_wcs`). The coverage AC's "three process
bundles, −40/27/125 °C and 3.0/3.3/3.6 V" is therefore 3 bundles × 3
supplies = **9 corners**, not a 27-point cross product — a 27-point grid
would invent 18 corners the operating box does not define. Stimulus on top:
2 frequencies (3.5, 24.4 MHz) × 2 duties (30 %, 70 %) = 4 points, i.e. 36
edge decks' worth of boundary readings per direction plus 9 DC decks.

Boundary resolution is one ladder step: 0.9·VDD/31 ≈ 87–105 mV (≈96 mV at
3.3 V).

## Results

### DC trip points (V; FB low; `../corners/results.csv` rows `kind=dc`)

| Bundle | VDD | `d1` trip | `xd5` trip | `ntmp` mid-rail crossing | `ntmp` min |
|---|---|---|---|---|---|
| typ | 3.0 | 1.389 | 1.391 | none | 2.549 |
| typ | 3.3 | 1.527 | 1.531 | none | 2.784 |
| typ | 3.6 | 1.668 | 1.673 | none | 3.022 |
| slow | 3.0 | 1.441 | 1.444 | none | 2.566 |
| slow | 3.3 | 1.580 | 1.583 | none | 2.806 |
| slow | 3.6 | 1.720 | 1.722 | none | 3.045 |
| fast | 3.0 | 1.346 | 1.350 | none | 2.519 |
| fast | 3.3 | 1.487 | 1.491 | none | 2.757 |
| fast | 3.6 | 1.632 | 1.638 | none | 2.989 |

- `d1` (the inv_hv input inverter's trip) sits at 43.5–47.8 % of VDD across
  the box. `xd5` tracks `d1` within +2.0 to +6.0 mV (same cell family one
  delay stage later) — the composite threshold is not sensitive to which of
  the two fan-out gates is quoted.
- `ntmp` never crosses mid-rail in a DC sweep at any corner (its series NMOS
  stack only conducts while *both* inputs sit above their trips, and the
  delayed leg's quasi-static swing is not enough to pull it low); the sweep
  minimum is tabled instead. This is why the dynamic decks, not the DC
  sweep, are what the switching question is answered from.

### Dynamic registration boundaries (V; last passing / first failing ladder level)

The boundary ladder step is **identical at all four stimulus points** (both
frequencies × both duties) at every corner — within the ~96 mV ladder
resolution no frequency or duty dependence resolved, so each cell below is
one number per corner, not four.

| Bundle | VDD | V_IL: highest still-registering LOW | (first failing) | V_IH: lowest still-registering HIGH | (first failing) |
|---|---|---|---|---|---|
| typ | 3.0 | 1.306 | 1.394 | 1.606 | 1.519 |
| typ | 3.3 | 1.437 | 1.533 | 1.863 | 1.767 |
| typ | 3.6 | 1.672 | 1.777 | 2.032 | 1.928 |
| slow | 3.0 | 1.394 | 1.481 | 1.694 | 1.606 |
| slow | 3.3 | 1.533 | 1.629 | 1.863 | 1.767 |
| slow | 3.6 | 1.672 | 1.777 | 2.032 | 1.928 |
| fast | 3.0 | 1.306 | 1.394 | 1.606 | 1.519 |
| fast | 3.3 | 1.437 | 1.533 | 1.767 | 1.671 |
| fast | 3.6 | 1.568 | 1.672 | 1.928 | 1.823 |

(Read `V_IL` as: low levels up to the first value still let every rising
edge register; levels from the parenthesised value up do not — the true
boundary is inside one ladder step between them. Symmetrically for `V_IH`.)

### Relation between the dynamic boundaries and the DC trip

- The **V_IL** boundary brackets the static `d1` trip at 32 of 36 stimulus
  points (9 corners × 4 stimulus points). The 4 misses are all
  `typ`/3.6 V: its last-passing low level (1.672 V) sits 3.9 mV *above* the
  DC trip (1.668 V) — inside one ladder step, and physically consistent,
  since a low level a few mV above the static trip still lets the falling
  transition cross the trip region. This is ladder resolution, not an
  anomaly; a finer ladder would be needed to separate them.
- The **V_IH** boundary sits consistently *above* the DC trip, by
  +0.218 to +0.364 V across all 36 points: high levels near the trip no
  longer produce a `set_up` pulse that crosses mid-rail even though the
  static sweep says the inverter has not switched off. Interpretation
  (flagged as interpretation, the measurement above is the finding): with
  the high level near V_M the `XN1` series pulldown loses overdrive before
  `ntmp` can fall far enough for the output inverter to switch, so the
  pulse amplitude degrades below mid-rail first. A corner where this did
  not hold would have been a bench bug; it holds at all 36.

### Binding corners of the operating box

- **V_IL is bound by 3.0 V**, where the still-registering low level is
  lowest: 1.306 V (43.5 % of VDD), at both `typ` and `fast`; `slow`/3.0 V
  allows 1.394 V. Above 3.0 V every corner still registers lows up to
  1.437–1.672 V (43.5–46.5 % of VDD).
- **V_IH is bound by `typ`/3.6 V**: high levels down to 2.032 V
  (56.5 % of VDD) still register everywhere; below 2.032 V the binding
  corner starts failing (first failing level 1.928 V). The other corners
  reach 1.606–1.928 V (53.5–56.5 % of VDD).
- The curator's candidate binding stimulus (30 % duty at 24.4 MHz, the
  shortest high time in the box) did not separate from the other three
  stimulus points at any corner: the ~12.3 ns high time at that point is
  still two orders of magnitude above the edgedet's ~5-inverter-delay
  window, so the bench resolves no stimulus dependence. The grid was sized
  to be able to see it (the 4 stimulus points are in the CSV); the finding
  is that the boundary is bundle+VDD-driven at the ratified range's
  endpoints.

For scale: a rail-to-rail CMOS drive (the row-2 stimulus model) has
enormous margin at every corner — the worst still-registering window per
corner is e.g. `typ`/3.6 V, low ≤ 1.672 V and high ≥ 2.032 V — but these
are measurements of the committed bufferless input stage, not a
recommendation; degraded-swing drivers have the table above as their
budget, and R-5's actual V_IL/V_IH values remain DR-002's ruling.

## Not measured (restated from `../corners/matrix.md`)

- DR-005's proposed 1–25 MHz widening: **not covered** — the grid is the
  ratified row-2 range's endpoints (3.5 / 24.4 MHz), which is what R-5
  gates on.
- The SG13G2 `pfd` (non-port sibling); post-layout parasitics;
  `mos_sf`/`mos_fs` split corners; mismatch Monte Carlo; stimulus points
  inside the 2×2 extremes; an input buffer (none exists in the DUT); the
  srlatch's own latching margin on degraded pulses (registration is
  defined at edgedet's OUT).
- The boundary between the two levels inside one ladder step (~96 mV at
  3.3 V) is unresolved by construction.

Row 2's electrical levels stay open; this record supplies the numbers only.
