# sim/ — append-only PVT evidence records

This is the first work to land here (previously "Empty until the first work
lands here" — see the repo README's "Repo layout" and `spec/porting-plan.md`
§1.3, "Testbench / corner-harness structure"). The convention below is
carried over **as-is** from `gf180-pll`'s own `sim/README.md` (itself copied
from `2AMLogic/gf180-bandgap`) per that section's own disposition table — it
is methodology, not circuit data, so it needs no per-PDK re-derivation.

## Directory / naming convention

```
sim/
  <slug>/
    testbench/            ngspice deck(s) + any generator script that builds
                           per-corner netlists from them
    netlist-snapshots/    the exact design/**/netlist/*.spice this record
                           simulated, frozen at commit time -- independent of
                           whatever the live export says today
    corners/               the PVT/sensitivity matrix definition and the raw
                           per-corner results (a CSV or equivalent)
    records/               one Markdown file per run, `RECORD-NNN-<title>.md`,
                           numbered and never edited in place
```

One directory per **claim under test**, not per run — `<slug>` names the
claim (e.g. `sg13cmos5l-loop-filter-momcap`), and every new run against that
same claim adds a new `RECORD-NNN` file, not a rewrite of an old one. A
genuinely different DUT (a different block, a different question) gets its
own sibling slug rather than being folded into an existing one.

**Records are append-only.** A record's conclusion can be superseded by a
later record (e.g. a re-run against an updated netlist), but the old record
stays in place, unedited — the evidence trail is the history, not just the
latest answer.

**Netlist provenance.** Every record's `netlist-snapshots/` freezes the
exact `.spice` export it simulated, plus the commit SHA it was frozen at (in
each snapshot's own header comment) — independent of whatever
`design/**/netlist/*.spice` says by the time someone reads the record later.

**PVT corner matrix.** The default sweep is the full process x supply x temp
matrix; any subset (e.g. a passive network with no supply-dependent device,
so "supply corner" does not apply) must state the reason explicitly in the
record, not silently drop an axis. The corner *count* is PDK-specific — see
each record for the axes it actually swept and why.

**Closed-loop internal-timestep bound** and **charge-domain PFD/CP
characterization** (the other two `spec/porting-plan.md` §1.3 methodology
items carried over as-is) apply once a closed-loop or PFD/CP testbench
exists. **No record below is a transistor-level closed-loop testbench**, so
the internal-timestep bound still does not apply. The charge-domain PFD/CP
characterization is *partially* engaged as of issue #27:
`sg13cmos5l-cp-icp-trim` characterises the charge pump's own delivered
current and up/down mismatch, but at DC with the switches held static —
the *charge*-domain (per-reference-cycle, switching) part of that
methodology item is still not exercised, and that record says so in its own
"What this does not bound".

## PDK scope — two independent campaigns, one convention

This repo targets two PDKs in parallel (`design/README.md` "SG13CMOS5L
port"): the original SG13G2 design directly under `design/`, and the
SG13CMOS5L port under `design/sg13cmos5l/`. Both campaigns use the directory
convention above, distinguished by the `<slug>` prefix (`sg13cmos5l-*` here;
an unprefixed or `sg13g2-*` slug for the original PDK once that campaign
starts). **SG13G2 still has no `sim/` results of its own** — both campaign
issues to date (#23 and #27, each Part of #16) are scoped to the SG13CMOS5L
port only, and neither adds, edits, or touches any SG13G2 result (there are
none to touch).

## SG13CMOS5L campaign status

Tracks issues #23 and #27 (both Part of #16). #23 owns the specific obligation
`spec/decision-records/DR-003-sg13cmos5l-port-readiness.md` Finding 2 names:
every spec row sensitive to the design's three `cap_cmomi` MOM-cap instance
sites (`loop_filter.XC1`/`XC2`, `vco.XCDECAP`) must be swept across a
plausible MOM-model-uncertainty band, because the installed PDK's own
`cap_cmomi`/`cap_cmomf` models carry **no characterised process-corner or
mismatch spread** (`cornerCAP.lib`'s own header, confirmed directly by this
campaign — see records below) and are "not validated on CMOS5L silicon."
#27 picks up the rows #23 explicitly deferred: the ones needing a
charge-pump characterisation, a loop-level combination of the three
measured block records, or a longer/edge-resolved transient. The table
below is the whole campaign, both issues, in the order the records landed.

| Slug | Claim under test | Spec row(s) (`spec/porting-plan.md` §1.2) | Status |
|---|---|---|---|
| [`sg13cmos5l-loop-filter-momcap`](sg13cmos5l-loop-filter-momcap/) | `loop_filter` R1/C1/C2 corner + MOM-cap-uncertainty sensitivity (zero/pole location) | 6/6a (loop bandwidth / phase margin) | Zero/pole location **bounded** by a real PVT+MOM sweep; the row's own kHz/degree numbers stay `insufficient-evidence` (needed the not-yet-re-derived Kvco table and Icp-trim table; both landed, and `sg13cmos5l-loop-bandwidth-pm` below now closes the row) |
| [`sg13cmos5l-vco-decap-momcap`](sg13cmos5l-vco-decap-momcap/) | `vco.XCDECAP` capacitance value + supply-decoupling pole sensitivity | 8 (period jitter), 12 (supply sensitivity) | Capacitance value **bounded** by a real MOM sweep; the absolute jitter-ps / dB-attenuation numbers stay `insufficient-evidence` (need a post-layout parasitic source impedance and a closed-loop phase-noise method ngspice cannot run today — DR-002 Decision 5) |
| [`sg13cmos5l-vco-kvco-table`](sg13cmos5l-vco-kvco-table/) | Open-loop `vco` frequency vs. `VCTRL` vs. 2-bit band code, real transient sweep (not MOM-cap-sensitive — no `cap_cmomi` instance survives this testbench's own XCDECAP-strip, see that record's "Tooling note") | 4/5 (Kvco bound / band-selection rule) | Kvco-vs-band-code table **bounded** by a real PVT-cornered open-loop sweep (3 corner bundles x 4 band codes x 5 `VCTRL` points); row 6/6a's own loop-bandwidth number is now closed by `sg13cmos5l-loop-bandwidth-pm` below, and row 3 (divider retiming margin) still needs the divider chain's own re-derivation |
| [`sg13cmos5l-cp-icp-trim`](sg13cmos5l-cp-icp-trim/) | `cp` delivered current vs. mirror trim code, and up/down mismatch vs. output voltage (all-MOS DUT — no resistor and no `cap_cmomi` instance, so neither the RES-corner nor the MOM axis applies) | 6/6a (Icp-trim table), 10 (reference spur, mismatch input) | Icp-trim table **bounded** by 306 real DC sweeps (5 MOS corners x 3 temps + a ±10% supply sub-axis x 6 trim codes x 3 switch states): the mirror-referenced ladder tracks its reference to within 0.14% across the whole PVT matrix. Row 10's own dBc number stays `insufficient-evidence` — the *static* mismatch is now real, but a spur level additionally needs switching charge mismatch, the PFD reset window, and a stable loop to define a carrier |
| [`sg13cmos5l-loop-bandwidth-pm`](sg13cmos5l-loop-bandwidth-pm/) | Linearised open-loop gain around the **real** `loop_filter` subckt, with `Icp` and `Kvco` taken from the two measured records above | 6/6a (loop bandwidth / phase margin) | **`insufficient-evidence` CLEARED — and the bound is a failure to meet the criteria.** `f_c` = 0.33–4.64 MHz, PM = 1.55–20.33° across 90 real-subckt AC runs; **0 of 90 meet the ≥45° criterion** with the as-drawn filter, and `Icp` cannot trade one criterion against the other. A separate proposal sweep (`corners/proposal.csv`, explicitly *not* the committed design) shows `R1` ×20 with the 10 µA trim code meets both criteria at every PVT bundle. Also records that the ported `f_ref` = 1–25 MHz / `N` = 4–64 rows are mutually inconsistent with the measured VCO band |
| [`sg13cmos5l-vco-duty-cycle`](sg13cmos5l-vco-duty-cycle/) | Open-loop `vco` output duty cycle (rising *and* falling 50%-of-rail crossings), plus the ring's own average supply current | 13 (output duty cycle), 11 (power, one domain) | Duty cycle **bounded** by 300 real transient runs (5 MOS corners — including the `mos_sf`/`mos_fs` split corners the Kvco record left open — x 3 temps x 4 band codes x 5 `VCTRL` points): 43.74–51.56%, with **30 of 300 points below the 45% floor**, all at −40 C. Reproduces gf180-pll's own carried-forward duty-cycle design flag on a different process. Row 11 stays `insufficient-evidence` (only the `vdd_vco` and `cp` domains are measured) |

**Still deferred, and explicitly `insufficient-evidence`** (follow-up issues
filed off #27, Part of #16):

| Spec row | Why it is still open |
|---|---|
| 3 — divider retiming margin | Needs a functional `divider_chain` testbench. An exploratory testbench built during #27 did **not** produce a trustworthy result (the chain's first ÷2 stage divides correctly at 600 MHz but the inner stages do not toggle, and the block has no reset pin, so an initialisation artifact could not be ruled out inside that session). Nothing was published rather than publishing an unverified "the divider is broken" claim |
| 7 — lock time | Needs a transistor-level closed-loop transient. The linearised loop's own measured PM ≤ 20.3° means a settling time derived from that linearisation would not describe the committed design, so none is reported |
| 10 — reference spur | Static charge-pump mismatch is now real (`sg13cmos5l-cp-icp-trim`); the dBc figure additionally needs switching charge mismatch, the PFD reset window, and a *stable* closed loop to define a carrier around |
| 11 — power | `vdd_vco` (measured, 3.09–8.88 mW) and `cp` (measured, ≈66 µW at the 10 µA code) are bounded; `pfd`, `divider_chain` and `lock_detector` are not, so no whole-PLL total is claimed |
| 16 — lock-detector window / hysteresis | Not attempted in #27. Note `lock_detector.XCW`/`XDW.XC1` are `cap_cmomi` instances that DR-003 Finding 2's own three-instance list does **not** name, so any MOM-cap sensitivity found there is new scope |

None of the deferred rows is MOM-cap-sensitive in DR-003 Finding 2's own
sense *except* row 16 (see above), so they remain outside that record's
specific obligation even though they are open `spec/porting-plan.md`
"re-derive" rows.

## Provenance of this convention

Per `spec/porting-plan.md` §1.3: this directory structure and its
append-only discipline are carried over from `2AMLogic/gf180-pll`'s own
`sim/README.md` (itself copied from `2AMLogic/gf180-bandgap`) — a
methodology convention, not circuit data, so no SG13G2/SG13CMOS5L
re-derivation applies to the convention itself.
