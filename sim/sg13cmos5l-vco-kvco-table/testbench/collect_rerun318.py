#!/usr/bin/env python3
"""Turn the `klt sim` deck-list output of gen_rerun318.py's grid into
`../corners/results_rerun318.csv` and compare it with RECORD-001's
`../corners/results.csv` (issue #318).

    python3 -I collect_rerun318.py OUTDIR DECKS_SHA256_CSV OUT_CSV

Extraction is `run.sh`'s own: the `per1 = <value>` line ngspice prints, with
`freq_hz = 1.0 / period` computed exactly as `run.sh` does, so the two CSVs
are comparable field by field.  A unit with no `per1` line is written `NA`,
`run.sh`'s own non-oscillation encoding.
"""
import csv
import pathlib
import re
import sys

PER1_RE = re.compile(r"^per1 = (\S+)\s*$", re.M)
HEADER = ["pvt_bundle", "mos_corner", "res_corner", "temp_c", "band_code",
          "vctrl_v", "period_s", "freq_hz"]


def main():
    outdir, shacsv, out_csv = (pathlib.Path(p) for p in sys.argv[1:4])
    rows, out = list(csv.DictReader(open(shacsv))), []
    for r in rows:
        text = (outdir / r["id"] / "stdout.bin").read_text(errors="replace")
        hits = PER1_RE.findall(text)
        head = [r["pvt_bundle"], r["mos_corner"], r["res_corner"], r["temp_c"],
                r["band_code"], r["vctrl_v"]]
        if not hits:
            out.append(head + ["NA", "NA"])
            continue
        period = hits[-1]
        out.append(head + [period, repr(1.0 / float(period))])
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(out)

    # Comparison with RECORD-001, keyed on the five matrix axes.
    orig_path = pathlib.Path(__file__).resolve().parent.parent / "corners" / "results.csv"
    orig = {tuple(d[k] for k in HEADER[:6]): d for d in csv.DictReader(open(orig_path))}
    same = diff = missing = na = 0
    worst = (0.0, None)
    for row in out:
        key = tuple(row[:6])
        if row[6] == "NA":
            na += 1
        if key not in orig:
            missing += 1
            print(f"MISSING in results.csv: {key}")
            continue
        was, now = orig[key]["period_s"], row[6]
        if was == now:
            same += 1
            continue
        diff += 1
        if "NA" not in (was, now):
            rel = abs(float(now) - float(was)) / float(was)
            worst = max(worst, (rel, key))
    print(f"rows {len(out)}  identical-period-to-RECORD-001 {same}  "
          f"differing {diff}  NA {na}  keys-not-in-RECORD-001 {missing}")
    if worst[1]:
        print(f"largest relative period difference {worst[0]:.3e} at {worst[1]}")
    extra = set(orig) - {tuple(r[:6]) for r in out}
    if extra:
        print(f"RECORD-001 rows not covered by this rerun: {sorted(extra)}")


main()
