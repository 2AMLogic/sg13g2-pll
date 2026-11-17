#!/usr/bin/env python3
"""Turn the klt-sim batch reports of this rerun (issue #232) into CSVs with the
historical column layouts, at NEW paths (never the historical corners/*.csv).

usage: reports_to_csv.py <reports-dir> <corners-out-dir>
<reports-dir> holds <name>.request/report.json per request (klt --batch-set -o).
"""
import csv
import json
import pathlib
import re
import sys

src, out = map(pathlib.Path, sys.argv[1:3])


def load(name):
    p = src / f"{name}.request" / "report.json"
    return json.loads(p.read_text()) if p.exists() else None


def val(c, n):
    for m in c["measurements"]:
        if m["name"] == n:
            return "NA" if m["value"] is None else repr(m["value"])
    return "NA"


def corner(c):
    mos = c["process"]
    return mos, c["temperature_c"], c["params"].get("vddp", 3.3)


VARS = ("asdrawn", "fbfix")
with open(out / "rerun232-hold.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow("variant,mos_corner,temp_c,vdd_v,q_end_v,s_end_v,t_decay_s".split(","))
    for v in VARS:
        d = load(f"hold_{v}")
        for c in d["corners"]:
            w.writerow([v, *corner(c), val(c, "q_end"), val(c, "s_end"), val(c, "t_decay")])

with open(out / "rerun232-setup.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow("variant,mos_corner,temp_c,vdd_v,tsu_s,q_sample_v".split(","))
    for v in VARS:
        d = load(f"setup_{v}")
        for c in d["corners"]:
            mos, t, vdd = corner(c)
            w.writerow([v, mos, t, vdd, repr(c["params"]["tsu"]), val(c, "q_s")])

with open(out / "rerun232-opconv.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow("variant,ic,converged,status,divout_v,job_id,note".split(","))
    for v in VARS:
        for ic in ("none", "applied"):
            d = load(f"opconv_{v}_{ic}")
            if d is None:
                continue
            c = d["corners"][0]
            note = " | ".join(x["message"][:160] for x in c.get("diagnostics", []))
            conv = "yes" if c["status"] == "pass" and val(c, "divout") != "NA" else "no"
            w.writerow([v, ic, conv, c["status"], val(c, "divout"),
                        d["environment"].get("remote", {}).get("job_id", ""), note.replace(",", ";")])

for stage in ("func_baseline", "retime"):
    rows = []
    for v in VARS:
        d = load(f"{stage}_{v}")
        if d is None:
            continue
        for c in d["corners"]:
            diag = " | ".join(x["message"][:120] for x in c.get("diagnostics", [])).replace(",", ";")
            rows.append([v, *corner(c), c["status"], c.get("runtime_s"),
                         *[val(c, m["name"]) for m in c["measurements"]], diag])
            names = [m["name"] for m in c["measurements"]]
    if rows:
        with open(out / f"rerun232-{stage}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["variant", "mos_corner", "temp_c", "vdd_v", "status", "runtime_s", *names, "diagnostics"])
            w.writerows(rows)
