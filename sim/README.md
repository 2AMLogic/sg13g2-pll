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
exists; neither SG13CMOS5L record below is a closed-loop testbench, so
neither applies yet to what's committed here.

## PDK scope — two independent campaigns, one convention

This repo targets two PDKs in parallel (`design/README.md` "SG13CMOS5L
port"): the original SG13G2 design directly under `design/`, and the
SG13CMOS5L port under `design/sg13cmos5l/`. Both campaigns use the directory
convention above, distinguished by the `<slug>` prefix (`sg13cmos5l-*` here;
an unprefixed or `sg13g2-*` slug for the original PDK once that campaign
starts). **As of this record, SG13G2 has no `sim/` results of its own yet**
— this issue's own scope (#23, Part of #16) is the SG13CMOS5L campaign only,
and it does not add, edit, or touch any SG13G2 result (there are none to
touch).

## SG13CMOS5L campaign status

Tracks issue #23 (Part of #16), which itself owns the specific obligation
`spec/decision-records/DR-003-sg13cmos5l-port-readiness.md` Finding 2 names:
every spec row sensitive to the design's three `cap_cmomi` MOM-cap instance
sites (`loop_filter.XC1`/`XC2`, `vco.XCDECAP`) must be swept across a
plausible MOM-model-uncertainty band, because the installed PDK's own
`cap_cmomi`/`cap_cmomf` models carry **no characterised process-corner or
mismatch spread** (`cornerCAP.lib`'s own header, confirmed directly by this
campaign — see records below) and are "not validated on CMOS5L silicon."

| Slug | Claim under test | Spec row(s) (`spec/porting-plan.md` §1.2) | Status |
|---|---|---|---|
| [`sg13cmos5l-loop-filter-momcap`](sg13cmos5l-loop-filter-momcap/) | `loop_filter` R1/C1/C2 corner + MOM-cap-uncertainty sensitivity (zero/pole location) | 6/6a (loop bandwidth / phase margin) | Zero/pole location **bounded** by a real PVT+MOM sweep; the row's own kHz/degree numbers stay `insufficient-evidence` (need the not-yet-re-derived Kvco table and Icp-trim table — see Deferred work below) |
| [`sg13cmos5l-vco-decap-momcap`](sg13cmos5l-vco-decap-momcap/) | `vco.XCDECAP` capacitance value + supply-decoupling pole sensitivity | 8 (period jitter), 12 (supply sensitivity) | Capacitance value **bounded** by a real MOM sweep; the absolute jitter-ps / dB-attenuation numbers stay `insufficient-evidence` (need a post-layout parasitic source impedance and a closed-loop phase-noise method ngspice cannot run today — DR-002 Decision 5) |
| [`sg13cmos5l-vco-kvco-table`](sg13cmos5l-vco-kvco-table/) | Open-loop `vco` frequency vs. `VCTRL` vs. 2-bit band code, real transient sweep (not MOM-cap-sensitive — no `cap_cmomi` instance survives this testbench's own XCDECAP-strip, see that record's "Tooling note") | 4/5 (Kvco bound / band-selection rule) | Kvco-vs-band-code table **bounded** by a real PVT-cornered open-loop sweep (3 corner bundles x 4 band codes x 5 `VCTRL` points); row 6/6a's own loop-bandwidth number still needs the Icp-trim table (deferred, see below), and row 3 (divider retiming margin) still needs the divider chain's own re-derivation |

**Deferred to follow-up issue #27** (Part of #16): the divider
retiming-margin closure (row 3, now unblocked on this record's own
top-of-band frequency data), the Icp-trim table and the actual
loop-bandwidth/phase-margin numbers that combine it with the filter data
above (row 6/6a), lock time (row 7), duty cycle (row 13), lock-detector
window/hysteresis (row 16), reference spur (row 10), and power (row 11) —
each needs either a closed-loop testbench, a long transient/tuning-range
sweep, or both, beyond what this issue's own per-device and open-loop
characterization methodology reaches in one session. None of these rows is
MOM-cap-sensitive in DR-003 Finding 2's own sense (they depend on active
devices, not the three flagged cap instances), so they are out of *this*
issue's specific DR-003 obligation even though they remain open
`spec/porting-plan.md` "re-derive" rows.

## Provenance of this convention

Per `spec/porting-plan.md` §1.3: this directory structure and its
append-only discipline are carried over from `2AMLogic/gf180-pll`'s own
`sim/README.md` (itself copied from `2AMLogic/gf180-bandgap`) — a
methodology convention, not circuit data, so no SG13G2/SG13CMOS5L
re-derivation applies to the convention itself.
