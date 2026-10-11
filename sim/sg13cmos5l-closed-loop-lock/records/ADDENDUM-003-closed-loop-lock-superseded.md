# ADDENDUM-003: RECORD-001 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #225, Part of #211 / #199). It does
not edit `RECORD-001-closed-loop-lock-spur-power.md`. Contract:
`sim/README.md` "Provenance addenda". This addendum asserts nothing about
the original run's PDK revision, tool or host (arm64 macOS, ngspice-47,
unrecorded tree); it only replaces the evidence claim with the measurement in
`RECORD-010-closed-loop-lock-rerun-pinned.md`, which carries the dual-tree
revisions, tool, host and command. The rerun reproduced RECORD-001's
qualitative outcome and every quantity it cites to within about 1 percent
(spur figure 0.06 dB), but it is NOT byte-identical (different host, arch and
ngspice build); the small differences are tabulated in the rerun record. Part
A and Part B, single PVT point only.

ADDENDUM-FOR: sg13cmos5l-closed-loop-lock/records/RECORD-001-closed-loop-lock-spur-power.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 9e8dab1b61f6e4d0813f7dce3e27ba898d203d16dc45aec2c0504eeb1f0868c6
ADDENDUM-RERUN: sg13cmos5l-closed-loop-lock/records/RECORD-010-closed-loop-lock-rerun-pinned.md
ADDENDUM-EVIDENCE: historical bench rebuilt from commit 1da08d7 and run.sh rerun unmodified at full duration (Part A 500 ns, Part B 2.5 us, mos_tt/27 C/3.3 V) on the pinned dual-tree PDK; results_as_drawn, results_proposal and lock_trace_proposal differ numerically from the originals (not byte-identical) but reproduce the outcome: Part A fb never toggles, lock_time None; Part B 49 cycles, delta_f/f_ref drifting -0.8 percent to -22.9 percent, lock_time None.
