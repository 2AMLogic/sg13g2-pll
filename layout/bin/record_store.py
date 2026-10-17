#!/usr/bin/env python3
"""Content-addressed storage for layout report records (issue #261).

Both layout flow drivers write a complete, timestamped record directory
under `<port>/reports/<record-id>/`. Most large artifacts (`*.gds`,
`extract.*.json`, ...) come out byte-identical run after run. This module
is the *storage* half of the answer: after a record is fully written and
rendered, `dedupe` moves each large file into a shared, immutable object
store `<port>/reports/objects/<sha256>` and leaves a relative symlink at
the original path. Every path a reader or reproduction step used before
still resolves to the same bytes.

It is a storage change only:

- Every record keeps its own directory, id, `record.md`, `plan.json` and
  `build.json` (all stay inline, never deduplicated), so per-run outcome,
  failure and provenance evidence is unchanged.
- Each deduplicated record gets `artifacts.json`, listing every file with
  its sha256, size and storage kind. Equality is established by content
  hash, never by name or timestamp.
- Objects are named by their hash, written once, read-only. An existing
  object whose bytes do not hash to its name is an error, never silently
  reused or overwritten, so a later run cannot alter an earlier record.
- `verify` fails on a missing, dangling or corrupt reference.
- Records written before this module existed hold plain files and no
  `artifacts.json`; they are never touched.

    record_store.py dedupe <record-dir>    # run by the flow drivers
    record_store.py verify <record-dir>    # exit 1 on any problem
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

MANIFEST = "artifacts.json"
OBJECTS_DIR = "objects"
SCHEMA = 1
# Files that are the per-run evidence itself stay inline regardless of size.
ALWAYS_INLINE = frozenset({"record.md", "plan.json", "build.json", MANIFEST})
# Below this, a symlink costs about as much as the file; keep it inline.
MIN_DEDUPE_BYTES = 64 * 1024


class StoreError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_object(objects: Path, digest: str, src: Path) -> Path:
    """Place `src`'s bytes at objects/<digest> (moving it), or reuse a
    verified existing object. Raises StoreError on a corrupt object."""
    obj = objects / digest
    if obj.exists():
        if sha256_file(obj) != digest:
            raise StoreError(f"corrupt object {obj}: bytes do not hash to its name")
        src.unlink()
        return obj
    objects.mkdir(exist_ok=True)
    os.replace(src, obj)
    obj.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return obj


def dedupe(record_dir: Path, min_bytes: int = MIN_DEDUPE_BYTES) -> dict:
    """Deduplicate a finished record in place and write its manifest."""
    record_dir = record_dir.resolve()
    if not record_dir.is_dir():
        raise StoreError(f"not a record directory: {record_dir}")
    if (record_dir / MANIFEST).exists():
        raise StoreError(f"{record_dir.name} already has {MANIFEST}; records are not rewritten")
    objects = record_dir.parent / OBJECTS_DIR
    entries = []
    for path in sorted(record_dir.iterdir()):
        if path.name in ALWAYS_INLINE:
            continue
        if path.is_symlink() or not path.is_file():
            raise StoreError(f"unexpected non-regular entry in record: {path}")
        size = path.stat().st_size
        digest = sha256_file(path)
        if size < min_bytes:
            entries.append({"path": path.name, "sha256": digest, "size": size,
                            "storage": "inline"})
            continue
        obj = _ensure_object(objects, digest, path)
        path.symlink_to(os.path.relpath(obj, record_dir))
        entries.append({"path": path.name, "sha256": digest, "size": size,
                        "storage": "object"})
    manifest = {"schema": SCHEMA, "record_id": record_dir.name, "artifacts": entries}
    (record_dir / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify(record_dir: Path) -> list[str]:
    """Return a list of problems; empty means every artifact resolves and
    hashes to its manifest entry. A record without a manifest is a
    pre-#261 plain record and is reported as such, not as an error."""
    record_dir = record_dir.resolve()
    manifest_path = record_dir / MANIFEST
    if not manifest_path.is_file():
        return []
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{MANIFEST} is not valid JSON: {exc}"]
    problems = []
    listed = set()
    for e in manifest.get("artifacts", []):
        name = e["path"]
        listed.add(name)
        p = record_dir / name
        if not p.exists():  # follows symlinks: dangling link => missing
            problems.append(f"{name}: missing or dangling reference")
            continue
        if e["storage"] == "object" and not p.is_symlink():
            problems.append(f"{name}: manifest says object but file is inline")
        digest = sha256_file(p)
        if digest != e["sha256"]:
            problems.append(f"{name}: sha256 {digest} != manifest {e['sha256']}")
        elif p.stat().st_size != e["size"]:
            problems.append(f"{name}: size differs from manifest")
    for p in record_dir.iterdir():
        if p.name not in listed and p.name not in ALWAYS_INLINE:
            problems.append(f"{p.name}: not listed in {MANIFEST}")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("dedupe", "verify"):
        print("usage: record_store.py {dedupe|verify} <record-dir>", file=sys.stderr)
        return 2
    rd = Path(argv[2])
    try:
        if argv[1] == "dedupe":
            m = dedupe(rd)
            n = sum(1 for e in m["artifacts"] if e["storage"] == "object")
            print(f"record_store.py: {rd.name}: {n} artifacts in objects/, "
                  f"{len(m['artifacts']) - n} inline")
        problems = verify(rd)
    except StoreError as exc:
        print(f"record_store.py: {exc}", file=sys.stderr)
        return 1
    for p in problems:
        print(f"record_store.py: {rd.name}: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
