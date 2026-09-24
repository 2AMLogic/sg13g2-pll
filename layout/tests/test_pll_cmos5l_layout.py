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

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import pll_layout  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CMOS5L_NETLIST_DIR = REPO_ROOT / "design" / "sg13cmos5l" / "netlist"

kdb = pytest.importorskip("klayout.db", reason="needs the pinned klt install")

import cmos5l_devices as dev  # noqa: E402
import cmos5l_floorplan  # noqa: E402
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

    The numbers matter and are checked, and *which* numbers is what moved:
    the recognition half of the gap closed upstream with issue #114/PR #119
    (klayout-tools#1466 merged as #1475 for extraction, #1942/#1944 for the
    reference-side `X ... PARAMS:` card), so the reason now cites those as
    the closed half and names the drawing side -- no `klt gen` generator --
    as the part that is actually left. klayout-tools#1463 was the old
    "extracts no capacitor at all" framing and is deliberately gone with it.
    #1454/#1455 are the SG13G2 MIM chain and must still never appear here:
    the two ports' capacitors are physically different devices with
    separately-tracked histories, and this is the assertion that keeps one
    port's gap from being misattributed to the other.

    This is the *planner's* reason. `pll_cmos5l_layout.promote_local_mom_caps`
    clears it on this flow's own plan (see
    `test_promote_local_mom_caps_promotes_exactly_the_cap_cmomi_groups`), so a
    group still carrying it at the build step means the promotion did not run.
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
        assert "1466" in reason and "1475" in reason
        assert "1455" not in reason and "1454" not in reason
        # the live gap is the drawing side, and the reason says whose job it is
        assert "cap_array" in reason
        assert "promote" in reason


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


# The two tests below replace `test_reference_device_map_covers_the_resistors_
# and_not_the_capacitor` and `test_capacitor_probe_map_is_a_strict_superset_of_
# the_primary_map`, which read `flow.REFERENCE_DEVICE_MAP` /
# `flow.CAPACITOR_PROBE_DEVICE_MAP`. Issue #114/PR #119 retired both constants
# on purpose: the deck's own curated table resolves `rppd`/`rhigh` at this
# pin, so no caller-side resistor map is needed, and the capacitor is no
# longer "left out of the primary run" pending a secondary probe -- it is
# drawn locally and carried into the compare. What is tested here is what
# replaced them: the promotion that puts the capacitor into the primary run,
# and the caller-side reference rewrite that makes it comparable.


def test_promote_local_mom_caps_promotes_exactly_the_cap_cmomi_groups(cmos5l_plan):
    """The capacitor is no longer excluded from the primary run: every
    `cap_cmomi` group is promoted to a locally drawn one, gains the
    `(class, w_um, l_um)` device the marker is expected to extract as, and
    loses its planner `blocked_reason` -- leaving it in place would misreport
    a drawn device as blocked.

    "Exactly" is the other half, and is what the retired strict-superset
    assertion was protecting: the promotion must be the *only* difference
    between the shared plan and this flow's plan. MOS and resistor groups are
    untouched (the deck resolves `rppd`/`rhigh` itself at this pin, which is
    why the old caller-side resistor map went away rather than being renamed).
    """
    plan = copy.deepcopy(cmos5l_plan)
    before = {
        group["id"]: copy.deepcopy(group)
        for block in plan["blocks"]
        for group in block["groups"]
    }

    promoted = flow.promote_local_mom_caps(plan)

    after = {
        group["id"]: group for block in plan["blocks"] for group in block["groups"]
    }
    assert set(after) == set(before), "promotion must not add or drop groups"
    cap_ids = {
        gid
        for gid, group in before.items()
        if group["kind"] == "capacitor" and group["params"]["model"] == "cap_cmomi"
    }
    assert cap_ids, "the CMOS5L netlists do declare cap_cmomi capacitors"
    assert set(promoted) == cap_ids
    # ...and nothing else moved.
    for gid, group in after.items():
        if gid not in cap_ids:
            assert group == before[gid]
            continue
        assert group["generator"] == "local_mom_cap"
        assert "blocked_reason" not in group
        assert group["expected"] == {
            "class": "cap_cmomi",
            "w_um": before[gid]["params"]["w_um"],
            "l_um": before[gid]["params"]["l_um"],
            "count": 1,
        }


def test_mom_cap_reference_rewrites_only_the_capacitor_cards():
    """`mom_cap_reference` is the caller-side rewrite that replaced the
    capacitor probe: it emits the `X <name> <a> <b> cap_cmomi PARAMS: W= L=`
    card shape `klt lvs`'s custom-device-class reader recognises, with W/L in
    **bare-number microns** (a `40u` suffix parses as SI metres and would
    mismatch the extracted marker bbox by 1e6) and `m=` expanded one card per
    drawn marker.

    Everything that is not a `cap_cmomi` card is left to the normalizer's own
    `subckt-call` conversion -- which is the modern form of "differs in
    exactly one thing": the capacitor is the only device this flow has to
    hand-write a card for.
    """
    text = (
        ".subckt probe A B VSS\n"
        "XR1 A B sub! rppd w=0.6u l=810u m=1 b=0\n"
        "XC1 A VSS cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double"
        " subblock=0 m=1 mm_ok=1\n"
        "XC2 B VSS cap_cmomi w=10u l=20u mmin=1 mmax=4 feed=double"
        " subblock=0 m=3 mm_ok=1\n"
        ".ends\n"
    )
    lines = [
        line.strip()
        for line in flow.mom_cap_reference(text).splitlines()
        if line.strip()
    ]

    cap_cards = [line for line in lines if "cap_cmomi" in line]
    assert cap_cards == [
        "XC1 A VSS cap_cmomi PARAMS: W=40 L=40",
        "XC2__0 B VSS cap_cmomi PARAMS: W=10 L=20",
        "XC2__1 B VSS cap_cmomi PARAMS: W=10 L=20",
        "XC2__2 B VSS cap_cmomi PARAMS: W=10 L=20",
    ]
    # The resistor needs no caller-side device map any more: the normalizer
    # converts it to plain-element form and the deck's own sheet-rho fills a
    # real value in, so the compare verifies resistance rather than skipping
    # it on the `0` placeholder.
    resistor = next(line for line in lines if line.startswith("R1 ")).split()
    assert "rppd" in resistor
    value = resistor[resistor.index("rppd") - 1]  # the token right before the class
    assert float(value) > 0
    # The hierarchy itself rides through untouched.
    assert lines[0] == ".subckt probe A B VSS"
    assert lines[-1] == ".ends"


def test_mom_cap_reference_rejects_a_card_it_cannot_carry_faithfully():
    """A cap card with no readable geometry, or a non-positive multiplier,
    must raise rather than silently emit a reference the layout cannot match
    -- a wrong reference reads as an LVS mismatch in the drawn device."""
    with pytest.raises(ValueError):
        flow.mom_cap_reference("XC1 A B cap_cmomi w=40u m=1\n")
    with pytest.raises(ValueError):
        flow.mom_cap_reference("XC1 A B cap_cmomi w=40u l=40u m=0\n")


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


# --- Generator-vs-local footprint probe helpers (issue #35) ----------------
#
# The probes themselves run `klt` and are recorded as evidence, not simulated
# here (same split as everywhere else in this file). What *is* unit-testable
# is the two pure reducers the probe's verdict is computed from -- if either
# is wrong, the record would report a compatible footprint that is not one.


def test_port_column_pitch_finds_the_tightest_pair_not_the_average():
    """The riser-column invariant is decided by the *closest* two columns."""
    ports = [
        {"name": "U0_S", "x_um": 0.21},
        {"name": "U0_G", "x_um": 0.67},
        {"name": "U0_D", "x_um": 1.13},
        {"name": "U1_S", "x_um": 10.0},
    ]
    assert flow._port_column_pitch(ports) == pytest.approx(0.46)


def test_port_column_pitch_ignores_terminals_sharing_one_column():
    """Two ports at the same x are one column, not a zero-width gap: a shared
    column is `check_riser_columns`'s own fatal error, and reporting 0.0 here
    would conflate "too tight" with "identical"."""
    ports = [
        {"name": "R0_A", "x_um": 0.21},
        {"name": "R0_B", "x_um": 0.21},
        {"name": "R1_A", "x_um": 1.11},
    ]
    assert flow._port_column_pitch(ports) == pytest.approx(0.90)
    assert flow._port_column_pitch([{"name": "P", "x_um": 1.0}]) is None


def test_extracted_models_reads_the_pdk_binding_not_the_deck_class(tmp_path):
    """`sg13_hv_*` vs `sg13_lv_*` is the whole generator-vs-local question on
    the MOS side, and it appears only on the emitted `X` cards -- the JSON
    response reports the deck class (`nfet`/`pfet`) for both."""
    (tmp_path / "probe.extracted.spice").write_text(
        "* extracted by klt extract --deck sg13cmos5l\n"
        ".SUBCKT probe vsubs\n"
        "X$1 \\$3 \\$1 \\$4 vsubs sg13_hv_nmos L=0.5U W=2U\n"
        "X$2 \\$5 \\$2 \\$6 vsubs sg13_hv_nmos L=0.5U W=2U\n"
        ".ENDS probe\n"
    )
    assert flow._extracted_models(tmp_path, "probe") == ["sg13_hv_nmos"]
    assert flow._extracted_models(tmp_path, "absent") == []


# --- Locality floorplan pass (issue #101) -----------------------------------
#
# `pll_vco` is composed through a net-affinity floorplan pass before the
# per-net-track router draws it: the group order, the member->unit assignment
# inside every group cell, and the Metal3 track order are chosen to shorten
# the nets the ring topology makes local (ring1..ring5, the per-stage nh/nt
# nets), instead of the type-sorted left-to-right row the other five blocks
# keep.  The three correctness invariants that matter are unit-tested here:
#
# * the pass never invents or drops connectivity -- every group keeps exactly
#   its own members, every member keeps exactly its own nets, and the multiset
#   of per-net pin counts over the whole block is unchanged;
# * the predicted wire length the pass optimises is the *router's* arithmetic
#   (the same collect_terminals -> span + riser sum `route()` draws), so the
#   number the record reports as "predicted" cannot drift from the drawn one;
# * the pass is deterministic -- the same plan, groups and geometries produce
#   the same floorplan and the same track order on every run.


@pytest.fixture(scope="module")
def vco_composed(cmos5l_plan):
    """The plan's vco block with every drawable group drawn once (geometry
    exactly as `build_block` gets it), for floorplan tests to reuse.

    `main()` runs `promote_local_mom_caps` over the plan before it builds any
    block, so the fixture does too -- on a deep copy, because the shared
    `cmos5l_plan` fixture is what the planner-side tests assert the *unpromoted*
    state on. Without it the vco block's `XCDECAP` `cap_cmomi` group still
    carries `generator=None` and would be dispatched to `draw_res_group`,
    which is neither what `build_block` does nor something the capacitor's
    params dict can satisfy.
    """
    plan = copy.deepcopy(cmos5l_plan)
    flow.promote_local_mom_caps(plan)
    block = next(b for b in plan["blocks"] if b["name"] == "vco")
    builder = dev.Builder()
    groups, geometries = [], {}
    for group in block["groups"]:
        # Same two gates `build_block` applies, in the same order.
        if group["kind"] not in flow.DRAWABLE_KINDS or group.get("generator") is None:
            continue
        if group["kind"] == "mos_array":
            geometries[group["id"]] = flow.draw_mos_group(builder, group)
        elif group["kind"] == "capacitor":
            geometries[group["id"]] = flow.draw_cap_group(builder, group)
        else:
            geometries[group["id"]] = flow.draw_res_group(builder, group)
        groups.append(group)
    sizes = [(g["id"], *flow.group_size_um(g)) for g in groups]
    return block, builder, groups, geometries, sizes


def test_only_the_vco_block_uses_the_locality_strategy():
    """The floorplan pass is opted in per block name: `vco` (issue #101)
    reaps it, and every other block keeps the single-row composition its
    committed record and PEX evidence were produced from."""
    assert flow.FLOORPLAN_STRATEGIES == {"vco": "locality"}
    assert flow.DEFAULT_FLOORPLAN_STRATEGY == "single_row"


def test_locality_floorplan_shortens_vco_wire_and_keeps_connectivity(
    vco_composed,
):
    """The pass must measurably reduce total routed wire vs the single_row
    order of the same drawn groups -- including on `ring1`, the net issue
    #101 names -- while conserving every net and pin."""
    block, builder, groups, geometries, sizes = vco_composed
    result = cmos5l_floorplan.locality_floorplan(
        groups,
        geometries,
        sizes,
        flow.GROUP_SPACING_UM,
        collect=flow.collect_terminals,
    )
    assert result["wire_length_um"] < result["baseline_wire_length_um"]
    # Connectivity conservation: same groups, same members per group, same
    # per-net pin multiset over the whole block.
    assert {g["id"] for g in result["ordered_groups"]} == {g["id"] for g in groups}
    for placed in result["ordered_groups"]:
        source = next(g for g in groups if g["id"] == placed["id"])
        assert [m["device"] for m in placed["members"]] == [
            m["device"] for m in source["members"]
        ] or sorted(m["device"] for m in placed["members"]) == sorted(
            m["device"] for m in source["members"]
        )
        # a member keeps its own nets; only the unit slot it occupies moves
        assert sorted(
            tuple(sorted(m["ports"].values())) for m in placed["members"]
        ) == sorted(tuple(sorted(m["ports"].values())) for m in source["members"])

    def pin_counts(ordered, origins):
        terminals, _notes = flow.collect_terminals(
            ordered, geometries, origins
        )
        counts: dict[str, int] = {}
        for terminal in terminals:
            counts[terminal.net] = counts.get(terminal.net, 0) + 1
        return counts

    sizes_ordered = [
        (g["id"], *flow.group_size_um(g)) for g in result["ordered_groups"]
    ]
    assert pin_counts(
        result["ordered_groups"], flow.single_row_pack(sizes_ordered, flow.GROUP_SPACING_UM)
    ) == pin_counts(groups, flow.single_row_pack(sizes, flow.GROUP_SPACING_UM))
    # ring1 -- the net the issue asks to see improve -- must be shorter.
    per_net = dict(result["per_net_wire_length_um"])
    assert per_net["ring1"] < result["baseline_per_net_wire_length_um"]["ring1"]


def test_locality_floorplan_prediction_matches_the_router(vco_composed):
    """The number the pass reports must be the number `route()` draws: same
    terminals, same track order, same span+riser arithmetic -- so the
    record's "predicted" and "drawn" wire lengths can never drift apart."""
    block, builder, groups, geometries, sizes = vco_composed
    result = cmos5l_floorplan.locality_floorplan(
        groups,
        geometries,
        sizes,
        flow.GROUP_SPACING_UM,
        collect=flow.collect_terminals,
    )
    # compose into the fixture's own builder: the group cells that the
    # floorplan order instantiates already live in that layout.
    cell = builder.open_cell("pll_vco_floorplan_probe")
    origins = flow.single_row_pack(
        [(g["id"], *flow.group_size_um(g)) for g in result["ordered_groups"]],
        flow.GROUP_SPACING_UM,
    )
    for placed in result["ordered_groups"]:
        builder.instantiate(
            cell, builder.layout.cell(placed["id"]), origins[placed["id"]]["x"], 0.0
        )
    terminals, _notes = flow.collect_terminals(
        result["ordered_groups"], geometries, origins
    )
    channel_y0 = max(h for _id, _w, h in sizes) + route.CHANNEL_GAP_UM
    drawn = route.route(
        builder, cell, terminals, channel_y0, track_order=result["track_order"]
    )
    assert drawn.wire_length_um == pytest.approx(
        result["wire_length_um"], abs=1e-6
    )

    # And the same for the baseline: composing the identity (single-row,
    # by-name tracks) order of the same groups with no track_order argument
    # -- the pre-#101 flow, live -- must reproduce the pass's
    # baseline_wire_length_um, so the reported baseline is the router's own
    # output rather than a parallel arithmetic that can drift.
    legacy_cell = builder.open_cell("pll_vco_single_row_probe")
    legacy_origins = flow.single_row_pack(
        [(g["id"], *flow.group_size_um(g)) for g in groups], flow.GROUP_SPACING_UM
    )
    for group in groups:
        builder.instantiate(
            legacy_cell,
            builder.layout.cell(group["id"]),
            legacy_origins[group["id"]]["x"],
            0.0,
        )
    legacy_terminals, _legacy_notes = flow.collect_terminals(
        groups, geometries, legacy_origins
    )
    legacy_drawn = route.route(
        builder, legacy_cell, legacy_terminals, channel_y0
    )
    assert legacy_drawn.wire_length_um == pytest.approx(
        result["baseline_wire_length_um"], abs=1e-6
    )


def test_locality_floorplan_track_order_puts_widest_net_lowest(vco_composed):
    """Tracks are assigned by descending drawn-pin count (the rearrangement
    optimum for one-riser-per-pin channel routing), so the supply rails ride
    the lowest -- shortest-riser -- tracks."""
    block, builder, groups, geometries, sizes = vco_composed
    result = cmos5l_floorplan.locality_floorplan(
        groups,
        geometries,
        sizes,
        flow.GROUP_SPACING_UM,
        collect=flow.collect_terminals,
    )
    ordered = list(result["track_order"])
    assert ordered.index("GND_VCO") == 0
    assert ordered.index("VDD_VCO") == 1
    # descending pin count, name as the deterministic tie-break
    counts = result["per_net_pin_count"]
    pairs = [(-counts[n], n) for n in ordered]
    assert pairs == sorted(pairs)


def test_locality_floorplan_is_deterministic(vco_composed):
    """Same plan, same groups, same geometries: byte-identical floorplan."""
    block, builder, groups, geometries, sizes = vco_composed
    one = cmos5l_floorplan.locality_floorplan(
        groups, geometries, sizes, flow.GROUP_SPACING_UM,
        collect=flow.collect_terminals,
    )
    two = cmos5l_floorplan.locality_floorplan(
        groups, geometries, sizes, flow.GROUP_SPACING_UM,
        collect=flow.collect_terminals,
    )
    assert one["group_order"] == two["group_order"]
    assert one["track_order"] == two["track_order"]
    assert one["wire_length_um"] == two["wire_length_um"]
    assert one["member_slots"] == two["member_slots"]


def test_locality_floorplan_never_worsens_a_single_group_block(vco_composed):
    """On a block of one group the pass has no choices to make: it must
    return the identity order, the identity member assignment and the
    by-name track order's own cost, never a worse arrangement."""
    block, builder, groups, geometries, sizes = vco_composed
    only = groups[:1]
    result = cmos5l_floorplan.locality_floorplan(
        only,
        {groups[0]["id"]: geometries[groups[0]["id"]]},
        sizes[:1],
        flow.GROUP_SPACING_UM,
        collect=flow.collect_terminals,
    )
    assert result["group_order"] == [groups[0]["id"]]
    assert result["member_slots"][groups[0]["id"]] == [
        m["device"] for m in groups[0]["members"]
    ]
    assert result["wire_length_um"] <= result["baseline_wire_length_um"]


def test_route_honours_an_explicit_track_order():
    """`route()` keeps its by-name track assignment for every existing
    caller, and draws a caller-supplied net -> track order when given one."""
    builder = dev.Builder()
    cell = builder.open_cell("track_order_probe")
    terminals = [
        route.Terminal(net="B", x_um=1.0, y_um=0.0, label="t.B"),
        route.Terminal(net="B", x_um=3.0, y_um=0.0, label="t.B2"),
        route.Terminal(net="A", x_um=5.0, y_um=0.0, label="t.A"),
    ]
    by_name = route.route(builder, cell, terminals, 10.0)
    assert [n["track"] for n in by_name.nets] == [0, 1]  # A then B
    assert "track_order_source" not in by_name.as_dict()

    builder_two = dev.Builder()
    cell_two = builder_two.open_cell("track_order_probe_two")
    custom = route.route(
        builder_two, cell_two, list(terminals), 10.0, track_order=["B", "A"]
    )
    tracks = {n["net"]: n["track"] for n in custom.as_dict()["nets"]}
    assert tracks == {"B": 0, "A": 1}
    assert custom.as_dict()["track_order_source"] == "floorplan"


def test_route_rejects_a_track_order_that_disagrees_with_the_terminals():
    """A track order naming a net the terminals don't carry (or missing one
    they do) is a caller bug: fail loudly, never silently re-sort."""
    builder = dev.Builder()
    cell = builder.open_cell("track_order_bad_probe")
    terminals = [
        route.Terminal(net="A", x_um=1.0, y_um=0.0, label="t.A"),
        route.Terminal(net="B", x_um=2.0, y_um=0.0, label="t.B"),
    ]
    with pytest.raises(route.RouteError):
        route.route(
            builder, cell, list(terminals), 10.0, track_order=["A", "B", "ghosts"]
        )
    with pytest.raises(route.RouteError):
        route.route(builder, cell, list(terminals), 10.0, track_order=["A"])
