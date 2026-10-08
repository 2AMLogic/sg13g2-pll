#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/cpdiag_metrics.py
(issue #150, Part of #16)

Metric extraction for the RECORD-006 charge-pump dynamic-term diagnostic.
Pure Python (no numpy); importable for the synthetic-trace self-test
`test_cpdiag_metrics.py`.

`lock_trace` is a line-for-line port of the inline extractor in
`run_closed_loop_cascbias.sh` (the one that produced the historical
`../corners/lock_trace_proposal_cascbias.csv`), so the unchanged control is
judged by exactly the definition RECORD-005 used.  Additions: `summarize`
(final-20-cycle stats, longest dual-lock run, lock time, STRICT
inequalities) and the per-cycle pulse/charge extractor `cycle_charge`.
"""
import bisect
import math

DF_LIMIT = 0.01      # |delta f / f_ref| < 1 %  (strict)
PH_LIMIT = 0.05      # |phase error| < 5 % of T_ref (strict)
HOLD_N = 20          # consecutive cycles that define "locked"


def rising_edges(t, v, vth):
    out = []
    for i in range(1, len(v)):
        if v[i - 1] < vth <= v[i]:
            frac = (vth - v[i - 1]) / (v[i] - v[i - 1]) if v[i] != v[i - 1] else 0.0
            out.append(t[i - 1] + frac * (t[i] - t[i - 1]))
    return out


def falling_edges(t, v, vth):
    out = []
    for i in range(1, len(v)):
        if v[i - 1] >= vth > v[i]:
            frac = (v[i - 1] - vth) / (v[i - 1] - v[i])
            out.append(t[i - 1] + frac * (t[i] - t[i - 1]))
    return out


def lock_trace(t, ref, fb, vth, fref):
    """[(t_ref_edge, delta_f_frac, phase_err_frac), ...] -- RECORD-005 definition."""
    ref_edges = rising_edges(t, ref, vth)
    fb_edges = rising_edges(t, fb, vth)
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


def is_dual_lock(df, pe):
    """Strict inequalities; non-finite values never satisfy the criterion."""
    return (math.isfinite(df) and math.isfinite(pe)
            and abs(df) < DF_LIMIT and abs(pe) < PH_LIMIT)


def longest_run(flags):
    """(length, start_index) of the longest run of True (first on ties)."""
    best, best_i, run, start = 0, None, 0, 0
    for i, f in enumerate(flags):
        if f:
            if run == 0:
                start = i
            run += 1
            if run > best:
                best, best_i = run, start
        else:
            run = 0
    return best, best_i


def lock_time(trace, hold_n=HOLD_N):
    """t of the first cycle of the first run of >= hold_n dual-lock cycles,
    or None (absent lock is None, never 0)."""
    run = 0
    for idx, (_, df, pe) in enumerate(trace):
        run = run + 1 if is_dual_lock(df, pe) else 0
        if run >= hold_n:
            return trace[idx - hold_n + 1][0]
    return None


def summarize(trace, n_final=20):
    flags = [is_dual_lock(df, pe) for _, df, pe in trace]
    flags_f = [math.isfinite(df) and abs(df) < DF_LIMIT for _, df, _ in trace]
    n, i0 = longest_run(flags)
    nf, _ = longest_run(flags_f)
    fin = trace[-n_final:]
    out = {
        "n_cycles": len(trace),
        "longest_dual_lock_run": n,
        "longest_dual_lock_start_s": trace[i0][0] if i0 is not None else None,
        "longest_freq_lock_run": nf,
        "lock_time_s": lock_time(trace),
        "n_final": len(fin),
    }
    if fin:
        pes = [pe for _, _, pe in fin]
        dfs = [df for _, df, _ in fin]
        out.update(
            phase_mean=sum(pes) / len(pes), phase_min=min(pes), phase_max=max(pes),
            df_mean=sum(dfs) / len(dfs), df_min=min(dfs), df_max=max(dfs),
        )
    return out


# ---------------------------------------------------------------------------
# integration helpers (non-uniform grids)
# ---------------------------------------------------------------------------
def _at(t, y, x):
    j = bisect.bisect_right(t, x)
    if j <= 0:
        return y[0]
    if j >= len(t):
        return y[-1]
    f = (x - t[j - 1]) / (t[j] - t[j - 1]) if t[j] != t[j - 1] else 0.0
    return y[j - 1] + f * (y[j] - y[j - 1])


def trapz(t, y, ta, tb):
    """Trapezoid integral of y(t) over [ta, tb], linear interpolation at the ends."""
    if tb <= ta or not t:
        return 0.0
    lo = bisect.bisect_right(t, ta)
    hi = bisect.bisect_left(t, tb)
    pts = [(ta, _at(t, y, ta))] + [(t[k], y[k]) for k in range(lo, hi)] + [(tb, _at(t, y, tb))]
    return sum(0.5 * (y0 + y1) * (x1 - x0) for (x0, y0), (x1, y1) in zip(pts, pts[1:]))


# ---------------------------------------------------------------------------
# per-pulse-pair timing and charge
# ---------------------------------------------------------------------------
NAN = float("nan")


def _mean(t, y, a, b):
    return trapz(t, y, a, b) / (b - a) if b > a else NAN


def pulse_cycles(t, up, dn, icp, vth=1.65, trim=0.35e-9, guard=1.0e-9, quiet_pre=1.5e-9,
                 quiet_post=4.0e-9):
    """One row per UP/DN pulse pair (one per reference cycle in lock).

    t, up, dn, icp : RAW (un-linearized) vectors; icp = i(Vpr), positive =
        current delivered into the loop filter (UP-type charge is positive).
    A pair is the UP pulse [u_r, u_f] (v(up) > vth) with the DN pulse
    [d_r, d_f] that starts within it (or just before it); lead/overlap/tail
    are the three disjoint segments of the union:
        lead    [min(u_r,d_r), max(u_r,d_r))    only the earlier pulse high
        overlap [max(u_r,d_r), min(u_f,d_f))    both high
        tail    [min(u_f,d_f), max(u_f,d_f))    only the later-ending one high
    Cycle window = [start_k - guard, start_{k+1} - guard) so each cycle's
    charge is integrated exactly once.

    Columns (SI units): t_start, lead_is_up, t_lead, t_ovl, t_tail,
    q_cycle (net charge into the filter over the cycle window), q_lead,
    q_ovl, q_rest (= q_cycle - q_lead - q_ovl, i.e. tail + post-pulse
    edge/settling), i_lead (mean current inside `lead`, `trim` removed each
    side; NaN if the segment is too short), i_ovl (same for `overlap`),
    i_off (mean current in the quiet interval [end+quiet_post,
    next_start-quiet_pre], both pulses low), and
    q_edge = q_cycle - i_lead*t_lead - i_ovl*t_ovl  (NaN unless both plateau
    levels are measurable): the charge that is NOT explained by flat
    plateau currents over the measured state durations, i.e. the
    edge/injection/settling term plus any tail plateau.
    """
    ur, uf = rising_edges(t, up, vth), falling_edges(t, up, vth)
    dr, df = rising_edges(t, dn, vth), falling_edges(t, dn, vth)
    pairs = []
    for a in ur:
        b = [x for x in uf if x > a]
        if not b:
            continue
        b = b[0]
        # DN rising edge belonging to this pair: within the UP pulse or up to
        # 6 ns before it (DN-leading); take the closest one
        cand = [x for x in dr if a - 6e-9 <= x <= b]
        if not cand:
            continue
        d_r = min(cand, key=lambda x: abs(x - a))
        d_f = [x for x in df if x > d_r]
        if not d_f:
            continue
        pairs.append((a, b, d_r, d_f[0]))
    rows = []
    for k in range(len(pairs) - 1):
        a, b, c, d = pairs[k]
        a2, b2, c2, d2 = pairs[k + 1]
        s, s2 = min(a, c), min(a2, c2)
        e = max(b, d)
        w0, w1 = s - guard, s2 - guard
        o0, o1 = max(a, c), min(b, d)
        lead_up = a <= c
        t_lead = o0 - s
        t_ovl = max(0.0, o1 - o0)
        t_tail = max(b, d) - min(b, d)
        q_cycle = trapz(t, icp, w0, w1)
        q_lead = trapz(t, icp, s, o0)
        q_ovl = trapz(t, icp, o0, o1) if o1 > o0 else 0.0
        i_lead = _mean(t, icp, s + trim, o0 - trim) if t_lead > 2 * trim + 0.2e-9 else NAN
        i_ovl = _mean(t, icp, o0 + trim, o1 - trim) if t_ovl > 2 * trim + 0.2e-9 else NAN
        qa, qb = e + quiet_post, s2 - quiet_pre
        i_off = _mean(t, icp, qa, qb) if qb - qa > 1e-9 else NAN
        if math.isnan(i_lead) or math.isnan(i_ovl):
            q_edge = NAN
        else:
            q_edge = q_cycle - i_lead * t_lead - i_ovl * t_ovl
        rows.append(dict(
            t_start=s, lead_is_up=int(lead_up), t_lead=t_lead, t_ovl=t_ovl, t_tail=t_tail,
            q_cycle=q_cycle, q_lead=q_lead, q_ovl=q_ovl, q_rest=q_cycle - q_lead - q_ovl,
            i_lead=i_lead, i_ovl=i_ovl, i_off=i_off, q_edge=q_edge))
    return rows
