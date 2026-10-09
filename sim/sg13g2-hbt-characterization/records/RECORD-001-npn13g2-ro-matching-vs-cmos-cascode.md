# RECORD-001: SG13G2 `npn13G2` output resistance and mirror matching vs. the `cp` CMOS cascode leg, plus a `klt extract`/`klt lvs` bipolar probe

- **Slug**: `sg13g2-hbt-characterization`
- **Issue**: #181 (measurement only; adopts nothing)
- **Claim under test**: the deferral trigger of
  `spec/decision-records/DR-002-supply-device-flavor.md` Decision 2 (HBT current
  mirror/cascode "deferred, not adopted"), which asks for extracted `r_o`/matching
  data showing "a real compliance-range or matching advantage over the CMOS
  wide-swing cascode". The verdict is in `DR-009` (this record's decision record).
- **Tooling**: ngspice 46; `~/share/pdk/ihp-sg13g2` (`cornerHBT.lib`, `cornerMOShv.lib`,
  `sg13g2_hbt_mod.lib`, `sg13g2_hbt_mod_mismatch.lib`). Device name verified against the
  installed PDK: subcircuit `npn13G2 c b e bn` in `sg13g2_hbt_mod.lib` (VBIC level 9,
  `vbe_max = vce_max = 1.6`, `vbc_max = 5.1`), xschem symbol
  `sg13g2_pr/npn13G2.sym`. `klt sim` client **0.6.0** for the batch runs (see
  "Tool friction"), `klt` 0.7.0 for the local probe and extract/LVS.
- **PDK revision**: `IHP-Open-PDK` commit `5cccb161f7492697cfa52eb14dc03beb00bdca9e`
  (tag `v0.3.0`). The installed `~/share/pdk/ihp-sg13g2` tree is not a git checkout; its
  `.fetched-version` marker reads `0.3.0`, and the git blob hashes of the six model files
  these benches load (`sg13g2_hbt_mod.lib`, `sg13g2_hbt_mod_mismatch.lib`, `cornerHBT.lib`,
  `cornerMOShv.lib`, `sg13g2_moshv_mod.lib`, `sg13g2_moshv_parm.lib`) are identical to
  `ihp-sg13g2/libs.tech/ngspice/models/` at that tag. The batch report
  `corners/reports/hbt_ro.klt-report.json` records `models_lib_sha256` `bae3d705...`, which
  equals the sha256 of the local `cornerHBT.lib`; `cmos_ro_nominal.klt-report.json`'s
  `5a1f862d...` equals the local `cornerMOShv.lib`. The slim `hbt_mm` report carries no
  model hash, so the MC job's fleet-side tree is not independently confirmed. The other
  files in the tree (and the OSDI objects) were not compared.
- **Reproduce**: `testbench/run.sh` (requests in `requests/`, reducer
  `testbench/analyze.py`; raw reports in `corners/reports/`, CSVs in `corners/`).
- **Matrix**: `corners/matrix.md`.

## What was and was not exercised

| Item | Status | Where it ran |
|---|---|---|
| HBT `r_o` vs Vce at 3 currents, 3 temperatures x 3 HBT process corners (9 corners) | **Exercised** | Spot batch fleet, job `klt-sim-88622d7e1391`, 9/9 pass |
| HBT mirror-ratio mismatch, MC n=50 per corner x 9 corners (450 runs) | **Exercised** | Spot batch fleet, job `klt-sim-1f2270c3890b`, 450/450 pass |
| CMOS cascode leg `r_o` / compliance, `mos_tt` / 27 C | **Exercised** (one corner) | local, one `ngspice -b` via `klt sim --backend local` |
| CMOS cascode leg at -40 / 125 C and `mos_ss` / `mos_ff` | **Not exercised** | batch submit failed (below); not run locally by host rule |
| CMOS cascode leg matching spread (MC) | **Not exercised** | same; the 450-run MC request was not run |
| CMOS leg supply sensitivity (3.0 / 3.6 V) | **Not exercised** | not in scope of this bench |
| HBT in the actual `cp` leg / stacked with a CMOS cascode | **Not exercised** | out of scope (no `cp` redesign) |
| Layout-extracted `r_o`/matching (the word "extracted" in DR-002) | **Impossible with the current deck** | see the extract/LVS section |

Batch failures, reported rather than worked around:

1. First submission with `klt` 0.7.0: job `klt-sim-c4fbdf5d2978` ended `failed`, exit 87,
   `batch_runner_version_mismatch` (runner klt 0.5.0, client 0.7.0), all 9 corners
   `errored`. Already tracked upstream as `2AMLogic/klayout-tools#2948` (and #2851, #2877, #2901).
   The run was redone with a 0.6.0 client in a throwaway venv inside the worktree
   (host `klt` untouched), which the runner accepted.
2. CMOS grid (`requests/cmos_ro.request.json`, job `klt-sim-77f32614fa0b`): all 9 corners
   `errored`, `Unknown model type psp103va` / `Unable to find definition of model
   xmbn:sg13g2_hv_nmos_psp`. The runner has no OSDI objects and the 0.6.0 client does not
   stage them (`options.stage_model_inputs: true` was set). Related upstream:
   `2AMLogic/klayout-tools#2570` (no ihp-sg13g2 remote-sim AMI), #2901. The CMOS
   mismatch request (`cmos_mm.request.json`) was then not submitted: its one attempt
   hit `BATCH_MAX_CONCURRENT_INSTANCES=8` and the same OSDI limitation guarantees the
   same failure. **No local grid fallback was run.** The single nominal local corner is
   the only CMOS data here.

## Methodology

**HBT bench** (`testbench/tb_hbt_ro.sp`): a diode-connected `npn13G2` (Nx=1, 0.96 um x
0.12 um emitter per the model card default) fed by an ideal `Iref`; five identical
output transistors share its base and each has its collector held by an ideal source at
Vce = 0.3 / 0.6 / 0.9 / 1.2 / 1.5 V. `Iref` is DC-swept and the quantities read at
2.5 / 10 / 80 uA (the sibling `cp` trim ladder's low, nominal and high codes). The
collector currents are the HBT mirror's output currents, so they include the reference
transistor's base-current copy error; `r_o = dVce/dIc` is taken between Vce points at
the same base voltage.

**HBT matching bench** (`tb_hbt_mm.sp`): reference + four outputs at Vce = 0.9 V, using
the `*_mismatch` library sections, whose model draws `area = agauss(1, 0.1, ...)` per
instance (`sg13g2_hbt_mod_mismatch.lib`), seeded by `klt sim` per MC sample.
Each sample re-draws the reference and all outputs (distinct per-instance values were
confirmed in a 3-sample local probe before the batch run). Reported: ratio
`Ic_out/Iref` and the equivalent Vbe offset `Vt * sigma(ln ratio)`. The 200 ratios per
cell come from 50 independent reference draws, so the 4 outputs of one sample share
that sample's reference error (n_eff is between 50 and 200).

**CMOS comparison leg** (`tb_cmos_ro.sp`): the `cp_leg_n` mirror/cascode devices of
`design/cp_leg_n.sch` (`M1`, `M2` = `sg13_hv_nmos` 8u/1u) with its output switch `SWO`
(6u/0.3u, on) and the high-swing bias replica `MBN`/`MBNC`/`MCN` from
`design/sg13cmos5l/cp.sch` (DR-006: 8u/1u, 8u/1u, 2u/3u). **Provenance caveat**: the
SG13G2 tree's own `design/cp.sch` still has bare voltage bias pins `IBN`/`ICN` and no
replica (the DR-006 defect); the replica lives only in the SG13CMOS5L tree, so this
bench stands the replica in, fed by two ideal currents tracking `Iref`. Ten copies of
the leg have `VOUT` held at 0.3 ... 3.0 V. The bias reference itself is ideal (DR-002
Decision 1 keeps bias generation out of scope).

## Results: HBT `Ic`-`Vce` output resistance

`r_o` over Vce 0.9 -> 1.5 V (forward-active at all nine corners; the diode-connected
reference sits at Vbe = 0.55-0.86 V). Source: `corners/hbt_ro.csv`, `corners/analysis-output.md`.

| process | T (C) | Vbe at 2.5 / 10 / 80 uA (V) | r_o at 2.5 uA | r_o at 10 uA | r_o at 80 uA | r_o 0.6->0.9 V at 10 uA | Ic(1.5 V)/Iref at 10 uA |
|---|---|---|---|---|---|---|---|
| hbt_typ | -40 | 0.776 / 0.804 / 0.848 | 58.14 M | 8.80 M | 0.279 M | 9.22 M | 1.0039 |
| hbt_typ | 27 | 0.689 / 0.726 / 0.784 | 55.45 M | 9.49 M | 0.335 M | 10.52 M | 1.0008 |
| hbt_typ | 125 | 0.555 / 0.604 / 0.681 | 40.73 M | 8.66 M | 0.393 M | 12.00 M | 0.9988 |
| hbt_bcs | -40 | 0.771 / 0.799 / 0.843 | 57.53 M | 8.63 M | 0.264 M | 9.06 M | 1.0061 |
| hbt_bcs | 27 | 0.683 / 0.720 / 0.777 | 54.60 M | 9.30 M | 0.319 M | 10.34 M | 1.0047 |
| hbt_bcs | 125 | 0.547 / 0.596 / 0.672 | 39.58 M | 8.41 M | 0.376 M | 11.78 M | 1.0051 |
| hbt_wcs | -40 | 0.782 / 0.810 / 0.855 | 59.06 M | 9.02 M | 0.297 M | 9.44 M | 1.0004 |
| hbt_wcs | 27 | 0.697 / 0.734 / 0.792 | 56.76 M | 9.77 M | 0.356 M | 10.78 M | 0.9945 |
| hbt_wcs | 125 | 0.565 / 0.615 / 0.692 | 42.43 M | 9.02 M | 0.417 M | 12.34 M | 0.9885 |

(All `r_o` in ohm, "M" = 10^6.) At the nominal 10 uA code, `r_o` is 8.4-9.8 Mohm over the
whole 3 x 3 grid, i.e. a spread of about +/-8% about 9 Mohm; it scales roughly as 1/Ic
(the implied Early voltage is about 90 V at 10 uA). Collector current at Vce = 0.3 V is
98.6-98.8% of its value at 1.5 V at every corner at the 10 uA code, so the HBT's
saturation floor is at or below 0.3 V in this model. The model card's `vce_max = 1.6 V`
marks the upper edge of the validated region.

## Results: HBT mirror-ratio mismatch (modelled)

Source: `corners/hbt_mm_summary.csv` (per-sample data in `corners/hbt_mm_samples.csv`).
Ratio = `Ic_out/Iref` at Vce = 0.9 V.

| process | T (C) | sigma(ratio), % (2.5 / 10 / 80 uA) | sigma(dVbe-equivalent), mV |
|---|---|---|---|
| hbt_typ | -40 | 15.61 / 15.61 / 15.62 | 3.13 |
| hbt_typ | 27 | 13.28 / 13.28 / 13.29 | 3.45 |
| hbt_typ | 125 | 13.23 / 13.24 / 13.26 | 4.52 |
| hbt_bcs | -40 | 13.91 / 13.91 / 13.92 | 2.75 |
| hbt_bcs | 27 | 13.21 / 13.21 / 13.22 | 3.41 |
| hbt_bcs | 125 | 13.49 / 13.50 / 13.52 | 4.64 |
| hbt_wcs | -40 | 12.96 / 12.97 / 12.97 | 2.53 |
| hbt_wcs | 27 | 14.42 / 14.43 / 14.44 | 3.75 |
| hbt_wcs | 125 | 12.93 / 12.94 / 12.95 | 4.35 |

Mean ratios are 0.975-1.044 (the offset from 1 is sampling noise of a 50-sample mean,
plus the mirror's base-current error). Interpretation limits, stated plainly:

- The spread is independent of current and process by construction: the PDK mismatch
  model is a single 10% 1-sigma **area** perturbation per instance (about 14% in the
  ratio of two devices), and the `Vt * sigma(ln ratio)` column then rises with T purely
  through `Vt`. It is the library's model, not a layout-aware or measured figure.
- `klt sim` itself reports for this PDK family: "mismatch activity for the 'bipolar'
  family is not independently verified for PDK family 'sg13g2'; treat any sampled spread
  for it as unconfirmed" (recorded in the report's `monte_carlo_env`).
- It is a single minimum-size device (Nx=1); the area-scaling of the model (a device with
  larger Nx, or several in parallel) was **not exercised**, so the table says nothing about
  how matching improves with emitter count.

## Results: CMOS `cp_leg_n` cascode leg, `mos_tt` / 27 C only

Source: `corners/cmos_ro_nominal.csv`. The sink current is measured at the leg's `VOUT`
(behind the on switch `SWO`).

| Iref | Isink at Vout = 0.3 / 0.9 / 1.5 / 2.1 / 3.0 V (uA) | r_o, Vout 1.2->3.0 V | r_o, Vout 0.9->1.5 V | lowest Vout with Isink >= 98% of Isink(3.0 V) |
|---|---|---|---|---|
| 2.5 uA | 2.493 / 2.502 / 2.507 / 2.512 / 2.529 | 75.1 M | 119.1 M | 0.3 V |
| 10 uA | 9.810 / 10.003 / 10.015 / 10.025 / 10.056 | 39.2 M | 51.7 M | 0.6 V |
| 80 uA | 67.087 / 79.521 / 80.216 / 80.258 / 80.293 | 11.4 M | 0.86 M (knee) | 0.9 V |

(For the 80 uA code the 0.9->1.5 V span still contains the cascode's knee, so the figure
is a compliance edge, not a plateau `r_o`; the 1.2->3.0 V figure is the plateau value.)

### Side by side, nominal corner (`typ`/27 C), 10 uA code

| | HBT `npn13G2` (mirror, Nx=1) | CMOS `cp_leg_n` wide-swing cascode |
|---|---|---|
| r_o | 9.5 M (Vce 0.9->1.5 V) | 39 M (Vout 1.2->3.0 V); 52 M (0.9->1.5 V) |
| usable output range at this bias | at/below 0.3 V up to the model's 1.6 V Vce limit | 0.6 V up to 3.0 V (the top of the sweep) |
| mirror-ratio spread | 13.3% 1-sigma (model; Nx=1) | **not exercised** |
| temperature / process | 9 corners | 1 corner |

## `klt extract` / `klt lvs` bipolar probe

Files in `layout-probe/`: `npn_probe.gds` (the PDK's own `npn13G2` cell from
`libs.ref/sg13g2_pr/gds/sg13g2_pr.gds`, flattened into one top cell), `npn_probe.reference.spice`,
`npn_probe.lvs.request.json`, and the raw `extract-report.json`, `npn_probe.extracted.spice`,
`lvs-report.json`.

- **`klt extract --deck sg13g2 --pdk ihp-sg13g2`**: `status: extracted`, `device_count: 0`,
  `device_classes` = nfet, pfet, cap_cmim, rfcmim, cap_cmomi, cap_cmomf, resistor,
  dantenna, dpantenna (no bipolar class). The emitter, base and collector geometry is
  not an extracted device; 12 routing-stack clusters "join no extracted net". Layers
  1/20, 26/0, 33/0 and 51/0 are reported outside the deck's connectivity graph. This is
  exactly the gap tracked upstream as `#2860`-`#2863` (umbrella `#2864`, reopening
  the closed/declined `#1232`), so **no new issue was filed for it**.
- **`klt lvs`** with the reference as a subcircuit call `XQ1 c b e sub npn13G2 Nx=1`
  (the form xschem emits for this symbol): `status: "match"`, `error_count: 0`, devices
  0 / 0 / 0, warnings only. With the same circuit as a plain-element `Q1 c b e sub npn13G2`
  card the verdict is `mismatch` (7 errors, reference devices 1, layout devices 0). A
  zero-device layout therefore passes LVS against a subcircuit-call reference containing
  a bipolar. This is a new tool defect and was filed as
  **`2AMLogic/klayout-tools#2952`** (generic wording, no PLL detail).

Consequence for this repo: until `#2860`-`#2864` land, a bipolar can be neither extracted
nor LVS-checked, and any block that contains one and is checked with this deck must not be
read from a `match` status alone.

## Other upstream issues (all already open; not re-filed)

`#2948`, `#2851`, `#2877`, `#2901` (runner/client version skew), `#2570` and `#2901`
(no ihp-sg13g2 OSDI on the batch runner), `#2860`-`#2864` (bipolar extraction).

## Conclusion

See `spec/decision-records/DR-009-hbt-cascode-trigger-verdict.md`. In short: the data do
not show an HBT compliance or matching advantage over the CMOS cascode, and the
evidence needed for a full comparison (CMOS PVT grid and matching) was not obtainable on
this host; the trigger is **not met**.
