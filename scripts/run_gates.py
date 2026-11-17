#!/usr/bin/env python3
"""Run the repo's tool-free stdlib gates, derived from item-10.json (#393).

Stdlib only, offline, no klt. `package.json` used to hand-enumerate every
stdlib gate in two `&&` chains (`test`, `check:ci`) that nothing reconciled
against `.github/workflows/signoff.yml` -- add a 14th gate to the workflow and
the local command quietly stopped mirroring CI. This runner deletes that
second enumeration: the gate list is *derived* from
`manifests/inventories/item-10.json`'s `checks[].argv`, the attested claim
about which gates exist, which `scripts/check_signoff_inventory_parity.py`
(#395) already guards against workflow drift:

    signoff.yml --guarded by #393's predecessor (#399)--> item-10.json
                --derived by construction-->            this runner

A gate added to signoff.yml must be inventoried or the parity guard fails CI;
once inventoried it appears in `pnpm test` / `pnpm run check:ci` here
automatically. No new parser: each `argv` is taken verbatim as a token list
(the repo keeps exactly one python3-invocation-text parser, the parity
checker), and the only classification is `--tests`, on the gate file's
basename.

item-10.json scopes `checks` to signoff.yml's gates, so three real gates --
plus this runner's own unit test -- are appended here as a literal,
reason-bearing tail instead:

- `manifests/check_netlist_stamp.py` -- CI reaches it only through
  `klt signoff --attest 1`, never as a direct `python3` line, so the parity
  guard does not require it in the inventory.
- `scripts/check_artifact_manifests.py` and
  `scripts/test_check_artifact_manifests.py` -- they live in
  `.github/workflows/artifact-manifests.yml`, not signoff.yml.
- `scripts/test_run_gates.py` -- this runner's own unit test, wired into
  artifact-manifests.yml by #393. The tail is unguarded by construction;
  it is small, static, and each entry carries its reason.

Semantics: gates run in order, tests before checks (mirroring the old
`check:ci` = `pnpm run test && <checks>` shape, stable within each group),
each gate's inventory name is printed as it starts, the run stops at the
first failure and exits with that command's exit code. `--tests` selects the
entries whose gate file's basename starts with `test_` -- exactly the old
`test` chain. A malformed or missing inventory, a non-`python3` entry, or a
zero-gate resolution is a loud error (exit 2), never a silent pass: running
zero gates would look like every local gate passing.

The inventory is opened read-only, always; this runner never writes
`item-10.json` or its envelope.

Usage:
    python3 scripts/run_gates.py           # everything (the old check:ci)
    python3 scripts/run_gates.py --tests   # test_*.py gates (the old test)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY = REPO_ROOT / "manifests" / "inventories" / "item-10.json"

# Gates check:ci runs that item-10.json deliberately does not inventory (its
# `description` scopes `checks` to signoff.yml's gates only). Literal table,
# each with its reason; see the module docstring.
TAIL = (
    {
        "name": "netlist-stamp",
        "argv": ["python3", "-B", "manifests/check_netlist_stamp.py"],
        "reason": "CI reaches this gate only through `klt signoff --attest 1` "
                  "on item-1, never as a direct python3 line in signoff.yml, "
                  "so the inventory-parity guard does not require it.",
    },
    {
        "name": "artifact-manifests",
        "argv": ["python3", "-B", "scripts/check_artifact_manifests.py"],
        "reason": "Lives in .github/workflows/artifact-manifests.yml; "
                  "item-10's checks scope is signoff.yml's gates only.",
    },
    {
        "name": "artifact-manifests-unit-tests",
        "argv": ["python3", "-B", "scripts/test_check_artifact_manifests.py"],
        "reason": "Same scope reason as its check: it belongs to "
                  "artifact-manifests.yml, which item-10 does not inventory.",
    },
    {
        "name": "stdlib-gates-runner-unit-tests",
        "argv": ["python3", "-B", "scripts/test_run_gates.py"],
        "reason": "This runner's own unit test, added to "
                  "artifact-manifests.yml by issue #393; item-10's checks "
                  "scope is signoff.yml only.",
    },
)


def fail(message):
    print(f"run_gates: {message}", file=sys.stderr, flush=True)
    raise SystemExit(2)


def load_inventory(path=INVENTORY):
    """Read the attested inventory, read-only; fail loudly on anything odd."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read inventory {path}: {exc}")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"inventory {path} is not valid JSON: {exc}")
    checks = doc.get("checks") if isinstance(doc, dict) else None
    if not isinstance(checks, list):
        fail(f"inventory {path} has no 'checks' list")
    return checks


# Interpreter flags, by what follows the flag (its arity):
# - NO_SCRIPT_FLAGS take one argument that is not a script file, and nothing
#   after it is either, so the invocation runs no script file at all:
#   -m: 1 arg, the module name; -c: 1 arg, the command string.
# - VALUE_FLAGS take exactly one value token of their own, after which the
#   gate file and its arguments may follow; script_token skips that value
#   and keeps scanning: -X: 1 (e.g. utf8); -W: 1 (e.g. ignore);
#   --check-hash-based-pycs: 1 (default/always/never).
# Any other flag consumes nothing (e.g. -B: 0 args); the first non-flag
# token after the interpreter is the script.
NO_SCRIPT_FLAGS = {"-m", "-c"}
VALUE_FLAGS = {"-X", "-W", "--check-hash-based-pycs"}


def script_token(argv):
    """The gate file path in an argv: first non-flag token after the
    interpreter, or None for invocations that run no file (a `-m module`, a
    `-c snippet`, a bare REPL). argv lists, never invocation text."""
    i = 1
    while i < len(argv):
        token = argv[i]
        if token in NO_SCRIPT_FLAGS:
            return None
        if token in VALUE_FLAGS:
            i += 2  # skip the flag's own value; the script may follow
            continue
        if not token.startswith("-"):
            return token
        i += 1
    return None


def is_test_entry(argv):
    """`--tests` selection: the gate file's basename starts with `test_`."""
    script = script_token(argv)
    return script is not None and Path(script).name.startswith("test_")


def to_entry(check, index):
    """Validate one `checks[]` entry -> (name, argv). The inventory is
    attested to be exactly the python3 stdlib gates, so an entry whose argv[0]
    is not `python3` fails the run rather than being skipped: the attestation
    changed shape and the runner must not guess."""
    where = f"checks[{index}]"
    if not isinstance(check, dict):
        fail(f"{where} is not an object")
    name = check.get("name")
    if not isinstance(name, str) or not name:
        fail(f"{where} has no name")
    argv = check.get("argv")
    if not isinstance(argv, list) or not argv:
        fail(f"{where} ({name}) has no argv list")
    if not all(isinstance(token, str) for token in argv):
        fail(f"{where} ({name}) has a non-string argv token")
    if argv[0] != "python3":
        fail(f"{where} ({name}) starts with {argv[0]!r}, not 'python3' -- "
             "the inventory is attested to contain only python3 gates")
    if len(argv) < 2:
        fail(f"{where} ({name}) runs no command")
    return name, list(argv)


def resolve_commands(checks, tests_only=False, tail=True):
    """The ordered (name, argv) gate list: inventory + tail, validated, then
    tests before checks (stable). Empty resolution is an error."""
    entries = [to_entry(check, i) for i, check in enumerate(checks)]
    if tail:
        entries.extend((t["name"], list(t["argv"])) for t in TAIL)
    selected = [(name, argv) for name, argv in entries
                if is_test_entry(argv) or not tests_only]
    if not selected:
        mode = "--tests" if tests_only else "the inventory"
        fail(f"{mode} resolved zero gates; refusing to run nothing")
    tests = [(name, argv) for name, argv in selected if is_test_entry(argv)]
    checks_only = [(name, argv) for name, argv in selected
                   if not is_test_entry(argv)]
    return tests + checks_only


def run_commands(commands, cwd=REPO_ROOT):
    """Run each gate in order from `cwd`; stop at the first failure and
    return its exit code (0 when every gate passes)."""
    for name, argv in commands:
        print(f"[run_gates] {name}: {' '.join(argv)}", flush=True)
        returncode = subprocess.run(argv, cwd=cwd).returncode
        if returncode != 0:
            print(f"[run_gates] {name} failed (exit {returncode}); "
                  f"stopping.", file=sys.stderr, flush=True)
            return returncode
    print(f"[run_gates] all {len(commands)} gates passed.", flush=True)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run the stdlib gate set derived from "
                    "manifests/inventories/item-10.json.")
    parser.add_argument("--tests", action="store_true",
                        help="run only the gates whose file is named test_*.py")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    commands = resolve_commands(load_inventory(), tests_only=args.tests)
    return run_commands(commands)


if __name__ == "__main__":
    sys.exit(main())
