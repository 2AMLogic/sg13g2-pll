#!/usr/bin/env python3
"""Self-test for cpdiag_metrics.py on synthetic traces (issue #150).

Run:  python3 -I test_cpdiag_metrics.py      (stdlib only; exit 0 = pass)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpdiag_metrics as m  # noqa: E402


def trace(flags, good=(0.001, 0.02), bad=(0.001, 0.2)):
    out = []
    for i, f in enumerate(flags):
        df, pe = good if f else bad
        out.append((50e-9 * (i + 1), df, pe))
    return out


def test_lock_metrics():
    # no lock at all
    s = m.summarize(trace([False] * 30))
    assert s["lock_time_s"] is None and s["longest_dual_lock_run"] == 0
    # 19-cycle run: not a lock
    s = m.summarize(trace([False] * 5 + [True] * 19 + [False] * 5))
    assert s["longest_dual_lock_run"] == 19 and s["lock_time_s"] is None
    # 20-cycle run: lock time = first cycle of the run
    t = trace([False] * 5 + [True] * 20 + [False] * 5)
    s = m.summarize(t)
    assert s["longest_dual_lock_run"] == 20 and s["lock_time_s"] == t[5][0]
    # a run split by one bad cycle never reaches 20
    s = m.summarize(trace([True] * 12 + [False] + [True] * 12))
    assert s["longest_dual_lock_run"] == 12 and s["lock_time_s"] is None
    # strict inequalities at the thresholds
    assert not m.is_dual_lock(0.0, 0.05)
    assert not m.is_dual_lock(0.01, 0.0)
    assert not m.is_dual_lock(0.0, -0.05)
    assert m.is_dual_lock(0.0099999, 0.0499999)
    assert not m.is_dual_lock(float("inf"), 0.0)
    assert not m.is_dual_lock(0.0, float("nan"))
    # boundary values do not create a lock
    t = [(50e-9 * (i + 1), 0.0, 0.05) for i in range(30)]
    assert m.summarize(t)["lock_time_s"] is None
    # empty trace is handled
    s = m.summarize([])
    assert s["n_cycles"] == 0 and s["lock_time_s"] is None
    # final-20 statistics
    t = [(1.0, 0.0, 0.2)] * 10 + [(2.0, 0.001, 0.08)] * 20
    s = m.summarize(t)
    assert abs(s["phase_mean"] - 0.08) < 1e-12 and s["n_final"] == 20


def square(t_grid, period, delay, width, hi=3.3, edge=1e-10):
    out = []
    for x in t_grid:
        ph = (x - delay) % period
        out.append(hi if 0 <= ph < width else 0.0)
    return out


def test_lock_trace_phase():
    fref = 20e6
    tref = 1 / fref
    dt = 50e-12
    grid = [i * dt for i in range(int(1.2e-6 / dt))]
    ref = square(grid, tref, 5e-9, 25e-9)
    fb = square(grid, tref, 5e-9 + 0.08 * tref, 25e-9)     # fb lags by 8 % of T_ref
    tr = m.lock_trace(grid, ref, fb, 1.65, fref)
    assert len(tr) >= 20
    for _, df, pe in tr[3:]:
        assert abs(pe - 0.08) < 2e-3 and abs(df) < 3e-3, (df, pe)  # 50 ps grid quantisation
    s = m.summarize(tr)
    assert s["lock_time_s"] is None          # 8 % > 5 % -> never dual-locked
    fb2 = square(grid, tref, 5e-9 + 0.03 * tref, 25e-9)
    s2 = m.summarize(m.lock_trace(grid, ref, fb2, 1.65, fref))
    assert s2["lock_time_s"] is not None and abs(s2["phase_mean"] - 0.03) < 2e-3


def test_trapz_and_pulse_cycles():
    dt = 20e-12
    n = int(200e-9 / dt)
    t = [i * dt for i in range(n)]
    assert abs(m.trapz(t, [2.0] * n, 10e-9, 20e-9) - 2.0 * 10e-9) < 1e-18
    # synthetic cp: UP leads DN by 3 ns, both end together after 4 ns of overlap,
    # period 50 ns.  Current = +10 uA while only UP is high, +1 uA while both are
    # high (mismatched), 0 otherwise.
    up = [0.0] * n
    dn = [0.0] * n
    ic = [0.0] * n
    for k in range(4):
        u0 = 20e-9 + 50e-9 * k
        d0, e = u0 + 3e-9, u0 + 7e-9
        for i, x in enumerate(t):
            if u0 <= x < e:
                up[i] = 3.3
            if d0 <= x < e:
                dn[i] = 3.3
            if u0 <= x < d0:
                ic[i] = 10e-6
            elif d0 <= x < e:
                ic[i] = 1e-6
    rows = m.pulse_cycles(t, up, dn, ic)
    assert len(rows) == 3
    r = rows[1]
    assert r["lead_is_up"] == 1
    assert abs(r["t_lead"] - 3e-9) < 1e-10 and abs(r["t_ovl"] - 4e-9) < 1e-10
    assert abs(r["q_cycle"] - (10e-6 * 3e-9 + 1e-6 * 4e-9)) < 1e-16
    assert abs(r["i_lead"] - 10e-6) < 1e-8 and abs(r["i_ovl"] - 1e-6) < 1e-8
    assert abs(r["q_edge"]) < 1e-16        # ideal rectangles -> no unexplained charge
    assert abs(r["i_off"]) < 1e-12
    # sign convention: current into the filter is positive; an extra -50 fC spike
    # shows up as q_edge = -50 fC
    for i, x in enumerate(t):
        if abs(x - (20e-9 + 50e-9 + 7.2e-9)) < dt / 2:
            ic[i] += -50e-15 / dt
    r2 = m.pulse_cycles(t, up, dn, ic)[1]
    assert abs(r2["q_edge"] - (-50e-15)) < 2e-15, r2["q_edge"]
    # off-state-only: no pulses -> no rows
    assert m.pulse_cycles(t, [0.0] * n, [0.0] * n, ic) == []


if __name__ == "__main__":
    test_lock_metrics()
    test_lock_trace_phase()
    test_trapz_and_pulse_cycles()
    print("test_cpdiag_metrics: all passed")
