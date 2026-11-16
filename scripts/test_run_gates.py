"""Tests for run_gates.py (issue #393).

Stdlib `unittest`, offline, no klt. `run_gates.py` derives the local gate list
from `manifests/inventories/item-10.json`'s `checks[].argv` plus a small
documented tail, replacing the `&&` chains package.json used to hand-enumerate.
These tests pin the resolved lists against the committed inventory via golden
`EXPECTED_*` pins (the pre-rewrite behavior-preservation proof was one-shot and
was retired with the first post-rewrite gate addition; see #462), and pin the
execution semantics (tests first, stop at first failure, exit code out).

Run from the repo root: python3 scripts/test_run_gates.py
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import run_gates as rg  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

RUNNER_TEST = "scripts/test_run_gates.py"


def g(path, *args):
    """The argv shape every inventory entry uses: python3 -B <script> [args]."""
    return ["python3", "-B", path, *args]


def entry(name, script, *args):
    """One fixture `checks[]` entry in the inventory's shape."""
    return {"name": name, "argv": g(script, *args)}


# The exact resolved lists the runner must produce on the committed tree:
# the inventory's gates plus the one gate this issue adds (the runner's own
# unit test, mandated into the tail by the issue). Tests first, then checks;
# within each group the inventory's file order is preserved and the tail
# entries come last. These are golden pins, not a second enumeration: when a
# gate is added to item-10.json, extend them in inventory order.
EXPECTED_TEST_PATHS = (
    "characterization/test_check_records.py",
    "characterization/test_gen_summary.py",
    "manifests/test_check_lvs_coverage.py",
    "manifests/test_check_drc_coverage.py",
    "manifests/test_check_erc_coverage.py",
    "manifests/test_check_pex_coverage.py",
    "manifests/test_check_testbench_coverage.py",
    "manifests/test_check_spec_citations.py",
    "manifests/test_check_netlist_stamp.py",
    "design/test_check_pfd_reset_parity.py",
    "sim/sg13cmos5l-closed-loop-lock/testbench/test_cpdiag_metrics.py",
    "sim/sg13cmos5l-closed-loop-lock/testbench/test_mismatch_gain_metrics.py",
    "sim/sg13cmos5l-postlayout-pex-pvt/extraction/test_run_pex_guard.py",
    "scripts/test_check_signoff_inventory_parity.py",
    "scripts/test_check_artifact_manifests.py",
    RUNNER_TEST,
)
EXPECTED_FULL = (
    ("records-unit-tests", g("characterization/test_check_records.py")),
    ("summary-unit-tests", g("characterization/test_gen_summary.py")),
    ("lvs-coverage-unit-tests", g("manifests/test_check_lvs_coverage.py")),
    ("drc-coverage-unit-tests", g("manifests/test_check_drc_coverage.py")),
    ("erc-coverage-unit-tests", g("manifests/test_check_erc_coverage.py")),
    ("pex-coverage-unit-tests", g("manifests/test_check_pex_coverage.py")),
    ("testbench-coverage-unit-tests", g("manifests/test_check_testbench_coverage.py")),
    ("spec-citations-unit-tests", g("manifests/test_check_spec_citations.py")),
    ("netlist-stamp-unit-tests", g("manifests/test_check_netlist_stamp.py")),
    ("pfd-reset-parity-unit-tests", g("design/test_check_pfd_reset_parity.py")),
    ("cpdiag-metrics-unit-tests",
     g("sim/sg13cmos5l-closed-loop-lock/testbench/test_cpdiag_metrics.py")),
    ("mismatch-gain-metrics-unit-tests",
     g("sim/sg13cmos5l-closed-loop-lock/testbench/test_mismatch_gain_metrics.py")),
    ("run-pex-guard-self-test",
     g("sim/sg13cmos5l-postlayout-pex-pvt/extraction/test_run_pex_guard.py")),
    ("signoff-inventory-parity-unit-tests",
     g("scripts/test_check_signoff_inventory_parity.py")),
    ("artifact-manifests-unit-tests", g("scripts/test_check_artifact_manifests.py")),
    ("stdlib-gates-runner-unit-tests", g(RUNNER_TEST)),
    ("records-format", g("characterization/check_records.py")),
    ("summary-fresh", g("characterization/gen_summary.py", "--check")),
    ("lvs-coverage", g("manifests/check_lvs_coverage.py")),
    ("drc-coverage", g("manifests/check_drc_coverage.py")),
    ("erc-coverage", g("manifests/check_erc_coverage.py")),
    ("pex-coverage", g("manifests/check_pex_coverage.py")),
    ("testbench-coverage", g("manifests/check_testbench_coverage.py")),
    ("spec-citations", g("manifests/check_spec_citations.py")),
    ("pfd-reset-parity", g("design/check_pfd_reset_parity.py")),
    ("signoff-inventory-parity", g("scripts/check_signoff_inventory_parity.py")),
    ("netlist-stamp", g("manifests/check_netlist_stamp.py")),
    ("artifact-manifests", g("scripts/check_artifact_manifests.py")),
)


class Pin(unittest.TestCase):
    """The committed tree resolves to exactly the pinned gate list."""

    def setUp(self):
        self.checks = rg.load_inventory()

    def test_full_resolution_matches_expected_list(self):
        resolved = rg.resolve_commands(self.checks, tests_only=False)
        self.assertEqual(
            [(name, argv) for name, argv in resolved], list(EXPECTED_FULL))

    def test_tests_selection_matches_expected_list(self):
        resolved = rg.resolve_commands(self.checks, tests_only=True)
        self.assertEqual(
            [rg.script_token(argv) for _, argv in resolved],
            list(EXPECTED_TEST_PATHS))

    def test_tests_before_checks(self):
        resolved = rg.resolve_commands(self.checks, tests_only=False)
        seen_check = False
        for _, argv in resolved:
            if rg.is_test_entry(argv):
                self.assertFalse(seen_check, "a test entry followed a check entry")
            else:
                seen_check = True


class Derivation(unittest.TestCase):
    """The gate list comes from the inventory, not from a second hardcoded one."""

    def test_fabricated_entries_are_derived(self):
        checks = [
            entry("pre-existing-check", "a/check.py"),
            entry("fresh-unit-test", "a/test_new_thing.py", "--fast"),
            entry("fresh-check", "a/new_check.py", "--mode", "x"),
        ]
        resolved = rg.resolve_commands(checks, tests_only=False, tail=False)
        self.assertEqual(resolved, [
            ("fresh-unit-test", g("a/test_new_thing.py", "--fast")),
            ("pre-existing-check", g("a/check.py")),
            ("fresh-check", g("a/new_check.py", "--mode", "x")),
        ])
        tests = rg.resolve_commands(checks, tests_only=True, tail=False)
        self.assertEqual(tests, [("fresh-unit-test", g("a/test_new_thing.py", "--fast"))])

    def test_arguments_pass_through_intact(self):
        resolved = rg.resolve_commands(
            [entry("with-args", "a/gen.py", "--check", "--base", "x")],
            tests_only=False, tail=False)
        self.assertEqual(
            resolved, [("with-args", g("a/gen.py", "--check", "--base", "x"))])

    def test_arguments_reach_the_gate_process(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rg.run_commands(
                [("args", ["python3", "-c",
                           "import sys; sys.exit(0 if sys.argv[1:] == ['--check'] else 3)",
                           "--check"])],
                cwd=REPO)
        self.assertEqual(rc, 0)

    def test_tail_is_four_documented_entries(self):
        self.assertEqual(len(rg.TAIL), 4)
        scripts = sorted(rg.script_token(t["argv"]) for t in rg.TAIL)
        self.assertEqual(scripts, sorted([
            "manifests/check_netlist_stamp.py",
            "scripts/check_artifact_manifests.py",
            "scripts/test_check_artifact_manifests.py",
            RUNNER_TEST,
        ]))
        for t in rg.TAIL:
            self.assertTrue(t.get("reason"), f"tail entry {t['name']} has no reason")
            self.assertEqual(t["argv"][0], "python3")

    def test_non_python3_entry_is_rejected_with_stated_rule(self):
        with self.assertRaises(SystemExit) as ctx:
            rg.resolve_commands(
                [{"name": "odd", "argv": ["python3.12", "-B", "a.py"]}],
                tests_only=False, tail=False)
        self.assertEqual(ctx.exception.code, 2)

    def test_dash_c_entry_has_no_script_and_is_not_a_test(self):
        resolved = rg.resolve_commands(
            [{"name": "inline", "argv": ["python3", "-c", "print('x')"]},
             entry("real-test", "a/test_real.py")],
            tests_only=False, tail=False)
        self.assertEqual(resolved, [
            ("real-test", g("a/test_real.py")),
            ("inline", ["python3", "-c", "print('x')"]),
        ])
        # Even a `-c` body that looks like a test file has no script file.
        tests = rg.resolve_commands(
            [{"name": "inline", "argv": ["python3", "-c", "test_fixtures"]},
             entry("real-test", "a/test_real.py")],
            tests_only=True, tail=False)
        self.assertEqual(tests, [("real-test", g("a/test_real.py"))])


class ScriptTokenFlags(unittest.TestCase):
    """script_token against each interpreter flag's arity (#470): -B
    consumes nothing, -m/-c mean no script file follows, and the value
    flags (-X, -W, --check-hash-based-pycs) skip exactly one value token
    of their own and keep scanning for the script."""

    def test_dash_b_consumes_nothing(self):
        self.assertEqual(rg.script_token(["python3", "-B", "a/test_x.py"]),
                         "a/test_x.py")

    def test_dash_m_runs_no_file(self):
        self.assertIsNone(rg.script_token(["python3", "-m", "unittest"]))

    def test_dash_c_runs_no_file(self):
        self.assertIsNone(rg.script_token(["python3", "-c", "print('x')"]))

    def test_dash_x_skips_its_value(self):
        self.assertEqual(
            rg.script_token(["python3", "-X", "utf8", "a/test_x.py"]),
            "a/test_x.py")

    def test_dash_w_skips_its_value(self):
        self.assertEqual(
            rg.script_token(["python3", "-W", "ignore", "a/test_x.py"]),
            "a/test_x.py")

    def test_check_hash_based_pycs_skips_its_value(self):
        self.assertEqual(
            rg.script_token(
                ["python3", "--check-hash-based-pycs", "default",
                 "a/test_x.py"]),
            "a/test_x.py")

    def test_value_flag_as_last_token_finds_no_script(self):
        self.assertIsNone(rg.script_token(["python3", "-X"]))

    def test_flag_value_starting_with_dash_is_skipped(self):
        self.assertEqual(
            rg.script_token(["python3", "-W", "-weird", "a/test_x.py"]),
            "a/test_x.py")


class Execution(unittest.TestCase):
    """Tests first, stop at the first failure, exit code out, gates named."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.dir = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def test_stops_at_first_failure_and_propagates_exit_code(self):
        sentinel = self.dir / "after-failure-ran"
        commands = [
            ("passing", ["python3", "-c", "import sys; sys.exit(0)"]),
            ("failing", ["python3", "-c", "import sys; sys.exit(3)"]),
            ("after", ["python3", "-c", f"open({str(sentinel)!r}, 'w').close()"]),
        ]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rg.run_commands(commands, cwd=self.dir)
        self.assertEqual(rc, 3)
        self.assertFalse(sentinel.exists(), "gates after the failure still ran")
        self.assertIn("passing", out.getvalue())
        self.assertIn("failing", out.getvalue())

    def test_each_gate_name_is_printed(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rg.run_commands(
                [("hello-gate", ["python3", "-c", "pass"])], cwd=self.dir)
        self.assertEqual(rc, 0)
        self.assertIn("hello-gate", out.getvalue())

    def test_all_pass_reports_zero(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rg.run_commands(
                [("a", ["python3", "-c", "pass"]),
                 ("b", ["python3", "-c", "pass"])], cwd=self.dir)
        self.assertEqual(rc, 0)


class InventoryLoading(unittest.TestCase):
    """Read-only, and every malformed shape fails loudly instead of running
    zero gates (the one failure mode that would silently disable the local
    gate set)."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.dir = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def write(self, text):
        path = self.dir / "item-10.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_inventory_fails_loudly(self):
        with self.assertRaises(SystemExit) as ctx:
            rg.load_inventory(self.dir / "absent.json")
        self.assertEqual(ctx.exception.code, 2)

    def test_malformed_json_fails_loudly(self):
        with self.assertRaises(SystemExit) as ctx:
            rg.load_inventory(self.write("{not json"))
        self.assertEqual(ctx.exception.code, 2)

    def test_missing_checks_key_fails_loudly(self):
        with self.assertRaises(SystemExit):
            rg.load_inventory(self.write(json.dumps({"schema_version": 1})))

    def test_checks_not_a_list_fails_loudly(self):
        with self.assertRaises(SystemExit):
            rg.load_inventory(self.write(json.dumps({"checks": {}})))

    def test_bad_entry_shapes_fail_loudly(self):
        bad = [
            [],
            {"name": "x"},
            {"argv": ["python3", "-B", "a.py"]},
            {"name": "", "argv": ["python3", "-B", "a.py"]},
            {"name": "x", "argv": []},
            {"name": "x", "argv": "python3 -B a.py"},
            {"name": "x", "argv": ["python3", "-B", 7]},
            {"name": "x", "argv": ["python3"]},
        ]
        for checks in ([c] for c in bad):
            with self.assertRaises(SystemExit, msg=repr(checks)):
                rg.resolve_commands(checks, tests_only=False, tail=False)

    def test_zero_resolved_gates_is_an_error(self):
        with self.assertRaises(SystemExit):
            rg.resolve_commands([], tests_only=False, tail=False)
        with self.assertRaises(SystemExit):
            rg.resolve_commands([entry("only-check", "a/check.py")],
                                tests_only=True, tail=False)

    def test_inventory_is_never_written(self):
        before = rg.INVENTORY.read_bytes()
        checks = rg.load_inventory()
        rg.resolve_commands(checks, tests_only=False)
        rg.resolve_commands(checks, tests_only=True)
        self.assertEqual(rg.INVENTORY.read_bytes(), before)


class Main(unittest.TestCase):
    def test_main_flags(self):
        parser = rg.build_parser()
        self.assertFalse(parser.parse_args([]).tests)
        self.assertTrue(parser.parse_args(["--tests"]).tests)


if __name__ == "__main__":
    unittest.main()
