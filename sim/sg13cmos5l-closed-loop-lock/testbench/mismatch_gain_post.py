#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/mismatch_gain_post.py
(issue #385) -- turn the RECORD-014 gain sweep's two `klt sim` reports into
`../corners/mismatch_gain.csv` and a fit summary.

    python3 -I mismatch_gain_post.py POINTS_JSON DC_REPORT LOOP_REPORT \
        --csv ../corners/mismatch_gain.csv --summary ../corners/mismatch_gain_fit.json

`POINTS_JSON` is the `points.json` `gen_mismatch_gain_requests.py` wrote; the
two reports are either single `klt sim` envelopes or `--batch-set` aggregates
(both shapes are accepted).  A set envelope carries `requests[]`, each naming
the member request file it ran and the path of that member's own report --
the member path is how a corner is tied back to its mismatch point, since the
set's per-member report directories are numbered by submission order and
carry no tag of their own.

The x-axis is the **measured** DC mismatch of each perturbed snapshot, never
the mismatch the generator asked for; the y-axis is the final-20-cycle mean
static phase error from `mismatch_gain_metrics.lock_trace_from_edges` over
the reported `v(ref)` / `v(fb)` crossing times.  A point whose loop did not
hold dual lock over those cycles is written to the CSV with its numbers and
`dual_lock=0`, and is EXCLUDED from every fit (a phase error read off a loop
that is not locked is not a static phase error).

A point the fleet did not return is NOT silently dropped, and -- this is the
distinction that matters -- it is never recorded as an unlocked point: a
corner whose report carries no `crossings` series (a `--batch-set` member
still running at collection, a `batch_poll_timeout`, an errored unit) is
listed in the summary's `not_collected` with its own diagnostic codes and on
stderr, and gets no CSV row.  "The loop did not lock" and "we never got an
answer" are different findings and the CSV must not blur them.  A missing DC
corner is still fatal -- without the measured x-axis a loop result cannot be
placed.
"""
import argparse
import json
import math
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpdiag_metrics as cm         # noqa: E402
import mismatch_gain_metrics as mg  # noqa: E402

FREF = 20e6
N_FINAL = 20

CSV_COLUMNS = [
    "tag", "target_pct", "k", "temp_c", "mos_corner",
    "mismatch_pct", "iup_a", "idn_a",
    "phase_mean_pct", "phase_min_pct", "phase_max_pct",
    "df_mean_pct", "n_cycles", "n_final",
    "longest_dual_lock_run", "lock_time_s", "dual_lock",
    "vc_avg_v", "i_cp_a", "ref_edges", "fb_edges",
]


def iter_corners(report, base):
    """(request_path_or_None, corner) for a single or a `--batch-set` report.

    `base` is the directory the envelope was read from, so a member report
    recorded as a relative path still resolves.
    """
    members = report.get("requests")
    if not isinstance(members, list):
        members = report.get("results")
    if isinstance(members, list):
        for member in members:
            req = member.get("request")
            body = member.get("report")
            if isinstance(body, str):
                path = pathlib.Path(body)
                if not path.is_absolute():
                    path = base / path
                body = json.loads(path.read_text())
            elif not isinstance(body, dict):
                body = member
            for corner in body.get("corners") or []:
                yield req, corner
    else:
        for corner in report.get("corners") or []:
            yield None, corner


def meas_map(corner):
    return {m["name"]: m for m in corner.get("measurements") or []}


def tag_from_request(path, tags):
    """`.../loop/mm_p8/request.json` -> `mm_p8`."""
    if not path:
        return None
    for part in reversed(pathlib.PurePath(path).parts):
        if part in tags:
            return part
    return None


def collect(report, base, tags, kind):
    """{(tag, temp_c): corner} -- refuses a report it cannot key."""
    out = {}
    for req, corner in iter_corners(report, base):
        tag = tag_from_request(req, tags)
        if tag is None:
            raise SystemExit(
                f"{kind} report: cannot tell which mismatch point a corner "
                f"belongs to (request={req!r}). Re-run the set from the "
                "generated tree so each member's path carries its tag.")
        key = (tag, float(corner["temperature_c"]))
        if key in out:
            raise SystemExit(f"{kind} report: duplicate corner {key}")
        out[key] = corner
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("points_json")
    ap.add_argument("dc_report")
    ap.add_argument("loop_report")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--summary", required=True)
    a = ap.parse_args()

    points = json.loads(pathlib.Path(a.points_json).read_text())
    by_tag = {p["tag"]: p for p in points["points"]}
    dc_path, loop_path = pathlib.Path(a.dc_report), pathlib.Path(a.loop_report)
    dc = collect(json.loads(dc_path.read_text()), dc_path.parent, by_tag, "dc")
    loop = collect(json.loads(loop_path.read_text()), loop_path.parent, by_tag, "loop")

    rows, missing = [], []
    for tag, meta in by_tag.items():
        for temp in points["temps_c"]:
            key = (tag, float(temp))
            if key not in dc:
                raise SystemExit(
                    f"missing dc corner {key}: without the measured DC mismatch "
                    "this point has no x-axis and cannot be placed")
            if key not in loop:
                missing.append({"tag": tag, "temp_c": temp, "reason": "no corner in the report",
                                "codes": []})
                continue
            dm, lm = meas_map(dc[key]), meas_map(loop[key])
            if "crossings" not in lm.get("t_ref", {}) or "crossings" not in lm.get("t_fb", {}):
                # No edge series came back at all -- the unit did not produce a
                # result.  That is NOT "the loop did not lock"; keep it out of
                # the CSV so the two can never be confused.
                missing.append({
                    "tag": tag, "temp_c": temp,
                    "reason": "report carries no crossing series for v(ref)/v(fb)",
                    "corner_status": loop[key].get("status"),
                    "codes": sorted({d.get("code") for d in (loop[key].get("diagnostics") or [])
                                     if d.get("code")}),
                })
                continue
            ref = lm["t_ref"]["crossings"]
            fb = lm["t_fb"]["crossings"]
            if ref.get("truncated") or fb.get("truncated"):
                raise SystemExit(f"{key}: crossing series truncated -- raise `max`")
            trace = mg.lock_trace_from_edges(ref.get("times") or [],
                                             fb.get("times") or [], FREF)
            s = cm.summarize(trace, N_FINAL)
            fin = trace[-N_FINAL:]
            locked = bool(fin) and all(cm.is_dual_lock(df, pe) for _, df, pe in fin)
            rows.append({
                "tag": tag, "target_pct": meta["target_pct"], "k": meta["k"],
                "temp_c": temp, "mos_corner": points["mos_corner"],
                "mismatch_pct": dm["mismatch_pct"]["value"],
                "iup_a": dm["iup_a"]["value"], "idn_a": dm["idn_a"]["value"],
                "phase_mean_pct": None if "phase_mean" not in s else s["phase_mean"] * 100,
                "phase_min_pct": None if "phase_min" not in s else s["phase_min"] * 100,
                "phase_max_pct": None if "phase_max" not in s else s["phase_max"] * 100,
                "df_mean_pct": None if "df_mean" not in s else s["df_mean"] * 100,
                "n_cycles": s["n_cycles"], "n_final": s["n_final"],
                "longest_dual_lock_run": s["longest_dual_lock_run"],
                "lock_time_s": s["lock_time_s"], "dual_lock": int(locked),
                "vc_avg_v": lm["vc_avg"]["value"], "i_cp_a": lm["i_cp"]["value"],
                "ref_edges": lm["t_ref"]["value"], "fb_edges": lm["t_fb"]["value"],
            })

    rows.sort(key=lambda r: (r["temp_c"], r["mismatch_pct"]))
    out = pathlib.Path(a.csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        f.write(",".join(CSV_COLUMNS) + "\n")
        for r in rows:
            f.write(",".join("" if r[c] is None else repr(r[c]) if isinstance(r[c], float)
                             else str(r[c]) for c in CSV_COLUMNS) + "\n")

    def fits(sel):
        pts = [r for r in sel if r["dual_lock"] and r["phase_mean_pct"] is not None]
        xs = [r["mismatch_pct"] for r in pts]
        ys = [r["phase_mean_pct"] for r in pts]
        return {"n_points": len(pts), "n_excluded_unlocked": len(sel) - len(pts),
                "free": mg.fit_line(xs, ys),
                "through_origin": mg.fit_through_origin(xs, ys)}

    summary = {
        "issue": 385, "slug": "sg13cmos5l-closed-loop-lock",
        "fref_hz": FREF, "n_final_cycles": N_FINAL,
        "x": "measured DC mismatch_pct of the perturbed cp snapshot",
        "y": "final-20-cycle mean static phase error, % of T_ref",
        "not_collected": missing,
        "per_temperature": {str(t): fits([r for r in rows if r["temp_c"] == t])
                            for t in points["temps_c"]},
        "pooled": fits(rows),
        "baseline": [{"temp_c": r["temp_c"], "mismatch_pct": r["mismatch_pct"],
                      "phase_mean_pct": r["phase_mean_pct"]}
                     for r in rows if r["tag"] == "mm_nom"],
        "screening_limit_model": {
            "note": "the +/-3.5 % screening limit assumes this gain, through the origin",
            "slope_pp_per_pp": 9.176 / 6.42,
            "source": "sim/sg13cmos5l-cp-icp-trim-mc/README.md 'Limit (still needs a ruling)'",
        },
    }
    pathlib.Path(a.summary).write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")

    print(f"wrote {out} ({len(rows)} rows) and {a.summary}", file=sys.stderr)
    for m in missing:
        codes = ", ".join(m.get("codes") or []) or "none"
        print(f"  NOT COLLECTED: {m['tag']} at {m['temp_c']} C -- {m['reason']} "
              f"[{codes}]; absent from the CSV and from every fit (this is NOT an "
              "unlocked point)", file=sys.stderr)
    for t, f in summary["per_temperature"].items():
        free = f["free"]
        if free:
            print(f"  {t:>5} C: slope {free['slope']:+.4f} pp/pp  intercept "
                  f"{free['intercept']:+.4f} pp  resid_rms {free['resid_rms']:.4f} pp "
                  f"(n={free['n']}, excluded {f['n_excluded_unlocked']})", file=sys.stderr)
        else:
            print(f"  {t:>5} C: no fit (n={f['n_points']})", file=sys.stderr)
    p = summary["pooled"]["free"]
    if p:
        print(f"  pooled: slope {p['slope']:+.4f} pp/pp  intercept {p['intercept']:+.4f} pp "
              f"R^2 {p['r_squared']:.4f}", file=sys.stderr)


if __name__ == "__main__":
    main()
