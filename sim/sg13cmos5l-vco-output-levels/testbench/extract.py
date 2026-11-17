#!/usr/bin/env python3
"""Turn a `klt sim` deck-list report directory into corners/results.csv and
print the per-corner pass/fail summary against the row-14 bounds.

    python3 -I extract.py FLEET_OUTDIR DECKS_SHA256_CSV OUT_RESULTS

Bounds (spec/target-spec.md row 14, VDD = 3.3 V): V_OH >= 0.9 x VDD = 2.97 V,
V_OL <= 0.1 x VDD = 0.33 V.  Margins are signed: positive = inside the bound.
"""
import csv, re, sys, pathlib

outdir, shacsv, out_res = map(pathlib.Path, sys.argv[1:4])
VDD = 3.3
VOH_MIN, VOL_MAX = 0.9 * VDD, 0.1 * VDD
KEYS = ("voh", "vol", "vmax", "vmin")

def get(txt, k):
    m = re.search(rf"^{k}\s*=\s*(\S+)\s*$", txt, re.M)
    return float(m.group(1)) if m else None

hdr = ["mos_corner", "res_corner", "temp_c", "band_code", "vctrl_v", "voh_v", "vol_v",
       "vmax_v", "vmin_v", "voh_margin_v", "vol_margin_v", "pass"]
res = []
with open(out_res, "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(hdr)
    for r in csv.DictReader(open(shacsv)):
        txt = (outdir / r["id"] / "stdout.bin").read_text(errors="replace")
        v = [get(txt, k) for k in KEYS]
        head = [r["mos_corner"], r["res_corner"], r["temp_c"], r["band_code"], r["vctrl_v"]]
        if any(x is None for x in v):
            w.writerow(head + ["NA"] * 7)
            continue
        voh, vol = v[0], v[1]
        mh, ml = voh - VOH_MIN, VOL_MAX - vol
        ok = "pass" if mh >= 0 and ml >= 0 else "FAIL"
        w.writerow(head + [f"{x:.5f}" for x in v] + [f"{mh:.5f}", f"{ml:.5f}", ok])
        res.append((head, voh, vol, mh, ml, ok))

n = len(res)
print(f"{n} valid rows; {sum(1 for x in res if x[5] == 'FAIL')} FAIL")
if res:
    b = min(res, key=lambda x: x[3]); print("binding V_OH:", b[0], f"{b[1]:.4f} V (margin {b[3]:+.4f})")
    b = min(res, key=lambda x: x[4]); print("binding V_OL:", b[0], f"{b[2]:.4f} V (margin {b[4]:+.4f})")
