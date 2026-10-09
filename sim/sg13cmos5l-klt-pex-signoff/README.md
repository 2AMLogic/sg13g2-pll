# sg13cmos5l-klt-pex-signoff

`klt pex` envelopes (T1 item 7, issue #152) for the routed blocks of layout
record `20261003-183059-dc5644a`. This slug is separate from
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

`PDK_ROOT=<parent of ihp-sg13cmos5l> ./run-klt-pex.sh <pfd|cp|loop_filter|vco|divider_chain>`

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

This proves **nominal evidence integrity**, not a complete PVT or spec pass:
one corner per block, no `limits` declared. `lock_detector` remains explicitly
withheld pending #157; a `pex.lock_detector.json` appearing before the gate is
updated fails the check.
