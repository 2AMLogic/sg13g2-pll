#!/usr/bin/env python3
"""sg13g2-pll :: closed-loop-real-divider PVT campaign collector (issue #516).

    python3 -I pvt_metrics.py --pinned-closure CSV --real-netlist FILE
            --control-netlist FILE --out-dir DIR REPORT.json [REPORT.json ...]

Reads the `klt sim` report envelope(s) the campaign's requests produced
(single-report or `--batch-set` `{kind, requests[].report}` shape), grades
every unit, and writes the append-only RECORD-003 artifacts under DIR:

    pvt_units.csv    one row per unit: corner, arm, measurements, lock
                     verdict, lock time (warm-started), final-20-cycle
                     statistics, edges per FB period, f_vco/f_fb, and the
                     pre-stated per-unit predictions (divider bound from
                     sg13cmos5l-divider-max-frequency RECORD-001's committed
                     per-corner table; band-00 600 MHz reach interpolated
                     from sg13cmos5l-vco-kvco-table RECORD-002's committed
                     rerun CSV -- unpredicted corners are marked, never
                     extrapolated)
    pvt_summary.json machine-readable roll-up (per-unit verdicts, prediction
                     hit/miss, failing-block attribution, units with no
                     verdict and why)
    batch-jobs.csv   every fleet job id the reports cite
    staged-pdk-check.json  the RECORD-015-trap gate: each report's
                     `environment.staged_model_inputs.source_sha256` graded
                     against the generator's `pinned-closure.csv`

The arm of a report member is identified by its `environment.netlist_sha256`
against the local request netlists (`--real-netlist` / `--control-netlist`);
a member matching neither is an error, not a guess.

Lock criterion: the campaign's dual-lock definition, unchanged -- per
reference cycle `|delta_f|/f_ref < 1 %` AND `|phase| < 5 % of T_ref`
(RECORD-005's definition), held for >= 20 consecutive cycles; the trace is
built from the `t_ref`/`t_fb` crossing series by
`mismatch_gain_metrics.lock_trace_from_edges` (imported from
../../sg13cmos5l-closed-loop-lock/testbench/, the same function
test_mismatch_gain_metrics.py pins to the sampled-waveform `lock_trace`).
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "mismatch_gain_metrics",
    os.path.join(HERE, "../../sg13cmos5l-closed-loop-lock/testbench",
                 "mismatch_gain_metrics.py"))
mg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mg)

FREF = 9.375e6
TREF = 1.0 / FREF
TSTOP_S = 10e-6
TAVG0_S = 8e-6
CLK_FROM_S = 7.8e-6
HOLD_N = 20
DF_LIMIT, PH_LIMIT = mg.DF_LIMIT, mg.PH_LIMIT
CP_COMPLIANCE_V = (0.25, 3.10)
DIVIDER_STAR_VDD = {3.0: 2.97, 3.6: 3.63}   # adjacent star point per supply unit
KVCO_BUNDLES = {  # results_rerun318.csv pvt_bundle -> (mos_corner, temp_c)
    "typ": ("mos_tt", 27), "slow": ("mos_ss", 125), "fast": ("mos_ff", -40),
}


def load_divider_bounds(root):
    """{(mos, temp, vdd): (last_exact_mhz, first_fail_mhz)} for N = 64, from
    sg13cmos5l-divider-max-frequency RECORD-001's committed by-corner table."""
    path = root / "sim/sg13cmos5l-divider-max-frequency/corners/max-freq-by-corner.csv"
    out = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            if row["n_nominal"] != "64":
                continue
            out[(row["mos_corner"], int(row["temp_c"]), float(row["vdd_v"]))] = \
                (row["last_exact_fin_mhz"], row["first_fail_fin_mhz"])
    return out


def load_kvco_band00(root):
    """{bundle: [(vctrl_v, freq_hz), ...]} band 00 rows, from the committed
    pinned-rerun CSV of sg13cmos5l-vco-kvco-table RECORD-002."""
    path = root / "sim/sg13cmos5l-vco-kvco-table/corners/results_rerun318.csv"
    out = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            if row["band_code"] != "00":
                continue
            out.setdefault(row["pvt_bundle"], []).append(
                (float(row["vctrl_v"]), float(row["freq_hz"])))
    for pts in out.values():
        pts.sort()
    return out


def interp_vctrl(pts, f_hz):
    """Linear-interpolated vctrl for `f_hz` inside the bundle's band-00 row,
    or None when f_hz is outside the characterised 0.3-2.7 V span."""
    for (v0, f0), (v1, f1) in zip(pts[:-1], pts[1:]):
        if f0 <= f_hz <= f1:
            return v0 + (v1 - v0) * (f_hz - f0) / (f1 - f0)
    return None


def predictions(mos, temp, vdd, div_bounds, kvco):
    """The pre-stated per-unit prediction (issue #516 step 5)."""
    exact, fail = div_bounds.get((mos, temp, vdd), (None, None))
    div_note = ""
    if exact is None:
        # the 8 cross corners have no divider bound; the supply units borrow
        # the adjacent +/-10 % star point (named, with its supply direction)
        star = DIVIDER_STAR_VDD.get(vdd)
        if star is not None:
            exact, fail = div_bounds.get((mos, temp, star), (None, None))
            if exact is not None:
                div_note = (f"adjacent star point {star} V "
                            f"({'below' if star < vdd else 'above'} the unit's "
                            f"{vdd} V supply)")
    if exact is None:
        div_pred = "unpredicted: no divider bound at this corner"
    else:
        div_pred = (f"within proven exact range (exact at {exact} MHz, first "
                    f"miscount {fail} MHz; +{float(exact) - 600.0:.0f} MHz "
                    f"margin at 600 MHz)")
    if div_note:
        div_pred += f" [{div_note}]"

    reach = None
    for bundle, pts in sorted(kvco.items()):
        if KVCO_BUNDLES[bundle] == (mos, temp):
            v = interp_vctrl(pts, 600e6)
            if v is not None:
                in_win = CP_COMPLIANCE_V[0] <= v <= CP_COMPLIANCE_V[1]
                reach = (f"reaches 600 MHz at ~{v:.3f} V ({bundle} bundle, "
                         f"{'inside' if in_win else 'OUTSIDE'} cp compliance "
                         f"{CP_COMPLIANCE_V[0]}-{CP_COMPLIANCE_V[1]} V)")
            else:
                reach = (f"600 MHz outside the characterised 0.3-2.7 V band-00 "
                         f"span ({bundle} bundle)")
            break
    if reach is None:
        reach = "unpredicted: no band-00 Kvco coverage at this corner"
    return div_pred, reach


def iter_reports(doc, path):
    if isinstance(doc, dict) and "requests" in doc and "corners" not in doc:
        for r in doc["requests"]:
            member = r["report"]
            if member is None:
                continue          # a refused member (e.g. not_launched) has no report
            if isinstance(member, str):
                # a --batch-set envelope names each member's report file;
                # klt writes it relative to the invocation directory
                cands = [pathlib.Path(member),
                         pathlib.Path(path).parent / member,
                         pathlib.Path(path).parent.parent / member]
                for c in cands:
                    if c.is_file():
                        member = json.load(open(c))
                        break
                else:
                    raise SystemExit(f"{path}: member report {r['report']!r} "
                                     "not found (tried CWD and envelope-relative)")
            yield r.get("job_id"), member
    else:
        yield None, doc


def meas_map(corner):
    out = {}
    for m in corner.get("measurements", []):
        if m.get("crossings") is not None:
            out[m["name"]] = {"times": m["crossings"].get("times") or [],
                              "truncated": bool(m["crossings"].get("truncated")),
                              "count": m["crossings"].get("count")}
        elif m.get("value") is not None:
            out[m["name"]] = m["value"]
    return out


def longest_run(trace):
    best = cur = 0
    best_end = None
    for i, (_, df, pe) in enumerate(trace):
        ok = abs(df) < DF_LIMIT and abs(pe) < PH_LIMIT
        cur = cur + 1 if ok else 0
        if cur > best:
            best, best_end = cur, i
    return best, (trace[best_end - best + 1][0] if best else None)


def grade_unit(mv):
    ref = (mv.get("t_ref") or {}).get("times") or []
    fb = (mv.get("t_fb") or {}).get("times") or []
    clk = (mv.get("t_clk") or {}).get("times") or []
    if any((mv.get(n) or {}).get("truncated") for n in ("t_ref", "t_fb", "t_clk")):
        return {"lock_verdict": None,
                "reason_no_verdict": "crossing series truncated -- raise max"}
    if len(ref) < 2 or not fb:
        return {"lock_verdict": None,
                "reason_no_verdict": "no ref/fb edge series came back"}
    trace = mg.lock_trace_from_edges(ref, fb, FREF)
    if not trace:
        return {"lock_verdict": None, "reason_no_verdict": "empty lock trace"}
    run, lock_time = longest_run(trace)
    grade = {"lock_verdict": "not_locked", "lock_time_s": lock_time,
             "lock_time_note": "warm-started (.ic vctrl = 1.23 V)",
             "longest_dual_lock_cycles": run}
    fin = trace[-HOLD_N:]
    grade["final20_df_mean"] = sum(r[1] for r in fin) / len(fin)
    grade["final20_phase_mean"] = sum(r[2] for r in fin) / len(fin)
    grade["final20_phase_min"] = min(r[2] for r in fin)
    grade["final20_phase_max"] = max(r[2] for r in fin)
    if all(abs(r[1]) < DF_LIMIT and abs(r[2]) < PH_LIMIT for r in fin) \
            and run >= HOLD_N:
        grade["lock_verdict"] = "locked"

    if len(clk) > 1:
        w = [e for e in clk if e >= TAVG0_S]
        if len(w) > 1:
            grade["f_vco_hz_8_10us"] = (len(w) - 1) / (w[-1] - w[0])
    if len(fb) > 1:
        w = [e for e in fb if e >= TAVG0_S]
        if len(w) > 1:
            grade["f_fb_hz_8_10us"] = (len(w) - 1) / (w[-1] - w[0])
    if len(clk) > 1 and len(fb) > 1:
        ratios = [sum(1 for e in clk if a <= e < b)
                  for a, b in zip(fb[:-1], fb[1:]) if b >= CLK_FROM_S]
        if ratios:
            grade["clk_per_fb_period_hist"] = json.dumps(
                {str(k): ratios.count(k) for k in sorted(set(ratios))},
                sort_keys=True)
            grade["fb_periods_scored"] = len(ratios)

    if grade["lock_verdict"] != "locked":
        hist = grade.get("clk_per_fb_period_hist")
        vc_max, vc_min = mv.get("vc_max"), mv.get("vc_min")
        if hist is not None and any(k != "64" for k in json.loads(hist)):
            grade["failing_block"] = "divider_chain (miscount in-loop)"
        elif vc_max is not None and vc_max > 0.95 * 3.3:
            grade["failing_block"] = "vctrl at/near the high rail (vco reach or cp drive)"
        elif vc_min is not None and vc_min < 0.35:
            grade["failing_block"] = "vctrl at/near the low rail (vco reach or cp drive)"
        else:
            grade["failing_block"] = "not isolated (loop-level; see crossings)"
    return grade


def check_closure(report, closure):
    env = report.get("environment", {})
    staged = env.get("staged_model_inputs") or []
    want = {name: h for name, _, h in closure}
    got = {}
    for e in staged:
        name = pathlib.Path(e.get("name", "")).name
        src = e.get("source_sha256")
        if src and name in want:
            got.setdefault(name, src)
    missing = sorted(n for n in want if n not in got)
    wrong = sorted(n for n, h in got.items() if want[n] != h)
    return {"staged_entries": len(staged), "closure_files": len(want),
            "matched": len(want) - len(missing) - len(wrong),
            "missing": missing, "sha_mismatch": wrong,
            "ok": not missing and not wrong}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reports", nargs="+", help="klt sim report JSON file(s)")
    ap.add_argument("--pinned-closure", required=True,
                    help="the generator's pinned-closure.csv")
    ap.add_argument("--real-netlist", action="append", required=True,
                    help="a real-arm request netlist (repeatable: the 3.3 V, "
                         "3.0 V and 3.6 V bodies differ; every member report "
                         "must match one of them)")
    ap.add_argument("--control-netlist", action="append", required=True,
                    help="the control-arm request's pll_control.cir")
    ap.add_argument("--out-dir", required=True,
                    help="append-only artifact dir (e.g. ../corners/pvt1)")
    a = ap.parse_args()
    root = HERE.parent.parent.parent
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def sha(p):
        return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    arm_sha = {"real": [sha(p) for p in a.real_netlist],
               "control": [sha(p) for p in a.control_netlist]}

    closure = []
    with open(a.pinned_closure) as fh:
        for row in csv.DictReader(fh):
            closure.append((pathlib.Path(row["staged_name"]).name,
                            row["source_path"], row["sha256"]))
    div_bounds = load_divider_bounds(root)
    kvco = load_kvco_band00(root)

    rows, jobs, closure_checks, no_verdict = [], [], [], []
    # One campaign row per unit: a unit can legitimately appear in several
    # reports (a `lost_shard`/error attempt, then its `--resume` re-run). The
    # LAST report's row wins, except a `pass` row always beats an earlier
    # `error` row for the same unit -- so the fleet jobs list below keeps the
    # full attempt trail while the units table carries one outcome per unit.
    by_unit = {}

    def put(row, nv):
        uid = row["unit_id"]
        prev = by_unit.get(uid)
        if prev is not None:
            if prev[0]["klt_status"] != "pass" and row["klt_status"] == "pass":
                pass                       # pass replaces the error row
            else:
                row = prev[0]              # earlier (or pass) row stands
                nv = False
        by_unit[uid] = (row, nv)

    for path in a.reports:
        doc = json.load(open(path))
        for job_id, rep in iter_reports(doc, path):
            env = rep.get("environment", {})
            nl_sha = env.get("netlist_sha256")
            if nl_sha in arm_sha["real"]:
                arm = "real"
            elif nl_sha in arm_sha["control"]:
                arm = "control"
            else:
                raise SystemExit(f"{path}: report member netlist sha {nl_sha} "
                                 "matches neither request netlist")
            rem = env.get("remote") or {}
            for fl in (rem.get("fleet") or [rem]):
                fleet = fl or {}
                jid = fleet.get("job_id") or job_id
                if jid:
                    jobs.append({"report": pathlib.Path(path).name,
                                 "arm": arm, "job_id": jid,
                                 "state": fleet.get("state"),
                                 "instance_id": fleet.get("instance_id"),
                                 "instance_type": fleet.get("instance_type"),
                                 "runner_klt_version": fleet.get("runner_klt_version")})
            cc = check_closure(rep, closure)
            cc["report"] = pathlib.Path(path).name
            cc["arm"] = arm
            closure_checks.append(cc)

            for c in rep.get("corners", []):
                mos = c.get("process")
                temp = c.get("temperature_c")
                sv = c.get("supply_v") or {}
                vdd = sv.get("vdd_vco")
                mv = meas_map(c)
                grade = grade_unit(mv)
                nv = grade["lock_verdict"] is None
                if nv:
                    no_verdict.append({"corner_id": c.get("corner_id"), "arm": arm,
                                       "status": c.get("status"),
                                       "reason": grade["reason_no_verdict"]})
                div_pred, reach_pred = predictions(mos, temp, vdd,
                                                   div_bounds, kvco)
                uid = f"{arm}_{mos}_{temp}c_{str(vdd).replace('.', 'v')}"
                put({
                    "unit_id": uid, "arm": arm, "mos_corner": mos,
                    "temp_c": temp, "vdd_v": vdd, "corner_id": c.get("corner_id"),
                    "klt_status": c.get("status"),
                    "i_pfd_a": mv.get("i_pfd"), "i_cp_a": mv.get("i_cp"),
                    "i_vco_a": mv.get("i_vco"), "i_div_a": mv.get("i_div"),
                    "vc_avg_v": mv.get("vc_avg"), "vc_max_v": mv.get("vc_max"),
                    "vc_min_v": mv.get("vc_min"),
                    "pred_divider": div_pred, "pred_vco_band00": reach_pred,
                    **grade,
                }, nv)
    rows = [r for r, _ in by_unit.values()]
    no_verdict = [{"unit_id": r["unit_id"], "corner_id": r["corner_id"],
                   "arm": r["arm"], "klt_status": r["klt_status"],
                   "reason": r["reason_no_verdict"]}
                  for r, nv in by_unit.values() if nv]

    cols = ["unit_id", "arm", "mos_corner", "temp_c", "vdd_v", "corner_id",
            "klt_status", "i_pfd_a", "i_cp_a", "i_vco_a", "i_div_a",
            "vc_avg_v", "vc_max_v", "vc_min_v", "pred_divider",
            "pred_vco_band00", "lock_verdict", "lock_time_s",
            "lock_time_note", "longest_dual_lock_cycles", "final20_df_mean",
            "final20_phase_mean", "final20_phase_min", "final20_phase_max",
            "f_vco_hz_8_10us", "f_fb_hz_8_10us", "clk_per_fb_period_hist",
            "fb_periods_scored", "failing_block", "reason_no_verdict"]
    with open(out / "pvt_units.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(out / "batch-jobs.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["report", "arm", "job_id", "state",
                                           "instance_id", "instance_type",
                                           "runner_klt_version"])
        w.writeheader()
        w.writerows(jobs)
    summary = {
        "n_units": len(rows),
        "n_locked": sum(1 for r in rows if r["lock_verdict"] == "locked"),
        "n_not_locked": sum(1 for r in rows if r["lock_verdict"] == "not_locked"),
        "n_no_verdict": len(no_verdict),
        "by_arm": {arm: {"units": sum(1 for r in rows if r["arm"] == arm),
                         "locked": sum(1 for r in rows
                                       if r["arm"] == arm and r["lock_verdict"] == "locked")}
                   for arm in ("real", "control")},
        "units_with_no_verdict": no_verdict,
        "staged_pdk_closure_all_ok": all(c["ok"] for c in closure_checks),
        "staged_pdk_checks": closure_checks,
        "batch_jobs": jobs,
    }
    with open(out / "pvt_summary.json", "w") as fh:
        json.dump(summary, fh, indent=1)
        fh.write("\n")
    with open(out / "staged-pdk-check.json", "w") as fh:
        json.dump(closure_checks, fh, indent=1)
        fh.write("\n")
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("staged_pdk_checks", "batch_jobs")}, indent=1))
    if no_verdict:
        print(f"WARNING: {len(no_verdict)} unit(s) carry no lock verdict",
              file=sys.stderr)
    if not summary["staged_pdk_closure_all_ok"]:
        raise SystemExit("staged pinned-PDK closure check FAILED (see "
                         "staged-pdk-check.json)")


if __name__ == "__main__":
    main()
