# RECORD-001: supply-range sweep (3.0 / 3.3 / 3.6 V) for `vco`, `lock_detector`, `divider_chain`

- **Slug**: `sg13cmos5l-supply-range`
- **Issue**: #187 (T1 item 5; spec row 18, risk R-9). Append-only. No spec
  bound is edited or relaxed by this record.
- **Reproduce**: `sim/sg13cmos5l-supply-range/testbench/run_batch.sh`
  (writes `../corners/{vco,lock_detector,divider}.csv`). Matrix and what is not
  covered: `../corners/matrix.md`.
- **Tool**: ngspice-46 via `klt sim --backend batch --wait-for-capacity 600`
  (client `klt 0.9.2.dev661+g1de5c0432aad`, runner `klt 0.9.0`,
  `runner_compatibility: match`), x86-64 Linux Spot workers. No ngspice was
  run on the dispatching host.
- **PDK**: `ihp-sg13g2` tree: PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e (the `sim/README.md` pin). The
  `ihp-sg13cmos5l` tree on the fleet image is an unstamped `/opt/pdk`; its
  revision is not independently established by this run, and it is not the
  legacy split-repository commit the `PDK-PIN` line names (see RECORD-006 of
  `sg13cmos5l-divider-nrange-retiming` for the same disclosure).

## Jobs

| Block | Job | Instance | Units |
|---|---|---|---|
| probe (`typ`, 3.0 V, `vco`, before the grid) | `klt-sim-31c02a3e54ab` | m7i.4xlarge | 20/20 pass |
| `vco` | `klt-sim-16b5b56e7d78` | c7i.8xlarge | 180/180 pass |
| `lock_detector` | `klt-sim-c480c2752c9a` | m7i.4xlarge | 18/18 pass |
| `divider_chain` | `klt-sim-cb6886b3501d` | c7i.8xlarge | 27/27 pass |

The first `divider_chain` submit (`klt-sim-c9586978fa65`) lost its client to a
local timeout and was resubmitted unchanged; only the second job's output is
used.

## Control: the 3.3 V rows do not reproduce `sg13cmos5l-vco-kvco-table/RECORD-001`

Same decks, same bundles, 3.3 V: the `vco` frequencies differ from that
record's `results.csv` by up to **3.08 %** (floor 431.6 MHz here vs 445.3 MHz;
ceiling 1575.6 vs 1562.0 MHz). The fleet's PDK tree is not the tree that record
ran on (see the PDK note above; the lock-detector `BATCH.md` documents a moved
`cornerRES.lib`). This was not diagnosed here. Consequence: **supply effects
below are stated against this run's own 3.3 V rows, not against the row-1 band
numbers**, and absolute comparison to row 1's 445.3 to 1562.0 MHz is confounded
by the tree change.

## Results

### `vco` (row 1 band, row 4/5 inputs; 60 points per VDD)

| VDD | Min freq | Max freq | Per-bundle range (MHz) |
|---|---|---|---|
| 3.0 V | 430.4 MHz (`slow`, any code, `VCTRL` 0.3 V) | 1553.5 MHz (`fast`, code 11, 2.7 V) | typ 497.1 to 1329.0; slow 430.4 to 1060.5; fast 571.8 to 1553.5 |
| 3.3 V | 431.6 MHz (`slow`) | 1575.6 MHz (`fast`, 11, 2.7 V) | typ 491.5 to 1357.6; slow 431.6 to 1102.9; fast 559.9 to 1575.6 |
| 3.6 V | 429.1 MHz (`slow`) | 1563.3 MHz (`fast`, 11, 2.7 V) | typ 484.0 to 1355.9; slow 429.1 to 1117.3; fast 547.7 to 1563.3 |

180/180 points oscillate (0 NA). Against the same-run 3.3 V rows, a +/-10 %
supply moves individual points by -4.86 % to +4.85 %: at 3.0 V from -3.84 %
(`slow`, 11, 2.7 V) to +4.85 % (`fast`, 00, 2.1 V); at 3.6 V from -4.86 %
(`fast`, 00, 2.1 V) to +1.31 % (`slow`, 11, 2.7 V). The band ends move far less
than interior points (floor within 0.6 % across VDD; ceiling highest at 3.3 V,
not at an endpoint). **Row 18 binding corner for `vco`**: floor `slow`/3.6 V
(429.1 MHz); ceiling `fast`/3.3 V in this run (1575.6 MHz), with 3.6 V at
1563.3 MHz. Whether the band stays inside row 1's 445.3 to 1562.0 MHz cannot be
read from this run because of the control finding above: the floor is below
445.3 MHz at all three VDD including 3.3 V, and the ceiling is above 1562.0 MHz
at 3.3 V and 3.6 V. No bound is moved by this record.

### `lock_detector` (row 16 window floor >= 2.5 ns)

Comparator window `twin_r`, 9/9 points valid:

| Bundle | 3.0 V | 3.3 V | 3.6 V |
|---|---|---|---|
| typ | 7.346 ns | 6.668 ns | 6.145 ns |
| slow | 10.249 ns | 9.423 ns | 8.790 ns |
| fast | 5.532 ns | 5.007 ns | 4.602 ns |

All nine are above 2.5 ns; the window shrinks monotonically with VDD, so the
binding corner for the floor is **`fast`/3.6 V, 4.602 ns (1.84x the floor)**.
Bare `schmitt_hv` thresholds (`vth_up`/`vth_dn`, 9/9 valid) scale with VDD:
hysteresis in volts (`vth_up` - `vth_dn`) is 0.866 to 1.008 V across the nine points, 0.277 to 0.292 of VDD (`../corners/lock_detector.csv`). **Time-domain hysteresis and chatter are not measured
here** (see `../corners/matrix.md`); this record makes no statement on them at
3.0/3.6 V.

### `divider_chain` (row 3)

* **Functional**: 18/18 `func` decks divide at the commanded ratio: N=64 and
  N=127 at 100 MHz in all nine bundle x VDD points (measured ratio 64.000 to
  64.001 and 127.000).
* **Retiming at 1562.0 MHz**: `typ` and `fast` produce a divided output at all
  three VDD; **`slow` (`mos_ss`/125 C) produces none at any VDD, including 3.3 V**
  (`dvo_max` 56 to 69 mV). That is row 3's already-recorded unmet retiming
  closure (R-3), not a supply effect. `fast` shows a smooth supply trend
  (`tdiv` 85.6 / 64.9 / 44.3 ns at 3.0 / 3.3 / 3.6 V).
* **Anomaly, not diagnosed**: `typ`/3.0 V `retime` has `tdiv` = 128.8 ns against
  86.3 ns at 3.3 V and 86.0 ns at 3.6 V, i.e. its second divided rising edge
  arrives one divide period (about 41 ns) later. The other eight points do not
  show this. The run cannot say whether it is a startup-state difference or a
  real marginal-closure signal at 3.0 V; a follow-up probe is owed before
  anyone reads it as either.

## Summary against row 18

| Block | Supply-range outcome | Binding corner |
|---|---|---|
| `vco` | oscillates and stays in a ~429 to 1576 MHz envelope at 3.0/3.3/3.6 V; interior points move up to -4.9/+4.9 % | floor `slow`/3.6 V; ceiling `fast`/3.3 V |
| `lock_detector` | window >= 2.5 ns at 9/9; hysteresis/chatter NOT measured | `fast`/3.6 V (4.602 ns) |
| `divider_chain` | N=64/127 functional 18/18; retiming unmet at `slow` for all VDD (pre-existing); `typ`/3.0 V retime anomaly open | `slow` (retiming); `typ`/3.0 V (anomaly) |

Row 18 stays Proposed. This record widens its evidence from `cp` to three more
blocks and names open items; it does not ratify the row.
