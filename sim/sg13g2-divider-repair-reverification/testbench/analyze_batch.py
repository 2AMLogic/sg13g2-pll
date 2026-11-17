#!/usr/bin/env python3
"""Reduce corners/reports/*.klt-report.json (RECORD-002, issue #235) to the
original RECORD-001 CSV column layout in NEW files (*_r002.csv); the original
CSVs are never touched.  A measurement with no value is written NA (the same
convention as the original harness)."""
import csv, glob, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, "..", "corners")
def load(n): return json.load(open(os.path.join(C, "reports", n + ".klt-report.json")))
def num(v): return "NA" if v is None else f"{v:.5e}"
def pv(cid):
    mos, _, t = cid.split("/")[:3]
    p = dict(kv.split("=") for kv in cid.split("params:")[1].split(",")) if "params:" in cid else {}
    return mos, t.rstrip("C"), p.get("vdd_p")
def meas(c): return {m["name"]: m["value"] for m in c["measurements"]}
FUNC = "ck1_max ck1_min ck2_max ck2_min ck3_max ck3_min ck4_max ck4_min ck5_max ck5_min dvo_max dvo_min fb_max fb_min tdiv_a tdiv_b tck_a tck_b idd".split()
HDR = "tag,variant,mos_corner,temp_c,vdd_v,fin_hz,p_word,n_nominal,reltol,ck1_max,ck1_min,ck2_max,ck2_min,ck3_max,ck3_min,ck4_max,ck4_min,ck5_max,ck5_min,dvo_max,dvo_min,fb_max,fb_min,tdiv_a_s,tdiv_b_s,tck_a_s,tck_b_s,idd_a".split(",")
def frow(tag, word, nnom, reltol, c):
    mos, t, v = pv(c["corner_id"]); m = meas(c)
    return [tag, "repaired", mos, t, v, "1.000000e+08", word, nnom, reltol] + [num(m.get(k)) for k in FUNC]
def write(name, hdr, rows):
    with open(os.path.join(C, name), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(hdr); w.writerows(rows)
rows = []
for k in ("mos5", "temp", "vdd"):
    rows += [frow("baseline", "000000", 64, 0.001, c) for c in load(f"func_baseline_{k}")["corners"]]
for word, nn in [("000001", 65), ("000010", 66), ("000100", 68), ("001000", 72), ("010000", 80), ("100000", 96), ("011111", 95), ("101010", 106), ("111111", 127)]:
    rows += [frow("code", word, nn, 0.001, c) for c in load(f"func_code_{word}")["corners"]]
for n in ("mos_ss_125", "mos_ff_-40"):
    rows += [frow("edge", "111111", 127, 0.001, c) for c in load(f"func_edge_{n}")["corners"]]
write("func_r002.csv", HDR, rows)
rows = []
for rt in ("0.001", "0.002", "0.005"):
    rows += [frow("tol", "000000", 64, rt, c) for c in load(f"func_tol_{rt}")["corners"]]
write("tol_convergence_r002.csv", HDR, rows)
rows = []
for k in ("mos5", "temp", "vdd"):
    for c in load(f"hold_{k}")["corners"]:
        m = meas(c); mos, t, v = pv(c["corner_id"])
        rows.append(["repaired", mos, t, v, num(m.get("q_end")), num(m.get("s_end")), num(m.get("t_decay"))])
write("hold_r002.csv", "variant,mos_corner,temp_c,vdd_v,q_end_v,s_end_v,t_decay_s".split(","), rows)
rows = []
for ic, key in (("none", "none"), ("applied", "ic")):
    c = load(f"opconv_{key}")["corners"][0]
    rows.append(["repaired", ic, "yes" if c["status"] == "pass" else "no", "ok" if c["status"] == "pass" else "; ".join(d.get("code", "") for d in c["diagnostics"])])
write("opconv_r002.csv", "variant,ic,converged,note".split(","), rows)

# ---- comparison against RECORD-001's CSVs (read-only) ------------------------
def key(r, n): return tuple(r[:n])
def rd(p): return list(csv.reader(open(os.path.join(C, p))))[1:]
def cmp_rows(old, new, nk, label):
    om = {key(r, nk): r for r in old}; worst = 0.0; miss = 0; diff = []
    for r in new:
        o = om.get(key(r, nk))
        if not o: miss += 1; continue
        for a, b, in zip(o[nk:], r[nk:]):
            try: fa, fb = float(a), float(b)
            except ValueError:
                if a != b: diff.append((r[:nk], a, b))
                continue
            rel = abs(fa - fb) / max(abs(fa), 1e-30); worst = max(worst, rel)
            if rel > 1e-3: diff.append((r[:nk], a, b))
    print(f"{label}: new={len(new)} old={len(old)} unmatched_new={miss} max_rel_diff={worst:.3g} diffs>1e-3={len(diff)}")
    for d in diff[:5]: print("   ", d)
cmp_rows(rd("func.csv"), rd("func_r002.csv"), 7, "func")
cmp_rows(rd("hold.csv"), rd("hold_r002.csv"), 4, "hold")
cmp_rows(rd("opconv.csv"), rd("opconv_r002.csv"), 2, "opconv")
if os.path.exists(os.path.join(C, "tol_convergence.csv")):
    cmp_rows(rd("tol_convergence.csv"), rd("tol_convergence_r002.csv"), 9, "tol")
