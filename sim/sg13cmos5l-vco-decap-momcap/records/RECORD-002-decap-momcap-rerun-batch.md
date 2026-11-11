# RECORD-002: rerun of RECORD-001's `vco.XCDECAP` grid through `klt sim` on the batch fleet (issue #316)

- **Slug**: `sg13cmos5l-vco-decap-momcap`
- **Issue**: #316 (child of #216, Part of #199, item 9 provenance migration).
  Append-only. This record reruns `RECORD-001-decap-momcap-sensitivity.md`
  (sha256 `2f1bef8c489476c641d82f6467506f67a6107d5bcaa1ffc376c4f4407a18a5cd`,
  identical at the implementation base `6bab68d`) and is the
  `ADDENDUM-RERUN` target of `ADDENDUM-001-record-001-superseded.md`. It
  edits no earlier record and no committed `corners/` or `testbench/` file.
- **What was rerun**: RECORD-001's whole grid, same DUT line
  (`cap_cmomi w=70u l=70u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1`),
  same illustrative `R_src = 3000 ohm` (not a measured impedance), same
  delta capacitors (`C_NOM * {-0.20, 0, +0.20}` with RECORD-001's committed
  `C_NOM = 5.286175e-12 F`): 3 temperature extractions (-40/27/125 C) and 3
  MOM-fraction pole sweeps at 27 C. The claim is unchanged: `XCDECAP`'s own
  capacitance and the fractional pole shift it implies. The rows' absolute
  jitter / ripple numbers stay `insufficient-evidence`, for the reasons
  RECORD-001 gives.
- **Command** (repository root; `KLT_SIM_BACKEND=batch` exported by the daemon):

  ```
  PDK_ROOT=$HOME/share/pdk python3 -I sim/sg13cmos5l-vco-decap-momcap/testbench/gen_rerun316_requests.py /tmp/r316
  cd /tmp/r316 && klt sim --batch-set extract/request.json pole_m20/request.json \
    pole_p00/request.json pole_p20/request.json --wait-for-capacity 600 \
    --format json --report-out batch-report.json -o out
  ```

  Each request has `backend: batch`, `models.pdk: ihp-sg13cmos5l`,
  `options.stage_model_inputs`, `batch.capacity_wait_s: 600`. A first submit
  with `models.pdk_root` set was refused client-side before anything was
  uploaded (`batch_set_preflight_failed`, `models_pdk_root_host_path`); the
  field was dropped and the grid submitted once (`attempts: 1` for every
  member, `refused: 0`). No part of the grid ran locally.
- **Fleet evidence** (`../corners/rerun316/*/batch-receipt.json`,
  `report.json`): all four jobs `done`, exit code 0, `aws-batch-fleet`,
  `us-east-1`, Spot, runner klt `0.9.0` (client `0.9.2.dev661+g1de5c0432aad`,
  `runner_compatibility: match`).

  | Request | Job id | Instance | Type |
  |---|---|---|---|
  | `extract` (3 temps) | `klt-sim-8e4c1fe9b4c9` | `i-0c1475868c45df8b6` | c7i.8xlarge |
  | `pole_m20` | `klt-sim-a5ffddb2be39` | `i-0f7ee07c226626661` | c7i.8xlarge |
  | `pole_p00` | `klt-sim-8634a70f2bc0` | `i-09bcc552d03190758` | m7i.4xlarge |
  | `pole_p20` | `klt-sim-345808b50bc8` | `i-00a652ca5c39ba204` | c7i.8xlarge |

- **Submitting host**: `loom-worker-3` (x86-64 Linux, 8-vCPU shared worker).
  Submitted 2026-11-11 ~19:59 UTC, all four collected within ~60 s.
- **Tools**: ngspice-46 on the worker (`/usr/local/bin/ngspice`, binary sha256
  `dc859418bedd0478ff439a2d3e2e09f4386a7f4d5e3f17671953e101a000cc60`,
  Xeon Platinum 8488C). Same major version as RECORD-001's `ngspice-46`; the
  build itself was not recorded there, so build identity is not compared.
- **PDK revisions** (submitter side, checked 2026-11-11):
  PDK ihp-sg13cmos5l revision f7bca32694fe3d58be0cc7d9df4b9f5db7161a14
  (`~/share/pdk/ihp-sg13cmos5l/.pdk-store.json`: `version` =
  that commit, `synced` 2026-10-15T15:39:18Z, bundle sha256
  `3195ba7f3a74e91fc4eced64102c9d61b00d8eadcf5e795d36d926d40ab4ad31`;
  the tree is a fleet-store bundle install, **not a git checkout**, so
  `git rev-parse` was not possible), and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (`.pdk-store.json` `version` `0.3.0`, bundle sha256
  `b3943b5757f106b62bf54d3477f76e4ea6deed9ff3e9772dab598e03b9f4b863`,
  synced 2026-10-15T15:39:14Z; the commit is the pin established in
  `sim/provenance-migration.md`, not re-derived here).
  **The cmos5l revision differs from the `PDK-PIN` line in `sim/README.md`
  (`607e18d4`)**: that pin is the older legacy-split-repository checkout the
  README itself says is superseded by the unified-tree install pin
  (`f7bca326`) in #213-#218. This record cites what it actually found and
  does not edit the pin; the gate's DISCREPANCY for this line is expected
  until that switch lands.
- **Limitation: the revision of the worker's model card is not proven.** The
  decks `.include` `cap_cmomi.lib` by `$PDK_ROOT/...`, which the batch worker
  resolves inside its own image (`/opt/pdk`, variant `ihp-sg13cmos5l`). The
  worker reported no PDK `SOURCES` stamp (`stamp_scheme: null`,
  `stamp_scope: image`) and the report cannot hash the include
  (`unhashed_reason: env_var`). The revisions above therefore describe the
  *submitter's* trees, not a proven readback of what the worker read. What
  *is* proven identical is the compiled model: the three OSDI objects were
  staged from the submitter's tree (`cap_cmomi.osdi` sha256 `972ff31c…`,
  `cap_cmomf.osdi` `d44927b3…`, `r3_cmc.osdi` `746f86fd…`; the worker's
  `model_inputs` digests equal the staged ones). The submitter's local
  `cap_cmomi.lib` sha256 is
  `ea8e1e2b2efcb072c0b516138f4ef1900691d217b7f1d8a7e810efe2de5d5e9a`, for
  anyone who can hash the worker's copy.
- **Model-availability differences versus RECORD-001**: RECORD-001 loaded
  `cap_cmomi.osdi`, `cap_cmomf.osdi` and `r3_cmc.osdi` through a generated
  `.spiceinit`; here the same three objects are loaded via
  `options.osdi_preload`. `r3_cmc.osdi` is preloaded in both but no device
  in either deck instantiates it (resistor model; the decks contain only
  `cap_cmomi`, an ideal R, an ideal C and sources), so it does not affect any
  number. Both PDK trees are read (`cap_cmomi` is not symlinked, but the
  cmos5l tree symlinks its other OSDI/model paths into `ihp-sg13g2`).
  RECORD-001's host tree was `~/share/pdk/ihp-sg13cmos5l` "v0.2.0" and its
  OSDI hashes were not recorded, so OSDI identity between the two runs is
  not established. Decks no longer pass through `sed` `@PDK_ROOT@` tokens or
  `run.sh`'s `check-osdi-arch.sh` preflight (the worker is x86-64).
- **Method differences, disclosed** (`../testbench/gen_rerun316_requests.py`
  is new; `run.sh` and the templates are untouched):
  1. C is taken from `.meas ac im_z_100k FIND vi(n1) AT=100k` (1 A drive, so
     `Im(Z) = Im(v(n1))`) rather than the last row of an `ac dec 5 1k 100k`
     print; same frequency, same formula.
  2. The -3 dB pole is ngspice's own `.meas ac ... WHEN vdb(vdd_vco)=-3.0103
     CROSS=1` (interpolation linear in frequency within the `dec 20` grid)
     rather than `run.sh`'s log-frequency interpolation. This is the whole
     reason the pole values differ in the 4th digit.
  3. **As-run defect, kept as evidence**: the request's `cdecap_f` expression
     used `-1/(2*pi*100k*im_z_100k)`; the current source pulls current *out*
     of `n1`, so `Im` is **positive** (+301078 ohm) and the reported
     `cdecap_f` is `-5.28617e-12`. The magnitude is right; the sign is an
     expression error, not a physical negative capacitance. The CSV below
     recomputes `C = 1/(2*pi*100k*|im_z_100k|)` from the raw `im_z_100k`;
     both are in `report.json`. The decks were not rerun to hide it.

## Results

`../corners/results_rerun316.csv` (raw: `../corners/rerun316/*/report.json`):

| Quantity | RECORD-001 | This rerun (fleet) |
|---|---|---|
| `C_decap` at -40 / 27 / 125 C | 5.286175 pF at each | 5.28617 pF at each (6 printed digits, all three identical) |
| Pole, -20% (4.229 pF) | 12.54 MHz (`1.253945e7`) | 12.54 MHz (`1.254210e7`) |
| Pole, 0% (5.286 pF) | 10.03 MHz (`1.003271e7`) | 10.03 MHz (`1.003460e7`) |
| Pole, +20% (6.343 pF) | 8.349 MHz (`8.348879e6`) | 8.363 MHz (`8.362530e6`) |
| Span ratio (max/min) | 1.502 | 1.4998 (analytic 1.5) |

Poles agree within 0.02% (nominal), 0.02% (-20%) and 0.16% (+20%); the
spread is the interpolation difference in item 2 above, not a model change.
The ~5.29 pF figure in `design/README.md` and the "decap value only"
disposition in `spec/target-spec.md` reproduce unchanged.
`cap_cmomi` again shows no temperature coefficient for this instance.

## What this does and does not replace

- Replaces the **evidence claim** for RECORD-001's temperature-invariance and
  MOM-band pole results with a run whose submit path, instances, tool
  version and submitter PDK trees are recorded. It does **not** establish
  RECORD-001's historical environment, and does not close the
  worker-model-card gap above.
- No consumer was edited: `design/README.md` and `spec/target-spec.md` cite
  only the 5.29 pF value and the "decap value only" scope, which reproduce;
  `corners/matrix.md` describes the grid shape, which is unchanged.
  `sim/PORTING-osdi-host-arch.md`, `docs/chipalooza/challenge-6-proposal.md`
  and the spec are left alone because nothing contradicts them.
- **Not covered, unchanged from RECORD-001**: absolute jitter or ripple
  attenuation, a full-ring PSRR, mismatch, and any post-layout `R_src`.
