# RECORD-002: floorplan-aware routing for `pll_vco`, and the PVT re-run against it

- **Slug**: `sg13cmos5l-postlayout-pex-pvt`
- **Issue**: #101 (sub-issue A of the #100 split of PR #99's judge-filed
  follow-ups; Part of #16) — the routing-style half of the post-layout
  deviation RECORD-001 measured.
- **DUT**: `pll_vco`, re-routed through the locality floorplan pass
  (`layout/bin/cmos5l_floorplan.py`, issue #101) and re-extracted; the
  control arm is the same frozen schematic netlist
  [`../../sg13cmos5l-vco-kvco-table/netlist-snapshots/vco.spice`](../../sg13cmos5l-vco-kvco-table/netlist-snapshots/vco.spice)
  RECORD-001 re-verified.
- **Tooling**: `ngspice-46`; klayout-tools at commit `729ee531e176` — the
  **same klt** RECORD-001's committed `provenance.json` names
  (`klt 0.4.0+g729ee531e176`; this session ran it as a `git archive` export,
  so its version string reports `klt 0.2.0+unknown` — the archive-mode
  artifact RECORD-001 §1.1 documents for its own re-verification run);
  installed `~/share/pdk/ihp-sg13cmos5l`; x86-64 Linux host.
- **Layout record**: `layout/sg13cmos5l-pll/reports/20260921-155747-c44fa68`
  (`LATEST`), produced by `layout/bin/run-pll-cmos5l-layout-flow.sh` at
  worktree tree `c44fa68` — the id's sha component is this flow's
  standard "tree the record was generated at" label, which for every
  committed record under `reports/` (e.g. `…-204105-457cf5b`,
  `…-070704-4520159`) is a builder-worktree sha, not a merge-resolvable
  commit. The branch was rebased onto `dccfbf5` (#105, ERC spec + report
  files only) after the record was produced; that commit touches nothing
  this flow or the sim harness consumes (`git show dccfbf5`: five new files
  plus a README section), so the record's inputs are identical trees on
  both sides of the rebase.
- **Reproduce**:
  - `layout/bin/run-pll-cmos5l-layout-flow.sh`
    → `layout/sg13cmos5l-pll/reports/20260921-155747-c44fa68/` (record;
    `compose.vco.json` carries the floorplan report)
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l
    PEX_KLT_PYTHONPATH=<klayout-tools checkout at 729ee531e176>/src
    ./extraction/run-pex.sh`
    → `netlist-snapshots/*.{spice,json}`, `provenance.json`
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
    → `corners/results.csv` (120 rows)
  - `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run_rc_attribution.sh`
    → `corners/rc_attribution.csv` (211 lines)
  - `./testbench/analyze.py`
    → `corners/deviation.csv`, `corners/control.csv`, every roll-up below
  - `LVS_KLT_PYTHONPATH=<same checkout>/src ./lvs-recheck/run-lvs-recheck.sh`
    → `lvs-recheck/summary.json`

---

## 1. What changed on the layout, and what did not

Issue #101 asked for a floorplan-aware pass that measurably reduces wire,
or a documented blocker. **It is achievable with this repo's own flow**, and
this record is the measurement. What the pass does (see
`layout/bin/cmos5l_floorplan.py`'s docstring for the full mechanics):

1. permutes the **group-cell order** on `vco`'s single row,
2. permutes the **member→unit-slot order inside each matched group cell**
   (a matched array draws every unit identically, so this relabels the
   plan's `port→net` map, never the drawn geometry — every per-group GDS is
   byte-identical to the previous record's),
3. permutes the **Metal3 track order** (`ring`-locality nets and rails no
   longer ride alphabetical tracks; the supply rails — most terminals — ride
   the lowest, shortest-riser tracks).

Applied by name to `vco` only (`layout/bin/pll_cmos5l_layout.py` →
`FLOORPLAN_STRATEGIES`); the other five blocks keep the pre-#101 single-row,
by-name-track composition **byte-for-byte**: `compose.cp.json`,
`compose.pfd.json`, `compose.divider_chain.json` and their GDS files are
identical to the committed `20260830-204105-457cf5b` record's — verified
byte-for-byte at this session, and that record is the same tree `d5355e1`
carried for those three blocks. `loop_filter` and `lock_detector` are the two
that legitimately
differ (§5.3) — their *netlists* changed on main before `d5355e1` landed, the
previous record predates that, and their layouts are simply regenerated from
the current netlists. Nothing else about the blocks' inputs differs.

What permits a shrink to remain DRC/LVS-clean analytically runs: the router's
two structural-correctness invariants (riser-column uniqueness, one trunk per
net per track) hold for **any** permutation, because it never adds a net,
splits one, or changes a device, footprint or spacing. Measured, per the
record:

- Block `klt drc`: **clean** (was clean).
- Block re-extraction: **44/45 devices matched** — identical to the previous
  record's 44/45; the unmatched one is, as before, the undrawn MoM decap.
- Block LVS: primary run still **not converted** (the deck's MoM capacitor
  class, klayout-tools#1463 — unchanged), and the labelled
  `cap_cmomi`-mapped probe run still compares with the **same mismatch
  structure**: 16 mismatches, same category counts, devices 44/45 nets
  33/34, on the previous record. `lvs-recheck/summary.json` confirms the
  **byte-identical verdict shape for all six blocks**
  (`vco`: mismatch, 12, devices 38/45 matched — exactly as at `d5355e1`),
  which is issue #101's acceptance criterion 2 verbatim.

**Wire length, in the router's own metric** (per-net span + one riser per
terminal; `cmos5l_route.route`'s `wire_length_um`, recorded in
`compose.vco.json` → `routing`):

| | `d5355e1` / record `20260830-204105-457cf5b` | this record | Δ |
|---|---:|---:|---:|
| Total routed wire, all 33 nets | 7 177.91 µm | **3 912.55 µm** | −45.5% |
| `ring1` | 413.08 µm | **126.20 µm** | −69.4% |
| `ring2` | 259.46 µm | 72.65 µm | −72.0% |
| `ring3` | 264.86 µm | 78.10 µm | −70.5% |
| `ring4` | 270.26 µm | 83.46 µm | −69.1% |
| `ring5` | 287.50 µm | 88.91 µm | −69.1% |

The pass recomputes the first column itself (`baseline_wire_length_um` in
`compose.vco.json` → `floorplan`, unit-tested equal to the live router
drawing the old order) — the reduction claimed here is self-contained,
not quoted from RECORD-001. Decomposition, same table: the track-order axis
alone is worth 7 177.91 → 6 808.91 µm (−5.1%); the placement axis alone
delivers the remaining 6 808.91 → 3 912.55 µm (−42.6%) at optimal tracks.
The descent is deterministic (2 passes, first-improvement over
swap/reinsertion neighbourhoods) and finds a **local, not global, optimum**
— it is "a considered pass," not "the optimum," and the remaining rail-span
wire (VDD/GND tracks still cross the block, as any supply net must) is the
dominant irreducible term left.

## 2. Extraction: same C-scaling class, one step smaller

`klt extract --deck sg13cmos5l --parasitics` re-run against the new
geometry. Same klt, same deck, same PDK, same options as RECORD-001 — and
before re-extracting the new geometry this session re-extracted both
`pll_vco.gds` and `pll_cp.gds` **from the old, committed record** with that
klt and reproduced the committed `netlist-snapshots/*.pex.spice`
**byte-identically**, so the tool pin is anchored, not assumed.

`netlist-snapshots/provenance.json` (totals for `pll_vco`):

| | `d5355e1` layout | this record | Δ |
|---|---:|---:|---:|
| devices / nets | 44 / 33 | 44 / 33 | — |
| ΣR | 2 393.04 Ω | **1 435.31 Ω** | −39.9% |
| ΣC | 558.81 fF | **343.43 fF** | −38.6% |
| C-coupling cards | 311 | 189 | −39.2% |

Per-net parasitic series-R, from the netlists themselves:
`ring1` 127.59 → 43.45 Ω (−66%), `ring2`..`ring5` −65 to −69%, `VBP`
97.80 → 61.10 Ω, `XBIAS.degb` 123.44 → 64.08 Ω, `bufmid` 92.00 → 47.47 Ω;
the supply rails' residual spans stay (e.g. `GND_VCO` 227.59 → 216.53 Ω), as
expected for any net that must reach every stage.

The extraction model and its caveats are unchanged from RECORD-001 §1.2:
lumped star per net, first-order, **uncalibrated** curated coefficients —
real numbers with a cited public source, not silicon-correlated. No metal
lacked a coefficient (`metals_without_coefficient` empty for all six blocks).

## 3. Matrix A re-run: the band recovers slightly more than half the deviation

120 transient runs (60 per arm, the same 3 PVT bundles × 4 band codes × 5
VCTRL points), **0 `NA`**, `corners/results.csv`.

**The control arm is still a control**: the schematic arm reproduces
**60 of 60** committed `sg13cmos5l-vco-kvco-table` frequencies with
**max |delta| = 0.000000%** (`corners/control.csv` — byte-identical to the
committed one, as 60/60 exact reproduction implies). This satisfies issue
#101's test-plan control clause verbatim.

### 3.1 Headline deviation, `d5355e1` → this record

| | Schematic (control) | Post-layout @`d5355e1` (RECORD-001) | Post-layout this record |
|---|---|---|---|
| Output band, all 60 points | 445.26 – 1561.97 MHz | 223.68 – 789.50 MHz | **347.55 – 1182.79 MHz** |
| Kvco avg, per bundle×band | 144.2 – 422.4 MHz/V | 67.6 – 207.6 MHz/V | **106.4 – 313.1 MHz/V** |
| Kvco peak local | 182.6 – 590.2 MHz/V | 85.2 – 293.4 MHz/V | **133.8 – 453.6 MHz/V** |

(Columns 2–3 reproduce RECORD-001 §2.2; values re-derived here from the
committed CSVs with the same sweep arithmetic that record used — average over
each bundle×band's 5-point VCTRL sweep, and the steepest single-segment slope
for "peak local" — so the columns are mechanically comparable, and the
re-derivation reproduces RECORD-001's own printed numbers exactly.)

Per-point ratio (`corners/deviation.csv`), **60 of 60 points**:

| | min | mean | max |
|---|---|---|---|
| f_postlayout / f_schematic, `d5355e1` | 0.4768 (−52.32%) | 0.5074 (−49.26%) | 0.5312 (−46.88%) |
| f_postlayout / f_schematic, **this record** | **0.7394 (−26.06%)** | **0.7742 (−22.58%)** | **0.7892 (−21.08%)** |

**The remaining ~22.6% deviation is still almost entirely capacitance.**
Matrix C re-run (30 points × 4 attribution arms + 3 bracket arms,
`corners/rc_attribution.csv`):

| arm | f vs its own schematic control, `d5355e1` (mean) | this record (mean) |
|---|---:|---:|
| `none` (devices only) | −0.69% | −0.70% |
| `r_only` | −1.40% | **−1.35%** |
| `c_only` | −48.83% | **−21.95%** |
| `full` | −49.21% | **−22.53%** |

Device-level extraction alone still costs <1% (the drawn footprints are
byte-identical), R costs ~1.4 pp, C costs everything else. The new routing's
C rests roughly where RECORD-001's `cscale25` bracket predicted a
quarter-wire floorplan would (−20.7% there, −21.95% here — the same
order-of-magnitude conclusion, now measured on a real route instead of a
scalar).

**Issue #101 AC #4 (harness already resumable, re-run end-to-end)** — met;
no testbench code changed (`git diff` against `d5355e1` covers only
`layout/bin` and the evidence directories).

## 4. The DR-005 question: **narrowed, not closed**

Issue #101 asked explicitly whether the gap to the spec rows DR-005 amended
now closes, narrows, or does not move — with numbers, and **without** this
issue touching `spec/porting-plan.md` or DR-005 (its acceptance criterion 6
makes not-touching a requirement; both files are byte-identical at this
PR's head).

Measured against the schematic band DR-005's amended rows 2/3 were written
from (445.26 – 1561.97 MHz):

- upper coverage: post-layout top end 789.50 → **1182.79 MHz**, recovering
  393.29 of the 772.47 MHz deficit (**51.0%**);
- lower coverage: post-layout bottom end 223.68 → **347.55 MHz**, recovering
  123.87 of the 221.58 MHz deficit (**55.8%**);
- whole-matrix: mean per-point deficit −49.26% → −22.58%, recovering
  26.68 of 49.26 percentage points (**54.2%**).

So the gap **narrowed to roughly half its previous size and did not close**:
the post-layout band still sits at 0.74–0.79× the schematic band on every
one of the 60 points. Whether rows 2/3 as amended still describe a
synthesisable `f_ref`/`N` pair grid against **347.55–1182.79 MHz** instead of
445.26 – 1561.97 MHz is precisely the question the follow-on
decision-record issue must answer with this record's numbers — and whether
the remaining ~22% is worth another routing pass (the irreducible rail spans
this one-row style keeps, common-centroid stacking, a real supply grid, or
folding the row) is a floorplan-effort question, not a spec one. This record
does not answer either; it hands them the evidence.

## 5. Every comparison this record relies on, stated as checks

### 5.1 The klt pin

`729ee531e176` == the commit RECORD-001's committed `provenance.json`
already names (`klt 0.4.0+g729ee531e176`). This session ran it from a `git
archive` export (its `--version` self-reports `klt 0.2.0+unknown` in that
mode — the artifact RECORD-001 §1.1 documents). Two probes against the old
committed record's GDS reproduced its committed `pll_vco.pex.spice` and
`pll_cp.pex.spice` byte-for-byte before any new geometry was extracted; the
full `run-pex.sh` pass shows the same property structurally (next point).

### 5.2 Unchanged blocks re-extract byte-identically

`pfd`, `cp`, `divider_chain`: GDS byte-identical to record
`20260830-204105-457cf5b` (and to `d5355e1` — no design change touched them)
⇒ their regenerated `.pex.spice` files are byte-identical to the committed
ones (only their `.pex.json` `"file"` path fields differ, naming this
record). Their `provenance.json` totals match RECORD-001 §1.3 exactly
(for `cp`: R 914.862 Ω, C 219.402 fF, 20 devices / 18 nets). **Matrix B
(`cp` DC trim, 612 committed points) is therefore not re-run**: its DUT's
GDS and extracted netlist are byte-identical, so its committed
`corners/cp_results.csv` remains the valid evidence for exactly the same
reason it was valid at `d5355e1`. `analyze.py`'s cp section reads those
committed rows and reports the same numbers RECORD-001 committed.

### 5.3 The two blocks whose layouts legitimately moved, disclosed

`loop_filter` and `lock_detector`: their schematic netlists changed on main
**before** `d5355e1` landed (`design+sim: resize SG13CMOS5L loop_filter R1
and re-verify…` — the `resized` snapshots; the lock-detector crowbar/hyst
fixes), so the `20260830` layout record was already stale for them. This
record regenerates their layouts from the current netlists — hence the
changed `compose.*.json`, `.pex.spice` and `.pex.json` for exactly those two
blocks. Their evidence quality is unchanged where it matters: their
`lvs-recheck` verdict shapes are identical (mismatch / not-converted
respectively, same mismatch categories and counts), and neither block enters
this record's vco analysis.

### 5.4 The band survivor-guarantee is unchanged from RECORD-001

0 `NA` rows in this run, no `NA` was ever resumed, and the control arm
reproduces the committed schematic campaign 60/60 exactly, so any future
interrupted-run concern inherits RECORD-001's own resume discipline
(`PEX_WORK`, never resuming an `NA`).

## 6. Where this leaves the canary statement

RECORD-001 warned that its post-layout numbers were an **upper bound set by
routing style, not a floorplan prediction**. With this record the warning
shrinks but does not retire: the measured deviation budget for this block is
now ~22.6% mean under an *uncalibrated* first-order extraction model, against
~49.3% before — of which under 1 pp is the device floor both layouts share
and ~1.4 pp is parasitic R, so the interconnect-C share fell from ~48 to
~22 pp, with `ring1` itself 69% shorter. A
representative analog floorplan (matching, supply grid, folding) remains
**not** what this flow draws — every floorplan claim in
`layout/sg13cmos5l-pll/README.md`'s "What it is not" still applies except
where this record's numbers supersede them, and that README states the
delta.

**Spec status**: `spec/porting-plan.md` and
`spec/decision-records/DR-005-fref-n-vco-band-reconciliation.md` untouched
— checked as byte-identical at this PR's head. The decision-record issue
that step 5 of #101's "Suggested Approach" reserves this evidence for
remains to be filed/answered separately; this record is that evidence, and
does not take the decision.
