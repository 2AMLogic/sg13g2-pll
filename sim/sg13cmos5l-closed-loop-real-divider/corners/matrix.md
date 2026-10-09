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
