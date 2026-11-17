#!/usr/bin/env python3
"""Fold the #323 batch reports into the rerun CSVs (same columns as the originals).

    python3 -I collect.py REQ_DIR BATCH_JSON CORNERS_OUT_DIR

REQ_DIR holds manifest.json from gen_requests.py; BATCH_JSON is the
`klt sim --batch-set` aggregate envelope.  Writes results-rerun323.csv,
rc_attribution-rerun323.csv, cp_results-rerun323.csv, jobs-rerun323.csv.
A unit with no measured value is written as NA (never dropped).
"""
import csv, json, pathlib, sys

req, batch, outd = (pathlib.Path(a) for a in sys.argv[1:4])
man = json.loads((req / "manifest.json").read_text())
env = json.loads(batch.read_text())
BUND = {"typ": ("mos_tt", "res_typ", 27), "slow": ("mos_ss", "res_wcs", 125),
        "fast": ("mos_ff", "res_bcs", -40)}
rows = {"vco": [], "rc": [], "cp": []}
jobs = []
for r in env["requests"]:
    name = pathlib.Path(r["request"]).parent.name
    rep = json.loads((batch.parent / r["report"]).read_text()) if not pathlib.Path(r["report"]).is_absolute() else json.loads(pathlib.Path(r["report"]).read_text())
    cs = rep["corners"]
    ids = man[name]
    assert len(cs) == len(ids), (name, len(cs), len(ids))
    jobs.append((name, r["job_id"], rep["status"], rep["corner_count"], rep["passed"],
                 rep["failed"], rep["errored"], rep["inconclusive"]))
    for c, i in zip(cs, ids):
        m = {x["name"]: x.get("value") for x in c["measurements"]}
        if name.startswith("cp_"):
            arm = name.split("_")[1]
            mos, t, vdd, st = i
            iref = name.split("iref")[1]
            v = m.get("icp_a")
            rows["cp"].append([arm, mos, t, vdd, iref, st, round(vdd / 2, 4) if v is not None else "NA",
                               "%.9g" % v if v is not None else "NA"])
        else:
            b, bl, vc = i
            mos, res, t = BUND[b]
            p = m.get("per1")
            f = "%r" % (1.0 / p) if p else "NA"
            lab = name.split("_", 1)[1] if name.startswith("rc_") else name.split("_")[1]
            rows["rc" if name.startswith("rc_") else "vco"].append(
                [lab, b, mos, res, t, bl, vc, "%.6e" % p if p else "NA", f])
hdr = {"vco": "arm,pvt_bundle,mos_corner,res_corner,temp_c,band_code,vctrl_v,period_s,freq_hz",
       "rc": "variant,pvt_bundle,mos_corner,res_corner,temp_c,band_code,vctrl_v,period_s,freq_hz",
       "cp": "arm,mos_corner,temp_c,vdd_v,iref_a,state,vout_v,icp_a"}
fn = {"vco": "results-rerun323.csv", "rc": "rc_attribution-rerun323.csv", "cp": "cp_results-rerun323.csv"}
outd.mkdir(parents=True, exist_ok=True)
for k in rows:
    with open(outd / fn[k], "w") as f:
        f.write(hdr[k] + "\n")
        for ln in sorted(",".join(map(str, r)) for r in rows[k]):
            f.write(ln + "\n")
    print(fn[k], len(rows[k]), "rows,", sum(r[-1] == "NA" for r in rows[k]), "NA")
with open(outd / "jobs-rerun323.csv", "w") as f:
    f.write("request,job_id,status,units,passed,failed,errored,inconclusive\n")
    for j in sorted(jobs):
        f.write(",".join(map(str, j)) + "\n")
