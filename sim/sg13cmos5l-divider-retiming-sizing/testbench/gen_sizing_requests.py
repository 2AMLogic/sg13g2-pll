#!/usr/bin/env python3
"""Render the issue-#189 retiming-sizing campaign as `klt sim` batch requests.

Variants scale the MOS widths inside private copies of the dff_tg_hv latch
(and its inv_hv / tgate_hv leaves), leaving every other cell untouched:
  sf = width scale for the XFRT retiming flop only
  sc = width scale for the dff_tg_hv flops inside the six div23_cell stages
Scale 1 reuses the original subckt names (byte-identical to the frozen
repaired snapshot). Stimuli, matrices and time arithmetic are those of
../../sg13cmos5l-divider-nrange-retiming/testbench/gen_rerun233_requests.py.

Usage: gen_sizing_requests.py <stage> <c:f> [<c:f> ...] [--corners all|tt]
  c, f: "b" (base) or kt/ki/kf/ko width scales (fwd-TG, storage-inv, feedback, out-buf)
  stage: setup | retime       writes <stage>_<tag>.request.json + decks/
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent.parent / "sg13cmos5l-divider-nrange-retiming"
SNAP = (OLD / "netlist-snapshots" / "divider_chain_repaired.spice").read_text()
DECKS = HERE / "decks"
PDK = "ihp-sg13cmos5l"
MODEL_LIB = f"$PDK_ROOT/{PDK}/libs.tech/ngspice/models/cornerMOShv.lib"
OSDI = [f"$PDK_ROOT/{PDK}/libs.tech/ngspice/osdi/{n}.osdi" for n in ("psp103", "psp103_nqs", "mosvar")]

PVT = [("mos_tt", 27, 3.3), ("mos_ss", 27, 3.3), ("mos_ff", 27, 3.3), ("mos_sf", 27, 3.3),
       ("mos_fs", 27, 3.3), ("mos_tt", -40, 3.3), ("mos_tt", 125, 3.3),
       ("mos_tt", 27, 2.97), ("mos_tt", 27, 3.63)]
PVT_SETUP = [("mos_tt", 27, 3.3), ("mos_ss", 125, 3.3), ("mos_ff", -40, 3.3)]
TPER_TOB = 640.20512e-12
# finer than the RECORD-003 list so the bracket is tight around the new bound
TSU_LIST = ["1500p", "1000p", "800p", "700p", "600p", "500p", "450p", "400p", "350p",
            "300p", "250p", "200p", "150p", "100p", "50p", "0p"]


def g(x, fmt=".6e"):
    return format(x, fmt)


def tag(m, t, v):
    return f"{m}_{t}_{v}".replace("-", "m").replace(".", "p")


def subckt(name):
    m = re.search(rf"^\.subckt {name} .*?^\.ends\n", SNAP, re.S | re.M)
    return m.group(0)


def scale_w(text, s):
    return re.sub(r"w=([0-9.]+)u", lambda m: f"w={float(m.group(1)) * s:g}u", text)


def fmt(s):
    return f"{s:g}".replace(".", "p")


GROUPS = {  # instance -> (group, leaf)
    "XTG1": ("t", "tgate_hv"), "XTG2": ("t", "tgate_hv"),
    "XIM": ("i", "inv_hv"), "XIS": ("i", "inv_hv"),
    "XIMF": ("f", "inv_hv"), "XISF": ("f", "inv_hv"),
    "XTGFBM": ("f", "tgate_hv"), "XTGFBS": ("f", "tgate_hv"),
    "XBQ": ("o", "inv_hv"),
}


def parse_k(spec):
    """'b' (base) or 'kt/ki/kf/ko' width scales: fwd-TG / storage-inv / feedback / out-buf."""
    if spec == "b":
        return None
    k = [float(x) for x in spec.split("/")]
    assert len(k) == 4, spec
    return None if k == [1, 1, 1, 1] else tuple(k)


def ktag(k):
    return "b" if k is None else "-".join(fmt(x) for x in k)


def dff_variant(k):
    """Private per-group scaled leaf copies + dff subckt; returns (text, dffname)."""
    if k is None:
        return "", "dff_tg_hv"
    tg = ktag(k)
    out, scales = [], dict(zip("tifo", k))
    for grp, sc in scales.items():
        for leaf in ("inv_hv", "tgate_hv"):
            if sc != 1 and any(v == (grp, leaf) for v in GROUPS.values()):
                out.append(scale_w(subckt(leaf), sc).replace(
                    f".subckt {leaf}", f".subckt {leaf}_{grp}{fmt(sc)}"))
    dff = subckt("dff_tg_hv").replace(".subckt dff_tg_hv", f".subckt dff_tg_hv_{tg}")
    for inst, (grp, leaf) in GROUPS.items():
        sc = scales[grp]
        if sc != 1:
            dff = re.sub(rf"^({inst} .* ){leaf}$", rf"\1{leaf}_{grp}{fmt(sc)}", dff, flags=re.M)
    return "\n".join(out + [dff]) + "\n", f"dff_tg_hv_{tg}"


def dut(kc, kf):
    name = f"divider_chain_c{ktag(kc)}_f{ktag(kf)}.spice"
    extra_c, dffc = dff_variant(kc)
    extra_f, dfff = dff_variant(kf)
    text = SNAP
    if kc is not None:
        cell = subckt("div23_cell")
        newcell = cell.replace(".subckt div23_cell", ".subckt div23_cell_sc")
        newcell = re.sub(r"(\bXDFF[QM] .* )dff_tg_hv$", rf"\1{dffc}", newcell, flags=re.M)
        text += "\n" + extra_c + "\n" + newcell
        text = re.sub(r"^(XD\d .* )div23_cell$", r"\1div23_cell_sc", text, flags=re.M)
    if kf is not None and kf != kc:
        text += "\n" + extra_f
    text = re.sub(r"^(XFRT .* )dff_tg_hv$", rf"\1{dfff}", text, flags=re.M)
    DECKS.mkdir(exist_ok=True)
    (DECKS / name).write_text(text)
    return name, dfff


def subst(tmpl, **kw):
    text = (OLD / "testbench" / tmpl).read_text()
    text = text.replace("@PDK_ROOT@/@PDK@/libs.tech/ngspice/models/cornerMOShv.lib", MODEL_LIB)
    for k, v in kw.items():
        text = text.replace(f"@{k}@", str(v))
    osdi = "\n".join(f"pre_osdi {p}" for p in OSDI)
    return text.replace(".control\n", f".control\n{osdi}\n", 1)


def main():
    stage = sys.argv[1]
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    tt_only = "--corners" in sys.argv and sys.argv[sys.argv.index("--corners") + 1] == "tt"
    args = [a for a in args if ":" in a]
    decks, man = [], {}
    for a in args:
        sc, sf = (parse_k(x) for x in a.split(":"))
        net, dfff = dut(sc, sf)
        vt = f"c{ktag(sc)}_f{ktag(sf)}"
        if stage == "setup":
            tcap = g(30e-12 + 8 * TPER_TOB); tsamp = g(30e-12 + 8.25 * TPER_TOB)
            for mos, temp, vdd in (PVT_SETUP[:1] if tt_only else PVT_SETUP):
                for tsu in TSU_LIST:
                    t = subst("tb_dff_setup.sp.tmpl", CORNER_MOS=mos, TEMP=temp, VDD=vdd,
                              TPER=g(TPER_TOB), TON=g(0.5 * TPER_TOB), TCAP=tcap, TSU=tsu,
                              TSAMPLE=tsamp, NETLIST=net)
                    t = t.replace("Xdut d clk q vdd 0 dff_tg_hv", f"Xdut d clk q vdd 0 {dfff}")
                    uid = f"setup_{vt}_{tag(mos, temp, vdd)}_{tsu}"
                    (DECKS / f"{uid}.sp").write_text(t)
                    decks.append({"id": uid, "deck": f"decks/{uid}.sp", "timeout_s": 1800})
                    man[uid] = dict(stage=stage, vt=vt, mos=mos, temp=temp, vdd=vdd, tsu=tsu)
        else:
            for mos, temp, vdd in (PVT[:1] if tt_only else PVT):
                t = subst("tb_div_retime.sp.tmpl", CORNER_MOS=mos, TEMP=temp, VDD=vdd,
                          VDD50=repr(0.5 * vdd), TPER=format(TPER_TOB, ".8e"),
                          TON=g(0.44 * TPER_TOB), TSTEP=g(0.02 * TPER_TOB),
                          TSTOP=g(4.0 * 64 * TPER_TOB), TMEAS=g(1.05 * 64 * TPER_TOB),
                          RELTOL="0.001", P0=0, P1=0, P2=0, P3=0, P4=0, P5=0, NETLIST=net)
                uid = f"retime_{vt}_{tag(mos, temp, vdd)}"
                (DECKS / f"{uid}.sp").write_text(t)
                decks.append({"id": uid, "deck": f"decks/{uid}.sp", "timeout_s": 7200})
                man[uid] = dict(stage=stage, vt=vt, mos=mos, temp=temp, vdd=vdd)
    name = f"{stage}_" + "_".join(a.replace(":", "-").replace("/", "-").replace(".", "p") for a in args)
    if len(name) > 100:
        import hashlib
        name = f"{stage}_set-" + hashlib.sha256(name.encode()).hexdigest()[:10]
    req = {"engine": "ngspice", "backend": "batch", "models": {"pdk": PDK}, "decks": decks,
           "options": {"timeout_s": 7200}, "batch": {"capacity_wait_s": 600}}
    (HERE / f"{name}.request.json").write_text(json.dumps(req, indent=2) + "\n")
    mp = HERE / "manifest.json"
    old = json.loads(mp.read_text()) if mp.exists() else {}
    old.update(man); mp.write_text(json.dumps(old, indent=2, sort_keys=True) + "\n")
    print(name, len(decks), "units", file=sys.stderr)


main()
