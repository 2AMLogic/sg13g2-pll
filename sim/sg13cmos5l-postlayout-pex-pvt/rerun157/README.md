# rerun157/ — append-only re-extraction and re-measurement for issue #157

The committed top-level snapshots, provenance roll-up and RECORD CSVs of
this campaign are never edited in place; #157's evidence lives under this
directory and in `corners/*-rerun157.*`, following the `rerun-324/`
precedent. Evidence record: `records/RECORD-009-lock-detector-reextraction-and-pex-remeasurement.md`.

    netlist-snapshots/rerun-157/   the fresh extraction (script-reproducible via
                                   extraction/run-pex.sh's PEX_BLOCKS/PEX_SNAP_SUBDIR)
    corners/*-rerun157.*           the batch-fleet re-measurement CSVs
    tools/                         the ngspice replay/record shim cycle (below)
    analyze_pfd_ld.log             testbench/analyze_pfd_ld.py stdout for the rerun

## tools/ — the bridge cycle

Shape copied from `rerun325/tools` (#325's provenance migration rerun); the
scratch paths are environment variables here, not literals.

    LD157_TREE=<scratch repo tree> LD157_RUN=<state dir> PDK_ROOT=<pdk root>

  ngspice-bridge  `ngspice -b DECK` shim: cache hit -> replay the batch
                  result; miss -> record the deck + referenced WORK files
                  into $LD157_PENDING, exit 0 silently. runpass.sh
                  materialises it as `$LD157_RUN/shim-bin/ngspice` and puts
                  ONLY that directory first on PATH — a shim file named
                  anything other than `ngspice` falls through to the real
                  ngspice and runs the grid locally, which is exactly what
                  the batch driver exists to prevent.
  runpass.sh N    one runner pass (unmodified testbench/run_lock_detector.sh)
                  through the shim; writes $LD157_RUN/passN.log. A pass may
                  die early on a still-unsolved dependency (empty replay) —
                  that is the protocol, not a failure.
  passdeck.py     convert: pending decks -> deck-list request dir
                  (abs paths -> $PDK_ROOT, .spiceinit osdi -> pre_osdi).
                  ingest: unit results -> the shim's cache.
  submit.sh       `klt sim --backend batch --wait-for-capacity 600`; never
                  local, never a capacity-refusal fallback.

Cycle until `runpass.sh` reports `pending=0`; that pass's reduction is the
committed CSV set. #157's run: passes 1-10, submits in RECORD-009's table.
