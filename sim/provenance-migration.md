# Item 9 provenance migration — inventory and dispositions (issue #210)

Phase 1 of the #199 campaign (Part of #182). This file classifies every
record grandfathered in `_GRANDFATHERED` /
`KNOWN_DEFECTS` (`manifests/check_testbench_coverage.py`) under the addendum
contract from #198 (`sim/README.md` § "Provenance addenda"). It also records
how today's `ihp-sg13g2` pin was established.

**This phase changes no evidence.** It adds no addendum and no record, edits
no existing record, and touches no evidence consumer. All 37 records stay
unresolved and item 9 stays `unmet`. Execution belongs to the batch issues
#211–#217, and integration to #218.

- Base: `main` @ `71d71ed04bb61c2df5c7dae9cc129af80bab97cc`, 2026-10-10.
- Inventory host: `loom-worker-1`, x86-64 Linux.
- Scope: 37 records across 15 benches. That is exactly the `_GRANDFATHERED`
  tuple, cross-checked mechanically (§ "Live verification").

## Today's pins

| Tree | Pin | How established |
|---|---|---|
| `ihp-sg13cmos5l` | `607e18d4bd9214a52575c194b4181ef449f9252f` | Unchanged from #179. The worker's `~/share/pdk/ihp-sg13cmos5l` is a clean git checkout (`git status --porcelain` empty). Its reflog has a single entry, `clone` at 2026-08-25 15:54:11 UTC, with no later checkout. |
| `ihp-sg13g2` | `5cccb161f7492697cfa52eb14dc03beb00bdca9e` | **New (this issue).** Upstream `IHP-GmbH/IHP-Open-PDK` tag `v0.3.0` (lightweight tag, commit date 2026-03-11T13:53:59Z). Verified against the worker's installed tree with a separate user-space checkout (§ "Pin verification"). |

The worker's `ihp-sg13g2` tree is a release-tarball install. Its
`.fetched-version` marker reads `0.3.0` (mtime 2026-08-24 23:18 UTC). It
matches `2AMLogic/klayout-tools`'s `scripts/fetch-ihp-sg13g2.sh`, which
pins `IHP_OPEN_PDK_VERSION="0.3.0"` and writes that marker. Every tracked
file's mtime is 2026-03-11 13:53, the tag's commit time as preserved by the
tarball. The only later content is the host-local additions listed below:
- `libs.tech/ngspice/osdi/*.osdi` (built 2026-08-25 13:17);
- `__pycache__/`;
- a 2026-09-09 clone of the `openems_ihp_sg13g2` submodule at `b67d46a2`.
  It is not the gitlink `e29417aa`, and ngspice never reads it.
- `klayout/python/pycell4klayout-api/source`.

`sim/sg13g2-hbt-characterization/records/RECORD-001` (#181) independently
cited the same commit, from blob-hash identity of six model files. The
verification here covers the whole tree.

Both pins are **today's reproducibility targets**. Neither is evidence of
what any individual historical record ran against. The contract keeps the
two apart: a `recovered` addendum carries the historical revision, and the
gate reports it if it differs from the pin.

## Finding: every SG13CMOS5L transistor-level record is mixed-PDK

The upstream `ihp-sg13cmos5l` repository tracks these paths as git symlinks
(mode `120000`) into the sibling `../../../../ihp-sg13g2/` tree:
- under `libs.tech/ngspice/models/`: 26 model cards, among them
  `cornerMOShv.lib`, `cornerMOSlv.lib`, `cornerMOSCAP.lib`,
  `cornerRES.lib`, `resistors_mod*.lib`, `resistors_stat.lib`,
  `sg13g2_moshv_*.lib`, `sg13g2_moslv_*.lib`, `sg13g2_moscap_*.lib`,
  `sg13g2_svaricaphv_*.lib`, `sg13g2_esd.lib`, `sg13g2_bondpad.lib`;
- under `libs.tech/ngspice/osdi/`: `psp103.osdi`, `psp103_nqs.osdi`,
  `mosvar.osdi`, `r3_cmc.osdi`.

The only real CMOS5L-owned simulation files are `cap_cmomi`/`cap_cmomf`
(`.lib` and `.osdi`), `cornerCAP.lib`, `cornerDIO.lib`, `cornerPNP.lib`,
`diodes.lib` and the `pnpMPA` cards.

Every `sg13cmos5l-*` bench with records loads at least one symlinked file:
- 11 of them load `cornerMOShv.lib`;
- the two MOM-cap benches load `r3_cmc.osdi`, and `loop-filter-momcap`
  also loads `cornerRES.lib`;
- `klt-pex-signoff` loads both through `klt`.

So all 34 SG13CMOS5L records read content from **both** trees, whatever the
slug says. In practice:

- A `recovered` addendum for any of them needs one `ADDENDUM-PDK` line per
  tree (`ihp-sg13cmos5l` *and* `ihp-sg13g2`).
- A superseding rerun in an `sg13cmos5l-*` bench cannot at present cite its
  `ihp-sg13g2` revision. `check_record()` compares every cited revision with
  the pin for `tree_of(slug)` only, so an honest dual citation fails as a
  DISCREPANCY. This was reproduced with a probe record outside the repo. It
  is filed as **#221** and blocks the rerun path of #211–#216.
- `klt` envelopes cannot carry this provenance either:
  `provenance.pdk.version` is `null` for git-checkout and tarball installs,
  and the sibling tree is not named. Filed upstream as
  `2AMLogic/klayout-tools#3070`.

### `schmitt_rewire` (explicit mixed-PDK evidence)

`sg13cmos5l-lock-detector-window/corners/schmitt_rewire.csv` is written by
`testbench/run_schmitt_rewire.sh`. That script requires `PDK_ROOT` to hold
both trees and loops over `(pdk, netlist)` pairs. The CSV's own `pdk`
column, counted here, splits as:

| `pdk` value | rows | DUT netlist |
|---|---|---|
| `ihp-sg13cmos5l` | 54 | `design/sg13cmos5l/netlist/lock_detector.spice` (`schmitt_hv`) |
| `ihp-sg13g2` | 54 | `design/netlist/lock_detector.spice` (`schmitt_hv`) |

The only record consuming it is
`sg13cmos5l-lock-detector-window/records/RECORD-003-hysteresis-fix.md` (#66),
in its 108-row "measured on both PDKs" table. For that record the slug is
wrong twice:
- the 54 `ihp-sg13cmos5l` rows still read `ihp-sg13g2` model cards through
  the symlinks;
- the other 54 rows are pure `ihp-sg13g2` runs (`PDK=ihp-sg13g2`, OSDI from
  that tree).

Its addendum, recovered or superseding, has to account for both arms
separately. `schmitt_crowbar_variants.csv` (RECORD-004, 180 rows) is
`ihp-sg13cmos5l`-only by its `pdk` column, but it is still mixed through
the symlinks.

Mixed-PDK claims that are *not* in a `pdk` column:
- `sg13g2-divider-repair-reverification/RECORD-001` transfers the
  non-re-run stages' numbers from the CMOS5L-tree campaign
  (`sg13cmos5l-divider-nrange-retiming/RECORD-003`), on a `cmp`
  byte-identity argument.
- `sg13g2-vco-kvco-table/RECORD-001` only *compares* against the CMOS5L
  table and does not depend on it.

## Contemporaneous host evidence available

| Id | Evidence | Applies to |
|---|---|---|
| E1 | `loom-worker-1` Claude Code session transcripts under `~/.claude/projects/-home-ubuntu-GitHub-sg13g2-pll/`. Sessions `b1b5d53a…` (subagent `a7138a92…`) and `d62d0f84…` (subagent `a8f933b5…`) show the record's runs executing in `.loom/worktrees/issue-159` with `PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l`, between 2026-10-08T23:31Z and 2026-10-09T00:36Z. `ngspice --version` in the same session printed `ngspice-46`. On this host `~/.local/bin/ngspice` is still ngspice-46 and `/usr/bin/ngspice` is ngspice-42. The CMOS5L reflog (one clone, 2026-08-25) and the `ihp-sg13g2` tree state above both predate the run. **Not durable:** the transcripts exist only on this host and are not committed. #211 must quote the relevant lines, with the file hashes, in the addendum's evidence. | `sg13cmos5l-closed-loop-real-divider/RECORD-001` |
| E2 | The record's own bytes. Its "Tooling" section cites `~/share/pdk/ihp-sg13cmos5l` at git `607e18d4bd92…`, a 12-hex prefix consistent with the pin. It also cites OSDI sha256 prefixes `psp103` `2e4299c4…`, `psp103_nqs` `839b1644…`, `mosvar` `25e64a37…`, `r3_cmc` `4fead17b…`, "symlinked from the sibling `ihp-sg13g2` tree". All four equal the objects in `loom-worker-1`'s `ihp-sg13g2/libs.tech/ngspice/osdi/` today. The **`ihp-sg13g2` half is weaker.** The record hashes only the compiled OSDI objects, not the `ihp-sg13g2` model cards (`cornerMOShv.lib` etc.). Tying those to `v0.3.0` relies on the OSDI objects being host builds that sit in the `v0.3.0` tarball tree. #211 must decide whether that is enough, and otherwise supersede. | `sg13cmos5l-closed-loop-lock/RECORD-006` |
| — | Nothing else. 33 records were committed 2026-08-29 … 2026-09-23, before the oldest transcript on this host (2026-10-03). The transcripts here contain no producing run for the later `lock-detector-window/RECORD-005` (2026-10-03) or `klt-pex-signoff/RECORD-001` (2026-10-08). No PR body carries a `host=` provenance marker. Of the 35, 22 name "x86-64 Linux" or a `/home/ubuntu` Linux worker, but not *which* worker. Workers receive `~/share/pdk` by tar copy from a sibling (`2AMLogic/2am` `infra/aws/loom-worker/new-worker.md` § PDKs), so worker-1's state is evidence about worker-1 only. 9 records ran (wholly or partly) on an arm64 macOS host whose trees are unknown, and 4 name no host. | the other 35 |

Recovery is still possible for an x86-64 "superseded" row if an operator
produces, from the *producing* worker, a transcript or log of the run plus
that worker's PDK reflog and tree state. That record would then move to
`recovered`. Without it, the honest disposition is a superseding rerun.

## Inventory (37 records)

Legend:
- **Scope**: `N` means one PVT point, local single runs allowed by host
  policy. `G` means a multi-corner grid, which must go through the
  `klt sim` batch fleet.
- **PDK tree(s) read**: `cmos5l + g2 (symlinked)` means `ihp-sg13cmos5l`
  with its model cards and/or OSDI resolved into `ihp-sg13g2` (see above).
- **Evidence consumers**: from `git grep` of the record's file name at
  base. Duplicate file names are filtered by slug. The gate's own
  `_GRANDFATHERED` list and the record itself are excluded.
  - `src` = `characterization/sources.json`
  - `sum` = `characterization/SUMMARY.md`
  - `base` = `characterization/records_baseline.json`
  - `spec` = `spec/target-spec.md`
  - `prop` = `docs/chipalooza/challenge-6-proposal.md`
  - `DR-NNN` = `spec/decision-records/`
  - a bare `RECORD-NNN` = another record in the same bench
- **Disposition**: `recovered` means historical provenance is recoverable
  from evidence E1/E2. "Candidate" means the batch must still verify it
  and write the addendum. `superseded` means a new same-bench rerun that
  cites the original, carries the current pins, and replaces the evidence
  claim.

| # | Record (`sim/`-relative) | Added | Scope | PDK tree(s) read | Contemporaneous host evidence | Evidence consumers | Disposition | Batch |
|---|---|---|---|---|---|---|---|---|
| 1 | `sg13cmos5l-closed-loop-lock/records/RECORD-001-closed-loop-lock-spur-power.md` | `1da08d7` 2026-08-30 | N, multi-run | cmos5l + g2 (symlinked) | arm64 macOS (host/tree unknown) | base, prop, spec | superseded | #211 |
| 2 | `sg13cmos5l-closed-loop-lock/records/RECORD-002-pfd-reset-parity-root-cause.md` | `65e2cb6` 2026-08-30 | N, multi-run | cmos5l + g2 (symlinked) | arm64 macOS (host/tree unknown) | base, design/sg13cmos5l/pfd.sch, prop | superseded | #211 |
| 3 | `sg13cmos5l-closed-loop-lock/records/RECORD-003-pfd-reset-fix-closed-loop-rerun.md` | `d633b9d` 2026-08-30 | N, multi-run | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | base, prop | superseded | #211 |
| 4 | `sg13cmos5l-closed-loop-lock/records/RECORD-004-icp-mismatch-phase-error-diagnostic.md` | `f38b0ee` 2026-08-30 | N, multi-run | cmos5l + g2 (symlinked) | arm64 macOS (host/tree unknown) | base | superseded | #211 |
| 5 | `sg13cmos5l-closed-loop-lock/records/RECORD-005-cascbias-real-cp-static-phase-error-rerun.md` | `f54b9ef` 2026-08-30 | N | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, prop | superseded | #211 |
| 6 | `sg13cmos5l-closed-loop-lock/records/RECORD-006-cp-dynamic-charge-term-diagnostic.md` | `41699d8` 2026-10-08 | N, multi-run | cmos5l + g2 (symlinked) | x86-64 Linux shared worker; **record cites** cmos5l `607e18d4bd92` and OSDI sha256 prefixes that match worker-1 today | base, spec | recovered (candidate, E2) | #211 |
| 7 | `sg13cmos5l-closed-loop-real-divider/records/RECORD-001-repaired-divider-in-loop-nominal.md` | `33fd583` 2026-10-09 | N | cmos5l + g2 (symlinked) | **loom-worker-1**, 2026-10-08/09 session transcripts (E1) | sum, src, sim/README, spec | recovered (candidate, E1) | #211 |
| 8 | `sg13cmos5l-cp-icp-trim/records/RECORD-001-icp-trim-and-mismatch.md` | `b37918d` 2026-08-30 | G | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | base, prop, spec | superseded | #212 |
| 9 | `sg13cmos5l-cp-icp-trim/records/RECORD-002-cascode-bias-mismatch-remeasure.md` | `f54b9ef` 2026-08-30 | G | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, prop, spec | superseded | #212 |
| 10 | `sg13cmos5l-cp-icp-trim/records/RECORD-003-issue83-finetrim-icp.md` | `e54bd37` 2026-08-30 | G (targeted) | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, prop, sg13cmos5l-loop-bandwidth-pm/RECORD-003, DR-007, spec | superseded | #212 |
| 11 | `sg13cmos5l-cp-icp-trim/records/RECORD-004-issue79-finetrim-icp.md` | `a724ddd` 2026-08-30 | G (targeted) | cmos5l + g2 (symlinked) | arm64 macOS (host/tree unknown); cap_cmom* rebuilt locally | sum, src, prop, sg13cmos5l-loop-bandwidth-pm/RECORD-004, DR-008, spec | superseded | #212 |
| 12 | `sg13cmos5l-divider-nrange-retiming/records/RECORD-001-nrange-retiming-margin.md` | `1d824d3` 2026-08-30 | G | cmos5l + g2 (symlinked) | not stated; `~/share/pdk` | base, prop | superseded | #212 |
| 13 | `sg13cmos5l-divider-nrange-retiming/records/RECORD-002-pdk-root-token-fix-reverification.md` | `b8a14c8` 2026-08-30 | G (partial re-run) | cmos5l + g2 (symlinked) | Linux worker, `/home/ubuntu/share/pdk`; worker not named | base | superseded | #212 |
| 14 | `sg13cmos5l-divider-nrange-retiming/records/RECORD-003-divider-repair-reverification.md` | `a95a887` 2026-09-22 | G | cmos5l + g2 (symlinked) | Linux worker, `/home/ubuntu/share/pdk`; worker not named | sum, src, prop, sg13g2-divider-repair-reverification/RECORD-001, spec | superseded | #212 |
| 15 | `sg13cmos5l-klt-pex-signoff/records/RECORD-001-klt-pex-nominal-envelopes.md` | `e56e14a` 2026-10-08 | N, 5 blocks | cmos5l + g2 (symlinked); envelope `pdk.version` is null | not stated; klt 0.6.0 envelopes | sum, src, spec | superseded | #213 |
| 16 | `sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md` | `db36732` 2026-08-30 | G | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named (arm64 verification of a fix also mentioned) | base, design/README.md, prop, sim/PORTING-osdi-host-arch.md | superseded | #213 |
| 17 | `sg13cmos5l-lock-detector-window/records/RECORD-002-resized-window-hysteresis-chatter.md` | `07e1866` 2026-08-30 | G | cmos5l + g2 (symlinked) | arm64 macOS (host/tree unknown) | base, design/README.md, design/sg13cmos5l/delaywin_hv.sch, design/sg13cmos5l/lock_detector.sch | superseded | #213 |
| 18 | `sg13cmos5l-lock-detector-window/records/RECORD-003-hysteresis-fix.md` | `a595772` 2026-08-30 | G | cmos5l + g2 (symlinked); **plus the explicit `ihp-sg13g2` arm of `schmitt_rewire.csv`** | x86-64 Linux, `~/share/pdk`; worker not named | base, design/README.md, design/sg13cmos5l/lock_detector.sch, design/sg13cmos5l/schmitt_hv.sch, DR-006, spec | superseded | #213 |
| 19 | `sg13cmos5l-lock-detector-window/records/RECORD-004-crowbar-current-mitigation.md` | `36e4bae` 2026-08-31 | G | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, design/README.md, manifests/test_check_spec_citations.py, sim/README, spec | superseded | #213 |
| 20 | `sg13cmos5l-lock-detector-window/records/RECORD-005-rpu-body-on-vss.md` | `3fd7967` 2026-10-03 | N | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named; `/home/ubuntu/.local/bin/ngspice` | sum, src, prop, layout/sg13cmos5l-pll/README.md, spec | superseded | #213 |
| 21 | `sg13cmos5l-loop-bandwidth-pm/records/RECORD-001-loop-bandwidth-phase-margin.md` | `b37918d` 2026-08-30 | G | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, design/README.md, prop | superseded | #214 |
| 22 | `sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-icp-input-refresh.md` | `f54b9ef` 2026-08-30 | G | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, sg13cmos5l-cp-icp-trim/RECORD-002 | superseded | #214 |
| 23 | `sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md` | `ffec56a` 2026-08-30 | G | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, prop, sg13cmos5l-cp-icp-trim/RECORD-003, sg13cmos5l-cp-icp-trim/RECORD-004, sim/sg13cmos5l-cp-icp-trim/testbench/run_issue79_finetrim.sh, sim/sg13cmos5l-cp-icp-trim/testbench/run_issue83_finetrim.sh, RECORD-003, RECORD-004, sim/sg13cmos5l-loop-bandwidth-pm/testbench/run_issue79_finetrim.sh, sim/sg13cmos5l-loop-bandwidth-pm/testbench/run_issue83_finetrim.sh, DR-007, DR-008, spec | superseded | #214 |
| 24 | `sg13cmos5l-loop-bandwidth-pm/records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md` | `e54bd37` 2026-08-30 | G (targeted) | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, prop, sg13cmos5l-cp-icp-trim/RECORD-003, DR-007, spec | superseded | #214 |
| 25 | `sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md` | `a724ddd` 2026-08-30 | G (targeted) | cmos5l + g2 (symlinked) | arm64 macOS (host/tree unknown); cap_cmom* rebuilt locally | sum, src, prop, manifests/test_check_spec_citations.py, sg13cmos5l-cp-icp-trim/RECORD-004, DR-008, spec | superseded | #214 |
| 26 | `sg13cmos5l-loop-filter-momcap/records/RECORD-001-rc-corner-momcap-sensitivity.md` | `fac4e4a` 2026-08-30 | G | cmos5l + g2 (symlinked) (`cornerRES.lib`, `r3_cmc.osdi`) | not stated; `~/share/pdk` | base, design/README.md, prop, sim/sg13cmos5l-loop-filter-momcap/corners/matrix.md | superseded | #214 |
| 27 | `sg13cmos5l-loop-filter-momcap/records/RECORD-002-r1-resize-momcap.md` | `ffec56a` 2026-08-30 | G | cmos5l + g2 (symlinked) (`cornerRES.lib`, `r3_cmc.osdi`) | x86-64 Linux, `~/share/pdk`; worker not named | sum, src, sim/sg13cmos5l-loop-filter-momcap/corners/matrix.md, spec | superseded | #214 |
| 28 | `sg13cmos5l-postlayout-pex-pvt/records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md` | `d5355e1` 2026-09-19 | G, PEX | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named; klt 0.4.0 | sum, src, prop, sim/sg13cmos5l-postlayout-pex-pvt/README.md, spec | superseded | #215 |
| 29 | `sg13cmos5l-postlayout-pex-pvt/records/RECORD-002-floorplan-aware-vco-route.md` | `ff8b653` 2026-09-21 | G, PEX | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named; klt `729ee531e176` | sum, src, prop, sim/sg13cmos5l-postlayout-pex-pvt/README.md, spec | superseded | #215 |
| 30 | `sg13cmos5l-postlayout-pex-pvt/records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md` | `07751ca` 2026-09-21 | G, PEX | cmos5l + g2 (symlinked) | x86-64 Linux **and** arm64 macOS (re-measured on both) | sum, src, prop, sim/sg13cmos5l-postlayout-pex-pvt/README.md | superseded | #215 |
| 31 | `sg13cmos5l-postlayout-pex-pvt/records/RECORD-004-postlayout-pex-pvt-loop-filter-and-divider-chain.md` | `bd62f15` 2026-09-23 | G, PEX | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named (8-core) | sum, src, prop, sim/sg13cmos5l-postlayout-pex-pvt/README.md | superseded | #215 |
| 32 | `sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md` | `fac4e4a` 2026-08-30 | G | cmos5l + g2 (symlinked) (`r3_cmc.osdi`) | not stated; `~/share/pdk` | base, design/README.md, prop, sim/sg13cmos5l-vco-decap-momcap/corners/matrix.md, spec | superseded | #216 |
| 33 | `sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md` | `b37918d` 2026-08-30 | G | cmos5l + g2 (symlinked) | x86-64 Linux, `~/share/pdk`; worker not named | base, prop, manifests/test_check_spec_citations.py, spec | superseded | #216 |
| 34 | `sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md` | `db5ec6a` 2026-08-29 | G | cmos5l + g2 (symlinked) | arm64 build host (cap_cmom* failed to load); x86-64 also named | sum, src, prop, sim/sg13cmos5l-divider-nrange-retiming/testbench/tb_div_retime.sp.tmpl, DR-005, spec | superseded | #216 |
| 35 | `sg13g2-divider-repair-reverification/records/RECORD-001-divider-repair-reverification.md` | `e643c39` 2026-09-23 | G (partial; rest transferred) | g2 (fresh runs) + **cmos5l-tree results transferred** from `sg13cmos5l-divider-nrange-retiming/RECORD-003` | Linux worker, `/home/ubuntu/share/pdk`; worker not named | sum, src, spec | superseded | #217 |
| 36 | `sg13g2-lock-detector-window/records/RECORD-001-resized-window-hysteresis-chatter.md` | `40b020e` 2026-08-31 | G | g2 | x86-64 Linux, 8 cores, `~/share/pdk/ihp-sg13g2`; worker not named | sum, src, design/README.md, sim/README, sim/sg13g2-lock-detector-window/README.md, sim/sg13g2-lock-detector-window/corners/matrix.md, spec | superseded | #217 |
| 37 | `sg13g2-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md` | `b3031f6` 2026-09-09 | G | g2 | arm64 macOS (host/tree unknown) | sum, src, manifests/test_check_spec_citations.py, spec | superseded | #217 |

Totals:
- 2 `recovered` candidates: #7 (E1) and #6 (E2).
- 35 `superseded`.
- Every one of the 34 `sg13cmos5l-*` rows is mixed-PDK.
- #18 also carries the explicit `ihp-sg13g2` `schmitt_rewire` arm.
- #35 transfers CMOS5L-tree results.

## Execution batches

| Batch | Records (rows above) | Recovered | Superseded (N / G) | Flags |
|---|---|---|---|---|
| #211 closed-loop lock + real divider | 1–7 | 2 (#6, #7) | 5 (5 N / 0 G) | **Decompose.** 5 reruns × (record + addendum + regenerated CSVs) exceeds 8 files. Split the two recovery addenda (no simulation) from the 5 nominal reruns. Reruns must rebuild each original's DUT from git history at its commit, because later records overwrote the bench's `corners/` and snapshots. Original runtimes were roughly 7–50 min per deck, several decks per record. Blocked on #221 for the rerun half. |
| #212 charge pump + divider retiming | 8–14 | 0 | 7 (0 N / 7 G) | **Blocked + decompose.** All grids. `klt sim`'s batch backend refuses `ihp-sg13cmos5l` (`2AMLogic/klayout-tools#2727`, open), and host policy forbids local grids. Exceeds 8 files. Also blocked on #221. |
| #213 PEX sign-off + lock detector | 15–20 | 0 | 6 (2 N / 4 G) | **Decompose.** #15 (`klt pex`, 5 single-corner blocks) and #20 (nominal) can run locally. #16–#19 are grids, blocked on klayout-tools#2727. #18 needs both `schmitt_rewire` arms. Coordinate #139 (RECORD-005's owed full grid). Blocked on #221. |
| #214 loop bandwidth + loop filter | 21–27 | 0 | 7 (0 N / 7 G) | **Blocked + decompose.** All grids (klayout-tools#2727). Exceeds 8 files. Coordinate #203 and DR-007/DR-008, which cite #23/#24. Blocked on #221. |
| #215 post-layout PEX/PVT | 28–31 | 0 | 4 (0 N / 4 G) | **Blocked + decompose.** PEX grids (klayout-tools#2727). 4 × (record + addendum + CSVs) exceeds 8 files. Recovered or superseded provenance does not make stale layout evidence current. Blocked on #221. |
| #216 SG13CMOS5L VCO family | 32–34 | 0 | 3 (0 N / 3 G) | **Blocked; borderline size** (about 9 files). Grids (klayout-tools#2727). #34 originally ran on arm64 with `cap_cmom*` unavailable, so its rerun differs in device set as well as host. Blocked on #221. |
| #217 SG13G2 divider, lock detector, VCO | 35–37 | 0 | 3 (0 N / 3 G) | **Blocked; borderline size** (about 9 files). The batch fleet cannot run PSP/OSDI MOS grids for `ihp-sg13g2` today: the runner has no OSDI objects (see `sg13g2-hbt-characterization/RECORD-001` "Batch failures", `2AMLogic/klayout-tools#2570`, #2901). #35's transferred CMOS5L-tree stages must be re-measured or explicitly scoped out. Not blocked on #221 (single tree). |

No batch can finish its grid reruns until a fleet route exists for these
PDKs. That is a tool and worker-spec gap, not a design gap, and it is
reported here rather than worked around locally.

## Pin verification (live, 2026-10-10, `loom-worker-1`)

The commands below were run in a fresh temporary directory. Nothing was
written to `~/share/pdk` or to any host-wide path. `TMPDIR` was unset, so
`mktemp` used `/tmp`.

```console
$ D=$(mktemp -d /tmp/issue210-ihp-open-pdk.XXXXXX)        # -> /tmp/issue210-ihp-open-pdk.EyxJSe
$ git -C "$D" clone --no-checkout --filter=blob:none https://github.com/IHP-GmbH/IHP-Open-PDK ihp-open-pdk
Cloning into 'ihp-open-pdk'...
$ R=$D/ihp-open-pdk
$ git -C "$R" rev-parse 'v0.3.0^{commit}'; git -C "$R" cat-file -t v0.3.0
5cccb161f7492697cfa52eb14dc03beb00bdca9e
commit
$ git -C "$R" -c advice.detachedHead=false checkout 5cccb161f7492697cfa52eb14dc03beb00bdca9e
HEAD is now at 5cccb161 Merge pull request #865 from IHP-GmbH/dev
$ git -C "$R" remote get-url origin
https://github.com/IHP-GmbH/IHP-Open-PDK
$ git -C "$R" rev-parse HEAD
5cccb161f7492697cfa52eb14dc03beb00bdca9e
$ git -C "$R" describe --tags --exact-match HEAD
v0.3.0
$ git -C "$R" log -1 --format='%H %cI %s' HEAD
5cccb161f7492697cfa52eb14dc03beb00bdca9e 2026-03-11T13:53:59+00:00 Merge pull request #865 from IHP-GmbH/dev
$ git -C "$R" rev-parse HEAD:ihp-sg13g2
09e38a29fdfa9156a5953ca7cd2b0f49e09c785c
$ git -C "$R" ls-remote origin refs/tags/v0.3.0
5cccb161f7492697cfa52eb14dc03beb00bdca9e	refs/tags/v0.3.0
$ git -C "$R" status --porcelain | wc -l
0
$ git -C "$R" ls-files ihp-sg13g2 | wc -l              # includes 5 submodule gitlinks
4907
$ cat ~/share/pdk/ihp-sg13g2/.fetched-version
0.3.0
$ diff -rq "$R/ihp-sg13g2" ~/share/pdk/ihp-sg13g2 | grep -c '^Files '                              # differing files
0
$ diff -rq "$R/ihp-sg13g2" ~/share/pdk/ihp-sg13g2 | grep -vc '^Only in /home/ubuntu/share/pdk/ihp-sg13g2'   # files missing from the install
0
$ diff -rq "$R/ihp-sg13g2" ~/share/pdk/ihp-sg13g2          # all 18 lines: host-local additions only
Only in /home/ubuntu/share/pdk/ihp-sg13g2: .fetched-version
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/klayout/python/import_netlist: __pycache__
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/klayout/python/pycell4klayout-api: source
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/klayout/python/sg13g2_native_pcell_lib: __pycache__
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib: __pycache__
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp: __pycache__
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/ngspice: osdi
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: .git
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: .gitattributes
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: .gitignore
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: LICENSE
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: README.md
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: doc
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: more_examples
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: pyproject.toml
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: scripts
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: stackup_editor
Only in /home/ubuntu/share/pdk/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2: workflow
$ git -C "$R" rev-parse origin/HEAD                       # upstream main has moved on
5e6d592e4002946a4616f798c357f0f3c06cf3b6
$ git -C "$R" diff --stat HEAD origin/HEAD -- ihp-sg13g2/libs.tech/ngspice/models | tail -1
 23 files changed, 1098 insertions(+), 114 deletions(-)
$ sha256sum ~/share/pdk/ihp-sg13g2/libs.tech/ngspice/osdi/*.osdi
25e64a374ab523dbfeb7ffed75dcb8b086ee10f06120a9074bd68b92d7b0fb41  .../mosvar.osdi
2e4299c4683997e26469410dc1ab36b02ced924b1ac0972d6c4eae360e1fc796  .../psp103.osdi
839b164483205601c09032951f6c41d3580f15e506dc40a7202950d3afbdfc7d  .../psp103_nqs.osdi
4fead17bc2e9cbfe3df6f106e9dbd6f2cdcd48c002af9c56c2ca0b0712fce350  .../r3_cmc.osdi
```

CMOS5L tree, read-only:

```console
$ git -C ~/share/pdk/ihp-sg13cmos5l rev-parse HEAD
607e18d4bd9214a52575c194b4181ef449f9252f
$ git -C ~/share/pdk/ihp-sg13cmos5l reflog --date=iso
607e18d HEAD@{2026-08-25 15:54:11 +0000}: clone: from https://github.com/IHP-GmbH/ihp-sg13cmos5l.git
$ git -C ~/share/pdk/ihp-sg13cmos5l status --porcelain | wc -l
0
$ git -C ~/share/pdk/ihp-sg13cmos5l ls-files -s libs.tech/ngspice/models/cornerMOShv.lib libs.tech/ngspice/osdi/psp103.osdi
120000 59bb2f74f7f0a1f9dfcaff025b4e760148800e5f 0	libs.tech/ngspice/models/cornerMOShv.lib
120000 a161715d2fab3411804d8423225e80f004a3b196 0	libs.tech/ngspice/osdi/psp103.osdi
```

## Live verification (this phase)

- `python3 manifests/check_testbench_coverage.py` with the new pin prints
  `OK: 17 benches indexed; 37 grandfathered records, 37 unresolved`. That
  is 37 `known (follow-up #182)` notes, 0 resolved, no DISCREPANCY. The
  manifest still cites no item-9 evidence and the tier report still grades
  item 9 unmet.
- `python3 manifests/test_check_testbench_coverage.py`: 51 tests pass.
  One test needed a fixture fix. `test_unknown_pin_fails_once_nothing_grandfathered`
  relied on the committed README still having an `UNKNOWN` pin. It now
  writes `PDK-PIN ihp-sg13g2 UNKNOWN` into its temporary copy, so it still
  exercises the same check. The gate itself is unchanged.
- `characterization/check_records.py`, `characterization/gen_summary.py --check`
  and `manifests/check_spec_citations.py` still pass.
- Inventory coverage: the 37 paths in the table above are compared
  mechanically with `_GRANDFATHERED`. Both sets are equal, in the same
  order, with no duplicates, and every path exists.
- `git diff --name-status origin/main` lists only:
  - `sim/README.md` (M)
  - `manifests/test_check_testbench_coverage.py` (M, fixture only)
  - this file (A)

  No record, addendum, or evidence consumer is added or changed.
