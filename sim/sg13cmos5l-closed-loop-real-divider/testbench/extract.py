#!/usr/bin/env python3
"""sg13g2-pll :: closed-loop-real-divider extraction (issue #159).

usage: extract.py TAG WAVE_DAT OUT_DIR FREF TAVG0

Reuses the campaign's own dual-lock criterion UNCHANGED by loading
lock_analysis() from ../../sg13cmos5l-closed-loop-lock/testbench/extract.py
(|delta f|/f_ref < 1% AND |phase err| < 5% of T_ref, >= 20 consecutive ref
cycles). Adds divider-ratio / edge-count / VCO-frequency extraction.
Writes OUT_DIR/trace_TAG.csv (per-ref-cycle), OUT_DIR/summary_TAG.json, and
a decimated waveform OUT_DIR/vctrl_TAG.csv (columns t_s,vctrl_v,fb_v; about
1 sample/ns).  In summary_TAG.json each window's "t1" is the last simulated
sample time t[-1]; the window is closed at its end (no edge is excluded for
lying at or before t1) -- the window has no upper cut-off other than the end
of the record.
"""
import importlib.util, json, os, sys

tag, wave, out, fref_s, tavg0_s = sys.argv[1:6]
fref = float(fref_s)
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "campaign_extract", os.path.join(here, "../../sg13cmos5l-closed-loop-lock/testbench/extract.py"))
camp = importlib.util.module_from_spec(spec); spec.loader.exec_module(camp)

def parse_time(s):
    for suf, m in (("u", 1e-6), ("n", 1e-9), ("p", 1e-12)):
        if s.endswith(suf): return float(s[:-1]) * m
    return float(s)
tavg0 = parse_time(tavg0_s)

t, ref, fb, vctrl = [], [], [], []
with open(wave) as f:
    for line in f:
        p = line.split()
        if len(p) < 8: continue
        try: v = [float(x) for x in p[:8]]
        except ValueError: continue
        t.append(v[0]); ref.append(v[1]); fb.append(v[3]); vctrl.append(v[5])
        if len(t) == 1: clk = []
        clk.append(v[7])

VTH = 1.65
trace, lock_time = camp.lock_analysis(t, ref, fb, VTH, fref)
with open(f"{out}/trace_{tag}.csv", "w") as f:
    f.write("t_s,delta_f_frac,phase_err_frac,dual_lock_ok\n")
    for r in trace: f.write(",".join(str(x) for x in r) + "\n")

ref_e = camp.rising_edges(t, ref, VTH)
fb_e = camp.rising_edges(t, fb, VTH)
clk_e = camp.rising_edges(t, clk, VTH)

def window_stats(t0, t1):
    # Window = [t0, end of record].  Every interpolated edge lies at or before
    # t[-1] = t1, so no upper bound is applied (this is the same edge set the
    # earlier "e < tend + 1" test selected; "+ 1" was a 1-second sentinel).
    c = [e for e in clk_e if e >= t0]
    b = [e for e in fb_e if e >= t0]
    r = [e for e in ref_e if e >= t0]
    d = {"t0": t0, "t1": t1, "clk_edges": len(c), "fb_edges": len(b), "ref_edges": len(r)}
    d["f_vco_hz_mean"] = (len(c) - 1) / (c[-1] - c[0]) if len(c) > 1 else None
    d["f_fb_hz_mean"] = (len(b) - 1) / (b[-1] - b[0]) if len(b) > 1 else None
    d["f_ref_hz_mean"] = (len(r) - 1) / (r[-1] - r[0]) if len(r) > 1 else None
    # per-fb-period ratio: VCO edges between successive fb edges
    ratios = []
    for a, bb in zip(b[:-1], b[1:]):
        ratios.append(sum(1 for e in c if a <= e < bb))
    d["clk_edges_per_fb_period"] = {str(k): ratios.count(k) for k in sorted(set(ratios))}
    d["mean_ratio_edges"] = sum(ratios) / len(ratios) if ratios else None
    return d

tend = t[-1]
w_all = window_stats(0.0, tend)
w_fin = window_stats(max(tend - 500e-9, 0.0), tend)
w_avg = window_stats(tavg0, tend)

# longest dual-lock / freq-lock runs, final-20 stats
def longest(pred):
    best = cur = 0; best_end = None
    for i, r in enumerate(trace):
        cur = cur + 1 if pred(r) else 0
        if cur > best: best, best_end = cur, i
    return best, (trace[best_end - best + 1][0] if best else None)
l_dual = longest(lambda r: r[3])
l_freq = longest(lambda r: abs(r[1]) < 0.01)
fin = trace[-20:]
summ = {
    "tag": tag, "n_samples": len(t), "t_end_s": tend,
    "vctrl_start": vctrl[0], "vctrl_end": vctrl[-1],
    "vctrl_min": min(vctrl), "vctrl_max": max(vctrl),
    "n_ref_cycles_in_trace": len(trace),
    "lock_time_s": lock_time,
    "longest_dual_lock_run_cycles": l_dual[0], "longest_dual_lock_run_start_s": l_dual[1],
    "longest_freq_lock_run_cycles": l_freq[0], "longest_freq_lock_run_start_s": l_freq[1],
    "windows": {"all": w_all, "final_500ns": w_fin, "avg_window": w_avg},
}
if fin:
    summ["final20_df_min"] = min(r[1] for r in fin)
    summ["final20_df_max"] = max(r[1] for r in fin)
    summ["final20_df_mean"] = sum(r[1] for r in fin) / len(fin)
    summ["final20_phase_min"] = min(r[2] for r in fin)
    summ["final20_phase_max"] = max(r[2] for r in fin)
    summ["final20_phase_mean"] = sum(r[2] for r in fin) / len(fin)
json.dump(summ, open(f"{out}/summary_{tag}.json", "w"), indent=1)
# decimated vctrl trace, one point per ~ns
with open(f"{out}/vctrl_{tag}.csv", "w") as f:
    f.write("t_s,vctrl_v,fb_v\n")
    step = max(1, int(round(1e-9 / (t[1] - t[0]))))
    for i in range(0, len(t), step): f.write(f"{t[i]:.6e},{vctrl[i]:.6f},{fb[i]:.4f}\n")
print(json.dumps(summ, indent=1))
