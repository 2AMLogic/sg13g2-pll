# RECORD-001: `cp` Icp-trim table and up/down mismatch (DC, PVT-cornered)

- **Slug**: `sg13cmos5l-cp-icp-trim`
- **Issue**: #27 (Part of #16, Chipalooza Challenge #6, SG13CMOS5L
  closed-loop PVT campaign) — the follow-up issue #23's three records each
  defer the Icp-trim table to.
- **DUT**: `cp` (SG13CMOS5L port, PR #26) — the full block (`inv_hv` x2 +
  `cp_leg_p` + `cp_leg_n` + `cp_dumpbuf`), instantiated verbatim from
  `../netlist-snapshots/cp.spice` (frozen at commit
  `db5ec6afaf79a04aeb13b9a43a4b5905472ff37a`). **No netlist derivation of any
  kind** — unlike the `sg13cmos5l-vco-kvco-table` record, this testbench
  needs no instance stripped.
- **Claim under test**: `spec/porting-plan.md` row 6/6a ("Loop bandwidth /
  phase margin") ports the *mechanism* — "a coarse Icp trim keyed to f_ref,
  not a filter redesign" — as-is, and marks "every kHz number and the
  trim-code table" as re-derive. This record delivers the trim table.
  Row 10 ("Reference spur") requires re-derivation "entirely from SG13G2's
  own charge-pump mismatch data"; this record delivers that mismatch data.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host.
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  writes `../corners/results.csv` (306 rows) and `../corners/compliance.csv`
  (3111 rows).
- **Reproducibility fix (issue #44)**: `../testbench/tb_cp_dc.sp.tmpl` used a
  literal `.lib $PDK_ROOT/$PDK/...` line. ngspice's `.lib`/`.include`
  directive parser only reliably expands OS environment variables on some
  builds (this record's own `ngspice-46`, evidently, since the numbers below
  did reproduce); a reproduction attempt on a different `ngspice-47` build
  hit a fatal "library file not found" error on every run instead, which the
  original `run.sh`'s `2>/dev/null` silently turned into a false `NA`
  result. Fixed by substituting `@PDK_ROOT@`/`@PDK@` tokens via `run.sh`'s
  own `sed` line (the same convention `@CORNER_MOS@` already used, and the
  same fix shape issue #43 applied to the pre-existing `vco-kvco-table`/
  `loop-filter-momcap`/`vco-decap-momcap` testbenches), and `run.sh`'s
  `2>/dev/null` was replaced with an explicit ngspice exit-code check.
  **Re-ran the full 306-row/3111-row matrix after the fix**
  (`ngspice-46`, same `~/share/pdk/ihp-sg13cmos5l` install this record
  already named): zero `NA` rows, zero fatal errors, and both
  `results.csv` and `compliance.csv` reproduce **byte-for-byte identical**
  to the values already committed here — the original numbers were real,
  not fabricated; only the template's env-var portability was broken.

## What is real here, and what is testbench

**Real**: every device in the `cp` block, its topology, its sizing, and the
PSP103 compact models behind `sg13_hv_nmos`/`sg13_hv_pmos` at five process
corners and three temperatures.

**Testbench-local, and NOT part of the committed design**: the cascode
current-mirror *reference* that drives the block's four bias pins.
`cp.sch` exposes `IBP`/`ICP`/`IBN`/`ICN` as external pins and contains no
bias generator (`design/README.md`: "Charge pump (`cp.sch`) has a single
fixed-current leg per polarity, no 2-bit unit-element Icp trim"). Driving
those pins with fixed *voltages* would make the measured current a property
of the absent bias network rather than of the charge pump, so this testbench
biases the block the way a cascode mirror is normally biased: a
diode-connected replica stack built from devices of exactly the W/L the leg
it mirrors uses (24 µm/1 µm PMOS, 8 µm/1 µm NMOS — read off the frozen
snapshot), driven by an ideal reference current. The replica instances are
named `XMREF*` in `../testbench/tb_cp_dc.sp.tmpl` so they cannot be mistaken
for design content.

**This makes the missing on-chip bias generator a real, recorded design
gap, not an assumption**: the trim table below is a table of *mirror
reference current* -> *delivered Icp*. Realising it on silicon requires a
bias block that does not exist in `design/sg13cmos5l/` today. See "Spec-row
disposition" for how that is carried forward.

## Sign convention

`icp` is the current the charge pump delivers **into** the `VOUT` node:
positive = sourcing into the loop filter (UP asserted), negative = sinking
out of it (DN asserted). In ngspice a voltage source's branch current is
positive flowing in at its `+` terminal, so this is exactly `i(Vout)` with
no flip. Verified empirically rather than assumed: the UP=1/DN=0 state must
source, and measures `+10.046 µA` at the 10 µA trim code (`mos_tt`, 27 C).

## Methodology

For each PVT point, trim code and UP/DN state, a DC sweep of `VOUT` from
0.15 V to VDD-0.15 V in 50 mV steps. The value at VDD/2 goes to
`results.csv` (the trim table); the full curve at the nominal 10 µA code
goes to `compliance.csv` (the compliance/mismatch data). See
`../corners/matrix.md` for the full axis rationale, including why no
resistor-corner and no MOM-cap axis applies to this DUT.

## Results — the Icp trim table

Across all 15 PVT points at 3.3 V (`../corners/results.csv`):

| Trim code (I_ref) | I_up range (µA) | I_dn range (µA) | Mirror gain I_up/I_ref | Up/down mismatch (%) |
|---|---|---|---|---|
| 2.5 µA | 2.516 – 2.520 | 2.622 – 2.678 | 1.0066 – 1.0080 | −6.09 … −4.07 |
| 5 µA | 5.027 – 5.033 | 5.198 – 5.288 | 1.0053 – 1.0067 | −4.94 … −3.33 |
| 10 µA | 10.041 – 10.054 | 10.302 – 10.442 | 1.0041 – 1.0054 | −3.81 … −2.53 |
| 20 µA | 20.059 – 20.083 | 20.423 – 20.643 | 1.0030 – 1.0041 | −2.78 … −1.77 |
| 40 µA | 40.073 – 40.114 | 40.522 – 40.873 | 1.0018 – 1.0029 | −1.89 … −1.10 |
| 80 µA | 80.035 – 80.116 | 80.482 – 81.051 | 1.0004 – 1.0015 | −1.16 … −0.56 |

**The trim ladder is essentially PVT-independent when driven from a current
reference.** The total spread of `I_up` across five process corners and a
165 C temperature span is **≤ 0.14%** at every code — the copy tracks the
reference, not the corner. This is the single most useful property for row
6/6a: it means the loop's `Icp` term contributes almost no corner spread of
its own to the loop gain, so the loop-bandwidth spread is dominated by
`Kvco` and by the filter's `R1`, both of which the sibling records already
bound. It is also *conditional* on the bias generator being a current
reference; a voltage-biased implementation would not inherit it.

**Supply sensitivity** (`mos_tt`, 27 C, 10 µA code, ±10% of 3.3 V per
`spec/porting-plan.md` row 18): `I_up` moves **+0.158%** and `I_dn`
**−1.185%** across the full 3.0 → 3.6 V range. Small, but it moves the two
legs in *opposite* directions, so it acts directly on the mismatch term
below rather than cancelling.

## Results — up/down mismatch (the reference-spur driver)

The N leg systematically sinks more than the P leg sources. At VDD/2 the
mismatch is **−2.5% to −6.1%**, worst at the smallest trim code and at cold,
best at the largest code and hot. It is *not* worst at the split
`mos_sf`/`mos_fs` corners — those land inside the `mos_ss`…`mos_ff` span —
which is a real and slightly counter-intuitive result: both legs are
cascoded and mirror-referenced, so the dominant mismatch mechanism here is
output-conductance/headroom asymmetry between a 24 µm PMOS stack and an
8 µm NMOS stack, not NMOS-vs-PMOS threshold skew.

Per-corner detail at the nominal 10 µA code, 3.3 V
(`../corners/compliance.csv`):

| MOS corner | T (C) | I_up @1.65 V (µA) | I_dn @1.65 V (µA) | mismatch (%) | dual-leg ±5% compliance | net mismatch @2.7 V (nA) |
|---|---|---|---|---|---|---|
| mos_tt | −40 | +10.046 | −10.402 | −3.48 | 0.70 – 2.75 V | −900.7 |
| mos_tt | 27 | +10.046 | −10.369 | −3.17 | 0.60 – 2.90 V | −812.4 |
| mos_tt | 125 | +10.049 | −10.330 | −2.76 | 0.50 – 3.05 V | −693.5 |
| mos_ss | −40 | +10.041 | −10.365 | −3.17 | 0.70 – 2.80 V | −856.8 |
| mos_ss | 27 | +10.041 | −10.337 | −2.90 | 0.60 – 3.10 V | −774.1 |
| mos_ss | 125 | +10.044 | −10.302 | −2.53 | 0.50 – 3.05 V | −663.6 |
| mos_ff | −40 | +10.051 | −10.442 | −3.81 | 0.70 – 2.75 V | −947.5 |
| mos_ff | 27 | +10.051 | −10.405 | −3.46 | 0.65 – 2.85 V | −853.1 |
| mos_ff | 125 | +10.054 | −10.360 | −3.00 | 0.50 – 3.05 V | −726.3 |
| mos_sf | −40 | +10.049 | −10.383 | −3.27 | 0.70 – 2.80 V | −874.3 |
| mos_sf | 27 | +10.049 | −10.353 | −2.98 | 0.60 – 2.95 V | −788.9 |
| mos_sf | 125 | +10.051 | −10.316 | −2.59 | 0.50 – 3.05 V | −673.8 |
| mos_fs | −40 | +10.044 | −10.422 | −3.69 | 0.70 – 2.75 V | −928.2 |
| mos_fs | 27 | +10.044 | −10.387 | −3.36 | 0.60 – 2.90 V | −837.0 |
| mos_fs | 125 | +10.046 | −10.345 | −2.93 | 0.50 – 3.05 V | −714.3 |

"dual-leg ±5% compliance" is the `VOUT` interval over which *both* legs stay
within 5% of their own mid-rail value. The usable window is roughly
**0.7 – 2.75 V** worst-case (cold), widening to 0.5 – 3.05 V hot — i.e. the
charge pump loses regulation at both rails well before the VCO's own `VCTRL`
range does. `sg13cmos5l-vco-kvco-table` swept `VCTRL` over 0.3 – 2.7 V; the
bottom 0.4 V of that range is **outside** this charge pump's cold-corner
compliance window, so the low end of the VCO's tuning curve is not reachable
in closed loop at the cold corner. Recorded as a real finding; closing it is
a sizing question, not a measurement question.

**Balance point.** The net mismatch (`state=both`) crosses zero at
`VOUT ≈ 0.95 – 1.02 V` at every corner except `mos_ff`/27 C and
`mos_fs`/27 C, where `compliance.csv` shows additional crossings at
0.20 V / 0.30 V — *below* the dual-leg compliance window, where neither leg
is in regulation, so they are headroom artifacts rather than a second
balance point. Above the balance point the pump nets *down*: −0.81 µA at
2.7 V (`mos_tt`, 27 C), i.e. **−8.1% of `Icp`** at the top of the VCO's
control range. That asymmetry — not the mid-rail figure — is the number a
reference-spur calculation must use, because a PLL locked near the top of
its band sits exactly there.

## Cross-checks

- **Mirror fidelity is not assumed**: `I_up/I_ref` is measured, and is
  within 0.8% of unity at every code and corner (largest deviation
  +0.80% at the 2.5 µA code, where the replica's own `VDS` headroom is
  smallest).
- **`both` is measured, not inferred**: the net mismatch current is measured
  with both switches asserted rather than subtracted from two separate
  runs, because both legs share the `VDUMP` node and the `cp_dumpbuf`
  follower. Comparing the two at `mos_tt`/27 C/10 µA: measured `both` =
  −323.2291 nA, while `I_up + I_dn` from the two separate runs =
  −323.2300 nA — agreement to 6 significant figures, so at DC the
  shared-`VDUMP` node introduces no measurable leg-to-leg interaction. That
  is a result, not an assumption that made the measurement redundant; and
  it says nothing about the *switching* case, which this record does not
  measure (see "What this does not bound").

## Spec-row disposition (per this repo's CLAUDE.md — no claim without a testbench)

- **Row 6/6a — Icp-trim table**: **bounded by this record.** The
  reference-current-to-`Icp` mapping, its PVT spread (≤0.14%), and its
  supply sensitivity (≤1.2% over ±10%) are all measured on the committed
  block. The *loop-bandwidth and phase-margin numbers themselves* are closed
  in the sibling record `sg13cmos5l-loop-bandwidth-pm`, which consumes this
  table.
- **Row 10 — reference spur**: **partially bounded — the charge-pump
  mismatch input is now real; the dBc number itself stays
  `insufficient-evidence`.** This record supplies exactly what
  `spec/porting-plan.md` row 10 asks for ("re-derive entirely from SG13G2's
  own charge-pump mismatch data") as *static* DC mismatch. A spur level in
  dBc additionally needs (a) the switching-transient charge mismatch (clock
  feedthrough and charge injection at the UP/DN switches, which is a
  transient quantity this DC record cannot see), (b) the PFD's own reset
  window / static phase offset setting how long both legs are on per
  reference cycle, and (c) a stable closed loop to define a carrier at all —
  and per the sibling loop-bandwidth record, the as-drawn loop has no stable
  operating point to measure a spur around. Marked `insufficient-evidence`
  explicitly; deferred to issue #37 (Part of #16).

## What this does not bound

- **Switching (dynamic) charge mismatch** — clock feedthrough, charge
  injection and the UP/DN skew through `XIUP`/`XIDN` are transient effects;
  every measurement here is DC with the switches held static.
- **Any closed-loop quantity** — no PFD, no filter, no VCO, no divider is
  present in this testbench.
- **Device mismatch (random)** — no per-instance mismatch model is available
  for `sg13_hv_nmos`/`sg13_hv_pmos` in this campaign; every number above is
  the nominal, matched-device result. The systematic P-vs-N asymmetry
  measured above is a *design* asymmetry, not a statistical one.
- **The bias generator** — it does not exist in the committed design (see
  "What is real here"), so the trim mechanism's own accuracy, monotonicity
  and code count are not measured by this record.
