# ERC power-delivery (structural) record — `20260921-155144-00b0094`

T1 item 11 evidence for the composed + routed divider chain, per
[issue #103](https://github.com/2AMLogic/sg13g2-pll/issues/103):
the first `klt erc` supply read written for an IHP SG13-family PDK anywhere in
the fleet. This is **not** a layout-flow record (those are produced by
`layout/bin/run-pll-cmos5l-layout-flow.sh`); it is a derived evidence record
frozen against the committed artifacts of flow record
[`20260830-204105-457cf5b`](../20260830-204105-457cf5b/) — its `pll_divider_chain.gds`
is the unchanged input here (content-hash below) and nothing in that record is
rewritten.

- **klt**: `0.5.0+gb15edf5e3a2e` — klayout-tools pinned by exact upstream
  commit `b15edf5e3a2e56467a3406c98a2555eb1a5ae45c` for this run only (the
  repo's own `layout/requirements.txt` pin `fdf04f71` predates `klt erc`'s
  `status`/`provenance` stamping, #1984/#2049, which is what lets this record
  pin its inputs by content-hash). Both committed reports self-attest this
  build in `provenance.klt_version`.
- **Input layout**: `../20260830-204105-457cf5b/pll_divider_chain.gds`,
  `provenance.input.content_hash` =
  `sha256:8b57386f6dad5d3a928cdf6b40269920149895ffedef5d2832148cf21645afed`
  — identical to the committed GDS (verified by `sha256sum` at commit time).
- **Specs** (committed at `layout/sg13cmos5l-pll/`): `erc-supply-spec.json`
  (sha256 `25dc7084…`, the #103 item-11 artifact — `ties[]` deliberately
  omitted) and `erc-welltie-check-spec.json` (sha256 `3f3eefb2…`, the
  supplementary checked-tie probe — see below).

## Verdict: `erc_status: "clean"` on both reads — one island per declared supply, zero supply findings

| Read | `erc_findings` | `erc_status` | `status` (antenna half) | `erc.missing_tie` |
| --- | --- | --- | --- | --- |
| `erc.supply-spec.pll_divider_chain.json` | **0** | **`clean`** | `not_checked` | **not computed** — `erc_coverage.inapplicable: no_ties_declared` |
| `erc.welltie-check.pll_divider_chain.json` | **0** | **`clean`** | `not_checked` | **checked** (`pfet_row_nwell_tap` in `erc_coverage.checked`), zero findings |

- **Zero `erc.unconnected_net`** and **zero `erc.supply_short`** naming either
  declared supply (`VDD_DIV`, `VSS`): each resolves to exactly **one**
  electrical island — `erc.unconnected_net` fires on zero matches *and* on
  more than one, so a zero finding count is the positive one-island verdict,
  not merely an absence.
- **Antenna half honestly `not_checked`**: `klt erc`'s antenna-ratio limit
  table is sky130-only, so on this PDK every level reports `verdict:
  "unchecked"` and the overall `status` follows it (`not_checked`, exit 4) by
  design. Item 11 grades the `erc_findings` rules, never the overall `status`
  (klayout-tools#1994) — the sg13g2/sg13cmos5l antenna-limit table remains an
  untranscribed upstream gap.
- **91 gate nets** discovered; zero `erc.floating_gate`. The `VDD_DIV` cluster
  carries 7.0 µm² of real gate-oxide area (4 gate fingers): these are the NAND
  input devices of the `XD5` divide stage whose `MODIN` is tied static-high to
  `VDD_DIV` — declared by the committed
  `design/sg13cmos5l/netlist/divider_chain.spice` (`XD5 VDD_DIV P5 …`), present
  in the same record's extracted netlist, and part of the 316/316 `match`.
  Not a short; the LVS of the same GDS matched with those gates on the
  supply.

### The two reads, and why there are two

`erc-supply-spec.json` (the #103 item-11 artifact) deliberately declares **no
`ties[]`**: at #103's curation, `klt erc`'s `ties[]` collapsed a real routed
standard-cell design into one island and reported a FALSE `erc.supply_short`
(klayout-tools#2169), so #103 ruled the spec be committed `ties[]`-less and
`erc.missing_tie` be documented as **not computed** — an absence of evidence,
not evidence of absence. The report records exactly that:
`erc_coverage.inapplicable: [{id: "erc.missing_tie:[]", reason:
"no_ties_declared"}]`.

klayout-tools#2169 **closed upstream on 2026-09-20** (PR #2186 isolates the
tie connectivity graph from the wire/via graph; PR #2199 grades a degenerate
tap declaration as skipped rather than clean), which makes a genuinely
*checked* well-tie verdict expressible for the first time. The supplementary
`erc.welltie-check-spec.json` probe is the new machinery exercised on this,
the first SG13-family ERC spec in the fleet: it declares the pfet row's n-well
tie as `tap_layer: Cont(6/0)` narrowed by `tap_requires: [nSD(7/0)]` — the
curated `sg13cmos5l` deck's own `tap_nplus` derivation (`nSD & Activ & NWell`,
klayout-tools#1414), which provably excludes every pfet source/drain contact
(opposite-doping `pSD` implant). The result: the tie is graded **checked**
(not skipped-degenerate), and reports **zero `erc.missing_tie`** — the n-well
tap exists and reaches `VDD_DIV`. The substrate half of the tie question is
*not* expressible as a `ties[]` entry on this stream (no `PWell`/`Substrate`
shape is drawn; the p+ substrate-tie strip sits in the bare global substrate,
which no declared well shape can carry) and stays covered by the standing-in
evidence named in `erc-supply-spec.json`'s comment block: the compose route
record (`divider_chain_nfet_w2_l0p5.substrate_tap` pinned into `VSS`) and the
same-record LVS `match` carrying both supplies in its `net_correspondence`.

## Standing-in well-tie evidence (while `erc.missing_tie` is not computed by the item-11 artifact)

1. `../20260830-204105-457cf5b/lvs.divider_chain.json` — `status: "match"`
   (316/316 devices, 142/142 nets) against `divider_chain.reference.spice`,
   with **both supplies in `net_correspondence` paired to reference-side
   nets** (`VDD_DIV`→`VDD_DIV`, `VSS`→`VSS`, pins): the supplies were part of
   the compare, not absent from it — the analog-column demand of the upstream
   item text.
2. `../20260830-204105-457cf5b/compose.divider_chain.json` — the routing
   record pins `divider_chain_pfet_w5_l0p5.nwell_tap` into `VDD_DIV`'s 105-pin
   route and `divider_chain_nfet_w2_l0p5.substrate_tap` into `VSS`'s 89-pin
   route: both body ties are drawn *and wired* into the supply rails.
3. The committed GDS itself — the n-well tie is drawn as an `nSD`(7/0)-covered
   Activ strip inside the row's merged `NWell`(31/0), labelled `VDD_DIV` on
   `NWell.pin`(31/2) and `Metal1.pin`(8/2) (the deck's `well_label`); the
   substrate tie as a `pSD`(14/0)-covered Activ strip outside every NWell.
4. The checked-tie probe above (this record) — upstream's #2186-era machinery
   grades the n-well half **checked, zero findings** at this pinned build.

## Layer-number provenance

Every layer in both specs was resolved from the PDK's own
`libs.tech/klayout/tech/sg13cmos5l.lyp` and cross-checked against
klayout-tools' curated `sg13cmos5l` deck table at the repo's own pin
(`layout/requirements.txt` @ `fdf04f71`, deck sha256 `9b8dfb65…` — the same
hash flow record `20260830-204105-457cf5b` cites). Full justification of each
`stackup` entry and each `label_layer` is inline in the specs' `_comment`
blocks, per #103's acceptance criteria.
