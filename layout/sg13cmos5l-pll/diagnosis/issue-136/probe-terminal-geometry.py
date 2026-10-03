#!/usr/bin/env python3
"""Issue #136 geometry probe: the two facts `klt drc` cannot see.

For each `pll_lock_detector.gds` named on the command line, report

* every `Via1` (19/0) that does not sit inside `Metal1` (8/0) -- a riser
  landing on no lower metal. The curated `sg13cmos5l` deck's
  `metal1.enclosing.via1.1` only flags a via that *partially* overlaps
  Metal1 (klayout-tools#2726), so a via on nothing passes DRC clean;
* the source/drain `Cont` (6/0) count on the `w=0.25u` group cell
  `lock_detector_nfet_w0p25_l16` -- the deck reads no `Cont` rule at all.

Run with the pinned venv's interpreter (it needs `klayout.db`):

    layout/.venv/bin/python probe-terminal-geometry.py \
        ../../reports/20260923-020931-a95a887-dirty/pll_lock_detector.gds \
        ../../reports/20261003-183059-dc5644a/pll_lock_detector.gds
"""

from __future__ import annotations

import sys

import klayout.db as kdb


def region(layout: kdb.Layout, cell: kdb.Cell, layer: int, datatype: int) -> kdb.Region:
    index = layout.find_layer(layer, datatype)
    if index is None:
        return kdb.Region()
    return kdb.Region(cell.begin_shapes_rec(index))


def probe(path: str) -> None:
    layout = kdb.Layout()
    layout.read(path)
    top = layout.top_cell()
    via1 = region(layout, top, 19, 0)
    metal1 = region(layout, top, 8, 0)
    orphans = via1.not_inside(metal1)
    print(f"{path}")
    print(f"  Via1 total: {via1.count()}, not inside Metal1: {orphans.count()}")
    for polygon in orphans.each():
        box = polygon.bbox()
        print(f"    orphan Via1 at ({box.left * layout.dbu:.3f}, {box.bottom * layout.dbu:.3f}) um")

    cell = layout.cell("lock_detector_nfet_w0p25_l16")
    if cell is None:
        print("  no lock_detector_nfet_w0p25_l16 cell")
        return
    cont = region(layout, cell, 6, 0)
    gatpoly = region(layout, cell, 5, 0)
    activ = region(layout, cell, 1, 0)
    sd_cont = (cont & activ).count()
    gate_cont = (cont & gatpoly).count()
    print(
        f"  lock_detector_nfet_w0p25_l16: Cont on Activ (source/drain/tap) = {sd_cont}, "
        f"Cont on GatPoly (gate pad) = {gate_cont}"
    )


def main(argv: list[str]) -> int:
    for path in argv:
        probe(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
