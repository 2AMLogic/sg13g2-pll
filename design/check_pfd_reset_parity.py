#!/usr/bin/env python3
"""Static guard: reset-chain parity of the committed pfd netlists (#297).

The PFD reset must be AND(UP, DN): a NAND2 followed by an ODD number of
inverters, with the result on the R pin of both srlatch instances. An even
count makes the PFD blind to lead vs. lag (#56 / #71 for the SG13CMOS5L port,
#283 / #284 for the top-level pfd). This walks the structure from the file's
own ``.subckt`` headers; no instance names are hard-coded. Stdlib only.

Usage: check_pfd_reset_parity.py [netlist ...]   (default: both committed)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_NETLISTS = [
    HERE / "netlist" / "pfd.spice",
    HERE / "sg13cmos5l" / "netlist" / "pfd.spice",
]
INVERTERS = ("inv_hv", "inv2x_hv")


class ParityError(Exception):
    pass


def parse(path):
    """Return {subckt: (ports, [(inst, nets, cell)])} with '+' joined."""
    lines = []
    for raw in Path(path).read_text().splitlines():
        if raw.startswith("+") and lines:
            lines[-1] += " " + raw[1:]
        else:
            lines.append(raw)
    subckts, cur = {}, None
    for line in lines:
        tok = line.split()
        if not tok or tok[0].startswith("*"):
            continue
        head = tok[0].lower()
        if head == ".subckt":
            cur = tok[1]
            subckts[cur] = ([t for t in tok[2:] if "=" not in t], [])
        elif head == ".ends":
            cur = None
        elif cur is not None and tok[0][0] in "Xx":
            body = [t for t in tok[1:] if "=" not in t]
            subckts[cur][1].append((tok[0], body[:-1], body[-1]))
    return subckts


def pins(subckts, cell, inst):
    """Map pin name -> net for one instance, using the header in this file."""
    if inst[2] != cell and inst[2] not in subckts:
        raise ParityError(f"{inst[0]}: subckt {inst[2]} not defined in file")
    ports = subckts[inst[2]][0]
    if len(ports) != len(inst[1]):
        raise ParityError(f"{inst[0]}: {len(inst[1])} nets for {len(ports)} pins")
    return dict(zip(ports, inst[1]))


def consumed_nets(sub, inst):
    """Nets on the input pins of one instance (outputs excluded)."""
    outs = {"nand2_hv": ("Y",), "inv_hv": ("Y",), "inv2x_hv": ("Y",),
            "srlatch": ("Q", "QB"), "edgedet": ("OUT",)}.get(inst[2], ())
    return [n for pin, n in pins(sub, inst[2], inst).items()
            if pin not in outs and pin not in ("VDD", "VSS")]


def check(path):
    """Raise ParityError on a bad reset chain; return the inverter count."""
    sub = parse(path)
    if "pfd" not in sub:
        raise ParityError("no .subckt pfd")
    ports, insts = sub["pfd"]
    for need in ("UP", "DN"):
        if need not in ports:
            raise ParityError(f"pfd has no {need} port")

    latches = [i for i in insts if i[2] == "srlatch"]
    if len(latches) != 2:
        raise ParityError(f"expected 2 srlatch instances, found {len(latches)}")
    reset_nets = {pins(sub, "srlatch", i)["R"] for i in latches}
    if len(reset_nets) != 1:
        raise ParityError(f"srlatch R pins on different nets: {sorted(reset_nets)}")
    reset = reset_nets.pop()

    nands = [i for i in insts if i[2] == "nand2_hv"]
    cand = [i for i in nands
            if {pins(sub, "nand2_hv", i)["A1"], pins(sub, "nand2_hv", i)["A2"]}
            == {"UP", "DN"}]
    if len(cand) != 1:
        raise ParityError(
            f"expected exactly 1 nand2_hv with inputs UP and DN, found {len(cand)}")
    net = pins(sub, "nand2_hv", cand[0])["Y"]

    count, seen = 0, {net}
    while net != reset:
        # Consumers = instances with an INPUT pin on this net. Output pins
        # (Y of the driver, Q/QB of latches) are not loads.
        users = [i for i in insts if net in consumed_nets(sub, i)]
        if len(users) != 1 or users[0][2] not in INVERTERS:
            desc = ", ".join(f"{u[0]}({u[2]})" for u in users) or "nothing"
            raise ParityError(
                f"reset chain from net {net} does not reach {reset} through "
                f"single inverters; net {net} drives {desc}")
        p = pins(sub, users[0][2], users[0])
        if p["A"] != net:
            raise ParityError(f"{users[0][0]} input is not on net {net}")
        net = p["Y"]
        count += 1
        if net in seen:
            raise ParityError(f"reset chain loops at net {net}")
        seen.add(net)
    if count % 2 == 0:
        raise ParityError(
            f"even inverter count ({count}) between NAND2(UP,DN) and {reset}: "
            f"reset = NAND(UP,DN) cannot tell lead from lag (#56, #283); need odd")
    return count


def main(argv):
    paths = [Path(a) for a in argv] or DEFAULT_NETLISTS
    rc = 0
    for p in paths:
        try:
            n = check(p)
            print(f"OK   {p}: {n} inverters after NAND2(UP,DN), reset=AND(UP,DN)")
        except (ParityError, OSError) as e:
            print(f"FAIL {p}: {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
