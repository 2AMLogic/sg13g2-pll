"""Unit tests for the `klt pdk find` argv construction in both record
renderers (issue #124).

`--pdk-root` used to be spliced at index 2 -- before the `find`
subcommand -- producing `klt pdk --pdk-root <root> find ...`, which
argparse rejects and the renderers silently swallow into `{}` (rendering
"not resolved (plan-only run)" for a full run). These tests capture the
argv actually handed to `subprocess.run` (no `klt` install and no PDK
needed) and assert `--pdk-root` lands after `find`, and that the
no-`pdk-root` branch leaves the command untouched.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parents[1] / "bin"


def _load_renderer(filename: str):
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_"), BIN_DIR / filename
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def captured_cmds(monkeypatch):
    cmds: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        cmds.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return cmds


def _pdk_find_cmd(cmds) -> list[str]:
    """The `klt pdk find` invocation among the captured commands.

    Matches by the `find` token so it still locates the (malformed)
    command the pre-fix code builds -- the full-equality assertions
    below then fail on that shape for exactly the right reason.
    """
    (found,) = [c for c in cmds if "find" in c]
    return found


def _write_plan(tmp_path: Path, plan: dict) -> Path:
    record = tmp_path / "rec"
    record.mkdir()
    (record / "plan.json").write_text(json.dumps(plan))
    return record


# --- render-pll-cmos5l-record.py ---------------------------------------------


def test_cmos5l_pdk_root_spliced_after_find(captured_cmds, tmp_path):
    mod = _load_renderer("render-pll-cmos5l-record.py")
    record = _write_plan(tmp_path, {"blocks": [{"device_count": 0}]})
    rc = mod.main(
        [
            "render-pll-cmos5l-record.py",
            str(record),
            "klt",
            "ihp-sg13cmos5l",
            "sg13cmos5l",
            "/pdk/root",
        ]
    )
    assert rc == 0
    assert _pdk_find_cmd(captured_cmds) == [
        "klt",
        "pdk",
        "find",
        "--pdk-root",
        "/pdk/root",
        "--pdk",
        "ihp-sg13cmos5l",
        "--format",
        "json",
    ]


def test_cmos5l_without_pdk_root_command_unchanged(captured_cmds, tmp_path):
    mod = _load_renderer("render-pll-cmos5l-record.py")
    record = _write_plan(tmp_path, {"blocks": [{"device_count": 0}]})
    rc = mod.main(
        [
            "render-pll-cmos5l-record.py",
            str(record),
            "klt",
            "ihp-sg13cmos5l",
            "sg13cmos5l",
        ]
    )
    assert rc == 0
    assert _pdk_find_cmd(captured_cmds) == [
        "klt",
        "pdk",
        "find",
        "--pdk",
        "ihp-sg13cmos5l",
        "--format",
        "json",
    ]


# --- render-pll-record.py ----------------------------------------------------


def test_pll_pdk_root_spliced_after_find(captured_cmds, tmp_path):
    mod = _load_renderer("render-pll-record.py")
    record = _write_plan(tmp_path, {"blocks": [{"groups": []}], "device_flavor": "x"})
    rc = mod.main(
        ["render-pll-record.py", str(record), "klt", "ihp-sg13g2", "/pdk/root"]
    )
    assert rc == 0
    assert _pdk_find_cmd(captured_cmds) == [
        "klt",
        "pdk",
        "find",
        "--pdk-root",
        "/pdk/root",
        "--pdk",
        "ihp-sg13g2",
        "--format",
        "json",
    ]


def test_pll_without_pdk_root_command_unchanged(captured_cmds, tmp_path):
    mod = _load_renderer("render-pll-record.py")
    record = _write_plan(tmp_path, {"blocks": [{"groups": []}], "device_flavor": "x"})
    rc = mod.main(["render-pll-record.py", str(record), "klt", "ihp-sg13g2"])
    assert rc == 0
    assert _pdk_find_cmd(captured_cmds) == [
        "klt",
        "pdk",
        "find",
        "--pdk",
        "ihp-sg13g2",
        "--format",
        "json",
    ]
