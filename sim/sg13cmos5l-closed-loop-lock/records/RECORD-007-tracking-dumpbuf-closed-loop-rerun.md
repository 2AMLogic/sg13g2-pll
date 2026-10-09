# RECORD-007: RECORD-005/006's proposal deck re-run with the tracking dump buffer (DR-010): row 7's static phase error falls from 8.20% to 0.78% at nominal

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #165 (Part of #16). Design change:
  `spec/decision-records/DR-010-cp-dumpbuf-tracking-ota-pair.md`. DC,
  loading and stability evidence for the same snapshot:
  `../../sg13cmos5l-cp-icp-trim/records/RECORD-005-issue165-tracking-dumpbuf-dc.md`.
- **Append-only.** This record does not edit `RECORD-001` through
  `RECORD-006`, any earlier snapshot, CSV or script. New files:
  `../netlist-snapshots/cp_otabuf.spice`,
  `../testbench/run_closed_loop_otabuf.sh`, and
  `../corners/{lock_trace_cpdiag_otabuf*.csv, cpdiag_cycles_otabuf*.csv,
  cpdiag_summary_otabuf*.json}`.
- **What this is, and what it is not.** This is RECORD-005/006's **proposal
  deck** with one change: `cp` is the new committed snapshot. Everything that
  makes it a proposal deck is unchanged:
  - a behavioural XSPICE divide-by-64 instead of the committed
    `divider_chain`;
  - `R1` resized 120u to 2400u;
  - ideal capacitors for every MOM cap;
  - `XCDECAP` stripped;
  - ideal `IREF` sources into `cp`'s bias pins.

  These numbers are **not committed-PLL performance and not sign-off
  evidence**. The `cp` itself is the committed design.
- **Tooling**: `ngspice-46` (`~/.local/bin/ngspice`; RECORD-006 used
  ngspice-47 and RECORD-005 used ngspice-46), `klt 0.7.0+gb82427b30c96`
  (recorded, not used to simulate), `ihp-sg13cmos5l` PDK revision `607e18d4bd9214a52575c194b4181ef449f9252f` (clean, equal to the
  `sim/README.md` pin), Python 3.12.3 (stdlib only), x86-64 Linux shared
  worker. `set num_threads=1`.

## The change under test

`cp_dumpbuf` was an NMOS source follower that held `VDUMP` 0.937 V below
`VOUT`. It is now a complementary pair of unity-gain 5T OTAs (DR-010).
Snapshot `../netlist-snapshots/cp_otabuf.spice` (sha256
`c8a55d8d2234c4686f85054830d92eb4b41a256bfaeb44e039b1089033294452`) is frozen
from `design/sg13cmos5l/netlist/cp.spice` at commit `093ab2c`
(`feature/issue-165`; the squash-merge sha will differ, the content will
not). The other four blocks are the same frozen snapshots RECORD-005/006
used, built by RECORD-006's own **unmodified** `cpdiag_build.py`
(`control_probe`: no edit, empty variant diff, checked by the runner) and
measured with RECORD-006's own probe deck `tb_pll_cpdiag.sp.tmpl` and
post-processor `cpdiag_post.py`. The numbers below are therefore directly
comparable with RECORD-006's `control_probe` and `ideal_dump` rows. The
summary JSON's `inputs_sha256.cp_cascbias.spice` field hashes the
`cp_otabuf.spice` content (the scratch copy is named for
`cpdiag_build.py`). The runner adds `cp_snapshot` and `pvt` fields that say
so.

## Corners: what ran and what did not

**One PVT point: `mos_tt`/`res_typ`/27 C/3.3 V**, the same point as
RECORD-001 to RECORD-006. It ran twice to check determinism. **No other
corner was run.**

- Host policy sends corner grids to the Spot batch fleet as `klt sim`
  requests and forbids a local grid.
- In this issue, the batch route was exercised directly with this snapshot's
  DC grid (`../../sg13cmos5l-cp-icp-trim/records/RECORD-005`). The first
  submission returned `batch_no_capacity`. The second launched and exited 87
  because the fleet runner runs `klt 0.5.0` against the 0.7.0 client
  (klayout-tools#2851, #2901). `ihp-sg13cmos5l` has no fleet image
  (klayout-tools#2727).
- A closed-loop grid would hit the same runner. It was not expressed as a
  request and spent on a known failure, and it was not run locally.

The full-PVT closed-loop re-run is **owed** and must go through `klt sim`
once the fleet can run this PDK. Corners matter here: the buffer's offset,
its loading and its tails all move with corner and temperature (DC values in
the cp-icp-trim RECORD-005 are nominal only).

## Result

Final 20 of 49 reference cycles (`t` > 1.5 us); same metric code and window
as RECORD-005/006.

| Quantity | RECORD-005 (source follower) | RECORD-006 (b) `ideal_dump` (ideal VCVS) | **This record (DR-010 buffer)** | repeat `_rep` |
|---|---|---|---|---|
| static phase error, final-20 mean [min, max] | 8.203% [8.200, 8.221] | 1.048% [1.010, 1.071] | **0.779% [0.731, 0.800]** | 0.779% [0.731, 0.800] |
| df/f_ref, final-20 mean | -0.00020% | -0.00256% | **+0.00091%** | +0.00091% |
| longest dual-lock run (\|df\| < 1% AND \|phase\| < 5%) | 4 | 45 | **42** (from `t` = 400 ns, to the end of the run) | 42 |
| longest freq-lock run | 42 | 45 | 45 | 45 |
| lock time (first cycle of the first >= 20-cycle dual-lock run) | None | 250 ns | **400 ns** | 400 ns |
| `vc_avg`, 2.0-2.5 us | 2.386934 V | 2.387105 V | 2.386820 V | 2.386820 V |
| `VDUMP` mean, last 20% of the run | 1.4953 V (RECORD-006 control) | 2.3870 V | **2.3726 V** (-14.3 mV vs `vc_avg`) | |
| `i_cp` (`vdd_cp`), 2.0-2.5 us | -39.26 uA | -33.13 uA | **-64.89 uA** | -64.89 uA |
| reference / FB rising edges | 50 / 50 | 50 / 50 | 50 / 50 | |
| ngspice exit status, all samples finite | 0, yes | 0, yes | 0, yes | |

Per-cycle charge, final-20 medians, from `../corners/cpdiag_cycles_otabuf.csv`
(positive = into the filter; definitions as RECORD-006):

| | t_lead (ns) | t_ovl (ns) | q_lead (fC) | q_ovl (fC) | q_rest (fC) | q_cycle (fC) | i_off (nA) |
|---|---|---|---|---|---|---|---|
| RECORD-006 `control_probe` (source follower) | 4.116 | 0.805 | +17.52 | -23.18 | +5.67 | +0.002 | -26.444 |
| RECORD-006 (b) `ideal_dump` | 0.535 | 0.806 | -3.67 | -2.59 | +6.24 | -0.010 | -0.115 |
| **This record** | **0.378** | 0.807 | -4.15 | **-2.97** | +6.96 | -0.138 | +0.030 |

**Row 7's 5% static-phase-error threshold is met at this point on this
deck**, with a 42-cycle continuous dual lock, which is more than the 20
cycles row 7's lock-time definition needs. The 5% criterion is unchanged.

## Reading

- **The mechanism RECORD-006 named is gone.** The both-high segment's charge
  falls from -23.2 fC to -3.0 fC, close to the ideal tracker's -2.6 fC. The
  UP lead the loop needs to replace it falls from 4.1 ns to 0.38 ns. The
  real buffer sits 14.3 mV below `VOUT` in the loop, in line with its DC
  offset of -14.9 mV at 2.40 V (cp-icp-trim RECORD-005). RECORD-006's
  charge-per-volt scaling makes that about 0.5 fC per cycle. RECORD-006's
  post-pulse settling tail (`i_off` -26 nA, present only with the source
  follower) is also gone.
- **0.78% is slightly better than the ideal VCVS's 1.05%.** That is the same
  direction as RECORD-006's own observation that a real buffer's finite
  output impedance lets `VDUMP` absorb part of each turn-on transient. This
  record does not separately prove which term makes up the 0.27 pp
  difference.
- **What limits the residual** is RECORD-006's second-order term at equal
  levels: the real steering switches' own injection and feedthrough, about
  8 fC open-loop (RECORD-006 (b) vs (a)+(b)). A dump buffer cannot remove
  it. This is the next term, and switch-charge cancellation is the lever.
  RECORD-006's other second-order term, about 0.8 pp from the source
  follower's own dynamics, does not appear: the DR-010 buffer lands below the
  ideal tracker.
- **Lock time is 400 ns against the ideal tracker's 250 ns.** The longest
  dual-lock run starts at cycle 8 (`t` = 400 ns). `df/f` is inside the 1%
  bound from cycle 5 (`t` = 250 ns) to the end. The phase acquisition
  transient undershoots to -5.22% and -5.09% at 300 and 350 ns, just outside
  the 5% band. The 3-cycle difference is that undershoot, not a
  frequency-lock difference.

## Row-by-row disposition (does not edit RECORD-001 to RECORD-006)

- **Row 7 (lock time / static phase error)**: **passes at `mos_tt`/27 C/
  3.3 V on the proposal deck** (0.779%, 42-cycle dual lock, lock time
  400 ns), against 8.20% and no lock before this change. **Not established**
  across PVT (not run, see above), on the committed loop (`divider_chain`,
  the committed `R1`, real MOM caps, a real `Iref`), or post-layout. Row 7
  still proposes no lock-time number (spec R-2), and this record proposes
  none.
- **Row 10 (reference spur)**: no number. The loop now phase-locks at this
  point, which is a precondition RECORD-001 found missing, but this record
  does not measure a spur.
- **Row 11 (power)**: the `cp` domain draws 64.89 uA in this deck, up from
  39.26 uA. The +25.6 uA is the buffer's two tails, which matches the DC
  measurement in cp-icp-trim RECORD-005 (+25.59 uA). This supersedes
  RECORD-005's `cp` figure for the DR-010 design only.

## What this does not bound

- **Corners**: nominal only (see above).
- **The PLL loop's phase margin with `cp`'s output capacitance**: the
  buffer adds at most 10.5 fF to the 100 fF `C2` node (nominal). That is in
  this deck, but not in `sg13cmos5l-loop-bandwidth-pm`'s model (#196).
- **Random mismatch**: no Monte Carlo of the buffer's input offset.
- **Low `Icp`*`T_ref`**: a fixed charge residue costs more phase at low trim
  codes and low `f_ref`. Only 10 uA / 20 MHz is exercised here.
- **Layout**: `pll_cp`'s layout predates this change (#195).

## Determinism

The run was repeated (`RUN_TAG=_rep`, same inputs, same `ngspice-46`, one process). `lock_trace_cpdiag_otabuf_rep.csv` and `cpdiag_cycles_otabuf_rep.csv` are byte-identical to the first run's files (`cmp`), and every `lock_metrics` and `meas` field of the two summary JSONs is equal. The `_rep` files are committed next to the originals.

## Reproduce

```bash
export PDK_ROOT=<parent of ihp-sg13cmos5l> PDK=ihp-sg13cmos5l   # ngspice >= 43 (OSDI v0.4) on PATH
cd sim/sg13cmos5l-closed-loop-lock/testbench
./run_closed_loop_otabuf.sh                 # about 8 min here, one ngspice process
RUN_TAG=_rep ./run_closed_loop_otabuf.sh    # repeat
# Other corners: one per invocation via MOS_CORNER/RES_CORNER/TEMP/VDD, but a
# grid of them belongs on the batch fleet as a `klt sim` request, never a
# local loop.
```
