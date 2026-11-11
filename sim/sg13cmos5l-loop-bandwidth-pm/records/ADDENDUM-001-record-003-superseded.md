# ADDENDUM-001: RECORD-003 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #320, child of #214, Part of #199,
item 9). It does not edit `RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`. Contract: `sim/README.md` "Provenance
addenda". RECORD-003 names no PDK revision; no contemporaneous evidence of its environment was recovered. This addendum asserts nothing about the original run's
environment; it replaces the evidence claim with the measurement in
`RECORD-006-issue83-close-gap-rerun-pinned.md`, which carries both PDK revisions, the tool versions, the batch job
ids and the exact commands.

ADDENDUM-FOR: sg13cmos5l-loop-bandwidth-pm/records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: b30578ffffb25e93d3461f77da3e3d87bedb334b9dd348986a12ac2d51d65fbf
ADDENDUM-RERUN: sg13cmos5l-loop-bandwidth-pm/records/RECORD-006-issue83-close-gap-rerun-pinned.md
ADDENDUM-EVIDENCE: one probe job (klt-sim-6ccf414a19e7) and one three-corner `klt sim --backend batch` job (klt-sim-8682d469bfe8) on the frozen loop_filter_resized snapshot; the slow-bundle 3.75 uA tuple still passes both criteria (fc 3.711740e+05 Hz, PM 51.751 deg) but does not reproduce RECORD-003's figures (3.592385e+05 Hz, 49.973 deg); Icp is the original input, not remeasured (#231).
