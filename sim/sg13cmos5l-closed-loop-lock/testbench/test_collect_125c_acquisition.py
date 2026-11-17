#!/usr/bin/env python3
"""Self-test for collect_125c_acquisition.py (issue #389).

    python3 -I test_collect_125c_acquisition.py

Runs on synthetic data only -- no PDK, no ngspice, no network -- in the
style of the sibling `test_mismatch_gain_metrics.py`.

Two things are load-bearing:

`test_loop_report_without_crossings_is_refused`
    The issue's edge case: a batch unit that did not produce a result must
    be recorded as NOT COLLECTED, never as an unlocked point. The collector
    must refuse a report whose corner carries no crossing series rather
    than emitting a metrics row.

`test_vco_row_and_na`
    The per1 extraction must equal `collect_rerun318.py`'s (last `per1 = `
    line, `freq_hz = 1.0 / period`), and a unit with no `per1` line must
    land in the CSV as NA -- run.sh's own non-oscillation encoding -- never
    as a measured frequency.

`test_vco_flat_dot_out_layout` (issue #453)
    The VCO diagnostic must not report an absent stdout as a missing
    `per1` line: resolved-but-`per1`-less and unresolvable units are
    named in separate lines, the latter with the NOT COLLECTED framing
    the loop half already refuses on. The CSV is unaffected -- NA stays
    NA either way.
"""
import io
import json
import math
import os
import pathlib
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_125c_acquisition as ca  # noqa: E402
import mismatch_gain_metrics as mg     # noqa: E402

FREF = 20e6
TREF = 1.0 / FREF


def crossings(sig, period, t_stop, vth=1.65, amp=3.3):
    """Rising-edge times of a square wave, as a `klt sim` crossings block."""
    times, t = [], 0.25 * period
    while t < t_stop:
        times.append(round(t, 12))
        t += period
    return {"signal": sig, "level": vth, "edge": "rise", "value": len(times),
            "truncated": False, "times": times}


def corner_report(ref_period, fb_period):
    """A one-corner report shaped like the RECORD-015 loop member's."""
    n = 50
    def meas(name, sig, period):
        c = crossings(sig, period, n * ref_period)
        return {"name": name, "value": c["value"], "crossings": c}
    return {"corners": [{
        "corner_id": "mos_tt/novdd/125C", "process": "mos_tt",
        "temperature_c": 125, "status": "pass",
        "measurements": [
            {"name": "vc_avg", "value": 3.28989, "unit": "V"},
            {"name": "i_cp", "value": -5.07764e-05, "unit": "A"},
            meas("t_ref", "v(ref)", ref_period),
            meas("t_fb", "v(fb)", fb_period),
        ],
    }]}


def test_loop_metrics_roundtrip():
    """A railed unlocked point: df mean from the two periods, dual_lock 0."""
    with tempfile.TemporaryDirectory() as td:
        path = pathlib.Path(td) / "report.json"
        # fb 0.6 % slow -- the RECORD-014 mm_nom 125 C situation.
        path.write_text(json.dumps(corner_report(TREF, TREF / 0.994)))
        out = pathlib.Path(td) / "metrics.json"
        ca.collect_loop(path, out)
        m = json.loads(out.read_text())
    trace = mg.lock_trace_from_edges(
        crossings("v(ref)", TREF, 50 * TREF)["times"],
        crossings("v(fb)", TREF / 0.994, 50 * TREF)["times"], FREF)
    s = mg.fit_line([], [])
    assert m["n_cycles"] == len(trace), (m["n_cycles"], len(trace))
    # fb uniformly 0.6 % slow: freq-lock holds (|df| < 1 %) but the phase
    # error drifts past the 5 % band, so the final 20 are not dual-locked.
    assert m["dual_lock"] == 0
    assert m["longest_dual_lock_run"] < m["longest_freq_lock_run"]
    assert abs(m["df_mean_pct"] - (-0.6)) < 0.01, m["df_mean_pct"]
    assert m["vc_avg_v"] == 3.28989
    assert s is None  # fit_line guard on empty input, while we are here


def test_loop_locks_when_periods_match():
    with tempfile.TemporaryDirectory() as td:
        path = pathlib.Path(td) / "report.json"
        path.write_text(json.dumps(corner_report(TREF, TREF)))
        out = pathlib.Path(td) / "metrics.json"
        ca.collect_loop(path, out)
        m = json.loads(out.read_text())
    assert m["dual_lock"] == 1 and m["longest_dual_lock_run"] > 20
    assert abs(m["df_mean_pct"]) < 1e-9


def test_loop_report_without_crossings_is_refused():
    """NOT COLLECTED, never an unlocked point: no series -> hard refusal."""
    with tempfile.TemporaryDirectory() as td:
        path = pathlib.Path(td) / "report.json"
        rep = corner_report(TREF, TREF)
        rep["corners"][0]["measurements"] = [
            m for m in rep["corners"][0]["measurements"]
            if not m["name"].startswith("t_")]
        path.write_text(json.dumps(rep))
        try:
            ca.collect_loop(path, pathlib.Path(td) / "out.json")
        except SystemExit as e:
            assert "NOT COLLECTED" in str(e), e
        else:
            raise AssertionError("collector accepted a report with no crossings")


def test_vco_row_and_na():
    with tempfile.TemporaryDirectory() as td:
        outdir = pathlib.Path(td)
        for uid, per in (("b11_v3p3", 7.873107e-10), ("b00_v2p1", 1.31279e-09),
                         ("dead", None)):
            d = outdir / uid
            d.mkdir()
            body = "Simulation text\nper1                =  9.9e-10 (bogus first)\n"
            if per is not None:
                body += f"per1 = {per!r}\n"
            else:
                body = "no oscillation here\n"
            (d / "stdout.bin").write_text(body)
        shacsv = outdir / "decks.csv"
        shacsv.write_text(
            "id,mos_corner,res_corner,temp_c,band_code,vctrl_v,deck_sha256\n"
            "b11_v3p3,mos_tt,res_typ,125,11,3.3,aa\n"
            "b00_v2p1,mos_tt,res_typ,125,00,2.1,bb\n"
            "dead,mos_tt,res_typ,125,00,2.1,cc\n")
        out_csv = outdir / "vco.csv"
        ca.collect_vco(outdir, shacsv, out_csv)
        rows = {r["id"]: r for r in __import__("csv").DictReader(open(out_csv))}
    got = float(rows["b11_v3p3"]["period_s"])
    assert got == 7.873107e-10, got  # the LAST per1 line wins, as rerun318's does
    assert abs(float(rows["b11_v3p3"]["freq_hz"]) - 1.0 / got) < 1e-6
    assert rows["b00_v2p1"]["period_s"] == "1.31279e-09"
    assert rows["dead"]["period_s"] == "NA" and rows["dead"]["freq_hz"] == "NA"


def test_vco_flat_dot_out_layout():
    """The committed raw layout: flat `<id>.out` files resolve too; a unit
    with both candidates takes the `<id>/stdout.bin` convention, and a
    single unresolvable unit still lands NA (no refusal).  Its fixture
    also has one unit of each NA kind -- `dead` (stdout resolved, no
    `per1` line) and `missing` (no file at all) -- so the printed
    diagnostic must name them under different labels (issue #453): the
    unresolved wording carries the NOT COLLECTED framing and says nothing
    about a `per1` line."""
    with tempfile.TemporaryDirectory() as td:
        outdir = pathlib.Path(td)
        (outdir / "b11_both.out").write_text(
            "Simulation text\nper1 = 9.9e-10\n")
        conv = outdir / "b11_both"
        conv.mkdir()
        (conv / "stdout.bin").write_text(
            "Simulation text\nper1 = 7.873107e-10\n")
        (outdir / "b00_v2p1.out").write_text(
            "Simulation text\nper1 = 1.31279e-09\n")
        (outdir / "dead.out").write_text("no oscillation here\n")
        shacsv = outdir / "decks.csv"
        shacsv.write_text(
            "id,mos_corner,res_corner,temp_c,band_code,vctrl_v,deck_sha256\n"
            "b11_both,mos_tt,res_typ,125,11,3.3,aa\n"
            "b00_v2p1,mos_tt,res_typ,125,00,2.1,bb\n"
            "dead,mos_tt,res_typ,125,00,2.1,cc\n"
            "missing,mos_tt,res_typ,125,00,2.1,dd\n")
        out_csv = outdir / "vco.csv"
        buf = io.StringIO()
        with redirect_stdout(buf):
            ca.collect_vco(outdir, shacsv, out_csv)
        text = buf.getvalue()
        rows = {r["id"]: r for r in __import__("csv").DictReader(open(out_csv))}
    got = float(rows["b11_both"]["period_s"])
    assert got == 7.873107e-10, got  # stdout.bin beat the flat .out candidate
    assert rows["b00_v2p1"]["period_s"] == "1.31279e-09"
    assert rows["dead"]["period_s"] == "NA"
    assert rows["missing"]["period_s"] == "NA" and rows["missing"]["freq_hz"] == "NA"
    no_per1 = [l for l in text.splitlines() if "no per1 line" in l]
    not_res = [l for l in text.splitlines() if "did not resolve" in l]
    assert len(no_per1) == 1 and "dead" in no_per1[0] and "missing" not in no_per1[0], text
    assert len(not_res) == 1 and "missing" in not_res[0] \
        and "dead" not in not_res[0] and "per1" not in not_res[0] \
        and "NOT COLLECTED" in not_res[0], text


def test_vco_refuses_when_no_unit_resolves():
    """No readable stdout for ANY unit -> hard refusal naming both layouts,
    never an emitted all-NA CSV."""
    with tempfile.TemporaryDirectory() as td:
        outdir = pathlib.Path(td)
        shacsv = outdir / "decks.csv"
        shacsv.write_text(
            "id,mos_corner,res_corner,temp_c,band_code,vctrl_v,deck_sha256\n"
            "gone,mos_tt,res_typ,125,11,3.3,aa\n"
            "lost,mos_tt,res_typ,125,00,2.1,bb\n")
        out_csv = outdir / "vco.csv"
        try:
            ca.collect_vco(outdir, shacsv, out_csv)
        except SystemExit as e:
            assert "stdout.bin" in str(e) and "<id>.out" in str(e), e
        else:
            raise AssertionError("collector emitted a CSV with zero stdout inputs")
        assert not out_csv.exists()


def test_fit_helpers_untouched():
    """The collector must not grow its own fit or lock math."""
    assert ca.mg is mg
    assert ca.cm.DF_LIMIT == 0.01 and ca.cm.PH_LIMIT == 0.05
    assert math.isclose(ca.TARGET_F_HZ, 64 * FREF)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("all collect_125c_acquisition self-tests passed")
