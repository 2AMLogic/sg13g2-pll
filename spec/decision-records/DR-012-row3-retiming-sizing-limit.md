# DR-012: Row 3 retiming closure is not reachable by `dff_tg_hv` width sizing alone

- **Status**: proposed
- **Date**: 2026-11-11
- **Decided by**: Builder agent, issue #189
- **Related**: #189, #362, spec row 3, R-3, DR-001 (T1 items 8 and 9)
- **Evidence**: `sim/sg13cmos5l-divider-retiming-sizing/records/RECORD-001-xfrt-latch-sizing-sweep.md`, `sim/sg13cmos5l-divider-retiming-sizing/records/RECORD-002-retime-and-structural.md`, `sim/sg13cmos5l-divider-retiming-sizing/records/RECORD-003-capture-edge-waveform.md`

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

## Update (RECORD-002, issue #189 remaining increment)

Still proposed; spec unchanged. RECORD-002 retimed the feedback-weakened variants at the resolved corners
(N=64 and N=127) and evaluated one structural alternative (opposite-edge retiming of `XFRT`). Findings:

- Width sizing leaves the deck-arithmetic closing bound at 822 to 852 MHz at the worst resolved corner
  (tt/-40 C); 918 to 922 MHz at tt/27 C.
- Opposite-edge retiming raises it to 1301 MHz (tt/-40 C) and 1332 MHz (tt/27 C), still below 1562.0 MHz,
  and it does not give a single capture edge (k+0.5 vs k+1.5 depending on arrival).
- At ss/27 C and tt/125 C the divider core stops dividing between 1400 and 1562 MHz in every variant, so
  no `XFRT` change can reach 1562.0 MHz there; that needs chain-stage sizing.
- The in-situ `tfb - tdiv` data are consistent with next-edge (k+1) capture, not the one-period-late
  reading of RECORD-003, and conflict with the isolated setup deck. Unresolved.

Consequence: ratifiers should not choose a lower top-of-band from the 825 to 1277 MHz figures until a
waveform-level check of the in-situ capture edge is done. Layout and spec untouched.

## Update (RECORD-003, issue #362: the Finding 4 waveform check)

Still proposed; spec unchanged. RECORD-003 saved the `XFRT` D, CK, Q and internal nodes for the base chain at
1562 MHz, N=64, tt/27 C and tt/-40 C only (batch `wrdata`). Result:

- The rising `DIVOUT` edge is captured at the next CK edge (k+1) with a stretched clk->Q of 451 ps (tt/27 C)
  and 387 ps (tt/-40 C); the k+2 reading of nrange RECORD-003 Finding 4 is excluded for the rising edge.
- The falling `DIVOUT` edge is captured one period later (k+2): the first CK edge gives a marginal master
  capture that recovers; the retimed `FB` falls 1251 ps (tt/27 C) / 1122 ps (tt/-40 C) after `DIVOUT`,
  about one `T_vco` more than the rising delay, so the retimed output is duty-distorted at 1562 MHz.
- The isolated setup deck disagrees because it scores a capture only when `Q` is correct within T/4 (160 ps);
  the in-situ captures resolve in 387 to 488 ps. The 500 to 600 ps bracket bounds fast clk->Q, not logical
  correctness. Not reproduced in an isolated deck.

Consequence: the 825 to 1277 MHz deck-arithmetic figures are not a logical-failure bound and should not be
used alone to pick a lower top-of-band; whether duty-distorted, k+1/k+2 retiming at 1562.0 MHz is acceptable is
a ratification question, with the other seven corners' waveforms still missing. R-3 is unchanged.
