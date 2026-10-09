"""Tests for gen_summary.py, on temporary copies only (no simulation, no sim/ edits).

Run from the repo root: python3 characterization/test_gen_summary.py
"""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gen_summary as g  # noqa: E402


class Extrema(unittest.TestCase):
    ROWS = [
        {"arm": "a", "x": "1.5", "c": "p"},
        {"arm": "a", "x": "-2", "c": "q"},
        {"arm": "b", "x": "100", "c": "p"},
        {"arm": "a", "x": "NA", "c": "p"},
        {"arm": "a", "x": "", "c": "p"},
    ]

    def test_min_max_all(self):
        e = g.extrema(self.ROWS, "x")
        self.assertEqual((e["min"], e["max"]), (-2.0, 100.0))
        self.assertEqual((e["rows"], e["numeric"], e["non_numeric"]), (5, 3, 2))

    def test_filter(self):
        e = g.extrema(self.ROWS, "x", {"arm": "a"})
        self.assertEqual((e["min"], e["max"]), (-2.0, 1.5))
        self.assertEqual(e["rows"], 4)

    def test_no_numeric(self):
        e = g.extrema(self.ROWS, "x", {"arm": "a", "c": "zzz"})
        self.assertIsNone(e["min"])
        self.assertIsNone(e["max"])

    def test_coverage(self):
        cov = g.coverage(self.ROWS, ["c"], {"arm": "a"})
        self.assertEqual(cov["c"], ["p", "q"])

    def test_committed_csv_matches_independent_computation(self):
        """Extrema of a committed CSV equals a from-scratch parse of the raw file."""
        src = g.load_sources()
        ds = next(d for d in src["datasets"] if d["id"] == "g2-vco-kvco-table")
        t = ds["tables"][0]
        lines = (g.ROOT / t["path"]).read_text().strip().splitlines()
        col = lines[0].split(",").index("freq_hz")
        vals = [float(l.split(",")[col]) for l in lines[1:]]
        e = g.extrema(g.read_rows(t), "freq_hz")
        self.assertEqual((e["min"], e["max"]), (min(vals), max(vals)))


class Tree(unittest.TestCase):
    """Copy only the files sources.json cites into a temp root."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = g.load_sources()
        for ds in self.src["datasets"]:
            for _, rel, _ in g.source_files(ds):
                dst = self.tmp / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(g.ROOT / rel, dst)
        self.summary = self.tmp / "SUMMARY.md"
        self.summary.write_text(g.render(self.src, self.tmp))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def first_csv(self):
        ds = next(d for d in self.src["datasets"] if d["id"] == "g2-vco-kvco-table")
        return self.tmp / ds["tables"][0]["path"]

    def test_clean_tree_passes(self):
        self.assertEqual(g.check(self.src, self.tmp, self.summary), [])

    def test_committed_summary_is_fresh(self):
        self.assertEqual(g.check(self.src), [])

    def test_hash_mismatch_detected(self):
        p = self.first_csv()
        p.write_text(p.read_text().replace("2.024444e-09", "2.024445e-09", 1))
        probs = g.check_hashes(self.src, self.tmp)
        self.assertTrue(any("sha256 changed" in x for x in probs), probs)
        self.assertTrue(g.check(self.src, self.tmp, self.summary))

    def test_missing_source_detected(self):
        self.first_csv().unlink()
        probs = g.check_hashes(self.src, self.tmp)
        self.assertTrue(any("missing" in x for x in probs), probs)

    def test_unpinned_hash_detected(self):
        src = copy.deepcopy(self.src)
        src["datasets"][0]["tables"][0]["sha256"] = ""
        self.assertTrue(any("no sha256" in x for x in g.check_hashes(src, self.tmp)))

    def test_stale_summary_detected(self):
        self.summary.write_text(self.summary.read_text().replace("| 60 |", "| 61 |", 1))
        probs = g.check(self.src, self.tmp, self.summary)
        self.assertTrue(any("stale" in x for x in probs), probs)

    def test_stale_extrema_detected(self):
        """A moved bound (summary edited to disagree with the CSV) is stale."""
        txt = self.summary.read_text()
        self.summary.write_text(txt.replace("1.56197e+09", "1.56198e+09", 1))
        self.assertTrue(g.check(self.src, self.tmp, self.summary))

    def test_missing_summary_detected(self):
        self.summary.unlink()
        self.assertTrue(g.check(self.src, self.tmp, self.summary))


class NoSpecVerdict(unittest.TestCase):
    def test_no_pass_fail_column(self):
        header = [l for l in g.render(g.load_sources()).splitlines() if l.startswith("| Quantity")]
        self.assertTrue(header)
        for h in header:
            low = h.lower()
            for bad in ("pass", "fail", "spec", "target", "meets"):
                self.assertNotIn(bad, low)

    def test_every_dataset_has_required_context(self):
        for ds in g.load_sources()["datasets"]:
            for k in ("pdk", "dut_revision", "context", "conditions", "method", "status", "record", "tables", "metrics"):
                self.assertTrue(ds.get(k), (ds["id"], k))
            self.assertIn(ds["status"], ("current", "superseded", "historical"))
            for m in ds["metrics"]:
                self.assertTrue(m.get("units") and m.get("coverage_columns") is not None, (ds["id"], m))

    def test_sources_json_is_explicit_paths_only(self):
        for ds in g.load_sources()["datasets"]:
            for _, rel, _ in g.source_files(ds):
                self.assertNotIn("*", rel)
                self.assertTrue(rel.startswith("sim/"))


if __name__ == "__main__":
    unittest.main()
