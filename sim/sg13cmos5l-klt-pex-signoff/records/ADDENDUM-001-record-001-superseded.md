# ADDENDUM-001: RECORD-001 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #255, child of #213, Part of #199). It
does not edit `RECORD-001-klt-pex-nominal-envelopes.md`. Contract:
`sim/README.md` "Provenance addenda". RECORD-001's envelopes record
`pdk.version: null`, name no host, and were made with klt 0.6.0; no
contemporaneous evidence of the producing session's PDK revisions was
recovered. This addendum asserts nothing about the original run's
environment. It replaces the evidence claim with the measurement in
`RECORD-003-klt-pex-nominal-rerun-pinned.md`, which carries both PDK
revisions (`ihp-sg13cmos5l` 607e18d4, `ihp-sg13g2` 5cccb161), the tool
versions, host and exact command.

Scope is stated plainly. All five blocks (`pfd`, `cp`, `loop_filter`, `vco`,
`divider_chain`) were rerun at the single nominal corner on the reconstructed
original inputs (layout record `20261003-183059-dc5644a`; dut/requests from
commit `e56e14a`); every delta reproduces RECORD-001. This does NOT make the
current PEX evidence (`reports/pex.*.json`, layout `20261010-012952-a4ca1b8`,
RECORD-002) or whole-design sign-off current, and it does not touch
RECORD-002, `lock_detector` or any PVT grid. One failed attempt (ngspice-42
refuses the OSDI objects) is retained in the rerun record.

ADDENDUM-FOR: sg13cmos5l-klt-pex-signoff/records/RECORD-001-klt-pex-nominal-envelopes.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 6d27e42d100ebda96fb297222d1ab6a3b8debbada9d5cd65f002bdb403108eee
ADDENDUM-RERUN: sg13cmos5l-klt-pex-signoff/records/RECORD-003-klt-pex-nominal-rerun-pinned.md
ADDENDUM-EVIDENCE: all five blocks of the nominal klt pex flow rerun with klt 0.7.1.dev228 and ngspice-46 on the pinned dual-tree PDK against the original layout record and the e56e14a inputs; every extracted value and delta reproduces RECORD-001 (pfd +77.848/+9.251 %, cp +0.173/-0.051 %, loop_filter +29.646 %, vco +151.008 %, divider_chain -0.002/0.0 %); old-layout nominal diagnostics only, current PEX not refreshed.
