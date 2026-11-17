# ADDENDUM-004: RECORD-004 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #326, Part of #215 / #211). It does not
edit `RECORD-004-postlayout-pex-pvt-loop-filter-and-divider-chain.md` or its
CSVs. Contract: `sim/README.md` "Provenance addenda". This addendum asserts
nothing about the original run's PDK revision, tool or host; it only replaces
the evidence claim with the measurement in
`RECORD-008-postlayout-pex-pvt-loop-filter-and-divider-chain-rerun.md`, which
carries the PDK evidence (including that the batch image's `ihp-sg13cmos5l`
tree is not the pinned checkout), tool, batch job ids and commands. The rerun
reproduces the divider-chain division ratio on all 36 rows and the loop
filter's capacitances and post-layout/schematic deviations; it does not
reproduce the loop filter's absolute `R1` (-3.6 % to +6.0 % by resistor
corner), and a single-deck control on the pinned tree attributes that to PDK
content.

ADDENDUM-FOR: sg13cmos5l-postlayout-pex-pvt/records/RECORD-004-postlayout-pex-pvt-loop-filter-and-divider-chain.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: f2642e6134182c4de7f4a41d7501b552c9514b48b8d94944fdb7949ecd99304a
ADDENDUM-RERUN: sg13cmos5l-postlayout-pex-pvt/records/RECORD-008-postlayout-pex-pvt-loop-filter-and-divider-chain-rerun.md
ADDENDUM-EVIDENCE: historical bench rebuilt from commit bd62f15; run_loop_filter.sh and run_divider_chain.sh rerun unmodified through a deck-replay bridge as 54 klt sim decks units (18 loop filter, 36 divider chain) on the batch fleet; mixed reproduction, retained in full.
