#!/usr/bin/env python3
"""Generate the klt sim requests and PFD-only testbenches for
sim/sg13g2-pfd-reset-parity (issue #283).  Pure text generation; runs nothing.
Writes ../requests/*.json and tb_*.sp."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
REQ = os.path.join(HERE, "..", "requests")
# image-baked on the batch runner (a host path is refused for backend 'batch')
OSDI = [f"$PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/osdi/{o}.osdi"
        for o in ("psp103", "psp103_nqs", "mosvar", "r3_cmc")]
VDD, TREF, TOFF = 3.3, 50e-9, 5e-9   # 20 MHz, REF/FB 5 ns (10 % of period) apart
TSTOP, TAVG0 = 500e-9, 200e-9

TB = """* sg13g2-pll :: sim/sg13g2-pfd-reset-parity (issue #283): PFD-only lead/lag check.
* DUT: ../netlist-snapshots/pfd_{variant}.spice ({what}).
* {case}: {desc}.  Same period, fixed per-cycle offset of {toff:g} s.
.include ../netlist-snapshots/pfd_{variant}.spice
Vdd vdd 0 dc {vdd}
Vref ref 0 pulse(0 {vdd} {rd:g} 100p 100p {th:g} {tref:g})
Vfb  fb  0 pulse(0 {vdd} {fd:g} 100p 100p {th:g} {tref:g})
XPFD ref fb up dn vdd 0 pfd
.end
"""
CASES = {"reflead": (0, TOFF, "REF leads FB (FB must speed up: UP should dominate)"),
         "fblead": (TOFF, 0, "FB leads REF (FB must slow down: DN should dominate)")}
VARIANTS = {"before": "origin/main as of 26247c1, 2-stage reset chain",
            "after": "regenerated design/netlist/pfd.spice, 3-stage reset chain"}

def request(variant, case, tb, backend, process, temps):
    return {
        "engine": "ngspice", "backend": backend,
        "netlist": f"../testbench/{tb}",
        "models": {"pdk": "ihp-sg13g2", "lib": "libs.tech/ngspice/models/cornerMOShv.lib"},
        "corners": {"process": process, "temperature_c": temps},
        "analysis": {"kind": "tran", "args": f"100p {TSTOP:g}"},
        "measurements": [
            {"name": "up_avg", "spice": f".meas tran up_avg avg v(up) from={TAVG0:g} to={TSTOP:g}"},
            {"name": "dn_avg", "spice": f".meas tran dn_avg avg v(dn) from={TAVG0:g} to={TSTOP:g}"}],
        "options": {"osdi_preload": OSDI, "timeout_s": 600, "keep_artifacts": True},
    }

for variant, what in VARIANTS.items():
    for case, (rd, fd, desc) in CASES.items():
        tb = f"tb_{variant}_{case}.sp"
        with open(os.path.join(HERE, tb), "w") as f:
            f.write(TB.format(variant=variant, what=what, case=case, desc=desc, toff=TOFF,
                              vdd=VDD, rd=rd, fd=fd, th=TREF / 2 - 100e-12, tref=TREF))
        with open(os.path.join(REQ, f"{variant}_{case}_pvt.request.json"), "w") as f:
            json.dump(request(variant, case, tb, "batch", ["mos_tt", "mos_ss", "mos_ff"], [-40, 27, 125]), f, indent=2)
            f.write("\n")
