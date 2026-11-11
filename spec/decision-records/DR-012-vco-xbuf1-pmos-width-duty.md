# DR-012: Narrow the first `vco` output-buffer PMOS to 8.5u to meet the row 13 duty-cycle bound

- **Status**: proposed
- **Date**: 2026-11-11
- **Decided by**: Builder agent, issue #188 (ratification pending)
- **Related**: #188, spec row 13, R-8, row 1, row 11, `sg13cmos5l-vco-duty-cycle`
  RECORD-001, RECORD-002, RECORD-003
- **Evidence**: `sim/sg13cmos5l-vco-duty-cycle/records/RECORD-003-xbuf1-pmos-resize-duty-closure.md`

## Context

Row 13's ported bound is 45 to 55 % duty. RECORD-001 measured 43.74 to
51.56 % (30 of 300 below 45 %), and RECORD-002's fleet rerun 43.71 to 51.50 %
(31 of 300), all at -40 C. R-8 asks for a redesign or a ratified deviation; the
bound is not relaxed here. This record takes the redesign branch.

## Decision

In `design/sg13cmos5l/vco.sch`, replace `XBUF1` (`inv2x_hv`, P 10u / N 4u) with
discrete `MBP1` (`sg13_hv_pmos`, w 8.5u, l 0.5u) and `MBN1` (`sg13_hv_nmos`,
w 4u, l 0.5u). `XBUF2` and the shared `inv2x_hv` cell are unchanged. The spec
bound stays 45 to 55 %. RECORD-003 shows 46.02 to 53.87 % over the same 300
points (0 below 45 %, 0 above 55 %).

## Alternatives considered

- **Ratified deviation of the -40 C floor** (R-8's other branch): relaxes a
  ported spec row; not chosen, and not an agent's call.
- **Widen XBUF1's NMOS or change `inv2x_hv` itself**: the cell is shared with the
  `pfd`, so editing it changes a block this issue does not cover.
- **A duty-correcting stage**: more devices and a layout cost for an effect
  one width achieves; not tried.
- **P width 7u or 8u**: 7u puts `mos_ff`/125 C above 55 % (56.98 %, single
  probe); 8u leaves 0.23 pp to 55 % at that point. 8.5u balances the two ends.

## Consequences

- Row 13 is met on the 300-point grid with about 1 pp of margin at each end;
  that margin is thin and does not cover post-layout skew or mismatch.
- Row 1's period-derived frequency range moves about +2 to +3 % (RECORD-003);
  the Kvco band table was not rerun and must be before it is cited with this
  buffer.
- The `vco` layout (`layout/sg13cmos5l-pll/`) and its LVS reference are
  stale: `XBUF1` is now two discrete devices. Follow-up owed, not done here.
- The netlist gate (`netlist.yml`) was not confirmed locally; see RECORD-003.
- The 8.5u width is a single-parameter choice, not an optimum.
