#!/usr/bin/env python3
"""Spec citation gate: structure and resolution of spec/target-spec.md's row table.

Checks ONLY that the citations in the `## Row table` section resolve; it never
reads or compares bounds, binding corners, or Status against measured
compliance (row 13 is O with a failing candidate by design).

  * the table has the 9-column header; every data row has 9 cells; row labels
    are unique and are exactly 0..18 with the merged 4/5 and 6/6a;
  * Status is one of M, P, N, O;
  * "Measured by": each hyphenated backticked bench slug names an existing
    sim/<bench>/ directory; each backticked `records/<file>` attaches to the
    nearest preceding bench in the cell and sim/<bench>/records/<file> exists;
    an M row cites at least one record;
  * an O row's bound cell contains `Gate:` text or an R-n reference (row 13 has
    only R-8);
  * every `R-n` in the table resolves to a `**R-n.` heading in `## Needs a ruling`;
  * every `DR-NNN` in the table matches at least one
    spec/decision-records/DR-NNN-*.md (numbers are not unique); a backticked
    slug right after it (e.g. DR-006 `loop-filter-r1-resize`) must match that
    exact file;
  * backticked `sim/<bench>/records/<file>` paths anywhere in the spec exist.

Stdlib only. Exit 0 = pass, 1 = fail.
Usage: check_spec_citations.py [--root DIR] [--spec P]
"""
import argparse
import re
import sys
from pathlib import Path

LABELS = [str(i) for i in range(19)]
LABELS = [l for l in LABELS if l not in ("4", "5", "6")]
LABELS += ["4/5", "6/6a"]
STATUSES = {"M", "P", "N", "O"}
NCOLS = 9
BENCH = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")
DR = re.compile(r"\bDR-(\d{3})(?:\s+Decision\s+\d+)?(?:\s+`([a-z0-9-]+)`)?")
RN = re.compile(r"\bR-(\d+)\b")


def section(text, name):
    m = re.search(r"^## " + re.escape(name) + r"\s*$", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[:n.start()] if n else rest


def table_rows(sec):
    lines = [l for l in sec.splitlines() if l.startswith("|")]
    return [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]


def check(root, spec):
    root, errs = Path(root), []
    text = Path(spec).read_text()
    sec = section(text, "Row table")
    if sec is None:
        return ["spec: no '## Row table' section"]
    rows = table_rows(sec)
    if len(rows) < 2 or len(rows[0]) != NCOLS or not rows[0][0].startswith("Row"):
        return [f"table: header is not the {NCOLS}-column Row table header"]
    data = rows[2:]  # skip header and |---| separator
    ruling = section(text, "Needs a ruling") or ""
    rids = set(re.findall(r"^\*\*R-(\d+)\.", ruling, re.M))
    drdir = root / "spec" / "decision-records"
    drfiles = sorted(p.name for p in drdir.glob("DR-*.md")) if drdir.is_dir() else []

    seen = []
    for cells in data:
        label = cells[0]
        if len(cells) != NCOLS:
            errs.append(f"row {label}: has {len(cells)} cells, expected {NCOLS}")
            continue
        seen.append(label)
        status, measured = cells[2], cells[7]
        row = " | ".join(cells)
        if status not in STATUSES:
            errs.append(f"row {label}: Status {status!r} is not one of M, P, N, O")
        nrec = 0
        bench = None
        for tok in re.findall(r"`([^`]+)`", measured):
            if tok.startswith("records/"):
                if bench is None:
                    errs.append(f"row {label}: record {tok} cited with no preceding bench")
                    continue
                nrec += 1
                if not (root / "sim" / bench / tok).is_file():
                    errs.append(f"row {label}: missing record sim/{bench}/{tok}")
            elif BENCH.match(tok):
                bench = tok
                if not (root / "sim" / bench).is_dir():
                    errs.append(f"row {label}: missing bench directory sim/{bench}")
        if status == "M" and nrec == 0:
            errs.append(f"row {label}: Status M cites no record in 'Measured by'")
        if status == "O" and "Gate:" not in cells[5] and not RN.search(cells[5]):
            errs.append(f"row {label}: Status O has neither 'Gate:' text nor an R-n ruling reference")
        for n in sorted(set(RN.findall(row)), key=int):
            if n not in rids:
                errs.append(f"row {label}: cites R-{n}, no '**R-{n}.' heading in 'Needs a ruling'")
        for num, slug in DR.findall(row):
            hits = [f for f in drfiles if f.startswith(f"DR-{num}-")]
            if not hits:
                errs.append(f"row {label}: cites DR-{num}, no spec/decision-records/DR-{num}-*.md")
            elif slug and not any(f == f"DR-{num}-{slug}.md" for f in hits):
                errs.append(f"row {label}: cites DR-{num} `{slug}`, no file DR-{num}-{slug}.md")
    dup = sorted({l for l in seen if seen.count(l) > 1})
    for l in dup:
        errs.append(f"row {l}: duplicate row label")
    for l in LABELS:
        if l not in seen:
            errs.append(f"row {l}: missing from the Row table")
    for l in seen:
        if l not in LABELS:
            errs.append(f"row {l}: unexpected row label")
    for p in sorted(set(re.findall(r"`(sim/[^`\s]+/records/[^`\s]+)`", text))):
        if not (root / p).is_file():
            errs.append(f"spec: cited path {p} does not exist")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--spec", default=None)
    a = ap.parse_args(argv)
    spec = a.spec or Path(a.root) / "spec" / "target-spec.md"
    errs = check(a.root, spec)
    for e in errs:
        print("FAIL:", e)
    print("spec citations:", "FAIL" if errs else "ok")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
