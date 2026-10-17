#!/usr/bin/env python3
"""Offline netlist-currency stamp for the T1 item-1 attestation (#267).

`klt signoff --attest 1` needs, for every derived netlist, a `check` command
that exits 0 only while that netlist is current. The real freshness gate
regenerates the netlist with xschem (design/netlist.sh --check, run by
.github/workflows/netlist.yml); signoff.yml installs no xschem, so it cannot
run that. This script is the xschem-free form: design/netlist.stamp.json
records, per schematic tree, a digest of every source (*.sch, *.sym) and, per
netlist, its sha256, taken when the netlists were last regenerated. The check
fails when a source or a netlist differs from its stamp, so a schematic edit
cannot ride through without the stamp (and so the envelope) being refreshed.

What this does NOT prove: that the stamped netlist equals what xschem emits for
the stamped sources. `--update` re-stamps whatever is on disk; run it only
right after `design/netlist.sh` and `design/sg13cmos5l/netlist.sh` and a green
netlist.yml. netlist.yml stays the regeneration gate.

Stdlib only. Exit 0 = current, 1 = stale or malformed.
Usage: check_netlist_stamp.py [--root DIR] [--netlist PATH] [--update]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

TREES = ("design", "design/sg13cmos5l")
STAMP = "design/netlist.stamp.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root, tree):
    """sha256 over sorted `name NUL file-sha256 LF` lines of the tree's *.sch/*.sym."""
    files = sorted(p for p in (root / tree).iterdir() if p.suffix in (".sch", ".sym"))
    h = hashlib.sha256()
    for p in files:
        h.update(f"{p.name}\0{sha(p)}\n".encode())
    return h.hexdigest(), len(files)


def current(root):
    out = {"schema_version": 1, "trees": {}, "netlists": {}}
    for tree in TREES:
        digest, count = tree_digest(root, tree)
        out["trees"][tree] = {"source_files": count, "sources_sha256": digest}
        for p in sorted((root / tree / "netlist").glob("*.spice")):
            out["netlists"][p.relative_to(root).as_posix()] = {
                "tree": tree,
                "sha256": sha(p),
            }
    return out


def check(root, only=None):
    stamp_path = root / STAMP
    if not stamp_path.is_file():
        return [f"{STAMP} is missing"]
    stamp, now = json.loads(stamp_path.read_text()), current(root)
    errors = []
    if only is not None:
        if only not in stamp["netlists"]:
            return [f"{only} is not stamped in {STAMP}"]
        if only not in now["netlists"]:
            return [f"{only} does not exist"]
        trees = [stamp["netlists"][only]["tree"]]
        names = [only]
    else:
        trees, names = list(TREES), sorted(set(stamp["netlists"]) | set(now["netlists"]))
    for tree in trees:
        if stamp["trees"].get(tree) != now["trees"][tree]:
            errors.append(f"{tree}: schematic/symbol sources changed since the netlists were stamped")
    for name in names:
        if stamp["netlists"].get(name) != now["netlists"].get(name):
            errors.append(f"{name}: netlist differs from its stamp (or is unstamped/missing)")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=Path(__file__).resolve().parent.parent, type=Path)
    ap.add_argument("--netlist", help="check only this repo-relative netlist and its tree")
    ap.add_argument("--update", action="store_true", help="re-stamp what is on disk")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.update:
        (root / STAMP).write_text(json.dumps(current(root), indent=2) + "\n")
        print(f"wrote {STAMP}")
        return 0
    errors = check(root, args.netlist)
    for e in errors:
        print(f"FAIL: {e}", file=sys.stderr)
    if not errors:
        print("netlist stamp current" + (f": {args.netlist}" if args.netlist else ""))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
