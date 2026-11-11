# ADDENDUM-002: RECORD-004 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #231, child of #212, Part of #199,
item 9). It does not edit `RECORD-004-issue79-finetrim-icp.md`. Contract:
`sim/README.md` "Provenance addenda". RECORD-004 ran on arm64 macOS with
ngspice-47 and locally rebuilt `cap_cmom*` objects, names no PDK revision, and
no contemporaneous evidence of that environment was recovered. This addendum
asserts nothing about it. It replaces the evidence claim with the measurement
in `RECORD-007-issue79-finetrim-icp-rerun.md`, which discloses that the rerun
host (x86-64 Linux batch fleet) and tool (ngspice-46) differ.

ADDENDUM-FOR: sg13cmos5l-cp-icp-trim/records/RECORD-004-issue79-finetrim-icp.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 03110e5c6dd4763fbf1d3feb48e094171ff5d3d017c5636b3c54c01d191bcd73
ADDENDUM-RERUN: sg13cmos5l-cp-icp-trim/records/RECORD-007-issue79-finetrim-icp-rerun.md
ADDENDUM-EVIDENCE: the 11 uA three-PVT-point (ff/-40, tt/27, ss/125, 3.3V) three-state measurement rerun through klt sim on the batch fleet (jobs klt-sim-ee1f23ef4ca5, klt-sim-4b48acb43d7c, klt-sim-388e2d401518; runner klt 0.9.0, ngspice-46) against the unchanged cp.spice snapshot; up/dn agree with RECORD-004 to the last printed digit, both-state residuals differ by 0.02-0.03%; no consumer figure changed.
