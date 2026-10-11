# ADDENDUM-002: RECORD-003 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #227, Part of #211 / #199). It does
not edit `RECORD-003-pfd-reset-fix-closed-loop-rerun.md`. Contract:
`sim/README.md` "Provenance addenda". This addendum asserts nothing about
the original run's PDK revision, tool or host; it only replaces the evidence
claim with the measurement in `RECORD-009-pfd-reset-fix-closed-loop-rerun-pinned.md`,
which carries the dual-tree revisions, tool, host and command. The rerun
reproduced all four RECORD-003 result files byte-for-byte (Part A and Part B,
single PVT point only).

ADDENDUM-FOR: sg13cmos5l-closed-loop-lock/records/RECORD-003-pfd-reset-fix-closed-loop-rerun.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 94d6640b7a835affce1bb2acd5c773eeeb0da852fdb6812422f64eeda953a2e0
ADDENDUM-RERUN: sg13cmos5l-closed-loop-lock/records/RECORD-009-pfd-reset-fix-closed-loop-rerun-pinned.md
ADDENDUM-EVIDENCE: historical bench rebuilt from commit d633b9d5d33b2b403bc1fd43b449c5a1abdbd1db and run.sh rerun unmodified at full duration (Part A 500 ns, Part B 2.5 us, mos_tt/27 C/3.3 V); results_as_drawn, results_proposal, lock_trace_as_drawn and lock_trace_proposal CSVs byte-identical to the originals.
