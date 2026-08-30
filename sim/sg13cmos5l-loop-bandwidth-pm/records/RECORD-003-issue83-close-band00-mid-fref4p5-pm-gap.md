# RECORD-003: closing the `band=00, mid interval, f_ref=4.5MHz` PM gap (issue #83) with a fine Icp-trim code

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #83 (Part of #16). Supersedes nothing: `RECORD-001` (as-drawn
  filter) and `RECORD-002` (resized filter, full amended `f_ref` range) both
  stand unedited, with their own `../corners/{results,results_resized,
  mom_band,proposal}.csv` and crosscheck files. This record adds a **new**,
  separate CSV (`../corners/results_resized_issue83_finetrim.csv`) targeted
  at exactly the one gap `RECORD-002` left open at this (band, interval,
  `f_ref`) tuple.
- **DUT**: `../netlist-snapshots/loop_filter_resized.spice`, the SAME frozen
  post-resize (DR-006, `R1` x44.2) snapshot `RECORD-002` used -- no geometry
  edit of any kind. `Icp` comes from
  `../../sg13cmos5l-cp-icp-trim/corners/results_issue83_finetrim.csv`
  (`sg13cmos5l-cp-icp-trim/records/RECORD-003-issue83-finetrim-icp.md`), a
  new, targeted Icp-trim measurement at a code (3.75 uA) not in the original
  six-code ladder. `Kvco`/`fvco`/`n_div` are read directly off `RECORD-002`'s
  own committed row for this tuple (`../corners/results_resized.csv`,
  `pvt_bundle=slow, band_code=00, kvco_interval=mid, fref_hz=4.5e6`), not
  re-derived, so this record cannot silently drift from the exact operating
  point the gap was measured at.
- **Claim under test**:
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  found `band=00, mid Kvco interval, f_ref=4.5MHz` (`slow` bundle,
  `n_div`=119 -- the only bundle reachable at this tuple) fails both
  `spec/porting-plan.md` row 6/6a criteria simultaneously at every one of
  the existing six trim codes: 2.5 uA meets `f_c < f_ref/10` but PM =
  43.639 deg, 1.36 deg short of the 45 deg floor; 5 uA and above meet PM but
  `f_c` exceeds the ceiling. This record tests whether an intermediate Icp
  value closes both simultaneously.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_issue83_finetrim.sh`
  writes `../corners/results_resized_issue83_finetrim.csv` (1 data row,
  same 14-column schema as `../corners/results_resized.csv`).
  `../corners/results_resized.csv` and every other existing corners file
  are untouched (`git diff` empty, verified before committing this record).

## Result

| `pvt_bundle` | `band_code` | `kvco_interval` | `fref_hz` | `n_div` | `trim_code` | `icp_a` | `fc_hz` | `pm_deg` | `fc_ceiling_hz` | `meets_ceiling` | `meets_pm45` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| slow | 00 | mid | 4.500000e+06 | 119 | 3.75u | 3.750478e-06 | 3.592385e+05 | 49.973 | 4.500000e+05 | **yes** | **yes** |

**Both criteria clear, with real margin, real subckt** (not lumped, not
estimated): `f_c` = 359.24 kHz is 20.2% under the 450 kHz ceiling; PM =
49.973 deg is 4.97 deg over the 45 deg floor. This closes the one gap issue
#83 tracks.

For context, the full sensitivity between the two existing bracketing codes
(explored during this record's derivation, real subckt, same tuple, not
separately committed as corners data since it is superseded by the single
chosen code above -- shown here for the decision record's own "why 3.75 uA"
justification):

| `iref_a` | `icp_a` (measured) | `fc_hz` | `pm_deg` | `meets_ceiling` | `meets_pm45` |
|---|---|---|---|---|---|
| 2.5u (existing) | 2.517044e-06 | 2.690506e+05 | 43.639 | yes | no |
| 2.7u | 2.700453e-06 | 2.825778e+05 | 44.783 | yes | no |
| 2.8u | 2.800455e-06 | 2.899271e+05 | 45.372 | yes | yes |
| 3.0u | 3.000459e-06 | 3.045812e+05 | 46.484 | yes | yes |
| 3.5u | 3.500472e-06 | 3.410530e+05 | 48.918 | yes | yes |
| **3.75u (committed)** | **3.750478e-06** | **3.592385e+05** | **49.973** | **yes** | **yes** |
| 4.0u | 4.000485e-06 | 3.774120e+05 | 50.933 | yes | yes |
| 4.5u | 4.500499e-06 | 4.137436e+05 | 52.604 | yes | yes |
| 5.0u (existing) | 5.028064e-06 | 4.520837e+05 | 54.058 | no | yes |

The crossing point (both criteria simultaneously satisfied) lies between
2.7 uA and 2.8 uA; 3.75 uA (the arithmetic midpoint of the two existing
bracketing codes) was chosen over the bare minimum ~2.8 uA to keep real
margin against process/model uncertainty on both sides (20.2% `f_c`
headroom, 4.97 deg PM headroom) rather than a code that would only barely
clear either criterion.

**Reproducibility**: re-ran `./testbench/run_issue83_finetrim.sh` a second
time in a fresh scratch dir; `../corners/results_resized_issue83_finetrim.csv`
reproduced byte-for-byte identical.

## Why no other operating region can regress

This mitigation changes **no geometry** (`R1`/`C1`/`C2` are the identical
resized values `RECORD-002` verified) and reads **no existing trim code's**
Icp value -- it adds one new (Icp value, operating point) pair that only
this one previously-failing tuple uses. Every other row in
`../corners/results_resized.csv` is computed from the same unmodified
`loop_filter_resized` subckt and the same six original trim codes, neither
of which this record touches, so none of the other 29 (band, interval,
`f_ref`) combinations in the full amended-range matrix -- including issue
#79's still-open `band=00, low interval, f_ref=4.5MHz` gap -- can be
affected by this change. Confirmed directly:
`git diff -- ../corners/results_resized.csv` is empty (this record adds a
new file, `results_resized_issue83_finetrim.csv`, and edits nothing else in
`../corners/`).

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 6/6a**: `band=00, mid interval, f_ref=4.5MHz` (`slow` bundle, the
  only bundle reachable at this tuple) now meets both criteria with real
  margin at the trim code documented in
  `spec/decision-records/DR-007-cp-icp-trim-fine-code-band00-mid-fref4p5.md`.
  This closes the second of the two outright failures
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  and `spec/decision-records/DR-006-loop-filter-r1-resize.md` both flagged
  (`band=00/low/f_ref=4.5MHz`, issue #79, **remains open**;
  `band=00/mid/f_ref=4.5MHz`, issue #83, **closed by this record**). The 12
  other partial-PVT-coverage combinations `RECORD-002` flagged (only 1-2 of
  3 bundles simulated, passing at every bundle actually simulated) are
  unaffected and remain a coverage gap for future work, not addressed here.
