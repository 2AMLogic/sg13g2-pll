# RECORD-004: a targeted fine-trim Icp measurement (11 uA, all three PVT bundles) for issue #79

- **Slug**: `sg13cmos5l-cp-icp-trim`
- **Issue**: #79 (Part of #16). Supersedes nothing -- `RECORD-001`,
  `RECORD-002` (the full 306-row/3111-row six-code campaign, all 17 PVT/
  supply points), and `RECORD-003` (issue #83's own 3.75 uA fine-trim code,
  a DIFFERENT operating-point tuple) all stand unedited, with their own
  `../corners/results.csv`, `../corners/compliance.csv`, and
  `../corners/results_issue83_finetrim.csv`. This record is a **targeted
  addition**: one new trim code (11 uA), three PVT points (`mos_ff/-40C`,
  `mos_tt/27C`, `mos_ss/125C`, all at 3.3 V), not a re-run of the full
  campaign.
- **DUT**: `../netlist-snapshots/cp.spice` (same frozen snapshot
  `RECORD-002`/`RECORD-003` use, post-DR-006-cp-cascode-bias-replica --
  `IBP`/`ICP`/`IBN`/`ICN` are current inputs), instantiated verbatim, no
  strip.
- **Claim under test**: `spec/porting-plan.md` row 6/6a's Icp-trim
  mechanism, exercised at a finer granularity than the original six-code
  characterisation grid, specifically to supply the Icp values
  `spec/decision-records/DR-008-cp-icp-trim-fine-code-band00-low-fref4p5.md`
  and `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`
  need to close issue #79's PM gap.
- **Why 11 uA and all three bundles**:
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md`
  found `band=00, LOW Kvco interval, f_ref=4.5MHz` reachable at **all three**
  PVT bundles (`n_div`=127/114/103 for fast/typ/slow respectively) -- unlike
  issue #83's own gap (a different tuple, reachable only at `slow`). At the
  existing 10 uA code, `typ`/`slow` already pass (47.624/52.226 deg PM) but
  `fast` (the binding bundle) is 0.87 deg short (44.127 deg); at 20 uA, PM
  clears everywhere but `f_c` exceeds the 450 kHz ceiling for **all three**
  bundles. A real-subckt scan (loop-level AC, see the companion loop record)
  found the feasible Icp window is bounded by two *different* bundles at
  each edge: `fast`'s PM=45 deg floor near 10.6 uA, `slow`'s
  `f_c`=ceiling near 11.47 uA -- a window only ~0.85 uA wide, not the wide
  margin issue #83's single-bundle gap had. 11 uA was chosen close to that
  window's own arithmetic midpoint (~11.05 uA) for balanced real margin on
  both binding constraints. See
  `spec/decision-records/DR-008-cp-icp-trim-fine-code-band00-low-fref4p5.md`
  "Decision" for the full scan table.
- **Tooling**: `ngspice-47`, installed `~/share/pdk/ihp-sg13cmos5l` (with
  its `cap_cmomi.osdi`/`cap_cmomf.osdi` locally rebuilt for the host
  architecture via `openvaf-compile-va.sh`, per
  `sim/PORTING-osdi-host-arch.md`), arm64 macOS host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_issue79_finetrim.sh`
  writes `../corners/results_issue79_finetrim.csv` (10 rows: header + 3
  PVT points x up/dn/both states, matching `../corners/results.csv`'s own
  7-column schema). `../corners/results.csv`,
  `../corners/results_issue83_finetrim.csv`, and `../corners/compliance.csv`
  are untouched.

## Result

| `mos_corner` | `temp_c` | `vdd_v` | `iref_a` | `state` | `vout_v` | `icp_a` |
|---|---|---|---|---|---|---|
| `mos_ff` | -40 | 3.3 | 11u | up | 1.6500 | 1.100049e-05 |
| `mos_ff` | -40 | 3.3 | 11u | dn | 1.6500 | -1.102240e-05 |
| `mos_ff` | -40 | 3.3 | 11u | both | 1.6500 | -2.191701e-08 |
| `mos_tt` | 27 | 3.3 | 11u | up | 1.6500 | 1.100050e-05 |
| `mos_tt` | 27 | 3.3 | 11u | dn | 1.6500 | -1.101848e-05 |
| `mos_tt` | 27 | 3.3 | 11u | both | 1.6500 | -1.797570e-08 |
| `mos_ss` | 125 | 3.3 | 11u | up | 1.6500 | 1.100077e-05 |
| `mos_ss` | 125 | 3.3 | 11u | dn | 1.6500 | -1.101604e-05 |
| `mos_ss` | 125 | 3.3 | 11u | both | 1.6500 | -1.529873e-08 |

The `up`-state rows (1.100049e-05 / 1.100050e-05 / 1.100077e-05 A for
`mos_ff`/`mos_tt`/`mos_ss` respectively) are the values
`sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`
consumes, in the exact same `icp_for()`-style lookup convention
`../../sg13cmos5l-loop-bandwidth-pm/testbench/run.sh` already uses for the
original six codes. `up`/`dn` mismatch (0.199% `mos_ff`, 0.163% `mos_tt`,
0.139% `mos_ss` at this code) and the `both`-state net current are recorded
for schema consistency with `../corners/results.csv`, not because this
issue needs the reference-spur mechanism re-derived at this code.

**Reproducibility**: re-ran `./testbench/run_issue79_finetrim.sh` a second
time in a fresh scratch dir; `../corners/results_issue79_finetrim.csv`
reproduced byte-for-byte identical.

## Spec-row disposition

- **Row 6/6a**: this record supplies three additional Icp-trim data points
  (one per PVT bundle) consumed by the loop-level record that closes issue
  #79's gap (see
  `sim/sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md`).
  It does not itself make a stability claim -- that claim is made, and
  verified against both criteria, at the loop level.
