#!/usr/bin/env python3
"""Net-affinity floorplan pass for one composed block (issue #101).

**Why this module exists.** `cmos5l_route.py`'s per-net-track channel router
is correct by construction -- risers never share a column, trunks never share
a track -- but its *cost* is set almost entirely by the floorplan it is handed.
The single-row pack this flow has used since issue #29 places matched device
groups in type-sorted order, which scatters one logical structure across the
whole row: on ``vco``, the five ring stages share device *types* with each
other and with the buffer, so every stage's devices land in four different
type-group cells spread across the block, and the nets that only connect
neighbours (``ring1``..``ring5``, the per-stage ``nh``/``nt`` nets) run 60-290
um to do a job a few microns of wire could.  RECORD-001
(``sim/sg13cmos5l-postlayout-pex-pvt``) measured the consequence this pass
exists to shrink: 7 178 um of routed wire on a 45-device block, ~99% of whose
~2x frequency loss is parasitic *capacitance*.

**What this pass changes, and what it refuses to change.** It permutes three
things and nothing else:

1. the **left-to-right order of the group cells** on the row,
2. which **member device occupies which unit slot inside each matched group
   cell** (a matched array draws every unit identically, so a member
   permutation is a relabelling of the port->net map, not a geometry change),
3. the **Metal3 track order** the router assigns nets (handed to
   :func:`cmos5l_route.route` as ``track_order``).

It never adds, removes, splits or merges a net; never touches a device's
W/L/flavour/count; never changes a group cell's drawn geometry; never
introduces a second row (the router's straight-up-to-the-channel scheme
cannot reach a second row); never changes any inter-group spacing.  The
router's structural-correctness invariants are therefore untouched: the
terminal set -- one riser column per terminal, unique by construction -- is
exactly the set the single-row pack would produce, in the same y band, only
at different x.

**The cost model is the router's own arithmetic, re-derived, not
approximated.** For a net with drawn terminals at ``(x_i, y_i)`` on track
``k`` above channel base ``y0``, :func:`cmos5l_route.route` draws

* one riser per terminal: ``y0 + k*pitch - y_i`` of Metal2, and
* one trunk segment spanning the net's leftmost to rightmost riser:

so the model here sums exactly those two terms over the same terminals that
``collect_terminals`` produces from the same ``groups[].members[].ports``
map -- and the unit test pins the model to the router by running both on the
same block and asserting the sums agree to 1e-6.  Two baselines are reported,
both derived from these same drawn groups rather than quoted from a prior
record, so the reduction the pass claims is self-contained:

* ``baseline_wire_length_um`` -- the identity (plan-order) placement with the
  **by-name** track order every pre-#101 composition assigned: exactly what
  the prior flow would have drawn, directly comparable to a committed
  record's own ``routing.wire_length_um``.
* ``single_row_optimal_tracks_wire_length_um`` -- the identity placement with
  the pin-count track order: what the *track axis alone* is worth, so the
  record can state how much of the reduction came from each axis.

**Track order is closed-form, placement order is searched.** The two axes
are independent: a net's riser term depends only on its track index and its
terminals' y; its span term depends only on its terminals' x.  For the track
axis the total cost is ``sum(net) p_net * (y0 + k_net*pitch)``, which the
rearrangement inequality minimises exactly by assigning tracks in descending
drawn-pin order (name as the deterministic tie-break) -- the supply rails,
with the most terminals, ride the lowest, shortest-riser tracks instead of
tracks 8 and 23 as the alphabetical assignment gave them.

For the placement axis no closed form exists (it is a quadratic assignment
problem on the nets' terminal spreads), so the pass runs a deterministic
first-improvement descent over two move families on each axis --

* group swaps and group reinsertions, and
* the same two moves applied to the member->slot permutation inside each
  group,

-- scanning moves in a fixed lexicographic order and repeating passes until
one full pass adopts no move or ``MAX_PASSES`` is hit.  First-improvement
with a fixed scan order is fully deterministic: the same plan, the same
drawn groups and the same geometries always reach the same floorplan, which
the unit test asserts by running the pass twice.  It is a local optimum, not
a global one, and the module says so rather than claiming optimality.

**Ring circles do not fit a straight line, and the pass does not pretend they
do.** A five-stage ring has five stage-to-stage adjacencies and one of them
wraps; a linear row can make at most four of them cell-adjacent.  The descent
knows nothing about "the ring" -- it only sees net spread -- but on this
block it discovers the same trick a hand floorplan would: rotate the member
order inside two of the stage groups so the wrap edge lands where the buffer
is, keeping every ring net's span inside the stage cluster instead of across
the block.  The result on ``vco`` is ~45% less wire in total and ~69% less on
``ring1`` (see the module section in the committed record's compose JSON or
``RECORD-002``); a *representative* analog floorplan it is not -- no
common-centroid matching, no supply grid, no folding -- and no claim in this
module should be read as one.  What it measurably is: the same circuit, DRC
clean, extracted and LVS-compared identically, on materially less wire.

Scope: applied per block by name (``pll_cmos5l_layout.FLOORPLAN_STRATEGIES``);
every block not named there keeps byte-for-byte the single-row composition
and by-name track assignment that its committed record and PEX netlist were
produced from.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Sequence

import cmos5l_devices as dev
import cmos5l_route as route

#: Descent pass cap. The vco block converges in a handful of passes; the cap
#: exists so a pathological block cannot loop forever, not because any known
#: block needs more than a few.
MAX_PASSES = 64

#: Floating-point improvement threshold (um). Anything smaller is rounding
#: noise, and adopting it would make the pass order sensitive to last-bit
#: jitter that carries no physical meaning.
IMPROVEMENT_EPS_UM = 1e-9

#: Terminal-kind prefix of a member port key: ``U<d>_S`` (MOS) and
#: ``R<d>_A``/``R<d>_B``/``R<d>_BULK`` (poly resistor), as
#: ``pll_layout.plan_block`` writes them and ``collect_terminals``/the drawing
#: halves consume them.
_PORT_KEY_RE = re.compile(r"^([UR])(\d+)_(.+)$")

#: What :func:`locality_floorplan` returns to its caller and to the committed
#: compose JSON. ``ordered_groups`` carries relabelled member copies in
#: floorplan order; every other key is reporting.
#
# (Annotation lives here because the recursive dict type is painful inline.)
FloorplanResult = dict[str, Any]

#: ``collect_terminals``-shaped callback: (ordered_groups, geometries,
#: origins) -> (terminals, notes).  Passed in by the caller (rather than
#: imported from ``pll_cmos5l_layout``) so this module cannot import the
#: module that drives it -- the dependency stays one-directional, matching
#: how ``cmos5l_route`` is wired.
CollectFn = Callable[
    [Sequence[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, float]]],
    tuple[list[Any], list[dict[str, Any]]],
]


def _rekey_port(port: str, slot: int) -> str:
    """Rewrite a member port key's unit index, keeping its suffix.

    ``U2_D`` at slot 0 becomes ``U0_D``; ``R1_BULK`` becomes ``R0_BULK``.
    A key that does not match the plan's own ``[UR]<n>_<suffix>`` convention
    is a caller-side (plan-format) bug and fails loudly rather than being
    silently re-labelled -- a mis-keyed port would strand a net pin.
    """
    match = _PORT_KEY_RE.match(port)
    if match is None:
        raise route.RouteError(f"unparseable member port key {port!r}")
    kind, _unit, suffix = match.groups()
    return f"{kind}{slot}_{suffix}"


def _relabeled_copy(group: dict[str, Any], perm: list[int]) -> dict[str, Any]:
    """A shallow copy of ``group`` whose members occupy ``perm``'s unit slots.

    ``perm[slot] = <index into group["members"]>``, so ``perm`` reads as
    "the member now drawn at unit slot ``slot``".  The identity permutation
    returns the group itself, un-copied -- relabelling is a no-op there and
    the record's group JSON then stays the plan's own object.
    """
    members = group["members"]
    if perm == list(range(len(members))):
        return group
    placed: list[dict[str, Any]] = []
    for slot, member_index in enumerate(perm):
        source = members[member_index]
        placed.append(
            {
                "device": source["device"],
                "unit": slot,
                "ports": {
                    _rekey_port(port, slot): net
                    for port, net in source["ports"].items()
                },
            }
        )
    placed_group = dict(group)
    placed_group["members"] = placed
    return placed_group


def _track_order_by_pin_count(terminals: Sequence[Any]) -> list[str]:
    """Nets in descending drawn-pin-count order, name as tie-break.

    The exact rearrangement optimum for the router's per-pin riser term
    (see the module docstring): the net with the most terminals rides the
    lowest, shortest-riser track.
    """
    counts: dict[str, int] = {}
    for terminal in terminals:
        counts[terminal.net] = counts.get(terminal.net, 0) + 1
    return sorted(counts, key=lambda net: (-counts[net], net))


def _wire_cost(
    channel_y0_um: float,
    terminals: Sequence[Any],
    track_order: list[str],
) -> tuple[float, dict[str, float]]:
    """The router's own span + riser arithmetic over drawn terminals, with
    the tracks assigned in ``track_order``.

    The descent always hands this the pin-count optimum
    (:func:`_track_order_by_pin_count`), so the cost it minimises and the
    cost it reports are the same function.  The baseline evaluation hands it
    the by-name order instead -- :func:`cmos5l_route.route`'s assignment for
    every pre-#101 caller -- so ``baseline_wire_length_um`` is what the
    prior flow would have drawn from these same groups, byte-comparable to
    the committed record's own ``routing.wire_length_um``.  See the module
    docstring for why this arithmetic must not drift from
    :func:`cmos5l_route.route`.
    """
    by_net: dict[str, list[Any]] = {}
    for terminal in terminals:
        by_net.setdefault(terminal.net, []).append(terminal)

    track_index = {net: index for index, net in enumerate(track_order)}

    total = 0.0
    per_net: dict[str, float] = {}
    for net, pins in by_net.items():
        trunk_y = channel_y0_um + track_index[net] * dev.ROUTE_PITCH_UM
        span = max(p.x_um for p in pins) - min(p.x_um for p in pins)
        risers = sum(trunk_y - p.y_um for p in pins)
        per_net[net] = span + risers
        total += per_net[net]
    return total, per_net


def locality_floorplan(
    drawn_groups: Sequence[dict[str, Any]],
    geometries: dict[str, dict[str, Any]],
    sizes: Sequence[tuple[str, float, float]],
    spacing_um: float,
    collect: CollectFn,
    max_pin_count: int = 4096,
) -> FloorplanResult:
    """Floorplan one block's drawn groups for the channel router.

    Args:
        drawn_groups: the block's drawable groups in plan order (the same
            list ``build_block`` would hand ``single_row_pack``).
        geometries: per-group drawing geometry, exactly as ``draw_mos_group``
            / ``draw_res_group`` returned it -- the source of every terminal
            coordinate, so the model can never disagree with the drawing.
        sizes: ``(group_id, width_um, height_um)`` per drawn group, in the
            same length as ``drawn_groups`` (the caller already computes
            these for the packer).
        spacing_um: inter-group spacing on the row (the caller's
            ``GROUP_SPACING_UM``); held constant through the search.
        collect: ``collect_terminals`` itself, passed by the caller so the
            pass and the real composition use one terminal-derivation path.
        max_pin_count: descent guard, never reached on this design: refuse to
            search a block whose terminal count is absurd rather than spend
            unbounded time in the move loop.

    Returns a dict (never a claim about DRC/LVS -- those stay ``klt``'s):

    * ``strategy``: ``"locality"``.
    * ``group_order``: placed group ids, left to right.
    * ``ordered_groups``: group objects in the same order; every group whose
      member->slot assignment changed is a shallow copy with relabelled
      member ports, otherwise the plan's own group object.
    * ``member_slots``: group id -> the member device names in slot order
      (the audit trail for the relabelling).
    * ``track_order``: net names in assigned Metal3 track order, handable
      straight to :func:`cmos5l_route.route`.
    * ``per_net_pin_count``: drawn terminals per net (placement-invariant;
      reported so the record can show rails got the low tracks).
    * ``baseline_wire_length_um`` / ``baseline_per_net_wire_length_um``:
      what the pre-101 flow would have drawn from these same groups --
      identity placement, by-name tracks (the router's default).
    * ``single_row_optimal_tracks_wire_length_um``: identity placement with
      the pin-count track order -- the track axis's contribution alone.
    * ``wire_length_um`` / ``per_net_wire_length_um``: the final cost.
    * ``passes``: descent passes actually run.
    """
    if len(drawn_groups) != len(sizes):
        raise route.RouteError(
            f"floorplan: {len(drawn_groups)} groups but {len(sizes)} sizes"
        )
    total_pins = sum(len(g["members"]) * 5 for g in drawn_groups)
    if total_pins > max_pin_count:
        raise route.RouteError(
            f"floorplan: ~{total_pins} terminals exceeds the {max_pin_count} "
            "descent guard; raise the guard deliberately, not silently"
        )

    group_count = len(drawn_groups)
    widths = {gid: width for gid, width, _height in sizes}
    heights = [height for _gid, _width, height in sizes]
    channel_y0 = max(heights) + route.CHANNEL_GAP_UM

    order = list(range(group_count))  # index into drawn_groups, left to right
    perms = {
        group["id"]: list(range(len(group["members"])))
        for group in drawn_groups
    }

    def evaluate(order: list[int], perms: dict[str, list[int]]):
        # The descent reaches for the caller's own collect() on every
        # evaluation, so the cost model and the real terminal derivation can
        # never be two implementations.
        ordered = [
            _relabeled_copy(drawn_groups[g], perms[drawn_groups[g]["id"]])
            for g in order
        ]
        origins: dict[str, dict[str, float]] = {}
        x = 0.0
        for group in ordered:
            gid = group["id"]
            origins[gid] = {"x": round(x, 4), "y": 0.0}
            x += widths[gid] + spacing_um
        terminals, _notes = collect(ordered, geometries, origins)
        total, per_net = _wire_cost(
            channel_y0, terminals, _track_order_by_pin_count(terminals)
        )
        pins: dict[str, int] = {}
        for terminal in terminals:
            pins[terminal.net] = pins.get(terminal.net, 0) + 1
        return total, per_net, pins, ordered, terminals

    def cost_of(order: list[int], perms: dict[str, list[int]]) -> float:
        return evaluate(order, perms)[0]

    (
        best_total,
        best_per_net,
        pin_counts,
        best_ordered,
        identity_terminals,
    ) = evaluate(order, perms)
    # The decomposition the record reports, evaluated once up front:
    #
    # * ``single_row_optimal_tracks`` -- the identity (plan-order) placement
    #   with the pin-count track order: what the *track axis alone* is worth.
    # * ``baseline`` -- the identity placement with the by-name track order
    #   the prior flow assigned: exactly what the pre-#101 composition of
    #   these same drawn groups would draw, comparable to the committed
    #   record's own routing.wire_length_um.
    identity_optimal_tracks_total, _ = _wire_cost(
        channel_y0, identity_terminals, _track_order_by_pin_count(identity_terminals)
    )
    identity_nets = {terminal.net for terminal in identity_terminals}
    baseline_total, baseline_per_net = _wire_cost(
        channel_y0, identity_terminals, sorted(identity_nets)
    )

    passes = 0
    while passes < MAX_PASSES:
        improved = False
        passes += 1

        # -- group swaps, lexicographic first-improvement ------------------ #
        for i in range(group_count - 1):
            for j in range(i + 1, group_count):
                candidate = list(order)
                candidate[i], candidate[j] = candidate[j], candidate[i]
                total = cost_of(candidate, perms)
                if total < best_total - IMPROVEMENT_EPS_UM:
                    order, best_total = candidate, total

                    improved = True

        # -- group reinsertions (remove one, insert elsewhere) ------------- #
        for i in range(group_count):
            for j in range(group_count):
                if i == j:
                    continue
                candidate = list(order)
                gid = candidate.pop(i)
                candidate.insert(j, gid)
                total = cost_of(candidate, perms)
                if total < best_total - IMPROVEMENT_EPS_UM:
                    order, best_total = candidate, total

                    improved = True

        # -- member swaps + reinsertions, groups in placement order -------- #
        for position in range(group_count):
            gid = drawn_groups[order[position]]["id"]
            member_count = len(perms[gid])
            for i in range(member_count - 1):
                for j in range(i + 1, member_count):
                    candidate = {
                        key: list(value) for key, value in perms.items()
                    }
                    candidate[gid][i], candidate[gid][j] = (
                        candidate[gid][j],
                        candidate[gid][i],
                    )
                    total = cost_of(order, candidate)
                    if total < best_total - IMPROVEMENT_EPS_UM:
                        perms, best_total = candidate, total

                        improved = True
            for i in range(member_count):
                for j in range(member_count):
                    if i == j:
                        continue
                    candidate = {
                        key: list(value) for key, value in perms.items()
                    }
                    moved = candidate[gid].pop(i)
                    candidate[gid].insert(j, moved)
                    total = cost_of(order, candidate)
                    if total < best_total - IMPROVEMENT_EPS_UM:
                        perms, best_total = candidate, total

                        improved = True
        if not improved:
            break

    best_total, best_per_net, pin_counts, best_ordered, _final = evaluate(
        order, perms
    )
    track_order = sorted(pin_counts, key=lambda net: (-pin_counts[net], net))

    return {
        "strategy": "locality",
        "group_order": [drawn_groups[g]["id"] for g in order],
        "ordered_groups": best_ordered,
        "member_slots": {
            group["id"]: [m["device"] for m in group["members"]]
            for group in best_ordered
        },
        "track_order": track_order,
        "per_net_pin_count": dict(sorted(pin_counts.items())),
        "baseline_wire_length_um": round(baseline_total, 3),
        "baseline_per_net_wire_length_um": {
            net: round(length, 3) for net, length in sorted(baseline_per_net.items())
        },
        "single_row_optimal_tracks_wire_length_um": round(
            identity_optimal_tracks_total, 3
        ),
        "wire_length_um": round(best_total, 3),
        "per_net_wire_length_um": {
            net: round(length, 3) for net, length in sorted(best_per_net.items())
        },
        "passes": passes,
    }
