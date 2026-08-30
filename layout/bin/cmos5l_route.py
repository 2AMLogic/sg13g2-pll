#!/usr/bin/env python3
"""Channel router for the SG13CMOS5L PLL blocks (issue #29).

**Why this exists rather than `klt gen-compose --routing`.** `klt gen-compose`
does have a router, and this repo's SG13G2 flow already drives that verb for
placement. Two separate, both-measured reasons it is not used here:

1. **At this repo's pinned `klt` build it cannot route on this PDK at all.**
   Routing resolves `routing.layer_role` through the *same* per-PDK-family
   role->layer table (`gen._PDK_ROLE_LAYERS`) every `klt gen` generator
   resolves its device layers through, and at the pin that table has no
   `sg13cmos5l` entry. Placement-only composition succeeds on
   `ihp-sg13cmos5l`; adding a `routing` block to the same request fails with
   ``PDK variant 'ihp-sg13cmos5l' is not supported by this generator``. That
   is the gap **klayout-tools#1462** tracked -- and it **closed upstream
   2026-08-30T04:31Z**, after this repo's pin. Both transcripts are re-taken
   on every run (:func:`pll_cmos5l_layout.probe_gen_compose_router`) and
   committed as `gen-compose.probe.*.json`, so the day the pin moves past
   #1462 the record says so by itself rather than by anyone remembering to
   re-check.

2. **Past that fix it still cannot route a block this size** -- which is why
   the pin moving does not retire this module. Measured directly against
   `klt`, with this flow's own placed groups, declared ports and
   schematic-derived `connectivity[]`: on `cp`, the *smallest* block here (8
   groups, 14 devices, 13 multi-pin nets), `klt gen-compose` routes **1 of 13
   nets** and rejects the other twelve, essentially all with
   ``crosses already-routed net 'DN'``. Its router has no track or layer
   assignment between nets, so the first net accepted rejects the rest
   regardless of how much empty space the composition has. Filed upstream as
   **klayout-tools#1467**.

   First measured at `b10fa3c` (#1462's own merge commit) and, since issue
   #35, **re-measured on every run** rather than remembered:
   :func:`pll_cmos5l_layout.probe_gen_compose_block_routing` rebuilds exactly
   that request from this run's own drawn groups and commits the raw
   responses as `gen-compose.probe.block-*.json`. It reproduces unchanged at
   the current pin. The same probe also asks for
   ``routing.cross_block_layer_role`` -- the one mechanism `gen-compose` has
   for moving a rejected net onto a different metal -- and this PDK family
   has no second routing metal role to name (the role table exposes exactly
   one, ``metal``), so that escape is unavailable here too.

So this module draws the interconnect the same way `cmos5l_devices.py` draws
the devices -- locally, with `klayout.db` -- and leaves the whole verification
half (`klt drc`, `klt extract`, `klt lvs`) to `klt` against the curated deck,
unmodified. Both tool gaps stay filed upstream either way.

**The routing style, and why it is this one.** A per-net-track channel router:

* Every device terminal is brought up on its own vertical **Metal2 riser**,
  at its own x column. Columns are unique by construction (each unit device
  contributes a gate, source and drain column at fixed offsets inside its own
  footprint, and every group is placed in one left-to-right row), so two
  risers can never occupy the same x.
* Every net gets one horizontal **Metal3 trunk** on its own y track, in a
  channel above the whole block. A trunk spans its own net's leftmost to
  rightmost riser and drops a `Via2` onto each.
* Net names are written on the trunk, on `Metal3.pin` (30/2) -- the layer the
  curated deck's `EXTRACTION_DECK.metal_labels` actually reads.

That is not a good floorplan and does not pretend to be one: it is the
routing style whose *correctness* is structural rather than searched. Risers
never share a column, trunks never share a track, and the only riser/trunk
crossings are between different layers, so the router cannot draw a short --
which is the property that makes an LVS result off it mean something. Wire
length is bad and the channel is tall; both are floorplan problems, and the
block README says so rather than this module claiming otherwise.

Nothing here decides *what* connects to what. Every net and every terminal's
net membership comes from the plan's own `groups[].members[].ports` map,
which `pll_layout.build_plan` derives from the committed schematic netlist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cmos5l_devices as dev

#: Vertical gap between the tallest placed group and the first Metal3 track
#: (um). Large enough that a trunk never sits over a group's own top edge,
#: where a riser has not yet reached full height.
CHANNEL_GAP_UM = 2.0


@dataclass(frozen=True)
class Terminal:
    """One routable point: a `Via1` landing on a device's own Metal1 pad."""

    net: str
    x_um: float
    y_um: float
    #: `<group id>.<port>` -- e.g. `cp_nfet_w2_l0p5.U0_D`. Traceability only.
    label: str


@dataclass
class RouteResult:
    """What the router actually drew, reported per net."""

    nets: list[dict[str, Any]] = field(default_factory=list)
    channel_y0_um: float = 0.0
    track_pitch_um: float = dev.ROUTE_PITCH_UM
    wire_length_um: float = 0.0
    #: Nets the *plan* declares whose terminal set the layout cannot supply in
    #: full -- always because some device on the net was never drawn. Each
    #: entry names the missing ports and why, never a bare count.
    incomplete_nets: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "style": "per-net Metal3 track over per-terminal Metal2 risers",
            "riser_layer": "Metal2.drawing (10/0)",
            "trunk_layer": "Metal3.drawing (30/0)",
            "label_layer": "Metal3.pin (30/2)",
            "wire_width_um": dev.ROUTE_W_UM,
            "track_pitch_um": self.track_pitch_um,
            "channel_y0_um": round(self.channel_y0_um, 4),
            "net_count": len(self.nets),
            "routed_net_count": sum(1 for n in self.nets if n["routed"]),
            "wire_length_um": round(self.wire_length_um, 3),
            "nets": self.nets,
            "incomplete_nets": self.incomplete_nets,
        }


class RouteError(RuntimeError):
    """Raised when the router would have had to draw something wrong.

    Deliberately fatal rather than best-effort: this router's whole claim is
    that a short is structurally impossible, so a column collision is a bug in
    the placement constants, not a net to quietly drop.
    """


def check_riser_columns(terminals: list[Terminal]) -> None:
    """Fail loudly if two different nets' risers would sit too close in x.

    The one invariant the whole scheme rests on. `metal2.space.1` is 0.21 um
    and a riser is `ROUTE_W_UM` (0.30 um) wide, so two columns of different
    nets need `>= 0.51 um` of centre-to-centre separation;
    :data:`cmos5l_devices.ROUTE_PITCH_UM` (0.60 um) is what the device pitches
    are actually built to hold, and is what is required here.
    """
    ordered = sorted(terminals, key=lambda t: (t.x_um, t.net))
    for previous, current in zip(ordered, ordered[1:]):
        if previous.net == current.net:
            continue
        if current.x_um - previous.x_um < dev.ROUTE_PITCH_UM - 1e-9:
            raise RouteError(
                f"riser columns too close: {previous.label} (net {previous.net!r}) "
                f"at x={previous.x_um:.4f} and {current.label} "
                f"(net {current.net!r}) at x={current.x_um:.4f} are "
                f"{current.x_um - previous.x_um:.4f} um apart, under the "
                f"{dev.ROUTE_PITCH_UM} um column pitch"
            )


def route(
    builder: dev.Builder,
    cell: Any,
    terminals: list[Terminal],
    channel_y0_um: float,
    incomplete_nets: list[dict[str, Any]] | None = None,
) -> RouteResult:
    """Draw every net's risers, trunk, vias and label into `cell`.

    `terminals` are in `cell`'s own coordinate frame. `channel_y0_um` is the y
    of the first Metal3 track; the caller supplies it because only the caller
    knows how tall the placed groups are.

    Nets are assigned tracks in sorted name order, so the same plan always
    produces the same layout -- the record's evidence is reproducible, not
    dependent on dict iteration order.
    """
    builder.cell = cell
    check_riser_columns(terminals)

    by_net: dict[str, list[Terminal]] = {}
    for terminal in terminals:
        by_net.setdefault(terminal.net, []).append(terminal)

    result = RouteResult(
        channel_y0_um=channel_y0_um, incomplete_nets=list(incomplete_nets or [])
    )
    for index, net in enumerate(sorted(by_net)):
        pins = sorted(by_net[net], key=lambda t: t.x_um)
        trunk_y = channel_y0_um + index * dev.ROUTE_PITCH_UM
        length = 0.0

        for pin in pins:
            dev.draw_via1(builder, pin.x_um, pin.y_um)
            dev.draw_wire(builder, dev.L_METAL2, pin.x_um, pin.y_um, pin.x_um, trunk_y)
            dev.draw_via2(builder, pin.x_um, trunk_y)
            length += trunk_y - pin.y_um

        x0, x1 = pins[0].x_um, pins[-1].x_um
        dev.draw_wire(builder, dev.L_METAL3, x0, trunk_y, x1, trunk_y)
        length += x1 - x0
        # One label per net, on the trunk. A single-terminal net still gets a
        # trunk (a ROUTE_W_UM square) and a name: an unnamed net is what LVS
        # cannot compare, and a net with one drawn pin is still a real,
        # nameable node of the schematic.
        builder.route_label(net, (x0 + x1) / 2, trunk_y)

        result.nets.append(
            {
                "net": net,
                "track": index,
                "trunk_y_um": round(trunk_y, 4),
                "trunk_x_um": [round(x0, 4), round(x1, 4)],
                "pin_count": len(pins),
                "pins": [pin.label for pin in pins],
                "routed": True,
                "route_length_um": round(length, 3),
            }
        )
        result.wire_length_um += length

    return result
