#!/usr/bin/env python3
"""Render the RECORD-003 grid (#188, XBUF1 P=8.5u) as a `klt sim` deck-list request.

    python3 -I gen_issue188_requests.py OUTDIR

Writes OUTDIR/request.json, OUTDIR/decks/<id>.sp (308 decks: the 300-point
grid of run.sh plus its 8 timestep-convergence points), OUTDIR/decks/vco_open.spice
(the XCDECAP-stripped copy of the frozen snapshot, same derivation as
run.sh) and OUTDIR/decks.sha256.csv.  Decks are the original
tb_vco_duty.sp.tmpl with the substitutions run.sh makes; the only changes
are PDK-relative ($PDK_ROOT, expanded by the fleet runner) library paths and
a `.control` block of `pre_osdi` lines after the title (run.sh's
.spiceinit has no deck-list equivalent).  Submit with:

    klt sim OUTDIR/request.json --backend batch --wait-for-capacity 600 -o RESULTS
"""
import csv, hashlib, json, pathlib, re, sys

here = pathlib.Path(__file__).resolve().parent
snap = here.parent / "netlist-snapshots" / "vco_issue188.spice"
out = pathlib.Path(sys.argv[1]).resolve()
(out / "decks").mkdir(parents=True, exist_ok=True)

(out / "decks" / "vco_open.spice").write_text(
    re.sub(r"^(XCDECAP)", r"*\1", snap.read_text(), flags=re.M))

tmpl = (here / "tb_vco_duty.sp.tmpl").read_text()
pdk = "$PDK_ROOT/ihp-sg13cmos5l"
osdi = [f"pre_osdi {pdk}/libs.tech/ngspice/osdi/{n}.osdi"
        for n in ("psp103", "psp103_nqs", "mosvar", "r3_cmc")]

PAIRS = [("mos_tt", "res_typ"), ("mos_ss", "res_wcs"), ("mos_ff", "res_bcs"),
         ("mos_sf", "res_typ"), ("mos_fs", "res_typ")]
TEMPS = [-40, 27, 125]
BANDS = [("00", "0.0", "0.0"), ("10", "3.3", "0.0"),
         ("01", "0.0", "3.3"), ("11", "3.3", "3.3")]
VCTRL = ["0.3", "0.9", "1.5", "2.1", "2.7"]

units = []  # (id, mos, res, temp, band, b0v, b1v, vctrl, tstep)
for mos, res in PAIRS:
    for t in TEMPS:
        for b, b0, b1 in BANDS:
            for v in VCTRL:
                units.append((f"grid_{mos}_{t}_{b}_{v}", mos, res, t, b, b0, b1, v, "20p"))
for tstep in ("20p", "5p"):
    for mos, res, t, b, b0, b1, v in (
            ("mos_tt", "res_typ", 27, "00", "0.0", "0.0", "1.5"),
            ("mos_sf", "res_typ", 27, "11", "3.3", "3.3", "2.7"),
            ("mos_fs", "res_typ", 27, "11", "3.3", "3.3", "2.7"),
            ("mos_ss", "res_wcs", 125, "00", "0.0", "0.0", "0.9")):
        units.append((f"conv_{tstep}_{mos}_{t}_{b}_{v}", mos, res, t, b, b0, b1, v, tstep))

decks, rows = [], []
for uid, mos, res, t, b, b0, b1, v, tstep in units:
    s = tmpl
    for k, val in (("@CORNER_MOS@", mos), ("@CORNER_RES@", res), ("@TEMP@", str(t)),
                   ("@VCTRL@", v), ("@B0V@", b0), ("@B1V@", b1), ("@TSTEP@", tstep),
                   ("@PDK_ROOT@/@PDK@", pdk)):
        s = s.replace(k, val)
    first, rest = s.split("\n", 1)
    s = first + "\n.control\n" + "\n".join(osdi) + "\n.endc\n" + rest
    p = out / "decks" / f"{uid}.sp"
    p.write_text(s)
    rows.append((uid, mos, res, t, b, v, tstep, hashlib.sha256(s.encode()).hexdigest()))
    decks.append({"id": uid, "deck": f"decks/{uid}.sp",
                  "timeout_s": 900})

req = {"backend": "batch", "engine": "ngspice",
       "models": {"pdk": "ihp-sg13cmos5l"},
       "decks": decks,
       "batch": {"capacity_wait_s": 600},
       "options": {"timeout_s": 900}}
(out / "request.json").write_text(json.dumps(req, indent=2) + "\n")
with open(out / "decks.sha256.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "mos_corner", "res_corner", "temp_c", "band_code", "vctrl_v",
                "tstep", "deck_sha256"])
    w.writerows(rows)
print(f"wrote {len(decks)} decks to {out}")
