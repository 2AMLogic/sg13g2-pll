#!/usr/bin/env python3
"""Flatten a hierarchical design netlist into one `.subckt` for `klt pex`.

Usage: flatten-schematic.py SRC.spice TOP_SUBCKT NEW_NAME PIN,PIN,... > out.sp

`klt pex` flags a `model_mismatch` when the schematic leg instantiates user
subckts the flat extracted netlist does not, so the schematic leg is flattened
down to the PDK leaf devices (MOS, `rppd`/`rhigh`, `cap_cmomi`), keeping every
device card verbatim. Instance names are hierarchical (`Xa.Xb.XMP`) with `.`
mapped to `_`. Internal nets are prefixed by their instance path; pins and
ground are mapped through; the schematic's `sub!` global is mapped to `vsubs`
(the extracted netlist's own substrate global). No other edit is made.
"""
import re, sys

src, top, new, pins = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
subckts, cur = {}, None
for raw in open(src).read().replace("\n+", " ").splitlines():
    line = raw.strip()
    if not line or line.startswith("*"):
        continue
    low = line.lower()
    if low.startswith(".subckt"):
        t = line.split(); cur = t[1]; subckts[cur] = (t[2:], []); continue
    if low.startswith(".ends"):
        cur = None; continue
    if cur and not line.startswith("."):
        subckts[cur][1].append(line.split())

LEAF = ("sg13_hv_nmos", "sg13_hv_pmos", "rppd", "rhigh", "cap_cmomi")
GLOBALS = {"sub!": "vsubs"}  # schematic substrate global -> the extracted netlist's own `.GLOBAL vsubs`
out = []

def expand(name, ports, prefix, netmap):
    for t in subckts[name][1]:
        inst = t[0]
        if inst[0].upper() == "X":
            # model is the first token after the nets that names a subckt or leaf
            k = next(i for i in range(1, len(t)) if t[i] in subckts or t[i] in LEAF)
            nets, model, rest = t[1:k], t[k], t[k + 1:]
            mapped = [n if n == "0" else GLOBALS.get(n) or netmap.get(n, prefix + n) for n in nets]
            if model in subckts:
                sub_ports = subckts[model][0]
                expand(model, sub_ports, prefix + inst + "_", dict(zip(sub_ports, mapped)))
            else:
                out.append(" ".join([("X" + prefix + inst[1:]).rstrip("_")] + mapped + [model] + rest))
        else:
            raise SystemExit("unsupported card in %s: %s" % (name, " ".join(t)))

top_ports = subckts[top][0]
assert set(top_ports) <= set(pins), (top_ports, pins)  # extra pins expose top-level internal nets
expand(top, top_ports, "", {p: p for p in top_ports})
print("* flattened from %s subckt %s by flatten-schematic.py (device cards verbatim)" % (src, top))
print(".subckt %s %s" % (new, " ".join(pins)))
print("\n".join(out))
print(".ends %s" % new)
