#!/usr/bin/env python3
"""Check that item-10's `checks` inventory covers every gate signoff.yml runs.

Stdlib only, offline, no klt. `manifests/inventories/item-10.json` claims to
inventory "everything in signoff.yml except the base-ref append-only check",
and `klt signoff --attest 10` executes exactly what that `checks` list names.
Nothing used to compare the two: a `python3` gate could be added to
`.github/workflows/signoff.yml`, the item-10 envelope dutifully re-attested
(it hashes the workflow's raw bytes), and the attestation still never run it.
Three gates drifted in that way before this gate existed (issue #395).

The comparison is **one-directional** on purpose: it fails when `signoff.yml`
invokes a gate the inventory omits, and stays silent when the inventory lists
a gate the workflow does not (yet) run. An extra `checks` entry is strictly
more verification -- `klt signoff --attest 10` *executes* it -- so the
inventory may legitimately lead the workflow across a merge interval, and
flagging that would redden `main` for nothing.

Invocations are compared argument-aware, not as a set of paths:
`characterization/check_records.py` is invoked twice in signoff.yml with
different arguments, and a path-set comparison cannot see that divergence.
Interpreter flags (`-B`) are normalized away, so the inventory's
`["python3", "-B", "x.py"]` matches the workflow's bare `python3 x.py`.

Usage: check_signoff_inventory_parity.py [--root DIR] [--workflow F] [--inventory F]
"""
import argparse
import json
import re
import shlex
import sys
from pathlib import Path

WORKFLOW = ".github/workflows/signoff.yml"
INVENTORY = "manifests/inventories/item-10.json"

# Invocations in signoff.yml that deliberately stay out of the inventory.
#
# `flag` is what makes the invocation un-attestable, so the entry keys on the
# flag rather than on its (shell-expanded) value. Each entry MUST still match
# something in signoff.yml: an exclusion that no longer applies is an error
# here, not a silent skip, because it would otherwise hide the gate it names
# forever after the workflow stopped running it.
EXCLUSIONS = (
    {
        "path": "characterization/check_records.py",
        "flag": "--base",
        "reason": "append-only enforcement needs a PR base ref (origin/$BASE_REF); "
                  "there is no base to diff against at attest time. signoff.yml "
                  "runs it on pull requests. This is the one exclusion item-10's "
                  "own description claims.",
    },
)

# `python3` as a whole word: not `python3.12`, not `/usr/bin/python3` (which
# this workflow never uses), not the `python -m venv` that builds the klt venv.
PYTHON3_RE = re.compile(r"(?<![\w./-])python3(?![\w.-])")
# `<<EOF`, `<<'EOF'`, `<<-"EOF"` -- the redirect is stripped before splitting so
# the heredoc at signoff.yml's byte-compare step does not read as an argument.
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
# Tokens that end one command within a `run:` block.
OPERATORS = {"&&", "||", "|", ";", "&", ">", ">>", "<", "2>", "2>&1", "|&"}
# Interpreter flags that take the next token and mean "no script file follows".
NO_SCRIPT_FLAGS = {"-m", "-c", "-X", "-W", "--check-hash-based-pycs"}


def normalize(tokens):
    """argv tokens *after* the `python3` word -> (script, args) or None.

    None means the invocation runs no gate file: a `-m module`, a `-c snippet`,
    a bare REPL, or the `python3 - <<'PY'` heredoc (whose "path" is `-`).
    """
    i = 0
    while i < len(tokens) and tokens[i].startswith("-") and tokens[i] != "-":
        if tokens[i] in NO_SCRIPT_FLAGS:
            return None
        i += 1
    if i >= len(tokens):
        return None
    script = tokens[i]
    if not script.endswith(".py"):
        return None
    return (script, tuple(tokens[i + 1:]))


def command_tokens(text):
    """shlex-split a shell fragment, stopping at the first operator token."""
    text = HEREDOC_RE.sub(" ", text).rstrip()
    while text.endswith("\\"):  # `run:` line continuations
        text = text[:-1].rstrip()
    try:
        tokens = shlex.split(text)
    except ValueError:  # unbalanced quotes across lines -- degrade, don't crash
        tokens = text.split()
    out = []
    for tok in tokens:
        if tok in OPERATORS or tok.startswith("#"):
            break
        out.append(tok)
    return out


def workflow_invocations(text):
    """{(script, args): [1-based line numbers]} for every gate signoff.yml runs.

    Skips `#` comment lines and the bodies of heredocs, so commented-out gates
    and embedded Python are not mistaken for invocations.
    """
    found = {}
    delimiter = None
    for lineno, line in enumerate(text.splitlines(), 1):
        if delimiter is not None:
            if line.strip() == delimiter:
                delimiter = None
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        heredoc = HEREDOC_RE.search(line)
        for match in PYTHON3_RE.finditer(line):
            inv = normalize(command_tokens(line[match.end():]))
            if inv is not None:
                found.setdefault(inv, []).append(lineno)
        if heredoc:
            delimiter = heredoc.group(2)
    return found


def inventory_invocations(doc):
    """{(script, args): [check names]} for every `checks` entry in the inventory."""
    found = {}
    for entry in doc.get("checks", []):
        argv = entry.get("argv") if isinstance(entry, dict) else None
        if not isinstance(argv, list) or not argv:
            continue
        argv = [str(a) for a in argv]
        inv = normalize(argv[1:] if PYTHON3_RE.fullmatch(argv[0]) else argv)
        if inv is not None:
            found.setdefault(inv, []).append(entry.get("name") or "<unnamed>")
    return found


def fmt(inv):
    return " ".join((inv[0],) + inv[1])


def check(root=".", workflow=None, inventory=None):
    root = Path(root)
    workflow = Path(workflow) if workflow else root / WORKFLOW
    inventory = Path(inventory) if inventory else root / INVENTORY

    problems = []
    try:
        wf_text = workflow.read_text()
    except OSError as exc:
        return [f"{workflow}: cannot read the workflow ({exc})"], 0
    try:
        doc = json.loads(inventory.read_text())
    except (OSError, ValueError) as exc:
        return [f"{inventory}: cannot read the inventory ({exc})"], 0

    in_workflow = workflow_invocations(wf_text)
    in_inventory = inventory_invocations(doc)

    excluded = set()
    for rule in EXCLUSIONS:
        matched = [i for i in in_workflow if i[0] == rule["path"] and rule["flag"] in i[1]]
        if not matched:
            problems.append(
                f"stale exclusion: nothing in {workflow.name} invokes "
                f"{rule['path']} with {rule['flag']} any more. Remove the "
                f"EXCLUSIONS entry in {Path(__file__).name} (it would hide a "
                f"future re-addition of that gate), or restore the invocation."
            )
        excluded.update(matched)

    for inv in sorted(set(in_workflow) - set(in_inventory) - excluded):
        lines = ", ".join(str(n) for n in in_workflow[inv])
        problems.append(
            f"{workflow.name} runs `python3 {fmt(inv)}` (line {lines}) but "
            f"{inventory.name} does not inventory it: add a `checks` entry "
            f'{{"name": "<kebab-case>", "argv": ["python3", "-B", '
            f'"{inv[0]}"{"".join(f", {a!r}" for a in inv[1])}]}} and re-attest '
            f"the envelope, or add an EXCLUSIONS entry here with a reason."
        )

    return problems, len(in_workflow)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--workflow", default=None)
    ap.add_argument("--inventory", default=None)
    a = ap.parse_args(argv)
    problems, n = check(a.root, a.workflow, a.inventory)
    for p in problems:
        print("FAIL:", p)
    if problems:
        print(f"signoff/inventory parity: FAIL ({len(problems)} problem(s))")
        return 1
    print(f"signoff/inventory parity: ok ({n} gate invocation(s) in "
          f"{Path(WORKFLOW).name}, {len(EXCLUSIONS)} documented exclusion(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
