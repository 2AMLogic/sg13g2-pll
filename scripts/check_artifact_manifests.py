#!/usr/bin/env python3
"""Check the artifact-store manifests under manifests/artifacts/.

Stdlib only. Validates the `klt artifact` manifest shape (schema_version 1),
requires every `uri` to be a logical `artifact:<key>` name, rejects storage
locations (s3://, arn:aws:, bucket endpoints) anywhere in a manifest, and fails
if a stored object's sha256 equals a committed file (bytes in both places).

Bytes are NOT re-hashed against the store here (that needs the broker):
`klt artifact verify <manifest>` does that, on a fleet worker.

Usage: check_artifact_manifests.py [--root DIR]
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST_DIR = "manifests/artifacts"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
URI_RE = re.compile(r"^artifact:([^/\s]\S*)$")
LEAK_RE = re.compile(r"s3://|arn:aws:|amazonaws\.com|https?://", re.I)
REQUIRED = ("sha256", "size", "kind", "producer", "uri")
OPTIONAL = ("name", "media_type")
PRODUCER = ("tool", "version", "loom.repo", "commit")


def entry_problems(e):
    if not isinstance(e, dict):
        return ["entry is not an object"]
    out = []
    missing = [f for f in REQUIRED if f not in e]
    extra = sorted(set(e) - set(REQUIRED) - set(OPTIONAL))
    if missing:
        out.append("missing " + ", ".join(missing))
    if extra:
        out.append("unknown field(s) " + ", ".join(extra))
    sha = e.get("sha256")
    if not (isinstance(sha, str) and SHA_RE.match(sha)):
        out.append("sha256 must be 64 lowercase hex digits")
    size = e.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        out.append("size must be a positive integer")
    if e.get("kind") != "evidence":
        out.append("kind must be 'evidence'")
    prod = e.get("producer")
    if not isinstance(prod, dict) or set(prod) != set(PRODUCER):
        out.append("producer must carry exactly " + ", ".join(PRODUCER))
    uri = e.get("uri")
    m = URI_RE.match(uri) if isinstance(uri, str) else None
    if not m:
        out.append("uri must be a logical 'artifact:<key>' name")
    elif isinstance(sha, str) and not m.group(1).endswith(sha):
        out.append("uri key does not end in the entry's sha256")
    return out


def manifest_problems(path, text):
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return [f"{path}: not valid JSON ({exc})"]
    out = []
    if LEAK_RE.search(text):
        out.append(f"{path}: names a storage location (s3://, arn:aws:, bucket or URL); only artifact:<key> is allowed")
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        return out + [f"{path}: schema_version must be 1"]
    if set(doc) != {"schema_version", "entries"}:
        out.append(f"{path}: top level must be exactly schema_version, entries")
    entries = doc.get("entries")
    if not isinstance(entries, list) or not entries:
        return out + [f"{path}: entries must be a non-empty list"]
    for i, e in enumerate(entries):
        out += [f"{path}: entries[{i}]: {p}" for p in entry_problems(e)]
    return out


def tracked_files(root):
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True)
    return [Path(p.decode()) for p in r.stdout.split(b"\0") if p]


def committed_duplicates(root, manifests):
    """(manifest, name, tracked path) where a stored object's bytes are also committed."""
    want = {}
    for path, doc in manifests:
        for e in doc.get("entries", []):
            if isinstance(e, dict) and isinstance(e.get("sha256"), str) and isinstance(e.get("size"), int):
                want.setdefault((e["size"], e["sha256"]), []).append((path, e.get("name", e["sha256"])))
    sizes = {s for s, _ in want}
    out = []
    for rel in tracked_files(root):
        if rel.parts[:2] == ("manifests", "artifacts"):
            continue
        p = root / rel
        try:
            if not p.is_file() or p.is_symlink() or p.stat().st_size not in sizes:
                continue
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            continue
        for path, name in want.get((p.stat().st_size, digest), []):
            out.append(f"{path}: object {name} duplicates committed file {rel} (bytes must live in one place)")
    return out


def check(root):
    root = Path(root)
    problems, loaded = [], []
    files = sorted((root / MANIFEST_DIR).glob("*.manifest.json"))
    for f in files:
        rel = f.relative_to(root).as_posix()
        text = f.read_text()
        p = manifest_problems(rel, text)
        problems += p
        if not p:
            loaded.append((rel, json.loads(text)))
    if loaded:
        problems += committed_duplicates(root, loaded)
    return problems, len(files)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args(argv)
    problems, n = check(args.root)
    for p in problems:
        print("FAIL", p)
    if problems:
        return 1
    print(f"OK: {n} artifact manifest(s) checked; stored bytes were NOT re-hashed "
          "(run `klt artifact verify <manifest>` on a fleet worker for that).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
