# DR-012: Row 3 retiming closure is not reachable by `dff_tg_hv` width sizing alone

- **Status**: proposed
- **Date**: 2026-11-11
- **Decided by**: Builder agent, issue #189
- **Related**: #189, spec row 3, R-3, DR-001 (T1 items 8 and 9)
- **Evidence**: `sim/sg13cmos5l-divider-retiming-sizing/records/RECORD-001-xfrt-latch-sizing-sweep.md`

## Context

R-3 leaves two branches open: accept a lower top-of-band, or re-close the one-edge retiming at 1562.0 MHz
by a sizing campaign. RECORD-001 (this issue) ran the first part of that campaign.

## Decision

No spec change. Record that width sizing of the forward TGs, storage inverters, feedback and output
buffer of `dff_tg_hv` (8 variants incl. base) leaves the tt/27 and ff/-40 setup floor at 500 to 600 ps,
against a measured `t_arr` of 484.9 ps and a 640.2 ps period; only the ss/125 bracket improved
(1000-1500 to 600-700 ps). The sizing branch of R-3 is therefore not shown to close, and remains open
until a structural alternative is evaluated.

## Alternatives considered

- **Ratify a lower top-of-band now** — premature: this record is a partial campaign (no 9-corner retime of
  any resized variant), so it does not give the numeric bound ratifiers would need.
- **Continue width sizing only** — the data show no tt/ff sensitivity to it.

## Consequences

R-3 is unchanged. Follow-ups: retime the feedback-weakened variants at 9 corners; evaluate a structural
change (shorter ripple path, or an opposite-edge / pre-scaled retiming). Row 11's divider figure stays gated.
