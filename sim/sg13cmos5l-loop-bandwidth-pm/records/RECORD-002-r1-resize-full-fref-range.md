# RECORD-002: resized loop filter, verified against the full amended `f_ref` range (issue #41, DR-006)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #41 (Part of #16, Chipalooza Challenge #6). Supersedes nothing:
  `RECORD-001` measured the **as-drawn** filter (0/90 combinations meeting PM
  >= 45 deg) and stands unedited, with its own frozen netlist snapshot and
  its own unsuffixed `../corners/{results,mom_band,proposal}.csv` and
  `crosscheck.txt`. This record measures the **resized** filter, and against
  a **wider** claim than `RECORD-001`'s own proposal: the full amended
  `f_ref` range from `spec/decision-records/DR-005`
  (`spec/porting-plan.md` row 2 = 3.5-24.4 MHz, row 3 `N` in [64,127]), not
  the single fixed 25 MHz point `RECORD-001`'s proposal was validated at.
- **DUT**: `../netlist-snapshots/loop_filter_resized.spice`, frozen at this
  record's own branch (parent commit
  `15de40cbb38392c5b38b758e263d60a42f60776d`). `XR1` (`rppd`) resized from
  `w=4u l=120u` to **`w=0.6u l=810u`** (see "Why x44.2, not x20" below);
  `XC1`/`XC2` untouched.
- **Claim under test**: `spec/porting-plan.md` row 6/6a (`f_c < f_ref/10`,
  PM >= 45 deg), **and** the curator-added acceptance criterion on issue #41:
  whether the resized filter's `f_c`/PM holds across the *entire* amended
  `f_ref` range, not only the 25 MHz point the pre-existing proposal was
  computed at.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  now writes Parts A-C (unchanged, byte-identical to `RECORD-001`) **and**
  Part D: `../corners/results_resized.csv` (426 rows) and
  `../corners/crosscheck_resized.txt`.

## Pre-resize sanity check (issue #41's own Test Plan)

Before any schematic edit, `./run.sh` was run against the **unmodified**
filter. `results.csv`, `mom_band.csv`, `proposal.csv` and `crosscheck.txt`
reproduced **byte-for-byte identical** to the already-committed files (`git
diff` empty). Confirms the original finding from this environment's own PDK
setup: `f_c` = 0.33-4.64 MHz, PM = 1.55-20.33 deg, **0 of 90** combinations
meet PM >= 45 deg.

## Headline result

**The originally-proposed "R1 x20" scale does not close the loop across the
amended `f_ref` range once operation near the amended floor is included.**
Confirmed directly (not inferred) by re-running the real, resized `rppd`+
`cap_cmomi` subckt at x20 across a widened matrix (both band codes, three
`Kvco` intervals including a new `low` interval near the VCO's own measured
floor, `f_ref` = 4.5-22 MHz, `N` in [64,127]):

| Scenario (x20, real subckt) | Best single trim code across all 3 PVT bundles | Worst-bundle PM at that code |
|---|---|---|
| `band=11, top interval` (the pre-existing proposal's own scenario), `f_ref` >= 9 MHz | 10u | 47.3-58.3 deg (**holds**, matches `RECORD-001`'s 25 MHz point) |
| `band=00, low interval` (near-VCO-floor VCTRL), `f_ref` = 4.5 MHz | 10u | **22.0 deg** (typ 24.4, slow 28.2, fast 22.0) -- **23 deg short of the 45 deg criterion** |

The x20 proposal's own validated scenario (`band=11`, `Kvco` "top" interval,
the exact slice `RECORD-001`'s `proposal.csv` used) **does re-verify cleanly
across its own full amended-range `N`-reachable window** (`f_ref` from 9 MHz
up to 22 MHz for this scenario's own fvco, since band 11's higher `fvco`
structurally cannot reach lower `f_ref` within `N` <= 127): PM = 51.3-58.3
deg at the 10 uA code, real subckt, every reachable point. **But that
scenario never reaches the amended floor at all** -- band 11's fvco is too
high. The floor (3.5-7 MHz) is only reachable by band 00 at low VCTRL, which
the pre-existing proposal never tested, and where x20 fails badly (see
table above).

## Why x44.2, not x20

Because x20 fails a real, ratified-spec-legal operating region (not an edge
case: DR-005 ratified `f_ref` down to 3.51 MHz specifically, and that floor
is *only* reachable near the VCO's own measured floor, i.e. low `VCTRL`),
this record searched for a scale factor that closes the loop across the
**full** matrix: both bands, all three `Kvco` intervals (`low`/`mid`/`top`),
`f_ref` from 3.6 to 24.4 MHz, `N` in [64,127]. Because `R1`'s area-minimizing
geometry (co-scaling `l` up and `w` down by `sqrt(scale)`, see
`sim/sg13cmos5l-loop-filter-momcap/records/RECORD-002`) keeps `Area`
**constant regardless of the scale factor chosen**, there is no area penalty
for picking a larger scale than x20 -- the search below is purely a stability
question, not an area trade.

Real per-corner `R1` was measured (`tb_extract_r.sp.tmpl`) at several
candidate geometries, then swept through `tb_loop_ac_lumped.sp.tmpl` across
the full matrix (an exploratory step, not itself the committed evidence --
the committed evidence is the *real*-subckt Part D run at the chosen
geometry, below):

| Candidate | `R1` (nominal, `res_typ`) | Scale | Worst-case PM margin over 45 deg (lumped estimate, full matrix) |
|---|---|---|---|
| x20 (`w=0.9u l=546u`) | 155.7 kOhm | 19.98x | **-22.6 deg** (at `band=00, low, f_ref=4.5 MHz`) |
| x43.4 (`w=0.6u l=796u`) | 338.3 kOhm | 43.41x | +0.15 deg |
| **x44.2 (`w=0.6u l=810u`)** | **344.2 kOhm** | **44.17x** | **+0.75 deg** (best found) |
| x45.1 (`w=0.59u l=814u`) | 351.7 kOhm | 45.13x | -1.73 deg (at a *different* combo, `band=00, mid, f_ref=5.5 MHz`) |

x44.2 was chosen as the best margin found in this search (not a global
optimum -- the search was a coarse grid, not an exhaustive one). **This
finding is itself informative**: margin does not increase monotonically
with scale -- different (band, interval, `f_ref`) combinations bind at
different scales (the near-floor/low-interval region wants a *larger* `R1`;
some mid-band/mid-interval combinations start failing again above ~x48),
consistent with a single `R1` zero being pulled in two directions by the
huge span of `Icp x Kvco / N` combinations the amended range now legally
allows. See "What this does not close" below.

## Result at the committed geometry (x44.2, real subckt, Part D)

`../corners/results_resized.csv`, 426 rows, real resized `loop_filter`
subckt (not the lumped exploratory search above): **28 of 29** distinct
(band, `Kvco` interval, `f_ref`) combinations with all 3 PVT bundles present
have a trim code meeting **both** criteria (`f_c < f_ref/10`, PM >= 45 deg)
simultaneously at every bundle, with real margins from +0.3 deg up to
+14 deg. **One does not**: `band=00, low interval, f_ref=4.5 MHz` -- the
same near-floor corner the x20-vs-x44.2 search above identified -- where the
best single code (10 uA) gives PM = 44.13 deg (fast bundle, the binding
one; typ = 47.62 deg, slow = 52.23 deg), **0.87 deg short** of the 45 deg
criterion, real subckt.

This is a **25x improvement** in worst-case margin over x20 at the same
corner (x20: PM = 22.0 deg, a 23 deg shortfall; x44.2: PM = 44.13 deg, a
0.87 deg shortfall) for **no additional area cost** (see
`sim/sg13cmos5l-loop-filter-momcap/records/RECORD-002` "Why the geometry
chosen" -- `Area` is held constant by the co-scaling construction regardless
of scale factor). It is not a complete closure of every point in the
amended envelope.

### The pre-existing proposal's own scenario, re-verified

`band=11, top interval` (the exact scenario `RECORD-001`'s `proposal.csv`
validated, at 25 MHz only) at the resized x44.2 filter, 10 uA trim code,
real subckt, across every `f_ref` this scenario's own `N`-reachable window
admits:

| Bundle | `f_ref` (MHz) | `N` | `f_c` (MHz) | PM (deg) |
|---|---|---|---|---|
| typ | 11 | 115 | 1.378 | 57.64 |
| typ | 13 | 97 | 1.592 | 56.13 |
| typ | 16 | 79 | 1.883 | 53.76 |
| typ | 19 | 66 | 2.171 | 51.30 |
| slow | 9 | 116 | 1.132 | 58.27 |
| slow | 11 | 95 | 1.343 | 56.76 |
| slow | 13 | 80 | 1.549 | 54.96 |
| slow | 16 | 65 | 1.831 | 52.30 |
| fast | 13 | 111 | 1.482 | 57.99 |
| fast | 16 | 91 | 1.755 | 56.34 |
| fast | 19 | 76 | 2.036 | 54.33 |
| fast | 22 | 66 | 2.280 | 52.49 |

Comfortable margin (51.3-58.3 deg) at every point. Confirms the resize is
sound for the operating region the original evidence already covered.

## Cross-check: real subckt vs. lumped equivalent (Part D′)

`../corners/crosscheck_resized.txt`, `typ` bundle, band 11, top interval,
`f_ref` = 19 MHz (inside the amended range, `N` = 66):

|  | `f_c` | PM |
|---|---|---|
| real `loop_filter_resized` subckt | 2.171 MHz | 51.30 deg |
| lumped R/C from `loop-filter-momcap` RECORD-002's measured `R1`/`C1`/`C2` | 2.348 MHz | 57.71 deg |
| difference | +8.16% | +6.41 deg |

Larger than `RECORD-001`'s own cross-check at the as-drawn filter (+1.38%
`f_c`, +0.05 deg PM). The lumped model is **optimistic** relative to the
real compact model at this larger `R1`, by a non-trivial margin -- worth
flagging explicitly since the exploratory geometry search above ("Why
x44.2, not x20") used the lumped model, not the real subckt, for its scale
sweep. The **committed** headline numbers above are all from the real
subckt (Part D), not the lumped search, so this discrepancy does not affect
the reported margins -- but it does mean the lumped model should not be
trusted for fine (<10 deg) margin discrimination at this `R1` scale without
a real-subckt spot-check, which is exactly what this cross-check is for.

## What this does not close

- **The single near-floor corner** (`band=00`, low `VCTRL`, `f_ref` around
  4.5 MHz) is **not** closed with margin -- it is 0.87 deg short at the best
  trim code, real subckt. This is close enough that it may be recoverable by
  further R1 tuning, by a coarser or finer trim-code choice this record did
  not sweep (only the standard 6-code ladder), or it may need a `C1`/`C2`
  re-tuning that a pure `R1` resize cannot reach -- this record does not
  settle which. **Filed as a follow-up issue** rather than iterated further
  here (see the PR this record ships in for the issue number) -- this
  record's own search already showed margin is not monotonic in `R1` scale,
  so continued search within this issue's scope risked exactly the kind of
  open-ended optimization `builder.md`'s scope-management guidance warns
  against.
- **Every (band, interval) x `f_ref` combination was not exhaustively
  swept** -- the 12-point `f_ref` grid and 3 Kvco intervals are a
  representative sampling of the amended range, not every possible
  operating point. A future campaign could sweep finer if the near-floor
  gap above is worked further.
- Everything `RECORD-001` already stated as out of scope (large-signal/
  acquisition behaviour, sampled-loop z-domain effects beyond the
  `f_c < f_ref/10` guard, reference spur/jitter/phase noise, a full
  per-`f_ref` trim-code keying table) remains out of scope here too.

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 6/6a**: **substantially improved, not fully closed.** The resized
  filter (x44.2) meets both criteria at 28 of 29 distinct operating regions
  spanning the full amended `f_ref` range, with real, PVT-cornered,
  real-subckt margins; the as-drawn filter met 0 of 90. The one exception
  (near-floor, low-`VCTRL`, `band=00`) is quantified above, not hidden, and
  is not claimed as passing -- this record does not relax the criterion to
  make it pass, per this repo's own CLAUDE.md.
