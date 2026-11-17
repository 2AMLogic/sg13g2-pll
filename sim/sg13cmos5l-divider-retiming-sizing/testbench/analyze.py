#!/usr/bin/env python3
"""Reduce klt sim deck reports (setup + retime) to per-variant/corner closing bounds.
Usage: analyze.py <raw-dir|raw-*.tar.gz> [...]   (dirs hold <id>/stdout.bin per unit)
Retime rows carry N (64/127), VCO MHz and neg (XFRT clocked on the falling VCO edge, RECORD-002).
For neg variants the one-edge window is 1.5*T_vco (t_arr + t_setup <= 1.5 T); the clock-inverter
delay is not credited (conservative).  setup brackets are looked up on the non-neg variant name.
Retime rows also print implied_c2q: tfb-tdiv minus the distance from the DIVOUT edge to each
candidate capture edge (rising: k+1 / k+2; neg: k+0.5 / k+1.5 / k+2.5).  A negative value rules
that hypothesis out; the plausible one is the one whose c2q stays near-constant across runs.
t_setup bracket: smallest TSU that captures (q_sample > VDD/2) is the upper bound,
next smaller TSU (not captured) the lower. t_arr = tdiv mod T_vco (RECORD-003 method).
F_close = 1/(t_arr + t_setup_upper), as RECORD-003 Finding 4."""
import json, re, sys, tarfile, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
MAN = json.loads((HERE / "manifest.json").read_text())
TPER = 640.20512e-12
def val(txt, k):
    m = re.search(rf"^{k}\s*=\s*(\S+)", txt, re.M)
    try: return float(m.group(1))
    except Exception: return None
setup, ret = {}, {}
NEG = {}
_tmp = tempfile.TemporaryDirectory()
def _dirs():
    for a in sys.argv[1:]:   # a dir of <id>/stdout.bin, or a raw-*.tar.gz holding the same
        if a.endswith(".tar.gz"):
            dst = Path(_tmp.name) / Path(a).name
            with tarfile.open(a) as t: t.extractall(dst, filter="data")
            yield dst
        else:
            yield Path(a)
for d in _dirs():
    for ud in sorted(p for p in d.iterdir() if p.is_dir()):
        m = MAN.get(ud.name)
        if not m: continue
        so = (ud / "stdout.bin").read_text(errors="replace")
        if m["stage"] == "setup":
            setup.setdefault((m["vt"], m["mos"], m["temp"], m["vdd"]), []).append((float(m["tsu"][:-1]), val(so, "q_s"), m["vdd"]))
        else:
            ret[(m["vt"], m["mos"], m["temp"], m["vdd"], m.get("n", 64), m.get("fmhz", 1562.0))] = {k: val(so, k) for k in ("tdiv","tfb","idd","dvo_max","fb_max")}
res = {}
for (vt, mos, temp, vdd), rows in sorted(setup.items()):
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
    res[(vt, mos, temp, vdd)] = (lo, hi)
    print(f"setup {vt:9s} {mos}/{temp:>4}C/{vdd}V  t_setup in ({lo}, {hi}] ps")
for k, v in sorted(ret.items()):
    vt, mos, temp, vdd, n, fm = k
    td = v["tdiv"]
    if td is None or v["tfb"] is None: print("retime", k, "NA (tdiv/tfb unresolved)", v); continue
    T = 1e6 / fm * 1e-12
    tarr = (td % T) * 1e12
    neg = vt.endswith("_neg")
    s = res.get((vt.removesuffix("_neg"), mos, temp, vdd))
    fc = ""
    if s and s[1] is not None:
        fc = f"  F_close<= {(1.5 if neg else 1.0) * 1e6/(tarr + s[1]):.0f} MHz (t_setup_hi={s[1]:.0f})"
    d = (v["tfb"] - td) * 1e12
    # implied FB clk->Q under each capture-edge hypothesis: tfb-tdiv = (edge - DIVOUT edge) + c2q
    Tp = T * 1e12
    hyp = ((0.5, 1.5, 2.5) if neg else (1.0, 2.0))
    imp = "/".join(f"{d - (h * Tp - tarr):.0f}" for h in hyp)
    labels = "/".join(f"k+{h:g}" for h in hyp)
    print(f"retime {vt:14s} N={n} {fm:g}MHz {mos}/{temp}C/{vdd}V tdiv={td*1e9:.3f}ns t_arr={tarr:.1f}ps tfb-tdiv={d:.1f}ps implied_c2q[{labels}]={imp}ps idd={v['idd']*1e3:.3f}mA{fc}")
