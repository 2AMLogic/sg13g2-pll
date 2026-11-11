#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-lock-detector-window (issue #327, Part of #257/#213)

`klt sim` deck-list driver for RECORD-001's grid AS PRODUCED AT COMMIT db36732.

Why not `batch_grid.py --dut/--dir`: the db36732 grid is a different grid, not
just a different DUT file.  XRPU is l=6u (today 700u), XCW/XDW.XC1 are
8u/8u and 4u/4u*2 (today 40u), f_ref is 25/5/1 MHz (today 24.4/12/3.5 MHz),
the ladder is ONE 31-copy transient per point (today 22 decks per corner),
tstop is 4 reference periods, and there are 92 ladder points (today 21).  So
this module imports batch_grid.py for the generic machinery that is the same
(init block with pre_osdi, deck-list request writer, stdout lookup, scalar
parser, trtol=1 `retry`) and holds only the db36732 matrix and phase logic.

Source files are NOT copied into the repo: `src` materialises them with
`git show db36732:<path>` into WORKDIR/src, so the reconstruction is exact and
reproducible.  Decks are `run.sh`'s own templates with run.sh's substitutions,
the one deliberate difference being path-only: `$PDK` -> `ihp-sg13cmos5l`
(run.sh exports PDK; the fleet runner's deck-list unit has no such variable)
and `@DUT@` -> a sibling file name.  The raw `stdout.bin` of every deck is
reduced by db36732's own `gen_ladder.py reduce` and run.sh's own sed/awk
patterns.

Subcommands (WORKDIR is created if missing; no PDK_ROOT needed):

  src    WORKDIR                      git show db36732 files into WORKDIR/src
  gen    WORKDIR PHASE [--probe]      PHASE in phase0|phase1|phase2
  retry  WORKDIR PHASE                delegates to batch_grid.retry (trtol=1)
  reduce WORKDIR CORNERS_DIR          write corners/*_rerun327.csv
"""
import argparse
import importlib.util
import json
import math
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent
REPO = RECORD.parent.parent
COMMIT = "db36732"
SUFFIX = "rerun327"
SRC_FILES = {
    "testbench": ["gen_ladder.py", "mom_inject.py", "run.sh", "tb_extract_c.sp.tmpl",
                  "tb_extract_r.sp.tmpl", "tb_lock_ladder.sp.tmpl",
                  "tb_schmitt_hyst.sp.tmpl", "tb_window.sp.tmpl"],
    "netlist-snapshots": ["lock_detector.spice"],
}
RPU = ("0.5u", "6u")
XCW = ("XCW", "8u", "8u", 1)
XC1 = ("XDW.XC1", "4u", "4u", 2)
VSUP_NOM = "3.3"
TRST = "1n"


def _bg():
    spec = importlib.util.spec_from_file_location("batch_grid", HERE / "batch_grid.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


bg = _bg()
RC_LIST, TEMPS = ["res_typ", "res_bcs", "res_wcs"], [-40, 27, 125]


def src(work):
    d = pathlib.Path(work) / "src"
    base = RECORD.relative_to(REPO).as_posix()
    for sub, names in SRC_FILES.items():
        (d / sub).mkdir(parents=True, exist_ok=True)
        for n in names:
            data = subprocess.check_output(["git", "-C", str(REPO), "show", "%s:%s/%s/%s" % (COMMIT, base, sub, n)])
            (d / sub / n).write_bytes(data)
    print("materialised %s files from %s into %s" % (sum(map(len, SRC_FILES.values())), COMMIT, d))


def tpl(work, name):
    return (work / "src" / "testbench" / name).read_text()


def fix_paths(text):
    return text.replace("$PDK/", bg.PDK + "/")


def render(work, name, subs):
    text = tpl(work, name)
    for k, v in subs.items():
        text = text.replace(k, str(v))
    left = [l for l in text.splitlines() if not l.startswith("*") and re.search(r"@[A-Z_0-9]+@", l)]
    if left:
        raise SystemExit("unsubstituted placeholders in %s: %s" % (name, left))
    return bg.with_init(fix_paths(text), osdi_cmomi=True)


def variants():
    return ["real", "ideal-0.20", "ideal0.00", "ideal0.20"]


def points():
    """run.sh section 3, verbatim order: (mos res temp vsup fref variant)."""
    pts = []
    for mos, res in [("mos_tt", "res_typ"), ("mos_ss", "res_wcs"), ("mos_ff", "res_bcs"),
                     ("mos_sf", "res_typ"), ("mos_fs", "res_typ"),
                     ("mos_tt", "res_wcs"), ("mos_tt", "res_bcs")]:
        for temp in TEMPS:
            for var in variants():
                pts.append((mos, res, temp, VSUP_NOM, "25e6", var))
    for temp in TEMPS:
        for vsup in ("2.97", "3.63"):
            pts.append(("mos_tt", "res_typ", temp, vsup, "25e6", "real"))
    for fref in ("1e6", "5e6"):
        pts.append(("mos_tt", "res_typ", 27, VSUP_NOM, fref, "real"))
    assert len(pts) == 92
    return pts


def tag_of(mos, res, temp, vsup, fref, var):
    return "%s_%s_%sc_%sv_%dMHz_%s" % (mos, res, temp, vsup, int(float(fref) / 1e6), var)


def win_uid(mos, res, temp, vsup, var):
    return "win_%s_%s_%sc_%sv_%s" % (mos, res, temp, vsup, var)


def tstep_probes():
    return ["20p", "5p", "1.25p"], [("mos_tt", "res_typ", 27, "real"), ("mos_ss", "res_wcs", 125, "ideal0.20"),
                                    ("mos_ff", "res_bcs", -40, "ideal-0.20"), ("mos_sf", "res_typ", 27, "real")]


def phase0(work, probe):
    units = []
    for rc in RC_LIST:
        for t in TEMPS:
            if probe and (rc, t) != ("res_typ", 27):
                continue
            units.append(("R_%s_%s" % (rc, t), render(work, "tb_extract_r.sp.tmpl", {
                "@RES_CORNER@": rc, "@TEMP@": t, "@W@": RPU[0], "@L@": RPU[1]}), []))
    for inst, w, l, m in (XCW, XC1):
        for t in TEMPS:
            if probe and (inst, t) != ("XCW", 27):
                continue
            units.append(("C_%s_%s" % (inst, t), render(work, "tb_extract_c.sp.tmpl", {
                "@W@": w, "@L@": l, "@M@": m, "@TEMP@": t}), []))
    bg.write_request(work / ("probe" if probe else "phase0"), units)


def c_nominals(work):
    cn, rows, rval = {}, [], {}
    for rc in RC_LIST:
        for t in TEMPS:
            txt, _ = bg.stdout_of(work, "phase0", "R_%s_%s" % (rc, t))
            v = bg.scalar(txt, "rval")
            rval[(rc, t)] = v
            rows.append("R,XRPU(rhigh),%s,%s,%s,%s,1,%s" % (rc, t, RPU[0], RPU[1], v or "NA"))
    for inst, w, l, m in (XCW, XC1):
        for t in TEMPS:
            txt, _ = bg.stdout_of(work, "phase0", "C_%s_%s" % (inst, t))
            mm = re.search(r"^0\s+\S+\s+(\S+)", txt, re.M)
            if mm is None:
                # run.sh has no closed-form fallback: a missing cap_cmomi is a hard failure.
                raise SystemExit("cap_cmomi extraction failed for %s/%s on the fleet; no fallback (as run.sh)" % (inst, t))
            rows.append("C,%s(cap_cmomi),none,%s,%s,%s,%s,%s" % (inst, t, w, l, m, mm.group(1)))
            if t == 27:
                cn[inst] = mm.group(1)
    return cn, rows


def build_duts(work, cn):
    d = work / "duts"
    d.mkdir(exist_ok=True)
    tb = work / "src" / "testbench"
    snap = work / "src" / "netlist-snapshots" / "lock_detector.spice"
    subprocess.check_call([sys.executable, "-I", str(tb / "mom_inject.py"), str(snap), str(d / "dut_real.spice"), "real"])
    for frac in ("-0.20", "0.00", "0.20"):
        subprocess.check_call([sys.executable, "-I", str(tb / "mom_inject.py"), str(snap),
                               str(d / ("dut_ideal%s.spice" % frac)), "ideal", frac, cn["XCW"], cn["XDW.XC1"]])
    return d


def phase1(work, probe):
    cn, _ = c_nominals(work)
    duts = build_duts(work, cn)
    dut = lambda v: duts / ("dut_%s.spice" % v)
    units, seen = [], set()
    for mos, res, temp, vsup, fref, var in points():
        uid = win_uid(mos, res, temp, vsup, var)
        if uid in seen:
            continue
        seen.add(uid)
        t = render(work, "tb_window.sp.tmpl", {
            "@CORNER_MOS@": mos, "@CORNER_RES@": res, "@TEMP@": temp, "@VSUP@": vsup,
            "@VMID@": "%.6f" % (float(vsup) / 2), "@TSTEP@": "20p", "@DUT@": "dut_%s.spice" % var})
        units.append((uid, t, [dut(var)]))
    for mos in ("mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"):
        for temp in TEMPS:
            for vsup in ("2.97", "3.3", "3.63"):
                t = render(work, "tb_schmitt_hyst.sp.tmpl", {
                    "@CORNER_MOS@": mos, "@TEMP@": temp, "@VSUP@": vsup,
                    "@VMID@": "%.6f" % (float(vsup) / 2), "@DUT@": "dut_real.spice"})
                units.append(("sch_%s_%s_%s" % (mos, temp, vsup), t, [dut("real")]))
    tsteps, probes = tstep_probes()
    for tstep in tsteps:
        for mos, res, temp, var in probes:
            t = render(work, "tb_window.sp.tmpl", {
                "@CORNER_MOS@": mos, "@CORNER_RES@": res, "@TEMP@": temp, "@VSUP@": VSUP_NOM,
                "@VMID@": "1.65", "@TSTEP@": tstep, "@DUT@": "dut_%s.spice" % var})
            units.append(("ts_%s_%s_%s_%s_%s" % (tstep, mos, res, temp, var), t, [dut(var)]))
    bg.write_request(work / "phase1", units)


def twin_r(work, mos, res, temp, vsup, var):
    txt, _ = bg.stdout_of(work, "phase1", win_uid(mos, res, temp, vsup, var))
    return bg.scalar(txt, "twin_r")


def ladder_params(fref):
    f = float(fref)
    t = 1.0 / f
    return "%.6e" % t, "%.6e" % (4 * t), "%.6e" % (2 * t), "%.6e" % (t / 500)


def phase2(work, probe):
    tb = work / "src" / "testbench"
    units = []
    for pt in points():
        mos, res, temp, vsup, fref, var = pt
        tw = twin_r(work, mos, res, temp, vsup, var)
        if tw is None:
            continue  # reduce emits run.sh's NA row
        tref, tstop, tsettle, tstep = ladder_params(fref)
        out = work / "phase2" / "tmp.sp"
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([sys.executable, "-I", str(tb / "gen_ladder.py"), "gen",
                               "--template", str(tb / "tb_lock_ladder.sp.tmpl"), "--out", str(out),
                               "--dut", "dut_%s.spice" % var, "--corner-mos", mos, "--corner-res", res,
                               "--temp", str(temp), "--vsup", vsup, "--tref", tref, "--trst", TRST,
                               "--twin", tw, "--tstep", tstep, "--tstop", tstop, "--tsettle", tsettle],
                              stdout=subprocess.DEVNULL)
        text = bg.with_init(fix_paths(out.read_text()), osdi_cmomi=True)
        out.unlink()
        units.append(("lad_%s" % tag_of(*pt), text, [work / "duts" / ("dut_%s.spice" % var)]))
    bg.write_request(work / "phase2", units, timeout_s=3600)


def reduce_all(work, corners):
    tb = work / "src" / "testbench"
    out = SUFFIX
    retried = []

    def used(phase, uid, tag):
        _, r = bg.stdout_of(work, phase, uid)
        if r:
            retried.append("%s (%s)" % (tag, uid))

    _, rc_rows = c_nominals(work)
    (corners / ("rc_extract_%s.csv" % out)).write_text("kind,instance,corner,temp_c,w,l,m,value\n" + "\n".join(rc_rows) + "\n")

    rows = ["corner_tag,mos_corner,res_corner,temp_c,vsup_v,fref_hz,dut_variant,twin_r_s,twin_f_s"]
    for mos, res, temp, vsup, fref, var in points():
        txt, _ = bg.stdout_of(work, "phase1", win_uid(mos, res, temp, vsup, var))
        tr, tf = bg.scalar(txt, "twin_r"), bg.scalar(txt, "twin_f")
        rows.append("%s,%s,%s,%s,%s,%s,%s,%s,%s" % (tag_of(mos, res, temp, vsup, fref, var), mos, res, temp,
                                                    vsup, fref, var, tr or "NA", tf or "NA"))
    (corners / ("window_%s.csv" % out)).write_text("\n".join(rows) + "\n")
    for mos, res, temp, vsup, fref, var in points():
        used("phase1", win_uid(mos, res, temp, vsup, var), "window " + tag_of(mos, res, temp, vsup, fref, var))

    rows = ["mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd"]
    for mos in ("mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"):
        for temp in TEMPS:
            for vsup in ("2.97", "3.3", "3.63"):
                uid = "sch_%s_%s_%s" % (mos, temp, vsup)
                txt, _ = bg.stdout_of(work, "phase1", uid)
                used("phase1", uid, "schmitt " + uid)
                u, d = bg.scalar(txt, "vth_up"), bg.scalar(txt, "vth_dn")
                r = ("%s,%s,%.6e,%.4f" % (u, d, float(u) - float(d), 100 * (float(u) - float(d)) / float(vsup))
                     if u and d else "NA,NA,NA,NA")
                rows.append("%s,%s,%s,%s" % (mos, temp, vsup, r))
    (corners / ("schmitt_%s.csv" % out)).write_text("\n".join(rows) + "\n")

    rows = ["mos_corner,res_corner,temp_c,dut_variant,tstep,twin_r_s"]
    tsteps, probes = tstep_probes()
    for tstep in tsteps:
        for mos, res, temp, var in probes:
            uid = "ts_%s_%s_%s_%s_%s" % (tstep, mos, res, temp, var)
            txt, _ = bg.stdout_of(work, "phase1", uid)
            used("phase1", uid, "tstep " + uid)
            rows.append("%s,%s,%s,%s,%s,%s" % (mos, res, temp, var, tstep, bg.scalar(txt, "twin_r") or "NA"))
    (corners / ("tstep_convergence_%s.csv" % out)).write_text("\n".join(rows) + "\n")

    lrows = ["corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,tau_deassert_xwin,"
             "hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,lock_max_deep_v,trec_s,"
             "vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,"
             "ladder_states_discharged_start,ladder_states_charged_start"]
    rawf = corners / ("ladder_raw_%s.csv" % out)
    rawf.write_text("corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,lka_max_v,"
                    "lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v\n")
    for pt in points():
        mos, res, temp, vsup, fref, var = pt
        tag = tag_of(*pt)
        tw = twin_r(work, mos, res, temp, vsup, var)
        if tw is None:
            lrows.append(tag + ",NA" * 18)
            continue
        uid = "lad_%s" % tag
        txt, _ = bg.stdout_of(work, "phase2", uid)
        used("phase2", uid, "ladder " + tag)
        r = subprocess.run([sys.executable, "-I", str(tb / "gen_ladder.py"), "reduce", "--tag", tag,
                            "--vsup", vsup, "--twin", tw, "--raw", str(rawf)],
                           input=txt, capture_output=True, text=True, check=True)
        lrows.append(r.stdout.strip())
    (corners / ("ladder_%s.csv" % out)).write_text("\n".join(lrows) + "\n")
    (corners / ("solver_retries_%s.txt" % out)).write_text("".join(x + "\n" for x in sorted(set(retried))))
    print("solver retries: %d unit(s) needed trtol=1" % len(set(retried)), file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("src").add_argument("workdir")
    g = sub.add_parser("gen")
    g.add_argument("workdir"); g.add_argument("phase", choices=["phase0", "phase1", "phase2"])
    g.add_argument("--probe", action="store_true")
    r = sub.add_parser("retry")
    r.add_argument("workdir"); r.add_argument("phase", choices=["phase0", "phase1", "phase2"])
    d = sub.add_parser("reduce")
    d.add_argument("workdir"); d.add_argument("corners")
    a = p.parse_args()
    work = pathlib.Path(a.workdir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    if a.cmd == "src":
        src(work)
    elif a.cmd == "gen":
        {"phase0": phase0, "phase1": phase1, "phase2": phase2}[a.phase](work, a.probe)
    elif a.cmd == "retry":
        bg.retry(work, a.phase)
    else:
        reduce_all(work, pathlib.Path(a.corners).resolve())


if __name__ == "__main__":
    main()
