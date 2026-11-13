# sg13cmos5l-cp-icp-trim-mc — Monte Carlo bench for the `cp` up/dn mirror mismatch

Issue #178 (T1 item 6, "Statistical claims carry Monte Carlo evidence").
Sibling of `../sg13cmos5l-cp-icp-trim/` (same DUT, same bias; that bench
measures corners, this one measures spread).

**Status: the campaign has run.** 1500 samples (5 mismatch process sections
x 3 temperatures x N = 100, seed 178) on the batch fleet, a `klt yield`
envelope in `reports/yield.mc.json`, and the estimate with its confidence
interval in `records/RECORD-002-cp-mismatch-mc-yield.md`. Both controls were
re-run on the refreshed DUT. The #191 blockers are cleared; see "History"
for what replaced them.

## What is measured

One `cp` instance (`netlist-snapshots/cp.spice`, the **DR-010** `cp` frozen
from `design/sg13cmos5l/netlist/cp.spice` at commit `093ab2c`), Iref = 10 uA
trim code, VDD = 3.3 V, VOUT = 2.40 V (the closed loop's own operating
point, `../sg13cmos5l-cp-icp-trim/records/RECORD-002`). One DC sweep of
`Vup` over {0, 3.3 V} with DN = 3.3 V - UP gives the DN-leg current
(point 0) and the UP-leg current (point 1) from the **same** random draw:

    mismatch_pct = (Iup + Idn) / ((Iup - Idn) / 2) * 100        (Idn < 0)

Supply is fixed at 3.3 V in the netlist (no `corners.supply_v` axis); the
corner axes are 5 MOS mismatch sections x {-40, 27, 125} C. `cp` has no
resistor, so no resistor corner applies (same statement as the sibling bench).

## Mismatch is PDK-revision sensitive — read this before re-running

`sg13_hv_nmos`/`sg13_hv_pmos` carry PDK-supplied per-instance mismatch under
ngspice: the `mos_{tt,ss,ff,sf,fs}_mismatch` sections of `cornerMOShv.lib`
pull in `sg13g2_moshv_mismatch.lib` (one-sigma Pelgrom-style parameters) and
`sg13g2_moshv_mod_mismatch.lib`, whose instance parameters are `agauss(...)`
draws of the form `agauss(w, sigma, (mm_ok != 1 ? 0 : 1))`. The gate is the
**subcircuit instance parameter `mm_ok`**, and IHP moved its default between
the two `ihp-sg13cmos5l` revisions `../README.md` names:

| Tree | `.subckt sg13_hv_[np]mos … mm_ok=` | Enable lives in |
|---|---|---|
| `PDK-PIN` `607e18d4…` (the repo's reproducibility target) | `1` | the model file's own default |
| install pin `f7bca326…` (what the fleet image and `$PDK_ROOT` carry today) | `0` | the xschem symbol, which now netlists `mm_ok=@mm_ok` per instance |

`design/sg13cmos5l/netlist/cp.spice` was netlisted with the **older**
symbols, so its MOS instance lines carry no `mm_ok=` at all. Run this bench
against the newer tree and every `agauss` collapses to its nominal: the
campaign returns **sigma exactly 0 on every measurement**, with no error, no
warning and `status: pass`. A zero-spread run is indistinguishable from a
perfectly matched circuit unless you already know to look.

Two things guard against that:

1. **`testbench/gen_requests.py` refuses to emit a request it cannot prove
   will draw.** `--pinned-pdk` is required (no `$PDK_ROOT` fallback) and the
   generator reads the resolved mismatch library's `.subckt` defaults,
   aborting unless both HV MOS devices default to `mm_ok=1`.
2. **The negative control and the positive probe are run on the same deck**
   before the campaign; the probe is what fails loudly if the draw is dead.

`klt sim`'s own per-family mismatch-activity report cannot help here: it
reports `active: null` ("not independently verified for PDK family
`sg13cmos5l`") whether or not mismatch is live. That tool gap is
2AMLogic/klayout-tools#5486, which describes this exact `mm_ok` shape; the
guard above is the local stand-in until it lands.

No sigma value in this directory is invented; all are the PDK's.

## Seed, N, controls

| Item | Value |
|---|---|
| Seed | 178 (`monte_carlo.seed`; per-sample seeds are SHA-256 derived, echoed per sample in the report and in `corners/mc-samples.csv`) |
| N | 100 per corner x 15 corners = 1500 samples (`mc.request.json`) |
| `vary` | `mismatch` |
| Negative control | `negative_control.request.json`: section `mos_tt` (no mismatch library), 20 samples. Every stddev is exactly 0. Committed: `reports/sim.negative_control.dr010-pinned.json` |
| Positive probe | `positive_probe.request.json`: `mos_tt_mismatch`, 3 samples. Non-zero spread; exits 3 on the screening limit. Committed: `reports/sim.positive_probe.dr010-pinned.json` |

The negative control's single value, **-0.298465 %**, equals the sibling
bench's nominal at VOUT = 2.40 V (`RECORD-002`: -0.298 %), so this deck
reproduces the corner-bench number on the DR-010 `cp` before any mismatch is
added.

The #191 reports (`reports/sim.negative_control.json`,
`reports/sim.positive_probe.json`) are the pre-DR-010 runs and are **not**
overwritten or edited; they belong to `records/RECORD-001`.

## Result, in one table

Full numbers, per-corner breakdown and every caveat:
`records/RECORD-002-cp-mismatch-mc-yield.md`.

| | |
|---|---|
| Samples | 1500 (15 corners x N = 100), 0 errored, 0 lost shards |
| `mismatch_pct` mean / sigma | -0.3201 % / 3.8769 % |
| Yield vs the `+/-3.5 %` screening limit | **63.47 %**, 95 % CI [60.97 %, 65.91 %] (Clopper-Pearson, pooled) |
| Cpk / sigma-to-spec | 0.2734 / 0.820 |
| Worst corners | `mos_fs_mismatch` / -40 C and `mos_sf_mismatch` / -40 C, 47/100 each |
| Best corner | `mos_tt_mismatch` / 125 C, 74/100 |
| `klt yield` sample-size verdict | **`insufficient`** — N = 1500 gives +/-2.47 pp; 8907 needed for the default +/-1 pp |
| `klt signoff` T1 item 6 | analog **`unmet` / `undersized_sample`** (was `no_evidence`); digital unchanged `unmet` / `no_evidence` |

Since issue #385 the `+/-3.5 %` row of that table is a **historical**
grading value, not a live bound — see "Limit (still needs a ruling)" below.
Item 6 still grades `unmet` / `undersized_sample` against the committed
`reports/yield.mc.json`; the manifest is not re-pointed at the re-grade.

The dominant axis is **temperature, not process corner**: sigma is lower at
125 C than at -40 C in all five process sections (-40 C: 3.963-4.765 %;
125 C: 3.078-3.448 %), falling monotonically with temperature in four of
them -- `mos_tt_mismatch` is flat between -40 C and 27 C (3.963 % ->
3.973 %) before dropping to 3.121 % at 125 C -- while the means stay within
+/-1.02 % everywhere. The shortfall against the screening limit is
distribution width, not offset.

The campaign was run at the N the issue specifies, and the `insufficient`
verdict is reported rather than engineered away: `klt yield`'s default
+/-1 pp target is not a repo requirement, and the limit being graded against
is itself unratified, so its uncertainty dominates +/-2.47 pp of sampling
noise. A ratified limit should land before a bigger campaign.

## Limit (still needs a ruling) — and `+/-3.5 %` is now RETIRED

`spec/target-spec.md` row 7 (lock time) proposes **no number**, and no row
carries a `cp` mismatch limit. The only quantitative statement in the repo
is the closed-loop dual-lock criterion, `|static phase error| < 5 %` of
`T_ref` (`../sg13cmos5l-closed-loop-lock/records/RECORD-003` to `-005`).
`mc.request.json` therefore grades `mismatch_pct` against **+/-3.5 %**,
derived only from existing records: 5 % / (9.176 % phase error per 6.42 %
mismatch at VOUT = 2.40 V, `RECORD-003` and the sibling `RECORD-002`) = 3.50 %.
That is an empirical, single-point, linear-through-origin screening limit
(`RECORD-004` states the analytic gain is not derived), and its derivation
used closed-loop records made on the **pre-DR-010** `cp`. It is not a
ratified spec number and the spec was not edited to add one. No
`target_yield` is declared, so the `klt yield` envelope reports an estimate
rather than a pass/fail against a number nobody ratified.

**That derivation has since been measured and does not hold.** Issue #385
re-measured the mismatch-to-static-phase-error gain on the committed DR-010
`cp` (`../sg13cmos5l-closed-loop-lock/records/RECORD-014-cp-mismatch-phase-error-gain.md`,
six injected mismatch points spanning -11.998 to +12.009 % at -40 / 27 /
125 C): the slope is **-0.0394 to -0.0484 pp/pp**, about **30x smaller**
than the 1.4293 pp/pp the `+/-3.5 %` value was divided out of and of the
**opposite sign**, with a +0.754 to +0.842 pp intercept, and a
linear-through-origin model is rejected (forcing the intercept to zero
multiplies the fit residual by 22x to 90x). Across the whole measured span
the worst static phase error is 1.3265 % against the 5 % criterion.
`spec/decision-records/DR-013-cp-mismatch-limit.md` (proposed) therefore
**retires `+/-3.5 %` as a row-7-derived bound** and proposes no replacement
and no `target_yield`; `spec/target-spec.md` R-12 carries the ruling.

`testbench/mc.request.json` is **not edited** — the committed request is
what produced the committed samples, and editing it would invalidate
`reports/sim.mc.json`'s provenance. Its `min -3.5 / max 3.5` is history, not
a live bound.

`corners/mc-samples.csv` carries every sample, so the yield can be
recomputed against any later ratified limit without re-simulating — see
`records/RECORD-002`, "Recomputing this against a different limit".
`records/RECORD-003-regrade-proposed-limit.md` is the first such re-grade:
`klt yield --limits testbench/yield.proposed-limit.limits.json` on the
committed `reports/sim.mc.json`, against DR-013's **evidence-coverage**
bound of `+/-11.92 %` (how far RECORD-014's evidence reaches, *not* a spec
limit), writing `reports/yield.mc.proposed-limit.json` beside — never over —
`reports/yield.mc.json`:

| | `RECORD-002` (+/-3.5 %) | `RECORD-003` (+/-11.92 %) |
|---|---|---|
| empirical yield | 63.47 %, CI [60.97 %, 65.91 %] | **99.60 %, CI [99.13 %, 99.85 %]** |
| Cpk / sigma-to-spec | 0.2734 / 0.820 | 0.9973 / 2.992 |
| `sample_size.required_n` | 8907 | **154** |
| `sample_size.verdict` | `insufficient` | **`sufficient`** |

So no resize is indicated on sample-size grounds at that bound; a later
ratified limit near the distribution's body would reopen the question, and
`mc-samples.csv` makes answering it a re-grade rather than a re-run. The
`negative_control` warning both envelopes carry is **not** cleared by the
re-grade — see `records/RECORD-003`, "The `negative_control` warning".

## Cold start

The pinned tree is an `ihp-sg13cmos5l` git checkout at `../README.md`'s
`PDK-PIN ihp-sg13cmos5l 607e18d4…`. On the fleet workers it is the
`~/share/pdk/ihp-sg13cmos5l.bak-<timestamp>` directory the 2026-10-15 PDK
sync renamed aside (`git rev-parse HEAD` must print the pin); elsewhere,
clone that commit. `$PDK_ROOT` is deliberately **not** used — see "Mismatch
is PDK-revision sensitive" above.

    export PINNED_PDK=<ihp-sg13cmos5l checkout at 607e18d4...>
    cd sim/sg13cmos5l-cp-icp-trim-mc
    python3 -I testbench/gen_requests.py --pinned-pdk "$PINNED_PDK"   # rewrites the three *.request.json

    # controls, one corner each -- local is allowed for a single unit
    klt sim testbench/negative_control.request.json --backend local --format json \
        > reports/sim.negative_control.dr010-pinned.json     # exit 0, stddev 0
    klt sim testbench/positive_probe.request.json   --backend local --format json \
        > reports/sim.positive_probe.dr010-pinned.json       # exit 3 (limits), stddev > 0

    # the campaign: batch fleet only, never a local grid (host rules)
    klt sim testbench/mc.request.json --backend batch --wait-for-capacity 600 \
        --format json --report-out reports/sim.mc.json -o reports/mc-batch-receipts
    python3 -I testbench/collect_mc.py reports/sim.mc.json --outdir corners

    # the yield envelope, from the reports/ directory so `samples` stays
    # relative (klt signoff hashes the file that field names)
    cd reports && uvx --from "klayout-tools[yield]" klt yield sim.mc.json \
        --measurement mismatch_pct --format json > yield.mc.json

`klt yield` needs the `klt_yield_native` extension, which the host tool does
not carry; the `uvx` form above resolves a build that does. Nothing is
installed host-wide.

Item 6 is wired by the `6.analog` entry in `manifests/sg13g2-pll.json`,
whose `content_hash` is the sha256 of `reports/sim.mc.json` (the document
`yield.mc.json`'s `samples` field names), with
`manifests/sg13g2-pll.tier-report.json` regenerated by the pinned
`klt signoff` in `.github/workflows/signoff.yml` — never by hand. The
digital partition (`divider_chain`) has no statistical row and
`manifests/README.md` says so; it gets no citation here.

## History

`records/RECORD-001` (PR #191) established the bench, the controls and the
mismatch model on the pre-DR-010 `cp`, and recorded three blockers: the
batch backend refusing `models.pdk: ihp-sg13cmos5l`
(2AMLogic/klayout-tools#2727), a fleet runner too old for `osdi_preload`
(#2851, #2901), and `klt yield` unusable on the worker. All three are
closed or worked around: the campaign ran on the fleet with
`options.stage_model_inputs` shipping the pinned model bytes (so
`models.pdk` is not needed at all), the runner is now klt 0.9.0, and
`klt yield` runs in a throwaway `uvx` environment. `records/RECORD-002`
carries the campaign; `RECORD-001` is unedited.
