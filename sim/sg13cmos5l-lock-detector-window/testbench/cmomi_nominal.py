#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-lock-detector-window (issue #52, Part of #16)

Nominal low-frequency capacitance of one ``cap_cmomi`` instance, evaluated
directly from the installed model's OWN closed-form expression.

WHY THIS EXISTS -- a host-local PDK-install defect, not a modelling choice.
``../testbench/tb_extract_c.sp.tmpl`` measures this quantity by simulating the
compact model, and that is still the preferred path: ``run.sh`` uses it
whenever ngspice can load ``cap_cmomi.osdi``, and only falls back here when it
cannot.  On an **arm64 macOS** host it cannot.  Of the six OSDI objects in
``$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/``, four (``psp103``,
``psp103_nqs``, ``mosvar``, ``r3_cmc``) are gitignored build products
symlinked from the sibling ``ihp-sg13g2`` tree and are rebuilt locally for
whatever host they are installed on -- they are arm64 Mach-O here and load
fine, which is why every MOS and every ``rhigh`` measurement in this record IS
a real compact-model simulation.  The two MoM-capacitor objects
(``cap_cmomi.osdi``, ``cap_cmomf.osdi``) are instead **tracked files shipped
prebuilt** by the PDK (see ``$PDK_ROOT/ihp-sg13cmos5l/Makefile``'s own
``test-gnucap`` guard: *"unlike the OSDI above these two are tracked files, so
a pull is the fix rather than a build"*), and the shipped binaries are
x86-64 ELF.  ngspice on arm64 reports ``slice is not valid mach-o file`` and
every ``cap_cmomi`` instance then fails with ``Unable to find definition of
model xcap:cap_cmomi_mod``.  Rebuilding them needs ``openvaf``/``openvaf-r``,
which has no arm64-macOS release binary.

WHAT THIS COMPUTES.  ``cap_cmomi.va``'s own low-frequency capacitance, i.e.
the ``Cmain`` the model builds in its ``@(initial_model)`` block, transcribed
term for term from
``$PDK_ROOT/ihp-sg13cmos5l/libs.tech/verilog-a/cap_cmomi/cap_cmomi.va``::

    ax          = floor(l_um/0.84 + 1e-6)        , clamped >= 1
    ay          = floor(w_um/0.89 + 1e-6)        , clamped >= 2
    active_area = ax * ay * 0.84 * 0.89                        [um^2]
    pad_len     = ay * 0.89 + 0.42                             [um]
    density[N]  = 0.55 (N<=2) | 0.82 (N==3) | 1.09 (N>=4)      [fF/um^2]
                  keyed by the metal layer count N = mmax - mmin + 1
    Cfeed       = 0.152*pad_len              (feed = double)   [fF]
                  0.1625*pad_len + 0.0916    (feed = same)
                  0                          (feed = none)
    C           = m * (density*active_area + Cfeed) * 1e-15    [F]

This is the *whole* low-frequency capacitance of the model: the remaining
elements of ``cap_cmomi``'s equivalent circuit (Lskin/Rskin, Lcore, Rseries,
and the Cox/Rsub/Csub substrate shunt) are RF branches with no effect at the
sub-GHz rates this record's transients run at.

VALIDATION -- against measurements this repo already owns, not against
itself.  ``../records/RECORD-001`` (issue #38) ran ``tb_extract_c.sp.tmpl``
against the real OSDI model on an x86-64 Linux host and recorded two
geometries.  This module reproduces both to every digit that record prints::

    XCW      w=8u l=8u m=1   RECORD-001: 59.82 fF   here: 59.818 fF
    XDW.XC1  w=4u l=4u m=2   RECORD-001: 27.29 fF   here: 27.286 fF

``selftest`` below re-checks exactly that, and ``run.sh`` runs it before
using any value this module returns.

Usage::

    cmomi_nominal.py <w_um> <l_um> [m] [mmin] [mmax] [feed]   # prints farads
    cmomi_nominal.py selftest                                 # exits non-zero on drift
"""

import math
import sys

UNIT_X = 0.84   # unit-cell pitch along l [um]
UNIT_Y = 0.89   # unit-cell pitch along w [um]
PAD_END = 0.42  # half a bar of pad at each end [um]
CFEED_SLOPE = 0.1625   # [fF/um] single-side
CFEED_END = 0.0916     # [fF]    single-side end fringing
CFEED2_SLOPE = 0.152   # [fF/um] opposite-side (double) feed

# RECORD-001's own measured values, for selftest.  (w, l, m) -> farads.
RECORD_001_MEASURED = {
    (8.0, 8.0, 1): 59.82e-15,     # lock_detector.XCW,     pre-resize
    (4.0, 4.0, 2): 27.29e-15,     # lock_detector.XDW.XC1, pre-resize
}


def c_nominal(w_um, l_um, m=1, mmin=1, mmax=4, feed="double"):
    """Low-frequency capacitance [F] of one cap_cmomi instance, m included."""
    nlay = max(1, int(mmax) - int(mmin) + 1)
    ax = math.floor(l_um / UNIT_X + 1.0e-6)
    ay = math.floor(w_um / UNIT_Y + 1.0e-6)
    ax = 1.0 if ax < 1.0 else float(ax)
    ay = 2.0 if ay < 2.0 else float(ay)
    active_area = ax * ay * UNIT_X * UNIT_Y
    pad_len = ay * UNIT_Y + PAD_END
    density = 0.55 if nlay <= 2 else (0.82 if nlay == 3 else 1.09)
    if feed == "double":
        cfeed = CFEED2_SLOPE * pad_len
    elif feed == "same":
        cfeed = CFEED_SLOPE * pad_len + CFEED_END
    else:
        cfeed = 0.0
    return float(m) * (density * active_area + cfeed) * 1.0e-15


def selftest():
    ok = True
    for (w_um, l_um, m), measured in sorted(RECORD_001_MEASURED.items()):
        got = c_nominal(w_um, l_um, m)
        rel = abs(got - measured) / measured
        status = "ok" if rel < 1e-3 else "DRIFT"
        if rel >= 1e-3:
            ok = False
        print("cmomi_nominal selftest w=%gu l=%gu m=%d: model %.5g F vs "
              "RECORD-001 measured %.5g F (%.3f%%) %s"
              % (w_um, l_um, m, got, measured, 100 * rel, status))
    return 0 if ok else 1


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip())
    if sys.argv[1] == "selftest":
        raise SystemExit(selftest())
    args = sys.argv[1:]
    w_um = float(args[0])
    l_um = float(args[1])
    m = int(args[2]) if len(args) > 2 else 1
    mmin = int(args[3]) if len(args) > 3 else 1
    mmax = int(args[4]) if len(args) > 4 else 4
    feed = args[5] if len(args) > 5 else "double"
    print("%.6e" % c_nominal(w_um, l_um, m, mmin, mmax, feed))


if __name__ == "__main__":
    main()
