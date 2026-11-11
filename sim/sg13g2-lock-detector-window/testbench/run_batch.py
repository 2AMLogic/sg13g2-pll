#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13g2-lock-detector-window/testbench/run_batch.py (issue #236)

Same-bench batch rerun of RECORD-001 (superseded by RECORD-002 via
ADDENDUM-001).  Renders the SAME templates and the SAME corner matrices that
./run.sh and ./run_hysteresis_diag.sh use, but ships every ngspice deck to the
batch fleet as a `klt sim` deck-list request instead of running ngspice here
(host policy: no hand-launched ngspice grids).  Nothing is re-derived: the
matrix lists below are copied from run.sh / run_hysteresis_diag.sh and the
ladder is reduced by the unchanged ../../tools/gen_lock_ladder.py.

Outputs go to NEW paths, suffix `_resized_rerun236` -- the original `_resized`
CSVs are append-only evidence and are never opened for writing.

Usage (state lives in --work, so every step is resumable):
  run_batch.py stage1 --work W      # rc_extract, window, schmitt, tstep, per-corner windows
  run_batch.py stage2 --work W      # ladder (21 corners x 24 decks) + hysteresis diag
  run_batch.py reduce --work W      # parse raw stdout -> ../corners/*_resized_rerun236.csv

`stageN` only renders + submits + waits; `reduce` is offline.  Not covered
(stated, not silent): the four SIZING sweeps (run_rc_sizing.sh,
run_xmpd_sizing.sh -> rc_sizing/rc_pairing/window_sizing/xmpd_sizing.csv).
They select the geometry; the claim RECORD-001 makes is the measurement of the
frozen, already-sized snapshot, which is what this reruns.
"""
import argparse
import csv
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC = HERE.parent
CORNERS = REC / "corners"
SNAP = REC / "netlist-snapshots" / "lock_detector_resized.spice"
GEN = REC.parent / "tools" / "gen_lock_ladder.py"
SFX = "_resized_rerun236"
PDKV = "$PDK_ROOT/ihp-sg13g2"      # resolved by the executing host's environment
DUTNAME = "lock_detector_resized.spice"

VSUP_NOM = "3.3"
TRST = "1n"
FREF_SLOW = "3.5e6"
FREF_FAST = "24.4e6"
LADDER_SET = "resized"
K_SETTLE = 4
TSTOP_MAX = "32e-6"
TSTEP_DIV = 25
TAUBIG_XWIN = "20.00"
XRPU = ("0.5u", "500u")
XCW = ("45u", "45u")
XC1 = ("45u", "45u")
DIAG_FRACS = "0.90 1.00 1.05 1.10 1.15 1.20 1.25 1.30 1.40 1.50 1.60 1.75 2.00".split()
DIAG_FREF = "24.4e6"

SPICEINIT = (
    "osdi {p}/libs.tech/ngspice/osdi/psp103.osdi\n"
    "osdi {p}/libs.tech/ngspice/osdi/psp103_nqs.osdi\n"
    "osdi {p}/libs.tech/ngspice/osdi/mosvar.osdi\n"
    "osdi {p}/libs.tech/ngspice/osdi/r3_cmc.osdi\n"
    "set num_threads=1\n"
).format(p=PDKV)

# ---- matrices: copied verbatim from run.sh ---------------------------------
MAIN_BUNDLES = [("mos_tt", "res_typ", "cap_typ"), ("mos_ss", "res_wcs", "cap_wcs"),
                ("mos_ff", "res_bcs", "cap_bcs"), ("mos_sf", "res_typ", "cap_typ"),
                ("mos_fs", "res_typ", "cap_typ")]
RES_ISO = [("mos_tt", "res_wcs", "cap_typ"), ("mos_tt", "res_bcs", "cap_typ")]
CAP_ISO = [("mos_tt", "res_typ", "cap_wcs"), ("mos_tt", "res_typ", "cap_bcs")]


def window_points():
    pts = []
    for b in MAIN_BUNDLES + RES_ISO + CAP_ISO:
        for t in ("-40", "27", "125"):
            pts.append((*b, t, VSUP_NOM, FREF_FAST))
    for t in ("-40", "27", "125"):
        for v in ("2.97", "3.63"):
            pts.append(("mos_tt", "res_typ", "cap_typ", t, v, FREF_FAST))
    for f in (FREF_SLOW, "12e6"):
        pts.append(("mos_tt", "res_typ", "cap_typ", "27", VSUP_NOM, f))
    pts.append(("mos_ff", "res_bcs", "cap_bcs", "-40", "3.63", FREF_FAST))
    pts.append(("mos_ss", "res_wcs", "cap_wcs", "125", "2.97", FREF_FAST))
    return pts


def ladder_points():
    pts = []
    for rc in ("res_typ", "res_bcs", "res_wcs"):
        for t in ("-40", "27", "125"):
            pts.append(("mos_tt", rc, "cap_typ", t, VSUP_NOM, FREF_SLOW))
    for rc, t in (("res_typ", "27"), ("res_bcs", "125"), ("res_wcs", "-40")):
        pts.append(("mos_tt", rc, "cap_typ", t, VSUP_NOM, FREF_FAST))
    pts.append(("mos_ff", "res_wcs", "cap_typ", "-40", VSUP_NOM, FREF_FAST))
    pts.append(("mos_ss", "res_bcs", "cap_typ", "125", VSUP_NOM, FREF_FAST))
    pts.append(("mos_tt", "res_typ", "cap_typ", "27", "3.63", FREF_FAST))
    for cap in ("cap_bcs", "cap_wcs"):
        pts.append(("mos_tt", "res_typ", cap, "27", VSUP_NOM, FREF_SLOW))
    for v in ("2.97", "3.63"):
        pts.append(("mos_tt", "res_typ", "cap_typ", "27", v, FREF_SLOW))
    for mos in ("mos_ff", "mos_ss"):
        pts.append((mos, "res_typ", "cap_typ", "27", VSUP_NOM, FREF_SLOW))
    return pts


def ftag(f):
    return ("%.1f" % (float(f) / 1e6)).replace(".", "p") + "MHz"


def ctag(mos, res, cap, temp, vsup, fref):
    return "%s_%s_%s_%sc_%sv_%s" % (mos, res, cap, temp, vsup, ftag(fref))


def uid(s):
    return s.replace("-", "m")


# ---- rendering ---------------------------------------------------------------
DUT_TEXT = SNAP.read_text()


def inline_dut(text):
    """Replace the template's `.include <DUT>` line by the frozen snapshot,
    verbatim (a deck-list request ships the deck byte-for-byte and stages an
    include only at a path next to the deck; inlining keeps one unit == one
    file with no second copy of the snapshot in the tree)."""
    out = []
    for line in text.splitlines(keepends=True):
        if line.startswith(".include ") and DUTNAME in line:
            out.append("* ---- netlist-snapshots/%s inlined verbatim ----\n" % DUTNAME)
            out.append(DUT_TEXT if DUT_TEXT.endswith("\n") else DUT_TEXT + "\n")
            out.append("* ---- end snapshot ----\n")
        else:
            out.append(line)
    return "".join(out)


def render(tmpl, subs):
    t = (HERE / tmpl).read_text()
    subs = dict(subs)
    subs.update({"@DUT@": DUTNAME, "@PDK_ROOT@/@PDK@": PDKV})
    # longest token first so `@PDK_ROOT@/@PDK@` wins over its parts
    for k in sorted(subs, key=len, reverse=True):
        t = t.replace(k, str(subs[k]))
    left = [m for m in re.findall(r"@[A-Z_0-9]+@", "\n".join(
        l for l in t.splitlines() if not l.lstrip().startswith("*")))]
    if left:
        raise SystemExit("unsubstituted tokens in %s: %s" % (tmpl, sorted(set(left))))
    return inline_dut(t)


def window_deck(mos, res, cap, temp, vsup, tstep="20p"):
    vmid = "%.6f" % (float(vsup) / 2)
    return render("tb_window.sp.tmpl", {
        "@CORNER_MOS@": mos, "@CORNER_RES@": res, "@CORNER_CAP@": cap,
        "@TEMP@": temp, "@VSUP@": vsup, "@VMID@": vmid, "@TSTEP@": tstep})


# ---- klt transport -----------------------------------------------------------
class Stage:
    def __init__(self, work, name):
        self.dir = Path(work) / name
        self.units = []          # (id, deck_text)

    def add(self, unit_id, text):
        assert unit_id not in dict(self.units), unit_id
        self.units.append((unit_id, text))

    def write_request(self, req_name="request"):
        d = self.dir / req_name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spiceinit.txt").write_text(SPICEINIT)
        decks = []
        for i, t in self.units:
            (d / (i + ".sp")).write_text(t)
            decks.append({"id": i, "deck": i + ".sp",
                          "inputs": [{"path": "spiceinit.txt", "name": ".spiceinit"}]})
        req = {"engine": "ngspice", "backend": "batch", "models": {"pdk": "ihp-sg13g2"},
               "decks": decks,
               "options": {"timeout_s": 3600, "keep_artifacts": True}}
        p = d / "request.json"
        p.write_text(json.dumps(req, indent=1) + "\n")
        return p


def klt(args, log):
    env = dict(os.environ, KLT_SIM_BACKEND="batch")
    with open(log, "w") as lf:
        return subprocess.call(["klt", "sim"] + args, env=env, stderr=lf)


def stdout_of(outdir, unit_id):
    # a unit that failed first time and passed on the recorded trtol=1 retry
    # (see `retry`) is read from the retry; the failed attempt stays on disk.
    rp = Path(outdir).parent / "retry" / "out" / unit_id / "stdout.bin"
    p = rp if rp.exists() else Path(outdir) / unit_id / "stdout.bin"
    return p.read_text(errors="replace") if p.exists() else None


def scalar(text, name):
    if text is None:
        return None
    m = re.search(r"^%s *= *([0-9.eE+-]+)" % re.escape(name), text, re.M)
    return m.group(1) if m else None


# ---- stage 1 -----------------------------------------------------------------
def stage1(work):
    st = Stage(work, "stage1")
    meta = {}
    for rc in ("res_typ", "res_bcs", "res_wcs"):
        for t in ("-40", "27", "125"):
            i = uid("R_%s_%s" % (rc, t))
            st.add(i, render("tb_extract_r.sp.tmpl", {
                "@RES_CORNER@": rc, "@TEMP@": t, "@W@": XRPU[0], "@L@": XRPU[1]}))
            meta[i] = ["R", rc, t]
    for inst, (w, l) in (("XCW", XCW), ("XDW.XC1", XC1)):
        for cc in ("cap_typ", "cap_bcs", "cap_wcs"):
            for t in ("-40", "27", "125"):
                i = uid("C_%s_%s_%s" % (inst, cc, t))
                st.add(i, render("tb_extract_c.sp.tmpl", {
                    "@CAP_CORNER@": cc, "@TEMP@": t, "@W@": w, "@L@": l, "@M@": "1"}))
                meta[i] = ["C", inst, cc, t, w, l]
    for p in window_points():
        mos, res, cap, t, v, f = p
        i = uid("W_" + ctag(*p))
        st.add(i, window_deck(mos, res, cap, t, v))
        meta[i] = ["W", *p]
    for mos in ("mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"):
        for t in ("-40", "27", "125"):
            for v in ("2.97", "3.3", "3.63"):
                i = uid("S_%s_%s_%s" % (mos, t, v))
                st.add(i, render("tb_schmitt_hyst.sp.tmpl", {
                    "@CORNER_MOS@": mos, "@TEMP@": t, "@VSUP@": v,
                    "@VMID@": "%.6f" % (float(v) / 2)}))
                meta[i] = ["S", mos, t, v]
    for tstep in ("20p", "5p", "1.25p"):
        for mos, res, cap, t in (("mos_tt", "res_typ", "cap_typ", "27"),
                                 ("mos_ss", "res_wcs", "cap_wcs", "125"),
                                 ("mos_ff", "res_bcs", "cap_bcs", "-40"),
                                 ("mos_sf", "res_typ", "cap_typ", "27")):
            i = uid("T_%s_%s_%s_%s_%s" % (mos, res, cap, t, tstep))
            st.add(i, window_deck(mos, res, cap, t, VSUP_NOM, tstep))
            meta[i] = ["T", mos, res, cap, t, tstep]
    seen = set()
    for p in ladder_points():           # per-ladder-corner window, as run.sh does
        k = ctag(*p)
        i = uid("LW_" + k)
        if i not in seen:
            seen.add(i)
            st.add(i, window_deck(p[0], p[1], p[2], p[3], p[4]))
            meta[i] = ["LW", *p]
    for mos, res, cap, t in (("mos_tt", "res_wcs", "cap_typ", "-40"),
                             ("mos_ff", "res_wcs", "cap_typ", "-40")):
        i = uid("DW_%s_%s_%s_%s" % (mos, res, cap, t))
        st.add(i, window_deck(mos, res, cap, t, VSUP_NOM))
        meta[i] = ["DW", mos, res, cap, t]
    req = st.write_request()
    (st.dir / "meta.json").write_text(json.dumps(meta, indent=1))
    print("stage1: %d units -> %s" % (len(st.units), req))
    return req


# ---- stage 2 -----------------------------------------------------------------
def load_s1(work):
    out = Path(work) / "stage1" / "out"
    meta = json.loads((Path(work) / "stage1" / "meta.json").read_text())
    R, C, LW, DW = {}, {}, {}, {}
    for i, m in meta.items():
        txt = stdout_of(out, i)
        if m[0] == "R":
            R[(m[1], m[2])] = scalar(txt, "rval")
        elif m[0] == "C" and m[1] == "XCW":
            cv = None
            for line in (txt or "").splitlines():
                if re.match(r"^0\s", line):
                    cv = line.split()[2]
                    break
            C[(m[2], m[3])] = cv
        elif m[0] == "LW":
            LW[ctag(*m[1:])] = scalar(txt, "twin_r")
        elif m[0] == "DW":
            DW[(m[1], m[2], m[3], m[4])] = scalar(txt, "twin_r")
    return R, C, LW, DW


def ladder_params(R, C, twin, res, cap, temp, fref):
    tref = 1.0 / float(fref)
    rc = float(R[(res, temp)]) * float(C[(cap, temp)])
    n_cycles = int(math.ceil(min(K_SETTLE * rc, float(TSTOP_MAX)) / tref))
    tstop = n_cycles * tref
    settle = "%.4f" % (1.0 - math.exp(-tstop / rc))
    return dict(tref=repr(tref), rc=rc, rc_over="%.6f" % (rc / tref), n_cycles=n_cycles,
                settle=settle, tstop=repr(tstop), tsettle=repr(tstop - 2 * tref),
                tstep=repr(tref / (TSTEP_DIV + 0.0)),
                taubig=repr(float(TAUBIG_XWIN) * float(twin)))


def stage2(work):
    R, C, LW, DW = load_s1(work)
    gspec = importlib.util.spec_from_file_location("gen_ladder", GEN)
    g = importlib.util.module_from_spec(gspec)
    gspec.loader.exec_module(g)
    npts = len(g.LADDER_FRACS_SETS[LADDER_SET])
    reqs = []
    plan = {"ladder": {}, "diag": {}}
    for p in ladder_points():
        mos, res, cap, temp, vsup, fref = p
        tag = ctag(*p)
        twin = LW.get(tag)
        if not twin:
            print("window failed for %s; ladder skipped (NA row)" % tag)
            continue
        lp = ladder_params(R, C, twin, res, cap, temp, fref)
        st = Stage(work, "stage2/ladder_" + uid(tag))
        st.add("base", render("tb_lock_recovery.sp.tmpl", {
            "@CORNER_MOS@": mos, "@CORNER_RES@": res, "@CORNER_CAP@": cap, "@TEMP@": temp,
            "@VSUP@": vsup, "@VMID@": "%.6f" % (float(vsup) / 2), "@TREF@": lp["tref"],
            "@TRST@": TRST, "@TAUBIG@": lp["taubig"], "@TSTEP@": lp["tstep"],
            "@TSTOP@": lp["tstop"], "@TSETTLE@": lp["tsettle"]}))
        for k in range(npts):
            tmp = st.dir / "_gen.sp"
            st.dir.mkdir(parents=True, exist_ok=True)
            subprocess.check_call([
                sys.executable, str(GEN), "gen", "--template", str(HERE / "tb_lock_ladder_point.sp.tmpl"),
                "--out", str(tmp), "--dut", DUTNAME, "--fracs-set", LADDER_SET,
                "--corner-mos", mos, "--corner-res", res, "--corner-cap", cap, "--temp", temp,
                "--vsup", vsup, "--tref", lp["tref"], "--trst", TRST, "--twin", twin,
                "--tstep", lp["tstep"], "--tstop", lp["tstop"], "--tsettle", lp["tsettle"],
                "--pdk-root", "$PDK_ROOT", "--pdk", "ihp-sg13g2", "--only-index", str(k)],
                stdout=subprocess.DEVNULL)
            st.add("pt%02d" % k, inline_dut(tmp.read_text()))
            tmp.unlink()
        reqs.append(str(st.write_request()))
        plan["ladder"][tag] = dict(twin=twin, dir=str(st.dir), **lp)
    # hysteresis diagnostic (run_hysteresis_diag.sh)
    for mos, res, cap, temp in (("mos_tt", "res_wcs", "cap_typ", "-40"),
                                ("mos_ff", "res_wcs", "cap_typ", "-40")):
        twin = DW[(mos, res, cap, temp)]
        rval, cval = R[(res, temp)], C[(cap, temp)]
        tref = 1.0 / float(DIAG_FREF)
        rc = float(rval) * float(cval)
        ncyc = int(math.ceil(min(K_SETTLE * rc, float(TSTOP_MAX)) / tref))
        tstop = ncyc * tref
        sfrac = "%.4f" % (1.0 - math.exp(-tstop / rc))
        tsettle, tstep = tstop - 2 * tref, tref / (TSTEP_DIV + 0.0)
        tag = "%s_%s_%s_%sc" % (mos, res, cap, temp)
        st = Stage(work, "stage2/diag_" + uid(tag))
        for frac in DIAG_FRACS:
            tau = "%.6e" % (float(frac) * float(twin))
            st.add("d%s" % frac.replace(".", "p"), render("tb_hyst_diag.sp.tmpl", {
                "@CORNER_MOS@": mos, "@CORNER_RES@": res, "@CORNER_CAP@": cap, "@TEMP@": temp,
                "@VSUP@": "3.3", "@TREF@": repr(tref), "@TRST@": "1n", "@TAU@": tau,
                "@TSTEP@": repr(tstep), "@TSTOP@": repr(tstop), "@TSETTLE@": repr(tsettle)}))
        reqs.append(str(st.write_request()))
        plan["diag"][tag] = dict(mos=mos, res=res, cap=cap, temp=temp, rval=rval, cval=cval,
                                 rc=repr(rc), ncyc=ncyc, sfrac=sfrac, twin=twin, dir=str(st.dir))
    (Path(work) / "stage2").mkdir(parents=True, exist_ok=True)
    (Path(work) / "stage2" / "plan.json").write_text(json.dumps(plan, indent=1))
    (Path(work) / "stage2" / "requests.txt").write_text("\n".join(reqs) + "\n")
    print("stage2: %d requests" % len(reqs))


# ---- retry (run.sh's run_ngspice_or_die: one recorded trtol=1 retry) ---------
def failed_units(rdir):
    rep = rdir / "report.json"
    if not rep.exists():
        return None
    r = json.loads(rep.read_text())
    return [u["id"] for u in r["units"] if u["status"] != "pass"]


def retry(work):
    """Per request dir whose report has non-pass units: write a retry request
    holding ONLY those decks with ` trtol=1` appended to the `.options reltol=`
    line (the exact edit run.sh makes), at <dir>/retry/.  Submit separately."""
    dirs = [Path(work) / "stage1"] + sorted((Path(work) / "stage2").glob("ladder_*")) \
        + sorted((Path(work) / "stage2").glob("diag_*"))
    reqs = []
    for d in dirs:
        bad = failed_units(d)
        if not bad:
            continue
        st = Stage(d, "retry")
        src = d / "request"
        for i in bad:
            t = (src / (i + ".sp")).read_text()
            t2 = re.sub(r"^(\.options reltol=.*)$", r"\1 trtol=1", t, flags=re.M)
            if t2 == t:
                raise SystemExit("no .options reltol= line in %s/%s" % (d, i))
            st.add(i, t2)
        reqs.append(str(st.write_request("request")))
        print("retry %s: %s" % (d.name, bad))
    (Path(work) / "retry_requests.txt").write_text("\n".join(reqs) + "\n")


# ---- reduce ------------------------------------------------------------------
def reduce_all(work):
    R, C, LW, DW = load_s1(work)
    meta = json.loads((Path(work) / "stage1" / "meta.json").read_text())
    out1 = Path(work) / "stage1" / "out"
    CORNERS.mkdir(exist_ok=True)

    def val(i, name):
        return scalar(stdout_of(out1, i), name) or "NA"

    with open(CORNERS / ("rc_extract" + SFX + ".csv"), "w") as f:
        f.write("kind,instance,corner,temp_c,w,l,m,value,source\n")
        for i, m in meta.items():
            if m[0] == "R":
                f.write("R,XRPU(rhigh),%s,%s,%s,%s,1,%s,ngspice-subckt\n"
                        % (m[1], m[2], XRPU[0], XRPU[1], R[(m[1], m[2])] or "NA"))
        for inst, (w, l) in (("XCW", XCW), ("XDW.XC1", XC1)):
            for cc in ("cap_typ", "cap_bcs", "cap_wcs"):
                for t in ("-40", "27", "125"):
                    i = uid("C_%s_%s_%s" % (inst, cc, t))
                    cv = None
                    for line in (stdout_of(out1, i) or "").splitlines():
                        if re.match(r"^0\s", line):
                            cv = line.split()[2]
                            break
                    f.write("C,%s(cap_cmim),%s,%s,%s,%s,1,%s,ngspice-subckt\n"
                            % (inst, cc, t, w, l, cv or "NA"))
    with open(CORNERS / ("window" + SFX + ".csv"), "w") as f:
        f.write("corner_tag,mos_corner,res_corner,cap_corner,temp_c,vsup_v,fref_hz,twin_r_s,twin_f_s\n")
        for p in window_points():
            i = uid("W_" + ctag(*p))
            f.write("%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (ctag(*p), *p, val(i, "twin_r"), val(i, "twin_f")))
    with open(CORNERS / ("schmitt" + SFX + ".csv"), "w") as f:
        f.write("mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd\n")
        for mos in ("mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"):
            for t in ("-40", "27", "125"):
                for v in ("2.97", "3.3", "3.63"):
                    i = uid("S_%s_%s_%s" % (mos, t, v))
                    u, d = scalar(stdout_of(out1, i), "vth_up"), scalar(stdout_of(out1, i), "vth_dn")
                    if u and d:
                        h = float(u) - float(d)
                        row = "%s,%s,%.6e,%.4f" % (u, d, h, 100 * h / float(v))
                    else:
                        row = "NA,NA,NA,NA"
                    f.write("%s,%s,%s,%s\n" % (mos, t, v, row))
    with open(CORNERS / ("tstep_convergence" + SFX + ".csv"), "w") as f:
        f.write("mos_corner,res_corner,cap_corner,temp_c,tstep,twin_r_s\n")
        for tstep in ("20p", "5p", "1.25p"):
            for mos, res, cap, t in (("mos_tt", "res_typ", "cap_typ", "27"),
                                     ("mos_ss", "res_wcs", "cap_wcs", "125"),
                                     ("mos_ff", "res_bcs", "cap_bcs", "-40"),
                                     ("mos_sf", "res_typ", "cap_typ", "27")):
                i = uid("T_%s_%s_%s_%s_%s" % (mos, res, cap, t, tstep))
                f.write("%s,%s,%s,%s,%s,%s\n" % (mos, res, cap, t, tstep, val(i, "twin_r")))

    plan = json.loads((Path(work) / "stage2" / "plan.json").read_text())
    hdr = ("corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,"
           "tau_deassert_xwin,hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,"
           "lock_max_deep_v,trec_s,vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,"
           "ladder_states_discharged_start,ladder_states_charged_start,rc_s,tref_s,rc_over_tref,"
           "n_cycles,settle_frac")
    rawhdr = ("corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,"
              "lka_max_v,lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v")
    gspec = importlib.util.spec_from_file_location("gen_ladder", GEN)
    g = importlib.util.module_from_spec(gspec)
    gspec.loader.exec_module(g)
    npts = len(g.LADDER_FRACS_SETS[LADDER_SET])
    missing = []
    with open(CORNERS / ("ladder" + SFX + ".csv"), "w") as lf, \
         open(CORNERS / ("ladder_raw" + SFX + ".csv"), "w") as rf:
        lf.write(hdr + "\n")
        rf.write(rawhdr + "\n")
        for p in ladder_points():
            tag = ctag(*p)
            if tag not in plan["ladder"]:
                lf.write(tag + "," + ",".join(["NA"] * 23) + "\n")
                continue
            pl = plan["ladder"][tag]
            out = Path(pl["dir"]) / "out"
            parts = []
            for i in ["base"] + ["pt%02d" % k for k in range(npts)]:
                t = stdout_of(out, i)
                if t is None:
                    missing.append("%s/%s" % (tag, i))
                    t = ""
                parts.append(t)
            rawtmp = Path(work) / ("raw_" + uid(tag))
            r = subprocess.run([sys.executable, str(GEN), "reduce", "--tag", tag, "--vsup", p[4],
                                "--fracs-set", LADDER_SET, "--twin", pl["twin"], "--raw", str(rawtmp)],
                               input="".join(parts), capture_output=True, text=True, check=True)
            lf.write(r.stdout.strip() + ",%.6e,%.6e,%s,%s,%s\n" % (
                pl["rc"], float(pl["tref"]), pl["rc_over"], pl["n_cycles"], pl["settle"]))
            rf.write(rawtmp.read_text())
    with open(CORNERS / ("hysteresis_diag" + SFX + ".csv"), "w") as f:
        f.write("corner_tag,mos_corner,res_corner,cap_corner,temp_c,vsup_v,fref_hz,r_xrpu_ohm,c_xcw_f,"
                "rc_s,n_cycles,settle_frac,twin_r_s,tau_xwin,tau_s,vwin_discharged_start_avg_v,"
                "vwin_charged_start_avg_v,lock_discharged_start_avg_v,lock_charged_start_avg_v\n")
        for tag, d in plan["diag"].items():
            out = Path(d["dir"]) / "out"
            for frac in DIAG_FRACS:
                t = stdout_of(out, "d%s" % frac.replace(".", "p"))
                tau = "%.6e" % (float(frac) * float(d["twin"]))
                g_ = lambda n: scalar(t, n) or ""
                f.write("%s,%s,%s,%s,%s,3.3,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (
                    tag, d["mos"], d["res"], d["cap"], d["temp"], DIAG_FREF, d["rval"], d["cval"],
                    d["rc"], d["ncyc"], d["sfrac"], d["twin"], frac, tau,
                    g_("va_avg"), g_("vb_avg"), g_("la_avg"), g_("lb_avg")))
    if missing:
        print("MISSING stdout for %d decks: %s" % (len(missing), missing[:10]))
    print("reduced -> %s/*%s.csv" % (CORNERS, SFX))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["stage1", "stage2", "retry", "reduce"])
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    {"stage1": stage1, "stage2": stage2, "retry": retry, "reduce": reduce_all}[a.step](a.work)
