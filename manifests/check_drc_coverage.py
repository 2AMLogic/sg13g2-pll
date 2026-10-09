#!/usr/bin/env python3
"""Item 3 coverage gate: every composed block's committed DRC wrapper report.

manifests/sg13g2-pll.json grades T1 item 3 from ONE live command (klt drc on
the divider GDS). That sample must not conceal a missing, failed, violating or
stale sibling, so this gate resolves the authoritative six-block layout record
from the manifest's existing LVS/layout citations (the directory of the 4.analog
citation, cross-checked against the other 1/2/4 citations) and requires, for
each of pfd, cp, loop_filter, vco, lock_detector, divider_chain:

  * drc.pll_<block>.json exists and parses (wrapper: ok/returncode/response);
  * wrapper ok is true and returncode is 0;
  * response.status == "clean", violation_count == 0, no violations listed;
  * response.provenance.input.content_hash (or provenance.content_hash, the
    shape klt drc emits) equals "sha256:" + sha256 of the adjacent
    pll_<block>.gds (which must exist);
  * a response.coverage object is present and retains its disclosures:
    rules_skipped and layers_in_stream_without_rules are lists (possibly
    non-empty -- the curated starter deck is NOT required to be complete),
    nothing_checked is not true, and some layers/rules were checked.

It also verifies the live item-3 divider command binds to the same divider
content: the command's GDS exists, its sha256 equals the citation's
content_hash and the record's divider GDS hash (the immutable record path may
differ), and the deck matches the sibling reports' deck. Stdlib only.
Exit 0 = pass, 1 = fail.

Usage: check_drc_coverage.py [--manifest PATH] [--record DIR]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_lvs_coverage import ANALOG_BLOCKS, DIGITAL_BLOCK, sha256_file  # noqa: E402

BLOCKS = ANALOG_BLOCKS + (DIGITAL_BLOCK,)


def check_block(record, block):
    """Return a list of error strings for one block (empty = pass)."""
    rep = record / f"drc.pll_{block}.json"
    gds = record / f"pll_{block}.gds"
    if not rep.is_file():
        return [f"{block}: missing report {rep}"]
    try:
        doc = json.loads(rep.read_text())
    except (OSError, ValueError) as e:
        return [f"{block}: unreadable report {rep}: {e}"]
    if not isinstance(doc, dict):
        return [f"{block}: report is not a JSON object"]
    errs = []
    if doc.get("ok") is not True:
        errs.append(f"{block}: wrapper ok is {doc.get('ok')!r}, expected true")
    if doc.get("returncode") != 0:
        errs.append(f"{block}: wrapper returncode is {doc.get('returncode')!r}, expected 0")
    resp = doc.get("response")
    if not isinstance(resp, dict):
        return errs + [f"{block}: no /response object"]
    if resp.get("status") != "clean":
        errs.append(f"{block}: response.status is {resp.get('status')!r}, expected 'clean'")
    if resp.get("violation_count") != 0:
        errs.append(f"{block}: violation_count is {resp.get('violation_count')!r}, expected 0")
    if resp.get("violations"):
        errs.append(f"{block}: response lists {len(resp['violations'])} violation(s)")
    prov = resp.get("provenance")
    recorded = None
    if isinstance(prov, dict):
        inp = prov.get("input")
        recorded = (inp.get("content_hash") if isinstance(inp, dict) else None) or prov.get("content_hash")
    if not recorded:
        errs.append(f"{block}: response.provenance content_hash missing")
    if not gds.is_file():
        errs.append(f"{block}: missing adjacent GDS {gds}")
    elif recorded and sha256_file(gds) != recorded:
        errs.append(
            f"{block}: stale evidence, envelope hash {recorded} != "
            f"{sha256_file(gds)} ({gds.name})"
        )
    cov = resp.get("coverage")
    if not isinstance(cov, dict):
        errs.append(f"{block}: response.coverage object missing")
    else:
        for k in ("rules_skipped", "layers_in_stream_without_rules"):
            if not isinstance(cov.get(k), list):
                errs.append(f"{block}: coverage.{k} disclosure missing (expected a list)")
        if cov.get("nothing_checked") is True:
            errs.append(f"{block}: coverage.nothing_checked is true")
        if not cov.get("layers_checked") or not cov.get("rules_checked"):
            errs.append(f"{block}: coverage lists no checked layers/rules")
    return errs


def check_manifest(manifest_path, record, cites=True):
    """Citations resolve into the record; the live item-3 command binds to it."""
    errs = []
    ev = json.loads(Path(manifest_path).read_text()).get("evidence", {})
    for key in (("1.analog", "1.digital", "2.analog", "2.digital", "4.analog", "4.digital") if cites else ()):
        c = ev.get(key)
        if not isinstance(c, dict) or Path(c.get("file", "")).parent != record:
            errs.append(f"manifest: {key} does not cite the record {record}")
    c3 = ev.get("3")
    cmd = c3.get("command") if isinstance(c3, dict) else None
    if not (isinstance(cmd, list) and len(cmd) >= 3 and cmd[:2] == ["klt", "drc"]):
        return errs + ["manifest: item 3 is not a 'klt drc <gds>' command citation"]
    gds = Path(cmd[2])
    if gds.name != f"pll_{DIGITAL_BLOCK}.gds":
        errs.append(f"manifest: item 3 command targets {gds.name}, expected pll_{DIGITAL_BLOCK}.gds")
    if not gds.is_file():
        return errs + [f"manifest: item 3 GDS {gds} does not exist"]
    live = sha256_file(gds)
    if live != c3.get("content_hash"):
        errs.append(f"manifest: item 3 content_hash {c3.get('content_hash')!r} != sha256 of {gds} ({live})")
    sib = record / f"pll_{DIGITAL_BLOCK}.gds"
    if not sib.is_file() or sha256_file(sib) != live:
        errs.append(f"manifest: item 3 divider content differs from the record's {sib}")
    deck = cmd[cmd.index("--deck") + 1] if "--deck" in cmd[:-1] else None
    try:
        sib_deck = json.loads((record / f"drc.pll_{DIGITAL_BLOCK}.json").read_text())["response"]["deck"]
    except (OSError, ValueError, KeyError, TypeError):
        sib_deck = None
    # An unreadable sibling report is already reported by check_block.
    if deck is None or (sib_deck is not None and deck != sib_deck):
        errs.append(f"manifest: item 3 deck {deck!r} != sibling divider report deck {sib_deck!r}")
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
    for b in BLOCKS:
        errs += check_block(record, b)
    # With --record (a temporary copy) the item-3 divider binding is still
    # checked, against that copy; only the record-location checks are skipped.
    errs += check_manifest(a.manifest, record, cites=not a.record)
    if errs:
        print(f"FAIL: DRC coverage of {record}", file=sys.stderr)
        for e in errs:
            print("  " + e, file=sys.stderr)
        return 1
    print(f"OK: {record}: {len(BLOCKS)} composed-block DRC reports clean, hash-bound to adjacent GDS; item-3 divider citation bound")
    return 0


if __name__ == "__main__":
    sys.exit(main())
