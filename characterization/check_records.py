#!/usr/bin/env python3
"""Validate sim/ evidence records: numbering, format, sources.json coverage, append-only.

Offline, stdlib-only, runs no simulation and never edits sim/.

  python3 characterization/check_records.py                    # layout/format/sources checks
  python3 characterization/check_records.py --base origin/main  # + append-only vs a base ref (CI, PR)

Rules (derived from the 37 records committed when this checker was written;
none is invented, each holds for all of them):
  1. every bench dir sim/<bench>/ that has a records/ dir uses only
     RECORD-NNN-<slug>.md names, numbered from 001 with no gaps (a duplicated
     number is tolerated only where records_baseline.json grandfathers it);
     every bench dir (those with a testbench/ or records/) must have records/.
  2. each record starts with `# RECORD-NNN: <title>` where NNN matches the
     filename, has at least one `## ` section, and states its corner coverage
     (the word "corner", any case).  Spec-row / "does not bound" sections are
     common but NOT universal, so they are not required.
  3. every record is cited by characterization/sources.json, or is listed in
     records_baseline.json (historical records that predate this checker).
  4. with --base: no record present at the base ref may be deleted, renamed,
     modified or type-changed (new records may be added).
  5. with --base: records_baseline.json may only shrink -- every
     unlisted_in_sources path and duplicate_numbers (bench, number) entry must
     already be present in the base ref's copy.  A base without the file (the
     PR that introduces it) is skipped.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NAME_RE = re.compile(r"^RECORD-(\d{3})-[A-Za-z0-9][A-Za-z0-9._-]*\.md$")
H1_RE = re.compile(r"^# RECORD-(\d{3}): \S")
RECORD_PATH_RE = re.compile(r"^sim/[^/]+/records/RECORD-[^/]+\.md$")


def bench_dirs(root):
    sim = Path(root) / "sim"
    return sorted(d for d in sim.iterdir()
                  if d.is_dir() and ((d / "testbench").is_dir() or (d / "records").is_dir()))


def check_layout(root, baseline):
    errs = []
    dups = baseline.get("duplicate_numbers", {})
    for b in bench_dirs(root):
        rel = b.relative_to(root).as_posix()
        rec = b / "records"
        if not rec.is_dir():
            errs.append(f"{rel}: bench dir has no records/")
            continue
        nums = []
        for f in sorted(rec.iterdir()):
            m = NAME_RE.match(f.name)
            if not m:
                errs.append(f"{rel}/records/{f.name}: not named RECORD-NNN-<slug>.md")
            else:
                nums.append(int(m.group(1)))
        if not nums:
            errs.append(f"{rel}/records: no RECORD-*.md files")
            continue
        allowed = set(dups.get(rel, []))
        for n in sorted({n for n in nums if nums.count(n) > 1} - allowed):
            errs.append(f"{rel}/records: duplicate number {n:03d}")
        for n in sorted(allowed - {n for n in nums if nums.count(n) > 1}):
            errs.append(f"{rel}/records: baseline grandfathers duplicate {n:03d} but there is none (stale)")
        missing = sorted(set(range(1, max(nums) + 1)) - set(nums))
        if missing:
            errs.append(f"{rel}/records: numbering gap, missing "
                        + ", ".join(f"{n:03d}" for n in missing))
    return errs


def check_format(root):
    errs = []
    for f in sorted(Path(root).glob("sim/*/records/RECORD-*.md")):
        rel = f.relative_to(root).as_posix()
        m = NAME_RE.match(f.name)
        lines = f.read_text(encoding="utf-8").splitlines()
        h = H1_RE.match(lines[0]) if lines else None
        if not h:
            errs.append(f"{rel}: first line must be '# RECORD-NNN: <title>'")
        elif m and h.group(1) != m.group(1):
            errs.append(f"{rel}: title number {h.group(1)} != filename number {m.group(1)}")
        if not any(l.startswith("## ") for l in lines):
            errs.append(f"{rel}: no '## ' section heading")
        if not re.search(r"corner", "\n".join(lines), re.I):
            errs.append(f"{rel}: does not state its corner coverage (no mention of 'corner')")
    return errs


def sources_records(sources):
    """Every record path cited anywhere in a sources.json document."""
    out = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and RECORD_PATH_RE.match(o):
            out.add(o)
    walk(sources)
    return out


def check_sources(root, sources, baseline):
    errs = []
    on_disk = {f.relative_to(root).as_posix() for f in Path(root).glob("sim/*/records/RECORD-*.md")}
    cited = sources_records(sources)
    grand = set(baseline.get("unlisted_in_sources", []))
    for p in sorted(cited - on_disk):
        errs.append(f"sources.json cites {p}, which does not exist")
    for p in sorted(on_disk - cited - grand):
        errs.append(f"{p}: not listed in characterization/sources.json")
    for p in sorted(grand & cited):
        errs.append(f"{p}: listed in sources.json, remove it from records_baseline.json (stale)")
    for p in sorted(grand - on_disk):
        errs.append(f"{p}: in records_baseline.json but does not exist (stale)")
    return errs


def check_append_only(root, base):
    """Fail on any record deleted/renamed/modified/type-changed relative to `base`."""
    r = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-status", "--no-renames",
         "--diff-filter=DMT", f"{base}...HEAD", "--", "sim/"],
        capture_output=True, text=True)
    if r.returncode != 0:
        return [f"git diff against {base} failed: {r.stderr.strip()}"]
    names = {"D": "deleted", "M": "modified", "T": "type-changed"}
    errs = []
    for line in r.stdout.splitlines():
        status, _, path = line.partition("\t")
        if RECORD_PATH_RE.match(path):
            errs.append(f"{path}: {names.get(status, status)} (records are append-only; add a new record instead)")
    return errs


BASELINE_REL = "characterization/records_baseline.json"


def check_baseline_growth(root, base, baseline):
    """Fail on any records_baseline.json entry that the copy at `base` lacks."""
    v = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
                       capture_output=True, text=True)
    if v.returncode != 0:
        return [f"cannot resolve base ref {base} to check {BASELINE_REL} growth"]
    r = subprocess.run(["git", "-C", str(root), "show", f"{base}:{BASELINE_REL}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []  # base predates the baseline: this change introduces it
    try:
        old = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        return [f"{BASELINE_REL} at {base} is not valid JSON: {e}"]
    errs = []
    old_unlisted = set(old.get("unlisted_in_sources", []))
    for p in sorted(set(baseline.get("unlisted_in_sources", [])) - old_unlisted):
        errs.append(f"{BASELINE_REL}: unlisted_in_sources adds {p}, absent at {base} "
                    "(the baseline may only shrink; list new records in sources.json)")
    old_dups = {(b, int(n)) for b, ns in old.get("duplicate_numbers", {}).items() for n in ns}
    new_dups = {(b, int(n)) for b, ns in baseline.get("duplicate_numbers", {}).items() for n in ns}
    for b, n in sorted(new_dups - old_dups):
        errs.append(f"{BASELINE_REL}: duplicate_numbers adds {b} {n:03d}, absent at {base} "
                    "(the baseline may only shrink; give the new record the next free number)")
    return errs


def run(root=ROOT, base=None):
    root = Path(root)
    sources = json.loads((root / "characterization/sources.json").read_text())
    bp = root / BASELINE_REL
    baseline = json.loads(bp.read_text()) if bp.exists() else {}
    errs = check_layout(root, baseline) + check_format(root) + check_sources(root, sources, baseline)
    if base:
        errs += check_append_only(root, base)
        errs += check_baseline_growth(root, base, baseline)
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", help="git ref to enforce append-only against (e.g. origin/main)")
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args(argv)
    errs = run(a.root, a.base)
    for e in errs:
        print(f"FAIL: {e}")
    print(f"check_records: {'FAILED, %d problem(s)' % len(errs) if errs else 'ok'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
