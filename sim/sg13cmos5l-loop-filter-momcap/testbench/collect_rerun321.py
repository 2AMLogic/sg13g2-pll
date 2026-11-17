#!/usr/bin/env python3
"""Collect the issue-#321 batch outdir into new rerun CSVs (never touches the originals).

  python3 -I collect_rerun321.py <klt-sim outdir>

Same arithmetic as run.sh: R1 from `rval`, C1/C2 nominal from the last row of the
AC table (27 C), then the -20/0/+20 % uniform MOM band.  Writes
../corners/results_rerun321.csv (as-drawn) and ../corners/results_resized_rerun321.csv,
and prints a max-relative-difference comparison against the original CSVs.
"""
import csv, json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORN = HERE.parent / "corners"
out = Path(sys.argv[1])
man = json.loads((HERE / "rerun321" / "manifest.json").read_text())


def rval(uid):
    for ln in (out / uid / "stdout.bin").read_text().splitlines():
        if ln.startswith("rval"):
            return float(ln.split()[2])
    raise SystemExit(f"no rval in {uid}")


def cval(uid):
    rows = [ln.split() for ln in (out / uid / "stdout.bin").read_text().splitlines()
            if re.match(r"^\d+\s", ln)]
    return float(rows[-1][2])


c1, c2 = cval("c_c1_27"), cval("c_c2_27")
print(f"C1={c1:.6e} C2={c2:.6e} (27C)")
for cn in ("c1", "c2"):
    print(cn, "T-invariance:", [f"{cval(f'c_{cn}_{t}'):.6e}" for t in ("m40", "27", "125")])
hdr = "res_corner,temp_c,mom_frac,r1_ohm,c1_f,c2_f,fz_hz,fp_hz"
for geom, name, orig in (("asdrawn", "results_rerun321.csv", "results.csv"),
                         ("resized", "results_resized_rerun321.csv", "results_resized.csv")):
    lines = [hdr]
    for corner in ("res_typ", "res_bcs", "res_wcs"):
        for t in (-40, 27, 125):
            r1 = rval(f"r_{geom}_{corner}_{str(t).replace('-', 'm')}")
            for frac in (-0.20, 0.00, 0.20):
                a, b = c1 * (1 + frac), c2 * (1 + frac)
                fz = 1 / (2 * math.pi * r1 * a)
                fp = (a + b) / (2 * math.pi * r1 * a * b)
                lines.append(f"{corner},{t},{frac:.2f},{r1:.6e},{a:.6e},{b:.6e},{fz:.6e},{fp:.6e}")
    (CORN / name).write_text("\n".join(lines) + "\n")
    new = list(csv.DictReader(lines))
    old = list(csv.DictReader((CORN / orig).read_text().splitlines()))
    assert len(new) == len(old) == 27
    for col in ("r1_ohm", "c1_f", "c2_f", "fz_hz", "fp_hz"):
        d = [abs(float(n[col]) / float(o[col]) - 1) for n, o in zip(new, old)]
        print(f"{geom} {col}: max rel diff {max(d):.3e} min {min(d):.3e}")
    fz = [float(r["fz_hz"]) for r in new]
    print(f"{geom} fz range {min(fz):.4e}..{max(fz):.4e}; nominal R1 "
          f"{[float(r['r1_ohm']) for r in new if r['res_corner']=='res_typ' and r['temp_c']=='27'][0]:.6e}")
