# `manifests/` — the block's graded `klt signoff` state

| File | What it is |
| --- | --- |
| [`sg13g2-pll.json`](sg13g2-pll.json) | **The block manifest** — the stable path the fleet's tier roll-up consumes (2AMLogic/2am#956 reads exactly this file per canary). Declares the block's `block`/`kind` and, per T1 item, the evidence envelope that backs it. A citation pins its claimed input revision with `content_hash`; `klt signoff` refuses to grade a citation whose own provenance names a different revision (`stale_evidence` — a manifest citing an artifact that has since changed **fails**, it does not rot). |
| [`sg13g2-pll.tier-report.json`](sg13g2-pll.tier-report.json) | **The verdict of record** — `klt signoff --manifest manifests/sg13g2-pll.json --format json`, committed verbatim. Issue #6 (the gap-to-T1 tracker) points here instead of carrying its own hand-maintained checklist. |
| [`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml) | Re-runs the grade on every push/PR and byte-compares the fresh report against the committed one — drift is a CI failure by design. |

## Verdict, read off the committed report

`tier: null` — 3 of 22 T1 items `met` (22 = 11 items × 2 partitions, `kind:
"mixed-signal"`). Grade run:

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

Every citation in the manifest pins the same layout revision:

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

### Item 11 — power delivery (structural): `11.digital` `met`; `11.analog` `unmet` with nothing yet to cite

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
- **`11.analog` has no evidence yet** — the analog partition's five blocks
  have no `klt erc` supply spec or reports. #103 scoped divider_chain
  only; extending supply specs to `pfd`/`cp`/`loop_filter`/`vco`/
  `lock_detector` is open follow-up work this row surfaces rather than
  hides.

### Every `unmet` row, in one line each (full `reason`s in the report)

| Item | `reason` | The claim-compatible state behind it |
| --- | --- | --- |
| 1, 2, 9, 10 | `no_evidence` | Real material exists — committed schematics (`design/sg13cmos5l/*.sch`), composed GDS (`layout/sg13cmos5l-pll/reports/…/pll_*.gds`), committed testbenches (`sim/sg13cmos5l-*`), repo hygiene — but these items bind to **no `klt` verb**, and citing an unrelated passing envelope to turn them green is the dishonesty this file exists to prevent (`docs/cli/signoff.md` → "the safest default is to leave them uncited"). |
| 4 (both rows) | `no_evidence` | LVS `match` exists for five blocks — `pfd`, `cp`, `divider_chain`, `loop_filter` (#114/#119), `vco` (#113: schematic resistor bodies re-declared on `VSS`; committed pathways under `sim/sg13cmos5l-postlayout-pex-pvt/lvs-recheck/reports/`) — while `lock_detector`'s residual is its documented `SUB!` `PU`/`PD` split. A bare-key citation would render both partitions `met` off the partition that does match — deliberately not cited. |
| 5 (both rows) | `no_evidence` | No **ratified** spec table yet (prerequisite: draft + ratify through `spec/` per the two-key mechanism), so no corner campaign is gradeable "vs a ratified spec"; partial pre-layout PVT evidence exists as ngspice records, not `klt sim` envelopes. |
| 6 | `no_evidence` | No Monte Carlo campaign; no `klt yield` envelope. |
| 7 (both rows) | `no_evidence` | A **post-layout PEX PVT campaign exists** (`sim/sg13cmos5l-postlayout-pex-pvt/` — RECORD-001/002, klt-extracted R/C on the routed geometry) but as ngspice run records; item 7 accepts only a `klt pex` envelope for these partitions (an SDF-annotated `klt functional-verification` for an RTL digital partition — not this block's full-custom sub-case). No `klt pex` run exists yet. |
| 8 | `no_evidence` | No aggregated, current characterization artifact; a `generic` envelope would be the vehicle and none is committed. |
| 11 (analog) | `no_evidence` | Analog-partition supply specs/reports do not exist yet (see above). |

## The tool that grades

The grade is meaningful only tied to the build that produced it — the
committed `build` block of [`sg13g2-pll.tier-report.json`](sg13g2-pll.tier-report.json):

```
klt 0.5.0+gb15edf5e3a2e  (klayout-tools @ b15edf5e3a2e56467a3406c98a2555eb1a5ae45c,
dirty: false, grading_ruleset_id: sha256:1a01464d…)
```

exactly the upstream commit the committed ERC evidence itself self-attests
in every ERC envelope's `provenance.klt_version` — one build produced both
the evidence and this grade. This commit bundles the 11-item tier doc
(klayout-tools#2025/#2057) whose item-11 grading rules match the running
build, which is why neither `--tiers-doc` overrides nor the PyPI `0.5.0`
release (10-item doc, no item-11 ruleset) can re-grade this file. Install
the grader from a **clean clone** of the pinned commit — a
`git+https://…@<commit>` direct install builds from a dirty temp checkout
and reports `dirty: true` in the report's build block:

```bash
git clone https://github.com/2AMLogic/klayout-tools /tmp/klt
git -C /tmp/klt checkout b15edf5e3a2e56467a3406c98a2555eb1a5ae45c
python3 -m venv /tmp/klt-venv
# klayout pinned to this commit's own uv.lock entry (KLAYOUT_VERSION_EXPECTED)
/tmp/klt-venv/bin/pip install -q "klayout==0.30.10" /tmp/klt
/tmp/klt-venv/bin/klt --version   # klt 0.5.0+gb15edf5e3a2e
```

and the committed report is reproduced with the grade re-run from the
repo root (the manifest's evidence paths resolve against the invoking
process's working directory — no manifest-relative anchoring):

```bash
/tmp/klt-venv/bin/klt signoff --manifest manifests/sg13g2-pll.json --format json \
  | diff - manifests/sg13g2-pll.tier-report.json
```

## CI — the gate that keeps this honest

[`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml)
installs the pinned grader at that commit, re-runs the full grade (the
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
