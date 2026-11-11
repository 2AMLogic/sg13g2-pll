# ADDENDUM-002: RECORD-002 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #232, Part of #212 / #199). It does not
edit `RECORD-002-pdk-root-token-fix-reverification.md`. Contract: `sim/README.md`
"Provenance addenda". This addendum asserts nothing about the original run's
PDK revision, tool or host; it only replaces the evidence claim for the
measurements RECORD-002 reported with `RECORD-005-pdk-root-token-fix-rerun-pinned.md`,
which carries the PDK trees, tool, batch jobs and commands, and reports that
as-drawn `opconv` (still failing at 150 s in the original) and as-drawn
`retime` (all `NA` in the original) did not reproduce. It does not rerun
`run.sh`'s token-substitution fix itself.

ADDENDUM-FOR: sg13cmos5l-divider-nrange-retiming/records/RECORD-002-pdk-root-token-fix-reverification.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: ca8c08834a7e793e236bac70a6fc883809746ceae488e58c7b25cf193c862d4d
ADDENDUM-RERUN: sg13cmos5l-divider-nrange-retiming/records/RECORD-005-pdk-root-token-fix-rerun-pinned.md
ADDENDUM-EVIDENCE: opconv (4 rows) and hold (18 rows) rerun in full and the nominal-corner retime rows of both variants rerun through klt sim on the batch fleet; fbfix opconv, hold and the fbfix nominal retime figures reproduced, as-drawn opconv and retime did not; the other 16 retime rows were not rerun.
