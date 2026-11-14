# Corner / operating-point definition -- sg13cmos5l-closed-loop-real-divider (issue #159)

**NOMINAL ONLY. This is not a PVT campaign and supports no full-PVT claim.**
One point, two arms (single local `ngspice -b` per arm, run sequentially):

| Axis | Value |
|---|---|
| MOS corner | `mos_tt` |
| Resistor corner | `res_typ` |
| Temperature | 27 C |
| Supply (all four domains) | 3.3 V |
| f_ref | 20 MHz (50 ns), 50% duty |
| Divider word | `P5..P0 = 000000` (N = 64) -- real arm: pins tied to 0 V; control arm: behavioural /2^6 |
| VCO band | `B0 = B1 = 3.3 V` |
| Initial conditions | `vctrl = 2.46 V`, `xvco.ring1 = 0.5 V`; real arm only: 13 divider flop latch nodes = 0 V |
| Solver | ngspice-46 defaults, `.tran 100p 2500n 0 100p`, `num_threads=2`, `.save` of 4 waves + 4 supply currents |
| Duration / averaging window | 2500 ns / 2000-2500 ns |
| Lock criterion | campaign's existing dual-lock (`lock_analysis` from `../sg13cmos5l-closed-loop-lock/testbench/extract.py`, imported unchanged): `|df/f_ref| < 1%` and `|phase| < 5% T_ref` for >= 20 consecutive reference cycles |

Why a single point: the issue scopes this as a nominal integration baseline;
a PVT grid, if later wanted, must go to the batch fleet as a `klt sim` request
and is out of scope here.

Supporting divider-alone diagnostic (`testbench/run_div_speed.sh`): same rails,
word, latch `.ic` and solver options; ideal pulse clock at 200 MHz, 640 MHz and
1.28 GHz, one nominal run each (not a corner grid).
Persisted extraction per run: [200 MHz](edges_divspeed_200MHz.txt),
[640 MHz](edges_divspeed_640MHz.txt), [1.28 GHz](edges_divspeed_1280MHz.txt)
(each with a `.json` of the same name); ratios 64 / 64 / 96 clk edges per FB period.
These were re-run once each under issue #168 (ngspice-47, nominal; see RECORD-001
"Re-run conditions"); original logs are unchanged.

Second operating point (issue #401, RECORD-002): the same nominal corner and
N = 64, but band code `00` (`B0 = B1 = 0 V`), `f_ref` = 9.375 MHz
(`T_ref` = 106.67 ns), target `f_vco` = 600 MHz, `.ic vctrl = 1.23 V`
(interpolated from `sg13cmos5l-vco-kvco-table` RECORD-001's band `00` row),
`cp` snapshot `cp-dr010.spice` (the committed DR-010 block; RECORD-001's
`cp.spice` stays untouched as its frozen pre-DR-010 export), and
`.tran 100p 10u 0 100p` with an 8-10 us averaging window (94 `T_ref`; the
dual-lock criterion needs 20 consecutive cycles after acquisition, and
RECORD-001's 2500 ns default spans only ~23 `T_ref` at this `f_ref`).
ngspice-47, `num_threads=2`; every artifact carries `TAG_SUFFIX=_o2`
(`corners/*_o2`, selected via `CP_SNAP=cp-dr010.spice` and the run.sh
`FREF/B0V/B1V/VC0/TSTOP/TAVG0` overrides; `run.sh` defaults still reproduce
RECORD-001's point). Chosen so the loop's required VCO frequency (600 MHz)
sits 40 MHz below the 640 MHz where RECORD-001's ideal-clock bracket proves
exact /64, and below target-spec row 3's measured 866 MHz one-edge retiming
closing bound at `mos_tt`/27 C. The row 6/6a loop-bandwidth / phase-margin
criteria are NOT re-verified at this (band, `f_ref`) tuple; the deck's ideal
10 uA `IREF` is carried over unchanged.
