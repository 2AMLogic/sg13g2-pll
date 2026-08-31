# RECORD-004: closing the `band=00, low interval, f_ref=4.5MHz` PM gap (issue #79) with a fine Icp-trim code

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #79 (Part of #16). Supersedes nothing: `RECORD-001` (as-drawn
  filter), `RECORD-002` (resized filter, full amended `f_ref` range), and
  `RECORD-003` (issue #83's own fine-trim close of a DIFFERENT tuple --
  `band=00, MID interval, f_ref=4.5MHz`) all stand unedited, with their own
  `../corners/{results,results_resized,mom_band,proposal,
  results_resized_issue83_finetrim}.csv` and crosscheck files. This record
  adds a **new**, separate CSV
  (`../corners/results_resized_issue79_finetrim.csv`) targeted at exactly
  the one gap `RECORD-002` left open at this (band, interval, `f_ref`)
  tuple.
- **DUT**: `../netlist-snapshots/loop_filter_resized.spice`, the SAME
  frozen post-resize (DR-006, `R1` x44.2) snapshot `RECORD-002`/`RECORD-003`
  use -- no geometry edit of any kind. `Icp` comes from
  `../../sg13cmos5l-cp-icp-trim/corners/results_issue79_finetrim.csv`
  (`sg13cmos5l-cp-icp-trim/records/RECORD-004-issue79-finetrim-icp.md`), a
  new, targeted Icp-trim measurement at a code (11 uA) not in the original
  six-code ladder and distinct from issue #83's own 3.75 uA code.
  `Kvco`/`fvco`/`n_div` are read directly off `RECORD-002`'s own committed
  rows for this tuple (`../corners/results_resized.csv`,
  `pvt_bundle in {fast,typ,slow}, band_code=00, kvco_interval=low,
  fref_hz=4.5e6`), not re-derived, so this record cannot silently drift
  from the exact operating point the gap was measured at.
- **Claim under test**:
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  found `band=00, low Kvco interval, f_ref=4.5MHz` (reachable at **all
  three** PVT bundles -- `n_div`=127/114/103 for fast/typ/slow) fails both
  `spec/porting-plan.md` row 6/6a criteria simultaneously at every one of
  the existing six trim codes: at 10 uA, `typ`/`slow` pass (47.624/52.226
  deg PM) but `fast` (the binding bundle) is 0.87 deg short of the 45 deg
  floor (44.127 deg, `f_c`=345923.9 Hz, well under the ceiling); at 20 uA,
  PM clears everywhere (54.429/56.764/58.798 deg) but `f_c` exceeds the
  450 kHz ceiling for **all three** bundles (583267/622503/721683 Hz).
  This record tests whether an intermediate Icp value closes both
  criteria, at all three bundles simultaneously (a single trim code must
  serve every PVT corner a manufactured part could land in -- see
  `spec/decision-records/DR-008-cp-icp-trim-fine-code-band00-low-fref4p5.md`
  "Why a single code, not per-corner codes").
- **Tooling**: `ngspice-47`, installed `~/share/pdk/ihp-sg13cmos5l` (with
  its `cap_cmomi.osdi`/`cap_cmomf.osdi` locally rebuilt for the host
  architecture via `openvaf-compile-va.sh`, per
  `sim/PORTING-osdi-host-arch.md`), arm64 macOS host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_issue79_finetrim.sh`
  writes `../corners/results_resized_issue79_finetrim.csv` (3 data rows,
  one per PVT bundle, same 14-column schema as
  `../corners/results_resized.csv`). `../corners/results_resized.csv`,
  `../corners/results_resized_issue83_finetrim.csv`, and every other
  existing corners file are untouched (`git diff` empty, verified before
  committing this record).

## Result

| `pvt_bundle` | `band_code` | `kvco_interval` | `fref_hz` | `n_div` | `trim_code` | `icp_a` | `fc_hz` | `pm_deg` | `fc_ceiling_hz` | `meets_ceiling` | `meets_pm45` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fast | 00 | low | 4.500000e+06 | 127 | 11u | 1.100049e-05 | 3.686111e+05 | 45.592 | 4.500000e+05 | **yes** | **yes** |
| typ | 00 | low | 4.500000e+06 | 114 | 11u | 1.100050e-05 | 3.851478e+05 | 49.043 | 4.500000e+05 | **yes** | **yes** |
| slow | 00 | low | 4.500000e+06 | 103 | 11u | 1.100077e-05 | 4.352370e+05 | 53.454 | 4.500000e+05 | **yes** | **yes** |

**All three bundles clear both criteria, real subckt** (not lumped, not
estimated), at the SAME trim code (11 uA -- a manufactured part is
trimmed once per `f_ref`, not once per PVT corner it might land in):

- `fast` (the bundle that failed the 10 uA code by 0.87 deg): `f_c` =
  368.6 kHz, 18.1% under the 450 kHz ceiling; PM = 45.592 deg, 0.592 deg
  over the 45 deg floor -- a real, measured, positive margin, though
  narrower than issue #83's own fine-trim margin (see "Why the margin is
  narrower than issue #83's" below).
- `typ`: `f_c` = 385.1 kHz (14.4% under ceiling), PM = 49.043 deg (4.043
  deg over floor).
- `slow` (the bundle that bounds the Icp window from above): `f_c` =
  435.2 kHz, 3.28% under the 450 kHz ceiling (the narrowest headroom of the
  three); PM = 53.454 deg, 8.454 deg over the floor.

## Why 11 uA -- the real-subckt scan that established the feasible window

Unlike issue #83's gap (a single binding bundle, wide margin available
between the two nearest existing codes), this gap has **different bundles
binding at each edge** of the feasible Icp range: `fast`'s PM floor pulls
the code up, `slow`'s `f_c` ceiling pulls it back down, and `typ` is
comfortably inside both bounds throughout. A real-subckt scan (loop-level
AC, same DUT/method as the committed result above) at several intermediate
codes found:

| `iref_a` | `fast` `pm_deg` (floor 45) | `slow` `fc_hz` (ceiling 450000) |
|---|---|---|
| 10.5u | 44.838 (fails) | 419394.5 (passes, 6.8% headroom) |
| 10.6u | 44.992 (fails) | 422562.1 (passes) |
| 10.7u | 45.144 (passes) | 425730.6 (passes) |
| 10.8u | 45.295 | 428900.0 |
| 10.9u | 45.444 | 432067.6 |
| **11.0u (committed)** | **45.592** | **435237.1** |
| 11.1u | 45.738 | 438406.4 |
| 11.2u | 45.883 | 441573.8 |
| 11.3u | 46.026 | 444744.7 |
| 11.4u | 46.168 | 447913.6 (passes, 0.46% headroom) |
| 11.45u | 46.239 | 449498.8 (passes, 0.11% headroom) |
| 11.5u | 46.309 | 451082.6 (**fails ceiling**) |

The feasible window (both edges satisfied simultaneously) is bounded below
by `fast`'s PM=45 deg crossing (between 10.6u and 10.7u, ~10.6 uA) and
above by `slow`'s `f_c`=450 kHz crossing (between 11.45u and 11.5u,
~11.47 uA) -- a window only ~0.85 uA wide. **11 uA was chosen because it
sits close to that window's own arithmetic midpoint (~11.05 uA)**, giving
the most balanced real margin available on both binding constraints
simultaneously, not because it is a bare-minimum or an arbitrarily
generous choice. `typ` was checked at every scanned code and never binds
either edge (its own margin stays >= 3.7 deg PM and >= 10% `fc` headroom
throughout the scanned range).

**Why the margin is narrower than issue #83's**: issue #83's gap had only
one binding bundle (`slow`), so its own fine-trim code (3.75 uA) could be
chosen with ~5 deg PM margin and ~20% `fc` headroom simultaneously. This
gap's window is intrinsically narrower because two *different* bundles
bind at opposite edges of the same one-dimensional Icp knob -- pushing the
code up to help `fast`'s PM directly erodes `slow`'s `fc` headroom, and
there is no third degree of freedom in this mitigation to decouple them.
0.592 deg (fast) and 3.28% (slow) are the best simultaneously-achievable
margins available from an Icp-trim-code change alone; a joint `R1`/`C1`/`C2`
retune could in principle widen this window further but was not pursued --
see the decision record's "Alternatives considered" for why a narrower
but real, measured, positive margin was accepted over a broader geometry
change for this specific gap.

**Reproducibility**: re-ran `./testbench/run_issue79_finetrim.sh` a second
time in a fresh scratch dir; `../corners/results_resized_issue79_finetrim.csv`
reproduced byte-for-byte identical.

## Why no other operating region can regress

This mitigation changes **no geometry** (`R1`/`C1`/`C2` are the identical
resized values `RECORD-002` verified) and reads **no existing trim code's**
Icp value, and is a **separate** code/file from issue #83's own 3.75 uA
fine-trim addition -- it adds one new (Icp value, operating point) triple
(one per PVT bundle) that only this one previously-failing tuple uses.
Every other row in `../corners/results_resized.csv` is computed from the
same unmodified `loop_filter_resized` subckt and the same six original
trim codes, neither of which this record touches, so none of the other
(band, interval, `f_ref`) combinations in the full amended-range matrix --
including issue #83's own `band=00, mid interval, f_ref=4.5MHz` gap,
already closed by `RECORD-003` -- can be affected by this change.
Confirmed directly: `git diff -- ../corners/results_resized.csv
../corners/results_resized_issue83_finetrim.csv` is empty (this record
adds one new file, `results_resized_issue79_finetrim.csv`, and edits
nothing else in `../corners/`).

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 6/6a**: `band=00, low interval, f_ref=4.5MHz`, all three PVT
  bundles, now meets both criteria with real (if narrow, for `fast`/`slow`)
  margin at the trim code documented in
  `spec/decision-records/DR-008-cp-icp-trim-fine-code-band00-low-fref4p5.md`.
  This closes the LAST of the two outright failures
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  ("Full accounting, all 30 combinations": 16 pass with full 3-bundle
  coverage, 12 pass with only 1-2 bundles simulated, 2 fail outright) and
  `spec/decision-records/DR-006-loop-filter-r1-resize.md` both flagged
  (`band=00/mid/f_ref=4.5MHz`, issue #83, 1-bundle coverage, closed by
  `RECORD-003`; `band=00/low/f_ref=4.5MHz`, issue #79, full 3-bundle
  coverage, **closed by this record**). Both of `RECORD-002`'s two outright
  failures are now closed via a fine Icp-trim code; the 12
  partial-PVT-coverage combinations `RECORD-002` flagged (only 1-2 of 3
  bundles simulated -- a *coverage* gap, not a *failure*, at every bundle
  actually simulated) remain partially covered. Neither this record nor
  `RECORD-003` extends that coverage, which is a separate future-work item,
  not part of either issue's own scope.
