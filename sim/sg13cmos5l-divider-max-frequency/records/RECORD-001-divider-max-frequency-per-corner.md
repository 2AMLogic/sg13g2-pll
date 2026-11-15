# RECORD-001: divider_chain maximum input frequency per corner (640-1562 MHz, N=64/127, 9 PVT corners, pinned PDK)

Issue #402. Part of #16 (row 3 context). Bench: `sim/sg13cmos5l-divider-max-frequency/`.

## What this record claims

The committed (repaired) `divider_chain` alone, driven by an ideal clock, is characterised
over its maximum input frequency: for N=64 and N=127 at a 9-point PVT star, the highest
clock frequency at which **every scored feedback (FB) period contains exactly N rising
clock edges**, per corner, to a stated resolution. At the nominal corner's first failing
frequency the record names the first stage that departs from the ideal per-stage edge
cascade, with committed waveform evidence. This is the characterisation the closed-loop
slug's three-point bracket explicitly was not
(`sim/sg13cmos5l-closed-loop-real-divider/records/RECORD-001` § "Root cause": *"a 3-point
bracket (640 MHz ok, 1.28 GHz not), not a characterisation of the speed limit"*).

## Method

### Testbench

`testbench/tb_div_maxfreq.sp.tmpl`, rendered per unit by
`testbench/gen_maxfreq_requests.py` into pre-composed decks (288 coarse + refine +
control units) run verbatim by `klt sim` deck-list requests. Per unit:

- the divider alone (`netlist-snapshots/divider_chain.spice`), both clock inputs tied to
  one ideal `pulse` source (CKIN = CKIN_VCO = ck: in the closed loop they are the same
  net, as in `tb_div_func.sp.tmpl`);
- drive shape = the `tb_div_speed.sp.tmpl` convention the anchors must reproduce against:
  **80 ps edges, ~50 % duty** (`CH = TPER/2 - 80p`), amplitude VDD;
- `.ic` symmetry break on all 13 `dff_tg_hv` state elements (the recorded testbench
  workaround for the no-reset design gap, `sg13cmos5l-divider-nrange-retiming` RECORD-001
  Finding 1);
- reltol 0.001 (the value `sg13cmos5l-divider-nrange-retiming`'s tol stage showed this
  deck family converges at; 0.005 fails), timestep **20 ps** for every sweep unit
  (>= 32 samples per 640 ps clock period at 1562 MHz, the top of the sweep);
- `TSTOP = 8.0*N/f_clk + 20 ns`; the first 10 ns of the clock is inside the rise, and FB
  periods 1..3 are startup (the first post-startup FB edge is shifted by the .ic settling
  glitch: measured 6.7 ns at the 640 MHz anchor) and never scored; **FB periods 4..8 are
  scored, >= 4 of which must lie fully inside the window** `[2.0*N/f, 7.5*N/f]`.

### Edge counting

Every rising 50 %-crossing time of the clock and of FB (and, on stage-count units, of
`ck1..ck5` and DIVOUT) is measured by ngspice itself: one generated
`.meas tran <name> when v(<node>)=VDD/2 rise=k` line per edge index. `.meas` interpolates
on the solver's own points (<= timestep apart), so crossing times do not depend on a
re-gridded waveform; a missing edge prints a named `failed!` line and is recorded as such.
The collector (`testbench/collect_maxfreq.py`) buckets the clock edges per FB period
(interval `[f[i], f[i+1])`) and scores each period against N. **The per-period list is the
evidence, never a single ratio**: an adjacent N-1, N+1 pair summing to 2N is the signature
of a sampling-boundary artifact; a real failure shows a sustained wrong count (as the
committed 1.28 GHz artifact's flat `96,96,96,96,96` does).

Verdicts: `exact` (all scored periods == N, >= 4 periods), `exact-partial` (all == N but
fewer scored -- possible when a corner's longer settling shifts the window; treated as
exact for bounds but named), `miscount` (any scored period != N), `fb-stopped` (< 2 FB
edges in the window), `engine-error`.

### Pinned PDK (staged, not resolved on the worker)

The fleet image's `/opt/pdk/ihp-sg13cmos5l` is the post-2026-10-15 `f7bca326...` install,
not this repo's pin. As in `sg13cmos5l-vco-kvco-table` RECORD-002 (issue #318), the
generator requires `--pinned-pdk DIR`, copies the pinned tree's `cornerMOShv.lib` model
closure (8 files) and the three OSDI objects beside the decks (`decks/models/`,
`decks/osdi/`, `staged_pdk.sha256.csv`), and the decks name them by relative path —
`klt sim`'s deck-list preservation contract stages those bytes from the submitting host,
so `$PDK_ROOT` is never read and the record may cite the pin. The pinned checkout is the
clean git tree at `~/share/pdk/ihp-sg13cmos5l.bak-20261015T153815Z` (HEAD
`607e18d4bd9214a52575c194b4181ef449f9252f`); its model cards and OSDI objects are
symlinks into the sibling `ihp-sg13g2` tree, whose installed `libs.tech/ngspice` subtree
was re-verified byte-identical to the `ihp-sg13g2` pin `5cccb161...` install on the day
of the run (`diff -rq` clean, `.fetched-version` = 0.3.0). Both trees are cited
tree-qualified below; copyfile followed the symlinks, so the staged bytes are the pinned
targets' bytes (per-file sha256 in the committed `staged_pdk.sha256.csv`).

### Anchors (harness validation against the committed bracket)

The DUT is byte-identical to the one `sg13cmos5l-closed-loop-real-divider` RECORD-001
simulated (comment-line-stripped `diff` empty against that slug's snapshot), so that
slug's committed three-point bracket is a free regression test of this harness. Both
anchors ran locally, one unit per request, nominal corner, N=64, with per-stage counts:

| Anchor | This harness | RECORD-001's committed artifact | Stage cascade (per FB period) |
| --- | --- | --- | --- |
| 640 MHz | `exact`, scored counts `64,64,64,64,64` | `64,64,64,64` (`corners/edges_divspeed_640MHz.json`) | `ck=64, ck1=32, ck2=16, ck3=8, ck4=4, ck5=2, fb=1, divout=1` — exactly the cascade `N = 64 + sum(P_i*2^i)` unrolls to |
| 1280 MHz | `miscount`, scored counts `96,96` | `96,96,96,96,96` (`corners/edges_divspeed_1280MHz.json`) | `ck=96` but `ck1=32, ck2=16, ck3=8, ck4=4, ck5=2`: **XD0** (the first `div23_cell`) is already the stage off its expected count — it captures only ~2/3 of its input edges |

The 640 MHz stage cascade equals the analytically expected `64,32,16,8,4,2,1`
(`c_{k+1} = (c_k - P_k)/2`, `c_0` on CKIN, `c_6` on DIVOUT) — the control the
stage-isolation attribution relies on.

## Coverage

- **N**: 64 (word `000000`) and 127 (word `111111`, the structural maximum).
- **Corners** (the 9-point baseline star of `sg13cmos5l-divider-nrange-retiming`
  RECORD-003 / its pinned rerun): `mos_tt/ss/ff/sf/fs` at 27 C / 3.3 V, `mos_tt` at
  -40 C and 125 C, `mos_tt` at 2.97 V and 3.63 V. The supply axis is the +/-10 %
  star (2.97/3.63 V), **not** the 3.0/3.6 V of `sg13cmos5l-supply-range`. Temperature is
  `mos_tt`-only at the extremes: a full 5x3x3 star would be 36 corners RECORD-003 never
  ran (the PVT-matrix rule in `sim/README.md` requires stating this, not dropping the
  axis silently).
- **Frequency**: 640 -> 1562 MHz. Coarse wave 64 MHz steps (640, 704, ..., 1536, plus
  1562 itself; 16 points x 18 cells = 288 units); refine wave 51 units at 16 MHz interior
  points inside each cell's exact/fail transition (17 two-sided cells x 3 points);
  **stated resolution 16 MHz** (~1 % of the top of band). The top of the sweep is row 1's
  ceiling, 1562.0 MHz (`spec/target-spec.md:91`, the `fast`/band-11/2.7 V operating
  point). One-sided results are named as such in `corners/max-freq-by-corner.csv`.
- **Resolution control**: three checks, all committed under `corners/`.
  (1) The declared-failing nominal point 1152 MHz re-run at half the sampling step
  (`n64_mos_tt_27c_3v3_f1152_s10`, 10 ps): verdict `miscount` unchanged, but the per-period
  counts differ (`85,85,85` at 10 ps vs `88,87,88` at 20 ps, `edges_n64_mos_tt_27c_3v3_f1152_s10.json`
  vs `edges_n64_mos_tt_27c_3v3_f1152_w.json`) — near the failure boundary the number of
  edges XD0 swallows is timestep-sensitive, so failing-point counts are reported as
  solver-dependent, not physical constants. (2) The nominal cell's exact/fail BOUND
  re-checked at 10 ps: 1120 MHz `exact` (`64,64,64,64,64`) and 1136 MHz `miscount`
  (`75,75,75,75`) — both verdicts match the 20 ps grid, so the stated 16 MHz bound is
  timestep-robust. (3) No swept failing point shows the sampling-boundary signature
  (an adjacent N-1/N+1 pair summing to 2N): every failing cell's counts are a sustained
  near-constant (e.g. `80,80,80`, `96,96,96,96,96`, `128,128`), and the stage-count
  controls show `ck1..ck5,fb,divout` at their ideal cascade values in every scored period
  — the bucketing is not splitting periods.
- Batch route only: every grid job went through `klt sim --backend batch` with
  `--wait-for-capacity 600`; all 191 batch job ids (two coarse attempts after an
  interrupted session, the `--resume` completion, refine, four controls runs, the 2-unit
  probe) are in `corners/batch-jobs.csv`. The anchors are the only locally-run units
  (single-unit probes, host policy). No hand-launched ngspice grid.

## Results

Every scored FB period's count is in `corners/maxfreq.csv` (339 swept units, one row each;
per-period lists and edge times in `corners/edges_<unit>.json`); the per-corner bounds are
`corners/max-freq-by-corner.csv` (regenerated by `testbench/collect_maxfreq.py --merge`):

| Corner | N=64: exact at / first miscount | N=127: exact at / first miscount |
| --- | --- | --- |
| `mos_ff` 27 C 3.3 V | 1232 / 1248 MHz | 832 / 848 MHz |
| `mos_fs` 27 C 3.3 V | 1104 / 1120 MHz | 736 / 752 MHz |
| `mos_sf` 27 C 3.3 V | 1120 / 1136 MHz | 752 / 768 MHz |
| `mos_ss` 27 C 3.3 V | 992 / 1008 MHz | 656 / 672 MHz |
| `mos_tt` −40 C 3.3 V | 1312 / 1328 MHz | 880 / 896 MHz |
| `mos_tt` 27 C 2.97 V | 1008 / 1024 MHz | 672 / 688 MHz |
| `mos_tt` 27 C 3.3 V (nominal) | 1120 / 1136 MHz | 752 / 768 MHz |
| `mos_tt` 27 C 3.63 V | 1216 / 1232 MHz | 816 / 832 MHz |
| `mos_tt` 125 C 3.3 V | 880 / 896 MHz | **miscounts at every swept frequency** (bound: fails ≥ 640 MHz, resolution 64 MHz) |

Each entry is a bracket, not a point: "exact at F" means every scored FB period contained
exactly N rising clock edges at F, and "first miscount" is the next swept frequency where
some scored period did not; the stated resolution is 16 MHz everywhere except the one
one-sided cell (64 MHz, nothing exact anywhere in the swept range).

Reading the table:

- **The divider-alone functional limit is 880–1328 MHz (N=64) across the star** —
  comfortably above the closed-loop campaign's 640 MHz operating floor, but below row 1's
  1562.0 MHz VCO ceiling in every corner: **the committed chain cannot ship an exact-N
  divide anywhere in the spec's top VCO band at any tested corner.**
- **N=127 fails at ~2/3 the N=64 limit at every corner** (0.65–0.71 across the nine) —
  the margin cost of the top programming word is large and uniform.
- The corner ordering is the expected digital one: faster with lower temperature
  (−40 > 27 > 125 C), faster with higher supply (3.63 > 3.3 > 2.97 V), `ff` fastest and
  `ss` slowest of the five MOS corners; `mos_tt`/125 C is the only cell with no exact
  point at all for N=127.
- Failing counts are a sustained near-constant per cell (e.g. nominal N=64: 75–96 edges
  per FB period at 1136–1280 MHz, 128 at 1562 MHz) — the XD0 stage absorbs the surplus
  (next section), the downstream cascade stays ideal.

## Failing-stage isolation at the nominal first-failing frequency

The nominal N=64 cell's first failing frequency is 1136 MHz (refine wave). Wave-dump
control units (8-column stage nodes, `testbench/maxfreq/decks/*_w.sp`, 20 ps) commit the
per-stage evidence; `corners/waves-n64_mos_tt_27c_3v3_f1136_w.csv.gz` is the waveform
(`corners/edges_n64_mos_tt_27c_3v3_f1136_w.json` the derived counts), with the last-exact
neighbour 1120/1088 MHz and the coarse first-fail 1152 MHz as controls:

| Unit | f (MHz) | verdict | ck | ck1 | ck2 | ck3 | ck4 | ck5 | fb | divout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `…f1088_w` (last coarse-exact) | 1088 | `exact`, `64×5` | 64 | 32 | 16 | 8 | 4 | 2 | 1 | 1 |
| `…f1136_w` (**first fail**) | 1136 | `miscount`, `80,80,80` | **80** | 32 | 16 | 8 | 4 | 2 | 1 | 1 |
| `…f1152_w` | 1152 | `miscount`, `88,87,88` | 88–87 | 32 | 16 | 8 | 4 | 2 | 1 | 1 |

**XD0 — the first `div23_cell` — is the stage that departs first.** At 1136 MHz every
scored FB period stretches to 80 clock edges while `ck1` stays at exactly 32: a ÷2 stage
fed 80 edges should emit 40, so XD0 is failing to capture 20 of them (setup violation at
its internal `dff_tg_hv`), and every downstream stage divides its (stretched) input
exactly. The failure is a capture-rate deficiency inside XD0, not a bucketing artifact:
the per-period counts are sustained (80,80,80 — no N−1/N+1 pair), the downstream cascade
is at its ideal values in every scored period, and the 10 ps re-run at this frequency
(`…f1136_s10`, `75,75,75,75`) reproduces the verdict with the same signature. Closer to
the boundary the swallowed fraction shrinks (75 edges at 1136 → 85 at 1152 → 96 at
1280 → 128 at 1562); the anchor table above already showed the same stage off-count at
1280 MHz. The absolute count value near the boundary is timestep-sensitive (85 vs 88 at
1152 MHz, 75 vs 80 at 1136 MHz, 10 ps vs 20 ps) — reported as solver-dependent; the
verdicts and the bound bracket are not (resolution control 2).

## Report against the row-3 isolated-flop brackets

`spec/target-spec.md:93` records one-edge closing bounds of 825 MHz (`mos_tt`/−40 C),
866 MHz (`mos_tt`/27 C) and 1277 MHz (`mos_ff`/27 C) from isolated-flop setup brackets;
`sg13cmos5l-divider-retiming-sizing` RECORD-002 flags them UNRESOLVED against in-situ
`tfb`−`tdiv` evidence. This record measures the whole-chain functional limit directly
(N=64), so it speaks to that disagreement:

| Corner | Isolated-flop closing bound | This record, N=64 | Relation |
| --- | --- | --- | --- |
| `mos_tt` −40 C | 825 MHz | exact ≤ 1312 MHz | functional limit exceeds the bracket by ≥ 487 MHz (59 %) |
| `mos_tt` 27 C | 866 MHz | exact ≤ 1120 MHz | exceeds the bracket by ≥ 254 MHz (29 %) |
| `mos_ff` 27 C | 1277 MHz | exact ≤ 1232 MHz, miscounts ≥ 1248 MHz | bracket lies **above** the measured failure threshold by ≥ 29 MHz |

The isolated-flop brackets are neither a floor nor a ceiling for the working chain: at
both `tt` corners the chain divides exactly far above its bracket, while at `mos_ff`/27 C
it miscounts below its bracket. Directionally this **supports the in-situ reading**
RECORD-002 favoured (next-edge capture works beyond the isolated-flop numbers) for the
`tt` corners, and adds a caveat the brackets could not see: whole-chain function fails
earlier than any single-flop closure bound at the fast corner, because the binding stage
is XD0's capture rate (previous section), not the retiming flop the brackets sized. This
is reporting, not resizing: neither `spec/target-spec.md` row 3 nor RECORD-002 was edited
(both append-only; out of scope per the issue).

## Provenance

- **PDK**: PDK ihp-sg13cmos5l revision 607e18d4bd9214a52575c194b4181ef449f9252f — the
  `sim/README.md` pin, staged byte-exact beside the decks by the generator from the clean
  pinned checkout (per-file sha256 in `testbench/maxfreq/staged_pdk.sha256.csv`; closure
  re-verified into PDK ihp-sg13g2 revision 5cccb161f7492697cfa52eb14dc03beb00bdca9e, see
  § "Pinned PDK" above). The fleet image's own `/opt/pdk` tree was never read (`$PDK_ROOT`
  unresolved on every worker run; `models_lib_comparison: not_comparable,
  runner_hash_unavailable` in the reports).
- **DUT**: `netlist-snapshots/divider_chain.spice`, sha256
  `1c72f2384969d8469ff45ac02f22eb8b490d1d98b6454c6c991925c90ebc173e`, frozen verbatim
  from `design/sg13cmos5l/netlist/divider_chain.spice` at commit `1b0f9c9` (origin/main,
  header-recorded). The closed-loop slug's snapshot has a different file hash
  (`f9e60ee3…`, different provenance header); comment-line-stripped bodies are identical,
  which is what makes that slug's bracket a valid anchor for this harness.
- **Tools**: ngspice-47 on every worker run (banner in each report's
  `worker_environment`) and ngspice-47 locally for the two anchors; client klt
  `0.9.2.dev1029+g76f47afa48f1` for the probe and both coarse attempts, client klt
  `0.9.3.dev3+gd5d57daf9a14` for the resume/refine/controls runs; runner klt 0.9.0
  (`runner_compatibility: match` in every report). Workers: spot `c7i.4xlarge`
  (Xeon Platinum 8488C), us-east-1.
- **Batch route**: 191 batch jobs (list with per-job state:
  `corners/batch-jobs.csv`). Session-interruption recovery, recorded because it explains
  the attempt structure: the first coarse submit (96 × 3-unit shards, 2026-11-14 21:29)
  and the resubmit (49 shards, 23:03) each lost their client mid-poll; `--attach
  --collect-partial` then `--resume` (2026-11-15) collected the finished shards and
  re-issued only the 90 units without valid records; 198 of the 288 coarse units were
  resumed without re-simulation. Every unit in the committed CSVs ran exactly once.
- **Template revision note**: the wave-deck rendering fix (control-block `tran` for
  `wrdata`, 2026-11-15) post-dates the anchors/coarse/refine runs. Those phases' decks
  differ from a fresh render of the committed template in header-comment lines only;
  their as-run bytes are attested by the committed per-phase `decks.sha256.csv` files
  and the per-unit `deck_sha256` in every report and edges artifact. The controls decks
  (both wave units included) were rendered from the fixed template and attest their own
  bytes the same way. The wave-deck failure this fix addresses is recorded in
  § "Resolution control" item (1)'s sibling artifacts: the first controls run's two wave
  units exited with ngspice's `Unable to find definition of model v(xdiv.ck2` (the
  spliced-comment failure; `controls.report.json` superseded by the passing rerun).
- **Deck rendering guard**: the generator now refuses any template whose `@POST@`/`@MEAS@`/
  `@TRAN@` tokens occur more than once and any rendered deck whose live/control sections
  do not match the unit's phase — the failure mode above cannot re-render silently.

## What this does not bound

- Post-layout (PEX) speed — schematic-level, ideal-clock, divider-alone only.
- Any redesign or resizing of the divider (R-3 / DR-012 are out of scope; nothing in
  `spec/target-spec.md` or any decision record was edited).
- The SG13G2 (non-port) divider: it has no maximum-input-frequency evidence at all; the
  re-worded `divider-speed` gap in `characterization/sources.json` says exactly that.
- Closed-loop lock: row 7 still fails independently (see `sg13cmos5l-closed-loop-lock`).
