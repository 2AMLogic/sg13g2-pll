#!/usr/bin/env python3
"""Fold the issue #329 klt-sim batch reports into corners/schmitt_rewire_rerun329.csv.

Usage: collect_rerun329.py <batch-set-output-dir> [--jobs-out jobs.tsv]
Same column schema as the original corners/schmitt_rewire.csv (not modified);
also prints a per-arm comparison against it.  Reads reports only; runs nothing.
"""
import csv, json, pathlib, re, sys

REC = pathlib.Path(__file__).resolve().parent.parent
PDK = {"cmos5l": "ihp-sg13cmos5l", "g2": "ihp-sg13g2"}
LABEL = {"as_drawn": "as_drawn", "rewired": "feedback_rewired"}
out = pathlib.Path(sys.argv[1])
man = json.load(open(out / "set-manifest.json")) if (out / "set-manifest.json").exists() else None
sets = json.load(open(out.with_suffix(".json"))) if out.with_suffix(".json").exists() else None
rows, jobs = [], []
for rep in sorted(out.glob("schmitt_rewire_*.request/report.json")):
    m = re.match(r"schmitt_rewire_(cmos5l|g2)_(as_drawn|rewired)_(\d)p(\d+)\.request", rep.parent.name)
    arm, dut, a, b = m.groups(); vsup = "%s.%s" % (a, b)
    d = json.load(open(rep))
    jobs.append((arm, dut, vsup, d["environment"]["remote"]["job_id"], d["environment"]["remote"].get("runner_klt_version"), d["status"]))
    for c in d["corners"]:
        ms = {x["name"]: x["value"] for x in c["measurements"]}
        u, dn = ms.get("vth_up"), ms.get("vth_dn")
        if u is None or dn is None:
            row = ["NA"] * 4
        else:
            h = u - dn
            row = ["%.5e" % u if False else repr(u), repr(dn), "%.6e" % h, "%.4f" % (100 * h / float(vsup))]
        rows.append([PDK[arm], LABEL[dut], c["process"], "%g" % c["temperature_c"], vsup] + row)
order = {"mos_tt": 0, "mos_ff": 1, "mos_ss": 2}
rows.sort(key=lambda r: (r[0] != "ihp-sg13cmos5l", r[1] != "as_drawn", order[r[2]], float(r[3]), float(r[4])))
dest = REC / "corners/schmitt_rewire_rerun329.csv"
with open(dest, "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow("pdk,dut,mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd".split(","))
    w.writerows(rows)
orig = {tuple(r[:5]): r for r in csv.reader(open(REC / "corners/schmitt_rewire.csv")) if r[0] != "pdk"}
for r in rows:
    o = orig[tuple(r[:5])]
    r.append(o)
print("rows:", len(rows), "->", dest)
for key in sorted({(r[0], r[1]) for r in rows}):
    sel = [r for r in rows if (r[0], r[1]) == key]
    hy = [float(r[7]) for r in sel if r[7] != "NA"]
    dh = [abs(float(r[7]) - float(r[-1][7])) for r in sel if r[7] != "NA" and r[-1][7] != "NA"]
    print(key, "n=%d" % len(sel), "NA=%d" % sum(r[7] == "NA" for r in sel), "hyst_V min/max %.4g/%.4g" % (min(hy), max(hy)),
          "max|d hyst vs original| %.3g V" % max(dh))
print("\n".join("\t".join(map(str, j)) for j in jobs))
