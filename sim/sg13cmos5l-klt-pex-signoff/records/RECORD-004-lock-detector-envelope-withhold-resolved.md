# RECORD-004: `lock_detector`'s `klt pex` envelope — the withhold resolved (issue #157)

- **Slug**: `sg13cmos5l-klt-pex-signoff`
- **Issue**: #157 (the deliberate withhold of RECORD-001/README since #152's
  audit). Append-only. Produces the sixth and last block envelope; nothing
  in RECORD-001..003, the committed legs, requests or envelopes was edited
  (`git diff --stat` shows additions plus the gate/README updates the
  promotion needs). `lock_detector` is now a gated block
  (`manifests/check_pex_coverage.py` BLOCKS), no longer in WITHHELD.
- **DUT binding**: the runner's manifest-derived layout record
  (`4.analog`) = `20261010-012952-a4ca1b8`; envelope
  `provenance.input.content_hash` = `sha256:54bea524f81541c7…` = the
  record's `pll_lock_detector.gds` (byte-identical in the issue's
  `20261003-183059-dc5644a` and in `LATEST` `20261027-175228-74cf8d0-dirty`).
  The same GDS the postlayout-pex-pvt campaign's
  `netlist-snapshots/rerun-157/` re-extraction used (its RECORD-009).
- **PDK revisions.** `sim/README.md` pins `ihp-sg13cmos5l`
  607e18d4bd9214a52575c194b4181ef449f9252f and `ihp-sg13g2`
  5cccb161f7492697cfa52eb14dc03beb00bdca9e; the envelope's own
  `provenance.pdk.version` is null (klayout-tools#3070, as in every
  committed envelope), so the pin is the citation, not a run attestation.
- **Command**:
  `PDK_ROOT=<pdk-root> ./run-klt-pex.sh lock_detector` (the runner's new
  case; `klt pex --backend local`, one nominal corner — the README's
  single-corner rule; the runner and gate derivation are unchanged).
## 1. Envelope and bench

- **Envelope** (`reports/pex.lock_detector.json`): `status: pass`, 3/0/0
  passed/failed/errored, `pin_count_mismatch`/`flat_dut_mismatch` null,
  `body_bias.status: biased` with `unbiased_device_count: 0` and empty
  unbiased-net lists — the audit step #152 withheld the block for — ,
  `corner_count: 1`, extraction deck `sg13cmos5l` (41 devices / 23 nets),
  comparison coverage fully known (3 delta rows, nothing skipped/unknown).
- **Bench** (`dut/tb_lock_detector.sp` +
  `requests/lock_detector.request.json`): a sustained-phase-error burst on
  UP (2 µs high) then release, so both of the block's paths are measured on
  top-level pins only — the fast delaywin-chain transition (~0.8 µs) and
  the slow XRPU/XCW integrating-node recovery (~3-5 µs, the RC-dominated
  path), plus the settled supply current. Measurements are
  direction-agnostic (`when v(lock)=1.65 cross=N`) because the LOCK
  polarity is the campaign's own convention, not this bench's input. The
  16 µs window is the campaign's TSTOP_MAX convention with margin.
- **Tool**: `klt 0.9.3.dev3+gd5d57daf9a14` (KLayout 0.30.13), ngspice-47,
  both legs `--backend local` on the submitting host. The committed
  five-block envelopes pinned `klt 0.6.0+g1eb3e4bfd0f5` / KLayout
  0.30.12 / ngspice-46; the envelope's own `provenance` records this run's
  versions. The extraction model statement moved with the tool generation
  (see the postlayout-pex-pvt campaign's RECORD-009 §3 for the measured
  consequence); no cross-version byte-identity is claimed.
## 2. Results (nominal `typ/novdd/27C`, schematic → extracted)

  | measurement | schematic | extracted | delta |
  |---|---|---|---|
  | `lock_cross1_t` (error-burst transition) | 828.917 ns | 1107.180 ns | +33.6 % |
  | `lock_cross2_t` (RC recovery) | 5318.92 ns | 6218.78 ns | +16.9 % |
  | `idd_lock_avg` (settled, 10-15 µs) | −94.60 nA | −180.90 nA | −91.2 % |

  The `idd_lock_avg` percentage reads large but is a nanoamp-scale
  quiescent current (−0.095 → −0.181 µA); it is the settled-lock housekeeping
  current, not a signal path. The two transition times carry the sign of
  the extracted 3.9 pF / 21.9 kΩ interconnect (postlayout-pex-pvt
  RECORD-009's numbers for this extraction).
- **`model_mismatch` disclosure**: the envelope carries `kind:
  "count_only"` — the schematic leg instantiates 2 `cap_cmomi` devices (the
  design's `XDW.XC1` is one `m=2` instance) while the extraction emits 3
  cards (the m=2 device as two drawn cells plus `XCW`), with both
  family lists empty and MOS/rhigh counts equal. Per `klt pex`'s own
  `model_mismatch` documentation this is finger/multiplier decomposition
  that never invalidates `delta[]` — and `klt lvs` reconciles the same
  split on this block: the manifest's item-4 LVS envelope on this GDS is
  `status: match`, 41/41 devices and 23/23 nets matched,
  `body_verification: verified`. The gate previously required
  `model_mismatch: null`
  outright; it now accepts exactly the benign shape (count_only with empty
  `reference_only`/`extracted_only`) and still fails every other
  divergence — a `model_set` mismatch or a count_only that names families
  remains a failure, negative-tested in
  `manifests/test_check_pex_coverage.py`.
- **Limits**: nominal-only evidence integrity, exactly like the other five
  blocks — one corner, no `limits` declared; not a PVT or spec pass. The
  PVT re-measurement of this block's post-layout behaviour is the
  postlayout-pex-pvt campaign's RECORD-009.
- **`7.analog` note**: the manifest's item-7 analog citation stays
  `pex.vco.json` (the largest-shift block; a manifest key takes one
  envelope and a list grades `invalid_evidence`). `lock_detector`'s
  envelope joins pfd/cp/loop_filter as committed, uncited, gate-checked
  item-7 evidence — the withhold that kept it out of that set is closed.
