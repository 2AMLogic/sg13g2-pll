# Corner matrix — `sg13cmos5l-loop-bandwidth-pm`

**Claim under test**: `spec/porting-plan.md` row 6/6a — the loop's own
unity-gain crossover `f_c` and phase margin, against the two stability
criteria that row carries over as-is (`f_c < f_ref/10`, PM ≥ 45°). Both
sibling records that touch this row
(`sg13cmos5l-loop-filter-momcap/records/RECORD-001` and
`sg13cmos5l-vco-kvco-table/records/RECORD-001`) mark it
`insufficient-evidence` pending exactly this combination; this record
supplies it.

## Axes

| Axis | Values | Why |
|---|---|---|
| PVT bundle | `typ` (`res_typ`, 27 C), `slow` (`res_wcs`, 125 C), `fast` (`res_bcs`, −40 C) | Identical to the `sg13cmos5l-vco-kvco-table` record's own 3-bundle convention, deliberately: the `Kvco` term and the filter's `R1` term must never be taken from mismatched corners. The `Icp` term is read from the matching MOS corner of `sg13cmos5l-cp-icp-trim` (`mos_tt`/`mos_ss`/`mos_ff` at the same temperature) |
| Band code | `00` (lowest `Kvco`) and `11` (highest) | The two extremes of the measured Kvco-vs-band table; the intermediate `10`/`01` codes lie between them and add no new bound |
| `Kvco` interval | `mid` (0.9 → 1.5 V secant) and `top` (2.1 → 2.7 V secant) | The Kvco record's own finding is that Kvco is measurably non-constant across `VCTRL`; a single scalar would misstate loop gain, so both a mid-range and a top-of-range local slope are carried through, each with the VCO frequency it belongs to |
| `f_ref` | 25 MHz and 10 MHz | `spec/porting-plan.md` row 2 carries a 1–25 MHz reference interface. A scenario is generated only when the required `N = f_VCO/f_ref` lands inside row 3's `N ∈ [4, 64]`; at 10 MHz that admits only 3 of the 12 (bundle, band, interval) combinations, and **at 5 MHz and below none at all** — see RECORD-001 "The reference-frequency range is not reachable" |
| Trim code | 2.5, 5, 10, 20, 40, 80 µA | The same ladder `sg13cmos5l-cp-icp-trim` swept; the measured `Icp` at that code and PVT point is used, not the nominal code value |
| MOM-cap uncertainty | −20% / 0 / +20% (Part B only) | DR-003 Finding 2's obligation, propagated to the loop level. `cap_cmomi` has no corner knob in the installed PDK, so the band can only be applied through the predecessor record's own *measured* C1/C2 values — see the lumped-variant testbench header for why that requires a second deck |
| `R1` scale (Part C only) | ×1, ×5, ×10, ×20, ×50, ×100 | A **proposal** sweep, not a measurement of the committed design; kept in its own `proposal.csv` for that reason |

## Run counts

| Part | Deck | Filter | Runs | Output |
|---|---|---|---|---|
| A | `tb_loop_ac_real.sp.tmpl` | **real `loop_filter` subckt** (`rppd` + `cap_cmomi` compact models) | 90 | `results.csv` |
| A′ | both decks | real vs. lumped at the nominal point | 2 | `crosscheck.txt` |
| B | `tb_loop_ac_lumped.sp.tmpl` | lumped, from the predecessor record's measured R1/C1/C2 | 54 | `mom_band.csv` |
| C | `tb_loop_ac_lumped.sp.tmpl` | lumped, `R1` scaled (proposal) | 108 | `proposal.csv` |

## What is NOT swept, and why

- **Supply.** The loop-gain terms this record combines are `Icp` (measured
  supply sensitivity ≤1.2% over ±10%, `sg13cmos5l-cp-icp-trim`), `Kvco`
  (measured at 3.3 V only, per DR-004's all-3.3-V internal-domain
  ratification) and `R1`/`C1`/`C2` (passive, supply-independent). The
  supply axis therefore enters only through `Icp`'s own ≤1.2% term, which
  is far below the corner spread already swept. Stated rather than dropped.
- **Random device mismatch.** No per-instance mismatch model is available
  for this campaign (the same limitation the sibling records record).
- **The sampled-loop (z-domain) correction.** This is a continuous-time
  linearisation; the `f_c < f_ref/10` criterion is exactly the guard-band
  that makes that approximation admissible, and it is *evaluated*, never
  assumed satisfied.
