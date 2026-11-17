# ADDENDUM-001: RECORD-001 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #321, Part of #214 / #199). It does not edit `RECORD-001-rc-corner-momcap-sensitivity.md`. Contract: `sim/README.md` "Provenance addenda". It asserts nothing about the original run's host, ngspice build or PDK revision (not recorded; the original read `cornerRES.lib` and `r3_cmc.osdi` from the symlinked ihp-sg13g2 tree); it only replaces the evidence claim with the measurement in `RECORD-003-rc-corner-momcap-rerun-batch.md`, which carries the batch job ids, tool, command and PDK citation (cmos5l revision inferred `f7bca326`, not the README pin; limitation stated there). The rerun is NOT byte-identical: R1 differs by 0.15-0.90 % per row (PDK content), C1/C2 identical, nominal fz 12.06 MHz vs 12.07 MHz, MOM band alone x1.500 unchanged.

ADDENDUM-FOR: sg13cmos5l-loop-filter-momcap/records/RECORD-001-rc-corner-momcap-sensitivity.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 2c9eb20152a99dda9c4fc71db621bf42ee8e7806596bbf0703ef3cb8e9b5e364
ADDENDUM-RERUN: sg13cmos5l-loop-filter-momcap/records/RECORD-003-rc-corner-momcap-rerun-batch.md
ADDENDUM-EVIDENCE: historical DUT geometry rebuilt from the frozen snapshot and the unchanged extraction templates, full 27-row grid rerun on the klt batch fleet (probe klt-sim-ace9d0bf810c, grid klt-sim-c165c43bf163, ngspice-46); R1 differs by 0.15-0.90 % per row (PDK content), C1/C2 identical, nominal fz 12.06 MHz vs 12.07 MHz, MOM band alone x1.500 unchanged.
