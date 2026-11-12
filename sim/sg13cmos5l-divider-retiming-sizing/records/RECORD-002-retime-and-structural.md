# RECORD-002: 9-corner retime of feedback-weakened `dff_tg_hv`, opposite-edge retiming, and the slow-corner divider ceiling (issue #189)

- **Slug**: `sg13cmos5l-divider-retiming-sizing`. Append-only; RECORD-001 is not edited. Consumes
  `../sg13cmos5l-divider-nrange-retiming/` (RECORD-003 DUT, harness templates) unchanged.
- **Issue**: #189 (spec row 3, R-3), remaining increment after RECORD-001. **Outcome: the acceptance bar
  (closing bound >= 1562.0 MHz at all 9 corners) was NOT met.** This record gives the best achieved
  bound per corner, what limits it, and two observations that bear on how the bound should be read
  (Findings 3 and 4). No variant is adopted; `design/` and the spec are unchanged.
- **Tool / backend**: ngspice-46 via `klt sim --backend batch --wait-for-capacity 600` (client
  `klt 0.9.2.dev661+g1de5c0432aad`, runner `klt 0.9.0`, compatibility `match`), PDK `ihp-sg13cmos5l`.
  All 671 units ran on the Spot fleet, all `pass`. Jobs: probe `klt-sim-6cbc19460088` (2 units, tt/27);
  retime 9 corners N=64 `klt-sim-f996ba1d0994` (54); retime N=127 `klt-sim-267f8882d95f` (27);
  frequency sweep tt/27 `klt-sim-350bd1671750` (14); setup brackets at 9 corners
  `klt-sim-ea17b065013d` (576); slow-corner sweep `klt-sim-899cc848fb07` (14). No local `ngspice`
  was run. `klt sim --batch-set` crashes on `decks[]` requests (upstream 2AMLogic/klayout-tools#5317,
  #5337), so the requests were submitted as four separate `klt sim` invocations.
- **PDK revision**: **not stamped** (the batch reports carry no PDK identity), so the ran-on revision is
  inferred exactly as in RECORD-001 (`f7bca326...`, not the `sim/README.md` pin) and carries the same
  PDK-confound caveat. Not re-established here.
- **Reproduce**: `testbench/gen_sizing_requests.py` (`retime|setup <c:f>... [--corners tt|pvt9|slow2]
  [--n 127] [--freqs MHz,...]`; an `@neg` suffix on `f` clocks `XFRT` from an inverter on `CKIN_VCO`)
  writes decks, `manifest.json` and a request; `testbench/analyze.py corners/raw-*.tar.gz` reproduces
  `corners/analysis-record002.txt` byte for byte (checked). Raw per-unit `stdout.bin` are in
  `corners/raw-*.tar.gz`, batch reports in `corners/report-*.json.gz`.

## Method

Same stimuli and arithmetic as RECORD-001 / RECORD-003 Finding 4: `t_arr` = `tdiv` mod `T_vco`
(`T_vco` = 640.205 ps), `t_setup` bracket from the isolated-flop setup deck (`TSU` list of 16 points),
`F_close = 1/(t_arr + t_setup_hi)`. This record extends it three ways: setup brackets at all 9 PVT
points for 4 flop variants; the retime deck at 9 corners for 6 variants (N=64) and 3 variants (N=127,
`P0..P5` = VDD); and a **structural variant**, `@neg`: `XFRT` clocked from one `inv_hv` on `CKIN_VCO`
(captures on the falling VCO edge), added only in the testbench copy of the netlist. For `@neg` the
one-edge window is taken as `1.5 T_vco` (`F_close = 1.5/(t_arr + t_setup_hi)`); the clock-inverter delay
is not credited. The `@neg` setup bracket is the isolated flop's (same flop, ideal 50% clock), not
re-measured behind the inverter.

## Finding 1: feedback-weakened variants do not move the closing bound (N=64, resolved corners)

`F_close` upper bounds in MHz, deck-arithmetic convention, `corners/analysis-record002.txt`:

| Corner | `t_arr` base (ps) | base | `kf`=.5 (1/1/.5/1) | `kf`=.25 | 2/.5/.5/1 | `@neg` base | `@neg` `kf`=.5 |
|---|---|---|---|---|---|---|---|
| tt/-40 C | 598.8 | 834 | 845 | 852 | 822 | 1301 | 1304 |
| tt/27 C | 484.9 | 922 | 919 | 918 | 918 | 1332 | 1336 |
| tt/27 C, 2.97 V | 113.8 | 1229 | 1411 | 1417 | 1352 | 1969 | 2270 |
| tt/27 C, 3.63 V | 160.7 | 1314 | 1320 | 1324 | 1280 | 2049 | 2048 |
| ff/27 C | 106.2 | 1416 | 1423 | 1426 | 1372 | 2270 | 2271 |
| fs/27 C | 372.8 | 932 | 1027 | 1027 | 1021 | 1317 | 1455 |
| sf/27 C | 413.4 | 987 | 987 | 987 | 982 | 1406 | 1412 |
| ss/27 C, tt/125 C | divider does not run at 1562 MHz (Finding 2) | | | | | | |

The feedback-weakened variants matter only where the base bracket is `(600,700]` (the 2.97 V and fs
points) and only by changing `t_setup_hi` by 100 ps. At tt/27 and tt/-40 they are within 2% of base.
The `t_setup` brackets are `(500,600]` ps at every point except `(600,700]` for base at fs, ss, 2.97 V,
125 C and for `kf` <= .5 at 125 C (`corners/analysis-record002.txt`, `setup` lines). N=127 repeats the
picture (`kf`=.5: 853 MHz at tt/-40, 935 at tt/27; base 841, 937), `t_arr` within 20 ps of N=64.
Best resolved-corner bound for width sizing: **822 to 852 MHz at tt/-40 C** (the worst resolved corner).

## Finding 2: at ss/27 C and tt/125 C the divider core stops dividing between 1400 and 1562 MHz

At 1562 MHz every variant, including base, leaves `DIVOUT` at 52 to 157 mV peak (`dvo_max`) at both
corners, so `tdiv` is unresolved (the RECORD-003 "NA, run budget" reading is not the reason: these runs
completed). Base chain, N=64, frequency sweep (`corners/raw-retime-fsweep-slow2.tar.gz`): `DIVOUT` and
`FB` reach 3.37 to 3.44 V at 600, 800, 1000, 1100, 1200, 1300 and 1400 MHz at both corners. The ceiling
therefore lies in (1400, 1562) MHz at ss/27 C and at tt/125 C. It is set by the divider's own stages,
upstream of `XFRT`, so **no `XFRT` sizing or retiming change can reach 1562 MHz at these two corners**; it
would need the chain stages (`div23_cell`) sized, which this campaign did not do. The sweep is coarse
(100 MHz steps); the ceiling is not bisected.

## Finding 3: the opposite-edge variant raises the deck-arithmetic bound but does not remove the ambiguity

`@neg` gives 1301 to 1304 MHz at the worst resolved corner (tt/-40 C), 1332 at tt/27 C (vs 834 and 922
for base). That is the best achieved bound in this campaign, and it is still **below 1562.0 MHz**.
It also does not give a single deterministic capture edge: the falling edge at `0.5 T` and the one at
`1.5 T` both lie inside the arrival spread. tt/27 C frequency sweep, `@neg`, implied `FB` clk->Q per
hypothesis (`corners/analysis-record002.txt`, `implied_c2q`): capture at k+0.5 at 900, 1250 and 1400 MHz
(clk->Q 498, 569, 534 ps), at k+1.5 at 800, 1000, 1100 and 1562 MHz (486, 504, 512, 536 ps). The extra
period has moved to a different arrival band, not disappeared. The variant therefore does not by itself
close R-3. It costs one `inv_hv` (7 um of channel width) and, at tt/27 C/1562 MHz, +0.121 mA divider
supply current (2.372 mA base, 2.493 mA `@neg`, +5.1%; N=127: 2.270 vs 2.393 mA); the `kf`=.5 flop alone
is -0.056 mA (2.316 mA). Row 11's divider figure is not updated by this record.

## Finding 4: in-situ `tfb - tdiv` is not consistent with the "one period late" reading of RECORD-003

RECORD-003 Finding 4 reads `tfb - tdiv` = 636.4 ps at tt/27 C as a stable k+2 capture. For the base chain
the next VCO edge after the `DIVOUT` edge is `T - t_arr` = 155.3 ps away, and a k+2 capture would put `FB`
at least 795.5 ps after `DIVOUT` (155.3 + 640.2) plus clk->Q. 636.4 ps is smaller than that, so k+2 is
arithmetically excluded; k+1 gives an implied clk->Q of 481 ps. Across the tt/27 C base sweep (800 to
1562 MHz) the implied k+1 clk->Q is 447, 426, 430, 433, 442, 453, 481 ps, rising smoothly as the window
shrinks (875 to 155 ps), while the k+2 hypothesis is negative at every point. All 7 resolved corners at
1562 MHz are likewise k+1-consistent (implied clk->Q 417 to 481 ps at tt/-40 C and tt/27 C). So the
retimed `FB` edge appears to follow the next VCO edge at 1562 MHz with a clk->Q that stretches by about
55 ps, not to land one period late.

This conflicts with the isolated setup deck, which needs `TSU` of 500 to 600 ps, and with an isolated-flop
clk->Q below 160 ps (the deck samples `Q` at `t_cap + T/4`) versus the 417 to 481 ps implied in situ.
**This is not resolved here**: no waveform of the in-situ capture was taken (batch decks save only
`meas` values), the `FB` 50% crossing of the 2nd rise is paired with the 2nd `DIVOUT` rise by index, and
the in-situ clk->Q has not been reproduced in an isolated deck. What this record claims is limited to: the
deck-arithmetic bound (Findings 1, 3) and the in-situ data point to different answers, so ratifiers
should not pick the lower top-of-band from the 825 to 1277 MHz figures alone until a waveform-level
check of the in-situ capture edge (a `.save`d `tran` of `DIVOUT`, `CKIN_VCO`, `FB` at tt/27 C and
tt/-40 C) settles which reading holds. Findings 1 and 3 use the deck convention for comparability with
RECORD-003 and say nothing about Finding 4.

## Best achieved per-corner bounds and limits

Deck-arithmetic convention, N=64, 1562.0 MHz stimulus: see Finding 1 table; best achieved is `@neg`
(1301 to 2271 MHz over the 7 resolved corners, worst case 1301 MHz at tt/-40 C). Limits: (a) the arrival
`t_arr` (up to 617 ps) against the isolated flop's 500 to 700 ps setup bracket, which no width sizing
moved; (b) at ss/27 C and tt/125 C the divider core's own ceiling in (1400, 1562) MHz (Finding 2); (c)
for `@neg`, the two-edge ambiguity (Finding 3). The deck-arithmetic bound **>= 1562.0 MHz at all 9
corners is not reached by any variant**.

## Not done (stated, not hidden)

- No variant adopted: no netlist regenerated, no 20-point functional matrix re-run, `design/` unchanged.
  The `@neg` testbench netlists live in `testbench/decks/` (not committed; regenerated by the script).
- Chain-stage (`div23_cell`) sizing for the Finding 2 ceiling; a finer `TSU` grid; a bisection of the
  slow-corner ceiling; `@neg` setup measured behind the inverter; the waveform check in Finding 4.
- Offline ngspice only; spec not changed. Live verification is not applicable beyond ngspice.

## Proposed decision

`spec/decision-records/DR-012-row3-retiming-sizing-limit.md` (still proposed) is updated with this
evidence: R-3 stays open, with the Finding 4 check as the gating follow-up before any lower top-of-band
is ratified.
