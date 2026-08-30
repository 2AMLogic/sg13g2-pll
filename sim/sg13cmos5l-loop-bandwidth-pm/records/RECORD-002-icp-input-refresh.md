# RECORD-002: mechanical re-derivation after `cp`'s Icp table changed (issue #72) — every verdict unchanged

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #72 (Part of #16) — not a new claim about this campaign. This
  record exists because issue #72 changed one of this campaign's three
  measured **inputs**, and `../testbench/run.sh` reads that input at runtime,
  so the committed `../corners/*.csv` would otherwise no longer be what the
  committed tree reproduces.
- **This record does not edit `RECORD-001`** (append-only, per this
  directory's own convention). `RECORD-001`'s method, matrix, thresholds and
  conclusions are untouched and unrevisited here.
- **What changed upstream**: `design/sg13cmos5l/cp.sch` gained an on-chip
  high-swing cascode bias replica
  (`spec/decision-records/DR-006-cp-cascode-bias-replica.md`), and
  `../../sg13cmos5l-cp-icp-trim` re-measured its Icp trim table against the
  mitigated block
  (`../../sg13cmos5l-cp-icp-trim/records/RECORD-002-…`). The `Icp` this
  campaign consumes (`icp_a`, the `up`-state current at VDD/2 at the matching
  MOS corner/temperature) therefore moves by at most **0.782%**.
- **What did NOT change**: `../testbench/run.sh`, both `.sp.tmpl` decks, the
  matrix, the two other inputs (`sg13cmos5l-loop-filter-momcap`'s R1/C1/C2,
  `sg13cmos5l-vco-kvco-table`'s Kvco), and every threshold.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`.
  **Runtime on this host, this session: ~23 s**; rewrites
  `../corners/results.csv` (90 rows), `../corners/mom_band.csv` (54 rows),
  `../corners/proposal.csv` (108 rows) and `../corners/crosscheck.txt`.

## Result: every numeric output moves by well under 1%, and no verdict flips

| Output | Rows | Max Δ `icp_a` | Max Δ `fc_hz` | Max Δ `pm_deg` | Verdict flips |
|---|---|---|---|---|---|
| `results.csv` | 90 | 0.782% | 0.392% | 0.428% | **0** (`meets_ceiling`, `meets_pm45`) |
| `mom_band.csv` | 54 | 0.782% | 0.392% | 0.415% | **0** |
| `proposal.csv` | 108 | 0.782% | 0.700% | 0.415% | **0** (`meets_both`) |

252 rows compared cell-by-cell against the pre-change committed files; every
boolean verdict column is byte-identical.

`RECORD-001`'s two headline findings are therefore unchanged, restated with
the refreshed numbers:

- **No trim code closes the loop with the as-drawn filter.** Still 0/90 rows
  meet both criteria.
- **The `R1` ×20 / 10 µA trim-code pair remains the widest-margin
  (filter, trim) pair**, at PM **58.56 – 61.78°** across the three PVT
  bundles, against `RECORD-001`'s own 58.62 – 61.82°.

`crosscheck.txt`'s real-subckt-vs-lumped agreement is likewise unchanged in
substance: `Icp` 1.004607e-05 → 1.000047e-05 A, `f_c` 954.6 → 952.4 kHz
(real subckt), and the real-vs-lumped difference stays at **+1.379% on `f_c`
and +0.051° on PM** — the same two digits `RECORD-001` reported, because that
difference is a property of the filter model, not of `Icp`.

## Disposition

- **Row 6/6a (loop bandwidth / phase margin)**: **unchanged.** Still bounded
  by `RECORD-001`, whose conclusions this re-derivation reproduces at the
  same thresholds with a refreshed `Icp` input. No re-derivation of any
  threshold, and no new claim, is made here.

## What this does not bound

Everything `RECORD-001`'s own "What this does not bound" lists, unchanged —
this record adds no new measurement, only a refreshed evaluation of the same
model against one changed input.
