"""PDK-free unit tests for layout/bin/pll_layout.py (issue #13).

Runs with no `klt` install and no PDK -- only the `Plan` half of
`pll_layout.py` (netlist parsing, recursive flattening, grouping) is
exercised here. The `Build` half (`Builder`/`attempt_build`, which shells out
to `klt`) is deliberately not covered by this file; it needs the pinned
`klt` install + a real `ihp-sg13g2` PDK, and is exercised manually via
`layout/bin/run-pll-layout-flow.sh` (see layout/pll/README.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import pll_layout  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
NETLIST_DIR = REPO_ROOT / "design" / "netlist"


# --- read_cards --------------------------------------------------------------


def test_read_cards_parses_ports_and_instance_cards():
    text = """
* comment
.subckt foo A B VDD VSS
XM1 A B VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
+ b=0
.ends
"""
    blocks = pll_layout.read_cards(text)
    assert blocks["foo"]["ports"] == ["A", "B", "VDD", "VSS"]
    (card,) = blocks["foo"]["cards"]
    assert card["name"] == "XM1"
    assert card["model"] == "sg13_hv_pmos"
    assert card["nets"] == ["A", "B", "VDD", "VDD"]
    assert card["params"] == {"w": "5u", "l": "0.5u", "ng": "1", "m": "1", "b": "0"}


def test_read_cards_uppercases_are_not_required_lowercase_params():
    # SG13G2's own netlists write params lowercase (unlike sky130's W=/L=);
    # this asserts the parser does not silently expect the other case.
    text = ".subckt r A B\nXR A B rppd w=1u l=30u m=1 b=0\n.ends\n"
    blocks = pll_layout.read_cards(text)
    assert blocks["r"]["cards"][0]["params"]["w"] == "1u"


def test_read_cards_unwraps_doubly_commented_top_header():
    text = "**.subckt top A B\nXM1 A B foo\n**.ends\n"
    blocks = pll_layout.read_cards(text)
    assert "top" in blocks


# --- flatten_block: recursive hierarchy expansion ---------------------------


def test_flatten_block_leaf_only():
    blocks = pll_layout.read_cards(
        ".subckt leaf A B VDD VSS\n"
        "XM1 A B VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1\n"
        ".ends\n"
    )
    devices = pll_layout.flatten_block(blocks, "leaf")
    assert len(devices) == 1
    assert devices[0]["path"] == "XM1"
    assert devices[0]["model"] == "sg13_hv_pmos"
    assert devices[0]["nets"] == ["A", "B", "VDD", "VDD"]


def test_flatten_block_recurses_and_resolves_ports():
    blocks = pll_layout.read_cards(
        ".subckt top IN OUT VDD VSS\n"
        "XI1 IN mid VDD VSS inv\n"
        "XI2 mid OUT VDD VSS inv\n"
        ".ends\n"
        ".subckt inv A Y VDD VSS\n"
        "XMP Y A VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1\n"
        "XMN Y A VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1\n"
        ".ends\n"
    )
    devices = pll_layout.flatten_block(blocks, "top")
    assert len(devices) == 4
    paths = {d["path"] for d in devices}
    assert paths == {"XI1.XMP", "XI1.XMN", "XI2.XMP", "XI2.XMN"}
    # XI1's own inv instance: Y net (the sub-block's local "Y") resolves to
    # the caller-supplied "mid" net; A resolves to "IN".
    xi1_xmp = next(d for d in devices if d["path"] == "XI1.XMP")
    assert xi1_xmp["nets"] == ["mid", "IN", "VDD", "VDD"]
    xi2_xmp = next(d for d in devices if d["path"] == "XI2.XMP")
    assert xi2_xmp["nets"] == ["OUT", "mid", "VDD", "VDD"]


def test_flatten_block_namespaces_internal_nets_per_instance():
    # Two instances of the same leaf subckt must not collide on an internal
    # (non-port) net -- this is exactly divider_chain's own div23_cell x 6
    # shape.
    blocks = pll_layout.read_cards(
        ".subckt top A B VDD VSS\n"
        "XU1 A n1 VDD VSS unit\n"
        "XU2 n1 B VDD VSS unit\n"
        ".ends\n"
        ".subckt unit IN OUT VDD VSS\n"
        "XM1 IN internal VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1\n"
        "XM2 internal OUT VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1\n"
        ".ends\n"
    )
    devices = pll_layout.flatten_block(blocks, "top")
    nets_by_path = {d["path"]: d["nets"] for d in devices}
    # XU1's "internal" net is namespaced under XU1.; XU2's under XU2. --
    # never the same net.
    assert nets_by_path["XU1.XM1"][1] == "XU1.internal"
    assert nets_by_path["XU2.XM1"][1] == "XU2.internal"
    assert nets_by_path["XU1.XM1"][1] != nets_by_path["XU2.XM1"][1]


def test_flatten_block_treats_bang_suffixed_nets_as_global():
    blocks = pll_layout.read_cards(
        ".subckt top A B\n"
        "XU1 A n1 unit\n"
        ".ends\n"
        ".subckt unit IN OUT\n"
        "XR IN sub! rppd w=1u l=30u m=1 b=0\n"
        ".ends\n"
    )
    devices = pll_layout.flatten_block(blocks, "top")
    assert devices[0]["nets"][1] == "sub!"  # not namespaced/prefixed


def test_flatten_block_raises_on_unknown_model():
    blocks = pll_layout.read_cards(
        ".subckt top A B\nXQ A B some_unmodeled_device\n.ends\n"
    )
    with pytest.raises(pll_layout.PlanError, match="some_unmodeled_device"):
        pll_layout.flatten_block(blocks, "top")


def test_flatten_block_raises_on_missing_top():
    blocks = pll_layout.read_cards(".subckt other A B\n.ends\n")
    with pytest.raises(pll_layout.PlanError, match="top"):
        pll_layout.flatten_block(blocks, "top")


def test_flatten_block_raises_on_port_count_mismatch():
    blocks = pll_layout.read_cards(
        ".subckt top A\nXU1 A extra unit\n.ends\n"
        ".subckt unit IN\n.ends\n"
    )
    with pytest.raises(pll_layout.PlanError, match="port"):
        pll_layout.flatten_block(blocks, "top")


# --- assert_ratified_device_flavor (DR-002 Decision 0 guard) ---------------


def test_assert_ratified_device_flavor_accepts_hv_devices():
    devices = [{"path": "XM1", "model": "sg13_hv_nmos", "params": {}}]
    pll_layout.assert_ratified_device_flavor(devices)  # no raise


def test_assert_ratified_device_flavor_rejects_thin_oxide_devices():
    devices = [{"path": "XM1", "model": "sg13_lv_nmos", "params": {}}]
    with pytest.raises(pll_layout.PlanError, match="DR-002"):
        pll_layout.assert_ratified_device_flavor(devices)


# --- factor_rows_cols ---------------------------------------------------------


@pytest.mark.parametrize(
    "count,expected",
    [(1, (1, 1)), (5, (1, 5)), (6, (2, 3)), (18, (3, 6)), (32, (4, 8))],
)
def test_factor_rows_cols(count, expected):
    assert pll_layout.factor_rows_cols(count) == expected


def test_factor_rows_cols_rejects_nonpositive():
    with pytest.raises(pll_layout.PlanError):
        pll_layout.factor_rows_cols(0)


# --- plan_block: grouping ----------------------------------------------------


def test_plan_block_groups_mos_by_flavor_w_l():
    devices = [
        {
            "path": f"XM{i}",
            "model": "sg13_hv_pmos",
            "nets": ["D", "G", "S", "B"],
            "params": {"w": "5u", "l": "0.5u"},
        }
        for i in range(4)
    ] + [
        {
            "path": "XM4",
            "model": "sg13_hv_nmos",
            "nets": ["D", "G", "S", "B"],
            "params": {"w": "2u", "l": "0.5u"},
        }
    ]
    plan = pll_layout.plan_block("blk", devices)
    assert plan["device_count"] == 5
    kinds = {g["kind"] for g in plan["groups"]}
    assert kinds == {"mos_array"}
    pfet_group = next(g for g in plan["groups"] if g["params"]["flavor"] == "pfet")
    assert pfet_group["count"] == 4
    assert pfet_group["params"]["rows"] * pfet_group["params"]["cols"] == 4
    nfet_group = next(g for g in plan["groups"] if g["params"]["flavor"] == "nfet")
    assert nfet_group["count"] == 1
    # Every mos_array group carries an "expected" cross-check (class, W, L,
    # count) the build step's extraction result is compared against.
    assert pfet_group["expected"] == {
        "class": "pfet",
        "w_um": 5.0,
        "l_um": 0.5,
        "count": 4,
    }


def test_plan_block_groups_resistors_by_flavor_w_l():
    devices = [
        {
            "path": "XR1",
            "model": "rppd",
            "nets": ["A", "B", "sub!"],
            "params": {"w": "1u", "l": "30u"},
        },
        {
            "path": "XR2",
            "model": "rhigh",
            "nets": ["A", "B", "sub!"],
            "params": {"w": "0.5u", "l": "8u"},
        },
    ]
    plan = pll_layout.plan_block("blk", devices)
    assert {g["kind"] for g in plan["groups"]} == {"res_array"}
    flavors = {g["params"]["flavor"] for g in plan["groups"]}
    assert flavors == {"rppd", "rhigh"}
    for group in plan["groups"]:
        assert group["expected"]["class"] == group["params"]["flavor"]
        assert group["expected"]["count"] == group["count"]


def test_plan_block_plans_cap_cmim_as_a_drawable_cap_array_group():
    # cap_cmim (SG13G2's own MIM capacitor) draws via `klt gen cap_array`
    # since klayout-tools#1461 -- issue #31's re-bump.
    devices = [
        {
            "path": "XC1",
            "model": "cap_cmim",
            "nets": ["TOP", "BOT"],
            "params": {"w": "40u", "l": "40u"},
        }
    ]
    plan = pll_layout.plan_block("blk", devices)
    (group,) = plan["groups"]
    assert group["kind"] == "capacitor"
    assert group["generator"] == "cap_array"
    assert "blocked_reason" not in group
    assert group["params"] == {"plate_w_um": 40.0, "plate_h_um": 40.0, "num": 1}
    assert group["expected"] == {
        "class": "cap_cmim",
        "area_um2": 1600.0,
        "perimeter_um": 160.0,
        "count": 1,
    }


def test_plan_block_records_but_never_attempts_cap_cmomi():
    # cap_cmomi (the SG13CMOS5L port's MoM capacitor, DR-004) still has no
    # `klt gen` generator on any PDK family.
    devices = [
        {
            "path": "XC1",
            "model": "cap_cmomi",
            "nets": ["TOP", "BOT"],
            "params": {"w": "40u", "l": "40u"},
        }
    ]
    plan = pll_layout.plan_block("blk", devices)
    (group,) = plan["groups"]
    assert group["kind"] == "capacitor"
    assert group["generator"] is None
    assert group["expected"] is None
    assert "never drawn" in group["blocked_reason"]


def test_plan_block_member_port_maps_are_recorded():
    devices = [
        {
            "path": "XM0",
            "model": "sg13_hv_nmos",
            "nets": ["d0", "g0", "s0", "b0"],
            "params": {"w": "2u", "l": "0.5u"},
        }
    ]
    plan = pll_layout.plan_block("blk", devices)
    (group,) = plan["groups"]
    (member,) = group["members"]
    assert member["device"] == "XM0"
    assert member["ports"] == {
        "U0_D": "d0",
        "U0_G": "g0",
        "U0_S": "s0",
        "U0_B": "b0",
    }


# --- build_plan against the real committed netlists -------------------------


@pytest.mark.skipif(not NETLIST_DIR.is_dir(), reason="design/netlist/ not present")
def test_build_plan_covers_every_named_block():
    plan = pll_layout.build_plan(NETLIST_DIR)
    names = [b["name"] for b in plan["blocks"]]
    assert names == pll_layout.BLOCK_ORDER


@pytest.mark.skipif(not NETLIST_DIR.is_dir(), reason="design/netlist/ not present")
def test_build_plan_every_block_has_at_least_one_device():
    plan = pll_layout.build_plan(NETLIST_DIR)
    for block in plan["blocks"]:
        assert block["device_count"] > 0, block["name"]
        assert sum(g["count"] for g in block["groups"]) == block["device_count"]


@pytest.mark.skipif(not NETLIST_DIR.is_dir(), reason="design/netlist/ not present")
def test_build_plan_loop_filter_has_resistor_and_two_capacitors():
    plan = pll_layout.build_plan(NETLIST_DIR)
    loop_filter = next(b for b in plan["blocks"] if b["name"] == "loop_filter")
    kinds = [g["kind"] for g in loop_filter["groups"]]
    assert kinds.count("res_array") == 1
    assert kinds.count("capacitor") == 2
    assert loop_filter["device_count"] == 3


@pytest.mark.skipif(not NETLIST_DIR.is_dir(), reason="design/netlist/ not present")
def test_build_plan_devices_are_all_ratified_flavor(monkeypatch):
    # Exercises the DR-002 guard against the real committed netlists: this
    # must not raise.
    plan = pll_layout.build_plan(NETLIST_DIR)
    assert plan["device_flavor"].startswith("sg13_hv_nmos/sg13_hv_pmos")
    for block in plan["blocks"]:
        for group in block["groups"]:
            if group["kind"] == "mos_array":
                assert group["params"]["flavor"] in ("nfet", "pfet")


@pytest.mark.skipif(not NETLIST_DIR.is_dir(), reason="design/netlist/ not present")
def test_plan_totals_matches_sum_of_block_device_counts():
    plan = pll_layout.build_plan(NETLIST_DIR)
    totals = pll_layout.plan_totals(plan)
    assert sum(totals.values()) == sum(b["device_count"] for b in plan["blocks"])


# --- shelf_pack (pure, PDK-free composition floorplan helper) ---------------


def test_shelf_pack_places_left_to_right_within_target_width():
    origins = pll_layout.shelf_pack(
        [("a", 10.0, 5.0), ("b", 10.0, 5.0)], target_width_um=100.0, spacing_um=2.0
    )
    assert origins["a"] == {"x": 0.0, "y": 0.0}
    assert origins["b"] == {"x": 12.0, "y": 0.0}


def test_shelf_pack_wraps_to_a_new_shelf_past_target_width():
    origins = pll_layout.shelf_pack(
        [("a", 10.0, 5.0), ("b", 10.0, 5.0)], target_width_um=15.0, spacing_um=2.0
    )
    assert origins["a"] == {"x": 0.0, "y": 0.0}
    assert origins["b"]["x"] == 0.0
    assert origins["b"]["y"] > 0.0


def test_shelf_pack_is_deterministic():
    sizes = [("a", 10.0, 5.0), ("b", 20.0, 3.0), ("c", 5.0, 8.0)]
    first = pll_layout.shelf_pack(sizes, target_width_um=25.0, spacing_um=1.0)
    second = pll_layout.shelf_pack(sizes, target_width_um=25.0, spacing_um=1.0)
    assert first == second


# --- _match_group_extraction / _match_block_extraction ----------------------


def test_match_group_extraction_accepts_exact_match():
    group = {"expected": {"class": "nfet", "w_um": 6.0, "l_um": 1.0, "count": 1}}
    extract_report = {
        "devices": [
            {"name": "$1", "class": "nfet", "params": {"w_um": 6.0, "l_um": 1.0}}
        ]
    }
    result = pll_layout._match_group_extraction(group, extract_report)
    assert result["matched"] is True
    assert result["mismatches"] == []


def test_match_group_extraction_flags_wrong_class():
    group = {"expected": {"class": "nfet", "w_um": 6.0, "l_um": 1.0, "count": 1}}
    extract_report = {
        "devices": [
            {"name": "$1", "class": "pfet", "params": {"w_um": 6.0, "l_um": 1.0}}
        ]
    }
    result = pll_layout._match_group_extraction(group, extract_report)
    assert result["matched"] is False
    assert any("class" in m for m in result["mismatches"])


def test_match_group_extraction_flags_wrong_dimension():
    group = {"expected": {"class": "nfet", "w_um": 6.0, "l_um": 1.0, "count": 1}}
    extract_report = {
        "devices": [
            {"name": "$1", "class": "nfet", "params": {"w_um": 6.5, "l_um": 1.0}}
        ]
    }
    result = pll_layout._match_group_extraction(group, extract_report)
    assert result["matched"] is False
    assert any("w_um" in m for m in result["mismatches"])


def test_match_group_extraction_flags_device_count_mismatch():
    group = {"expected": {"class": "nfet", "w_um": 6.0, "l_um": 1.0, "count": 2}}
    extract_report = {
        "devices": [
            {"name": "$1", "class": "nfet", "params": {"w_um": 6.0, "l_um": 1.0}}
        ]
    }
    result = pll_layout._match_group_extraction(group, extract_report)
    assert result["matched"] is False
    assert any("expected 2 device" in m for m in result["mismatches"])


def test_match_group_extraction_accepts_exact_capacitor_match():
    # A MiM cap has no single W/L to compare -- `expected` carries
    # area_um2/perimeter_um instead, and the match branches on that.
    group = {
        "expected": {
            "class": "cap_cmim",
            "area_um2": 1600.0,
            "perimeter_um": 160.0,
            "count": 1,
        }
    }
    extract_report = {
        "devices": [
            {
                "name": "$1",
                "class": "cap_cmim",
                "params": {"c_f": 2.4064e-12, "area_um2": 1600.0, "perimeter_um": 160.0},
            }
        ]
    }
    result = pll_layout._match_group_extraction(group, extract_report)
    assert result["matched"] is True
    assert result["mismatches"] == []


def test_match_group_extraction_flags_wrong_capacitor_area():
    group = {
        "expected": {
            "class": "cap_cmim",
            "area_um2": 1600.0,
            "perimeter_um": 160.0,
            "count": 1,
        }
    }
    extract_report = {
        "devices": [
            {
                "name": "$1",
                "class": "cap_cmim",
                "params": {"c_f": 2.4e-12, "area_um2": 1599.0, "perimeter_um": 160.0},
            }
        ]
    }
    result = pll_layout._match_group_extraction(group, extract_report)
    assert result["matched"] is False
    assert any("area_um2" in m for m in result["mismatches"])


def test_match_block_extraction_sums_expected_counts_by_class():
    block = {
        "groups": [
            {
                "kind": "mos_array",
                "generator": "mos_array",
                "count": 3,
                "expected": {"class": "nfet"},
            },
            {
                "kind": "mos_array",
                "generator": "mos_array",
                "count": 2,
                "expected": {"class": "pfet"},
            },
            {
                "kind": "capacitor",
                "generator": "cap_array",
                "count": 1,
                "expected": {"class": "cap_cmim"},
            },
            {
                "kind": "capacitor",
                "generator": None,
                "count": 1,
                "expected": None,
            },
        ]
    }
    extract_report = {"device_counts": {"nfet": 3, "pfet": 2, "cap_cmim": 1}}
    result = pll_layout._match_block_extraction(block, extract_report)
    # The blocked (generator: None) capacitor group is excluded -- its
    # `expected` is None and it was never drawn/composed.
    assert result["expected_counts"] == {"nfet": 3, "pfet": 2, "cap_cmim": 1}
    assert result["matched"] is True


def test_match_block_extraction_flags_count_mismatch():
    block = {
        "groups": [
            {
                "kind": "mos_array",
                "generator": "mos_array",
                "count": 3,
                "expected": {"class": "nfet"},
            }
        ]
    }
    extract_report = {"device_counts": {"nfet": 2}}
    result = pll_layout._match_block_extraction(block, extract_report)
    assert result["matched"] is False
    assert any("nfet" in m for m in result["mismatches"])
