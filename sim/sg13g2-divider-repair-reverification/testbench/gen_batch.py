#!/usr/bin/env python3
"""Generate the klt sim requests (+ the hold/opconv bench bodies) for
sim/sg13g2-divider-repair-reverification RECORD-002 (issue #235).
Pure text generation; runs nothing.  The func body (tb_div_func_batch.sp) is
committed by hand and is shared with the probe request.
Writes ../requests/*.request.json, tb_dff_hold_batch.sp, tb_opconv_{none,ic}.sp."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
REQ = os.path.join(HERE, "..", "requests")
OSDI = [f"$PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/osdi/{o}.osdi"
        for o in ("psp103", "psp103_nqs", "mosvar", "r3_cmc")]
LIB = {"pdk": "ihp-sg13g2", "lib": "libs.tech/ngspice/models/cornerMOShv.lib"}
TPER = 10e-9
OPTS = {"osdi_preload": OSDI, "timeout_s": 1800, "keep_artifacts": True}

# The 9-point reduced matrix of RECORD-001 as three one-factor requests.
MATRIX = {
    "mos5": ({"process": ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"], "temperature_c": [27]}, [3.3]),
    "temp": ({"process": ["mos_tt"], "temperature_c": [-40, 125]}, [3.3]),
    "vdd":  ({"process": ["mos_tt"], "temperature_c": [27]}, [2.97, 3.63]),
}

def dump(name, req):
    with open(os.path.join(REQ, name + ".request.json"), "w") as f:
        json.dump(req, f, indent=2); f.write("\n")

def func_meas(nnom, divb=3, diva=2):
    tstop = (divb + 0.4) * nnom * TPER; tmeas = 1.05 * nnom * TPER
    m = []
    for sig, nm in [(f"v(xdiv.ck{k})", f"ck{k}") for k in range(1, 6)] + [("v(divout)", "dvo"), ("v(fb)", "fb")]:
        for fn in ("max", "min"):
            m.append({"name": f"{nm}_{fn}", "spice": f".meas tran {nm}_{fn} {fn} {sig} from={tmeas:.6e} to={tstop:.6e}"})
    m += [{"name": "tdiv_a", "spice": f".meas tran tdiv_a when v(divout)='vdd_p/2' rise={diva}"},
          {"name": "tdiv_b", "spice": f".meas tran tdiv_b when v(divout)='vdd_p/2' rise={divb}"},
          {"name": "tck_a", "spice": ".meas tran tck_a when v(ck)='vdd_p/2' rise=3"},
          {"name": "tck_b", "spice": ".meas tran tck_b when v(ck)='vdd_p/2' rise=4"},
          {"name": "idd", "spice": f".meas tran idd avg i(vdd) from={tmeas:.6e} to={tstop:.6e}"}]
    return m, tstop

def func_req(corners, params, word, nnom, reltol=None, exclude=None):
    m, tstop = func_meas(nnom)
    c = dict(corners); c["params"] = dict(params)
    n = len(c["params"]["vdd_p"])  # params arrays are zipped, not crossed
    c["params"].update({f"b{i}": [(word >> i) & 1] * n for i in range(6)})
    o = dict(OPTS)
    if reltol is not None: o["ngspice_options"] = {"reltol": reltol}
    r = {"engine": "ngspice", "backend": "batch", "netlist": "../testbench/tb_div_func_batch.sp",
         "models": LIB, "corners": c,
         "analysis": {"kind": "tran", "args": f"{0.03 * TPER:.6e} {tstop:.6e}"},
         "measurements": m, "options": o}
    if exclude: r["exclude"] = exclude
    return r

# ---- func: baseline (word 0, N=64), code sweep (tt/27/3.3), edge, tol -------
for k, (c, vdds) in MATRIX.items():
    dump(f"func_baseline_{k}", func_req(c, {"vdd_p": vdds}, 0, 64))
for word, nnom in [(1, 65), (2, 66), (4, 68), (8, 72), (16, 80), (32, 96), (31, 95), (42, 106), (63, 127)]:
    dump(f"func_code_{word:06b}", func_req({"process": ["mos_tt"], "temperature_c": [27]}, {"vdd_p": [3.3]}, word, nnom))
for mos, t in [("mos_ss", 125), ("mos_ff", -40)]:
    dump(f"func_edge_{mos}_{t}", func_req({"process": [mos], "temperature_c": [t]}, {"vdd_p": [3.3]}, 63, 127))
tolc = {"process": ["mos_tt", "mos_ss"], "temperature_c": [27, 125]}
tolx = [{"process": "mos_tt", "temperature_c": 125}, {"process": "mos_ss", "temperature_c": 27}]
for rt in (0.001, 0.002, 0.005):
    dump(f"func_tol_{rt}", func_req(tolc, {"vdd_p": [3.3]}, 0, 64, reltol=rt, exclude=tolx))

# ---- hold --------------------------------------------------------------------
HOLD = """* sg13g2-pll :: sim/sg13g2-divider-repair-reverification (issue #235): one dff_tg_hv latch hold.
* Circuit BODY for klt sim; same stimulus/.ic/measure as tb_dff_hold.sp.tmpl.
.options reltol=0.001
.global sub!
.include ../netlist-snapshots/divider_chain_repaired.spice
.param vdd_p=3.3
Vdd vdd 0 dc 'vdd_p'
Vsub sub! 0 dc 0
Vd d 0 dc 'vdd_p'
Vclk clk 0 pwl 0 0 0.9n 0 1.0n 'vdd_p' 1.9n 'vdd_p' 2.0n 0
Xdut d clk q vdd 0 dff_tg_hv
.ic v(xdut.m)=0 v(xdut.s)=0
.save v(q) v(xdut.s)
"""
open(os.path.join(HERE, "tb_dff_hold_batch.sp"), "w").write(HOLD)
hm = [{"name": "q_end", "spice": ".meas tran q_end find v(q) at=41.9n"},
      {"name": "s_end", "spice": ".meas tran s_end find v(xdut.s) at=41.9n"},
      {"name": "t_decay", "spice": ".meas tran t_decay when v(q)='0.9*vdd_p' fall=1 td=2.0n"}]
for k, (c, vdds) in MATRIX.items():
    cc = dict(c); cc["params"] = {"vdd_p": vdds}
    dump(f"hold_{k}", {"engine": "ngspice", "backend": "batch", "netlist": "../testbench/tb_dff_hold_batch.sp",
                       "models": LIB, "corners": cc, "analysis": {"kind": "tran", "args": "20p 42n"},
                       "measurements": hm, "options": dict(OPTS)})

# ---- opconv ------------------------------------------------------------------
OP = """* sg13g2-pll :: sim/sg13g2-divider-repair-reverification (issue #235): DC OP convergence, ic={ic}.
.global sub!
.include ../netlist-snapshots/divider_chain_repaired.spice
Vdd vdd 0 dc 3.3
Vsub sub! 0 dc 0
Vck ck 0 dc 0
Vp0 p0 0 dc 0
Vp1 p1 0 dc 0
Vp2 p2 0 dc 0
Vp3 p3 0 dc 0
Vp4 p4 0 dc 0
Vp5 p5 0 dc 0
Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain
{ics}"""
ics = "".join(f".ic v(xdiv.xd{d}.xdffq.m)=0 v(xdiv.xd{d}.xdffq.s)=0 v(xdiv.xd{d}.xdffm.m)=0 v(xdiv.xd{d}.xdffm.s)=0\n"
              for d in range(6)) + ".ic v(xdiv.xfrt.m)=0 v(xdiv.xfrt.s)=0\n"
for ic, txt in (("none", ""), ("ic", ics)):
    open(os.path.join(HERE, f"tb_opconv_{ic}.sp"), "w").write(OP.format(ic=ic, ics=txt))
    dump(f"opconv_{ic}", {"engine": "ngspice", "backend": "batch", "netlist": f"../testbench/tb_opconv_{ic}.sp",
         "models": LIB, "corners": {"process": ["mos_tt"], "temperature_c": [27]},
         "analysis": {"kind": "op", "args": ""},
         "measurements": [{"name": "divout", "expr": "v(divout)", "unit": "V"},
                          {"name": "fb", "expr": "v(fb)", "unit": "V"}],
         "options": dict(OPTS)})
