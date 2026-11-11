# ADDENDUM-001: RECORD-001 evidence claim superseded by a same-bench fleet rerun

Append-only provenance addendum (issue #317, Part of #216 / #199). It does not
edit `RECORD-001-duty-cycle-and-vco-current.md`. Contract: `sim/README.md`
"Provenance addenda". RECORD-001 cites only `ngspice-46` and an install path,
never a PDK revision. This addendum asserts nothing about the original run's
environment; it replaces the evidence claim with the measurement in
`RECORD-002-duty-cycle-and-vco-current-rerun-fleet.md`, which carries the
PDK pins, tool, fleet job, host and command.

The rerun is full-scope (300 + 8 runs) but does not reproduce RECORD-001
exactly: duty 43.71–51.50 % (original 43.74–51.56 %), 31 points below the 45 %
floor (original 30), all at -40 C, and supply current within 2.2 %. The
original's failures are retained. The PDK commits are the repo pins,
supported by byte-identical model/OSDI hashes on the worker, not read from the
worker (RECORD-002 states this).

ADDENDUM-FOR: sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 87edf592929efe37eb5588c5c2577f89d952a2a2623070c69422d825853fa009
ADDENDUM-RERUN: sg13cmos5l-vco-duty-cycle/records/RECORD-002-duty-cycle-and-vco-current-rerun-fleet.md
ADDENDUM-EVIDENCE: the full 300-run grid plus 8-run timestep check rerun as one 308-deck klt sim request on the batch fleet (job klt-sim-2ce90b38ce36, ngspice-46, runner klt 0.9.0) against the frozen DUT snapshot; worker model and OSDI files hash-identical to the pinned ihp-sg13cmos5l 607e18d4 / ihp-sg13g2 5cccb161 install; duty 43.71-51.50 %, 31 of 300 below 45 % (original 30), all at -40 C; numbers differ from the original in the last digits and are not byte-identical.
