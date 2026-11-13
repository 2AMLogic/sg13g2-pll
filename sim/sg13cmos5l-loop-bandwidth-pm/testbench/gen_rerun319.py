#!/usr/bin/env python3
"""Render the issue-#319 rerun of RECORD-001 / -002 / -002-r1 as `klt sim` batch
`decks[]` requests, and collect the returned units back into new CSVs.

Why this exists
---------------
Each of the three originals was produced by `testbench/run.sh`, which loops
`ngspice -b` locally over a few hundred decks.  Dispatch workers forbid
hand-launched local ngspice grids, so the grid has to be expressed as a
`klt sim --backend batch` request.  Re-expressing the campaign as a *corner*
request would mint a different artifact than the originals were minted by, so
this uses the deck-transport (`decks[]`) path instead: klt ships each deck
byte-for-byte and runs `ngspice -b` on it, exactly as `run.sh` did.

Fidelity
--------
The matrix, the `crossover()` interpolation and every CSV writer are the
*historical* ones: this script extracts each original's own `run.sh` from git
at that original's producing commit, lifts the embedded Python verbatim, and
replaces **only** the body of `run_ac()` -- the function that shells out to
ngspice.  In `render` mode `run_ac` writes the deck; in `collect` mode it reads
that deck's returned `ac.dat`.  Nothing else about the historical program is
touched, and the historical *input* CSVs (Kvco / R-C / Icp tables) are read
from the same historical tree, so each rerun measures that original's own
historical DUT rather than today's design.

Deck deltas vs. what `run.sh` ran (the only ones, both forced by the runner):
  * `@PDK_ROOT@/@PDK@` (or b37918d's literal `$PDK_ROOT/$PDK`) resolves to
    `$PDK_ROOT/ihp-sg13cmos5l`, which the runner expands into its own PDK --
    the spelling klt documents for naming the runner's PDK from a deck.
  * `run.sh` loaded the three OSDI objects from a `.spiceinit` in its scratch
    dir; a shipped deck has no `.spiceinit`, so the same three objects are
    loaded with `pre_osdi` lines at the top of `.control` (ngspice hoists
    them).  Same objects, same order.

Usage
-----
  python3 -I gen_rerun319.py render                 # decks + request JSONs
  python3 -I gen_rerun319.py collect <outdir> ...   # one outdir per arm ('-' skips)
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC_DIR = HERE.parent                      # sim/sg13cmos5l-loop-bandwidth-pm
REPO = REC_DIR.parent.parent               # repo root
OUT = HERE / "rerun319"
BENCH = "sim/sg13cmos5l-loop-bandwidth-pm"
PDK = "ihp-sg13cmos5l"
TIMEOUT_S = 900
OSDI = [f"$PDK_ROOT/{PDK}/libs.tech/ngspice/osdi/{n}.osdi"
        for n in ("cap_cmomi", "cap_cmomf", "r3_cmc")]

# One entry per original record being superseded: the producing commit, the
# netlist snapshots `run.sh` stages into its scratch dir, and the CSV/text
# outputs the historical program writes (historical name -> rerun name).
SNAPSHOTS = {
    "b37918d": {
        "commit": "b37918d",
        "record": "RECORD-001-loop-bandwidth-phase-margin.md",
        "stage": {"loop_filter.spice": "loop_filter_snap.spice"},
        "outputs": {"results.csv": "results_rerun319.csv",
                    "mom_band.csv": "mom_band_rerun319.csv",
                    "proposal.csv": "proposal_rerun319.csv",
                    "crosscheck.txt": "crosscheck_rerun319.txt"},
    },
    "f54b9ef": {
        "commit": "f54b9ef",
        "record": "RECORD-002-icp-input-refresh.md",
        "stage": {"loop_filter.spice": "loop_filter_snap.spice"},
        "outputs": {"results.csv": "results_icp_refresh_rerun319.csv",
                    "mom_band.csv": "mom_band_icp_refresh_rerun319.csv",
                    "proposal.csv": "proposal_icp_refresh_rerun319.csv",
                    "crosscheck.txt": "crosscheck_icp_refresh_rerun319.txt"},
    },
    # Part D, re-driven against ffec56a's own tree: the faithful "rerun at the
    # original's commit".  Note that ffec56a's COMMITTED results_resized.csv
    # carries the PRE-#72 Icp values (fast 1.005123e-05 / slow 1.004412e-05 /
    # typ 1.004607e-05 at the 10u code) -- the b37918d table, not the refreshed
    # one already present in its own tree.  So the original Part D ran before
    # the #72 input refresh merged and was never regenerated against it.  The
    # `_origicp` control arm below re-runs this same grid on the Icp table the
    # original actually consumed, which separates that input refresh from
    # PDK/tool drift.
    "ffec56a": {
        "commit": "ffec56a",
        "record": "RECORD-002-r1-resize-full-fref-range.md",
        "stage": {"loop_filter.spice": "loop_filter_snap.spice",
                  "loop_filter_resized.spice": "loop_filter_snap_resized.spice"},
        "outputs": {"results_resized.csv": "results_resized_rerun319.csv",
                    "crosscheck_resized.txt": "crosscheck_resized_rerun319.txt"},
    },
    "ffec56a_origicp": {
        "commit": "ffec56a",
        "icp_from": "b37918d",
        "record": "RECORD-002-r1-resize-full-fref-range.md (control: the Icp table the original consumed)",
        "stage": {"loop_filter.spice": "loop_filter_snap.spice",
                  "loop_filter_resized.spice": "loop_filter_snap_resized.spice"},
        "outputs": {"results_resized.csv": "results_resized_origicp_rerun319.csv",
                    "crosscheck_resized.txt": "crosscheck_resized_origicp_rerun319.txt"},
    },
}

# `run_ac`'s replacement body.  Everything else in the historical program --
# the matrix, crossover(), the CSV writers -- is executed verbatim.
RUN_AC = '''def run_ac(tmpl, subs, tag):
    src = open(f"{HERE}/{tmpl}").read()
    for k, v in subs.items():
        src = src.replace(k, str(v))
    return _KLT_RUN_AC(tag, tmpl, src)
'''
RUN_AC_RE = re.compile(r"^def run_ac\(tmpl, subs, tag\):\n.*?^    return rows\n",
                       re.M | re.S)


def historical_tree(commit):
    """Extract the repo at `commit` into a temp dir (caller removes it)."""
    d = Path(tempfile.mkdtemp(prefix=f"rerun319-{commit}-"))
    archive = subprocess.run(["git", "-C", str(REPO), "archive", commit],
                             stdout=subprocess.PIPE, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(d)], input=archive, check=True)
    return d


def historical_python(tree):
    """The Python program embedded in that commit's own run.sh, with run_ac swapped."""
    sh = (tree / BENCH / "testbench" / "run.sh").read_text()
    body = sh.split("python3 - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    body, n = RUN_AC_RE.subn(RUN_AC, body)
    if n != 1:
        raise SystemExit("could not substitute run_ac (matched %d times)" % n)
    return body


def to_deck(src):
    """The two runner-forced edits, and nothing else."""
    src = src.replace("$PDK_ROOT/$PDK/", f"$PDK_ROOT/{PDK}/")
    src = src.replace("@PDK_ROOT@/@PDK@", f"$PDK_ROOT/{PDK}")
    pre = "".join(f"pre_osdi {p}\n" for p in OSDI)
    src, n = re.subn(r"^\.control\n", ".control\n" + pre, src, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("deck has no .control block to hoist pre_osdi into")
    leftover = [l for l in src.splitlines() if "@" in l and not l.startswith("*")]
    if leftover:
        raise SystemExit("unsubstituted token(s): %r" % leftover[:3])
    return src


def drive(label, mode, outdir=None):
    """Execute the historical program with run_ac in `render` or `collect` mode."""
    spec = SNAPSHOTS[label]
    commit = spec["commit"]
    tree = historical_tree(commit)
    try:
        if spec.get("icp_from"):
            icp = "sim/sg13cmos5l-cp-icp-trim/corners/results.csv"
            (tree / icp).write_text(subprocess.check_output(
                ["git", "-C", str(REPO), "show", f"{spec['icp_from']}:{icp}"], text=True))
        hbench = tree / BENCH
        work = Path(tempfile.mkdtemp(prefix=f"rerun319-work-{commit}-"))
        # The historical program writes its CSVs under {REC}/corners.  Point it
        # at scratch so no committed original is ever opened for writing.
        (work / "rec" / "corners").mkdir(parents=True)
        decks = OUT / label / "decks"
        manifest = {}

        if mode == "render":
            decks.mkdir(parents=True, exist_ok=True)
            for f in decks.glob("*"):
                f.unlink()
            for src_name, dst_name in spec["stage"].items():
                shutil.copyfile(hbench / "netlist-snapshots" / src_name, decks / dst_name)

        def run_ac(tag, tmpl, src):
            if mode == "render":
                (decks / f"{tag}.sp").write_text(to_deck(src))
                manifest[tag] = {"template": tmpl, "commit": commit, "arm": label}
                # A synthetic magnitude/phase pair so the historical writers
                # run to completion; render-mode CSVs are scratch, not evidence.
                return [(10.0, 2.0, -90.0), (1e9, 0.5, -90.0)]
            dat = Path(outdir) / tag / "ac.dat"
            if not dat.exists():
                raise SystemExit(f"missing {dat} -- unit {tag} produced no ac.dat")
            rows = []
            for line in dat.read_text().splitlines():
                p = line.split()
                if len(p) >= 4:
                    try:
                        rows.append((float(p[0]), float(p[1]), float(p[3])))
                    except ValueError:
                        pass
            if not rows:
                raise SystemExit(f"empty ac.dat for unit {tag}")
            return rows

        env = {"WORK": str(work), "HERE": str(hbench / "testbench"),
               "RECORD_DIR": str(work / "rec"), "SIM_ROOT": str(tree / "sim"),
               "PDK_ROOT": os.environ.get("PDK_ROOT", "/nonexistent"), "PDK": PDK}
        os.environ.update(env)
        g = {"__name__": "__main__", "_KLT_RUN_AC": run_ac}
        exec(compile(historical_python(tree), f"run.sh:{commit}", "exec"), g)

        if mode == "render":
            (OUT / label).mkdir(parents=True, exist_ok=True)
            (OUT / label / "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            return sorted(manifest)
        produced = {}
        for hist_name, new_name in spec["outputs"].items():
            hist_path = tree / BENCH / "corners" / hist_name
            produced[new_name] = ((work / "rec" / "corners" / hist_name).read_text(),
                                  hist_path.read_text() if hist_path.exists() else None)
        return produced
    finally:
        shutil.rmtree(tree, ignore_errors=True)


def compare(new_text, old_text, label):
    """Per-column max relative difference and verdict flips, rerun vs the original."""
    new = list(csv.DictReader(new_text.splitlines()))
    old = list(csv.DictReader(old_text.splitlines()))
    if len(new) != len(old):
        print(f"  {label}: ROW COUNT {len(new)} vs {len(old)} -- not comparable")
        return
    num, verdict = {}, {}
    for n, o in zip(new, old):
        for col, nv in n.items():
            ov = o[col]
            if col.startswith("meets_"):
                verdict[col] = verdict.get(col, 0) + (nv != ov)
                continue
            try:
                a, b = float(nv), float(ov)
            except ValueError:
                continue
            if b:
                num[col] = max(num.get(col, 0.0), abs(a / b - 1))
    print(f"  {label}: {len(new)} rows; " + ", ".join(
        f"{c} max rel diff {d:.3e}" for c, d in sorted(num.items()) if d) or "identical")
    for c, k in sorted(verdict.items()):
        print(f"    {c}: {k} flip(s) of {len(new)}")


def request(label, ids):
    return {
        "engine": "ngspice",
        "backend": "batch",
        "models": {"pdk": PDK},
        "decks": [{"id": i,
                   "deck": f"rerun319/{label}/decks/{i}.sp",
                   "outputs": ["ac.dat"],
                   "timeout_s": TIMEOUT_S} for i in ids],
        "options": {"timeout_s": TIMEOUT_S},
        "batch": {"capacity_wait_s": 600},
    }


def main(argv):
    if not argv or argv[0] not in ("render", "collect"):
        raise SystemExit(__doc__)
    if argv[0] == "render":
        probe = None
        for label in SNAPSHOTS:
            ids = drive(label, "render")
            path = HERE / f"rerun319_{label}.request.json"
            path.write_text(json.dumps(request(label, ids), indent=2) + "\n")
            print(f"{label}: {len(ids)} decks -> {path.name}")
            if probe is None:
                # The RECORD-001 cross-check point: typ / band 11 / top
                # interval / f_ref 25 MHz / 10 uA.  RECORD-001 publishes its
                # historical value (f_c 954.6 kHz, PM 4.275 deg), so this one
                # unit is a real check on the whole pipeline before the grid.
                probe = (label, "A_typ_11_top_25_10u")
                assert probe[1] in ids, probe
        c, uid = probe
        (HERE / "probe319.request.json").write_text(
            json.dumps(request(c, [uid]), indent=2) + "\n")
        print(f"probe: {c}/{uid} -> probe319.request.json")
        return
    outdirs = argv[1:]
    if len(outdirs) != len(SNAPSHOTS):
        raise SystemExit(f"collect needs {len(SNAPSHOTS)} outdirs, one per arm in "
                         f"order: {list(SNAPSHOTS)} (use '-' to skip an arm)")
    for label, outdir in zip(SNAPSHOTS, outdirs):
        if outdir == "-":
            print(f"=== {label}: skipped")
            continue
        print(f"=== {label} ({SNAPSHOTS[label]['record']})")
        for new_name, (text, hist) in drive(label, "collect", outdir).items():
            (REC_DIR / "corners" / new_name).write_text(text)
            print(f"  wrote corners/{new_name}")
            if hist is not None and new_name.endswith(".csv"):
                compare(text, hist, new_name)
            elif hist is not None:
                print(f"  --- original {new_name} ---")
                for ln in hist.splitlines()[-5:]:
                    print("    | " + ln)
                print(f"  --- rerun {new_name} ---")
                for ln in text.splitlines()[-5:]:
                    print("    | " + ln)


main(sys.argv[1:])
