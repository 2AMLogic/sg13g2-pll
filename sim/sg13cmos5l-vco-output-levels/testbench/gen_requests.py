#!/usr/bin/env python3
"""Render the vco output-levels grid (issue #190, spec row 14) as a `klt sim`
deck-list request.

    python3 -I gen_requests.py OUTDIR

Writes OUTDIR/request.json, OUTDIR/decks/<id>.sp, OUTDIR/decks/vco_open.spice
(the XCDECAP-stripped copy of ../netlist-snapshots/vco.spice) and
OUTDIR/decks.sha256.csv.  Grid: 3 PVT bundles (tt/typ, ss/wcs, ff/bcs) x
3 temperatures x 2 band codes (00, 11) x 3 VCTRL points = 54 transients.
Submit with (see run.sh):

    klt sim OUTDIR/request.json --backend batch --wait-for-capacity 600 -o RESULTS
"""
import csv, hashlib, json, pathlib, re, sys

here = pathlib.Path(__file__).resolve().parent
snap = here.parent / "netlist-snapshots" / "vco.spice"
out = pathlib.Path(sys.argv[1]).resolve()
(out / "decks").mkdir(parents=True, exist_ok=True)

(out / "decks" / "vco_open.spice").write_text(
    re.sub(r"^(XCDECAP)", r"*\1", snap.read_text(), flags=re.M))

tmpl = (here / "tb_vco_levels.sp.tmpl").read_text()
pdk = "$PDK_ROOT/ihp-sg13cmos5l"
osdi = [f"pre_osdi {pdk}/libs.tech/ngspice/osdi/{n}.osdi"
        for n in ("psp103", "psp103_nqs", "mosvar", "r3_cmc")]

BUNDLES = [("mos_tt", "res_typ"), ("mos_ss", "res_wcs"), ("mos_ff", "res_bcs")]
TEMPS = [-40, 27, 125]
BANDS = [("00", "0.0", "0.0"), ("11", "3.3", "3.3")]
VCTRL = ["0.3", "1.5", "2.7"]

decks, rows = [], []
for mos, res in BUNDLES:
    for t in TEMPS:
        for b, b0, b1 in BANDS:
            for v in VCTRL:
                uid = f"lvl_{mos}_{t}_{b}_{v}"
                s = tmpl
                for k, val in (("@CORNER_MOS@", mos), ("@CORNER_RES@", res),
                               ("@TEMP@", str(t)), ("@VCTRL@", v), ("@B0V@", b0),
                               ("@B1V@", b1), ("@TSTEP@", "20p"),
                               ("@PDK_ROOT@/@PDK@", pdk)):
                    s = s.replace(k, val)
                first, rest = s.split("\n", 1)
                s = first + "\n.control\n" + "\n".join(osdi) + "\n.endc\n" + rest
                (out / "decks" / f"{uid}.sp").write_text(s)
                rows.append((uid, mos, res, t, b, v, hashlib.sha256(s.encode()).hexdigest()))
                decks.append({"id": uid, "deck": f"decks/{uid}.sp", "timeout_s": 900})

req = {"backend": "batch", "engine": "ngspice",
       "models": {"pdk": "ihp-sg13cmos5l"},
       "decks": decks,
       "batch": {"capacity_wait_s": 600},
       "options": {"timeout_s": 900}}
(out / "request.json").write_text(json.dumps(req, indent=2) + "\n")
with open(out / "decks.sha256.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "mos_corner", "res_corner", "temp_c", "band_code", "vctrl_v",
                "deck_sha256"])
    w.writerows(rows)
print(f"wrote {len(decks)} decks to {out}")
