#!/usr/bin/env python3
"""Regenerate the three klt sim request files in this directory.

    PDK_ROOT=<parent of ihp-sg13cmos5l> python3 gen_requests.py

mc.request.json                the campaign: 5 mismatch-enabled process
                               corners x 3 temperatures x N=100, seed 178,
                               batch backend.
negative_control.request.json  mos_tt (NO mismatch section) x 27 C x 20
                               samples, local: every spread must be exactly 0.
positive_probe.request.json    mos_tt_mismatch x 27 C x 3 samples, local: the
                               spread must be non-zero (the mismatch section
                               is live under this exact netlist).

All three share one measurement block and one options block, so a control
exercises the same deck path as the campaign.

models.pdk is deliberately omitted: klt's batch backend refuses the
`ihp-sg13cmos5l` variant (2AMLogic/klayout-tools#2727); a request without
models.pdk is accepted, and options.stage_model_inputs ships the SG13CMOS5L
model library and OSDI binaries with the job.
"""
import json, os, pathlib

pdk_root = os.environ.get("PDK_ROOT", "/home/ubuntu/share/pdk")
tech = f"{pdk_root}/ihp-sg13cmos5l/libs.tech/ngspice"
here = pathlib.Path(__file__).resolve().parent

base = {
    "engine": "ngspice",
    "netlist": "tb_cp_mc.sp",
    "models": {"lib": f"{tech}/models/cornerMOShv.lib"},
    "analysis": {"kind": "dc", "args": "Vup 0 3.3 3.3"},
    "measurements": [
        {"name": "iup_a", "unit": "A", "expr": "i(Vout)[1]"},
        {"name": "idn_a", "unit": "A", "expr": "i(Vout)[0]"},
        # (Iup + Idn) / mean(|Iup|, |Idn|), Idn < 0.  Limit: see README
        # "Limit" -- an evidence-derived screening limit, NOT a ratified
        # spec number (spec row 7 proposes none).
        {"name": "mismatch_pct", "unit": "%",
         "expr": "(i(Vout)[1] + i(Vout)[0]) / ((i(Vout)[1] - i(Vout)[0]) / 2) * 100",
         "limits": {"min": -3.5, "max": 3.5}},
    ],
    "options": {
        "osdi_preload": [f"{tech}/osdi/{n}.osdi"
                         for n in ("psp103", "psp103_nqs", "mosvar")],
        "stage_model_inputs": True,
        "ngspice_init": ["set numdgt=12"],
        "timeout_s": 600,
    },
}

def emit(name, **over):
    r = json.loads(json.dumps(base))
    r.update(over)
    (here / name).write_text(json.dumps(r, indent=2) + "\n")

emit("mc.request.json", backend="batch",
     corners={"process": [f"mos_{c}_mismatch" for c in ("tt", "ss", "ff", "sf", "fs")],
              "temperature_c": [-40, 27, 125]},
     monte_carlo={"n": 100, "seed": 178, "vary": "mismatch",
                  "quantiles": [0.5, 5, 50, 95, 99.5]})
emit("negative_control.request.json", backend="local",
     corners={"process": ["mos_tt"], "temperature_c": [27]},
     monte_carlo={"n": 20, "seed": 178, "vary": "mismatch"})
emit("positive_probe.request.json", backend="local",
     corners={"process": ["mos_tt_mismatch"], "temperature_c": [27]},
     monte_carlo={"n": 3, "seed": 178, "vary": "mismatch"})
