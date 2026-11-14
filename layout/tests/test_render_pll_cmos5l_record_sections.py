"""Per-section tests for `render-pll-cmos5l-record.py` (issue #376).

The golden tests next door pin the whole document against this repo's
committed records, but every committed record was produced by a run that
took the *same* path through the renderer's conditionals: `klt gen-compose`
re-probed and accepted, the real-block probe run and still only partly
routing, no undrawn devices, no incomplete nets. The branches that fire on a
*different* upstream state -- the ones that decide whether a record says
klayout-tools#1467 "reproduces at this pin" or "no longer reproduces", and
which of three mutually exclusive sentences describes the `klt gen` family
gap -- have no committed record to compare against, and a wrong branch here
puts a wrong sentence into committed evidence.

Splitting `main()` into one helper per report section is what makes those
branches reachable from a test at all: each helper takes plain dicts and
returns its own lines, so a state that has never occurred in a real run can
still be rendered and asserted.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parents[1] / "bin"


def _load_renderer():
    spec = importlib.util.spec_from_file_location(
        "render_pll_cmos5l_record_sections", BIN_DIR / "render-pll-cmos5l-record.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _load_renderer()


# --- minimal fixtures --------------------------------------------------------


def _block(**over) -> dict:
    """One `build.json` block with every key the renderer reads."""
    block = {
        "name": "cp",
        "groups_drawn": 2,
        "group_count": 2,
        "devices_drawn": 4,
        "device_count": 4,
        "devices_drc_clean": 4,
        "devices_matched": 4,
        "composed": True,
        "routed_nets": 3,
        "incomplete_nets": 0,
        "block_drc_clean": True,
        "block_drc_violations": 0,
        "block_match": {"matched": True},
        "block_lvs": None,
        "compose": None,
        "results": [],
    }
    block.update(over)
    return block


def _build(**over) -> dict:
    build = {"blocks": [_block()]}
    build.update(over)
    return build


def _plan(**over) -> dict:
    plan = {"blocks": [{"device_count": 4}], "device_flavor": "thick-oxide"}
    plan.update(over)
    return plan


def _text(lines) -> str:
    return "\n".join(lines)


# --- the three family clauses (verdict section) ------------------------------


def test_family_clause_reprobed_and_block_remeasured():
    """Both probes ran: the record cites this run's own re-measurement."""
    build = _build(
        gen_compose_probe={"routing": {"ok": True}},
        gen_compose_block_probe={
            "ran": True,
            "block": "cp",
            "nets_declared": 22,
            "attempts": {"block-routing": {"routed_net_count": 2, "net_count": 22}},
        },
    )
    text = _text(R._verdict_lines(_plan(), build, "ihp-sg13cmos5l", "sg13cmos5l"))

    assert "this run's own re-probe (below) shows that gap fixed" in text
    assert "this run *also* re-measured" in text
    assert "(`cp`, 22 multi-pin nets)" in text
    assert "routes **2 of 22** nets" in text
    assert "has not been repeated against it this run" not in text


def test_family_clause_reprobed_without_block_remeasurement():
    """Two-pad probe accepted but no real-block probe: the #1467 measurement
    is explicitly flagged as predating this pin, not quietly reused."""
    build = _build(gen_compose_probe={"routing": {"ok": True}})
    text = _text(R._verdict_lines(_plan(), build, "ihp-sg13cmos5l", "sg13cmos5l"))

    assert "this run's own re-probe (below) shows that gap fixed" in text
    assert "that measurement predates this pin and has not been repeated" in text
    assert "this run *also* re-measured" not in text


def test_family_clause_still_rejected_at_this_pin():
    """Routing probe rejected: the family gap is stated in the present tense."""
    build = _build(gen_compose_probe={"routing": {"ok": False}})
    text = _text(R._verdict_lines(_plan(), build, "ihp-sg13cmos5l", "sg13cmos5l"))

    assert "at this repo's pin every `klt gen` generator" in text
    assert "closed upstream 2026-08-30, after this pin" in text
    assert "this run's own re-probe" not in text


def test_verdict_counts_are_summed_across_blocks():
    build = _build(
        blocks=[
            _block(name="cp", devices_drawn=4, devices_drc_clean=4, devices_matched=3),
            _block(
                name="vco",
                devices_drawn=2,
                devices_drc_clean=1,
                devices_matched=1,
                composed=False,
                block_drc_clean=False,
                block_match={"matched": False},
                routed_nets=5,
                block_lvs={"status": "match"},
            ),
        ]
    )
    plan = _plan(blocks=[{"device_count": 4}, {"device_count": 2}])
    verdict = _text(R._verdict_lines(plan, build, "ihp-sg13cmos5l", "sg13cmos5l"))

    assert "**6 / 6 devices drawn**" in verdict
    assert "**5 / 6 DRC-clean**" in verdict
    assert "**4 / 6 re-extracted matching the schematic**" in verdict
    assert "1 / 2 blocks composed and routed (8 nets)" in verdict
    assert "1 DRC-clean, 1 device-count-matched" in verdict
    assert "**1 / 2 LVS `match`**" in verdict


# --- per-block table ---------------------------------------------------------


@pytest.mark.parametrize(
    "block_lvs,expected",
    [
        (None, "| — |"),
        ({"ran": False}, "| not converted |"),
        (
            {
                "ran": True,
                "status": "match",
                "counts": {
                    "devices": {"matched": 28, "reference": 28},
                    "nets": {"matched": 22, "reference": 22},
                },
            },
            "| **match** (devices 28/28, nets 22/22) |",
        ),
    ],
)
def test_per_block_lvs_cell(block_lvs, expected):
    row = R._per_block_lines(_build(blocks=[_block(block_lvs=block_lvs)]))[-2]
    assert row.endswith(expected)


def test_per_block_incomplete_nets_annotated():
    rows = R._per_block_lines(
        _build(blocks=[_block(routed_nets=20, incomplete_nets=3)])
    )
    assert "| 20 (3 incomplete) |" in rows[-2]


def test_per_block_clean_block_has_no_incomplete_annotation():
    rows = R._per_block_lines(_build(blocks=[_block(routed_nets=20)]))
    assert "| 20 |" in rows[-2]
    assert "incomplete" not in rows[-2]


# --- floorplan ---------------------------------------------------------------


def test_floorplan_section_absent_without_locality_blocks():
    assert R._floorplan_lines(_build()) == []


def test_floorplan_section_reports_the_compose_arithmetic():
    build = _build(
        blocks=[
            _block(
                name="vco",
                compose={
                    "strategy": "locality",
                    "floorplan": {
                        "wire_length_um": 1000,
                        "baseline_wire_length_um": 1500,
                        "single_row_optimal_tracks_wire_length_um": 1200,
                    },
                },
            )
        ]
    )
    text = _text(R._floorplan_lines(build))

    assert text.startswith("### Floorplan\n")
    assert "total routed wire **1000 um** vs **1500 um**" in text
    assert "`1200 um`" in text
    assert "`compose.vco.json` -> `floorplan`" in text


# --- gen-compose two-pad probe ----------------------------------------------


def test_gen_compose_probe_section_absent_without_a_probe():
    assert R._gen_compose_probe_lines(_build()) == []


def test_gen_compose_probe_accepted():
    build = _build(
        gen_compose_probe={
            "placement": {"returncode": 0, "ok": True},
            "routing": {"returncode": 0, "ok": True},
        }
    )
    text = _text(R._gen_compose_probe_lines(build))

    assert "- placement-only: exit 0 (accepted)" in text
    assert "- with `routing`: exit 0 (accepted)" in text
    assert "**Both probes above are now accepted.**" in text
    assert "which is why the probe above still rejects" not in text


def test_gen_compose_probe_rejected_reports_the_error():
    build = _build(
        gen_compose_probe={
            "placement": {"returncode": 0, "ok": True},
            "routing": {"returncode": 2, "ok": False, "error": "unknown pdk family"},
        }
    )
    text = _text(R._gen_compose_probe_lines(build))

    assert "- with `routing`: exit 2 (rejected) — `unknown pdk family`" in text
    assert "after this repo's `layout/requirements.txt` pin" in text
    assert "**Both probes above are now accepted.**" not in text


# --- real-block probe --------------------------------------------------------


def _block_probe(routed_net_count: int, net_count: int = 22, **over) -> dict:
    probe = {
        "ran": True,
        "block": "cp",
        "group_count": 13,
        "device_count": 28,
        "port_count": 9,
        "nets_declared": net_count,
        "attempts": {
            "block-declare": {"returncode": 0, "net_count": net_count},
            "block-routing": {
                "returncode": 0,
                "routed_net_count": routed_net_count,
                "net_count": net_count,
                "leg_rejection_reasons": {"crosses already-routed net": 7},
            },
            "block-routing-two-layer": {
                "returncode": 2,
                "error": "no such layer role",
            },
        },
    }
    probe.update(over)
    return probe


def test_block_probe_section_absent_when_it_did_not_run():
    assert R._block_probe_lines(_build()) == []
    assert R._block_probe_lines(_build(gen_compose_block_probe={"ran": False})) == []


def test_block_probe_reproduces_the_upstream_gap():
    text = _text(
        R._block_probe_lines(_build(gen_compose_block_probe=_block_probe(2)))
    )

    assert "- declare-only (no `routing`): exit 0, 22 nets validated" in text
    assert "**2 of 22 nets routed**" in text
    assert "exit 2 — `no such layer role`" in text
    assert "- 7 × `crosses already-routed net`" in text
    assert "**klayout-tools#1467 reproduces at this pin.**" in text


def test_block_probe_fully_routed_retires_the_gap():
    """The branch no committed record has ever taken: every net routed."""
    text = _text(
        R._block_probe_lines(_build(gen_compose_block_probe=_block_probe(22)))
    )

    assert "**klayout-tools#1467 no longer reproduces at this pin.**" in text
    assert "Every declared net routed." in text
    assert "**klayout-tools#1467 reproduces at this pin.**" not in text


def test_block_probe_without_rejection_reasons_omits_that_list():
    probe = _block_probe(2)
    probe["attempts"]["block-routing"].pop("leg_rejection_reasons")
    text = _text(R._block_probe_lines(_build(gen_compose_block_probe=probe)))

    assert "Per-leg rejection reasons" not in text


# --- generator footprint probe ----------------------------------------------


def test_footprint_section_absent_without_probes():
    assert R._generator_footprint_lines(_build()) == []


def test_footprint_row_for_a_generator_that_refused_to_draw():
    build = _build(
        generator_footprint_probe=[
            {
                "generator": "mos_array",
                "key": "nfet_w2_l1",
                "source_group": "cp_nfet_w2_l1",
                "required_column_pitch_um": 1.2,
                "drew": False,
                "error": "unsupported pdk family",
            }
        ]
    )
    text = _text(R._generator_footprint_lines(build))

    assert "#### Generator-drawn footprints, re-measured" in text
    assert "at least 1.2 µm apart" in text
    assert (
        "| `mos_array` (`nfet_w2_l1`) | `cp_nfet_w2_l1` | no — "
        "`unsupported pdk family` | — | — | — | — | — |"
    ) in text


def test_footprint_row_flags_an_under_pitch_and_a_missing_body_port():
    build = _build(
        generator_footprint_probe=[
            {
                "generator": "mos_array",
                "key": "pfet_w6_l1",
                "source_group": "cp_pfet_w6_l1",
                "required_column_pitch_um": 1.2,
                "drew": True,
                "drc_clean": False,
                "drc_violation_count": 4,
                "device_counts": {"pfet": 2},
                "pdk_models": ["sg13_lv_pmos"],
                "min_port_column_pitch_um": 0.6,
                "column_pitch_ok": False,
                "body_port_declared": False,
                "unbiased_pmos_body_nets": 2,
                "drc_hint_notes": ["widen the landing pad", "widen the landing pad"],
            }
        ]
    )
    text = _text(R._generator_footprint_lines(build))

    assert (
        "| 4 | `pfet`×2 → `sg13_lv_pmos` | 0.6 µm ❌ under 1.2 µm | **no** | 2 |"
    ) in text
    # notes are de-duplicated, not repeated once per probe entry
    assert text.count("- `widen the landing pad`") == 1


def test_footprint_clean_row_uses_the_tick():
    build = _build(
        generator_footprint_probe=[
            {
                "generator": "res_array",
                "key": "rppd",
                "source_group": "lf_rppd",
                "required_column_pitch_um": 1.2,
                "drew": True,
                "drc_clean": True,
                "device_counts": {},
                "pdk_models": [],
                "min_port_column_pitch_um": 2.0,
                "column_pitch_ok": True,
                "body_port_declared": True,
                "unbiased_pmos_body_nets": 0,
            }
        ]
    )
    text = _text(R._generator_footprint_lines(build))

    assert "| clean | — | 2.0 µm ✅ | yes | 0 |" in text


# --- interconnect / incomplete nets -----------------------------------------


def test_interconnect_table_reports_zeroes_for_an_uncomposed_block():
    text = _text(R._interconnect_lines(_build(blocks=[_block(compose=None)])))
    assert "| `cp` | 0 | 0 | 0 | — |" in text
    assert "A net listed as incomplete" not in text


def test_incomplete_nets_grouped_by_reason_and_deduplicated():
    note = {
        "net": "vbias",
        "missing_pin": "XM12/G",
        "reason": "cap_cmomi has no generator at this pin",
    }
    build = _build(
        blocks=[
            _block(
                compose={
                    "routing": {
                        "terminal_count": 8,
                        "net_count": 4,
                        "wire_length_um": 120,
                        # the same (net, missing_pin) twice: reported once
                        "incomplete_nets": [note, dict(note), {**note, "net": "vout"}],
                    },
                    "terminal_count": 8,
                }
            )
        ]
    )
    text = _text(R._interconnect_lines(build))

    assert "| `vbias`, `vout` |" in text
    assert text.count("`vbias` (missing `XM12/G`)") == 1
    assert "  - reason: cap_cmomi has no generator at this pin" in text


# --- devices never drawn -----------------------------------------------------


def test_never_drawn_section_says_so_when_everything_drew():
    text = _text(R._never_drawn_lines(_build()))
    assert "### Devices recorded but never drawn" in text
    assert "- none: every planned device was drawn." in text


def test_never_drawn_section_groups_group_ids_by_captured_reason():
    build = _build(
        blocks=[
            _block(
                results=[
                    {"attempted": True, "group_id": "g1"},
                    {"attempted": False, "group_id": "g3", "reason": "no generator"},
                    {"attempted": False, "group_id": "g2", "reason": "no generator"},
                    {"attempted": False, "group_id": "g4", "reason": "deck gap"},
                ]
            )
        ]
    )
    text = _text(R._never_drawn_lines(build))

    assert "- `g2`, `g3` — no generator" in text
    assert "- `g4` — deck gap" in text
    assert "none: every planned device was drawn." not in text


# --- LVS ---------------------------------------------------------------------


def test_lvs_section_reports_an_unconverted_block_with_its_error():
    build = _build(blocks=[_block(block_lvs={"ran": False, "error": "no deck entry"})])
    text = _text(R._lvs_lines(build))

    assert "### LVS status" in text
    assert "- `cp` — **not converted**: no deck entry" in text


def test_lvs_section_reports_counts_and_categories():
    build = _build(
        blocks=[
            _block(
                block_lvs={
                    "ran": True,
                    "status": "mismatch",
                    "counts": {
                        "devices": {"matched": 38, "reference": 45},
                        "nets": {"matched": 25, "reference": 33},
                        "pins": {"matched": 9, "reference": 9},
                    },
                    "mismatch_count": 3,
                    "category_counts": {"net.merged": 1, "device.missing": 2},
                }
            )
        ]
    )
    text = _text(R._lvs_lines(build))

    assert (
        "- `cp` — **mismatch**, devices 38/45, nets 25/33, pins 9/9; "
        "`mismatch_count` 3 (device.missing: 2, net.merged: 1)"
    ) in text


def test_lvs_section_says_none_when_there_are_no_mismatch_categories():
    build = _build(
        blocks=[
            _block(
                block_lvs={
                    "ran": True,
                    "status": "match",
                    "counts": {
                        "devices": {"matched": 4, "reference": 4},
                        "nets": {"matched": 3, "reference": 3},
                        "pins": {"matched": 2, "reference": 2},
                    },
                    "mismatch_count": 0,
                    "category_counts": {},
                }
            )
        ]
    )
    assert "`mismatch_count` 0 (none)" in _text(R._lvs_lines(build))


# --- device flavor + plan-only path -----------------------------------------


def test_device_flavor_section_is_the_plans_own_prose():
    text = _text(R._device_flavor_lines(_plan(device_flavor="thick-oxide (DR-002)")))
    assert text.startswith("### Device flavor\n\nthick-oxide (DR-002)")


def test_render_plan_only_stops_at_the_verdict():
    out = R.render(
        "20260101-000000-abcdef0",
        _plan(blocks=[{"device_count": 7}, {"device_count": 3}]),
        None,
        "ihp-sg13cmos5l",
        "sg13cmos5l",
        {},
        {},
        "klt 0.8.0",
    )

    assert out.startswith(
        "# PLL SG13CMOS5L layout record — `20260101-000000-abcdef0`\n"
    )
    assert "- **PDK resolved**: not resolved (plan-only run)" in out
    assert "- **Deck**: `sg13cmos5l`" in out
    assert "## Verdict: PLAN ONLY — nothing drawn this run" in out
    assert "`plan.json` derives **10** device(s) across 2 blocks." in out
    assert "### Per-block" not in out
    assert out.endswith("\n")


def test_render_header_falls_back_when_klt_reports_nothing():
    out = R.render(
        "rec", _plan(), None, "ihp-sg13cmos5l", "sg13cmos5l", {}, {}, ""
    )
    assert "- **klt**: `unknown`" in out
