"""Negative tests for check_pex_coverage.py, on temporary copies only.

Run from the repo root: python3 manifests/test_check_pex_coverage.py
The committed evidence is never modified: a minimal repo tree is rebuilt in a
temp dir (GDS symlinked read-only, everything else copied and edited there).
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_pex_coverage as chk  # noqa: E402

REPO = Path.cwd().resolve()
MANIFEST = "manifests/sg13g2-pll.json"
S = chk.SIGNOFF
REC = Path(json.loads((REPO / MANIFEST).read_text())["evidence"]["4.analog"]["file"]).parent
ORIG_STALE = dict(chk.STALE_PENDING)


class Pex(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / S, self.root / S)
        (self.root / "manifests").mkdir()
        shutil.copy(REPO / MANIFEST, self.root / MANIFEST)
        shutil.copytree(REPO / "design/sg13cmos5l/netlist", self.root / "design/sg13cmos5l/netlist")
        rec = self.root / REC
        rec.mkdir(parents=True)
        for b in chk.BLOCKS:
            (rec / f"pll_{b}.gds").symlink_to((REPO / REC / f"pll_{b}.gds").resolve())
        (rec / "lvs.lock_detector.json").write_text("{}")

    def tearDown(self):
        chk.STALE_PENDING.clear()
        chk.STALE_PENDING.update(ORIG_STALE)
        shutil.rmtree(self.root)

    def run_chk(self):
        err = io.StringIO()
        with redirect_stderr(err):
            rc = chk.main(["--root", str(self.root)])
        return rc, err.getvalue()

    def rep(self, b):
        return self.root / S / "reports" / f"pex.{b}.json"

    def edit(self, path, fn):
        d = json.loads(path.read_text())
        fn(d)
        path.write_text(json.dumps(d))

    def fails(self, *needles):
        rc, err = self.run_chk()
        self.assertEqual(rc, 1, err)
        for n in needles:
            self.assertIn(n, err)

    def test_baseline_passes(self):
        rc, err = self.run_chk()
        self.assertEqual(rc, 0, err)

    def test_removed_report_each_block(self):
        for b in chk.BLOCKS:
            with self.subTest(b):
                self.rep(b).unlink()
                self.fails(f"{b}: missing PEX report")
                shutil.copy(REPO / S / "reports" / f"pex.{b}.json", self.rep(b))

    def test_failed_status(self):
        self.edit(self.rep("pfd"), lambda d: d.update(status="fail", failed=1))
        self.fails("pfd: status 'fail'")

    def test_unbiased_body(self):
        self.edit(self.rep("cp"), lambda d: d["body_bias"].update(status="unbiased", unbiased_device_count=3))
        self.fails("cp: body_bias not clean")

    def test_stale_uncited_report_hash(self):
        self.edit(self.rep("loop_filter"), lambda d: d["provenance"]["input"].update(content_hash="sha256:" + "0" * 64))
        self.fails("loop_filter: provenance input hash")

    def test_foreign_block_identity(self):
        shutil.copy(self.rep("pfd"), self.rep("cp"))
        self.fails("cp: layout.path", "cp: provenance input hash")

    def test_altered_leg(self):
        leg = self.root / S / "dut/pll_pfd.schematic.sp"
        leg.write_text(leg.read_text() + "* tampered\n")
        self.fails("pfd: schematic leg sha256", "pfd: committed schematic leg differs")

    # STALE_PENDING is empty since #195; these tests inject an entry to keep the
    # mechanism's negative coverage (tearDown restores the module state).
    def stale(self, b="cp", issue="#999"):
        chk.STALE_PENDING[b] = issue
        return b

    def make_export_stale(self, b):
        src = self.root / f"design/sg13cmos5l/netlist/{b}.spice"
        txt = src.read_text()
        self.assertIn("w=2u", txt)
        src.write_text(txt.replace("w=2u", "w=3u", 1))

    def test_stale_pending_is_empty(self):
        # #195 acceptance: no block is excused from the freshness checks.
        self.assertEqual(ORIG_STALE, {})

    def test_altered_leg_of_stale_pending_block(self):
        # A STALE_PENDING block keeps its leg-integrity check.
        b = self.stale()
        self.make_export_stale(b)
        leg = self.root / S / f"dut/pll_{b}.schematic.sp"
        leg.write_text(leg.read_text() + "* tampered\n")
        self.fails(f"{b}: schematic leg sha256")

    def test_genuinely_stale_pending_block_passes(self):
        # The documented-unmet state still works when the staleness is real.
        b = self.stale()
        self.make_export_stale(b)
        rc, err = self.run_chk()
        self.assertEqual(rc, 0, err)

    def test_stale_pending_entry_must_be_removed_once_fresh(self):
        # cp's export, leg and report are fresh: re-listing it must fail.
        b = self.stale()
        self.fails(f"{b}: listed in STALE_PENDING", "stale entry")

    def test_stale_pending_block_cannot_be_cited(self):
        b = self.stale()
        self.make_export_stale(b)
        mp = self.root / MANIFEST
        self.edit(mp, lambda d: d["evidence"]["7.analog"].update(file=f"{S}/reports/pex.{b}.json"))
        self.fails(f"manifest: 7.analog cites {b}")

    def test_cp_export_change_is_stale(self):
        # Without an exception, a moved cp export fails closed (the pre-#195 state).
        self.make_export_stale("cp")
        self.fails("cp: design export cp.spice sha256", "PEX evidence is stale")

    def test_cp_report_on_pre_dr010_gds(self):
        # The pre-#195 envelope's input hash (the source-follower pll_cp).
        self.edit(self.rep("cp"), lambda d: d["provenance"]["input"].update(
            content_hash="sha256:95c64289aabffba79a0eee418c5f2012ef4c04f710bf325124e65fd8b640872c"))
        self.fails("cp: provenance input hash")

    def test_changed_source_export(self):
        src = self.root / "design/sg13cmos5l/netlist/vco.spice"
        src.write_text(src.read_text() + "\n* design edit\n")
        self.fails("vco: design export vco.spice sha256", "PEX evidence is stale")

    def test_hash_only_edit_is_not_enough(self):
        # Change the design for real (alters the flattened output), then "fix" the
        # provenance hash only: the regeneration compare must still fail.
        src = self.root / "design/sg13cmos5l/netlist/pfd.spice"
        txt = src.read_text()
        self.assertIn("w=5u", txt)
        src.write_text(txt.replace("w=5u", "w=6u", 1))
        pp = self.root / S / "leg-provenance.json"
        self.edit(pp, lambda d: d["blocks"]["pfd"].update(source_sha256=chk.sha256_file(src)))
        self.fails("pfd: committed schematic leg differs")

    def test_lock_detector_stays_withheld(self):
        self.rep("lock_detector").write_text("{}")
        self.fails("lock_detector: report present but evidence is withheld pending #157")

    def test_manifest_citation_hash(self):
        mp = self.root / MANIFEST
        self.edit(mp, lambda d: d["evidence"]["7.analog"].update(content_hash="sha256:" + "1" * 64))
        self.fails("manifest: 7.analog pinned to")


if __name__ == "__main__":
    unittest.main()
