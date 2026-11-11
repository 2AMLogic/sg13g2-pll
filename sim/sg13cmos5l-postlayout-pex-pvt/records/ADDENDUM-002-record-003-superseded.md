# ADDENDUM-002: RECORD-003 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #325, Part of #215 / #211). It does not
edit `RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` or its CSVs.
Contract: `sim/README.md` "Provenance addenda". This addendum asserts nothing
about the original run's PDK revision, tool or host; it only replaces the
evidence claim with the measurement in
`RECORD-006-postlayout-pex-pvt-pfd-and-lock-detector-rerun.md`, which carries
the PDK evidence (including that the batch image's `ihp-sg13cmos5l` tree is not
the pinned checkout), tool, batch job ids and commands. The rerun reproduces
the schematic arm, the post-layout `reflead` rows, 101/102 window-control
points and the capacitor rows; it does not reproduce the post-layout `fblead`
mode inversion, the resistor extraction, the ladder classes or the window
deviation magnitude, and two single-deck controls on the pinned tree attribute
the first two to PDK content.

ADDENDUM-FOR: sg13cmos5l-postlayout-pex-pvt/records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: d46a1309738e46e6594d8080b3baef565ee33e25b4df2cab7b6aa4a01fe515c6
ADDENDUM-RERUN: sg13cmos5l-postlayout-pex-pvt/records/RECORD-006-postlayout-pex-pvt-pfd-and-lock-detector-rerun.md
ADDENDUM-EVIDENCE: historical bench rebuilt from commit 07751ca; run_pfd.sh and run_lock_detector.sh rerun unmodified through a deck-replay bridge as 6 klt sim decks requests (534 units) on the batch fleet; mixed reproduction, retained in full.
