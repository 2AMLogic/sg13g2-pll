#!/usr/bin/env python3
"""Render the RECORD-001 matrix as pre-composed decks + a `klt sim` decks request.

Issue #237 (superseded rerun of RECORD-001).  No shell loop runs ngspice: the
decks go to the batch fleet as one `klt sim --backend batch` request
(see run_rerun.sh).  Same bench: decks are rendered from tb_vco_kvco.sp.tmpl
and include the frozen ../netlist-snapshots/vco.spice (staged as vco.spice).

  gen_rerun.py [--probe] [--outdir DIR]
    --probe   emit one deck only (typ / 00 / VCTRL=1.5) as probe.request.json
"""
import argparse, json, pathlib, shutil

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent
BUNDLES = [("typ", "mos_tt", "res_typ", "cap_typ", "27"),
           ("slow", "mos_ss", "res_wcs", "cap_wcs", "125"),
           ("fast", "mos_ff", "res_bcs", "cap_bcs", "-40")]
BANDS = [("00", "0.0", "0.0"), ("10", "3.3", "0.0"), ("01", "0.0", "3.3"), ("11", "3.3", "3.3")]
VCTRLS = ["0.3", "0.9", "1.5", "2.1", "2.7"]
OSDI = ["psp103", "psp103_nqs", "mosvar", "r3_cmc"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--outdir", default=str(HERE / "rerun"))
    a = ap.parse_args()
    out = pathlib.Path(a.outdir)
    decks_dir = out / ("probe-decks" if a.probe else "decks")
    if decks_dir.exists():
        shutil.rmtree(decks_dir)
    decks_dir.mkdir(parents=True)
    # byte-identical copy of the frozen snapshot beside the decks: a decks request
    # ships the deck verbatim and stages `.include vco.spice` from the deck's dir.
    shutil.copyfile(RECORD / "netlist-snapshots" / "vco.spice", decks_dir / "vco.spice")
    tmpl = (HERE / "tb_vco_kvco.sp.tmpl").read_text()
    # ngspice parses .lib/.include itself; the runner expands $PDK_ROOT (klt sim
    # "Preservation and isolation"); OSDI objects are preloaded via pre_osdi.
    pre = "".join(f"pre_osdi $PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/osdi/{o}.osdi\n" for o in OSDI)
    decks = []
    for bname, mos, res, cap, temp in BUNDLES:
        for blabel, b0, b1 in BANDS:
            for v in VCTRLS:
                if a.probe and not (bname, blabel, v) == ("typ", "00", "1.5"):
                    continue
                uid = f"{bname}_b{blabel}_v{v.replace('.', 'p')}"
                t = (tmpl.replace("@CORNER_MOS@", mos).replace("@CORNER_RES@", res)
                     .replace("@CORNER_CAP@", cap).replace("@TEMP@", temp)
                     .replace("@VCTRL@", v).replace("@B0V@", b0).replace("@B1V@", b1)
                     .replace("@DUT@", "vco.spice")
                     .replace("@PDK_ROOT@", "$PDK_ROOT").replace("@PDK@", "ihp-sg13g2"))
                t = t.replace(".control\nrun", ".control\n" + pre + "run")
                (decks_dir / f"{uid}.sp").write_text(t)
                decks.append({"id": uid, "deck": f"{decks_dir.name}/{uid}.sp",
                              "timeout_s": 1800})
    req = {"engine": "ngspice", "backend": "batch", "models": {"pdk": "ihp-sg13g2"},
           "decks": decks, "options": {"timeout_s": 1800, "max_workers": 2}}
    name = "probe.request.json" if a.probe else "rerun.request.json"
    (out / name).write_text(json.dumps(req, indent=2) + "\n")
    print(f"wrote {len(decks)} decks, {out / name}")

main()
