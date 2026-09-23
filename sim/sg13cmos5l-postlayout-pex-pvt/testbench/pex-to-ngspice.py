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
   commands (`.SUBCKT`, `.ENDS`, `.GLOBAL`) are never matched. This is a
   tooling gap, not a modelling choice -- filed upstream as
   klayout-tools#2145 (see the record's section 7, "Friction encountered").

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
   modelling choice -- already filed upstream as klayout-tools#1157, whose
   scope condition this pass narrowed by confirmation comment (the 3-node R
   card is emitted with `--pdk` supplied too). See the record's section 7,
   "Friction encountered".

3. **Extracted MOM-cap device cards -> the PDK subckt call's own parameter
   form.** `klt extract` emits a drawn `cap_cmomi`/`cap_cmomf` instance as

       XD_$1 NZ__t0 VSS__t0 cap_cmomi PARAMS: W=40 L=40

   -- bare micron numbers behind a `PARAMS:` keyword. The PDK's own model
   interface is `.subckt cap_cmomi PLUS MINUS w=5e-6 l=5e-6 ...` (SI
   meters), so with `.option scale=1` ngspice reads `W=40` as 40 METERS:
   the capacitance comes out 1e12x oversize, which is silent at DC (a cap
   blocks DC regardless) and only shows up as an effectively-shorted cap
   in AC. The same extractor's resistor cards carry proper unit suffixes
   (`L=810U W=0.6U`), so the cap-card form is an inconsistency, not a
   convention -- filed upstream as klayout-tools#2355. Until it closes,
   the card is rewritten to the identical device call the design's own
   schematic netlist writes for the same device class

       XD_$1 NZ__t0 VSS__t0 cap_cmomi w=40u l=40u

   (`mmin`/`mmax`/`feed`/`subblock`/`mm_ok` are left to the subckt's own
   defaults, which equal the design netlist's values for every instance
   this flow draws; `m=1` likewise). Only the parameter SPELLING changes:
   the geometry numbers are the drawn ones, verbatim, with a `u` appended
   exactly the way transform 2 lowercases and passes through the resistor
   geometry. This is a tooling gap, not a modelling choice -- see the
   record's "Friction encountered" section.

4. **Nothing else.** Every `M`/`X` device line, every parasitic `R*__t*` /
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

# `X<name> <a> <b> <model> PARAMS: W=<num> L=<num>`  (klt's extracted
# MOM-cap device card). The geometry arrives as a bare micron number; the
# PDK subckt interfaces take SI meters, so the rewrite appends the `u`
# suffix (klayout-tools#2355). Cards whose W/L already carry a unit suffix
# (a future fixed klt) fall through untouched.
_CAPC = re.compile(
    r"^X(?P<name>\S+)\s+(?P<a>\S+)\s+(?P<b>\S+)\s+"
    r"(?P<model>cap_cmo\w+)\s+PARAMS:\s+"
    r"W=(?P<w>[0-9.]+)\s+L=(?P<l>[0-9.]+)\s*$"
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
    capc = 0
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
        else:
            m = _CAPC.match(ln)
            if m:
                capc += 1
                ln = "X{name} {a} {b} {model} w={w}u l={l}u".format(
                    name=m.group("name"),
                    a=m.group("a"),
                    b=m.group("b"),
                    model=m.group("model"),
                    w=m.group("w"),
                    l=m.group("l"),
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
        "%d MOM-cap device cards respelled to the PDK subckt parameter form "
        "(klayout-tools#2355), "
        "%d parasitic R + %d parasitic C cards passed through unchanged"
        % (src, dst, dots, res3, capc, after[0], after[1]),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
