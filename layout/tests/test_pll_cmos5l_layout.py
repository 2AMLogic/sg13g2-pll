"""Unit tests for the SG13CMOS5L device-level layout flow (issue #24).

Split the same way `test_pll_layout_plan.py` splits the SG13G2 side:

* The **plan** half needs no PDK, no `klt` and no `klayout` -- it is
  `pll_layout`'s own parser/flattener pointed at `design/sg13cmos5l/netlist`.
* The **draw** half needs `klayout.db` (the pinned `klt` install brings it in)
  but still no PDK and no `klt` subprocess: it checks the geometry
  `cmos5l_devices.py` emits, and the packer/drawer agreement that the composed
  floorplan depends on.

What is deliberately *not* covered here: `klt drc`/`klt extract`/`klt lvs`
results. Those are real tool output, not something a unit test should
simulate -- they live in the committed record under
`layout/sg13cmos5l-pll/reports/` and are produced by
`layout/bin/run-pll-cmos5l-layout-flow.sh`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import pll_layout  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CMOS5L_NETLIST_DIR = REPO_ROOT / "design" / "sg13cmos5l" / "netlist"

kdb = pytest.importorskip("klayout.db", reason="needs the pinned klt install")

import cmos5l_devices as dev  # noqa: E402
import pll_cmos5l_layout as flow  # noqa: E402


@pytest.fixture(scope="module")
def cmos5l_plan():
    return pll_layout.build_plan(CMOS5L_NETLIST_DIR)


# --- Plan half (shared with the SG13G2 flow) --------------------------------


def test_every_cmos5l_block_netlist_plans(cmos5l_plan):
    """All six blocks parse, flatten and group from the CMOS5L netlists."""
    assert [b["name"] for b in cmos5l_plan["blocks"]] == pll_layout.BLOCK_ORDER
    assert all(b["device_count"] > 0 for b in cmos5l_plan["blocks"])


def test_cmos5l_plan_totals_are_mos_resistor_and_mom_capacitor(cmos5l_plan):
    """The port's device set is MOS + poly resistors + MoM capacitors only.

    Guards the MIM->MoM swap (#22/DR-004): a regression that reintroduced
    `cap_cmim` on the CMOS5L side -- a device that family forbids outright --
    would show up here as an unexpected model rather than as a silently
    different layout.
    """
    totals = pll_layout.plan_totals(cmos5l_plan)
    assert set(totals) == {"mos_array", "res_array", "capacitor"}
    assert sum(totals.values()) == sum(
        b["device_count"] for b in cmos5l_plan["blocks"]
    )

    models = set()
    for block_name in pll_layout.BLOCK_ORDER:
        cards = pll_layout.read_cards(
            (CMOS5L_NETLIST_DIR / f"{block_name}.spice").read_text()
        )
        for device in pll_layout.flatten_block(cards, block_name):
            models.add(device["model"])
    assert models == {"sg13_hv_nmos", "sg13_hv_pmos", "rppd", "rhigh", "cap_cmomi"}


def test_cmos5l_capacitors_are_recorded_with_their_own_blocked_reason(cmos5l_plan):
    """A MoM capacitor is never silently dropped, and never attributed to the
    SG13G2 side's MIM gap -- it carries its own two tracked upstream issues."""
    cap_groups = [
        group
        for block in cmos5l_plan["blocks"]
        for group in block["groups"]
        if group["kind"] == "capacitor"
    ]
    assert cap_groups, "the CMOS5L netlists do declare capacitors"
    for group in cap_groups:
        assert group["params"]["model"] == "cap_cmomi"
        reason = group["blocked_reason"]
        assert "1462" in reason and "1463" in reason
        assert "1455" not in reason and "1454" not in reason


def test_ratified_device_flavor_holds_on_the_cmos5l_netlists():
    """DR-002 Decision 0: thick-oxide (HV) CMOS throughout, on this port too."""
    for block_name in pll_layout.BLOCK_ORDER:
        cards = pll_layout.read_cards(
            (CMOS5L_NETLIST_DIR / f"{block_name}.spice").read_text()
        )
        pll_layout.assert_ratified_device_flavor(
            pll_layout.flatten_block(cards, block_name)
        )


# --- Device geometry --------------------------------------------------------


def test_mos_active_size_puts_width_on_x_and_length_on_y():
    act_w, act_h = dev.mos_active_size(4.0, 0.5)
    assert act_w == 4.0
    assert act_h == pytest.approx(0.5 + 2 * dev.SD_EXT_UM)


def test_pfet_margin_is_wider_than_nfet_margin():
    """A PFET carries a pSD implant the NFET does not, so its own drawn
    extent is wider -- the packer must not assume one pitch for both."""
    assert dev.mos_margins("pfet")[0] > dev.mos_margins("nfet")[0]


def test_rhigh_carries_nsd_and_rppd_does_not():
    """The one layer that physically distinguishes the two poly-resistor
    flavours, and the one the curated deck's `requires`/`excludes` sets key
    on (klayout-tools#1415)."""
    assert dev.L_NSD in dev.RES_MARKERS["rhigh"]
    assert dev.L_NSD not in dev.RES_MARKERS["rppd"]
    assert set(dev.RES_MARKERS["rppd"]) < set(dev.RES_MARKERS["rhigh"])


def test_unknown_flavors_raise_rather_than_drawing_something_else():
    builder = dev.Builder()
    builder.open_cell("t")
    with pytest.raises(ValueError):
        dev.draw_hv_mos(builder, "bjt", 0.0, 0.0, 1.0, 0.5)
    with pytest.raises(ValueError):
        dev.draw_poly_res(builder, "rsil", 0.0, 0.0, 1.0, 5.0)


def test_metal1_terminal_pad_clears_the_decks_min_width():
    """`PAD_H_UM` is the narrowest Metal1 dimension this flow ever draws; the
    curated deck's `metal1.width.1` floor is 0.16 um."""
    assert dev.PAD_H_UM >= 0.16


# --- Group drawing / packing ------------------------------------------------


def _group(kind: str, **params):
    base = {"id": "g", "kind": kind, "count": params.pop("count"), "params": params}
    return base


def test_drawn_mos_group_has_one_active_per_planned_device():
    builder = dev.Builder()
    group = _group(
        "mos_array", count=6, flavor="nfet", w_um=2.0, l_um=0.5, rows=2, cols=3
    )
    flow.draw_mos_group(builder, group)
    cell = builder.layout.cell("g")
    active_index = builder.layout.layer(*dev.L_ACTIV)
    # One box per unit device, plus exactly one substrate-tap strip.
    assert cell.shapes(active_index).size() == 6 + 1


def test_drawn_pfet_group_gets_one_shared_well_and_one_well_label():
    """Three separate wells would extract as three unrelated body nets; the
    label is what keeps `klt extract` from reporting `unbiased_pmos_body_nets`."""
    builder = dev.Builder()
    group = _group(
        "mos_array", count=4, flavor="pfet", w_um=5.0, l_um=0.5, rows=1, cols=4
    )
    geometry = flow.draw_mos_group(builder, group)
    cell = builder.layout.cell("g")
    assert cell.shapes(builder.layout.layer(*dev.L_NWELL)).size() == 1
    assert cell.shapes(builder.layout.layer(*dev.L_NWELL_PIN)).size() == 1
    assert geometry["body_tie"]["kind"] == "nwell_tap"
    assert geometry["body_tie"]["net_label"] == "g_B"


def test_nfet_group_draws_no_well_at_all():
    """An NMOS body is the p-substrate: a well here would be wrong against the
    PCell *and* would flip the deck's `active - nwell` NMOS derivation."""
    builder = dev.Builder()
    group = _group(
        "mos_array", count=2, flavor="nfet", w_um=2.0, l_um=0.5, rows=1, cols=2
    )
    flow.draw_mos_group(builder, group)
    cell = builder.layout.cell("g")
    assert cell.shapes(builder.layout.layer(*dev.L_NWELL)).size() == 0


@pytest.mark.parametrize(
    "group",
    [
        _group("mos_array", count=7, flavor="nfet", w_um=4.0, l_um=0.5, rows=1, cols=7),
        _group("mos_array", count=6, flavor="pfet", w_um=5.0, l_um=1.0, rows=2, cols=3),
        _group("mos_array", count=1, flavor="pfet", w_um=24.0, l_um=1.0, rows=1, cols=1),
        _group("res_array", count=3, flavor="rppd", width_um=1.0, length_um=60.0),
        _group("res_array", count=1, flavor="rhigh", width_um=0.5, length_um=8.0),
    ],
)
def test_group_size_um_bounds_the_geometry_actually_drawn(group):
    """The shelf-packer sizes groups from constants rather than from the
    layout, so the two must not drift: a group that draws wider than
    `group_size_um` reports would overlap its neighbour in the composed cell
    and only surface as a DRC violation much later.
    """
    builder = dev.Builder()
    if group["kind"] == "mos_array":
        flow.draw_mos_group(builder, group)
    else:
        flow.draw_res_group(builder, group)
    bbox = builder.layout.cell("g").dbbox()
    width, height = flow.group_size_um(group)
    assert bbox.left >= -1e-6
    assert bbox.bottom >= -1e-6
    assert bbox.right <= width + 1e-6
    assert bbox.top <= height + 1e-6


def test_reference_device_map_covers_the_resistors_and_not_the_capacitor():
    """Documents the split between the two tracked upstream gaps: the
    resistors need a caller-side map (klayout-tools#1464) but *can* be mapped;
    the MoM capacitor cannot be mapped at all, because the deck declares no
    capacitor class to map it to (klayout-tools#1463)."""
    assert set(flow.REFERENCE_DEVICE_MAP) == {"rppd", "rhigh"}
    assert all(
        entry["kind"] == "resistor" for entry in flow.REFERENCE_DEVICE_MAP.values()
    )
    assert "cap_cmomi" not in flow.REFERENCE_DEVICE_MAP
