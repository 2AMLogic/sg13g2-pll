# RECORD-003: closed-loop PVT campaign at the divider-compatible operating point — 17 real + 3 control units, 19/20 dual-lock, `mos_ss`/125 C fails in the divider

- **Slug**: `sg13cmos5l-closed-loop-real-divider`
- **Issue**: #516 (T1 items 5 and 8; gates rows 7, 10, 11 and the second
  half of 16 through R-2). Append-only: RECORD-001, RECORD-002 and
  ADDENDUM-001 are not edited and none of their committed bytes is
  overwritten — every artifact of this record lives under the new tag
  `corners/pvt1/` and the new request tree `testbench/pvt/`.
- **Scope**: the RECORD-002 operating point (band `00`, `f_ref` = 9.375 MHz,
  N = 64, 600 MHz, committed `pfd` + DR-010 `cp` + `loop_filter` + `vco` +
  repaired `divider_chain`) across PVT: 5 MOS corners x {-40, 27, 125} C at
  3.3 V (15 real units) plus `mos_tt` / 27 C at 3.0 and 3.6 V (row 18's
  endpoints), each with the behavioural-divider control arm at the three
  `mos_tt` temperatures — 17 real + 3 control units, one 10 us transient
  each, schematic-level, pre-layout. Resistor corner held at `res_typ`
  everywhere (RECORD-002's deck; the campaign axes are MOS x temp x
  supply). No spec-row number is proposed, amended or relaxed anywhere in
  this record.
- **Corner coverage**: 20 units as above; every unit graded, no corner
  dropped (the one failing corner is kept and its failing block named).

## Tooling, provenance, fleet

- **Engine**: ngspice-47 on the batch-fleet runner image
  (`engine_version` "47", `/usr/local/bin/ngspice`), `num_threads=4`,
  `numdgt=12`, per-unit `.option scale=1 reltol=1e-3 vntol=1e-4 abstol=1e-9
  trtol=7` (see "Attempt history" for why the cold units need the augmented
  line). This is a **solver-option delta vs RECORD-002**, whose deck ran the
  default tolerances at 27 C; at the nominal tuple the two agree to ~0.6 %
  on static phase and ~0.1 uA on every per-domain current (table below).
- **klt**: client `0.9.3.dev2575+g6bd18bbc8637`, fleet runner `0.9.0`
  (compatibility `match`), backend `batch`, staged model closure
  (`options.stage_model_inputs`) — the fleet image's own PDK tree is never
  read. Every report's `environment.staged_model_inputs.source_sha256` is
  graded against the generator's `pinned-closure.csv` (the RECORD-015 trap:
  the pinned tree's model cards are symlinks into the sibling `ihp-sg13g2`
  tree, so the *closure*, not just the `cornerMOShv.lib` hash, is what must
  ship): `corners/pvt1/staged-pdk-check.json` — **all reports matched all
  closure files, zero missing, zero sha mismatch**.
- **Pins** (gate-parsed form, `sim/README.md`): PDK-PIN `ihp-sg13cmos5l`
  `607e18d4bd9214a52575c194b4181ef449f9252f`; PDK `ihp-sg13g2` revision
  `5cccb161f7492697cfa52eb14dc03beb00bdca9e`. The staged seeds resolve to
  the `ihp-sg13g2` release install (`cornerMOShv.lib` sha256
  `5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e847b3e93481a`,
  `cornerRES.lib` `2c18502104146804444a567abfe7d00520752bf75426809f9d79f40198fe9c1e`);
  the full closure (both corner libs, their same-directory includes, the
  four OSDI objects) is committed as
  `testbench/pvt/pinned-closure.csv`.
- **Batch job ids**: `corners/pvt1/batch-jobs.csv` carries every job the
  collected reports cite (15 jobs: 10 grid, the ss/-40 C uic re-run,
  the shard-2 resume, the three slow-corner solos), with state, instance
  id/type and runner version. The full attempt trail — including two jobs
  killed with their client and one spot-reclaimed job whose results never
  reached a report — is disclosed under "Attempt history".

## `vctrl` start-point policy and window (issue #516 step 3)

`.ic v(vctrl)` stays at RECORD-002's **1.23 V at every unit**, and the
window stays **10 us = 93.75 `T_ref`**: a per-corner interpolation is
impossible for 14 of 17 units (the committed band-00 Kvco table covers
exactly three PVT bundles), and no corner needed the slack — the slowest
acquisition measured is 2.03 us (`mos_tt`/-40 C), leaving >= 69 reference
cycles after acquisition, far beyond the 20 the dual-lock criterion needs.
**Every lock time in this record is therefore warm-started** (1.23 V sits
9–289 mV from each unit's settled `vctrl`), exactly as RECORD-002's was;
nothing here is a cold-start acquisition claim.

## The 20-unit table

Lock criterion: the campaign's dual-lock (`|df/f_ref| < 1 %` AND
`|phase| < 5 % T_ref` for >= 20 consecutive reference cycles), trace built
from the `t_ref`/`t_fb` crossing series by the committed, self-tested
`mismatch_gain_metrics.lock_trace_from_edges` (same function
`test_mismatch_gain_metrics.py` pins to the sampled-waveform `lock_trace`).
Static phase is the mean over the final 20 reference cycles (8–10 us
window); currents are 8–10 us averages per supply domain. Full
machine-readable rows, including per-unit predictions and the clk-per-FB-
period histograms, are committed as `corners/pvt1/pvt_units.csv`
(`pvt_summary.json` rolls them up).

Real arm (17 units):

| Unit (`mos`/T/Vdd) | Verdict | Lock (ns, warm) | Static phase mean (min–max, % `T_ref`) | `f_vco` 8–10 us (MHz) | `vc_avg` (V) | `i_pfd`/`i_cp`/`i_vco`/`i_div` (uA) |
|---|---|---|---|---|---|---|
| tt / 27 / 3.3 | **locked** | 320 | 1.739 (1.712–1.765) | 600.003 | 1.260 | -25.3 / -62.0 / -1443.5 / -1374.6 |
| tt / 125 / 3.3 | **locked** | 320 | 1.506 (1.457–1.601) | 599.986 | 1.293 | -25.8 / -62.1 / -1277.9 / -1411.2 |
| ss / 27 / 3.3 | **locked** | 320 | 1.572 (1.502–1.672) | 599.985 | 1.233 | -24.3 / -61.6 / -1303.9 / -1318.2 |
| **ss / 125 / 3.3** | **not_locked** | 427 | 1.244 (-0.147–2.846) | 600.021 | 1.388 | -24.8 / -62.0 / -1190.4 / -1346.2 |
| ff / 27 / 3.3 | **locked** | 533 | 1.895 (1.860–1.934) | 599.995 | 1.191 | -26.4 / -62.2 / -1565.0 / -1441.0 |
| ff / 125 / 3.3 | **locked** | 320 | 1.617 (1.595–1.650) | 599.993 | 1.234 | -26.9 / -62.3 / -1378.1 / -1473.2 |
| sf / 27 / 3.3 | **locked** | 320 | 1.602 (1.555–1.652) | 600.026 | 1.342 | -25.4 / -62.2 / -1443.3 / -1378.9 |
| sf / 125 / 3.3 | **locked** | 427 | 1.339 (1.213–1.465) | 600.000 | 1.400 | -25.9 / -62.3 / -1289.0 / -1415.4 |
| fs / 27 / 3.3 | **locked** | 533 | 1.861 (1.834–1.892) | 600.007 | 1.122 | -25.2 / -61.7 / -1428.2 / -1372.8 |
| fs / 125 / 3.3 | **locked** | 1707 | 1.630 (1.557–1.695) | 599.996 | 1.191 | -25.7 / -61.9 / -1267.4 / -1403.9 |
| tt / -40 / 3.3 | **locked** | 2027 | 1.821 (1.777–1.889) | 599.992 | 1.122 | -25.0 / -61.5 / -1554.3 / -1364.7 |
| ss / -40 / 3.3 (uic) | **locked** | 853 | 1.706 (1.681–1.751) | 599.994 | 1.090 | -24.1 / -60.6 / -1396.2 / -1308.9 |
| ff / -40 / 3.3 | **locked** | 1813 | 1.933 (1.882–1.995) | 599.994 | 1.207 | -26.2 / -62.3 / -1750.3 / -1432.1 |
| sf / -40 / 3.3 | **locked** | 1920 | 1.734 (1.673–1.789) | 599.991 | 1.209 | -25.2 / -61.8 / -1551.2 / -1368.9 |
| fs / -40 / 3.3 | **locked** | 640 | 1.920 (1.850–2.033) | 600.021 | 1.042 | -25.0 / -61.2 / -1557.8 / -1364.2 |
| tt / 27 / 3.0 | **locked** | 320 | 1.554 (1.496–1.610) | 599.994 | 1.190 | -22.5 / -61.5 / -1212.1 / -1215.5 |
| tt / 27 / 3.6 | **locked** | 960 | 1.945 (1.865–2.063) | 599.952 | 1.348 | -28.2 / -62.6 / -1686.7 / -1540.6 |

Control arm (behavioural /64 divider, `mos_tt`, 3.3 V):

| Unit | Verdict | Lock (ns, warm) | Static phase mean (% `T_ref`) | `f_vco` (MHz) | `i_pfd`/`i_cp`/`i_vco` (uA) |
|---|---|---|---|---|---|
| tt / -40 | **locked** | 213 | 1.832 | 600.002 | -24.8 / -61.5 / -1452.9 |
| tt / 27 | **locked** | 107 | 1.759 | 600.001 | -25.0 / -62.0 / -1341.5 |
| tt / 125 | **locked** | 213 | 1.550 | 600.003 | -25.5 / -62.1 / -1175.5 |

Readings:

- **19 of 20 units meet the dual-lock criterion.** Every locked unit holds
  it from its lock time to the end of the 10 us window (>= 69 cycles), with
  static phase 1.34–1.95 % of `T_ref` (the 1.24 % unit, ss/125, did not lock) — under the 5 % R-2 bound with about
  2.6x margin at the worst locked corner — and `f_vco` 599.95–600.03 MHz.
- **Nominal cross-check vs RECORD-002** (same tuple, option-line delta
  only): lock 320 ns vs 320 ns, static phase 1.739 % vs 1.729 %, `i_vco`
  -1443.5 uA vs -1443.5 uA, `i_div` -1374.6 vs -1374.5 uA, `vc_avg`
  1.2604 V vs 1.2746 V. The campaign reproduces the nominal record.
- **The one failure is `mos_ss` / 125 C, and it is in the divider.** The
  unit tracks 600 MHz on average and its mean static phase is 1.24 %, but
  the in-loop divider miscounts: of the 20 scored FB periods (7.8 us on),
  15 carry exactly 64 clk edges, two carry 63 and two carry 65 — so the
  per-cycle dual-lock criterion is broken mid-window. `vctrl` is settled
  mid-range (1.388 V, min/max well inside the rails), ruling out a VCO
  reach or cp drive failure; the failing block is **`divider_chain`
  (miscount in-loop)**. This is the first measured evidence of a
  slow-corner miscount at 600 MHz — RECORD-001's divider star has NO bound
  at any 125 C cross corner (its lowest N = 64 bound anywhere is 880 MHz at
  `mos_tt`/125 C), and `sg13cmos5l-vco-kvco-table` covers band 00 at this
  tuple only through the slow bundle. The corner is kept, not dropped; a
  divider-level attribution (which stage, why ss/125 specifically) is NOT
  isolated here and belongs with the divider redesign tracker (#514, whose
  9-corner star scope is exactly this axis family).
- **Edge-count histogram note**: every unit's first scored FB period reads
  57 edges — including every locked unit and both arms. That is the
  `t_clk` series' 7.8 us bucket-alignment boundary (a partial period
  entering the window), not a miscount; the divider criterion uses the
  8–10 us average window where locked units read a clean 19/19 periods at
  exactly 64.
- **Per-domain supply current** (row 11 input, 8–10 us averages, sign as
  measured into the sources): `i_pfd` -22.5 to -28.2 uA, `i_cp` -60.6 to
  -62.6 uA, `i_vco` -1175.5 to -1750.3 uA (real arm; control -1175.5 to
  -1452.9), `i_div` -1215.5 to -1541.0 uA — whole-loop total 2.51 to
  3.32 mA over the 17 real units, monotonically tracking supply and
  inversely tracking temperature as expected.

## Pre-stated predictions vs outcomes (issue #516 step 5)

Written into `corners/pvt1/pvt_units.csv` by the collector from the two
committed sources only — `sg13cmos5l-divider-max-frequency` RECORD-001's
N = 64 per-corner bounds and `sg13cmos5l-vco-kvco-table` RECORD-002's
band-00 rows — never extrapolated:

- **Divider bound**: the 12 units with a divider prediction (9 real + 3 control; the real ones
  on the 9-point star: five MOS corners at
  27 C, `mos_tt` at -40/125 C, `mos_tt` at 2.97/3.63 V borrowed for the
  3.0/3.6 V units, each named with its supply direction) were predicted
  "within proven exact range"; the tightest is `mos_tt`/125 C at +280 MHz
  margin (exact at 880 MHz, first miscount 896 MHz). The eight cross
  corners (ss/ff/sf/fs at -40 and 125 C) are marked **"unpredicted: no
  divider bound at this corner"** — 8 of 17 real units. Outcome: every
  predicted unit locked with exact edge counts; the one failure (ss/125)
  sits in the unpredicted set, so no prediction was falsified.
- **Band-00 VCO reach**: the three bundle corners predict 600 MHz at
  ~1.229 V (typ), ~1.585 V (slow = ss/125, inside cp compliance
  0.25–3.10 V), ~0.933 V (fast = ff/-40); the 3.0 V and 3.6 V `mos_tt`/27 C units also receive the typ-bundle
  reach, because the collector matches a bundle on (MOS corner, temperature)
  only — a 3.3 V-characterised reach lent to a different supply, unlike the
  divider borrow, which names its supply direction; so 5 real units are
  predicted, and the other 12 real units are
  marked **"unpredicted: no band-00 Kvco coverage"**. Outcome: the typ and
  fast corners settled at 1.260 V and 1.207 V (within 35 mV and 274 mV of
  the interpolated pair); the slow corner settled at 1.388 V — 197 mV
  below the interpolated 1.585 V, consistent with the divider miscounting
  (the loop parks where *its* fb rate says 600 MHz-equivalent, not where a
  clean /64 would). RECORD-015's failure mode (125 C non-acquisition from
  VCO tuning range) did NOT occur at this operating point: no unit pinned
  `vctrl` at a rail.

## Attempt history (fleet; the canary ledger)

- **Probe** (host rule: one unit before the grid): `mos_ss`/125 C — the
  slowest expected corner — job `klt-sim-8be67309a1c1`, done in 1245 s.
  It ran the *pre-cold-fix* option line (deck sha256 `3df72d47...`, commit
  `40a1963`), before the -40 C aborts forced the augmented line; the grid
  then re-ran the same corner on the final deck. Disclosed, not counted as
  a campaign unit.
- **Grid attempt 1** (`--batch-set`, jobs `klt-sim-a6424be1a0bf`,
  `e6d676d6323a`, `a8728467deff`, `8dd1fa7f1943`, `391d1ddab1cc`,
  `16739b6c37e9`, `374a7c960d6a`, `7e9a1f0162e6`, `931045b160a6`,
  `897fb607b06b`): every -40 C unit that ran aborted with
  `timestep_too_small` (dynamic gmin stepping failed) under the default
  option line; two shards were never launched (`not_launched` capacity
  refusals, jobs `236e273e732b`, `d65338118dcf` allocated but unspent).
  Fix: the divider-max-frequency campaign's proven cold option line
  (verbatim, same DUT family) + the five -40 C units as single-unit jobs.
- **`mos_ss`/-40 C additionally needs `uic`**: it still aborted inside the
  first 300 ns under both option lines (measured locally; `mos_tt`/-40 C
  passes without uic, so it is the ss start-up region). The unit request
  starts directly from the deck's `.ic` cards; re-run as job
  `klt-sim-44c05c9a194e` — pass, 1766 s, and the *locked* verdict above.
  The `mos_ss`/125 C deck needed no uic.
- **Resume attempts for the lost 3-unit shard** (sf/125, fs/27, fs/125):
  two clients were killed with their sessions (jobs `649517e6c6f0`,
  `027ea4f3fa57` and `c320aa49fec8`, `3b5e1253c625` completed but their
  envelopes died uncollected; `c96638a0920e` was spot-reclaimed mid-run);
  the collected resume job `klt-sim-f5918c7938d2` then **timed out at the
  fleet's 3600 s whole-job ceiling (the request's own client-side
  `job_timeout_s` was 3500 s; the job died at 3504 s) — 3 ngspice x 4 threads = 12 solver
  threads on an 8-vCPU instance is 1.5x oversubscribed and nothing
  finished**. Fix: the three units re-emitted as their own single-unit
  requests (the cold-unit pattern; generator `SOLO_WARM_UNITS`) — jobs
  `klt-sim-610b082dc610` (1058 s), `ad2ea046a47d` (1203 s),
  `47892f59156e` (1123 s), all pass. Fleet lesson recorded here and in the
  generator: a shared shard of `num_threads=4` units starves at 3+ units
  per 8-vCPU instance well before the per-unit timeout.
- **klt gaps hit** (filed upstream per the friction protocol:
  klayout-tools#7114 and #7115):
  a `--batch-set` member refused `not_launched` at envelope-write time
  keeps `report: null` even when its job later runs and collects (the
  member result is only at the conventional on-disk path); and `--resume`
  trusts the killed client's stale shard map, re-running shards the fleet
  had already finished. Both cost fleet budget here; neither lost data.

## Reproduce

    # requests: byte-identical regeneration (verified against the committed tree)
    python3 -I testbench/gen_pvt_requests.py \
        --pinned-pdk /home/ubuntu/share/pdk/ihp-sg13cmos5l.bak-20261015T153815Z \
        testbench/pvt
    # probe, then the grid (host rules: batch fleet, never local loops)
    klt sim testbench/pvt/probe/request.json --backend batch \
        --wait-for-capacity 600 -o testbench/pvt/probe-run \
        --format json --report-out testbench/pvt/probe-run/probe.report.json
    klt sim --batch-set testbench/pvt/real_3v3/request.json \
        testbench/pvt/real_cold_tt_-40c/request.json ... testbench/pvt/control/request.json \
        --wait-for-capacity 600 --capacity-retries 3 --format json \
        --report-out testbench/pvt/pvt.report.json
    # collect (this wrote every committed corners/pvt1/ artifact)
    python3 -I testbench/pvt_metrics.py --pinned-closure testbench/pvt/pinned-closure.csv \
        --real-netlist testbench/pvt/real_3v3/pll_real.cir \
        --real-netlist testbench/pvt/real_3v0/pll_real.cir \
        --real-netlist testbench/pvt/real_3v6/pll_real.cir \
        --control-netlist testbench/pvt/control/pll_control.cir \
        --out-dir corners/pvt1 testbench/pvt/pvt.report.json \
        testbench/pvt/ss-uic.report.json testbench/pvt/real3v3-resume3.report.json \
        testbench/pvt/slow3.report.json

`run.sh` is untouched (its defaults still reproduce RECORD-001's point and
would overwrite committed `corners/` files). The circuit body per arm is
byte-for-byte what `run.sh` renders for RECORD-002's `_o2` runs, minus the
cards `klt sim` owns; `testbench/pvt/units.csv` lists all 20 units plus the
probe.

## What this does and does not establish

- **Establishes** (schematic, pre-layout, one 10 us run per unit,
  simulator-deterministic, staged pinned closure verified per report): at
  the RECORD-002 operating point the real-block closed loop **meets the
  dual-lock criterion — including the 5 % static-phase bound — at 16 of 17
  PVT corners and both supply endpoints**, with warm-started acquisitions
  of 0.32–2.03 us and per-domain supply currents as tabulated. R-2's gate
  ("a phase-locked closed loop that meets the 5 % static-phase criterion on
  the real blocks") is now evidenced at 16/17 corners — **not all of PVT**:
  `mos_ss`/125 C does not lock, failing in the divider.
- **Row 7 (lock time)**: these are warm-started numbers, one run per
  corner, no cold-start acquisition, no statistical treatment — they are
  the PVT evidence R-2 was waiting for, not a row-7 number (that needs a
  decision record and ratification; nothing is proposed here).
- **Row 10 (reference spur)**: still owed. A locked carrier now exists at
  16 corners, but no spur/switching-charge measurement was made in this
  campaign.
- **Row 11 (power)**: per-domain 8–10 us averages at 20 corners are now
  recorded; no whole-PLL total is proposed (also gated on R-3), and these
  are transient-window averages, not a power-down/standby characterisation
  (row 17 is waived for v1 regardless).
- **Row 16, second half** ("window >= 2x worst static phase offset"): still
  unmeasured — the stretch goal of instantiating `lock_detector` was NOT
  done (fleet budget went to the shard recovery instead). The campaign does
  supply the input that decision needs: worst locked-corner static phase
  1.95 % of `T_ref` (3.6 V unit), so "2x worst" sits at ~3.9 % of `T_ref`
  (~4.1 ns at this `f_ref`) against lock-detector windows of 3.7–11.2 ns
  (RECORD-003..005 ladders).
- **Not re-verified here**: row 6/6a at this tuple; the ideal-clock divider
  bracket at any PVT point other than nominal; any post-layout behaviour.
- **Stale upstream text, named not edited** (out of scope per #516): R-2's
  evidence paragraph in `spec/target-spec.md` ("Current evidence: the
  mitigated `cp` leaves an 8.204 % static phase error") and
  `manifests/README.md` ("a closed loop that acquires (the nominal
  real-divider loop does not acquire)") still describe RECORD-001; both
  predate RECORD-002 and now this record. #530 covers only the chipalooza
  proposal's two passages — a follow-up for these two is filed with this
  record (#531).
