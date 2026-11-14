#!/usr/bin/env python3
"""Helpers shared by the manifests/ coverage gates and their self-tests.

Three facts live here instead of once per gate:

  * `record_from_evidence` / `record_from_manifest` -- the authoritative
    layout record is the directory of the manifest's `4.analog` file
    citation. Four gates in `.github/workflows/signoff.yml` grade one record
    and must agree about where it is; this is the single place that
    convention is encoded, so moving the record is one edit, and a manifest
    without that citation fails the same way in every caller (a message, not
    a bare `KeyError`).
  * `sha256_file` -- `"sha256:" + sha256` of a file's bytes, the prefixed
    form every committed envelope's `content_hash` uses. Note
    `check_netlist_stamp.py`'s `sha()` deliberately returns a *bare*
    hexdigest for a different consumer and is not this function.
  * `load` -- read JSON as `(doc, err)` so a gate can accumulate the error
    alongside its other findings instead of raising.

Stdlib only (`manifests/README.md`) and side-effect-free on import. Callers
reach it with the idiom the gates already use:

    sys.path.insert(0, str(Path(__file__).parent))
    from _common import record_from_manifest, sha256_file
"""
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path):
    """`"sha256:" + sha256` of the file at `path`, read in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def load(path):
    """`(doc, None)` on success, `(None, message)` if unreadable or not JSON."""
    try:
        return json.loads(Path(path).read_text()), None
    except (OSError, ValueError) as e:
        return None, f"unreadable {path}: {e}"


def record_from_evidence(evidence):
    """Authoritative record dir: the parent of the `4.analog` file citation.

    Exits with a message rather than raising, so a malformed manifest is
    reported identically by every gate instead of three different ways.
    """
    c = evidence.get("4.analog") if isinstance(evidence, dict) else None
    if not isinstance(c, dict) or "file" not in c:
        sys.exit("manifest has no 4.analog file citation")
    return Path(c["file"]).parent


def record_from_manifest(manifest_path):
    """`record_from_evidence` of the manifest JSON at `manifest_path`."""
    ev = json.loads(Path(manifest_path).read_text()).get("evidence", {})
    return record_from_evidence(ev)
