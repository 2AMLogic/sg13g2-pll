# ADDENDUM-001: RECORD-001 evidence claim superseded by a same-bench fleet rerun on the pinned PDK

Append-only provenance addendum (issue #318, child of #216 / Part of #199).
It does not edit `RECORD-001-kvco-band-code-table.md`. Contract:
`sim/README.md` § "Provenance addenda".

RECORD-001 cites only `ngspice-47` and an install path
(`~/share/pdk/ihp-sg13cmos5l`, `ReleaseNote.md` `v0.2.0`) — no PDK commit for
either tree it read, and its host is named only as an arm64 build host on
which `cap_cmomi.osdi`/`cap_cmomf.osdi` failed to load. No contemporaneous
evidence recovers those revisions, so the disposition is `superseded`, not
`recovered`: **this addendum asserts nothing about the original run's
environment.** It replaces RECORD-001's evidence claim with the measurement
in `RECORD-002-kvco-band-code-table-rerun-pinned.md`, which carries both PDK
revisions, the tool versions, the fleet job, the host and the command.

The rerun is full-scope (all 60 runs) and **reproduces RECORD-001's
`period_s` byte-for-byte at every one of the 60 points**, so RECORD-001's
results table, band-selection and Kvco-nonconstancy findings and its
1562.0 MHz top-of-band figure stand as measured; no figure is replaced and
no consumer is re-pointed. Unlike the sibling reruns in this campaign, the
grid did not run on the fleet image's own (unpinned, `f7bca326`) CMOS5L
tree: the pinned model closure was staged to the worker through `klt sim`'s
deck-list contract, and every unit's `host_resolved` list is empty, so the
cited revisions are the bytes that ran rather than a repo pin assumed of a
worker. Device coverage is **not** claimed identical to the original: the
two `cap_cmom*` OSDI objects that could not load on the original's arm64
host do load here, measured by a separate probe, while the rerun still keeps
`XCDECAP` stripped exactly as `run.sh` does (RECORD-002 § "Device coverage").

ADDENDUM-FOR: sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: dc3f74cbea6d8e923e343d00799572bd9cb22c8c46ef924a0ddaca7b355c4f7f
ADDENDUM-RERUN: sg13cmos5l-vco-kvco-table/records/RECORD-002-kvco-band-code-table-rerun-pinned.md
ADDENDUM-EVIDENCE: RECORD-001's full 60-unit grid (3 PVT bundles x 4 band codes x 5 VCTRL points) rerun as one klt sim deck-list request on the batch fleet (grid job klt-sim-9c012bb4ecf5, c7i.8xlarge spot in us-east-1f, ngspice-47 on the worker, runner klt 0.9.0, client klt 0.9.2.dev915; single-unit pre-probe klt-sim-58490b6bd691) against the frozen DUT snapshot with XCDECAP stripped as run.sh does; the corner-library closure and the four OSDI objects were staged from the clean ihp-sg13cmos5l 607e18d4 checkout preserved on loom-worker-4, whose model symlinks resolve into the ihp-sg13g2 5cccb161 tree, so all 60 units ran on the pinned bytes with host_resolved empty and one identical staged-include hash set; 60/60 units passed and all 60 period_s values are byte-identical to the committed corners/results.csv (14 units needed dynamic gmin stepping, disclosed); a separate probe (klt-sim-a8b56f40dc7e) shows both pinned cap_cmom* OSDI objects load on the x86-64 worker and the snapshot's own XCDECAP device simulates at 5.315078 pF, which the original's arm64 host could not do.
