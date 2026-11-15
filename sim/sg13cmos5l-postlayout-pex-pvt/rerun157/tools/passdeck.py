#!/usr/bin/env python3
"""pending/ -> batch request dir (convert) and out dir -> cache (ingest).

rerun157's adaptation of rerun325/tools/passdeck.py: absolute PDK/work paths
in each pending deck -> $PDK_ROOT / relative, the runner's .spiceinit osdi
lines -> pre_osdi in the deck's first .control block; everything else ships
verbatim. All paths from argv, none hardcoded.

  convert REQDIR PDK_ROOT PDK SPICEINIT   -> REQDIR/{request.json,rendered/}
  ingest  OUTDIR                          -> unit results into $LD157_CACHE
"""
import sys, os, re, json, shutil, glob

mode = sys.argv[1]
CACHE = os.environ["LD157_CACHE"]
PENDING = os.environ["LD157_PENDING"]

if mode == "convert":
    out, pdk_root, pdk, spiceinit = sys.argv[2:6]
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out + "/rendered")
    osdi = [l.split(None, 1)[1].strip().replace(pdk_root, "$PDK_ROOT")
            for l in open(spiceinit) if l.startswith("osdi ")]
    pre = "".join("pre_osdi %s\n" % o for o in osdi)
    decks = []
    for k in sorted(os.listdir(PENDING)):
        if os.path.exists(os.path.join(CACHE, k, "rc")):
            continue  # already simulated (or errored-and-ingested) in an earlier cycle
        cwd = open(f"{PENDING}/{k}/cwd").read()
        t = open(f"{PENDING}/{k}/deck.sp").read().replace(cwd + "/", "").replace(pdk_root, "$PDK_ROOT")
        t, n = re.subn(r"(?mi)^\.control\s*$", ".control\n" + pre.rstrip("\n"), t, count=1)
        assert n == 1, k
        d = f"{out}/rendered/{k}"
        os.makedirs(d)
        open(d + "/deck.sp", "w").write(t)
        for f in glob.glob(f"{PENDING}/{k}/refs/*"):
            b = os.path.basename(f)
            b = b[5:] if b.startswith("REL__") else b.replace(cwd.replace("/", "__") + "__", "")
            shutil.copy(f, d + "/" + b)
        decks.append({"id": k, "deck": f"rendered/{k}/deck.sp", "inputs": [], "outputs": [],
                      "timeout_s": 7200})
    req = {"backend": "batch", "engine": "ngspice", "models": {"pdk": pdk}, "decks": decks,
           "options": {"timeout_s": 7200, "max_workers": 8},
           "batch": {"capacity_wait_s": 600}}
    json.dump(req, open(out + "/request.json", "w"), indent=1)
    print(len(decks), "decks")
else:
    outdir = sys.argv[2]
    n = 0
    for u in glob.glob(outdir + "/*/unit.json"):
        k = os.path.basename(os.path.dirname(u))
        j = json.load(open(u))
        rc = j["result"].get("exit_code")
        if rc is None:
            print("no rc", k)
            continue
        c = os.path.join(CACHE, k)
        os.makedirs(c, exist_ok=True)
        shutil.copy(os.path.dirname(u) + "/stdout.bin", c + "/stdout.bin")
        shutil.copy(os.path.dirname(u) + "/stderr.bin", c + "/stderr.bin")
        open(c + "/rc", "w").write(str(rc))
        n += 1
    print("ingested", n)
