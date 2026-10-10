# sg13cmos5l-klt-pex-signoff

`klt pex` envelopes (T1 item 7, issue #152) for the routed blocks of the
layout record the manifest's `4.analog` citation names. That is
`20261010-012952-a4ca1b8` since #195 (RECORD-002); RECORD-001 measured
`20261003-183059-dc5644a`. This slug is separate from
`../sg13cmos5l-postlayout-pex-pvt/` (ngspice PVT campaign) because item 7
accepts only a `klt pex` JSON envelope, which that campaign never produced.

```
dut/        schematic legs (flattened from design/sg13cmos5l/netlist/ by
            flatten-schematic.py) + the klt sim testbench bodies
requests/   klt sim request JSONs (one nominal corner each)
reports/    verbatim `klt pex --format json` envelopes -- what the manifest cites
records/    RECORD-NNN, append-only
run-klt-pex.sh          regenerates one reports/pex.<block>.json
flatten-schematic.py    hierarchical design netlist -> one flat .subckt
```

`PDK_ROOT=<parent of ihp-sg13cmos5l> [KLT=<klt>] ./run-klt-pex.sh <pfd|cp|loop_filter|vco|divider_chain>`

The runner binds to the directory of the manifest's `4.analog` citation, the
same derivation the gate uses, so it cannot run against a record the gate does
not check. The committed envelopes were produced with
`klt 0.6.0+g1eb3e4bfd0f5` and ngspice-46 (see each RECORD). The installed
`psp103`/`psp103_nqs`/`mosvar` OSDI objects target OSDI v0.4. ngspice-46
loads them. ngspice-42 (OSDI v0.3 only) fails at model load. `--backend batch`
refuses `osdi_preload`.

Every request is a single corner and runs with `--backend local`. A
multi-corner or Monte Carlo version must be expressed as `klt sim` corners /
`monte_carlo` and dispatched to the batch fleet; none was run here.
`lock_detector` has no envelope on purpose (#157).

## Integrity gate (issue #170)

`manifests/check_pex_coverage.py` (run in `.github/workflows/signoff.yml`,
negative-tested by `manifests/test_check_pex_coverage.py`) validates all five
envelopes, not just the two the manifest cites: status pass, body bias
`biased` with zero unbiased devices, block identity and
`provenance.input.content_hash` against the GDS in the authoritative layout
record, and that each `dut/pll_<block>.schematic.sp` leg equals a fresh
re-flatten of its `design/sg13cmos5l/netlist/` export. `leg-provenance.json`
records the export, leg and flattener hashes. When a design export changes the
gate fails and names the block: the evidence is stale and must be regenerated
(re-flatten, `run-klt-pex.sh`, re-verify); editing the hashes alone cannot pass
because the re-flatten compare is independent. Old results are never rewritten.

**`cp` is fresh again (#195, RECORD-002).** Issue #165 / DR-010 replaced
`cp_dumpbuf` (source follower -> tracking 5T-OTA pair). From #165 until #195,
`cp` was carried as a `STALE_PENDING` entry. #195 redrew `pll_cp` (LVS
`match` 28/28 devices, 22/22 nets, DRC and ERC clean), re-flattened the leg,
re-ran all five envelopes against the new record, and emptied
`STALE_PENDING`. The mechanism is kept and negative-tested. **The cp
envelope still measures only the output current**, at DC, with one leg
steered to `VOUT`. It does not observe `VDUMP` tracking, so the DR-010
buffer's post-layout behaviour is not evidenced here (see RECORD-002's
limits).

This proves **nominal evidence integrity**, not a complete PVT or spec pass:
one corner per block, no `limits` declared. `lock_detector` remains explicitly
withheld pending #157; a `pex.lock_detector.json` appearing before the gate is
updated fails the check.
