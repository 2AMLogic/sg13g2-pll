#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-lock-detector-window (issue #38, Part of #16)

Write a MOM-band variant of the frozen ``lock_detector`` netlist snapshot.

WHY THIS EXISTS.  ``cap_cmomi`` has no corner, mismatch or statistical spread
in the installed PDK: ``cornerCAP.lib``'s own header states that every
corner/mismatch/stat section maps to the SAME nominal model, and
``cap_cmomi.lib``'s header states the coefficients are transferred from SG13G2
and "NOT YET VALIDATED ON ihp-sg13cmos5l SILICON".  So the +/-20%
MOM-model-uncertainty band that
``spec/decision-records/DR-003-sg13cmos5l-port-readiness.md`` Finding 2
requires cannot be swept by re-simulating the compact model -- there is no
knob on it.

METHODOLOGY PRECEDENT -- followed literally.
``sim/sg13cmos5l-loop-bandwidth-pm/testbench/tb_loop_ac_lumped.sp.tmpl``
documents the workaround issue #27 used at the loop level: *extract the real
value, then re-inject it as an ideal element scaled by the band, and
cross-check the nominal point against the real subckt.*  This script produces
exactly those variants of the DUT:

  ``real``          the frozen snapshot, byte for byte.  This is the committed
                    design and the cross-check reference.
  ``ideal <frac>``  every ``cap_cmomi`` instance commented out and replaced by
                    an ideal linear capacitor of ``(1 + frac) * C_nominal``,
                    with ``C_nominal`` measured per geometry by
                    ``tb_extract_c.sp.tmpl``.  ``frac = 0`` is the control
                    point that isolates ideal-vs-real modelling error from the
                    band itself; ``frac = -0.20`` / ``+0.20`` are the band.

The two instances rewritten are exactly the two ``cap_cmomi`` sites DR-003
Finding 2's own three-instance list (``loop_filter.XC1``/``XC2``,
``vco.XCDECAP``) does NOT name, and which ``design/README.md`` records as
"not covered by this update; their hysteresis-window sensitivity remains
open":

    lock_detector.XCW        w=8u l=8u m=1   -- the integrating-node cap
    lock_detector.XDW.XC1    w=4u l=4u m=2   -- the comparator-window cap

WHY NOT A PARALLEL DELTA CAPACITOR (what
``sim/sg13cmos5l-loop-filter-momcap/`` did).  That record's DUT is a passive
AC network, where a negative delta capacitor for the low side of the band is
numerically harmless.  Here the caps sit on switching nodes inside an
inverter chain, and a negative capacitor on ``delaywin_hv``'s output node
makes ngspice's transient fail outright -- "Timestep too small ... trouble
with node xw.d2" at a quiescent time point, i.e. a solver instability, not a
circuit result.  Replacing the instance wholesale keeps every element's
capacitance positive at every band point.  The cost of doing it this way is
that the ideal element drops ``cap_cmomi``'s substrate shunt and its RF
equivalent network, which is precisely what the ``ideal frac = 0`` control
point measures.

MOM_FRAC is applied with the same sign and magnitude to BOTH instances,
representing a *systematic* model/coefficient bias -- the kind of error a
wrong density-transfer coefficient would cause -- not independent
per-instance mismatch, which ``cap_cmomi`` does not characterise either and
which this record does not attempt to bound.

The frozen snapshot itself is never modified; variants are written to a
scratch directory by ``run.sh``.

Usage:
    mom_inject.py <snapshot.spice> <out.spice> real
    mom_inject.py <snapshot.spice> <out.spice> ideal <frac> <C_XCW> <C_XC1>
"""

import sys

# instance name -> which extracted nominal capacitance it takes
INSTANCES = {"XCW": "c_xcw", "XC1": "c_xc1"}


def to_ideal(src_text, frac, c_xcw, c_xc1):
    """Comment out each cap_cmomi instance and emit an ideal cap in its place."""
    nominal = {"c_xcw": c_xcw, "c_xc1": c_xc1}
    seen = set()
    out = []
    for line in src_text.splitlines():
        parts = line.split()
        name = parts[0] if parts else ""
        if (len(parts) >= 4 and name in INSTANCES
                and parts[3].lower() == "cap_cmomi"):
            plus, minus = parts[1], parts[2]
            val = (1.0 + frac) * nominal[INSTANCES[name]]
            out.append("* MOM band {:+.0%}: cap_cmomi instance {} replaced by "
                       "an ideal linear cap".format(frac, name))
            out.append("* (original instance kept below, commented out, so the "
                       "geometry stays visible)")
            out.append("*" + line)
            out.append("Cideal_{} {} {} {:.6e}".format(name, plus, minus, val))
            seen.add(name)
        else:
            out.append(line)
    missing = set(INSTANCES) - seen
    if missing:
        raise SystemExit("mom_inject: cap_cmomi instance(s) not found in "
                         "snapshot: " + ", ".join(sorted(missing)))
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__.strip())
    src, dst, mode = sys.argv[1:4]
    with open(src) as fh:
        text = fh.read()
    if mode == "real":
        result = text
    elif mode == "ideal":
        if len(sys.argv) != 7:
            raise SystemExit("mom_inject: ideal mode needs <frac> <C_XCW> "
                             "<C_XC1>")
        frac, c_xcw, c_xc1 = (float(x) for x in sys.argv[4:7])
        result = to_ideal(text, frac, c_xcw, c_xc1)
    else:
        raise SystemExit("mom_inject: mode must be 'real' or 'ideal'")
    with open(dst, "w") as fh:
        fh.write(result)


if __name__ == "__main__":
    main()
