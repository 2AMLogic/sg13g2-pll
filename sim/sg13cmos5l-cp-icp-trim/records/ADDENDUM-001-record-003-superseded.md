# ADDENDUM-001: RECORD-003 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #231, child of #212, Part of #199,
item 9). It does not edit `RECORD-003-issue83-finetrim-icp.md`. Contract:
`sim/README.md` "Provenance addenda". RECORD-003 names no worker and cites no
PDK revision, and no contemporaneous evidence of the producing session's
environment was recovered. This addendum asserts nothing about the original
run's environment. It replaces the evidence claim with the measurement in
`RECORD-006-issue83-finetrim-icp-rerun.md`, which carries the PDK revisions
found, tool versions, batch job id and command, and states its limitations.

ADDENDUM-FOR: sg13cmos5l-cp-icp-trim/records/RECORD-003-issue83-finetrim-icp.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 482d9e84eba0c6ad27f27dda98c7615f58f9292f7a6247b6da4fb6c9a74f2ba6
ADDENDUM-RERUN: sg13cmos5l-cp-icp-trim/records/RECORD-006-issue83-finetrim-icp-rerun.md
ADDENDUM-EVIDENCE: the 3.75 uA mos_ss/125C/3.3V three-state measurement rerun through klt sim on the batch fleet (job klt-sim-a6c59058e711, runner klt 0.9.0, ngspice-46) against the unchanged cp.spice snapshot; up/dn agree with RECORD-003 to 1e-6 relative, the both-state residual differs by 0.02%; no consumer figure changed.
