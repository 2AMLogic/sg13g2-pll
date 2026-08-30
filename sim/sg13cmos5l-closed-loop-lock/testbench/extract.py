#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/extract.py
(issue #37, Part of #16)

Post-processes the two decks' `wave_<tag>.dat.last` (uniformly resampled
v(ref) v(fb) v(vctrl) v(clk) v(lock), see the .tmpl files' own `linearize`/
`wrdata` lines) and the ngspice `.meas` output captured in `log_<tag>.txt`,
and writes:

  ../corners/results_as_drawn.csv   -- one row: domain currents + lock/spur
                                       verdict for the as-drawn deck
  ../corners/results_proposal.csv   -- same, for the proposal deck
  ../corners/lock_trace_<tag>.csv   -- per-reference-cycle Delta-f / phase
                                       error trace, the row 7 evidence

No numpy/scipy dependency (matches this repo's other extraction scripts) --
edge detection is linear interpolation between adjacent samples, and the
reference-spur estimate uses a single-frequency (Goertzel) DFT rather than a
full FFT, since only the f_ref component is needed.
"""
import csv
import math
import re
import sys


def read_wave(path, ncols=10):
    """wrdata multi-vector format: (t, v)-pairs repeated per vector, i.e.
    columns are [t_ref, ref, t_fb, fb, t_vctrl, vctrl, t_clk, clk, t_lock,
    lock]. All t_* columns are identical (linearize put every vector on the
    same uniform grid) -- only the first is used as the common time base.
    """
    t, ref, fb, vctrl, clk, lock = [], [], [], [], [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) < ncols:
                continue
            try:
                vals = [float(x) for x in p[:ncols]]
            except ValueError:
                continue
            t.append(vals[0])
            ref.append(vals[1])
            fb.append(vals[3])
            vctrl.append(vals[5])
            clk.append(vals[7])
            lock.append(vals[9])
    return t, ref, fb, vctrl, clk, lock


def rising_edges(t, v, vth):
    """Interpolated times of every rising crossing of `vth`."""
    out = []
    for i in range(1, len(v)):
        if v[i - 1] < vth <= v[i]:
            frac = (vth - v[i - 1]) / (v[i] - v[i - 1]) if v[i] != v[i - 1] else 0.0
            out.append(t[i - 1] + frac * (t[i] - t[i - 1]))
    return out


def read_meas(log_path):
    """Parses ngspice `print` output lines of the form `name = value`."""
    out = {}
    pat = re.compile(r'^(i_\w+|vc_\w+)\s*=\s*([-\d.eE+]+)')
    with open(log_path) as f:
        for line in f:
            m = pat.match(line.strip())
            if m:
                out[m.group(1)] = float(m.group(2))
    return out


def lock_analysis(t, ref, fb, vth, fref, df_frac=0.01, phase_frac=0.05, hold_n=20):
    """Row 7: dual delta-f / static-phase-error criterion.

    For each reference cycle, compares the ref period to the fb period
    measured over the SAME interval (delta-f), and the fb edge's phase
    offset within that ref period (static phase error, as a fraction of
    the ref period). Both must stay within threshold for `hold_n`
    consecutive cycles for the interval to count as "locked".

    Thresholds (this record's own re-derivation, per spec/porting-plan.md
    row 7's own "port the structure, re-derive the numeric target"
    disposition -- gf180-pll's own numeric target is NOT ported, only the
    dual-threshold structure): |delta-f|/f_ref < 1%, |phase error| < 5% of
    one reference period, held for >= 20 consecutive reference cycles (1 us
    at f_ref = 20 MHz -- chosen, along with Part B's own TSTOP, to fit this
    host's measured ~1 ns/s wall-clock rate; see ../corners/matrix.md).
    """
    ref_edges = rising_edges(t, ref, vth)
    fb_edges = rising_edges(t, fb, vth)
    tref = 1.0 / fref
    trace = []
    if len(ref_edges) < 2 or not fb_edges:
        return trace, None

    fb_idx = 0
    for i in range(1, len(ref_edges)):
        r0, r1 = ref_edges[i - 1], ref_edges[i]
        period_ref = r1 - r0
        # Nearest fb edge to r1 (the feedback edge this ref cycle is judged
        # against), and the fb period spanning the same interval.
        while fb_idx + 1 < len(fb_edges) and fb_edges[fb_idx + 1] <= r1:
            fb_idx += 1
        nearest = min(fb_edges, key=lambda e: abs(e - r1)) if fb_edges else None
        if nearest is None:
            continue
        phase_err = (nearest - r1) / tref  # fraction of tref, signed
        # local fb period: distance between the two fb edges bracketing this
        # cycle, if both exist.
        prior = max([e for e in fb_edges if e < nearest], default=None)
        if prior is None:
            continue
        period_fb = nearest - prior
        df_frac_meas = (1.0 / period_fb - 1.0 / period_ref) / fref if period_fb > 0 else float("inf")
        ok = abs(df_frac_meas) < df_frac and abs(phase_err) < phase_frac
        trace.append((r1, df_frac_meas, phase_err, ok))

    # Find the earliest index after which `hold_n` consecutive cycles are ok.
    run = 0
    lock_time = None
    for idx, (tt, dff, pe, ok) in enumerate(trace):
        run = run + 1 if ok else 0
        if run >= hold_n:
            lock_start_idx = idx - hold_n + 1
            lock_time = trace[lock_start_idx][0]
            break
    return trace, lock_time


def goertzel_mag(t, x, freq):
    """Single-frequency DFT magnitude of x(t) at `freq`, over the samples
    given (assumed uniformly spaced). Returns the peak amplitude of the
    cosine component at that frequency (i.e. 2*|X(f)|/N convention)."""
    n = len(t)
    if n < 2:
        return 0.0
    dt = (t[-1] - t[0]) / (n - 1)
    re_sum = 0.0
    im_sum = 0.0
    for k, (tt, xx) in enumerate(zip(t, x)):
        ang = 2 * math.pi * freq * (tt - t[0])
        re_sum += xx * math.cos(ang)
        im_sum -= xx * math.sin(ang)
    mag = 2.0 * math.hypot(re_sum, im_sum) / n
    return mag


def spur_dbc(t, vctrl, fref, kvco_hz_per_v, window_frac=0.5):
    """Row 10: reference-spur estimate from the f_ref-frequency ripple
    component of vctrl in the LATTER `window_frac` of the trace (assumed
    closer to steady state), converted to an equivalent FM sideband level
    via the standard narrowband-FM approximation:
        spur_dBc ~= 20*log10( (Kvco * V_ripple_peak) / (2 * f_ref) )
    where V_ripple_peak is the peak amplitude of the f_ref component of
    vctrl (Goertzel DFT at exactly f_ref) and Kvco is the LOCAL secant slope
    (Hz/V) from ../../sg13cmos5l-vco-kvco-table at the operating point this
    deck targets (see ../corners/matrix.md)."""
    n = len(t)
    i0 = int(n * (1 - window_frac))
    tw, vw = t[i0:], vctrl[i0:]
    if len(tw) < 4:
        return None
    v_ripple = goertzel_mag(tw, vw, fref)
    beta = kvco_hz_per_v * v_ripple / (2.0 * fref)
    if beta <= 0:
        return None
    return 20 * math.log10(beta), v_ripple


def parse_time(s):
    s = s.strip()
    if s.endswith("u"):
        return float(s[:-1]) * 1e-6
    if s.endswith("n"):
        return float(s[:-1]) * 1e-9
    if s.endswith("p"):
        return float(s[:-1]) * 1e-12
    return float(s)


def main():
    work, record_dir, fref_s, tstop_s, tavg0_s = sys.argv[1:6]
    fref = float(fref_s)
    tstop_a, tstop_b = [parse_time(x) for x in tstop_s.split(",")]
    tavg0_a, tavg0_b = [parse_time(x) for x in tavg0_s.split(",")]
    tstop_by_tag = {"as_drawn": tstop_a, "proposal": tstop_b}
    tavg0_by_tag = {"as_drawn": tavg0_a, "proposal": tavg0_b}

    # Local Kvco secant (typ, band 11, top interval) reused from
    # ../../sg13cmos5l-loop-bandwidth-pm's own convention -- the closest
    # measured interval to this deck's 1280 MHz target.
    KVCO_HZ_PER_V = (1359.111326e6 - 1161.944505e6) / (2.7 - 2.1)  # ~328.6 MHz/V

    rows_out = []
    for tag in ("as_drawn", "proposal"):
        wave_path = f"{work}/wave_{tag}.dat.last"
        log_path = f"{work}/log_{tag}.txt"
        try:
            t, ref, fb, vctrl, clk, lock = read_wave(wave_path)
        except FileNotFoundError:
            print(f"WARNING: no wave file for {tag}", file=sys.stderr)
            continue
        meas = read_meas(log_path)

        trace, lock_time = lock_analysis(t, ref, fb, vth=1.65, fref=fref)
        with open(f"{record_dir}/corners/lock_trace_{tag}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_s", "delta_f_frac", "phase_err_frac", "within_thresh"])
            for row in trace:
                w.writerow(row)

        spur = spur_dbc(t, vctrl, fref, KVCO_HZ_PER_V)
        spur_val = spur[0] if spur else None
        vripple = spur[1] if spur else None

        vc_end = vctrl[-1] if vctrl else None
        vc_start = vctrl[0] if vctrl else None

        rows_out.append({
            "tag": tag,
            "tstop_s": tstop_by_tag[tag],
            "i_pfd_a": meas.get("i_pfd"),
            "i_cp_a": meas.get("i_cp"),
            "i_vco_a": meas.get("i_vco"),
            "i_div_a": meas.get("i_div"),
            "i_ld_a": meas.get("i_ld"),
            "vc_avg_v": meas.get("vc_avg"),
            "vc_max_v": meas.get("vc_max"),
            "vc_min_v": meas.get("vc_min"),
            "vc_end_v": vc_end,
            "vc_start_v": vc_start,
            "lock_time_s": lock_time,
            "spur_dbc": spur_val,
            "vctrl_ripple_at_fref_v": vripple,
            "n_ref_cycles_observed": len(trace),
        })

        print(f"[{tag}] i_pfd={meas.get('i_pfd')} i_cp={meas.get('i_cp')} "
              f"i_vco={meas.get('i_vco')} i_div={meas.get('i_div')} "
              f"i_ld={meas.get('i_ld')} vc: {vc_start}->{vc_end} "
              f"lock_time={lock_time} n_cycles={len(trace)} spur_dBc={spur_val}",
              file=sys.stderr)

    if rows_out:
        fields = list(rows_out[0].keys())
        for row, path in zip(rows_out, (
                f"{record_dir}/corners/results_as_drawn.csv",
                f"{record_dir}/corners/results_proposal.csv")[:len(rows_out)]):
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerow(row)


if __name__ == "__main__":
    main()
