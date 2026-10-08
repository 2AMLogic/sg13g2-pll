#!/usr/bin/env python3
"""Items 1/2/4 coverage gate: every analog block's LVS envelope in the cited record.

manifests/sg13g2-pll.json cites ONE analog LVS envelope (lock_detector) for
T1 item 4's analog partition. That sample must not conceal a missing or stale
sibling, so this gate inspects the exact record directory the manifest cites
and requires, for each of the five analog blocks (pfd, cp, loop_filter, vco,
lock_detector):

  * lvs.<block>.json exists and parses (wrapper: ok/returncode/response);
  * wrapper ok is true and returncode is 0;
  * response.status == "match";
  * response.provenance.input.content_hash == "sha256:" + sha256 of the
    adjacent pll_<block>.gds (which must exist).

It also checks the manifest's 4.analog / 4.digital citations resolve into that
record with pointer "/response". Stdlib only. Exit 0 = pass, 1 = fail.

Usage: check_lvs_coverage.py [--manifest PATH] [--record DIR]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ANALOG_BLOCKS = ("pfd", "cp", "loop_filter", "vco", "lock_detector")
DIGITAL_BLOCK = "divider_chain"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def check_block(record, block, kind="lvs"):
    """Return a list of error strings for one block (empty = pass).

    kind "lvs" (T1 item 4 and item 1) expects status "match" in
    lvs.<block>.json; kind "extract" (T1 item 2) expects status "extracted"
    in extract.pll_<block>.json. Both are bound to the adjacent GDS hash.
    """
    rep = record / (f"lvs.{block}.json" if kind == "lvs" else f"extract.pll_{block}.json")
    want_status = "match" if kind == "lvs" else "extracted"
    gds = record / f"pll_{block}.gds"
    if not rep.is_file():
        return [f"{block}: missing report {rep}"]
    try:
        doc = json.loads(rep.read_text())
    except (OSError, ValueError) as e:
        return [f"{block}: unreadable report {rep}: {e}"]
    errs = []
    if not isinstance(doc, dict):
        return [f"{block}: report is not a JSON object"]
    if doc.get("ok") is not True:
        errs.append(f"{block}: wrapper ok is {doc.get('ok')!r}, expected true")
    if doc.get("returncode") != 0:
        errs.append(f"{block}: wrapper returncode is {doc.get('returncode')!r}, expected 0")
    resp = doc.get("response")
    if not isinstance(resp, dict):
        return errs + [f"{block}: no /response object"]
    if resp.get("status") != want_status:
        errs.append(f"{block}: response.status is {resp.get('status')!r}, expected {want_status!r}")
    prov = resp.get("provenance")
    inp = prov.get("input") if isinstance(prov, dict) else None
    recorded = inp.get("content_hash") if isinstance(inp, dict) else None
    if not recorded:
        errs.append(f"{block}: response.provenance.input.content_hash missing")
    if not gds.is_file():
        errs.append(f"{block}: missing adjacent GDS {gds}")
    elif recorded and sha256_file(gds) != recorded:
        errs.append(
            f"{block}: stale evidence, envelope hash {recorded} != "
            f"{sha256_file(gds)} ({gds.name})"
        )
    return errs


def check_manifest(manifest_path, record):
    errs = []
    ev = json.loads(Path(manifest_path).read_text()).get("evidence", {})
    cites = (
        ("1.analog", "lvs", "lock_detector"), ("1.digital", "lvs", DIGITAL_BLOCK),
        ("2.analog", "extract", "lock_detector"), ("2.digital", "extract", DIGITAL_BLOCK),
        ("4.analog", "lvs", "lock_detector"), ("4.digital", "lvs", DIGITAL_BLOCK),
    )
    for key, kind, block in cites:
        c = ev.get(key)
        if not isinstance(c, dict):
            errs.append(f"manifest: {key} citation missing")
            continue
        name = f"lvs.{block}.json" if kind == "lvs" else f"extract.pll_{block}.json"
        want = (record / name).as_posix()
        if c.get("file") != want:
            errs.append(f"manifest: {key} cites {c.get('file')!r}, expected {want!r}")
        if c.get("pointer") != "/response":
            errs.append(f"manifest: {key} pointer is {c.get('pointer')!r}, expected '/response'")
    return errs


def record_from_manifest(manifest_path):
    c = json.loads(Path(manifest_path).read_text()).get("evidence", {}).get("4.analog")
    if not isinstance(c, dict) or "file" not in c:
        sys.exit("manifest has no 4.analog file citation")
    return Path(c["file"]).parent


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", default="manifests/sg13g2-pll.json")
    ap.add_argument("--record", help="record dir (default: the one 4.analog cites)")
    a = ap.parse_args(argv)
    record = Path(a.record) if a.record else record_from_manifest(a.manifest)
    errs = []
    for kind in ("lvs", "extract"):
        for b in ANALOG_BLOCKS + (DIGITAL_BLOCK,):
            errs += check_block(record, b, kind)
    if not a.record:
        errs += check_manifest(a.manifest, record)
    if errs:
        print(f"FAIL: LVS coverage of {record}", file=sys.stderr)
        for e in errs:
            print("  " + e, file=sys.stderr)
        return 1
    print(f"OK: {record}: {len(ANALOG_BLOCKS)} analog + {DIGITAL_BLOCK} LVS and extract envelopes match their adjacent GDS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
