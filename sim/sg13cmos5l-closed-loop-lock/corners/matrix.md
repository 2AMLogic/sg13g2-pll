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
