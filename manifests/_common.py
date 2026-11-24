#!/usr/bin/env python3
"""Helpers shared by the manifests/ coverage gates and their self-tests.

Six facts live here instead of once per gate:

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
  * `open_envelope` -- the opening preamble every gate runs on a committed
    klt envelope (missing / unreadable / wrong shape, wrapped or direct),
    so the four signoff gates open evidence identically (#410).
  * `envelope_input_hash` -- the one spelling of "the hash this envelope
    recorded for its input": `provenance.input.content_hash`. The former
    top-level `provenance.content_hash` fallback in check_drc_coverage.py
    was dead (0 of 385 committed envelopes carry that shape) and is gone
    (operator ruling 2026-11-23, issue #410 option a); a gate reading any
    other key is a gate checking a different contract.
  * `check_hash_bound` -- the adjacent-GDS binding pair (GDS present,
    recorded hash equal) with the caller's mismatch wording, the one check
    behind "hash-bound evidence" in all four gates.

Stdlib only (`manifests/README.md`) and side-effect-free on import. Callers
reach it with the idiom the gates already use:

    sys.path.insert(0, str(Path(__file__).parent))
    from _common import check_hash_bound, open_envelope, record_from_manifest
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


def open_envelope(path, label, wrapped, noun="report"):
    """Open one committed klt envelope: `(payload, errors)`.

    The four signoff gates open the same artefacts the same way, so the
    preamble lives once (#410). `wrapped=True` is the lvs/drc dialect:
    `path` holds a wrapper document (ok/returncode/response) and the payload
    is its /response object, with wrapper faults reported alongside.
    `wrapped=False` is the pex/erc dialect: `path` holds a direct envelope
    and a document carrying an "error" or "response" key is rejected.
    `label` prefixes every message (a block name); `noun` names the artefact
    ("PEX report", "ERC report") so each gate's output stays recognisable.
    An early error returns `(None, [message])`; wrapper faults discovered on
    the way to a usable payload are returned with it.
    """
    if not Path(path).is_file():
        return None, [f"{label}: missing {noun} {path}"]
    try:
        doc = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return None, [f"{label}: unreadable {noun} {path}: {e}"]
    errs = []
    if wrapped:
        if not isinstance(doc, dict):
            return None, [f"{label}: report is not a JSON object"]
        if doc.get("ok") is not True:
            errs.append(f"{label}: wrapper ok is {doc.get('ok')!r}, expected true")
        if doc.get("returncode") != 0:
            errs.append(f"{label}: wrapper returncode is {doc.get('returncode')!r}, expected 0")
        payload = doc.get("response")
        if not isinstance(payload, dict):
            return None, errs + [f"{label}: no /response object"]
        return payload, errs
    if not isinstance(doc, dict) or "error" in doc or "response" in doc:
        return None, [f"{label}: {Path(path).name} is not a direct {noun} envelope"]
    return doc, errs


def envelope_input_hash(payload):
    """The hash this envelope recorded for its input, or None.

    One spelling for all four gates: `provenance.input.content_hash`, the
    only shape any committed envelope carries (operator ruling 2026-11-23,
    issue #410 option a). Works on a direct envelope and on a wrapper's
    /response object alike.
    """
    prov = payload.get("provenance") if isinstance(payload, dict) else None
    inp = prov.get("input") if isinstance(prov, dict) else None
    return inp.get("content_hash") if isinstance(inp, dict) else None


def check_hash_bound(payload, gds, label, message):
    """The adjacent-GDS binding pair every gate runs: the error list.

    One check for all four gates (#410): the recorded input hash
    (`envelope_input_hash`) is reported when missing and must equal
    `sha256_file(gds)`, which must exist. `message` is the caller's mismatch
    wording -- the one thing the gates keep individually recognisable --
    formatted with `h`=recorded hash, `sha`=`sha256_file(gds)`, `name`=
    `gds.name` and `gds`=the path. Callers that pair hashes across reports
    read the recorded hash themselves via `envelope_input_hash` (#565).
    """
    errs = []
    recorded = envelope_input_hash(payload)
    if not recorded:
        errs.append(f"{label}: provenance.input.content_hash missing")
    if not gds.is_file():
        errs.append(f"{label}: missing adjacent GDS {gds}")
    elif recorded and sha256_file(gds) != recorded:
        errs.append(f"{label}: " + message.format(h=recorded, sha=sha256_file(gds), name=gds.name, gds=gds))
    return errs


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
