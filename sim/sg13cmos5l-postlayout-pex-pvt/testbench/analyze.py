#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/analyze.py
(issue #30, Part of #16 -- post-layout PEX + PVT re-simulation)

Turns ../corners/results.csv (both arms, 120 rows) into the two derived
artifacts ../records/RECORD-001 cites:

  ../corners/deviation.csv   per (bundle, band, VCTRL) point: the schematic
                             control frequency, the post-layout frequency,
                             and the post-layout/schematic ratio
  ../corners/control.csv     the schematic arm re-run HERE vs. the committed
                             ../../sg13cmos5l-vco-kvco-table/corners/
                             results.csv, so the claim "the control arm
                             reproduces the original campaign" is a checked
                             number and not an assertion

Also prints a per-bundle and per-band roll-up to stdout, which is what the
record's own tables are transcribed from.

Usage:  ./analyze.py            (paths are resolved relative to this file)
"""

from __future__ import annotations

import csv
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD_DIR = os.path.dirname(HERE)
SIM_ROOT = os.path.dirname(RECORD_DIR)

RESULTS = os.path.join(RECORD_DIR, "corners", "results.csv")
COMMITTED = os.path.join(
    SIM_ROOT, "sg13cmos5l-vco-kvco-table", "corners", "results.csv"
)
DEVIATION = os.path.join(RECORD_DIR, "corners", "deviation.csv")
CONTROL = os.path.join(RECORD_DIR, "corners", "control.csv")

KEY = ("pvt_bundle", "band_code", "vctrl_v")


def _key(row: dict) -> tuple:
    return tuple(row[k] for k in KEY)


def _f(v: str) -> float | None:
    return None if v == "NA" else float(v)


def main() -> int:
    rows = list(csv.DictReader(open(RESULTS)))
    post = {_key(r): r for r in rows if r["arm"] == "postlayout"}
    sch = {_key(r): r for r in rows if r["arm"] == "schematic"}

    if set(post) != set(sch):
        sys.exit(
            "FATAL: the two arms do not cover the same points -- "
            "postlayout-only %s, schematic-only %s"
            % (sorted(set(post) - set(sch)), sorted(set(sch) - set(post)))
        )

    # --- deviation: post-layout vs. its own schematic control ---------------
    ratios = []
    with open(DEVIATION, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "pvt_bundle", "mos_corner", "res_corner", "temp_c",
                "band_code", "vctrl_v",
                "freq_hz_schematic", "freq_hz_postlayout",
                "ratio_post_over_sch", "delta_pct",
            ]
        )
        for k in sorted(post, key=lambda t: (t[0], t[1], float(t[2]))):
            p, s = post[k], sch[k]
            fp, fs = _f(p["freq_hz"]), _f(s["freq_hz"])
            if fp is None or fs is None:
                w.writerow(
                    [p["pvt_bundle"], p["mos_corner"], p["res_corner"],
                     p["temp_c"], p["band_code"], p["vctrl_v"],
                     s["freq_hz"], p["freq_hz"], "NA", "NA"]
                )
                continue
            ratio = fp / fs
            ratios.append((k, ratio))
            w.writerow(
                [p["pvt_bundle"], p["mos_corner"], p["res_corner"],
                 p["temp_c"], p["band_code"], p["vctrl_v"],
                 "%.6g" % fs, "%.6g" % fp, "%.6f" % ratio,
                 "%+.3f" % ((ratio - 1.0) * 100.0)]
            )

    # --- control: this session's schematic arm vs. the committed campaign ---
    committed = {}
    for r in csv.DictReader(open(COMMITTED)):
        committed[(r["pvt_bundle"], r["band_code"], r["vctrl_v"])] = r

    control_dev = []
    with open(CONTROL, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "pvt_bundle", "band_code", "vctrl_v",
                "freq_hz_committed", "freq_hz_control_rerun",
                "ratio_rerun_over_committed", "delta_pct",
            ]
        )
        for k in sorted(sch, key=lambda t: (t[0], t[1], float(t[2]))):
            c = committed.get(k)
            s = sch[k]
            if c is None:
                w.writerow([k[0], k[1], k[2], "MISSING", s["freq_hz"], "NA", "NA"])
                continue
            fc, fs = _f(c["freq_hz"]), _f(s["freq_hz"])
            if fc is None or fs is None:
                w.writerow([k[0], k[1], k[2], c["freq_hz"], s["freq_hz"], "NA", "NA"])
                continue
            ratio = fs / fc
            control_dev.append(abs(ratio - 1.0) * 100.0)
            w.writerow(
                [k[0], k[1], k[2], "%.6g" % fc, "%.6g" % fs,
                 "%.9f" % ratio, "%+.6f" % ((ratio - 1.0) * 100.0)]
            )

    # --- roll-up ------------------------------------------------------------
    def stats(vals):
        return min(vals), statistics.mean(vals), max(vals)

    all_r = [r for _, r in ratios]
    lo, mean, hi = stats(all_r)
    print("post-layout / schematic frequency ratio over %d points:" % len(all_r))
    print("  min %.4f (%+.2f%%)  mean %.4f (%+.2f%%)  max %.4f (%+.2f%%)"
          % (lo, (lo - 1) * 100, mean, (mean - 1) * 100, hi, (hi - 1) * 100))

    for axis, idx in (("bundle", 0), ("band", 1), ("VCTRL", 2)):
        print("\nby %s:" % axis)
        vals = sorted({k[idx] for k, _ in ratios},
                      key=lambda v: float(v) if idx == 2 else v)
        for v in vals:
            sel = [r for k, r in ratios if k[idx] == v]
            lo, mean, hi = stats(sel)
            print("  %-6s n=%2d  min %+.2f%%  mean %+.2f%%  max %+.2f%%"
                  % (v, len(sel), (lo - 1) * 100, (mean - 1) * 100, (hi - 1) * 100))

    if control_dev:
        print("\ncontrol arm vs. committed sg13cmos5l-vco-kvco-table, %d points:"
              % len(control_dev))
        print("  max |delta| = %.6f%%   (0.000000%% means byte-identical)"
              % max(control_dev))
        exact = sum(1 for d in control_dev if d == 0.0)
        print("  %d/%d points reproduce the committed frequency exactly"
              % (exact, len(control_dev)))

    print("\nwrote %s\nwrote %s" % (DEVIATION, CONTROL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
