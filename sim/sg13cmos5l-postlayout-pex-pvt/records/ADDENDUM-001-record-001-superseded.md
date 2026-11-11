# ADDENDUM-001: RECORD-001 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #323, Part of #215 / #211). It does not
edit `RECORD-001-postlayout-pex-pvt-vco-and-cp.md` or its CSVs. Contract:
`sim/README.md` "Provenance addenda". This addendum asserts nothing about the
original run's PDK revision, tool or host; it only replaces the evidence claim
with the measurement in `RECORD-005-postlayout-pex-pvt-vco-and-cp-rerun.md`,
which carries the PDK revisions (and what could not be verified), tool, batch
job ids and commands. The rerun reproduces the headline vco result, the cp
`up`/`dn` rows and the RC attribution to within ~3 %, and does not reproduce
the cp `both`-state rows. It also records that the base `corners/results.csv`
and `corners/rc_attribution.csv` are no longer the `d5355e1` values.

ADDENDUM-FOR: sg13cmos5l-postlayout-pex-pvt/records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 237f4a0e7f7cf410e9413d323fd826ae6063aaa3b773bb280c743dab3ca26b12
ADDENDUM-RERUN: sg13cmos5l-postlayout-pex-pvt/records/RECORD-005-postlayout-pex-pvt-vco-and-cp-rerun.md
ADDENDUM-EVIDENCE: historical layout record 20260830-204105-457cf5b and testbench rebuilt from commit d5355e1, re-extracted and the vco (120), cp (612) and RC-attribution (210) matrices rerun unmodified apart from the disclosed cp operating-point method, as 21 klt sim requests on the batch fleet; vco ratio and RC attribution reproduce, cp both-state rows do not.
