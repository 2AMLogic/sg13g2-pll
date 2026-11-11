# ADDENDUM-002: RECORD-001 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #232, Part of #212 / #199). It does not
edit `RECORD-001-nrange-retiming-margin.md`. Contract: `sim/README.md`
"Provenance addenda". This addendum asserts nothing about the original run's
PDK revision, tool or host; it only replaces the evidence claim with the
measurements in `RECORD-005-nrange-retiming-margin-rerun-pinned.md`, which
carries the PDK trees, tool, batch jobs and commands, and reports where the
rerun did not reproduce the original (the `opconv` non-convergence, the
as-drawn "dead chain" state, and the `retime` `NA`s) and which corners it does
not cover (baseline and retime are nominal only).

ADDENDUM-FOR: sg13cmos5l-divider-nrange-retiming/records/RECORD-001-nrange-retiming-margin.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: e50fce4402c5db2ebb83cbc8417216288f3ca65cfc5677d828ce7b11a9a69e6d
ADDENDUM-RERUN: sg13cmos5l-divider-nrange-retiming/records/RECORD-005-nrange-retiming-margin-rerun-pinned.md
ADDENDUM-EVIDENCE: pre-repair divider_chain (as-drawn and fbfix variants, snapshot byte-identical at 1d824d3) rerun through klt sim on the batch fleet; hold (18 rows), setup (36) and opconv (4) full, func baseline and retime at the nominal corner only; hold, setup and fbfix N=64.00 reproduced, as-drawn opconv non-convergence and dead-chain state not reproduced.
