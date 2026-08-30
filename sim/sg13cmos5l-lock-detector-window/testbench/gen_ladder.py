#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-lock-detector-window (issue #38, Part of #16)

Build one per-corner instance of ``tb_lock_ladder.sp.tmpl``, and reduce the
resulting ngspice log to the record's per-corner numbers.

Two subcommands:

``gen``    substitute the skeleton's scalar placeholders and generate the
           phase-error ladder (device cards, ``.ic`` cards, ``.meas`` cards).
           The ladder is expressed in units of THIS corner's own measured
           comparator window ``twin_r`` (from ``tb_window.sp.tmpl``), because
           ``spec/porting-plan.md`` row 16 states its hysteresis criterion as
           a fraction OF THE WINDOW.  The ladder is dense (0.15 x window
           steps) through the region where the threshold actually sits, so a
           hysteresis of 25% of the window -- the row's own criterion -- is
           resolvable rather than merely bracketed.

``reduce`` parse the ngspice log and emit two CSV fragments: the per-ladder
           point raw states, and the one-line per-corner summary (assert
           threshold, de-assert threshold, hysteresis, chatter, currents).

Ladder point k instantiates the DUT TWICE from one stimulus pair:
  * copy A starts fully DISCHARGED (VWIN = 0)  -- "just saw a wide error";
    the largest tau at which A still settles into the in-window state is the
    ASSERT threshold.
  * copy B starts fully CHARGED (VWIN = VDD)   -- "has been clean a long
    time"; the largest tau at which B still holds the in-window state is the
    DE-ASSERT threshold.
Their difference is the hysteresis in phase-error units.

State classification, per copy, over the settle window (last two reference
periods of the run), from the LOCK pin itself:
    IN   -- lk_max <  0.1 * VDD   (pin steady at one rail)
    OUT  -- lk_min >  0.9 * VDD   (pin steady at the other rail)
    TOG  -- anything else: the pin is moving, or sitting between the rails.
``TOG`` deliberately covers both "toggles every reference cycle" (chatter) and
"settles to an intermediate voltage" (a partially-driven output).  Both are
failures of row 16's "no chatter" criterion and both are recorded as such
rather than thresholded into a clean HIGH/LOW.

NOTE ON POLARITY.  ``IN``/``OUT`` above are named for the DUT's *internal*
state (is the integrating node above or below the Schmitt trip), not for the
logic level of the LOCK pin.  The mapping between them is
``../records/RECORD-001`` Finding 1's subject and is resolved there once, from
the zero-phase-error copy, rather than assumed here.
"""

import argparse
import csv
import re
import sys

# Ladder in units of the corner's own measured comparator window twin_r.
# Dense (0.15 x window) from 1.0 to 2.5 x window because that is where the
# threshold sits (the coincidence gate needs the error pulse to exceed the
# window by enough to actually discharge the integrating node, not merely to
# exceed it); coarse outside, where only "clearly in" / "clearly out" matters.
LADDER_FRACS = [
    0.25, 0.50,
    1.00, 1.15, 1.30, 1.45, 1.60, 1.75, 1.90, 2.05, 2.20, 2.35, 2.50,
    10.00,
]


def gen(args):
    with open(args.template) as fh:
        tmpl = fh.read()

    twin = float(args.twin)
    vsup = float(args.vsup)
    tref = float(args.tref)
    taus = [f * twin for f in LADDER_FRACS]

    devices, ics, meas = [], [], []
    keep = ["lkr", "xr.vwin", "vddl#branch", "vddu#branch"]
    for k, (frac, tau) in enumerate(zip(LADDER_FRACS, taus)):
        devices.append(
            "* ladder point {k}: tau = {f:.2f} x twin_r = {tau:.6e} s".format(
                k=k, f=frac, tau=tau))
        devices.append(
            "Vupl{k} upl{k} 0 pulse(0 {v} 'ttd' 'ttr' 'ttr' '{tau:.6e}+trst' "
            "'tref')".format(k=k, v=vsup, tau=tau))
        devices.append(
            "Vdnl{k} dnl{k} 0 pulse(0 {v} 'ttd+{tau:.6e}' 'ttr' 'ttr' 'trst' "
            "'tref')".format(k=k, v=vsup, tau=tau))
        devices.append(
            "Xa{k} upl{k} dnl{k} lka{k} vdd 0 lock_detector".format(k=k))
        devices.append(
            "Xb{k} upl{k} dnl{k} lkb{k} vdd 0 lock_detector".format(k=k))
        ics.append(".ic v(xa{k}.vwin)=0 v(xb{k}.vwin)={v}".format(k=k, v=vsup))
        for cp in ("a", "b"):
            for stat in ("min", "max", "avg"):
                meas.append(
                    "meas tran l{c}{k}_{s} {s} v(lk{c}{k}) from={t0} "
                    "to={t1}".format(c=cp, k=k, s=stat, t0=args.tsettle,
                                     t1=args.tstop))
        for stat in ("min", "max", "avg"):
            meas.append(
                "meas tran va{k}_{s} {s} v(xa{k}.vwin) from={t0} "
                "to={t1}".format(k=k, s=stat, t0=args.tsettle, t1=args.tstop))
        keep += ["lka{k}".format(k=k), "lkb{k}".format(k=k),
                 "xa{k}.vwin".format(k=k)]

    subs = {
        "@LADDER_DEVICES@": "\n".join(devices),
        "@LADDER_IC@": "\n".join(ics),
        "@LADDER_MEAS@": "\n".join(meas),
        # ngspice's `save` accumulates across invocations, so the list is
        # emitted in short chunks rather than as one very long line.
        "@LADDER_SAVE@": "\n".join(
            "save " + " ".join(keep[i:i + 8])
            for i in range(0, len(keep), 8)),
        "@CORNER_MOS@": args.corner_mos,
        "@CORNER_RES@": args.corner_res,
        "@TEMP@": args.temp,
        "@VSUP@": args.vsup,
        "@VMID@": "{:.6f}".format(vsup / 2.0),
        "@VHI@": "{:.6f}".format(0.9 * vsup),
        "@VLO@": "{:.6f}".format(0.1 * vsup),
        "@TREF@": "{:.6e}".format(tref),
        "@TRST@": args.trst,
        "@TAUBIG@": "{:.6e}".format(LADDER_FRACS[-1] * twin),
        "@TSTEP@": args.tstep,
        "@TSTOP@": args.tstop,
        "@TSETTLE@": args.tsettle,
        "@DUT@": args.dut,
        # ngspice's `.lib`/`.include` netlist parser does not expand shell/OS
        # environment variables, so the PDK path has to be a real filesystem
        # path by the time ngspice parses the generated deck (issue #54).
        "@PDK_ROOT@": args.pdk_root,
        "@PDK@": args.pdk,
    }
    # Substitution is line-based and skips comment lines, for two reasons:
    # the skeleton's own header documents its placeholder names and must keep
    # them readable, and the three multi-line placeholders would otherwise be
    # spliced into the middle of a comment line -- which turns every line
    # after the first into a live SPICE card.
    lines = []
    for line in tmpl.splitlines():
        if line.startswith("*"):
            lines.append(line)
            continue
        stripped = line.strip()
        if stripped in ("@LADDER_DEVICES@", "@LADDER_IC@",
                        "@LADDER_MEAS@", "@LADDER_SAVE@"):
            lines.append(subs[stripped])
            continue
        for key, val in subs.items():
            if key.startswith("@LADDER_"):
                continue
            line = line.replace(key, val)
        lines.append(line)
    out = "\n".join(lines) + "\n"

    left = [l for l in out.splitlines()
            if not l.startswith("*") and re.search(r"@[A-Z_]+@", l)]
    if left:
        raise SystemExit("gen_ladder: unsubstituted placeholders: %s" % left)
    with open(args.out, "w") as fh:
        fh.write(out)

    # Emit the ladder taus so run.sh can label the raw rows without
    # recomputing them.
    print(",".join("{:.6e}".format(t) for t in taus))


def _scalars(text):
    vals = {}
    for m in re.finditer(r"^(\w+)\s*=\s*(-?[\d.eE+-]+)", text, re.M):
        try:
            vals[m.group(1)] = float(m.group(2))
        except ValueError:
            pass
    return vals


def _classify(lo, hi, vsup, in_rail):
    """Classify one copy's settled LOCK pin.

    ``in_rail`` is the rail the block itself drives LOCK to when it sees zero
    phase error, measured in the same run from the recovery copy -- so this
    function never assumes the polarity of the LOCK output.
    """
    steady_lo = hi < 0.1 * vsup
    steady_hi = lo > 0.9 * vsup
    if steady_lo:
        return "IN" if in_rail == "lo" else "OUT"
    if steady_hi:
        return "IN" if in_rail == "hi" else "OUT"
    return "TOG"


def reduce_log(args):
    text = sys.stdin.read()
    v = _scalars(text)
    vsup = float(args.vsup)
    twin = float(args.twin)
    taus = [f * twin for f in LADDER_FRACS]

    # Polarity, read from the block: the recovery copy sees zero phase error,
    # so whatever rail its LOCK settles at IS the in-window level.
    lr_lo, lr_hi = v.get("lr_min"), v.get("lr_max")
    if lr_hi is not None and lr_hi < 0.1 * vsup:
        in_rail = "lo"
    elif lr_lo is not None and lr_lo > 0.9 * vsup:
        in_rail = "hi"
    else:
        in_rail = "unresolved"

    raw = csv.writer(open(args.raw, "a"))
    states = {"a": [], "b": []}
    for k, (frac, tau) in enumerate(zip(LADDER_FRACS, taus)):
        row_states = {}
        for cp in ("a", "b"):
            lo = v.get("l{}{}_min".format(cp, k))
            hi = v.get("l{}{}_max".format(cp, k))
            row_states[cp] = ("NA" if lo is None or hi is None
                              else _classify(lo, hi, vsup, in_rail))
            states[cp].append(row_states[cp])
        raw.writerow([
            args.tag, "{:.2f}".format(frac), "{:.6e}".format(tau),
            row_states["a"], row_states["b"],
            _fmt(v.get("la{}_min".format(k))), _fmt(v.get("la{}_max".format(k))),
            _fmt(v.get("la{}_avg".format(k))),
            _fmt(v.get("lb{}_min".format(k))), _fmt(v.get("lb{}_max".format(k))),
            _fmt(v.get("lb{}_avg".format(k))),
            _fmt(v.get("va{}_min".format(k))), _fmt(v.get("va{}_max".format(k))),
            _fmt(v.get("va{}_avg".format(k))),
        ])

    # The in-window state is whatever the zero-phase-error copies settle to.
    # It is read from the block itself rather than assumed, so this reduction
    # is correct regardless of the LOCK pin's polarity.
    def threshold(seq):
        """Largest ladder tau still in the in-window state, with no earlier
        ladder point already out of it.  Returns (tau, frac) or (None, None)
        if even the smallest ladder point is already out."""
        best = (None, None)
        for frac, tau, st in zip(LADDER_FRACS, taus, seq):
            if st != "IN":
                break
            best = (tau, frac)
        return best

    ta, fa = threshold(states["a"])
    td, fd = threshold(states["b"])
    hyst = None if (ta is None or td is None) else td - ta
    hyst_pct = None if hyst is None else 100.0 * hyst / twin

    # Chatter, at the DEEPEST out-of-window ladder point (10 x window -- an
    # unambiguous static phase error, not a marginal one): does the LOCK pin
    # sit steadily at the out-of-window rail, or does it move?  "chatter" is
    # reserved for a pin that swings more than 80% of the rail inside the
    # settle window, i.e. genuinely toggling rather than merely sitting at an
    # intermediate level; the intermediate case is reported separately so the
    # two failure modes are not conflated.
    last = len(LADDER_FRACS) - 1
    dlo, dhi = v.get("la{}_min".format(last)), v.get("la{}_max".format(last))
    if dlo is None or dhi is None:
        chat = "NA"
    elif dhi - dlo > 0.8 * vsup:
        chat = "chatter"
    elif states["a"][last] == "TOG":
        chat = "intermediate"
    else:
        chat = "steady"

    print(",".join([
        args.tag,
        "{:.6e}".format(twin),
        in_rail,
        _fmt(ta), _fmt(fa), _fmt(td), _fmt(fd),
        _fmt(hyst), _fmt(hyst_pct),
        chat, _fmt(dlo), _fmt(dhi),
        _fmt(v.get("trec")),
        _fmt(v.get("vr_min")), _fmt(v.get("vr_max")),
        _fmt(abs(v["idd_lock"]) if "idd_lock" in v else None),
        _fmt(abs(v["idd_unlock"]) if "idd_unlock" in v else None),
        "".join(s[0] for s in states["a"]),
        "".join(s[0] for s in states["b"]),
    ]))


def _fmt(x):
    return "NA" if x is None else "{:.6e}".format(x)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen")
    g.add_argument("--template", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--dut", required=True)
    g.add_argument("--corner-mos", required=True)
    g.add_argument("--corner-res", required=True)
    g.add_argument("--temp", required=True)
    g.add_argument("--vsup", required=True)
    g.add_argument("--tref", required=True)
    g.add_argument("--trst", required=True)
    g.add_argument("--twin", required=True)
    g.add_argument("--tstep", required=True)
    g.add_argument("--tstop", required=True)
    g.add_argument("--tsettle", required=True)
    g.add_argument("--pdk-root", required=True)
    g.add_argument("--pdk", required=True)
    g.set_defaults(func=gen)

    r = sub.add_parser("reduce")
    r.add_argument("--tag", required=True)
    r.add_argument("--vsup", required=True)
    r.add_argument("--twin", required=True)
    r.add_argument("--raw", required=True)
    r.set_defaults(func=reduce_log)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
