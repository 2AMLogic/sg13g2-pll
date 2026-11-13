#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/mismatch_gain_metrics.py
(issue #385) -- metrics for the RECORD-014 mismatch-to-phase-error gain sweep.

Two things live here, both pure Python (stdlib only) and both importable so
`test_mismatch_gain_metrics.py` can pin them:

`lock_trace_from_edges`
    The same per-reference-cycle `(t, delta_f_frac, phase_err_frac)` trace
    `cpdiag_metrics.lock_trace` builds, but taking the two rising-edge time
    lists directly instead of extracting them from a sampled waveform.  The
    gain sweep runs on the batch fleet, where the per-corner waveform is not
    what comes back -- `klt sim`'s `measurements[].crossings` returns the
    1.65 V rising-crossing times of `v(ref)` and `v(fb)` instead.  Feeding
    those to this function keeps RECORD-005's phase-error definition, which
    every record in this slug since RECORD-005 is quoted against;
    `test_mismatch_gain_metrics.py` asserts the two agree exactly on a
    sampled trace.  `cpdiag_metrics.py` itself is NOT edited (its sha256 is
    cited by the committed `cpdiag_summary_*.json` files).

`fit_line` / `fit_through_origin`
    Least-squares slope and intercept with the residual, and the
    slope-only fit the `+/-3.5 %` screening limit assumes.  Reporting both
    is what lets RECORD-014 say whether a linear-through-origin model holds
    rather than assuming it does.
"""
import math

#: Re-exported so a caller does not have to import two modules to get the
#: criterion the records use.  (Values, not behaviour -- see cpdiag_metrics.)
DF_LIMIT = 0.01
PH_LIMIT = 0.05


def lock_trace_from_edges(ref_edges, fb_edges, fref):
    """[(t_ref_edge, delta_f_frac, phase_err_frac), ...] -- RECORD-005 definition.

    Line-for-line the body of `cpdiag_metrics.lock_trace` after its two
    `rising_edges` calls, so a trace built from `klt sim` crossing times and
    one built from a sampled waveform are the same object.
    """
    tref = 1.0 / fref
    trace = []
    if len(ref_edges) < 2 or not fb_edges:
        return trace
    for i in range(1, len(ref_edges)):
        r0, r1 = ref_edges[i - 1], ref_edges[i]
        period_ref = r1 - r0
        nearest = min(fb_edges, key=lambda e: abs(e - r1))
        phase_err = (nearest - r1) / tref
        prior = max([e for e in fb_edges if e < nearest], default=None)
        if prior is None:
            continue
        period_fb = nearest - prior
        if period_fb > 0 and period_ref > 0:
            df = (1.0 / period_fb - 1.0 / period_ref) / fref
        else:
            df = float("inf")
        trace.append((r1, df, phase_err))
    return trace


def fit_line(xs, ys):
    """Ordinary least squares `y = a + b*x`.

    Returns `{"slope", "intercept", "n", "resid_rms", "resid_max",
    "r_squared"}`; `None` when fewer than two distinct abscissae are given
    (a slope through one point is not a measurement).
    """
    n = len(xs)
    if n < 2 or len(set(xs)) < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    sst = sum((y - my) ** 2 for y in ys)
    ssr = sum(r * r for r in res)
    return {"n": n, "slope": b, "intercept": a,
            "resid_rms": math.sqrt(ssr / n), "resid_max": max(abs(r) for r in res),
            "r_squared": (1.0 - ssr / sst) if sst > 0 else None}


def fit_through_origin(xs, ys):
    """Least squares `y = b*x` -- the model the `+/-3.5 %` limit assumes.

    Returns `{"slope", "n", "resid_rms", "resid_max"}`, or `None` when every
    abscissa is zero.
    """
    sxx = sum(x * x for x in xs)
    if not xs or sxx == 0:
        return None
    b = sum(x * y for x, y in zip(xs, ys)) / sxx
    res = [y - b * x for x, y in zip(xs, ys)]
    return {"n": len(xs), "slope": b,
            "resid_rms": math.sqrt(sum(r * r for r in res) / len(res)),
            "resid_max": max(abs(r) for r in res)}
