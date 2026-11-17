#!/usr/bin/env python3
"""Flatten the four rerun-331 `klt sim` batch reports into one CSV and compare
it with RECORD-004's committed grid.  Usage (from this directory):

    python3 -I post_rerun331.py
"""
import csv, json, math, pathlib

here = pathlib.Path(__file__).resolve().parent
corners = here.parent / "corners"
VARIANTS = ("asdrawn", "long2u", "long4u", "long8u")
rows = []
for v in VARIANTS:
    rep = json.load(open(corners / "rerun331" / f"report_{v}.json"))
    job = rep["environment"]["remote"]["job_id"]
    for c in rep["corners"]:
        m = {x["name"]: x["value"] for x in c["measurements"]}
        vs = c["supply_v"]["vdd"]
        rows.append(dict(
            variant=v, mos_corner=c["process"], temp_c=c["temperature_c"],
            vsup_v=vs, status=c["status"], job_id=job,
            vth_rising_v=m["vth_up"], vth_falling_v=m["vth_dn"],
            hysteresis_v=m["hysteresis"],
            hysteresis_pct_of_vdd=100 * m["hysteresis"] / vs,
            i_peak_rise_a=m["i_peak_rise"],
            v_at_i_peak_rise_v=vs * m["t_peak_rise"] / 2e-6,
            i_peak_fall_a=m["i_peak_fall"],
            v_at_i_peak_fall_v=vs * (4e-6 - m["t_peak_fall"]) / 2e-6,
            i_vdd2_rise_a=abs(m["i_vdd2_rise"]), i_vdd2_fall_a=abs(m["i_vdd2_fall"]),
            i_worst_a=max(m["i_peak_rise"], m["i_peak_fall"]),
            i_rail_lo_a=abs(m["i_rail_lo"]), i_rail_hi_a=abs(m["i_rail_hi"])))
assert len(rows) == 180
out = corners / "schmitt_crowbar_variants_rerun331.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: (f"{x:.6e}" if isinstance(x, float) else x) for k, x in r.items()})

orig = {}
for r in csv.DictReader(open(corners / "schmitt_crowbar_variants.csv")):
    orig[(r["variant"], r["mos_corner"], int(r["temp_c"]), float(r["vsup_v"]))] = r
print("rows:", len(rows), " statuses:", sorted({r["status"] for r in rows}))
for col, oc in (("vth_rising_v", "vth_rising_v"), ("vth_falling_v", "vth_falling_v"),
                ("hysteresis_v", "hysteresis_v"), ("i_peak_rise_a", "i_peak_rise_a"),
                ("i_peak_fall_a", "i_peak_fall_a"), ("i_worst_a", "i_worst_a")):
    worst = (0.0, None)
    for r in rows:
        o = orig[(r["variant"], r["mos_corner"], r["temp_c"], r["vsup_v"])]
        a, b = r[col], float(o[oc])
        rel = abs(a - b) / abs(b) if b else math.inf
        worst = max(worst, (rel, (r["variant"], r["mos_corner"], r["temp_c"], r["vsup_v"])), key=lambda t: t[0])
    print(f"{col}: max |rerun-orig|/orig = {100*worst[0]:.3f} % at {worst[1]}")
for v in VARIANTS:
    s = [r for r in rows if r["variant"] == v]
    ow = [float(orig[(v, r["mos_corner"], r["temp_c"], r["vsup_v"])]["i_worst_a"]) for r in s]
    print(v, "i_worst max rerun %.4e orig %.4e A; hyst min rerun %.4f orig %.4f V" % (
        max(r["i_worst_a"] for r in s), max(ow), min(r["hysteresis_v"] for r in s),
        min(float(orig[(v, r["mos_corner"], r["temp_c"], r["vsup_v"])]["hysteresis_v"]) for r in s)))
