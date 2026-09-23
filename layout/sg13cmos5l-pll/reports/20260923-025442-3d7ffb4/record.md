# ERC power-delivery (structural) record — `20260923-025442-3d7ffb4`

Refresh of the T1 item 11 evidence for the composed + routed divider
chain, re-pinned to the #113 record rebuild's GDS (which carries #121's
`dff_tg_hv` hold-path fix — 394 devices, 181 routed nets). Same shape and
same verdicts as the superseded record
[`20260921-155144-00b0094`](../20260921-155144-00b0094/): this is **not a
layout-flow record** (those are produced by
`layout/bin/run-pll-cmos5l-layout-flow.sh`); it is a derived evidence
record frozen against the committed artifacts of flow record
[`20260923-020931-a95a887-dirty`](../20260923-020931-a95a887-dirty/) — its
`pll_divider_chain.gds` is the unchanged input here (content-hash below)
and nothing in that record is rewritten.

- **klt**: `0.5.0+gb15edf5e3a2e` — klayout-tools pinned by exact upstream
  commit `b15edf5e3a2e56467a3406c98a2555eb1a5ae45c` for this run only,
  the same pinned grading build `.github/workflows/signoff.yml` installs.
  Both committed reports self-attest this build in
  `provenance.klt_version`.
- **Input layout**:
  `../20260923-020931-a95a887-dirty/pll_divider_chain.gds`,
  `provenance.input.content_hash` =
  `sha256:27149fd03a59d5f59ea23ae39b7f0ea7d61c765e79022184960ca04ec4ba5196`
  — identical to the committed GDS (verified by `sha256sum` at commit
  time).
- **Specs** (committed at `layout/sg13cmos5l-pll/`, unchanged from the
  prior record): `erc-supply-spec.json` (the #103 item-11 artifact —
  `ties[]` deliberately omitted) and `erc-welltie-check-spec.json` (the
  supplementary checked-tie probe).

## Verdict: `erc_status: "clean"` on both reads — one island per declared supply, zero supply findings

| Read | `erc_findings` | `erc_status` | `status` (antenna half) | `erc.missing_tie` |
| --- | --- | --- | --- | --- |
| `erc.supply-spec.pll_divider_chain.json` | **0** | **`clean`** | `not_checked` | **not computed** — `erc_coverage.inapplicable: no_ties_declared` |
| `erc.welltie-check.pll_divider_chain.json` | **0** | **`clean`** | `not_checked` | **checked** (`erc.missing_tie:["pfet_row_nwell_tap"]` in `erc_coverage.checked`), zero findings |

- **Zero `erc.unconnected_net`** and **zero `erc.supply_short`** naming
  either declared supply (`VDD_DIV`, `VSS`): each resolves to exactly
  **one** electrical island.
- **Antenna half honestly `not_checked`**: `klt erc`'s antenna-ratio
  limit table is sky130-only today — the same untranscribed upstream gap
  the prior record disclosed. Item 11 grades the `erc_findings` rules,
  never the report's overall `status` (klayout-tools#1994).
- Gate count moved 91 → 117 with #121's added devices; the supply
  structure verdict is unchanged.
