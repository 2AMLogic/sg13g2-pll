# ADDENDUM-001: RECORD-002 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #324, Part of #215 / #199). It does
not edit `RECORD-002-floorplan-aware-vco-route.md`. Contract: `sim/README.md`
"Provenance addenda". This addendum asserts nothing about the original run's
PDK revision, tool or host ("worker not named", `~/share/pdk`, ngspice-46);
it only replaces the evidence claim with the measurement in
`RECORD-005-floorplan-aware-vco-route-rerun-pinned.md`, which carries the
dual-tree revisions, tools, hosts, commands and the batch job ids. The rerun
reproduced the layout (all GDS byte-identical), the extracted VCO netlist
(byte-identical), the 120-row Matrix A grid (identical to printing
precision), the 210-row RC attribution grid (max 0.098%) and the LVS-recheck
verdict shape. Item 9 stays unmet.

ADDENDUM-FOR: sg13cmos5l-postlayout-pex-pvt/records/RECORD-002-floorplan-aware-vco-route.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 79a7c066cac4e00550694c266c10aa1cbe2450563d43394a70424f5966fc1630
ADDENDUM-RERUN: sg13cmos5l-postlayout-pex-pvt/records/RECORD-005-floorplan-aware-vco-route-rerun-pinned.md
ADDENDUM-EVIDENCE: layout flow rerun at ff8b653 (GDS byte-identical), PEX with klt 729ee531e176 (pll_vco.pex.spice byte-identical), Matrix A and RC-attribution grids rerun as 27 klt sim batch requests (330 units, all pass; 33 batch jobs listed in corners/rerun-324/jobs.json) with the pinned dual-tree model cards staged, LVS recheck rerun; results reproduce the original CSVs to printing precision (Matrix A) and 0.098 percent (RC attribution); not byte-identical text, different host and OSDI build.
