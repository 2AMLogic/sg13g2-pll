#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/analyze_pfd_ld.py
(issue #102, Part of #16 -- post-layout PEX arms for pfd and lock_detector)

The RECORD-003 roll-up -- the counterpart RECORD-001's analyze.py was for its
own matrices (this file deliberately does NOT touch analyze.py or any of
RECORD-001's CSVs):

  * consumes ../corners/pfd_results.csv, ../corners/pfd_control.csv,
    ../corners/ld_window.csv, ../corners/ld_ladder.csv,
    ../corners/ld_tstep_convergence.csv and the sibling campaigns'
    committed rows;
  * writes ../corners/ld_deviation.csv (the per-PVT-point whole-cell window
    postlayout-vs-aslayout deviation, the interconnect-isolating A/B);
  * prints every headline number the record quotes (pfd duty deltas per
    offset, the window deviation band, the missing-cap window collapse vs
    the committed crowbarfix design, the ladder row-16 criteria per arm,
    the supply-current deltas, the control-reproduction tallies).

Usage:  python3 analyze_pfd_ld.py
"""

from __future__ import annotations

import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
CORNERS = os.path.normpath(os.path.join(_HERE, "..", "corners"))
CAMPAIGN_LD = os.path.normpath(os.path.join(
    _HERE, "..", "..", "sg13cmos5l-lock-detector-window", "corners"))


def read_csv(name):
    with open(os.path.join(CORNERS, name)) as fh:
        return list(csv.DictReader(fh))


def pct(new, old):
    return 100.0 * (float(new) - float(old)) / float(old)


def main() -> int:
    print("== pfd: post-layout duty-space deviation per offset (ratified point = 5e-9)")
    pfdr = read_csv("pfd_results.csv")
    for case in ("reflead", "fblead"):
        for off in ("5e-9", "10e-9", "20e-9"):
            try:
                sch = [r for r in pfdr if r["arm"] == "schematic"
                       and r["case"] == case and r["offset_s"] == off][0]
                pex = [r for r in pfdr if r["arm"] == "postlayout"
                       and r["case"] == case and r["offset_s"] == off][0]
            except IndexError:
                continue
            print("  %-8s off=%-6s sch up/dn %-7s %-7s | pex up/dn %-7s %-7s "
                  "| up duty %+.1f%% dn duty %s"
                  % (case, off,
                     sch["up_duty_frac"], sch["dn_duty_frac"],
                     pex["up_duty_frac"], pex["dn_duty_frac"],
                     pct(pex["up_duty_frac"], sch["up_duty_frac"]),
                     ("%+.1f%%" % pct(pex["dn_duty_frac"], sch["dn_duty_frac"]))
                     if float(sch["dn_duty_frac"]) else "NA"))

    print("== pfd: schematic control arm vs committed pfd_polarity_diag.csv (fixed rows)")
    for r in read_csv("pfd_control.csv"):
        print("  %-8s committed up/dn %-9s %-9s this host %-9s %-9s "
              "delta %+.4f / %+.4f V"
              % (r["case"], r["committed_fixed_up_avg_v"],
                 r["committed_fixed_dn_avg_v"], r["this_host_sch_up_avg_v"],
                 r["this_host_sch_dn_avg_v"], float(r["delta_up_avg_v"]),
                 float(r["delta_dn_avg_v"])))

    print("== lock_detector: window A/B (whole-cell), postlayout vs aslayout")
    win = read_csv("ld_window.csv")
    sch = {(r["mos_corner"], r["res_corner"], r["temp_c"], r["vsup_v"]): r
           for r in win if r["arm"] == "aslayout" and r["deck"] == "wholecell"}
    pex = {(r["mos_corner"], r["res_corner"], r["temp_c"], r["vsup_v"]): r
           for r in win if r["arm"] == "postlayout" and r["deck"] == "wholecell"}
    diffs = []
    with open(os.path.join(CORNERS, "ld_deviation.csv"), "w") as fh:
        w = csv.writer(fh)
        w.writerow(["mos_corner", "res_corner", "temp_c", "vsup_v",
                    "sch_wholecell_twin_r_s", "postlayout_wholecell_twin_r_s",
                    "twin_r_s_delta", "twin_r_delta_pct"])
        for k in sorted(sch):
            if k not in pex:
                continue
            s, p = (float(sch[k]["twin_r_s"]), float(pex[k]["twin_r_s"]))
            d = pct(p, s)
            diffs.append(d)
            w.writerow([k[0], k[1], k[2], k[3], sch[k]["twin_r_s"],
                        pex[k]["twin_r_s"], "%.6e" % (p - s), "%.4f" % d])
    if diffs:
        print("  twin_r delta: min %+.2f%% mean %+.2f%% max %+.2f%% "
              "over %d PVT points (ld_deviation.csv)"
              % (min(diffs), sum(diffs) / len(diffs), max(diffs), len(diffs)))

    print("== lock_detector: the missing-cap window collapse vs the committed design")
    ctl = {}
    with open(os.path.join(CAMPAIGN_LD, "window_crowbarfix.csv")) as fh:
        for r in csv.DictReader(fh):
            if r["dut_variant"] == "real" and r["vsup_v"] == "3.3":
                ctl[(r["mos_corner"], r["res_corner"], r["temp_c"])] = \
                    float(r["twin_r_s"])
    bare = {(r["mos_corner"], r["res_corner"], r["temp_c"]): float(r["twin_r_s"])
            for r in win if r["arm"] == "aslayout" and r["deck"] == "bare"
            and r["vsup_v"] == "3.3"}
    ks = sorted(set(ctl) & set(bare))
    for k in ks:
        print("  %-18s crowbarfix twin_r %8.4g ns | as-layout bare %8.4g ns "
              "(%.1f%% of committed)"
              % ("/".join([k[0], k[1], k[2] + "C"]), ctl[k] * 1e9,
                 bare[k] * 1e9, 100.0 * bare[k] / ctl[k]))

    print("== lock_detector: ladder row-16 criteria per arm/corner")
    lad = read_csv("ld_ladder.csv")
    for r in lad:
        print("  %-44s rail %-10s assert %-6s deassert %-6s hyst %-8s "
              "chatter %-12s idd_in/out %-9s %-9s rc/Tref(wbasis) %s"
              % (r["corner_tag"], r["in_window_lock_rail"],
                 r["tau_assert_xwin"], r["tau_deassert_xwin"],
                 r["hysteresis_pct_of_window"], r["chatter"],
                 r["idd_inlock_a"], r["idd_outlock_a"],
                 r["rc_over_tref_on_cwin_basis"]))

    print("== lock_detector: timestep convergence (typ whole-cell window)")
    for r in read_csv("ld_tstep_convergence.csv"):
        print("  %-12s %-6s twin_r %s" % (r["arm"], r["tstep"], r["twin_r_s"]))

    print("== lock_detector: control reproduction tallies")
    d = read_csv("ld_window_control_delta.csv")
    nb = len([r for r in d if r["committed_twin_r_s"] != "NA"])
    ni = len([r for r in d if r["byte_identical"] == "yes"])
    print("  window_crowbarfix.csv: %d/%d byte-identical" % (ni, nb))
    rc = read_csv("ld_rc_control.csv")
    ni = len([r for r in rc if float(r["delta"]) == 0.0])
    print("  rc_extract_crowbarfix.csv: %d/%d byte-identical"
          % (ni, len(rc)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
