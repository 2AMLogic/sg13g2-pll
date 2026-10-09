# sg13g2-hbt-characterization

Issue #181. Measurement-only bench: SG13G2 `npn13G2` output resistance (Ic-Vce) and mirror
matching at -40/27/125 C, compared with the `cp_leg_n` CMOS cascode leg, plus a `klt extract`
/ `klt lvs` probe on a minimal `npn13G2` cell. Layout follows `sim/README.md`
(`testbench/`, `requests/`, `corners/`, `records/`, `layout-probe/`). Records are append-only.
Start at `records/RECORD-001-npn13g2-ro-matching-vs-cmos-cascode.md`; verdict in
`spec/decision-records/DR-009-hbt-cascode-trigger-verdict.md`.
