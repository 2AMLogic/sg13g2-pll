#!/usr/bin/env python3
"""Fold a `klt sim` Monte Carlo report into the two committed CSVs under
../corners/, so the campaign stays readable and recomputable without parsing
the 1500-entry JSON.

    python3 -I collect_mc.py ../reports/sim.mc.json --outdir ../corners

Writes:
  mc-samples.csv     one row per sample: corner, process, temp, sample index,
                     the three derived seeds, the three measurements and the
                     sample's own pass/fail against the screening limit.
  mc-per-corner.csv  one row per expanded corner: n, mean, stddev and the
                     report's own quantiles for each measurement.

`mc-samples.csv` is the raw evidence: `klt yield --limits` can be re-run
against any later ratified limit from these samples alone (see
../records/RECORD-002, "Recomputing this against a different limit").
"""
import argparse
import csv
import json
import pathlib

MEAS = ["iup_a", "idn_a", "mismatch_pct"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("report", help="a klt sim --format json Monte Carlo report")
    ap.add_argument("--outdir", default="../corners")
    a = ap.parse_args()

    rep = json.loads(pathlib.Path(a.report).read_text())
    out = pathlib.Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for c in rep["corners"]:
        mc = c.get("monte_carlo") or {}
        vals = {m["name"]: m for m in (c.get("measurements") or [])}
        row = {
            "corner_id": c["corner_id"],
            "process": c.get("process"),
            "temperature_c": c.get("temperature_c"),
            "sample_index": mc.get("sample_index"),
            "rndseed": mc.get("seed"),
            "process_seed": mc.get("process_seed"),
            "mismatch_seed": mc.get("mismatch_seed"),
            "status": c.get("status"),
        }
        for name in MEAS:
            row[name] = (vals.get(name) or {}).get("value")
            row[f"{name}_status"] = (vals.get(name) or {}).get("status")
        rows.append(row)
    rows.sort(key=lambda r: (str(r["process"]), r["temperature_c"] if
                             r["temperature_c"] is not None else 0,
                             r["sample_index"] if r["sample_index"] is not None else 0))
    with open(out / "mc-samples.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    per = []
    for m in rep["measurements"]:
        stats = m.get("monte_carlo") or {}
        for bc in stats.get("by_corner") or []:
            rec = {
                "measurement": m["name"],
                "unit": m.get("unit"),
                "corner_id": bc["corner_id"],
                "n": bc.get("n"),
                "errored": bc.get("errored"),
                "mean": bc.get("mean"),
                "stddev": bc.get("stddev"),
                "min": bc.get("min"),
                "max": bc.get("max"),
            }
            for q, v in (bc.get("quantiles") or {}).items():
                rec[q] = v
            per.append(rec)
    keys = []
    for rec in per:
        for k in rec:
            if k not in keys:
                keys.append(k)
    with open(out / "mc-per-corner.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(per)

    print(f"wrote {len(rows)} sample rows and {len(per)} per-corner rows to {out}")


main()
