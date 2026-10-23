# `manifests/` — the block's graded `klt signoff` state

| File | What it is |
| --- | --- |
| [`sg13g2-pll.json`](sg13g2-pll.json) | **The block manifest** — the stable path the fleet's tier roll-up consumes (2AMLogic/2am#956 reads exactly this file per canary). Declares the block's `block`/`kind` and, per T1 item, the evidence envelope that backs it. A citation pins its claimed input revision with `content_hash`; `klt signoff` refuses to grade a citation whose own provenance names a different revision (`stale_evidence` — a manifest citing an artifact that has since changed **fails**, it does not rot). |
| [`sg13g2-pll.tier-report.json`](sg13g2-pll.tier-report.json) | **The verdict of record** — `klt signoff --manifest manifests/sg13g2-pll.json --format json`, committed verbatim. Issue #6 (the gap-to-T1 tracker) points here instead of carrying its own hand-maintained checklist. |
| [`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml) | Re-runs the grade on every push/PR and byte-compares the fresh report against the committed one — drift is a CI failure by design. |

## Verdict, read off the committed report

`tier: null` — 14 of 22 T1 items `met` (22 = 11 items × 2 partitions, `kind:
"mixed-signal"`). Item 10 moved to `met` on both partitions (#266); item 1 went
`unmet` on both at that pin bump and is `met` again from a
`klt signoff --attest 1` envelope (#267; see "Items 1 and 2"). Grade run:

```
klt signoff --manifest manifests/sg13g2-pll.json --format json
```

Exit code 3 is the *expected* contract for a block that is not yet T1 — the
command ran and graded (exit 0 = every item met; exit 1/2 = the run itself
errored and nothing was graded). The per-item `met`/`unmet` rows and the
`reason` for every unmet item are in the committed report; this README is the
**claim** — the scope and caveats a `met` row carries, which the grader
cannot check on its own.

## Claim

### Block and kind

- `block`: `sg13g2-pll` — this repo's row id in the fleet roll-up
  (2AMLogic/2am#956).
- `kind`: **`mixed-signal`**, confirmed against the block rather than taken
  from issue #104: this design is the fleet's first *closed-loop,
  mixed-signal* SG13CMOS5L entry — six blocks with real charge-domain and
  tuning-loop dynamics (`docs/chipalooza/challenge-6-proposal.md` §1) — a
  charge-pump PLL ported per `spec/decision-records/DR-001-pll-architecture.md`.
- **Partition boundary** (required by the mixed-signal kind, so a reviewer
  can tell which evidence covers which silicon):
  - **Analog partition** = the loop's continuous-time / charge-domain path:
    `pfd` (charge-domain reset timing), `cp`, `loop_filter`, `vco`
    (current-starved ring), `lock_detector` (passive window comparator).
  - **Digital partition** = `divider_chain`: cascaded ÷2/3 static-CMOS
    Vaucher chain plus the N-independent retiming flop, hand-captured from
    the committed schematic (no RTL, no synthesis, no P&R) — the tier doc's
    **full-custom digital sub-case**, graded by the Digital column but
    evidenced (SPICE-reference LVS, PVT-matrix SPICE) exactly like the
    Analog column's artifacts.
  - No chip-level `pll_top`/pad-ring wrapper exists yet (DR-004) — all
  evidence below is per composed sub-block, and the manifest's citations
  name the digital partition's largest composed block, `pll_divider_chain`
  (394 devices, 181 routed nets).

### The one artifact story every citation traces to

The digital partition's citations (items 3, 11.digital, 4.digital) all pin the same `pll_divider_chain` layout revision:

```
sha256:27149fd03a59d5f59ea23ae39b7f0ea7d61c765e79022184960ca04ec4ba5196
  = sha256 of layout/sg13cmos5l-pll/reports/20260923-020931-a95a887-dirty/pll_divider_chain.gds
```

the #113 record rebuild's GDS, which supersedes the pre-#121 revision
(`sha256:8b57386f…`, still frozen unchanged in the older committed record
directories `20260830-204105-457cf5b` and `20260921-155747-c44fa68`).
The ERC and LVS citations are committed envelopes whose own
`provenance.input.content_hash` already carries this hash; the DRC
citation is a **command-backed** entry that re-runs `klt drc` live, and
its pin is graded against the fresh run's own reported input hash.

The divider GDS is byte-identical in the later records
`20261003-183059-dc5644a` and `20261010-012952-a4ca1b8` (same sha256), which is why item 4's digital
citation can live in the newer record without changing that revision. The
**analog** GDS revisions are a separate story, told under item 4.

### Item 3 — DRC clean: `met` (both partition rows), with the coverage disclosure the grader cannot check

The manifest's `"3"` entry is command-backed: `klt drc` runs live on
`pll_divider_chain.gds` with the curated `sg13cmos5l` deck, so CI re-grades
against the artifact as committed, not against a file's say-so.

- **Scope disclosure.** Item 3 is kind-independent, so one `met` citation
  renders **both** partition rows. The block has **no chip-level top GDS**
  (DR-004), so the claim the row carries is: *every composed sub-block is
  drawn and DRC-checkable at the pinned deck*. All six are DRC-clean today
  — one shared record directory holds the six committed per-block runs
  (`layout/sg13cmos5l-pll/reports/20260923-020931-a95a887-dirty/drc.pll_{pfd,cp,
  vco,divider_chain,lock_detector,loop_filter}.json`, `status: clean`,
  569/569 devices — the MoM caps drawn at #119 closed the former
  device-level gap, and #121's 78 added divider devices re-drew clean) —
  the mechanically graded citation is one of them, re-run live.
- **Sibling-record check (`manifests/check_drc_coverage.py`).** The live
  command re-runs the divider only, so the other five blocks are not
  re-graded. A `signoff.yml` CI step (negative tests in
  `manifests/test_check_drc_coverage.py`, run on temporary copies) resolves the
  authoritative six-block record from the manifest's LVS/layout citations
  (`20261010-012952-a4ca1b8` since #195, whose `drc.pll_<block>.json` wrappers are the
  committed same-revision runs) and requires for every block: wrapper
  `ok: true`, `returncode: 0`, `status: clean` with `violation_count` 0 and no
  listed violations, provenance input hash equal to the sha256 of the adjacent
  `pll_<block>.gds`, and a `coverage` object that still carries the
  `rules_skipped` and `layers_in_stream_without_rules` disclosures (they may
  be non-empty; the starter deck is not required to be complete, and this is
  not a foundry-signoff claim). It also verifies the live item-3 command's
  divider GDS hash equals both the citation's `content_hash` and the record's
  divider GDS, so the older immutable record path it targets is bound to the
  same divider content. A new layout revision therefore needs fresh matching
  DRC evidence; historical records are never edited.
- **Coverage gaps, quoted from the cited envelope** (item 3 requires these
  disclosed, never hidden behind "clean"):
  - `layers_in_stream_without_rules`:
    `6/0` Cont, `7/0` nSD, `8/2` Metal1.pin, `14/0` pSD, `30/2`
    Metal3.pin, `31/0` NWell, `31/2` NWell.pin, `44/0` ThickGateOx —
    marker/pin/implant layers the curated `sg13cmos5l` deck has **no rule
    for** (the deck's DRC scope is `Activ/GatPoly/Metal1/Via1/Metal2/Vian/
    Metal3/TopVia1/TopMetal1` geometry: deck scope `5.5 Activ`, `5.8
    GatPoly`, `5.16 Metal1`, `5.19 Via1`, `5.17 Metaln`, `5.20 Vian`,
    `5.21 TopVia1`, `5.22 TopMetal1`).
  - `rules_skipped`: `metal3.enclosing.via3.1`,
    `metal4.{enclosing.topvia1.1,space.1,width.1}`,
    `topmetal1.{enclosing.topvia1.1,space.1,width.1}`,
    `topvia1.{space.1,width.1}`, `via3.{space.1,width.1}` — deck rules
    with **no drawn geometry at those levels in this stream**, so the deck
    itself skips them. The block routes supplies/signal on Metal1–Metal3
    only.

### Items 1 and 2 — design sources and layout: both `met`; item 1 from a `klt signoff --attest 1` envelope (#267)

**Item 1 is `met` on both partitions from an artifact-anchored attestation
(#267).** The pin that brought the item-10 producer (klayout-tools#2844, #266)
accepts only a `generic` attestation for items 1, 9 and 10, so the native
`klt lvs` citations item 1 used to carry were refused (`unmet`/`wrong_kind`).
`1.analog` and `1.digital` now both cite
[`inventories/item-1.envelope.json`](inventories/item-1.envelope.json), bound to
inventory [`inventories/item-1.json`](inventories/item-1.json) (`sources`: the 48
`design/**/*.sch`; `derived`: the 12 committed netlists, 6 per PDK tree). The
envelope hashes every source and netlist, so a drifted schematic or netlist fails
`klt signoff --attest 1 --check` in `signoff.yml`. Item 2 still accepts native
citations and is unchanged.

**Disclosed gap: no xschem in `signoff.yml`.** Each derived netlist's freshness
`check` is the offline [`check_netlist_stamp.py`](check_netlist_stamp.py): it
compares every `*.sch`/`*.sym` in a tree and each netlist against
[`../design/netlist.stamp.json`](../design/netlist.stamp.json), so editing a
source or a netlist without re-stamping fails. It does **not** regenerate: it
cannot show the stamped netlist equals what xschem emits for the stamped
sources. That regeneration gate stays `netlist.yml` (`design/netlist.sh --check`,
runner-apt xschem). After a design change: run both `netlist.sh`, get
`netlist.yml` green, `python3 manifests/check_netlist_stamp.py --update`, then
re-attest and regrade (commands under "Reproducing the grade").

The rest of this section describes the
sources and the gap behind the old citations and still holds.

Items 1 and 2 bound to no `klt` verb at the previous pin: `klt signoff` graded them on whether
*some* passing native envelope was cited and fresh against its pinned
`content_hash`, **not** on topical relevance (`docs/cli/signoff.md` → "Items
1, 2, 9, and 10"). A `met` row here therefore means "a fresh passing
envelope over these artifacts is cited", and the claim itself rests on the
committed material named below. Compound (list) citations are accepted for
item 11 only, so each partition row cites one envelope, mirroring item 4:

| Row | Cites (record `20261010-012952-a4ca1b8`, #195) | Pinned to |
| --- | --- | --- |
| `1.analog` | `lvs.lock_detector.json` (`/response`) | `pll_lock_detector.gds` `54bea524…afc` |
| `1.digital` | `lvs.divider_chain.json` (`/response`) | `pll_divider_chain.gds` `27149fd0…5196` |
| `2.analog` | `extract.pll_lock_detector.json` (`/response`) | `pll_lock_detector.gds` `54bea524…afc` |
| `2.digital` | `extract.pll_divider_chain.json` (`/response`) | `pll_divider_chain.gds` `27149fd0…5196` |

- **Item 1 (design sources).** The artifacts are the committed schematics
  (`design/*.sch`, `design/sg13cmos5l/*.sch`) and the netlists derived from
  them (`design/netlist/*.spice`, `design/sg13cmos5l/netlist/*.spice`:
  `cp`, `divider_chain`, `lock_detector`, `loop_filter`, `pfd`, `vco`),
  generated by `design/netlist.sh` and `design/sg13cmos5l/netlist.sh`. The
  cited LVS envelopes are the closest envelope that *consumed* that netlist
  lineage (layout vs. the SPICE reference); they do not prove the netlists
  are current. **"Regenerated on design change" is enforced separately** by
  [`.github/workflows/netlist.yml`](../.github/workflows/netlist.yml), which
  regenerates every netlist with the committed generators and fails on
  `git diff`. Disclosed gaps of that gate: xschem is the runner's apt
  package (not a pinned container), so the `* xschem XSCHEM Vx.y.z` banner
  line (committed: 3.4.7; local verification used 3.4.4) is the one line
  excluded from the diff; the SG13G2 PDK is pinned to the last IHP-Open-PDK
  commit before the `mm_ok=1` symbol change (the host copy has no recorded
  revision, so this is a best-fit pin). The job was observed green on a
  GitHub runner on PR #155; the local run also reproduced all 12 netlists
  apart from that banner line.
- **Item 2 (layout).** The artifacts are the six composed `pll_<block>.gds`
  in the record, with provenance in `record.md` and the reproducible flow
  `layout/bin/run-pll-cmos5l-layout-flow.sh`. The cited `klt extract`
  envelopes are bound by hash to the exact GDS.
  `manifests/check_lvs_coverage.py` (CI step) now also requires, for all six
  blocks, an `ok` extract envelope with `status: extracted` whose input hash
  equals the adjacent GDS, so the two cited samples cannot hide a missing or
  stale sibling.
- **`divider_chain` is the full-custom, hand-captured sub-case for item 2
  (and item 1)**: no RTL, no synthesis and **no P&R**. Its digital-column
  rows are satisfied by the Analog column's artifacts per the tier doc: the
  GDS is hand-drawn (by this repo's `cmos5l_devices.py`/`cmos5l_route.py`,
  not place-and-route output) from the committed schematic. No P&R script
  exists or is claimed.
- Tool gap: `klt signoff` cannot bind items 1/2 to a generator, directory
  or command-backed netlist-freshness check; see the friction issue filed
  at 2AMLogic/klayout-tools#2887.

### Item 4 — LVS clean: `4.analog` and `4.digital` `met`, from record `20261010-012952-a4ca1b8`

Both rows cite a wrapper report from the immutable record
`layout/sg13cmos5l-pll/reports/20261010-012952-a4ca1b8/`, using
`"pointer": "/response"` to reach the `klt lvs` envelope inside the wrapper
(`returncode`, `ok`, `response`, `stderr`). Pointer support is why the
grader pin moved (see "The tool that grades"). The committed wrappers are
cited as-is: nothing was normalised.

**Re-pinned by #195.** That record is a full flow re-run that redraws
`pll_cp` for DR-010 (#165). Every non-cp block GDS, including both cited
ones, is byte-identical to the #136 closure record
`20261003-183059-dc5644a`, which stays frozen. So the cited `content_hash`
values are unchanged. Every 1/2/4 citation moved to the new directory
together, because `check_lvs_coverage.py`, `check_drc_coverage.py`,
`check_erc_coverage.py` and `check_pex_coverage.py` all derive the one
authoritative six-block record from `4.analog`. With the citations left on
the old directory, those gates would have kept checking the pre-#165 `pll_cp`.

- `4.digital` = `lvs.divider_chain.json`, pinned to
  `sha256:27149fd0…5196` = sha256 of `pll_divider_chain.gds` (the
  digital partition is exactly this block; hash unchanged since
  `20260923-020931-a95a887-dirty`).
- `4.analog` = `lvs.lock_detector.json`, pinned to
  `sha256:54bea524…afc` = sha256 of `pll_lock_detector.gds`. **Why
  `lock_detector`:** it is the block whose `SUB!` `PU`/`PD` split was the
  last documented LVS mismatch (closed by #136), so citing it is the
  strongest single sample. One citation stands for five blocks, so
  it is **not** trusted alone: `manifests/check_lvs_coverage.py` (a CI step
  in `signoff.yml`; negative tests in `manifests/test_check_lvs_coverage.py`,
  run on temporary copies) inspects the exact record the manifest cites and
  requires for every analog block wrapper `ok: true`, `returncode: 0`,
  `response.status == "match"`, and
  `response.provenance.input.content_hash` equal to the sha256 of the
  adjacent `pll_<block>.gds`. A missing, failed, mismatching or stale
  sibling fails CI even though the grader never sees it.

All six blocks, as verified by that gate (record `20261010-012952-a4ca1b8`,
577 of 577 devices, 299 nets across the six):

| Block | Partition | `pll_<block>.gds` sha256 (= envelope input hash) |
| --- | --- | --- |
| `pfd` | analog | `30588e30497221d5211eec168e71a1e326a821c65e4cb43b18aab622729f16a7` |
| `cp` | analog | `840267fda95d9ae699ba85f2fc7b7931a19cc05bf2e3c93d2978899545dfe050` (DR-010 redraw, #195; was `95c64289…872c`) |
| `loop_filter` | analog | `8a3c9e3ee57f2b414133b9a4b0ff7a0cf3a8be889940cfaa3780587565debce3` |
| `vco` | analog | `21d0d72a7ca94dda5e739863d4dc7b65378096cf879a6ad15f6a7f5ea01818f7` |
| `lock_detector` | analog (**cited**) | `54bea524f81541c7c3be3fdad14423acf47eb7a0972c07932701c3e691ac2afc` |
| `divider_chain` | digital (**cited**) | `27149fd03a59d5f59ea23ae39b7f0ea7d61c765e79022184960ca04ec4ba5196` |

Disclosures that travel with these envelopes (not softened):

- **`power_connectivity.status` is `"unchecked"`** in both cited envelopes
  (expected for a SPICE reference). That satisfies item 4; it is **not** a
  verified power grid and must not be read as one.
- **`klayout_version_mismatch: true`** on every source envelope: they were
  recorded with `klt 0.6.0+gdaf06a51afaf` on KLayout `0.30.12`, not the
  engine version the tool expected. The grader accepts this provenance
  (`input_verified: true`, status `met`), but the record is not claimed to
  have been produced on the expected KLayout. (#195's record was produced
  with the same pin and engine, so this disclosure carries over unchanged.)

### Item 7 — post-layout verification: `7.analog` and `7.digital` `met`, audit-first (#152)

**What is cited.** Item 7 accepts only a `klt pex` envelope. Five were
produced (`klt 0.6.0+g1eb3e4bfd0f5`, KLayout 0.30.12, ngspice-46, one nominal
corner each, `--backend local`; `sim/sg13cmos5l-klt-pex-signoff/run-klt-pex.sh`).
They were re-run by #195 against layout record `20261010-012952-a4ca1b8`
(RECORD-002; the runner now reads that record from `4.analog`), and each
envelope's
`provenance.input.content_hash` equals the GDS hash in the item 1/2 table
above:

| Item | Citation | GDS sha256 (= `content_hash`) | Spec row measured (schematic -> extracted) |
| --- | --- | --- | --- |
| `7.analog` | `sim/sg13cmos5l-klt-pex-signoff/reports/pex.vco.json` | `pll_vco.gds` `21d0d72a...18f7` | ring `clk_period_s` at `VCTRL`=1.65 V: 1.454 ns -> 3.649 ns (**+151 %**) |
| `7.digital` | `.../pex.divider_chain.json` | `pll_divider_chain.gds` `27149fd0...5196` | word 000000 divide period 640.003 ns -> 639.989 ns (-0.002 %, N = 64 both legs) |

The analog partition has five blocks but a manifest key takes **one**
envelope (a list of envelopes with different hashes grades
`invalid_evidence`). The cited one is the block with the *largest* shift, not
the most flattering. The other committed envelopes are not cited but are in
the same directory: `pfd` (UP/DN average duty, +77.8 % / +9.3 %), `cp`
(output current at 10 uA reference, +0.141 % up / -0.039 % down on the
DR-010 redraw; this DC bench does not observe the dump buffer's tracking),
`loop_filter` (NZ step-response t63, +29.6 %).

**Body-bias audit (the step that decides what may be cited).** Each block's
PEX netlist was checked for how device bodies are bound, and the netlist's
GDS compared with the current record's:

| Block | Snapshot netlist checked (`sim/sg13cmos5l-postlayout-pex-pvt/netlist-snapshots/`) | Snapshot GDS == current GDS? | Device bodies in snapshot | `klt pex` `body_bias.status` on current GDS | Verdict |
| --- | --- | --- | --- | --- | --- |
| `pfd` | `pll_pfd.pex.spice` | yes | nmos `VSS` (33), pmos `VDD` (33) | `biased` | pass |
| `cp` | `pll_cp.pex.spice` | yes | nmos `VSS` (11), pmos `VDD` (9) | `biased` | pass |
| `loop_filter` | `pll_loop_filter.pex.spice` | yes | `rppd` bulk `vsubs` (substrate global, 0 V in the testbench) | `biased` | pass |
| `vco` | `pll_vco.pex.spice` | yes | nmos `GND_VCO` (21), pmos `VDD_VCO` (17), `rppd`/`rhigh` `GND_VCO` | `biased` | pass |
| `divider_chain` | `pll_divider_chain.pex.spice` | yes | nmos `VSS` (173), pmos `VDD_DIV` (120) | `biased` | pass |
| `lock_detector` | `pll_lock_detector.pex.spice` | **no** (`61a18fc1...` vs `54bea524...afc`) | nmos `VSS`, pmos `VDD`, `rhigh` `VSS` (but on the pre-#136 layout) | not run | **withheld** |

That table records the #152 audit. **#195 changes cp's row.** The current
`pll_cp.gds` (`840267fd…e050`) is the DR-010 redraw, so the cp snapshot above
no longer matches it. That snapshot belongs to the postlayout-pex-pvt campaign
and describes the pre-#165 cp. The redraw's own bindings are taken from the
layout record's `pll_cp.extracted.spice`: nmos `VSS` (14), pmos `VDD` (12),
and pmos `XBUF_PSRC` (2). Those two are `MP1`/`MP2`, whose bulk is their source
by design (DR-010). The new `pex.cp.json` reports `body_bias.status:
biased` with zero unbiased devices. `XBUF_PSRC` is a driven internal node,
not an anonymous body net.

No snapshot had a body on an anonymous net, and every `unbiased_pmos_body_nets`
list is empty. **`lock_detector` is not cited**: its committed PEX netlist
and its postlayout-pex-pvt evidence describe the pre-#136 layout, no `klt pex`
envelope exists for the current GDS, and the full-PVT grid for the #136 DUT
is still owed (#139). Re-extraction and the `klt pex` run are filed as
**#157**; the multi-corner part goes through `klt sim` corners / `monte_carlo`
(batch), not a local ngspice grid.

**Disclosures that travel with these two `met` rows (not softened).**

- **`met` here is "a `klt pex` envelope ran clean on a biased netlist", not
  "post-layout meets a spec".** The requests declare no `limits`, so every
  `delta[].status` is `pass` by construction; the deltas above are measured
  facts, not graded ones. The VCO's +151 % period shift (about 2.5x slower)
  is the same effect RECORD-001 of the postlayout-pex-pvt campaign measured
  (post-layout band 223.7-789.5 MHz vs schematic 445.3-1562.0 MHz) and is not
  hidden by the green row.
- **One nominal corner, one operating point per block** (`mos_tt`/`typ`,
  27 C, 3.3 V). The PVT grids of the postlayout-pex-pvt campaign remain
  ngspice run records; this item cites the envelopes only. Multi-corner
  re-runs belong on the batch fleet via `klt sim`; no grid was run here.
- **The schematic leg is flattened by a repo script**
  (`sim/sg13cmos5l-klt-pex-signoff/flatten-schematic.py`): `klt pex` needs
  a flat schematic DUT with the extracted cell's pin list, and has no flatten
  option (filed upstream as klayout-tools#2889). Device cards are verbatim; the
  schematic `sub!` global is mapped to `vsubs`.
- `klt pex` was invoked with `--pins` to demote the extractor's promoted
  internal nets (the `loop_filter` run deliberately keeps `NZ` as a pin so the
  step response can be measured).
- Extracted resistors/capacitors now parse in ngspice without
  `pex-to-ngspice.py` (the installed `klt` emits unit-suffixed `X` cards), so
  these envelopes need none of that script's transforms.

### Item 11 — power delivery (structural): `11.digital` and `11.analog` `met`

- **`11.digital` is graded `met` from three committed facts, one live
  gate** (the compound citation is `[erc, lvs]`):
  - the `erc` part is the **well-tie probe report**
    `reports/20260923-025442-3d7ffb4/erc.welltie-check.pll_divider_chain.json`
    (input hash `2714…`, `erc_status: "clean"`, `erc_finding_count: 0`).
    Its spec (`layout/sg13cmos5l-pll/erc-welltie-check-spec.json`) declares
    both supplies (`VDD_DIV`, `VSS`) as `kind: "supply"` **and** the
    pfet-row n-well tie as a checked `ties[]` entry — the run reports
    `erc.missing_tie:["pfet_row_nwell_tap"]`, `erc.unconnected_net` and
    `erc.supply_short` **checked, zero findings**, nothing in
    `erc_coverage.skipped` (no degenerate tap). The *item-11 artifact*
    report (`erc.supply-spec.pll_divider_chain.json`, also clean) is the
    companion committed at #103/#105; its spec deliberately omits
    `ties[]` (recorded `erc_coverage.inapplicable: no_ties_declared` —
    the klayout-tools#2169 workaround that closed upstream 2026-09-20).
  - the `lvs` part is the same-GDS recheck
    `sim/sg13cmos5l-postlayout-pex-pvt/lvs-recheck/reports/divider_chain.lvs.json`
    (`status: match`, 394/394 devices, 181/181 nets) **with both supplies
    carried by the reference**: `net_correspondence` pairs
    `VDD_DIV`→`VDD_DIV` and `VSS`→`VSS` (pin: true) — the full-custom
    (no-P&R) branch of item 11, satisfied by the Analog column's
    artifacts.
  - the same-revision pin `2714…` across the ERC, LVS and DRC citations —
    the item's evidence is internally consistent under the manifest's
    staleness gate.
  - Standing disclosures that travel with the evidence: the ERC reports'
    `status: "not_checked"` is the **antenna** half — `klt erc`'s
  antenna-ratio limit table is sky130-only today (upstream gap, not
  graded by item 11 per klayout-tools#1994). `erc.missing_tie` on the
  *artifact* report is disclosed not-computed (pre-#2234 form); the
  *probe* is the checked-tie evidence, exactly because #2169's fix was
  the canary's own filing.
- **`11.analog` is graded `met` from the `lock_detector` pair; CI checks
  that all five analog blocks are clean** (#147). The compound citation is
  `[erc, lvs]`:
  - the `erc` part is
    `layout/sg13cmos5l-pll/reports/20261010-014035-a4ca1b8/erc.supply-spec.pll_lock_detector.json`,
    a direct `klt erc` envelope run at the grading build
    (`0.6.0+ge6284fbe62e2`, KLayout 0.30.10) with `--deck sg13cmos5l`.
  - the `lvs` part is the item-4 envelope
    `reports/20261010-012952-a4ca1b8/lvs.lock_detector.json` (`/response`,
    `status: match`). Its `net_correspondence` pairs `VDD`→`VDD` and
    `VSS`→`VSS` (pin: true).
  - Both parts are pinned to `pll_lock_detector.gds`
    `sha256:54bea524…afc`, which is the input hash in both envelopes.
    `lock_detector` is cited for the same reason as item 4: it is the
    block whose substrate split was the last LVS residual.
  - **One citation stands for five blocks**, so
    `manifests/check_erc_coverage.py` (a CI step in `signoff.yml`, with
    negative tests in `manifests/test_check_erc_coverage.py`) checks
    **every** analog block on each push and PR. Each block must have its own
    ERC report (distinct input hash, `file` = `pll_<block>.gds`). That hash
    must equal both the adjacent GDS and the block's LVS input. The spec hash
    must equal the committed spec. The supplies must be exactly the DR-004
    rails, each a port of the block's `.subckt` in
    `design/sg13cmos5l/netlist/` and in the reference, and paired in LVS
    `net_correspondence`. Every supply and tie must be in
    `erc_coverage.checked`, with nothing `skipped` or `unknown`. A drawn-NWell
    tie must never be reported as an assertion, and the substrate tie must
    be. The run form is checked from `provenance`: the four MOS blocks must
    report `deck.name: sg13cmos5l` at the pinned deck `content_hash`, and
    `vco` (rppd, rhigh) and `lock_detector` (rhigh) must list those
    resistor bodies as carved out in `provenance.devices`, so no resistor
    body can bridge a split supply island. `loop_filter` must report
    `deck: null`, and no `gates[].net` may contain a declared supply (its
    one uncarved rppd "gate" is `NZ,VCTRL`, which must not touch `VSS`).
    Its no-ties disclosure is re-checked against the GDS layer set, and a
    malformed or truncated stream fails the gate rather than reading as
    "layer absent". Findings must be zero. Because the committed tier report says `met`,
    all five must be clean. An `unmet` state would have to list each
    defective block's follow-up issue in the script's `KNOWN_DEFECTS`.

  All five, read from the committed reports (record
  [`20261010-014035-a4ca1b8`](../layout/sg13cmos5l-pll/reports/20261010-014035-a4ca1b8/record.md),
  #195; it supersedes `20261008-230856-cd95c87`, which stays frozen):

  | Block | `erc_status` | Findings | Input hash (`pll_<block>.gds` = LVS input) | Supplies checked (1 island each) | Ties checked | Asserted (well_boxes) | Inapplicable |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | `pfd` | clean | 0 | `30588e30…16a7` | `VDD`, `VSS` | `nwell_tap`, `substrate_tap` | `substrate_tap` | — |
  | `cp` | clean | 0 | `840267fd…e050` | `VDD`, `VSS` (+ `XBUF.PSRC`, 1 island) | `nwell_tap` (VDD wells), `psrc_nwell_tap` (the PSRC well), `substrate_tap` | all three | — |
  | `loop_filter` | clean | 0 | `8a3c9e3e…bce3` | `VSS` | none | — | `erc.missing_tie` (`ties_disclosed_unexpressible`: no Activ/NWell/MOS drawn) |
  | `vco` | clean | 0 | `21d0d72a…18f7` | `VDD_VCO`, `GND_VCO` | `nwell_tap`, `substrate_tap` | `substrate_tap` | — |
  | `lock_detector` (**cited**) | clean | 0 | `54bea524…2afc` | `VDD`, `VSS` | `nwell_tap`, `substrate_tap` | `substrate_tap` | — |

  Standing limits that travel with this row (not softened):
  - **Antenna not checked.** Every report has `status: "not_checked"`,
    because klt's antenna table covers sky130 only (klayout-tools#1994).
    Item 11 grades the connectivity findings only.
  - **The substrate tie is a `well_boxes` assertion**, one box per nfet
    group. These streams draw no p-well or substrate polygon. That is weaker
    evidence than a drawn well, and the verdict of record says so in
    `power_delivery.ties_checked_by_well_assertion`. The drawn-NWell
    `nwell_tap` is the physically checked half.
  - **cp's NWell selection is an assertion too (#195).** The DR-010 PMOS
    pair's source-tied well (`XBUF.PSRC`) shares the NWell layer with five
    `VDD` wells, and no layer marks the difference. cp's spec therefore
    picks the two classes with complementary literal boxes, so both NWell
    ties appear under `checked_by_well_assertion` (the wells and taps are
    still drawn). This needs the box selectors of klayout-tools#2540, which
    postdate the grading build. **cp's ERC report is therefore produced by
    `klt 0.6.0+g1eb3e4bfd0f5`** (pinned per block in `check_erc_coverage.py`'s
    `BLOCK_BUILD`), not by `e6284fbe62e2`. The grader reads only the cited
    `lock_detector` pair, so the tier report is unaffected. The grading
    build's own run on the old two-tie spec is committed as a negative run:
    one `erc.missing_tie` on the PSRC well. Well-to-well spacing is not
    checked by the curated deck at all (klayout-tools#3012). A caller-side
    probe measures it at 7.36 um against `NW.b1` = 1.80 um.
  - **`loop_filter` has no tie to check, and says so.** It is passive (one
    rppd, two MoM caps), with no Activ, no NWell and no MOS. CI accepts its
    disclosure only after re-reading the GDS. It is not presented as checked
    coverage, and it is not the cited block. klt also cannot run
    `loop_filter` in the MOS blocks' form, because it exits 1 on a cell with
    no transistor gate (filed as klayout-tools#2896). Its report uses the
    no-`active_layer`, no-`--deck` form, in which the rppd body becomes a
    fake "gate" (see the record).
  - **The LVS halves are the `20261010-012952-a4ca1b8` envelopes** (`klt
    0.6.0+gdaf06a51afaf`, KLayout 0.30.12, `klayout_version_mismatch:
    true`), bound to the ERC runs by input hash.

### Every `unmet` row, in one line each (full `reason`s in the report)

| Item | `reason` | The claim-compatible state behind it |
| --- | --- | --- |
| 1 (both rows) | — | **No longer `unmet`: both rows `met`** (#267; see "Items 1 and 2"). Cited from a `klt signoff --attest 1` envelope; the per-netlist freshness check is an offline digest stamp, not an xschem regeneration (disclosed there).
| 9 (both rows) | `no_evidence` | Real material exists — committed testbenches (`sim/sg13cmos5l-*`) — and item 9 does bind to a verb (`klt signoff --attest 9`), so it is **not** "unbindable". It stays uncited because the `check_testbench_coverage.py` gate still carries 37 grandfathered pre-gate records (#182, #198) and an item-9 attestation is owned by the #199 campaign. Citing an unrelated passing envelope to turn it green is the dishonesty this file exists to prevent. |
| 10 | — | **No longer `unmet`: both rows `met`** (see "Item 10" below). |
| 5 (both rows) | `no_evidence` | No **ratified** spec table yet (prerequisite: draft + ratify through `spec/` per the two-key mechanism), so no corner campaign is gradeable "vs a ratified spec"; partial pre-layout PVT evidence exists as ngspice records, not `klt sim` envelopes. |
| 6 | `no_evidence` | No Monte Carlo campaign; no `klt yield` envelope. |
| 7 (both rows) | — | **No longer `unmet`: both rows `met`** (see "Item 7" above). Not cited: `pfd`, `cp`, `loop_filter` (analog envelopes committed but the analog row takes one citation) and `lock_detector` (withheld, #157). |
| 8 | `no_evidence` | `characterization/SUMMARY.md` now exists (generated and CI-checked, #171), but it is **deliberately not cited**. See "Item 8 decision (#171)" below. |
| 11 (analog) | — | **No longer `unmet`: `met`** (see "Item 11" above; all five blocks clean in CI). |

## Item 10 — repo hygiene: both rows `met`, from a `klt signoff --attest 10` envelope (#266)

| Row | Cites | Pinned to |
| --- | --- | --- |
| `10.analog` | [`inventories/item-10.envelope.json`](inventories/item-10.envelope.json) | inventory [`inventories/item-10.json`](inventories/item-10.json) `9e36e959…261b9` |
| `10.digital` | the same envelope | the same inventory hash |

Both partitions cite the one envelope, as the manifest requires for a
mixed-signal block. The envelope is tool-produced (`klt signoff --attest 10
--inventory manifests/inventories/item-10.json -o …`); nothing in it is
hand-written, and nothing is borrowed from another item's evidence.

**What the attestation checks.** Each of the hygiene files exists and is
hashed: `README.md`, `LICENSE`, `spec/target-spec.md` and the three workflows
`.github/workflows/{signoff,layout-tests,netlist}.yml`. Sixteen audit commands
then each run, without a shell, from the repo root and must exit 0: the
records checker and its unit tests, the summary generator's unit tests and
`--check`, and the six `manifests/check_*` gates with their unit tests (the
same offline, stdlib-only scripts `signoff.yml` runs). In CI, `klt signoff
--attest 10 --inventory … --check …` re-attests and diffs against the
committed envelope, so an edited or missing hygiene file, or a failing gate,
fails the `grade` job.

**What it does not check.**

- It does not run the CI workflows, simulations, DRC/LVS or the netlist
  regeneration (`netlist.yml`, `layout-tests.yml`); those need xschem, a
  simulator or network, and CI runs them itself. The workflows are attested
  as present and unchanged, not as green.
- It does not run `check_records.py --base` (append-only enforcement), which
  needs a PR base ref; `signoff.yml` still runs it on pull requests.
- It does not judge the content of the README or the spec. The README's spec
  table cites `spec/target-spec.md`, whose status is still **DRAFT**. Item 10
  asks for "its spec table", not a ratified one; ratification is item 5's
  precondition (#148), and `spec/` is unchanged here.
- The manifest pin binds the inventory file only. A change to an inventoried
  file leaves the pin fresh and is caught by the `--check` step, not by the
  manifest grade.

## Item 8 decision (#171): characterization summary exists, item stays `unmet`

[`characterization/SUMMARY.md`](../characterization/SUMMARY.md) aggregates the
committed `sim/` evidence (source map and sha256 pins in
[`characterization/sources.json`](../characterization/sources.json); CI
regenerates it, byte-compares it, and re-checks every source hash and every
min/max, with no simulation). It is not cited from the manifest.

**Grader-contract check.** Re-read against the pin in
`.github/workflows/signoff.yml` (at the time, `e6284fbe62e2`, `klt
0.6.0+ge6284fbe62e2`; `docs/cli/signoff.md`, "Generic evidence"; not
re-read at the #266 bump to `44cc42323184`, and item 8 is still uncited), item 8 accepts a `generic` evidence
envelope and nothing else (kind-restricted since klayout-tools#2044):
`schema_version: 1`, `kind: "generic"`, `status: "pass"|"fail"` (caller-asserted,
never re-derived), optional `summary`, `source`, `provenance`. Only
`provenance.input.content_hash` can pin freshness; a manifest `content_hash` pin
on a generic envelope without it renders `unmet`/`unverifiable_provenance`.
The envelope has no `partial` status.

**Decision.** Emitting `status: "pass"` would assert that the block is
characterized, which the summary itself says it is not; emitting `fail` would
only swap one `unmet` reason for another. So no envelope is committed and the
tier report and manifest are unchanged (item 8 stays `unmet`/`no_evidence`).

**Remaining requirement to grade item 8 `met`.** All of the following, then a
hand-written `generic` envelope generated from the summary (with
`provenance.input.content_hash` over `SUMMARY.md`), cited with a pinned
`content_hash`, and the tier report regenerated with the pinned klt (never by
hand):

- a ratified spec table: the spec is drafted in `spec/target-spec.md`
  (Status: DRAFT) and awaits the two-key ratification under `ratification/`
  (no tracking issue filed), so the summary can be read against a spec;
- full PVT coverage on the current DUT, including the `lock_detector` bodyfix
  re-verification (#139) and the `lock_detector` PEX re-extraction (#157);
- divider speed evidence on the current design (no tracking issue filed; the
  #168 follow-on retained edge counts but they are not selected into the
  summary);
- the charge-pump PVT and Monte Carlo evidence for the DR-010 dump buffer
  (#178), the real-cp loop PM re-check across the fast/slow grid (#203), and a
  closed loop that acquires (the nominal real-divider loop does not acquire).

## The tool that grades

The grade is meaningful only tied to the build that produced it — the
committed `build` block of [`sg13g2-pll.tier-report.json`](sg13g2-pll.tier-report.json):

```
klt 0.7.1.dev1744+g44cc42323184  (klayout-tools @ 44cc42323184a2f3a440b89789bf174488a6b1e4,
dirty: false, grading_ruleset_id: sha256:903c4365…)
```

a commit containing the `klt signoff --attest` producer (klayout-tools#2844,
needed for item 10) and still accepting the RFC 6901 `"pointer"` bindings
(klayout-tools#2376) that the item-4 citations use. The #266 bump moved from
`e6284fbe62e2` (klt 0.6.0, KLayout 0.30.10) to `44cc42323184` (KLayout
0.30.12, from that commit's `uv.lock`).

**Rows that moved at the #266 bump** (committed report before and after,
row by row on id, partition, status, reason): `10.analog` and `10.digital`
`unmet/no_evidence` to `met` (the goal); `1.analog` and `1.digital` `met` to
`unmet/wrong_kind` (a consequence of the tool, not of any artifact change:
classified at `67e684ed`, the merge of klayout-tools#2844, and the grade does
not move at `67e684ed~1`, which has no producer; no commit that has the
`--attest` producer keeps item 1 `met` on a native citation). Every other row
is identical, including the `1`/`2`/`3`/`4`/`7`/`11` rows that stay `met` and
`5`/`6`/`8`/`9` that stay `unmet/no_evidence`; T2-T4 stay
`tier_not_supported`. Top-level fields that moved: `build` and
`source_doc_content_hash` (the checklist doc changed upstream; the 22-item
denominator is unchanged).

The previous pins' history: `b15edf5e3a2e` (klt 0.5.0) had no `pointer`
support, so it could not grade the item-4 citations; the PyPI `0.5.0`
release (10-item doc, no item-11 ruleset) still cannot re-grade this file.

**Checklist diff between the earlier pins** (`b15edf5e3a2e` to `e6284fbe62e2`; superseded by the #266 bump above, kept for history): the
tier doc `docs/design-evidence-tiers.md` changed (ruleset id
`1a01464d…` to `9f99f04d…`, doc hash changed) but the denominator stays
22 (11 items x 2 partitions), and comparing the committed 0.5.0 report with
the fresh 0.6.0 grade row by row (id, partition, status, reason, title) the
only changes are `4.analog` and `4.digital` going `unmet/no_evidence` to
`met`. Items 3 and 11.digital remain `met`; `klayout` stays pinned at
`0.30.10`. The tier-doc additions are partition-boundary reporting and
extra ERC tie reasons, which do not affect these rows.

Install the grader from a **clean clone** of the pinned commit — a
`git+https://…@<commit>` direct install builds from a dirty temp checkout
and reports `dirty: true` in the report's build block:

```bash
git clone https://github.com/2AMLogic/klayout-tools /tmp/klt
git -C /tmp/klt checkout 44cc42323184a2f3a440b89789bf174488a6b1e4
python3 -m venv /tmp/klt-venv
# klayout pinned to this commit's own uv.lock entry (KLAYOUT_VERSION_EXPECTED)
/tmp/klt-venv/bin/pip install -q "klayout==0.30.12" /tmp/klt
/tmp/klt-venv/bin/klt --version   # klt 0.7.1.dev1744+g44cc42323184
```

and the committed report is reproduced with the grade re-run from the
repo root (the manifest's evidence paths resolve against the invoking
process's working directory — no manifest-relative anchoring):

```bash
/tmp/klt-venv/bin/klt signoff --manifest manifests/sg13g2-pll.json --format json \
  | diff - manifests/sg13g2-pll.tier-report.json
/tmp/klt-venv/bin/klt signoff --attest 10 --inventory manifests/inventories/item-10.json \
  --check manifests/inventories/item-10.envelope.json   # exit 0 = still attests
/tmp/klt-venv/bin/klt signoff --attest 1 --inventory manifests/inventories/item-1.json \
  --check manifests/inventories/item-1.envelope.json    # exit 0 = still attests
```

Regenerate the item-1 envelope likewise (`--attest 1`, `-o …/item-1.envelope.json`) after a design change. Regenerate the item-10 envelope with the same command plus
`-o manifests/inventories/item-10.envelope.json` whenever an inventoried
file (the hygiene files, including `signoff.yml`) or the inventory changes,
then regenerate the tier report. The hygiene files are hashed into the
envelope, so editing one without re-attesting fails CI.

## CI — the gate that keeps this honest

[`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml)
installs the pinned grader at that commit, first runs `manifests/check_lvs_coverage.py` (every analog LVS envelope in the
cited record: `match`, wrapper `ok`, hash equal to the adjacent GDS),
`manifests/check_drc_coverage.py` (all six composed-block DRC reports, item 3) and
`manifests/check_erc_coverage.py` (all five analog ERC supply reports, see
item 11) and `manifests/check_pex_coverage.py` (all five nominal `klt pex`
envelopes and their flattened schematic legs, item 7 siblings; `lock_detector`
withheld, #157; proves nominal evidence integrity, **not** a PVT/spec pass), each with its temporary-copy negative tests, `manifests/check_testbench_coverage.py` (item 9: every `sim/` bench indexed with an executable entry point, every record citing a PDK revision and tool version, PDK pin in `sim/README.md` "Cold start"; the 37 pre-gate records are grandfathered under #182 and can be resolved only by validated append-only `ADDENDUM-*.md` associations (recovered provenance or superseding rerun; format in `sim/README.md` "Provenance addenda", issue #198; no addenda are committed yet, migration status 0 of 37 resolved), so item 9 stays `unmet` and uncited in the manifest), then re-runs the full grade (the
command-backed DRC citation re-runs live; every file-backed envelope is
re-read and its pinned `content_hash` re-checked), and byte-compares the
fresh report against the committed one.

- **Exit 0 or 3 from `klt signoff`** = graded (3: this block has unmet
  items — expected); **1 or 2** = the grade itself errored → CI fails.
- **Any byte drift** between the fresh and committed
  report → CI fails, naming the drifted rows. Drift means one of: an
  evidence artifact changed without re-grading (`stale_evidence`), a
  report flipped met/unmet, an evidence file moved or was deleted, or the
  grader's ruleset changed — all of them are exactly the "rot" this
  machinery exists to catch. The report is refreshed by regenerating and
  recommitting it, never by hand-editing.

- **Spec citation gate (`manifests/check_spec_citations.py`).** A CI step in
  `signoff.yml` (negative tests in `manifests/test_check_spec_citations.py`)
  checks that every bench, record, `R-n` ruling and `DR-NNN` decision record
  cited in `spec/target-spec.md`'s Row table exists, and that Status is M/P/N/O
  with M rows citing a record and O rows carrying a gate or ruling. Structure
  and resolution only: it never reads bounds or compares Status to measured
  compliance.

New raw evidence stored outside git is described in [`artifacts/README.md`](artifacts/README.md).
