#!/usr/bin/env python3
"""Reduce a `klt sim` decks report (gen_rerun.py request) to corners/results-rerun.csv.

  collect_rerun.py <outdir-with-unit-dirs>   (prints a comparison vs corners/results.csv)
"""
import csv, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent
sys.path.insert(0, str(HERE))
out = pathlib.Path(sys.argv[1])
B = {"typ": ("mos_tt", "res_typ", "cap_typ", "27"), "slow": ("mos_ss", "res_wcs", "cap_wcs", "125"),
     "fast": ("mos_ff", "res_bcs", "cap_bcs", "-40")}
rows = []
for bname in B:
    for band in ("00", "10", "01", "11"):
        for v in ("0.3", "0.9", "1.5", "2.1", "2.7"):
            uid = f"{bname}_b{band}_v{v.replace('.', 'p')}"
            so = out / uid / "stdout.bin"
            m = re.search(rb"^per1 = (\S+)", so.read_bytes(), re.M) if so.exists() else None
            if m:
                p = m.group(1).decode()
                rows.append([bname, *B[bname][:3], B[bname][3], band, v, p, repr(1.0 / float(p))])
            else:
                rows.append([bname, *B[bname][:3], B[bname][3], band, v, "NA", "NA"])
dst = RECORD / "corners" / "results-rerun.csv"
with dst.open("w", newline="") as f:
    f.write("pvt_bundle,mos_corner,res_corner,cap_corner,temp_c,band_code,vctrl_v,period_s,freq_hz\n")
    for r in rows:
        f.write(",".join(r) + "\n")
orig = {tuple(r[:2] + r[5:7]): r for r in csv.reader((RECORD / "corners" / "results.csv").open()) if r[0] != "pvt_bundle"}
na = [r for r in rows if r[7] == "NA"]
same = diff = 0
for r in rows:
    o = orig.get(tuple(r[:2] + r[5:7]))
    if o and o[7] == r[7]:
        same += 1
    else:
        diff += 1
        print("DIFF", r[:2] + r[5:8], "orig", o and o[7])
print(f"wrote {dst}: {len(rows)} rows, {len(na)} NA, identical-period-to-RECORD-001 {same}, differing {diff}")
