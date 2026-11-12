#!/usr/bin/env python3
"""Split the 36-deck divider request (passdeck.py convert output) into 9 requests of 4 decks,
balanced by simulated time/step (the fleet's whole-job ceiling is 3600 s; one 36-deck job hit it,
and --max-units-per-job does not split `decks` requests). usage: split_div.py (paths as used: /tmp/r326)."""
import json, re, os, shutil
src = '/tmp/r326/reqdiv'
r = json.load(open(src + '/request.json'))
def v(x):
    x = x.lower()
    for s, k in (('meg', 1e6), ('u', 1e-6), ('n', 1e-9), ('p', 1e-12), ('m', 1e-3)):
        if x.endswith(s): return float(x[:-len(s)]) * k
    return float(x)
def cost(d):
    t = open(f"{src}/{d['deck']}").read()
    m = re.search(r'(?mi)^\.tran\s+(\S+)\s+(\S+)', t)
    return v(m.group(2)) / v(m.group(1)) if m else 1
cs = sorted(((cost(d), d) for d in r['decks']), key=lambda x: -x[0])
K = 9; groups = [[] for _ in range(K)]; load = [0] * K
for c, d in cs:
    i = load.index(min(load)); groups[i].append(d); load[i] += c
for i, g in enumerate(groups):
    out = f'/tmp/r326/reqdivp{i}'; shutil.rmtree(out, ignore_errors=True); os.makedirs(out + '/rendered')
    for d in g: shutil.copytree(f"{src}/rendered/{d['id']}", f"{out}/rendered/{d['id']}")
    rr = dict(r); rr['decks'] = g; json.dump(rr, open(out + '/request.json', 'w'), indent=1)
