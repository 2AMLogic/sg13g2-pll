#!/usr/bin/env python3
"""Self-test for threshold_grid.py's reduce DC-side honesty (issue #453).

    python3 -I test_threshold_grid.py

Runs on synthetic stdout.bin files only -- no PDK, no ngspice, no network.

The load-bearing distinction (issue #453): a DC deck whose stdout did not
resolve must be visible as absent -- flagged `nounit` in the CSV and named
on a SANITY line -- never rendered as the same `NA` a resolved deck
legitimately records for `vth_ntmp` (RECORD-001: the nand output never
crosses mid-rail in DC, so "NA" is a real measurement there).  On a
fully-resolved run every flag stays empty, which is what keeps the
committed, hash-pinned `corners/results.csv` byte-identical under
regeneration.
"""
import csv
import io
import os
import pathlib
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import threshold_grid as tg  # noqa: E402

DC_OK = "vth_d1 = 1.65\nvth_xd5 = 0.9\nntmp_min = 0.3\n"   # no vth_ntmp: genuine NA


def dc_ids():
    return ["dc_%s_%s" % (b[0], tg.tag(vdd)) for b, vdd in tg.points(False)]


def edge_ids():
    ids = []
    for b, vdd in tg.points(False):
        for ftag, _ in tg.FREQS:
            for duty in tg.DUTIES:
                for direction in ("il", "ih"):
                    ids.append("%s_%s_%s_%s_d%d"
                               % (direction, b[0], tg.tag(vdd), ftag, duty))
    return ids


def write_stdout(work, uid, text):
    d = work / "pfdthr" / "out" / uid
    d.mkdir(parents=True, exist_ok=True)
    (d / "stdout.bin").write_text(text)


def edge_ok(uid):
    """A fully-registering edge deck: `t_rise_1` at the first edge and every
    segment-last crossing at its expected time, so no seg1/nofail flag."""
    direction, _, vddtag, ftag, _ = uid.split("_")
    tper = 1.0 / dict(tg.FREQS)[ftag]
    lines = ["t_rise_1 = %.6e" % (tg.TR / 2.0)]
    for k in range(1, tg.N_SEG + 1):
        t_exp = (k - 1) * tg.N_CYC * tper + (tg.N_CYC - 1) * tper + tg.TR / 2.0
        lines.append("t_rise_%d = %.6e" % (k * tg.N_CYC, t_exp))
    return "\n".join(lines) + "\n"


def reduce(work):
    buf = io.StringIO()
    with redirect_stdout(buf):
        tg.reduce_all(work, work / "corners")
    rows = list(csv.DictReader(open(work / "corners" / "results.csv")))
    dc = {"dc_" + r["bundle"] + "_" + r["vdd_v"].replace(".", "p"): r
          for r in rows if r["kind"] == "dc"}
    return buf.getvalue(), dc


def test_all_dc_resolved_has_zero_flags():
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        for uid in dc_ids():
            write_stdout(work, uid, DC_OK)
        for uid in edge_ids():
            write_stdout(work, uid, edge_ok(uid))
        text, dc = reduce(work)
    assert len(dc) == len(dc_ids())
    for uid, r in dc.items():
        assert r["flag"] == "", (uid, r["flag"])      # byte-invisible path
    assert dc["dc_typ_3p3"]["vth_d1_v"] == "1.65"
    assert dc["dc_typ_3p3"]["vth_ntmp_v"] == "NA"     # resolved-deck NA, empty flag
    assert "SANITY DC stdout resolution: %d/%d decks resolved" \
        % (len(dc_ids()), len(dc_ids())) in text


def test_all_dc_absent_is_flagged_and_named():
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        for uid in edge_ids():                        # DC stdouts all absent
            write_stdout(work, uid, edge_ok(uid))
        text, dc = reduce(work)
    assert len(dc) == len(dc_ids())
    for uid, r in dc.items():
        assert r["flag"] == "nounit", (uid, r["flag"])
        assert r["vth_d1_v"] == "NA" and r["vth_ntmp_v"] == "NA"
    assert "SANITY DC stdout resolution: 0/%d decks resolved" % len(dc_ids()) in text
    unres = [l for l in text.splitlines() if l.startswith("  DC UNRESOLVED")]
    assert len(unres) == 1
    for uid in dc_ids():
        assert uid in unres[0], (uid, unres[0])


def test_partial_dc_absent_flags_only_the_missing_one():
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        for uid in dc_ids():
            write_stdout(work, uid, DC_OK)
        for uid in edge_ids():
            write_stdout(work, uid, edge_ok(uid))
        gone = dc_ids()[4]
        (work / "pfdthr" / "out" / gone / "stdout.bin").unlink()
        text, dc = reduce(work)
    for uid, r in dc.items():
        assert (r["flag"] == "nounit") == (uid == gone), (uid, r["flag"])
    assert "SANITY DC stdout resolution: %d/%d decks resolved" \
        % (len(dc_ids()) - 1, len(dc_ids())) in text
    assert gone in text


def test_resolved_measless_dc_stays_na_not_nounit():
    """A deck whose stdout resolved but carries no .meas lines keeps NA with
    an empty flag: absence of a measurement is not absence of an input."""
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        for uid in dc_ids():
            write_stdout(work, uid, DC_OK)
        for uid in edge_ids():
            write_stdout(work, uid, edge_ok(uid))
        write_stdout(work, dc_ids()[2], "simulator produced nothing measurable\n")
        text, dc = reduce(work)
    r = dc[dc_ids()[2]]
    assert r["flag"] == "" and r["vth_d1_v"] == "NA", r
    assert "SANITY DC stdout resolution: %d/%d decks resolved" \
        % (len(dc_ids()), len(dc_ids())) in text


def test_grid_shape_unchanged():
    """81 rows, 9 of them DC -- the schema this self-test reasons about."""
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        for uid in dc_ids():
            write_stdout(work, uid, DC_OK)
        for uid in edge_ids():
            write_stdout(work, uid, edge_ok(uid))
        _, dc = reduce(work)
    assert len(dc_ids()) == 9 and len(edge_ids()) == 72


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("all threshold_grid self-tests passed")
