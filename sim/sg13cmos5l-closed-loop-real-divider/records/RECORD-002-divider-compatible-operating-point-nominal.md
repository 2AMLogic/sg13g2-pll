# RECORD-002: closed loop at a divider-compatible operating point — band 00, f_ref = 9.375 MHz, N = 64 — nominal — real-divider arm LOCKS

- **Slug**: `sg13cmos5l-closed-loop-real-divider`
- **Issue**: #401 (Part of #16; advances #6). Append-only: RECORD-001 and
  ADDENDUM-001 are not edited, and none of their committed `corners/` or
  `netlist-snapshots/` bytes is overwritten — every artifact of this record
  carries a `_o2` tag and the DR-010 `cp` is a NEW snapshot file (see
  "Reproduce").
- **Scope**: ONE nominal point (`mos_tt` / `res_typ` / 27 C / 3.3 V),
  pre-layout, two arms (behavioural-divider control, real `divider_chain`),
  plus one ideal-clock divider-only diagnostic at the same frequency. Not a
  PVT campaign, not post-layout; no spec row is ratified, amended or relaxed.
- **Tooling**: ngspice-47 (`~/.local/bin/ngspice` wrapper, sha256
  `39ca1adb826660324c3626f72bd946ec40704f0f3fc8e243c623f76e24b3eee2`),
  x86-64 Linux, `num_threads=2`. Each run below is a single local
  `ngspice -b`, run sequentially. ADDENDUM-001 recorded ngspice-46 for
  RECORD-001's runs; the host default has since moved to ngspice-47.

## Operating point — the one RECORD-001 left untested

RECORD-001 established that the N = 64 loop at `f_ref` = 20 MHz (VCO at
1.28 GHz, band `11`) does not acquire because the real `divider_chain`
misdivides at that frequency, while dividing exactly by 64 at 200 and
640 MHz on an ideal clock; whether the loop locks at an operating point the
divider can sustain was left untested. This record runs that point:

| Axis | Value | Why |
|---|---|---|
| Divider word | `P5..P0 = 000000` (N = 64), unchanged | the only ratio whose control arm needs no new behavioural divider (`arm_control.inc` is hard-wired six-stage /64) |
| VCO band | `B0 = B1 = 0 V` (band `00`) | lowest Kvco row of the table, against the halved `f_c < f_ref/10` ceiling |
| `f_ref` | 9.375 MHz (`T_ref` = 106.67 ns, 50 % duty) | inside target-spec row 2 (3.5–24.4 MHz); N = 64 puts `f_vco` at 600 MHz |
| Target `f_vco` | 600.0 MHz | 40 MHz below the 640 MHz where RECORD-001's ideal-clock bracket proves exact /64 (margin, not the bracket edge), and below target-spec row 3's measured 866 MHz `mos_tt`/27 C one-edge retiming closing bound |
| `.ic v(vctrl)` | 1.23 V | linear interpolation of `sg13cmos5l-vco-kvco-table` RECORD-001's band `00` row (0.9 V → 533.08 MHz, 1.5 V → 654.98 MHz gives 1.229 V for 600 MHz); mid-range — far from the 0.3/2.7 V characterised ends and from `cp`'s 0.25–3.10 V compliance window — so a rail-pinned `vctrl` would be unambiguous evidence of non-acquisition, not of a bad start |
| Duration | `.tran 100p 10u 0 100p` (10 us = 93.75 `T_ref`; 94 ref edges, 93 cycles in the per-cycle trace) | the dual-lock criterion needs 20 consecutive cycles *after* acquisition; RECORD-001's 2500 ns default spans only ~23 `T_ref` at this `f_ref` |
| Averaging window | 8–10 us (18.75 `T_ref`) | `.meas` current/`vctrl` averages, same shape as RECORD-001's 2.0–2.5 us |
| `NGSPICE_TIMEOUT` | 3600 s (control) / 5400 s (real) | the default 2400 s would kill the longer window (RECORD-001's real arm already needed 912 s for 2500 ns) |

Everything else is held at RECORD-001's values: nominal corner, 3.3 V rails,
ideal 10 uA `IREF` (S3), loop-filter ideal caps at the campaign values (S1),
VCO `XCDECAP` stripped (S2), lock detector not instantiated (S5), real-arm
latch `.ic` symmetry break (S7), solver options and `.save` list identical.
The full substitution list S1–S7 is disclosed in RECORD-001 and carries over
unchanged; nothing on that list changes meaning here. The one deck delta vs
RECORD-001 is the charge pump itself: the DR-010 complementary dump-buffer
`cp` — the committed design — replaces the pre-DR-010 frozen export. That is
not a substitution (it removes one); `run.sh` gained a `CP_SNAP` selector for
it, plus `FREF/B0V/B1V/VC0` overrides. **`run.sh` defaults still reproduce
RECORD-001's point** (FREF 20e6, band `11`, `VC0` 2.46, `cp.spice`); a bare
`./run.sh <arm>` with no `TAG_SUFFIX` would overwrite RECORD-001's committed
`corners/` artifacts, so every run here sets a non-empty `TAG_SUFFIX`.

## Frozen DUT inputs (`netlist-snapshots/`)

| Snapshot | sha256 (of the snapshot file) | vs RECORD-001 |
|---|---|---|
| `pfd.spice` | `56309ee99b96300a0de0d2ff2efaee82dd5043125232315b3641e081c9697c4c` | unchanged |
| `cp.spice` | `111d033757a3530d80de782d891c022f9d91a693a98015b715724cb6b08f93e8` | unchanged (RECORD-001's pre-DR-010 export, kept in place) |
| `cp-dr010.spice` | `a3dfd0e8a37864d3ad46b26fc095c86515c68c83c4f39865dbf3aa7bb898115a` | **NEW**: DR-010 block, body byte-identical to `design/sg13cmos5l/netlist/cp.spice` at `ab6e9f1` (origin/main) |
| `loop_filter.spice` | `ddb7d526ad919c998085ac411c3feaf134c566f2468f4f942a248befd843549b` | unchanged |
| `vco.spice` | `3473ac1274f5c3a78c86ac319d5daca7ffb339071f44576a8403fffbad7fe507` | unchanged |
| `divider_chain.spice` | `f9e60ee31cb44183a4d5bd58dc68b307d16e716f1a0df90af8d9593ceb2e20af` | unchanged |

`.subckt cp`'s port list is identical between the pre-DR-010 snapshot and the
DR-010 block (only the internal `cp_dumpbuf` gained an `IBP` port, wired
inside `cp`), so the swap needs no testbench rewiring: the template's
`XCP up dn ibp icp ibn icn vctrl vdd_cp 0 cp` line is unchanged.

## Results (`corners/`; per arm: `log_*_o2.txt`, `trace_*_o2.csv`, `vctrl_*_o2.csv`, `summary_*_o2.json`)

Lock criterion: the campaign's existing dual-lock (`|df/f_ref| < 1 %` AND
`|phase| < 5 % T_ref` for >= 20 consecutive reference cycles),
`lock_analysis` imported unchanged from
`../sg13cmos5l-closed-loop-lock/testbench/extract.py`, exactly as in
RECORD-001.

| Quantity | Control (behavioural /64) | Real `divider_chain` |
|---|---|---|
| Dual lock / `lock_time` | **yes** (213.4 ns = 2.0 `T_ref`) | **yes** (320.0 ns = 3.0 `T_ref`) |
| Longest dual-lock run | 92 cycles (from 213 ns to end of trace) | 91 cycles (from 320 ns to end of trace) |
| Frequency-lock (`\|df\|<1 %`) longest run | 92 cycles | 91 cycles |
| `vctrl` start -> end (min / max) | 1.23 -> 1.2635 V (1.2073 / 1.4153) | 1.23 -> 1.2740 V (1.2167 / 1.5402) |
| `vc_avg` 8–10 us (min / max in window) | 1.2644 V (1.2443 / 1.3664) | 1.2746 V (1.2542 / 1.3793) |
| `f_vco` (8–10 us / final 500 ns) | 600.008 / 599.93 MHz | 599.996 / 599.94 MHz |
| `f_fb` (8–10 us) | 9.37507 MHz | 9.37499 MHz |
| clk edges per FB period (8–10 us; whole run) | 64 (18/18; 93/93) | 64 (18/18; 93/93) |
| Final-20-cycle `df/f_ref` mean | -0.0013 % (-0.040 / +0.041 %) | -0.00035 % (-0.118 / +0.084 %) |
| Final-20-cycle phase error (% `T_ref`) | 1.741 (1.715–1.756) | 1.729 (1.705–1.837) |
| `i_pfd` / `i_cp` / `i_vco` (avg 8–10 us) | -25.0 / -62.1 / -1341.6 uA | -25.3 / -62.1 / -1443.5 uA |
| `i_div` (avg) | 0 (unloaded) | -1374.5 uA |
| Wall time | 957 s | 2376 s |

**Real-divider arm: the loop acquires and locks.** With the DR-010 `cp` and
the divider inside its proven range, the closed loop acquires in 3 reference
cycles (320 ns) and then holds the dual-lock criterion for the remaining 91
cycles to the end of the 10 us window — the criterion neither arm could meet
in RECORD-001. The real chain divides exactly 64 in **93/93** FB periods
(5952 clk edges in those 93 periods, not one dropped or doubled; 6003 across
the full 10 us run), so at 600 MHz the in-loop
divider behaves exactly like the ideal-clock case — in contrast to 1.28 GHz,
where the ideal clock gave 96 and the in-loop waveform 128. The VCO settles
at 599.996 MHz (final-20-cycle `df` mean -0.00035 %), and the static phase
error is 1.729 % of `T_ref`, under the 5 % bound that failed both arms at the
old point.

This answers RECORD-001's open question affirmatively. That record's real-arm
non-acquisition was a top-of-band divider-speed effect: the in-loop misdivide
is absent at 600 MHz (93/93 FB periods at exactly 64). RECORD-001's *control*
arm failed the same criterion for a different, loop-level reason (8.31 %
static phase error with no real divider in the loop); that failure is also
absent here (1.741 %), but this record does not attribute why — `f_ref`,
band, Kvco and the `cp` all moved together (see "What this does and does not
establish").
The same loop discipline (`pfd` + `loop_filter` + `vco` + repaired
`divider_chain`, with the `cp` updated to the committed DR-010 block) locks
at an operating point the divider can sustain, and the divider produces the
commanded ratio edge-exactly in-loop there. It localizes the 1.28 GHz failure
to that operating point; it does not characterise where between 640 and
1280 MHz the divider stops counting exactly (that is #402's scope).

Warm-start caveat: `lock_time` here is a warm-started acquisition —
`.ic vctrl` = 1.23 V sits ~35–45 mV from the settled value (1.264/1.275 V),
plus the `ring1` and divider-latch `.ic` — not a cold-start acquisition from
an arbitrary control voltage, and not a row-7 claim (row 7 is gated on real
blocks across PVT, R-2).


## Supporting ideal-clock diagnostic at 600 MHz

`testbench/run_div_speed.sh 6e8` (`TSTOP_OVERRIDE=900n`, nominal, 182 s):
the same frozen `divider_chain`, same rails/word/latch `.ic`, ideal 50 % duty
clock at 600 MHz. Persisted artifacts:
[edges_divspeed_600MHz.txt](../corners/edges_divspeed_600MHz.txt) /
[json](../corners/edges_divspeed_600MHz.json), log
[log_divspeed_600MHz.txt](../corners/log_divspeed_600MHz.txt): **64 clk edges
per FB period in 8/8 periods**, `i_div` avg -1373.27 uA. The RECORD-001
bracket therefore extends to: 200 MHz exact, **600 MHz exact (new, this
record)**, 640 MHz exact, 1.28 GHz wrong (96 edges). The loop's required
frequency here is one the divider provably counts correctly on a clean clock,
with margin on both sides of the proven 640 MHz point.

## Provenance — PDK tree and revisions

- **MOS models**: the deck loads `cornerMOShv.lib` (`mos_tt`) from the
  CMOS5L tree; that file is byte-identical on this host (sha256
  `5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a`) to the
  release install of the unified repository — PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e, as established in
  `sim/provenance-migration.md` from the `.fetched-version` 0.3.0 marker
  (the install is a tarball, not a git checkout). This is the record's
  gate-parsed revision citation, following the working precedent of
  `sg13cmos5l-loop-filter-momcap/records/RECORD-003-rc-corner-momcap-rerun-batch.md`.
- **The tree that actually ran** is NOT that release install and NOT the
  `PDK-PIN ihp-sg13cmos5l 607e18d4bd9214a52575c194b4181ef449f9252f` clone
  either: it is `~/share/pdk/ihp-sg13cmos5l`, the unified-repository fleet
  bundle, store version `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14`
  (bundle sha256
  `3195ba7f3a74e91fc4eced64102c9d61b00d8eadcf5e795d36d926d40ab4ad31`,
  `.pdk-store.json`, synced 2026-10-15, no `.git`). Its resistor card and
  OSDI objects differ from the release install's: `cornerRES.lib` here has
  sha256 `c6d749e72cfa2e06e4a14fac3f5662541bf6197b89265ecbedd632fd3503c425`
  (release install: `2c18502104146804444a567abfe7d00520752bf75426809f9d79f40198fe9c1e`),
  and the four loaded OSDI objects are bundle builds
  (`psp103` `dba873bcef3f1978b30d66a4dcb661f79c6f6386c29da8841712d84399e13f1a`,
  `psp103_nqs` `ad99ea641e0b88b29125a786e77f3dcb3b206b5e116e23c2a265783658e69754`,
  `mosvar` `cded61b14fbe50f74453e995a00f4876664328fd477badf672e5b2405cae5973`,
  `r3_cmc` `746f86fd1b89c309cbec7b23e661a66ee80b2d897ea229bc8e3fcc3757a673c3`).
  The content difference is real, not cosmetic:
  `sg13cmos5l-lock-detector-window` RECORD-011 measured `rhigh`-card-driven
  R shifts of -4.5 to -8.7 % between the pinned tree and this bundle. The
  pin re-stamp is #250 (open) and out of scope here; this record attributes
  itself to the pins per the `sim/README.md` convention while stating the
  ran-on tree plainly, and no corner landed in this record leans on a
  resistor value.
- **Tooling drift**: ngspice-47 here vs the ngspice-46 that ADDENDUM-001
  recorded for RECORD-001's runs (and that the #168 `run_div_speed` re-runs
  also used). No version-A/B was run; absolute cross-version comparability
  is not claimed.

## What this does and does not establish

- Establishes (nominal corner, pre-layout, ONE run per arm,
  simulator-deterministic, 10 us window): with the committed `pfd`, DR-010
  `cp`, `loop_filter`, `vco` and repaired `divider_chain`, the N = 64 loop
  **acquires and holds the dual-lock criterion at band `00`,
  `f_ref` = 9.375 MHz (600 MHz)** in both arms; the real chain divides
  exactly 64 in-loop (93/93 FB periods, no dropped or doubled edge in the
  window). This rules out the strong form of RECORD-001's failure mode: the
  in-loop miscount is not present at every operating point, and no
  frequency-independent loop defect prevents acquisition — the misdivide is
  localized to the ~1.28 GHz top-of-band operating point.
- The control arm's dual-lock success is itself a new datum for this bench
  family: RECORD-005 quoted 8.203 % static phase error and RECORD-001's
  control arm 8.31 % — both above the 5 % criterion — at 20 MHz / band `11`
  with the pre-DR-010 `cp`; here the control arm settles at 1.74 % and holds
  the dual-lock criterion for 92 cycles. This is NOT an isolated `cp` A/B:
  `f_ref`, band, Kvco and the `cp` all moved together. It is consistent with
  the DR-010 motivation (`cp-dumpbuf` charge-sharing fix) but does not by
  itself attribute the improvement.
- Row 7 (lock time) remains gated on real blocks (R-2). The control arm's
  213 ns acquisition is a behavioural-divider number, not a row-7 claim; the
  real arm's number, if any, is nominal-only.
- Does not establish: any PVT behaviour; post-layout behaviour; the top of
  band (band `00` ceiling 910.98 MHz untested; 9.375 MHz x N = 127 untested);
  the row 6/6a loop-bandwidth / phase-margin criteria — NOT re-verified at
  this (band, `f_ref`) tuple: both `f_ref` and Kvco moved, the Icp trim
  table was not re-selected, and the deck still drives the bias inputs with
  an ideal 10 uA `IREF` (S3), not any trim code. `lock_detector` behaviour
  (S5: not instantiated) remains unmeasured. No spec row is touched.

## Reproduce

```
cd testbench
# control arm — 957 s wall, 2 threads, this host
PDK_ROOT=<root> PDK=ihp-sg13cmos5l TAG_SUFFIX=_o2 CP_SNAP=cp-dr010.spice \
  FREF_OVERRIDE=9.375e6 B0V_OVERRIDE=0 B1V_OVERRIDE=0 VC0_OVERRIDE=1.23 \
  TSTOP_OVERRIDE=10u TAVG0_OVERRIDE=8u NGSPICE_TIMEOUT=3600 ./run.sh control
# real arm — 2376 s wall
PDK_ROOT=<root> PDK=ihp-sg13cmos5l TAG_SUFFIX=_o2 CP_SNAP=cp-dr010.spice \
  FREF_OVERRIDE=9.375e6 B0V_OVERRIDE=0 B1V_OVERRIDE=0 VC0_OVERRIDE=1.23 \
  TSTOP_OVERRIDE=10u TAVG0_OVERRIDE=8u NGSPICE_TIMEOUT=5400 ./run.sh real
# ideal-clock diagnostic at the same frequency — 182 s
PDK_ROOT=<root> PDK=ihp-sg13cmos5l TSTOP_OVERRIDE=900n ./run_div_speed.sh 6e8
```

`run.sh` without the overrides reproduces RECORD-001's point; never run it
bare (empty `TAG_SUFFIX` overwrites RECORD-001's committed `corners/`
artifacts — see the `run.sh` header).
