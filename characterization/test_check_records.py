"""Tests for check_records.py, on temporary copies/repos only (no sim/ edits).

Run from the repo root: python3 characterization/test_check_records.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_records as c  # noqa: E402

REC = "# RECORD-{n}: title (issue #1)\n\n## Result\n\nAll corners ok.\n"


def write(root, rel, text):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def git(root, *a):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                   check=True, capture_output=True)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = Path(self.tmp)
        self.paths = []
        for n, slug in (("001", "a"), ("002", "b")):
            rel = f"sim/bench/records/RECORD-{n}-{slug}.md"
            write(self.root, rel, REC.format(n=n))
            self.paths.append(rel)
        (self.root / "sim/bench/testbench").mkdir()
        write(self.root, "characterization/sources.json",
              json.dumps({"datasets": [{"record": self.paths[0], "extra_records": [self.paths[1]]}]}))

    def errs(self, base=None):
        return c.run(self.root, base)


class Layout(Fixture):
    def test_clean(self):
        self.assertEqual(self.errs(), [])

    def test_no_records_dir(self):
        shutil.rmtree(self.root / "sim/bench/records")
        self.assertTrue(any("no records/" in e for e in self.errs()))

    def test_gap(self):
        (self.root / self.paths[0]).rename(self.root / "sim/bench/records/RECORD-003-a.md")
        self.assertTrue(any("gap" in e and "001" in e for e in c.check_layout(self.root, {})))

    def test_duplicate_and_baseline(self):
        write(self.root, "sim/bench/records/RECORD-002-c.md", REC.format(n="002"))
        self.assertTrue(any("duplicate number 2" in e or "duplicate number 002" in e
                            for e in c.check_layout(self.root, {})))
        self.assertEqual(c.check_layout(self.root, {"duplicate_numbers": {"sim/bench": [2]}}), [])

    def test_stale_duplicate_baseline(self):
        self.assertTrue(c.check_layout(self.root, {"duplicate_numbers": {"sim/bench": [2]}}))

    def test_bad_name(self):
        write(self.root, "sim/bench/records/notes.md", "x")
        self.assertTrue(any("not named" in e for e in self.errs()))


class Format(Fixture):
    def test_title_mismatch(self):
        write(self.root, self.paths[1], REC.format(n="009"))
        self.assertTrue(any("!= filename" in e for e in self.errs()))

    def test_missing_title(self):
        write(self.root, self.paths[1], "## Result\ncorner\n")
        self.assertTrue(any("first line" in e for e in self.errs()))

    def test_missing_section_and_corner(self):
        write(self.root, self.paths[1], "# RECORD-002: t\n\ntext\n")
        e = self.errs()
        self.assertTrue(any("section" in x for x in e))
        self.assertTrue(any("corner" in x for x in e))


class Sources(Fixture):
    def test_unlisted(self):
        write(self.root, "sim/bench/records/RECORD-003-c.md", REC.format(n="003"))
        self.assertTrue(any("RECORD-003" in e and "not listed" in e for e in self.errs()))

    def test_baseline_exempts_and_goes_stale(self):
        p = "sim/bench/records/RECORD-003-c.md"
        write(self.root, p, REC.format(n="003"))
        b = {"unlisted_in_sources": [p]}
        s = json.loads((self.root / "characterization/sources.json").read_text())
        self.assertEqual(c.check_sources(self.root, s, b), [])
        (self.root / p).unlink()
        self.assertTrue(any("stale" in e for e in c.check_sources(self.root, s, b)))

    def test_dangling_citation(self):
        s = {"datasets": [{"record": "sim/bench/records/RECORD-009-z.md"}]}
        self.assertTrue(any("does not exist" in e for e in c.check_sources(self.root, s, {})))


class AppendOnly(Fixture):
    def setUp(self):
        super().setUp()
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")
        git(self.root, "checkout", "-q", "-b", "pr")

    def commit(self):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "pr")

    def test_no_change_ok(self):
        self.assertEqual(self.errs("main"), [])

    def test_added_record_ok(self):
        p = "sim/bench/records/RECORD-003-c.md"
        write(self.root, p, REC.format(n="003"))
        s = json.loads((self.root / "characterization/sources.json").read_text())
        s["datasets"][0]["extra_records"].append(p)
        write(self.root, "characterization/sources.json", json.dumps(s))
        self.commit()
        self.assertEqual(self.errs("main"), [])

    def test_deleted_record_fails(self):
        (self.root / self.paths[1]).unlink()
        self.commit()
        self.assertTrue(any("deleted" in e and "RECORD-002" in e for e in c.check_append_only(self.root, "main")))

    def test_edited_record_fails(self):
        with open(self.root / self.paths[0], "a") as f:
            f.write("\nsilently changed result\n")
        self.commit()
        self.assertTrue(any("modified" in e and "RECORD-001" in e for e in c.check_append_only(self.root, "main")))

    def test_renamed_record_fails(self):
        (self.root / self.paths[1]).rename(self.root / "sim/bench/records/RECORD-002-renamed.md")
        self.commit()
        self.assertTrue(any("deleted" in e for e in c.check_append_only(self.root, "main")))

    def test_non_record_edit_ok(self):
        write(self.root, "sim/bench/testbench/x.sp", "x")
        self.commit()
        self.assertEqual(c.check_append_only(self.root, "main"), [])

    def test_bad_base_reports(self):
        self.assertTrue(any("failed" in e for e in c.check_append_only(self.root, "nope")))
        self.assertTrue(c.check_baseline_growth(self.root, "nope", {}))


class BaselineGrowth(AppendOnly):
    """records_baseline.json may only shrink relative to the base ref."""
    NEW = "sim/bench/records/RECORD-003-c.md"

    def setUp(self):
        super().setUp()
        # Base branch carries a baseline with one grandfathered entry of each kind.
        git(self.root, "checkout", "-q", "main")
        write(self.root, "sim/bench/records/RECORD-002-dup.md", REC.format(n="002"))
        self.old = "sim/bench/records/RECORD-002-dup.md"
        self.baseline = {"unlisted_in_sources": [self.old], "duplicate_numbers": {"sim/bench": [2]}}
        self.write_baseline(self.baseline)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "baseline")
        git(self.root, "checkout", "-q", "pr")
        git(self.root, "reset", "-q", "--hard", "main")

    def write_baseline(self, b):
        write(self.root, c.BASELINE_REL, json.dumps(b))

    def test_unchanged_ok(self):
        self.assertEqual(self.errs("main"), [])

    def test_unlisted_entry_added_fails(self):
        write(self.root, self.NEW, REC.format(n="003"))
        self.write_baseline({**self.baseline, "unlisted_in_sources": [self.old, self.NEW]})
        self.commit()
        e = self.errs("main")
        self.assertTrue(any("unlisted_in_sources adds" in x and "RECORD-003" in x for x in e), e)

    def test_duplicate_entry_added_fails(self):
        write(self.root, "sim/bench/records/RECORD-001-dup.md", REC.format(n="001"))
        self.write_baseline({"unlisted_in_sources": [self.old, "sim/bench/records/RECORD-001-dup.md"],
                             "duplicate_numbers": {"sim/bench": [1, 2]}})
        self.commit()
        e = self.errs("main")
        self.assertTrue(any("duplicate_numbers adds sim/bench 001" in x for x in e), e)
        self.assertTrue(any("unlisted_in_sources adds" in x for x in e), e)

    def test_shrink_ok(self):
        s = json.loads((self.root / "characterization/sources.json").read_text())
        s["datasets"][0]["extra_records"].append(self.old)
        write(self.root, "characterization/sources.json", json.dumps(s))
        self.write_baseline({"unlisted_in_sources": [], "duplicate_numbers": {"sim/bench": [2]}})
        self.commit()
        self.assertEqual(self.errs("main"), [])

    def test_base_without_baseline_skipped(self):
        self.assertEqual(c.check_baseline_growth(self.root, "main~1", self.baseline), [])


class Committed(unittest.TestCase):
    def test_repo_records_pass(self):
        self.assertEqual(c.run(c.ROOT), [])


if __name__ == "__main__":
    unittest.main()
