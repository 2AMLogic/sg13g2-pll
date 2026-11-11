#!/usr/bin/env python3
"""Render the issue-#233 rerun campaign as batch-fleet `decks[]` requests.

Why this exists (issue #233, child of #212, Part of #199, item 9): RECORD-003's
`run.sh` loops ngspice locally, which the dispatch hosts forbid for grids.
This generator renders the SAME stage decks `run.sh` rendered -- same
templates, same matrices, same word list, same time/step arithmetic -- but
into pre-composed decks that `klt sim --backend batch` runs verbatim.

It does not touch `run.sh` or any original `corners/*.csv`. Outputs:

  rerun233/decks/<id>.sp        one rendered deck per unit (shipped byte for byte)
  rerun233/decks/divider_chain.spice  the DUT (beside the decks: `.include` resolves there): copy of ../netlist-snapshots/divider_chain_repaired.spice
  <stage>.request.json          one `decks[]` request per stage
  rerun233/manifest.json        unit id -> stage/row metadata (read by collect_rerun233.py)

The PDK is named as `$PDK_ROOT/...` so the runner's own PDK image resolves it
(klt sim.md "Preservation and isolation"); `pre_osdi` lines sit in each deck's
`.control` block, which ngspice hoists before circuit parse.

Usage: python3 gen_rerun233_requests.py        (run from anywhere; idempotent)
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORD_DIR = HERE.parent
OUTD = HERE / "rerun233"
DECKS = OUTD / "decks"

PDK = "ihp-sg13cmos5l"
MODEL_LIB = f"$PDK_ROOT/{PDK}/libs.tech/ngspice/models/cornerMOShv.lib"
OSDI = [f"$PDK_ROOT/{PDK}/libs.tech/ngspice/osdi/{n}.osdi"
        for n in ("psp103", "psp103_nqs", "mosvar")]
DUT = "divider_chain.spice"

# ---- matrices: copied from run.sh (do not edit independently) ---------------
PVT = [
    ("mos_tt", 27, 3.3), ("mos_ss", 27, 3.3), ("mos_ff", 27, 3.3),
    ("mos_sf", 27, 3.3), ("mos_fs", 27, 3.3),
    ("mos_tt", -40, 3.3), ("mos_tt", 125, 3.3),
    ("mos_tt", 27, 2.97), ("mos_tt", 27, 3.63),
]
PVT_SETUP = [("mos_tt", 27, 3.3), ("mos_ss", 125, 3.3), ("mos_ff", -40, 3.3)]
TPER_TOB = 640.20512e-12
TPER_100 = 10.0e-9
TSU_LIST = ["1500p", "1000p", "700p", "500p", "300p", "200p", "130p", "80p", "40p", "0p"]
CODE_WORDS = [("000001", 65), ("000010", 66), ("000100", 68), ("001000", 72),
              ("010000", 80), ("100000", 96), ("011111", 95), ("101010", 106),
              ("111111", 127)]
EDGE = [("mos_ss", 125, 3.3), ("mos_ff", -40, 3.3)]
TOL = [(rt, p) for rt in ("0.001", "0.002", "0.005")
       for p in (("mos_tt", 27, 3.3), ("mos_ss", 125, 3.3))]

TIMEOUT_S = {"opconv": 1800, "hold": 1800, "setup": 1800, "func": 7200, "retime": 7200}


def g(x, fmt=".6e"):
    return format(x, fmt)


def num(x):
    """Render like bash `python3 -c print(x)` / printf: plain repr of a float/int."""
    return str(x)


def subst(tmpl, **kw):
    text = (HERE / tmpl).read_text()
    text = text.replace("@PDK_ROOT@/@PDK@/libs.tech/ngspice/models/cornerMOShv.lib", MODEL_LIB)
    for k, v in kw.items():
        text = text.replace(f"@{k}@", str(v))
    assert "@" not in "".join(l for l in text.splitlines() if not l.startswith("*")), tmpl
    # hoisted pre_osdi inside the template's own .control block
    osdi = "\n".join(f"pre_osdi {p}" for p in OSDI)
    return text.replace(".control\n", f".control\n{osdi}\n", 1)


units = {}   # stage -> list of request deck entries
manifest = {}


def add(stage, uid, deck_text, meta):
    DECKS.mkdir(parents=True, exist_ok=True)
    (DECKS / f"{uid}.sp").write_text(deck_text)
    units.setdefault(stage, []).append({
        "id": uid, "deck": f"rerun233/decks/{uid}.sp",
        "timeout_s": TIMEOUT_S[stage]})
    manifest[uid] = dict(meta, stage=stage)


def tag(mos, temp, vdd):
    return f"{mos}_{temp}_{vdd}".replace("-", "m").replace(".", "p")


# ---- opconv ------------------------------------------------------------------
for ic in ("none", "applied"):
    lines = [f"* OP-convergence probe -- repaired, ic={ic}",
             f".lib {MODEL_LIB} mos_tt", ".option scale=1 temp=27", ".global sub!",
             f".include {DUT}", "Vdd vdd 0 dc 3.3", "Vsub sub! 0 dc 0", "Vck ck 0 dc 0"]
    lines += [f"Vp{i} p{i} 0 dc 0" for i in range(6)]
    lines.append("Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain")
    if ic == "applied":
        lines += [f".ic v(xdiv.xd{d}.xdffq.m)=0 v(xdiv.xd{d}.xdffq.s)=0 "
                  f"v(xdiv.xd{d}.xdffm.m)=0 v(xdiv.xd{d}.xdffm.s)=0" for d in range(6)]
        lines.append(".ic v(xdiv.xfrt.m)=0 v(xdiv.xfrt.s)=0")
    lines += [".control"] + [f"pre_osdi {p}" for p in OSDI] + [
        "op", "print v(divout) v(fb)", ".endc", ".end"]
    add("opconv", f"op_repaired_{ic}", "\n".join(lines) + "\n", {"variant": "repaired", "ic": ic})

# ---- hold --------------------------------------------------------------------
for mos, temp, vdd in PVT:
    vdd90 = 0.9 * vdd
    add("hold", f"hold_{tag(mos, temp, vdd)}",
        subst("tb_dff_hold.sp.tmpl", CORNER_MOS=mos, TEMP=temp, VDD=vdd, VDD90=repr(vdd90),
              THOLD="40n", NETLIST=DUT),
        {"variant": "repaired", "mos": mos, "temp": temp, "vdd": vdd})

# ---- setup -------------------------------------------------------------------
TCAP = g(30e-12 + 8 * TPER_TOB)
TSAMPLE = g(30e-12 + 8 * TPER_TOB + 0.25 * TPER_TOB)
TON_S = g(0.5 * TPER_TOB)
for mos, temp, vdd in PVT_SETUP:
    for tsu in TSU_LIST:
        add("setup", f"setup_{tag(mos, temp, vdd)}_{tsu}",
            subst("tb_dff_setup.sp.tmpl", CORNER_MOS=mos, TEMP=temp, VDD=vdd,
                  TPER=g(TPER_TOB), TON=TON_S, TCAP=TCAP, TSU=tsu, TSAMPLE=TSAMPLE,
                  NETLIST=DUT),
            {"variant": "repaired", "mos": mos, "temp": temp, "vdd": vdd, "tsu": tsu})


# ---- func --------------------------------------------------------------------
def func_deck(tper, word, diva, divb, nnom, reltol, mos, temp, vdd):
    pv = {}
    for i in (5, 4, 3, 2, 1, 0):
        pv[i] = vdd if word[5 - i] == "1" else 0
    ton = g(0.44 * tper)
    tstop = g((divb + 0.4) * nnom * tper)
    tmeas = g(1.05 * nnom * tper)
    tstep = g(0.03 * tper)
    return subst("tb_div_func.sp.tmpl", CORNER_MOS=mos, TEMP=temp, VDD=vdd,
                 VDD50=repr(0.5 * vdd), TPER=g(tper), TON=ton, TSTEP=tstep,
                 TSTOP=tstop, TMEAS=tmeas, DIVA=diva, DIVB=divb, RELTOL=reltol,
                 P0=pv[0], P1=pv[1], P2=pv[2], P3=pv[3], P4=pv[4], P5=pv[5],
                 NETLIST=DUT)


def add_func(rowtag, mos, temp, vdd, word, nnom, reltol, csv):
    uid = f"func_{rowtag}_{tag(mos, temp, vdd)}_{word}_rt{reltol.replace('.', 'p')}"
    add("func", uid, func_deck(TPER_100, word, 2, 3, nnom, reltol, mos, temp, vdd),
        {"variant": "repaired", "tag": rowtag, "mos": mos, "temp": temp, "vdd": vdd,
         "word": word, "nnom": nnom, "reltol": reltol, "csv": csv})


for mos, temp, vdd in PVT:
    add_func("baseline", mos, temp, vdd, "000000", 64, "0.001", "func")
for word, nnom in CODE_WORDS:
    add_func("code", "mos_tt", 27, 3.3, word, nnom, "0.001", "func")
for mos, temp, vdd in EDGE:
    add_func("edge", mos, temp, vdd, "111111", 127, "0.001", "func")
for rt, (mos, temp, vdd) in TOL:
    add_func("tol", mos, temp, vdd, "000000", 64, rt, "tol_convergence")

# ---- retime ------------------------------------------------------------------
ton = g(0.44 * TPER_TOB)
tstep = g(0.02 * TPER_TOB)
tstop = g(4.0 * 64 * TPER_TOB)
tmeas = g(1.05 * 64 * TPER_TOB)
for mos, temp, vdd in PVT:
    add("retime", f"retime_{tag(mos, temp, vdd)}",
        subst("tb_div_retime.sp.tmpl", CORNER_MOS=mos, TEMP=temp, VDD=vdd,
              VDD50=repr(0.5 * vdd), TPER=format(TPER_TOB, ".8e"), TON=ton, TSTEP=tstep,
              TSTOP=tstop, TMEAS=tmeas, RELTOL="0.001",
              P0=0, P1=0, P2=0, P3=0, P4=0, P5=0, NETLIST=DUT),
        {"variant": "repaired", "mos": mos, "temp": temp, "vdd": vdd})

# ---- write ---------------------------------------------------------------------
shutil.copyfile(RECORD_DIR / "netlist-snapshots" / "divider_chain_repaired.spice", DECKS / DUT)
for stage, decks in units.items():
    req = {"engine": "ngspice", "backend": "batch", "models": {"pdk": PDK},
           "decks": decks, "options": {"timeout_s": TIMEOUT_S[stage]},
           "batch": {"capacity_wait_s": 600}}
    (HERE / f"{stage}.request.json").write_text(json.dumps(req, indent=2) + "\n")
(OUTD / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print({s: len(d) for s, d in units.items()}, file=sys.stderr)
