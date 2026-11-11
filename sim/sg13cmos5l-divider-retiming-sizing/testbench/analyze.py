#!/usr/bin/env python3
"""Reduce klt sim deck reports (setup + retime) to per-variant/corner closing bounds.
Usage: analyze.py <raw-dir> [<raw-dir> ...]   (dirs hold <id>/stdout.bin per unit)
t_setup bracket: smallest TSU that captures (q_sample > VDD/2) is the upper bound,
next smaller TSU (not captured) the lower. t_arr = tdiv mod T_vco (RECORD-003 method).
F_close = 1/(t_arr + t_setup_upper), as RECORD-003 Finding 4."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
MAN = json.loads((HERE / "manifest.json").read_text())
TPER = 640.20512e-12
def val(txt, k):
    m = re.search(rf"^{k}\s*=\s*(\S+)", txt, re.M)
    try: return float(m.group(1))
    except Exception: return None
setup, ret = {}, {}
for d in map(Path, sys.argv[1:]):
    for ud in sorted(p for p in d.iterdir() if p.is_dir()):
        m = MAN.get(ud.name)
        if not m: continue
        so = (ud / "stdout.bin").read_text(errors="replace")
        if m["stage"] == "setup":
            setup.setdefault((m["vt"], m["mos"], m["temp"]), []).append((float(m["tsu"][:-1]), val(so, "q_s"), m["vdd"]))
        else:
            ret[(m["vt"], m["mos"], m["temp"], m["vdd"])] = {k: val(so, k) for k in ("tdiv","tfb","idd","dvo_max","fb_max")}
res = {}
for (vt, mos, temp), rows in sorted(setup.items()):
    rows.sort()
    cap = [t for t, q, v in rows if q is not None and q > v / 2]
    ncap = [t for t, q, v in rows if q is not None and q <= v / 2]
    # hi: smallest TSU such that every tested TSU >= hi captures (isolated captures at a
    # large TSU -- the previous transparent-phase tail -- do not count as closure)
    hi = None
    for t, q, v in sorted(rows, reverse=True):
        if q is not None and q > v / 2: hi = t
        else: break
    lo = max([t for t in ncap if hi is None or t < hi], default=None)
    res[(vt, mos, temp)] = (lo, hi)
    print(f"setup {vt:9s} {mos}/{temp:>4}C  t_setup in ({lo}, {hi}] ps")
for k, v in sorted(ret.items()):
    td = v["tdiv"]
    if td is None or v["tfb"] is None: print("retime", k, "NA (tdiv/tfb unresolved)", v); continue
    tarr = (td % TPER) * 1e12
    s = res.get((k[0], k[1], k[2]))
    fc = ""
    if s and s[1] is not None:
        fc = f"  F_close<= {1e6/(tarr + s[1]):.0f} MHz (t_setup_hi={s[1]:.0f})"
    print(f"retime {k[0]:9s} {k[1]}/{k[2]}C/{k[3]}V tdiv={td*1e9:.3f}ns t_arr={tarr:.1f}ps tfb-tdiv={(v['tfb']-td)*1e12:.1f}ps idd={v['idd']*1e3:.3f}mA{fc}")
