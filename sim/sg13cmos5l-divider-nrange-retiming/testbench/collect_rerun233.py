#!/usr/bin/env python3
"""Collect the issue-#233 batch rerun into corners/rerun-*.csv.

Reads the per-stage `klt sim` deck reports (<dir>/<stage>.json) plus each
unit's stdout.bin/stderr.bin under <dir>/<stage>/<id>/, applies run.sh's own
extractor and the same column layout as the original corners/*.csv, and writes
new files only (never the originals).

Usage: collect_rerun233.py <results-dir>   (stages: opconv hold setup func retime)
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORNERS = HERE.parent / "corners"
MAN = json.loads((HERE / "rerun233" / "manifest.json").read_text())
FUNC_KEYS = ("ck1_max ck1_min ck2_max ck2_min ck3_max ck3_min ck4_max ck4_min "
             "ck5_max ck5_min dvo_max dvo_min fb_max fb_min tdiv_a tdiv_b tck_a tck_b idd").split()
FUNC_HDR = ("tag,variant,mos_corner,temp_c,vdd_v,fin_hz,p_word,n_nominal,reltol,ck1_max,ck1_min,"
            "ck2_max,ck2_min,ck3_max,ck3_min,ck4_max,ck4_min,ck5_max,ck5_min,dvo_max,dvo_min,"
            "fb_max,fb_min,tdiv_a_s,tdiv_b_s,tck_a_s,tck_b_s,idd_a")


def extract(txt, keys):  # run.sh's extract.py, verbatim logic
    out = []
    for k in keys:
        m = re.search(rf"^{k}\s*=\s*(\S+)", txt, re.M)
        v = m.group(1) if m else "NA"
        try:
            float(v)
        except ValueError:
            v = "NA"
        out.append(v)
    return ",".join(out)


def main(res):
    res = Path(res)
    rows = {}
    status = {}
    for stage in ("opconv", "hold", "setup", "func", "retime"):
        rep = res / f"{stage}.json"
        if not rep.exists():
            continue
        d = json.loads(rep.read_text())
        for u in d["units"]:
            ud = res / stage / u["id"]
            so = (ud / "stdout.bin").read_bytes().decode(errors="replace") if (ud / "stdout.bin").exists() else ""
            se = (ud / "stderr.bin").read_bytes().decode(errors="replace") if (ud / "stderr.bin").exists() else ""
            m = MAN[u["id"]]
            status[u["id"]] = (u["status"], u["exit_code"], u.get("duration_s"))
            rows.setdefault(stage, []).append((u["id"], m, so, se))
    FOUT = lambda n: CORNERS / f"rerun-{n}.csv"
    if "opconv" in rows:
        with FOUT("opconv").open("w") as f:
            f.write("variant,ic,converged,note\n")
            for uid, m, so, se in rows["opconv"]:
                log = so + "\n" + se
                if re.search(r"doAnalyses: iteration limit reached|no convergence|singular matrix|Transient op failed", log, re.I):
                    conv = "no"
                elif re.search(r"^v\(divout\)", log, re.M):
                    conv = "yes"
                else:
                    conv = "no"
                n = re.search(r"iteration limit reached|singular matrix|gmin stepping failed|source stepping failed|transient op failed|timestep too small", log, re.I)
                note = n.group(0).replace(",", "") if n else ("ok" if conv == "yes" else "no-message-before-timeout")
                f.write(f"{m['variant']},{m['ic']},{conv},{note}\n")
    if "hold" in rows:
        with FOUT("hold").open("w") as f:
            f.write("variant,mos_corner,temp_c,vdd_v,q_end_v,s_end_v,t_decay_s\n")
            for uid, m, so, se in rows["hold"]:
                f.write(f"{m['variant']},{m['mos']},{m['temp']},{m['vdd']},{extract(so, ['q_end','s_end','t_decay'])}\n")
    if "setup" in rows:
        with FOUT("setup").open("w") as f:
            f.write("variant,mos_corner,temp_c,vdd_v,tsu_s,q_sample_v\n")
            for uid, m, so, se in rows["setup"]:
                f.write(f"{m['variant']},{m['mos']},{m['temp']},{m['vdd']},{m['tsu']},{extract(so, ['q_s'])}\n")
    if "func" in rows:
        fin = f"{1/10.0e-9:.6e}"
        outs = {"func": [], "tol_convergence": []}
        for uid, m, so, se in rows["func"]:
            o = extract(so, FUNC_KEYS)
            outs[m["csv"]].append(f"{m['tag']},{m['variant']},{m['mos']},{m['temp']},{m['vdd']},{fin},{m['word']},{m['nnom']},{m['reltol']},{o}")
        for name, lines in outs.items():
            with FOUT(name).open("w") as f:
                f.write(FUNC_HDR + "\n")
                f.write("\n".join(lines) + ("\n" if lines else ""))
    if "retime" in rows:
        tper = f"{640.20512e-12:.8e}"
        ftob = f"{1/640.20512e-12:.6e}"
        with FOUT("retime").open("w") as f:
            f.write("variant,mos_corner,temp_c,vdd_v,fin_hz,tper_s,tdiv_s,tfb_s,dvo_max,dvo_min,fb_max,fb_min,idd_a\n")
            for uid, m, so, se in rows["retime"]:
                f.write(f"{m['variant']},{m['mos']},{m['temp']},{m['vdd']},{ftob},{tper},{extract(so, ['tdiv','tfb','dvo_max','dvo_min','fb_max','fb_min','idd'])}\n")
    json.dump(status, sys.stderr, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
