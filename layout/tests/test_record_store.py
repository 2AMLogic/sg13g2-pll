"""Offline tests for bin/record_store.py (issue #261): identical vs changed
artifacts, per-run identity, stable prior records, missing/corrupt
references, pre-existing plain records and LATEST."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "bin"
spec = importlib.util.spec_from_file_location("record_store", BIN / "record_store.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)

BIG = 70 * 1024


def make_record(reports: Path, rid: str, gds: bytes, status: str = "pass") -> Path:
    d = reports / rid
    d.mkdir(parents=True)
    (d / "record.md").write_text(f"# {rid}\n{status}\n")
    (d / "plan.json").write_text("{}")
    (d / "build.json").write_text(f'{{"status": "{status}"}}')
    (d / "a.gds").write_bytes(gds)
    (d / "small.json").write_text("{}")
    return d


def test_identical_artifacts_share_one_object_but_keep_run_identity(tmp_path):
    r1 = make_record(tmp_path, "20260101-000000-aaa", b"x" * BIG)
    r2 = make_record(tmp_path, "20260102-000000-bbb", b"x" * BIG, status="fail")
    rs.dedupe(r1)
    rs.dedupe(r2)
    assert len(list((tmp_path / "objects").iterdir())) == 1
    assert (r1 / "a.gds").read_bytes() == (r2 / "a.gds").read_bytes()
    # per-run evidence stays inline and distinct
    assert (r1 / "build.json").read_text() != (r2 / "build.json").read_text()
    assert not (r2 / "build.json").is_symlink()
    assert rs.verify(r1) == [] and rs.verify(r2) == []


def test_changed_artifact_gets_its_own_object_and_prior_record_is_stable(tmp_path):
    r1 = make_record(tmp_path, "r1", b"x" * BIG)
    rs.dedupe(r1)
    before = (r1 / "a.gds").read_bytes()
    r2 = make_record(tmp_path, "r2", b"y" * BIG)
    rs.dedupe(r2)
    assert len(list((tmp_path / "objects").iterdir())) == 2
    assert (r1 / "a.gds").read_bytes() == before
    assert (r2 / "a.gds").read_bytes() != before


def test_small_files_stay_inline_and_manifest_records_hashes(tmp_path):
    r = make_record(tmp_path, "r", b"x" * BIG)
    m = rs.dedupe(r)
    by = {e["path"]: e for e in m["artifacts"]}
    assert by["small.json"]["storage"] == "inline"
    assert by["a.gds"]["storage"] == "object"
    assert by["a.gds"]["sha256"] == rs.sha256_file(r / "a.gds")
    assert not (r / "small.json").is_symlink()


def test_missing_object_fails_verify(tmp_path):
    r = make_record(tmp_path, "r", b"x" * BIG)
    rs.dedupe(r)
    next((tmp_path / "objects").iterdir()).unlink()
    assert any("missing or dangling" in p for p in rs.verify(r))


def test_corrupt_object_fails_verify_and_is_not_reused(tmp_path):
    r1 = make_record(tmp_path, "r1", b"x" * BIG)
    rs.dedupe(r1)
    obj = next((tmp_path / "objects").iterdir())
    obj.chmod(0o644)
    obj.write_bytes(b"z" * BIG)
    assert any("sha256" in p for p in rs.verify(r1))
    r2 = make_record(tmp_path, "r2", b"x" * BIG)
    with pytest.raises(rs.StoreError, match="corrupt object"):
        rs.dedupe(r2)


def test_unlisted_file_fails_verify(tmp_path):
    r = make_record(tmp_path, "r", b"x" * BIG)
    rs.dedupe(r)
    (r / "extra.json").write_text("{}")
    assert any("not listed" in p for p in rs.verify(r))


def test_plain_pre_existing_record_is_untouched_and_verifies(tmp_path):
    r = make_record(tmp_path, "old", b"x" * BIG)
    snap = {p.name: p.read_bytes() for p in r.iterdir()}
    assert rs.verify(r) == []
    assert {p.name: p.read_bytes() for p in r.iterdir()} == snap


def test_record_is_not_deduped_twice(tmp_path):
    r = make_record(tmp_path, "r", b"x" * BIG)
    rs.dedupe(r)
    with pytest.raises(rs.StoreError, match="already has"):
        rs.dedupe(r)


def test_latest_pointer_resolves_through_symlinks(tmp_path):
    r = make_record(tmp_path, "r", b"x" * BIG)
    rs.dedupe(r)
    (tmp_path / "LATEST").write_text("r\n")
    cur = tmp_path / (tmp_path / "LATEST").read_text().strip()
    assert (cur / "a.gds").stat().st_size == BIG
    assert os.readlink(cur / "a.gds").startswith("../objects/")
