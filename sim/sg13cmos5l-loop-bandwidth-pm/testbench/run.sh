#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-loop-bandwidth-pm/testbench/run.sh
# (issue #27, Part of #16 -- SG13CMOS5L closed-loop PVT campaign)
#
# Closes spec/porting-plan.md row 6/6a (loop bandwidth / phase margin) by
# combining three REAL measurements this repo already owns:
#   - the loop filter's own R1/C1/C2 (and their PVT + MOM-uncertainty band)
#     from ../../sg13cmos5l-loop-filter-momcap/corners/results.csv, plus the
#     real `loop_filter` subckt itself for the nominal MOM point;
#   - the VCO's per-band, per-corner Kvco table from
#     ../../sg13cmos5l-vco-kvco-table/corners/results.csv;
#   - the charge pump's own Icp-vs-trim-code table from
#     ../../sg13cmos5l-cp-icp-trim/corners/results.csv.
#
# Outputs (see ../records/RECORD-001):
#   ../corners/results.csv    as-drawn filter, real `loop_filter` subckt
#   ../corners/mom_band.csv   +/-20% MOM band, lumped-equivalent filter
#   ../corners/proposal.csv   R1-resizing proposal sweep (NOT the committed
#                             design -- kept in its own file for that reason)
#   ../corners/crosscheck.txt real-subckt vs. lumped-equivalent agreement at
#                             the nominal point
#
# APPEND-ONLY EVIDENCE (sim/README.md).  Issue #41 (DR-006) resized R1 (the
# "R1 x20" proposal above) and this script now ALSO runs Part D below: the
# RESIZED real `loop_filter` subckt, re-verified against the FULL amended
# `f_ref` range from DR-005 (spec/porting-plan.md row 2, 3.5-24.4 MHz; row 3
# N in [64,127]) rather than the single f_ref=25 MHz point Parts A-C above
# were computed at. Part D's own outputs (../corners/results_resized.csv,
# ../corners/crosscheck_resized.txt) are NEW files -- Parts A-C above and
# ../records/RECORD-001's citations of them are untouched. See
# ../records/RECORD-002.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
SIM_ROOT="$(cd "$RECORD_DIR/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"

# The real-subckt variant instantiates cap_cmomi (OSDI) and rppd (r3_cmc
# OSDI), so both must be loaded from a .spiceinit in ngspice's cwd -- ngspice
# only honors `osdi` at startup, not from an in-netlist .control block (a
# finding the predecessor loop-filter record already documents).
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/cap_cmomi.osdi
osdi $OSDI/cap_cmomf.osdi
osdi $OSDI/r3_cmc.osdi
EOF

# OSDI host-architecture preflight (issue #59).  cap_cmomi.osdi/cap_cmomf.osdi
# are architecture-specific binaries TRACKED in the upstream ihp-sg13cmos5l git
# repo (prebuilt x86-64 ELF) rather than host-local build products like
# psp103/r3_cmc, so on a non-x86-64 host they fail ngspice's dlopen with
# "Error opening osdi lib ... couldn't be loaded" -- which reads like a broken
# deck and is not one.  Fail here instead, naming the one-command rebuild
# (ihp-sg13cmos5l/libs.tech/verilog-a/openvaf-compile-va.sh).  Full finding and
# the cross-check protocol for a rebuilt model: ../../PORTING-osdi-host-arch.md
"$HERE/../../tools/check-osdi-arch.sh" --quiet \
  "$OSDI/cap_cmomi.osdi" "$OSDI/cap_cmomf.osdi" "$OSDI/r3_cmc.osdi"

cp "$RECORD_DIR/netlist-snapshots/loop_filter.spice" "$WORK/loop_filter_snap.spice"
cp "$RECORD_DIR/netlist-snapshots/loop_filter_resized.spice" "$WORK/loop_filter_snap_resized.spice"

export PDK_ROOT PDK
export WORK HERE RECORD_DIR SIM_ROOT

python3 - <<'PY'
import csv, math, os, subprocess, sys

WORK = os.environ["WORK"]
HERE = os.environ["HERE"]
REC  = os.environ["RECORD_DIR"]
SIM  = os.environ["SIM_ROOT"]
PDK_ROOT = os.environ["PDK_ROOT"]
PDK  = os.environ["PDK"]

# ---------------------------------------------------------------------------
# Inputs: three committed, real measurement records.
# ---------------------------------------------------------------------------
def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))

kvco_rows = load(f"{SIM}/sg13cmos5l-vco-kvco-table/corners/results.csv")
rc_rows   = load(f"{SIM}/sg13cmos5l-loop-filter-momcap/corners/results.csv")
icp_rows  = load(f"{SIM}/sg13cmos5l-cp-icp-trim/corners/results.csv")

# PVT bundles, kept identical to the Kvco record's own 3-bundle convention so
# the VCO term and the filter term are never taken from mismatched corners.
BUNDLES = {
    #  name : (kvco bundle, cornerRES section, temp C, cp mos corner)
    "typ":  ("typ",  "res_typ", "27",  "mos_tt"),
    "slow": ("slow", "res_wcs", "125", "mos_ss"),
    "fast": ("fast", "res_bcs", "-40", "mos_ff"),
}

# Trim codes (mirror reference currents) -- the same ladder the cp record swept.
TRIM_CODES = ["2.5u", "5u", "10u", "20u", "40u", "80u"]

def icp_for(bundle, code):
    """Measured |Icp| (A) at VDD/2 for this trim code and PVT bundle.

    Uses the `up` state (the pump sourcing into the filter) at 3.3 V and the
    bundle's own MOS corner/temperature -- a real DC measurement of the
    committed cp subckt, not a design intent."""
    _, _, temp, mos = BUNDLES[bundle]
    for r in icp_rows:
        if (r["mos_corner"] == mos and r["temp_c"] == temp
                and r["vdd_v"] == "3.3" and r["iref_a"] == code
                and r["state"] == "up" and r["icp_a"] != "NA"):
            return abs(float(r["icp_a"]))
    raise SystemExit(f"no Icp row for {bundle}/{code}")

def rc_for(bundle, mom_frac="0.00"):
    _, res, temp, _ = BUNDLES[bundle]
    for r in rc_rows:
        if (r["res_corner"] == res and r["temp_c"] == temp
                and r["mom_frac"] == mom_frac):
            return float(r["r1_ohm"]), float(r["c1_f"]), float(r["c2_f"])
    raise SystemExit(f"no R/C row for {bundle}/{mom_frac}")

# Resized R1 (issue #41, DR-006) -- reads
# ../../sg13cmos5l-loop-filter-momcap/corners/results_resized.csv, the
# sibling record's own post-resize R1/C1/C2 measurement, same shape as
# rc_for() above.
rc_rows_resized = load(f"{SIM}/sg13cmos5l-loop-filter-momcap/corners/results_resized.csv")

def rc_for_resized(bundle, mom_frac="0.00"):
    _, res, temp, _ = BUNDLES[bundle]
    for r in rc_rows_resized:
        if (r["res_corner"] == res and r["temp_c"] == temp
                and r["mom_frac"] == mom_frac):
            return float(r["r1_ohm"]), float(r["c1_f"]), float(r["c2_f"])
    raise SystemExit(f"no resized R/C row for {bundle}/{mom_frac}")

# Local (secant) Kvco over two VCTRL intervals of the committed table, plus the
# mid-interval frequency each slope belongs to. Kvco is measurably non-constant
# across the sweep (that record's own finding), so a single scalar would
# misstate the loop gain -- both intervals are carried through here.
INTERVALS = {"mid": ("0.9", "1.5"), "top": ("2.1", "2.7")}

# Part D (issue #41) extends this to a third, LOW interval (VCTRL 0.3-0.9V)
# -- the only pair of measured VCTRL points in
# ../../sg13cmos5l-vco-kvco-table/corners/results.csv that brackets the VCO's
# own measured floor (445.3 MHz at VCTRL=0.3V, DR-005's own cited number).
# Parts A-C above intentionally never used this interval (RECORD-001 scoped
# to mid/top only); it is added here, in a separate dict, specifically
# because DR-005's amended f_ref floor (3.51 MHz) is only reachable near this
# VCTRL region -- see RECORD-002 "Why a third Kvco interval".
INTERVALS_EXT = {"low": ("0.3", "0.9"), "mid": ("0.9", "1.5"), "top": ("2.1", "2.7")}

def kvco_points(bundle, band, intervals=INTERVALS):
    kb = BUNDLES[bundle][0]
    f = {}
    for r in kvco_rows:
        if r["pvt_bundle"] == kb and r["band_code"] == band and r["freq_hz"] != "NA":
            f[r["vctrl_v"]] = float(r["freq_hz"])
    out = {}
    for label, (v0, v1) in intervals.items():
        kv = (f[v1] - f[v0]) / (float(v1) - float(v0))       # Hz/V
        fo = 0.5 * (f[v0] + f[v1])                            # Hz
        out[label] = (kv, fo)
    return out

# ---------------------------------------------------------------------------
# ngspice driver + crossover extraction
# ---------------------------------------------------------------------------
def run_ac(tmpl, subs, tag):
    src = open(f"{HERE}/{tmpl}").read()
    for k, v in subs.items():
        src = src.replace(k, str(v))
    # @PDK_ROOT@/@PDK@: resolved filesystem path -- ngspice's `.lib`/
    # `.include` parser does not expand shell/OS environment variables
    # (issue #44), so tb_loop_ac_real.sp.tmpl's corner-lib lines must be
    # substituted here just like every other @TOKEN@.
    src = src.replace("@PDK_ROOT@", PDK_ROOT).replace("@PDK@", PDK)
    path = f"{WORK}/tb_{tag}.sp"
    open(path, "w").write(src)
    result = subprocess.run(["ngspice", "-b", f"tb_{tag}.sp"], cwd=WORK,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)
    if result.returncode != 0:
        print(f"ngspice failed for {tag} (exit {result.returncode}):",
              file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        raise SystemExit(f"ngspice failed for {tag} -- exit {result.returncode}")
    rows = []
    for line in open(f"{WORK}/ac.dat"):
        p = line.split()
        if len(p) >= 4:
            try:
                rows.append((float(p[0]), float(p[1]), float(p[3])))
            except ValueError:
                pass
    return rows

def crossover(rows):
    """Unity-gain frequency (Hz) and phase margin (deg), log-log interpolated.

    Returns (None, None) when |T| never crosses 1 inside the swept decade
    range -- reported as NA rather than extrapolated."""
    prev = None
    for f, m, ph in rows:
        if prev and prev[1] >= 1.0 > m and m > 0:
            f0, m0, p0 = prev
            t = (0.0 - math.log10(m0)) / (math.log10(m) - math.log10(m0))
            fc = 10 ** (math.log10(f0) + t * (math.log10(f) - math.log10(f0)))
            pm = 180.0 + (p0 + t * (ph - p0))
            return fc, pm
        prev = (f, m, ph)
    return None, None

def gains(icp, kvco_hz, n):
    return {"@KD@": repr(icp / (2 * math.pi)),
            "@KV@": repr(2 * math.pi * kvco_hz),
            "@INVN@": repr(1.0 / n)}

# Reference frequencies to test the sampled-loop ceiling against. Row 2 of
# spec/porting-plan.md carries a 1-25 MHz reference interface; N is capped at
# 64 by row 3, so a scenario is only generated when the required N lands
# inside [4, 64] for the VCO frequency actually measured.
FREFS_HZ = [25e6, 10e6]

# ---------------------------------------------------------------------------
# Part A -- as-drawn filter, REAL loop_filter subckt
# ---------------------------------------------------------------------------
res_path = f"{REC}/corners/results.csv"
with open(res_path, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["pvt_bundle", "band_code", "kvco_interval", "kvco_hz_per_v",
                "fvco_hz", "fref_hz", "n_div", "trim_code", "icp_a",
                "fc_hz", "pm_deg", "fc_ceiling_hz", "meets_ceiling",
                "meets_pm45"])
    n_runs = 0
    for bundle in BUNDLES:
        _, res_corner, temp, _ = BUNDLES[bundle]
        for band in ("00", "11"):
            for interval, (kvco, fvco) in kvco_points(bundle, band).items():
                for fref in FREFS_HZ:
                    ndiv = round(fvco / fref)
                    if not (4 <= ndiv <= 64):
                        continue
                    for code in TRIM_CODES:
                        icp = icp_for(bundle, code)
                        tag = f"A_{bundle}_{band}_{interval}_{int(fref/1e6)}_{code}"
                        rows = run_ac("tb_loop_ac_real.sp.tmpl",
                                      {"@CORNER_RES@": res_corner,
                                       "@TEMP@": temp, **gains(icp, kvco, ndiv)},
                                      tag)
                        fc, pm = crossover(rows)
                        ceil_hz = fref / 10.0
                        w.writerow([bundle, band, interval, f"{kvco:.6e}",
                                    f"{fvco:.6e}", f"{fref:.6e}", ndiv, code,
                                    f"{icp:.6e}",
                                    "NA" if fc is None else f"{fc:.6e}",
                                    "NA" if pm is None else f"{pm:.3f}",
                                    f"{ceil_hz:.6e}",
                                    "NA" if fc is None else ("yes" if fc < ceil_hz else "no"),
                                    "NA" if pm is None else ("yes" if pm >= 45.0 else "no")])
                        n_runs += 1
                        print(f"[A {n_runs}] {tag}: fc={fc} pm={pm}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Part A' -- cross-check: real subckt vs. lumped equivalent at the nominal point
# ---------------------------------------------------------------------------
bundle, band, interval, fref = "typ", "11", "top", 25e6
kvco, fvco = kvco_points(bundle, band)[interval]
ndiv = round(fvco / fref)
icp = icp_for(bundle, "10u")
r1, c1, c2 = rc_for(bundle, "0.00")
g = gains(icp, kvco, ndiv)
rows_real = run_ac("tb_loop_ac_real.sp.tmpl",
                   {"@CORNER_RES@": BUNDLES[bundle][1], "@TEMP@": BUNDLES[bundle][2], **g},
                   "X_real")
rows_lump = run_ac("tb_loop_ac_lumped.sp.tmpl",
                   {"@TEMP@": BUNDLES[bundle][2], "@R1@": repr(r1),
                    "@C1@": repr(c1), "@C2@": repr(c2), **g},
                   "X_lump")
fc_r, pm_r = crossover(rows_real)
fc_l, pm_l = crossover(rows_lump)
with open(f"{REC}/corners/crosscheck.txt", "w") as fh:
    fh.write(
        "Cross-check: real `loop_filter` subckt vs. lumped R/C equivalent built\n"
        "from the predecessor record's own measured R1/C1/C2, at the nominal\n"
        f"point (bundle={bundle}, band={band}, Kvco interval={interval},\n"
        f"f_ref={fref/1e6:.0f} MHz, N={ndiv}, trim code 10u, mom_frac=0.00).\n\n"
        f"  R1 = {r1:.6e} ohm   C1 = {c1:.6e} F   C2 = {c2:.6e} F\n"
        f"  Icp = {icp:.6e} A   Kvco = {kvco:.6e} Hz/V\n\n"
        f"  real subckt : f_c = {fc_r:.6e} Hz   PM = {pm_r:.3f} deg\n"
        f"  lumped R/C  : f_c = {fc_l:.6e} Hz   PM = {pm_l:.3f} deg\n"
        f"  difference  : f_c {100*(fc_l-fc_r)/fc_r:+.3f} %   PM {pm_l-pm_r:+.3f} deg\n")
print("[X] crosscheck written", file=sys.stderr)

# ---------------------------------------------------------------------------
# Part B -- MOM-uncertainty band propagated to the loop level
# ---------------------------------------------------------------------------
with open(f"{REC}/corners/mom_band.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["pvt_bundle", "band_code", "kvco_interval", "mom_frac",
                "r1_ohm", "c1_f", "c2_f", "trim_code", "icp_a",
                "fc_hz", "pm_deg"])
    for bundle in BUNDLES:
        kvco, fvco = kvco_points(bundle, "11")["top"]
        ndiv = round(fvco / 25e6)
        for mom in ("-0.20", "0.00", "0.20"):
            r1, c1, c2 = rc_for(bundle, mom)
            for code in TRIM_CODES:
                icp = icp_for(bundle, code)
                rows = run_ac("tb_loop_ac_lumped.sp.tmpl",
                              {"@TEMP@": BUNDLES[bundle][2], "@R1@": repr(r1),
                               "@C1@": repr(c1), "@C2@": repr(c2),
                               **gains(icp, kvco, ndiv)},
                              f"B_{bundle}_{mom}_{code}")
                fc, pm = crossover(rows)
                w.writerow([bundle, "11", "top", mom, f"{r1:.6e}", f"{c1:.6e}",
                            f"{c2:.6e}", code, f"{icp:.6e}",
                            "NA" if fc is None else f"{fc:.6e}",
                            "NA" if pm is None else f"{pm:.3f}"])
                print(f"[B] {bundle}/{mom}/{code}: fc={fc} pm={pm}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Part C -- filter-resizing PROPOSAL (not the committed design)
# ---------------------------------------------------------------------------
with open(f"{REC}/corners/proposal.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["pvt_bundle", "r1_scale", "r1_ohm", "c1_f", "c2_f",
                "fref_hz", "n_div", "trim_code", "icp_a", "fc_hz", "pm_deg",
                "fc_ceiling_hz", "meets_both"])
    for bundle in BUNDLES:
        kvco, fvco = kvco_points(bundle, "11")["top"]
        fref = 25e6
        ndiv = round(fvco / fref)
        r1n, c1, c2 = rc_for(bundle, "0.00")
        for scale in (1, 5, 10, 20, 50, 100):
            r1 = r1n * scale
            for code in TRIM_CODES:
                icp = icp_for(bundle, code)
                rows = run_ac("tb_loop_ac_lumped.sp.tmpl",
                              {"@TEMP@": BUNDLES[bundle][2], "@R1@": repr(r1),
                               "@C1@": repr(c1), "@C2@": repr(c2),
                               **gains(icp, kvco, ndiv)},
                              f"C_{bundle}_{scale}_{code}")
                fc, pm = crossover(rows)
                ok = (fc is not None and pm is not None
                      and fc < fref / 10.0 and pm >= 45.0)
                w.writerow([bundle, scale, f"{r1:.6e}", f"{c1:.6e}", f"{c2:.6e}",
                            f"{fref:.6e}", ndiv, code, f"{icp:.6e}",
                            "NA" if fc is None else f"{fc:.6e}",
                            "NA" if pm is None else f"{pm:.3f}",
                            f"{fref/10.0:.6e}", "yes" if ok else "no"])
                print(f"[C] {bundle}/x{scale}/{code}: fc={fc} pm={pm} ok={ok}",
                      file=sys.stderr)

# ---------------------------------------------------------------------------
# Part D (issue #41, DR-006) -- RESIZED real `loop_filter` subckt, verified
# against the FULL amended f_ref range (DR-005: 3.5-24.4 MHz, N in [64,127]),
# not just the single 25 MHz point Parts A-C were computed at. Both bands,
# all three Kvco intervals (including "low", the near-VCO-floor interval
# Parts A-C never used) -- this is the committed, resized design, so it gets
# the full matrix Part A gave the as-drawn filter, not just the "band 11 /
# top interval" slice Part C's proposal used.
# ---------------------------------------------------------------------------
FREFS_HZ_AMENDED = [3.6e6, 4.5e6, 5.5e6, 6.5e6, 7.5e6, 9e6, 11e6, 13e6,
                    16e6, 19e6, 22e6, 24.4e6]

res_path_resized = f"{REC}/corners/results_resized.csv"
with open(res_path_resized, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["pvt_bundle", "band_code", "kvco_interval", "kvco_hz_per_v",
                "fvco_hz", "fref_hz", "n_div", "trim_code", "icp_a",
                "fc_hz", "pm_deg", "fc_ceiling_hz", "meets_ceiling",
                "meets_pm45"])
    n_runs = 0
    for bundle in BUNDLES:
        _, res_corner, temp, _ = BUNDLES[bundle]
        for band in ("00", "11"):
            for interval, (kvco, fvco) in kvco_points(bundle, band, INTERVALS_EXT).items():
                for fref in FREFS_HZ_AMENDED:
                    ndiv = round(fvco / fref)
                    if not (64 <= ndiv <= 127):
                        continue
                    for code in TRIM_CODES:
                        icp = icp_for(bundle, code)
                        tag = f"D_{bundle}_{band}_{interval}_{fref/1e6:.2f}_{code}".replace(".", "p")
                        rows = run_ac("tb_loop_ac_real_resized.sp.tmpl",
                                      {"@CORNER_RES@": res_corner,
                                       "@TEMP@": temp, **gains(icp, kvco, ndiv)},
                                      tag)
                        fc, pm = crossover(rows)
                        ceil_hz = fref / 10.0
                        w.writerow([bundle, band, interval, f"{kvco:.6e}",
                                    f"{fvco:.6e}", f"{fref:.6e}", ndiv, code,
                                    f"{icp:.6e}",
                                    "NA" if fc is None else f"{fc:.6e}",
                                    "NA" if pm is None else f"{pm:.3f}",
                                    f"{ceil_hz:.6e}",
                                    "NA" if fc is None else ("yes" if fc < ceil_hz else "no"),
                                    "NA" if pm is None else ("yes" if pm >= 45.0 else "no")])
                        n_runs += 1
                        print(f"[D {n_runs}] {tag}: fc={fc} pm={pm}", file=sys.stderr)

# Part D' -- cross-check: resized real subckt vs. resized lumped equivalent,
# at a nominal point within the amended range (typ bundle, band 11, top
# interval, f_ref=19 MHz -- inside [3.5,24.4] MHz and giving N=66, inside
# DR-005's amended [64,127] range; matching Part A' style otherwise).
bundle, band, interval, fref = "typ", "11", "top", 19e6
kvco, fvco = kvco_points(bundle, band, INTERVALS_EXT)[interval]
ndiv = round(fvco / fref)
icp = icp_for(bundle, "10u")
r1r, c1r, c2r = rc_for_resized(bundle, "0.00")
g = gains(icp, kvco, ndiv)
rows_real_r = run_ac("tb_loop_ac_real_resized.sp.tmpl",
                     {"@CORNER_RES@": BUNDLES[bundle][1], "@TEMP@": BUNDLES[bundle][2], **g},
                     "Xr_real")
rows_lump_r = run_ac("tb_loop_ac_lumped.sp.tmpl",
                     {"@TEMP@": BUNDLES[bundle][2], "@R1@": repr(r1r),
                      "@C1@": repr(c1r), "@C2@": repr(c2r), **g},
                     "Xr_lump")
fc_rr, pm_rr = crossover(rows_real_r)
fc_lr, pm_lr = crossover(rows_lump_r)
with open(f"{REC}/corners/crosscheck_resized.txt", "w") as fh:
    fh.write(
        "Cross-check (issue #41, DR-006): RESIZED real `loop_filter` subckt\n"
        "vs. lumped R/C equivalent built from the resized filter's own\n"
        "measured R1/C1/C2 (sg13cmos5l-loop-filter-momcap RECORD-002), at a\n"
        f"nominal point inside the amended f_ref range (bundle={bundle},\n"
        f"band={band}, Kvco interval={interval}, f_ref={fref/1e6:.0f} MHz,\n"
        f"N={ndiv}, trim code 10u, mom_frac=0.00).\n\n"
        f"  R1 = {r1r:.6e} ohm   C1 = {c1r:.6e} F   C2 = {c2r:.6e} F\n"
        f"  Icp = {icp:.6e} A   Kvco = {kvco:.6e} Hz/V\n\n"
        f"  real subckt : f_c = {fc_rr:.6e} Hz   PM = {pm_rr:.3f} deg\n"
        f"  lumped R/C  : f_c = {fc_lr:.6e} Hz   PM = {pm_lr:.3f} deg\n"
        f"  difference  : f_c {100*(fc_lr-fc_rr)/fc_rr:+.3f} %   PM {pm_lr-pm_rr:+.3f} deg\n")
print("[X'] crosscheck_resized written", file=sys.stderr)

print("done", file=sys.stderr)
PY
