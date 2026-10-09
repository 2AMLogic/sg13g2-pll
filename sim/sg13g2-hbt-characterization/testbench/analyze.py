#!/usr/bin/env python3
"""Reduce the klt sim reports under ../corners/reports to the CSV/markdown tables
in ../records/RECORD-001.  Usage: analyze.py   (no args; reads/writes next to itself)."""
import csv, json, math, os, statistics as st
H = os.path.dirname(os.path.abspath(__file__)); C = os.path.join(H, "..", "corners")
IREF = {"2p5u": 2.5e-6, "10u": 10e-6, "80u": 80e-6}
VCE = [0.3, 0.6, 0.9, 1.2, 1.5]
VO = [0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0]
K_Q = 8.617333262e-5          # k/q in V/K

def rep(n): return json.load(open(os.path.join(C, "reports", n)))

# ---- HBT Ic-Vce / r_o ------------------------------------------------------
d = rep("hbt_ro.klt-report.json")
rows = []
for c in d["corners"]:
    v = {m["name"]: m["value"] for m in c["measurements"]}
    for i in IREF:
        for k, vce in enumerate(VCE, 1):
            rows.append(dict(corner=c["corner_id"], process=c["process"], temp_c=c["temperature_c"], iref_a=IREF[i],
                             vbe_v=v[f"vbe_{i}"], vce_v=vce, ic_a=-v[f"ic{k}_{i}"]))
with open(os.path.join(C, "hbt_ro.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)

def ro(rs, i, a, b):                       # ohm, between Vce a and b
    ia = next(r for r in rs if r["iref_a"] == IREF[i] and r["vce_v"] == a)
    ib = next(r for r in rs if r["iref_a"] == IREF[i] and r["vce_v"] == b)
    return (b - a) / (ib["ic_a"] - ia["ic_a"]), ia, ib
out = ["### HBT r_o (ohm), npn13G2 Nx=1, mirror-biased; span 0.9->1.5 V Vce (forward-active at every corner) | span 0.6->0.9 V",
       "| process | T (C) | Vbe @ Iref=2.5/10/80 uA (V) | r_o 2.5 uA | r_o 10 uA | r_o 80 uA | (0.6->0.9) 10 uA | Ic(1.5V)/Iref @10 uA |", "|---|---|---|---|---|---|---|---|"]
for c in d["corners"]:
    rs = [r for r in rows if r["corner"] == c["corner_id"]]
    vb = [next(r for r in rs if r["iref_a"] == IREF[i])["vbe_v"] for i in IREF]
    r1 = [ro(rs, i, 0.9, 1.5)[0] for i in IREF]
    r2 = ro(rs, "10u", 0.6, 0.9)[0]
    ratio = next(r for r in rs if r["iref_a"] == IREF["10u"] and r["vce_v"] == 1.5)["ic_a"] / 10e-6
    out.append(f"| {c['process']} | {c['temperature_c']} | {vb[0]:.3f} / {vb[1]:.3f} / {vb[2]:.3f} | {r1[0]/1e6:.2f} M | {r1[1]/1e6:.2f} M | {r1[2]/1e6:.3f} M | {r2/1e6:.2f} M | {ratio:.4f} |")

# ---- HBT mismatch ------------------------------------------------------------
m = rep("hbt_mm.klt-report.slim.json")
samples = {}
for s in m["samples"]:
    samples.setdefault((s["process"], s["temperature_c"]), []).append(s["values"])
mmrows = []
out += ["", "### HBT mirror-ratio mismatch (50 MC samples x 4 output devices = 200 ratios per cell; ratio = Ic_out/Iref at Vce = 0.9 V)",
        "| process | T (C) | Iref | mean ratio | sigma(ratio) % | sigma(dVbe-equiv) mV = Vt*sigma(ln ratio) |", "|---|---|---|---|---|---|"]
for (p, t), vals in sorted(samples.items(), key=lambda x: (x[0][0], x[0][1])):
    vt = K_Q * (t + 273.15)
    for i in IREF:
        rat = [-v[f"ic{k}_{i}"] / IREF[i] for v in vals for k in range(1, 5)]
        lr = [math.log(r) for r in rat]
        mmrows.append(dict(process=p, temp_c=t, iref_a=IREF[i], n=len(rat), mean_ratio=st.mean(rat), sigma_ratio=st.pstdev(rat),
                           sigma_dvbe_mv=1e3 * vt * st.pstdev(lr), min_ratio=min(rat), max_ratio=max(rat)))
        r = mmrows[-1]
        out.append(f"| {p.replace('_mismatch','')} | {t} | {i} | {r['mean_ratio']:.4f} | {100*r['sigma_ratio']/r['mean_ratio']:.2f} | {r['sigma_dvbe_mv']:.2f} |")
with open(os.path.join(C, "hbt_mm_summary.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, mmrows[0].keys()); w.writeheader(); w.writerows(mmrows)
with open(os.path.join(C, "hbt_mm_samples.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["corner_id", "mismatch_seed", "iref_a", "vbe_v"] + [f"ratio_out{k}" for k in range(1, 5)])
    for s in m["samples"]:
        for i in IREF:
            w.writerow([s["corner_id"], s["mc"]["mismatch_seed"], IREF[i], s["values"][f"vbe_{i}"]] +
                       [-s["values"][f"ic{k}_{i}"] / IREF[i] for k in range(1, 5)])

# ---- CMOS cascode leg, nominal ----------------------------------------------
n = rep("cmos_ro_nominal.klt-report.json")
c = n["corners"][0]; v = {x["name"]: x["value"] for x in c["measurements"]}
crow = []
for i in IREF:
    for k, vo in enumerate(VO, 1):
        crow.append(dict(corner=c["corner_id"], iref_a=IREF[i], vout_v=vo, isink_a=-v[f"io{k}_{i}"], vibn_v=v[f"ibn_{i}"]))
with open(os.path.join(C, "cmos_ro_nominal.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, crow[0].keys()); w.writeheader(); w.writerows(crow)
out += ["", f"### CMOS cp_leg_n cascode leg, {c['corner_id']} only (local single-corner probe)",
        "| Iref | Isink @0.3/0.9/1.5/2.1/3.0 V Vout (uA) | r_o 1.2->3.0 V | r_o 0.9->1.5 V | Vout where Isink >= 98% of Isink(3.0V) |", "|---|---|---|---|---|"]
for i in IREF:
    cs = [r for r in crow if r["iref_a"] == IREF[i]]
    g = lambda vo: next(r for r in cs if r["vout_v"] == vo)["isink_a"]
    vk = next((r["vout_v"] for r in cs if r["isink_a"] >= 0.98 * g(3.0)), None)
    out.append(f"| {i} | " + " / ".join(f"{g(x)*1e6:.3f}" for x in (0.3, 0.9, 1.5, 2.1, 3.0)) +
               f" | {(3.0-1.2)/(g(3.0)-g(1.2))/1e6:.2f} M | {(1.5-0.9)/(g(1.5)-g(0.9))/1e6:.2f} M | {vk} |")
print("\n".join(out))
