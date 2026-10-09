# RECORD-001: repaired transistor-level `divider_chain` in the closed loop — nominal corner — does NOT acquire

- **Slug**: `sg13cmos5l-closed-loop-real-divider`
- **Issue**: #159 (Part of #16; advances #6). Append-only; no historical record
  (`sg13cmos5l-closed-loop-lock` RECORD-001…005, `sg13cmos5l-divider-nrange-retiming`
  RECORD-001…003) and no production file was edited.
- **Scope**: ONE nominal point (`mos_tt` / `res_typ` / 27 C / 3.3 V), pre-layout.
  Not a PVT campaign, not sign-off, does not ratify or relax any spec bound.
  A PVT grid, if wanted later, must go through a `klt sim` batch request.
- **Tooling**: ngspice-46, `~/share/pdk/ihp-sg13cmos5l`, x86-64 Linux, `num_threads=2`.
  Each run below is a single local `ngspice -b`, run sequentially.

## Frozen DUT inputs (`netlist-snapshots/`, bodies byte-identical to `design/sg13cmos5l/netlist/` at `3da79b6`; only a provenance header added)

| Snapshot | sha256 (of the snapshot file) |
|---|---|
| `pfd.spice` | `56309ee99b96300a0de0d2ff2efaee82dd5043125232315b3641e081c9697c4c` |
| `cp.spice` | `111d033757a3530d80de782d891c022f9d91a693a98015b715724cb6b08f93e8` |
| `loop_filter.spice` | `ddb7d526ad919c998085ac411c3feaf134c566f2468f4f942a248befd843549b` |
| `vco.spice` | `3473ac1274f5c3a78c86ac319d5daca7ffb339071f44576a8403fffbad7fe507` |
| `divider_chain.spice` | `f9e60ee31cb44183a4d5bd58dc68b307d16e716f1a0df90af8d9593ceb2e20af` |

`cp` is the committed cascode-bias mitigated block (DR-006); `divider_chain` is the
#112/PR #121 repaired chain. Deck: `testbench/tb_pll_realdiv.sp.tmpl`, one template
rendered by `testbench/run.sh` into two arms; everything outside the arm block is
byte-identical between arms (rails, REF, bias currents, loop filter, VCO word
`B0=B1=3.3 V`, `.ic vctrl=2.46 V`, `.ic xvco.ring1=0.5 V`, solver options,
`.tran 100p 2500n 0 100p`, same `.save`). Averaging window 2000–2500 ns.
`f_ref` = 20 MHz, divider word `P5..P0 = 000000` (N = 64).

## Remaining substitutions (all disclosed; none changes a production file)

- S1 `loop_filter`: the two `cap_cmomi` instances replaced by ideal caps at the campaign's
  measured values (C1 = 1.691196 pF, C2 = 100.1529 fF), same as RECORD-003/005.
- S2 `vco`: `XCDECAP` stripped (campaign precedent).
- S3 `cp`: `IBP/ICP/IBN/ICN` driven by ideal 10 uA current sources.
- S4 `b0`/`b1` ideal rails; REF an ideal pulse source; four ideal supplies (`vdd_div` exists in both arms, unloaded in control).
- S5 `lock_detector` NOT instantiated (interface/applicability not verified here; no detector claim).
- S6 control arm only: ideal behavioural XSPICE /64 (6 `d_dff` toggle stages) in place of the divider.
- S7 real arm only: `.ic` = 0 V on the 13 divider flop latch nodes (block has no reset; symmetry break).

## Results (`corners/`; raw traces `vctrl_*.csv`, `trace_*.csv`; logs `log_*.txt`; summaries `summary_*.json`)

Lock criterion: the campaign's existing dual-lock (`|df/f_ref| < 1 %` AND `|phase| < 5 % T_ref`
for >= 20 consecutive reference cycles), `lock_analysis` imported unchanged from
`../sg13cmos5l-closed-loop-lock/testbench/extract.py`.

| Quantity | Control (behavioural /64) | Real `divider_chain` |
|---|---|---|
| Dual lock / `lock_time` | **no** (None); longest dual run 1 cycle | **no** (None); longest dual run 0 |
| Frequency-lock (`|df|<1 %`) longest run | 46 cycles (from 200 ns) | 0 cycles |
| `vctrl` start -> end (min / max) | 2.46 -> 2.388 V (2.228 / 2.489) | 2.46 -> 3.237 V (2.334 / 3.312) |
| `vc_avg` 2.0–2.5 us | 2.3872 V | 3.2622 V (rail-limited, 3.03–3.31 V) |
| `f_vco` (2.0–2.5 us) | 1.2800 GHz | 1.4050 GHz |
| `f_fb` (2.0–2.5 us) | 20.0003 MHz | 10.978 MHz |
| clk edges per FB period | 64 (49/49 periods) | 128 (5/5 final window); whole run 128 x26, 107 x1 |
| Measured ratio (edges) | 64.0 | 128.0 (127.2 whole run) |
| Final-20-cycle `df/f_ref` mean | -0.0076 % | -45.1 % |
| Final-20-cycle phase error | +8.2 .. 8.4 % T_ref (mean 8.31 %) | wraps -80 .. +91 % (no static value) |
| `i_pfd` / `i_cp` / `i_vco` (avg) | -52.5 / -38.5 / -2012 uA | -36.2 / -38.0 / -2410 uA |
| `i_div` (avg) | 0 (unloaded) | -2141 uA |

Control reproduces the prior campaign: frequency lock at exactly N = 64 with a stable
static phase error 8.31 % (RECORD-005 quoted 8.203 %; same >5 % dual-lock failure), so
the control deck is the unchanged proposal loop and fails the dual-lock criterion on its
own (that is a prior, known finding, not a regression of this bench).

**Real-divider arm: no acquisition.** In the closed loop the committed divider produces
one FB rising edge per **128** VCO edges, not 64 (first FB period 107, then 128 from there
on). FB therefore runs at ~11 MHz against a 20 MHz reference, the PFD sees a persistent
frequency deficit, `vctrl` is pumped up against the rail (3.24–3.31 V) and the VCO
saturates at ~1.40 GHz (the loop would need 2.56 GHz to equalise). The intended divide
ratio does **not** hold in-loop at this operating point.

## Supporting diagnostic (divider alone, ideal clock)

`testbench/run_div_speed.sh` (+ `tb_div_speed.sp.tmpl`): the same frozen `divider_chain`,
same rails/word/latch `.ic`, ideal 50 %-duty pulse clock, one nominal run per frequency:

| f_clk | clk edges per FB period | `i_div` avg |
|---|---|---|
| 200 MHz | 64, 64, 64, 64 | 459 uA |
| 640 MHz | 64, 64, 64, 64 | 1462 uA |
| 1.28 GHz | **96**, 96, 96, 96, 96 | 2274 uA |

So the repaired chain divides exactly by 64 at 200 and 640 MHz but already miscounts at the
1.28 GHz the control loop locks at (an ideal clock gives 96; the in-loop VCO waveform gives
128 — a different wrong ratio, same failure class). Consistent with, and an in-loop
consequence of, the top-of-band retiming/speed limit `sg13cmos5l-divider-nrange-retiming`
RECORD-001/003 reported (that bench's N=64 verification used the 100 MHz baseline). The
divider's exact-N result at 100 MHz does not carry to the ~1.28 GHz the N=64 loop needs.
Root cause (which stage drops/doubles edges) is not isolated here; this is a 3-point
bracket (640 MHz ok, 1.28 GHz not), not a characterisation of the speed limit.

## What this does and does not establish

- Establishes (nominal, pre-layout, ONE run per arm, simulator-deterministic): with the
  committed `pfd`/`cp`/`vco`/repaired `divider_chain`, the N=64 loop does not lock; the
  divider misdivides at the VCO's operating frequency.
- Does not establish: any PVT behaviour; whether a different word/f_ref (lower VCO frequency)
  would lock (untested); `lock_detector` behaviour; post-layout behaviour; any spec
  ratification or relaxation. Supply currents in the real arm are out-of-lock values and are
  not a power result.
- Row 7 (lock time) remains failing; the previous "no re-run exists" caveat is replaced by
  this measured no-lock result.

## Reproduce

```
cd testbench
PDK_ROOT=<root> PDK=ihp-sg13cmos5l ./run.sh control   # ~minutes
PDK_ROOT=<root> PDK=ihp-sg13cmos5l ./run.sh real      # 912 s wall, 2 threads, this host
PDK_ROOT=<root> PDK=ihp-sg13cmos5l TSTOP_OVERRIDE=1300n ./run_div_speed.sh 2e8
```
(`run_div_speed.sh 6.4e8` with `TSTOP_OVERRIDE=500n`; `run_div_speed.sh 1.28e9` with the 400n default.)
