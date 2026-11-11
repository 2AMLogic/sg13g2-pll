#!/usr/bin/env python3
"""Turn a `klt sim` deck-list report directory (RECORD-002 rerun, #188) into
the two CSVs run.sh writes, byte-compatible in schema and number formatting.

    python3 -I extract_issue188.py FLEET_OUTDIR DECKS_SHA256_CSV OUT_RESULTS OUT_TSTEP

Extraction is run.sh's own extract.py logic applied to each unit's
stdout.bin.  The shipped deck lists are in decks.sha256.csv (id order).
"""
import csv, re, sys, pathlib

outdir, shacsv, out_res, out_tstep = map(pathlib.Path, sys.argv[1:5])
KEYS = ("rise1", "fall1", "rise2", "rise3", "fall3", "rise4", "idd_avg")

def extract(txt):
    v = {}
    for k in KEYS:
        m = re.search(rf"^{k}\s*=\s*(\S+)\s*$", txt, re.M)
        v[k] = float(m.group(1)) if m else None
    if any(x is None for x in v.values()):
        return ["NA"] * 7
    per, thi = v["rise2"] - v["rise1"], v["fall1"] - v["rise1"]
    per2, thi2 = v["rise4"] - v["rise3"], v["fall3"] - v["rise3"]
    if min(per, thi, per2, thi2) <= 0:
        return ["NA"] * 7
    return [f"{per:.6e}", f"{thi:.6e}", f"{100*thi/per:.4f}", f"{per2:.6e}",
            f"{thi2:.6e}", f"{100*thi2/per2:.4f}", f"{abs(v['idd_avg']):.6e}"]

rows = list(csv.DictReader(open(shacsv)))
with open(out_res, "w") as fr, open(out_tstep, "w") as ft:
    fr.write("mos_corner,res_corner,temp_c,band_code,vctrl_v,period_s,thigh_s,duty_pct,"
             "period2_s,thigh2_s,duty2_pct,idd_avg_a\n")
    ft.write("mos_corner,res_corner,temp_c,band_code,vctrl_v,tstep,duty_pct\n")
    for r in rows:
        txt = (outdir / r["id"] / "stdout.bin").read_text(errors="replace")
        e = extract(txt)
        head = [r["mos_corner"], r["res_corner"], r["temp_c"], r["band_code"], r["vctrl_v"]]
        if r["id"].startswith("grid_"):
            fr.write(",".join(head + e) + "\n")
        else:
            ft.write(",".join(head + [r["tstep"], e[2]]) + "\n")
