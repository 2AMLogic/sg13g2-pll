# Roadmap — sg13g2-pll

An integer-N charge-pump PLL ported to IHP SG13G2 and SG13CMOS5L with open tools, kept as a
forcing function for the klayout-tools decks and flow on those PDKs.

Status as of 2026-11-13, `main` @ `3169bad0`. Verified against that tree and the tracker as
read the same day. The verdict of record stays in [`manifests/README.md`](../manifests/README.md)
and the [tier report](../manifests/sg13g2-pll.tier-report.json); `WORK_PLAN.md` stays the
generated label-state view. This file says what comes next and why.

## Where it stands

Tier report: `tier: null`, **14 of 22 T1 items met** (11 items x analog and digital partition),
graded by `klt signoff` 0.8.0 and byte-compared in CI (`.github/workflows/signoff.yml`).
Tracker: [#6](https://github.com/2AMLogic/sg13g2-pll/issues/6).

| T1 item | Analog | Digital | State behind it |
|---|---|---|---|
| 1 Design sources | met | met | attested envelope, `manifests/inventories/item-1.envelope.json` |
| 2 Layout | met | met | SG13CMOS5L record `20261010-012952-a4ca1b8`, six composed blocks |
| 3 DRC clean | met | met | curated `sg13cmos5l` deck; coverage gaps disclosed in `manifests/README.md` |
| 4 LVS clean | met | met | six blocks `match`; no chip-level top exists (DR-004) |
| 5 Corners vs ratified spec | unmet | unmet | `spec/target-spec.md` is DRAFT; no ratified table to grade against |
| 6 Monte Carlo | unmet | unmet | analog: 1500-sample `cp` campaign cited, `undersized_sample`; digital: no statistical row, uncited |
| 7 Post-layout | met | met | `sim/sg13cmos5l-klt-pex-signoff`; `lock_detector` withheld (#157) |
| 8 Characterization report | unmet | unmet | `characterization/SUMMARY.md` exists, deliberately not cited |
| 9 Testbenches shipped | unmet | unmet | `check_testbench_coverage.py`: 37 grandfathered records, 8 still unresolved |
| 10 Repo hygiene | met | met | attested envelope |
| 11 Power delivery | met | met | `klt erc` supply-spec records |

Design facts that shape the plan, each from a committed record:

- **The closed loop does not yet acquire on the real blocks.** With the transistor-level
  `divider_chain` in the loop the N=64 nominal run does not lock: the divider miscounts at the
  VCO frequency the loop needs (`sim/sg13cmos5l-closed-loop-real-divider` RECORD-001). Rows 7,
  10, 11 and half of 16 are open on this one gate (target-spec R-2).
- **Row 3 retiming closure is unmet at the 1562 MHz top of band**; width sizing alone does not
  close it (DR-012, proposed). **Row 13 duty cycle** misses 45 to 55 % at -40 C (R-8; PR #354).
- **`cp` mismatch**: the `+/-3.5 %` screening limit is retired (PR #390, DR-013 proposed).
- **Item 9** is down to 8 unresolved records after the batch-rerun campaign: `cp-icp-trim`
  RECORD-003/004, `loop-bandwidth-pm` RECORD-001 to 004 (five files), `vco-decap-momcap` RECORD-001.
- The spec has 17 rows: 6 measured, 3 proposed, 2 not specified, 7 open; of the fifteen decision
  records only DR-004 and DR-006 (lock-detector threshold) are ratified.

## In flight (open pull requests)

| PR | Issue | What | State |
|---|---|---|---|
| #394 | #391 | CI gate for two testbench metric self-tests | in review |
| #377 | #376 | split the SG13CMOS5L record renderer | approved |
| #375 | #319 | item 9: supersede `loop-bandwidth-pm` RECORD-001/002/002b | changes requested |
| #335 | #330 | RECORD-007: fast/slow PM anchor offset traced to PDK `cornerRES` drift | in review, held |
| #332 | #203 | RECORD-006: fast/slow PM with the real `cp` on VCTRL | CI failing, held for a maintainer |
| #354 | #188 | narrow the `vco` output-buffer PMOS for row 13 | CI failing, held for a maintainer |
| #304 | #301 | DR for a 50 MHz reference, trip band and LOCK polarity | approved, held for a human merge |

## Now

Startable today, but none is ready by label: items 1 to 3 need triage or approval (#389 and
#393 still carry a blocked label whose cited blocker closed) and items 4 to 7 need an issue.

1. **Re-extract `lock_detector` PEX from the current GDS** (#157). Done when a `klt pex`
   envelope for the post-#136 layout is committed with its `body_bias` block recorded.
2. **Proposal deck does not acquire at 125 C; `cp` campaign has no negative control** (#389).
   Done when a record states why the 125 C run rails VCTRL and the Monte Carlo report declares
   a negative control. The issue covers two things and should be split.
3. **Guard `package.json`'s gate chain against drift from the workflows** (#393). Done when a
   stdlib test fails if the two lists disagree.
4. **Real-divider closed loop at a lower VCO frequency** (no issue). RECORD-001 names this as
   untested. Done when a new record in `sim/sg13cmos5l-closed-loop-real-divider` reports lock
   or no-lock, with the divide ratio per FB period, at an operating point inside the divider's
   measured exact-N range, using the committed DR-010 `cp`.
5. **Divider maximum input frequency across corners** (no issue; the "Divider speed evidence"
   gap in `characterization/SUMMARY.md` has no tracker). Done when a record resolves the
   640 MHz to 1.28 GHz bracket per corner and the summary selects it.
6. **Reference-input threshold bench for `pfd`** (no issue; R-5 says no such bench exists).
   Done when a record gives the input switching threshold across the operating box.
7. **Refresh stale claim text** (no issue). `manifests/README.md` item 6 and the item-8
   requirement list, and the summary's gap table, still describe the `+/-3.5 %` limit as live
   and cite #139 and #178 as open trackers. Done when the text matches DR-013 and RECORD-003
   and every cited tracker is open, with the tier report byte-identical.

## Next

- **Render the two-layer probe result honestly** (#381): after PR #377 merges.
- **Joint R1/C1/C2 retune to close DR-008 `fast`** (#334): after RECORD-006 and RECORD-007 land
  (PRs #332, #335). Done when a new decision record states the values and row 6a holds at
  fast, typ and slow on the current PDK tree.
- **`lock_detector` rework for 50 MHz, then the full-PVT bench** (#302, then #303): after the
  DR in PR #304 merges. Parent: #296.
- **Finish item 9** (#320, #231, #316, then #218): done when the coverage gate prints zero
  unresolved records and item 9 is cited. #320 and #231 wait on the pin question below.
- **`vco` layout redraw and PEX refresh** (#356): after PR #354 merges.
- **Regenerate the SG13CMOS5L netlists** (#309, `mm_ok=1` drift): after the pin question.

## Later

- **Ratify the spec** (two-key, `ratification/`; not agent work). Unlocks items 5, 6 (digital,
  as not applicable) and 8, and the Chipalooza Challenge #6 bar (#16) sits behind the same
  evidence. First: rulings R-0 to R-12 in `spec/target-spec.md`; no tracking issue exists.
- **Row 3 at top of band.** First: is there a structural alternative to the retiming flop
  that closes at 1562 MHz, or is a lower top-of-band accepted (R-3, DR-012)?
- **Which VCO band the spec binds to.** First: does the post-layout band stand after a
  considered `vco` route, and does DR-005 need a superseding record (R-1)?
- **A `pll_top` or wrapper.** First: what the wrapper's I/O boundary is (DR-004). Row 15
  (area) and any chip-level DRC, LVS or power total need it.
- **Rows 8 and 12 (jitter, supply sensitivity).** First: a transient-noise or ISF method for
  the ring in ngspice, or a ruling that the rows stay unspecified like row 9 (R-7).
- **Item 6 to `met`.** First: whether a `cp` mismatch limit must exist at all and which row
  owns it (R-12); a larger sample alone would grade against nothing.
- **The SG13G2 (BiCMOS) target.** `layout/pll/` composes but its README states it is not
  DRC-clean or LVS-clean, and its sim evidence is five `sim/sg13g2-*` benches. First: whether this target is
  carried to the same evidence as the port, and whether the deferred HBT options (DR-002,
  DR-009) are exercised.

## Blocked and waiting

- **PDK pin re-stamp, #250.** `sim/README.md` pins `ihp-sg13cmos5l` at `607e18d4`; the
  klayout-tools fetch script moved to IHP-Open-PDK `f7bca326`. #320 and #231 are parked on #250 while
  #250 is parked on their campaigns (#214, #212, #218), a dependency cycle recorded on the
  issue that needs a maintainer decision on which side moves first.
- **Maintainer holds:** PRs #304, #332, #354; issues #316 and #384 (collapse `run_rerun256.sh`
  into a wrapper).

## Not planned

- An LC-tank VCO (rejected for v1 in DR-001), a power-down mode (row 17, waived) and an
  integrated phase-noise number (row 9, not specified).
- Relaxing any spec row to match a result. Unmet rows stay visible until redesigned or ruled on.
- Silicon measurements: `measurements/` stays empty.
