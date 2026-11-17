#!/usr/bin/env python3
"""Render the issue-#321 rerun of RECORD-001/-002 as `klt sim` batch `decks[]` requests.

`run.sh` loops `ngspice -b` locally, which dispatch hosts forbid for grids.
This renders the SAME single-device decks `run.sh` rendered (same templates,
same matrix) into pre-composed decks that `klt sim --backend batch` runs
verbatim.  It does not touch `run.sh` or any original `corners/*.csv`.

  rerun321/decks/<id>.sp   one rendered deck per unit
  probe.request.json       single-corner probe (as-drawn R1, res_typ, 27 C)
  rerun321.request.json    full grid: 18 R decks (2 geometries x 3 res corners
                           x 3 temps) + 6 C decks (C1/C2 x 3 temps)
  rerun321/manifest.json   unit id -> metadata (read by collect_rerun321.py)

Usage: python3 -I gen_rerun321.py   (idempotent; run from anywhere)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTD = HERE / "rerun321"
DECKS = OUTD / "decks"
PDK = "ihp-sg13cmos5l"
TECH = f"$PDK_ROOT/{PDK}/libs.tech/ngspice"
OSDI = [f"{TECH}/osdi/{n}.osdi" for n in ("cap_cmomi", "cap_cmomf", "r3_cmc")]
GEOMS = {"asdrawn": ("4u", "120u"), "resized": ("0.6u", "810u")}
RES_CORNERS = ["res_typ", "res_bcs", "res_wcs"]
TEMPS = [-40, 27, 125]
CAPS = {"c1": ("40u", "40u"), "c2": ("10u", "10u")}
TIMEOUT_S = 1800


def render(tmpl, **kw):
    text = (HERE / tmpl).read_text()
    text = text.replace("@PDK_ROOT@/@PDK@", f"$PDK_ROOT/{PDK}")
    for k, v in kw.items():
        text = text.replace(f"@{k}@", str(v))
    assert "@" not in "".join(l for l in text.splitlines() if not l.startswith("*")), tmpl
    pre = "\n".join(f"pre_osdi {p}" for p in OSDI)
    return text.replace(".control\n", f".control\n{pre}\n", 1)


def tag(t):
    return str(t).replace("-", "m")


units, manifest = [], {}


def add(uid, text, meta):
    DECKS.mkdir(parents=True, exist_ok=True)
    (DECKS / f"{uid}.sp").write_text(text)
    units.append({"id": uid, "deck": f"rerun321/decks/{uid}.sp", "timeout_s": TIMEOUT_S})
    manifest[uid] = meta


for gname, (w, l) in GEOMS.items():
    for corner in RES_CORNERS:
        for t in TEMPS:
            uid = f"r_{gname}_{corner}_{tag(t)}"
            add(uid, render("tb_extract_r.sp.tmpl", RES_CORNER=corner, TEMP=t, W=w, L=l),
                {"kind": "r", "geom": gname, "corner": corner, "temp": t, "w": w, "l": l})
for cname, (w, l) in CAPS.items():
    for t in TEMPS:
        uid = f"c_{cname}_{tag(t)}"
        add(uid, render("tb_extract_c.sp.tmpl", W=w, L=l, TEMP=t),
            {"kind": "c", "cap": cname, "temp": t, "w": w, "l": l})


def request(decks):
    return {"engine": "ngspice", "backend": "batch", "models": {"pdk": PDK},
            "decks": decks, "options": {"timeout_s": TIMEOUT_S},
            "batch": {"capacity_wait_s": 600}}


probe = [u for u in units if u["id"] == "r_asdrawn_res_typ_27"]
(HERE / "probe.request.json").write_text(json.dumps(request(probe), indent=2) + "\n")
(HERE / "rerun321.request.json").write_text(json.dumps(request(units), indent=2) + "\n")
(OUTD / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(len(units), "units")
