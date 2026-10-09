# Corner matrix: `sg13g2-hbt-characterization`

**Claim under test**: DR-002 Decision 2's deferral trigger ("extracted `r_o`/matching
data showing an HBT current source clears the ratified Vctrl-headroom floor with a
real compliance-range or matching advantage over the CMOS cascode"). Measurement
only; nothing is adopted.

| Axis | HBT `r_o` bench | HBT mismatch bench | CMOS leg bench |
|---|---|---|---|
| Process | `hbt_typ`, `hbt_bcs`, `hbt_wcs` (`cornerHBT.lib`) | `hbt_{typ,bcs,wcs}_mismatch` | `mos_tt` only (local probe). `mos_ss`/`mos_ff` + MC: **not exercised** |
| Temperature | -40, 27, 125 C (full cross with process = 9 corners) | same, x 50 MC samples = 450 runs | 27 C only. -40/125: **not exercised** |
| Supply | n/a (ideal sources) | n/a | 3.3 V nominal only; 3.0/3.6 V **not exercised** |
| Bias | Iref = 2.5 / 10 / 80 uA (dc sweep of `Iref`, measured at those points) | same | same |
| Vce / Vout | 0.3, 0.6, 0.9, 1.2, 1.5 V (npn13G2 `vce_max` = 1.6 V in the model card) | 0.9 V | 0.3 ... 3.0 V in 0.3 V steps |
| MC | none | `monte_carlo {n: 50, seed: 181, vary: mismatch}` | none run |

Bundles are crossed (3 x 3), not correlated, because `cornerHBT.lib` corner is
independent of any MOS corner in the HBT bench (no MOS device in it).

Backend: `batch` (Spot fleet) for both HBT benches; `local` single-corner for the
CMOS nominal probe. The CMOS grids were submitted to batch and failed (runner has
no OSDI objects); see RECORD-001.
