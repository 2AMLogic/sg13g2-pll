# `erc-supply-spec.pll_cp.json` — derivation notes (issue #195)

The other four analog ERC specs carry these notes in a `_comment` key. This
spec cannot. It is run on `klt 0.6.0+g1eb3e4bfd0f5`, which rejects unknown
spec keys (klayout-tools#2243), so the notes live here. This build is needed
because the cp well tie needs `well_requires_boxes` / `well_excludes_boxes`
(klayout-tools#2540). The grading build `e6284fbe62e2` does not have these
keys and silently ignores them (see "Why not the grading build" below).

- **Input**: `layout/sg13cmos5l-pll/reports/20261010-012952-a4ca1b8/pll_cp.gds`
  (top cell `pll_cp`), the DR-010 cp (#165) with the 10-device two-OTA
  `cp_dumpbuf`.
- **Run** (repo root): `klt erc <gds> <this spec> --top pll_cp --deck sg13cmos5l --format json`.
  The exact build and command are in
  `reports/20261010-014035-a4ca1b8/run-erc.sh`.

## Stackup and vias

These are the same as every sibling spec (`../erc-supply-spec.json` provenance).
GatPoly (5/0, gate role, `active_layer` Activ 1/0) connects to Metal1 (8/0),
Metal2 (10/0), Metal3 (30/0) and Metal4 (50/0) through Cont (6/0), Via1 (19/0),
Via2 (29/0) and Via3 (49/0). Labels come from Metal1.pin (8/2) and Metal3.pin
(30/2). `--deck sg13cmos5l` carves out deck resistor bodies. cp draws none.

## Nets

- `VDD`, `VSS` (`kind: supply`, `islands: 1`): the DR-004 rails and the
  supply ports of `.subckt cp` in `design/sg13cmos5l/netlist/cp.spice` and
  in the record's `cp.reference.spice`. The same-GDS `lvs.cp.json` pairs
  them `VDD->VDD` and `VSS->VSS`. `islands` is the native form of the
  repository's earlier `expected_islands` annotation (klayout-tools#2400).
  At this build it is graded, not ignored.
- `XBUF.PSRC` (`kind: signal`, `islands: 1`): the source node of the PMOS
  OTA input pair (`cp_dumpbuf` `MP1`/`MP2`, whose bulk is `PSRC`), as labelled
  by the layout flow. LVS pairs it to the reference's `BUF_PSRC`. Declaring
  it makes `erc.net_connectivity` prove that the well tap, the two sources
  and `MTP`'s drain form a single island.

## Ties

`pll_cp` draws six merged NWell shapes, one per pfet group. Five are
labelled `VDD`. The sixth, `cp_pfet_w6_l0p5` (`MP1`, `MP2`), is labelled
`XBUF.PSRC`. It is a separate well because those two devices tie their bulk
to their own source (DR-010). `layout/sg13cmos5l-pll/diagnosis/issue-195/`
has the probe that lists the wells and their labels. One `well_layer`
therefore carries two bias classes. No PDK layer separates them, because
both are ordinary HV pfet wells. The two classes are selected with literal
geometry:

- `nwell_tap` -> `VDD`: `well_layer` 31/0, `well_excludes_boxes`
  `[[215.16, 0.34, 230.92, 4.38]]`.
- `psrc_nwell_tap` -> `XBUF.PSRC`: `well_layer` 31/0, `well_requires_boxes`
  with the same box.

The box is the `cp_pfet_w6_l0p5` instance bounding box in the GDS, rounded
outward to 0.01 um. The nearest other NWell is 7.36 um away, so the box
touches exactly one well. The two entries are complementary, so every well is
graded exactly once. The selection is the caller's assertion. klt therefore
lists both ties in `erc_coverage.checked_by_well_assertion`. The wells
themselves are still drawn geometry, and each selected shape must hold its
own tap. That tap is Cont (6/0) ∩ nSD (7/0) ∩ Activ (1/0), the curated
deck's `nSD & Activ & NWell` well tie (klayout-tools#1414), and it must
reach the tie's net.

The selection can be falsified. If the box is moved onto a `VDD` well, both
ties report `erc.missing_tie`. If the box selects no shape, or every shape,
the tie is recorded as skipped (`degenerate_well_selection`). The ERC record
contains both negative runs.

`substrate_tap` -> `VSS` keeps the sibling form. These streams draw no
p-well, so the region is set by `well_layer: null` plus `well_boxes`
(klayout-tools#2255). There is one box per nfet group cell (`cp_nfet_w2_l0p5`,
`_w2_l1`, `_w2_l3`, `_w6_l0p3`, `_w8_l1`, `_w12_l1`, `_w16_l1`), each equal to
the instance bounding box rounded outward to 0.01 um. The tap is Cont ∩ pSD
(14/0) ∩ Activ. This is weaker evidence than a drawn well and is listed under
`checked_by_well_assertion`.

## Why not the grading build

At `e6284fbe62e2` (the `klt signoff` pin in `.github/workflows/signoff.yml`),
a `ties[]` entry grades **every** merged shape of its `well_layer` against one
net. That build has `well_requires`/`well_excludes` (marker layers,
klayout-tools#2339), but no layer marks this well. It does not have the
box selectors.

Run there with the previous two-tie spec, the new `pll_cp` reports exactly one
`erc.missing_tie`: the PSRC well, bbox `[215.72, 0.34, 230.92, 4.38]`, is
"not connected to declared net 'VDD'". That finding is correct for that
spec, and it is in the ERC record.

That build also **silently ignores** unknown spec keys. Given the box keys,
it reports 6 findings instead of rejecting the spec. Unknown-key rejection
came later (klayout-tools#2243), so this is fixed upstream. It is why cp is
not run at the grading build with keys that build cannot honour.
