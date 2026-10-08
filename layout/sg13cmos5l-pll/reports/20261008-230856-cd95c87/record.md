# ERC power-delivery (structural) record, analog partition: `20261008-230856-cd95c87`

T1 item 11 evidence for the five **analog** blocks (issue #147). This is
**not a layout-flow record**. It is a derived evidence record, frozen against
the committed GDS of flow record
[`20261003-183059-dc5644a`](../20261003-183059-dc5644a/) (the current
`LATEST`, which this record does not repoint). Nothing in that record is
rewritten. The digital partition's item-11 evidence stays in
[`20260923-025442-3d7ffb4`](../20260923-025442-3d7ffb4/) unchanged.

- **klt**: `0.6.0+ge6284fbe62e2`, klayout-tools at exact commit
  `e6284fbe62e25d9b293eed07889cb80a0b87e2f4` with `klayout==0.30.10`. This is
  the grading build `.github/workflows/signoff.yml` installs. It was installed
  into a throwaway venv from a clean clone (not the host `klt`, which is
  `0.7.0+g4cbdfa769875`). Every report records it in `provenance.klt_version`
  / `klayout_version`.
- **Command**: [`run-erc.sh`](run-erc.sh), run from the repo root with
  `KLT=<venv>/bin/klt`. Each block runs
  `klt erc <gds> layout/sg13cmos5l-pll/erc-supply-spec.pll_<block>.json --top pll_<block> [--deck sg13cmos5l] --format json`.
  The four MOS blocks use `--deck sg13cmos5l`. `loop_filter` does not; see below.
- **Specs**: `layout/sg13cmos5l-pll/erc-supply-spec.pll_<block>.json`. Each
  spec's `_comment` explains how every supply, tie and box was derived.
- **Exit code 4** on every run is expected. It means the antenna half is
  `not_checked`, because klt has no sg13cmos5l antenna table
  (klayout-tools#1994/#2179). The connectivity verdict is `erc_status`.

## Verdict: all five `erc_status: "clean"`, zero findings

| Block | Top cell | GDS sha256 (= `provenance.input.content_hash` = LVS input) | Spec sha256 | Supplies (1 island each) | Ties: checked | of which `checked_by_well_assertion` | Inapplicable | Skipped / unknown | Findings | `erc_status` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pfd` | `pll_pfd` | `30588e30497221d5211eec168e71a1e326a821c65e4cb43b18aab622729f16a7` | `f61226d1…14f6` | `VDD`, `VSS` | `nwell_tap` (2 NWells), `substrate_tap` (2 boxes) | `substrate_tap` | none | none | 0 | **clean** |
| `cp` | `pll_cp` | `95c64289aabffba79a0eee418c5f2012ef4c04f710bf325124e65fd8b640872c` | `2136bac9…3f9c` | `VDD`, `VSS` | `nwell_tap` (4), `substrate_tap` (6) | `substrate_tap` | none | none | 0 | **clean** |
| `loop_filter` | `pll_loop_filter` | `8a3c9e3ee57f2b414133b9a4b0ff7a0cf3a8be889940cfaa3780587565debce3` | `9277b45d…d000` | `VSS` | none (disclosed) | none | `erc.missing_tie` (`ties_disclosed_unexpressible`) | none | 0 | **clean** |
| `vco` | `pll_vco` | `21d0d72a7ca94dda5e739863d4dc7b65378096cf879a6ad15f6a7f5ea01818f7` | `83719d90…2764` | `VDD_VCO`, `GND_VCO` | `nwell_tap` (5), `substrate_tap` (6) | `substrate_tap` | none | none | 0 | **clean** |
| `lock_detector` | `pll_lock_detector` | `54bea524f81541c7c3be3fdad14423acf47eb7a0972c07932701c3e691ac2afc` | `3f30879b…e5ee` | `VDD`, `VSS` | `nwell_tap` (2), `substrate_tap` (3) | `substrate_tap` | none | none | 0 | **clean** |

`erc_coverage.checked` also lists one `erc.floating_gate` entry per gate net
(pfd 28, cp 9, vco 15, lock_detector 14, loop_filter 1), all with zero
findings. `provenance.devices` shows the deck carve-outs (`--deck sg13cmos5l`).
In `vco`, the `rppd` carve-out is 240.0 um² (5 bodies: 30+60+60+60+30 um x
1 um) and the `rhigh` carve-out is 4.0 um². In `lock_detector`, the `rhigh`
carve-out is 350.0 um² (700 x 0.5 um). These figures match the
reference-netlist geometry, so the resistor bodies were cut and nothing else
was. `pfd` and `cp` draw no resistor.

### Where each declaration comes from

- **Supplies.** Each block's supplies are the top-level ports of
  `design/sg13cmos5l/netlist/<block>.spice`, as listed in the DR-004 rail
  table: pfd/cp/lock_detector `VDD`/`VSS`, vco `VDD_VCO`/`GND_VCO`,
  loop_filter `VSS`. Each one is also a port of the record's
  `<block>.reference.spice`. The same-GDS `lvs.<block>.json` pairs each one to
  a reference net in `net_correspondence` (`pin: true`), and those envelopes
  report `status: match`, `top: pll_<block>` and
  `reference: <block>.reference.spice`. Helper-subcircuit aliases (`VDDV`,
  `GNDV`, vco_bias's `VDD`/`VSS`) are not declared.
- **N-well tie (drawn, physically checked).** The curated deck derives a well
  tie as `nSD & Activ & NWell` (klayout-tools#1414). Here the tap is declared
  as Cont (6/0) ∩ nSD (7/0) ∩ Activ (1/0), clipped to each drawn NWell
  (31/0). The tie net is the pfet body rail of the reference (`VDD`, or
  `VDD_VCO` in vco). Each merged NWell (one per pfet group) has to hold its
  own tap that reaches that net.
- **Substrate tie (asserted, the weaker claim).** These streams draw no
  p-well or substrate polygon, so the declaration uses `well_layer: null` plus
  `well_boxes` (klayout-tools#2255). There is one box per nfet group cell,
  equal to that instance's GDS bounding box rounded outward to 0.01 um. The
  tap is Cont ∩ pSD (14/0) ∩ Activ. Each box has to hold its own tap that
  reaches the nfet body rail (`VSS`, or `GND_VCO` in vco). The region is the
  caller's assertion, not drawn geometry. That is why it is listed under
  `checked_by_well_assertion`, and why the item-11 citation carries it in
  `power_delivery.ties_checked_by_well_assertion`.
- **loop_filter: no ties, disclosed.** The stream draws no Activ, no NWell
  and no nSD. Its only pSD shape and its two Cont shapes belong to the `rppd`
  body and head contacts on GatPoly. There is no MOS, so no transistor body
  needs a tie, and no p+ tap can exist. The rppd bulk is the global substrate
  (the reference's `sub!`, extracted as `vsubs`). The MOS blocks' taps bias
  it. Asserting a substrate box here would only manufacture a finding, and
  drawing a tap to get a clean status was not done. The spec says this with
  `ties_disclosure.kind: "unexpressible"`. CI (`manifests/check_erc_coverage.py`)
  accepts that disclosure for this block only, and only after it re-reads the
  GDS and confirms that layers 1 (Activ) and 31 (NWell) are absent.

### Falsifiability probes (not committed; reproduced by mutating the committed vco spec with `jq`)

| Probe | Mutation | Result |
| --- | --- | --- |
| a | `.ties[1].net = "VDD_VCO"` (substrate boxes on the wrong rail) | `violations`, **6** `erc.missing_tie` (one per asserted box) |
| d | `.ties[0].net = "GND_VCO"` (NWells on the wrong rail) | `violations`, **5** `erc.missing_tie` (one per NWell) |
| b | `.ties[0].tap_requires = []` (bare Cont tap) | `clean_partial`, `nwell_tap` skipped `degenerate_tap_declaration` |
| c | `.ties[1].well_boxes = [[0,-0.2,540.32,91.35]]` (whole top-cell extent) | `clean_partial`, `substrate_tap` skipped `degenerate_well_assertion` |

So the committed `clean` verdicts depend on the taps actually reaching the
declared rails. They would not survive a wrong net, an unnarrowed tap or an
extent-sized assertion.

## loop_filter: the gate-less form (klt friction, filed as klayout-tools#2896)

`klt erc` exits 1 when no net carries gate-role geometry. With the MOS
blocks' form (`active_layer` plus `--deck sg13cmos5l`), loop_filter has no
such net, for two reasons. No Activ is drawn, and the deck carves out the
only GatPoly shape, which is the rppd body. The error envelope from that
form is committed as
[`erc.deckform-error.pll_loop_filter.json`](erc.deckform-error.pll_loop_filter.json).
The committed loop_filter report therefore uses a spec with no
`active_layer`, run without `--deck`. In that run the rppd body counts as the
one "gate" (`gate0`, net `NZ,VCTRL`), and it conducts VCTRL<->NZ in the
connectivity model. That is a modelling artefact. Neither net is declared,
and R1 (`VCTRL NZ`) does not touch VSS, so VSS's one-island verdict is
unaffected. Only the declared-supply verdict is used from this run. Upstream
issue klayout-tools#2896 describes the gap in general terms.

## LVS half (cited, not re-run)

The paired LVS envelopes are the committed `lvs.<block>.json` wrappers in
`20261003-183059-dc5644a` (the item-4 envelopes). The klt version differs,
but the inputs are the same: `response.provenance.input.content_hash` equals
each ERC report's input hash and the sha256 of the GDS. They were not re-run.
Their provenance (`klt 0.6.0+gdaf06a51afaf`, KLayout `0.30.12`,
`klayout_version_mismatch: true`) is already graded `input_verified: true` by
the pinned grader for item 4. The same grader also accepts it as the item-11
LVS part. `power_connectivity.status` is `unchecked` on all five, as expected
for a plain-element SPICE reference that carries its own rails. For analog
item 11, the supply requirement is the `net_correspondence` pairing, not
`power_connectivity`.

## Standing limits (not softened)

- **Antenna not checked.** klt's antenna limit table covers sky130 only, so
  every report has `status: not_checked` and every gate is `unchecked`. Item
  11 grades the `erc_findings` rules, not the overall `status`
  (klayout-tools#1994).
- **Substrate ties are asserted.** A `well_boxes` tie proves that a p+ tap
  reaching the rail sits inside each asserted nfet-group box. It does not
  prove that the box is the actual body region. That is weaker evidence than
  a drawn well. The NWell ties are the physically checked half.
- **Connectivity graph limits.** Diffusion and well continuity are not
  modelled (klayout-tools#2180). MoM capacitors are not carved by `--deck` at
  this build (their finger sets are disjoint, so they cannot merge nets).
  `expected_islands: 1` is this repo's annotation; klt ignores the key, and
  one island is the only finding-free outcome.
