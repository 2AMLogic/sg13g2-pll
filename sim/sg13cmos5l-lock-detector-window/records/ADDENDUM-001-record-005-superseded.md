# ADDENDUM-001: RECORD-005 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #256, child of #213, Part of #199,
item 9). It does not edit `RECORD-005-rpu-body-on-vss.md`. Contract:
`sim/README.md` "Provenance addenda". RECORD-005 names no worker and cites
no PDK revision, and no contemporaneous evidence of the producing session's
environment was recovered. This addendum asserts nothing about the original
run's environment. It replaces the evidence claim with the measurement in
`RECORD-006-rpu-body-on-vss-rerun-pinned.md`, which carries both PDK
revisions (`ihp-sg13cmos5l` 607e18d4, `ihp-sg13g2` 5cccb161), the tool
versions, host and exact command.

Scope is stated plainly and unchanged: one nominal corner (mos_tt /
res_typ / 27 °C / 3.3 V) of the bodyfix DUT snapshot, which is
byte-identical to the producing revision (`3fd7967`); every one of the
seven output files reproduces RECORD-005's committed
`corners/*_bodyfix_nominal.*` set byte for byte. This does NOT satisfy the
owed full-PVT grid (#139), does not touch RECORD-001..004, the PEX record
(#157) or the SG13G2 campaign, and changes no consumer: no figure anywhere
was replaced, so no citation needed re-pointing.

ADDENDUM-FOR: sg13cmos5l-lock-detector-window/records/RECORD-005-rpu-body-on-vss.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 15313f19b3bb3d73e0ef5f9687eb0a016901f58fb578d7f79e6821a93ffa03a6
ADDENDUM-RERUN: sg13cmos5l-lock-detector-window/records/RECORD-006-rpu-body-on-vss-rerun-pinned.md
ADDENDUM-EVIDENCE: the nominal single-corner campaign rerun through run_rerun256.sh (run.sh with the output suffix changed only) on loom-worker-3 with ngspice-46, klt 0.7.1.dev256 and the pinned dual-tree PDK (ihp-sg13cmos5l 607e18d4, ihp-sg13g2 5cccb161), against the DUT snapshot byte-identical to producing revision 3fd7967; all seven outputs (rc_extract 3 rows, window, schmitt, ladder, ladder_raw 21 rows, tstep_convergence, solver_retries empty) reproduce RECORD-005's committed files byte-identically; nominal only, full-PVT grid still owed as #139.
