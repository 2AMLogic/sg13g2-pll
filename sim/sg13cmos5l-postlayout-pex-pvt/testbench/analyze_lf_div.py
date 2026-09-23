#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/analyze_lf_div.py
(issue #115, Part of #16 -- post-layout PEX arms for loop_filter and
divider_chain)

Roll-up for RECORD-004: every number the record quotes about Matrices F and
G comes from here, reading only the CSVs the two run scripts wrote
(lf_results.csv, lf_control.csv, div_results.csv, div_control.csv) plus the
committed campaign CSVs they deviate from. Nothing is re-simulated.

  ./analyze_lf_div.py            # prints every roll-up below

Outputs (stdout):
  loop_filter -- per-corner schematic-vs-postlayout r1/ctot/c2 ratios at
  mom_frac=0, the fz/fp band move at frac=0 per corner, the cap
  temperature-flatness spread per arm, and the control column's method
  deltas (min/max over the 27 committed rows).
  divider_chain -- per-point divide ratios for both arms, the post-layout
  ratio error vs its own schematic control (ppm), the idd move, the
  ck1..ck5 stage-liveness rails, and the control column's committed-vs-
  re-run agreement (max |ppm|, max idd %).
"""

from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORNERS = os.path.join(HERE, "..", "corners")


def read_csv(name):
    with open(os.path.join(CORNERS, name)) as fh:
        return list(csv.DictReader(fh))


def f(row, key):
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return float("nan")


def loop_filter():
    rows = read_csv("lf_results.csv")
    ctl = read_csv("lf_control.csv")
    print("=" * 72)
    print("Matrix F -- pll_loop_filter (driving-point AC, 27-row band)")
    print("=" * 72)

    print("\n-- control: schematic arm (this host, composite-AC method) vs")
    print("   the committed device-level results_resized.csv rows --")
    for col in ("r1_delta_pct", "c1_delta_pct", "c2_delta_pct",
                "fz_delta_pct", "fp_delta_pct"):
        vals = [f(r, col) for r in ctl]
        vals = [v for v in vals if v == v]
        print(f"   {col:14s} min {min(vals):+8.4f}%  max {max(vals):+8.4f}%"
              f"  over {len(vals)} rows")

    print("\n-- post-layout vs schematic control, mom_frac=0 --")
    print("   corner      temp   r1 sch->pex      ctot sch->pex"
          "     c2 sch->pex      fz sch->pex       fp sch->pex")
    by = {(r["arm"], r["res_corner"], int(r["temp_c"]), float(r["mom_frac"])): r
          for r in rows}
    for corner in ("res_typ", "res_bcs", "res_wcs"):
        for temp in (-40, 27, 125):
            s = by[("schematic", corner, temp, 0.0)]
            p = by[("postlayout", corner, temp, 0.0)]
            r1s, r1p = f(s, "r1_ohm"), f(p, "r1_ohm")
            cts, ctp = f(s, "ctot_f"), f(p, "ctot_f")
            c2s, c2p = f(s, "c2_f"), f(p, "c2_f")
            fzs, fzp = f(s, "fz_hz"), f(p, "fz_hz")
            fps, fpp = f(s, "fp_hz"), f(p, "fp_hz")
            print(f"   {corner:10s} {temp:4d}C  {r1s:9.3g}->{r1p:9.3g}"
                  f" ({(r1p/r1s-1)*100:+6.2f}%)"
                  f"  {cts:9.3g}->{ctp:9.3g} ({(ctp/cts-1)*100:+6.2f}%)"
                  f"  {c2s:9.3g}->{c2p:9.3g} ({(c2p/c2s-1)*100:+6.2f}%)")
            print(f"   {'':10s} {'':4s}   fz {fzs:9.3g}->{fzp:9.3g}"
                  f" ({(fzp/fzs-1)*100:+6.2f}%)"
                  f"   fp {fps:9.3g}->{fpp:9.3g} ({(fpp/fps-1)*100:+6.2f}%)")

    print("\n-- cap temperature-flatness per arm (frac=0, spread over")
    print("   -40/27/125 C as % of the 27C value) --")
    for arm in ("schematic", "postlayout"):
        for corner in ("res_typ",):
            v27 = f(by[(arm, corner, 27, 0.0)], "ctot_f")
            spread = max(abs(f(by[(arm, corner, t, 0.0)], "ctot_f") / v27 - 1)
                         for t in (-40, 27, 125))
            c227 = f(by[(arm, corner, 27, 0.0)], "c2_f")
            spread2 = max(abs(f(by[(arm, corner, t, 0.0)], "c2_f") / c227 - 1)
                          for t in (-40, 27, 125))
            print(f"   {arm:11s} ctot spread {spread*100:.4f}%"
                  f"   c2 spread {spread2*100:.4f}%")

    print("\n-- post-layout band extremes (frac=-0.20..+0.20, res_typ/27C) --")
    for arm in ("schematic", "postlayout"):
        sel = [by[(arm, "res_typ", 27, fr)] for fr in (-0.20, 0.0, 0.20)]
        fzs = [f(r, "fz_hz") for r in sel]
        fps = [f(r, "fp_hz") for r in sel]
        print(f"   {arm:11s} fz {min(fzs):.4e}..{max(fzs):.4e} Hz"
              f"   fp {min(fps):.4e}..{max(fps):.4e} Hz")


def divider():
    rows = read_csv("div_results.csv")
    ctl = read_csv("div_control.csv")
    print()
    print("=" * 72)
    print("Matrix G -- pll_divider_chain (functional divide ratio)")
    print("=" * 72)

    print("\n-- control: schematic arm re-run vs committed func.csv --")
    ppm = [abs(f(r, "n_delta_ppm")) for r in ctl]
    idd = [abs(f(r, "idd_delta_pct")) for r in ctl]
    print(f"   {len(ctl)} rows matched; max |n_delta| {max(ppm):.1f} ppm;"
          f" max |idd delta| {max(idd):.4f}%")

    def nmeas(r):
        td = f(r, "tdiv_b_s") - f(r, "tdiv_a_s")
        tc = f(r, "tck_b_s") - f(r, "tck_a_s")
        return td / tc if tc else float("nan")

    print("\n-- per-point divide ratio, both arms (n_nominal in the tag) --")
    print("   tag       mos     temp  vdd   word    n_sch      n_pex"
          "      err_ppm   idd_sch->pex")
    by = {(r["arm"], r["tag"], r["mos_corner"], r["temp_c"], r["vdd_v"],
           r["p_word"]): r for r in rows}
    for key in sorted(k for k in by if k[0] == "postlayout"):
        p = by[key]
        skey = ("schematic",) + key[1:]
        s = by.get(skey)
        if s is None:
            continue
        ns, np_ = nmeas(s), nmeas(p)
        err = (np_ - ns) / ns * 1e6 if ns and ns == ns and np_ == np_ else float("nan")
        ids, idp = f(s, "idd_a"), f(p, "idd_a")
        idd = (idp / ids - 1) * 100 if ids else float("nan")
        print(f"   {key[1]:9s} {key[2]:6s} {key[3]:>5s} {key[4]:5s}"
              f" {key[5]:6s} {ns:10.6f} {np_:10.6f} {err:+9.1f}"
              f"   {ids:10.4e}->{idp:10.4e} ({idd:+6.2f}%)")

    print("\n-- stage liveness on the post-layout arm (ck1..ck5, DIVOUT, FB")
    print("   rail excursions over the measurement window; mV) --")
    worst = {}
    for key in sorted(k for k in by if k[0] == "postlayout"):
        p = by[key]
        for n in ("ck1", "ck2", "ck3", "ck4", "ck5", "dvo", "fb"):
            hi, lo = f(p, f"{n}_max"), f(p, f"{n}_min")
            if hi != hi:
                continue
            swing = hi - lo
            cur = worst.get(n, (1e9, -1e9, ""))
            worst[n] = (min(cur[0], lo), max(cur[1], hi), key[1])
    for n, (lo, hi, _t) in sorted(worst.items()):
        print(f"   {n:4s} global min {lo*1000:8.1f} mV  max {hi*1000:8.1f} mV"
              f"  (worst-point swing {(hi-lo)*1000:8.1f} mV)")


def main():
    loop_filter()
    divider()
    return 0


if __name__ == "__main__":
    sys.exit(main())
