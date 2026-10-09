"""Negative tests for check_testbench_coverage.py, on temporary copies only.

Run from the repo root: python3 manifests/test_check_testbench_coverage.py
The committed sim/ tree is never modified.
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_testbench_coverage as chk  # noqa: E402

PIN = "607e18d4bd9214a52575c194b4181ef449f9252f"
SLUG = "sg13cmos5l-vco-kvco-table"
GOOD = f"- **Tooling**: `ngspice-46`, PDK revision `{PIN}`.\n"
BAD = "- **Tooling**: `ngspice-46`, installed `~/share/pdk/ihp-sg13cmos5l`.\n"


class Cov(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sim = self.tmp / "sim"
        shutil.copy("sim/README.md", self.tmp / "README.md")
        self.sim.mkdir()
        shutil.copy("sim/README.md", self.sim / "README.md")
        text = (self.sim / "README.md").read_text()
        for m in re.finditer(r"^\| `([^`]+)` \| `([^`]+)` \|", text, re.M):
            slug, entry = m.groups()
            (self.sim / slug / "records").mkdir(parents=True, exist_ok=True)
            ep = self.sim / slug / entry
            ep.parent.mkdir(parents=True, exist_ok=True)
            ep.write_text("#!/bin/sh\n")
            ep.chmod(0o755)
        self.recs = {}
        for rec in Path("sim").glob("*/records/RECORD-*.md"):
            dst = self.sim / rec.relative_to("sim")
            shutil.copy(rec, dst)
        self.man = self.tmp / "m.json"
        self.man.write_text(json.dumps({"evidence": {}}))
        self.tier = self.tmp / "t.json"
        self.set_tier("unmet")
        self.saved = dict(chk.KNOWN_DEFECTS)

    def tearDown(self):
        chk.KNOWN_DEFECTS.clear()
        chk.KNOWN_DEFECTS.update(self.saved)
        shutil.rmtree(self.tmp)

    def set_tier(self, status):
        self.tier.write_text(json.dumps({"items": [{"id": 9, "status": status}]}))

    def run_main(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = chk.main(["--sim", str(self.sim), "--manifest", str(self.man),
                           "--tier-report", str(self.tier)])
        return rc, err.getvalue()

    def new_record(self, body, slug=SLUG, name="RECORD-099-new.md"):
        p = self.sim / slug / "records" / name
        p.write_text(body)
        return p

    def test_committed_tree(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(chk.main([]), 0)

    def test_pass_on_copy(self):
        self.assertEqual(self.run_main()[0], 0)

    def test_new_record_missing_pdk_revision_fails(self):
        self.new_record(BAD)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("RECORD-099-new.md: no PDK revision", err)

    def test_new_record_with_pinned_revision_passes(self):
        self.new_record(GOOD)
        self.assertEqual(self.run_main()[0], 0)

    def test_new_record_missing_tool_version_fails(self):
        self.new_record(f"PDK revision {PIN}\n")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("no tool version", err)

    def test_discrepant_revision_fails(self):
        self.new_record("ngspice-46, PDK revision `" + "a" * 40 + "`\n")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("DISCREPANCY", err)

    def test_unindexed_bench_fails(self):
        (self.sim / "sg13cmos5l-new-bench" / "records").mkdir(parents=True)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("not in the sim/README.md bench index", err)

    def test_indexed_bench_without_dir_fails(self):
        shutil.rmtree(self.sim / SLUG)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("no sim/" + SLUG, err)

    def test_missing_entry_fails(self):
        (self.sim / SLUG / "testbench" / "run.sh").unlink()
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("does not exist", err)

    def test_non_executable_entry_fails(self):
        (self.sim / SLUG / "testbench" / "run.sh").chmod(0o644)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("not executable", err)

    def test_undocumented_invocation_fails(self):
        p = self.sim / "README.md"
        p.write_text(p.read_text().replace(f"sim/{SLUG}/testbench/run.sh", "TODO", 1))
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("does not document entry point", err)

    def test_missing_cold_start_fails(self):
        p = self.sim / "README.md"
        p.write_text(p.read_text().replace("## Cold start", "## Warm start"))
        self.assertEqual(self.run_main()[0], 1)

    def test_stale_known_defect_fails(self):
        rec = next(iter(chk.KNOWN_DEFECTS))
        (self.sim / rec).write_text(GOOD)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("stale entry", err)

    def test_met_with_open_defects_fails(self):
        self.set_tier("met")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("grades item 9 met", err)

    def test_manifest_citing_item9_with_open_defects_fails(self):
        self.man.write_text(json.dumps({"evidence": {"9.analog": {"file": "x"}}}))
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("cites item 9", err)

    def test_unknown_pin_fails_once_nothing_grandfathered(self):
        chk.KNOWN_DEFECTS.clear()
        for rec in (self.sim).glob("*/records/RECORD-*.md"):
            rec.write_text(GOOD)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("UNKNOWN", err)


if __name__ == "__main__":
    unittest.main()
