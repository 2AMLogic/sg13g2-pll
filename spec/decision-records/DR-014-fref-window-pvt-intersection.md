# DR-014: row 2's `f_ref` window is a corner union on a `Det` row — restate the lockable window as the PVT intersection

- **Status**: proposed
- **Date**: 2026-11-15
- **Decided by**: Builder agent, issue #426
- **Related**: #426 (this issue — the finding, the scope and the arithmetic
  below), PR #427 (open; commits the 125 C open-loop evidence this record
  cites by number, not by path, until it merges), #389 (the closed-loop
  campaign whose spec-side hand-off filed this finding), DR-005 (whose
  row-2 numeric derivation this record supersedes), #296 / ruling r7-q30 /
  #301 (the 50 MHz reference-input extension — a different claim; see
  Decision), R-1 / R-13 in `spec/target-spec.md` (which band the spec binds
  to; this record joins that ruling, it does not answer it)

## Context

`spec/target-spec.md` row 2 ("Reference input", `Kind` = **Det**) states
`f_ref` = 3.5 to 24.4 MHz with the derivation printed in the cell:
`3.51 = 445.3/127`, `24.4 = 1562.0/64`. Those two endpoints come from
**different, opposite corners** of the committed Kvco table
(`sim/sg13cmos5l-vco-kvco-table/corners/results.csv`, the primary table row
1's "Measured by" cell names; the SG13G2 corroboration table reproduces the
same bundle statistics): the floor from the `slow` bundle's slowest point
(445.3 MHz), the ceiling from the `fast` bundle's fastest (1562.0 MHz). No
single corner supports both. That is a corner **union**, while the spec
file's own legend says a `Det` row's "bound is a worst case over a declared
corner set, checked by a corner sweep" — the worst case over the corner set
is the **intersection** of what every declared corner supports. Reproduced
from the committed CSV:

```
$ python3 -I -c "
import csv, collections
by=collections.defaultdict(list)
for r in csv.DictReader(open('sim/sg13cmos5l-vco-kvco-table/corners/results.csv')): by[r['pvt_bundle']].append(float(r['freq_hz'])/1e6)
f={b:min(v) for b,v in by.items()}; c={b:max(v) for b,v in by.items()}
print('floor', {b:round(x,1) for b,x in f.items()})
print('ceil ', {b:round(x,1) for b,x in c.items()})
print('union     [%.4f, %.4f] MHz' % (min(f.values())/127, max(c.values())/64))
print('intersect [%.4f, %.4f] MHz' % (max(f.values())/127, min(c.values())/64))"
floor {'typ': 494.0, 'slow': 445.3, 'fast': 548.2}
ceil  {'typ': 1359.1, 'slow': 1113.8, 'fast': 1562.0}
union     [3.5060, 24.4058] MHz
intersect [4.3167, 17.4029] MHz
```

The union reproduces row 2's committed `3.5 to 24.4` exactly — the committed
number *is* the union, not a rounding of something else.

The defect first **bit** in the closed-loop proposal deck's 125 C runs
(issue #426; the open-loop evidence is committed by PR #427). The deck chose
`f_ref` = 20 MHz, `N` = 64 — `f_out` = 1280 MHz — justified against
`typ` = `mos_tt`/**27 C** band `11`, which the committed table measures at
1161.9 to 1359.1 MHz over `VCTRL` 2.1 to 2.7 V (the deck's corner matrix,
`sim/sg13cmos5l-closed-loop-lock/corners/matrix.md` on `main`, quotes the
same figures in its `f_out target` row; PR #427 edits that file, so rows are
located by label here). The run is at **125 C**, in the same band `11` over
the same swept `VCTRL` span, where the deck measured 1214.5 MHz at 2.7 V —
144.6 MHz slower (`1359.1 - 1214.5`) — and 1270.1 MHz at the 3.3 V rail,
9.9 MHz short of 1280 MHz (issue #426 / PR #427). Where that measurement
sits matters: `1270.1/64` = 19.845 MHz is **above** the intersection
ceiling derived below (17.403 MHz), so this measurement does not set the
corrected number — the committed `slow` row already bounded it at
1113.8 MHz. It is the first operating point to make the union defect bite,
not its arithmetic basis.

The operating box made the hole invisible: the 3-bundle subset couples
process with temperature (`fast` = `mos_ff`/-40 C, `typ` = `mos_tt`/27 C,
`slow` = `mos_ss`/125 C, per `spec/target-spec.md` "Operating box"), so
`mos_tt`/125 C exists in no committed row — the deck's measurement is the
first such point the repo has. A legal-looking interpolation off the `typ`
row survived review for the same reason. The deck's `f_ref` row inherited
defect 1 directly: it cites "DR-005's amended range (3.51–24.4 MHz); chosen
near the ceiling" — 20 MHz is inside the union but above the 17.403 MHz
intersection ceiling.

## Decision

**Row 2's lockable `f_ref` × N window is restated as the PVT intersection,
4.317 to 17.403 MHz at `N` in [64, 127]**, derived from the committed Kvco
table only:

- **Floor**: `548.2/127` = **4.317 MHz** — the **`fast`** bundle's own
  minimum. The fast VCO cannot tune down to the `slow` floor of 445.3 MHz,
  so the union floor is not a worst case any single corner supports.
- **Ceiling**: `1113.8/64` = **17.403 MHz** — the **`slow`** bundle's own
  maximum. The union ceiling of 24.4 MHz is reachable only at the `fast`
  bundle's best case.

This supersedes **DR-005's row-2 numeric derivation only**. Row 2 keeps the
union text (annotated, not overwritten, so the record trail shows both
derivations), and DR-005's qualitative conclusion — row 3's `N ∈ [64, 127]`
is structural, row 2's floor moves up materially from the ported 1 MHz —
**stands unchanged**. Row 3 is not touched. DR-005 itself asked for exactly
this kind of follow-up: "if #43's eventual fix produces a materially
different re-measured VCO band, the *specific* MHz values this record
derives … need a follow-up, superseding decision record". The trigger here
is a derivation defect rather than #43, but the superseding-record clause
applies the same way, and for the same reason: the qualitative direction
survives, the specific MHz values do not.

**17.403 MHz is conservative, by a bounded but unmeasured amount.** The
committed table stops at `VCTRL` = 2.7 V against a 3.3 V supply. At
`mos_tt`/125 C the last 0.6 V buys 55.6 MHz (1214.5 to 1270.1 MHz; issue
#426 / PR #427), so every corner's true rail ceiling is higher than its
tabulated ceiling by a bounded amount, and the `slow`-corner rail ceiling
is unmeasured. Extending the table to the rail is owed to the Kvco-table
campaign; this record simulates nothing and changes no bench.

**What this record does *not* bound: the reference-input interface.** Row 2
carries two claims under one name. Its title and `Partition` ("Reference
input / Analog (`pfd` input)") describe an **interface capability** — what
the `pfd` and `lock_detector` inputs can accept. Its numbers are pure
`f_out/N` arithmetic — **this PLL's lockable `f_ref` × N window**. Operator
ruling **r7-q30** on #296, implemented by #301, extends the *interface*
claim to 50 MHz. That extension is **not contradicted** by this correction:
a 50 MHz reference input is unremarkable, while 50 MHz × `N` = 64 = 3.2 GHz
is nowhere near this ring's 1562.0 MHz best-corner ceiling — an `f_ref` the
interface can accept but the loop cannot lock to is exactly the distinction
row 2 must carry. The two records compose: #301 owns the interface half,
this record bounds the lockable-window half. The ruling is not
re-litigated here.

## Alternatives considered

- **Widen the band-`11` coarse step / add a hotter band step** — rejected.
  The band select is a 2-bit source-degeneration ladder in `vco_bias`
  (`XRDEGB0` always on; `XSWB0`/`XSWB1` shunt `XRDEGB1`/`XRDEGB2`, per
  `design/sg13cmos5l/netlist/vco.spice`), so band `11` is already minimum
  degeneration. A third bit changes the `vco` interface (new pin → symbol,
  top level, layout, LVS, every testbench).
- **VCO core sizing/scaling for the hot corner** — rejected. DR-005 already
  rejected the VCO-change candidate on the record (laid out, DRC-clean,
  schematic-matched), and `spec/target-spec.md` R-1 reports the routed,
  extracted `vco` at 0.4768 to 0.5312 times the schematic frequency
  (223.7 to 789.5 MHz) with the band question still unruled — a 9.9 MHz
  schematic shortfall is dominated by an unresolved ~2x post-layout gap.
  Any `vco_bias` degeneration resize also moves *every* band and corner,
  invalidating the committed Kvco table and every campaign keyed to it
  (`loop-bandwidth-pm`, the Icp trim table / DR-007 / DR-008,
  `lock-detector-window`). `spec/porting-plan.md` row 3 already assigns
  that work to the device-characterization sizing campaign (DR-001 T1
  items 8–9).
- **Re-scope the row so the 1280 MHz target becomes legal again** —
  rejected. That is the relaxation CLAUDE.md forbids. This correction
  narrows a capability claim on methodology grounds and leaves the 125 C
  non-acquisition standing as a real, recorded result.

## Consequences

- Row 2's `Status` moves **M → O**: the row was never measured (its own
  "Binding corner" cell reads "n/a (arithmetic on the row 1 corners)" —
  column 9, not the "Measured by" cell, which separately reads "derived
  from the row 1 record"), and the corrected window needs a ruling. **R-13**
  joins it to R-1: both windows are arithmetic on row 1's schematic band,
  so a ruling that binds the spec to the post-layout band recomputes this
  one too.
- Closed-loop frequency planning at hot corners must pick `f_ref`/`N`
  inside the intersection, or extend the Kvco table to the rail first. The
  1280 MHz / 125 C non-acquisition is the expected behavior of the
  committed part at that point, not a defect of it.
- Nothing measured is withdrawn: the union endpoints remain correct as a
  union, DR-005's qualitative conclusion stands, and row 3 is untouched.
- Owed work, not done here: extend the Kvco table to `VCTRL` = 3.3 V and
  add decoupled process-x-temperature points (including `mos_tt`/125 C) —
  whoever does it retires the conservatism bound above and can narrow this
  window on the record.
