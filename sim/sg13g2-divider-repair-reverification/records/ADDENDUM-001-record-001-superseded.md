# ADDENDUM-001: RECORD-001 evidence claim superseded by a same-bench SG13G2 batch rerun

Append-only provenance addendum (issue #235, child of #217, item 9). It does
not edit `RECORD-001-divider-repair-reverification.md`. Contract:
`sim/README.md` "Provenance addenda". RECORD-001 cites no PDK revision and
names no worker, and no contemporaneous evidence of its environment was
recovered. This addendum asserts nothing about the original run's environment.
It replaces the evidence claim with the measurement in
`RECORD-002-divider-repair-reverification-rerun-pinned.md`, which carries the
PDK revision (`ihp-sg13g2` 5cccb161), the tool versions, the batch job ids and
the exact commands.

Scope, stated plainly: the `opconv`, `hold` and `func` stages of RECORD-001,
re-measured at the original scope on the frozen `divider_chain_repaired.spice`
snapshot (unchanged). RECORD-001's transferred CMOS5L `setup`/`retime` evidence
is NOT re-measured and is excluded from the new claim (it stays a transferred,
non-fresh number; replacement is owed to #233). No existing consumer figure was re-pointed
because none was replaced (`characterization/sources.json` only lists RECORD-002).

ADDENDUM-FOR: sg13g2-divider-repair-reverification/records/RECORD-001-divider-repair-reverification.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 0834a8b9b4ed0527aaeea6675d3297d59765c271927773feb2530b42e90ebc40
ADDENDUM-RERUN: sg13g2-divider-repair-reverification/records/RECORD-002-divider-repair-reverification-rerun-pinned.md
ADDENDUM-EVIDENCE: the opconv/hold/func stages re-run as klt sim requests on the batch fleet (backend batch, 23 jobs, ngspice-46 on the runner, runner klt 0.9.0, client klt 0.9.2.dev661) against the unchanged frozen divider_chain_repaired.spice snapshot and ihp-sg13g2 5cccb161 (repo pin; the runner's PDK stamp was unreadable, so the fleet-side revision is not independently observed); every row shared with RECORD-001's CSVs reproduces to the printed 6 digits, division ratios exact, hold 9/9; the reltol=0.005 arm collapses (timestep too small), kept as failed corners; transferred CMOS5L setup/retime evidence is excluded, not re-measured.
