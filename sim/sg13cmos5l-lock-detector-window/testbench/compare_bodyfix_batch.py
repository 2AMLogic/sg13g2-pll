#!/usr/bin/env python3
"""Keyed full-grid comparison: corners/*_bodyfix_batch.csv vs RECORD-004's
corners/*_crowbarfix.csv (issue #139, Part of #16).  Read-only on both sides.

Usage: python3 -I compare_bodyfix_batch.py [corners_dir]

Per file: keyed join on the identifying columns, fail on missing keys / header mismatch / baseline-vs-new duplicate-key
sets that differ (duplicates present identically on both sides are disclosed
and joined by occurrence index), classify every cell as exact (string-identical) / numeric (differs) /
text (non-numeric differs) and print every changed cell with its relative
change.  Exit 1 on any missing/extra key, differing duplicate-key set or header mismatch.
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORNERS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "corners")

KEYS = {
    "window": ["corner_tag"],
    "schmitt": ["mos_corner", "temp_c", "vsup_v"],
    "tstep_convergence": ["mos_corner", "res_corner", "temp_c", "dut_variant", "tstep"],
    "rc_extract": ["kind", "instance", "corner", "temp_c"],
    "ladder": ["corner_tag"],
    "ladder_raw": ["corner_tag", "tau_xwin"],
}


def load(path, keys):
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        rows, dups, seen = {}, [], {}
        for row in r:
            k = tuple(row[c] for c in keys)
            n = seen.get(k, 0)
            seen[k] = n + 1
            if n:
                dups.append(k)
            # duplicate keys are disclosed, then joined by occurrence index
            rows[k + (f"#{n}",)] = row
        return r.fieldnames, rows, dups


def num(s):
    try:
        return float(s)
    except ValueError:
        return None


bad = False
for name, keys in KEYS.items():
    base = os.path.join(CORNERS, f"{name}_crowbarfix.csv")
    new = os.path.join(CORNERS, f"{name}_bodyfix_batch.csv")
    hb, rb, db = load(base, keys)
    hn, rn, dn = load(new, keys)
    missing = sorted(set(rb) - set(rn))
    extra = sorted(set(rn) - set(rb))
    hdr_ok = hb == hn
    exact = changed_rows = changed_cells = 0
    detail = []
    for k in sorted(set(rb) & set(rn)):
        diffs = []
        for c in hb:
            a, b = rb[k][c], rn[k][c]
            if a == b:
                continue
            x, y = num(a), num(b)
            if x is not None and y is not None:
                rel = (y - x) / x if x else math.inf
                diffs.append((c, a, b, f"{rel:+.3%}"))
            else:
                diffs.append((c, a, b, "text"))
        if diffs:
            changed_rows += 1
            changed_cells += len(diffs)
            detail.append((k, diffs))
        else:
            exact += 1
    print(f"== {name}: base={len(rb)} new={len(rn)} exact_rows={exact} "
          f"changed_rows={changed_rows} changed_cells={changed_cells} "
          f"missing={len(missing)} extra={len(extra)} dup_base={len(db)} "
          f"dup_new={len(dn)} header_match={hdr_ok}")
    if db != dn:
        bad = True
        print("   DUPLICATE-KEY SETS DIFFER between baseline and new")
    if db:
        print("   duplicate keys (same on both sides, joined by occurrence):", db)
    if missing or extra or not hdr_ok:
        bad = True
        print("   MISSING:", missing, "EXTRA:", extra)
    for k, diffs in detail:
        for c, a, b, rel in diffs:
            print(f"   {'|'.join(k)} :: {c}: {a} -> {b} ({rel})")
sys.exit(1 if bad else 0)
