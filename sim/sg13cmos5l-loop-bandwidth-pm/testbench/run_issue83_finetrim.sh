#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-loop-bandwidth-pm/testbench/run_issue83_finetrim.sh
# (issue #83, Part of #16)
#
# Closes the ONE outright gap issue #83 tracks:
#   band=00, mid Kvco interval, f_ref=4.5MHz, slow PVT bundle (n_div=119)
# -- the only bundle reachable at this (band, interval, f_ref) tuple, per
# ../records/RECORD-002-r1-resize-full-fref-range.md "Result at the
# committed geometry". At the existing 2.5/5/10/20/40/80 uA trim ladder, NO
# code meets both `meets_ceiling` and `meets_pm45` simultaneously (2.5u:
# fc under ceiling but PM 43.639 deg, 1.36 deg short; 5u and above: PM
# clears but fc blows the ceiling).
#
# Mitigation (see spec/decision-records/DR-007-cp-icp-trim-fine-code-
# band00-mid-fref4p5.md): a single intermediate trim code, 3.75 uA -- the
# arithmetic midpoint of the existing 2.5/5 uA codes -- measured for the
# `slow` bundle only by
# ../../sg13cmos5l-cp-icp-trim/testbench/run_issue83_finetrim.sh
# (../../sg13cmos5l-cp-icp-trim/corners/results_issue83_finetrim.csv).
# `cp.sch` has no on-chip trim array (design/README.md) -- the "trim code"
# is a mirror reference current an (not-yet-drawn) bias generator would
# deliver, so an intermediate value is a legitimate operating point, not a
# hardware-infeasible one (../../sg13cmos5l-cp-icp-trim/corners/matrix.md).
#
# This is NOT a geometry change: R1/C1/C2 are untouched, so it cannot
# regress any other (band, interval, f_ref) combination in
# ../corners/results_resized.csv -- those rows are computed from the SAME
# unmodified filter and the SAME six original trim codes, none of which
# this script reads or writes.
#
# Writes ../corners/results_resized_issue83_finetrim.csv (same 14-column
# schema as ../corners/results_resized.csv, kept in a SEPARATE file --
# results_resized.csv is not touched).
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_issue83_finetrim.sh

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
# original six-code table, untouched).
icp_rows = load(f"{SIM}/sg13cmos5l-cp-icp-trim/corners/results_issue83_finetrim.csv")

def icp_for_finetrim():
    for r in icp_rows:
        if (r["mos_corner"] == "mos_ss" and r["temp_c"] == "125"
                and r["vdd_v"] == "3.3" and r["iref_a"] == "3.75u"
                and r["state"] == "up" and r["icp_a"] != "NA"):
            return abs(float(r["icp_a"]))
    raise SystemExit("no Icp row for the 3.75u fine-trim code (slow bundle)")

# The exact operating point issue #83 tracks -- read directly off
# ../corners/results_resized.csv's own row for this tuple (bundle=slow,
# band=00, interval=mid, f_ref=4.5MHz, n_div=119) rather than re-deriving
# Kvco from the raw Kvco table, so this script cannot silently drift from
# the tuple the gap was actually measured at.
BAND = "00"
INTERVAL = "mid"
FREF_HZ = 4.5e6
NDIV = 119
KVCO_HZ_PER_V = 1.683806e8
FVCO_HZ = 5.338997e8   # ../corners/results_resized.csv's own row for this tuple
CORNER_RES = "res_wcs"   # slow bundle
TEMP = "125"

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

icp = icp_for_finetrim()
g = gains(icp, KVCO_HZ_PER_V, NDIV)
rows = run_ac("tb_loop_ac_real_resized.sp.tmpl",
              {"@CORNER_RES@": CORNER_RES, "@TEMP@": TEMP, **g},
              "issue83_slow_00_mid_4p5_3p75u")
fc, pm = crossover(rows)
ceil_hz = FREF_HZ / 10.0

out_path = f"{REC}/corners/results_resized_issue83_finetrim.csv"
with open(out_path, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["pvt_bundle", "band_code", "kvco_interval", "kvco_hz_per_v",
                "fvco_hz", "fref_hz", "n_div", "trim_code", "icp_a",
                "fc_hz", "pm_deg", "fc_ceiling_hz", "meets_ceiling",
                "meets_pm45"])
    w.writerow(["slow", BAND, INTERVAL, f"{KVCO_HZ_PER_V:.6e}",
                f"{FVCO_HZ:.6e}",
                f"{FREF_HZ:.6e}", NDIV, "3.75u", f"{icp:.6e}",
                "NA" if fc is None else f"{fc:.6e}",
                "NA" if pm is None else f"{pm:.3f}",
                f"{ceil_hz:.6e}",
                "NA" if fc is None else ("yes" if fc < ceil_hz else "no"),
                "NA" if pm is None else ("yes" if pm >= 45.0 else "no")])

print(f"icp={icp:.6e} fc={fc} pm={pm}", file=sys.stderr)
print(f"wrote {out_path}", file=sys.stderr)
print("done", file=sys.stderr)
PY
