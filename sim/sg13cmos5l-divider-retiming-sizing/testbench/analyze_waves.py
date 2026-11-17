#!/usr/bin/env python3
"""Capture-edge / clk->Q readout from a `--waves` retime deck's waves.dat (RECORD-003). Stdlib only.

Usage: analyze_waves.py <waves.dat> <vdd> [--csv <corner-label>]   (--csv prints rows, header from --csv-header)
Columns of waves.dat (ngspice `wrdata`, time/value pairs): ck, divout, fb, xfrt.clkb, xfrt.m, xfrt.s, xfrt.sb.
For each DIVOUT edge (XFRT D) in the settled window it reports the FB edge (XFRT Q) that follows it and how
many CK (CKIN_VCO) rising edges lie between them, i.e. which capture edge (k+1, k+2) the flop used.
"""
import sys

NAMES = ["ck", "divout", "fb", "clkb", "m", "s", "sb"]


def load(path):
    t, v = [], {n: [] for n in NAMES}
    for line in open(path):
        x = line.split()
        if len(x) < 14:
            continue
        t.append(float(x[0]))
        for i, n in enumerate(NAMES):
            v[n].append(float(x[2 * i + 1]))
    return t, v


def cross(t, y, lvl, rise):
    out = []
    for i in range(len(t) - 1):
        a, b = y[i], y[i + 1]
        if (a < lvl <= b) if rise else (a >= lvl > b):
            out.append(t[i] + (lvl - a) / (b - a) * (t[i + 1] - t[i]))
    return out


CSV_HEADER = "corner,edge,n,d_edge_ns,next_ck_ps,fb_after_d_ps,ck_rises_between,capture_edge,clkq_ps"


def main():
    t, v = load(sys.argv[1])
    csv_label = sys.argv[sys.argv.index("--csv") + 1] if "--csv" in sys.argv else None
    lvl = float(sys.argv[2]) / 2
    ck_r = cross(t, v["ck"], lvl, True)
    gaps = sorted(b - a for a, b in zip(ck_r, ck_r[1:]))
    tper = gaps[len(gaps) // 2]
    if csv_label is None:
        print(f"T_vco = {tper * 1e12:.2f} ps; CK rises {len(ck_r)}")
    for label, rise in (("rise", True), ("fall", False)):
        d_e, f_e = cross(t, v["divout"], lvl, rise), cross(t, v["fb"], lvl, rise)
        if csv_label is None:
            print(f"-- DIVOUT {label} -> FB {label}")
        for k, td in enumerate(d_e, 1):
            fb = [x for x in f_e if x > td]
            nxt = [x for x in ck_r if x > td]
            if not fb or len(nxt) < 2:
                continue
            f = fb[0]
            between = sum(1 for x in ck_r if td < x < f)
            cap = max(x for x in ck_r if td < x < f)
            if csv_label:
                print(f"{csv_label},{label},{k},{td * 1e9:.4f},{(nxt[0] - td) * 1e12:.1f},{(f - td) * 1e12:.1f},"
                      f"{between},k+{between},{(f - cap) * 1e12:.1f}")
                continue
            print(f"{label} #{k} D@{td * 1e9:.4f}ns nextCK+{(nxt[0] - td) * 1e12:.1f}ps FB+{(f - td) * 1e12:.1f}ps "
                  f"CKrises_between={between} FB-nextCK={(f - nxt[0]) * 1e12:.1f}ps FB-2ndCK={(f - nxt[1]) * 1e12:.1f}ps")


if "--csv-header" in sys.argv:
    print(CSV_HEADER)
else:
    main()
