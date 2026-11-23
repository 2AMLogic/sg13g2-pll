#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/run_rerun256.sh
# (issue #256, child of #213, Part of #199 -- item 9 provenance migration;
# collapsed from a full copy into this wrapper by issue #384)
#
# NOT a new campaign.  RECORD-006
# (../records/RECORD-006-rpu-body-on-vss-rerun-pinned.md) reran RECORD-005's
# nominal corner through this path so the rerun could never overwrite
# RECORD-005's committed corners/*_bodyfix_nominal.* outputs.  It did so as a
# 921-line copy of run.sh whose only executable difference was the output
# suffix; that full copy is preserved at commit d69621f and is what
# RECORD-006's "byte-identical to run.sh" wording describes.  Reader note:
# ../record-006-runner-addendum.md.
#
# Now a thin wrapper: force OUT_TAG=_rerun256 (overriding any inherited value)
# and exec this directory's run.sh, which appends ${OUT_TAG:-} to its output
# names only -- the DUT snapshot stays
# netlist-snapshots/lock_detector_bodyfix.spice either way.
#
# Usage: identical to run.sh (see its header).  Environment and arguments
# pass through unchanged; run.sh's exit status -- including the shared-host
# full-grid guard's exit 2 -- is this script's exit status.  Outputs:
#   NOMINAL_ONLY=1 -> corners/*_bodyfix_nominal_rerun256.*   (RECORD-006)
#   full grid      -> corners/*_bodyfix_rerun256.* (still refused on
#                     batch-backend hosts, exactly as in run.sh)

export OUT_TAG=_rerun256
exec bash "$(dirname "${BASH_SOURCE[0]}")/run.sh" "$@"
