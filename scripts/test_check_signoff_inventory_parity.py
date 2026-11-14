"""Tests for check_signoff_inventory_parity.py (issue #395).

Stdlib `unittest`, offline, no klt. Synthetic workflow/inventory pairs cover
the parsing edges the real signoff.yml contains, plus one end-to-end assertion
that the committed tree is actually in parity.

Run from the repo root: python3 scripts/test_check_signoff_inventory_parity.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_signoff_inventory_parity as chk  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# Every fixture carries the `--base` invocation, so the EXCLUSIONS entry for it
# stays live; a fixture that drops it is asserting the stale-exclusion error.
BASE_STEP = """\
      - name: Records are append-only (pull requests)
        if: github.event_name == 'pull_request'
        run: python3 characterization/check_records.py --base "origin/$BASE_REF"
"""


def workflow(body, base_step=True):
    return "jobs:\n  records:\n    steps:\n" + body + (BASE_STEP if base_step else "")


def step(*commands):
    out = "      - name: A gate\n        run: |\n"
    return out + "".join(f"          {c}\n" for c in commands)


def inventory(*paths, dash_b=True, description="x"):
    checks = []
    for p in paths:
        argv = ["python3"] + (["-B"] if dash_b else [])
        if isinstance(p, tuple):
            argv += [p[0]] + list(p[1:])
            name = Path(p[0]).stem
        else:
            argv += [p]
            name = Path(p).stem
        checks.append({"name": name.replace("_", "-"), "argv": argv})
    return {"schema_version": 1, "kind": "t1-attestation-inventory", "t1_item": 10,
            "description": description, "hygiene": [], "checks": checks}


class Parity(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.dir = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def run_check(self, wf_text, inv_doc):
        wf = self.dir / "signoff.yml"
        inv = self.dir / "item-10.json"
        wf.write_text(wf_text)
        inv.write_text(json.dumps(inv_doc))
        return chk.check(self.dir, wf, inv)[0]

    # --- the core one-directional contract ----------------------------------

    def test_in_sync_passes(self):
        wf = workflow(step("python3 a/gate.py", "python3 a/test_gate.py"))
        self.assertEqual(self.run_check(wf, inventory("a/gate.py", "a/test_gate.py")), [])

    def test_gate_missing_from_inventory_fails_and_names_the_path(self):
        wf = workflow(step("python3 a/gate.py", "python3 a/test_gate.py"))
        problems = self.run_check(wf, inventory("a/gate.py"))
        self.assertEqual(len(problems), 1)
        self.assertIn("a/test_gate.py", problems[0])

    def test_inventory_ahead_of_workflow_passes(self):
        """One-directional: an extra `checks` entry is more verification, not drift.

        This is the PR #394 merge interval -- the inventory may list a gate the
        workflow does not run yet without reddening main.
        """
        wf = workflow(step("python3 a/gate.py"))
        self.assertEqual(self.run_check(wf, inventory("a/gate.py", "a/not_yet.py")), [])

    def test_every_missing_gate_is_reported_not_just_the_first(self):
        wf = workflow(step("python3 a/one.py", "python3 a/two.py", "python3 a/three.py"))
        problems = self.run_check(wf, inventory("a/two.py"))
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("a/one.py" in p for p in problems))
        self.assertTrue(any("a/three.py" in p for p in problems))

    # --- parsing edges present in the real signoff.yml ----------------------

    def test_dash_b_is_normalized_away_in_both_directions(self):
        wf = workflow(step("python3 a/gate.py"))
        self.assertEqual(self.run_check(wf, inventory("a/gate.py", dash_b=True)), [])
        self.assertEqual(self.run_check(wf, inventory("a/gate.py", dash_b=False)), [])
        wf_b = workflow(step("python3 -B a/gate.py"))
        self.assertEqual(self.run_check(wf_b, inventory("a/gate.py", dash_b=False)), [])
        self.assertEqual(self.run_check(wf_b, inventory("a/gate.py", dash_b=True)), [])

    def test_heredoc_is_not_a_gate_named_dash(self):
        wf = workflow(step("python3 - \"$RUNNER_TEMP/fresh.json\" <<'PY'",
                           "import json, sys",
                           "python3 not_a_real_gate.py",  # inside the heredoc body
                           "PY"))
        self.assertEqual(self.run_check(wf, inventory()), [])

    def test_commented_out_gate_is_ignored(self):
        wf = workflow(step("python3 a/gate.py") + "      # python3 a/retired.py\n")
        self.assertEqual(self.run_check(wf, inventory("a/gate.py")), [])

    def test_module_and_interpreter_only_invocations_are_not_gates(self):
        wf = workflow(step("python3 -m venv /tmp/v", "python3 -c 'import sys'", "python3"))
        self.assertEqual(self.run_check(wf, inventory()), [])

    def test_python3_as_a_substring_is_not_matched(self):
        wf = workflow(step("python3.12 a/gate.py", "/opt/python3-old/bin/py a/other.py"))
        self.assertEqual(self.run_check(wf, inventory()), [])

    def test_operator_terminates_the_invocation(self):
        """`python3 a.py && python3 b.py` is two gates, not one with args."""
        wf = workflow(step("python3 a/one.py && python3 a/two.py"))
        self.assertEqual(self.run_check(wf, inventory("a/one.py", "a/two.py")), [])

    # --- argument awareness -------------------------------------------------

    def test_arguments_are_part_of_the_invocation(self):
        """A path-set comparison cannot see this; check_records.py is the real case."""
        wf = workflow(step("python3 a/gen.py --check"))
        problems = self.run_check(wf, inventory("a/gen.py"))
        self.assertEqual(len(problems), 1)
        self.assertIn("--check", problems[0])
        self.assertEqual(self.run_check(wf, inventory(("a/gen.py", "--check"))), [])

    def test_same_path_invoked_twice_with_different_arguments(self):
        wf = workflow(step("python3 a/gate.py", "python3 a/gate.py --extra"))
        problems = self.run_check(wf, inventory("a/gate.py"))
        self.assertEqual(len(problems), 1)
        self.assertIn("--extra", problems[0])

    # --- the exclusion table ------------------------------------------------

    def test_base_ref_invocation_is_excluded_but_the_plain_one_is_not(self):
        wf = workflow("", base_step=True)
        self.assertEqual(self.run_check(wf, inventory("characterization/check_records.py")), [])
        # The exclusion keys on `--base`, so the argument-less invocation of the
        # same path is still required to be inventoried.
        wf_both = workflow(step("python3 characterization/check_records.py"))
        problems = self.run_check(wf_both, inventory())
        self.assertEqual(len(problems), 1)
        self.assertIn("characterization/check_records.py", problems[0])
        self.assertNotIn("--base", problems[0])

    def test_stale_exclusion_is_an_error(self):
        """An exclusion that matches nothing would hide the gate forever."""
        wf = workflow(step("python3 a/gate.py"), base_step=False)
        problems = self.run_check(wf, inventory("a/gate.py"))
        self.assertEqual(len(problems), 1)
        self.assertIn("stale exclusion", problems[0])
        self.assertIn("characterization/check_records.py", problems[0])

    def test_every_exclusion_carries_a_reason(self):
        for rule in chk.EXCLUSIONS:
            self.assertTrue(rule.get("reason", "").strip(), rule)
            self.assertTrue(rule.get("path"), rule)
            self.assertTrue(rule.get("flag"), rule)

    # --- unreadable inputs fail closed --------------------------------------

    def test_missing_workflow_fails(self):
        inv = self.dir / "item-10.json"
        inv.write_text(json.dumps(inventory()))
        problems, _ = chk.check(self.dir, self.dir / "nope.yml", inv)
        self.assertTrue(any("cannot read the workflow" in p for p in problems))

    def test_malformed_inventory_fails(self):
        wf = self.dir / "signoff.yml"
        wf.write_text(workflow(""))
        bad = self.dir / "item-10.json"
        bad.write_text("{not json")
        problems, _ = chk.check(self.dir, wf, bad)
        self.assertTrue(any("cannot read the inventory" in p for p in problems))


class CommittedTree(unittest.TestCase):
    """The gate must hold on the tree it ships in, and must bite when broken."""

    def test_repo_is_in_parity(self):
        problems, n = chk.check(REPO)
        self.assertEqual(problems, [])
        self.assertGreater(n, 0)

    def test_dropping_any_committed_entry_is_caught(self):
        doc = json.loads((REPO / chk.INVENTORY).read_text())
        self.assertTrue(doc["checks"])
        in_workflow = chk.workflow_invocations((REPO / chk.WORKFLOW).read_text())
        covered = 0
        with tempfile.TemporaryDirectory() as td:
            trimmed = Path(td) / "item-10.json"
            for i, dropped in enumerate(doc["checks"]):
                inv = chk.normalize([str(a) for a in dropped["argv"]][1:])
                # An inventory-ahead-of-workflow entry is legitimate and, by the
                # one-directional contract, is NOT meant to be caught.
                if inv is None or inv not in in_workflow:
                    continue
                covered += 1
                short = dict(doc, checks=doc["checks"][:i] + doc["checks"][i + 1:])
                trimmed.write_text(json.dumps(short))
                problems, _ = chk.check(REPO, REPO / chk.WORKFLOW, trimmed)
                self.assertTrue(
                    any(chk.fmt(inv) in p for p in problems),
                    f"dropping {dropped['name']} ({chk.fmt(inv)}) was not caught: {problems}",
                )
        self.assertEqual(covered, len(in_workflow) - len(chk.EXCLUSIONS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
