#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-supply-range (issue #187, T1 item 5)

Spec row 18 (supply range 3.0 to 3.6 V) was measured on `cp` only.  This
generator re-expresses three existing benches at VDD in {3.0, 3.3, 3.6} V over
their PVT bundles as `klt sim` **deck-list requests** for the batch fleet (the
dispatch hosts forbid hand-launched ngspice grids).  It never calls ngspice.

The sibling benches' own templates are the single source of truth; they are
read from there, never copied, and only the supply-dependent literals are
patched (each patch is asserted so a template edit cannot silently turn it
into a no-op):

  vco            ../sg13cmos5l-vco-kvco-table/testbench/tb_vco_kvco.sp.tmpl
  lock_detector  ../sg13cmos5l-lock-detector-window/testbench/{tb_window,tb_schmitt_hyst}.sp.tmpl
  divider_chain  ../sg13cmos5l-divider-nrange-retiming/testbench/{tb_div_func,tb_div_retime}.sp.tmpl

Subcommands (all take WORKDIR; PDK_ROOT is NOT needed -- decks carry the
literal `$PDK_ROOT/...` which the runner expands against its own PDK image):

  gen    WORKDIR BLOCK [--probe]   write WORKDIR/BLOCK/{request.json,decks/}
  reduce WORKDIR CORNERS_DIR       read WORKDIR/BLOCK/out/*/stdout.bin and
                                   write CORNERS_DIR/{vco,lock_detector,divider}.csv
                                   and CORNERS_DIR/summary.md

BLOCK is one of: vco, lockdet, divider.  --probe renders only the nominal
bundle at 3.0 V (the single-corner probe job).
"""
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent
SIM = RECORD.parent
SNAP = RECORD / "netlist-snapshots"
PDK = "ihp-sg13cmos5l"
PDK_REF = "$PDK_ROOT/" + PDK
OSDI_DIR = PDK_REF + "/libs.tech/ngspice/osdi"

VDDS = ["3.0", "3.3", "3.6"]
# name, MOS corner, RES corner, temp  (the VCO bench's own 3 correlated bundles)
BUNDLES = [("typ", "mos_tt", "res_typ", 27),
           ("slow", "mos_ss", "res_wcs", 125),
           ("fast", "mos_ff", "res_bcs", -40)]
VCO_BANDS = ["00", "10", "01", "11"]          # label = "<B0><B1>", as the VCO bench
VCO_VCTRL = ["0.3", "0.9", "1.5", "2.1", "2.7"]
# divider: tb_div_func word / nominal N (RECORD-003 conventions)
DIV_WORDS = [("000000", 64), ("111111", 127)]
TPER_FUNC = 10.0e-9           # 100 MHz, as the sibling bench
TPER_RETIME = 640.20512e-12   # 1562.0 MHz / 64 retiming-bound clock period
FUNC_KEYS = ("ck1_max ck1_min ck2_max ck2_min ck3_max ck3_min ck4_max ck4_min "
             "ck5_max ck5_min dvo_max dvo_min fb_max fb_min tdiv_a tdiv_b tck_a tck_b idd").split()
RETIME_KEYS = "tdiv tfb dvo_max dvo_min fb_max fb_min idd".split()


def tmpl(rel):
    return (SIM / rel).read_text()


def sub(text, **kw):
    for k, v in kw.items():
        text = text.replace("@%s@" % k, str(v))
    left = [l for l in text.splitlines() if not l.startswith("*") and re.search(r"@[A-Z_0-9]+@", l)]
    if left:
        raise SystemExit("supply_grid: unsubstituted placeholders: %s" % left)
    return text


def patch(text, old, new):
    if old not in text:
        raise SystemExit("supply_grid: sibling template no longer contains %r; update the patch" % old)
    return text.replace(old, new)


def with_init(text, osdi):
    """Insert pre_osdi + num_threads=1 into the deck (a deck-list unit has no
    .spiceinit).  Reuses the template's own .control block when it has one."""
    pre = "\n".join("pre_osdi %s/%s.osdi" % (OSDI_DIR, o) for o in osdi) + "\nset num_threads=1\n"
    if ".control\n" in text:
        return text.replace(".control\n", ".control\n" + pre, 1)
    lines = text.splitlines()
    return "\n".join(lines[:1] + [".control", pre.rstrip("\n"), ".endc"] + lines[1:]) + "\n"


def points(probe):
    return [(b, "3.0") for b in BUNDLES[:1]] if probe else [(b, v) for b in BUNDLES for v in VDDS]


def write_request(d, units, files, timeout_s):
    (d / "decks").mkdir(parents=True, exist_ok=True)
    for uid, text in units:
        (d / "decks" / (uid + ".sp")).write_text(text)
    for src in files:
        (d / "decks" / pathlib.Path(src).name).write_text(pathlib.Path(src).read_text())
    req = {"engine": "ngspice", "backend": "batch", "models": {"pdk": PDK},
           "decks": [{"id": u, "deck": "decks/%s.sp" % u, "timeout_s": timeout_s} for u, _ in units],
           "options": {"timeout_s": timeout_s, "max_workers": 2},
           "batch": {"capacity_wait_s": 600}}
    (d / "request.json").write_text(json.dumps(req, indent=2) + "\n")
    (d / "units.json").write_text(json.dumps([u for u, _ in units], indent=2) + "\n")
    print("wrote %s (%d decks)" % (d / "request.json", len(units)))


def tag(*a):
    return "_".join(str(x) for x in a).replace(".", "p").replace("-", "m")


# ------------------------------------------------------------------ vco
def gen_vco(d, probe):
    t = tmpl("sg13cmos5l-vco-kvco-table/testbench/tb_vco_kvco.sp.tmpl")
    t = patch(t, "Vdd vdd 0 dc 3.3", "Vdd vdd 0 dc @VDD@")
    t = patch(t, "val=1.65 rise=3 targ v(clk) val=1.65 rise=4", "val=@VMID@ rise=3 targ v(clk) val=@VMID@ rise=4")
    t = patch(t, ".include vco_open.spice", ".include vco_open.spice")
    t = patch(t, ".lib @PDK_ROOT@/@PDK@/libs.tech/ngspice/models/cornerMOShv.lib",
              ".lib $PDK_ROOT/@PDK@/libs.tech/ngspice/models/cornerMOShv.lib")
    t = patch(t, ".lib @PDK_ROOT@/@PDK@/libs.tech/ngspice/models/cornerRES.lib",
              ".lib $PDK_ROOT/@PDK@/libs.tech/ngspice/models/cornerRES.lib")
    # XCDECAP stripped exactly as the sibling run.sh does (ideal supply: provably inert)
    vco_open = "".join(("*" + l if l.startswith("XCDECAP") else l)
                       for l in (SNAP / "vco.spice").read_text().splitlines(True))
    units = []
    for (bn, mos, res, temp), vdd in points(probe):
        for band in VCO_BANDS:
            b0 = vdd if band[0] == "1" else "0.0"
            b1 = vdd if band[1] == "1" else "0.0"
            for vc in VCO_VCTRL:
                text = sub(t, PDK=PDK, CORNER_MOS=mos, CORNER_RES=res, TEMP=temp, VCTRL=vc,
                           B0V=b0, B1V=b1, VDD=vdd, VMID="%.6f" % (float(vdd) / 2))
                units.append(("vco_%s_%s_%s_%s" % (bn, tag(vdd), band, tag(vc)),
                              with_init(text, ["psp103", "psp103_nqs", "mosvar", "r3_cmc"])))
    (d).mkdir(parents=True, exist_ok=True)
    (d / "vco_open.spice").write_text(vco_open)
    write_request(d, units, [d / "vco_open.spice"], 1800)


# ------------------------------------------------------------- lock detector
def gen_lockdet(d, probe):
    d.mkdir(parents=True, exist_ok=True)
    dut = d / "dut_real.spice"
    subprocess.check_call([sys.executable, "-I", str(SIM / "sg13cmos5l-lock-detector-window/testbench/mom_inject.py"),
                           str(SNAP / "lock_detector_bodyfix.spice"), str(dut), "real"])
    win = tmpl("sg13cmos5l-lock-detector-window/testbench/tb_window.sp.tmpl")
    sch = tmpl("sg13cmos5l-lock-detector-window/testbench/tb_schmitt_hyst.sp.tmpl")
    units = []
    for (bn, mos, res, temp), vdd in points(probe):
        common = dict(PDK=PDK, CORNER_MOS=mos, CORNER_RES=res, TEMP=temp, VSUP=vdd,
                      VMID="%.6f" % (float(vdd) / 2), DUT="dut_real.spice")
        for kind, tt, extra in (("win", win, {"TSTEP": "20p"}), ("sch", sch, {})):
            text = tt.replace("@PDK_ROOT@", "$PDK_ROOT")
            text = sub(text, **common, **extra)
            units.append(("%s_%s_%s" % (kind, bn, tag(vdd)),
                          with_init(text, ["psp103", "psp103_nqs", "mosvar", "r3_cmc", "cap_cmomi"])))
    write_request(d, units, [dut], 3600)


# ---------------------------------------------------------------- divider
def g(x):
    return format(x, ".6e")


def gen_divider(d, probe):
    func = tmpl("sg13cmos5l-divider-nrange-retiming/testbench/tb_div_func.sp.tmpl")
    ret = tmpl("sg13cmos5l-divider-nrange-retiming/testbench/tb_div_retime.sp.tmpl")
    dut = SNAP / "divider_chain_repaired.spice"
    units = []
    for (bn, mos, res, temp), vdd in points(probe):
        v = float(vdd)
        base = dict(PDK=PDK, CORNER_MOS=mos, TEMP=temp, VDD=vdd, VDD50=repr(0.5 * v),
                    RELTOL="0.001", NETLIST=dut.name)
        for word, nnom in DIV_WORDS:
            pv = {i: (vdd if word[5 - i] == "1" else "0") for i in range(6)}
            tper = TPER_FUNC
            text = sub(func.replace("@PDK_ROOT@", "$PDK_ROOT"), **base,
                       TPER=g(tper), TON=g(0.44 * tper), TSTEP=g(0.03 * tper),
                       TSTOP=g((3 + 0.4) * nnom * tper), TMEAS=g(1.05 * nnom * tper),
                       DIVA=2, DIVB=3, P0=pv[0], P1=pv[1], P2=pv[2], P3=pv[3], P4=pv[4], P5=pv[5])
            units.append(("func_%s_%s_%s" % (bn, tag(vdd), word),
                          with_init(text, ["psp103", "psp103_nqs", "mosvar"])))
        tp = TPER_RETIME
        text = sub(ret.replace("@PDK_ROOT@", "$PDK_ROOT"), **base,
                   TPER=format(tp, ".8e"), TON=g(0.44 * tp), TSTEP=g(0.02 * tp),
                   TSTOP=g(4.0 * 64 * tp), TMEAS=g(1.05 * 64 * tp),
                   P0=0, P1=0, P2=0, P3=0, P4=0, P5=0)
        units.append(("retime_%s_%s" % (bn, tag(vdd)),
                      with_init(text, ["psp103", "psp103_nqs", "mosvar"])))
    write_request(d, units, [dut], 7200)


# ----------------------------------------------------------------- reduce
def val(text, k):
    m = re.search(r"^%s\s*=\s*(\S+)" % re.escape(k), text, re.M)
    if not m:
        return "NA"
    try:
        float(m.group(1))
        return m.group(1)
    except ValueError:
        return "NA"


def out_of(work, block, uid):
    p = work / block / "out" / uid / "stdout.bin"
    return p.read_text(errors="replace") if p.exists() else ""


def reduce_all(work, corners):
    corners.mkdir(parents=True, exist_ok=True)
    rows = {}
    # vco
    lines = ["bundle,mos_corner,res_corner,temp_c,vdd_v,band_code,vctrl_v,period_s,freq_hz"]
    for (bn, mos, res, temp), vdd in points(False):
        for band in VCO_BANDS:
            for vc in VCO_VCTRL:
                txt = out_of(work, "vco", "vco_%s_%s_%s_%s" % (bn, tag(vdd), band, tag(vc)))
                per = val(txt, "per1")
                fr = "NA" if per == "NA" else "%.6e" % (1.0 / float(per))
                lines.append(",".join(map(str, (bn, mos, res, temp, vdd, band, vc, per, fr))))
    (corners / "vco.csv").write_text("\n".join(lines) + "\n")
    # lock detector
    lines = ["bundle,mos_corner,res_corner,temp_c,vdd_v,twin_r_s,twin_f_s,t_up_s,t_dn_s,vth_up_v,vth_dn_v"]
    for (bn, mos, res, temp), vdd in points(False):
        w = out_of(work, "lockdet", "win_%s_%s" % (bn, tag(vdd)))
        s = out_of(work, "lockdet", "sch_%s_%s" % (bn, tag(vdd)))
        lines.append(",".join(map(str, (bn, mos, res, temp, vdd, val(w, "twin_r"), val(w, "twin_f"),
                                        val(s, "t_up"), val(s, "t_dn"), val(s, "vth_up"), val(s, "vth_dn")))))
    (corners / "lock_detector.csv").write_text("\n".join(lines) + "\n")
    # divider
    lines = ["kind,bundle,mos_corner,temp_c,vdd_v,word,n_nominal,n_measured,tdiv_s,tfb_s,dvo_max,dvo_min,idd_a"]
    for (bn, mos, res, temp), vdd in points(False):
        for word, nnom in DIV_WORDS:
            txt = out_of(work, "divider", "func_%s_%s_%s" % (bn, tag(vdd), word))
            v = {k: val(txt, k) for k in FUNC_KEYS}
            try:
                nmeas = "%.3f" % ((float(v["tdiv_b"]) - float(v["tdiv_a"])) / (float(v["tck_b"]) - float(v["tck_a"])))
            except (ValueError, ZeroDivisionError):
                nmeas = "NA"
            lines.append(",".join(map(str, ("func", bn, mos, temp, vdd, word, nnom, nmeas,
                                            v["tdiv_a"], "NA", v["dvo_max"], v["dvo_min"], v["idd"]))))
        txt = out_of(work, "divider", "retime_%s_%s" % (bn, tag(vdd)))
        v = {k: val(txt, k) for k in RETIME_KEYS}
        lines.append(",".join(map(str, ("retime", bn, mos, temp, vdd, "000000", 64, "NA",
                                        v["tdiv"], v["tfb"], v["dvo_max"], v["dvo_min"], v["idd"]))))
    (corners / "divider.csv").write_text("\n".join(lines) + "\n")


def main(argv):
    if len(argv) < 3 or argv[1] not in ("gen", "reduce"):
        raise SystemExit(__doc__)
    work = pathlib.Path(argv[2])
    if argv[1] == "gen":
        block = argv[3]
        fn = {"vco": gen_vco, "lockdet": gen_lockdet, "divider": gen_divider}[block]
        fn(work / block, "--probe" in argv)
    else:
        reduce_all(work, pathlib.Path(argv[3]))


if __name__ == "__main__":
    main(sys.argv)
