#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-loop-bandwidth-pm/testbench/summarize_issue196.py
(issue #196, Part of #16) -- RECORD-005 of this slug.

Reduces the `klt sim` reports of gen_issue196_ccp_requests.py's benches to two
NEW corners files (no earlier corners file is read for writing):

  ../corners/cout_issue196.csv
      per (bundle, VOUT): total idle cp capacitance on VOUT at 1 MHz for the
      3.75 / 10 / 11 uA codes, the buffer-less baseline (legs + switches), the
      buffer-only part (c10 - b10), 11 uA at 400 kHz, and 11 uA conductance.
  ../corners/results_resized_issue196_ccp.csv
      per DR-007 / DR-008 tuple: the committed RECORD-003/004 PM / fc
      ("before"), this bench's C_cp = 0 anchor (must reproduce "before"), the
      bias-network-only control, and the PM / fc with the real idle cp on
      VCTRL ("after"), worst case over (a) the tuple's own Kvco-interval VCTRL
      points and (b) the full 0.3-2.9 V range, with verdicts against spec
      row 6/6a (PM >= 45 deg, fc < f_ref/10).

A tuple whose bundle has no report (the batch grid did not run) is written
with status `blocked` and NA values -- never filled from another bundle.

    python3 summarize_issue196.py
"""
import csv
import json
import pathlib

here = pathlib.Path(__file__).resolve().parent
slug = here.parent
rep = slug / "reports"

VOUTS = [round(0.3 + 0.2 * i, 2) for i in range(14)]
INTERVAL_V = {"low": (0.3, 0.9), "mid": (0.9, 1.5)}   # ../corners/matrix.md


def vtag(v):
    return f"{v:.1f}".replace(".", "p")


def corners_from(paths):
    """bundle name -> {measurement name: value} for every corner that passed."""
    out = {}
    for p in paths:
        if not p.exists() or not p.read_text().strip():
            continue
        d = json.loads(p.read_text())
        for c in d.get("corners", []):
            if c.get("status") not in ("pass", "fail"):
                continue
            out[c["process"]] = {m["name"]: m.get("value") for m in c["measurements"]}
    return out


cout = corners_from([rep / "sim.cout_nominal.json", rep / "sim.cout_bundles.batch.json"])
pm = corners_from([rep / "sim.pm_ccp_nominal.json", rep / "sim.pm_ccp_bundles.batch.json"])


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


r79 = {r["pvt_bundle"]: r for r in load(slug / "corners" / "results_resized_issue79_finetrim.csv")}
r83 = {r["pvt_bundle"]: r for r in load(slug / "corners" / "results_resized_issue83_finetrim.csv")}
TUPLES = [
    ("dr008_fast", "DR-008", "fast", r79["fast"], "c11"),
    ("dr008_typ", "DR-008", "typ", r79["typ"], "c11"),
    ("dr008_slow", "DR-008", "slow", r79["slow"], "c11"),
    ("dr007_slow", "DR-007", "slow", r83["slow"], "c375"),
]


def fmt(x, f):
    return "NA" if x is None else format(x, f)


with open(slug / "corners" / "cout_issue196.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["pvt_bundle", "vout_v", "cout_ff_3p75u", "cout_ff_10u", "cout_ff_11u",
                "cout_ff_legs_only_10u", "cout_ff_buffer_only_10u",
                "cout_ff_11u_400khz", "gout_ns_11u"])
    for b in ("fast", "typ", "slow"):
        m = cout.get(b)
        if m is None:
            continue
        for v in VOUTS:
            t = vtag(v)
            c10, b10 = m[f"cout_ff_c10_{t}"], m[f"cout_ff_b10_{t}"]
            w.writerow([b, f"{v:.1f}", f"{m[f'cout_ff_c375_{t}']:.3f}", f"{c10:.3f}",
                        f"{m[f'cout_ff_c11_{t}']:.3f}", f"{b10:.3f}", f"{c10 - b10:.3f}",
                        f"{m[f'cout400k_ff_c11_{t}']:.3f}", f"{m[f'gout_ns_c11_{t}']:.3f}"])

rows = []
for tid, dr, bundle, row, ckind in TUPLES:
    ceil = float(row["fref_hz"]) / 10.0
    lo, hi = INTERVAL_V[row["kvco_interval"]]
    m = pm.get(bundle)
    cm = cout.get(bundle)
    rec = {"tuple": tid, "decision_record": dr, "pvt_bundle": bundle,
           "band_code": row["band_code"], "kvco_interval": row["kvco_interval"],
           "fref_hz": row["fref_hz"], "n_div": row["n_div"], "trim_code": row["trim_code"],
           "pm_deg_before": row["pm_deg"], "fc_hz_before": row["fc_hz"],
           "fc_ceiling_hz": f"{ceil:.6e}"}
    if m is None:
        rec.update(status="blocked")
        rows.append(rec)
        continue

    def worst(vs):
        pts = [(m[f"pm_deg_{tid}_v{vtag(v)}"], m[f"fc_hz_{tid}_v{vtag(v)}"], v) for v in vs]
        pmin = min(pts)
        return pmin, max(p[1] for p in pts)

    own = [v for v in VOUTS if lo - 1e-9 <= v <= hi + 1e-9]
    (pm_own, _, v_own), fcmax_own = worst(own)
    (pm_all, _, v_all), fcmax_all = worst(VOUTS)
    cmax_own = cmax_all = None
    if cm is not None:
        cmax_own = max(cm[f"cout_ff_{ckind}_{vtag(v)}"] for v in own)
        cmax_all = max(cm[f"cout_ff_{ckind}_{vtag(v)}"] for v in VOUTS)

    def verdict(p, f):
        return "pass" if (p >= 45.0 and f < ceil) else "fail"

    rec.update(
        status="ran",
        pm_deg_anchor_nocp=f"{m[f'pm_deg_{tid}_nocp']:.3f}",
        fc_hz_anchor_nocp=f"{m[f'fc_hz_{tid}_nocp']:.6e}",
        pm_deg_bias_only=f"{m[f'pm_deg_{tid}_lonly']:.3f}",
        ccp_ff_max_own_interval=fmt(cmax_own, ".3f"),
        pm_deg_after_own_interval=f"{pm_own:.3f}", vctrl_v_worst_own=f"{v_own:.1f}",
        fc_hz_max_own_interval=f"{fcmax_own:.6e}",
        verdict_own_interval=verdict(pm_own, fcmax_own),
        ccp_ff_max_full_range=fmt(cmax_all, ".3f"),
        pm_deg_after_full_range=f"{pm_all:.3f}", vctrl_v_worst_full=f"{v_all:.1f}",
        fc_hz_max_full_range=f"{fcmax_all:.6e}",
        verdict_full_range=verdict(pm_all, fcmax_all),
        dpm_deg_full_range=f"{pm_all - float(row['pm_deg']):.3f}",
    )
    rows.append(rec)

cols = ["tuple", "decision_record", "pvt_bundle", "band_code", "kvco_interval", "fref_hz",
        "n_div", "trim_code", "status", "pm_deg_before", "fc_hz_before",
        "pm_deg_anchor_nocp", "fc_hz_anchor_nocp", "pm_deg_bias_only",
        "ccp_ff_max_own_interval", "pm_deg_after_own_interval", "vctrl_v_worst_own",
        "fc_hz_max_own_interval", "verdict_own_interval",
        "ccp_ff_max_full_range", "pm_deg_after_full_range", "vctrl_v_worst_full",
        "fc_hz_max_full_range", "verdict_full_range", "dpm_deg_full_range", "fc_ceiling_hz"]
with open(slug / "corners" / "results_resized_issue196_ccp.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, restval="NA")
    w.writeheader()
    for r in rows:
        w.writerow(r)
        print(r)
