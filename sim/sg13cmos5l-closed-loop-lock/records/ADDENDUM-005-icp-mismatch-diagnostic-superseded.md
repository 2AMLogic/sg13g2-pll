# ADDENDUM-005: RECORD-004 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #228, Part of #211 / #199). It does
not edit `RECORD-004-icp-mismatch-phase-error-diagnostic.md`. Contract:
`sim/README.md` "Provenance addenda". This addendum asserts nothing about
the original run's PDK revision, tool or host (arm64 macOS, ngspice-47,
unrecorded tree); it only replaces the evidence claim with the measurement
in `RECORD-012-icp-mismatch-diagnostic-rerun-pinned.md`, which carries the
dual-tree revisions, tool, host and command. The rerun reproduced
RECORD-004's outcome and its cited run-length quantities exactly -- static
phase error collapsed to simulator noise (final-20-cycle mean -0.00044%
vs. the original's -0.00235%, both against the 9.176% RECORD-003
baseline), 41-cycle continuous dual-lock run from 450 ns to the end of the
2.45 us window with zero drop-outs, `lock_time` 450 ns, `i_cp` = 0. It is
NOT byte-identical (different host, arch and ngspice build); the numeric
differences are at the 1e-5..1e-4-of-`T_ref` noise level and are tabulated
in the rerun record. Single PVT point, Part B proposal deck with the ideal
exactly-symmetric `cp` substitution only.

ADDENDUM-FOR: sg13cmos5l-closed-loop-lock/records/RECORD-004-icp-mismatch-phase-error-diagnostic.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 03580e2668bdb7f547845fdbefd2eb8d5303f3eded0a58e40bee228c108b0375
ADDENDUM-RERUN: sg13cmos5l-closed-loop-lock/records/RECORD-012-icp-mismatch-diagnostic-rerun-pinned.md
ADDENDUM-EVIDENCE: historical bench rebuilt from commit f38b0ee and the icp-eq diagnostic (run_closed_loop_icp_eq_diag.sh) rerun unmodified at full duration (2.5 us, mos_tt/27 C/3.3 V, 49 reference cycles) on the pinned dual-tree PDK; the confirmed-mechanism outcome reproduced exactly (collapse to noise, 41-cycle dual-lock run, lock_time 450 ns) but the trace is not byte-identical (different host, arch and ngspice build).
