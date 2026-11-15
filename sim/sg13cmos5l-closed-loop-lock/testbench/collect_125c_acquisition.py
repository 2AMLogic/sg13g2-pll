#!/usr/bin/env python3
"""Turn the RECORD-015 `klt sim` outputs into the two committed evidence files
for the 125 C acquisition diagnosis (issue #389).

    python3 -I collect_125c_acquisition.py VCO_OUTDIR VCO_DECKS_SHA256_CSV \
        LOOP_REPORT --vco-csv ../corners/vco_openloop_125c.csv \
        --loop-json ../corners/loop_nominal_125c_metrics.json

`VCO_OUTDIR` is the `-o` directory the batch-set ran with (per-unit
`stdout.bin` files under it), `VCO_DECKS_SHA256_CSV` is the generator's own
deck manifest, and `LOOP_REPORT` is the collected single-corner report of the
unperturbed (`mm_nom`) closed-loop point.  Writes:

vco-csv
    One row per unit: band, `vctrl`, the `per1 = ...` line ngspice printed
    (the Kvco bench's own extraction), and `freq_hz = 1.0 / period` exactly
    as `collect_rerun318.py` computes it, so the new curve is comparable
    field by field with `../../sg13cmos5l-vco-kvco-table/corners/
    results_rerun318.csv`.  Also prints the two things RECORD-015 turns
    into its verdict: whether band code moves frequency at the probe point,
    and the highest frequency band `11` reaches and at which `vctrl`
    (against the 1280 MHz an N = 64 loop at 20 MHz needs).

loop-json
    The same metrics `mismatch_gain_post.py` computes for a RECORD-014
    point -- final-20 phase/df stats, longest dual-lock run, lock time,
    `vc_avg`, `i_cp` -- built with `mismatch_gain_metrics.
    lock_trace_from_edges` and `cpdiag_metrics.summarize` (the committed,
    self-tested functions) over the report's `v(ref)` / `v(fb)` crossing
    series, so the sanity point is compared to RECORD-014's `mm_nom` 125 C
    row like for like.
"""
import argparse
import csv
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cpdiag_metrics as cm         # noqa: E402
import mismatch_gain_metrics as mg  # noqa: E402

FREF = 20e6
N_FINAL = 20
TARGET_F_HZ = 64 * FREF

PER1_RE = re.compile(r"^per1 = (\S+)\s*$", re.M)


def collect_vco(outdir: pathlib.Path, shacsv: pathlib.Path, out_csv: pathlib.Path):
    rows = []
    for r in csv.DictReader(open(shacsv)):
        stdout = outdir / r["id"] / "stdout.bin"
        hits = PER1_RE.findall(stdout.read_text(errors="replace")) if stdout.is_file() else []
        period = hits[-1] if hits else None
        rows.append({
            "id": r["id"], "mos_corner": r["mos_corner"],
            "res_corner": r["res_corner"], "temp_c": r["temp_c"],
            "band_code": r["band_code"], "vctrl_v": r["vctrl_v"],
            "period_s": period if period else "NA",
            "freq_hz": repr(1.0 / float(period)) if period else "NA",
        })
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    numeric = [r for r in rows if r["period_s"] != "NA"]
    by_band = {}
    for r in numeric:
        by_band.setdefault(r["vctrl_v"], {})[r["band_code"]] = float(r["period_s"])
    probe = by_band.get("2.1")
    if probe and len(probe) == 4:
        periods = list(probe.values())
        spread = (max(periods) - min(periods)) / min(periods)
        print(f"band probe at vctrl=2.1 V: periods {sorted(probe.items())} "
              f"-> relative spread {spread:.3e}")
        print(f"band code is {'INERT' if spread == 0 else 'live'} in this deck at 2.1 V")

    b11 = sorted(((float(r["vctrl_v"]), 1.0 / float(r["period_s"]))
                  for r in numeric if r["band_code"] == "11"))
    if b11:
        top_v, top_f = b11[-1]
        reached = [vf for vf in b11 if vf[1] >= TARGET_F_HZ]
        print(f"band 11 (mos_tt/res_typ/{'125'} C): f(vctrl) = "
              + ", ".join(f"{v:g} V->{f / 1e6:.1f} MHz" for v, f in b11))
        if reached:
            print(f"1280 MHz ({TARGET_F_HZ:.0f} Hz) first reached at "
                  f"vctrl = {reached[0][0]:g} V; max {top_f / 1e6:.1f} MHz at {top_v:g} V")
        else:
            print(f"1280 MHz NOT reached at any swept vctrl; max "
                  f"{top_f / 1e6:.1f} MHz at {top_v:g} V -- short by "
                  f"{(TARGET_F_HZ - top_f) / 1e6:.1f} MHz")
    na = [r["id"] for r in rows if r["period_s"] == "NA"]
    if na:
        print(f"units with no per1 line (recorded NA, not as unlocked): {na}")


def collect_loop(report_path: pathlib.Path, out_json: pathlib.Path):
    report = json.loads(report_path.read_text())
    corners = report.get("corners") or []
    if len(corners) != 1:
        raise SystemExit(f"expected exactly 1 corner in {report_path}, got {len(corners)}")
    corner = corners[0]
    lm = {m["name"]: m for m in corner.get("measurements") or []}
    for sig in ("t_ref", "t_fb"):
        cr = lm.get(sig, {}).get("crossings")
        if not cr:
            raise SystemExit(
                f"report carries no crossing series for v({sig[2:]}) -- the unit "
                "did not produce a result; that is NOT COLLECTED, not unlocked")
        if cr.get("truncated"):
            raise SystemExit("crossing series truncated -- raise `max`")
    trace = mg.lock_trace_from_edges(lm["t_ref"]["crossings"]["times"],
                                     lm["t_fb"]["crossings"]["times"], FREF)
    s = cm.summarize(trace, N_FINAL)
    fin = trace[-N_FINAL:]
    locked = bool(fin) and all(cm.is_dual_lock(df, pe) for _, df, pe in fin)
    out = {
        "issue": 389, "slug": "sg13cmos5l-closed-loop-lock",
        "tag": "mm_nom", "temp_c": corner.get("temperature_c"),
        "mos_corner": corner.get("process"),
        "n_cycles": s["n_cycles"], "n_final": s["n_final"],
        "longest_dual_lock_run": s["longest_dual_lock_run"],
        "longest_freq_lock_run": s["longest_freq_lock_run"],
        "lock_time_s": s["lock_time_s"], "dual_lock": int(locked),
        "vc_avg_v": lm["vc_avg"]["value"], "i_cp_a": lm["i_cp"]["value"],
        "ref_edges": lm["t_ref"]["value"], "fb_edges": lm["t_fb"]["value"],
    }
    for key in ("phase_mean", "phase_min", "phase_max", "df_mean", "df_min", "df_max"):
        if key in s:
            out[key + "_pct"] = s[key] * 100
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1, sort_keys=True))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vco_outdir")
    ap.add_argument("vco_decks_sha256_csv")
    ap.add_argument("loop_report")
    ap.add_argument("--vco-csv", required=True)
    ap.add_argument("--loop-json", required=True)
    a = ap.parse_args()
    collect_vco(pathlib.Path(a.vco_outdir),
                pathlib.Path(a.vco_decks_sha256_csv),
                pathlib.Path(a.vco_csv))
    collect_loop(pathlib.Path(a.loop_report), pathlib.Path(a.loop_json))


if __name__ == "__main__":
    main()
