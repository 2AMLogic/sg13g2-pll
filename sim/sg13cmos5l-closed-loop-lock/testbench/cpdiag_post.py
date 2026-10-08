#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/cpdiag_post.py
(issue #150) -- post-processing for run_cp_dynamic_diag.sh.

usage: cpdiag_post.py VARIANT TAG WORK OUTDIR FREF TSTOP TMPL SNAP NGSPICE_RC
"""
import csv
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpdiag_metrics as m  # noqa: E402


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def read_cols(path, ncols):
    out = [[] for _ in range(ncols)]
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) < ncols:
                continue
            try:
                vals = [float(x) for x in p[:ncols]]
            except ValueError:
                continue
            for c in range(ncols):
                out[c].append(vals[c])
    return out


def meas_lines(log):
    d = {}
    for line in open(log):
        mm = re.match(r"^(i_pfd|i_cp|i_vco|i_ld|vc_avg|vc_max|vc_min)\s+=\s+(\S+)", line)
        if mm:
            d[mm.group(1)] = float(mm.group(2))
    return d


def ver(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip().splitlines()
    except Exception as e:  # noqa: BLE001
        return [f"unavailable: {e}"]


def main():
    variant, tag, work, outdir, fref_s, tstop, tmpl, snap, rc = sys.argv[1:10]
    fref = float(fref_s)
    name = variant + tag
    wave = read_cols(f"{work}/wave.dat", 10)
    t, ref, fb, vctrl = wave[0], wave[1], wave[3], wave[5]
    trace = m.lock_trace(t, ref, fb, 1.65, fref)
    with open(f"{outdir}/lock_trace_cpdiag_{name}.csv", "w") as f:
        f.write("t_s,delta_f_frac,phase_err_frac\n")
        for row in trace:
            f.write(",".join(str(x) for x in row) + "\n")
    summ = m.summarize(trace)
    summary = {
        "variant": variant, "tag": tag, "ngspice_exit": int(rc), "tstop": tstop,
        "lock_metrics": summ, "meas": meas_lines(f"{work}/log_run.txt"),
        "vctrl_first_last": [vctrl[0], vctrl[-1]] if vctrl else None,
        "finite": all(math.isfinite(x) for x in vctrl),
        "ref_edges": len(m.rising_edges(t, ref, 1.65)),
        "fb_edges": len(m.rising_edges(t, fb, 1.65)),
        "tools": {"ngspice": ver(["ngspice", "--version"])[:2], "python": sys.version.split()[0],
                  "pdk_git_head": ver(["git", "-C", os.environ.get("PDK_ROOT", "") + "/" + os.environ.get("PDK", ""), "rev-parse", "HEAD"]),
                  "ngspice_path": ver(["sh", "-c", "command -v ngspice"]),
                  "klt": ver(["klt", "--version"])},
        "inputs_sha256": {
            "deck_template": sha(tmpl),
            "deck_generated": sha(f"{work}/tb_run.sp"),
            "bundle": sha(f"{work}/pll_blocks_cpdiag.spice"),
            "models_inc": sha(f"{work}/cpdiag_models.inc"),
            "cp_cascbias.spice": sha(f"{snap}/cp_cascbias.spice"),
            "pfd.spice": sha(f"{snap}/pfd.spice"),
            "cpdiag_build.py": sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpdiag_build.py")),
            "cpdiag_metrics.py": sha(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpdiag_metrics.py")),
        },
        "trace_sha256": sha(f"{outdir}/lock_trace_cpdiag_{name}.csv"),
    }
    # control_hist: compare with the committed historical trace
    hist = os.path.join(snap, "..", "corners", "lock_trace_proposal_cascbias.csv")
    if variant == "control_hist" and os.path.exists(hist):
        with open(hist) as f:
            hrows = list(csv.reader(f))[1:]
        mine = [(a, b, c) for a, b, c in trace]
        summary["historical_compare"] = {
            "hist_rows": len(hrows), "new_rows": len(mine),
            "byte_identical": open(hist, "rb").read() == open(f"{outdir}/lock_trace_cpdiag_{name}.csv", "rb").read(),
        }
        if len(hrows) == len(mine):
            summary["historical_compare"]["max_abs_phase_diff"] = max(
                abs(float(h[2]) - x[2]) for h, x in zip(hrows, mine))
            summary["historical_compare"]["max_abs_df_diff"] = max(
                abs(float(h[1]) - x[1]) for h, x in zip(hrows, mine))
            summary["historical_compare"]["max_abs_t_diff_s"] = max(
                abs(float(h[0]) - x[0]) for h, x in zip(hrows, mine))
    # pulse / charge evidence (probe variants only)
    raw = f"{work}/cpraw.dat"
    if os.path.exists(raw):
        c = read_cols(raw, 12)
        rt, up, dn, icp, vdump = c[0], c[1], c[3], c[5], c[11]
        rows = m.pulse_cycles(rt, up, dn, icp)
        keys = ["t_start", "lead_is_up", "t_lead", "t_ovl", "t_tail", "q_cycle", "q_lead", "q_ovl",
                "q_rest", "i_lead", "i_ovl", "i_off", "q_edge"]
        with open(f"{outdir}/cpdiag_cycles_{name}.csv", "w") as f:
            f.write(",".join(keys) + "\n")
            for r in rows:
                f.write(",".join(repr(r[k]) for k in keys) + "\n")
        fin = rows[-20:]

        def med(k):
            v = [r[k] for r in fin if not math.isnan(r[k])]
            return statistics.median(v) if v else None
        summary["cycle_final20_median"] = {k: med(k) for k in keys if k != "t_start"}
        summary["n_pulse_pairs"] = len(rows)
        # mean vdump - mean vctrl over the averaging window
        # window start = TAVG0 = 0.8 * TSTOP (2.0 us of 2.5 us)
        t0 = 0.8 * rt[-1]
        idx = [i for i, x in enumerate(rt) if x >= t0]
        summary["vdump_mean_last20pct_V"] = sum(vdump[i] for i in idx) / max(1, len(idx))
        summary["cycle_csv_sha256"] = sha(f"{outdir}/cpdiag_cycles_{name}.csv")
    with open(f"{outdir}/cpdiag_summary_{name}.json", "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    s = summ
    print(f"[{name}] n={s['n_cycles']} phase_final20 mean={s.get('phase_mean', float('nan'))*100:.4f}% "
          f"[{s.get('phase_min', float('nan'))*100:.3f},{s.get('phase_max', float('nan'))*100:.3f}] "
          f"df_mean={s.get('df_mean', float('nan'))*100:.5f}% longest_dual={s['longest_dual_lock_run']} "
          f"freq_run={s['longest_freq_lock_run']} lock_time={s['lock_time_s']}", file=sys.stderr)


if __name__ == "__main__":
    main()
