# sg13cmos5l-cp-icp-trim-mc — Monte Carlo bench for the `cp` up/dn mirror mismatch

Issue #178 (T1 item 6, "Statistical claims carry Monte Carlo evidence").
Sibling of `../sg13cmos5l-cp-icp-trim/` (same DUT, same frozen netlist, same
bias; that bench measures corners, this one measures spread).

**Status: bench and controls committed; the campaign itself has NOT run.**
Two tool gaps block it on this fleet; see "Blockers". No yield estimate is
claimed anywhere in this directory, and `manifests/` is untouched.

## What is measured

One `cp` instance (`netlist-snapshots/cp.spice`, byte-identical to
`../sg13cmos5l-cp-icp-trim/netlist-snapshots/cp.spice`), Iref = 10 uA trim
code, VDD = 3.3 V, VOUT = 2.40 V (the closed loop's own operating point,
`../sg13cmos5l-cp-icp-trim/records/RECORD-002`). One DC sweep of `Vup`
over {0, 3.3 V} with DN = 3.3 V - UP gives the DN-leg current (point 0) and
the UP-leg current (point 1) from the **same** random draw:

    mismatch_pct = (Iup + Idn) / ((Iup - Idn) / 2) * 100        (Idn < 0)

Supply is fixed at 3.3 V in the netlist (no `corners.supply_v` axis); the
corner axes are 5 MOS mismatch sections x {-40, 27, 125} C. `cp` has no
resistor, so no resistor corner applies (same statement as the sibling bench).

## Mismatch model (confirmed, first step of the issue)

`sg13_hv_nmos`/`sg13_hv_pmos` do carry per-instance mismatch under ngspice.
`cornerMOShv.lib` has `mos_{tt,ss,ff,sf,fs}_mismatch` sections that include
`sg13g2_moshv_mismatch.lib` (one-sigma Pelgrom-style parameters, e.g. nmos
`delvto_mm` = 0.007, pmos 0.0045, `factuo_mm` 0.005 / 0.004, `dw_mm`/`dl_mm`
3e-9) and `sg13g2_moshv_mod_mismatch.lib`, whose instance parameters are
`agauss(...)` draws gated by `mm_ok`. `klt sim` seeds them through
`.options seed=`. This contradicts the sibling `RECORD-002` statement "no
per-instance mismatch model is available for `sg13_hv_nmos`/`sg13_hv_pmos`";
that record is append-only and is not edited (see `records/RECORD-001`).
No sigma value in this directory is invented; all are the PDK's.

## Seed, N, controls

| Item | Value |
|---|---|
| Seed | 178 (`monte_carlo.seed`; per-sample seeds are SHA-256 derived, echoed per corner in the report) |
| N | 100 per corner x 15 corners = 1500 samples (`mc.request.json`) |
| `vary` | `mismatch` |
| Negative control | `negative_control.request.json`: section `mos_tt` (no mismatch library), 20 samples. Every stddev is exactly 0. Committed: `reports/sim.negative_control.json` |
| Positive probe | `positive_probe.request.json`: `mos_tt_mismatch`, 3 samples, mismatch 2.855 / 6.269 / 7.983 %. Committed: `reports/sim.positive_probe.json` |

The negative control's single value, -0.2985 %, equals the sibling bench's
nominal at VOUT = 2.40 V (`RECORD-002`: -0.298 %), so this deck reproduces
the corner-bench number before any mismatch is added.

## Limit (needs a ruling)

`spec/target-spec.md` row 7 (lock time) proposes **no number**, and no row
carries a `cp` mismatch limit. The only quantitative statement in the repo
is the closed-loop dual-lock criterion, `|static phase error| < 5 %` of
`T_ref` (`../sg13cmos5l-closed-loop-lock/records/RECORD-003` to `-005`).
`mc.request.json` therefore grades `mismatch_pct` against **+/-3.5 %**,
derived only from existing records: 5 % / (9.176 % phase error per 6.42 %
mismatch at VOUT = 2.40 V, `RECORD-003` and the sibling `RECORD-002`) = 3.50 %.
That is an empirical, single-point, linear-through-origin screening limit
(`RECORD-004` states the analytic gain is not derived). It is not a ratified
spec number and the spec was not edited. A ruling is needed on the real limit.

## Cold start

    export PDK_ROOT=<parent of ihp-sg13cmos5l>     # default in the generator: ~/share/pdk
    cd sim/sg13cmos5l-cp-icp-trim-mc
    python3 testbench/gen_requests.py              # rewrites the three *.request.json
    klt sim testbench/negative_control.request.json --backend local --format json   # exit 0, stddev 0
    klt sim testbench/positive_probe.request.json   --backend local --format json   # exit 3 (limits), stddev > 0
    klt sim testbench/mc.request.json --format json > reports/sim.mc.json          # batch fleet; do NOT run locally
    klt yield reports/sim.mc.json --measurement mismatch_pct --format json > reports/yield.mc.json

Then write `records/RECORD-002` with the yield estimate and its confidence
interval from `reports/yield.mc.json`, and wire item 6 by adding a
`6.analog` entry to `manifests/sg13g2-pll.json` pointing at
`reports/yield.mc.json` and regenerating `manifests/sg13g2-pll.tier-report.json`
with the pinned `klt signoff` command in `.github/workflows/signoff.yml`
(never by hand). The digital partition (`divider_chain`) has no statistical
row and must say so explicitly when item 6 is wired.

## Blockers (as of this commit)

1. **Batch fleet cannot run this request.** Submitted with
   `stage_model_inputs`, no `models.pdk` (the batch backend refuses
   `ihp-sg13cmos5l`: 2AMLogic/klayout-tools#2727), and
   `batch.runner_version_check: warn`: the fleet runner ran klt 0.5.0 against
   client 0.7.0, silently ignored `options.osdi_preload`, and ngspice stopped
   with `Unable to find definition of model ...sg13g2_hv_pmos_psp` (log
   retrieved with `keep_artifacts`). With the default `enforce` the job exits
   87 `batch_runner_version_mismatch`. Upstream: klayout-tools#2851, #2901.
   Per host rules the grid was not run locally.
2. **`klt yield` is unusable on this worker**: `klt_yield_native` is not
   installed (also not via `uvx --from "klayout-tools[yield]"`), and host
   tools may not be changed. The yield report therefore does not exist yet.
