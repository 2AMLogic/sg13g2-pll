#!/usr/bin/env python3
"""Generate the `klt sim` batch requests for the RECORD-001 rerun (#323).

    python3 -I gen_requests.py HIST_DIR OUT_DIR

HIST_DIR is `git archive d5355e1` of the repo, in which
`extraction/run-pex.sh` has already been run (its `netlist-snapshots/` is
what `../netlist-snapshots/` here holds).  The historical testbench helpers
(`pex-to-ngspice.py`, `make-inst.py`) and templates are read from HIST_DIR
unmodified.  OUT_DIR/<name>/ gets a circuit body, its includes and a
`request.json`.  Nothing is simulated here.

Mapping of the historical runners onto requests (same matrices, no cuts):
  run.sh              -> vco_postlayout, vco_schematic   (60 units each)
  run_rc_attribution  -> rc_<variant> x 7                (30 units each)
  run_cp.sh           -> cp_<arm>_iref<I> x 12           (51 units each)
Per-unit axes are `corners.units`: process bundle (MOS + RES .lib sections),
temperature, and the DC sources (vctrl/b0/b1, or vdd/up/dn/vout) as
`supply_v`.  The cp DC sweep is replaced by an operating point at the sweep
point nearest VDD/2 (VDD/2 is on the historical 0.15 V + k*0.05 V grid for all
of 1.5/1.65/1.8 V, so it is the same point).
"""
import json, pathlib, re, subprocess, sys

hist = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2]).resolve()
bench = hist / "sim/sg13cmos5l-postlayout-pex-pvt"
tb, snap = bench / "testbench", bench / "netlist-snapshots"
MODELS = {"pdk": "ihp-sg13cmos5l", "lib": "libs.tech/ngspice/models/cornerMOShv.lib"}
RES = "libs.tech/ngspice/models/cornerRES.lib"
OSDI = ["$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/%s.osdi" % n
        for n in ("psp103", "psp103_nqs", "mosvar", "r3_cmc")]
PER1 = ".meas tran per1 trig v(clk) val=1.65 rise=3 targ v(clk) val=1.65 rise=4"


def run(*a):
    return subprocess.run([sys.executable, "-I", *map(str, a)], check=True,
                          capture_output=True, text=True).stdout


def body(tmpl, subs):
    """Template -> circuit body: drop .lib/.tran/.dc/.control..end cards."""
    keep, skip = [], False
    for ln in pathlib.Path(tmpl).read_text().splitlines():
        if ln.startswith(".control"):
            skip = True
        if skip or ln.startswith((".lib ", ".tran", ".end")):
            continue
        keep.append(ln)
    s = "\n".join(keep) + "\n"
    s = re.sub(r"\.option scale=1 temp=@TEMP@", ".option scale=1", s)
    for k, v in subs.items():
        s = s.replace(k, v)
    assert "@" not in re.sub(r"^\*.*$", "", s, flags=re.M), "unsubstituted token"
    return s


def emit(name, files, req):
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    for fn, txt in files.items():
        (d / fn).write_text(txt)
    req.update({"engine": "ngspice", "netlist": "body.cir", "models": MODELS,
                "backend": "batch"})
    req["options"] = {**req.get("options", {}), "osdi_preload": OSDI,
                      "stage_model_inputs": True, "timeout_s": 3600}
    (d / "request.json").write_text(json.dumps(req, indent=1) + "\n")


BUNDLES = {"typ": ("mos_tt", "res_typ", 27), "slow": ("mos_ss", "res_wcs", 125),
           "fast": ("mos_ff", "res_bcs", -40)}
BANDS = {"00": (0.0, 0.0), "10": (3.3, 0.0), "01": (0.0, 3.3), "11": (3.3, 3.3)}
VCTRL = [0.3, 0.9, 1.5, 2.1, 2.7]


def bundle(b):
    mos, res, t = BUNDLES[b]
    return ({"name": b, "sections": [mos, {"lib": RES, "section": res}]}, t)


def vco_units(bands):
    u, ids = [], []
    for b in BUNDLES:
        p, t = bundle(b)
        for bl in bands:
            for v in VCTRL:
                u.append({"process": p, "temperature_c": t,
                          "supply_v": {"vvctrl": v, "vb0": BANDS[bl][0], "vb1": BANDS[bl][1]}})
                ids.append((b, bl, v))
    return u, ids


def vco_request(units):
    return {"corners": {"units": units},
            "analysis": {"kind": "tran", "args": "20p 30n"},
            "measurements": [{"name": "per1", "unit": "s", "spice": PER1}]}


manifest = {}
base_subs = {"@VCTRL@": "0", "@B0V@": "0", "@B1V@": "0", "@CORNER_MOS@": "", "@CORNER_RES@": ""}

# ---- vco: pex + schematic arms -------------------------------------------
pex_tmp = out / ".tmp"
pex_tmp.mkdir(parents=True, exist_ok=True)
run(tb / "pex-to-ngspice.py", snap / "pll_vco.pex.spice", pex_tmp / "vco_pex.spice")
inst = run(tb / "make-inst.py", pex_tmp / "vco_pex.spice", "pll_vco", "vco",
           "VCTRL=vctrl", "B0=b0", "B1=b1", "CLK=clk", "VDD_VCO=vdd", "GND_VCO=0")
pex = (pex_tmp / "vco_pex.spice").read_text()
vco_open = "\n".join(("*" + l if l.startswith("XCDECAP") else l) for l in
                     (hist / "sim/sg13cmos5l-vco-kvco-table/netlist-snapshots/vco.spice"
                      ).read_text().splitlines()) + "\n"
units, ids = vco_units(BANDS)
emit("vco_postlayout", {"vco_pex.spice": pex, "vco_inst.spice": inst,
                        "body.cir": body(tb / "tb_vco_kvco_pex.sp.tmpl", base_subs)},
     vco_request(units))
emit("vco_schematic", {"vco_open.spice": vco_open,
                       "body.cir": body(tb / "tb_vco_kvco_sch.sp.tmpl", base_subs)},
     vco_request(units))
manifest["vco_postlayout"] = manifest["vco_schematic"] = ids

# ---- rc attribution: 7 variants x (3 bundles x bands 00,11 x 5 vctrl) ----
par_r = re.compile(r"^(R\S+\s+\S+\s+\S+\s+)([-+0-9.eE]+)\s*$")
par_c = re.compile(r"^(C\S+\s+\S+\s+\S+\s+)([-+0-9.eE]+)\s*$")
dev = re.compile(r"^[MXQD]", re.I)
base = None
rc_units, rc_ids = vco_units(["00", "11"])
for name, short_r, drop_c, cs in (("full", 0, 0, 1.0), ("c_only", 1, 0, 1.0),
                                  ("r_only", 0, 1, 1.0), ("none", 1, 1, 1.0),
                                  ("cscale25", 0, 0, 0.25), ("cscale10", 0, 0, 0.10),
                                  ("cscale05", 0, 0, 0.05)):
    o, nr, nc, nd = [], 0, 0, 0
    for ln in pex.splitlines():
        nd += bool(dev.match(ln))
        m = par_r.match(ln)
        if m:
            nr += 1
            o.append(m.group(1) + ("1e-6" if short_r else m.group(2)))
            continue
        if re.match(r"^C\S+\s+", ln):
            nc += 1
            if drop_c:
                o.append("*" + ln)
                continue
            if cs != 1.0:
                mc = par_c.match(ln)
                assert mc, ln
                o.append(mc.group(1) + repr(float(mc.group(2)) * cs))
                continue
        o.append(ln)
    if base is None:
        base = (nr, nc, nd)
    assert (nr, nc, nd) == base, (name, nr, nc, nd, base)
    emit("rc_" + name, {"vco_%s.spice" % name: "\n".join(o) + "\n", "vco_inst.spice": inst,
                        "body.cir": body(tb / "tb_vco_kvco_pex.sp.tmpl", base_subs)
                        .replace("vco_pex.spice", "vco_%s.spice" % name)},
         vco_request(rc_units))
    manifest["rc_" + name] = rc_ids

# ---- cp: 2 arms x 6 iref x (17 PVT x 3 states) -----------------------------
run(tb / "pex-to-ngspice.py", snap / "pll_cp.pex.spice", pex_tmp / "cp_pex.spice")
cp_inst = run(tb / "make-inst.py", pex_tmp / "cp_pex.spice", "pll_cp", "cp", "VSS=0")
cp_pex = (pex_tmp / "cp_pex.spice").read_text()
cp_snap = (hist / "sim/sg13cmos5l-cp-icp-trim/netlist-snapshots/cp.spice").read_text()
PVT = [(m, t, 3.3) for m in ("mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs")
       for t in (27, 125, -40)] + [("mos_tt", 27, 3.0), ("mos_tt", 27, 3.6)]
IREFS = ["2.5u", "5u", "10u", "20u", "40u", "80u"]
STATES = [("up", 1, 0), ("dn", 0, 1), ("both", 1, 1)]
cp_units, cp_ids = [], []
for m, t, vdd in PVT:
    for s, a, b in STATES:
        cp_units.append({"process": m, "temperature_c": t,
                         "supply_v": {"vdd": vdd, "vup": round(a * vdd, 4),
                                      "vdn": round(b * vdd, 4), "vout": round(vdd / 2, 4)}})
        cp_ids.append((m, t, vdd, s))
for arm, tmpl, files in (("postlayout", "tb_cp_dc_pex.sp.tmpl",
                          {"cp_pex.spice": cp_pex, "cp_inst.spice": cp_inst}),
                         ("schematic", "tb_cp_dc_sch.sp.tmpl", {"cp_snap.spice": cp_snap})):
    for iref in IREFS:
        subs = {"@VDD@": "3.3", "@IREF@": iref, "@UPV@": "0", "@DNV@": "0"}
        emit("cp_%s_iref%s" % (arm, iref),
             dict(files, **{"body.cir": body(tb / tmpl, subs)}),
             {"corners": {"units": cp_units}, "analysis": {"kind": "op", "args": ""},
              "measurements": [{"name": "icp_a", "unit": "A", "expr": "i(Vout)"}]})
        manifest["cp_%s_iref%s" % (arm, iref)] = cp_ids

(out / "manifest.json").write_text(json.dumps(manifest) + "\n")
print("requests:", len(manifest))
