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
import cmos5l_route as route  # noqa: E402
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
    SG13G2 side's MIM gap -- it carries its own tracked upstream issues.

    The numbers matter and are checked: klayout-tools#1463 (the deck
    recognises no capacitor) and #1466 (what device-recognition shape a MoM
    plate pair needs) are the two that are still **open**. #1454/#1455 are the
    SG13G2 MIM chain and must never appear here. #1462 closed 2026-08-30, so
    it may only appear as history, never as the live reason -- which is why
    this asserts on the two open numbers rather than on #1462.
    """
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
        assert "1463" in reason and "1466" in reason
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


def test_mos_margin_covers_every_marker_each_flavour_actually_draws():
    """The packer sizes groups from `mos_margins`, so it must bound the widest
    thing each flavour hangs off its active box -- the PFET's own `pSD` reach
    past the gate endcap (`Gat_c + pSD_i1`), and, since issue #29 added a
    contacted gate, the `GatPoly` landing pad (`Gat_c + GATE_PAD_W_UM`) on
    both. The pad is currently the binding constraint on both flavours, which
    is why this checks coverage rather than a pfet-wider-than-nfet ordering.
    """
    gate_pad_reach = dev.GAT_C + dev.GATE_PAD_W_UM
    assert dev.mos_margins("pfet")[0] >= max(
        dev.PSD_C, dev.GAT_C + dev.PSD_I1, gate_pad_reach
    )
    assert dev.mos_margins("nfet")[0] >= max(dev.TGO_A, gate_pad_reach)


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
    count = params.pop("count")
    body_net = params.pop("body_net", None)
    base: dict = {"id": "g", "kind": kind, "count": count, "params": params}
    if kind == "mos_array":
        base["members"] = [
            {
                "device": f"X{index}",
                "unit": index,
                "ports": {
                    f"U{index}_D": f"d{index}",
                    f"U{index}_G": f"g{index}",
                    f"U{index}_S": f"s{index}",
                    f"U{index}_B": body_net or "VSS",
                },
            }
            for index in range(count)
        ]
    else:
        base["members"] = [
            {
                "device": f"R{index}",
                "unit": index,
                "ports": {
                    f"R{index}_A": f"a{index}",
                    f"R{index}_B": f"b{index}",
                    f"R{index}_BULK": "sub!",
                },
            }
            for index in range(count)
        ]
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
    label is what keeps `klt extract` from reporting `unbiased_pmos_body_nets`.

    Since issue #29 the label is the *schematic's* own body net, not an
    invented `<group>_B`: an NWell named after the group extracts as a net the
    reference netlist has never heard of, which is a mismatch this flow would
    have manufactured itself.
    """
    builder = dev.Builder()
    group = _group(
        "mos_array",
        count=4,
        flavor="pfet",
        w_um=5.0,
        l_um=0.5,
        rows=1,
        cols=4,
        body_net="VDD",
    )
    geometry = flow.draw_mos_group(builder, group)
    cell = builder.layout.cell("g")
    assert cell.shapes(builder.layout.layer(*dev.L_NWELL)).size() == 1
    assert cell.shapes(builder.layout.layer(*dev.L_NWELL_PIN)).size() == 1
    assert geometry["body_tie"]["kind"] == "nwell_tap"
    assert geometry["body_tie"]["net"] == "VDD"


def test_group_body_net_refuses_to_pick_when_members_disagree():
    """A group whose devices tie their bodies to two different nets cannot be
    given one well label; returning `None` is what surfaces that rather than
    silently naming the well after whichever member sorted first."""
    group = _group("mos_array", count=2, flavor="pfet", w_um=5.0, l_um=0.5)
    group["members"][1]["ports"]["U1_B"] = "VDD_OTHER"
    assert flow.group_body_net(group) is None


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
    the MoM capacitor is deliberately left out of the **primary** run, because
    the deck extracts no capacitor at all (klayout-tools#1463) and a layout
    that cannot carry the device cannot match a reference that declares it."""
    assert set(flow.REFERENCE_DEVICE_MAP) == {"rppd", "rhigh"}
    assert all(
        entry["kind"] == "resistor" for entry in flow.REFERENCE_DEVICE_MAP.values()
    )
    assert "cap_cmomi" not in flow.REFERENCE_DEVICE_MAP


def test_capacitor_probe_map_is_a_strict_superset_of_the_primary_map():
    """The secondary probe must differ from the primary run in exactly one
    thing -- the capacitor entry -- or the two results are not comparable and
    the probe stops being evidence about #1463 specifically."""
    assert flow.CAPACITOR_PROBE_DEVICE_MAP["cap_cmomi"]["kind"] == "capacitor"
    assert (
        set(flow.CAPACITOR_PROBE_DEVICE_MAP) - set(flow.REFERENCE_DEVICE_MAP)
        == {"cap_cmomi"}
    )
    assert all(
        flow.CAPACITOR_PROBE_DEVICE_MAP[key] == value
        for key, value in flow.REFERENCE_DEVICE_MAP.items()
    )


# --- Routing ----------------------------------------------------------------


def test_every_mos_terminal_including_the_gate_is_routable():
    """A gate with no Metal1 landing has nowhere for a Via1 to drop, which is
    why `draw_hv_mos` grew a gate pad for issue #29."""
    builder = dev.Builder()
    group = _group("mos_array", count=3, flavor="nfet", w_um=2.0, l_um=0.5)
    geometry = flow.draw_mos_group(builder, group)
    assert set(geometry["terminals"]) == {
        f"U{i}_{t}" for i in range(3) for t in ("S", "G", "D")
    }
    assert geometry["tie_point"]


def test_riser_columns_are_pitch_apart_within_and_across_unit_devices():
    """The router's whole no-short claim rests on this: no two terminals of
    different nets may share (or crowd) a Metal2 riser column."""
    builder = dev.Builder()
    group = _group("mos_array", count=4, flavor="nfet", w_um=2.0, l_um=0.5)
    geometry = flow.draw_mos_group(builder, group)
    columns = sorted(x for x, _y in geometry["terminals"].values())
    columns.append(geometry["tie_point"][0])
    columns.sort()
    gaps = [b - a for a, b in zip(columns, columns[1:])]
    assert min(gaps) >= dev.ROUTE_PITCH_UM - 1e-9


def test_stacked_resistor_bars_do_not_share_a_riser_column():
    """Two bars stacked in y at the same x would put two different nets'
    end pads in one column; `RES_STAGGER_UM` is what separates them."""
    builder = dev.Builder()
    group = _group("res_array", count=3, flavor="rppd", width_um=1.0, length_um=30.0)
    geometry = flow.draw_res_group(builder, group)
    columns = sorted(x for x, _y in geometry["terminals"].values())
    gaps = [b - a for a, b in zip(columns, columns[1:])]
    assert min(gaps) >= dev.ROUTE_PITCH_UM - 1e-9


def test_check_riser_columns_rejects_a_shared_column():
    """The invariant is enforced, not merely intended: two different nets in
    one column is a fatal error, never a quietly-dropped net."""
    terminals = [
        route.Terminal(net="A", x_um=1.0, y_um=0.0, label="g.U0_D"),
        route.Terminal(net="B", x_um=1.05, y_um=0.0, label="g.U1_D"),
    ]
    with pytest.raises(route.RouteError):
        route.check_riser_columns(terminals)
    # ...but two terminals of the *same* net may share one, since merging them
    # is exactly what the net wants.
    same = [
        route.Terminal(net="A", x_um=1.0, y_um=0.0, label="g.U0_D"),
        route.Terminal(net="A", x_um=1.05, y_um=0.0, label="g.U1_D"),
    ]
    route.check_riser_columns(same)


def test_route_wire_width_can_actually_carry_a_via2():
    """`ROUTE_W_UM` is set by the via enclosure rule, not by the metal width
    floor -- a wire at `metal2.width.1` (0.20 um) cannot hold a Via2."""
    assert dev.ROUTE_W_UM >= dev.VIA2_SIZE_UM + 2 * dev.M2_ENC_VIA2_UM
    assert dev.ROUTE_PITCH_UM >= dev.ROUTE_W_UM + max(dev.M2_SPACE_UM, dev.M3_SPACE_UM)


def test_routed_nets_come_from_the_plans_own_port_map(cmos5l_plan):
    """No net in the routed layout is typed in: every one is a net the
    schematic-derived plan already names for that block."""
    block = next(b for b in cmos5l_plan["blocks"] if b["name"] == "cp")
    builder = dev.Builder()
    groups, geometries = [], {}
    for group in block["groups"]:
        if group["kind"] not in flow.DRAWABLE_KINDS:
            continue
        geometries[group["id"]] = flow.draw_mos_group(builder, group)
        groups.append(group)
    sizes = [(g["id"], *flow.group_size_um(g)) for g in groups]
    origins = flow.single_row_pack(sizes, flow.GROUP_SPACING_UM)
    terminals, notes = flow.collect_terminals(groups, geometries, origins)
    assert not notes  # cp is MOS-only: no resistor bulk to leave unrouted

    planned = {
        net
        for group in block["groups"]
        for member in group["members"]
        for net in member["ports"].values()
    }
    assert {t.net for t in terminals} == planned
    route.check_riser_columns(terminals)


def test_single_row_pack_never_stacks_two_groups_in_y():
    """A shelf pack would put a lower group's risers underneath an upper
    group; the router's straight-up-to-the-channel scheme cannot do that."""
    origins = flow.single_row_pack(
        [("a", 10.0, 4.0), ("b", 20.0, 9.0), ("c", 5.0, 2.0)], 6.0
    )
    assert [o["y"] for o in origins.values()] == [0.0, 0.0, 0.0]
    assert origins["b"]["x"] == pytest.approx(16.0)
    assert origins["c"]["x"] == pytest.approx(42.0)
