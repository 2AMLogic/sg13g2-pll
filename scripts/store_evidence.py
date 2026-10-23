#!/usr/bin/env python3
"""Store a run's raw outputs in the artifact store; commit only a manifest.

  store_evidence.py <bench> <run-id> <staged-dir> --summary <md>

Fails closed: if the broker is not configured or reachable, or `klt artifact`
is missing, nothing is written. Otherwise runs `klt artifact put` into
manifests/artifacts/<bench>-<run-id>.manifest.json and writes the committed
summary sim/<bench>/campaigns/<run-id>.md (name/size/sha256 per object).

The broker URL comes from $KLT_ARTIFACT_BROKER and is never put in argv,
files or output. <staged-dir> must be outside the tracked tree (use the
git-ignored .stage/ scratch dir only for staging, not for committing).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def die(msg):
    print(f"store_evidence: {msg}", file=sys.stderr)
    sys.exit(2)


def tracked(path):
    r = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", str(path)],
                       capture_output=True)
    return r.returncode == 0


def preflight():
    broker = os.environ.get("KLT_ARTIFACT_BROKER")
    if not broker:
        die("KLT_ARTIFACT_BROKER is not set; refusing (no fallback to committing bytes)")
    try:
        r = subprocess.run(["klt", "artifact", "put", "--help"], capture_output=True)
    except OSError:
        die("klt not found")
    if r.returncode != 0:
        die("this klt has no 'artifact put' verb (needs klayout-tools 7e3561f or later)")
    try:
        urllib.request.urlopen(broker, timeout=10)
    except urllib.error.HTTPError:
        pass  # the broker answered; any HTTP status proves reachability
    except Exception:
        die("artifact broker unreachable")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bench")
    ap.add_argument("run_id")
    ap.add_argument("staged_dir", type=Path)
    ap.add_argument("--summary", required=True, type=Path, help="markdown narrative for the committed record")
    args = ap.parse_args(argv)
    for v in (args.bench, args.run_id):
        if not NAME_RE.match(v):
            die(f"bad name {v!r}")
    staged = args.staged_dir.resolve()
    if not staged.is_dir():
        die(f"{staged} is not a directory")
    files = sorted(p for p in staged.rglob("*") if p.is_file())
    if not files:
        die("staged dir is empty")
    if any(tracked(p) for p in files):
        die("staged dir is inside the tracked tree; stage raw outputs outside git")
    if not args.summary.is_file():
        die(f"summary {args.summary} not found")
    preflight()

    manifest = ROOT / "manifests" / "artifacts" / f"{args.bench}-{args.run_id}.manifest.json"
    record = ROOT / "sim" / args.bench / "campaigns" / f"{args.run_id}.md"
    if manifest.exists() or record.exists():
        die("manifest or campaign record already exists (evidence is append-only)")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["klt", "artifact", "put", "--manifest", str(manifest), "--format", "json"]
    # Names are paths relative to the staged dir, not the local checkout.
    names = [p.relative_to(staged).as_posix() for p in files]
    for p, n in zip(files, names):
        r = subprocess.run(cmd + ["--name", n, str(p)], capture_output=True, text=True)
        if r.returncode != 0:
            manifest.unlink(missing_ok=True)
            die(f"klt artifact put failed for {n} (exit {r.returncode}); manifest removed")
    entries = json.loads(manifest.read_text())["entries"]
    lines = [f"# {args.bench} / {args.run_id}", "", args.summary.read_text().rstrip(), "",
             f"Raw outputs are in the artifact store, named by `{manifest.relative_to(ROOT).as_posix()}`.",
             "Verify with `klt artifact verify` on a fleet worker.", "",
             "| name | size | sha256 |", "| --- | ---: | --- |"]
    lines += [f"| `{e.get('name', '')}` | {e['size']} | `{e['sha256']}` |" for e in entries]
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text("\n".join(lines) + "\n")
    print(f"stored {len(entries)} object(s); wrote {manifest.relative_to(ROOT)} and {record.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
