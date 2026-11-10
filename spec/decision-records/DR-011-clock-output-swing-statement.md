# DR-011: State the `vco` output swing as single-ended per node, and record a downstream clock requirement as not assessed

- **Status**: proposed
- **Date**: 2026-11-10
- **Decided by**: Builder agent, issue #312
- **Related**: #312 (this issue), spec row 14 (output levels / drive), row 1
  (VCO band 445.3 to 1562.0 MHz), R-10, DR-001 (ring VCO, CMOS output)
- **Consumes**: issue #312 text (the consumer's figures, quoted as stated
  there); `2AMLogic/sg13g2-serdes` `spec/clock-requirement.md` (Level / load
  row; recorded by the issue's curator as a "Gap: 3.2x short" for this repo)
- **Evidence**: none. This record adds no simulation, schematic or number.

## Context

A downstream 10 Gb/s half-rate SerDes TX mux needs a 5.0 GHz clock at
>= 0.4 V per side (0.8 V differential peak-to-peak), centred near 0.6 V, into
a self-biased AC-coupled squarer. As stated in issue #312, in the consumer's
PVT sweep the mux output was not switched at the slow corner (ss, 1.08 V)
with 0.4 V per side, so the real need is higher. The consumer's
`DR-009-mux-clock-swing.md` was not read for this record; the figures above
are cited "as stated in issue #312", not as verified. Spec row 14 gave only
V_OH/V_OL into <= 50 fF without saying per node or differential, or which
interface it applies to.

## Decision

Statement-only change to row 14 of `spec/target-spec.md`:

1. Interface is the `vco` output buffer pin.
2. The swing is single-ended, per node, rail-referenced: V_OH >= 0.9 x VDD
   and V_OL <= 0.1 x VDD, i.e. 2.97 V / 0.33 V at 3.3 V.
3. Grading load is <= 50 fF, capacitive, DC-referenced.
4. No differential or common-mode figure is defined.
5. The consumer's requirement (0.4 V per side, ~0.6 V common mode,
   AC-coupled self-biased squarer, 5.0 GHz) is **not assessed**: the load
   model differs, and 5.0 GHz is outside the row 1 band. Row 14 has no
   testbench, so nothing is claimed as met.

No numeric bound is changed; the ported 0.9/0.1 bounds are not relaxed.
R-10 gains a pointer to this record.

## Alternatives considered

- **Add a differential/CML output spec** — the design has no such output; that
  is a design decision needing its own record and a testbench.
- **Run a swing testbench here** — out of scope for a statement; a separate
  issue if a ruling wants it.
- **Change the 445 to 1562 MHz band** — would relax or alter a ratified row;
  not this record's remit.

## Consequences

The consumer can read exactly what this repo does and does not state at its
output interface. The open question (consumer need above 0.4 V per side, slow
corner not switched) is recorded as input to a later ruling. Row 14 stays
without a measurement until a testbench exists, so it remains in R-10.
