#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/rerun-324/collect.py
(issue #324, Part of #215) -- turns the `klt sim --batch-set` reports into
rerun CSVs with the ORIGINAL columns, and compares them with the committed
originals (which it only reads).

  collect.py <grid-dir> <out-dir>

<grid-dir> holds one `<variant>_<bundle>.request/report.json` per request (and,
for the probe, `none_typ.json`).  Writes <out-dir>/results.csv (the 120-row
Matrix A grid), <out-dir>/rc_attribution.csv (the 210-row attribution grid),
<out-dir>/compare.txt and <out-dir>/jobs.json (job id per request).
"""
import csv
import json
import os
import statistics
import sys

grid, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
BENCH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUNDLES = {"typ": ("mos_tt", "res_typ", "27"), "slow": ("mos_ss", "res_wcs", "125"),
           "fast": ("mos_ff", "res_bcs", "-40")}
BAND = {(0.0, 0.0): "00", (3.3, 0.0): "10", (0.0, 3.3): "01", (3.3, 3.3): "11"}


def load(variant, bundle):
    p = os.path.join(grid, "%s_%s.request" % (variant, bundle), "report.json")
    resumed = os.path.join(grid, "%s_%s.resume.json" % (variant, bundle))
    if os.path.exists(resumed):  # a --resume completed a shard the capacity-capped fleet had refused
        p = resumed
    elif not os.path.exists(p):
        p = os.path.join(grid, "%s_%s.json" % (variant, bundle))
    return json.load(open(p))


def rows_for(variant, bundle):
    rep = load(variant, bundle)
    mos, res, temp = BUNDLES[bundle]
    jobs = rep["environment"]["remote"]
    for c in rep["corners"]:
        p = c["params"]
        band = BAND[(float(p["p_b0v"]), float(p["p_b1v"]))]
        if c["status"] != "pass" or not c["measurements"] or c["measurements"][0]["value"] is None:
            period = "NA"
            freq = "NA"
        else:
            period = c["measurements"][0]["value"]
            freq = 1.0 / period
        yield [bundle, mos, res, temp, band, "%g" % p["p_vctrl"], period, freq], c["status"], jobs


jobs = {}
res_rows, rc_rows, bad = [], [], []
for arm in ("postlayout", "schematic"):
    for b in BUNDLES:
        for r, st, j in rows_for(arm, b):
            if st != "pass":
                bad.append((arm, b, r[4], r[5], st))
            res_rows.append([arm] + r)
        jobs["%s_%s" % (arm, b)] = j.get("job_ids") or j.get("job_id")
for v in ("full", "c_only", "r_only", "none", "cscale25", "cscale10", "cscale05"):
    for b in BUNDLES:
        for r, st, j in rows_for(v, b):
            if st != "pass":
                bad.append((v, b, r[4], r[5], st))
            rc_rows.append([v] + r)
        jobs["%s_%s" % (v, b)] = j.get("job_ids") or j.get("job_id")

HDR = ["pvt_bundle", "mos_corner", "res_corner", "temp_c", "band_code", "vctrl_v", "period_s", "freq_hz"]
for name, hdr0, rows in (("results.csv", "arm", res_rows), ("rc_attribution.csv", "variant", rc_rows)):
    with open(os.path.join(out, name), "w", newline="") as f:
        f.write(",".join([hdr0] + HDR) + "\n")
        for r in sorted(rows, key=lambda r: [str(x) for x in r]):
            f.write(",".join(str(x) for x in r) + "\n")
# Job ids: the --batch-set envelope (stdout.json) names every job per request; the
# probe and the --resume are separate invocations whose job ids come from their reports.
jobs = {}
setenv = json.load(open(os.path.join(grid, "stdout.json")))
for q in setenv["requests"]:
    jobs[os.path.basename(q["request"]).replace(".request.json", "")] = q.get("job_ids")
rlog = os.path.join(grid, "postlayout_fast.resume.stderr.log")
if os.path.exists(rlog):
    import re
    resumed_ids = re.findall(r"batch job (klt-sim-[0-9a-f]+)(?: \(.*?\))?: done", open(rlog).read())
    jobs["postlayout_fast"] = sorted(set(jobs["postlayout_fast"]) | set(resumed_ids))
json.dump(jobs, open(os.path.join(out, "jobs.json"), "w"), indent=2, sort_keys=True)


def key(r, first):
    return (r[first], r["pvt_bundle"], r["band_code"], "%g" % float(r["vctrl_v"]))


def compare(orig_path, new_path, first, label, lines):
    o = {key(r, first): r for r in csv.DictReader(open(orig_path))}
    n = {key(r, first): r for r in csv.DictReader(open(new_path))}
    lines.append("%s: %d original rows, %d rerun rows, key sets equal: %s" % (
        label, len(o), len(n), set(o) == set(n)))
    d, na = [], []
    for k in sorted(set(o) & set(n)):
        a, b = o[k]["period_s"], n[k]["period_s"]
        if a == "NA" or b == "NA":
            if a != b:
                na.append((k, a, b))
            continue
        d.append((abs(float(b) / float(a) - 1.0) * 100.0, k))
    if d:
        v = [x for x, _ in d]
        lines.append("  period ratio |rerun/orig-1| %%: mean %.3f  median %.3f  max %.3f (%s)  n=%d" % (
            statistics.mean(v), statistics.median(v), max(v), max(d)[1], len(v)))
        lines.append("  rows within 1%%: %d / %d; within 2%%: %d / %d" % (
            sum(x <= 1 for x in v), len(v), sum(x <= 2 for x in v), len(v)))
    lines.append("  NA mismatches (orig vs rerun): %s" % (na or "none"))


lines = ["rerun failures/non-pass units: %s" % (bad or "none")]
compare(os.path.join(BENCH, "corners", "results.csv"), os.path.join(out, "results.csv"), "arm",
        "Matrix A results.csv", lines)
compare(os.path.join(BENCH, "corners", "rc_attribution.csv"), os.path.join(out, "rc_attribution.csv"),
        "variant", "rc_attribution.csv", lines)
open(os.path.join(out, "compare.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
