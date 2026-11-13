# PVT matrix — `sg13cmos5l-closed-loop-lock`

## Why a single PVT point, not the full matrix

Every sibling SG13CMOS5L record in this campaign (`sg13cmos5l-cp-icp-trim`,
`sg13cmos5l-loop-bandwidth-pm`, `sg13cmos5l-vco-duty-cycle`, ...) sweeps a
multi-corner matrix because each of those decks is small enough (a single
block, or a handful of real subckts driven by ideal sources) to run a few
hundred times in a reasonable wall-clock budget. This record's DUT is not
that: it is the **full six-block hierarchy** (`pfd` + `cp` + `loop_filter` +
`vco` + `divider_chain` + `lock_detector`), and the transient it needs to
resolve is a **closed-loop lock transient**, not an open-loop or DC sweep.

Measured directly on this host (arm64 macOS, `ngspice-47`): a 200 ns
transient of this six-block netlist (`tb_pll_closed.sp.tmpl`, `TMAX=100p`)
took **~199 s wall** (≈1 ns/s) — consistent with, and worse than, issue
#37's own runtime warning ("budget for two to three orders of magnitude more
simulated time on a netlist several times larger" than the ~40 ns/~2 s
single-VCO transient `sg13cmos5l-vco-duty-cycle` measured). At that measured
rate, this record's own two decks (500 ns as-drawn + 2.5 µs proposal, see
`../records/RECORD-001` "Why these durations") cost **~8 minutes and ~42
minutes respectively, at ONE PVT point** — confirmed directly (not just
extrapolated): the full `./testbench/run.sh` run this record's numbers come
from took ~50 minutes wall end-to-end. A 15-, 45-, or 90-point PVT sweep of
this specific testbench is not a reasonable ask within one build session on
this hardware.

**This record therefore runs ONE PVT point** — `mos_tt` / `res_typ` / 27 C /
3.3 V ("typ", the same nominal bundle every sibling record's own "typ"
label names) — for both Part A (as-drawn) and Part B (proposal), and states
that explicitly as the subset reason `sim/README.md`'s own convention
requires rather than silently dropping the PVT axes. This is consistent with
the deferred-rows table's own framing of #37 ("PVT-cornered or with an
explicit subset reason") — the reason here is a measured, stated runtime
constraint, not a shortcut.

## Operating point (shared by both decks)

| Parameter | Value | Source |
|---|---|---|
| `f_ref` | 20 MHz | Inside DR-005's amended range (3.51–24.4 MHz); chosen near the ceiling so the as-drawn `f_c` values (`sg13cmos5l-loop-bandwidth-pm`, 0.33–4.64 MHz) and the R1×20 proposal's `f_c` (~1.5–1.8 MHz) both sit comfortably under `f_ref`/10 |
| `N` | 64 (`P5..P0 = 000000`) | The divider chain's own structural floor (DR-005), all cells ÷2 |
| `f_out` target | 1280 MHz | `f_ref × N`; inside the VCO's measured `typ`/band-`11` range (1161.9–1359.1 MHz at `VCTRL` 2.1–2.7 V) |
| VCO band code | `11` (`B0=B1=VDD`) | Reaches 1280 MHz without needing `VCTRL` outside the swept 0.3–2.7 V range |
| `VC0` (initial `VCTRL`) | 2.46 V | Secant interpolation of the measured `typ`/band-`11` table for 1280 MHz — an initial condition, not a locked-value claim |
| Icp trim code | 10 µA | Same code `sg13cmos5l-cp-icp-trim`/`sg13cmos5l-vco-duty-cycle` report `vdd_vco`/`cp` current at |
| Supply | 3.3 V per domain (`vdd_pfd`/`vdd_cp`/`vdd_vco`/`vdd_div`/`vdd_ld`, ideal sources) | Nominal; row 11 measures domain current at one consistent operating point, not a supply sweep |

## What is NOT swept, and why

- **Process/temperature/supply corners** — runtime, see above.
- **MOM-cap uncertainty band** (`sg13cmos5l-loop-filter-momcap`'s own ±20%
  axis) — this record's `loop_filter` C1/C2 are already ideal-capacitor
  substitutions at the *nominal* MOM point (see `testbench/run.sh`'s own
  "OSDI host constraint" header); layering a MOM-uncertainty sweep on top of
  a value that is itself a host-forced substitution would compound two
  approximations without adding real information.
- **Icp trim code** — fixed at 10 µA (see above), not swept; that axis is
  already closed by `sg13cmos5l-cp-icp-trim` and `sg13cmos5l-loop-bandwidth-pm`.

## The RECORD-014 mismatch-gain grid (issue #385) — a THREE-temperature subset

`../records/RECORD-014-cp-mismatch-phase-error-gain.md` is the first record
in this slug that leaves 27 C. It sweeps a different axis from the two decks
above (injected `cp` DC up/dn mismatch) and declares its own matrix here.

| Axis | Swept | Reason |
|---|---|---|
| **Mismatch (the axis under test)** | 6 points, `mismatch_pct` -11.998 to +12.009 % (+/-3.1 sigma of `../../sg13cmos5l-cp-icp-trim-mc`'s measured 3.8769 % sigma), plus a 7th that was lost to a `batch_poll_timeout` (`mm_n4`, about -4 %, **not collected**, not failed) | injected by scaling the two cascode mirror devices of `.subckt cp_leg_p` by one factor `k`; `k` = 1 is the committed snapshot byte for byte |
| **Temperature** | **-40 / 27 / 125 C** | `../../sg13cmos5l-cp-icp-trim-mc/records/RECORD-002` reports that **temperature**, not process, dominates the mismatch spread (sigma 3.08-3.45 % at 125 C against 3.96-4.77 % at -40 C), so it is the axis this gain is most likely to move along |
| **Process** | `mos_tt` only | The quantity is a *gain*, not a worst-case bound, and the mismatch here is deliberate rather than drawn, so a process-section sweep would measure the deck's own corner spread rather than the sensitivity under test. Not run. |
| **Resistor corner** | `res_typ` only | follows the process decision; `loop_filter`'s `R1` is the only resistor and is already a x20 proposal-deck substitution |
| **Supply** | 3.3 V only | as every deck in this slug; row 18's +/-10 % axis is exercised on `cp` alone by `../../sg13cmos5l-cp-icp-trim`. Not run. |
| **`f_ref` / `N` / band / `VC0` / Icp trim** | fixed at the operating point above | unchanged from the two decks above, so RECORD-014's numbers are directly comparable with RECORD-007's |

Running the grid was affordable only because it went to the **Spot batch
fleet** as `klt sim` requests (one per mismatch point, three temperature
units each) rather than onto this host: 21 closed-loop transients at the
~8 min each the section above measures would be about 2.8 hours serial here,
against 10 to 17 min wall per fleet job with four in flight.

**125 C did not acquire lock at any mismatch point, including the
unperturbed one** (`vctrl` rails at 3.289 V). Those points are reported in
RECORD-014 and in `mismatch_gain.csv` with `dual_lock=0` and are excluded
from every fit, so the gain is established at **two** of the three
temperatures run. That is a property of this proposal deck, not of the
committed `cp`, and it is filed as issue #389.
