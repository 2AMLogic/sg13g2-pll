#!/usr/bin/env python3
"""Per-group NWell probe for a composed pll_<block>.gds (issue #195).

Usage (repo root): layout/.venv/bin/python layout/sg13cmos5l-pll/diagnosis/issue-195/probe-nwell.py GDS TOP [NW_B1_UM]

For every child instance that draws NWell (31/0) it prints the well's
NWell.pin (31/2) label (the body net the flow labels the well with), its bbox
in the top cell's coordinates, and the merged shape count; then the exact
minimum NWell-to-NWell separation for every pair of wells whose labels
differ (different-net wells), compared with the PDK's NW.b1 value
(min. PWell width between NWell regions of different net; 1.80 um in
ihp-sg13cmos5l's sg13cmos5l_tech_default.json). Exit 1 if any different-net
pair is closer than NW_B1_UM. The curated klt sg13cmos5l deck has no NWell
rule (31/0 is in its layers_in_stream_without_rules), so this is the only
NW.b1 evidence for the record.
"""
import sys
import klayout.db as db

gds, top = sys.argv[1], sys.argv[2]
nw_b1 = float(sys.argv[3]) if len(sys.argv) > 3 else 1.80
ly = db.Layout()
ly.read(gds)
t = ly.cell(top)
dbu = ly.dbu
NW, NWP = ly.layer(31, 0), ly.layer(31, 2)
wells = []
for inst in t.each_inst():
    c = inst.cell
    r = db.Region(c.begin_shapes_rec(NW)).transformed(inst.cplx_trans).merged()
    if r.is_empty():
        continue
    labels = sorted({it.shape().text.string for it in c.begin_shapes_rec(NWP) if it.shape().is_text()})
    wells.append((c.name, labels, r))
for name, lab, r in wells:
    b = r.bbox()
    print(f"{name}: NWell.pin label(s) {lab}, bbox [{b.left*dbu:.3f}, {b.bottom*dbu:.3f}, "
          f"{b.right*dbu:.3f}, {b.top*dbu:.3f}] um, {r.count()} merged shape(s)")
print(f"top cell merged NWell shapes: {db.Region(t.begin_shapes_rec(NW)).merged().count()}")
bad = 0
reach = int(1000 / dbu)
print(f"different-net NWell pairs (NW.b1 >= {nw_b1:.2f} um):")
for i in range(len(wells)):
    for j in range(i + 1, len(wells)):
        a, b = wells[i], wells[j]
        if a[1] == b[1]:
            continue
        ep = a[2].separation_check(b[2], reach, False, db.Metrics.Euclidian)
        d = min((e.distance() for e in ep.each()), default=None)
        dist = d * dbu if d is not None else float("inf")
        ok = dist >= nw_b1
        bad += not ok
        print(f"  {a[0]} {a[1]} <-> {b[0]} {b[1]}: {dist:.3f} um {'ok' if ok else 'VIOLATION'}")
sys.exit(1 if bad else 0)
