#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-loop-bandwidth-pm/testbench/run_issue79_finetrim.sh
# (issue #79, Part of #16)
#
# Closes the ONE outright gap issue #79 tracks:
#   band=00, LOW Kvco interval, f_ref=4.5MHz -- reachable at ALL THREE PVT
#   bundles (n_div=127/114/103 for fast/typ/slow), unlike issue #83's own
#   gap (a DIFFERENT tuple -- band=00, MID interval -- reachable only at the
#   `slow` bundle).
# ../records/RECORD-002-r1-resize-full-fref-range.md's own six-code ladder
# (2.5/5/10/20/40/80 uA) leaves this open: at 10 uA, `typ`/`slow` both pass
# (47.624/52.226 deg PM, real margin), but `fast` (the binding bundle) is
# 0.87 deg short of the 45 deg floor (44.127 deg, fc=345923.9 Hz, comfortably
# under the 450 kHz ceiling). At 20 uA, PM clears everywhere but fc blows
# the ceiling for ALL THREE bundles (fast/typ/slow: 583267/622503/721683 Hz,
# all > 450 kHz).
#
# Mitigation (see
# spec/decision-records/DR-008-cp-icp-trim-fine-code-band00-low-fref4p5.md):
# a single intermediate trim code, 11 uA, measured for all three PVT bundles
# by
# ../../sg13cmos5l-cp-icp-trim/testbench/run_issue79_finetrim.sh
# (../../sg13cmos5l-cp-icp-trim/corners/results_issue79_finetrim.csv).
# Unlike issue #83's gap (a single binding bundle, so any code above the PM
# floor and below the fc ceiling worked, wide margin available), THIS gap
# has DIFFERENT bundles binding at each edge of the feasible Icp window --
# `fast`'s PM=45 deg floor near 10.6 uA, `slow`'s fc=ceiling near
# 11.47 uA -- so the window is narrow (~0.85 uA wide) and 11 uA was chosen
# close to that window's own arithmetic midpoint, not an arbitrary round
# number with wide margin to spare. See the decision record's "Decision"
# section for the real-subckt scan that established both edges.
#
# This is NOT a geometry change: R1/C1/C2 are untouched, so it cannot
# regress any other (band, interval, f_ref) combination in
# ../corners/results_resized.csv -- those rows are computed from the SAME
# unmodified filter and the SAME six original trim codes, none of which
# this script reads or writes. It is also independent of issue #83's own
# 3.75 uA fine-trim code (a different tuple, a different corners file).
#
# Writes ../corners/results_resized_issue79_finetrim.csv (same 14-column
# schema as ../corners/results_resized.csv, kept in a SEPARATE file --
# results_resized.csv and results_resized_issue83_finetrim.csv are neither
# of them touched).
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_issue79_finetrim.sh

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SIM_ROOT="$(cd "$RECORD_DIR/.." && pwd)"

cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/cap_cmomi.osdi
osdi $OSDI/cap_cmomf.osdi
osdi $OSDI/r3_cmc.osdi
EOF

"$HERE/../../tools/check-osdi-arch.sh" --quiet \
  "$OSDI/cap_cmomi.osdi" "$OSDI/cap_cmomf.osdi" "$OSDI/r3_cmc.osdi"

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

def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))

# The one new Icp measurement this record's own cp-icp-trim companion script
# produced -- NOT ../../sg13cmos5l-cp-icp-trim/corners/results.csv (the
# original six-code table) and NOT results_issue83_finetrim.csv (a
# different tuple's fine-trim code).
icp_rows = load(f"{SIM}/sg13cmos5l-cp-icp-trim/corners/results_issue79_finetrim.csv")

def icp_for_finetrim(mos, temp):
    for r in icp_rows:
        if (r["mos_corner"] == mos and r["temp_c"] == temp
                and r["vdd_v"] == "3.3" and r["iref_a"] == "11u"
                and r["state"] == "up" and r["icp_a"] != "NA"):
            return abs(float(r["icp_a"]))
    raise SystemExit(f"no Icp row for the 11u fine-trim code ({mos}/{temp})")

# The exact operating point issue #79 tracks -- read directly off
# ../corners/results_resized.csv's own rows for this tuple (band=00,
# interval=low, f_ref=4.5MHz), for all three PVT bundles, rather than
# re-deriving Kvco/fvco/n_div from the raw Kvco table, so this script
# cannot silently drift from the exact operating point the gap was
# actually measured at.
BAND = "00"
INTERVAL = "low"
FREF_HZ = 4.5e6
CEIL_HZ = FREF_HZ / 10.0

# bundle: (res_corner, temp_c, mos_corner, kvco_hz_per_v, fvco_hz, n_div)
BUNDLES = {
    "fast": ("res_bcs", "-40", "mos_ff", 7.352722e7, 5.702764e8, 127),
    "typ":  ("res_typ", "27",  "mos_tt", 6.519822e7, 5.135223e8, 114),
    "slow": ("res_wcs", "125", "mos_ss", 6.354232e7, 4.643229e8, 103),
}

def run_ac(tmpl, subs, tag):
    src = open(f"{HERE}/{tmpl}").read()
    for k, v in subs.items():
        src = src.replace(k, str(v))
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

out_path = f"{REC}/corners/results_resized_issue79_finetrim.csv"
with open(out_path, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["pvt_bundle", "band_code", "kvco_interval", "kvco_hz_per_v",
                "fvco_hz", "fref_hz", "n_div", "trim_code", "icp_a",
                "fc_hz", "pm_deg", "fc_ceiling_hz", "meets_ceiling",
                "meets_pm45"])
    for bundle, (res_corner, temp, mos, kvco, fvco, ndiv) in BUNDLES.items():
        icp = icp_for_finetrim(mos, temp)
        g = gains(icp, kvco, ndiv)
        rows = run_ac("tb_loop_ac_real_resized.sp.tmpl",
                      {"@CORNER_RES@": res_corner, "@TEMP@": temp, **g},
                      f"issue79_{bundle}_00_low_4p5_11u")
        fc, pm = crossover(rows)
        w.writerow([bundle, BAND, INTERVAL, f"{kvco:.6e}", f"{fvco:.6e}",
                    f"{FREF_HZ:.6e}", ndiv, "11u", f"{icp:.6e}",
                    "NA" if fc is None else f"{fc:.6e}",
                    "NA" if pm is None else f"{pm:.3f}",
                    f"{CEIL_HZ:.6e}",
                    "NA" if fc is None else ("yes" if fc < CEIL_HZ else "no"),
                    "NA" if pm is None else ("yes" if pm >= 45.0 else "no")])
        print(f"[{bundle}] icp={icp:.6e} fc={fc} pm={pm}", file=sys.stderr)

print(f"wrote {out_path}", file=sys.stderr)
print("done", file=sys.stderr)
PY
