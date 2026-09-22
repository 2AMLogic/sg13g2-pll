# Corner matrix — `sg13cmos5l-divider-nrange-retiming`

**Claim under test**: `spec/porting-plan.md` row 3's own `re-derive` disposition
on the divider's retiming-margin closure (issue #36, Part of #16), plus a
functional low-frequency baseline, the divider's actual `N` range, and its
own average supply current (one of the three domains row 11 still needs).

## Why a reduced 9-point matrix

`../testbench/run.sh`'s first committed draft (built exploring this issue,
never executed to completion — see "What the previous attempt left behind"
below) carried the same 21-point full-cross-product PVT array
`sg13cmos5l-cp-icp-trim` uses (5 MOS corners × 3 temps at nominal 3.3 V, plus
a ±10 % supply sub-axis at `mos_tt`/`mos_ss`/`mos_ff` at 27 C). That shape is
appropriate for `sg13cmos5l-cp-icp-trim`'s own DC sweeps (fast per-point), but
`divider_chain` and `dff_tg_hv` decks are **transient** runs against a
316-device (`divider_chain`) or ~20-device (`dff_tg_hv`) netlist with PSP103
compact models, and this record's own environment is compute-bound, not
modelling-bound: a single `divider_chain` transient (a few hundred CKIN
cycles) takes single-digit-to-tens of seconds of wall time, and the `setup`
stage alone would be `2 variants × 21 PVT × 12 TSU = 504` such runs. That
does not fit this issue's own one-session budget, the same reasoning
`sg13cmos5l-vco-kvco-table/corners/matrix.md` ("Why 3 bundles, not the full
cross product") already gives for the same tradeoff on a different DUT.

This record instead uses a **one-factor-at-a-time reduced matrix**: the
nominal point, plus each axis varied independently from nominal, not crossed:

| Point | MOS corner | Temp | VDD | Role |
|---|---|---|---|---|
| 1 | `mos_tt` | 27 C | 3.3 V | Nominal |
| 2 | `mos_ss` | 27 C | 3.3 V | Slow NMOS+PMOS |
| 3 | `mos_ff` | 27 C | 3.3 V | Fast NMOS+PMOS |
| 4 | `mos_sf` | 27 C | 3.3 V | Slow NMOS / fast PMOS split |
| 5 | `mos_fs` | 27 C | 3.3 V | Fast NMOS / slow PMOS split |
| 6 | `mos_tt` | -40 C | 3.3 V | Cold, nominal process |
| 7 | `mos_tt` | 125 C | 3.3 V | Hot, nominal process |
| 8 | `mos_tt` | 27 C | 2.97 V | -10 % supply, nominal process/temp |
| 9 | `mos_tt` | 27 C | 3.63 V | +10 % supply, nominal process/temp |

This is **not** a claim that the true worst case always sits at one of these
9 points rather than at an uncrossed combination (e.g. `mos_ss`/125C/2.97V) —
it is an explicit, stated subset per `sim/README.md`'s own convention ("any
subset ... must state the reason explicitly in the record, not silently drop
an axis"). Every axis the full matrix swept is still represented at its
extremes; only the cross-product between axes is dropped.

## Why `setup` uses only 3 of the 9 points

`setup` additionally sweeps 10 `TSU` values (reduced from a 12-point list,
then extended upward by the #112 campaign to bracket the repaired cell's
~0.5–1.5 ns crossover — see `../testbench/run.sh`) per
corner per variant. Even at the reduced 9-point matrix this is `9 × 10 × 2 =
180` runs; the `dff_tg_hv` flop's own required setup time is dominated by its
own internal speed (which the *process* corner already brackets), not by
supply or temperature acting independently of process, so this stage further
restricts to the classic 3-bundle bracket also used for
`sg13cmos5l-vco-kvco-table`: nominal (`mos_tt`/27C/3.3V), slowest
(`mos_ss`/125C/3.3V), fastest (`mos_ff`/-40C/3.3V) — `PVT_SETUP` in
`../testbench/run.sh`. This still reports the setup-time requirement across
the full corner bracket the retiming-margin claim needs (worst case to best
case), just not at the full 9-point resolution.

## What the previous attempt left behind

An untracked, uncommitted, partially-run copy of this same testbench existed
in this worktree before this record. It had run only as far as
`corners/opconv.csv`'s header line (zero data rows) — the script died on its
first `opconv`-stage iteration. Root cause (fixed in this record's own
`run.sh`, see its `runsp()` and opconv-stage comments): under
`set -euo pipefail`, a `grep -oiE ... | head -1 | tr -d ','` pipeline that
finds no match returns non-zero (`pipefail`), and an unguarded assignment
`note="$(...)"` at that exit status triggers `set -e` and kills the whole
script — which happens on both a clean convergence *and* an unmatched-message
timeout, i.e. on most real outcomes. This record's own `run.sh` fixes that
with an explicit `|| true`, and additionally bounds every `ngspice` call with
`timeout` (default 150 s) after confirming independently, by hand,
that the as-drawn design's bare `op` analysis with no `.ic` does not
terminate within 5 real minutes (see the record's own Finding 1) — the exact
failure mode issue #36's own "Breadcrumbs from #27" section already reported
qualitatively. The testbench decks, corner matrix shape, and the two-variant
(`asdrawn`/`fbfix`) structure are otherwise unchanged from that prior attempt
— they were sound, only the harness script's error handling was not.

## Axes not swept

No RES corner axis and no MOM-cap axis: `divider_chain`'s own netlist
expands to `sg13_hv_nmos`/`sg13_hv_pmos` instances only (confirmed by reading
`../netlist-snapshots/divider_chain.spice`) — the same inapplicability
`sg13cmos5l-cp-icp-trim`'s own matrix documents for its own all-MOS DUT.

## Issue #112 re-verification campaign — what changed

The #112 repair campaign (see `../records/RECORD-003`) reuses this matrix
shape unchanged (same 9 points, same 3-bundle `setup` bracket) but changes
three things about how `../testbench/run.sh` runs it:

- **DUT**: single variant, `repaired` — the committed design as repaired by
  issue #112 (second feedback inverter per `dff_tg_hv` latch), frozen at
  `../netlist-snapshots/divider_chain_repaired.spice`. The two historical
  variants (`asdrawn` broken, `fbfix` weak-keeper proposal) are retired from
  the sweep; their results stay in RECORD-001/RECORD-002.
- **`reltol`**: whole-chain stages (`func`, `retime`) run at ngspice's own
  default `1e-3`, not the `5e-3` RECORD-001 used for wall-clock reasons.
  On the repaired chain the `5e-3` setting is demonstrably numerically
  fragile — a deterministic `Timestep too small` collapse at `xdiv.xd0.nt`
  on the very first baseline corner (RECORD-003 Finding 2), which also
  retrospectively explains RECORD-001 Finding 4's reproducibility trouble.
  The tolerance cross-check (`tol_convergence.csv`) runs the primary
  `1e-3`, an intermediate `2e-3`, and the fragile `5e-3` — the last
  through a failure-tolerant wrapper so its collapse is recorded as NA
  data rows rather than aborting the stage.
- **`func` stage additions**: the programming-word sweep adds two mixed
  words (`011111`, `101010`) to the per-bit-weight + ceiling set, and a new
  `edge` group runs the ceiling word (`111111`, `N=127`) at the slowest and
  fastest `setup`-bracket bundles, so both ends of the claimed `N` range
  carry PVT bracket coverage (`N=64` already has the full 9-point matrix
  from the baseline group).
