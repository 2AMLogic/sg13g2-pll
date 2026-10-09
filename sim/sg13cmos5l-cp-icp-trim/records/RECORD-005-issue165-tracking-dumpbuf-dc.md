# RECORD-005: `cp` with the tracking dump buffer (DR-010): |VDUMP - VOUT|, buffer loading and stability, and the Icp trim table re-run

- **Slug**: `sg13cmos5l-cp-icp-trim`
- **Issue**: #165 (Part of #16). Design change:
  `spec/decision-records/DR-010-cp-dumpbuf-tracking-ota-pair.md`.
- **Append-only.** This record edits no earlier record, no earlier snapshot,
  no earlier CSV and no earlier script. Every artifact it cites is new.
- **DUT**: `../netlist-snapshots/cp_otabuf.spice` (sha256
  `c8a55d8d2234c4686f85054830d92eb4b41a256bfaeb44e039b1089033294452`), frozen
  from `design/sg13cmos5l/netlist/cp.spice` at commit `093ab2c` on
  `feature/issue-165` (the squash-merge sha on main will differ; the content
  will not). `cp_dumpbuf` is now a complementary pair of unity-gain 5T OTAs
  (DR-010). `cp_leg_p`, `cp_leg_n`, the inverters and the DR-006 bias replica
  are byte-identical to `./cp.spice`.
- **Control DUT**: `../netlist-snapshots/cp.spice` (the frozen DR-006 `cp`
  with the source-follower buffer, untouched), run through the *same* deck.
  `cp`'s own pinout did not change, so the same deck drives both.
- **Tooling**: `klt 0.7.0+gb82427b30c96` (`klt sim`), `ngspice-46`
  (`~/.local/bin/ngspice`), `ihp-sg13cmos5l` PDK revision `607e18d4bd9214a52575c194b4181ef449f9252f` (clean checkout, equal to the
  `sim/README.md` pin), x86-64 Linux shared worker.

## What was run, and what was not

| Request (`../testbench/`) | Corners | Backend | Ran? | Report (`../reports/`) |
|---|---|---|---|---|
| `otabuf_nominal.request.json` (DC tracking + trim table) | `mos_tt` / 27 C / 3.3 V | local, one corner | **yes**, pass | `sim.otabuf_nominal.json` |
| `otabuf_control_nominal.request.json` (same deck, pre-#165 `cp`) | `mos_tt` / 27 C / 3.3 V | local, one corner | **yes**, fails the offset limit as intended | `sim.otabuf_control_nominal.json` |
| `otabuf_cin_nominal.request.json` (buffer loading on VOUT) | `mos_tt` / 27 C / 3.3 V | local, one corner | **yes**, pass | `sim.otabuf_cin_nominal.json` |
| `otabuf_lg_nominal.request.json` (buffer loop gain / PM) | `mos_tt` / 27 C / 3.3 V | local, one corner | **yes**, pass | `sim.otabuf_lg_nominal.json` |
| `otabuf_pvt.request.json` (DC, 5 MOS corners x -40/27/125 C) | 15 | batch fleet | **submitted twice, not run** | `batch-error.otabuf_pvt.first-submit.json`, `sim.otabuf_pvt.batch.json` |
| `otabuf_supply.request.json` (DC, `mos_tt`/27 C x VDD 3.0/3.6 V) | 2 | batch fleet | **not run** (submission withdrawn, see below) | none |
| `otabuf_cin_pvt.request.json`, `otabuf_lg_pvt.request.json` | 15 each | batch fleet | **not run** (same) | none |

**Why the grids did not run.** Host policy sends every corner grid to the
Spot batch fleet as a `klt sim` request and forbids a local grid. The DC PVT
request was submitted twice:

1. The first submission returned `batch_no_capacity`: "no capacity in any of
   the 30 pools after 3 attempt(s)". This was for an earlier sizing of the
   same request; the error is in the envelope.
2. The resubmission used `batch.capacity_wait_s: 900` and the final
   snapshot. It launched (`m7i.4xlarge` spot, job `klt-sim-a4729666c143`)
   and exited 87 after 27 s. The fleet runner runs `klt 0.5.0` against the
   `0.7.0` client (`runner_compatibility: mismatch`), so all 15 corners came
   back `batch_job_failed` and the request was not run
   (klayout-tools#2851, #2901).

`models.pdk` is omitted on purpose: the batch backend refuses
`ihp-sg13cmos5l` (klayout-tools#2727), so the request ships the model
library through `options.stage_model_inputs`, as in
`../../sg13cmos5l-cp-icp-trim-mc/`. A 0.5.0 runner also drops
`options.osdi_preload` (#2901), so an older client is not a route for this
PDK either (data point posted on #2851). The other three batch requests
would hit the same runner. They were withdrawn before launch rather than
spend three more instances on a known failure. **No corner other than
`mos_tt`/27 C/3.3 V was simulated for this record, and no local grid was
run.** Every full-PVT statement below is therefore owed. The requests are
committed and ready for re-submission once the fleet runner and PDK image
exist.

## Deck

`../testbench/gen_otabuf_requests.py` (stdlib only) writes the circuit
bodies and the requests. Three bodies:

- **`tb_cp_otabuf_dc.sp`**: 24 `cp` instances share one swept output
  voltage `VS`, 0.30 to 2.90 V in 50 mV steps (53 points). That is 6 trim
  codes (2.5/5/10/20/40/80 uA) x 4 switch states: `off` (UP = DN = 0, the
  idle state every turn-on starts from), `up`, `dn`, `both`. Each instance has
  its own four ideal reference currents and its own 0 V ammeter, with positive
  meaning the cp sources current into the output (the same convention as
  `tb_cp_dc.sp.tmpl`). The `off10` instance also has its own supply ammeter.
  The trim-table quantities are defined exactly as `run.sh` / RECORD-002
  define them, so this record is directly comparable. One exception:
  "at VDD/2" is read at the 1.65 V sweep point at every supply.
- **`tb_cp_otabuf_cin.sp`**: buffer loading. For 14 `VOUT` points
  (0.3 to 2.9 V), a pair of idle 10 uA `cp`s shares one AC source: the real
  one and a copy whose `XBUF` is an ideal unity VCVS (RECORD-006's
  `ideal_dump` edit, generated from the snapshot's own `cp` subckt). That
  copy draws nothing from `VOUT`. The capacitance difference at 1 MHz is
  what the buffer adds to the loop-filter node.
- **`tb_cp_otabuf_loopgain.sp`**: the buffer's own unity-feedback loop,
  measured in situ with the real legs and switches on `VDUMP`, at `VOUT` =
  0.5, 1.0, 1.65, 2.4 and 2.7 V. The `MN2`/`MP2` gates (the feedback inputs)
  are moved to a node closed at DC by a 1 GH inductor and driven at AC
  through a 1 F cap, so T = -v(VDUMP). Low-frequency phase was checked to be
  +180 deg, so the PM is the phase at |T| = 1. The loop is broken at a gate,
  so the feedback gates' own load is absent from `VDUMP`, which is a small
  optimistic error.

## Pass bounds (from DR-010; graded by `klt sim` limits)

| Quantity | Bound | Where it comes from |
|---|---|---|
| idle max \|VDUMP - VOUT\|, `VOUT` 0.30-2.70 V, every trim code | **<= 100 mV** | RECORD-006: 33.2 fC per 0.937 V of level. At 10 uA / 20 MHz, 100 mV is about 3.5 fC, or about 0.7 pp of `T_ref`. About 0.44 V would still close row 7 at 5% after the 1.05% ideal-tracker floor and the 0.8 pp dynamics reserve, so 100 mV keeps a 4x margin |
| buffer-added VOUT capacitance, 0.3-2.9 V | **<= 16.9 fF** (1% of C1 = 1.691 pF) | DR-001's adopted gf180-pll DR-005 condition 2 |
| buffer loop PM, five `VOUT` points | **>= 45 deg** (0.785 rad) | DR-005 condition 4 |

## Results at `mos_tt` / 27 C / 3.3 V (the only corner run)

### Tracking: |VDUMP - VOUT|, idle state, against the control

| Trim code | DR-010 buffer, max over 0.30-2.70 V | DR-010, max over 0.30-2.90 V | pre-#165 follower (control), max over 0.30-2.70 V |
|---|---|---|---|
| 2.5 uA | **13.6 mV** | 13.6 mV | 930.4 mV |
| 5 uA | **14.5 mV** | 14.5 mV | 954.7 mV |
| 10 uA | **14.9 mV** | 14.9 mV | 983.7 mV |
| 20 uA | **21.2 mV** | 21.2 mV | 1019.5 mV |
| 40 uA | **37.8 mV** | 37.8 mV | 1065.4 mV |
| 80 uA | **70.2 mV** | 70.2 mV | 1126.0 mV |

All six codes pass the 100 mV bound, and the control fails it at every code.
That is the negative control: the bound discriminates the old buffer from
the new one. At the 10 uA code the signed offset is **-14.87 mV at
`VOUT` = 2.40 V** (control: **-939.3 mV**, which reproduces RECORD-006's
0.937 V at 2.387 V) and -4.80 mV at 1.65 V. RECORD-006's charge-per-volt
scaling turns that into about 0.5 fC per cycle at 2.40 V, against
RECORD-006's 41.3 fC. The offset grows with the code (70 mV at 80 uA)
because the tails mirror the code and the systematic mirror Vds error grows
with overdrive.

**One-sided (acquisition) load, 10 uA code**: with UP alone asserted, the N
leg dumps 10 uA into `VDUMP` and the buffer must sink it. With DN alone, the
P leg sources 10 uA into it. Max |VDUMP - VOUT| over 0.30-2.70 V is
**155.6 mV (up)** and **173.5 mV (dn)**; at 2.40 V it is -93.3 / +66.2 mV.
The control gives 1041 / 2920 mV. This is finite output impedance under a
sustained load, not a turn-on level: every turn-on starts from the idle
state. It is reported, not graded.

### Supply current (DR-010 condition 3)

Whole-`cp` current, idle, 10 uA code, `VOUT` = 2.40 V: **61.56 uA**
(control: **35.97 uA**, equal to RECORD-002's "both-off 35.97 uA"). The
buffer change costs **+25.59 uA** (about 84 uW at 3.3 V), and this scales
with the trim code.

### Loading on the loop-filter node (DR-010 condition 2)

Buffer-added capacitance at 1 MHz, idle, 10 uA code:

| `VOUT` (V) | 0.3 | 0.5 | 0.7 | 0.9 | 1.1 | 1.3 | 1.5 | 1.7 | 1.9 | 2.1 | 2.3 | 2.5 | 2.7 | 2.9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C (fF) | 5.17 | 5.40 | 6.97 | 5.85 | 4.20 | 3.94 | 3.85 | 3.79 | 3.75 | 3.73 | 3.86 | 8.48 | **10.46** | 8.85 |

The maximum is **10.46 fF at 2.7 V, 0.62% of C1**, which passes the 16.9 fF
bound. The peak sits where the PMOS-input OTA's tail runs out of headroom
and its input C_gs stops being bootstrapped. Design exploration (scratch
decks, nominal only, not committed evidence) found the reasons for DR-010's
small input pairs:

- gf180-pll's 16u/48u input pairs measured 28-112 fF on the same quantity,
  up to 6.6% of C1.
- The pre-#165 follower measured 4.2-7.0 fF.
- The same first sizing gave 7.2 mV of idle offset at 10 uA.

### Buffer stability (DR-010 condition 4)

| `VOUT` (V) | 0.5 | 1.0 | 1.65 | 2.4 | 2.7 |
|---|---|---|---|---|---|
| DC loop gain (dB) | 31.9 | 35.2 | 35.7 | 35.6 | 35.8 |
| UGF (MHz) | 155 | 243 | 188 | 189 | 116 |
| PM (deg) | **74.5** | **77.1** | **73.5** | **75.0** | **76.0** |

The PM passes the 45 deg bound at every point, and the buffer settles in
nanoseconds against a 50 ns reference period. A 32-36 dB loop gain is
consistent with the idle offsets above.

### Icp trim table and up/dn mismatch, against RECORD-002

| Trim code | I_up @1.65 V (uA) | I_dn @1.65 V (uA) | mismatch @1.65 V | mismatch @2.40 V | RECORD-002 `mos_tt`/27 C @1.65 / @2.40 V |
|---|---|---|---|---|---|
| 2.5 uA | 2.5003 | -2.5085 | -0.331% | -0.588% | (code row: -0.384 ... -0.281% over PVT) |
| 5 uA | 5.0003 | -5.0120 | -0.234% | -0.416% | (-0.284 ... -0.192%) |
| 10 uA | 10.0005 | -10.0175 | **-0.170%** | **-0.298%** | **-0.170% / -0.298%**; I_up 10.0005, I_dn 10.0175 |
| 20 uA | 20.0008 | -20.0262 | -0.127% | -0.217% | (-0.185 ... -0.113%) |
| 40 uA | 40.0027 | -40.0487 | -0.115% | -0.197% | (-0.368 ... -0.084%) |
| 80 uA | 80.0495 | -80.2313 | -0.227% | -0.665% | (-0.887 ... -0.081%) |

Worst |mismatch| over 0.90-2.90 V at 10 uA is 0.583%, against RECORD-002's
0.720% worst over its full matrix. Net `both` current at 2.70 V, 10 uA, is
-39.14 nA, against RECORD-002's -39.1 nA. **The trim table and mismatch are
unchanged at this corner: the new and control `cp` give the same values to
every printed digit.** That is expected, because the dump buffer only sets
the dump branch's voltage and no measured `VOUT` current flows through it.
The existing trim and mismatch criteria (RECORD-002's table) therefore still
hold at nominal. The other 14 PVT points and the supply sub-axis are owed,
for the reason above.

## What this does not bound

- **Any corner other than `mos_tt`/27 C/3.3 V.** The tails, the offsets, the
  input capacitance and the PM all vary with corner and temperature. The
  three bounds are met at nominal only.
- **Random offset.** No Monte Carlo was run. The input devices are small
  (2u/1u, 6u/0.5u), so random offset may exceed the systematic 15 mV. The
  mismatch sections and the `klt sim` Monte Carlo pattern of
  `../../sg13cmos5l-cp-icp-trim-mc/` are the route, blocked the same way.
- **Switching (dynamic) charge.** This record is DC and small-signal. The
  closed-loop consequence is in
  `../../sg13cmos5l-closed-loop-lock/records/RECORD-007`.
- **The PM of the PLL loop itself.** `cp`'s output capacitance (legs plus
  buffer) has never been in `sg13cmos5l-loop-bandwidth-pm`'s model. That is
  filed as #196.

## Reproduce

```bash
export PDK_ROOT=<parent of ihp-sg13cmos5l>
cd sim/sg13cmos5l-cp-icp-trim
python3 -I testbench/gen_otabuf_requests.py
klt sim testbench/otabuf_nominal.request.json         --backend local --format json   # exit 0
klt sim testbench/otabuf_control_nominal.request.json --backend local --format json   # exit 3 (offset limits, by design)
klt sim testbench/otabuf_cin_nominal.request.json     --backend local --format json   # exit 0
klt sim testbench/otabuf_lg_nominal.request.json      --backend local --format json   # exit 0
# grids: batch fleet only, never locally
klt sim testbench/otabuf_pvt.request.json    --format json
klt sim testbench/otabuf_supply.request.json --format json
klt sim testbench/otabuf_cin_pvt.request.json --format json
klt sim testbench/otabuf_lg_pvt.request.json --format json
```

Each local request is one corner and one ngspice process (1-5 s here).
