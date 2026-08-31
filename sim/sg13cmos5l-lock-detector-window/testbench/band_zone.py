#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/band_zone.py
(issue #76, Part of #16)

HOW WIDE, IN PHASE ERROR, IS THE STATIC PHASE-ERROR ZONE THAT PARKS VWIN
BETWEEN schmitt_hv's TWO TRIP POINTS?

This is the static half of issue #76's deciding measurement, and it costs no
new simulation: ../records/RECORD-003 already published, per corner, both

  * the settled integrating-node voltage at every ladder phase-error point
    (../corners/ladder_raw_hystfix.csv, `vwin_a_avg_v`), and
  * that corner's own schmitt_hv trip points
    (../corners/schmitt_hystfix.csv, `vth_rising_v` / `vth_falling_v`),

and the in-band zone is just the pre-image of the band under the first curve.
Recomputing it from those two committed files -- rather than re-simulating --
also means this analysis cannot silently disagree with the record it builds on.

Reported per corner, in three units, because each answers a different question:
  * in units of the assert window (`twin_r`)  -- comparable with row 16;
  * in units of T_ref                         -- what a phase error actually is;
  * as a fraction of the half-period          -- the share of the phase-error
    axis a static operating point would have to land in to park in the band.

CAVEATS, stated rather than buried:
  * `vwin_a_avg_v` is ladder copy A, which starts DISCHARGED, and RECORD-003's
    run reached `settle_frac` = 0.97-0.99 rather than 1.0.  Copy A therefore
    approaches the equilibrium FROM BELOW, so the settled VWIN used here is a
    slight UNDER-estimate, which biases the reported zone toward slightly
    smaller phase errors.  Copy B's VWIN is not in the CSV, so no two-sided
    bracket is available without a re-run.
  * The ladder is a discrete grid (`gen_ladder.py`'s `hystfix` set), so both
    zone edges are LINEARLY INTERPOLATED between adjacent ladder points.  The
    grid step is 0.25x window below 2.5x and coarser above it, so the edge
    resolution degrades at the slow-f_ref corners whose thresholds sit at
    8-18x the window.
  * MOM-band variants (`ideal-0.20` / `ideal0.20`) are scored against the same
    measured trip points as the `real` variant at the same MOS/temp/supply
    corner: schmitt_hv contains no cap_cmomi instance, so the MOM axis cannot
    move its trip points.

Usage: band_zone.py <corners-dir> [suffix]

`suffix` selects which record's CSV set to score -- `_hystfix` (RECORD-003, the
default) or `_crowbarfix` (RECORD-004) -- and names the output
<corners-dir>/band_zone_static<suffix>.csv.  Running it for both is how
RECORD-004 shows that lengthening schmitt_hv's channels did not widen the
in-band zone it is trying to make cheaper.
"""
import csv
import os
import sys


def parse_tag(tag):
    """mos_tt_res_typ_-40c_3.3v_3p5MHz_real -> (mos, res, temp, vsup, fref, variant)"""
    parts = tag.split("_")
    mos = "_".join(parts[0:2])
    res = "_".join(parts[2:4])
    temp = parts[4][:-1]                 # '-40c' -> '-40'
    vsup = parts[5][:-1]                 # '3.3v' -> '3.3'
    fref = parts[6]
    variant = "_".join(parts[7:])
    return mos, res, temp, vsup, fref, variant


def crossings(pairs, lo, hi):
    """pairs = [(tau_xwin, vwin)] sorted by tau, vwin monotonically DECREASING
    with tau (more phase error -> more discharge).  Return (tau_at_hi, tau_at_lo)
    -- the phase errors at which the settled VWIN crosses the upper and lower
    trip point -- by linear interpolation, or None where the curve never gets
    there within the ladder's reach."""
    def cross(level):
        for i in range(1, len(pairs)):
            t0, v0 = pairs[i - 1]
            t1, v1 = pairs[i]
            if (v0 - level) * (v1 - level) <= 0 and v0 != v1:
                return t0 + (v0 - level) * (t1 - t0) / (v0 - v1)
        return None
    return cross(hi), cross(lo)


def main():
    corners = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "corners")
    corners = os.path.abspath(corners)
    suffix = sys.argv[2] if len(sys.argv) > 2 else "_hystfix"

    trips = {}
    with open(os.path.join(corners, f"schmitt{suffix}.csv")) as f:
        for r in csv.DictReader(f):
            key = (r["mos_corner"], r["temp_c"], r["vsup_v"])
            trips[key] = (float(r["vth_rising_v"]), float(r["vth_falling_v"]))

    meta = {}
    with open(os.path.join(corners, f"ladder{suffix}.csv")) as f:
        for r in csv.DictReader(f):
            if r["twin_r_s"] == "NA":
                continue
            meta[r["corner_tag"]] = r

    raw = {}
    with open(os.path.join(corners, f"ladder_raw{suffix}.csv")) as f:
        for r in csv.DictReader(f):
            raw.setdefault(r["corner_tag"], []).append(
                (float(r["tau_xwin"]), float(r["vwin_a_avg_v"])))

    out = os.path.join(corners, f"band_zone_static{suffix}.csv")
    with open(out, "w") as f:
        f.write("corner_tag,mos_corner,res_corner,temp_c,vsup_v,fref,dut_variant,"
                "twin_r_s,tref_s,vth_rising_v,vth_falling_v,"
                "vwin_at_zero_err_v,vwin_at_max_tau_v,"
                "tau_enter_band_xwin,tau_exit_band_xwin,zone_width_xwin,"
                "zone_width_s,zone_width_pct_of_tref,zone_pct_of_half_period,"
                "zone_enter_pct_of_tref,zone_exit_pct_of_tref,"
                "tau_assert_xwin,tau_deassert_xwin\n")
        for tag in sorted(raw):
            if tag not in meta:
                continue
            mos, res, temp, vsup, fref, variant = parse_tag(tag)
            key = (mos, temp, vsup)
            if key not in trips:
                sys.exit(f"no schmitt trip points for {key} (corner {tag})")
            vth_up, vth_dn = trips[key]
            pairs = sorted(raw[tag])
            t_hi, t_lo = crossings(pairs, vth_dn, vth_up)
            twin = float(meta[tag]["twin_r_s"])
            tref = float(meta[tag]["tref_s"])

            if t_hi is None:
                # settled VWIN never falls to the upper trip point within reach
                cells = ["NA"] * 8
            else:
                enter_pct = 100 * t_hi * twin / tref
                if t_lo is None:
                    # enters the band but the ladder ends before it leaves
                    cells = ["%.4f" % t_hi, ">%.2f" % pairs[-1][0],
                             ">%.4f" % (pairs[-1][0] - t_hi),
                             ">%.6e" % ((pairs[-1][0] - t_hi) * twin),
                             ">%.4f" % (100 * (pairs[-1][0] - t_hi) * twin / tref),
                             ">%.4f" % (200 * (pairs[-1][0] - t_hi) * twin / tref),
                             "%.4f" % enter_pct,
                             ">%.4f" % (100 * pairs[-1][0] * twin / tref)]
                else:
                    w = t_lo - t_hi
                    cells = ["%.4f" % t_hi, "%.4f" % t_lo, "%.4f" % w,
                             "%.6e" % (w * twin),
                             "%.4f" % (100 * w * twin / tref),
                             "%.4f" % (200 * w * twin / tref),
                             "%.4f" % enter_pct,
                             "%.4f" % (100 * t_lo * twin / tref)]
            f.write(",".join([
                tag, mos, res, temp, vsup, fref, variant,
                meta[tag]["twin_r_s"], meta[tag]["tref_s"],
                "%.6e" % vth_up, "%.6e" % vth_dn,
                "%.4f" % pairs[0][1], "%.4f" % pairs[-1][1],
            ] + cells + [
                meta[tag]["tau_assert_xwin"], meta[tag]["tau_deassert_xwin"],
            ]) + "\n")

    with open(out) as f:
        rows = list(csv.DictReader(f))
    print(f"wrote {out} ({len(rows)} corners)", file=sys.stderr)
    for r in rows:
        print(f"  {r['corner_tag']}: zone {r['tau_enter_band_xwin']} -> "
              f"{r['tau_exit_band_xwin']} x window = "
              f"{r['zone_width_pct_of_tref']}% of T_ref", file=sys.stderr)


if __name__ == "__main__":
    main()
