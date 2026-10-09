"""Negative tests for check_spec_citations.py, on temporary copies only.

Run from the repo root: python3 manifests/test_check_spec_citations.py
The committed spec/ and sim/ trees are never modified.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_spec_citations as chk  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SPEC = (REPO / "spec" / "target-spec.md").read_text()


class Cit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for rec in (REPO / "sim").glob("*/records/RECORD-*.md"):
            dst = self.tmp / rec.relative_to(REPO)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.touch()
        for p in (REPO / "spec" / "decision-records").glob("DR-*.md"):
            dst = self.tmp / "spec" / "decision-records" / p.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.touch()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_spec(self, text):
        p = self.tmp / "spec.md"
        p.write_text(text)
        return chk.check(self.tmp, p)

    def mutate(self, old, new, count=1):
        self.assertIn(old, SPEC)
        return self.run_spec(SPEC.replace(old, new, count))

    def assertFails(self, errs, *needles):
        joined = "\n".join(errs)
        self.assertTrue(errs, "expected failure, got none")
        for n in needles:
            self.assertIn(n, joined)

    def test_real_repo_passes(self):
        self.assertEqual(chk.check(REPO, REPO / "spec" / "target-spec.md"), [])

    def test_stub_tree_passes(self):
        self.assertEqual(self.run_spec(SPEC), [])

    def test_missing_record(self):
        errs = self.mutate("`records/RECORD-001-duty-cycle-and-vco-current.md` |",
                           "`records/RECORD-099-nope.md` |")
        self.assertFails(errs, "row 13", "RECORD-099-nope.md")

    def test_missing_bench_dir(self):
        errs = self.mutate("`sg13cmos5l-vco-duty-cycle`", "`sg13cmos5l-no-such-bench`")
        self.assertFails(errs, "row 13", "sg13cmos5l-no-such-bench")

    def test_bad_status(self):
        errs = self.mutate("| 14 | Output levels / drive | P |",
                           "| 14 | Output levels / drive | X |")
        self.assertFails(errs, "row 14", "'X'")

    def test_m_row_without_record(self):
        import re
        text = re.sub(r"(\| 17 \| Standby / power-down \| )N", r"\1M", SPEC)
        self.assertFails(self.run_spec(text), "row 17", "no record")

    def test_o_row_without_gate_or_ref(self):
        errs = self.mutate("No number proposed. Gate: R-7 | porting-plan row 8",
                           "No number proposed. | porting-plan row 8")
        self.assertFails(errs, "row 8", "Gate")

    def test_unknown_r_ref(self):
        errs = self.mutate("Gate: R-7 | porting-plan row 8", "Gate: R-77 | porting-plan row 8")
        self.assertFails(errs, "row 8", "R-77")

    def test_unknown_dr(self):
        errs = self.mutate("DR-002 Decision 5 (proposed)", "DR-099 Decision 5 (proposed)")
        self.assertFails(errs, "row 9", "DR-099")

    def test_missing_slugged_dr_file(self):
        errs = self.mutate("DR-006 `loop-filter-r1-resize`", "DR-006 `no-such-slug`")
        self.assertFails(errs, "row 6/6a", "no-such-slug")

    def test_dr006_triple_resolves_without_slug(self):
        self.assertEqual(len(list((self.tmp / "spec/decision-records").glob("DR-006-*.md"))), 3)
        self.assertEqual(self.mutate("DR-006 `loop-filter-r1-resize`", "DR-006"), [])

    def test_multi_bench_multi_record_cells(self):
        # rows 1, 6/6a, 16 cite several benches / records; dropping one file fails
        # only that citation, naming the row.
        (self.tmp / "sim/sg13cmos5l-loop-bandwidth-pm/records/"
         "RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md").unlink()
        errs = chk.check(self.tmp, self.write_spec(SPEC))
        self.assertEqual(len(errs), 1)
        self.assertFails(errs, "row 6/6a", "RECORD-004-issue79")
        (self.tmp / "sim/sg13g2-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md").unlink()
        self.assertFails(chk.check(self.tmp, self.write_spec(SPEC)), "row 1:")

    def write_spec(self, text):
        p = self.tmp / "spec.md"
        p.write_text(text)
        return p

    def test_row11_per_domain_path(self):
        errs = self.mutate("records/RECORD-004-crowbar-current-mitigation.md`.",
                           "records/RECORD-404-gone.md`.")
        self.assertFails(errs, "RECORD-404-gone.md")

    def test_missing_row(self):
        import re
        text = re.sub(r"^\| 17 \|.*\n", "", SPEC, flags=re.M)
        self.assertFails(self.run_spec(text), "row 17", "missing")


if __name__ == "__main__":
    unittest.main()
