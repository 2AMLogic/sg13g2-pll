#!/usr/bin/env python3
"""Self-test for run-pex.sh's PEX_BLOCKS/PEX_SNAP_SUBDIR guard (issue #438).

Run:  python3 test_run_pex_guard.py      (stdlib only, offline; exit 0 = pass)

`PEX_BLOCKS` without `PEX_SNAP_SUBDIR` is a *subset in-place* refresh: the
roll-up writer in run-pex.sh replaces the committed top-level
netlist-snapshots/provenance.json with only the named blocks -- silent
append-only evidence loss. The script must hard-fail that unpaired
combination BEFORE the PDK_ROOT requirement, so every case here runs with a
scrubbed environment: no PDK, no GDS, no klt.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "run-pex.sh")
SNAP_DIR = os.path.normpath(os.path.join(HERE, "..", "netlist-snapshots"))

GUARD_TEXT = "PEX_BLOCKS requires PEX_SNAP_SUBDIR"


def scrub_env(**extra):
    """os.environ minus PDK_ROOT and every PEX_* variable, plus `extra`."""
    env = {k: v for k, v in os.environ.items()
           if k != "PDK_ROOT" and not k.startswith("PEX_")}
    env.update(extra)
    return env


def run_script(env, script=SCRIPT):
    return subprocess.run(["bash", script], env=env, capture_output=True,
                          text=True)


def snap_state():
    """{relpath: sha256} of every file under netlist-snapshots/, recursive."""
    state = {}
    for root, _dirs, files in os.walk(SNAP_DIR):
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, SNAP_DIR)
            with open(path, "rb") as fh:
                state[rel] = hashlib.sha256(fh.read()).hexdigest()
    return state


def test_unpaired_combination_hard_fails_writing_nothing():
    """(a) PEX_BLOCKS alone: exit 1, FATAL naming both variables, no writes."""
    before = snap_state()
    r = run_script(scrub_env(PEX_BLOCKS="lock_detector"))
    assert r.returncode == 1, (r.returncode, r.stderr)
    assert "FATAL:" in r.stderr, r.stderr
    assert GUARD_TEXT in r.stderr, r.stderr
    assert "PEX_BLOCKS" in r.stderr and "PEX_SNAP_SUBDIR" in r.stderr, r.stderr
    assert snap_state() == before, "the failed run wrote under netlist-snapshots/"


def test_empty_pex_snap_subdir_counts_as_unset():
    """Edge: PEX_SNAP_SUBDIR="" is unset for the guard, matching the -n test."""
    before = snap_state()
    r = run_script(scrub_env(PEX_BLOCKS="lock_detector", PEX_SNAP_SUBDIR=""))
    assert r.returncode == 1, (r.returncode, r.stderr)
    assert GUARD_TEXT in r.stderr, r.stderr
    assert snap_state() == before, "the failed run wrote under netlist-snapshots/"


def test_paired_combination_passes_the_guard():
    """(b) Both variables set: the guard must NOT fire. With no PDK_ROOT the
    run fails at the pre-existing requirement instead -- and because that
    check sits before `mkdir -p "$SNAP"`, no subdirectory is left behind."""
    subdir = os.path.join(SNAP_DIR, "test-guard-probe")
    r = run_script(scrub_env(PEX_BLOCKS="lock_detector",
                             PEX_SNAP_SUBDIR="test-guard-probe"))
    assert r.returncode != 0, "expected the PDK_ROOT requirement to fail"
    assert GUARD_TEXT not in r.stderr, r.stderr
    assert "PDK_ROOT" in r.stderr, r.stderr
    assert not os.path.exists(subdir), "run created a snapshot subdirectory"


def test_empty_pex_blocks_counts_as_unset():
    """Edge: PEX_BLOCKS="" is unset -- the full in-place-refresh path, which
    without PDK_ROOT fails at the requirement, not at the guard."""
    r = run_script(scrub_env(PEX_BLOCKS=""))
    assert r.returncode != 0, "expected the PDK_ROOT requirement to fail"
    assert GUARD_TEXT not in r.stderr, r.stderr
    assert "PDK_ROOT" in r.stderr, r.stderr


def test_block_name_validation_still_reachable():
    """(c) PEX_BLOCKS naming a non-routed block still hits the pre-existing
    name validation. That check sits after PDK_ROOT and after
    `mkdir -p "$SNAP"`, so it runs against a copy of the extraction tree
    and leaves no stray netlist-snapshots/x/ in the real tree."""
    tmp = tempfile.mkdtemp(prefix="run-pex-guard-test-")
    try:
        copied = os.path.join(tmp, "record")
        shutil.copytree(HERE, copied)
        r = run_script(scrub_env(
            PDK_ROOT=os.path.join(tmp, "unused-pdk"),
            PEX_LAYOUT_RECORD="test-guard-dummy",
            PEX_SNAP_SUBDIR="x",
            PEX_BLOCKS="not_a_block",
        ), script=os.path.join(copied, "run-pex.sh"))
        assert r.returncode == 1, (r.returncode, r.stderr)
        assert GUARD_TEXT not in r.stderr, r.stderr
        assert "FATAL:" in r.stderr, r.stderr
        assert "does not route" in r.stderr, r.stderr
        assert "not_a_block" in r.stderr, r.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_unpaired_combination_hard_fails_writing_nothing()
    test_empty_pex_snap_subdir_counts_as_unset()
    test_paired_combination_passes_the_guard()
    test_empty_pex_blocks_counts_as_unset()
    test_block_name_validation_still_reachable()
    print("test_run_pex_guard: all passed")
