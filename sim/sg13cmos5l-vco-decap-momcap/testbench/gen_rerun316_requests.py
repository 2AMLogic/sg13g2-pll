#!/usr/bin/env python3
"""Generate the `klt sim` batch requests for the RECORD-002 rerun (#316).

    PDK_ROOT=<parent of ihp-sg13cmos5l> python3 -I gen_rerun316_requests.py OUTDIR

Reruns RECORD-001's grid as four requests under OUTDIR/<name>/ (each holds
`deck.cir` and `request.json`), submitted together with `klt sim --batch-set`:

  extract      cap_cmomi w=70u l=70u AC extraction at -40/27/125 C (3 units)
  pole_m20     R_src=3000 ohm single-pole network, delta cap = -20% of C_nom
  pole_p00     same, delta cap 0
  pole_p20     same, delta cap = +20% of C_nom

C_nom is RECORD-001's committed 27 C extraction (5.286175e-12 F), the value
run.sh feeds into its own delta caps, so the pole decks match the original
grid.  Differences from run.sh, disclosed in RECORD-002: the -3 dB frequency
is ngspice's `.meas ... WHEN` crossing (not run.sh's log-frequency
interpolation), and C is read at 100 kHz from `.meas`.
"""
import json, os, pathlib, sys

out = pathlib.Path(sys.argv[1]).resolve()
pdk_root = os.environ.get("PDK_ROOT", "/home/ubuntu/share/pdk")
tech = f"{pdk_root}/ihp-sg13cmos5l/libs.tech/ngspice"
C_NOM = 5.286175e-12
RSRC = 3000
CAP = "cap_cmomi w=70u l=70u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1"

EXTRACT = f"""* RECORD-002 (#316): vco.XCDECAP AC extraction
.include {tech}/models/cap_cmomi.lib
.option scale=1
Xcap n1 0 {CAP}
Rbleed n1 0 1e14
Iac n1 0 dc 0 ac 1
"""
POLE = """* RECORD-002 (#316): R_src-C_decap single-pole network, delta cap {delta:.6e} F
.include {tech}/models/cap_cmomi.lib
.option scale=1
Vsrc vdd 0 dc 0 ac 1
Rsrc vdd vdd_vco {rsrc}
Xcdecap vdd_vco 0 {cap}
Cdelta vdd_vco 0 {delta:.6e}
"""

def request(meas, ac_args, temps):
    return {
        "engine": "ngspice", "netlist": "deck.cir",
        "models": {"pdk": "ihp-sg13cmos5l"},
        "analysis": {"kind": "ac", "args": ac_args},
        "measurements": meas,
        "options": {
            "osdi_preload": [f"{tech}/osdi/{n}.osdi"
                             for n in ("cap_cmomi", "cap_cmomf", "r3_cmc")],
            "stage_model_inputs": True,
            "ngspice_init": ["set numdgt=12"],
            "timeout_s": 600},
        "backend": "batch",
        "batch": {"capacity_wait_s": 600},
        "corners": {"temperature_c": temps},
    }

reqs = {
    "extract": (EXTRACT, request(
        [{"name": "im_z_100k", "unit": "ohm",
          "spice": ".meas ac im_z_100k FIND vi(n1) AT=100k"},
         {"name": "cdecap_f", "unit": "F",
          "spice": ".meas ac cdecap_f PARAM='-1/(2*3.14159265*100k*im_z_100k)'"}],
        "dec 5 1k 100k", [-40, 27, 125])),
}
for tag, frac in (("m20", -0.20), ("p00", 0.0), ("p20", 0.20)):
    reqs[f"pole_{tag}"] = (
        POLE.format(delta=C_NOM * frac, tech=tech, rsrc=RSRC, cap=CAP),
        request([{"name": "pole_hz_db3", "unit": "Hz",
                  "spice": ".meas ac pole_hz_db3 WHEN vdb(vdd_vco)=-3.0103 CROSS=1"}],
                "dec 20 1 1000meg", [27]))

for name, (deck, req) in reqs.items():
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "deck.cir").write_text(deck + ".end\n")
    (d / "request.json").write_text(json.dumps(req, indent=2) + "\n")
    print("wrote", d / "request.json")
