"""Negative tests for check_lvs_coverage.py, on temporary copies only.

Run from the repo root: python3 manifests/test_check_lvs_coverage.py
The committed record is never modified.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_lvs_coverage as chk  # noqa: E402

REC = Path(json.loads(Path("manifests/sg13g2-pll.json").read_text())["evidence"]["4.analog"]["file"]).parent
BLOCKS = chk.ANALOG_BLOCKS + (chk.DIGITAL_BLOCK,)


class Cov(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for b in BLOCKS:
            shutil.copy(REC / f"lvs.{b}.json", self.tmp)
            shutil.copy(REC / f"pll_{b}.gds", self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, b, fn):
        p = self.tmp / f"lvs.{b}.json"
        d = json.loads(p.read_text())
        fn(d)
        p.write_text(json.dumps(d))

    def run_main(self):
        return chk.main(["--record", str(self.tmp)])

    def test_pass(self):
        self.assertEqual(self.run_main(), 0)

    def test_committed_record(self):
        self.assertEqual(chk.main([]), 0)

    def test_each_mismatch(self):
        for b in BLOCKS:
            with self.subTest(b):
                self.setUp()
                self.edit(b, lambda d: d["response"].__setitem__("status", "mismatch"))
                self.assertEqual(self.run_main(), 1)

    def test_missing_report(self):
        (self.tmp / "lvs.vco.json").unlink()
        self.assertEqual(self.run_main(), 1)

    def test_failed_wrapper(self):
        self.edit("cp", lambda d: d.update(ok=False))
        self.assertEqual(self.run_main(), 1)
        self.setUp()
        self.edit("cp", lambda d: d.update(returncode=1))
        self.assertEqual(self.run_main(), 1)

    def test_missing_status(self):
        self.edit("pfd", lambda d: d["response"].pop("status"))
        self.assertEqual(self.run_main(), 1)

    def test_missing_gds(self):
        (self.tmp / "pll_loop_filter.gds").unlink()
        self.assertEqual(self.run_main(), 1)

    def test_changed_gds(self):
        with open(self.tmp / "pll_lock_detector.gds", "ab") as f:
            f.write(b"\0")
        self.assertEqual(self.run_main(), 1)


if __name__ == "__main__":
    unittest.main()
