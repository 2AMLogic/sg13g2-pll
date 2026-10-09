#!/usr/bin/env python3
"""PEX sibling evidence gate: the five nominal `klt pex` envelopes + their schematic legs.

manifests/sg13g2-pll.json cites only the vco and divider_chain PEX envelopes
(T1 item 7). The other three (pfd, cp, loop_filter) are never byte-compared by
the fresh grade, so this gate inspects all five blocks and requires, per block:

  * reports/pex.<block>.json exists and is a direct `klt pex` envelope with
    status "pass", no pin_count/flat_dut/model mismatch, nothing failed or
    errored, comparison coverage known / nothing skipped / unknown, one corner,
    extraction deck sg13cmos5l;
  * body_bias.status "biased", unbiased_device_count 0, no unbiased nets;
  * block identity: layout.path is pll_<block>.gds in the authoritative layout
    record (the directory of the manifest's 4.analog citation), and
    provenance.input.content_hash equals sha256 of that GDS (a stale or
    foreign-block report fails; the five input hashes are distinct);
  * reference_netlist and every testbench schematic_netlist is the committed
    leg dut/pll_<block>.schematic.sp, whose sha256 matches
    leg-provenance.json, and whose requests exist;
  * leg freshness: design export sha256 matches leg-provenance.json AND the
    leg is re-flattened into a temp dir with flatten-schematic.py and compared
    byte for byte. A changed design export therefore marks the evidence stale;
    the fix is to re-flatten, re-run run-klt-pex.sh and re-verify -- editing
    hashes alone cannot pass because the regeneration compare is independent.
  * the manifest's 7.* citations (when present) point at one of these reports
    and pin the block GDS hash.

lock_detector is explicitly WITHHELD (issue #157): no pex.lock_detector.json
may exist yet. When #157 supplies valid evidence, promote it into BLOCKS.

SCOPE: this proves nominal evidence integrity (the envelopes are real, pass,
body-biased, bound to the right GDS and fresh legs). It is NOT a PVT or spec
pass: the requests declare no limits and run one corner.

Stdlib only. Exit 0 = pass, 1 = fail.
Usage: check_pex_coverage.py [--root DIR] [--manifest P]
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SIGNOFF = "sim/sg13cmos5l-klt-pex-signoff"
BLOCKS = ("pfd", "cp", "loop_filter", "vco", "divider_chain")
WITHHELD = {"lock_detector": "#157"}
REQUESTS = {"pfd": ["pfd"], "cp": ["cp_up", "cp_dn"], "loop_filter": ["loop_filter"],
            "vco": ["vco"], "divider_chain": ["divider_chain"]}


def sha256_file(p):
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    try:
        return json.loads(Path(p).read_text()), None
    except (OSError, ValueError) as e:
        return None, f"unreadable {p}: {e}"


def check_leg(root, block, prov):
    errs = []
    ent = (prov.get("blocks") or {}).get(block)
    if not isinstance(ent, dict):
        return [f"{block}: no entry in leg-provenance.json"]
    leg = root / f"{SIGNOFF}/dut/pll_{block}.schematic.sp"
    src = root / f"design/sg13cmos5l/netlist/{block}.spice"
    if ent.get("leg") != f"{SIGNOFF}/dut/pll_{block}.schematic.sp" or ent.get("source") != f"design/sg13cmos5l/netlist/{block}.spice":
        errs.append(f"{block}: leg-provenance paths do not name the expected leg/source")
    if not leg.is_file() or not src.is_file():
        return errs + [f"{block}: missing leg {leg} or design export {src}"]
    if sha256_file(leg) != ent.get("leg_sha256"):
        errs.append(f"{block}: schematic leg sha256 {sha256_file(leg)} != leg-provenance {ent.get('leg_sha256')} "
                    "(leg altered after its PEX run; regenerate and re-run klt pex)")
    if sha256_file(src) != ent.get("source_sha256"):
        errs.append(f"{block}: design export {src.name} sha256 {sha256_file(src)} != leg-provenance "
                    f"{ent.get('source_sha256')} (source changed since the leg was flattened; PEX evidence is stale)")
    flat = root / SIGNOFF / "flatten-schematic.py"
    if sha256_file(flat) != prov.get("flattener_sha256"):
        errs.append(f"{block}: flatten-schematic.py changed since leg-provenance was written")
    # Regenerate into a temp dir and compare bytes (run from the signoff dir so the
    # recorded relative source path in the header matches).
    r = subprocess.run([sys.executable, "-I", str(flat), f"../../design/sg13cmos5l/netlist/{block}.spice",
                        str(ent.get("top")), str(ent.get("new_name")), str(ent.get("pins"))],
                       cwd=root / SIGNOFF, capture_output=True, text=True)
    if r.returncode != 0:
        errs.append(f"{block}: re-flatten failed: {r.stderr.strip()[-200:]}")
    else:
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "regen.sp"
            out.write_text(r.stdout)
            if out.read_bytes() != leg.read_bytes():
                errs.append(f"{block}: committed schematic leg differs from a fresh re-flatten of {src.name} "
                            "(stale or edited leg; re-flatten, re-run run-klt-pex.sh, re-verify)")
    pins = str(ent.get("pins"))
    run = (root / SIGNOFF / "run-klt-pex.sh")
    if run.is_file() and f"pins={pins} " not in run.read_text() and f"pins={pins};" not in run.read_text():
        errs.append(f"{block}: pins {pins} not found in run-klt-pex.sh")
    return errs


def check_report(root, record, block):
    """Return (errors, input_hash)."""
    rep = root / f"{SIGNOFF}/reports/pex.{block}.json"
    if not rep.is_file():
        return [f"{block}: missing PEX report {rep}"], None
    d, err = load(rep)
    if err:
        return [f"{block}: {err}"], None
    if not isinstance(d, dict) or "error" in d or "response" in d:
        return [f"{block}: {rep.name} is not a direct klt pex envelope"], None
    errs = []
    if d.get("status") != "pass":
        errs.append(f"{block}: status {d.get('status')!r}, expected 'pass'")
    if d.get("failed") != 0 or d.get("errored") != 0 or not isinstance(d.get("passed"), int) or d["passed"] < 1:
        errs.append(f"{block}: passed/failed/errored = {d.get('passed')}/{d.get('failed')}/{d.get('errored')}")
    for k in ("pin_count_mismatch", "flat_dut_mismatch", "model_mismatch"):
        if d.get(k) is not None:
            errs.append(f"{block}: {k} is {d.get(k)!r}")
    bb = d.get("body_bias") or {}
    if bb.get("status") != "biased" or bb.get("unbiased_device_count") != 0 \
            or bb.get("unbiased_nets") or bb.get("unbiased_pmos_body_nets"):
        errs.append(f"{block}: body_bias not clean: {bb}")
    if d.get("corner_count") != 1:
        errs.append(f"{block}: corner_count {d.get('corner_count')!r}, nominal-only evidence expects 1")
    if (d.get("extraction") or {}).get("deck") != "sg13cmos5l":
        errs.append(f"{block}: extraction deck {(d.get('extraction') or {}).get('deck')!r}")
    cov = d.get("coverage") or {}
    if cov.get("known") is not True or cov.get("nothing_checked") or cov.get("skipped") or cov.get("unknown") \
            or not cov.get("checked"):
        errs.append(f"{block}: comparison coverage not clean (known/nothing_checked/skipped/unknown)")
    gds = record / f"pll_{block}.gds"
    if (d.get("layout") or {}).get("path") != gds.relative_to(root).as_posix():
        errs.append(f"{block}: layout.path {(d.get('layout') or {}).get('path')!r}, expected {gds.relative_to(root).as_posix()}")
    h = ((d.get("provenance") or {}).get("input") or {}).get("content_hash")
    if not gds.is_file():
        errs.append(f"{block}: missing GDS {gds}")
    elif h != sha256_file(gds):
        errs.append(f"{block}: provenance input hash {h} != sha256 of {gds.name} {sha256_file(gds)} "
                    "(report is stale or for another layout; re-run run-klt-pex.sh)")
    legp = f"{SIGNOFF}/dut/pll_{block}.schematic.sp"
    if (d.get("reference_netlist") or {}).get("path") != legp:
        errs.append(f"{block}: reference_netlist {(d.get('reference_netlist') or {}).get('path')!r}, expected {legp}")
    tbs = d.get("testbenches") or []
    want = [f"{SIGNOFF}/requests/{r}.request.json" for r in REQUESTS[block]]
    if [(t.get("request") or {}).get("path") for t in tbs] != want:
        errs.append(f"{block}: testbench requests {[(t.get('request') or {}).get('path') for t in tbs]} != {want}")
    for t in tbs:
        if (t.get("schematic_netlist") or {}).get("path") != legp:
            errs.append(f"{block}: testbench schematic_netlist is not {legp}")
    for w in want:
        if not (root / w).is_file():
            errs.append(f"{block}: missing request {w}")
    return errs, h


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--manifest", default="manifests/sg13g2-pll.json")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    m, err = load(root / a.manifest)
    if err:
        print("FAIL: " + err, file=sys.stderr)
        return 1
    ev = m.get("evidence", {})
    record = root / Path(ev["4.analog"]["file"]).parent
    prov, perr = load(root / SIGNOFF / "leg-provenance.json")
    errs = [perr] if perr else []
    hashes = {}
    for b in BLOCKS:
        e, h = check_report(root, record, b)
        errs += e
        hashes[b] = h
        if prov:
            errs += check_leg(root, b, prov)
    seen = [h for h in hashes.values() if h]
    if len(set(seen)) != len(seen):
        errs.append("two PEX reports share one input hash (duplicate block identity)")
    for b, issue in WITHHELD.items():
        stray = root / f"{SIGNOFF}/reports/pex.{b}.json"
        if stray.exists():
            errs.append(f"{b}: report present but evidence is withheld pending {issue}; "
                        "promote it into BLOCKS in this gate deliberately")
    known = {f"pex.{b}.json" for b in BLOCKS}
    for p in sorted((root / SIGNOFF / "reports").glob("*.json")):
        if p.name not in known and p.name.removeprefix("pex.").removesuffix(".json") not in WITHHELD:
            errs.append(f"unexpected report {p.name} not covered by the gate")
    for key in ("7.analog", "7.digital"):
        c = ev.get(key)
        if c is None:
            continue
        blk = next((b for b in BLOCKS if c.get("file") == f"{SIGNOFF}/reports/pex.{b}.json"), None)
        if blk is None:
            errs.append(f"manifest: {key} cites {c.get('file')!r}, not one of the gated reports")
        elif c.get("content_hash") != hashes.get(blk):
            errs.append(f"manifest: {key} pinned to {c.get('content_hash')}, {blk} GDS is {hashes.get(blk)}")
    if errs:
        print("FAIL: PEX sibling evidence coverage", file=sys.stderr)
        for e in errs:
            print("  " + e, file=sys.stderr)
        return 1
    print(f"OK: {len(BLOCKS)} nominal PEX envelopes + flattened legs fresh; "
          f"withheld: {', '.join(f'{b} ({i})' for b, i in WITHHELD.items())}. "
          "Nominal evidence integrity only -- not a PVT/spec pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
