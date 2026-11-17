# ADDENDUM-002: RECORD-002 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #321, Part of #214 / #199). It does not edit `RECORD-002-r1-resize-momcap.md`. Contract: `sim/README.md` "Provenance addenda". It asserts nothing about the original run's host, ngspice build or PDK revision (not recorded; the original read `cornerRES.lib` and `r3_cmc.osdi` from the symlinked ihp-sg13g2 tree); it only replaces the evidence claim with the measurement in `RECORD-004-r1-resize-momcap-rerun-batch.md`, which carries the batch job ids, tool, command and PDK citation (cmos5l revision inferred `f7bca326`, not the README pin; limitation stated there). The rerun is NOT byte-identical: R1 differs by 0.99-6.25 % per row (PDK content), C1/C2 identical, nominal R1 347.6 kOhm vs 344.2 kOhm, full-PVT R1 spread wider; RECORD-002's 44.15x-44.18x scale claim does not reproduce.

ADDENDUM-FOR: sg13cmos5l-loop-filter-momcap/records/RECORD-002-r1-resize-momcap.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: b665252373aa13728bb5275c83566f816c544e200d3a5765d05a03a01019b15d
ADDENDUM-RERUN: sg13cmos5l-loop-filter-momcap/records/RECORD-004-r1-resize-momcap-rerun-batch.md
ADDENDUM-EVIDENCE: historical DUT geometry rebuilt from the frozen snapshot and the unchanged extraction templates, full 27-row grid rerun on the klt batch fleet (probe klt-sim-ace9d0bf810c, grid klt-sim-c165c43bf163, ngspice-46); R1 differs by 0.99-6.25 % per row (PDK content), C1/C2 identical, nominal R1 347.6 kOhm vs 344.2 kOhm, full-PVT R1 spread wider; RECORD-002's 44.15x-44.18x scale claim does not reproduce.
