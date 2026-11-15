#!/usr/bin/env python3
"""Collect a `klt sim` decks run of sim/sg13cmos5l-divider-max-frequency
(issue #402) into ../corners/ evidence.

    python3 -I collect_maxfreq.py OUTDIR REPORT --phase anchors|coarse|refine|controls \
        [--outdircorners ../corners]

For every unit of `phase` in REPORT (a `mode: "decks"` report):

  * parses the unit's stdout.bin: `.meas tran <name> = <value>` lines give the
    interpolated VDD/2 crossing time of every rising edge of CKIN (`tck_k`),
    FB (`tfb_k`) and -- on stage-count units -- ck1..ck5 (`tckN_k`) and DIVOUT
    (`tdvo_k`); `.meas ... failed!` lines record missing edges as null;
  * buckets the CKIN edges per FB period (interval [f[i], f[i+1]), the same
    linear-interpolated 50 % crossings tb_div_speed's extractor used) and
    scores the periods that lie fully inside the time window
    [t_settle, t_score_end] -- the window decides, not a period index (in
    the committed data the first scored period is FB period 2 or 3, never 4);
  * writes ../corners/edges_<uid>.json (per-unit artifact: parameters, edge
    times, per-period counts, verdict) and appends a row to
    ../corners/maxfreq-<phase>.csv;
  * wave units' declared `waves.txt` output is gzipped to
    ../corners/waves-<uid>.csv.gz (the AC-3 waveform evidence).

Verdicts: exact (>= SCORE_PERIODS scored periods, all == N), exact-partial
(all == N but fewer periods scored -- see README in the record), miscount
(any scored period != N), fb-stopped (< 2 FB edges in the window),
engine-error (unit status not "pass").

    python3 -I collect_maxfreq.py --merge OUTDIR [--outdircorners ../corners]

merges the coarse+refine phase CSVs into ../corners/maxfreq.csv,
../corners/max-freq-by-corner.csv (per-corner exact/fail bounds) and
OUTDIR/brackets.json (the refine-phase input). Anchor, wave and
resolution-control units are harness evidence and are excluded from the
bounds (their frequencies duplicate grid points).

The per-period LIST is always reported, never a single ratio: an adjacent
N-1, N+1 pair summing to 2N is the signature of a sampling-boundary artifact,
a real failure shows a sustained wrong count (as 1.28 GHz's flat 96,96,96,96,96
does).
"""
import csv
import gzip
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent
SCORE_PERIODS = 4
BOTTOM_MHZ, TOP_MHZ = 640.0, 1562.0
STAGE_NODES = ["ck", "ck1", "ck2", "ck3", "ck4", "ck5", "fb", "divout"]
MEAS_NAME = {"tck": "ck", "tck1": "ck1", "tck2": "ck2", "tck3": "ck3",
             "tck4": "ck4", "tck5": "ck5", "tfb": "fb", "tdvo": "divout"}
# Only .meas output lines: the generator's names are t<node>_<k> with
# node in ck/ck1..ck5/fb/divout. Matching any `name = value` stdout line
# would silently absorb future ngspice lines of the same shape.
OK_RE = re.compile(r"^((?:tck[1-5]?|tfb|tdvo)_\d+)\s*=\s*([-+0-9.eE]+)\s*$", re.M)
FAIL_RE = re.compile(r"^\s*\.meas tran (\S+).*failed!", re.M)


def parse_stdout(text):
    ok = {m.group(1): float(m.group(2)) for m in OK_RE.finditer(text)}
    bad = set(FAIL_RE.findall(text))
    return ok, bad


def edges(meas, prefix, kmax):
    """Edge times for one node: [t_1..t_kmax]; a failed meas is a missing edge."""
    return [meas.get(f"{prefix}_{k}") for k in range(1, kmax + 1)]


def bucket(clk, fb, n, t_settle, t_score_end):
    """Per-FB-period CKIN edge counts + the scored subset (window)."""
    fbv = [t for t in fb if t is not None]
    periods = []
    for i in range(len(fbv) - 1):
        c = sum(1 for x in clk if x is not None and fbv[i] <= x < fbv[i + 1])
        periods.append({"j": i + 1, "t0": fbv[i], "t1": fbv[i + 1], "count": c})
    for p in periods:
        p["scored"] = (p["t0"] >= t_settle - 1e-12) and (p["t1"] <= t_score_end + 1e-12)
    scored = [p for p in periods if p["scored"]]
    return periods, scored


def verdict_of(unit_status, scored, n):
    if unit_status != "pass":
        return "engine-error"
    if not scored:
        return "fb-stopped"
    counts = [p["count"] for p in scored]
    if all(c == n for c in counts):
        return "exact" if len(scored) >= SCORE_PERIODS else "exact-partial"
    return "miscount"


def stage_counts(meas, bad, scored, nodes):
    """Per-stage edge counts inside each scored FB period."""
    out = {}
    for prefix, node in MEAS_NAME.items():
        if node not in nodes:
            continue
        kmax = max((int(m.group(1)) for m in
                    (re.match(rf"^{prefix}_(\d+)$", k) for k in list(meas) + list(bad))
                    if m), default=0)
        if not kmax:
            continue
        times = [meas.get(f"{prefix}_{k}") for k in range(1, kmax + 1)]
        out[node] = [sum(1 for x in times if x is not None and p["t0"] <= x < p["t1"])
                     for p in scored]
    return out


def collect_unit(res, uid, m, waves_txt=None):
    ud = res / uid
    so = (ud / "stdout.bin").read_bytes().decode(errors="replace") if (ud / "stdout.bin").exists() else ""
    ok, bad = parse_stdout(so)
    rep_unit = next((u for u in REPORT_UNITS if u["id"] == uid), {})
    clk = edges(ok, "tck", m["k_ck"])
    fb = edges(ok, "tfb", m["k_fb"])
    periods, scored = bucket(clk, fb, m["n_nominal"], m["t_settle_s"], m["t_score_end_s"])
    v = verdict_of(rep_unit.get("status", "pass"), scored, m["n_nominal"])
    nodes = STAGE_NODES if m.get("stage_counts") else ["ck", "fb"]
    art = {
        "unit": uid, "phase": m["phase"],
        "mos_corner": m["mos"], "temp_c": m["temp"], "vdd_v": m["vdd"],
        "p_word": m["p_word"], "n_nominal": m["n_nominal"], "fin_mhz": m["fin_mhz"],
        "fin_hz": m["fin_mhz"] * 1e6, "tstep_ps": m["tstep_ps"], "tstop_s": m["tstop_s"],
        "t_settle_s": m["t_settle_s"], "t_score_end_s": m["t_score_end_s"],
        "reltol": m["reltol"], "threshold_v": 0.5 * m["vdd"],
        "unit_status": rep_unit.get("status"), "exit_code": rep_unit.get("exit_code"),
        "duration_s": rep_unit.get("duration_s"), "engine_version": rep_unit.get("engine_version"),
        "deck_sha256": rep_unit.get("deck_sha256"),
        "n_clk_edges_found": sum(1 for x in clk if x is not None),
        "n_fb_edges_found": sum(1 for x in fb if x is not None),
        "clk_edge_times_s": [x for x in clk if x is not None],
        "fb_edge_times_s": [x for x in fb if x is not None],
        "periods": periods, "scored_periods": scored,
        "counts": [p["count"] for p in scored],
        "first_bad_period": next((p["j"] for p in scored if p["count"] != m["n_nominal"]), None),
        "verdict": v,
    }
    if m.get("stage_counts"):
        art["stage_counts"] = stage_counts(ok, bad, scored, nodes)
    if waves_txt is not None:
        art["waves_committed"] = f"corners/waves-{uid}.csv.gz"
    return art


def write_waves_gz(res, uid, corners):
    wf = res / uid / "waves.txt"
    if not wf.exists():
        return False
    rows = [l.split() for l in wf.read_text().splitlines() if l.strip()]
    if not rows:
        return False
    ncols = len(rows[0])
    if ncols % 2:
        raise SystemExit(f"{uid}: waves.txt has {ncols} columns; expected 2 per vector")
    nvec = ncols // 2
    if nvec != len(STAGE_NODES):
        raise SystemExit(f"{uid}: waves.txt has {nvec} vectors; expected {len(STAGE_NODES)}")
    with gzip.open(corners / f"waves-{uid}.csv.gz", "wt", compresslevel=9) as f:
        f.write("t_s," + ",".join(f"{n}_v" for n in STAGE_NODES) + "\n")
        for r in rows:
            f.write(",".join([r[0]] + [r[2 * i + 1] for i in range(nvec)]) + "\n")
    return True


CSV_COLS = ("phase,unit,mos_corner,temp_c,vdd_v,p_word,n_nominal,fin_mhz,tstep_ps,"
            "tstop_s,t_settle_s,t_score_end_s,reltol,verdict,scored_periods,counts,"
            "first_bad_period,unit_status,duration_s,engine_version,deck_sha256")


def g(x):
    """Compact numeric CSV cell: integral floats as ints, else repr."""
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)


def csv_row(art):
    return ",".join(str(x) for x in (
        art["phase"], art["unit"], art["mos_corner"], art["temp_c"], art["vdd_v"],
        art["p_word"], art["n_nominal"], art["fin_mhz"], art["tstep_ps"], art["tstop_s"],
        art["t_settle_s"], art["t_score_end_s"], art["reltol"], art["verdict"],
        len(art["scored_periods"]), " ".join(str(c) for c in art["counts"]),
        art["first_bad_period"] if art["first_bad_period"] is not None else "NA",
        art["unit_status"], art["duration_s"] if art["duration_s"] is not None else "NA",
        art["engine_version"], art["deck_sha256"]))


def do_collect(res, report, phase, corners):
    man = json.loads((HERE / "maxfreq" / "manifest.json").read_text())
    units = [u for u in report["units"] if man[u["id"]]["phase"] == phase]
    out = corners / f"maxfreq-{phase}.csv"
    rows = [CSV_COLS]
    # Idempotent across partial reports: a later run with a subset of the
    # phase's units must not clobber the rows already collected for the rest.
    done = {u["id"] for u in units}
    if out.exists():
        for r in csv.DictReader(out.open()):
            if r["unit"] not in done:
                rows.append(",".join(r[c] for c in CSV_COLS.split(",")))
    for u in units:
        uid = u["id"]
        m = man[uid]
        waves = True if m.get("waves") else None
        if m.get("waves"):
            waves = write_waves_gz(res, uid, corners)
            if not waves:
                print(f"WARNING: {uid}: waves.txt not collected", file=sys.stderr)
        art = collect_unit(res, uid, m, waves)
        (corners / f"edges_{uid}.json").write_text(json.dumps(art, indent=1) + "\n")
        rows.append(csv_row(art))
    out.write_text("\n".join(rows) + "\n")
    print(f"collected {len(units)} units -> {out}", file=sys.stderr)


def do_merge(res, corners):
    man = json.loads((HERE / "maxfreq" / "manifest.json").read_text())
    cells = {}
    allrows = []
    for phase in ("coarse", "refine"):
        f = corners / f"maxfreq-{phase}.csv"
        if not f.exists():
            continue
        for r in csv.DictReader(f.open()):
            allrows.append(r)
            key = (r["mos_corner"], float(r["temp_c"]), float(r["vdd_v"]),
                   int(r["n_nominal"]))
            cell = cells.setdefault(key, {"mos": r["mos_corner"], "temp": float(r["temp_c"]),
                                          "vdd": float(r["vdd_v"]),
                                          "n_nominal": int(r["n_nominal"]),
                                          "p_word": r["p_word"],
                                          "last_exact_mhz": None, "first_fail_mhz": None,
                                          "verdicts": {}})
            cell["verdicts"][float(r["fin_mhz"])] = r["verdict"]
    hdr = ("mos_corner,temp_c,vdd_v,n_nominal,p_word,last_exact_fin_mhz,"
           "first_fail_fin_mhz,resolution_mhz,bound")
    lines = [hdr]
    brackets = {"cells": []}
    for key in sorted(cells, key=lambda k: (k[0], float(k[1]), float(k[2]), int(k[3]))):
        c = cells[key]
        exact = [f for f, v in c["verdicts"].items() if v in ("exact", "exact-partial")]
        fail = [f for f, v in c["verdicts"].items() if v in ("miscount", "fb-stopped")]
        le = max(exact) if exact else None
        ff = min(fail) if fail else None
        if le is not None and ff is not None and le > ff:
            raise SystemExit(f"{key}: exact at {le} MHz above a fail at {ff} MHz "
                             "-- inconsistent bounds; investigate before merging")
        lo = le if le is not None else ff
        hi = ff if ff is not None else le
        res_mhz = (ff - le) if (le is not None and ff is not None) else 64.0
        if le is None:
            bound = (f"miscounts at every swept frequency (no exact point in "
                     f"{g(BOTTOM_MHZ)}-{g(TOP_MHZ)} MHz)")
        elif ff is None:
            bound = f"exact at every swept frequency (up to {g(le)} MHz)"
        else:
            bound = f"exact at {g(le)} MHz, miscounts at {g(ff)} MHz"
        lines.append(",".join([
            c["mos"], g(c["temp"]), g(c["vdd"]), str(c["n_nominal"]), c["p_word"],
            g(le) if le is not None else "NA", g(ff) if ff is not None else "NA",
            g(res_mhz), bound]))
        brackets["cells"].append({"mos": c["mos"], "temp": c["temp"], "vdd": c["vdd"],
                                  "n_nominal": c["n_nominal"], "p_word": c["p_word"],
                                  "last_exact_mhz": le, "first_fail_mhz": ff})
    (corners / "maxfreq.csv").write_text("\n".join(allrows and
                                                   [",".join(allrows[0].keys())] +
                                                   [",".join(r.values()) for r in allrows]) + "\n")
    (corners / "max-freq-by-corner.csv").write_text("\n".join(lines) + "\n")
    (res / "brackets.json").write_text(json.dumps(brackets, indent=1) + "\n")
    print(f"merged {len(allrows)} rows -> corners/maxfreq.csv, "
          f"corners/max-freq-by-corner.csv, {res / 'brackets.json'}", file=sys.stderr)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--merge":
        rest = argv[1:]
        res = pathlib.Path(rest[0]) if rest else pathlib.Path(HERE) / "maxfreq"
        corners = RECORD / "corners"
        if "--outdircorners" in rest:
            corners = pathlib.Path(rest[rest.index("--outdircorners") + 1])
        return do_merge(res.resolve(), corners.resolve())
    res = pathlib.Path(argv[0]).resolve()
    report = json.loads(pathlib.Path(argv[1]).read_text())
    phase = argv[argv.index("--phase") + 1]
    corners = RECORD / "corners"
    if "--outdircorners" in argv:
        corners = pathlib.Path(argv[argv.index("--outdircorners") + 1])
    if report.get("mode") != "decks":
        raise SystemExit(f"{argv[1]}: not a deck report (mode={report.get('mode')!r})")
    globals()["REPORT_UNITS"] = report["units"]
    do_collect(res, report, phase, corners)


if __name__ == "__main__":
    main()
