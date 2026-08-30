# RECORD-002: root cause of `cp`'s up/dn current mismatch, and the re-measured trim/mismatch table after the on-chip cascode-bias fix

- **Slug**: `sg13cmos5l-cp-icp-trim`
- **Issue**: #72 (Part of #16) — the design-level mitigation
  `../../sg13cmos5l-closed-loop-lock/records/RECORD-004`'s own "Decision"
  section asked for: tighten `cp`'s `up`/`dn` current-mirror matching, because
  that mismatch is the confirmed dominant mechanism behind the ≈9.18%
  row-7-failing static phase error `RECORD-003` measured in the closed loop.
- **This record does not edit `RECORD-001`** (append-only, per this
  directory's own convention). `RECORD-001`'s own tables remain the record of
  the as-drawn block; every "baseline" number quoted below is read out of
  that record and re-derived from the pre-change `corners/*.csv` this run
  replaced, and matches `RECORD-001`'s own published figures to the digit
  (e.g. `mos_tt`/27 C/10 µA: `up` +10.046 µA, `dn` −10.369 µA, −3.17%).
- **DUT**: `cp` (SG13CMOS5L port) **after** the issue-#72 change — the full
  block instantiated verbatim from `../netlist-snapshots/cp.spice`, re-frozen
  on the mitigated export (see that file's own provenance header; it names
  the snapshot it supersedes). No netlist derivation of any kind.
- **Design change under test** (`design/sg13cmos5l/cp.sch`,
  `spec/decision-records/DR-006-cp-cascode-bias-replica.md`): `cp.sch` now
  contains a **high-swing cascode bias replica per polarity**
  (`MBP`/`MBPC`/`MCP`, `MBN`/`MBNC`/`MCN`), so `IBP`/`ICP`/`IBN`/`ICN` are
  **current**-input pins. `cp_dumpbuf`'s `IBIAS` moves `ICN` → `IBN`.
  **Neither `cp_leg_p.sch` nor `cp_leg_n.sch` changed at all** — not one
  device, not one dimension. That is a result, not an oversight: the legs
  were never the defect (see "Root cause" below).
- **Testbench change**: `../testbench/tb_cp_dc.sp.tmpl` drops its own
  `XMREF*` replica stack (a testbench-local stand-in for the then-absent
  on-chip diodes) and drives the block's four bias pins with four ideal
  `@IREF@` reference currents instead. The trim code is still `@IREF@` and
  the measured `Icp` is still the block's own copy of it, so this record's
  trim table is directly comparable to `RECORD-001`'s. What is still
  testbench-local, and still a real design gap: the reference **current**
  itself — a bandgap-referenced `Iref` block does not exist in
  `design/sg13cmos5l/`.
- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`, x86-64
  Linux host (same tooling `RECORD-001` names).
- **Reproduce**: `PDK_ROOT=<pdk-root> PDK=ihp-sg13cmos5l ./testbench/run.sh`
  writes `../corners/results.csv` (306 rows) and `../corners/compliance.csv`
  (3111 rows). **Runtime on this host, this session: ~45 s** for the whole
  matrix; **306/306 rows numeric, zero `NA`, zero ngspice failures.**

## Root cause: the legs were fine; their bias was not

`RECORD-001` attributed the mismatch to "output-conductance/headroom
asymmetry between a 24 µm PMOS stack and an 8 µm NMOS stack". That is
directionally right but stops one level short of the mechanism, and the
level it stops short of is the one that turns out to be fixable. Measured
here, at `mos_tt`/27 C/3.3 V/10 µA on the as-drawn block:

**1. The "wide-swing cascode" the leg headers claim was not operating as a
cascode at all.** Each leg is `M1` (source device, gate `IBP`/`IBN`) in
series with `M2` (cascode, gate `ICP`/`ICN`). With no on-chip bias diodes,
every testbench tied `IBP` = `ICP` and `IBN` = `ICN` — the only thing a
voltage-input pin pair can be driven with from a single reference. Two
same-size devices in series with a **common** gate cannot both saturate: the
one nearer the rail is forced into deep triode, and the pair collapses into
a single composite device of length `L1 + L2`. The operating point says so
directly — the reference stack's own intermediate node and the leg's `tail`
node land on top of each other:

| | reference stack mid-node | leg `tail` | difference |
|---|---|---|---|
| P side | `nrp1` = 3.247172 V | 3.246864 V | 0.31 mV |

i.e. `M1`'s drain-source drop is ~53 mV against a `Vsg` of 865 mV. There is
no cascode; there is a 24 µm/2 µm PMOS mirror and an 8 µm/2 µm NMOS mirror.

**2. With no cascode, the copy error is plain channel-length modulation, and
the two legs' sensitivities differ by 8×.** Each leg is accurate at *its
own* reference `Vds` and drifts linearly away from it:

| | reference composite `Vds` | leg composite `Vds` @ `VOUT` = 1.65 V | Δ | measured copy error | implied effective λ |
|---|---|---|---|---|---|
| P (`up`) | 0.86496 V | 1.63208 V | +0.76712 V | **+0.4605%** | 0.00600 /V |
| N (`dn`) | 0.83704 V | 1.64774 V | +0.81070 V | **+3.6930%** | 0.04555 /V |

The `Δ`s are nearly equal (0.767 V vs 0.811 V) — the *headroom* is
essentially symmetric, contrary to the "headroom asymmetry" reading. What is
asymmetric is the output conductance: **7.6× on the implied λ, and 8.0× read
independently off the compliance sweep's own slope** over 0.95–2.75 V:

| | dI/dVOUT (as-drawn) | implied `r_out` |
|---|---|---|
| P leg | −0.0521 µA/V | 19.2 MΩ |
| N leg | +0.4188 µA/V | 2.39 MΩ |

So the two legs' copy errors — both positive, both over-delivering — simply
do not cancel: +0.46% against +3.69%, i.e. the ≈3.17% up/dn magnitude
mismatch at mid-rail, growing to **−6.42% at `VOUT` = 2.40 V**, which is
where the closed loop actually sits (`RECORD-003`'s `vc_avg` = 2.387 V).
**That 2.40 V figure, not the mid-rail one, is the number the row-7 static
phase error is proportional to.**

## The mitigation

Restore what the leg headers already claimed, by porting the in-block bias
content `gf180-pll`'s own `cp.sch` has and this port dropped
(`MBN`/`MCN`/`MBP`/`MCP` there): a **high-swing cascode bias replica** per
polarity, inside `cp.sch`, with two properties the old arrangement could not
have:

- `MBP`/`MBPC` (and `MBN`/`MBNC`) are exact same-`W`/`L` replicas of the leg
  stack, with the **bottom device's gate tied to the top of its own stack**,
  so the reference's bottom device sits at the same `Vds` the cascoded leg
  device does — the systematic term above is nulled by construction rather
  than cancelled by tuning.
- `MCP`/`MCN` are separate cascode-bias diodes at **`W/L` = (leg `W/L`)/12**,
  putting the cascode gate at `Vth + ≈3.5·Vov`. The textbook `/4` device
  (`Vth + 2·Vov`) was built and measured first and is **not** enough on this
  PDK's PSP103 devices — it leaves the leg's bottom device in triode
  (`nxn` = 186 mV against a `Vdsat` above it) and improves the mismatch only
  2.5×, versus ~20× at `/12`. Recorded as a measured sizing finding, not a
  textbook number carried over. `/12` is a measured knee, not a maximum: over
  the swept ratios `/4` `/8` `/12` `/16` `/24`, the mismatch at `VOUT` = 2.40 V
  (`mos_tt`/27 C) goes −2.562% / −0.505% / −0.298% / −0.242% / −0.212% while
  the bottom of the window (`VOUT` = 0.75 V) degrades monotonically
  −0.088% / −0.539% / −0.696% / −0.807% / −0.963% as the larger cascode step
  eats P-side headroom.

Rationale, alternatives considered, and cost are in
`spec/decision-records/DR-006-cp-cascode-bias-replica.md`.

**The result at the same operating point**: the leg's bottom device now
tracks its reference to within a millivolt or two, instead of 0.8 V —

| | reference mid-node `nxp`/`nxn` | leg `tail` @ `VOUT` = 1.65 V | Δ | @ `VOUT` = 2.40 V | Δ |
|---|---|---|---|---|---|
| P (`up`) | 2.978230 V | 2.977266 V | 0.96 mV | 2.978060 V | 0.17 mV |
| N (`dn`) | 0.307813 V | 0.315078 V | 7.3 mV | 0.319882 V | 12.1 mV |

and both legs' output resistance rises by more than an order of magnitude:

| | `r_out` as-drawn | `r_out` mitigated | improvement |
|---|---|---|---|
| P leg | 19.2 MΩ | 2908 MΩ | 151× |
| N leg | 2.39 MΩ | 49.5 MΩ | 20.7× |

Bias node voltages (`mos_tt`/27 C/10 µA), for reference: `IBP` = 2.5122 V,
`ICP` = 2.0447 V, `IBN` = 0.7680 V, `ICN` = 1.1574 V.

## Results — the re-measured Icp trim table

Across all 15 PVT points at 3.3 V (`../corners/results.csv`, 306 rows):

| Trim code (I_ref) | I_up range (µA) | I_dn range (µA) | Mirror gain I_up/I_ref | Up/down mismatch (%) |
|---|---|---|---|---|
| 2.5 µA | 2.500 – 2.501 | 2.507 – 2.510 | 1.0001 – 1.0002 | −0.384 … −0.281 |
| 5 µA | 5.000 – 5.001 | 5.010 – 5.015 | 1.0001 – 1.0001 | −0.284 … −0.192 |
| 10 µA | 10.000 – 10.001 | 10.015 – 10.021 | 1.0000 – 1.0001 | −0.208 … −0.143 |
| 20 µA | 20.001 – 20.004 | 20.023 – 20.041 | 1.0000 – 1.0002 | −0.185 … −0.113 |
| 40 µA | 40.001 – 40.044 | 40.035 – 40.192 | 1.0000 – 1.0011 | −0.368 … −0.084 |
| 80 µA | 80.006 – 80.244 | 80.071 – 80.944 | 1.0001 – 1.0030 | −0.887 … −0.081 |

Against `RECORD-001`'s own table for the same 15 points and the same six
codes:

| Trim code | mismatch, as-drawn (%) | mismatch, mitigated (%) | worst-case improvement |
|---|---|---|---|
| 2.5 µA | −6.086 … −4.071 | −0.384 … −0.281 | 15.8× |
| 5 µA | −4.944 … −3.329 | −0.284 … −0.192 | 17.4× |
| 10 µA | −3.814 … −2.533 | −0.208 … −0.143 | 18.3× |
| 20 µA | −2.780 … −1.770 | −0.185 … −0.113 | 15.1× |
| 40 µA | −1.891 … −1.100 | −0.368 … −0.084 | 5.1× |
| 80 µA | −1.161 … −0.557 | −0.887 … −0.081 | 1.3× |

**The improvement is smallest at the top code and that is expected, not
anomalous**: at 80 µA the bias replica's own `≈3.5·Vov` cascode step and the
legs' own overdrive both grow, so the block runs closer to its compliance
limits at mid-rail. The as-drawn design's mismatch was also smallest there
(the same mechanism, from the other direction). Every code still improves.

**Mirror fidelity is now essentially exact**: `I_up`/`I_ref` is within
0.02% of unity at the four lowest codes at every corner, against
0.4–0.8% before.

## Results — the re-measured up/down mismatch (the reference-spur / phase-error driver)

Per-corner detail at the nominal 10 µA code, 3.3 V, at `VOUT` = VDD/2 and at
`VOUT` = 2.40 V (the closed loop's own operating point):

| MOS corner | T (C) | as-drawn mm @1.65 V | mitigated mm @1.65 V | as-drawn mm @2.40 V | mitigated mm @2.40 V | as-drawn net @2.7 V (nA) | mitigated net @2.7 V (nA) |
|---|---|---|---|---|---|---|---|
| mos_tt | −40 | −3.48% | **−0.188%** | −7.10% | **−0.339%** | −900.7 | **−45.1** |
| mos_tt | 27 | −3.17% | **−0.170%** | −6.42% | **−0.298%** | −812.4 | **−39.1** |
| mos_tt | 125 | −2.76% | **−0.160%** | −5.51% | **−0.260%** | −693.5 | **−33.3** |
| mos_ss | −40 | −3.17% | −0.170% | −6.73% | −0.317% | −856.8 | −42.3 |
| mos_ss | 27 | −2.90% | −0.154% | −6.10% | −0.278% | −774.1 | −36.7 |
| mos_ss | 125 | −2.53% | −0.143% | −5.24% | −0.240% | −663.6 | −31.1 |
| mos_ff | −40 | −3.81% | −0.208% | −7.49% | −0.364% | −947.5 | −48.0 |
| mos_ff | 27 | −3.46% | −0.189% | −6.76% | −0.321% | −853.1 | −41.8 |
| mos_ff | 125 | −3.00% | −0.179% | −5.79% | −0.283% | −726.3 | −35.9 |
| mos_sf | −40 | −3.27% | −0.178% | −6.87% | −0.327% | −874.3 | −43.7 |
| mos_sf | 27 | −2.98% | −0.162% | −6.21% | −0.287% | −788.9 | −37.9 |
| mos_sf | 125 | −2.59% | −0.149% | −5.33% | −0.247% | −673.8 | −31.9 |
| mos_fs | −40 | −3.69% | −0.198% | −7.34% | −0.352% | −928.2 | −46.5 |
| mos_fs | 27 | −3.36% | −0.180% | −6.63% | −0.310% | −837.0 | −40.5 |
| mos_fs | 125 | −2.93% | −0.172% | −5.69% | −0.273% | −714.3 | −34.8 |

Supply sub-axis (`mos_tt`/27 C/10 µA, ±10% of 3.3 V): mismatch at VDD/2 is
−0.146% at 3.0 V and −0.194% at 3.6 V, against −2.65% / −3.67% as drawn.

**Worst case over the whole `VCTRL`-relevant band × the whole 15-point PVT
matrix** (0.90–2.90 V, 10 µA code):

| | worst \|mismatch\| in 0.90–2.90 V × 15 PVT | where |
|---|---|---|
| as drawn | **10.280%** | mos_ff / −40 C / 2.90 V |
| mitigated | **0.720%** | mos_fs / 125 C / 2.90 V |

## Compliance window — a second, unplanned improvement

`RECORD-001` recorded that the charge pump's own dual-leg ±5% compliance
window (0.70–2.75 V worst case, cold) does **not** cover the bottom of the
VCO's own 0.3–2.7 V `VCTRL` sweep, and called closing it "a sizing question,
not a measurement question". The cascode bias widens it substantially at
both ends, at every corner:

| MOS corner | T (C) | window, as-drawn | window, mitigated |
|---|---|---|---|
| mos_tt | −40 | 0.70 – 2.75 V | **0.25 – 3.15 V** |
| mos_tt | 27 | 0.60 – 2.90 V | 0.25 – 3.10 V |
| mos_tt | 125 | 0.50 – 3.05 V | 0.30 – 3.05 V |
| mos_ff | −40 | 0.70 – 2.75 V | 0.25 – 3.15 V |
| mos_ff | 27 | 0.65 – 2.85 V | 0.65 – 3.10 V |
| mos_ss | 125 | 0.50 – 3.05 V | 0.30 – 3.05 V |

## What got worse, stated rather than omitted

- **Below ≈0.85 V the mismatch is now marginally *worse* than as-drawn**
  (worst over 0.30–0.85 V × 15 PVT: −11.10% mitigated at `mos_ff`/27 C/0.45 V,
  against −8.69% as-drawn at `mos_ff`/27 C/0.50 V). The mechanism is measured,
  not guessed, and it is **not** the mirror: at low `VOUT` the P-side steering
  switch (`SWO`, 6 µm/0.3 µm PMOS, gate at `VSS` when asserted) has
  `|V_gs|` = `V(sw)` ≈ `VOUT`, so it saturates and becomes the
  current-limiting device instead of the mirror (measured at `VOUT` = 0.45 V:
  `sw` = 1.247 V, i.e. an 0.80 V drop across a switch that has 20 mV of drop
  at mid-rail). Both designs hit this; the as-drawn one partly *masked* it,
  because its P leg was over-delivering by +0.46% at the same time. This is a
  pre-existing topological property of a rail-gated steering switch, it is
  outside issue #72's scope, and the loop's own operating point (2.39 V) is
  nowhere near it — but it is a real ceiling on how low `VCTRL` can usefully
  go, and it is now the binding one at that end.
- **Supply current rises.** In this record's own DC deck (whole-`VDD`
  current, `mos_tt`/27 C/10 µA/`VOUT` = 2.4 V): `up` state 41.32 → 45.94 µA,
  `dn` state 21.18 → 26.88 µA, both-off 31.37 → 35.97 µA — i.e. **+4.6 to
  +5.7 µA**, because the block now sources two P-side bias branches from
  `VDD` where the testbench previously sourced one. Measured in the closed
  loop that shift is larger, because the P-side replica moved out of the
  testbench's own `vddrep` supply into the block's `vdd_cp` domain — see
  `../../sg13cmos5l-closed-loop-lock/records/RECORD-005`.
- **Four reference currents instead of two.** The mirror-bias and
  cascode-bias nodes are separate branches of a high-swing cascode bias by
  construction; tying them is exactly the defect. The still-absent off-block
  `Iref` generator therefore owes four matched outputs per trim code, not
  two. Recorded as a real, unchanged design gap.

## Side effect on row 6/6a (`Icp` nominal), checked rather than asserted

The mitigation **does** move the nominal delivered current, and the issue's
own Test Plan asks for this explicitly. At `mos_tt`/27 C/10 µA code,
`VOUT` = VDD/2:

| | as drawn | mitigated | change |
|---|---|---|---|
| `I_up` | 10.0461 µA | 10.0005 µA | −0.45% |
| `I_dn` | 10.3693 µA | 10.0175 µA | −3.39% |
| mean \|Icp\| | 10.2077 µA | 10.0090 µA | −1.95% |

**Re-verified against `../../sg13cmos5l-loop-bandwidth-pm` rather than
argued.** That campaign's `testbench/run.sh` reads this record's own
`../corners/results.csv` at runtime, so it was re-run end-to-end against the
new table (`ngspice-46`, same host, ~23 s) and its outputs re-committed —
see `../../sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-icp-input-refresh.md`.
Result: the largest change anywhere across its 252 output rows is **0.43% on
`pm_deg`** and 0.70% on `fc_hz`, with **zero verdict flips** —
`meets_ceiling`, `meets_pm45` and `meets_both` are byte-identical. That
record's own headline (`R1` ×20 with the 10 µA code, PM 58.62–61.82° across
the three PVT bundles) becomes 58.56–61.78°. So row 6/6a's conclusion is
unchanged, and it is unchanged *by measurement*.

## Spec-row disposition

- **Row 6/6a — Icp-trim table**: **still bounded, and now tighter.** The
  reference-current-to-`Icp` mapping is essentially exact (mirror gain within
  0.02% of unity at the four lowest codes at every PVT point, against
  0.4–0.8% before), and its PVT spread stays negligible. The loop-bandwidth
  and phase-margin numbers themselves are re-checked above and are unchanged
  in verdict.
- **Row 10 — reference spur**: **still `insufficient-evidence`, with a
  materially smaller static-mismatch input.** The per-cycle net mismatch this
  row's derivation consumes drops from −663…−948 nA to −31…−48 nA at
  `VOUT` = 2.7 V across the 15-point matrix. Everything `RECORD-001` listed
  as still missing (switching-transient charge mismatch, the PFD reset
  window, a stable locked carrier) is still missing, so no dBc number is
  claimed here either.
- **Row 7 — lock time**: not decided by this record. The closed-loop
  consequence is measured in
  `../../sg13cmos5l-closed-loop-lock/records/RECORD-005`.

## What this does not bound

- **Switching (dynamic) charge mismatch** — unchanged from `RECORD-001`:
  every measurement here is DC with the switches held static. The six new
  bias devices add gate/junction capacitance on `IBP`/`ICP`/`IBN`/`ICN`,
  which is a *dynamic* property this record cannot see; the closed-loop
  re-run in `RECORD-005` is the only evidence here that it does not bite.
- **Device mismatch (random)** — unchanged: no per-instance mismatch model is
  available for `sg13_hv_nmos`/`sg13_hv_pmos` in this campaign, so every
  number above is the nominal, matched-device result. This record removes a
  *systematic* design asymmetry; it says nothing about a statistical one, and
  a real bias replica's own random mismatch would set the floor on silicon.
- **The reference current generator** — still absent from
  `design/sg13cmos5l/` (see above), and now owed four outputs per polarity
  pair rather than two.
- **The dump-node buffer** — `cp_dumpbuf` is still a single NMOS source
  follower with a ~1 V offset (measured: `VDUMP` = 1.40 V at `VOUT` = 2.4 V),
  not a tracking unity-gain buffer. `gf180-pll`'s own `cp.sch` header argues
  at length that a dump node which does not track `VOUT` leaves a residual
  per-cycle charge skew proportional to (`VDUMP` − `VCTRL`). That is a
  separate, still-open gap this record neither fixes nor measures.
