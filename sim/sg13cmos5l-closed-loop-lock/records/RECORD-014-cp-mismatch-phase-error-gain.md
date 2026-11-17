# RECORD-014: the DC up/dn mismatch-to-static-phase-error gain on the DR-010 `cp` is -0.039 to -0.048 %/% , about 30x smaller than the +1.43 %/% the `+/-3.5 %` screening limit assumes, and not through the origin

- **Slug**: `sg13cmos5l-closed-loop-lock`
- **Issue**: #385 (follow-up to #178). The limit this measurement feeds:
  `spec/decision-records/DR-013-cp-mismatch-limit.md`. The campaign whose
  screening limit it re-derives:
  `../../sg13cmos5l-cp-icp-trim-mc/records/RECORD-002-cp-mismatch-mc-yield.md`
  and its re-grade `../../sg13cmos5l-cp-icp-trim-mc/records/RECORD-003-regrade-proposed-limit.md`.
- **Append-only.** This record edits no earlier record, snapshot, CSV or
  script. New files: `../testbench/gen_mismatch_gain_requests.py`,
  `../testbench/mismatch_gain_metrics.py`, `../testbench/mismatch_gain_post.py`,
  `../testbench/test_mismatch_gain_metrics.py`, and
  `../corners/{mismatch_gain.csv, mismatch_gain_fit.json,
  mismatch_gain_points.json, sim_mismatch_gain_dc.json,
  sim_mismatch_gain_loop.json}`. `cpdiag_metrics.py`, `cpdiag_build.py`,
  `cpdiag_post.py`, `tb_pll_cpdiag.sp.tmpl` and
  `run_closed_loop_otabuf.sh` are used **unmodified** (their sha256 are
  cited by the committed `cpdiag_summary_*.json` files and must not move).
- **What this is, and what it is not.** This is RECORD-007's deck -- which is
  RECORD-005/006's **proposal deck** -- re-run at seven injected DC
  mismatch points. Everything that makes it a proposal deck is unchanged
  and the numbers are **not committed-PLL performance and not sign-off
  evidence**:
  - a behavioural XSPICE divide-by-64 instead of the committed
    `divider_chain`;
  - `R1` resized 120u to 2400u;
  - ideal capacitors for every MOM cap;
  - `XCDECAP` stripped;
  - ideal `IREF` sources into `cp`'s bias pins.

  The `cp` itself is the committed DR-010 design, perturbed only as
  described below.
- **Tooling**: `ngspice-47` on the fleet workers (`/usr/local/bin/ngspice`,
  `environment.engine_version: "47"` in every corner report) and
  `ngspice-47` locally for the two single-point checks below;
  `klt 0.9.2.dev964+g02db14ecf46b` (client; it submitted, sharded and
  collected every unit).
  PDK `ihp-sg13cmos5l` revision `607e18d4bd9214a52575c194b4181ef449f9252f`
  -- the `sim/README.md` pin -- shipped to the workers as bytes by `options.stage_model_inputs` rather
  than resolved on the fleet image (17 staged files per unit;
  `cornerMOShv.lib` `source_sha256` `5a1f862dc304fdfe...`, equal to the
  hash RECORD-013 cites for the pinned tree; `cornerRES.lib`
  `2c18502104146804...`; OSDI `psp103` `2e4299c46839...`, `psp103_nqs`
  `839b16448320...`, `mosvar` `25e64a374ab5...`, `r3_cmc` `4fead17bc2e9...`,
  the same prefixes RECORD-013 cites). Python 3.12.3 (stdlib only),
  `set num_threads=1` per unit. Fleet instances `c7i.8xlarge`, `us-east-1`.

## What was injected, and how the x-axis is measured

`design/sg13cmos5l/cp.sch` is **not** edited. This is a diagnostic
substitution in the style of RECORD-004: the committed snapshot
`../netlist-snapshots/cp_otabuf.spice` (sha256 `c8a55d8d2234c468...`) is
copied and the **two cascode mirror devices of the UP leg only**
(`.subckt cp_leg_p`: `XM1` tail and `XM2` cascode, `sg13_hv_pmos w=24u
l=1u`) have their width scaled by one factor `k`. The DN leg, the bias
replica, both steering-switch pairs, the inverters and the DR-010 dump
buffer are byte-identical to the committed snapshot at every point.
`k = 1` returns the snapshot **byte for byte** -- the `mm_nom` deck's
sha256 is `c8a55d8d2234c468...`, equal to `cp_otabuf.spice` -- so the
unperturbed baseline is the committed `cp`, not a re-rendered copy of it.

**The x-axis is measured, not assumed.** Each perturbed snapshot's own DC
up/dn mismatch is measured by a separate `klt sim` DC request using the
Monte Carlo bench's own deck and definition
(`../../sg13cmos5l-cp-icp-trim-mc/README.md`: one `Vup` sweep over
{0, 3.3 V} through one `XCP`, `VOUT` = 2.40 V, `Iref` = 10 uA,
`mismatch_pct = (Iup + Idn) / ((Iup - Idn) / 2) * 100`), at the same three
temperatures as the closed-loop runs.

Scaling one mirror leg gives clean, monotonic steps that land within
0.08 pp of their target at every temperature, and the DN-leg current does
not move with `k` at all:

| point | `k` | `mismatch_pct` -40 C | 27 C | 125 C | `Idn` (all `k`, 27 C) |
|---|---|---|---|---|---|
| `mm_n12` | 0.889453 | -11.9984 % | -11.9616 % | -11.9268 % | -10.0300 uA |
| `mm_n8`  | 0.925841 | -8.0141 %  | -7.9757 %  | -7.9395 %  | " |
| `mm_nom` | **1.0 (committed)** | -0.3396 % | **-0.2985 %** | -0.2603 % | " |
| `mm_p4`  | 1.043929 | +3.9457 %  | +3.9881 %  | +4.0272 %  | " |
| `mm_p8`  | 1.086577 | +7.9345 %  | +7.9779 %  | +8.0177 %  | " |
| `mm_p12` | 1.131043 | +11.9244 % | +11.9686 % | +12.0089 % | " |
| `mm_n4`  | 0.963658 | -4.0287 %  | -3.9888 %  | -3.9514 %  | " |

The `mm_nom` value at 27 C, **-0.298465 %**, equals the Monte Carlo bench's
own negative-control value (`../../sg13cmos5l-cp-icp-trim-mc/README.md`:
-0.298465 %) and the sibling corner bench's nominal
(`../../sg13cmos5l-cp-icp-trim/records/RECORD-002`: -0.298 %) to every
printed digit, so the DC deck here reproduces the committed figure before
anything is perturbed.

The span reached is **-11.998 % to +12.009 %**, i.e. +/-3.1 sigma of the
campaign's measured 3.8769 % mismatch sigma (`RECORD-002`); 3 sigma is
11.63 %.

## Corners: what ran, what did not, and what did not lock

**`mos_tt` / `res_typ` / 3.3 V at -40, 27 and 125 C**, declared as its own
subset in `../corners/matrix.md`, "The RECORD-014 mismatch-gain grid". The
mismatch-point x
temperature grid is a grid, so it went to the Spot batch fleet as `klt sim`
requests with `--wait-for-capacity 600` (host rules forbid a local grid);
one request per mismatch point, three temperature units each, submitted as
two `--batch-set` sets (DC and closed-loop). Job ids are in
`../corners/sim_mismatch_gain_{dc,loop}.json` next to every corner they
produced.

- **Supply corner**: not swept. Every unit runs at 3.3 V, as every record
  in this slug does; row 18's +/-10 % axis is exercised on `cp` only by
  `../../sg13cmos5l-cp-icp-trim`, and adding it here would have tripled a
  grid whose purpose is the mismatch axis.
- **Process corner**: `mos_tt` only. The question is a gain, not a
  worst-case bound, and the mismatch being injected is deliberate rather
  than drawn, so a process-section sweep measures the deck's own corner
  spread rather than this record's quantity. `RECORD-002` already reports
  that the campaign's **temperature** axis, not its process axis, dominates
  the mismatch spread, which is why temperature is the axis swept here.
- **`mm_n4` closed loop: NOT COLLECTED (`batch_poll_timeout`).** Its batch
  job `klt-sim-5b7326c77dc6` never reached a terminal state: the client gave
  up after **5220 s** with
  `job klt-sim-5b7326c77dc6 did not reach a terminal state within 5220s
  (last observed state: running)` on all three of its temperature units, and
  the set exited 4. That is past the fleet's own 3600 s whole-job ceiling and
  5x to 8x the 625 to 1000 s every other member of the same set took, with no
  measurement returned -- the member's report carries three `error` corners
  and no `crossings` series. Its report is committed in
  `../corners/sim_mismatch_gain_loop.json` alongside the six that passed, so
  the gap is evidence rather than an absence.

  **It is recorded as not collected, NOT as an unlocked point**, and
  `mismatch_gain_post.py` enforces that distinction: a corner with no
  crossing series is listed in `mismatch_gain_fit.json`'s `not_collected`
  with its diagnostic code and gets no CSV row at all, so it can never be
  confused with the 125 C points below, which did return and did not lock.
  Its DC point (job `klt-sim-3cfb4e50692b`) returned normally and is in the
  table above.

  Six points -- five perturbed, both signs, reaching +/-11.92 %, plus the
  unperturbed baseline -- remain at each temperature, which is what the fits
  below use. `mm_n4` was a seventh, interior point (about -4 %) between two
  that did return, so its loss narrows no span and leaves both signs and the
  +/-3 sigma reach intact; it was not re-submitted.
- **125 C: the loop does not acquire at ANY mismatch point, including the
  unperturbed one.** `vctrl` sits at 3.2891 to 3.2907 V -- hard against the
  3.3 V rail -- `df/f_ref` is -0.60 % at every point, the longest dual-lock
  run is 0 cycles, and the final-20 phase "error" is -33 % to -40 %. The
  spread across the mismatch axis at 125 C (-33.5 % to -39.7 %) is a
  property of a railed loop, not a static phase error. **Every 125 C point
  is reported here and excluded from every fit**: a phase error read off a
  loop that is not locked is not a static phase error. This is a deck
  limitation at 125 C (the behavioural-divider proposal deck's `VC0` =
  2.46 V start and its `R1` x20 filter), not a mismatch result, and it is
  not caused by the perturbation. It is reported as a new gap below.

## Result

Final 20 of 49 reference cycles, same window and same definition as
RECORD-005 to RECORD-007. Full table: `../corners/mismatch_gain.csv`;
fits: `../corners/mismatch_gain_fit.json`.

### -40 C (locked at every point)

| point | `mismatch_pct` | static phase error, final-20 mean [min, max] | longest dual-lock run | `vc_avg` | `i_cp` |
|---|---|---|---|---|---|
| `mm_n12` | -11.9984 % | **+1.3219 %** [+1.154, +1.381] | 36 | 2.22491 V | -65.011 uA |
| `mm_n8`  | -8.0141 %  | +1.1618 % [+0.983, +1.221] | 36 | 2.22500 V | -65.206 uA |
| `mm_nom` | -0.3396 %  | +0.8391 % [+0.656, +0.899] | 36 | 2.22492 V | -65.597 uA |
| `mm_p4`  | +3.9457 %  | +0.6773 % [+0.519, +0.723] | 36 | 2.22494 V | -65.829 uA |
| `mm_p8`  | +7.9345 %  | +0.5348 % [+0.399, +0.574] | 36 | 2.22494 V | -66.051 uA |
| `mm_p12` | +11.9244 % | **+0.3810 %** [+0.130, +0.475] | 36 | 2.22511 V | -66.287 uA |

### 27 C (locked at every point)

| point | `mismatch_pct` | static phase error, final-20 mean [min, max] | longest dual-lock run | `vc_avg` | `i_cp` |
|---|---|---|---|---|---|
| `mm_n12` | -11.9616 % | **+1.3265 %** [+1.268, +1.447] | 45 | 2.38678 V | -64.374 uA |
| `mm_n8`  | -7.9757 %  | +1.1302 % [+1.077, +1.211] | 45 | 2.38679 V | -64.544 uA |
| `mm_nom` | -0.2985 %  | +0.7662 % [+0.715, +0.822] | 42 | 2.38685 V | -64.888 uA |
| `mm_p4`  | +3.9881 %  | +0.5809 % [+0.526, +0.625] | 42 | 2.38692 V | -65.090 uA |
| `mm_p8`  | +7.9779 %  | +0.4252 % [+0.355, +0.489] | 42 | 2.38700 V | -65.289 uA |
| `mm_p12` | +11.9686 % | **+0.1160 %** [+0.048, +0.189] | 41 | 2.38674 V | -65.562 uA |

### 125 C (not locked at any point -- not fitted)

| point | `mismatch_pct` | final-20 mean "phase" | `df/f_ref` | longest dual-lock run | `vc_avg` |
|---|---|---|---|---|---|
| `mm_n12` | -11.9268 % | -33.5256 % | -0.6026 % | 0 | 3.28912 V |
| `mm_n8`  | -7.9395 %  | -34.6461 % | -0.6006 % | 0 | 3.28938 V |
| `mm_nom` | -0.2603 %  | -36.6659 % | -0.5985 % | 0 | 3.28989 V |
| `mm_p4`  | +4.0272 %  | -37.7430 % | -0.5979 % | 0 | 3.29016 V |
| `mm_p8`  | +8.0177 %  | -38.7245 % | -0.5956 % | 0 | 3.29041 V |
| `mm_p12` | +12.0089 % | -39.7046 % | -0.5938 % | 0 | 3.29065 V |

### The fit: slope, intercept, residual, and whether through-origin holds

Ordinary least squares `phase_err_% = a + b * mismatch_%` over the locked
points only (`mismatch_gain_metrics.fit_line`), beside the slope-only fit
`phase_err_% = b * mismatch_%` the `+/-3.5 %` screening limit assumes
(`fit_through_origin`):

| | n | **slope `b`** (pp of `T_ref` per pp of mismatch) | **intercept `a`** (pp) | resid RMS | resid max | R^2 |
|---|---|---|---|---|---|---|
| -40 C, two-parameter | 6 | **-0.03940** | **+0.84199** | 0.0094 pp | 0.0163 pp | 0.99921 |
| -40 C, through origin | 6 | -0.03263 | (0 by construction) | **0.8401 pp** | 0.9304 pp | - |
| 27 C, two-parameter | 6 | **-0.04842** | **+0.75401** | 0.0348 pp | 0.0585 pp | 0.99278 |
| 27 C, through origin | 6 | -0.04193 | (0 by construction) | **0.7528 pp** | 0.8250 pp | - |
| pooled (both temperatures) | 12 | -0.04392 | +0.79791 | - | - | 0.96980 |
| **what `+/-3.5 %` assumes** | 1 | **+1.4293** | 0 | - | - | - |

**A linear-through-origin model does not hold.** Forcing the intercept to
zero multiplies the residual RMS by 90x at -40 C (0.0094 -> 0.8401 pp) and
by 22x at 27 C (0.0348 -> 0.7528 pp), and the forced residual is itself
about the size of the whole quantity being measured. A two-parameter line,
by contrast, fits to R^2 = 0.993 and 0.999 with a residual of 0.01 to
0.06 pp. The intercept is the DR-010 `cp`'s own residual at zero mismatch
-- RECORD-006's switch-injection / dump-node term, which RECORD-007
measured at 0.779 % and which no amount of current matching removes.

**The measured gain is about 30x smaller than the screening limit's, and
has the opposite sign.** |b| = 0.0394 to 0.0484 pp/pp against the assumed
1.4293 pp/pp (= 9.176 % / 6.42 %): a factor of 29.5x at 27 C and 36.3x at
-40 C. The sign is negative -- a UP-heavy pump *reduces* the static phase
error -- which is consistent with RECORD-006's mechanism: the residual term
removes charge from the filter every cycle, the loop answers with a
positive (UP-leading) phase offset, and extra UP current means less lead is
needed to supply the same charge. The old derivation, taken on the
pre-DR-010 `cp` where the DC mismatch term dominated, had both the
magnitude and the sign of today's `cp` wrong.

**Inverting the fit for row 7's 5 % criterion gives no usable bound.** The
fitted line reaches +5 % at `mismatch_pct` = **-87.7 %** (27 C) and
**-105.5 %** (-40 C), and -5 % at +118.8 % and +148.3 %. Those are 7.3x to
8.8x outside the measured span, 22.6 to 27.2 sigma out on the campaign's
own 3.8769 % sigma, and (the definition saturates at +/-200 %) correspond
to an UP leg carrying roughly a third of the DN leg's current. **The fit is
not validated there and this record extrapolates no bound from it.** What
it does establish is the positive statement: across the whole measured
+/-11.92 % span, at both temperatures where the proposal deck locks, the
worst final-20 mean static phase error is **1.3265 %** and the worst
single cycle is **+1.447 %**, against the 5 % criterion -- at least
**3.55 pp of margin** everywhere.

Put the other way: over the full +/-11.92 % span the mismatch term
contributes only +/-0.58 pp (27 C) and +/-0.47 pp (-40 C) of static phase
error, which is *less* than the 0.75 to 0.84 pp the zero-mismatch
intercept contributes by itself.

## Baseline reproduction, and the two extraction paths

The AC for this work is that the unperturbed point reproduces RECORD-007's
0.779 % at nominal, or the record explains the difference. Both were done,
on this host, at `mos_tt`/27 C/3.3 V:

| run | extraction | static phase error, final-20 mean [min, max] | dual-lock run | lock time | `i_cp` | `vc_avg` |
|---|---|---|---|---|---|---|
| **RECORD-007** (ngspice-46) | `wave.dat`, linearized 100 ps grid | 0.779 % [0.731, 0.800] | 42 | 400 ns | -64.89 uA | 2.386820 V |
| committed `run_closed_loop_otabuf.sh`, this host, ngspice-47 | same | **0.7780 %** [0.732, 0.802] | 42 | 400.05 ns | -64.8884 uA | 2.386854 V |
| this record's `mm_nom` unit, ngspice-47 | `klt sim` `crossings`, simulator's own grid | **0.7662 %** [0.715, 0.822] | 42 | 400.05 ns | -64.888 uA | 2.38685 V |

- **RECORD-007 is reproduced to 0.001 pp** by its own unmodified script on
  this host under ngspice-47 (0.7780 % vs 0.779 %), with the same 42-cycle
  dual lock and the same 400 ns lock time. The deck, the snapshots and the
  pinned PDK all reproduce.
- **The remaining 0.012 pp is the extraction path, not the simulation.**
  The second and third rows report `i_cp` = -64.888 uA and `vc_avg` =
  2.38685 V -- the same `.meas` values to every printed digit -- so the same
  transient ran. RECORD-005's phase definition interpolates the 1.65 V
  crossings of `v(ref)` and `v(fb)`; `cpdiag_post.py` reads them off the
  deck's `linearize`d uniform 100 ps grid, while `klt sim`'s `crossings`
  measurement reads them off the simulator's own (<= 100 ps) steps. 0.012 pp
  of `T_ref` is 6 ps. The two paths are otherwise the **same function**:
  `mismatch_gain_metrics.lock_trace_from_edges` is the body of
  `cpdiag_metrics.lock_trace` after its two `rising_edges` calls, and
  `../testbench/test_mismatch_gain_metrics.py` asserts on synthetic traces
  that the two return identical lists. 0.012 pp is 2 % of the smallest
  effect this record measures (the 0.58 pp mismatch term) and 0.24 % of the
  5 % criterion.

## Negative control, and the zero-mismatch point

RECORD-012's equal-current diagnostic (0 % mismatch by construction,
-0.00044 % phase error) is **not comparable** to this fit: it was measured
on the pre-DR-010 `cp`, where the DC term dominated and the dump-node
residual this record's intercept measures did not yet exist. The
within-this-record check is the unperturbed point against its own fitted
line: at 27 C the line predicts 0.7685 % at `mismatch_pct` = -0.2985 %
against 0.7662 % measured, a residual of **-0.0023 pp**, 15x inside the
fit's own 0.0348 pp residual RMS; at -40 C it predicts 0.8554 % against
0.8391 %, a residual of -0.0163 pp, at the fit's 0.0163 pp residual max.
The committed `cp` sits on the line the perturbed decks define.

No point at exactly `mismatch_pct` = 0 was run: the perturbation grid was
built around the committed snapshot (which is -0.2985 % at 27 C) rather
than around zero. The intercept is therefore an extrapolation of 0.3 pp
from the nearest measured point, which is 1/40th of the measured span.

## What this does not bound

- **125 C**: no gain is measured. The proposal deck does not acquire there
  at any mismatch point (above), so this record measures the gain at two of
  the three temperatures it ran.
- **Process and supply corners**: `mos_tt` / 3.3 V only (above).
- **The committed loop**: proposal deck (behavioural divider, `R1` x20,
  ideal MOM caps, ideal `IREF`), pre-layout, as RECORD-005 to RECORD-007.
- **Random mismatch**: the mismatch here is *injected* on one mirror leg.
  A drawn sample perturbs every device, so a real Monte Carlo draw at the
  same `mismatch_pct` is not guaranteed to produce the same phase error --
  this measures the sensitivity to the up/dn current ratio, which is the
  quantity `../../sg13cmos5l-cp-icp-trim-mc` grades, not the sensitivity to
  "all mismatch".
- **Other `cp` mismatch quantities**: switching-charge mismatch, bias
  replica mismatch and the dump buffer's own input offset are not stepped.
- **The x-axis is measured at `VOUT` = 2.40 V at every temperature**, which
  is the Monte Carlo bench's own operating point and is what makes these
  numbers directly comparable with `RECORD-002`'s draws. The closed loop
  does not sit there at every temperature: `vc_avg` is 2.3868 V at 27 C
  (within 13 mV of 2.40 V) but **2.2249 V at -40 C**, 175 mV lower. The
  -40 C row of the fit therefore pairs a phase error measured at 2.2249 V
  with a mismatch measured at 2.40 V. `../../sg13cmos5l-cp-icp-trim`'s
  `RECORD-002` is the record that shows `mismatch_pct` is `VOUT`-dependent,
  so the -40 C slope and intercept carry that systematic; the 27 C row does
  not materially. Re-measuring the DC axis at each temperature's own
  `vc_avg` would remove it and was not done.
- **`f_ref` and trim code**: 20 MHz, `Iref` = 10 uA only. RECORD-007's own
  caveat applies -- a fixed charge residue costs more phase at low
  `Icp * T_ref`, so the intercept (not the slope) is the term that grows at
  low trim codes.
- **Post-layout**: nothing here is extracted.

## New gap found by this record

**The proposal deck does not acquire lock at 125 C.** `vctrl` rails at
3.289 V with `df/f_ref` = -0.60 % at all six mismatch points, including the
unperturbed one, so this is not a mismatch effect. Every closed-loop record
in this slug before this one ran at 27 C only, so no earlier record would
have seen it. It is a property of the diagnostic deck (behavioural
divide-by-64, `VC0` = 2.46 V, `R1` x20), **not an evaluated claim about the
committed PLL**, and this record makes none. It is filed as issue #389
rather than worked around here.

## Reproduce

```bash
export PINNED_PDK=<ihp-sg13cmos5l checkout at 607e18d4...>
cd sim/sg13cmos5l-closed-loop-lock/testbench
python3 -I test_mismatch_gain_metrics.py            # offline self-test, no PDK
python3 -I gen_mismatch_gain_requests.py --pinned-pdk "$PINNED_PDK" /tmp/mmgain

# the grid: batch fleet only, never a local loop (host rules)
klt sim --batch-set /tmp/mmgain/dc/*/request.json   --wait-for-capacity 600 \
    --capacity-retries 3 -o /tmp/mmgain/dc-out   --format json
klt sim --batch-set /tmp/mmgain/loop/*/request.json --wait-for-capacity 600 \
    --capacity-retries 3 -o /tmp/mmgain/loop-out --format json

python3 -I mismatch_gain_post.py /tmp/mmgain/points.json \
    ../corners/sim_mismatch_gain_dc.json ../corners/sim_mismatch_gain_loop.json \
    --csv ../corners/mismatch_gain.csv --summary ../corners/mismatch_gain_fit.json

# the two single-point baseline checks (ONE unit each -- local is allowed)
PDK_ROOT=<parent> PDK=<pinned tree> OUT_PREFIX=/tmp/otabuf RUN_NAME=otabuf_i385 \
    ./run_closed_loop_otabuf.sh
```

`mismatch_gain_post.py` reads the committed `sim_mismatch_gain_*.json`
bundles (every member's own `klt sim` report, inlined under its request
path) so the tables above regenerate without re-simulating.
