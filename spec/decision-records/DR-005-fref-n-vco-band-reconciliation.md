# DR-005: reconciling f_ref (row 2), N (row 3) against the measured VCO band

- **Status**: proposed
- **Date**: 2026-08-30
- **Decided by**: Builder agent, issue #40
- **Related**: #16 (parent, epic), #40 (this issue), #27 (loop-bandwidth-pm
  work that first had to derive its own scenario list around this
  ambiguity), #36 (divider functional N range + retiming margin — open,
  advisory input, not a blocker to this record per Curator's dependency
  re-check on #40), #41 (loop-filter R1 resize — downstream consumer of the
  `f_ref` range this record settles), #43 (open — a reproducibility defect
  in the very testbench this record's numbers are drawn from; see
  "Evidentiary caveat" below), DR-001 (PLL architecture — this record
  revises one numeric claim DR-001 Decision 3 carried, without reopening the
  architecture choice itself; see "Relationship to DR-001")
- **Consumes**: `spec/porting-plan.md` §1.2 rows 2 (reference input), 3
  (multiplication ratio), 6/6a (loop bandwidth / phase margin, read but not
  amended); `sim/sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md`
  and its `corners/results.csv` (60/60 valid rows, independently re-derived
  by this record — see "Measured data" below); `design/README.md` §
  "SG13CMOS5L port" (the divider's structural N-range reading);
  `docs/chipalooza/challenge-6-proposal.md` §4 row 1 (independently
  corroborates the same 445.3–1562.0 MHz figures cited here)

---

## Context

Three numbers cannot hold simultaneously, per issue #40:

| Source | Value |
|---|---|
| `spec/porting-plan.md` row 2 (reference input, ported interface contract) | `f_ref` = 1–25 MHz |
| `spec/porting-plan.md` row 3 (multiplication ratio, ported requirement) | `N` in [4, 64], every integer, no holes |
| `sim/sg13cmos5l-vco-kvco-table/` (measured, open-loop VCO sweep) | oscillation frequency 445.3–1562.0 MHz across all 60 corner/band/`VCTRL` points |

`f_out = N × f_ref`. Issue #40's own framing states the contradiction
qualitatively; this record re-derives it quantitatively, directly from
`corners/results.csv` rather than from `RECORD-001`'s own rounded summary
table, and extends the analysis to determine which specific row(s) should
move.

### Measured data (independently re-derived, not just re-cited)

```
$ python3 -c "
import csv
rows = list(csv.DictReader(open('sim/sg13cmos5l-vco-kvco-table/corners/results.csv')))
freqs = [float(r['freq_hz']) for r in rows if r['freq_hz'] != 'NA']
print(len(rows), 'rows,', len(freqs), 'valid (no NA)')
print('min MHz', min(freqs)/1e6)
print('max MHz', max(freqs)/1e6)
"
60 rows, 60 valid (no NA)
min MHz 445.26016105950544
max MHz 1561.9721022410706
```

Confirms `RECORD-001`'s own summary table to 4 significant figures: floor
**445.3 MHz** (`slow` bundle, `VCTRL = 0.3 V`, all four band codes read
identically at this `VCTRL` — see `RECORD-001` "Band select has (almost) no
effect at low VCTRL"), ceiling **1562.0 MHz** (`fast` bundle, band `11`,
`VCTRL = 2.7 V`). No row is `NA` — every one of the 60 points is a real
oscillation measurement, consistent with `RECORD-001`'s own "no
NA/non-oscillating points" claim.

### The divider's structural N range (read from the schematic, not simulated)

`design/README.md` § "SG13CMOS5L port" states plainly: `divider_chain.sch`
hardwires all 6 `div23_cell` instances always active — a fixed-length
6-cell Vaucher (÷2/3) chain, not gf180-pll's chain-length-termination +
one-hot output mux. For a k-cell chain of this family, with each cell's own
÷2/÷3 modulus-select bit `p_i`, the division ratio is
`N = 2^k + Σ_{i=0}^{k-1} p_i·2^i`, ranging over every integer from `2^k`
(all cells ÷2) to `2^(k+1) - 1` (all cells ÷3) with **no holes**. For k = 6:
**N ∈ [64, 127]**, matching issue #40's own reading exactly. This is a
structural fact derived from the schematic's own cell count and topology,
independent of the disputed testbench (below) — it does not depend on
`sim/sg13cmos5l-vco-kvco-table/` at all. Issue #36 (open) is tasked with
*functionally confirming* this range (the chain has no reset pin and #36's
own breadcrumbs report OP-convergence problems at high frequency); per the
Curator's dependency re-check on #40, that confirmation sharpens this
record's conclusion but does not block it — the ÷2/3 structural math is not
itself in doubt, only whether the chain functions correctly across its full
speed range, which is a separate, already-tracked question.

### Provenance note: this data is from the SG13CMOS5L port, not a SG13G2-native sim

`RECORD-001`'s own DUT is `vco` "(SG13CMOS5L port, PR #26 / Closes #22)" —
no SG13G2-native VCO Kvco campaign exists in this repo (`sim/` has no
non-`sg13cmos5l-*` directory). `docs/chipalooza/challenge-6-proposal.md` §3
("Device substitution, in full") states the SG13CMOS5L port's active devices
— `sg13_hv_nmos`/`sg13_hv_pmos`, the transistors that set the ring's
oscillation frequency — are **identical** to SG13G2's own (477/482 devices
need no device-name or subcircuit-signature change; only 5 MIM→MOM
capacitor substitutions differ, none of which this specific open-loop
testbench's frequency measurement is sensitive to, since `VDD_VCO`/`GND_VCO`
are driven by ideal DC sources — `RECORD-001` "Why XCDECAP is stripped").
Per this repo's own CLAUDE.md ("the PDK is the variable, not the design"),
this record treats the measured SG13CMOS5L VCO band as the best available
proxy for the base SG13G2 design's own VCO band, in the absence of any
SG13G2-native measurement, rather than declining to use it.

### Evidentiary caveat — issue #43 (open, unresolved)

While reviewing this record's own evidentiary basis, this builder found
issue #43 (filed independently, before this record): `tb_vco_kvco.sp.tmpl`
contains `.lib $PDK_ROOT/$PDK/libs.tech/ngspice/models/cornerMOShv.lib
@CORNER_MOS@`, and `run.sh`'s own `sed` line substitutes only the
`@TOKEN@`-style placeholders — never `$PDK_ROOT`/`$PDK` — so the literal,
unexpanded string is handed to ngspice, which (confirmed independently by
#43's reporter, several isolated minimal reproductions) does not expand
shell/OS environment variables inside a `.lib`/`.include` netlist directive.
#43's reporter reran this exact script against a real installed PDK and
**every one of the 60 runs failed** with this error, contradicting
`RECORD-001`'s own "no NA rows" claim.

This builder cannot independently re-run the testbench (no PDK is installed
in this environment) and so cannot resolve #43 here — nor is resolving it
this issue's scope. This record proceeds on the measured values as the
**best currently-available evidence** rather than blocking on #43, for two
reasons stated plainly rather than assumed away:

1. `RECORD-001`'s own narrative contains detailed, specific, and internally
   self-consistent findings that would be unusual to fabricate wholesale —
   e.g. the band-select-inert-at-low-`VCTRL` finding is cross-checked by an
   independent probe of `xvco.xbias.degb` (1.61 µV vs. 0.84 µV) that a
   simple hand-estimate would not think to construct — consistent with a
   real run having occurred on whatever host/ngspice build produced it
   (ngspice `.lib`/`.include` environment-variable expansion is plausibly a
   version- or build-dependent behavior; #43 confirms non-expansion on its
   own reporter's specific `ngspice-47` build, not on every build that has
   ever run this template).
2. The qualitative conclusion this record reaches (§ "Decision" below) is
   **structurally robust** to the specific numeric values shifting by a
   plausible re-measurement margin: it depends on (a) the divider's
   structural N-range, which is independent of this sim entirely, and (b)
   the VCO's floor being far above what any credible `f_ref` (single-digit
   to tens-of-MHz, matching both sibling repos' own reference ranges) can
   reach at `N = 4` — a conclusion that would survive even a large
   percentage shift in the measured floor, since `445.3/4 = 111.3 MHz`
   already exceeds a plausible `f_ref` ceiling by 4–5×, not by a rounding
   margin.

**Consequence for this record's own numbers**: if #43's eventual fix
produces a materially different re-measured VCO band, the *specific* MHz
values this record derives (§ "Decision") need a follow-up, superseding
decision record — but the *qualitative* resolution (row 3's floor moves from
4 to the divider's own structural floor of 64; row 2's floor moves up
materially from 1 MHz) is very unlikely to reverse. This record's own
numbers are therefore stated as the best current derivation, not as
immune from revision.

---

## Why "amend row 2 alone" and "amend row 3 alone" both fail, and why the
## real fix touches both

Issue #40 frames four candidate resolutions as though they were largely
alternatives. Working the arithmetic through in full shows two of the four
are decisively ruled out, and the remaining two are not actually
independent — the real fix requires **both** together.

**Amending row 2 alone cannot work.** Even raising row 2's floor to its own
ceiling (25 MHz) does not rescue `N = 4`: `f_out = 4 × 25 = 100` MHz, still
less than half the VCO's measured floor (445.3 MHz). Reaching the floor at
`N = 4` requires `f_ref ≥ 445.3 / 4 = 111.3` MHz — a reference frequency
category neither sibling repo's own spec ever considered (gf180-pll: 1–25
MHz; sky130-pll inherits the same shape), and far outside what a crystal-
class reference input is for. No credible row-2 range rescues the ported
row-3 floor.

**Amending row 3 alone (to the divider's own [64, 127]) is necessary but not
sufficient without also touching row 2.** With `N ∈ [64, 127]` and the
*ported* `f_ref` ceiling of 25 MHz unchanged, `N = 64` at `f_ref = 25 MHz`
asks for `f_out = 1600` MHz — **above** the measured ceiling of 1562.0 MHz,
a target the VCO cannot reach. The ported row-2 ceiling is close (2.4%
over) but not exactly consistent with the new row-3 floor; leaving it
unchanged would let the interface contract claim an `f_ref` value that has
no valid `N` at all (since `N = 63` is outside the amended range and
`N = 64` overshoots).

**Restoring gf180-pll's chain-length-termination + one-hot mux (candidate
"change the divider," without also touching rows 2/3) does not fix the
contradiction either**, and this is the sharpest finding of this record: the
mux/termination mechanism only widens which *shorter* effective chain
lengths are reachable (letting `N` go as low as gf180-pll's own floor,
`N = 4`) — it does nothing about the VCO's own measured floor. Regardless of
what the divider can produce, `N = 4` still requires `f_ref ≥ 111.3` MHz to
reach 445.3 MHz, which restoring the mux does not change. **The root
constraint is the VCO's own measured tuning range, not the divider's
implementation.** This also means gf180-pll `DR-001` Decision 3's own stated
reason for choosing the Vaucher family over a pulse-swallow prescaler —
"a pulse-swallow floor of `N ≈ 12–16` would exclude `N = 4`" — does not
transfer to SG13G2/SG13CMOS5L's own numbers: this design's effectively
useful `N` floor (64, or higher depending on `f_ref`, see below) is already
far above any pulse-swallow prescaler's own structural floor, so that
specific argument is moot here regardless of which divider family is used.
This does **not** reopen DR-001's own architecture decision (see
"Relationship to DR-001"); it is a factual finding this record needs to
correctly evaluate candidate 3 and considered rejected.

**Amending the VCO band (candidate "change the VCO band") is rejected on
practical, not just arithmetic, grounds.** The VCO is already schematic-
captured, device-level laid out (`layout/sg13cmos5l-pll/`, issue #24/PR
#32 — 477/482 devices, DRC-clean, schematic-matched) and simulated
(`RECORD-001`). Nothing in this analysis motivates a VCO redesign — no
requirement demands a lower tuning range than what the ring already
achieves; the actual contradiction is entirely a downstream bookkeeping
mismatch between the *ported* `f_ref`/`N` capability ranges and the *real*
device that was subsequently built and measured. Re-deriving the VCO to hit
a hypothetical 4–25 MHz-compatible floor (roughly two orders of magnitude
lower than the measured floor) would mean abandoning already-laid-out,
DRC-clean, schematic-matched silicon-adjacent work for a change nothing in
the spec or the brief requires.

**Conclusion**: the defensible resolution amends **both** row 2 and row 3
together, using the measured VCO band and the divider's own structural range
as the two fixed points the new `f_ref` range is solved against.

---

## Decision

**Row 3 (multiplication ratio)**: amend the ported `N ∈ [4, 64]` (no holes)
to **`N ∈ [64, 127]`, no holes**, matching the as-drawn 6-cell ÷2/3 chain's
own structural range exactly (`N = 2^6 + Σp_i·2^i`). The "no holes"
*property* is preserved — every integer in the new range remains reachable
by varying the 6 per-cell modulus bits — only the *window* shifts up to
where the real divider (and, per the analysis above, the real VCO) actually
operate.

**Row 2 (reference input)**: amend the ported `f_ref = 1–25 MHz` to
**`f_ref ≈ 3.5–24.4 MHz`**, derived directly from the measured VCO band
divided by the new row-3 endpoints:

- **Floor**: `445.3 MHz (VCO floor) / 127 (max N)` = **3.51 MHz** — the
  lowest `f_ref` at which the divider's *widest* available ratio (`N = 127`)
  still reaches the VCO's measured floor. Below this, no `N` in the amended
  range reaches a valid output at all.
- **Ceiling**: `1562.0 MHz (VCO ceiling) / 64 (min N)` = **24.4 MHz** — the
  highest `f_ref` at which the divider's *narrowest* available ratio
  (`N = 64`) still stays within the VCO's measured ceiling. Above this,
  `N = 64` would ask the VCO to exceed its measured maximum.

Row 2's interface contract *shape* (CMOS square wave, rising-edge trigger,
30–70% duty) is **not** amended — only the frequency range. The electrical
levels (`V_IL`/`V_IH`) remain `re-derive`, unaffected by this record, per
row 2's own existing disposition.

Verified against the reworked ranges: no `f_ref` in `[3.51, 24.4]` MHz is
left with zero usable `N` in `[64, 127]` (at `f_ref = 3.51` MHz, `N = 127`
gives exactly the VCO floor; at `f_ref = 24.4` MHz, `N = 64` gives exactly
the VCO ceiling; intermediate `f_ref` values have progressively wider usable
`N` sub-ranges as they move away from either edge — see the two boundary
computations above, which are the tightest cases). No `N` in `[64, 127]` is
left with zero usable `f_ref` in the amended range, by the same two boundary
computations run in the other direction.

**Row 6/6a (loop bandwidth / phase margin)**: **left as-is, no amendment
needed.** The row's existing disposition already ports only the
*sampled-loop stability criteria* (`f_c < f_ref/10`, ≥45° phase margin) and
the *mechanism* (a coarse Icp trim keyed to `f_ref`), deferring every kHz
number to re-derivation — it does not hard-code an `f_ref` value or range
anywhere in its own text, so it is not made incorrect by this record's `f_ref`
amendment. The **consequence** worth recording explicitly (since #41 depends
on it for its own R1-sizing target, per the Curator's note on #40): the
`f_c` stability ceiling implied by the amended `f_ref` range is now
**0.35–2.44 MHz** (`f_ref/10` at the two new endpoints) — a *narrower, less
restrictive* worst case than the ported range implied (`f_ref = 1 MHz` would
have forced `f_c < 100 kHz`; the amended floor of 3.5 MHz relaxes the
tightest case to `f_c < 350 kHz`). This is a byproduct of raising `f_ref`'s
floor, not an independent finding, and it makes any future loop-filter
sizing pass's job easier, not harder.

### Applying the amended ranges to `spec/porting-plan.md`

`spec/porting-plan.md` §1.2 rows 2 and 3 are updated in this same PR to
state the amended ranges directly, with a citation to this record — see the
diff. Row 6/6a is left untouched, per the "left as-is" finding above.

---

## Relationship to DR-001

DR-001 (status: `proposed`, not yet ratified) Decision 3 states: "Exact
chain length ... is re-derived once SG13G2's own top-of-band `N`
requirement is known (porting-plan §1.2 row 3 ports the *requirement*,
`N ⊇ 4–64` with no holes, as-is ...)." This record supersedes that specific
numeric citation (the `N ⊇ 4–64` requirement itself, now amended to
`N ⊇ 64–127`) without reopening or reversing DR-001 Decision 3's own
**architecture** choice (cascaded ÷2/3 Vaucher chain, static CMOS, VCO-
clocked final retiming flop) — that choice is not touched here, and the
"amend the divider" candidate this record rejects (above) is about
restoring the chain-length-termination/mux *mechanism* within the same
Vaucher family, not about switching families.

This record does note, as a side finding for whoever eventually ratifies
DR-001, that one piece of DR-001 Decision 3's own supporting rationale (the
Vaucher chain's advantage over a pulse-swallow prescaler specifically
*because* `N = 4` must be reachable) no longer applies to this design's real
numbers, since `N = 4` turns out to be unreachable regardless of divider
family. This does not, by itself, argue for re-opening DR-001's architecture
decision — the ÷2/3 chain is already schematic-captured and device-level
laid out, and no other rationale in DR-001 Decision 3 is affected — but a
future record that does revisit DR-001 should account for it rather than
repeat the now-inapplicable `N = 4` argument. **Not re-litigated here**;
DR-001's architecture decision is out of this issue's scope.

## Alternatives considered

- **Amend row 2 only** (candidate 1, issue #40) — rejected: does not rescue
  `N = 4` at any credible `f_ref` (see "Why 'amend row 2 alone' ... fails"
  above). Insufficient on its own.
- **Amend row 3 only, to the divider's [64, 127]** (candidate 2, issue #40)
  — insufficient on its own: leaves the ported 25 MHz `f_ref` ceiling
  slightly over-claiming what `N = 64` can reach (1600 MHz vs. the measured
  1562.0 MHz ceiling). Adopted **in combination** with an amended row 2,
  not standalone.
- **Restore the divider's chain-length termination + one-hot mux**
  (candidate 3, issue #40) — rejected as *ineffective* for this specific
  contradiction (not merely undesirable): the VCO's measured floor, not the
  divider's fixed chain length, is the binding constraint on `N = 4`'s
  reachability. Restoring the mux would be extra design/verification cost
  for a capability (`N` values below 64) that no credible `f_ref` in a
  crystal-reference range could ever use with this VCO. Not ruled out
  forever — if a future, separately-motivated requirement needs finer `N`
  resolution than the ÷2/3 chain's own [64, 127] window natively offers,
  restoring the mux is a legitimate way to get it, but that is a distinct
  question from resolving this contradiction.
- **Change the VCO band** (candidate 4, issue #40) — rejected: the VCO is
  already schematic-captured and device-level laid out; nothing in the spec
  or the Chipalooza Challenge #6 brief motivates a lower tuning range, and
  discarding already-verified, DRC-clean work to chase a spec number that
  was itself an unverified carry-over from gf180-pll is exactly backwards
  per this repo's own CLAUDE.md ("the PDK is the variable, not the design").
- **Block on issue #43 before writing this record** — rejected: #43 is a
  testbench-reproducibility defect, not evidence that the underlying circuit
  behavior is different from what was measured; per "Evidentiary caveat"
  above, this record's qualitative conclusion is robust to a plausible
  re-measurement, and blocking a spec reconciliation on a tooling
  reproducibility bug (already tracked, not owned by this issue) would
  stall #27/#41's own already-dependent work for no corresponding gain in
  confidence.

## Consequences

**What this makes possible**:

- #41 (loop-filter R1 resize) has a concrete `f_ref` range (3.5–24.4 MHz) to
  size its own Icp-trim/R1 target against, and a *relaxed* (not tightened)
  `f_c` ceiling floor (350 kHz vs. the previously-implied 100 kHz worst
  case).
- Any future frequency-planning work (choosing a specific `f_ref`/`N` pair
  for a specific target output) now has a self-consistent pair of ranges
  that do not silently promise unreachable operating points.

**What this makes harder / what is accepted**:

- The divider's own usable `N` resolution is now a ~2:1 span (`[64, 127]`),
  materially narrower than gf180-pll's ported ~16:1 span (`[4, 64]`) — fewer
  distinct output-frequency steps are available at a fixed `f_ref` than the
  ported spec implied. This is a real capability reduction versus the
  carried-over expectation, not merely a bookkeeping change, and should be
  weighed if a future requirement needs finer frequency-selection
  granularity (in which case, restoring the chain-length-termination
  mechanism — rejected above as unnecessary for *this* contradiction — would
  be the mechanism to revisit).
- The reference-input range's practical floor is now materially higher
  (3.5 MHz vs. the ported 1 MHz) — any system-level assumption that this
  design accepts sub-3.5-MHz references must be corrected wherever it may
  already exist (this record's own search found none outside
  `spec/porting-plan.md` itself).

**What remains open**:

- Issue #36's own functional/retiming-margin measurement of the divider
  chain is unaffected by this record and still needed — this record amends
  the *numeric range*, not the retiming-margin closure `spec/porting-plan.md`
  row 3 still calls `re-derive`.
- Issue #43's testbench-reproducibility defect is unaffected by this record
  and still needs a fix + full re-run; if that re-run produces a materially
  different VCO band, a superseding decision record must re-derive this
  record's specific MHz values (the qualitative direction is expected to
  hold — see "Evidentiary caveat").
- DR-001 remains `proposed`, not ratified; whoever ratifies it should
  account for this record's "Relationship to DR-001" note.
