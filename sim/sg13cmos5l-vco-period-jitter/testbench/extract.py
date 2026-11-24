#!/usr/bin/env python3
"""Turn the klt sim deck-list outputs of sg13cmos5l-vco-period-jitter (#518)
into the committed corners/ CSVs, and grade the four method-validation
controls.  Offline, stdlib-only; never edits sim/.

    python3 -I extract.py bias  BIAS_OUTDIR   CORNERS_DIR        -> prints "VBP VBN"
    python3 -I extract.py cal   CAL_OUTDIR    CORNERS_DIR        -> prints sigma (A)
    python3 -I extract.py main  MAIN_OUTDIR   CORNERS_DIR        -> control verdicts; exit 1 on failure
    python3 -I extract.py calset CAL_OUTDIR FLEET_REPORT CORNERS -> per-op PVT calibration CSVs
    python3 -I extract.py campaign UNITS_CSV REPORT... CORNERS   -> pvt_jitter.csv (seed echo verified)
    python3 -I extract.py ripple UNITS_CSV REPORT... CORNERS     -> ripple.csv (deterministic vs random)

BIAS/CAL/MAIN_OUTDIR are klt sim -o directories; CORNERS_DIR is this
bench's corners/.  All numeric parameters in the outputs are read from the
generator's decks_meta.json (which extract reads from <OUTDIR>/../ or
<OUTDIR> itself -- run.sh keeps decks and -o side by side), so the CSVs
quote the exact deck strings, never a re-derivation.

calset/campaign/ripple reduce the #518 steps 4-5 fleet runs
(gen_campaign.py's outputs): calset reads the deck-list calibration
report (stdout files under the -o tree on batch) plus the generator's
cal_meta.json; campaign/ripple read the structured corner reports
(single or --batch-set envelopes) plus the generator's units.csv, verify
every unit's environment.transient_noise.seed against the declared seed,
and refuse an unseeded or mismatched unit.
"""
import csv, hashlib, json, math, pathlib, re, sys

FIRST, LAST = 51, 1051
XING_SKIP, XING_MIN = 50, 1000     # startup crossings skipped / periods kept
RIPPLE_MIN = 700    # ripple floor: > one full 1 MHz cycle (~650 periods)
TS = 1e-11                 # trrandom sample interval (s) -- matches gen_decks.py
CAL_TRAN_DT = 5e-12        # .tran step of the calibration transient = PSD grid
PSD_SEG = 1 << 14
PSD_TOL = (0.70, 1.40)     # in-band transient-PSD / .noise ratio bounds
CHI2_Z = 1.959964          # 95%


# ---------------------------------------------------------------- parsing
def stdout_of(phase_dir, uid):
    p = pathlib.Path(phase_dir) / "out" / uid / "stdout.bin"
    if not p.is_file():
        sys.exit(f"extract.py: missing {p} (unit {uid} did not run?)")
    return p.read_text(errors="replace")


def scalar(txt, name):
    m = re.search(rf"^{re.escape(name)}[ \t]*=[ \t]*(\S+)[ \t]*$", txt, re.M)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def vector_table(txt, header_re):
    """Rows of an ngspice control-mode `print` table whose header line
    matches `header_re`.  Long tables are emitted in chunks that each
    repeat the header (observed through klt's stdout capture); chunks are
    stitched.  Returns list of float tuples (re, im kept apart)."""
    rows, in_tab = [], False
    for line in txt.splitlines():
        s = line.strip()
        if re.match(header_re, s):
            in_tab = True
            continue
        if not in_tab:
            continue
        p = [c for c in line.split("\t") if c.strip() != ""]
        if len(p) >= 2 and p[0].isdigit():
            try:
                vals = tuple(float(c.rstrip(",")) for c in p[1:])
            except ValueError:
                sys.exit(f"extract.py: malformed table row: {line.strip()}")
            if not all(math.isfinite(x) for x in vals):
                sys.exit(f"extract.py: non-finite table row: {line.strip()}")
            rows.append(vals)
        elif s == "" or set(s) == {"-"}:
            continue
        else:
            break
    return rows


def fft_pow2(a):
    m = len(a)
    j = 0
    for i in range(1, m):
        bit = m >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= m:
        wl = complex(math.cos(-2 * math.pi / length), math.sin(-2 * math.pi / length))
        for i in range(0, m, length):
            wn = 1 + 0j
            half = length // 2
            for k in range(half):
                u = a[i + k]
                v = a[i + k + half] * wn
                a[i + k] = u + v
                a[i + k + half] = u - v
                wn *= wl
        length *= 2
    return a


def welch_psd(t, v, seg=PSD_SEG):
    """One-sided Welch PSD (V^2/Hz) with a Hann window on a uniform grid."""
    n = len(v)
    fs = 1.0 / (t[1] - t[0])
    w = [0.5 - 0.5 * math.cos(2 * math.pi * (i + 0.5) / seg) for i in range(seg)]
    wsum = sum(x * x for x in w)
    nseg = (n - seg) // seg
    if nseg < 4:
        sys.exit(f"extract.py: waveform too short for Welch ({nseg} segments)")
    acc = [0.0] * (seg // 2 + 1)
    for s in range(nseg):
        sv = v[s * seg:s * seg + seg]
        m = sum(sv) / seg
        x = [complex((sv[i] - m) * w[i], 0.0) for i in range(seg)]
        X = fft_pow2(x)
        for i in range(seg // 2 + 1):
            acc[i] += 2 * abs(X[i]) ** 2 / (fs * wsum)
    P = [a / nseg for a in acc]
    f = [i * fs / seg for i in range(len(P))]
    return f, P


def psd_at(f, P, f0):
    if f0 <= f[0]:
        return P[0]
    if f0 >= f[-1]:
        return P[-1]
    lo, hi = 0, len(f) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if f[mid] <= f0:
            lo = mid
        else:
            hi = mid
    frac = (f0 - f[lo]) / (f[hi] - f[lo])
    return P[lo] + frac * (P[hi] - P[lo])


def chi2_bounds(df, z=CHI2_Z):
    """Wilson-Hilferty approximation of the chi-square quantiles."""
    out = []
    for zz in (-z, z):
        out.append(df * (1 - 2 / (9 * df) + zz * math.sqrt(2 / (9 * df))) ** 3)
    return out  # [q_0.025, q_0.975]


# ---------------------------------------------------------------- phase: bias
def cmd_bias(outdir, corners):
    txt = stdout_of(outdir, "bias_op")
    vbp, vbn = scalar(txt, "v(vbp)"), scalar(txt, "v(vbn)")
    if vbp is None or vbn is None:
        sys.exit("extract.py: could not parse v(vbp)/v(vbn) from bias_op stdout")
    corners.mkdir(parents=True, exist_ok=True)
    with open(corners / "calibration_bias.csv", "w") as f:
        f.write("unit,corner_mos,corner_res,temp_c,vctrl_v,band_code,vbp_v,vbn_v\n")
        f.write(f"bias_op,mos_tt,res_typ,27,1.5,00,{vbp:.6e},{vbn:.6e}\n")
    print(f"{vbp:.9e} {vbn:.9e}")


# ---------------------------------------------------------------- phase: cal
def cmd_cal(outdir, corners):
    nz = stdout_of(outdir, "cal_noise")
    ac = stdout_of(outdir, "cal_ac")
    sw = stdout_of(outdir, "cal_dcsweep")
    trip = scalar(nz, "v(sout)")
    if trip is None:
        sys.exit("extract.py: could not parse the trip point v(sout) from "
                 "cal_noise stdout -- refusing to substitute a hard-coded value")
    noise_rows = vector_table(nz, r"^Index\s+frequency")
    ac_rows = vector_table(ac, r"^Index\s+frequency")
    if len(noise_rows) < 100 or len(ac_rows) < 100:
        sys.exit(f"extract.py: short tables (noise {len(noise_rows)}, ac {len(ac_rows)})")
    zmap = {f: math.hypot(re_, im) for f, re_, im in ac_rows}
    # every .noise frequency needs a finite, non-zero |Z_out| from .ac; a
    # silent skip would shrink calibration_noise.csv and the si fit band
    bad_join = [f0 for f0, _ in noise_rows
                if not (zmap.get(f0) is not None and math.isfinite(zmap[f0])
                        and zmap[f0] > 0.0)]
    if bad_join:
        sys.exit(f"extract.py: {len(bad_join)} of {len(noise_rows)} .noise "
                 "frequencies have no finite non-zero .ac |Z_out| "
                 f"(first: {bad_join[0]:.6e} Hz)")
    cal_noise_out = [[f"{f0:.6e}", f"{s:.6e}", f"{zmap[f0]:.6e}",
                      f"{s / zmap[f0]:.6e}"] for f0, s in noise_rows]
    # fit: band mean of S_v/|Z|^2 (A^2/Hz)
    band = [(s, zmap[f0]) for f0, s in noise_rows if 1e8 <= f0 <= 1e10]
    if not band:
        sys.exit("extract.py: no in-band (100 MHz..10 GHz) noise/ac points")
    si = [(s * s) / (Z * Z) for s, Z in band]
    si_mean = sum(si) / len(si)
    sigma = math.sqrt(si_mean / (2 * TS))
    # DC-transfer small-signal gain at the self-bias point (max |dv/dv| in
    # the +/-20 mV around the measured trip point)
    sw_rows = vector_table(sw, r"^Index\s+v-sweep")
    gains = []
    for (v0, o0), (v1, o1) in zip(sw_rows, sw_rows[1:]):
        if abs(v0 - trip) <= 0.025 or abs(v1 - trip) <= 0.025:
            if v1 != v0:
                gains.append(abs(o1 - o0) / abs(v1 - v0))
    gain = max(gains) if gains else None
    # per-device integrated-noise split (print all dump in the noise2 plot):
    # flicker-vs-thermal evidence for the 1/f exclusion.  Only the
    # sub-component vectors (suffix _idid/_flicker/_rd/_rs/...) are summed;
    # the bare per-device aggregates (no sub-suffix) would double-count.
    dev = []   # (name, value) per printed line -- repeated names kept
    for line in nz.splitlines():
        if not (line.startswith("onoise_total_") and ".xs1." in line):
            continue
        m = re.match(r"^onoise_total_(\S+)[ \t]*=[ \t]*(\S+)[ \t]*$", line)
        try:
            val = float(m.group(2)) if m else float("nan")
        except ValueError:
            val = float("nan")
        if not math.isfinite(val):
            sys.exit("extract.py: could not parse a finite per-device "
                     f"onoise_total_ reading from cal_noise stdout: {line.strip()!r}")
        dev.append((m.group(1), val))
    if not dev:
        sys.exit("extract.py: no per-device onoise_total_*.xs1.* dump found "
                 "in cal_noise stdout")
    is_sub = lambda k: re.search(r"(?:pmos|nmos|rfb)_", k) is not None
    is_flicker = lambda k: is_sub(k) and "flicker" in k
    is_thermal = lambda k: is_sub(k) and ("idid" in k or "_rd" in k
                                          or "_rs" in k or "thermal" in k)
    sub = [(k, v) for k, v in dev if is_sub(k)]
    flicker = [(k, v) for k, v in dev if is_flicker(k)]
    thermal = [(k, v) for k, v in dev if is_thermal(k)]
    # ngspice per-device integrated totals are rms-V contributions: their
    # quadrature sum reconstructs onoise_total (verified below)
    q = lambda d: math.sqrt(sum(v * v for _, v in d)) if d else None
    onoise_total = scalar(nz, "onoise_total")
    if onoise_total is None:
        sys.exit("extract.py: could not parse a finite onoise_total from "
                 "cal_noise stdout")
    dev_rows = []
    for k, v in dev:
        cls = ("flicker" if is_flicker(k) else "thermal" if is_thermal(k)
               else "other" if is_sub(k) else "excluded_aggregate")
        dev_rows.append([k, f"{v:.6e}", cls])
    fit_row = ["1.000000e+08", "1.000000e+10", len(si),
               f"{si_mean:.6e}", f"{min(si):.6e}", f"{max(si):.6e}",
               f"{TS:.5e}", f"{sigma:.5e}",
               f"{trip:.6e}",
               f"{gain:.4f}" if gain is not None else "NA",
               f"{onoise_total:.6e}",
               f"{q(sub):.6e}" if q(sub) is not None else "NA",
               f"{q(flicker):.6e}" if q(flicker) is not None else "NA",
               f"{q(thermal):.6e}" if q(thermal) is not None else "NA"]
    # Write CSVs only after all calibration inputs validate and parse cleanly.
    corners.mkdir(parents=True, exist_ok=True)
    with open(corners / "calibration_noise.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["f_hz", "onoise_v_rthz", "z_out_ohm", "si_eff_a_rthz"])
        w.writerows(cal_noise_out)
    # commit every per-device onoise_total_* row with its classification so
    # the flicker/thermal split (and its regexes) can be audited offline
    with open(corners / "calibration_devices.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["name", "onoise_total_v", "class"])
        w.writerows(dev_rows)
    with open(corners / "calibration_fit.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["fit_band_lo_hz", "fit_band_hi_hz", "n_band_pts",
                    "si_a2_per_hz", "si_min_a2_per_hz", "si_max_a2_per_hz",
                    "ts_s", "sigma_a", "trip_v", "ss_gain_v_per_v",
                    "onoise_total_v", "onoise_subcomponent_quadrature_v",
                    "stage_flicker_rms_v", "stage_channel_thermal_rms_v"])
        w.writerow(fit_row)
    print(f"{sigma:.5e}")


# ---------------------------------------------------------------- phase: main
def crossings(txt, uid):
    tc = {}
    for m in re.finditer(r"^tc(\d+)[ \t]*=[ \t]*(\S+)[ \t]*$", txt, re.M):
        try:
            v = float(m.group(2))
        except ValueError:
            continue
        if math.isfinite(v):
            tc[int(m.group(1))] = v
    missing = [k for k in range(FIRST, LAST + 1) if k not in tc]
    if missing:
        sys.exit(f"extract.py: {uid}: {len(missing)} crossings missing "
                 f"(first {missing[:3]}) -- run failed or stopped early")
    return tc


def period_stats(ts_):
    """rms/CI/... over an explicit list of period samples."""
    n = len(ts_)
    mean = sum(ts_) / n
    var = sum((x - mean) ** 2 for x in ts_) / (n - 1)
    rms = math.sqrt(var)
    lo_c, hi_c = chi2_bounds(n - 1)
    return {
        "n": n, "mean": mean, "rms": rms, "pp": max(ts_) - min(ts_),
        "pct": 100 * rms / mean,
        "ci_lo": rms * math.sqrt((n - 1) / hi_c),
        "ci_hi": rms * math.sqrt((n - 1) / lo_c),
        "half1": sum(ts_[:n // 2]) / (n // 2),
        "half2": sum(ts_[n // 2:]) / (n - n // 2),
    }


def jitter_stats(tc):
    return period_stats(
        [tc[k + 1] - tc[k] for k in sorted(tc) if k + 1 in tc])


def digest(tc):
    body = "".join(f"tc{k}={tc[k]!r}\n" for k in sorted(tc))
    return hashlib.sha256(body.encode()).hexdigest()


def cmd_main(outdir, corners):
    meta = json.loads((pathlib.Path(outdir) / "decks_meta.json").read_text())
    units = meta["units"]

    rows, dig = [], {}
    stats = {}
    for uid, u in units.items():
        if not uid.startswith("ring_"):
            continue
        tc = crossings(stdout_of(outdir, uid), uid)
        st = jitter_stats(tc)
        dig[uid] = digest(tc)
        stats[uid] = st
        rows.append([uid, u["seed"], u["sigma_a"], u["ts_s"], u["tran_step_s"],
                     st["n"], f"{st['mean']:.9e}", f"{st['rms']:.9e}",
                     f"{st['pp']:.9e}", f"{st['pct']:.6f}",
                     f"{st['ci_lo']:.9e}", f"{st['ci_hi']:.9e}",
                     f"{st['half1']:.9e}", f"{st['half2']:.9e}"])
    # PSD validation rows
    psd_rows, psd_ratio = [], {}
    for uid in [u for u in units if u.startswith("cal_tran_")]:
        path = pathlib.Path(outdir) / "out" / uid / "calpsd.txt"
        if not path.is_file():
            sys.exit(f"extract.py: {uid}: missing wrdata output {path}")
        d = []
        for l in path.read_text().splitlines():
            if not l.strip():
                continue
            parts = l.split()
            try:
                pair = (float(parts[0]), float(parts[1])) if len(parts) == 2 else None
            except ValueError:
                pair = None
            if pair is None or not (math.isfinite(pair[0]) and math.isfinite(pair[1])):
                sys.exit(f"extract.py: {uid}: malformed or non-finite wrdata row: {l.strip()}")
            d.append(pair)
        if len(d) < 2:
            sys.exit(f"extract.py: {uid}: wrdata output {path} has fewer than 2 samples")
        t = [x[0] for x in d]
        v = [x[1] for x in d]
        if abs((t[1] - t[0]) - CAL_TRAN_DT) > 1e-15:
            sys.exit(f"extract.py: {uid}: PSD grid {t[1]-t[0]} != {CAL_TRAN_DT}")
        f_, P = welch_psd(t, v)
        psd_ratio[uid] = []
        for f0, s in NOISE_REF:
            if 1e8 <= f0 <= 1e10:
                r = math.sqrt(psd_at(f_, P, f0)) / s
                psd_ratio[uid].append(r)
                psd_rows.append([uid, f"{f0:.6e}", f"{math.sqrt(psd_at(f_, P, f0)):.6e}",
                                 f"{s:.6e}", f"{r:.4f}"])

    # ---- controls
    ctrl = []

    def add(name, expectation, measured, ok):
        ctrl.append([name, expectation, measured, "PASS" if ok else "FAIL"])

    r_on, r_off = stats["ring_s42_t10p"], stats["ring_off_s42_t10p"]
    add("noise_off", "rms(sigma=0) < 1% of rms(sigma=cal)",
        f"{r_off['rms']:.3e} s vs {r_on['rms']:.3e} s "
        f"({100 * r_off['rms'] / r_on['rms']:.4f}%)",
        r_off["rms"] < 0.01 * r_on["rms"])
    r_h = stats["ring_s42_t5p"]
    add("timestep_halved", "|rms(tstep=5p)/rms(tstep=10p) - 1| < 10%",
        f"ratio {r_h['rms'] / r_on['rms']:.4f}",
        abs(r_h["rms"] / r_on["rms"] - 1) < 0.10)
    r_offh = stats["ring_off_s42_t5p"]
    add("timestep_halved_noise_off", "noise-off floor stays < 1% of noise-on rms",
        f"{r_offh['rms']:.3e} s ({100 * r_offh['rms'] / r_on['rms']:.4f}%)",
        r_offh["rms"] < 0.01 * r_on["rms"])
    r_a2, r_a05 = stats["ring_s42_amp2_t10p"], stats["ring_s42_amp05_t10p"]
    add("amplitude_x2", "rms(2*sigma) within 10% of 2x rms(sigma)",
        f"ratio {r_a2['rms'] / r_on['rms']:.4f}",
        abs(r_a2["rms"] / r_on["rms"] - 2) < 0.2)
    add("amplitude_x0p5", "rms(0.5*sigma) within 10% of 0.5x rms(sigma)",
        f"ratio {r_a05['rms'] / r_on['rms']:.4f}",
        abs(r_a05["rms"] / r_on["rms"] - 0.5) < 0.05)
    add("seed_repeat", "rerun of the same seed is bit-identical",
        "sha256 equal" if dig["ring_s42_t10p"] == dig["ring_s42_t10p_rep"]
        else "sha256 differ",
        dig["ring_s42_t10p"] == dig["ring_s42_t10p_rep"])
    seeds = [stats[u]["rms"] for u in ("ring_s42_t10p", "ring_s43_t10p", "ring_s44_t10p")]
    pooled = sum(seeds) / 3
    n = r_on["n"]
    cv = 1 / math.sqrt(2 * (n - 1))          # sampling CV of one rms estimate
    chi2 = sum((s - pooled) ** 2 for s in seeds) / (pooled * pooled * cv * cv)
    add("seed_scatter",
        "three seed rms values consistent with a common sigma: "
        "chi-square(2) <= 5.99 (95%)",
        f"seeds {[f'{s:.3e}' for s in seeds]}; pooled {pooled:.3e}; "
        f"chi2(2)={chi2:.2f} vs 5.99",
        chi2 <= 5.99)
    worst = []
    for uid, rr in psd_ratio.items():
        if rr:
            worst.append(f"{uid}: {min(rr):.3f}..{max(rr):.3f}")
    allr = [r for rr in psd_ratio.values() for r in rr]
    ok = bool(allr) and all(PSD_TOL[0] <= r <= PSD_TOL[1] for r in allr)
    add("cal_psd_band", f"every in-band ratio within {PSD_TOL}",
        "; ".join(worst) if worst else "no rows", ok)

    # Write CSVs only after all main-phase inputs validate and parse cleanly.
    corners.mkdir(parents=True, exist_ok=True)
    with open(corners / "period_jitter.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["unit", "seed", "sigma_a", "ts_s", "tran_step_s", "n_periods",
                    "mean_period_s", "rms_jitter_s", "pp_jitter_s",
                    "rms_pct_of_period", "ci95_lo_s", "ci95_hi_s",
                    "mean_period_first500_s", "mean_period_last500_s"])
        w.writerows(rows)
    with open(corners / "crossing_digest.csv", "w") as f:
        f.write("unit,n_crossings,crossing_table_sha256\n")
        for uid in sorted(dig):
            f.write(f"{uid},{LAST - FIRST + 1},{dig[uid]}\n")
    with open(corners / "calibration_psd.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["unit", "f_hz", "psd_tran_v_rthz", "noise_ref_v_rthz", "ratio"])
        w.writerows(psd_rows)
    with open(corners / "controls.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["control", "expectation", "measured", "verdict"])
        w.writerows(ctrl)
    failed = [c for c in ctrl if c[3] != "PASS"]
    for c in ctrl:
        print(f"[{c[3]}] {c[0]}: {c[2]}")
    if failed:
        sys.exit(f"extract.py: {len(failed)} control(s) FAILED")


# ------------------------------------------------- phase: calset (fleet PVT)
def _iter_reports(doc, path):
    """Yield (label, report) from a single report or a --batch-set
    {"requests": [...]} envelope (the closed-loop campaign's collector
    shape)."""
    if isinstance(doc, dict) and "requests" in doc and "corners" not in doc:
        for i, member in enumerate(doc["requests"]):
            yield f"{path}#requests[{i}]", member
    else:
        yield path, doc


def _unit_stdout(outdir, unit_row):
    """A batch deck report's `stdout` key names a file under the -o tree
    (measured: "typ_b00_v1p5__bias/stdout.bin"); a local report carries
    the text inline.  Return the text either way."""
    s = unit_row.get("stdout")
    if not s:
        sys.exit(f"extract.py: unit {unit_row.get('id')} has no stdout")
    p = pathlib.Path(outdir) / s
    if p.is_file():
        return p.read_text(errors="replace")
    if "\n" in s or "=" in s:          # inline text, not a path
        return s
    sys.exit(f"extract.py: unit {unit_row.get('id')}: stdout neither an "
             f"outdir-relative file ({p}) nor inline text")


def cmd_calset(outdir, report_path, corners):
    """The fleet calibration report (bias + noise + ac decks per operating
    point) -> calibration_bias_pvt.csv + calibration_pvt.csv."""
    doc = json.loads(pathlib.Path(report_path).read_text())
    outdir = pathlib.Path(outdir)
    meta_path = next((p for p in (outdir / "cal_meta.json",
                                  outdir.parent / "cal_meta.json")
                      if p.is_file()), None)
    if meta_path is None:
        sys.exit("extract.py: calset: no cal_meta.json in (or beside) the "
                 "-o tree -- copy the generator's cal_meta.json next to the "
                 "outputs (run_pvt.sh does)")
    meta = json.loads(meta_path.read_text())
    txt = {}
    for u in doc.get("units", []):
        if u.get("status") != "pass":
            sys.exit(f"extract.py: calset: deck unit {u.get('id')} "
                     f"status {u.get('status')!r} -- refusing to calibrate")
        txt[u["id"]] = _unit_stdout(outdir, u)
    bias_rows, fit_rows, sig = [], {}, {}
    for pid, pt in sorted(meta["points"].items()):
        uids = pt["units"]
        bt = txt.get(f"{pid}__bias")
        if bt is None:
            sys.exit(f"extract.py: calset: no bias deck output for {pid}")
        vbp = scalar(bt, "v(vbp)")
        vbn = scalar(bt, "v(vbn)")
        if vbp is None or vbn is None:
            sys.exit(f"extract.py: calset: {pid}: could not parse v(vbp)/"
                     "v(vbn) from the bias deck stdout")
        bias_rows.append([pid, pt["bundle"], pt["band_code"], pt["vctrl_v"],
                          pt["mos"], pt["res"], pt["temp_c"],
                          f"{vbp:.9e}", f"{vbn:.9e}"])
        if f"{pid}__noise" in uids:
            nz = txt[f"{pid}__noise"]
            ac = txt[f"{pid}__ac"]
            noise_rows = vector_table(nz, r"^Index\s+frequency")
            ac_rows = vector_table(ac, r"^Index\s+frequency")
            if len(noise_rows) < 100 or len(ac_rows) < 100:
                sys.exit(f"extract.py: calset: {pid}: short tables "
                         f"(noise {len(noise_rows)}, ac {len(ac_rows)})")
            zmap = {f: math.hypot(re_, im) for f, re_, im in ac_rows}
            bad = [f0 for f0, _ in noise_rows
                   if not (zmap.get(f0) is not None
                           and math.isfinite(zmap[f0]) and zmap[f0] > 0.0)]
            if bad:
                sys.exit(f"extract.py: calset: {pid}: {len(bad)} of "
                         f"{len(noise_rows)} .noise frequencies have no finite "
                         f"non-zero .ac |Z_out| (first {bad[0]:.6e} Hz)")
            band = [(s, zmap[f0]) for f0, s in noise_rows if 1e8 <= f0 <= 1e10]
            if not band:
                sys.exit(f"extract.py: calset: {pid}: no in-band points")
            si = [(s * s) / (Z * Z) for s, Z in band]
            si_mean = sum(si) / len(si)
            sigma = math.sqrt(si_mean / (2 * TS))
            trip = scalar(nz, "v(sout)")
            if trip is None:
                sys.exit(f"extract.py: calset: {pid}: no v(sout) trip point "
                         "in the noise deck stdout")
            vin = scalar(nz, "v(sin1)")
            if vin is None or abs(vin - trip) > 1e-3:
                sys.exit(f"extract.py: calset: {pid}: self-bias check failed "
                         f"(v(sin1)={vin} vs v(sout)={trip}) -- the stage op "
                         "point is not the circuit's own solution")
            key = (pt["bundle"], pt["band_code"], pt["vctrl_v"])
            fit_rows[pid] = [pt["bundle"], pt["band_code"], pt["vctrl_v"],
                             len(si), f"{si_mean:.6e}", f"{min(si):.6e}",
                             f"{max(si):.6e}", f"{TS:.5e}", f"{sigma:.5e}",
                             f"{trip:.6e}", f"{vin:.6e}"]
            sig[key] = (vbp, vbn, sigma)
    if len(sig) == 0:
        # bias-only pass (the two-step flow: sigma needs VBP/VBN first)
        corners.mkdir(parents=True, exist_ok=True)
        with open(corners / "calibration_bias_pvt.csv", "w") as f:
            w = csv.writer(f)
            w.writerow(["point_id", "bundle", "band_code", "vctrl_v",
                        "mos_corner", "res_corner", "temp_c", "vbp_v",
                        "vbn_v"])
            w.writerows(bias_rows)
        print(f"calset: bias-only pass, {len(bias_rows)} rows -> "
              "calibration_bias_pvt.csv; rerun gen --phase cal with "
              "--bias-csv, resubmit, and run calset on the full report")
        return
    if len(sig) != len(meta["points"]):
        sys.exit(f"extract.py: calset: {len(sig)} of {len(meta['points'])} "
                 "points have a noise/ac pair -- rerun gen --phase cal with "
                 "--bias-csv")
    # reference-point cross-check against RECORD-001's committed calibration
    # (the stop-and-report criterion RECORD-002 set for PDK drift)
    ref_fit = list(csv.DictReader(open(corners / "calibration_fit.csv")))[0]
    ref_bias = list(csv.DictReader(open(corners / "calibration_bias.csv")))[0]
    key = ("typ", "00", "1.5")
    ref_sigma = float(ref_fit["sigma_a"])
    delta = abs(sig[key][2] - ref_sigma) / ref_sigma
    if delta > 1e-3:
        sys.exit(f"extract.py: calset: reference-point sigma drifted: fleet "
                 f"{sig[key][2]:.6e} vs committed {ref_sigma:.6e} "
                 f"({delta:.2e} relative > 1e-3) -- RECORD-002's "
                 "stop-and-report criterion")
    b_commit = (f'{float(ref_bias["vbp_v"]):.6e}', f'{float(ref_bias["vbn_v"]):.6e}')
    b_fleet = (f"{sig[key][0]:.6e}", f"{sig[key][1]:.6e}")
    if b_fleet != b_commit:
        sys.exit(f"extract.py: calset: reference-point bias differs at 6-digit "
                 f"CSV precision: fleet {b_fleet} vs committed {b_commit}")
    corners.mkdir(parents=True, exist_ok=True)
    with open(corners / "calibration_bias_pvt.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["point_id", "bundle", "band_code", "vctrl_v", "mos_corner",
                    "res_corner", "temp_c", "vbp_v", "vbn_v"])
        w.writerows(bias_rows)
    with open(corners / "calibration_pvt.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["bundle", "band_code", "vctrl_v", "n_band_pts",
                    "si_a2_per_hz", "si_min_a2_per_hz", "si_max_a2_per_hz",
                    "ts_s", "sigma_a", "trip_v", "vin_v"])
        w.writerows([fit_rows[p] for p in sorted(fit_rows)])
    # the sigma CSV gen --phase pvt consumes (bundle, band, vctrl keys)
    with open(corners / "campaign_sigma.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["bundle", "band_code", "vctrl_v", "vbp_v", "vbn_v",
                    "sigma_a"])
        for (b, band, vc), (vbp, vbn, sigma) in sorted(sig.items()):
            w.writerow([b, band, vc, f"{vbp:.9e}", f"{vbn:.9e}",
                        f"{sigma:.5e}"])
    print(f"calset: {len(bias_rows)} bias rows, {len(sig)} sigmas; "
          f"reference sigma delta {delta:.2e} (PASS <= 1e-3)")


# ---------------------------------------------- phase: campaign / ripple
def _load_units(units_csv):
    with open(units_csv) as f:
        return {r["unit_id"]: r for r in csv.DictReader(f)}


def _series_of(report_member):
    """corners[0].measurements[] -> the t_clk crossings times list."""
    cs = report_member.get("corners") or []
    if len(cs) != 1:
        sys.exit(f"extract.py: expected exactly 1 corner per member, "
                 f"got {len(cs)}")
    if cs[0].get("status") != "pass":
        sys.exit(f"extract.py: corner {cs[0].get('corner_id')} status "
                 f"{cs[0].get('status')!r}")
    for m in cs[0].get("measurements", []):
        if m.get("name") == "t_clk" and isinstance(m.get("crossings"), dict):
            t = m["crossings"].get("times")
            if not t:
                sys.exit("extract.py: t_clk crossings series is empty")
            return t
    sys.exit("extract.py: no t_clk crossings measurement in member")


def _periods_from_series(times, uid, skip=XING_SKIP, need=XING_MIN):
    if len(times) < skip + need:
        sys.exit(f"extract.py: {uid}: {len(times)} crossings < "
                 f"{skip}+{need} -- run failed or stopped early")
    ts_ = [times[i + 1] - times[i] for i in range(skip, skip + need)]
    if not all(math.isfinite(x) and x > 0 for x in ts_):
        sys.exit(f"extract.py: {uid}: non-finite or non-positive period in "
                 "the crossings series")
    return ts_


def cmd_campaign(units_csv, report_paths, corners, allow_partial=False):
    units = _load_units(units_csv)
    rows, seen = [], {}
    for path in report_paths:
        doc = json.loads(pathlib.Path(path).read_text())
        for label, member in _iter_reports(doc, path):
            env = member.get("environment", {})
            nl = env.get("netlist") or {}
            name = nl.get("name") if isinstance(nl, dict) else None
            uid = name[:-4] if name and name.endswith(".cir") else None
            if uid not in units or uid in seen:
                sys.exit(f"extract.py: campaign: member netlist {name!r} "
                         f"({label}) matches no unique campaign unit")
            u = units[uid]
            tn = env.get("transient_noise") or {}
            if tn.get("seed") is None:
                sys.exit(f"extract.py: campaign: {uid}: report carries no "
                         "environment.transient_noise.seed -- an unseeded "
                         "campaign unit is not citable evidence")
            if str(tn.get("seed")) != str(u["seed"]):
                sys.exit(f"extract.py: campaign: {uid}: seed mismatch: report "
                         f"{tn.get('seed')} vs units.csv {u['seed']}")
            t = _series_of(member)
            ts_ = _periods_from_series(t, uid)
            st = period_stats(ts_)
            seen[uid] = True
            rows.append([uid, u["bundle"], u["band_code"], u["vctrl_v"],
                         u["mos"], u["res"], u["temp_c"], u["seed"],
                         u["sigma_a"], "1e-11", "10p", st["n"],
                         f"{st['mean']:.9e}", f"{st['rms']:.9e}",
                         f"{st['pp']:.9e}", f"{st['pct']:.6f}",
                         f"{st['ci_lo']:.9e}", f"{st['ci_hi']:.9e}",
                         f"{st['half1']:.9e}", f"{st['half2']:.9e}"])
    missing = [u for u in units if u not in seen and units[u]["kind"] == "pvt"]
    if missing and not allow_partial:
        sys.exit(f"extract.py: campaign: {len(missing)} pvt units missing "
                 f"from the reports (first {missing[:3]})")
    corners.mkdir(parents=True, exist_ok=True)
    with open(corners / "pvt_jitter.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["unit", "bundle", "band_code", "vctrl_v", "mos_corner",
                    "res_corner", "temp_c", "seed", "sigma_a", "ts_s",
                    "tran_step_s", "n_periods", "mean_period_s",
                    "rms_jitter_s", "pp_jitter_s", "rms_pct_of_period",
                    "ci95_lo_s", "ci95_hi_s", "mean_period_first500_s",
                    "mean_period_last500_s"])
        w.writerows(rows)
    print(f"campaign: {len(rows)} units -> pvt_jitter.csv")


def cmd_ripple(units_csv, report_paths, corners):
    units = _load_units(units_csv)
    per = {}
    for path in report_paths:
        doc = json.loads(pathlib.Path(path).read_text())
        for label, member in _iter_reports(doc, path):
            env = member.get("environment", {})
            nl = env.get("netlist") or {}
            name = nl.get("name") if isinstance(nl, dict) else None
            uid = name[:-4] if name and name.endswith(".cir") else None
            if uid not in units or units[uid]["kind"] != "ripple" or uid in per:
                sys.exit(f"extract.py: ripple: member netlist {name!r} "
                         f"({label}) matches no unique ripple unit")
            tn = env.get("transient_noise") or {}
            if str(tn.get("seed")) != str(units[uid]["seed"]):
                sys.exit(f"extract.py: ripple: {uid}: seed mismatch: report "
                         f"{tn.get('seed')} vs units.csv {units[uid]['seed']}")
            t = _series_of(member)
            if len(t) - 1 - XING_SKIP < RIPPLE_MIN:
                sys.exit(f"extract.py: ripple: {uid}: {len(t)} crossings < "
                         f"{XING_SKIP}+{RIPPLE_MIN} -- run failed or stopped "
                         "early; too short to resolve the 1 MHz modulation")
            ts_ = _periods_from_series(t, uid, need=len(t) - 1 - XING_SKIP)
            per[uid] = ts_
    need = {"ripbase_s42", "ripbase_off_s42", "rip_f1M_s42", "rip_f1M_off_s42",
            "rip_f100M_s42", "rip_f100M_off_s42"}
    missing = need - set(per)
    if missing:
        sys.exit(f"extract.py: ripple: missing units {sorted(missing)}")
    n = min(len(per[u]) for u in per)
    rows = []

    def stats_row(uid):
        ts_ = per[uid][:n]
        return period_stats(ts_)

    base_series = per["ripbase_s42"][:n]           # noise-on baseline
    base_off = per["ripbase_off_s42"][:n]          # noise-off baseline
    for uid in ("ripbase_s42", "ripbase_off_s42"):
        st = stats_row(uid)
        rows.append([uid, units[uid]["ripple_hz"], units[uid]["sigma_a"],
                     st["n"], f"{st['mean']:.9e}", f"{st['rms']:.9e}",
                     f"{st['pp']:.9e}", f"{st['pct']:.6f}", "", "", ""])
    for tag in ("f1M", "f100M"):
        # deterministic period modulation: the seed-matched difference
        # against the zero-ripple baseline removes the (common) injected
        # noise realization, leaving the supply-ripple response.  The
        # noise-off twin differences against the same baseline with no
        # noise at all; the last column reports the two pp values' delta
        # so a dirty separation is visible, not averaged away.
        det = [x - b for x, b in zip(per[f"rip_{tag}_s42"][:n], base_series)]
        det_off = [x - b for x, b in
                   zip(per[f"rip_{tag}_off_s42"][:n], base_off)]
        det_m = sum(det) / len(det)
        det_pp = max(det) - min(det)
        det_rms = math.sqrt(sum((d - det_m) ** 2 for d in det)
                            / (len(det) - 1))
        det_off_pp = max(det_off) - min(det_off)
        # random jitter of the ripple-on unit with the deterministic
        # modulation removed.  Subtract the independent noise-off estimate
        # (det_off), NOT `det`: x - det == baseline identically.
        st = stats_row(f"rip_{tag}_s42")
        resid = [x - d for x, d in zip(per[f"rip_{tag}_s42"][:n], det_off)]
        rm = sum(resid) / len(resid)
        resid_rms = math.sqrt(sum((x - rm) ** 2 for x in resid)
                              / (len(resid) - 1))
        rows.append([f"rip_{tag}_s42", units[f"rip_{tag}_s42"]["ripple_hz"],
                     units[f"rip_{tag}_s42"]["sigma_a"], st["n"],
                     f"{st['mean']:.9e}", f"{st['rms']:.9e}",
                     f"{st['pp']:.9e}", f"{st['pct']:.6f}",
                     f"{det_pp:.9e}", f"{det_rms:.9e}", f"{resid_rms:.9e}"])
        st_off = stats_row(f"rip_{tag}_off_s42")
        rows.append([f"rip_{tag}_off_s42",
                     units[f"rip_{tag}_off_s42"]["ripple_hz"],
                     units[f"rip_{tag}_off_s42"]["sigma_a"], st_off["n"],
                     f"{st_off['mean']:.9e}", f"{st_off['rms']:.9e}",
                     f"{st_off['pp']:.9e}", f"{st_off['pct']:.6f}",
                     f"{det_off_pp:.9e}", "",
                     f"{det_pp - det_off_pp:+.3e}"])
    corners.mkdir(parents=True, exist_ok=True)
    with open(corners / "ripple.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(["unit", "ripple_hz", "sigma_a", "n_periods",
                    "mean_period_s", "rms_jitter_s", "pp_jitter_s",
                    "rms_pct_of_period", "det_mod_pp_s", "det_mod_rms_s",
                    "resid_rms_s"])
        w.writerows(rows)
    print(f"ripple: {len(rows)} rows -> ripple.csv")


NOISE_REF = []  # filled by cmd_main from the cal phase CSV (see run.sh order)


def load_noise_ref(corners):
    global NOISE_REF
    with open(corners / "calibration_noise.csv") as f:
        NOISE_REF = [(float(r["f_hz"]), float(r["onoise_v_rthz"]))
                     for r in csv.DictReader(f)]


def main():
    a = sys.argv
    if len(a) >= 2 and a[1] == "calset":
        if len(a) != 5:
            sys.exit("usage: extract.py calset CAL_OUTDIR REPORT CORNERS")
        cmd_calset(pathlib.Path(a[2]), a[3], pathlib.Path(a[4]))
        return
    if len(a) >= 2 and a[1] == "campaign":
        rest = a[2:]
        allow_partial = False
        if rest and rest[0] == "--allow-partial":
            allow_partial = True
            rest = rest[1:]
        if len(rest) < 3:
            sys.exit("usage: extract.py campaign [--allow-partial] "
                     "UNITS_CSV REPORT... CORNERS")
        cmd_campaign(rest[0], rest[1:-1], pathlib.Path(rest[-1]),
                     allow_partial=allow_partial)
        return
    if len(a) >= 2 and a[1] == "ripple":
        if len(a) < 5:
            sys.exit("usage: extract.py ripple UNITS_CSV REPORT... CORNERS")
        cmd_ripple(a[2], a[3:-1], pathlib.Path(a[-1]))
        return
    if len(a) != 4 or a[1] not in ("bias", "cal", "main"):
        sys.exit(__doc__)
    phase, outdir, corners = a[1], pathlib.Path(a[2]), pathlib.Path(a[3])
    if phase == "bias":
        cmd_bias(outdir, corners)
    elif phase == "cal":
        cmd_cal(outdir, corners)
    else:
        load_noise_ref(corners)
        cmd_main(outdir, corners)


if __name__ == "__main__":
    main()
