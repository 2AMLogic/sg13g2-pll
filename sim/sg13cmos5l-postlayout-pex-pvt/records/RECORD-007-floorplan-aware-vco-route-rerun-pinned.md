# RECORD-007: rerun of RECORD-002 (floorplan-aware VCO route) on the pinned dual-tree PDK, grid on the batch fleet (issue #324)

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #324 (Part of #215 / #199, item 9 provenance migration).
  Append-only. This record reruns the whole flow of
  `RECORD-002-floorplan-aware-vco-route.md` (sha256
  `79a7c066cac4e00550694c266c10aa1cbe2450563d43394a70424f5966fc1630`,
  verified unchanged) and is the `ADDENDUM-RERUN` target of
  `ADDENDUM-003-record-002-superseded.md`. It edits neither
  `RECORD-002-floorplan-aware-vco-route.md` nor any historical file
  (`corners/results.csv`, `corners/rc_attribution.csv`,
  `netlist-snapshots/*`, `lvs-recheck/*`). Every new output is under a new
  name: `corners/rerun-324/`, `netlist-snapshots/rerun-324/`,
  `testbench/rerun-324/`. It supersedes only RECORD-002's *evidence claim*.
  **Item 9 stays `unmet`** (integration is #218); rerun provenance does not by
  itself make the layout evidence current.
- **Scope**: the six steps RECORD-002 lists under "Reproduce": layout flow at
  `ff8b653`, PEX re-extraction, Matrix A (120 transient rows), RC attribution
  (210 rows), LVS recheck. `pll_vco` only on the sim side, exactly as
  RECORD-002. Not rerun, by design: nothing else in the bench (RECORD-001,
  -003, -004 are #323, #325, #326).
- **PDK revisions** (checked on the run host `loom-worker-4`, 2026-11-11):
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  (`git rev-parse HEAD` of the pinned checkout, `git status --porcelain`
  empty, reflog one `clone` entry), and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (upstream `v0.3.0`; the tree is a release-tarball install,
  `.fetched-version` = `0.3.0`, not a git checkout; the revision is the pin
  verified in `sim/provenance-migration.md`). Both trees are read: the
  cmos5l tree reaches its `psp103` models and `cornerMOShv.lib` includes
  through symlinks into the sibling `ihp-sg13g2` tree, so both are cited.
  **How these exact trees were used.** This host's live `~/share/pdk` was
  re-provisioned on 2026-10-15 from the fleet PDK store (`.pdk-store.json`:
  `ihp-sg13cmos5l` upstream `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14`, which is
  *not* the repo pin) and the previous pinned checkouts were left beside it as
  `*.bak-20261015T153923Z`. Those two directories were copied unmodified
  (`cp -a`, read-only on the originals) to a scratch `PDK_ROOT=/tmp/r324/pdkroot`
  with `ihp-sg13cmos5l` and `ihp-sg13g2` as siblings; every step below ran
  against that root. klt's own provenance block confirms it
  (`provenance.pdk.version` = `git:607e18d4…`, linked tree `ihp-sg13g2`
  `fetched:0.3.0`); the four OSDI sha256 prefixes on the g2 copy are
  `psp103` `2e4299c4…`, `psp103_nqs` `839b1644…`, `mosvar` `25e64a37…`,
  `r3_cmc` `4fead17b…`, equal to the objects cited by the other pinned reruns.
- **Tools**: ngspice-46 (worker build of 2026-10-01, `/usr/local/bin/ngspice`,
  `engine_build_comparison` = `match` against the report's own banner; `klt
  sim` client `0.9.2.dev661+g1de5c0432aad`, batch runner `0.9.0`); layout flow
  and LVS recheck under the committed pin `klt 0.3.0+gfdf04f71ab39`
  (`layout/requirements.txt` at `ff8b653`, klayout 0.30.13); PEX with
  klayout-tools source at `729ee531e176`, the same one RECORD-002 names (it
  prints `klt 0.3.0+unknown`: a `git archive` export run through the pinned
  venv's interpreter, the archive-mode artifact RECORD-001 §1.1 documents).
- **Hosts**: layout flow, PEX, LVS recheck and request generation ran on
  `loom-worker-4` (x86-64 Linux, 8 vCPU, shared). The 330-unit grid ran on the
  Spot batch fleet (`us-east-1`, `c7i`/`m6i`/`m7i` instances), 33 batch jobs
  from 27 requests, ids in `corners/rerun-324/jobs.json`
  (`environment.remote.job_id` of each retained report).
  Model cards were **staged** with the job (`options.stage_model_inputs`), so the
  executed `.lib` cards are this record's pinned copies; their per-file
  sha256 are in each retained report's `environment.staged_model_inputs`
  (e.g. `cornerMOShv.lib` source `5a1f862d…`). **Limitation**: the four
  OSDI objects are *not* staged by klt; the runner loads them from its own image
  tree (`environment.osdi_preload_runner_resolved`), whose revision and hashes
  klt could not observe (`worker_environment.pdk_stamp_comparison` =
  `not_comparable`). The numerical agreement below is the only evidence that
  they behave like the pinned ones.

## Reproduction, step by step

1. **Layout flow at `ff8b653`.** `git worktree add --detach … ff8b653`, `layout/bin/setup-venv.sh`
   (installs `klayout-tools @ fdf04f71ab39`), then
   `PDK_ROOT=/tmp/r324/pdkroot PDK=ihp-sg13cmos5l layout/bin/run-pll-cmos5l-layout-flow.sh`
   (27 s). Produced record `20261111-201126-ff8b653`. **Every GDS (49 files,
   including the six `pll_*.gds` blocks) and every `compose.*.json` is
   byte-identical to the original `20260921-155747-c44fa68`.** The only
   differing files are klt's per-step JSON reports and `record.md`, and the one
   substantive difference inside them is `klayout_version` 0.30.12 -> 0.30.13.
   Summary identical: pfd 66/66, cp 20/20, loop_filter 1/3, vco 44/45,
   divider_chain 316/316, lock_detector 38/40; block DRC clean; LVS match /
   not converted as before. The layout flow therefore **did** reproduce on the
   current toolchain; the retained-failure branch of the issue did not trigger.
   (`corners/rerun-324/layout-flow.log`; the layout record itself is not
   re-committed, its GDS being identical to the committed one.)
2. **PEX.** `extraction/run-pex.sh` with `PEX_KLT_PYTHONPATH` = klt at
   `729ee531e176`. `pll_vco`: 44 devices, 33 nets, R=170 (**1435.309 ohm**
   total), C=33 (**343.427 fF**), exactly RECORD-002 §2. The extracted
   `pll_vco.pex.spice` is **byte-identical to the file committed at `ff8b653`**
   (the file in the tree today was regenerated later, with the net-name
   spelling of a newer klt, which is why it is not the baseline). Retained as
   `netlist-snapshots/rerun-324/pll_vco.pex.{spice,json}` and
   `provenance.json`. `pex-to-ngspice.py` / `make-inst.py` give the same
   output as their `ff8b653` versions.
3. **Grids as `klt sim` batch requests** (host rule: no shell-loop ngspice).
   `testbench/rerun-324/gen_requests.py` turns `run.sh` and
   `run_rc_attribution.sh` into 27 requests, one per (variant, PVT bundle);
   the band code and VCTRL point are a zipped `corners.params` axis, the
   coupled resistor corner is a `corners.process[].sections[]` bundle member
   (`cornerRES.lib`), the netlists/`.ic`/`.tran 20p 30n`/`per1` measurement are
   the originals'. A single-request probe (`none_typ`, 10 units) went first.
   Submitted with
   `PDK_ROOT=/tmp/r324/pdkroot klt sim --batch-set testbench/rerun-324/requests/*.request.json --max-in-flight 4 --capacity-retries 3 --wait-for-capacity 600 --max-units-per-job 10`.
   Envelope: `status: pass`, 27 submitted, 0 refused, all 330 units `pass`.
   `testbench/rerun-324/collect.py` writes `corners/rerun-324/results.csv`
   (120 rows, sha256 `d0c75f8799590176a7dd7c1580b0d1ab7f71af6865f024a52f4057209c8b37e5`)
   and `rc_attribution.csv` (210 rows, sha256
   `a1da7e90f111e959facf65efd7d998c06c52ab26f7e7a8bcac858c55edd076fe`) in the
   original columns and compares them to the committed ones
   (`compare.txt`).
4. **LVS recheck.** `lvs-recheck/run-lvs-recheck.sh` with the 729ee531 klt:
   verdict shape unchanged: pfd/cp/divider_chain `match`, vco `mismatch` (12;
   devices 38/45), loop_filter `mismatch` (12; 0/3), lock_detector not
   compared (`m=2` `cap_cmomi` multiplier the curated plain-element form
   cannot represent). Only the temp path in the error text, the klt version
   string and the layout record id differ from the committed summary
   (`corners/rerun-324/lvs-recheck-summary.json`).

## Result: RECORD-002's numbers reproduce

| | original | rerun |
|---|---|---|
| `results.csv`, rows | 120 | 120, all `pass`, same key set |
| `results.csv`, period vs original | -- | 120/120 within printing precision (klt prints 6 significant digits, the originals 7: e.g. `2.317949e-09` vs `2.31795e-09`); max relative diff 0.000% at that precision |
| `rc_attribution.csv`, rows | 210 | 210, all `pass`, same key set |
| `rc_attribution.csv`, period vs original | -- | median 0.000%, mean 0.004%, **max 0.098%** (`c_only`/fast/band 11/VCTRL 2.7); 210/210 within 1% |
| post-layout vs schematic frequency deviation, mean over 60 points | -22.577% | -22.577% (max pointwise difference 0.0006 pp) |
| ... by bundle typ / slow / fast | -22.56 / -23.28 / -21.89 | -22.56 / -23.28 / -21.89 |

The 0.098% worst case in the RC-attribution grid is not a rounding effect and
is not explained here (suspects: `klt sim`'s `alterparam`+`reset` flow versus
the original hand-substituted decks, and a different OpenMP/solver build); it
is two orders of magnitude below any figure RECORD-002 quotes.

**No figure in RECORD-002 or its consumers is replaced** by this rerun: it
reproduces them. The consumers (summary, sources, proposal, bench README,
spec) are therefore not edited, and no coverage is inflated.

## Retained: the first attempt on the image's own PDK (not used)

Before staging the model cards, the same 27 requests were run once with the
batch image's PDK tree (`corners/rerun-324/superseded-image-pdk-attempt/`:
`compare.txt`, `jobs.json`). All 330 units passed, but periods were on
average 1.5% from the originals (max 3.2%) in *both* arms, while the
post-layout/schematic ratio agreed to 0.11 pp mean: a common-mode shift from
a model-library revision that is not the pin. It is kept because it is the
reason staging was added, and it shows the batch image's tree is not the
pinned one. It is **not** cited as evidence for anything. During that attempt
one shard (10 of 20 units of one request) was refused outright by the fleet's
vCPU budget (`batch_no_capacity`, "304 vCPU already running ... exceeds
BATCH_MAX_VCPU=224") and completed with `--resume`. The retained evidence run
above saw five transient `batch_no_capacity` waits (logged in
`corners/rerun-324/reports/batch-set.stderr.log`), all absorbed by
`--wait-for-capacity 600` / `--capacity-retries 3`; no shard was lost. A first, hand-launched attempt that ran one request
with its output discarded (shell quoting error) was likewise not used.

## Limitations

* Rerun on a different host, ngspice binary and OSDI build than the original
  (original: "worker not named", ngspice-46). Agreement is to printing
  precision on Matrix A, to 0.098% on RC attribution; byte-identity of the
  CSV text is not claimed, only of the layout GDS and the extracted netlist.
* OSDI objects came from the runner image and are unverified (above).
* PEX uses klt `729ee531e176` as source on the pinned venv's interpreter and
  dependencies; the layout flow and LVS recheck use `fdf04f71ab39`, as the
  repo did at `ff8b653`.
* The caveats of RECORD-002 itself carry over unchanged: lumped-star,
  uncalibrated curated R/C coefficients, `pll_vco` only, MoM decap undrawn,
  VCO LVS not converted. This is not silicon correlation and not sign-off.
* The PDK pin is today's reproducibility target; this host's live PDK is a
  different upstream revision (`f7bca326…`, see above), so a third party on
  that tree would not be on the pin. The switch of the repo pin is owned by
  #213-#218, not done here.
