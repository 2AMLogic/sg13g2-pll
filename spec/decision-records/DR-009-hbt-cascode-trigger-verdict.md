# DR-009: DR-002 Decision 2 trigger (HBT charge-pump current source) is not met

- **Status**: proposed
- **Date**: 2026-10-09
- **Decided by**: Builder agent, issue #181
- **Related**: DR-002 (Decision 2 and its "Trigger to revisit" column; **not amended**),
  DR-006 `cp-cascode-bias-replica`, #181,
  `sim/sg13g2-hbt-characterization/records/RECORD-001-npn13g2-ro-matching-vs-cmos-cascode.md`

## Context

DR-002 Decision 2 keeps the CMOS wide-swing cascode as the charge-pump current-source
default and defers an HBT current mirror/cascode until "SG13G2's own device-characterization
campaign ... produces extracted `r_o`/matching data for an available HBT flavor showing a
real compliance-range or matching advantage over the CMOS wide-swing cascode at the
ratified Vctrl-headroom window". Issue #181 ran the first measurement against that trigger
(RECORD-001). This record only states whether the trigger is met. It adopts nothing and
changes neither DR-002's defaults nor the ratified spec nor `cp`.

## Decision

**The trigger is not met. DR-002 Decision 2 stands unchanged: CMOS wide-swing cascode by
default, HBT deferred.** Reasons, each traceable to RECORD-001:

1. **`r_o`: no advantage.** The single-device `npn13G2` mirror gives 8.4-9.8 Mohm at the
   10 uA code over 3 temperatures x 3 HBT process corners (-40/27/125 C; typ/bcs/wcs).
   The `cp_leg_n` CMOS cascode gives 39 Mohm (plateau) at the same code, at `mos_tt`/27 C
   (only corner exercised). The HBT is lower by roughly 4x at the one corner where both
   exist, and it falls as 1/Ic (0.26-0.42 Mohm at 80 uA vs 11.4 Mohm for the CMOS leg).
2. **Compliance: no demonstrated advantage over the window.** The HBT output holds its
   current down to Vce <= 0.3 V (a lower floor than the CMOS leg's 0.6 V at 10 uA), but
   the model card limits Vce to 1.6 V (`vce_max`), so a lone HBT does not cover the upper
   half of the 3.3 V compliance window that the CMOS leg covers to 3.0 V. Covering it would
   need a stacked CMOS device, a configuration that was not simulated. A lower floor with an
   unbridged ceiling is not a demonstrated "compliance-range advantage".
3. **Matching: no demonstrated advantage.** The PDK mismatch model gives about 13-16%
   1-sigma mirror-ratio spread (2.5-4.6 mV Vbe-equivalent) for Nx=1 across all nine corners.
   The CMOS leg's matching spread was **not exercised**, so no comparison can show an HBT
   advantage; the absolute figure is also model-only (`klt sim` flags bipolar mismatch for this
   PDK as "not independently verified") and independent of current by construction.
4. **"Extracted" cannot be satisfied yet.** `klt extract --deck sg13g2` recognises no
   bipolar device, and `klt lvs` can report a clean `match` for a zero-device layout against
   a subcircuit-call reference (upstream `2AMLogic/klayout-tools#2860`-`#2864`, new `#2952`).
   Layout-extracted `r_o`/matching for an HBT is therefore not obtainable.

What this does **not** establish: that an HBT cascode could never help. Open evidence, each
of which a later record may supply: (a) the CMOS leg over the same 9 corners and a matching
Monte Carlo (blocked on OSDI support on the batch runner, `#2570`/`#2901`, or a dedicated
simulation host); (b) an HBT in series with a thick-oxide CMOS cascode device so Vce stays
under 1.6 V; (c) an Nx sweep for matching.

## Alternatives considered

- **Declare the trigger met on the strength of the lower HBT saturation floor.** Rejected:
  the floor advantage is real in the model but is a few hundred mV of a 3 V window, and it
  comes with a worse `r_o` and an unaddressed Vce ceiling.
- **Declare the trigger "inconclusive".** Rejected as a verdict, kept as a caveat: for the
  `r_o` and compliance tests there is direct evidence against an advantage at the one
  corner where the CMOS leg was measured; the corners not exercised are named above. A
  later record can supersede this one if the full CMOS grid reverses the picture.
- **Run the CMOS grid locally to complete the comparison.** Rejected: host rules reserve
  corner grids for the batch fleet, and the batch runner cannot run PSP103 decks today.

## Consequences

- No design change. `cp` and DR-002 are untouched; no HBT appears in any schematic.
- The CMOS corner/MC comparison is owed and is a follow-up; it should be re-requested
  through `klt sim` once the batch runner can load OSDI models. That follow-up, not a
  redesign, is what would let this verdict be revisited (by a new DR that supersedes this one).
- Any later bipolar work in this repo has no working extract/LVS path until the upstream
  gaps close; its LVS status must be read together with device counts, not alone.
- DR numbering: DR-009 was the next unused number on `main` when written; renumber if
  another record claims it before merge (per `TEMPLATE.md`).
