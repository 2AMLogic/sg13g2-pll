"""Negative tests for check_testbench_coverage.py, on temporary copies only.

Run from the repo root: python3 manifests/test_check_testbench_coverage.py
The committed sim/ tree is never modified.
"""
import contextlib
import hashlib
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


SG = "sg13g2-vco-kvco-table"
REV2 = "b" * 40


class Addenda(Cov):
    def orig(self, slug=SLUG):
        p = next((self.sim / slug / "records").glob("RECORD-*.md"))
        return p, p.relative_to(self.sim).as_posix()

    def addendum(self, rel, kind="recovered", name="ADDENDUM-001-x.md", **kw):
        p = self.sim / rel
        f = {"FOR": rel, "KIND": kind, "SHA256": hashlib.sha256(p.read_bytes()).hexdigest(),
             "EVIDENCE": "host checkout log"}
        if kind == "recovered":
            f.update({"TOOL": "ngspice-46"})
        f.update(kw)
        lines = [f"ADDENDUM-{k}: {v}" for k, v in f.items() if v is not None]
        if kind == "recovered" and "PDK" not in kw:
            lines.append(f"ADDENDUM-PDK: {tree_for(rel)} {PIN}")
        if "PDK" in kw:
            lines = [l for l in lines if not l.startswith("ADDENDUM-PDK: None")]
        (self.sim / rel).parent.joinpath(name).write_text("\n".join(lines) + "\n")

    def test_recovered_resolves_and_original_untouched(self):
        p, rel = self.orig()
        before = p.read_bytes()
        self.addendum(rel)
        rc, err = self.run_main()
        self.assertEqual(rc, 0, err)
        self.assertEqual(p.read_bytes(), before)

    def test_recovered_differing_from_pin_is_retained(self):
        p, rel = self.orig()
        self.addendum(rel, PDK=None)
        a = p.parent / "ADDENDUM-001-x.md"
        a.write_text(a.read_text() + f"ADDENDUM-PDK: ihp-sg13cmos5l {REV2}\n")
        a.write_text("\n".join(l for l in a.read_text().splitlines()
                               if PIN not in l) + "\n")
        self.assertEqual(self.run_main()[0], 0)

    def test_mixed_pdk_ok_and_contradiction_fails(self):
        p, rel = self.orig()
        self.addendum(rel)
        a = p.parent / "ADDENDUM-001-x.md"
        base = a.read_text()
        a.write_text(base + f"ADDENDUM-PDK: ihp-sg13g2 {REV2}\n")
        self.assertEqual(self.run_main()[0], 0)
        a.write_text(base + f"ADDENDUM-PDK: ihp-sg13cmos5l {REV2}\n")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("contradictory", err)

    def test_wrong_tree_and_short_revision_fail(self):
        p, rel = self.orig()
        self.addendum(rel, PDK=None)
        a = p.parent / "ADDENDUM-001-x.md"
        a.write_text(a.read_text() + f"ADDENDUM-PDK: ihp-sg13zz {PIN}\n")
        rc, err = self.run_main()
        self.assertIn("unknown PDK tree", err)
        a.write_text(a.read_text().replace(f"ihp-sg13zz {PIN}", "ihp-sg13g2 abc123"))
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("40-hex", err)

    def test_missing_tool_fails(self):
        p, rel = self.orig()
        self.addendum(rel, TOOL="")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("no tool version", err)

    def test_missing_evidence_fails(self):
        p, rel = self.orig()
        self.addendum(rel, EVIDENCE="")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("missing ADDENDUM-EVIDENCE", err)

    def test_hash_mismatch_fails(self):
        p, rel = self.orig()
        self.addendum(rel, SHA256="0" * 64)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("SHA256", err)

    def test_dangling_and_cross_bench_for_fail(self):
        p, rel = self.orig()
        self.addendum(rel, FOR=f"{SLUG}/records/RECORD-777-none.md")
        rc, err = self.run_main()
        self.assertIn("dangling ADDENDUM-FOR", err)
        _, other = self.orig(SG)
        self.addendum(rel, FOR=other)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("not a record in the same bench", err)

    def test_unresolved_original_stays_open_and_item9_stays_unmet(self):
        p, rel = self.orig()
        self.addendum(rel, TOOL="")
        self.set_tier("met")
        self.assertEqual(self.run_main()[0], 1)

    def test_premature_item9_evidence_with_partial_resolution_fails(self):
        p, rel = self.orig()
        self.addendum(rel)
        self.man.write_text(json.dumps({"evidence": {"9.analog": {"file": "x"}}}))
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("cites item 9", err)

    def test_addendum_for_passing_record_fails(self):
        p, rel = self.orig()
        new = self.new_record(GOOD)
        self.addendum(new.relative_to(self.sim).as_posix())
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("no provenance defect", err)

    def test_duplicate_addenda_fail(self):
        p, rel = self.orig()
        self.addendum(rel)
        self.addendum(rel, name="ADDENDUM-002-y.md")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("more than one addendum", err)

    def rerun(self, rel, body=None, name="RECORD-098-rerun.md"):
        body = body or f"Supersedes {Path(rel).name}.\n{GOOD}"
        return self.new_record(body, name=name).relative_to(self.sim).as_posix()

    def test_superseding_rerun_resolves(self):
        p, rel = self.orig()
        rr = self.rerun(rel)
        self.addendum(rel, "superseded", RERUN=rr)
        rc, err = self.run_main()
        self.assertEqual(rc, 0, err)

    def test_superseded_must_not_assert_old_environment(self):
        p, rel = self.orig()
        rr = self.rerun(rel)
        self.addendum(rel, "superseded", RERUN=rr, TOOL="ngspice-46")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("does not prove the old environment", err)

    def test_unrelated_rerun_fails(self):
        p, rel = self.orig()
        rr = self.rerun(rel, body=GOOD)
        self.addendum(rel, "superseded", RERUN=rr)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("unrelated", err)

    def test_rerun_dangling_cross_bench_self_fail(self):
        p, rel = self.orig()
        self.addendum(rel, "superseded", RERUN=f"{SLUG}/records/RECORD-777-x.md")
        self.assertIn("dangling ADDENDUM-RERUN", self.run_main()[1])
        _, other = self.orig(SG)
        self.addendum(rel, "superseded", RERUN=other)
        self.assertIn("same bench", self.run_main()[1])
        self.addendum(rel, "superseded", RERUN=rel)
        self.assertIn("supersede itself", self.run_main()[1])

    def test_rerun_with_bad_provenance_fails(self):
        p, rel = self.orig()
        rr = self.rerun(rel, body=f"Supersedes {Path(rel).name}.\n{BAD}")
        self.addendum(rel, "superseded", RERUN=rr)
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("is itself unresolved", err)

    def test_cyclic_supersession_fails(self):
        p, rel = self.orig()
        a = self.new_record(f"x {Path(rel).name}\n{BAD}", name="RECORD-097-a.md")
        ra = a.relative_to(self.sim).as_posix()
        with p.open("a") as f:  # temp copy only: make the back-reference resolvable
            f.write("\nsee RECORD-097-a.md\n")
        # original -> a -> original
        self.addendum(rel, "superseded", RERUN=ra)
        self.addendum(ra, "superseded", RERUN=rel, name="ADDENDUM-002-y.md")
        rc, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("cyclic", err)

    def test_sg13g2_tree_recovery(self):
        p, rel = self.orig(SG)
        self.addendum(rel, PDK=None)
        a = p.parent / "ADDENDUM-001-x.md"
        a.write_text(a.read_text() + f"ADDENDUM-PDK: ihp-sg13g2 {REV2}\n")
        self.assertEqual(self.run_main()[0], 0)


def tree_for(rel):
    return chk.tree_of(rel.split("/")[0])


if __name__ == "__main__":
    unittest.main()
