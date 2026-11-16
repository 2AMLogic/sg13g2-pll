# RECORD-003: the committed 1500 samples re-graded against DR-013's evidence-coverage bound (+/-11.92 %) — 99.60 % inside it, and `klt yield`'s sample-size verdict turns `sufficient` (required_n 8907 -> 154)

- **Slug**: `sg13cmos5l-cp-icp-trim-mc`
- **Issue**: #385 (follow-up to #178). The limit:
  `spec/decision-records/DR-013-cp-mismatch-limit.md`. The measurement that
  retires the old screening value:
  `../../sg13cmos5l-closed-loop-lock/records/RECORD-014-cp-mismatch-phase-error-gain.md`.
- **Append-only, and nothing is re-simulated.** This record does not edit
  `RECORD-001`, `RECORD-002`, `reports/sim.mc.json`, `reports/yield.mc.json`,
  `corners/mc-samples.csv`, `testbench/mc.request.json` or any other
  committed file. It adds `testbench/yield.proposed-limit.limits.json` and
  `reports/yield.mc.proposed-limit.json`, which sit **beside**
  `reports/yield.mc.json`, never over it. The samples are the same 1500 draws
  `RECORD-002` collected; only the limits the grader is handed differ.
- **Tooling**: `klt yield` from a throwaway `uvx --from
  "klayout-tools[yield]"` environment (the host tool carries no
  `klt_yield_native`; nothing is installed host-wide) --
  `klt 0.9.2.dev964+g02db14ecf46b`, i.e. klt 0.9.2. No simulator ran. The samples were produced
  by the campaign `RECORD-002` records: `ngspice` on the Spot batch fleet,
  PDK `ihp-sg13cmos5l` revision `607e18d4bd9214a52575c194b4181ef449f9252f`
  (the `sim/README.md` pin), shipped as bytes by
  `options.stage_model_inputs`.
- **Corner coverage is `RECORD-002`'s, unchanged**: 5 mismatch-enabled
  process sections x 3 temperatures (-40 / 27 / 125 C) x N = 100 = 1500
  samples, seed 178, VDD fixed at 3.3 V in the netlist, no resistor corner
  (`cp` has none). The grader's `source_corners` lists all 15.

## What changed, and what it is not

`RECORD-002` graded `mismatch_pct` against **+/-3.5 %**, a screening value
derived in one step from closed-loop records made on the **pre-DR-010**
`cp`: 5 % (the row-7 static-phase criterion) divided by 1.4293 pp/pp
(9.176 % phase error per 6.42 % mismatch), assumed linear through the
origin. `RECORD-014` re-measured that gain on the committed DR-010 `cp` and
found it is **-0.0394 to -0.0484 pp/pp** — about 30x smaller, of the
opposite sign, and *not* through the origin (forcing the intercept to zero
multiplies the fit residual by 22x to 90x). The +/-3.5 % number therefore no
longer follows from anything, and **DR-013 retires it** rather than
re-deriving a replacement from row 7: inverting the measured fit puts the
5 % crossing at |mismatch| = 88 % to 106 %, which is 7x to 9x outside the
measured span and about 23 sigma out, so no bound is extrapolated from it.

The bound this record grades against is therefore **not a spec limit and
not a requirement**. `testbench/yield.proposed-limit.limits.json` states it
in its own header: **+/-11.92 %** is the *evidence-coverage* bound — the
narrower end, on each side, of the DC mismatch span over which `RECORD-014`
actually demonstrated that the DR-010 `cp` meets the 5 % criterion
(-11.9984 / +11.9244 % at -40 C and -11.9616 / +11.9686 % at 27 C). It
answers "what fraction of the campaign's draws land where row-7 compliance
has actually been shown?", which is a different question from "what
fraction pass spec", and the answer must not be read as the second one.

**No `target_yield` is declared**, for exactly the reason `RECORD-002`
declares none: a yield *claim* needs a ratified limit, `spec/target-spec.md`
proposes no `cp` mismatch number, and DR-013 is `Status: proposed`. The
envelope reports an estimate and `status: "reported"`, never a pass/fail.

## Result

`reports/yield.mc.proposed-limit.json`, produced by

    cd reports && uvx --from "klayout-tools[yield]" klt yield sim.mc.json \
        --measurement mismatch_pct \
        --limits ../testbench/yield.proposed-limit.limits.json --format json

| | `RECORD-002` (`reports/yield.mc.json`, +/-3.5 %) | **this record** (+/-11.92 %) |
|---|---|---|
| limits | min -3.5 / max 3.5 | min -11.92 / max 11.92 |
| samples | 1500, 0 errored | 1500, 0 errored (same draws) |
| mean / sigma | -0.3201 % / 3.8769 % | identical (the fit does not depend on the limits) |
| **empirical yield** (Clopper-Pearson, pooled) | 63.47 %, 95 % CI [60.97 %, 65.91 %] | **99.60 %, 95 % CI [99.13 %, 99.85 %]** |
| normal-model yield | 63.17 % | 99.78 % |
| Cp / Cpk | 0.3009 / 0.2734 | **1.0249 / 0.9973** |
| sigma-to-spec | 0.820 | **2.992** |
| limiting side | lower | lower |
| `sample_size.observed_ci_halfwidth` | +/-2.468 pp | **+/-0.361 pp** |
| `sample_size.required_n` (default +/-1 pp target) | 8907 | **154** |
| **`sample_size.verdict`** | `insufficient` | **`sufficient`** |

Six of the 1500 draws fall outside +/-11.92 %: four below (-13.6157,
-12.2143, -12.1868, -11.9292) and two above (+12.9329, +14.0069). By
corner: `mos_ff_mismatch`/-40 C 2/100, `mos_sf_mismatch`/-40 C 2/100,
`mos_tt_mismatch`/-40 C 1/100, `mos_tt_mismatch`/27 C 1/100; the other
eleven corners have none. That is the same -40 C-dominated pattern
`RECORD-002` reports for the sigma itself, at the tail instead of the body.

**No resize is needed at this bound, so no resize follow-up is filed for
sample size.** The `insufficient` verdict `RECORD-002` carries is not a
property of the campaign: it is `klt yield`'s statement that a 63 %
estimate needs 8907 samples to resolve to +/-1 pp. At 99.6 % the same 1500
samples already resolve to +/-0.36 pp and `required_n` falls to 154. This
is the outcome #385's own argument predicted — that `required_n` scales as
`p(1-p)` and so is a function of the limit, which is why the limit had to
be settled before anyone bought more samples.

**This does not make T1 item `6.analog` `met`**, and nothing here tries to.
`manifests/README.md` grades only against a two-key-ratified spec; DR-013 is
`proposed`, this envelope declares no `target_yield`, and
`manifests/sg13g2-pll.json` is not re-pointed at it — item 6 still cites
`reports/sim.mc.json` through `reports/yield.mc.json` and still grades
`unmet` / `undersized_sample`. Moving it is out of this record's scope.

## The `negative_control` warning: still open, and why

Both envelopes carry

    no measurement declared a negative_control -- this campaign has no
    seeded, known-bad variant demonstrating that the statistics above can
    actually detect a degraded design

and this record does **not** clear it. The disposition, stated plainly:

- The bench's own control (`reports/sim.negative_control.dr010-pinned.json`:
  `mos_tt` with no mismatch library, 20 samples, every stddev exactly 0) is
  the **opposite** kind of control. It proves the draw is live by showing
  zero spread when mismatch is off. `klt yield` wants a *known-bad* variant's
  own samples — a seeded defect whose yield must come back
  distinguishably worse — so the existing control does not qualify, and
  pointing the grader at it would be wrong rather than merely unhelpful.
- Declaring one needs a second Monte Carlo campaign (a deliberately
  offset `cp`, sampled the same way) and `klt yield-samples` to merge the
  two reports into a sample-set document. That document, not
  `reports/sim.mc.json`, would then be the grader's input — which is
  outside what this record was scoped to produce.
- **The material for it now exists.** `RECORD-014`'s
  `../../sg13cmos5l-closed-loop-lock/testbench/gen_mismatch_gain_requests.py`
  builds a `cp` whose DC mismatch is +11.97 % at 27 C from the committed
  snapshot by scaling one mirror leg. A mismatch-enabled campaign on that
  snapshot is a seeded known-bad variant for exactly this measurement: its
  draws would centre about 12 % from the committed mean, 3.1 sigma out, so
  the yield difference could not be sampling noise.

Issue #389, filed for the 125 C deck gap, carries this item as well, so it
is tracked rather than dropped.

## What this does not bound

- **Everything `RECORD-002` does not bound** still applies unchanged: these
  are schematic-level draws of one `cp` instance at one operating point
  (`VOUT` = 2.40 V, `Iref` = 10 uA, 3.3 V), pre-layout, with no `f_ref`,
  trim-code or supply axis.
- **The bound itself is evidence coverage, not a requirement.** 99.60 % is
  not a pass; no number here is compared with a ratified spec.
- **`RECORD-014`'s own limits propagate**: the span it demonstrates was
  measured at `mos_tt` only, at two of three temperatures (the proposal
  deck does not acquire at 125 C), on the proposal deck rather than the
  committed loop, and by *injecting* mismatch on one mirror leg rather than
  drawing it. A drawn sample perturbs every device, so landing inside
  +/-11.92 % of up/dn ratio is not by itself proof that a given draw meets
  row 7.
- **PDK-revision sensitivity** is unchanged and still binding: see
  `../README.md`, "Mismatch is PDK-revision sensitive".

## Reproduce

```bash
cd sim/sg13cmos5l-cp-icp-trim-mc/reports
uvx --from "klayout-tools[yield]" klt yield sim.mc.json \
    --measurement mismatch_pct \
    --limits ../testbench/yield.proposed-limit.limits.json \
    --format json > yield.mc.proposed-limit.json

# sanity: the SAME command at the retired screening limit reproduces
# RECORD-002's pooled yield exactly (63.4667 %, CI [60.972 %, 65.908 %],
# Cpk 0.27340, required_n 8907, verdict insufficient)
printf '{"measurements":{"mismatch_pct":{"min":-3.5,"max":3.5}}}' > /tmp/old.json
uvx --from "klayout-tools[yield]" klt yield sim.mc.json \
    --measurement mismatch_pct --limits /tmp/old.json --format json
```

That sanity re-grade was run and matched `reports/yield.mc.json` field for
field on `limits`, `yield`, `capability` and `sample_size`, which is what
establishes that `--limits` re-grades the committed samples rather than
changing them.
