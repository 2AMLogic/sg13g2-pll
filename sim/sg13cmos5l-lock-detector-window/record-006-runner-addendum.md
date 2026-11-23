# RECORD-006 runner addendum: `run_rerun256.sh` is now a thin wrapper

Bench-root provenance note for
[`records/RECORD-006-rpu-body-on-vss-rerun-pinned.md`](records/RECORD-006-rpu-body-on-vss-rerun-pinned.md)
— placed here, not under `records/`, because RECORD-006 documents its own
provenance (the migration-addendum format is for records with a provenance
defect) and `records/` filenames are restricted by
`characterization/check_records.py`. Operator ruling: issue #384, option (b)
(attended `/fleet:decide` session, round 20261121-r19, r19-q203).

## What changed

RECORD-006 (#256) reran RECORD-005's nominal corner through
`testbench/run_rerun256.sh`, which it describes as a copy of `run.sh` with
only the output suffix changed ("byte-identical below the header"). That
wording described the file **as of the commit that created it, `d69621f`**,
where the full 921-line copy still lives in history. Any later edit to
`run.sh` alone would have silently falsified it, and every fix to the bench
had to be mirrored by hand into the copy.

By the ruling above, the copy was collapsed (issue #384):

- `testbench/run_rerun256.sh` is now a short wrapper that forces
  `OUT_TAG=_rerun256` (overriding any inherited value) and execs its sibling
  `run.sh`, passing arguments and exit status through.
- `testbench/run.sh` appends `${OUT_TAG:-}` to its output names only. The
  DUT snapshot still keys on `SUFFIX=bodyfix`, so both entry points select
  `netlist-snapshots/lock_detector_bodyfix.spice`.

## What this preserves

- **The reproduction command.** RECORD-006's command block
  (`NOMINAL_ONLY=1 … bash …/testbench/run_rerun256.sh`) runs the same
  campaign through the same path, unchanged. The wrapper's `exec` hands
  `run.sh` the process, so `run.sh`'s exit status — including the
  shared-host full-grid guard's exit 2 on `KLT_SIM_BACKEND=batch` hosts —
  is the wrapper's exit status.
- **Output-name separation.** RECORD-005's committed
  `corners/*_bodyfix_nominal.*` and RECORD-006's
  `corners/*_bodyfix_nominal_rerun256.*` keep their distinct names: the
  tag lands in exactly the place the old copy's one differing line put it,
  so a rerun can still never overwrite a record's committed outputs.
- **The method citations.** The method entry for RECORD-006 in
  [`characterization/sources.json`](../../characterization/sources.json)
  ("unmodified rerun of RECORD-005's nominal campaign through
  testbench/run_rerun256.sh (run.sh with the output suffix changed only)")
  and the matching prose in `characterization/SUMMARY.md`,
  `sim/provenance-migration.md` and
  `records/ADDENDUM-001-record-005-superseded.md` described the runner as of
  their writing; the wrapper makes "run.sh with the output suffix changed
  only" literally true rather than approximately true. None of those files
  changed, and no committed output or output hash moved: the seven
  `corners/*_bodyfix_nominal_rerun256.*` files are untouched.
