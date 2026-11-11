# ADDENDUM-004: RECORD-002 resized-window campaign evidence claim superseded by a batch-fleet rerun

Append-only provenance addendum (issue #328, child of #213, Part of #199, item 9). It does not
edit `RECORD-002-resized-window-hysteresis-chatter.md`. Contract: `sim/README.md` "Provenance
addenda". This addendum asserts nothing about the original run's environment; it replaces the
evidence claim for RECORD-002's campaign with `RECORD-009-resized-window-hysteresis-chatter-rerun-batch.md`,
which reruns it on the DUT at producing commit `07e1866` through `klt sim` (probe job
klt-sim-2b9efd5902c3, phase jobs listed there). Scope: the full RECORD-002 grid (R/C, window,
Schmitt, timestep convergence, 18-point ladder). Window, Schmitt and C reproduce; R shifts by
-4.5 to -8.7 %; 17 of 18 ladder corners converge (one does not, disclosed) with one threshold
difference. Runner PDK revision is not independently verified. No consumer was changed.

ADDENDUM-FOR: sg13cmos5l-lock-detector-window/records/RECORD-002-resized-window-hysteresis-chatter.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 129f520ef9115288f01238f26cb03e7e97e57ddf1d26782ec10275226acb8cf4
ADDENDUM-RERUN: sg13cmos5l-lock-detector-window/records/RECORD-009-resized-window-hysteresis-chatter-rerun-batch.md
ADDENDUM-EVIDENCE: RECORD-002's grid rerun as klt sim batch deck-list requests on the Spot fleet (runner klt 0.9.0, ngspice-46) against the 07e1866 DUT; window twin_r, Schmitt thresholds and C identical, R -4.5..-8.7 %, 17/18 ladder corners converged (1 ngspice timestep-too-small failure retained), 1 ladder corner with a different assert threshold.
