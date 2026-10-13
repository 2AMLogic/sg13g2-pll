# RECORD-003: rerun of RECORD-001's five-block nominal `klt pex` flow on the pinned dual-tree PDK (issue #255)

- **Slug**: `sg13cmos5l-klt-pex-signoff`
- **Issue**: #255 (child of #213, Part of #199, item 9 provenance migration).
  Append-only. This record reruns `RECORD-001-klt-pex-nominal-envelopes.md`
  (sha256 `6d27e42d100ebda96fb297222d1ab6a3b8debbada9d5cd65f002bdb403108eee`,
  verified unchanged) and is the `ADDENDUM-RERUN` target of
  `ADDENDUM-001-record-001-superseded.md`. It does not edit RECORD-001,
  RECORD-002, `reports/pex.*.json` (the current envelopes, which measure a
  different layout record) or any consumer. New outputs live only under
  `reports/rerun255/`.
- **Scope, stated plainly**: all five blocks of RECORD-001 (`pfd`, `cp`
  (two legs), `loop_filter`, `vco`, `divider_chain`), one nominal corner
  each (`mos_tt`, plus `res_typ`/`cap_typ` where the block has R/C; 27 C;
  3.3 V), `--backend local`, single-unit runs. No grid, no PVT, no Monte
  Carlo, no batch submission. RECORD-002 (DR-010 cp redraw) and
  `lock_detector` (#157) are out of scope.
- **Reconstructed original inputs**:
  - Layout: `layout/sg13cmos5l-pll/reports/20261003-183059-dc5644a/pll_<block>.gds`
    (the record RECORD-001 measured, still in the tree). Each envelope's
    `provenance.input.content_hash` equals the original's, so the GDS bytes
    are identical.
  - `dut/` (schematic legs and testbench bodies) and `requests/` are taken
    from commit `e56e14a` (the commit that added RECORD-001) via
    `git archive`, **not** from today's tree: the cp leg was re-flattened
    for DR-010 in `51e583a` (#195), so today's `dut/pll_cp.schematic.sp`
    is not the original. The other four legs are unchanged between the
    two commits.
  - Flow: `run-klt-pex-rerun255.sh` (new), a copy of `run-klt-pex.sh` as of
    `e56e14a` with the fixed layout record, the archived inputs, and the
    output redirected to `reports/rerun255/pex.<block>.json`.
- **PDK revisions** (checked on the run host, 2026-10-13):
  PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f
  (`git -C ~/share/pdk/ihp-sg13cmos5l rev-parse HEAD`), and
  PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (upstream `v0.3.0`; the host tree is a release-tarball install,
  `.fetched-version` = `0.3.0`, not a git checkout; the revision is the pin
  established in `sim/provenance-migration.md`). Both trees are read: the
  `cornerMOShv.lib` model card and the PSP/mosvar OSDI objects the requests
  preload are symlinks from the cmos5l tree into the sg13g2 tree. The
  envelopes' own `provenance.pdk.version` is still `null` (klt does not
  record it), so the revisions above come from the host, not the envelope.
- **Tools**: `klt 0.7.1.dev228+g2f51907f7f2e` (envelope
  `provenance.klt_version`; RECORD-001 used `0.6.0+g1eb3e4bfd0f5`), KLayout
  0.30.12, ngspice-46 (a user-space scratch build left on this host by
  another sweep, `/tmp/issue-584-ngspice/prefix/bin/ngspice`, sha256
  `cc3ad3951c86155806229a8a2257be60d2db01d090f5a160c401632791fd82b7`; its
  build recipe was not verified here), deck `sg13cmos5l` (hash
  `sha256:7c8784c2...a34bf` now; `sha256:db9f44fa...c222a` in RECORD-001,
  so the deck inside klt changed between 0.6.0 and 0.7.1; unreleased in
  both), Python 3.12.3.
- **Host**: `loom-worker-3`, x86-64 Linux, 8 vCPU shared dispatch worker.
  `KLT_SIM_BACKEND=batch` is exported by the daemon; the runs used
  `--backend local` explicitly (nominal single corner).
- **Command** (per block, from the repository root; `PATH` led by a
  directory whose `ngspice` is a 3-line wrapper that execs the ngspice-46
  scratch build under `taskset -c 0,1`, because the host's provisioned
  `/usr/bin/ngspice` is ngspice-42 and cannot load the PSP OSDI objects):

  ```
  PDK_ROOT=$HOME/share/pdk PATH=/tmp/ngs46-255:$PATH \
    sim/sg13cmos5l-klt-pex-signoff/run-klt-pex-rerun255.sh <block>
  # which runs: klt pex layout/sg13cmos5l-pll/reports/20261003-183059-dc5644a/pll_<block>.gds \
  #   <archived e56e14a requests...> --deck sg13cmos5l --top pll_<block> \
  #   --pdk ihp-sg13cmos5l --pdk-root $PDK_ROOT --pins <pins> --backend local \
  #   --outdir <tmp> -o <tmp>/pll_<block>.pex.spice --format json \
  #   > sim/sg13cmos5l-klt-pex-signoff/reports/rerun255/pex.<block>.json
  ```

## Result

Envelope `status: pass` for all five blocks, `body_bias: biased` with zero
unbiased devices, device and net counts equal to RECORD-001's. Every
measurement reproduces RECORD-001 to the digits RECORD-001 prints.

| Block | Row | Schematic | Extracted | delta | Original delta (RECORD-001) |
| --- | --- | --- | --- | --- | --- |
| `pfd` | `up_avg` (V) | 0.0444679 | 0.0790851 | +77.848 % | +77.85 % |
| `pfd` | `dn_avg` (V) | 0.374396 | 0.409031 | +9.251 % | +9.25 % |
| `cp` | `icp_up_a` (A) | 1.000047e-5 | 1.001774e-5 | +0.173 % | +0.173 % |
| `cp` | `icp_dn_a` (A) | -1.00175e-5 | -1.00226e-5 | -0.051 % | -0.051 % |
| `loop_filter` | `t63_nz_s` (s) | 6.8243e-7 | 8.84742e-7 | +29.646 % | +29.65 % |
| `vco` | `clk_period_s` (s) | 1.45372e-9 | 3.64896e-9 | +151.008 % | +151.0 % |
| `divider_chain` | `div_period_s` (s) | 6.40003e-7 | 6.39989e-7 | -0.002 % | -0.002 % |
| `divider_chain` | `ck_period_s` (s) | 1.0e-8 | 1.0e-8 | 0.0 % | 0.0 % |

Programming word 000000 (divide-by-64), as in RECORD-001. A field-by-field
comparison of each rerun envelope against the one committed at `e56e14a`
shows only these differences: the klt version and deck hash above;
`request`/`reference_netlist`/`schematic_netlist` paths (the archived inputs
are outside the repository, so klt reports `scope: external`, `path: null`);
and a new `extraction.parasitic_integrity` block that klt 0.7.1 emits and
0.6.0 did not (all of its checks pass). For `loop_filter` and `vco` the
`extraction.netlist_sha256` also differs from the original while the device
and net counts and every measured value are unchanged; the cause was not
investigated (plausibly a klt/deck change in netlist serialisation).

## Limits and failures retained

- **One failed attempt is retained**: the first `pfd` run used the host's
  provisioned ngspice-42, which refuses the PSP OSDI objects ("NGSPICE only
  supports OSDI v0.3 but ... targets v0.4"). `klt pex` exited 4 with
  `status: error`, both rows `error`. Its envelope is kept verbatim as
  `reports/rerun255/pex.pfd.attempt1-ngspice42-errored.json`
  (sha256 `9ec3a71133693759164383516c16e66c592df39ccf0489f2e72d8f412e05c52f`).
  This is a host-spec gap (no ngspice-46 in the worker image), not a design
  result; it is reported in the PR for the worker spec, and nothing on the
  host was changed.
- The `divider_chain` run was twice interrupted by the dispatching session
  (the ngspice-46 build ran on ~4.5 cores, over the host's budget; the
  second attempt was killed mid-run and its truncated envelope was
  deleted). The reported envelope is the third, uninterrupted run, with
  ngspice pinned to 2 cores (`taskset -c 0,1`), 11 min 24 s wall. The
  `pfd`, `cp`, `loop_filter` and `vco` runs (each under a minute) ran
  before that cap was added.
- These are **nominal, pre-signoff diagnostics on the OLD layout record**
  (`20261003-183059-dc5644a`, original cp). The vco, pfd and loop_filter
  deltas are large and real, exactly as RECORD-001 says. No request
  declares `limits`, so `pass` means "ran and compared", not "met a spec".
- **This does not make the current PEX or whole-design sign-off current.**
  The authoritative layout record is `20261010-012952-a4ca1b8` (RECORD-002);
  `reports/pex.*.json` still describe it and are untouched. This record
  re-measures RECORD-001's claim only, on the pinned PDK and the current
  tool. Nothing here re-extracts `lock_detector` (#157), runs a PVT grid
  (#139), or touches RECORD-002's DR-010 cp redraw.
- Same-tool-version caveat: the original envelopes were made with klt 0.6.0;
  the rerun uses 0.7.1.dev228 and a different (unreleased) deck hash, so
  agreement is evidence about this tool/deck pair, not byte reproduction of
  the 0.6.0 run.
