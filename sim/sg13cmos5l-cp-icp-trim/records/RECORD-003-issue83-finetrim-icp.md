# RECORD-003: a targeted fine-trim Icp measurement (3.75 uA, `slow` bundle) for issue #83

- **Slug**: `sg13cmos5l-cp-icp-trim`
- **Issue**: #83 (Part of #16). Supersedes nothing -- `RECORD-001` and
  `RECORD-002` (the full 306-row/3111-row six-code campaign, all 17 PVT/
  supply points) stand unedited, with their own `../corners/results.csv`
  and `../corners/compliance.csv`. This record is a **targeted addition**:
  one new trim code (3.75 uA), one PVT point (`mos_ss`/125 C/3.3 V, the
  "slow" bundle `sg13cmos5l-loop-bandwidth-pm`'s testbench maps to), not a
  re-run of the full campaign.
- **DUT**: `../netlist-snapshots/cp.spice` (same frozen snapshot
  `RECORD-002` uses, post-DR-006-cp-cascode-bias-replica -- `IBP`/`ICP`/
  `IBN`/`ICN` are current inputs), instantiated verbatim, no strip.
- **Claim under test**: `spec/porting-plan.md` row 6/6a's Icp-trim
  mechanism, exercised at a finer granularity than the original six-code
  characterisation grid, specifically to supply the Icp value
  `spec/decision-records/DR-007-cp-icp-trim-fine-code-band00-mid-fref4p5.md`
  and `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`
  need to close issue #83's PM gap.
- **Why 3.75 uA and only the `slow` bundle**:
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  found `band=00, mid Kvco interval, f_ref=4.5MHz` fails at every existing
  trim code, with the `slow` bundle the only one that reaches a legal
  `n_div` at that tuple (`n_div`=119; `typ`/`fast` bundles' lowest reachable
  `f_ref` at `band=00, mid` is 5.5 MHz, confirmed directly against
  `../../sg13cmos5l-loop-bandwidth-pm/corners/results_resized.csv`). 3.75 uA
  is the arithmetic midpoint of the existing 2.5/5 uA codes, the two codes
  that bracket the failing region (2.5 uA: PM short by 1.36 deg; 5 uA:
  `fc` over the ceiling by 0.46%).
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_issue83_finetrim.sh`
  writes `../corners/results_issue83_finetrim.csv` (4 rows: header + up/dn/
  both states, matching `../corners/results.csv`'s own 7-column schema).
  `../corners/results.csv` and `../corners/compliance.csv` are untouched
  (`git diff` empty, verified before committing this record).

## Result

| `mos_corner` | `temp_c` | `vdd_v` | `iref_a` | `state` | `vout_v` | `icp_a` |
|---|---|---|---|---|---|---|
| `mos_ss` | 125 | 3.3 | 3.75u | up | 1.6500 | 3.750478e-06 |
| `mos_ss` | 125 | 3.3 | 3.75u | dn | 1.6500 | -3.758816e-06 |
| `mos_ss` | 125 | 3.3 | 3.75u | both | 1.6500 | -8.372323e-09 |

The `up`-state row (3.750478 uA, delivered current at `VOUT` = VDD/2) is the
value `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`
consumes, in the exact same `icp_for()`-style lookup convention
`../../sg13cmos5l-loop-bandwidth-pm/testbench/run.sh` already uses for the
original six codes. `up`/`dn` mismatch (0.222% at this code/corner) and the
`both`-state net current are recorded for schema consistency with
`../corners/results.csv`, not because this issue needs the reference-spur
mechanism re-derived at this code.

**Reproducibility**: re-ran `./testbench/run_issue83_finetrim.sh` a second
time in a fresh scratch dir; `../corners/results_issue83_finetrim.csv`
reproduced byte-for-byte identical.

## Spec-row disposition

- **Row 6/6a**: this record supplies one additional Icp-trim data point
  consumed by the loop-level record that closes issue #83's gap (see
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md`).
  It does not itself make a stability claim -- that claim is made, and
  verified against both criteria, at the loop level.
