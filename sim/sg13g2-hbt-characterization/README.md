# sg13g2-hbt-characterization

Issue #181. Measurement-only bench: SG13G2 `npn13G2` output resistance (Ic-Vce) and mirror
matching at -40/27/125 C, compared with the `cp_leg_n` CMOS cascode leg, plus a `klt extract`
/ `klt lvs` probe on a minimal `npn13G2` cell. Layout follows `sim/README.md`
(`testbench/`, `requests/`, `corners/`, `records/`, `layout-probe/`). Records are append-only.
Start at `records/RECORD-001-npn13g2-ro-matching-vs-cmos-cascode.md`; verdict in
`spec/decision-records/DR-009-hbt-cascode-trigger-verdict.md`.

Note on `requests/`: `cmos_ro.request.json` and `cmos_mm.request.json` are committed as
evidence of what was submitted, but both batch jobs **failed** (PSP103 is OSDI-only and the
batch runner had no OSDI objects; see RECORD-001). They produced no data. The only CMOS
numbers come from `cmos_ro_nominal.request.json`, one local corner (`mos_tt` / 27 C).
