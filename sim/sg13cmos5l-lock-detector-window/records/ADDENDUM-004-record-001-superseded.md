# ADDENDUM-004: RECORD-001 grid evidence claim superseded by a batch-fleet rerun

Append-only provenance addendum (issue #327, child of #213, Part of #199, item 9). It does not
edit `RECORD-001-window-hysteresis-chatter.md`. Contract: `sim/README.md` "Provenance addenda".
This addendum asserts nothing about the original run's environment; it replaces the evidence
claim for RECORD-001's 92-point grid with `RECORD-009-window-hysteresis-chatter-rerun-pinned.md`,
which reruns it on the DUT, templates and generator at producing commit `db36732` through
`klt sim` (probe job klt-sim-1a2d7ff81cdd, grid jobs klt-sim-4eabb71843d1 / klt-sim-e3ddde64ce5f /
klt-sim-b8b42124a998). Headline reproduces: 92/92 chatter, window 0.219-0.409 ns, 0 % hysteresis
at the ladder resolution. Resistor values differ (-4.4 % to -8.6 %, PDK `rhigh` drift) and are
disclosed in RECORD-009. Runner PDK revision is not independently verified. No consumer was
changed.

ADDENDUM-FOR: sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: ed6fdea23c59985b55e6f82fc320c62939c7a3f075881c1ca9a9c1a48e8714f5
ADDENDUM-RERUN: sg13cmos5l-lock-detector-window/records/RECORD-009-window-hysteresis-chatter-rerun-pinned.md
ADDENDUM-EVIDENCE: the 92-point lock_detector grid (92 windows, 92 ladders, 45 Schmitt, 12 tstep decks, 15 R/C extractions) rerun as 3 klt sim batch deck-list requests on the Spot fleet (runner klt 0.9.0, ngspice-46) against files reconstructed with git show db36732; window, Schmitt and tstep CSVs and all C values reproduce byte-identically, ladder verdicts reproduce, R differs by PDK rhigh drift.
