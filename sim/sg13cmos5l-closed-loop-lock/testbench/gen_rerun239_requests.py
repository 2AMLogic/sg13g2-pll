#!/usr/bin/env python3
"""Generate the `klt sim` batch requests for the RECORD-013 rerun grid (#239).

    PDK_ROOT=<parent of ihp-sg13cmos5l> python3 -I gen_rerun239_requests.py OUTDIR

One request per remaining closed-loop RECORD-006 variant (control_hist,
ideal_sw, ideal_dump_ofs, reset_narrow, reset_wide).  Each OUTDIR/<variant>/
holds the circuit body (`pll.cir`, the diagnostic deck minus its .lib/.tran/
.control cards), the variant bundle from cpdiag_build.py (built from the
FROZEN cp_cascbias.spice / pfd.spice snapshots, not today's cp) and
`request.json`.  Only quantities a request can express as measurements are
declared (supply currents and vctrl average, the template's own .meas
values); the lock/phase-error metrics need the raw wrdata trace and
cpdiag_post.py, which a batch report does not return, so a batch result from
these requests could NOT reproduce RECORD-006's phase-error figures.
Nominal corner only (mos_tt, res_typ, 27 C, 3.3 V).
"""
import json, os, pathlib, re, subprocess, sys

here = pathlib.Path(__file__).resolve().parent
snap = here.parent / "netlist-snapshots"
out = pathlib.Path(sys.argv[1]).resolve()
pdk_root = os.environ.get("PDK_ROOT", "/home/ubuntu/share/pdk")
tech = f"{pdk_root}/ihp-sg13cmos5l/libs.tech/ngspice"
VARS = ["control_hist", "ideal_sw", "ideal_dump_ofs", "reset_narrow", "reset_wide"]
VDD, TREF = "3.3", 1 / 20e6
SUBS = {"@TEMP@": "27", "@VDD@": VDD, "@TREF@": f"{TREF:.6e}",
        "@TREFH@": f"{TREF / 2 - 100e-12:.6e}", "@IREF@": "10u",
        "@B0V@": VDD, "@B1V@": VDD, "@VC0@": "2.46"}

for v in VARS:
    d = out / v
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-I", str(here / "cpdiag_build.py"), v,
                    str(snap), str(d)], check=True)
    if v == "control_hist":
        (d / "pll_blocks_prop_cascbias.spice").write_text(
            (d / "pll_blocks_cpdiag.spice").read_text())
        tmpl = here / "tb_pll_proposal_cascbias.sp.tmpl"
    else:
        tmpl = here / "tb_pll_cpdiag.sp.tmpl"
    keep = []
    for ln in tmpl.read_text().splitlines():
        if ln.startswith(".control"):
            break
        if ln.startswith((".lib ", ".tran")):
            continue
        keep.append(ln)
    body = "\n".join(keep) + "\n"
    for k, val in SUBS.items():
        body = body.replace(k, val)
    body = body.replace("\n.end\n", "\n")
    # the Part-B template's own cornerRES include moves into the body
    first, rest = body.split("\n", 1)
    body = first + "\n.lib " + tech + "/models/cornerRES.lib res_typ\n" + rest
    (d / "pll.cir").write_text(body)
    meas = [{"name": n, "unit": u, "spice": f".meas tran {n} avg {e} from=2000n to=2500n"}
            for n, e, u in (("i_pfd", "i(Vdd_pfd)", "A"), ("i_cp", "i(Vdd_cp)", "A"),
                            ("i_vco", "i(Vdd_vco)", "A"), ("i_ld", "i(Vdd_ld)", "A"),
                            ("vc_avg", "v(vctrl)", "V"))]
    req = {
        "engine": "ngspice", "netlist": "pll.cir",
        "models": {"lib": f"{tech}/models/cornerMOShv.lib"},
        "analysis": {"kind": "tran", "args": "100p 2500n 0 100p"},
        "measurements": meas,
        "options": {
            "osdi_preload": [f"{tech}/osdi/{n}.osdi"
                             for n in ("psp103", "psp103_nqs", "mosvar", "r3_cmc")],
            "stage_model_inputs": True, "timeout_s": 3600},
        "backend": "batch",
        "corners": {"process": ["mos_tt"], "temperature_c": [27]},
    }
    (d / "request.json").write_text(json.dumps(req, indent=2) + "\n")
    print("wrote", d / "request.json")
