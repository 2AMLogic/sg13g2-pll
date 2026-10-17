"""Negative tests for check_netlist_stamp.py, on a temporary copy only.

Run from the repo root: python3 manifests/test_check_netlist_stamp.py
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_netlist_stamp as chk  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class Stamp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for tree in chk.TREES:
            for p in (REPO / tree).iterdir():
                if p.suffix in (".sch", ".sym", ".spice"):
                    dst = self.tmp / p.relative_to(REPO)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(p, dst)
            shutil.copytree(REPO / tree / "netlist", self.tmp / tree / "netlist", dirs_exist_ok=True)
        shutil.copy(REPO / chk.STAMP, self.tmp / chk.STAMP)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_committed_is_current(self):
        self.assertEqual(chk.check(REPO), [])

    def test_edited_schematic_fails(self):
        with open(self.tmp / "design" / "pfd.sch", "a") as f:
            f.write("\n")
        self.assertTrue(chk.check(self.tmp))
        self.assertTrue(chk.check(self.tmp, "design/netlist/pfd.spice"))

    def test_edited_netlist_fails(self):
        with open(self.tmp / "design/sg13cmos5l/netlist/cp.spice", "a") as f:
            f.write("*\n")
        self.assertTrue(chk.check(self.tmp, "design/sg13cmos5l/netlist/cp.spice"))

    def test_unstamped_netlist_fails(self):
        self.assertTrue(chk.check(self.tmp, "design/netlist/nope.spice"))


if __name__ == "__main__":
    unittest.main()
