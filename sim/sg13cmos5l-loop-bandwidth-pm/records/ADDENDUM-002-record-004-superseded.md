# ADDENDUM-002: RECORD-004 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #320, child of #214, Part of #199,
item 9). It does not edit `RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`. Contract: `sim/README.md` "Provenance
addenda". RECORD-004 was produced on an arm64 macOS host with a locally rebuilt `cap_cmom*` OSDI and names no PDK revision; its host and tree are unknown and are not reproduced by the rerun. This addendum asserts nothing about the original run's
environment; it replaces the evidence claim with the measurement in
`RECORD-007-issue79-close-gap-rerun-pinned.md`, which carries both PDK revisions, the tool versions, the batch job
ids and the exact commands.

ADDENDUM-FOR: sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 372d1e4c99234dfa7357c6e608b95d6dc130461109f58a0400465d997785f060
ADDENDUM-RERUN: sg13cmos5l-loop-bandwidth-pm/records/RECORD-007-issue79-close-gap-rerun-pinned.md
ADDENDUM-EVIDENCE: same batch jobs (klt-sim-6ccf414a19e7 probe, klt-sim-8682d469bfe8); the 11 uA code does NOT reproduce RECORD-004's all-bundle pass: fast PM 44.345 deg (< 45) and slow fc 4.519310e+05 Hz (> 450 kHz), typ passes; RECORD-004 was produced on an arm64 macOS host with locally rebuilt OSDI objects of unknown tree, so the original environment is not reproduced; Icp is the original input, not remeasured (#231).
