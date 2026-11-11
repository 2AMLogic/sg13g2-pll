# RECORD-007: rerun of RECORD-004's 11 uA fine-trim Icp points (issue #231)

- **Slug**: `sg13cmos5l-cp-icp-trim`
- **Issue**: #231 (split from #212, Part of #199, item 9 provenance
  migration). Append-only. Reruns `RECORD-004-issue79-finetrim-icp.md`
  (sha256 `03110e5c6dd4763fbf1d3feb48e094171ff5d3d017c5636b3c54c01d191bcd73`,
  verified unchanged) and is the `ADDENDUM-RERUN` target of
  `ADDENDUM-002-record-004-superseded.md`. No original record, CSV or script
  and no `../corners/*.csv` file was edited.
- **What was rerun**: RECORD-004's claim: one trim code (11 uA), three PVT
  points (`mos_ff`/-40 C, `mos_tt`/27 C, `mos_ss`/125 C, all 3.3 V), three
  switch states, icp at Vout = 1.65 V.
- **The original ran on a different host and tool, disclosed**: RECORD-004
  was produced on an **arm64 macOS** host with **ngspice-47** and locally
  rebuilt `cap_cmomi`/`cap_cmomf` OSDI objects. This rerun ran on x86-64 Linux
  Spot instances with **ngspice-46** and the PSP/mosvar objects the runner
  provides. The two are not the same environment, and agreement between them
  is evidence of reproducibility, not of identical conditions. This bench's DUT
  uses no `cap_cmom*` device.
- **DUT, the original and not today's design**:
  `../netlist-snapshots/cp.spice`, unchanged since RECORD-004's commit
  `a724ddd` (`git diff a724ddd HEAD -- netlist-snapshots/cp.spice
  testbench/tb_cp_dc.sp.tmpl` is empty). NOT the DR-010 `cp` of `RECORD-005`.
- **Testbench, with the deviation disclosed**: as RECORD-006 (three state
  instances of the unmodified `cp` in one deck, one-point DC at 1.65 V,
  `../testbench/tb_cp_finetrim_11u.sp` from
  `../testbench/gen_finetrim_rerun231.py`), one request per PVT point because
  `klt sim` corners are a process x temperature product and the original
  needs three specific pairs, not nine. `run_issue79_finetrim.sh` is untouched.
- **PDK revisions**: PDK ihp-sg13cmos5l revision f7bca32694fe3d58be0cc7d9df4b9f5db7161a14
  (client tree `~/share/pdk/ihp-sg13cmos5l`, `.pdk-store.json` `version`;
  a bundle install, not a git checkout, so it was **not** verified against a
  git reflog), and PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e
  (client tree `.fetched-version` = `0.3.0`, the upstream `v0.3.0` pin). Both
  trees are read: the `cornerMOShv.lib` model card and the PSP/mosvar OSDI
  objects reach `ihp-sg13g2` through the cmos5l tree's symlinks.
  **The first revision differs from `sim/README.md`'s `PDK-PIN ihp-sg13cmos5l`
  (607e18d4...)**; the install steps in the same README name f7bca326 as the
  install pin and say evidence reruns on it are owned by #213-#218. It is cited
  as found, not as the pin. **The runner's own PDK tree is not established**:
  the report's `environment.remote.pdk` says `pdk stamp unreadable:
  FileNotFoundError` (`pdk_stamp_comparison`: `not_comparable`,
  `worker_stamp_unavailable`); only `cornerMOShv.lib`'s sha256
  `5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a` was
  hashed, on the client. The runner reads `/opt/pdk`.
- **Tools**: `klt 0.9.2.dev661+g1de5c0432aad` (client); batch runner
  `klt 0.9.0` (`runner_compatibility: match`, all required request features
  supported); `ngspice-46` on the runner (`/usr/local/bin/ngspice`, binary
  sha256 `dc859418bedd0478ff439a2d3e2e09f4386a7f4d5e3f17671953e101a000cc60`,
  build 2026-10-01), Linux x86-64 Spot instances (`aws-batch-fleet`, us-east-1).
  The `.spiceinit` OSDI list is `psp103`, `psp103_nqs`, `mosvar`
  (`options.osdi_preload`), exactly as the original scripts.
- **Command / host**: `klt sim --batch-set
  testbench/finetrim_issue79_mos_{ff_-40,tt_27,ss_125}.rerun231.request.json
  --wait-for-capacity 600`, reports `../reports/sim.finetrim_issue79_*.rerun231.json`.
  Batch jobs `klt-sim-d2e899835c9e` (ff), `klt-sim-4b48acb43d7c` (tt) and
  `klt-sim-388e2d401518` (ss) were submitted together. The tt (`m6i.4xlarge`)
  and ss (`m7i.4xlarge`) jobs completed, status `pass`. The ff job never
  started (no `status.json` after 300 s, a likely fleet-capacity stall) and was
  abandoned; the ff point was resubmitted alone as job
  `klt-sim-ee1f23ef4ca5` (`c7i.8xlarge`), status `pass`, and that job's result
  is the one recorded. The batch-set client was cut off by my own 590 s timeout
  before it collected, so the tt and ss reports were re-collected with
  `--attach` on their finished jobs.

## Result (rerun) against RECORD-004

| PVT | state | RECORD-004 `icp_a` | RECORD-007 `icp_a` |
|---|---|---|---|
| ff/-40 | up   | 1.100049e-05  | 1.100049e-05  |
| ff/-40 | dn   | -1.102240e-05 | -1.102240e-05 |
| ff/-40 | both | -2.191701e-08 | -2.191062e-08 |
| tt/27  | up   | 1.100050e-05  | 1.100050e-05  |
| tt/27  | dn   | -1.101848e-05 | -1.101847e-05 |
| tt/27  | both | -1.797570e-08 | -1.797020e-08 |
| ss/125 | up   | 1.100077e-05  | 1.100078e-05  |
| ss/125 | dn   | -1.101604e-05 | -1.101604e-05 |
| ss/125 | both | -1.529873e-08 | -1.529391e-08 |

Rerun CSV: `../corners/results_issue79_finetrim_rerun231.csv` (sha256
`17693a27ef5c38f1e7ac2bcfcc2dc0e23df9d42a8a22f8adf32f4fd2558bcf52`).
Four of nine `up`/`dn` pairs differ in the last printed digit at most; the
`both` residuals differ by 0.02-0.03% of themselves (about 5e-12 A). The `up`
values DR-008 consumes (11 uA bundle) are unchanged at the precision cited, so
DR-007/DR-008 and the loop-bandwidth records are not edited.

## Limitations

One code and three PVT points, as in the original. The runner's PDK tree is
unverified (see above). No repeat run was made, so run-to-run spread is
unmeasured. The residual differences are not attributed to host, tool or deck
change.
