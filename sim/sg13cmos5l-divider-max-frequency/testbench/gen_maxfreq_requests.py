#!/usr/bin/env python3
"""Render the issue-#402 divider max-frequency campaign as `klt sim` decks
requests that run against the **pinned** `ihp-sg13cmos5l` tree.

    python3 -I gen_maxfreq_requests.py --pinned-pdk DIR [--outdir DIR] PHASE
        [--units UID[,UID...]] [--brackets FILE] [--first-fail-mhz F --neighbor-mhz F]
        [--timeout-s S]

PHASE is one of:

  anchors   2 nominal units (640 MHz and 1280 MHz, N=64, mos_tt/27 C/3.3 V)
            with per-stage edge counts. These anchor the harness against the
            committed three-point bracket of
            sim/sg13cmos5l-closed-loop-real-divider RECORD-001 (exact 64 at
            640 MHz, 96 at 1.28 GHz, same byte-identical DUT). Run LOCALLY,
            one unit per request (`--units`), per host policy.
  coarse    the sweep grid: N in {64, 127} x 9 PVT corners x 16 coarse
            frequencies (640 -> 1562 MHz in 64 MHz steps plus 1562 MHz).
            Batch fleet.
  refine    interpolation points (--brackets FILE, the JSON the collector
            writes) at REFINE_STEP_MHZ inside each cell's exact/fail
            transition. Batch fleet.
  controls  one 10 ps resolution-control unit at the nominal first-failing
            frequency plus two wave-dump units (first-fail + neighbour,
            N=64 nominal) for the failing-stage isolation. Batch fleet.

Why the pinned tree, and how: the fleet image's
`/opt/pdk/ihp-sg13cmos5l` is the post-2026-10-15 `f7bca326...` install, not
`sim/README.md`'s `PDK-PIN ihp-sg13cmos5l 607e18d4...`, and a record citing
any other revision fails the item-9 gate. This generator uses the same
mechanism as `../../sg13cmos5l-vco-kvco-table/testbench/gen_rerun318.py`
(issue #318): the pinned tree's corner-library closure and OSDI objects are
copied BESIDE the decks (`decks/models/`, `decks/osdi/`) and the decks name
them by relative path, which `klt sim`'s deck-list preservation contract
stages from the submitting host -- so the pinned bytes ship with the job
and `$PDK_ROOT` is never read. The DUT itself is the frozen snapshot
(../netlist-snapshots/divider_chain.spice) staged beside the decks the same
way.

The deck, per-unit timing and the drive shape (80 ps edges, ~50 % duty)
are documented in tb_div_maxfreq.sp.tmpl's header. Outputs per phase:

  OUTDIR/decks/<uid>.sp          one rendered deck per unit (shipped byte for byte)
  OUTDIR/decks/divider_chain.spice  the DUT, beside the decks (`​.include` resolves there)
  OUTDIR/decks/models/, osdi/    the staged pinned-PDK files
  OUTDIR/<phase>.request.json    one `decks[]` request per phase
  OUTDIR/manifest.json           uid -> unit metadata (read by collect_maxfreq.py)
  OUTDIR/decks.sha256.csv        per-unit deck sha256 (attested independently by klt)
  OUTDIR/staged_pdk.sha256.csv   per-file sha256 of every staged pinned-PDK file

Submit with (host policy: grids go to the batch fleet, never local loops):

    klt sim OUTDIR/coarse.request.json --backend batch --submit-only \
        --wait-for-capacity 600 -o OUTDIR/run-coarse --format json
    # poll --job-status, then collect:
    klt sim OUTDIR/coarse.request.json --backend batch \
        --attach OUTDIR/run-coarse/batch-shards.json \
        -o OUTDIR/run-coarse --format json --report-out OUTDIR/coarse.report.json
"""
import argparse
import csv
import hashlib
import json
import pathlib
import re
import shutil

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent

PDK = "ihp-sg13cmos5l"
OSDI = ["psp103", "psp103_nqs", "mosvar"]
DUT = "divider_chain.spice"
TMPL = "tb_div_maxfreq.sp.tmpl"
RELTOL = "0.001"

# ---- campaign geometry (stated in RECORD-001; do not edit independently) -----
CORNER_TT = ("mos_tt", 27, 3.3)
# RECORD-003's / rerun233's 9-point baseline star (gen_rerun233_requests.py PVT):
# 5 MOS corners at 27 C/3.3 V, tt at -40 C and 125 C, tt at 2.97 V and 3.63 V.
# The supply axis is +/-10 % (2.97/3.63 V), NOT the 3.0/3.6 V of the supply-range
# campaign; temperature is mos_tt-only at the extremes (no 5x3x3 star: that
# would be 36 corners RECORD-003 never ran).
PVT = [
    ("mos_tt", 27, 3.3), ("mos_ss", 27, 3.3), ("mos_ff", 27, 3.3),
    ("mos_sf", 27, 3.3), ("mos_fs", 27, 3.3),
    ("mos_tt", -40, 3.3), ("mos_tt", 125, 3.3),
    ("mos_tt", 27, 2.97), ("mos_tt", 27, 3.63),
]
WORDS = {64: "000000", 127: "111111"}   # written P5..P0, corners/func.csv convention
COARSE_MHZ = list(range(640, 1537, 64)) + [1562]     # 16 points, 1536 = 640+14*64
REFINE_STEP_MHZ = 16.0
BOTTOM_MHZ, TOP_MHZ = COARSE_MHZ[0], COARSE_MHZ[-1]
N_LIST = sorted(WORDS)

# TSTOP = START_PERIODS*N/f + SETTLE_GUARD_S, scored window (collector):
# [SETTLE_PERIODS*N/f, SCORE_END_PERIODS*N/f] => SCORE_PERIODS periods.
# The first post-startup FB edge is shifted by the .ic settling glitch
# (measured 6.7 ns at the 640 MHz anchor, i.e. < 0.07*N/f). The window is
# defined in TIME: an FB period is scored iff it lies fully inside it, and
# in the committed data the first scored period is 2 or 3, never 4.
START_PERIODS = 8.0
SETTLE_GUARD_S = 20e-9
MIN_TSTOP_S = 250e-9
SETTLE_PERIODS = 2.0
SCORE_END_PERIODS = 7.5
SCORE_PERIODS = 4
EDGE_P = 80e-12          # clock edge rate: the tb_div_speed.sp.tmpl convention

TIMEOUT_S = 900


def g(x, fmt=".6e"):
    return format(x, fmt)


def num(x):
    return str(x)


def tag(mos, temp, vdd):
    return f"{mos}_{temp}c_{vdd}".replace("-", "m").replace(".", "v")


def unit_id(n, mos, temp, vdd, fmhz, suffix=""):
    return f"n{n}_{tag(mos, temp, vdd)}_f{fmhz:04d}{suffix}"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_closure(src_models: pathlib.Path, dest: pathlib.Path, seeds):
    """Copy `seeds` and, recursively, every file their `.include` directives
    name, dereferencing symlinks (the pinned tree tracks most model cards as
    symlinks into the sibling ihp-sg13g2 tree).  Returns the copied names."""
    dest.mkdir(parents=True, exist_ok=True)
    queue, done = list(seeds), []
    while queue:
        name = queue.pop(0)
        if name in done:
            continue
        src = src_models / name
        if not src.is_file():
            raise SystemExit(f"model closure: {src} is not a readable file")
        shutil.copyfile(src, dest / name)  # follows symlinks
        done.append(name)
        for target in re.findall(r"^\s*\.(?:include|inc)\s+(\S+)\s*$",
                                 src.read_text(errors="replace"), re.M):
            if "/" in target or target.startswith("$"):
                raise SystemExit(
                    f"model closure: {src} includes {target!r}; this generator "
                    "only follows same-directory relative includes")
            queue.append(target)
    return done


def timing(n, fmhz, tstep_s):
    f = fmhz * 1e6
    tstop = START_PERIODS * n / f + SETTLE_GUARD_S
    if tstop < MIN_TSTOP_S:
        tstop = MIN_TSTOP_S
    tstop = -(-tstop // tstep_s) * tstep_s          # round up to a tstep multiple
    tper = 1.0 / f
    ch = tper / 2.0 - EDGE_P                        # tb_div_speed.sp.tmpl arithmetic
    if ch <= 0:
        raise SystemExit(f"{fmhz} MHz: high time {ch}s <= 0 at {EDGE_P*1e12:.0f} ps edges")
    k_ck = int(tstop * f) + 1                       # CKIN risings within TSTOP (+ margin)
    k_fb = int(tstop * f / n) + 3                   # FB risings (+ startup/lateness margin)
    return {"tper": tper, "ch": ch, "tstop": tstop,
            "t_settle": SETTLE_PERIODS * n / f, "t_score_end": SCORE_END_PERIODS * n / f,
            "k_ck": k_ck, "k_fb": k_fb}


STAGE_NODES = ["v(ck)", "v(xdiv.ck1)", "v(xdiv.ck2)", "v(xdiv.ck3)",
               "v(xdiv.ck4)", "v(xdiv.ck5)", "v(fb)", "v(divout)"]


def meas_lines(t, stage_counts, tstep_s):
    """`.meas ... rise=k` lines: the FIRST VDD/2 crossing of every rising edge,
    per node. Meas interpolates on the solver's own points (<= tstep apart),
    not on a re-gridded wave, so the crossing times do not depend on a
    `linearize` pass."""
    lines = []
    names = (["tck"] + [f"tck{i}" for i in range(1, 6)] + ["tfb", "tdvo"]) \
        if stage_counts else ["tck", "tfb"]
    vecs = (STAGE_NODES if stage_counts else ["v(ck)", "v(fb)"])
    vdd50 = t["vdd50"]
    for name, vec in zip(names, vecs):
        kmax = t["k_fb"] if vec == "v(fb)" else t["k_ck"]
        for k in range(1, kmax + 1):
            lines.append(f".meas tran {name}_{k} when {vec}={num(vdd50)} rise={k}")
    return lines


def render_deck(meta, t):
    mos, temp, vdd = meta["mos"], meta["temp"], meta["vdd"]
    word = meta["p_word"]
    pv = {i: (vdd if word[5 - i] == "1" else 0) for i in range(6)}
    tstep = meta["tstep_ps"] * 1e-12
    # The control block executes BEFORE deck-level analyses, so a wave unit's
    # wrdata must see the transient vectors: the analysis is started by a
    # control-block `tran` command (deck-level @TRAN@ rendered empty) and
    # linearize/wrdata follow it. Non-wave units keep the deck-level .tran.
    tran = f".tran {g(tstep)} {g(t['tstop'])} 0 {g(tstep)}"
    post = ""
    savelist = "v(ck) v(fb)"
    if meta.get("waves") or meta.get("stage_counts"):
        savelist = " ".join(STAGE_NODES)
    if meta.get("waves"):
        tran = ""
        post = (f"tran {g(tstep)} {g(t['tstop'])} 0 {g(tstep)}\n"
                "linearize " + " ".join(STAGE_NODES) + "\n"
                "wrdata waves.txt " + " ".join(STAGE_NODES))
    text = (HERE / TMPL).read_text()
    # render_deck substitutes with a global replace, so a token that injects
    # MULTI-LINE deck syntax (@POST@, @MEAS@) must occur exactly once in the
    # template: a second occurrence -- e.g. mentioned in this header comment
    # -- would splice live deck syntax into a comment (the wave-deck failure
    # this guard replaced; the 2026-11-15 controls run).
    for token in ("@POST@", "@MEAS@", "@TRAN@"):
        if text.count(token) != 1:
            raise SystemExit(f"{TMPL}: {token} occurs {text.count(token)} times; "
                             "multi-line tokens must occur exactly once")
    for token, value in (
            ("@CORNER_MOS@", mos), ("@TEMP@", temp), ("@VDD@", vdd),
            ("@VDD50@", num(0.5 * vdd)), ("@TPER@", g(t["tper"])), ("@CH@", g(t["ch"])),
            ("@TSTEP@", g(tstep)), ("@TSTOP@", g(t["tstop"])), ("@RELTOL@", RELTOL),
            ("@P0@", pv[0]), ("@P1@", pv[1]), ("@P2@", pv[2]),
            ("@P3@", pv[3]), ("@P4@", pv[4]), ("@P5@", pv[5]),
            ("@SAVELIST@", savelist), ("@TRAN@", tran), ("@POST@", post),
            ("@MEAS@", "\n".join(meas_lines(t, meta.get("stage_counts"), tstep)))):
        text = text.replace(token, str(value))
    if "@" in re.sub(r"(?m)^\*.*$", "", text):
        raise SystemExit(f"{meta['unit']}: unsubstituted @TOKEN@ left in deck")
    if meta.get("waves"):
        if text.count("wrdata waves.txt") != 1 or ".tran " in \
                re.sub(r"(?m)^\*.*$", "", text):
            raise SystemExit(f"{meta['unit']}: wave deck must dump waves exactly "
                             "once and start its transient from the control block")
    elif "wrdata" in re.sub(r"(?m)^\*.*$", "", text):
        raise SystemExit(f"{meta['unit']}: non-wave deck rendered a wrdata line")
    return text


def emit(out, decks_dir, phase, metas, backend, timeout_s, max_upj=None, max_conc=None):
    decks, rows, manifest = [], [], {}
    mpath = pathlib.Path(out) / "manifest.json"
    if mpath.exists():
        manifest = json.loads(mpath.read_text())
    for meta in metas:
        t = timing(meta["n_nominal"], meta["fin_mhz"], meta["tstep_ps"] * 1e-12)
        t["vdd50"] = 0.5 * meta["vdd"]
        text = render_deck(meta, t)
        uid = meta["unit"]
        (decks_dir / f"{uid}.sp").write_text(text)
        entry = {"id": uid, "deck": f"decks/{uid}.sp", "timeout_s": timeout_s}
        if meta.get("waves"):
            entry["outputs"] = ["waves.txt"]
        decks.append(entry)
        m = dict(meta, tper_s=t["tper"], ch_s=t["ch"], tstop_s=t["tstop"],
                 t_settle_s=t["t_settle"], t_score_end_s=t["t_score_end"],
                 k_ck=t["k_ck"], k_fb=t["k_fb"],
                 reltol=RELTOL, timeout_s=timeout_s, phase=phase)
        manifest[uid] = m
        rows.append((uid, meta["n_nominal"], meta["mos"], meta["temp"], meta["vdd"],
                     meta["p_word"], meta["fin_mhz"], meta["tstep_ps"],
                     sha256(decks_dir / f"{uid}.sp")))
    request = {
        "engine": "ngspice",
        "backend": backend,
        "decks": decks,
        "options": {"timeout_s": timeout_s, "max_workers": 1},
    }
    if backend == "batch":
        # models.pdk selects the fleet IMAGE only; the model bytes are the
        # staged pinned ones, never this image's tree.
        request["models"] = {"pdk": PDK}
        batch = {"capacity_wait_s": 600}
        if max_upj:
            batch["max_units_per_job"] = max_upj
        if max_conc:
            batch["max_concurrent_jobs"] = max_conc
        request["batch"] = batch
    name = f"{phase}.request.json"
    (pathlib.Path(out) / name).write_text(json.dumps(request, indent=2) + "\n")
    mpath.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with open(pathlib.Path(out) / f"{phase}.decks.sha256.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "n_nominal", "mos_corner", "temp_c", "vdd_v",
                    "p_word", "fin_mhz", "tstep_ps", "deck_sha256"])
        w.writerows(rows)
    print(f"wrote {len(decks)} decks -> {name} (backend {backend})", flush=True)


def stage_pinned(pdk, decks_dir):
    """Copy the pinned tree's model closure and OSDI objects beside the decks.
    Returns (staged rows, done). Idempotent: skips files already staged with
    the right bytes (the phases share one decks/ directory)."""
    tech = pdk / "libs.tech" / "ngspice"
    staged = []
    models_done = copy_closure(tech / "models", decks_dir / "models",
                               ["cornerMOShv.lib"])
    for name in models_done:
        staged.append((f"models/{name}", str((tech / 'models' / name).resolve()),
                       sha256(decks_dir / "models" / name)))
    (decks_dir / "osdi").mkdir(exist_ok=True)
    for name in OSDI:
        src = tech / "osdi" / f"{name}.osdi"
        if not src.is_file():
            raise SystemExit(f"OSDI: {src} is not a readable file")
        dst = decks_dir / "osdi" / f"{name}.osdi"
        if not dst.exists() or sha256(dst) != sha256(src):
            shutil.copyfile(src, dst)  # follows symlinks
        staged.append((f"osdi/{name}.osdi", str(src.resolve()), sha256(dst)))
    dst = decks_dir / DUT
    snap = RECORD / "netlist-snapshots" / DUT
    if not dst.exists() or sha256(dst) != sha256(snap):
        shutil.copyfile(snap, dst)
    return staged


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pinned-pdk", default=None,
                    help="the ihp-sg13cmos5l tree at sim/README.md's PDK-PIN "
                         "revision 607e18d4... (required)")
    ap.add_argument("--outdir", default=str(pathlib.Path(HERE) / "maxfreq"))
    ap.add_argument("phase", choices=["anchors", "coarse", "refine", "controls"])
    ap.add_argument("--units", default=None,
                    help="emit a request with only these unit ids (comma-separated); "
                         "manifest gains the phase's other units only when they are "
                         "rendered. Used to run one anchor unit locally.")
    ap.add_argument("--brackets", default=None,
                    help="refine: brackets.json written by collect_maxfreq.py --merge")
    ap.add_argument("--first-fail-mhz", type=float, default=None,
                    help="controls: the nominal N=64 first-failing frequency (MHz)")
    ap.add_argument("--neighbor-mhz", type=float, default=None,
                    help="controls: the nominal N=64 neighbour frequency to dump "
                         "(the last exact one)")
    ap.add_argument("--s10-also-mhz", default=None,
                    help="controls: extra resolution-control points at half the "
                         "sweep timestep (comma-separated MHz), e.g. the nominal "
                         "cell's exact/fail boundary pair")
    ap.add_argument("--timeout-s", type=int, default=TIMEOUT_S)
    ap.add_argument("--max-units-per-job", type=int, default=None,
                    help="batch shard size; default floor((3600-120)/timeout-s)")
    args = ap.parse_args()

    if not args.pinned_pdk:
        raise SystemExit(
            "gen_maxfreq_requests.py: --pinned-pdk DIR is required -- an "
            "ihp-sg13cmos5l checkout at sim/README.md's PDK-PIN revision "
            "607e18d4.... There is no $PDK_ROOT fallback: the record must cite "
            "the pin, and the fleet image's tree is a newer install. See the "
            "module docstring.")
    pdk = pathlib.Path(args.pinned_pdk).expanduser().resolve()
    out = pathlib.Path(args.outdir).resolve()
    decks_dir = out / "decks"
    decks_dir.mkdir(parents=True, exist_ok=True)
    staged = stage_pinned(pdk, decks_dir)
    with open(out / "staged_pdk.sha256.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["staged_name", "source_path", "sha256"])
        w.writerows(sorted(staged))

    max_upj = args.max_units_per_job or max(1, (3600 - 120) // args.timeout_s)
    keep = set(args.units.split(",")) if args.units else None

    def filt(metas):
        if keep is None:
            return metas
        sel = [m for m in metas if m["unit"] in keep]
        if not sel:
            raise SystemExit(f"--units: none of {sorted(keep)} is a {args.phase} unit")
        return sel

    if args.phase == "anchors":
        metas = []
        for fmhz in (640, 1280):
            mos, temp, vdd = CORNER_TT
            metas.append({"unit": unit_id(64, mos, temp, vdd, fmhz, "_a"),
                          "n_nominal": 64, "p_word": WORDS[64], "mos": mos,
                          "temp": temp, "vdd": vdd, "fin_mhz": float(fmhz),
                          "tstep_ps": 20.0, "stage_counts": True})
        emit(out, decks_dir, "anchors", filt(metas), "local", args.timeout_s)
        return

    if args.phase == "coarse":
        metas = []
        for mos, temp, vdd in PVT:
            for n in N_LIST:
                for fmhz in COARSE_MHZ:
                    metas.append({"unit": unit_id(n, mos, temp, vdd, fmhz),
                                  "n_nominal": n, "p_word": WORDS[n], "mos": mos,
                                  "temp": temp, "vdd": vdd, "fin_mhz": float(fmhz),
                                  "tstep_ps": 20.0})
        emit(out, decks_dir, "coarse", filt(metas), "batch", args.timeout_s, max_upj, 6)
        return

    if args.phase == "refine":
        if not args.brackets:
            raise SystemExit("--brackets FILE is required for the refine phase")
        brackets = json.loads(pathlib.Path(args.brackets).read_text())
        metas = []
        for b in brackets["cells"]:
            lo, hi = b["last_exact_mhz"], b["first_fail_mhz"]
            if lo is None or hi is None:
                continue  # one-sided bound: nothing to interpolate
            f = lo + REFINE_STEP_MHZ
            while f < hi - 1e-9:
                metas.append({"unit": unit_id(b["n_nominal"], b["mos"], b["temp"],
                                              b["vdd"], int(round(f)), "_r"),
                              "n_nominal": b["n_nominal"], "p_word": WORDS[b["n_nominal"]],
                              "mos": b["mos"], "temp": b["temp"], "vdd": b["vdd"],
                              "fin_mhz": round(f, 3), "tstep_ps": 20.0})
                f += REFINE_STEP_MHZ
        emit(out, decks_dir, "refine", filt(metas), "batch", args.timeout_s, max_upj, 4)
        return

    # controls
    if not args.first_fail_mhz or not args.neighbor_mhz:
        raise SystemExit("controls needs --first-fail-mhz and --neighbor-mhz")
    mos, temp, vdd = CORNER_TT
    metas = [
        {"unit": unit_id(64, mos, temp, vdd, int(round(args.first_fail_mhz)), "_s10"),
         "n_nominal": 64, "p_word": WORDS[64], "mos": mos, "temp": temp, "vdd": vdd,
         "fin_mhz": args.first_fail_mhz, "tstep_ps": 10.0},
        {"unit": unit_id(64, mos, temp, vdd, int(round(args.first_fail_mhz)), "_w"),
         "n_nominal": 64, "p_word": WORDS[64], "mos": mos, "temp": temp, "vdd": vdd,
         "fin_mhz": args.first_fail_mhz, "tstep_ps": 20.0, "waves": True,
         "stage_counts": True},
        {"unit": unit_id(64, mos, temp, vdd, int(round(args.neighbor_mhz)), "_w"),
         "n_nominal": 64, "p_word": WORDS[64], "mos": mos, "temp": temp, "vdd": vdd,
         "fin_mhz": args.neighbor_mhz, "tstep_ps": 20.0, "waves": True,
         "stage_counts": True},
    ]
    # Optional extra resolution-control points: e.g. the nominal cell's
    # exact/fail boundary pair re-run at half the sweep timestep, to check the
    # exact/fail BOUND (not only the failing point's counts) against the
    # sampling step.
    if args.s10_also_mhz:
        for fmhz in (float(x) for x in args.s10_also_mhz.split(",")):
            metas.append({"unit": unit_id(64, mos, temp, vdd, int(round(fmhz)), "_s10"),
                          "n_nominal": 64, "p_word": WORDS[64], "mos": mos,
                          "temp": temp, "vdd": vdd, "fin_mhz": fmhz,
                          "tstep_ps": 10.0})
    emit(out, decks_dir, "controls", filt(metas), "batch", args.timeout_s, max_upj, 4)


main()
