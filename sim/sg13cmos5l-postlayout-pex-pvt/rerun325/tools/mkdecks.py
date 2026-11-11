#!/usr/bin/env python3
"""Turn a runner's rendered scratch work dir into a klt `decks` request.

Adaptation only: absolute PDK/work paths -> $PDK_ROOT / relative, and the
runner's .spiceinit osdi lines -> `pre_osdi` in the deck's .control block.
Everything else in the deck is shipped as rendered by the unmodified runner.
usage: mkdecks.py WORK OUTDIR PDK_ROOT PDKTREE 'deck-glob' [extra input globs...]
"""
import sys, os, re, glob, json, shutil
work, out, pdk_root, pdk, deckglob = sys.argv[1:6]
inputs_glob = sys.argv[6:]
os.makedirs(out + "/rendered", exist_ok=True)
osdi = [l.split(None,1)[1].strip() for l in open(work + "/.spiceinit") if l.startswith("osdi ")]
osdi = [o.replace(pdk_root, "$PDK_ROOT") for o in osdi]
inputs = []
for g in inputs_glob:
    for p in sorted(glob.glob(os.path.join(work, g))):
        shutil.copy(p, out + "/rendered/" + os.path.basename(p)); inputs.append({"path": "rendered/" + os.path.basename(p), "name": os.path.basename(p)})
decks = []
for p in sorted(glob.glob(os.path.join(work, deckglob))):
    t = open(p).read()
    t = t.replace(work + "/", "").replace(pdk_root, "$PDK_ROOT")
    # pre_osdi first line inside the first .control block
    pre = "".join("pre_osdi %s\n" % o for o in osdi)
    t, n = re.subn(r"(?mi)^\.control\s*$", ".control\n" + pre.rstrip("\n"), t, count=1)
    assert n == 1, p
    name = os.path.basename(p)
    open(out + "/rendered/" + name, "w").write(t)
    decks.append({"id": name[:-3] if name.endswith(".sp") else name, "deck": "rendered/" + name,
                  "inputs": [], "outputs": [], "timeout_s": 3600})
req = {"backend": "batch", "engine": "ngspice", "models": {"pdk": pdk},
       "decks": decks, "options": {"timeout_s": 3600, "max_workers": 2},
       "batch": {"capacity_wait_s": 600}}
json.dump(req, open(out + "/request.json", "w"), indent=1)
print(len(decks), "decks ->", out + "/request.json")
