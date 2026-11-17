# ADDENDUM-001: RECORD-003 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #233, child of #212, Part of #199,
item 9). It does not edit `RECORD-003-divider-repair-reverification.md`.
Contract: `sim/README.md` "Provenance addenda". RECORD-003 names no worker
and no PDK revision, and no contemporaneous evidence of the producing
session's environment was recovered. This addendum asserts nothing about the
original run's environment. It replaces the evidence claim with the
measurement in `RECORD-004-divider-repair-reverification-rerun-pinned.md`,
which carries the PDK pins and exactly what was verified about the worker's
copy, the tool versions, the batch job ids and the commands.

Scope is stated plainly: all five RECORD-003 stages (`opconv`, `hold`,
`setup`, `func`, `retime`) on the DUT snapshot that is byte-identical to the
producing revision (`a95a887`), with RECORD-003's own reduced matrices. No
logic outcome differs; analog values differ only in the last printed digit.
The two `reltol = 5e-3` arms fail as RECORD-003 Finding 2 describes. This
does not widen RECORD-003's coverage, does not touch RECORD-001/RECORD-002
(the broken as-committed DUT, which remain grandfathered), and changes no
consumer.

ADDENDUM-FOR: sg13cmos5l-divider-nrange-retiming/records/RECORD-003-divider-repair-reverification.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 5812315e4dfd1f466bf4774cced691aa8f8d9b5dc23cf8c5fc2ed7072c9458a4
ADDENDUM-RERUN: sg13cmos5l-divider-nrange-retiming/records/RECORD-004-divider-repair-reverification-rerun-pinned.md
ADDENDUM-EVIDENCE: all five stages rerun as 76 pre-composed decks rendered by testbench/gen_rerun233_requests.py from run.sh's own templates and matrices, on the klt batch fleet (ngspice-46, runner klt 0.9.0, jobs klt-sim-a78e8e3b623f, klt-sim-83c2aa507d64, klt-sim-83279cacd753, klt-sim-54b56d42f020, klt-sim-c38ff179299b) against the DUT snapshot byte-identical to producing revision a95a887; the worker's PSP103/PSP103-NQS/mosvar OSDI objects and cornerMOShv.lib are sha256-identical to the pinned ihp-sg13cmos5l 607e18d4 / ihp-sg13g2 5cccb161 trees (the worker exposes no git revision); 20/20 divide ratios exact, 9/9 hold, 7/9 retime resolved as originally, reltol 5e-3 arms fail as originally.
