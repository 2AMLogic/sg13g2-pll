# RECORD-007: rerun of RECORD-003's `schmitt_rewire` grid via `klt sim` on the batch fleet (issue #329)

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #329 (split from #257, child of #213, Part of #199, item 9 provenance
  migration). Append-only. Reruns the `corners/schmitt_rewire.csv` grid behind
  `RECORD-003-hysteresis-fix.md` (sha256 `78f0663d46e8bd5db7123225571905238019cfcf18f6d0b455471b4afba63a00`, verified unchanged) and is the
  `ADDENDUM-RERUN` target of `ADDENDUM-002-record-003-superseded.md`. No earlier record or
  committed `corners/` file was edited.
- **What was rerun**: RECORD-003 "Term 1" only: `schmitt_hv`'s feedback rewiring, measured as
  input-referred hysteresis, as-drawn control vs as-committed (`feedback_rewired`), on **both**
  PDK arms (`ihp-sg13cmos5l` and the explicit `ihp-sg13g2` arm), 3 MOS corners x 3
  temperatures x 3 supplies = 27 points per (PDK, DUT), 108 rows. The rest of RECORD-003
  (XMPD re-size, `schmitt_hystfix`/`run.sh` campaign) is **not** rerun here.
- **DUT at its producing commit, not today's design**: both `lock_detector.spice` netlists were
  taken with `git show a595772:<path>` (`design/sg13cmos5l/netlist/lock_detector.spice`,
  `design/netlist/lock_detector.spice`); today's copies differ (later resizing). The as-drawn
  control is the same two-substitution reversal as `run_schmitt_rewire.sh`'s `as_drawn()`.
  Files: `../netlist-snapshots/rerun329/{cmos5l,g2}_{as_drawn,rewired}.spice`; generator
  `../testbench/gen_rerun329.py`.
- **Entry point / deviation, disclosed**: `testbench/run_schmitt_rewire.sh` is a local ngspice
  loop and was **not** run. Its template `tb_schmitt_rewire.sp.tmpl` was turned into 12 decks
  (`../testbench/rerun329/`, one per PDK/DUT/supply, literal supply and mid-rail threshold because
  a `.meas ... when v()=` card cannot follow `corners.supply_v`) and 12 `klt sim` requests
  (`../requests/schmitt_rewire_*.request.json`); MOS corner and temperature are request axes.
  Original `.lib`, `.option temp`, `.tran` and `.meas` lines moved from the deck to klt's generated
  control (same `.tran 1n 4u`, same `find v(vin) when v(sout)=VMID fall=1 / rise=1`). The OSDI
  preflight (`check-osdi-arch.sh`) is replaced by `options.osdi_preload` on the runner.
- **Probe first**: `../requests/schmitt_rewire_probe.request.json` (cmos5l / rewired / mos_tt /
  27 C / 3.3 V), job `klt-sim-5a775113a446`, runner klt `0.9.0`, ngspice-46: `vth_up`
  2.06969 V, `vth_dn` 1.13525 V (original 2.06875 / 1.13525).
- **Grid command**:

  ```
  klt sim --batch-set sim/sg13cmos5l-lock-detector-window/requests/schmitt_rewire_{cmos5l,g2}_*.request.json \
    --max-in-flight 4 --wait-for-capacity 600 --capacity-retries 3 --format json -o <outdir>
  ```

  Status `pass`, 12 submitted, 0 refused, exit 0. Folded to
  `../corners/schmitt_rewire_rerun329.csv` by `../testbench/collect_rerun329.py`.
- **Tools**: client `klt 0.9.2.dev661+g1de5c0432aad`; runner klt `0.9.0` (`runner_compatibility:
  match`), ngspice-46 (`/usr/local/bin/ngspice`, sha256
  `dc859418bedd0478ff439a2d3e2e09f4386a7f4d5e3f17671953e101a000cc60`, built 2026-10-01), AWS Batch
  Spot fleet, `us-east-1`, Intel Xeon Platinum 8488C. Submitted from `loom-worker` host
  `host-a6032f0c`.
- **PDK revisions (pin, NOT independently verified on the runner)**: PDK ihp-sg13cmos5l revision
  607e18d4bd9214a52575c194b4181ef449f9252f and PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e, the pins in `sim/provenance-migration.md`. The
  runner's PDK lives at `/opt/pdk` and its stamp was unreadable
  (`pdk stamp unreadable: FileNotFoundError`, `pdk_stamp_comparison: not_comparable`); the
  client's `~/share/pdk/ihp-sg13cmos5l` is no longer a git checkout, so no revision could be read
  from either side. Only `cornerMOShv.lib` is hash-matched (client side, sha256
  `5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a`, identical in both
  client trees). Tool gaps already tracked upstream: klayout-tools#5318, #3462.

## Results

| PDK | DUT | Hysteresis (V) | % of VDD | vs RECORD-003 CSV |
|---|---|---|---|---|
| `ihp-sg13cmos5l` | as drawn | 0.88 - 1.58 mV | 0.025 - 0.053 | all 27 trip-point pairs identical |
| `ihp-sg13cmos5l` | feedback rewired | 0.8048 - 1.0586 | 26.28 - 30.34 | **differs**: max 2.0 mV (V_TH+) / 2.3 mV (V_TH-), at mos_ss/27 C/3.63 V |
| `ihp-sg13g2` | as drawn | 0.88 - 1.58 mV | 0.025 - 0.053 | all 27 identical |
| `ihp-sg13g2` | feedback rewired | 0.8044 - 1.0581 | 26.29 - 30.33 | all 27 identical |

The rewiring conclusion stands on both arms (about 1000x more hysteresis than the as-drawn cell,
every corner, 26-30 % of VDD). The two arms are reported separately, each with its own job ids
(below). RECORD-003 stated the two PDKs' trip points were identical field for field; in this
rerun they are **not**: the cmos5l-rewired arm moved by up to ~2 mV per trip point while the
g2-rewired arm reproduced exactly. The cause was not isolated (candidates: runner `/opt/pdk`
cmos5l tree vs the original host's tree, ngspice build, transient step noise on the rewired
cell); no further runs were made. Hysteresis shifts by at most 4.0 mV (0.4 % of VDD), well inside the
originally reported band.

| Arm | Supply | Job ids (as_drawn / rewired) |
|---|---|---|
| cmos5l | 2.97 V | klt-sim-6f10e516e44f / klt-sim-ba7b31d91d52 |
| cmos5l | 3.3 V | klt-sim-3f062fa28f86 / klt-sim-4e74d81ee410 |
| cmos5l | 3.63 V | klt-sim-f148b5b62b70 / klt-sim-e4e626e460ad |
| g2 | 2.97 V | klt-sim-69e608035ea0 / klt-sim-8d1d1cdb9728 |
| g2 | 3.3 V | klt-sim-dade84b5318f / klt-sim-8ed9df71615b |
| g2 | 3.63 V | klt-sim-040a3e0ee9c8 / klt-sim-602f839a5d23 |

## What this does not bound

- The original run's environment (superseded, not recovered).
- The runner's actual PDK revision (unproven, see above); the PDK-identity statement of
  RECORD-003 is not re-established for the cmos5l arm.
- The rest of RECORD-003, RECORD-005, PEX, #139. No consumer figure was replaced, so
  `characterization/` was not changed.
- No failed attempts: one probe, one 12-request set, no retries.
