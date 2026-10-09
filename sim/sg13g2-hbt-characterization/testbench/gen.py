#!/usr/bin/env python3
"""Generate the klt sim request JSONs and DUT netlist bodies for
sim/sg13g2-hbt-characterization.  Writes ../requests/*.json and
../testbench/*.sp.  Pure text generation; runs nothing."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REQ = os.path.join(HERE, "..", "requests")
PDK = "/home/ubuntu/share/pdk/ihp-sg13g2"      # override with $PDK_DIR
PDK = os.environ.get("PDK_DIR", PDK)
OSDI = [f"{PDK}/libs.tech/ngspice/osdi/{o}.osdi"
        for o in ("psp103", "psp103_nqs", "mosvar", "r3_cmc")]
IREFS = {"2p5u": 2.5e-6, "10u": 10e-6, "80u": 80e-6}
TEMPS = [-40, 27, 125]

def req(name, netlist, lib, sections, meas, mc=None, osdi=True):
    r = {
        "engine": "ngspice",
        "backend": "batch",
        "netlist": f"../testbench/{netlist}",
        "models": {"pdk": "ihp-sg13g2", "lib": f"libs.tech/ngspice/models/{lib}"},
        "corners": {"process": sections, "temperature_c": TEMPS},
        "analysis": {"kind": "dc", "args": "Iref 2.5u 80u 2.5u"},
        "measurements": meas,
        "options": {"osdi_preload": OSDI, "timeout_s": 600, "keep_artifacts": True},
    }
    if not osdi:
        # VBIC (level 9) is native to ngspice: no OSDI object needed, so the batch
        # backend (which rejects osdi_preload) can take this request as-is.
        del r["options"]["osdi_preload"]
    else:
        # PSP103 is OSDI-only; the batch backend needs the model binaries staged.
        r["options"]["stage_model_inputs"] = True
    if mc:
        r["monte_carlo"] = mc
    with open(os.path.join(REQ, name), "w") as f:
        json.dump(r, f, indent=2); f.write("\n")

def at(i): return IREFS[i] if False else None

def find(name, expr, i):
    return {"name": name, "spice": f".meas dc {name} find {expr} at={IREFS[i]:.4g}"}

# --- HBT current-mirror: ref diode + outputs at fixed Vce -------------------
VCES = [0.3, 0.6, 0.9, 1.2, 1.5]
with open(os.path.join(HERE, "tb_hbt_ro.sp"), "w") as f:
    f.write("* sg13g2-pll :: npn13G2 mirror, Ic-vs-Vce.  Ref = diode-connected npn13G2 fed by Iref;\n"
            "* outputs share the base node, collector forced to fixed Vce by ideal sources.\n"
            "* i(Vcn) is NEGATIVE of collector current (current enters + terminal convention).\n"
            ".global sub!\nVsub sub! 0 dc 0\n"
            "Iref 0 nb dc 10u\nXQr nb nb 0 0 npn13G2 Nx=1\n")
    for k, v in enumerate(VCES, 1):
        f.write(f"XQo{k} c{k} nb 0 0 npn13G2 Nx=1\nVc{k} c{k} 0 dc {v}\n")
meas = [find(f"vbe_{i}", "v(nb)", i) for i in IREFS]
for i in IREFS:
    for k, v in enumerate(VCES, 1):
        meas.append(find(f"ic{k}_{i}", f"i(vc{k})", i))
req("hbt_ro.request.json", "tb_hbt_ro.sp", "cornerHBT.lib", ["hbt_typ", "hbt_bcs", "hbt_wcs"], meas, osdi=False)

# --- HBT mismatch: ref + 4 identical outputs at Vce ~ Vbe ---------------------
with open(os.path.join(HERE, "tb_hbt_mm.sp"), "w") as f:
    f.write("* sg13g2-pll :: npn13G2 mirror mismatch.  Ref + 4 outputs, each output collector\n"
            "* held at 0.9 V (~Vbe).  Run with the *_mismatch lib sections; each Monte Carlo\n"
            "* sample draws independent area for every instance (agauss in the PDK lib).\n"
            ".global sub!\nVsub sub! 0 dc 0\n"
            "Iref 0 nb dc 10u\nXQr nb nb 0 0 npn13G2 Nx=1\n")
    for k in range(1, 5):
        f.write(f"XQo{k} c{k} nb 0 0 npn13G2 Nx=1\nVc{k} c{k} 0 dc 0.9\n")
meas = [find(f"vbe_{i}", "v(nb)", i) for i in IREFS]
for i in IREFS:
    for k in range(1, 5):
        meas.append(find(f"ic{k}_{i}", f"i(vc{k})", i))
req("hbt_mm.request.json", "tb_hbt_mm.sp", "cornerHBT.lib",
    ["hbt_typ_mismatch", "hbt_bcs_mismatch", "hbt_wcs_mismatch"], meas,
    mc={"n": 50, "seed": 181, "vary": "mismatch"}, osdi=False)

# --- CMOS cascode leg (cp_leg_n devices + DR-006 replica) ---------------------
VOS = [0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0]
def cmos_body(nout, vo_list, mm):
    s = ("* sg13g2-pll :: CMOS wide-swing cascode sink leg of cp (cp_leg_n devices:\n"
         "* M1 mirror + M2 cascode, 8u/1u; SWO switch 6u/0.3u, on) with the DR-006 bias\n"
         "* replica (MBN/MBNC/MCN, from design/sg13cmos5l/cp.sch).  Replica is fed by two\n"
         "* ideal Iref sources (bias generation is out of block scope, DR-002 Decision 1).\n"
         "* Each output leg has its VOUT held by an ideal source.  i(Vo*) = -(sink current).\n"
         ".global sub!\nVsub sub! 0 dc 0\nVdd VDD 0 dc 3.3\nVdn DN 0 dc 3.3\n"
         "Iref 0 nref dc 10u\nVs nref IBN dc 0\nFrefc 0 ICN Vs 1\n"
         "XMBN nxn IBN 0 0 sg13_hv_nmos w=8u l=1u ng=1 m=1\n"
         "XMBNC IBN ICN nxn 0 sg13_hv_nmos w=8u l=1u ng=1 m=1\n"
         "XMCN ICN ICN 0 0 sg13_hv_nmos w=2u l=3u ng=1 m=1\n")
    for k, v in enumerate(vo_list, 1):
        s += (f"XM1_{k} tail{k} IBN 0 0 sg13_hv_nmos w=8u l=1u ng=1 m=1\n"
              f"XM2_{k} sw{k} ICN tail{k} 0 sg13_hv_nmos w=8u l=1u ng=1 m=1\n"
              f"XSWO_{k} out{k} DN sw{k} 0 sg13_hv_nmos w=6u l=0.3u ng=1 m=1\n"
              f"Vo{k} out{k} 0 dc {v}\n")
    return s
with open(os.path.join(HERE, "tb_cmos_ro.sp"), "w") as f:
    f.write(cmos_body(len(VOS), VOS, False))
meas = [find(f"ibn_{i}", "v(IBN)", i) for i in IREFS]
for i in IREFS:
    for k in range(1, len(VOS) + 1):
        meas.append(find(f"io{k}_{i}", f"i(vo{k})", i))
req("cmos_ro.request.json", "tb_cmos_ro.sp", "cornerMOShv.lib", ["mos_tt", "mos_ss", "mos_ff"], meas)

# --- CMOS leg mismatch: replica + 4 identical legs at VOUT = 1.65 V -----------
with open(os.path.join(HERE, "tb_cmos_mm.sp"), "w") as f:
    f.write(cmos_body(4, [1.65] * 4, True))
meas = [find(f"ibn_{i}", "v(IBN)", i) for i in IREFS]
for i in IREFS:
    for k in range(1, 5):
        meas.append(find(f"io{k}_{i}", f"i(vo{k})", i))
req("cmos_mm.request.json", "tb_cmos_mm.sp", "cornerMOShv.lib",
    ["mos_tt_mismatch", "mos_ss_mismatch", "mos_ff_mismatch"], meas,
    mc={"n": 50, "seed": 181, "vary": "mismatch"}, osdi=True)

# --- CMOS leg, single nominal corner, LOCAL backend ---------------------------
# The batch fleet cannot run PSP103 (OSDI) decks (see RECORD-001), so the CMOS
# comparison is exercised at ONE corner only (mos_tt / 27 C), which is a single
# ngspice process -- the host rules permit one local debug-probe corner.
def _nominal():
    path = os.path.join(REQ, "cmos_ro.request.json")
    r = json.load(open(path))
    r["backend"] = "local"
    r["corners"] = {"process": ["mos_tt"], "temperature_c": [27]}
    r["options"].pop("stage_model_inputs", None)
    with open(os.path.join(REQ, "cmos_ro_nominal.request.json"), "w") as f:
        json.dump(r, f, indent=2); f.write("\n")
_nominal()
