# ADDENDUM-004: RECORD-005 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #229, Part of #211 / #199). It does
not edit `RECORD-005-cascbias-real-cp-static-phase-error-rerun.md`. Contract:
`sim/README.md` "Provenance addenda". This addendum asserts nothing about
the original run's PDK revision, tool or host; it only replaces the evidence
claim with the measurement in `RECORD-011-cascbias-real-cp-rerun-pinned.md`,
which carries the dual-tree revisions, tool, host and command. The rerun
reproduced the RECORD-005 trace CSV byte-for-byte (nominal point only,
single Part B deck; no corner grid).

ADDENDUM-FOR: sg13cmos5l-closed-loop-lock/records/RECORD-005-cascbias-real-cp-static-phase-error-rerun.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 112d3a800b576be4c2392767f4c22cba8d3cc150178d352e32fd4d0d2aec890e
ADDENDUM-RERUN: sg13cmos5l-closed-loop-lock/records/RECORD-011-cascbias-real-cp-rerun-pinned.md
ADDENDUM-EVIDENCE: historical bench rebuilt from commit f54b9efb889c3693783c730d1d686874ee8b78b7 and run_closed_loop_cascbias.sh rerun unmodified at full duration (Part B 2.5 us, mos_tt/27 C/3.3 V, one nominal point); lock_trace_proposal_cascbias CSV byte-identical to the original.
