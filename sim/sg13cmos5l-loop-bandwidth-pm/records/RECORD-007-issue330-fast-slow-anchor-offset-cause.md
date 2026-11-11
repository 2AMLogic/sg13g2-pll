# RECORD-007: why the C_cp = 0 anchor does not reproduce RECORD-003/004 at `fast` / `slow` (issue #330)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #330 (Part of #16). Follows `RECORD-006` (#203, PR #332).
- **Append-only.** No earlier record, template, script, request, snapshot,
  report or corners file is edited. New artifacts only:
  `../reports/issue330/ab/` (decks, logs, `.dat`, `run_ab.sh`,
  `run_pdk_ab.sh`, `pm.py`).
- **Runs**: nine single-unit local `ngspice -b` runs (`ngspice-46`, one corner
  each, sequential). No grid, no batch submit, no re-run of the RECORD-006 jobs
  `klt-sim-eac8c7058128` / `klt-sim-305db5c52616`.
- **Reduction**: `pm.py` interpolates the |T| = 1 crossing (log-f, log-|T|) of
  `wrdata` output; PM = 180 deg + phase there. At the committed
  `fast` input it returns the same 44.345 deg `klt` measured.

## Cause

**The PDK tree changed between RECORD-004 and RECORD-006.** The
`ihp-sg13cmos5l` checkout in `/home/ubuntu/share/pdk` was replaced on
2026-10-15 (the previous tree survives as
`ihp-sg13cmos5l.bak-20261015T153636Z`, git `607e18d4`, 2026-08-25;
`RECORD-004` was committed 2026-08-30). `cornerRES.lib` changed in the
`res_bcs` / `res_wcs` sections:

| | previous tree | current tree |
|---|---|---|
| `res_bcs` `rsh_rhigh` / `dw_rppd_par` | 1020 / (not defined) | 1160 / **+0.03e-6** |
| `res_wcs` `rsh_rhigh` / `dw_rppd_par` | 1700 / (not defined) | 1560 / **-0.03e-6** |
| `res_typ` | `res_area = res_rpara = 1.0` | all `d*` params 0.0 |
| `cornerRES.lib` sha256 (first 16) | `2c18502104146804` | `c6d749e72cfa2e06` |
| `resistors_mod.lib` sha256 (first 16) | `c2329110bcb66894` | `7c77da0c0419c8a3` |
| `r3_cmc.osdi` sha256 (first 16) | `4fead17bc2e9cbfe` | `746f86fd1b89c309` |

The current `res_bcs` / `res_wcs` apply a +/-0.03 um width bias to `rppd`, and
the filter's R1 is `rppd w=0.6u` (DR-006), so the bias is +/-5 % of its width.
`res_typ` carries no bias, which is why `typ` reproduced and `fast`/`slow` did
not. The current-tree `cornerRES.lib` hash is the one RECORD-006's own report
lists under `environment.corner_section_libs`
(`c6d749e72cfa2e06...`), so the batch runner used the current tree, as the
client did. Not klt, not the section/temperature mechanism, not the bench.

## Evidence

### A/B on DR-008 `fast` (-40 C), current PDK, one corner each

All three use `tb_loop_ac_real_resized.sp.tmpl` with the inputs the klt request
already carries for `dr008_fast_nocp`
(Kd 1.750782e-6, Kv 4.619851e8, 1/N 0.0078740157; these equal
Icp/2pi, 2pi*Kvco, 1/127 from `RECORD-004`'s row, so the operating-point feed
is not the cause).

| Variant | Deck difference vs original | f_c (Hz) | PM (deg) |
|---|---|---|---|
| A `orig` | original template: `cornerRES res_bcs`, `.option temp=-40` | 3.628450e5 | 44.345 |
| B `mosff` | A plus `.lib cornerMOShv.lib mos_ff` (what the klt request adds) | 3.628450e5 | 44.345 |
| C `mosff_dottemp` | B with `.temp -40` instead of `.option temp` | 3.628450e5 | 44.345 |

`diff tb_A_orig.sp tb_B_mosff.sp` shows only the added `.lib` line. The
`mos_ff` section, the temperature mechanism and the cap-model include are
ruled out: the original deck already gives the klt number on the current PDK.

### Anchor on the previous vs current PDK tree (three tuples, original deck)

| Tuple | Corner | Committed PM | Previous tree PM / f_c | Current tree PM / f_c | Committed f_c |
|---|---|---|---|---|---|
| DR-008 band 00 / low | `fast`, res_bcs, -40 C | 45.592 | **45.592** / 3.686111e5 | 44.345 / 3.628450e5 | 3.686111e5 |
| DR-008 band 00 / low | `slow`, res_wcs, 125 C | 53.454 | **53.454** / 4.352370e5 | 54.953 / 4.519307e5 | 4.352370e5 |
| DR-007 band 00 / mid | `slow`, res_wcs, 125 C | 49.973 | **49.973** / 3.592385e5 | 51.751 / 3.711725e5 | 3.592385e5 |

On the previous tree all three PM *and* f_c values equal the committed
`RECORD-003`/`004` values to every printed digit. On the current tree they equal
`RECORD-006`'s anchors (44.345, 54.953, 51.751).

### Gate (`RECORD-005`: the C_cp = 0 anchor "must reproduce" the committed PM)

The anchor reproduces the committed PM exactly (difference 0.000 deg, to the
3 decimals the committed CSVs carry) at all three tuples when the previous PDK
tree is used. On the current tree it does not (-1.247, +1.499, +1.778 deg).
So the bench is sound; the committed `RECORD-003`/`004` numbers are the ones
that are stale against the PDK now in use.

## Verdict, stated against the PDK in use now

`RECORD-006` already measured the real-cp PM on the **current** tree, and the
cause above is the PDK, not the bench, so those numbers stand and no re-run was
needed (nothing in the bench changed):

| Tuple | Corner | Anchor, no cp | PM with real cp, own / full range | Row 6a (>= 45 deg) |
|---|---|---|---|---|
| DR-008 band 00 / low | `fast`, -40 C | 44.345 | 43.788 / 43.648 | **fails**, and fails with no cp at all |
| DR-008 band 00 / low | `slow`, 125 C | 54.953 | 54.116 / 53.916 | passes |
| DR-007 band 00 / mid | `slow`, 125 C | 51.751 | 51.158 / 50.880 | passes |

Under the previous tree DR-008 `fast` passed (45.592 anchor; about 45.0 / 44.9
with the cp's measured -0.56 / -0.70 deg, a projection, not a run, and
borderline). Under the current tree the anchor itself is 0.655 deg below the
floor, so **DR-008 `fast` fails row 6a on the PDK now in use**. Neither tree is
claimed here to be the "right" silicon model; the current one is what the fleet
resolves today.

### Which of the three closures could work (arithmetic on measured numbers)

The issue lists: fine-trim recentre, joint R1/C1/C2 retune, lower cp VOUT
capacitance.

- **Lower cp VOUT capacitance** cannot close it: with the cp removed entirely
  the `fast` anchor is 44.345 deg, still below 45. Best case recovers only the
  cp's own 0.56-0.70 deg.
- **Fine-trim recentre** cannot close it by itself: on the current tree the
  `slow` anchor f_c is already 451.93 kHz at 11 uA, above the 450 kHz ceiling
  (449.4 kHz with the cp). `fast` needs more Icp for PM, `slow` needs less for
  f_c. Extrapolating `RECORD-004`'s ~1.5 deg/uA `fast` slope (previous tree)
  to the 0.655 deg deficit gives roughly +0.45 uA, about +4 % Icp and about +4 %
  `slow` f_c, past the ceiling. That slope is extrapolated from an older tree,
  not measured.
- **Joint R1/C1/C2 retune** is the only remaining option, but picking its values
  needs a verified scan on the current tree across all (band, interval, f_ref)
  tuples. That is a batch grid and is not done here.

## Closure decision record: not written

No `DR-0NN` is added. The elimination above leaves one family of fixes, but a
decision record has to state the values design can lock to, and none were
measured here. Writing a DR that picks a retune without a scan would be a claim
without a testbench. DR-007, DR-008 and spec row 6a are unchanged. The retune
scan and its DR are tracked in #334.

## klt friction

No klt issue is filed. The cause is PDK content drift, not klt behaviour: klt
applied the sections correctly (variants A/B/C agree) and its report already
carries the `cornerRES.lib` hash that distinguishes the two trees.

## Not covered

- The joint R1/C1/C2 retune scan and its decision record (#334).
- Layout parasitics (PEX); supply, mismatch, the #139 lock-detector grid.
- Whether `RECORD-001`..`004`'s other tuples shift on the current tree (only the
  three tuples `RECORD-006` measured were checked).
