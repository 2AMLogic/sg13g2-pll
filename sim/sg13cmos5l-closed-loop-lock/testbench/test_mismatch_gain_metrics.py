#!/usr/bin/env python3
"""Self-test for mismatch_gain_metrics.py (issue #385).

    python3 -I test_mismatch_gain_metrics.py

Runs on synthetic data only -- no PDK, no ngspice, no network -- in the
style of the sibling `test_cpdiag_metrics.py`.

The load-bearing test is `test_edges_path_equals_waveform_path`: RECORD-014's
phase error comes from `klt sim` crossing times, every earlier record in this
slug computed it from a sampled `wave.dat`, and the two must be the same
number or the records cannot be compared.  It builds a sampled trace, runs
the committed `cpdiag_metrics.lock_trace` over it, and asserts
`lock_trace_from_edges` fed that trace's own rising edges returns an
identical list.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpdiag_metrics as cm        # noqa: E402
import mismatch_gain_metrics as mg  # noqa: E402

FREF = 20e6
TREF = 1.0 / FREF
VTH = 1.65
VDD = 3.3


def square(t, period, phase, duty=0.5, amp=VDD, slew=100e-12):
    """Trapezoidal square wave, `phase` seconds late, sampled at times `t`."""
    out = []
    for x in t:
        u = ((x - phase) % period)
        if u < slew:
            out.append(amp * u / slew)
        elif u < duty * period:
            out.append(amp)
        elif u < duty * period + slew:
            out.append(amp * (1.0 - (u - duty * period) / slew))
        else:
            out.append(0.0)
    return out


def sampled(phase_s, n_cycles=50, dt=20e-12):
    n = int(n_cycles * TREF / dt)
    t = [i * dt for i in range(n)]
    return t, square(t, TREF, 0.0), square(t, TREF, phase_s)


def test_edges_path_equals_waveform_path():
    for phase_s in (0.0, 0.004 * TREF, -0.031 * TREF, 0.09 * TREF):
        t, ref, fb = sampled(phase_s)
        want = cm.lock_trace(t, ref, fb, VTH, FREF)
        got = mg.lock_trace_from_edges(cm.rising_edges(t, ref, VTH),
                                       cm.rising_edges(t, fb, VTH), FREF)
        assert got == want, f"phase={phase_s}: {len(got)} vs {len(want)} rows"
        assert len(want) > 40, "synthetic trace should give ~49 cycles"
    print("ok test_edges_path_equals_waveform_path")


def test_phase_error_sign_and_scale():
    """A feedback edge 4 % of T_ref late reads +4 %, early reads -4 %."""
    for frac in (0.04, -0.04):
        t, ref, fb = sampled(frac * TREF)
        trace = mg.lock_trace_from_edges(cm.rising_edges(t, ref, VTH),
                                         cm.rising_edges(t, fb, VTH), FREF)
        s = cm.summarize(trace)
        assert abs(s["phase_mean"] - frac) < 1e-6, (frac, s["phase_mean"])
        assert abs(s["df_mean"]) < 1e-9
    print("ok test_phase_error_sign_and_scale")


def test_degenerate_edge_lists():
    assert mg.lock_trace_from_edges([], [], FREF) == []
    assert mg.lock_trace_from_edges([1e-9], [1e-9], FREF) == []
    assert mg.lock_trace_from_edges([1e-9, 2e-9], [], FREF) == []
    print("ok test_degenerate_edge_lists")


def test_fit_line_exact():
    xs = [-12.0, -8.0, -4.0, 0.0, 4.0, 8.0, 12.0]
    ys = [0.25 * x + 1.5 for x in xs]
    f = mg.fit_line(xs, ys)
    assert abs(f["slope"] - 0.25) < 1e-12
    assert abs(f["intercept"] - 1.5) < 1e-12
    assert f["resid_rms"] < 1e-12 and f["resid_max"] < 1e-12
    assert abs(f["r_squared"] - 1.0) < 1e-12
    assert mg.fit_line([1.0], [2.0]) is None
    assert mg.fit_line([1.0, 1.0], [2.0, 3.0]) is None
    print("ok test_fit_line_exact")


def test_fit_through_origin_sees_the_offset():
    """An offset line fitted through the origin leaves a residual the
    two-parameter fit does not -- the discriminator RECORD-014 reports."""
    xs = [-12.0, -8.0, -4.0, 4.0, 8.0, 12.0]
    ys = [0.25 * x + 1.5 for x in xs]
    free, orig = mg.fit_line(xs, ys), mg.fit_through_origin(xs, ys)
    assert free["resid_rms"] < 1e-12
    assert orig["resid_rms"] > 1.0, orig
    assert abs(orig["slope"] - 0.25) < 1e-9, orig  # symmetric x: slope survives
    assert mg.fit_through_origin([], []) is None
    assert mg.fit_through_origin([0.0, 0.0], [1.0, 2.0]) is None
    print("ok test_fit_through_origin_sees_the_offset")


def test_lock_criterion_constants_match_the_records():
    assert (mg.DF_LIMIT, mg.PH_LIMIT) == (cm.DF_LIMIT, cm.PH_LIMIT)
    assert (mg.DF_LIMIT, mg.PH_LIMIT) == (0.01, 0.05)
    print("ok test_lock_criterion_constants_match_the_records")


def main():
    test_edges_path_equals_waveform_path()
    test_phase_error_sign_and_scale()
    test_degenerate_edge_lists()
    test_fit_line_exact()
    test_fit_through_origin_sees_the_offset()
    test_lock_criterion_constants_match_the_records()
    print("all mismatch_gain_metrics self-tests passed")


if __name__ == "__main__":
    main()
