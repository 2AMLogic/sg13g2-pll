#!/usr/bin/env python3
"""Self-test for run-pex.sh's PEX_BLOCKS/PEX_SNAP_SUBDIR guards (issues #438, #458).

Run:  python3 test_run_pex_guard.py      (stdlib only, offline; exit 0 = pass)

`PEX_BLOCKS` without `PEX_SNAP_SUBDIR` is a *subset in-place* refresh: the
roll-up writer in run-pex.sh replaces the committed top-level
netlist-snapshots/provenance.json with only the named blocks -- silent
append-only evidence loss. The script must hard-fail that unpaired
combination BEFORE the PDK_ROOT requirement, so every case here runs with a
scrubbed environment: no PDK, no GDS, no klt.

Issue #458 adds a second guard next to it: a non-empty `PEX_SNAP_SUBDIR`
must be a *plain new name* -- no "/", never "." or "..". "." would alias
the committed top-level snapshots (the very target the #438 guard keeps
subset runs away from) and "../.." would write outside the record directory
entirely. That check is unconditional on `PEX_BLOCKS` -- the escape needs
no PEX_BLOCKS -- and equally sits before PDK_ROOT.
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
SUBDIR_GUARD_TEXT = "is not a plain new subdirectory name"


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


def test_rejected_subdir_values_hard_fail_writing_nothing():
    """(d, issue #458) A non-empty PEX_SNAP_SUBDIR must be a plain new name:
    '.', '..', '../..', 'a/b' -- and trailing slash 'x/', which contains
    '/' too -- all exit 1 with a FATAL naming the value, whether or not
    PEX_BLOCKS is also set. "PDK_ROOT" absent from stderr proves the guard
    fires before the PDK_ROOT requirement, and snap_state() unchanged
    proves nothing was written (the guard sits before mkdir -p "$SNAP")."""
    for value in (".", "..", "../..", "a/b", "x/"):
        for blocks in (None, "lock_detector"):
            label = f"PEX_SNAP_SUBDIR={value!r}"
            extra = {"PEX_SNAP_SUBDIR": value}
            if blocks is not None:
                extra["PEX_BLOCKS"] = blocks
                label += f" + PEX_BLOCKS={blocks!r}"
            before = snap_state()
            r = run_script(scrub_env(**extra))
            assert r.returncode == 1, (label, r.returncode, r.stderr)
            assert "FATAL:" in r.stderr, (label, r.stderr)
            assert SUBDIR_GUARD_TEXT in r.stderr, (label, r.stderr)
            assert value in r.stderr, (label, r.stderr)
            assert "PDK_ROOT" not in r.stderr, (label, r.stderr)
            assert snap_state() == before, \
                (label, "the failed run wrote under netlist-snapshots/")


def test_empty_pex_snap_subdir_alone_is_still_in_place_refresh():
    """Edge (issue #458): PEX_SNAP_SUBDIR="" with no PEX_BLOCKS is the full
    in-place refresh -- the new check must ignore it; without PDK_ROOT the
    run fails at the requirement, not at either guard."""
    r = run_script(scrub_env(PEX_SNAP_SUBDIR=""))
    assert r.returncode != 0, "expected the PDK_ROOT requirement to fail"
    assert SUBDIR_GUARD_TEXT not in r.stderr, r.stderr
    assert GUARD_TEXT not in r.stderr, r.stderr
    assert "PDK_ROOT" in r.stderr, r.stderr


def test_plain_name_already_on_disk_still_accepted():
    """Edge (issue #458): 'rerun-157' is a committed subdirectory -- a plain
    name must still pass both guards, since append-only rerun is the
    feature. Without PDK_ROOT the run stops at the requirement, before
    mkdir -p, so the committed tree is untouched."""
    r = run_script(scrub_env(PEX_SNAP_SUBDIR="rerun-157"))
    assert r.returncode != 0, "expected the PDK_ROOT requirement to fail"
    assert SUBDIR_GUARD_TEXT not in r.stderr, r.stderr
    assert GUARD_TEXT not in r.stderr, r.stderr
    assert "PDK_ROOT" in r.stderr, r.stderr


if __name__ == "__main__":
    test_unpaired_combination_hard_fails_writing_nothing()
    test_empty_pex_snap_subdir_counts_as_unset()
    test_paired_combination_passes_the_guard()
    test_empty_pex_blocks_counts_as_unset()
    test_block_name_validation_still_reachable()
    test_rejected_subdir_values_hard_fail_writing_nothing()
    test_empty_pex_snap_subdir_alone_is_still_in_place_refresh()
    test_plain_name_already_on_disk_still_accepted()
    print("test_run_pex_guard: all passed")
