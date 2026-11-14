"""Golden tests for `render-pll-cmos5l-record.py`'s full-run rendering
(issue #376).

Until #376 the renderer was one 525-line `main()` whose report sections were
reachable only after it had shelled out to `klt` three times, so the ~460
lines that produce every number and every conditional sentence of a full-run
`record.md` ran in no test -- they executed only at the end of
`run-pll-cmos5l-layout-flow.sh`, which needs the PDK and `klt`. `render()` is
now a pure function of `plan.json` + `build.json` + the resolved PDK/deck
identity, so the committed records can be re-rendered here with no `klt`, no
PDK and no file write, and compared byte-for-byte.

The oracle is this repo's own append-only evidence: re-rendering a committed
record's `plan.json` + `build.json` must reproduce its committed `record.md`
exactly. The three header lines that come from `klt` itself (klt version,
resolved PDK, deck identity) are not in either JSON file, so they are parsed
back out of the committed record and handed to `render()` -- everything below
them is the rendering under test.

**Why the fixture list is pinned rather than globbed.** A committed
`record.md` is evidence of what the renderer said on the day that flow ran,
and records are never edited afterwards. When the renderer's prose changes,
the flow is re-run and the new record is checked in; the older records keep
the older wording and stop round-tripping. `GOLDEN_RECORDS` therefore names
the records the *current* renderer reproduces. Globbing every record would
force a future prose change to either edit committed evidence or delete the
oracle, and auto-skipping mismatches would make this file pass vacuously.

Maintaining it: after a flow re-run that changes rendered prose, add the new
record id here and drop any id that no longer round-trips. Never edit a
committed `record.md` to make this test pass.

**The one section currently cut from the comparison.** Issue #381 corrected
the real-block probe's closing sentence, which asserted that a second routing
plane "cannot be selected on this PDK family at all" even on the runs whose
own two-layer attempt was accepted and routed more nets than the single-layer
one. All four records listed below are such runs, so none of them round-trips
through that section any more -- while every other section of all four still
does. Rather than edit committed evidence or empty the oracle (which
`test_latest_record_is_a_golden` would catch), the three byte-comparisons
below cut the block-probe section from *both* sides via
`_without_block_probe_section()`; its wording is covered instead by the
committed-`build.json` cases in `test_render_pll_cmos5l_record_sections.py`.
Remove the cut -- and with it this paragraph -- once the next flow run commits
a record rendered with the corrected wording and the four ids below are
dropped under the rule in the paragraph above.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

LAYOUT_DIR = Path(__file__).resolve().parents[1]
BIN_DIR = LAYOUT_DIR / "bin"
REPORTS_DIR = LAYOUT_DIR / "sg13cmos5l-pll" / "reports"

#: Committed records the renderer reproduces byte-for-byte at its current
#: prose. Records older than these (20260830-*, 20260921-155747-c44fa68)
#: predate the LVS-section rewrite that replaced the per-block "secondary
#: cap-probe" paragraphs, and are deliberately NOT listed -- see the module
#: docstring.
GOLDEN_RECORDS = (
    "20260923-020931-a95a887-dirty",
    "20261003-183059-dc5644a",
    "20261010-012952-a4ca1b8",
    "20261027-175228-74cf8d0-dirty",
)


#: First line of the real-block probe section, in both the committed records
#: and the renderer's own output.
BLOCK_PROBE_HEADING = "#### Re-measured against a real block (klayout-tools#1467)"


def _without_block_probe_section(text: str) -> str:
    """Return `text` with the real-block probe section removed.

    The section runs from `BLOCK_PROBE_HEADING` up to, not including, the
    next line that starts a heading. A text with no such heading is a
    failure, not a no-op: a silent "cut nothing" would turn these
    comparisons back into whole-file ones without saying so, and a renamed
    heading would make them pass while comparing the very prose the cut
    exists to exclude.
    """
    lines = text.splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(BLOCK_PROBE_HEADING)),
        None,
    )
    assert start is not None, (
        f"no {BLOCK_PROBE_HEADING!r} heading to cut -- the section is gone or "
        "renamed, so this comparison is no longer the one it claims to be"
    )
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("#")),
        len(lines),
    )
    return "".join(lines[:start] + lines[end:])


def _load_renderer():
    spec = importlib.util.spec_from_file_location(
        "render_pll_cmos5l_record", BIN_DIR / "render-pll-cmos5l-record.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RENDERER = _load_renderer()


def _header_values(record_md: str) -> dict:
    """Recover the `klt`-sourced header inputs from a committed record.

    Those three lines are the only part of the document that does not come
    from `plan.json` / `build.json`; reading them back lets the comparison
    cover the whole file rather than stopping below the header.
    """
    klt_version = re.search(
        r"^- \*\*klt\*\*: `(.*)`$", record_md, re.MULTILINE
    ).group(1)
    pdk = re.search(
        r"^- \*\*PDK variant requested\*\*: `(.*)`$", record_md, re.MULTILINE
    ).group(1)

    resolved = re.search(
        r"^- \*\*PDK resolved\*\*: `(.*?)` at `(.*?)` \(via (.*?)\)$",
        record_md,
        re.MULTILINE,
    )
    pdk_info = (
        {
            "variant": resolved.group(1),
            "root": resolved.group(2),
            "resolved_via": resolved.group(3),
        }
        if resolved
        else {}
    )

    deck_line = re.search(
        r"^- \*\*Deck\*\*: `(.*?)` \(`(.*?)`\), device classes: (.*)$",
        record_md,
        re.MULTILINE,
    )
    if deck_line:
        deck = deck_line.group(1)
        deck_info = {
            "deck": deck,
            "content_hash": deck_line.group(2),
            "device_classes": [c.strip() for c in deck_line.group(3).split(",")],
        }
    else:
        deck = re.search(r"^- \*\*Deck\*\*: `(.*)`$", record_md, re.MULTILINE).group(1)
        deck_info = {}

    return {
        "klt_version": klt_version,
        "pdk": pdk,
        "deck": deck,
        "pdk_info": pdk_info,
        "deck_info": deck_info,
    }


def _render(record_dir: Path, committed: str) -> str:
    header = _header_values(committed)
    return RENDERER.render(
        record_dir.name,
        json.loads((record_dir / "plan.json").read_text()),
        json.loads((record_dir / "build.json").read_text()),
        header["pdk"],
        header["deck"],
        header["pdk_info"],
        header["deck_info"],
        header["klt_version"],
    )


@pytest.mark.parametrize("record_id", GOLDEN_RECORDS)
def test_golden_record_fixture_is_present(record_id: str):
    """Guard the oracle itself: a vanished fixture must fail, not pass."""
    record_dir = REPORTS_DIR / record_id
    for name in ("plan.json", "build.json", "record.md"):
        assert (record_dir / name).is_file(), f"missing {record_id}/{name}"


@pytest.mark.parametrize("record_id", GOLDEN_RECORDS)
def test_golden_record_has_a_block_probe_section(record_id: str):
    """Guard the cut: it must remove a real section, never nothing.

    If a committed record had no block-probe heading, the three
    comparisons below would silently become whole-file ones for it -- and
    would then fail on the corrected wording for the wrong reason.
    """
    committed = (REPORTS_DIR / record_id / "record.md").read_text()
    assert BLOCK_PROBE_HEADING in committed
    cut = _without_block_probe_section(committed)
    assert len(cut) < len(committed)
    assert BLOCK_PROBE_HEADING not in cut


def test_block_probe_cut_fails_without_the_heading():
    """The guard above is a real assertion, not a comment about one."""
    with pytest.raises(AssertionError, match="no '#### Re-measured"):
        _without_block_probe_section("## Record\n\nno block probe here\n")


def test_block_probe_cut_keeps_the_following_section():
    """The cut ends at the next heading, not at the end of the document."""
    text = (
        "## Routing\n\n"
        f"{BLOCK_PROBE_HEADING}\n\nsomething measured\n\n"
        "#### Generator-drawn footprints, re-measured\n\nkept\n"
    )

    assert _without_block_probe_section(text) == (
        "## Routing\n\n#### Generator-drawn footprints, re-measured\n\nkept\n"
    )


def test_latest_record_is_a_golden():
    """`reports/LATEST` names the newest full run; it must round-trip.

    This is what stops the pinned list above from quietly rotting: a flow
    re-run that changes rendered prose has to add its own record here.
    """
    latest = (REPORTS_DIR / "LATEST").read_text().strip()
    if not (REPORTS_DIR / latest / "build.json").is_file():
        pytest.skip(f"LATEST ({latest}) is a plan-only record, nothing to compare")
    assert latest in GOLDEN_RECORDS


@pytest.mark.parametrize("record_id", GOLDEN_RECORDS)
def test_committed_record_rerenders_byte_identically(record_id: str):
    record_dir = REPORTS_DIR / record_id
    committed = (record_dir / "record.md").read_text()
    rendered = _render(record_dir, committed)
    assert _without_block_probe_section(rendered) == _without_block_probe_section(
        committed
    )


@pytest.mark.parametrize("record_id", GOLDEN_RECORDS)
def test_render_shells_out_to_nothing(record_id: str, monkeypatch):
    """`render()` is pure: a `klt` call from inside it is a regression.

    The whole point of the split is that the document can be produced
    without the PDK or `klt`; a helper that quietly reached for a
    subprocess would still pass the byte-comparison above on a machine
    that happens to have `klt` installed.
    """
    import subprocess

    def forbidden(*args, **kwargs):  # pragma: no cover - only runs on failure
        raise AssertionError(f"render() shelled out: {args!r}")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "check_output", forbidden)

    record_dir = REPORTS_DIR / record_id
    committed = (record_dir / "record.md").read_text()
    rendered = _render(record_dir, committed)
    assert _without_block_probe_section(rendered) == _without_block_probe_section(
        committed
    )


def test_render_writes_nothing(tmp_path, monkeypatch):
    """`render()` returns text; only `main()` touches the filesystem."""
    record_dir = REPORTS_DIR / GOLDEN_RECORDS[-1]
    committed = (record_dir / "record.md").read_text()

    real_write_text = Path.write_text

    def forbidden(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError(f"render() wrote {self}")

    monkeypatch.setattr(Path, "write_text", forbidden)
    try:
        rendered = _render(record_dir, committed)
    finally:
        monkeypatch.setattr(Path, "write_text", real_write_text)
    assert _without_block_probe_section(rendered) == _without_block_probe_section(
        committed
    )
