#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-lock-detector-window (issue #322, Part of #139)

`klt sim` batch-request generator + reducer for the lock_detector full grid.

run.sh loops local `ngspice -b`; dispatch workers forbid that (host rules:
corner grids go to the batch fleet).  This module re-expresses the SAME grid
as `klt sim` **deck-list requests** (`decks[]`, klt docs "Pre-composed
decks"): run.sh's own templates are rendered here with the same substitutions
and shipped verbatim, the fleet runs `ngspice -b` on each, and the raw
`stdout.bin` of every deck comes back and is reduced by the SAME parsers
(`sim/tools/gen_lock_ladder.py reduce`, the same sed/awk patterns run.sh
uses).  A corner-style request (`corners`/`analysis`/`measurements`) would
mint a different artifact from the one RECORD-001..006 minted, so it is not
used.

The grid has data dependencies run.sh resolves by running serially, so it is
three submissions (each a single `klt sim` call, driven by run_batch.sh):

  phase0  R extraction (rhigh) + C extraction (cap_cmomi, real model)
  phase1  window, Schmitt, tstep-convergence decks  (need C for ideal DUTs)
  phase2  ladder decks: per corner 1 recovery deck + N ladder-point decks
          (need twin_r from phase1 and R*C from phase0)

then `reduce` writes the CSV set with a NEW suffix (`bodyfix_batch`, or
`bodyfix_batch_nominal` under --nominal), never run.sh's `bodyfix*`.

Subcommands (all take WORKDIR; PDK_ROOT is NOT needed -- decks carry the
literal `$PDK_ROOT/...` the runner expands against its own PDK image):

  gen   WORKDIR PHASE [--nominal]   write WORKDIR/PHASE/{request.json,decks}
  retry WORKDIR PHASE               trtol=1 retry request for errored units
  reduce WORKDIR CORNERS_DIR [--nominal]

Retry mapping (AC 2): run.sh retries a failed deck ONCE with `trtol=1`.
A deck-list job cannot retry in-fleet, so `retry` re-renders each errored
unit with trtol=1 appended to its `.options reltol=` line and run_batch.sh
resubmits only those; each is logged to solver_retries_<out>.txt exactly as
run.sh does.  A unit that fails the retry too aborts reduce.
"""
import argparse
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent
TOOLS = RECORD.parent / "tools"
SNAP = RECORD / "netlist-snapshots" / "lock_detector_bodyfix.spice"
PDK = "ihp-sg13cmos5l"
PDK_REF = "$PDK_ROOT/" + PDK
OSDI_DIR = PDK_REF + "/libs.tech/ngspice/osdi"
OSDI_HARD = ["psp103", "psp103_nqs", "mosvar", "r3_cmc"]

VSUP_NOM = "3.3"
TRST = "1n"
K_SETTLE = 4
TSTOP_MAX = 16e-6
TSTEP_DIV = 25
RPU_W, RPU_L = "0.5u", "700u"
XCW = ("XCW", 40, 40, 1)
XC1 = ("XDW.XC1", 40, 40, 2)
LADDER_SET = "hystfix"
SUFFIX = "bodyfix_batch"


# ----------------------------------------------------------------- helpers
def ftag(fref):
    return ("%.1f" % (float(fref) / 1e6)).replace(".", "p") + "MHz"


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def gen_mod():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen_ladder", TOOLS / "gen_lock_ladder.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def render(tmpl, subs, extra_control=True):
    """Template -> deck text, same sed-style substitution as run.sh.

    A `.control` block carrying pre_osdi + num_threads (what run.sh puts in
    .spiceinit) is inserted after the title line, since a deck-list unit has
    no .spiceinit.  pre_osdi runs before the circuit is parsed.
    """
    text = (HERE / tmpl).read_text()
    subs = dict(subs, **{"@PDK_ROOT@": "$PDK_ROOT", "@PDK@": PDK})
    for k, v in subs.items():
        text = text.replace(k, str(v))
    left = [l for l in text.splitlines()
            if not l.startswith("*") and re.search(r"@[A-Z_0-9]+@", l)]
    if left:
        raise SystemExit("batch_grid: unsubstituted placeholders in %s: %s" % (tmpl, left))
    return with_init(text, osdi_cmomi=True)


def with_init(text, osdi_cmomi):
    objs = list(OSDI_HARD) + (["cap_cmomi"] if osdi_cmomi else [])
    head = [".control"] + ["pre_osdi %s/%s.osdi" % (OSDI_DIR, o) for o in objs] \
        + ["set num_threads=1", ".endc"]
    lines = text.splitlines()
    return "\n".join(lines[:1] + head + lines[1:]) + "\n"


def write_request(phase_dir, units, timeout_s=3600):
    """units: list of (id, deck_text, inputs[list of Path], outputs)."""
    decks = []
    for uid, text, inputs in units:
        (phase_dir / "decks").mkdir(parents=True, exist_ok=True)
        (phase_dir / "decks" / (uid + ".sp")).write_text(text)
        d = {"id": uid, "deck": "decks/%s.sp" % uid}
        if inputs:
            # klt resolves a deck's relative `.include` against the DECK's own
            # directory and stages that closure itself (declaring it under
            # `inputs` too is refused as a duplicate destination), so the DUT
            # file just sits next to the decks.
            for p in inputs:
                shutil.copyfile(p, phase_dir / "decks" / pathlib.Path(p).name)
        decks.append(d)
    req = {
        "engine": "ngspice",
        "backend": "batch",
        "models": {"pdk": PDK},
        "decks": decks,
        "options": {"timeout_s": timeout_s, "max_workers": 2},
    }
    (phase_dir / "request.json").write_text(json.dumps(req, indent=2) + "\n")
    (phase_dir / "units.json").write_text(json.dumps([u[0] for u in units], indent=2) + "\n")
    print("wrote %s (%d decks)" % (phase_dir / "request.json", len(decks)))


def stdout_of(work, phase, uid):
    """Raw stdout text of a unit, preferring its trtol=1 retry result."""
    for d in (work / (phase + "_retry") / "out", work / phase / "out"):
        p = d / uid / "stdout.bin"
        if p.exists():
            return p.read_text(errors="replace"), d.parent.name.endswith("_retry")
    raise SystemExit("batch_grid: no result for unit %s in %s (run its klt sim first)" % (uid, phase))


def scalar(text, name):
    m = re.search(r"^%s *= *([0-9.eE+-]+)" % re.escape(name), text, re.M)
    return m.group(1) if m else None


# --------------------------------------------------------------- matrices
def matrices(nominal):
    """The grid, copied from run.sh sections 1-6 (kept in step by the parity run)."""
    if nominal:
        rc_list, temp_list = ["res_typ"], [27]
    else:
        rc_list, temp_list = ["res_typ", "res_bcs", "res_wcs"], [-40, 27, 125]
    return rc_list, temp_list


def variants(have_cmomi):
    v = ["ideal-0.20", "ideal0.00", "ideal0.20"]
    return (["real"] + v) if have_cmomi else v


def window_points(nominal, primary, vs):
    if nominal:
        return [("mos_tt", "res_typ", 27, VSUP_NOM, "24.4e6", primary)]
    pts = []
    for mos, res in [("mos_tt", "res_typ"), ("mos_ss", "res_wcs"), ("mos_ff", "res_bcs"),
                     ("mos_sf", "res_typ"), ("mos_fs", "res_typ"),
                     ("mos_tt", "res_wcs"), ("mos_tt", "res_bcs")]:
        for temp in (-40, 27, 125):
            for var in vs:
                pts.append((mos, res, temp, VSUP_NOM, "24.4e6", var))
    for temp in (-40, 27, 125):
        for vsup in ("2.97", "3.63"):
            pts.append(("mos_tt", "res_typ", temp, vsup, "24.4e6", primary))
            pts.append(("mos_tt", "res_typ", temp, vsup, "24.4e6", "ideal-0.20"))
    for fref in ("3.5e6", "12e6"):
        pts.append(("mos_tt", "res_typ", 27, VSUP_NOM, fref, primary))
    for var in ("ideal-0.20", primary):
        for vsup in ("3.63", "3.3"):
            pts.append(("mos_ff", "res_bcs", -40, vsup, "24.4e6", var))
    return pts


def ladder_points(nominal, primary):
    if nominal:
        return [("mos_tt", "res_typ", 27, VSUP_NOM, "3.5e6", primary)]
    p = []
    for res in ("res_typ", "res_bcs", "res_wcs"):
        for temp in (-40, 27, 125):
            p.append(("mos_tt", res, temp, VSUP_NOM, "3.5e6", primary))
    for res, temp in (("res_typ", 27), ("res_bcs", 125), ("res_wcs", -40)):
        p.append(("mos_tt", res, temp, VSUP_NOM, "24.4e6", primary))
    p.append(("mos_ff", "res_wcs", -40, VSUP_NOM, "24.4e6", primary))
    p.append(("mos_ss", "res_bcs", 125, VSUP_NOM, "24.4e6", primary))
    p.append(("mos_tt", "res_typ", 27, "3.63", "24.4e6", primary))
    for var in ("ideal-0.20", "ideal0.20"):
        p.append(("mos_tt", "res_typ", 27, VSUP_NOM, "3.5e6", var))
    for mos in ("mos_ff", "mos_ss"):
        p.append((mos, "res_typ", 27, VSUP_NOM, "3.5e6", primary))
    for vsup in ("2.97", "3.63"):
        p.append(("mos_tt", "res_typ", 27, vsup, "3.5e6", primary))
    return p


def tstep_probes(nominal, primary):
    if nominal:
        return ["20p"], [("mos_tt", "res_typ", 27, primary)]
    return (["20p", "5p", "1.25p"],
            [("mos_tt", "res_typ", 27, primary), ("mos_ss", "res_wcs", 125, "ideal0.20"),
             ("mos_ff", "res_bcs", -40, "ideal-0.20"), ("mos_sf", "res_typ", 27, primary)])


def schmitt_points(nominal):
    if nominal:
        return ["mos_tt"], [3.3]
    return ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"], [2.97, 3.3, 3.63]


def tag_of(mos, res, temp, vsup, fref, var):
    return "%s_%s_%sc_%sv_%s_%s" % (mos, res, temp, vsup, ftag(fref), var)


# ------------------------------------------------------------------ phases
def phase0(work, nominal):
    rc_list, temp_list = matrices(nominal)
    units = []
    for rc in rc_list:
        for t in temp_list:
            text = render("tb_extract_r.sp.tmpl", {
                "@RES_CORNER@": rc, "@TEMP@": t, "@W@": RPU_W, "@L@": RPU_L})
            units.append(("R_%s_%s" % (rc, t), text, []))
    for inst, w, l, m in (XCW, XC1):
        for t in temp_list:
            text = render("tb_extract_c.sp.tmpl", {
                "@W@": "%du" % w, "@L@": "%du" % l, "@M@": m, "@TEMP@": t})
            units.append(("C_%s_%s" % (inst, t), text, []))
    write_request(work / "phase0", units)


def c_values(work, nominal):
    """-> (have_cmomi, {inst: C}, rc_rows, rvals).  Falls back to the closed
    form (cmomi_nominal.py) when the fleet's cap_cmomi deck did not load,
    exactly as run.sh does when its preflight exits 3; that is recorded in
    the `source` column."""
    rc_list, temp_list = matrices(nominal)
    rows, rval = [], {}
    for rc in rc_list:
        for t in temp_list:
            txt, _ = stdout_of(work, "phase0", "R_%s_%s" % (rc, t))
            v = scalar(txt, "rval")
            rows.append("R,XRPU(rhigh),%s,%s,%s,%s,1,%s,ngspice-osdi" % (rc, t, RPU_W, RPU_L, v or "NA"))
            rval[(rc, t)] = v
    have, cnom = True, {}
    cvals = {}
    for inst, w, l, m in (XCW, XC1):
        for t in temp_list:
            txt, _ = stdout_of(work, "phase0", "C_%s_%s" % (inst, t))
            mm = re.search(r"^0\s+\S+\s+(\S+)", txt, re.M)
            cvals[(inst, t)] = mm.group(1) if mm else None
            if mm is None:
                have = False
    for inst, w, l, m in (XCW, XC1):
        for t in temp_list:
            if have:
                v, src = cvals[(inst, t)], "ngspice-osdi"
            else:
                v = subprocess.check_output([sys.executable, "-I", str(HERE / "cmomi_nominal.py"),
                                             str(w), str(l), str(m)], text=True).strip()
                src = "va-formula"
            rows.append("C,%s(cap_cmomi),none,%s,%su,%su,%s,%s,%s" % (inst, t, w, l, m, v or "NA", src))
            if t == 27:
                cnom[inst] = v
    return have, cnom, rows, rval


def build_duts(work, have, cnom):
    d = work / "duts"
    d.mkdir(exist_ok=True)
    mi = HERE / "mom_inject.py"
    if have:
        subprocess.check_call([sys.executable, "-I", str(mi), str(SNAP), str(d / "dut_real.spice"), "real"])
    for frac in ("-0.20", "0.00", "0.20"):
        subprocess.check_call([sys.executable, "-I", str(mi), str(SNAP), str(d / ("dut_ideal%s.spice" % frac)),
                               "ideal", frac, cnom["XCW"], cnom["XDW.XC1"]])
    return d


def phase1(work, nominal):
    have, cnom, _, _ = c_values(work, nominal)
    duts = build_duts(work, have, cnom)
    primary = "real" if have else "ideal0.00"
    vs = variants(have)
    units = []
    seen = set()

    def dut(var):
        return duts / ("dut_%s.spice" % var)

    def win(mos, res, temp, vsup, var, tstep, uid):
        vmid = "%.6f" % (float(vsup) / 2)
        return render("tb_window.sp.tmpl", {
            "@CORNER_MOS@": mos, "@CORNER_RES@": res, "@TEMP@": temp, "@VSUP@": vsup,
            "@VMID@": vmid, "@TSTEP@": tstep, "@DUT@": "dut_%s.spice" % var}), [dut(var)]

    wpts = window_points(nominal, primary, vs)
    # every ladder corner's twin_r is that corner's own window deck
    for lp in ladder_points(nominal, primary):
        mos, res, temp, vsup, fref, var = lp
        wpts.append((mos, res, temp, vsup, fref, var))
    for mos, res, temp, vsup, fref, var in wpts:
        uid = "win_%s_%s_%sc_%sv_%s" % (mos, res, temp, vsup, var)
        if uid in seen:
            continue
        seen.add(uid)
        t, inp = win(mos, res, temp, vsup, var, "20p", uid)
        units.append((uid, t, inp))
    smos, svsup = schmitt_points(nominal)
    _, temp_list = matrices(nominal)
    for mos in smos:
        for temp in temp_list:
            for vsup in svsup:
                vmid = "%.6f" % (float(vsup) / 2)
                t = render("tb_schmitt_hyst.sp.tmpl", {
                    "@CORNER_MOS@": mos, "@TEMP@": temp, "@VSUP@": vsup, "@VMID@": vmid,
                    "@DUT@": "dut_%s.spice" % primary})
                units.append(("sch_%s_%s_%s" % (mos, temp, vsup), t, [dut(primary)]))
    tsteps, probes = tstep_probes(nominal, primary)
    for tstep in tsteps:
        for mos, res, temp, var in probes:
            t = render("tb_window.sp.tmpl", {
                "@CORNER_MOS@": mos, "@CORNER_RES@": res, "@TEMP@": temp, "@VSUP@": VSUP_NOM,
                "@VMID@": "1.65", "@TSTEP@": tstep, "@DUT@": "dut_%s.spice" % var})
            units.append(("ts_%s_%s_%s_%s_%s" % (tstep, mos, res, temp, var), t, [dut(var)]))
    write_request(work / "phase1", units)
    (work / "state.json").write_text(json.dumps({"have_cmomi": have, "primary": primary}) + "\n")


def twin(work, mos, res, temp, vsup, var):
    txt, _ = stdout_of(work, "phase1", "win_%s_%s_%sc_%sv_%s" % (mos, res, temp, vsup, var))
    return scalar(txt, "twin_r"), scalar(txt, "twin_f")


def ladder_params(work, nominal, pt, rval, cnom):
    mos, res, temp, vsup, fref, var = pt
    tr, _ = twin(work, mos, res, temp, vsup, var)
    if tr is None:
        return None
    tref = 1.0 / float(fref)
    c = {"ideal-0.20": 0.8, "ideal0.20": 1.2}.get(var, 1.0) * float(cnom["XCW"])
    rc = float(rval[(res, temp)]) * c
    n_cycles = int(math.ceil(min(K_SETTLE * rc, TSTOP_MAX) / tref))
    tstop = n_cycles * tref
    settle = 1.0 - math.exp(-tstop / rc)
    return dict(tr=tr, tref=tref, rc=rc, n_cycles=n_cycles, tstop=tstop, settle=settle,
                tsettle=tstop - 2 * tref, tstep=tref / TSTEP_DIV, rc_over=rc / tref)


def phase2(work, nominal):
    st = load(work / "state.json")
    have, primary = st["have_cmomi"], st["primary"]
    _, cnom, _, rval = c_values(work, nominal)
    g = gen_mod()
    nfr = len(g.LADDER_FRACS_SETS[LADDER_SET])
    duts = work / "duts"
    units = []
    for pt in ladder_points(nominal, primary):
        mos, res, temp, vsup, fref, var = pt
        p = ladder_params(work, nominal, pt, rval, cnom)
        if p is None:
            continue  # reduce emits run.sh's NA row for this corner
        tag = tag_of(*pt)
        dutf = duts / ("dut_%s.spice" % var)
        vmid = "%.6f" % (float(vsup) / 2)
        taubig = "%s" % (float(p["tr"]) * 10.00)
        base = render("tb_lock_recovery.sp.tmpl", {
            "@CORNER_MOS@": mos, "@CORNER_RES@": res, "@TEMP@": temp, "@VSUP@": vsup, "@VMID@": vmid,
            "@TREF@": p["tref"], "@TRST@": TRST, "@TAUBIG@": taubig, "@TSTEP@": p["tstep"],
            "@TSTOP@": p["tstop"], "@TSETTLE@": p["tsettle"], "@DUT@": "dut_%s.spice" % var})
        units.append(("lad_%s_base" % tag, base, [dutf]))
        for k in range(nfr):
            out = work / "phase2" / ("pt_%s_%d.tmp" % (tag, k))
            out.parent.mkdir(parents=True, exist_ok=True)
            subprocess.check_call(
                [sys.executable, "-I", str(TOOLS / "gen_lock_ladder.py"), "gen",
                 "--template", str(HERE / "tb_lock_ladder_point.sp.tmpl"), "--out", str(out),
                 "--dut", "dut_%s.spice" % var, "--fracs-set", LADDER_SET,
                 "--corner-mos", mos, "--corner-res", res, "--temp", str(temp), "--vsup", vsup,
                 "--tref", str(p["tref"]), "--trst", TRST, "--twin", p["tr"],
                 "--tstep", str(p["tstep"]), "--tstop", str(p["tstop"]),
                 "--tsettle", str(p["tsettle"]), "--pdk-root", "$PDK_ROOT", "--pdk", PDK,
                 "--only-index", str(k)], stdout=subprocess.DEVNULL)
            text = with_init(out.read_text(), osdi_cmomi=True)
            out.unlink()
            units.append(("lad_%s_pt%02d" % (tag, k), text, [dutf]))
    write_request(work / "phase2", units)


# ------------------------------------------------------------------- retry
def retry(work, phase):
    rep_path = work / phase / "report.json"
    if not rep_path.exists():
        raise SystemExit("batch_grid: %s missing" % rep_path)
    rep = load(rep_path)
    bad = [u["id"] for u in rep.get("units", []) if u.get("status") != "pass"]
    rdir = work / (phase + "_retry")
    if not bad:
        print("no errored units in %s" % phase)
        if rdir.exists():
            for f in rdir.glob("request.json"):
                f.unlink()
        return
    units = []
    for uid in bad:
        text = (work / phase / "decks" / (uid + ".sp")).read_text()
        new = re.sub(r"^(\.options reltol=.*)$", r"\1 trtol=1", text, flags=re.M)
        if new == text:
            raise SystemExit("batch_grid: unit %s failed and has no .options reltol= line to relax" % uid)
        req = load(work / phase / "request.json")
        incs = re.findall(r"^\.include +(dut_\S+)", text, flags=re.M)
        units.append((uid, new, [work / phase / "decks" / i for i in incs]))
    write_request(rdir, units)
    for u in bad:
        print("[solver-retry] %s failed on the committed .options; retrying with trtol=1" % u, file=sys.stderr)


# ------------------------------------------------------------------ reduce
def reduce_all(work, corners, nominal):
    out = SUFFIX + ("_nominal" if nominal else "")
    st = load(work / "state.json")
    have, primary = st["have_cmomi"], st["primary"]
    have0, cnom, rc_rows, rval = c_values(work, nominal)
    retried = []

    def used_retry(phase, uid, tag):
        _, r = stdout_of(work, phase, uid)
        if r:
            retried.append("%s (%s)" % (tag, uid))

    (corners / ("rc_extract_%s.csv" % out)).write_text(
        "kind,instance,corner,temp_c,w,l,m,value,source\n" + "\n".join(rc_rows) + "\n")

    # window
    rows = ["corner_tag,mos_corner,res_corner,temp_c,vsup_v,fref_hz,dut_variant,twin_r_s,twin_f_s"]
    vs = variants(have)
    for mos, res, temp, vsup, fref, var in window_points(nominal, primary, vs):
        uid = "win_%s_%s_%sc_%sv_%s" % (mos, res, temp, vsup, var)
        tr, tf = twin(work, mos, res, temp, vsup, var)
        used_retry("phase1", uid, "window " + tag_of(mos, res, temp, vsup, fref, var))
        rows.append("%s,%s,%s,%s,%s,%s,%s,%s,%s" % (tag_of(mos, res, temp, vsup, fref, var), mos, res,
                                                    temp, vsup, fref, var, tr or "NA", tf or "NA"))
    (corners / ("window_%s.csv" % out)).write_text("\n".join(rows) + "\n")

    # schmitt
    rows = ["mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd"]
    smos, svsup = schmitt_points(nominal)
    _, temp_list = matrices(nominal)
    for mos in smos:
        for temp in temp_list:
            for vsup in svsup:
                uid = "sch_%s_%s_%s" % (mos, temp, vsup)
                txt, _ = stdout_of(work, "phase1", uid)
                used_retry("phase1", uid, "schmitt " + uid)
                u, d = scalar(txt, "vth_up"), scalar(txt, "vth_dn")
                if u and d:
                    h = float(u) - float(d)
                    r = "%s,%s,%.6e,%.4f" % (u, d, h, 100 * h / float(vsup))
                else:
                    r = "NA,NA,NA,NA"
                rows.append("%s,%s,%s,%s" % (mos, temp, vsup, r))
    (corners / ("schmitt_%s.csv" % out)).write_text("\n".join(rows) + "\n")

    # tstep convergence
    rows = ["mos_corner,res_corner,temp_c,dut_variant,tstep,twin_r_s"]
    tsteps, probes = tstep_probes(nominal, primary)
    for tstep in tsteps:
        for mos, res, temp, var in probes:
            uid = "ts_%s_%s_%s_%s_%s" % (tstep, mos, res, temp, var)
            txt, _ = stdout_of(work, "phase1", uid)
            used_retry("phase1", uid, "tstep " + uid)
            rows.append("%s,%s,%s,%s,%s,%s" % (mos, res, temp, var, tstep, scalar(txt, "twin_r") or "NA"))
    (corners / ("tstep_convergence_%s.csv" % out)).write_text("\n".join(rows) + "\n")

    # ladder
    g = gen_mod()
    nfr = len(g.LADDER_FRACS_SETS[LADDER_SET])
    hdr = ("corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,"
           "tau_deassert_xwin,hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,"
           "lock_max_deep_v,trec_s,vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,"
           "ladder_states_discharged_start,ladder_states_charged_start,rc_s,tref_s,rc_over_tref,"
           "n_cycles,settle_frac")
    rawhdr = ("corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,"
              "lka_max_v,lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v")
    lrows, rawf = [hdr], corners / ("ladder_raw_%s.csv" % out)
    rawf.write_text(rawhdr + "\n")
    for pt in ladder_points(nominal, primary):
        mos, res, temp, vsup, fref, var = pt
        tag = tag_of(*pt)
        p = ladder_params(work, nominal, pt, rval, cnom)
        if p is None:
            lrows.append(tag + ",NA" * 23)
            continue
        combined = ""
        for uid in ["lad_%s_base" % tag] + ["lad_%s_pt%02d" % (tag, k) for k in range(nfr)]:
            txt, _ = stdout_of(work, "phase2", uid)
            used_retry("phase2", uid, "ladder " + tag)
            combined += txt
        res_ = subprocess.run(
            [sys.executable, "-I", str(TOOLS / "gen_lock_ladder.py"), "reduce", "--tag", tag,
             "--vsup", vsup, "--fracs-set", LADDER_SET, "--twin", p["tr"], "--raw", str(rawf)],
            input=combined, capture_output=True, text=True, check=True)
        lrows.append(res_.stdout.strip() + ",%.6e,%.6e,%.3f,%d,%.4f" % (
            p["rc"], p["tref"], p["rc_over"], p["n_cycles"], p["settle"]))
    (corners / ("ladder_%s.csv" % out)).write_text("\n".join(lrows) + "\n")
    (corners / ("solver_retries_%s.txt" % out)).write_text("".join(r + "\n" for r in sorted(set(retried))))
    print("solver retries: %d unit(s) needed trtol=1" % len(set(retried)), file=sys.stderr)
    print("primary DUT variant: %s, cap_cmomi loadable on fleet: %s" % (primary, have), file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("workdir"); g.add_argument("phase", choices=["phase0", "phase1", "phase2"])
    g.add_argument("--nominal", action="store_true")
    r = sub.add_parser("retry")
    r.add_argument("workdir"); r.add_argument("phase", choices=["phase0", "phase1", "phase2"])
    d = sub.add_parser("reduce")
    d.add_argument("workdir"); d.add_argument("corners"); d.add_argument("--nominal", action="store_true")
    a = p.parse_args()
    work = pathlib.Path(a.workdir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    if a.cmd == "gen":
        {"phase0": phase0, "phase1": phase1, "phase2": phase2}[a.phase](work, a.nominal)
    elif a.cmd == "retry":
        retry(work, a.phase)
    else:
        reduce_all(work, pathlib.Path(a.corners).resolve(), a.nominal)


if __name__ == "__main__":
    main()
