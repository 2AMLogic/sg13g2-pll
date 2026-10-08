#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/cpdiag_pulse_post.py
(issue #150) -- post-processing for run_cp_pulse_charge.sh.
usage: cpdiag_pulse_post.py VARIANT TAG WORK OUTDIR SNAP RC
"""
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpdiag_metrics as m  # noqa: E402


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    icpt = my - slope * mx
    resid = max(abs(y - (slope * x + icpt)) for x, y in zip(xs, ys))
    return slope, icpt, resid


def main():
    variant, tag, work, outdir, snap, rc = sys.argv[1:7]
    cols = [[] for _ in range(8)]
    for line in open(f"{work}/cppulse.dat"):
        p = line.split()
        if len(p) < 8:
            continue
        try:
            v = [float(x) for x in p[:8]]
        except ValueError:
            continue
        for i in range(8):
            cols[i].append(v[i])
    t, up, dn, ic, vd = cols[0], cols[1], cols[3], cols[5], cols[7]
    ur, uf = m.rising_edges(t, up, 1.65), m.falling_edges(t, up, 1.65)
    dr, df = m.rising_edges(t, dn, 1.65), m.falling_edges(t, dn, 1.65)
    evs = [l.strip().split(",") for l in open(f"{work}/events.csv")][1:]
    rows = []
    for mode, wcmd, start in evs:
        s = float(start)
        # measured widths at the 1.65 V thresholds of the driven nets
        def edge(lst, lo, hi):
            c = [x for x in lst if lo <= x <= hi]
            return c[0] if c else None
        a, b = edge(ur, s - 1e-9, s + 2e-9), edge(uf, s, s + 12e-9)
        c, d = edge(dr, s - 1e-9, s + 2e-9), edge(df, s, s + 12e-9)
        if mode == "up":
            w = b - a
        elif mode == "dn":
            w = d - c
        else:
            w = 0.5 * ((b - a) + (d - c))
        # integration window: 1 ns before the first edge to 12 ns after the last edge
        w0, w1 = s - 1.0e-9, s + float(wcmd) + 12.0e-9
        q = m.trapz(t, ic, w0, w1)
        rows.append(dict(mode=mode, width_s=w, q_c=q, start_s=s))
    with open(f"{outdir}/cppulse_events_{variant}{tag}.csv", "w") as f:
        f.write("mode,start_s,width_s,q_c\n")
        for r in rows:
            f.write(f"{r['mode']},{r['start_s']!r},{r['width_s']!r},{r['q_c']!r}\n")
    fits = {}
    for mode in ("up", "dn", "both"):
        xs = [r["width_s"] for r in rows if r["mode"] == mode]
        ys = [r["q_c"] for r in rows if r["mode"] == mode]
        sl, ic0, res = ols(xs, ys)
        fits[mode] = {"I_plateau_A": sl, "Q0_C": ic0, "max_fit_resid_C": res, "n": len(xs)}
    # superposition check: both-fit vs up-fit + dn-fit
    fits["superposition"] = {
        "I_both_minus_(Iup+Idn)_A": fits["both"]["I_plateau_A"] - fits["up"]["I_plateau_A"] - fits["dn"]["I_plateau_A"],
        "Q0_both_minus_(Q0up+Q0dn)_C": fits["both"]["Q0_C"] - fits["up"]["Q0_C"] - fits["dn"]["Q0_C"],
    }
    # quiet level (both low): mean over the pre-pulse window and over every gap
    quiet = m.trapz(t, ic, 20e-9, 90e-9) / 70e-9
    meas = {}
    for line in open(f"{work}/log_run.txt"):
        mm = re.match(r"^(i_cp_avg_quiet|i_out_quiet|vdump_quiet|vswp_quiet|vswn_quiet|vswp_on|vswn_on)\s+=\s+(\S+)", line)
        if mm:
            meas[mm.group(1)] = float(mm.group(2))
    summ = {"variant": variant, "tag": tag, "ngspice_exit": int(rc), "fits": fits,
            "i_out_quiet_trapz_A": quiet, "meas": meas,
            "finite": all(x == x and abs(x) < 1e9 for x in ic),
            "events_csv_sha256": sha(f"{outdir}/cppulse_events_{variant}{tag}.csv"),
            "tools": {"ngspice": subprocess.run(["ngspice", "--version"], capture_output=True, text=True).stdout.strip().splitlines()[:2],
                      "ngspice_path": subprocess.run(["sh", "-c", "command -v ngspice"], capture_output=True, text=True).stdout.strip()},
            "deck_sha256": sha(f"{work}/tb_run.sp"), "bundle_sha256": sha(f"{work}/pll_blocks_cpdiag.spice"),
            "template_sha256": sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tb_cp_pulse_charge.sp.tmpl"))}
    json.dump(summ, open(f"{outdir}/cppulse_summary_{variant}{tag}.json", "w"), indent=1, sort_keys=True)
    for k in ("up", "dn", "both"):
        f = fits[k]
        print(f"[{variant}{tag}] {k}: I={f['I_plateau_A']*1e6:.4f} uA  Q0={f['Q0_C']*1e15:.3f} fC  resid={f['max_fit_resid_C']*1e15:.3f} fC",
              file=sys.stderr)


if __name__ == "__main__":
    main()
