#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim/testbench/collect_rerun.py
(issue #230). Folds the `klt sim` batch reports written by the
gen_rerun_requests.py requests (../reports/rerun/full/<rerun>_<key>.request/
report.json) into CSVs with the ORIGINAL records' schema, at NEW paths:

  ../corners/rerun-record-00N-results.csv     (N = 1, 2; rows as results.csv)
  ../corners/rerun-record-00N-compliance.csv  (rows as compliance.csv)

Any corner that is not `pass`, or any missing measurement, is written as `NA`
(never dropped). Usage: python3 collect_rerun.py
"""
import json, pathlib

here = pathlib.Path(__file__).resolve().parent
root = here.parent
CODES = [("2p5", "2.5u"), ("5", "5u"), ("10", "10u"), ("20", "20u"), ("40", "40u"), ("80", "80u")]
STATES = ["up", "dn", "both"]
KEYS = [("pvt33", 3.3), ("v30", 3.0), ("v36", 3.6)]
HDR = "mos_corner,temp_c,vdd_v,iref_a,state,vout_v,icp_a\n"
MOS = ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"]
ORDER = [(m, t) for m in MOS for t in (27, 125, -40)]


def num(v, fmt):
    return "NA" if v is None else format(v, fmt)


for rr, n in (("rerun1", 1), ("rerun2", 2)):
    res, comp = [HDR], [HDR]
    # original order: 15 PVT points (mos_tt first), then the two supply points
    jobs = []
    for key, vdd in KEYS:
        rep = json.load(open(root / f"reports/rerun/full/{rr}_{key}.request/report.json"))
        byc = {(c["process"], c["temperature_c"]): c for c in rep["corners"]}
        jobs.append((vdd, byc))
    seq = [(3.3, m, t) for m, t in ORDER] + [(3.0, "mos_tt", 27), (3.6, "mos_tt", 27)]
    for vdd, mos, t in seq:
        c = dict(jobs)[vdd][(mos, t)] if False else next(b for v, b in jobs if v == vdd)[(mos, t)]
        meas = {m["name"]: (m["value"] if c["status"] == "pass" else None) for m in c["measurements"]}
        vm = meas.get("vs_mid_v")
        for tag, iref in CODES:
            for st in STATES:
                res.append(f"{mos},{t},{vdd},{iref},{st},{num(vm, '.4f')},"
                           f"{num(meas.get(f'icp_mid_{st}_{tag}'), '.6e')}\n")
        for st in STATES:
            k = 0
            while f"cmp_{st}_10_k{k:02d}" in meas:
                comp.append(f"{mos},{t},{vdd},10u,{st},{0.15 + 0.05 * k:.4f},"
                            f"{num(meas[f'cmp_{st}_10_k{k:02d}'], '.6e')}\n")
                k += 1
    (root / f"corners/rerun-record-00{n}-results.csv").write_text("".join(res))
    (root / f"corners/rerun-record-00{n}-compliance.csv").write_text("".join(comp))
    print(rr, len(res) - 1, "results rows;", len(comp) - 1, "compliance rows;",
          sum(r.count("NA") for r in res + comp), "NA")
