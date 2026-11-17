#!/usr/bin/env python3
"""convert: pending/ -> request dir.  ingest: unit results -> cache/.  (adaptation only: abs paths -> $PDK_ROOT/relative, .spiceinit osdi -> pre_osdi)"""
import sys, os, re, json, shutil, glob
mode = sys.argv[1]
P = "/tmp/r326/pending"; C = "/tmp/r326/cache"
if mode == "convert":
    out, pdk_root, pdk, spiceinit, cwdfilter = sys.argv[2:7]
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out + "/rendered")
    osdi = [l.split(None, 1)[1].strip().replace(pdk_root, "$PDK_ROOT") for l in open(spiceinit) if l.startswith("osdi ")]
    pre = "".join("set num_threads=1\n" for l in open(spiceinit) if l.strip()=="set num_threads=1") + "".join("pre_osdi %s\n" % o for o in osdi)
    decks = []
    for k in sorted(os.listdir(P)):
        if os.path.exists(C + "/" + k + "/rc"): continue
        cwd = open(f"{P}/{k}/cwd").read()
        if cwdfilter not in cwd: continue
        t = open(f"{P}/{k}/deck.sp").read().replace(cwd + "/", "").replace(pdk_root, "$PDK_ROOT")
        t, n = re.subn(r"(?mi)^\.control\s*$", ".control\n" + pre.rstrip("\n"), t, count=1)
        assert n == 1, k
        d = f"{out}/rendered/{k}"; os.makedirs(d)
        open(d + "/deck.sp", "w").write(t)
        for f in glob.glob(f"{P}/{k}/refs/*"):
            b = os.path.basename(f); b = b[5:] if b.startswith("REL__") else b.replace(cwd.replace("/", "__") + "__", "")
            shutil.copy(f, d + "/" + b)
        decks.append({"id": k, "deck": f"rendered/{k}/deck.sp", "inputs": [], "outputs": [], "timeout_s": 7200})
    json.dump({"backend": "batch", "engine": "ngspice", "models": {"pdk": pdk}, "decks": decks,
               "options": {"timeout_s": 7200, "max_workers": 8}, "batch": {"capacity_wait_s": 600}},
              open(out + "/request.json", "w"), indent=1)
    print(len(decks), "decks")
else:
    outdir = sys.argv[2]; n = 0
    for u in glob.glob(outdir + "/*/unit.json"):
        k = os.path.basename(os.path.dirname(u)); j = json.load(open(u))
        rc = j["result"].get("exit_code")
        if rc is None: print("no rc", k); continue
        c = f"{C}/{k}"; os.makedirs(c, exist_ok=True)
        shutil.copy(os.path.dirname(u) + "/stdout.bin", c + "/stdout.bin"); shutil.copy(os.path.dirname(u) + "/stderr.bin", c + "/stderr.bin")
        open(c + "/rc", "w").write(str(rc)); n += 1
    print("ingested", n)
