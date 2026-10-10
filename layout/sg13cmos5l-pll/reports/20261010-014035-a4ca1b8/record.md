# ERC power-delivery (structural) record, analog partition: `20261010-014035-a4ca1b8`

This is T1 item 11 evidence for the five **analog** blocks, re-run for issue
#195 against the GDS of flow record
[`20261010-012952-a4ca1b8`](../20261010-012952-a4ca1b8/). That record redraws
`pll_cp` for DR-010 (#165). Like [`20261008-230856-cd95c87`](../20261008-230856-cd95c87/),
which it supersedes, this is a **derived evidence record, not a layout-flow
record**. It does not repoint `LATEST`. No earlier record is rewritten.

- **What changed**: only `pll_cp`. The four other analog GDS files are
  byte-identical to `20261003-183059-dc5644a` (same sha256). They were re-run
  with the same build, specs and form as `20261008-230856-cd95c87`, and each
  report matches its predecessor byte for byte apart from the `file` path
  (checked with `diff` on the pretty-printed JSON).
- **Builds**: two builds, each installed into a throwaway venv from a clean
  clone. Neither is the host `klt`.
  - `pfd`, `loop_filter`, `vco`, `lock_detector`: `klt 0.6.0+ge6284fbe62e2`
    (`e6284fbe62e25d9b293eed07889cb80a0b87e2f4`, `klayout==0.30.10`), the
    grading build `.github/workflows/signoff.yml` installs. Deck
    `sg13cmos5l` `sha256:1912f174…2909`, `released: true`.
  - `cp`: `klt 0.6.0+g1eb3e4bfd0f5` (`1eb3e4bfd0f5957bb643fdecfde26c7badea2c67`,
    `klayout==0.30.12`), the build behind the item-7 `klt pex` envelopes. It
    is needed for `well_requires_boxes`/`well_excludes_boxes`
    (klayout-tools#2540, merged 2026-09-28; the grading build is from
    2026-09-23). Its bundled deck is `sha256:db9f44fa…222a` and reports
    `released: false`. That build does not list the hash as a release.
    Between the two builds, `decks/sg13cmos5l.py` changes only fixed-size
    via max-size rules (`threshold_max_dbu`), a `dummy` (100/50) layer
    declaration, resistor end-term and width-offset coefficients, and
    documentation. Here klt erc uses the deck only for resistor-body
    carve-outs, and cp draws no resistor.
    `manifests/check_erc_coverage.py` pins cp to this build and deck hash
    (`BLOCK_BUILD`), and keeps the other four on the grading build's deck.
- **Command**: [`run-erc.sh`](run-erc.sh), run from the repo root with
  `KLT=<grading venv>/bin/klt KLT_CP=<1eb3e4 venv>/bin/klt`.
- **Exit code 4** is expected on every clean run. The antenna half is
  `not_checked` because there is no sg13cmos5l antenna table
  (klayout-tools#1994/#2179). The connectivity verdict is in `erc_status`.

## Verdict: all five `erc_status: "clean"`, zero findings

| Block | GDS sha256 (= ERC input = LVS input) | Spec sha256 | Build | Nets (1 island each) | Ties checked | of which `checked_by_well_assertion` | Skipped / unknown | Findings | `erc_status` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pfd` | `30588e30…16a7` | `f61226d1…14f6` | grading | `VDD`, `VSS` | `nwell_tap`, `substrate_tap` | `substrate_tap` | none | 0 | **clean** |
| `cp` | `840267fda95d9ae699ba85f2fc7b7931a19cc05bf2e3c93d2978899545dfe050` | `9d259622…99a3` | 1eb3e4 | `VDD`, `VSS`, `XBUF.PSRC` | `nwell_tap` (5 VDD wells), `psrc_nwell_tap` (1 well), `substrate_tap` (7 boxes) | all three | none | 0 | **clean** |
| `loop_filter` | `8a3c9e3e…bce3` | `55cb027f…41a3` | grading | `VSS` | none (disclosed, `ties_disclosed_unexpressible`) | none | none | 0 | **clean** |
| `vco` | `21d0d72a…18f7` | `83719d90…2764` | grading | `VDD_VCO`, `GND_VCO` | `nwell_tap`, `substrate_tap` | `substrate_tap` | none | 0 | **clean** |
| `lock_detector` (cited) | `54bea524…2afc` | `3f30879b…e5ee` | grading | `VDD`, `VSS` | `nwell_tap`, `substrate_tap` | `substrate_tap` | none | 0 | **clean** |

`cp` has 12 `erc.floating_gate` entries, all checked with zero findings (the
pre-#165 cp had 9). The same-GDS `lvs.cp.json` in `20261010-012952-a4ca1b8` is
`match`, with 28/28 devices and 22/22 nets. It pairs `VDD->VDD`, `VSS->VSS`
and `XBUF_PSRC->BUF_PSRC`.

## cp: the source-tied PMOS pair's well

DR-010's PMOS OTA input pair (`cp_dumpbuf` `MP1`/`MP2`) ties its bulk to its
own source `PSRC`. So `pll_cp` draws six NWell shapes: five labelled `VDD` and
one, `cp_pfet_w6_l0p5`, labelled `XBUF.PSRC`. The extracted netlist puts both
devices' bulk on `XBUF_PSRC`
(`X$19 XBUF_PDA VOUT XBUF_PSRC XBUF_PSRC sg13_hv_pmos L=0.5U W=6U`), and LVS
matches it. That well's nearest different-net NWell is 7.36 um away, against
the PDK's `NW.b1` = 1.80 um. The curated klt deck has **no NWell rule**, so
this distance comes from the caller-side probe
[`../../diagnosis/issue-195/probe-nwell.py`](../../diagnosis/issue-195/probe-nwell.py)
(output: `probe-nwell.pll_cp.txt`), not from `klt drc`. The deck gap is filed
as [klayout-tools#3012](https://github.com/2AMLogic/klayout-tools/issues/3012).

The spec ([`erc-supply-spec.pll_cp.json`](../../erc-supply-spec.pll_cp.json),
derivation in [`erc-supply-spec.pll_cp.md`](../../erc-supply-spec.pll_cp.md))
grades the two NWell classes with complementary literal-box selections: `nwell_tap` -> `VDD`
excludes the box `[215.16, 0.34, 230.92, 4.38]` (the `cp_pfet_w6_l0p5`
instance bbox), and `psrc_nwell_tap` -> `XBUF.PSRC` requires it. The selection
is the caller's assertion, and klt reports both ties under
`checked_by_well_assertion`. Each selected well is still drawn geometry and
must hold its own Cont ∩ nSD ∩ Activ tap that reaches the tie's net.

### Negative runs (committed alongside, not cited)

| File | Build | Spec | Result |
| --- | --- | --- | --- |
| `erc.negative-old-two-tie-spec.pll_cp.json` | grading | the pre-#195 two-tie cp spec (`git show a4ca1b8:…`) | exit 3, **1 finding**: `erc.missing_tie` `nwell_tap`, bbox `[215.72, 0.34, 230.92, 4.38]` um (the PSRC well) "not connected to declared net 'VDD'". With one net per well layer, the old spec cannot describe this layout, and the grading build cannot select wells by box. |
| `erc.negative-box-on-vdd-well.pll_cp.json` | 1eb3e4 | current spec, box moved onto `cp_pfet_w6_l0p3` (a VDD well) | exit 3, **2 findings**: the PSRC well against `VDD` and the VDD well against `XBUF.PSRC`. A misplaced box is caught. |
| `erc.negative-box-on-no-well.pll_cp.json` | 1eb3e4 | current spec, box moved off every well | exit 3: both box-selected ties are `skipped` (`degenerate_well_selection`), and `nwell_tap`, now excluding nothing, reports the PSRC well against `VDD`. |

One more result was observed while choosing the build and is recorded here,
not as a file. Run with the box keys, the grading build **silently ignores**
them (it predates unknown-key rejection, klayout-tools#2243) and reports 6
findings, one per well against the wrong net. That is why cp is not
graded at the grading build. Unknown-key rejection is fixed upstream, so no
new issue was filed.

## Standing limits (unchanged from the previous record)

- **Antenna not checked** (klayout-tools#1994).
- **The substrate tie is a `well_boxes` assertion** (no drawn p-well). For
  cp, the NWell *selection* is now an assertion as well. The wells
  themselves are drawn.
- **`loop_filter`** keeps the no-`--deck`, no-`active_layer` form and its
  `ties_disclosed_unexpressible` disclosure (klayout-tools#2896).
