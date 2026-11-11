# ADDENDUM-002: RECORD-003 schmitt_rewire evidence claim superseded by a batch-fleet rerun

Append-only provenance addendum (issue #329, child of #213, Part of #199, item 9). It does not
edit `RECORD-003-hysteresis-fix.md`. Contract: `sim/README.md` "Provenance addenda". This
addendum asserts nothing about the original run's environment; it replaces the evidence claim
for RECORD-003's `schmitt_rewire` grid with `RECORD-007-hysteresis-fix-rerun-pinned.md`, which
reruns it on the DUT at producing commit `a595772` through `klt sim` (probe job
klt-sim-5a775113a446, 12 grid jobs listed there). Scope: the as-drawn vs rewired hysteresis grid
(108 rows, both PDK arms) only. Three of four arms reproduce exactly; the cmos5l-rewired arm
differs by up to ~2 mV per trip point (disclosed in RECORD-007). Runner PDK revision is not
independently verified. No consumer was changed.

ADDENDUM-FOR: sg13cmos5l-lock-detector-window/records/RECORD-003-hysteresis-fix.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 78f0663d46e8bd5db7123225571905238019cfcf18f6d0b455471b4afba63a00
ADDENDUM-RERUN: sg13cmos5l-lock-detector-window/records/RECORD-007-hysteresis-fix-rerun-pinned.md
ADDENDUM-EVIDENCE: the schmitt_rewire grid (3 MOS corners x 3 temperatures x 3 supplies x as-drawn/rewired x ihp-sg13cmos5l/ihp-sg13g2, 108 rows) rerun as 12 klt sim batch requests on the Spot fleet (runner klt 0.9.0, ngspice-46) against netlists reconstructed from a595772; 3 of 4 arms identical to corners/schmitt_rewire.csv, cmos5l-rewired within 2.3 mV per trip point.
