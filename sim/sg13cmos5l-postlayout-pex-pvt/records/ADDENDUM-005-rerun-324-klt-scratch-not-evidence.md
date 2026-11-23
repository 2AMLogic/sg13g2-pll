# ADDENDUM-005: the rerun-324 klt scratch cache is superseded and NOT evidence

Append-only non-provenance note addendum (issue #398, operator ruling of
2026-11-23, option `a`; attended `/fleet:decide` session, round 20261121-r19,
r19-q201, slate r19-s17). It does not edit
`RECORD-007-floorplan-aware-vco-route-rerun-pinned.md` or any file under
`testbench/rerun-324/`. Contract: `sim/README.md` "Provenance addenda". This
addendum asserts nothing about any run's PDK revision, tool or host, replaces
no evidence claim, and resolves no provenance defect; it only discloses what
a reader grepping the bench tree needs to know before trusting what they
find.

## What is annotated

`testbench/rerun-324/requests/.klt/` — klt's own per-request scratch cache
(`.klt/sim/<request>/<corner-hash>/{.spiceinit, corner.cir, corner.json}`,
plus `batch-receipt.json`, `report.json`, `set-manifest.json`), 33 files,
36,166 bytes, committed by accident in `ff0744f` ("sim: rerun postlayout-pex-pvt
RECORD-002 flow on pinned dual-tree PDK; superseded addendum", 2026-11-11).

It is a **superseded scratch cache, not evidence**:

- It is a partial snapshot of a *different, superseded, unpinned* attempt
  than the one RECORD-007 attests. Its `set-manifest.json` lists exactly one
  of the record's 27 requests (`c_only_fast`), and its `report.json` shows
  job `klt-sim-d9fceaabf5b0`, `provenance.pdk.source = "search root:
  ~/share/pdk"`, `provenance.pdk.version = null`, and
  `environment.staged_model_inputs = null` — no PDK revision and no staged
  model cards, i.e. the run predates the pinning RECORD-007 exists to
  establish.
- Its measured corner 0 `per1 = 2.25564e-09` disagrees with the attested
  `2.30523e-09` by ~2.1%. **Do not read it as a measurement of this bench.**
- It embeds absolute host paths from a deleted Loom worktree
  (`/home/ubuntu/GitHub/sg13g2-pll/.loom/worktrees/issue-324/...`) that no
  longer exists.
- It cannot be used as rerun input either: `collect.py` needs a grid dir
  with all 27 request/report pairs plus `stdout.json`; the scratch holds
  1 of 27 reports and no `stdout.json`, and the `ngspice.log` files its
  `report.json` references are not tracked.

The files are kept only because `CLAUDE.md` ratifies `sim/` as append-only
evidence, so nothing committed under `sim/` is deleted (operator ruling on
#398). The attested per-request reports live in
`corners/rerun-324/reports/*.report.json.gz` — e.g.
`c_only_fast.report.json.gz`, job `klt-sim-bd04d83df646`,
`provenance.pdk.source = "PDK_ROOT environment variable"`,
`git:607e18d4bd9214a52575c194b4181ef449f9252f`, 12 staged model-input
entries, corner 0 `per1 = 2.30523e-09`. Recurrence is closed separately:
`.gitignore` now carries a `.klt/` rule.

ADDENDUM-FOR: sg13cmos5l-postlayout-pex-pvt/records/RECORD-007-floorplan-aware-vco-route-rerun-pinned.md
ADDENDUM-KIND: note
ADDENDUM-SHA256: 1e5e5dc7c56295474a88761c8ca68dc8e862d0b4d27a9414899cc6423f6e6981
ADDENDUM-EVIDENCE: commit ff0744f accidentally committed the 33-file (36,166-byte) klt scratch cache under testbench/rerun-324/requests/.klt/ from a superseded unpinned attempt (job klt-sim-d9fceaabf5b0, search-root PDK, staged_model_inputs null, 1 of 27 requests); #398 operator ruling 2026-11-23 option a keeps the bytes under the append-only rule and requires this annotation that they are NOT evidence.
