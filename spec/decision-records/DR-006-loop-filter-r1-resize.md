# DR-006: `loop_filter` R1 resize -- geometry, scale factor, and the R1-vs-C1 area trade

- **Status**: proposed
- **Date**: 2026-08-30
- **Decided by**: Builder agent, issue #41

## Context

`sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-001` measured the
as-drawn `loop_filter` (`XR1` = `rppd` `w=4u l=120u`, ~7.79 kOhm nominal)
against `spec/porting-plan.md` row 6/6a's stability criteria (`f_c <
f_ref/10`, phase margin >= 45 deg) across 90 real-subckt PVT/trim
combinations: **0 met the PM criterion.** The filter's own zero
(`f_z` = 1/(2*pi*R1*C1) ~ 9-17 MHz) sat one to two decades above any
crossover the loop could reach, so the loop behaved as an uncompensated
double integrator at every reachable operating point. `RECORD-001`'s own
`corners/proposal.csv` identified `R1` scaled ~20x (with a 10 uA `Icp` trim
code) as closing the loop at a single fixed `f_ref` = 25 MHz point (PM
58.6-61.8 deg, `f_c` 1.50-1.63 MHz).

Two things changed the target this decision has to hit, both already
recorded elsewhere and cited here rather than re-derived:

1. **DR-005** (merged via PR #46, resolving issue #40) amended
   `spec/porting-plan.md` row 2 (`f_ref`) from the ported 1-25 MHz to
   **3.5-24.4 MHz**, and row 3 (`N`) from `[4,64]` to **`[64,127]`** --
   derived from the measured VCO band (445.3-1562.0 MHz) divided by the
   divider's own structural `N` range. The consequence for row 6/6a DR-005
   states explicitly: the `f_c < f_ref/10` ceiling is now **0.35-2.44 MHz**
   across the amended range, worst case **350 kHz** at the new 3.5 MHz
   floor -- a range the x20 proposal's own 25 MHz validation point never
   probed.
2. Issue #41's curator added an explicit acceptance criterion: the chosen
   `R1` value must be checked against this *entire* amended `f_ref` range,
   "especially near the 3.5 MHz floor," before this issue can be considered
   done -- because the pre-existing evidence (`RECORD-001`'s proposal) was
   validated at exactly one point, the *loosest* corner of the amended
   range, not its tightest.

This record documents the geometry chosen, the scale factor actually
verified (which is **not** x20 -- see "Decision" below), and the `R1`-vs-`C1`
area trade the original evidence raised but deliberately left unsettled.

## Decision

**`R1` is resized from `rppd w=4u l=120u` to `rppd w=0.6u l=810u` (`b=0
m=1`), landing `R1` ~44.2x the as-drawn value (~344.2 kOhm nominal, `typ`
corner).** This is a materially larger scale than `RECORD-001`'s original
x20 proposal. Full derivation and the real-subckt evidence:
`sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002`,
`sim/sg13cmos5l-loop-filter-momcap/records/RECORD-002`.

### Why x44.2, not the pre-existing x20 proposal

Re-running the real, resized `loop_filter` subckt at x20 across the full
amended matrix (both `Kvco`-vs-band-code corners, three `Kvco` operating
intervals including a "low" interval near the VCO's own measured floor,
`f_ref` spanning the amended 3.5-24.4 MHz range with `N` in [64,127])
showed x20 **does not** close the loop everywhere in this matrix. It
re-verifies cleanly (PM 51.3-58.3 deg, real subckt) for the *specific*
scenario `RECORD-001`'s own proposal used (`band=11`, `Kvco` "top"
interval) across that scenario's own reachable `f_ref` window -- but that
scenario's `fvco` is too high to ever reach the amended floor. The floor
(3.5-7 MHz) is only reachable near the VCO's low-`VCTRL` operating region
(`band=00`, "low" `Kvco` interval), where x20's real-subckt PM bottoms out
at **22.0 deg** at `f_ref` = 4.5 MHz -- 23 deg short of the 45 deg
criterion, not a marginal shortfall.

A scale search (real per-corner `R1` measured via `tb_extract_r.sp.tmpl`,
swept through the lumped-equivalent AC testbench across the full matrix)
found x44.2 (`w=0.6u l=810u`) as the best-margin candidate: worst-case
lumped-model PM margin +0.75 deg above the 45 deg criterion, versus x20's
-22.6 deg. **This is not a monotonic search** -- x45.1 already regresses at
a *different* binding combination (`band=00, mid` interval, `f_ref` =
5.5 MHz), showing the near-floor and mid-band operating regions pull the
single `R1` zero in different directions as scale increases. See DR-006's
sibling records for the full candidate table.

**Re-verified at the committed geometry with the real subckt** (not the
lumped exploratory search):
`sim/sg13cmos5l-loop-bandwidth-pm/corners/results_resized.csv`, 426 rows.
28 of 29 distinct (band, `Kvco` interval, `f_ref`) combinations with all
3 PVT bundles present meet both criteria simultaneously, real margins
+0.3 to +14 deg. **One does not**: `band=00`, low `VCTRL`, `f_ref` =
4.5 MHz -- best trim code (10 uA) gives PM = 44.13 deg (fast bundle, the
binding one), **0.87 deg short**. This is a 25x improvement in worst-case
margin over x20 at the identical corner (22.0 deg -> 44.13 deg), for
**zero additional area cost** (see below) -- but it is not a complete
closure of the amended envelope, and this record does not claim it is.
That one remaining gap is filed as a follow-up issue rather than iterated
further here (see "Consequences").

### Geometry: why co-scale `l` and `w`, not scale either alone

`rppd`'s DRC bounds (`sg13cmos5l_tech.json`): `rppd_minW = 0.5u`,
`rppd_maxL = 1m` (1000 um). Both single-axis scalings are infeasible at
either the x20 or the x44.2 target:

- **Length-only** at x20 needs `l` = 120u * 20 = 2400u -- exceeds
  `rppd_maxL` (1000u) by 2.4x. At x44.2, worse still.
- **Width-only** at x20 needs `w` = 4u / 20 = 0.2u -- violates `rppd_minW`
  (0.5u). At x44.2, worse still.

`rppd`'s own DC resistance (`R ~ 70e-6/w + 260*l/(w+6e-9)`, cross-checked
against the real `r3_cmc` compact model to <0.2% at the as-drawn geometry)
is dominated by the `l/w` "squares" term for `l >> w`. **Co-scaling `l` up
and `w` down by `sqrt(scale)`** is not just how the DRC bounds are
satisfied -- for a fixed sheet resistance, `R ~ l/w` and `Area = l*w`, so
`R*Area ~ l^2`: this specific split holds `Area` **constant regardless of
the scale factor chosen**. This is why moving from x20 to x44.2 (more than
doubling the resistance) cost essentially nothing in area: 480 um^2
(as-drawn) -> 491 um^2 (x20) -> 486 um^2 (x44.2), all within ~2% of each
other. The area question this decision actually had to answer was "R1 vs.
C1," not "which scale factor" -- see below.

### The R1-vs-C1 area trade

`RECORD-001`'s own proposal noted, but did not settle, the alternative of
scaling `C1` instead of `R1`. This record settles it quantitatively:

| Approach | Area cost | `Icp` consequence |
|---|---|---|
| **`R1` resize (chosen)**, any scale in the 20-44x range tested | **~480-491 um^2** (co-scaled `rppd`, ~+1-2% vs. as-drawn) | None -- `Icp` trim ladder unaffected |
| `C1` scaled 20x instead (`cap_cmomi`) | ~34 pF needed, ~183 x 183 um, **~0.033 mm^2** -- ~22% of `spec/porting-plan.md` row 15's entire 0.15 mm^2 filter area budget, for one capacitor | Pushes required `Icp` to ~200 uA, off the top of the measured trim ladder (`sg13cmos5l-cp-icp-trim`'s own sweep tops out well below that) |

The `R1` route is decisively cheaper, by roughly two orders of magnitude in
area, and does not strain the `Icp` trim ladder. This holds regardless of
which `R1` scale factor is chosen (x20 or x44.2) -- the co-scaling
construction above means the area verdict does not change as the target
scale factor increases, which is exactly why this record was free to adopt
the larger, better-margined x44.2 value once the amended `f_ref` range
showed x20 was insufficient, without reopening the area trade.

### Manufacturability caveat (schematic-level only)

An 810 um single straight `rppd` leg is a real layout concern this record
does not resolve: `rppd`'s own pycell exposes a `b` (bends) parameter for
meandering a long resistor into a compact serpentine footprint, and a
future layout pass should use it rather than drawing a single 810 um strip.
This decision is schematic/netlist-level only (matching this issue's own
scope); `b=0` is kept in the schematic for now, consistent with the
as-drawn instance's own convention.

## Alternatives considered

- **Keep the pre-existing x20 proposal as-is** -- rejected: re-verification
  against the amended `f_ref` range (a curator-added, evidence-required
  acceptance criterion) shows it fails by 23 deg of phase margin at a real,
  ratified-spec-legal near-floor operating point. Not a rounding-error
  shortfall.
- **Scale `C1` instead of `R1`** -- rejected: costs ~22% of the entire
  filter area budget for one capacitor and pushes `Icp` off the top of the
  measured trim ladder (see "R1-vs-C1 area trade" above), versus `R1`'s
  ~1-2% area cost at any scale tested.
- **Pure single-axis `R1` geometry scaling** (length-only or width-only) --
  rejected: both violate `rppd`'s own DRC bounds (`maxL`=1mm, `minW`=0.5u)
  at either x20 or x44.2. Not drawable.
- **Keep searching for a scale factor that closes 100% of the amended
  matrix with comfortable margin** -- rejected for *this* record: the
  search already showed margin is non-monotonic in scale (different
  operating regions bind at different scale factors), so continued search
  within this issue's scope risked an open-ended optimization loop rather
  than a bounded decision. x44.2 (the best margin found in a real,
  documented search) is adopted, and the one remaining gap is filed as a
  follow-up issue instead.

## Consequences

**What this makes possible**:

- `spec/porting-plan.md` row 6/6a moves from "0 of 90 combinations meet the
  criteria" to "28 of 29 distinct amended-range operating regions meet both
  criteria, with real margin" -- a substantial, evidence-backed
  improvement, not a full closure.
- The `R1`-vs-`C1` area question `RECORD-001` raised but did not settle is
  now settled quantitatively, and settled in a way that is robust to the
  specific `R1` scale factor chosen (the co-scaling geometry construction
  holds `Area` ~constant across the whole 20-44x range tested), so a future
  record revisiting the remaining near-floor gap does not need to re-open
  this area trade.

**What this makes harder / what is accepted**:

- One operating region (`band=00`, low `VCTRL`, `f_ref` around 4.5 MHz) is
  **not** closed with margin -- 0.87 deg short at the real subckt's best
  trim code. This is a real, quantified, accepted gap, not glossed over.
  Filed as a follow-up issue for a future record to close (via finer trim
  granularity, a further `R1` search, or a `C1`/`C2` re-tuning this record
  does not attempt).
- The lumped-equivalent testbench (`tb_loop_ac_lumped.sp.tmpl`), used for
  the exploratory scale search, was found to diverge from the real subckt
  by up to +8.16% `f_c` / +6.41 deg PM at this larger `R1` scale (versus
  +1.38%/+0.05 deg at the as-drawn scale in `RECORD-001`'s own cross-check)
  -- larger than the as-drawn filter's own lumped-vs-real agreement. A
  future scale search at this `R1` magnitude should real-subckt spot-check
  more densely than this record did, not rely on the lumped model alone for
  fine margin discrimination.
- The 810 um `rppd` leg (`b=0`) is a layout concern this decision defers to
  a future layout pass (see "Manufacturability caveat" above) -- not a
  blocker for this schematic-level decision, but not free either.

**What remains open**:

- Whether the one remaining gap needs a `C1`/`C2` re-tuning (not just
  `R1`), a finer trim-code ladder, or is acceptable as-is given its small
  (<1 deg) size relative to model/process uncertainty already documented
  elsewhere in this repo (e.g. the ±20% MOM-cap band's own ~0.4-2 deg PM
  swing at other operating points) is a design judgement call this record
  does not make. Filed as a follow-up issue.
- Whether `f_ref` operation this close to the amended floor (3.5-5 MHz) is
  actually used by any real system-level frequency plan, or is a
  theoretical corner of the ratified range that a future frequency-planning
  decision might narrow away, is likewise not settled here.
