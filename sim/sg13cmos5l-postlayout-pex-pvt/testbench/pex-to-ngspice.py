#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/pex-to-ngspice.py
(issue #30, Part of #16 -- post-layout PEX + PVT re-simulation)

Makes a `klt extract --parasitics --pdk ihp-sg13cmos5l` netlist parseable by
ngspice, WITHOUT touching a single parasitic value.

Exactly three mechanical transforms are applied, and the script reports how
many times each fired so the record can state what was changed:

1. **Hierarchical dots in net names -> underscore.** `klt` names a net that
   came from a sub-instance `XBIAS.n2s`; ngspice reserves `.` as its own
   hierarchy separator, so `v(xvco.XBIAS.n2s)` is unresolvable and the raw
   name is a parse hazard. `XBIAS.n2s` -> `XBIAS_n2s`. Applied only where a
   dot sits between two identifier characters whose left side starts with a
   letter/underscore, so numeric literals (`L=0.28U`, `AS=0.8P`) and dot
   commands (`.SUBCKT`, `.ENDS`, `.GLOBAL`) are never matched.

2. **Three-terminal resistor cards -> the PDK's own resistor subcircuit
   call.** `klt` binds MOS devices to the PDK subcircuits when `--pdk` is
   given, but emits the deck's `rppd`/`rhigh` resistors as raw SPICE `R`
   cards carrying a THIRD (bulk) node:

       R$39 n2s__t0 GND__t0 GND__t15 7800 rppd L=30U W=1U

   ngspice's `R` card takes two nodes, so that line is unparseable. It is
   rewritten to the identical device call the design's own schematic netlist
   writes for the same device (`design/sg13cmos5l/netlist/vco.spice` line 43,
   `XRS n2s VSS sub! rppd w=1u l=30u m=1 b=0`):

       X$39 n2s__t0 GND__t0 GND__t15 rppd w=1u l=30u m=1 b=0

   Same three terminals, same model, same W/L -- only the card type changes.
   The extracted 7800-ohm VALUE is dropped because the PDK subcircuit
   computes its own resistance from W/L; that is the same binding the
   schematic-level campaign already simulates, so the two sides of the
   comparison stay on the same resistor model. This is a tooling gap, not a
   modelling choice -- filed upstream (see the record's "Friction filed
   upstream" section).

3. **Nothing else.** Every `M`/`X` device line, every parasitic `R*__t*` /
   `C*` card, every value, is passed through byte-for-byte apart from
   transform 1's renaming. The script asserts this: it counts parasitic R/C
   cards before and after and fails if the totals move.

Usage:  pex-to-ngspice.py <in.pex.spice> <out.spice>
"""

from __future__ import annotations

import re
import sys

# A dot between two identifier characters, left side starting with a letter or
# underscore: matches `XBIAS.n2s`, never `0.28U` and never `.SUBCKT`.
_HIER_DOT = re.compile(r"(?<![\w.])([A-Za-z_][\w$]*)((?:\.[A-Za-z_][\w$]*)+)")

# `R<name> <n+> <n-> <nbulk> <value> <model> L=<l> W=<w>`  (klt's 3-terminal
# resistor card). Two-terminal parasitic R cards (`R$t0 a b 1.57`) have no
# model name and are deliberately NOT matched.
_RES3 = re.compile(
    r"^R(?P<name>\S+)\s+(?P<a>\S+)\s+(?P<b>\S+)\s+(?P<bulk>\S+)\s+"
    r"(?P<value>[-+0-9.eE]+)\s+(?P<model>[A-Za-z]\w*)\s+"
    r"L=(?P<l>\S+)\s+W=(?P<w>\S+)\s*$"
)


def _dedot(line: str) -> tuple[str, int]:
    hits = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal hits
        hits += 1
        return m.group(1) + m.group(2).replace(".", "_")

    return _HIER_DOT.sub(sub, line), hits


def _count_parasitics(lines: list[str]) -> tuple[int, int]:
    r = sum(1 for ln in lines if re.match(r"^R\S*\s+\S+\s+\S+\s+[-+0-9.eE]+\s*$", ln))
    c = sum(1 for ln in lines if ln[:1] == "C")
    return r, c


def main() -> int:
    src, dst = sys.argv[1], sys.argv[2]
    with open(src) as fh:
        lines = [ln.rstrip("\n") for ln in fh]

    before = _count_parasitics(lines)

    out: list[str] = []
    dots = 0
    res3 = 0
    for ln in lines:
        if ln.startswith("*"):
            out.append(ln)
            continue
        m = _RES3.match(ln)
        if m:
            res3 += 1
            ln = (
                "X{name} {a} {b} {bulk} {model} w={w} l={l} m=1 b=0".format(
                    name=m.group("name"),
                    a=m.group("a"),
                    b=m.group("b"),
                    bulk=m.group("bulk"),
                    model=m.group("model"),
                    w=m.group("w").lower(),
                    l=m.group("l").lower(),
                )
            )
        ln, hits = _dedot(ln)
        dots += hits
        out.append(ln)

    after = _count_parasitics(out)
    if before != after:
        sys.exit(
            "FATAL: parasitic card count changed (R,C) %s -> %s -- refusing to "
            "write a netlist whose parasitics this script altered." % (before, after)
        )

    with open(dst, "w") as fh:
        fh.write("\n".join(out) + "\n")

    print(
        "pex-to-ngspice: %s -> %s: %d hierarchical names de-dotted, "
        "%d 3-terminal resistor cards rebound to PDK subcircuits, "
        "%d parasitic R + %d parasitic C cards passed through unchanged"
        % (src, dst, dots, res3, after[0], after[1]),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
