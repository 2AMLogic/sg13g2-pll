"""Tests for check_artifact_manifests.py and store_evidence.py fail-closed paths.

Run from the repo root: python3 scripts/test_check_artifact_manifests.py
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_artifact_manifests as chk  # noqa: E402

DATA = b"raw sim output\n"
SHA = hashlib.sha256(DATA).hexdigest()
ENTRY = {
    "sha256": SHA, "size": len(DATA), "kind": "evidence", "name": "a/raw.csv",
    "producer": {"tool": "klt", "version": "0.7.1", "loom.repo": "o/r", "commit": None},
    "uri": f"artifact:o/r/{SHA}",
}


class Check(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "manifests" / "artifacts").mkdir(parents=True)

    def tearDown(self):
        self._t.cleanup()

    def write(self, entry=None, raw=None):
        doc = {"schema_version": 1, "entries": [entry or ENTRY]}
        text = raw if raw is not None else json.dumps(doc)
        (self.root / "manifests" / "artifacts" / "b-r1.manifest.json").write_text(text)

    def problems(self):
        return chk.check(self.root)[0]

    def test_no_manifests_passes(self):
        self.assertEqual(chk.check(self.root), ([], 0))

    def test_valid_passes(self):
        self.write()
        self.assertEqual(self.problems(), [])

    def test_non_artifact_uri_fails(self):
        e = copy.deepcopy(ENTRY)
        e["uri"] = "file:///tmp/x"
        self.write(e)
        self.assertTrue(self.problems())

    def test_s3_uri_fails(self):
        e = copy.deepcopy(ENTRY)
        e["uri"] = "s3://bucket/key"
        self.write(e)
        self.assertTrue(any("storage location" in p for p in self.problems()))

    def test_arn_in_name_fails(self):
        e = copy.deepcopy(ENTRY)
        e["name"] = "arn:aws:s3:::b"
        self.write(e)
        self.assertTrue(any("storage location" in p for p in self.problems()))

    def test_bad_schema_fails(self):
        self.write(raw=json.dumps({"schema_version": 2, "entries": [ENTRY]}))
        self.assertTrue(self.problems())

    def test_missing_field_fails(self):
        e = copy.deepcopy(ENTRY)
        del e["size"]
        self.write(e)
        self.assertTrue(self.problems())

    def test_committed_duplicate_fails(self):
        self.write()
        (self.root / "dup.csv").write_bytes(DATA)
        subprocess.run(["git", "-C", str(self.root), "add", "dup.csv"], check=True)
        self.assertTrue(any("duplicates committed file dup.csv" in p for p in self.problems()))

    def test_same_size_different_bytes_passes(self):
        self.write()
        (self.root / "other.csv").write_bytes(b"x" * len(DATA))
        subprocess.run(["git", "-C", str(self.root), "add", "other.csv"], check=True)
        self.assertEqual(self.problems(), [])


class StoreFailsClosed(unittest.TestCase):
    def test_no_broker_env_writes_nothing(self):
        script = Path(__file__).parent / "store_evidence.py"
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "raw.csv").write_bytes(DATA)
            (Path(d) / "s.md").write_text("summary")
            env = {k: v for k, v in os.environ.items() if k != "KLT_ARTIFACT_BROKER"}
            r = subprocess.run([sys.executable, str(script), "b", "r1", d, "--summary", str(Path(d) / "s.md")],
                               env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("KLT_ARTIFACT_BROKER", r.stderr)
        self.assertFalse((Path(__file__).parent.parent / "manifests" / "artifacts" / "b-r1.manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
