# RECORD-009: rerun of RECORD-002's resized lock-detector campaign via `klt sim` on the batch fleet (issue #328)

- **Slug**: `sg13cmos5l-lock-detector-window`
- **Issue**: #328 (split from #257, child of #213, Part of #199, item 9 provenance
  migration). Append-only. Reruns the campaign behind
  `RECORD-002-resized-window-hysteresis-chatter.md` (sha256
  `129f520ef9115288f01238f26cb03e7e97e57ddf1d26782ec10275226acb8cf4`, verified unchanged) and is the
  `ADDENDUM-RERUN` target of `ADDENDUM-004-record-002-superseded.md`. No earlier record or
  committed `corners/` file was edited; every output below carries the new suffix `rerun328`.
- **DUT at its producing commit, not today's design**: `07e1866`. The frozen
  `../netlist-snapshots/lock_detector_resized.spice` was compared with
  `git show 07e1866:sim/sg13cmos5l-lock-detector-window/netlist-snapshots/lock_detector_resized.spice`
  (byte-identical) and with `07e1866:design/sg13cmos5l/netlist/lock_detector.spice` (identical except
  the snapshot's 18-line provenance header). Today's `design/.../lock_detector.spice` was not used.
- **Entry point**: `07e1866:testbench/run.sh`, a local `ngspice -b` loop (~2 h wall by its own
  record) that was **not** run. Its grid is re-expressed as `klt sim` deck-list requests by
  `../testbench/batch_grid_rerun328.py` (a profile over #322's `batch_grid.py`) and driven by
  `../testbench/run_rerun328.sh`. Grid matrices (R/C, window, Schmitt, timestep-convergence) are
  `07e1866`'s; the 18-point ladder matrix and the `record002` ladder fractions are re-stated from it.
  Templates `tb_lock_recovery` / `tb_lock_ladder_point` are the `07e1866` copies
  (`../testbench/rerun328/`); HEAD's copies add `itl4=5000 gmin=1e-11` (#66), which RECORD-002 did
  not have. The other templates are byte-identical between `07e1866` and HEAD.
- **Deviations from `run.sh`, disclosed**: (1) decks run as `klt sim` units (`pre_osdi` and
  `num_threads=1` in a `.control` block replace `.spiceinit`; the OSDI-arch preflight is replaced by the
  runner's own image). (2) A deck that errors is retried once with `trtol=1`, then once more with
  `trtol=1 itl4=5000 gmin=1e-11` (see Failures); `run.sh` had no retry.
- **Probe first**: one `R_res_typ_27` deck, job `klt-sim-2b9efd5902c3`, runner klt `0.9.0`,
  ngspice-46, `rval = 2.069878e+06` ohm (original 2.266979e+06; see R below), 5 s.
- **Grid command** (per phase; each is one `klt sim --backend batch --wait-for-capacity 600
  <phase>/request.json --format json`), run through `run_rerun328.sh`:

  | Phase | Content | Units | Job id | Result |
  |---|---|---|---|---|
  | phase0 | R and C extraction | 15 | `klt-sim-332a5a5443e3` | pass |
  | phase1 | window (incl. each ladder corner's `twin_r`), Schmitt, timestep convergence | 157 | `klt-sim-93491bd10e67` | pass |
  | phase2 | ladder: per corner 1 recovery deck + 9 point decks | 180 | `klt-sim-de093cb26886` | 179 pass, 1 error |
  | phase2 retry (`trtol=1`) | the 1 errored unit | 1 | `klt-sim-a659aea3361e` | error |
  | phase2 retry2 (`trtol=1 itl4=5000 gmin=1e-11`) | same unit | 1 | `klt-sim-9abed5c2d78e` | error |

  The generated decks/requests/raw stdout are not committed (regenerate with `run_rerun328.sh`; job ids
  above identify the fleet runs). Folded to `../corners/{rc_extract,window,schmitt,tstep_convergence,ladder,ladder_raw}_rerun328.csv`
  by `batch_grid_rerun328.py reduce`.
- **Tools**: client `klt 0.9.2.dev661+g1de5c0432aad`; runner klt `0.9.0` (`runner_compatibility:
  match`), ngspice-46, AWS Batch Spot fleet, `us-east-1`, `m7i.4xlarge` / `m6i.4xlarge`. Submitted
  from `loom-worker` host `host-a6032f0c`. The original ran on arm64 macOS / ngspice-47 (RECORD-002's
  Tooling line), so **host, ngspice version and OSDI build all differ**; no single cause can be
  attributed to any difference below.
- **PDK revisions (pin, NOT independently verified on the runner)**: PDK ihp-sg13cmos5l revision
  607e18d4bd9214a52575c194b4181ef449f9252f and PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e, the pins in `sim/provenance-migration.md`. The runner's
  PDK lives at `/opt/pdk`; its stamp is not comparable to the client's, so no revision was read from
  the runner (same gap as RECORD-007; klayout-tools#5318, #3462).

## Results against RECORD-002's committed CSVs

| Output | Rows (orig / rerun) | Comparison |
|---|---|---|
| R extraction (`rhigh`, 9) | 9 / 9 | **differs**: -8.69 % (`res_typ`), -4.47 % (`res_bcs`), -8.23 % (`res_wcs`), uniform across temperature. E.g. `res_typ`/27 C 2.266979 -> 2.069878 Mohm. Cause not isolated (candidates: runner PDK tree vs original host's, ngspice 46 vs 47). |
| C extraction (6) | 6 / 6 | **identical** to 7 digits (1.691196 pF, 3.382393 pF), but the *source* differs: the original used the closed-form (`va-formula`) because `cap_cmomi.osdi` did not load on arm64; the runner loads the real OSDI model (`ngspice-osdi`). The formula is thereby cross-checked against the real model. |
| window | 79 / 100 | the 70 tags present in both: `twin_r` identical to printed precision (no deviation), 0 NA. The rerun has 21 more rows because `real` (the actual `cap_cmomi`) is simulated as a DUT variant; the original's `ideal0.00` primary rows at 9 points are replaced by `real` there. `real` window: 4.565 - 9.423 ns, inside the original's 3.688 - 11.24 ns range. |
| Schmitt (45) | 45 / 45 | **identical**: V_TH+/V_TH- unchanged (max difference 0.0 V); hysteresis 0.88 - 1.58 mV, as before. |
| timestep convergence (12) | 12 / 12 | `ideal` rows identical; `real` vs the original's `ideal0.00` within 0.013 %. |
| ladder (18) | 18 / **17 + 1 unconverged** | see below. |

### Ladder (17 of 18 corners converged)

All 17 converged corners are `steady` (no chatter), as in RECORD-002. The rerun's recovery time
`trec` is 4 - 9 % shorter at every converged point, consistent with the R shift above (RC/T_ref falls by the
same factor); `n_cycles` fell by 0 - 33 at some points because it is derived from RC. In-lock
supply current agrees to within ~3 %; out-of-lock current agrees within ~3 % except
`mos_tt/res_typ/27 C/3.3 V/24.4 MHz`, where it is 8.80e-05 A against 6.66e-05 A (+32 %), and
`mos_tt/res_bcs/125 C/24.4 MHz` (+9 %).

Assert/de-assert thresholds agree at 16 of 17 corners. **One corner differs**:
`mos_tt/res_bcs/27 C/3.3 V/3.5 MHz`: original assert and de-assert both at 1.0 x window (hysteresis
0 %), rerun assert at 0.5 x and de-assert at 1.0 x, i.e. **hysteresis 50 % of window** at this
ladder's coarse (0.5 -> 1.0) step. RECORD-002 reported 0 of 18 corners with resolvable hysteresis;
this rerun has 1 of 17. Its row-16 hysteresis verdict ("still fails" at the other 16 corners) is
unchanged; the single corner is **reported, not interpreted** (no further runs were made, so
whether it is a real threshold shift or a bracketing artefact is not known).

## Failures and limitations retained

- **Unconverged ladder corner**: `mos_tt/res_wcs/-40 C/3.3 V/3.5 MHz/real`, ladder point 04
  (unit `lad_mos_tt_res_wcs_-40c_3.3v_3p5MHz_real_pt04`). ngspice exits 1: `Timestep too small; time
  = 8.28571e-06, timestep = 1.42857e-20: trouble with node "xa4.xxor.n1"`, identically on the
  committed options, with `trtol=1`, and with `trtol=1 itl4=5000 gmin=1e-11`. Its row in
  `ladder_rerun328.csv` is all `NA`; its raw rows are absent. RECORD-002 had converged at this
  corner on its host, so this is a platform/version-dependent convergence difference, cause not
  isolated. It is not filed as a tool gap (the failure is in the simulator, not in klt).
- `solver_retries_rerun328.txt` is empty because its reducer only logs retries for units it used;
  the unit above is not used (NA row). The retry history is the table above.
- The `rerun328` ladder's `settle_frac`/`n_cycles` columns follow `run.sh`'s formula applied to the
  *rerun's* R (so they differ from the original wherever R differs).
- Runner PDK revision is unproven (above). RECORD-002's tooling description and RECORD-002 itself
  are not re-established beyond the numbers shown here.

## What this does not bound

- The original run's environment (superseded, not recovered).
- RECORD-001, RECORD-003..007, `schmitt_hv` crowbar/hysteresis follow-ups, PEX, #139, and any
  local ngspice grid (none was run).
- No consumer figure was replaced: `corners/matrix.md`, `characterization/` and the row-16
  disposition in RECORD-002 are untouched, because the one differing ladder corner and the R shift
  are unresolved and would not justify rewriting them.
