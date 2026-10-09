"""Negative tests for check_drc_coverage.py, on temporary copies only.

Run from the repo root: python3 manifests/test_check_drc_coverage.py
The committed record is never modified. In every sibling-fault test the live
item-3 divider citation stays intact (asserted), so the failure is attributable
to the sibling DRC evidence alone.
"""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_drc_coverage as chk  # noqa: E402

MANIFEST = Path("manifests/sg13g2-pll.json")
REC = Path(json.loads(MANIFEST.read_text())["evidence"]["4.analog"]["file"]).parent


class Cov(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for b in chk.BLOCKS:
            shutil.copy(REC / f"drc.pll_{b}.json", self.tmp)
            shutil.copy(REC / f"pll_{b}.gds", self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, b, fn):
        p = self.tmp / f"drc.pll_{b}.json"
        d = json.loads(p.read_text())
        fn(d)
        p.write_text(json.dumps(d))

    def fails(self):
        # Divider citation intact against the authoritative record, yet the
        # run on the damaged copy must fail.
        self.assertEqual(chk.check_manifest(str(MANIFEST), REC), [])
        with contextlib.redirect_stderr(io.StringIO()):
            return chk.main(["--record", str(self.tmp)]) == 1

    def test_pass(self):
        self.assertEqual(chk.main(["--record", str(self.tmp)]), 0)

    def test_committed_record(self):
        self.assertEqual(chk.main([]), 0)

    def test_starter_deck_disclosures_allowed(self):
        # Non-empty skipped rules / unruled layers are retained, not failures.
        d = json.loads((self.tmp / "drc.pll_pfd.json").read_text())["response"]["coverage"]
        self.assertTrue(d["rules_skipped"] and d["layers_in_stream_without_rules"])

    def test_each_block_missing(self):
        for b in chk.BLOCKS:
            with self.subTest(b):
                self.setUp()
                (self.tmp / f"drc.pll_{b}.json").unlink()
                self.assertTrue(self.fails())

    def test_malformed(self):
        for b in chk.BLOCKS:
            with self.subTest(b):
                self.setUp()
                (self.tmp / f"drc.pll_{b}.json").write_text("{not json")
                self.assertTrue(self.fails())
        self.setUp()
        (self.tmp / "drc.pll_cp.json").write_text("[]")
        self.assertTrue(self.fails())
        self.setUp()
        self.edit("cp", lambda d: d.pop("response"))
        self.assertTrue(self.fails())

    def test_failed_wrapper(self):
        self.edit("vco", lambda d: d.update(ok=False))
        self.assertTrue(self.fails())
        self.setUp()
        self.edit("vco", lambda d: d.update(returncode=1))
        self.assertTrue(self.fails())

    def test_violating(self):
        for b in chk.BLOCKS:
            with self.subTest(b):
                self.setUp()
                self.edit(b, lambda d: d["response"].update(
                    status="violations", violation_count=3))
                self.assertTrue(self.fails())
        self.setUp()
        self.edit("pfd", lambda d: d["response"].update(violations=[{"rule": "x"}]))
        self.assertTrue(self.fails())

    def test_hash_stale(self):
        for b in chk.BLOCKS:
            with self.subTest(b):
                self.setUp()
                with open(self.tmp / f"pll_{b}.gds", "ab") as f:
                    f.write(b"\0")
                self.assertTrue(self.fails())

    def test_missing_gds_or_hash(self):
        (self.tmp / "pll_loop_filter.gds").unlink()
        self.assertTrue(self.fails())
        self.setUp()
        self.edit("cp", lambda d: d["response"].pop("provenance"))
        self.assertTrue(self.fails())

    def test_coverage_disclosures_required(self):
        self.edit("lock_detector", lambda d: d["response"].pop("coverage"))
        self.assertTrue(self.fails())
        for k in ("rules_skipped", "layers_in_stream_without_rules"):
            self.setUp()
            self.edit("vco", lambda d: d["response"]["coverage"].pop(k))
            self.assertTrue(self.fails())
        self.setUp()
        self.edit("vco", lambda d: d["response"]["coverage"].update(nothing_checked=True))
        self.assertTrue(self.fails())

    def test_divider_citation_binding(self):
        m = json.loads(MANIFEST.read_text())
        good = lambda mm: chk.check_manifest(self._write(mm), REC)  # noqa: E731
        self.assertEqual(good(m), [])
        bad = json.loads(json.dumps(m))
        bad["evidence"]["3"]["content_hash"] = "sha256:" + "0" * 64
        self.assertTrue(good(bad))
        bad = json.loads(json.dumps(m))
        bad["evidence"]["3"]["command"][2] = str(self.tmp / "nope.gds")
        self.assertTrue(good(bad))
        bad = json.loads(json.dumps(m))
        bad["evidence"]["3"]["command"][-1] = "json"
        i = bad["evidence"]["3"]["command"].index("--deck")
        bad["evidence"]["3"]["command"][i + 1] = "other"
        self.assertTrue(good(bad))
        # divider content differing from the record's divider GDS
        other = self.tmp / "pll_divider_chain.gds"
        other.write_bytes(b"x")
        bad = json.loads(json.dumps(m))
        bad["evidence"]["3"]["command"][2] = str(other)
        bad["evidence"]["3"]["content_hash"] = chk.sha256_file(other)
        self.assertTrue(good(bad))

    def _write(self, m):
        p = self.tmp / "m.json"
        p.write_text(json.dumps(m))
        return str(p)


if __name__ == "__main__":
    unittest.main()
