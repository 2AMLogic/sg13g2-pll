# ADDENDUM-001: RECORD-001 evidence claim superseded by a fleet rerun

Append-only provenance addendum (issue #316, child of #216, Part of #199,
item 9). It does not edit `RECORD-001-decap-momcap-sensitivity.md`.
Contract: `sim/README.md` "Provenance addenda". RECORD-001 cites only an
install path and `ngspice-46`, and no evidence of the producing session's
environment was recovered, so this addendum asserts nothing about the original
run's environment. It replaces the evidence claim with the measurement in
`RECORD-002-decap-momcap-rerun-batch.md` (`klt sim` batch fleet, jobs
`klt-sim-8e4c1fe9b4c9`, `-a5ffddb2be39`, `-8634a70f2bc0`, `-345808b50bc8`),
which states its PDK revisions, tool version, command and limitations,
including that the worker's own model-card revision is not proven.

ADDENDUM-FOR: sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 2f1bef8c489476c641d82f6467506f67a6107d5bcaa1ffc376c4f4407a18a5cd
ADDENDUM-RERUN: sg13cmos5l-vco-decap-momcap/records/RECORD-002-decap-momcap-rerun-batch.md
ADDENDUM-EVIDENCE: the full RECORD-001 grid (3 temperature extractions, 3 MOM-fraction pole sweeps, R_src 3000 ohm illustrative) rerun as four klt sim requests on the batch fleet (ngspice-46, models.pdk ihp-sg13cmos5l, wait-for-capacity 600); C_decap reproduces at 5.28617 pF and the poles within 0.16%; the -3 dB crossing method differs and the as-run cdecap_f sign error are disclosed in RECORD-002.
