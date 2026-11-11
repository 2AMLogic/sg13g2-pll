#!/usr/bin/env python3
"""Generate the klt-sim batch requests that rerun RECORD-001/002 of this bench
(issue #232, Part of #212 / #199).

Historical DUT: ../../netlist-snapshots/divider_chain.spice is byte-identical
at 1d824d3 (RECORD-001), b8a14c8 (RECORD-002) and today's main (sha256
9cfc67ce...); the `fbfix` proposal variant is derived from it with the same
three-line edit the historical run.sh used (copied verbatim below).  The
repaired divider (divider_chain_repaired.spice) is NOT used.

Decks are the historical templates turned into netlist bodies + `.meas`
cards.  The PVT matrix is the historical reduced 9-point (setup: 3-bundle)
matrix, expressed as a crossed grid minus `exclude` rules; supply is a
`corners.params` value (`vddp`) because the historical decks scale their
stimulus with the rail.

    python3 gen_requests.py     # writes next to this file
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SNAP = HERE.parent.parent / "netlist-snapshots" / "divider_chain.spice"
PDK = "/home/ubuntu/share/pdk/ihp-sg13cmos5l"
OSDI = [f"{PDK}/libs.tech/ngspice/osdi/{n}.osdi" for n in ("psp103", "psp103_nqs", "mosvar")]
TPER_TOB = 640.20512e-12

OLD = ("XIM M MB VDD VSS inv_hv\nXTGFBM MB CLK CLKB M VDD VSS tgate_hv\n"
       "XTG2 M CLK CLKB S VDD VSS tgate_hv\nXIS S SB VDD VSS inv_hv\n"
       "XTGFBS SB CLKB CLK S VDD VSS tgate_hv\n")
NEW = ("XIM M MB VDD VSS inv_hv\nXIMF MB MFB VDD VSS inv_wk_hv\n"
       "XTGFBM MFB CLK CLKB M VDD VSS tgate_hv\nXTG2 M CLK CLKB S VDD VSS tgate_hv\n"
       "XIS S SB VDD VSS inv_hv\nXISF SB SFB VDD VSS inv_wk_hv\n"
       "XTGFBS SFB CLKB CLK S VDD VSS tgate_hv\n")
TAIL = ("\n* PROPOSAL-ONLY weak keeper inverter (see run.sh header). Not a\n"
        "* committed cell; exists only inside this record's work directory.\n"
        ".subckt inv_wk_hv A Y VDD VSS\n"
        "XMP Y A VDD VDD sg13_hv_pmos w=1.25u l=0.5u ng=1 m=1\n"
        "XMN Y A VSS VSS sg13_hv_nmos w=0.5u l=0.5u ng=1 m=1\n.ends\n")
src = SNAP.read_text()
assert OLD in src
(HERE / "divider_chain.spice").write_text(src)
(HERE / "divider_chain_fbfix.spice").write_text(src.replace(OLD, NEW) + TAIL)
VAR = {"asdrawn": "divider_chain.spice", "fbfix": "divider_chain_fbfix.spice"}

PVT9 = [("mos_tt", 27, 3.3), ("mos_ss", 27, 3.3), ("mos_ff", 27, 3.3), ("mos_sf", 27, 3.3),
        ("mos_fs", 27, 3.3), ("mos_tt", -40, 3.3), ("mos_tt", 125, 3.3),
        ("mos_tt", 27, 2.97), ("mos_tt", 27, 3.63)]
PVT3 = [("mos_tt", 27, 3.3), ("mos_ss", 125, 3.3), ("mos_ff", -40, 3.3)]
NOM = [("mos_tt", 27, 3.3)]
PROCS = ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"]


def corners(points):
    procs = sorted({p for p, _, _ in points}, key=PROCS.index)
    temps = sorted({t for _, t, _ in points})
    vdds = sorted({v for _, _, v in points})
    keep = set(points)
    ex = [{"process": p, "temperature_c": t, "params": {"vddp": v}}
          for p in procs for t in temps for v in vdds if (p, t, v) not in keep]
    return {"process": procs, "temperature_c": temps, "params": {"vddp": vdds}}, ex


def request(netlist, analysis, meas, points, *, timeout, budget=None, params=None):
    c, ex = corners(points)
    c["params"].update(params or {})
    opts = {"osdi_preload": OSDI, "stage_model_inputs": True,
            "ngspice_init": ["set numdgt=12", "set num_threads=1"], "timeout_s": timeout}
    if budget:
        opts["wall_clock_budget_s"] = budget
    r = {"engine": "ngspice", "netlist": netlist,
         "models": {"lib": f"{PDK}/libs.tech/ngspice/models/cornerMOShv.lib"},
         "analysis": analysis, "measurements": meas, "options": opts,
         "backend": "batch", "corners": c, "batch": {"capacity_wait_s": 600}}
    if ex:
        r["exclude"] = ex
    return r


def meas(name, card, unit):
    return {"name": name, "spice": card, "unit": unit}


def write(name, body, req):
    (HERE / f"{name}.sp").write_text(body)
    (HERE / f"{name}.request.json").write_text(json.dumps(req, indent=2) + "\n")


IC = "".join(
    f".ic v(xdiv.xd{d}.xdffq.m)=0 v(xdiv.xd{d}.xdffq.s)=0 "
    f"v(xdiv.xd{d}.xdffm.m)=0 v(xdiv.xd{d}.xdffm.s)=0\n" for d in range(6)
) + ".ic v(xdiv.xfrt.m)=0 v(xdiv.xfrt.s)=0\n"
PWORD = "".join(f"Vp{i} p{i} 0 dc 0\n" for i in range(6))
XDIV = "Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain\n"

for v, net in VAR.items():
    # ---- hold (RECORD-001 Finding 2) ----
    body = f"""* RECORD-001 hold stage rerun (issue #232), variant {v}
.option scale=1
.global sub!
.include {net}
.param vddp=3.3
Vdd vdd 0 dc 'vddp'
Vsub sub! 0 dc 0
Vd d 0 dc 'vddp'
Vclk clk 0 pwl 0 0 0.9n 0 1.0n 'vddp' 1.9n 'vddp' 2.0n 0
Xdut d clk q vdd 0 dff_tg_hv
.ic v(xdut.m)=0 v(xdut.s)=0
"""
    m = [meas("q_end", ".meas tran q_end find v(q) at=41.9n", "V"),
         meas("s_end", ".meas tran s_end find v(xdut.s) at=41.9n", "V"),
         meas("t_decay", ".meas tran t_decay when v(q)='0.9*vddp' fall=1 td=2.0n", "s")]
    write(f"hold_{v}", body,
          request(f"hold_{v}.sp", {"kind": "tran", "args": "20p 42n"}, m, PVT9, timeout=600))

    # ---- setup (RECORD-001 Finding 3) ----
    tcap = 30e-12 + 8 * TPER_TOB
    tsamp = tcap + 0.25 * TPER_TOB
    body = f"""* RECORD-001 setup stage rerun (issue #232), variant {v}
.option scale=1
.global sub!
.include {net}
.param vddp=3.3 tsu=300p tcap={tcap:.6e}
Vdd vdd 0 dc 'vddp'
Vsub sub! 0 dc 0
Vclk clk 0 pulse(0 'vddp' 0 60p 60p {0.5 * TPER_TOB:.6e} {TPER_TOB:.6e})
Vd d 0 pwl 0 0 'tcap - tsu - 15p' 0 'tcap - tsu + 15p' 'vddp'
Xdut d clk q vdd 0 dff_tg_hv
.ic v(xdut.m)=0 v(xdut.s)=0
"""
    write(f"setup_{v}", body, request(
        f"setup_{v}.sp", {"kind": "tran", "args": f"5p {tsamp + 20e-12:.6e}"},
        [meas("q_s", f".meas tran q_s find v(q) at={tsamp:.6e}", "V")], PVT3, timeout=600,
        params={"vddp": [3.3] * 6, "tsu": [300e-12, 200e-12, 130e-12, 80e-12, 40e-12, 0.0]}))

    # ---- opconv (RECORD-001 Finding 1): bare .op, with / without .ic ----
    for ic in ("none", "applied"):
        body = f"""* OP-convergence probe (issue #232) -- {v}, ic={ic}
.option scale=1
.global sub!
.include {net}
.param vddp=3.3
Vdd vdd 0 dc 'vddp'
Vsub sub! 0 dc 0
Vck ck 0 dc 0
{PWORD}{XDIV}{IC if ic == "applied" else ""}"""
        write(f"opconv_{v}_{ic}", body, request(
            f"opconv_{v}_{ic}.sp", {"kind": "op", "args": ""},
            [{"name": "divout", "expr": "v(divout)", "unit": "V"}], NOM, timeout=150))

    # ---- func baseline, 100 MHz, word 000000, N=64 (RECORD-001 Finding 4) ----
    tper = 10e-9
    ton = 0.44 * tper
    tstop = (3 + 0.4) * 64 * tper
    tmeas = 1.05 * 64 * tper
    body = f"""* func baseline rerun (issue #232), variant {v}, 100 MHz, word 000000
.option scale=1
.options reltol=0.005 vntol=1e-4 abstol=1e-9 trtol=7
.global sub!
.include {net}
.param vddp=3.3
Vdd vdd 0 dc 'vddp'
Vsub sub! 0 dc 0
Vck ck 0 pulse(0 'vddp' 0 60p 60p {ton:.6e} {tper:.6e})
{PWORD}{XDIV}{IC}"""
    cards = []
    for k in range(1, 6):
        cards += [meas(f"ck{k}_max", f".meas tran ck{k}_max max v(xdiv.ck{k}) from={tmeas:.6e} to={tstop:.6e}", "V"),
                  meas(f"ck{k}_min", f".meas tran ck{k}_min min v(xdiv.ck{k}) from={tmeas:.6e} to={tstop:.6e}", "V")]
    cards += [meas("dvo_max", f".meas tran dvo_max max v(divout) from={tmeas:.6e} to={tstop:.6e}", "V"),
              meas("dvo_min", f".meas tran dvo_min min v(divout) from={tmeas:.6e} to={tstop:.6e}", "V"),
              meas("fb_max", f".meas tran fb_max max v(fb) from={tmeas:.6e} to={tstop:.6e}", "V"),
              meas("fb_min", f".meas tran fb_min min v(fb) from={tmeas:.6e} to={tstop:.6e}", "V"),
              meas("tdiv_a", ".meas tran tdiv_a when v(divout)='0.5*vddp' rise=2", "s"),
              meas("tdiv_b", ".meas tran tdiv_b when v(divout)='0.5*vddp' rise=3", "s"),
              meas("idd", f".meas tran idd avg i(vdd) from={tmeas:.6e} to={tstop:.6e}", "A")]
    write(f"func_baseline_{v}", body, request(
        f"func_baseline_{v}.sp", {"kind": "tran", "args": f"{0.03 * tper:.6e} {tstop:.6e}"},
        cards, NOM, timeout=3000, budget=3300))

    # ---- retime, top-of-band 1562 MHz, word 000000 (RECORD-001 Finding 5) ----
    ton = 0.44 * TPER_TOB
    tstop = 4.0 * 64 * TPER_TOB
    tmeas = 1.05 * 64 * TPER_TOB
    body = f"""* retime rerun (issue #232), variant {v}, top-of-band 1562 MHz, word 000000
.option scale=1
.options reltol=0.005 vntol=1e-4 abstol=1e-9 trtol=7
.global sub!
.include {net}
.param vddp=3.3
Vdd vdd 0 dc 'vddp'
Vsub sub! 0 dc 0
Vck ck 0 pulse(0 'vddp' 0 60p 60p {ton:.6e} {TPER_TOB:.8e})
{PWORD}{XDIV}{IC}"""
    write(f"retime_{v}", body, request(
        f"retime_{v}.sp", {"kind": "tran", "args": f"{0.02 * TPER_TOB:.6e} {tstop:.6e}"},
        [meas("tdiv", ".meas tran tdiv when v(divout)='0.5*vddp' rise=2", "s"),
         meas("tfb", ".meas tran tfb when v(fb)='0.5*vddp' rise=2", "s"),
         meas("dvo_max", f".meas tran dvo_max max v(divout) from={tmeas:.6e} to={tstop:.6e}", "V"),
         meas("dvo_min", f".meas tran dvo_min min v(divout) from={tmeas:.6e} to={tstop:.6e}", "V"),
         meas("fb_max", f".meas tran fb_max max v(fb) from={tmeas:.6e} to={tstop:.6e}", "V"),
         meas("fb_min", f".meas tran fb_min min v(fb) from={tmeas:.6e} to={tstop:.6e}", "V"),
         meas("idd", f".meas tran idd avg i(vdd) from={tmeas:.6e} to={tstop:.6e}", "A")],
        NOM, timeout=3000, budget=3300))
