# ADDENDUM-003: RECORD-004 crowbar-grid evidence claim superseded by a batch-fleet rerun

Append-only provenance addendum (issue #331, child of #213, Part of #257 and
#199, item 9). It does not edit `RECORD-004-crowbar-current-mitigation.md`.
Contract: `sim/README.md` "Provenance addenda". RECORD-004 names no worker and
cites no PDK revision, and no contemporaneous evidence of the producing
session's environment was recovered; this addendum asserts nothing about the
original run's environment. It replaces the evidence claim for the grid that
`testbench/run_schmitt_crowbar.sh` produces with the measurement in
`RECORD-008-crowbar-grid-rerun-batch.md` (4 variants x 45 PVT points on the
Spot batch fleet via `klt sim`, DUT `netlist-snapshots/lock_detector_hystfix.spice`
as of `36e4bae`). Scope: the crowbar grid only; RECORD-004's closed-loop and
ladder evidence is not rerun and no consumer was re-pointed.

ADDENDUM-FOR: sg13cmos5l-lock-detector-window/records/RECORD-004-crowbar-current-mitigation.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: a9b432b67c4cf9cd0d23dfa8552300d0c33f8166fc5b507e5201aa8fa234b0cf
ADDENDUM-RERUN: sg13cmos5l-lock-detector-window/records/RECORD-008-crowbar-grid-rerun-batch.md
ADDENDUM-EVIDENCE: the 180-point crowbar grid rerun as four klt sim batch requests (jobs klt-sim-f55e820a7ee1 asdrawn, klt-sim-06122414b773 long2u, klt-sim-f09bfeb8b93c long4u, klt-sim-c853b5423324 long8u; runner klt 0.9.0, PDK at the pinned revisions, ngspice-46) against the frozen hystfix snapshot; all 180 points pass, worst-case peak crowbar 640.6/195.4/97.6/49.9 uA reproduces exactly, trip points within 0.32 %; fall-peak estimator differs up to 7.9 %, i_midband not reproduced (i_vdd2 substituted).
