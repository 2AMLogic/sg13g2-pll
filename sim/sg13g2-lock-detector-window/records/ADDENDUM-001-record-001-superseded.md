# ADDENDUM-001: RECORD-001 evidence claim superseded by a same-bench batch rerun

Append-only provenance addendum (issue #236, execution child of #217, item 9).
It does not edit `RECORD-001-resized-window-hysteresis-chatter.md`. Contract:
`sim/README.md` "Provenance addenda". RECORD-001 names no worker and cites no
PDK revision, and no contemporaneous evidence of the producing session's
environment was recovered. This addendum asserts nothing about the original
run's environment. It replaces the evidence claim with the measurement in
`RECORD-002-resized-window-hysteresis-chatter-batch-rerun.md`, which carries
the PDK revision, tool versions, host, command and batch job ids.

Scope, stated plainly: the measurement RECORD-001 reports (R/C extraction,
window matrix, readout Schmitt, timestep convergence, the 21-corner ladder
with recovery and supply current, and the hysteresis diagnostic) was re-run
at the original matrices against the frozen DUT snapshot, byte-identical to
the producing commit `40b020e`. Six of seven output files reproduce
byte for byte; the seventh (`ladder_raw`) differs only in line endings. The
four sizing sweeps that selected the geometry (`rc_sizing`, `rc_pairing`,
`window_sizing`, `xmpd_sizing`) were NOT rerun and stay RECORD-001's
unreplaced evidence. No figure was replaced, so no consumer changed.

ADDENDUM-FOR: sg13g2-lock-detector-window/records/RECORD-001-resized-window-hysteresis-chatter.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 9bc950952a2aa07444e24d4d341b52afff17dedf6daaca8b17fcd4707027e8eb
ADDENDUM-RERUN: sg13g2-lock-detector-window/records/RECORD-002-resized-window-hysteresis-chatter-batch-rerun.md
ADDENDUM-EVIDENCE: the RECORD-001 measurement matrices rerun through testbench/run_batch.py as klt sim deck-list requests on the batch fleet (31 evidence jobs listed in corners/batch_rerun236/jobs.tsv, ngspice-46, runner klt 0.9.0, submitted from loom-worker-2 on 2026-11-11), against the DUT snapshot byte-identical to producing revision 40b020e; 684 decks, 10 retried once with trtol=1 and passed; rc_extract, window, schmitt, ladder, tstep_convergence and hysteresis_diag outputs byte-identical to RECORD-001's committed files, ladder_raw identical modulo CRLF; sizing sweeps not rerun.
