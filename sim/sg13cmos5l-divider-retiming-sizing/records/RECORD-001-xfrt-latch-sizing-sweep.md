# RECORD-001: `dff_tg_hv` width-sizing sweep against the row-3 one-edge retiming closure (issue #189)

- **Slug**: `sg13cmos5l-divider-retiming-sizing`. Append-only. Consumes, does not edit,
  `../sg13cmos5l-divider-nrange-retiming/` (RECORD-003 DUT, harness templates).
- **Issue**: #189 (spec row 3, R-3). **Outcome: the acceptance bar (closing bound >= 1562.0 MHz at 9
  corners) was NOT met, and this record does not claim a closing bound for any resized variant.** It
  gives the quantified limit the issue's alternative acceptance asks for, on a *partial* campaign.
- **Tool / backend**: ngspice-46 via `klt sim --backend batch --wait-for-capacity 600` (client
  `klt 0.9.2.dev661+g1de5c0432aad`), PDK `ihp-sg13cmos5l`. Every grid ran on the Spot fleet. Jobs:
  probe `klt-sim-e27f65264710` (16 units, baseline, tt only); uniform-scale setup (144 units) and
  retime (6 units) sweeps (job ids were printed to stderr and not kept; reports in `../corners/*.gz`);
  sizing setup sweep `klt-sim-c1e9936f64b0` (384 units, 8 variants x 3 corners x 16 `TSU`, all pass).
  One local debug probe (two single `ngspice -b` decks, tt/27 C, waveform `meas` only) was run to
  interpret the setup cliff; it is not a result.
- **PDK trees**: as in `../sg13cmos5l-divider-nrange-retiming/records/RECORD-005`; the worker PDK
  revision is not independently stamped (`/opt/pdk`, no stamp). Not re-established here.
- **Reproduce**: `testbench/gen_sizing_requests.py <setup|retime> <c:f>... [--corners tt]` writes decks
  + a `klt sim` request (`b` = base, or `kt/ki/kf/ko` width scales); `testbench/analyze.py <report dirs>`
  reduces them. `b:b` regenerates the frozen `divider_chain_repaired.spice` byte for byte (checked).

## Method

Variants scale `w` in private copies of the `inv_hv`/`tgate_hv` leaves inside `dff_tg_hv`, by group:
`kt` forward TGs (XTG1/XTG2), `ki` storage inverters (XIM/XIS), `kf` feedback (XIMF/XISF/XTGFBM/XTGFBS),
`ko` output buffer (XBQ). Only widths change (`L=0.5u`, `ng=1`, `m=1`). `c` applies to the 12 flops in
the six `div23_cell`s, `f` to `XFRT`. Stimuli, 3-corner setup matrix, 9-point retime matrix and the
`F_close = 1/(t_arr + t_setup)` arithmetic are RECORD-003 Finding 4's; the `TSU` list is refined to 16
points (1500 ... 0 ps). A variant's `t_setup` bracket is `(lo, hi]` with `hi` the smallest `TSU` such
that **every** tested `TSU >= hi` captures (isolated captures at large `TSU` do not count; see Finding 2).

## Finding 1: uniform width scaling does not help and breaks the chain

| Variant (all flop devices x) | setup bracket tt/27, ff/-40 (ps) | ss/125 (ps) | retime tt/27 |
|---|---|---|---|
| base | (500,600] | (1000,1500] | `t_arr` 484.9 ps, `tfb-tdiv` 636.4 ps, 2.372 mA; `F_close` <= 922 MHz (600 ps upper bound) |
| `f` x2, x4 (XFRT only) | identical | identical | x2: chain mis-divides (2nd `DIVOUT` rise at 4.49 ns); x4: `FB` never toggles |
| `c` x2 (all 12 chain flops) | not run (setup deck is single-flop; same as `f` x2 by construction) | | `DIVOUT` never toggles (dvo_max 34 mV); x2/x4 with `f` x1/x2/x4 likewise (59, 93 mV) |

A self-loaded latch scaled uniformly keeps its RC; only the unscaled `nand3`/`nor2`/`inv_hv` drivers
see more load. Nominal-corner only; no other corner was run for these. The `922 MHz` baseline differs
from RECORD-003's 866 MHz because this campaign re-measured `t_arr` (484.9 vs 454.9 ps) and uses a
finer `TSU` list; both are single runs, not reconciled.

## Finding 2: the setup cliff is a clock-phase race-through, not a latch settle time

Local waveform probe, base flop, tt/27 C, clk 50% rising at `t_cap`, high until about `t_cap-260 ps`:
at `TSU = 600 ps`, `M` already follows `D` between `t_cap-600` and `t_cap-500` (D arrives about 40 ps
after the *previous* rising edge, while `CKBB` is still low, so TG1 is still passing); it is captured
via the previous transparent phase. At `TSU = 500 ps` `D` arrives while TG1 is closed, the master opens
at about `t_cap-260`, and `M` only reaches 1.95 V at `t_cap` (0.77 V at `t_cap-50`): the master needs
more than the ~260 ps low phase. So "`t_setup` = 500-600 ps" really says the master cannot settle
inside the transparent window, and the deck samples `Q` at `t_cap + T/4`, so it also folds in clk->Q.
(`meas` values at 13 time points, deck `setup_*_mos_tt_27_3p3_{500p,600p}`; not kept as a file.)

## Finding 3: per-group sizing moves only the slow corner

Sizing sweep (`../corners/setup-sizing-sweep2.txt`): variants (`kt/ki/kf/ko`) `1/1/.5/1`, `1/1/.25/1`,
`2/1/.5/1`, `2/1/.25/1`, `1/.5/.5/1`, `2/.5/.5/1`, `1/1/.5/2`, all on `XFRT`:

- tt/27 C and ff/-40 C: bracket `(500,600]` ps in **every** variant, identical to base.
- ss/125 C: `(600,700]` ps in every variant with `kf <= 0.5` versus base `(1000,1500]` (a 300-800 ps gain).
  `kt`, `ki`, `ko` made no difference at the 100 ps `TSU` resolution used.

Weakening the feedback helps the slow corner (less contention with the write path) but not the
typical/fast corners, whose floor is set by the phase window, not the feedback.

## Quantified limit (the issue's alternative acceptance)

The top of band needs `t_arr + t_setup <= T_vco = 640.2 ps`. Measured baseline `t_arr` = 484.9 ps
(tt/27, six-stage ripple). `t_setup` at tt/27 and ff/-40 is > 500 ps for **all 8 sizings** tried
(base + 7), so closing at 1562.0 MHz would need `t_arr` <= ~140 ps, 3.5x below the measured ripple
delay. Best value for tt/27 with a measured `t_arr`: `F_close <= 922 MHz` (base, not improved). No
resized variant has a measured `t_arr` (the chain retime runs were not done for the Finding-3 variants),
so **no** improved closing bound is claimed for them. Limits: the ripple arrival and a setup floor that
width sizing in these four groups does not move at tt/ff.

## Not done (stated, not hidden)

- No variant was carried to a 9-corner retime campaign, the 20-point functional matrix, or an area /
  power (row 11) comparison; no netlist was regenerated and `design/` is unchanged (no variant was
  adopted).
- Retime for the Finding-3 variants, a finer `TSU` grid near the new `ss/125` bracket, and sizing of the
  `nand`/`nor`/`inv` glue and of the clock inverters (`XICLK`/`XICKBB`, not scaled) were not run.
- Offline fixture only; no live behavior beyond ngspice. Spec not changed.

## Proposed decision

`spec/decision-records/DR-012-row3-retiming-sizing-limit.md` (proposed): R-3 stays open; ratifiers may
read this record as the evidence for the "accept a lower top-of-band" branch, or fund a structural change.
