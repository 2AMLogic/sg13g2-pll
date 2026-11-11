#!/usr/bin/env python3
"""sg13g2-pll :: summarize_rerun320.py (issue #320, RECORD-006).

Read ../reports/sim.rerun320_bundles.batch.json and write the two new rerun
CSVs (same 14-column schema as the originals' results_resized_issue{83,79}_
finetrim.csv), taking each loop's value ONLY from its own bundle's corner:

    python3 summarize_rerun320.py
"""
import csv
import json
import pathlib

here = pathlib.Path(__file__).resolve().parent
slug = here.parent
env = json.loads((slug / "reports/sim.rerun320_bundles.batch.json").read_text())

val = {}  # (corner process, measurement) -> value
for c in env["corners"]:
    for m in c["measurements"]:
        val[(c["process"], m["name"])] = m["value"]


def rows(orig_csv, loops):
    orig = {r["pvt_bundle"]: r for r in csv.DictReader(open(slug / "corners" / orig_csv))}
    out = []
    for bundle, tag in loops:
        o = orig[bundle]
        fc = val[(bundle, f"fc_hz_{tag}")]
        pm = val[(bundle, f"pm_deg_{tag}")]
        ceil = float(o["fref_hz"]) / 10.0
        out.append([bundle, o["band_code"], o["kvco_interval"], o["kvco_hz_per_v"],
                    o["fvco_hz"], o["fref_hz"], o["n_div"], o["trim_code"], o["icp_a"],
                    f"{fc:.6e}", f"{pm:.3f}", f"{ceil:.6e}",
                    "yes" if fc < ceil else "no", "yes" if pm >= 45.0 else "no"])
    return out


HDR = ["pvt_bundle", "band_code", "kvco_interval", "kvco_hz_per_v", "fvco_hz",
       "fref_hz", "n_div", "trim_code", "icp_a", "fc_hz", "pm_deg",
       "fc_ceiling_hz", "meets_ceiling", "meets_pm45"]
for name, orig, loops in (
    ("results_resized_issue83_finetrim_rerun320.csv",
     "results_resized_issue83_finetrim.csv", [("slow", "dr007_slow")]),
    ("results_resized_issue79_finetrim_rerun320.csv",
     "results_resized_issue79_finetrim.csv",
     [("fast", "dr008_fast"), ("typ", "dr008_typ"), ("slow", "dr008_slow")]),
):
    with open(slug / "corners" / name, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HDR)
        w.writerows(rows(orig, loops))
    print("wrote", name)
