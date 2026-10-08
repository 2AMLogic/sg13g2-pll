#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/cpdiag_build.py
(issue #150, Part of #16)

Builds the block bundle for one RECORD-006 diagnostic variant.  Everything is
derived from the FROZEN snapshots in ../netlist-snapshots (never from
design/); the committed `cp`/`pfd` are not modified.  The non-cp/pfd blocks
(vco XCDECAP strip, loop_filter ideal caps + R1 x20, lock_detector ideal caps)
reproduce run_closed_loop_cascbias.sh's own derivation exactly.

usage: cpdiag_build.py VARIANT SNAP_DIR WORK_DIR

VARIANT:
  control_hist  frozen cp_cascbias + frozen pfd, no edits (RECORD-005 deck)
  control_probe same netlists as control_hist (the probe is a testbench
                0 V source, see tb_pll_cpdiag.sp.tmpl)
  ideal_sw      (a) XSWO/XSWD of both legs -> ideal voltage-controlled
                switches; mirrors, cascode bias, inverters, XBUF untouched
  ideal_dump    (b) XBUF (cp_dumpbuf) removed, VDUMP driven by an ideal unity
                VCVS copy of VOUT; real switches and mirrors untouched
  ideal_dump_ofs (b') XBUF removed, VDUMP driven by an ideal unity VCVS
                that KEEPS the real buffer's measured static level shift
                (VDUMP = VOUT - DUMP_OFS).  Discriminates the dump node's DC
                level (charge sharing) from the buffer's dynamics/impedance.
  ideal_both    (a)+(b) together (open-loop pulse bench only)
  reset_narrow  (c) pfd reset chain 3 -> 1 inverter stages
  reset_wide    (c) pfd reset chain 3 -> 5 inverter stages

Writes WORK/pll_blocks_cpdiag.spice, WORK/cpdiag_models.inc and
WORK/variant.diff (unified diff of the edited cp/pfd vs the snapshot).
"""
import difflib
import re
import sys

VT = 1.65      # switch control threshold, V (VDD/2 at VDD = 3.3 V)
VH = 0.1       # ngspice switch hysteresis half-width, V
RON = 1e3      # on resistance, ohm
ROFF = 1e12    # off resistance, ohm
# Static VOUT - VDUMP of the REAL cp_dumpbuf, measured by the control open-loop
# pulse bench (cppulse_summary_control_probe.json: meas.vdump_quiet at
# VOUT = 2.387 V, ngspice-42, mos_tt, 27 C).
DUMP_OFS = 0.937396  # = 2.387 - 1.449604

C1_F = 1.691196e-12
C2_F = 1.001529e-13


def main(variant, snap, work):
    def read(name):
        with open(f"{snap}/{name}") as f:
            return f.read()

    cp = read("cp_cascbias.spice")
    assert "XMBP" in cp and "XMCN" in cp
    pfd = read("pfd.spice")
    cp0, pfd0 = cp, pfd
    models = "* no extra models for this variant\n"

    if variant in ("control_hist", "control_probe"):
        pass
    elif variant in ("ideal_sw", "ideal_both"):
        reps = [
            (r"(?m)^XSWO VOUT UPB sw VDD sg13_hv_pmos .*$", "SSWO sw VOUT VDD UPB swp_ideal"),
            (r"(?m)^XSWD VDUMP UP sw VDD sg13_hv_pmos .*$", "SSWD sw VDUMP VDD UP swp_ideal"),
            (r"(?m)^XSWO VOUT DN sw VSS sg13_hv_nmos .*$", "SSWO sw VOUT DN VSS swn_ideal"),
            (r"(?m)^XSWD VDUMP DNB sw VSS sg13_hv_nmos .*$", "SSWD sw VDUMP DNB VSS swn_ideal"),
        ]
        for pat, rep in reps:
            cp, n = re.subn(pat, rep, cp)
            assert n == 1, pat
        models = (f".model swp_ideal sw vt={VT} vh={VH} ron={RON} roff={ROFF}\n"
                  f".model swn_ideal sw vt={VT} vh={VH} ron={RON} roff={ROFF}\n")
    if variant in ("ideal_dump", "ideal_both"):
        cp, n = re.subn(r"(?m)^XBUF VOUT IBN VDUMP VDD VSS cp_dumpbuf$",
                        "EDUMP VDUMP VSS VOUT VSS 1", cp)
        assert n == 1
    if variant == "ideal_dump_ofs":
        cp, n = re.subn(r"(?m)^XBUF VOUT IBN VDUMP VDD VSS cp_dumpbuf$",
                        f"EDUMP VDUMP vdofs VOUT VSS 1\nVDOFS vdofs VSS dc {-DUMP_OFS:.6f}", cp)
        assert n == 1
    if variant in ("reset_narrow", "reset_wide"):
        old = ("XI1 reset_raw reset_d1 VDD VSS inv_hv\n"
               "XI1B reset_d1 reset_d2 VDD VSS inv_hv\n"
               "XI2 reset_d2 reset VDD VSS inv2x_hv\n")
        assert old in pfd
        if variant == "reset_narrow":
            new = "XI2 reset_raw reset VDD VSS inv2x_hv\n"
        else:
            new = ("XI1 reset_raw reset_d1 VDD VSS inv_hv\n"
                   "XI1B reset_d1 reset_d2 VDD VSS inv_hv\n"
                   "XI1C reset_d2 reset_d3 VDD VSS inv_hv\n"
                   "XI1D reset_d3 reset_d4 VDD VSS inv_hv\n"
                   "XI2 reset_d4 reset VDD VSS inv2x_hv\n")
        pfd = pfd.replace(old, new)
    if variant not in ("control_hist", "control_probe", "ideal_sw", "ideal_dump", "ideal_both",
                       "ideal_dump_ofs", "reset_narrow", "reset_wide"):
        sys.exit(f"unknown variant {variant}")

    diff = "".join(difflib.unified_diff(
        cp0.splitlines(True), cp.splitlines(True), "snapshot/cp_cascbias.spice", "variant/cp", n=1))
    diff += "".join(difflib.unified_diff(
        pfd0.splitlines(True), pfd.splitlines(True), "snapshot/pfd.spice", "variant/pfd", n=1))

    vco = read("vco.spice")
    vco = re.sub(r"(?m)^XCDECAP", "*XCDECAP", vco)
    assert "*XCDECAP" in vco

    def sub_cap(text, xname, n1, n2, value):
        pat = re.compile(rf"(?m)^X{xname}\s+{n1}\s+{n2}\s+cap_cmomi\b.*$")
        new, n = pat.subn(f"C{xname} {n1} {n2} {value:.6e}", text)
        assert n == 1
        return new

    lf = read("loop_filter.spice")
    lf = sub_cap(lf, "C1", "NZ", "VSS", C1_F)
    lf = sub_cap(lf, "C2", "VCTRL", "VSS", C2_F)
    lf2 = re.sub(r"(?m)^(XR1\s+VCTRL\s+NZ\s+sub!\s+rppd\s+w=4u\s+l=)120u", r"\g<1>2400u", lf)
    assert lf2 != lf

    density = C2_F / (10e-6 * 10e-6)
    ld = read("lock_detector.spice")
    ld = sub_cap(ld, "CW", "VWIN", "VSS", density * (8e-6 * 8e-6))
    ld = sub_cap(ld, "C1", "OUT", "VSS", density * (4e-6 * 4e-6) * 2)

    with open(f"{work}/pll_blocks_cpdiag.spice", "w") as f:
        f.write(pfd + "\n" + cp + "\n" + lf2 + "\n" + vco + "\n" + ld)
    with open(f"{work}/cpdiag_models.inc", "w") as f:
        f.write(models)
    with open(f"{work}/variant.diff", "w") as f:
        f.write(diff)


if __name__ == "__main__":
    main(*sys.argv[1:4])
