# RECORD-015: the 125 C non-acquisition is the VCO's own tuning range — band-11 tops out at 1270.1 MHz at the 3.3 V rail, 9.9 MHz short of the 1280 MHz an N = 64 loop needs

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #389 (part 1), the follow-up `RECORD-014` filed for its 125 C
  non-acquisition gap. The design finding this records: #426 (filed at
  `loom:triage`; no `vco` change is made here).
- **Append-only.** This record edits no earlier record, snapshot, CSV or
  script in this slug. It adds
  `../testbench/gen_125c_acquisition_requests.py` and
  `../testbench/collect_125c_acquisition.py`, and the evidence files
  `../corners/{sim_vco_openloop_125c.json, vco_openloop_125c.csv,
  vco_openloop_125c.decks.sha256.csv, vco_openloop_125c.staged_pdk.sha256.csv,
  vco_openloop_125c_raw/, sim_125c_nominal.json,
  loop_nominal_125c_metrics.json}`. The one committed file it modifies
  outside this directory is `../corners/matrix.md`, whose RECORD-014 section
  this record's verdict replaces (outcome (b) of the issue's acceptance
  criteria — matrix.md already stated the limitation and deferred the cause
  to this issue).
- **Tooling**: `ngspice-47` on the Spot batch fleet
  (`environment.engine_version: "47"` in both reports), submitted and
  collected by `klt sim --batch-set`, client `klt 0.9.2.dev1029+g76f47afa48f1`.
  PDK `ihp-sg13cmos5l` revision `607e18d4bd9214a52575c194b4181ef449f9252f`
  (the `sim/README.md` pin), shipped to the workers as
  bytes — the staged hashes in both reports match what the committed
  `../../sg13cmos5l-cp-icp-trim-mc` campaign and RECORD-014 cite
  (`psp103.osdi` `2e4299c4...`, `psp103_nqs.osdi` `839b1644...`,
  `mosvar.osdi` `25e64a37...`, `r3_cmc.osdi` `4fead17b...`,
  `cornerMOShv.lib` staged hash `40c41404...` in the stage normalization,
  local `sha256` `5a1f862d...`). Fleet jobs: `klt-sim-dcc446b0de33` (VCO
  grid), `klt-sim-36052c300e2a` (closed-loop sanity point). Python 3.12
  (stdlib only), `set num_threads=1` per unit.
- **A discarded first submission preceded this record.** The same three
  requests were first generated against `/home/ubuntu/share/pdk/
  ihp-sg13cmos5l` — a tree whose `cornerMOShv.lib` carries the pin's own
  `sha256` (`5a1f862d...`) but whose `sg13g2_moshv_mod*.lib` and OSDI bytes
  are the post-2026-10-15 install's, where the HV MOS mismatch subcircuits
  default to `mm_ok=0`. Its control campaign returned sigma exactly 0.0000 %
  (the invisible-null trap `../../sg13cmos5l-cp-icp-trim-mc/testbench/
  gen_requests.py`'s `mm_ok` guard exists for), and every unit it produced
  was discarded uncommitted; jobs `klt-sim-f3765f252318`,
  `klt-sim-da1fd63a880a`, `klt-sim-70583a612331`. All committed evidence
  here comes from the re-generated requests pointed at the pinned tree
  (`ihp-sg13cmos5l.bak-20261015T153815Z` on this host), verified by running
  that tree through `gen_requests.py`'s `mm_ok` closure check before
  submission. Lesson recorded for the next builder: a pin-matching
  `cornerMOShv.lib` does not make a tree the pin — check the closure.

## What was measured, and what it answers

RECORD-014 left four candidates for the 125 C non-acquisition: the
behavioural divider's XSPICE bridges, the `R1` x20 filter, the `VC0` = 2.46 V
start point, and the VCO's own 125 C tuning range. This record runs two
measurements — the open-loop VCO point first (one corner, the issue's
implementation guidance), and the unperturbed closed-loop point as the
sanity anchor — and the answer is the fourth candidate.

### 1. Open-loop VCO sweep — band `11`, `mos_tt` / `res_typ` / 125 C, `vctrl` to the rail

The DUT is this slug's frozen `../netlist-snapshots/vco.spice` with
`XCDECAP` commented out — byte-identical device lines to
`../../sg13cmos5l-vco-kvco-table`'s DUT copy, which is where the deck body
comes from (`tb_vco_kvco.sp.tmpl`, staged-closure form, `.ic
v(xvco.ring1)=0.5`, period measured between rising edges 3 and 4 at 1.65 V
exactly as that bench measures). Band `11` (`B0V` = `B1V` = 3.3 V) is the
proposal deck's own selection (`run_closed_loop_otabuf.sh`: `B0V=$VDD;
B1V=$VDD; VC0=2.46`). Ten units, one 40 ns transient each, ~1 s per unit on
the fleet.

**First, the band inputs were verified live** — the issue's verified
correction 4 warns that the committed Kvco table shows band code inert
there, and that nothing may be concluded from the band choice before this
deck proves the inputs move frequency. A four-band probe at `vctrl` = 2.1 V:

| band | `f_osc` at 2.1 V |
|---|---|
| `00` | 761.7 MHz |
| `10` | 904.9 MHz |
| `01` | 994.8 MHz |
| `11` | **1062.2 MHz** |

39.5 % relative spread, and a local re-measure with the window moved to
edges 20–21 confirms the ring is already settled at edges 3–4 (period drift
0.03 % across the 40 ns window). **Band `11` is the fastest band, and the
proposal deck selects it — the curve below is measured in the loop's own
best case.** (The committed table's band-`11` rows are genuine band-`11`
measurements at every `vctrl` ≥ 0.9 V; the "band-inert" reading behind the
issue's verified correction 4 holds only at the 0.3 V rows, where all four
codes collapse in every bundle — 13 of the table's 15 `(bundle, vctrl)`
groups are band-live. A dated correction to that effect is appended to the
issue body.)

The band-`11` curve, all seven sweep points:

| `vctrl` (V) | `f_osc` (MHz) |
|---|---|
| 0.3 | 487.3 |
| 0.9 | 570.1 |
| 1.5 | 819.3 |
| 2.1 | 1062.2 |
| 2.7 | 1214.5 |
| 3.0 | 1247.6 |
| **3.3 (the rail)** | **1270.1** |

**The VCO does not reach 1280 MHz at any `vctrl` the 3.3 V supply can
deliver.** The curve saturates into the rail — the last whole volt delivers
55.6 MHz and the final 0.3 V only 22.5 MHz — and tops out **9.9 MHz short**
of the `f_ref` × N = 20 MHz × 64 = 1280 MHz target. Report:
`../corners/sim_vco_openloop_125c.json` (deck-list envelope; per-unit
`stdout` committed under `../corners/vco_openloop_125c_raw/`), parsed table
`../corners/vco_openloop_125c.csv`, deck manifest
`../corners/vco_openloop_125c.decks.sha256.csv`, staged-PDK manifest
`../corners/vco_openloop_125c.staged_pdk.sha256.csv`.

Consistency with the committed Kvco table: this curve is bracketed by that
table's own band-`11` rows, exactly as the corner ordering predicts —
`typ`/27 C reaches 1359.1 MHz at 2.7 V, `slow`/`mos_ss`/125 C only 1113.8
MHz, and this `mos_tt`/125 C point reads 1214.5 MHz at 2.7 V, between them.

### 2. Closed-loop sanity point — the unchanged deck reproduces RECORD-014 before any variable is changed

RECORD-014's unperturbed `mm_nom` deck (`k` = 1 — `gen_mismatch_gain_requests.perturb_cp` returns the committed `cp_otabuf.spice` byte for byte, `sha256` `c8a55d8d...` asserted at generation), narrowed to the single failing corner `mos_tt` / `res_typ` / 125 C. Metrics computed with the committed, self-tested functions (`mismatch_gain_metrics.lock_trace_from_edges` + `cpdiag_metrics.summarize`) over the report's `v(ref)`/`v(fb)` crossing series. Report `../corners/sim_125c_nominal.json`, metrics `../corners/loop_nominal_125c_metrics.json`.

| | RECORD-014 `mm_nom` 125 C | **this re-run** |
|---|---|---|
| `vc_avg` | 3.28989 V | **3.28989 V** |
| `df/f_ref` (final-20 mean) | -0.5985 % | **-0.59848 %** |
| longest dual-lock run | 0 | **0** |
| final-20 "phase" mean | -36.6659 % | **-36.6659 %** |
| ref / fb edges | 50 / 50 | 50 / 50 |

Reproduced to every printed digit. The deck, the snapshots and the pinned
PDK all reproduce at 125 C, and the loop behaves exactly as RECORD-014
reported: `vctrl` hard against the rail, `fb` running 0.6 % slow, never
acquiring.

## The four candidates

- **VCO range: CONFIRMED — this is the cause.** The open-loop measurement
  above: the plant itself cannot reach 1280 MHz at 125 C in the deck's own
  band at any `vctrl` ≤ 3.3 V. No change downstream of the VCO can pull the
  loop to a frequency the VCO cannot produce.
- **Behavioural divider (XSPICE bridges): ruled out by measurement.** The
  sanity point's `df/f_ref` = -0.5985 % means `f_fb` = 19.880 MHz, and the
  50 `fb` edges arrive at the ÷64 rate of a ~1272 MHz `clk` — the divider
  divides by exactly 64. A ÷63 misdivide would instead show the loop locking
  (or seeking) `f_out` = 1260 MHz with `df` = -1.5625 %; neither is
  observed. The railed loop's implied `f_out` (1272.3 MHz from `df`) sits
  0.23 % from the open-loop curve at the same rail voltage (1269.4 MHz
  interpolated at 3.29 V) — the closed loop rides the VCO's own curve to
  its ceiling, which is only possible if the divider and the bridges pass
  the frequency through correctly.
- **`R1` x20 loop filter: NOT TESTED** — and moot given the confirmed cause:
  the loop is driving `vctrl` UP into the rail (the charge direction is
  correct), so the filter conducts; its bandwidth shapes the approach, not
  the ceiling the plant saturates at.
- **`VC0` = 2.46 V start point: NOT TESTED** — moot for the same reason: it
  sets only where on the curve the transient starts; the loop has already
  saturated `vctrl` and is still 0.6 % slow, so no start point inside the
  supply range changes the outcome.

## Verdict, and what follows from it

**The 125 C non-acquisition is a design finding, not a deck finding: the
VCO's band-`11` tuning range at `mos_tt` / 125 C tops out ~10 MHz below the
1280 MHz the loop needs.** Per the issue's acceptance criteria this takes
outcome (b): `../corners/matrix.md`'s RECORD-014 section now states this
diagnosed cause in place of its "filed as issue #389" deferral, and the
design question itself is filed as **#426** (`loom:triage`) — band ladder
range, VCO core sizing, or a spec-row re-scope are that issue's to weigh. No
`vco` change is made in this slug, and no deck fix is attempted: a deck that
locked at 125 C would have to detune the band selection away from the
proposal's own `B0V` = `B1V` = VDD choice, which would measure a different
deck, not this one.

## Corners: what ran, what did not

- **Ran**: `mos_tt` / `res_typ` / 125 C / 3.3 V (both measurements); band
  `00`/`01`/`10` at 2.1 V only (the band probe); band `11` at
  0.3/0.9/1.5/2.1/2.7/3.0/3.3 V.
- **Not run**: every other process/resistor/temperature/supply corner; the
  closed-loop deck at any other start point or band (moot, above); the
  committed `divider_chain` (this slug's deck is the behavioural-divider
  proposal deck — the finding is stated for the VCO subckt, which is the
  committed `vco` in both decks).
- No unit timed out; both jobs reached terminal state and every corner
  returned (nothing is recorded as not-collected).

## Reproduce

```bash
export PINNED_PDK=<ihp-sg13cmos5l checkout at 607e18d4... — verify the
                   mm_ok closure check passes, see the discarded-submission
                   note above>
cd sim/sg13cmos5l-closed-loop-lock/testbench
python3 -I test_collect_125c_acquisition.py         # offline self-test, no PDK
python3 -I gen_125c_acquisition_requests.py --pinned-pdk "$PINNED_PDK" /tmp/i389

klt sim --batch-set /tmp/i389/vco/request.json /tmp/i389/loop_nominal/request.json \
    --wait-for-capacity 600 --capacity-retries 3 -o /tmp/i389/sim-out --format json \
    --report-out /tmp/i389/batchset-report.json

python3 -I collect_125c_acquisition.py /tmp/i389/sim-out/request \
    /tmp/i389/vco/decks.sha256.csv /tmp/i389/sim-out/request-1/report.json \
    --vco-csv ../corners/vco_openloop_125c.csv \
    --loop-json ../corners/loop_nominal_125c_metrics.json
```

The CSV and the metrics JSON regenerate from the committed reports with no
simulator: `collect_125c_acquisition.py` re-parses
`../corners/vco_openloop_125c_raw/*.out` when handed the report directory
committed beside them, and the loop metrics recompute from
`../corners/sim_125c_nominal.json`'s crossing series alone.
