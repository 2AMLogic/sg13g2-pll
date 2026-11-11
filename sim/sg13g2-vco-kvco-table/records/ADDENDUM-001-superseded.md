# ADDENDUM-001: RECORD-001 evidence claim superseded by a same-bench SG13G2 batch rerun

Append-only provenance addendum (issue #237, Part of #217 / #182). It does not
edit `RECORD-001-kvco-band-code-table.md`. Contract: `sim/README.md`
"Provenance addenda". This addendum asserts nothing about the original run's
PDK revision, tool or host (an arm64 macOS run, tree unknown); it only
replaces the evidence claim with the measurement in
`RECORD-002-kvco-band-code-table-rerun.md`, which carries the PDK revision,
tool, command, batch job ids and result scope.

ADDENDUM-FOR: sg13g2-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: a7efd9d0579ecfd3437b11e20820a088962c4b0017c67d81134c2d0e80e6abe5
ADDENDUM-RERUN: sg13g2-vco-kvco-table/records/RECORD-002-kvco-band-code-table-rerun.md
ADDENDUM-EVIDENCE: same-bench rerun of the full 60-run matrix (3 PVT bundles x 4 band codes x 5 VCTRL) on the batch fleet via klt sim decks request, job klt-sim-a102ccafc592; 60/60 units ran, 0 NA, all 60 periods byte-identical to RECORD-001's results.csv.
