# RECORD-004: the seeded known-bad negative control — a `mm_p12`-perturbed `cp` campaign reads `detected` at both committed limit sets (+/-3.5 % and +/-11.92 %), and the nominal envelopes are unchanged by the merge

- **Slug**: `sg13cmos5l-cp-icp-trim-mc`
- **Issue**: #389 (part 2). The gap this closes: `RECORD-003`'s carried
  disposition — `klt yield`'s `negative_control` warning was open on this
  bench's campaign ("no measurement declared a negative_control"), and the
  bench's own `reports/sim.negative_control.dr010-pinned.json` is the
  *opposite* kind of control (a zero-spread liveness proof, not a seeded
  known-bad variant), so pointing the grader at it would be wrong rather
  than merely unhelpful.
- **Append-only, and the committed campaign is not re-simulated.** This
  record adds new files beside the committed ones and edits no earlier
  record, snapshot, report, CSV or request: `../netlist-snapshots/cp-mm_p12.spice`
  (new), `../testbench/tb_cp_mc_mm_p12.sp` (new),
  `../testbench/mc.mm_p12.request.json` (new), `reports/sim.mc.mm_p12.json`
  (new), `reports/yield-samples.mc.json` (new),
  `reports/yield.mc.with-control.json` (new),
  `reports/yield.mc.proposed-limit.with-control.json` (new). The two new
  yield envelopes sit beside `reports/yield.mc.json` and
  `reports/yield.mc.proposed-limit.json`, never over them.
- **Tooling**: the control campaign ran `ngspice-47` on the Spot batch
  fleet (job `klt-sim-8ecae6282d9f`, submitted by `klt sim`, client
  `klt 0.9.2.dev1029+g76f47afa48f1`); the merge and both re-grades ran
  `klt yield-samples` / `klt yield` `0.9.2` in the throwaway
  `uvx --from "klayout-tools[yield]"` environment (the host tool carries no
  `klt_yield_native`; nothing installed host-wide). No simulator ran for
  the merge or the grades. PDK `ihp-sg13cmos5l` revision `607e18d4bd9214a52575c194b4181ef449f9252f`
  (the `sim/README.md` pin), shipped as bytes by `options.stage_model_inputs` — the
  staged hashes in `reports/sim.mc.mm_p12.json` equal what the committed
  `reports/sim.mc.json` records (`psp103.osdi` `2e4299c4...`,
  `psp103_nqs.osdi` `839b1644...`, `mosvar.osdi` `25e64a37...`,
  `sg13g2_moshv_mod_mismatch.lib` `52d45aec...`), so the control drew on
  the same mismatch model bytes as the campaign it controls.
- **A discarded first submission preceded this record.** The control was
  first submitted against `/home/ubuntu/share/pdk/ihp-sg13cmos5l` — a tree
  whose `cornerMOShv.lib` carries the pin's own `sha256` but whose
  `sg13g2_moshv_mod*.lib`/OSDI bytes are the newer install's, where the HV
  MOS mismatch subcircuits default to `mm_ok=0`. It returned sigma exactly
  0.0000 % on all 100 draws (job `klt-sim-70583a612331`) — the
  invisible-null trap `../testbench/gen_requests.py`'s `mm_ok` guard exists
  for, reached here because the guard is a check inside that generator and
  the hand-written control request bypassed it. Every unit of that run was
  discarded uncommitted; the committed control comes from the request
  re-pointed at the pinned tree (verified by running
  `gen_requests.py`'s closure check against it before submission).

## What the control is

`RECORD-014` (sibling bench `../../sg13cmos5l-closed-loop-lock`) measured
the DC gain of an *injected* up/dn mismatch by scaling the two cascode
mirror devices of `.subckt cp_leg_p` by one factor `k`. Its `mm_p12` point
(`k` = 1.131043) lands at **+11.9686 %** DC mismatch at 27 C — about 3.1
sigma of this campaign's measured 3.8769 % sigma, far outside any sampling
noise. That is exactly the material a negative control needs, and it is
mounted here on this bench's own committed snapshot:

- `../netlist-snapshots/cp-mm_p12.spice` was rendered by
  `gen_mismatch_gain_requests.py`'s own `perturb_cp` at `k` =
  `scale_for(12.0)` = 1.131043, applied to this bench's committed
  `../netlist-snapshots/cp.spice` (`sha256` `063450257a9b3ab2...`). Only
  the two `cp_leg_p` mirror widths move (`24u` -> `27.145036u`); every
  other device line is byte-identical to `cp.spice`.
- `../testbench/tb_cp_mc_mm_p12.sp` is `tb_cp_mc.sp` byte for byte apart
  from that `.include` and its header — same VOUT = 2.40 V operating point,
  same 10 uA trim code, same two-point `Vup` sweep through one `XCP`
  instance, same `mismatch_pct` expression and `+/-3.5 %` limits.
- `../testbench/mc.mm_p12.request.json` is `mc.request.json` narrowed to
  `mos_tt_mismatch` / 27 C, N = 100 (one per-corner slice of the committed
  campaign), **seed 178** — the campaign's own seed. Per-sample seeds are
  derived from the corner's index within the request (plus the sample index
  and that seed), not from the corner's process/temperature identity, and
  the control request has a single corner — so its draws inherit the
  index-0 seed stream, which in the committed campaign (5 process sections
  x 3 temperatures, process-major) is the `mos_tt_mismatch`/−40 C slice,
  not its 27 C slice. Measured on the two committed reports: control draw
  *i* is seed-identical to the campaign's `mos_tt_mismatch`/−40 C draw *i*
  for **100/100** draws, and to its 27 C slice for **0/100**. There is
  therefore no same-temperature draw-level pairing between control and
  campaign — and none is needed: `klt yield` grades the control unpaired
  (its empirical yield against the nominal population), so the verdict
  below does not rest on any pairing.

## Result

The control campaign (`reports/sim.mc.mm_p12.json`): 100 draws, 0 errored,
0 inconclusive — **mean +12.2735 %, sigma 3.4797 %**, range +1.6089 % to
+18.3034 % (a mismatch-enabled campaign against a snapshot seeded 3.1 sigma
UP: the draws centre where the seeding aims, and their spread matches the
committed campaign's per-corner sigma at this corner, 3.973 %, to ~12 %).

One cross-temperature comparison the seed coincidence *does* buy (see the
request bullet above): paired draw for draw against the campaign's
`mos_tt_mismatch`/−40 C slice — the slice whose seed stream the control
inherited — the perturbation delta is **+12.2483 % ± 0.4931 %** (mean ± sd,
n = 100). With 100/100 seed-identical draws, sampling noise largely cancels,
and the tight sd confirms `perturb_cp(scale_for(12.0))` injects the ~+12 %
it claims. Read only the size of that effect, not its precise value: control
at 27 C vs campaign draws at −40 C confounds temperature with the
perturbation. The unpaired 27 C comparison shows the difference — mean
+12.4712 % with sd 5.4931 %, i.e. statistically two independent samples
(sd ≈ sqrt(3.973² + 3.480²) = 5.28 %), no pairing benefit at all.

The merge (`klt yield-samples reports/sim.mc.json --negative-control
reports/sim.mc.mm_p12.json` -> `reports/yield-samples.mc.json`; the
document records both sources' `sha256` under `derivation`) and the two
re-grades:

| | `+/-3.5 %` (`yield.mc.with-control.json`) | `+/-11.92 %` (`yield.mc.proposed-limit.with-control.json`) |
|---|---|---|
| nominal empirical yield | 63.47 %, CI [60.97 %, 65.91 %] | 99.60 %, CI [99.13 %, 99.85 %] |
| nominal `sample_size.verdict` | `insufficient` (required_n 8907) | `sufficient` (required_n 154) |
| **control empirical yield** | **1 %**, CI [0.03 %, 5.45 %] | **46 %**, CI [35.98 %, 56.26 %] |
| control vs nominal CI overlap | none | none |
| **`negative_control.verdict`** | **`detected`** | **`detected`** |

**The campaign's statistics detect the seeded defect at both committed
limit sets**, and neither new envelope carries the "no measurement declared
a negative_control" warning any more (each carries only the same
no-`target_yield` advisory the committed envelopes carry).

**Sanity: the merge changed nothing but the control.** A field-by-field
comparison of each new envelope's nominal `mismatch_pct` measurement
against the committed envelope it extends (`yield.mc.json` /
`yield.mc.proposed-limit.json`), excluding only the new `negative_control`
key, shows **no differing field**: the nominal samples are the committed
1500 draws verbatim, mean -0.3201 % / sigma 3.8769 %, both yields
identical, and the `sample_size` verdicts are unchanged. At `+/-3.5 %` the
control reads 1/100 inside (its one low-tail draw, +1.61 %); at
`+/-11.92 %` the control's centre sits almost exactly on the upper limit,
so about half its draws fall inside — 46 % — which is still a CI-detached
46 pp yield collapse against the nominal 99.60 %.

## What this control does not show

- **One process section**: `mos_tt_mismatch` only. The committed campaign's
  other four sections are uncontrolled by this run.
- **One temperature**: 27 C only. `RECORD-002` reports the spread peaks at
  -40 C, so a control there would be graded against a wider nominal — not
  run here.
- **One injected defect on one mirror leg**: the perturbation scales
  `cp_leg_p`'s two mirror devices only (RECORD-014's substitution style).
  It says nothing about detection of switching-charge mismatch, bias
  replica mismatch, or the dump buffer's input offset.
- **The committed envelope grades**: `reports/yield.mc.json` and
  `reports/yield.mc.proposed-limit.json` are untouched, and the
  `6.analog` manifest citation is not re-pointed at the new envelopes. The
  control demonstrates the statistics *can* detect a degraded design; it
  does not change any yield number.

## Corners: what ran, what did not

- **Ran**: `mos_tt_mismatch` / 27 C, N = 100, seed 178, 3.3 V in the
  netlist, no resistor corner (`cp` has none) — one of the committed
  campaign's fifteen corners, as the issue fixed.
- **Not run**: every other process section and temperature; the
  mismatch-disabled sections (`mos_tt` etc.); any repeat or enlarged N.

## Reproduce

```bash
# the degraded snapshot (no simulator): RECORD-014's perturbation on this
# bench's committed cp.spice
cd sim/sg13cmos5l-closed-loop-lock/testbench
python3 -I -c '
import pathlib, sys; sys.path.insert(0, ".")
import gen_mismatch_gain_requests as g
src = pathlib.Path("../../sg13cmos5l-cp-icp-trim-mc/netlist-snapshots/cp.spice")
out = g.perturb_cp(src.read_text(), g.scale_for(12.0))
pathlib.Path("../../sg13cmos5l-cp-icp-trim-mc/netlist-snapshots/cp-mm_p12.spice").write_text(out)'
cd ../../sg13cmos5l-cp-icp-trim-mc

# the control campaign (batch fleet, never local)
klt sim testbench/mc.mm_p12.request.json --backend batch --wait-for-capacity 600 \
    --report-out reports/sim.mc.mm_p12.json --format json

# merge + grades (throwaway env; no simulator; regenerates from committed reports)
cd reports
uvx --from "klayout-tools[yield]" klt yield-samples sim.mc.json \
    --negative-control sim.mc.mm_p12.json --description "seeded known-bad cp: ..." \
    --format json > yield-samples.mc.json
uvx --from "klayout-tools[yield]" klt yield yield-samples.mc.json \
    --measurement mismatch_pct --format json > yield.mc.with-control.json
uvx --from "klayout-tools[yield]" klt yield yield-samples.mc.json \
    --measurement mismatch_pct --limits ../testbench/yield.proposed-limit.limits.json \
    --format json > yield.mc.proposed-limit.with-control.json
```

`gen_mismatch_gain_requests.py` refuses to run without `--pinned-pdk` and
`klt sim` without a request whose `models.lib` names the pinned tree; see
the discarded-submission note above for why the tree check is load-bearing
here.
