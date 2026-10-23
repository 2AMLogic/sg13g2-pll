#!/usr/bin/env python3
"""Reduce ../corners/reports/*.klt-report.json to ../corners/pfd_parity.csv.
Verdict needs |UP-DN| > 0.05 in the right direction.
UP/DN are scored as the fraction of VDD (3.3 V) averaged over 200-500 ns."""
import csv, glob, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
VDD = 3.3
rows = []
for p in sorted(glob.glob(os.path.join(HERE, "..", "corners", "reports", "*_pvt.klt-report.json"))):
    variant, case = re.match(r"(before|after)_(reflead|fblead)_pvt", os.path.basename(p)).groups()
    for c in json.load(open(p))["corners"]:
        m = {x["name"]: x["value"] for x in c["measurements"]}
        up, dn = m["up_avg"] / VDD, m["dn_avg"] / VDD
        want_up = case == "reflead"
        big, small = (up, dn) if want_up else (dn, up)
        # lead/lag must separate UP from DN by >5 % of VDD; a ~0 spread is a PFD
        # that does not hold its outputs (symmetric blips), not a textbook answer
        ok = big - small > 0.05
        rows.append([variant, case, c["process"], c["temperature_c"], f"{up:.4f}", f"{dn:.4f}",
                     "textbook" if ok else "NO-LEAD/LAG-DISCRIMINATION"])
out = os.path.join(HERE, "..", "corners", "pfd_parity.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["variant", "case", "process", "temp_c", "up_duty", "dn_duty", "verdict"]); w.writerows(rows)
print(open(out).read())
