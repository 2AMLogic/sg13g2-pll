#!/usr/bin/env python3
"""Schematic-driven, per-block PLL layout on **SG13CMOS5L** (#24, routed by #29).

The SG13CMOS5L sibling of `pll_layout.py` (issue #13, SG13G2). Same contract,
same evidence shape, one structural difference:

* `pll_layout.py` **plans** the device set and then asks `klt gen` to draw it.
* This module reuses that identical plan half verbatim
  (`pll_layout.build_plan`, `_match_group_extraction`,
  `_match_block_extraction` are all imported, not re-implemented) and draws
  and routes the geometry itself with `cmos5l_devices.py`/`cmos5l_route.py`,
  originally because **every `klt gen` generator -- and `klt
  gen-compose`'s router -- rejected the `ihp-sg13cmos5l` PDK family**
  outright (the gap klayout-tools#1462 tracked, closed upstream 2026-08-30).

  That gap is now closed and present at this repo's pin, and the local
  drawing and routing stay anyway -- a decision made against measurement
  rather than habit (issue #35), and re-measured on **every** run so it
  cannot go stale silently. The three probes that take that measurement live
  in `cmos5l_probes.py` (split out by issue #372) and are called from
  :func:`build`:

  * :func:`cmos5l_probes.probe_gen_compose_router` -- the original two-pad
    probe, which now reports the family accepted;
  * :func:`cmos5l_probes.probe_gen_compose_block_routing` -- the same request
    shape against a **real** block (`cp`: 8 groups, 14 devices, 13 multi-pin
    nets), where `gen-compose` still routes 1 of 13 nets
    (klayout-tools#1467) and offers no second routing plane on this family to
    move the rest onto;
  * :func:`cmos5l_probes.probe_generator_footprints` -- `klt gen
    mos_array`/`res_array` run on this design's own group parameters, which
    shows `mos_array` output extracting as the *thin*-oxide `sg13_lv_*`
    devices, leaving every PMOS body unbiased, and reporting terminal columns
    too tight for `cmos5l_route`'s risers. See `cmos5l_devices.py`'s own
    docstring for the three findings and
    `layout/sg13cmos5l-pll/README.md`'s friction log for what is filed
    upstream.

  The verification half is unchanged and is still entirely `klt`'s: `klt drc
  --deck sg13cmos5l`, `klt extract --deck sg13cmos5l --pdk ihp-sg13cmos5l`
  and `klt lvs` are what produce every pass/fail claim here.

What this flow does, per block, in order:

1. **Plan** (pure, PDK-free, shared with the SG13G2 flow): parse
   `design/sg13cmos5l/netlist/<block>.spice`, flatten the schematic hierarchy
   to leaf devices, group them by `(class, W, L)`.
2. **Draw** each `mos_array`/`res_array` group as its own cell, with a shared
   NWell + n+ well tap per PMOS group and a p+ substrate tap per NMOS group
   (`cmos5l_devices.draw_pfet_array_well`/`draw_nfet_array_tap`), and each
   `cap_cmomi` capacitor group as its own cell
   (`cmos5l_devices.draw_mom_cap`, issue #114) -- a local interdigitated
   Metal1-Metal4 MoM footprint under a `Recog.mom` (99/39) recognition
   marker sized to the schematic's own declared `w`/`l`.
3. **DRC** each drawn group (`klt drc --deck sg13cmos5l`).
4. **Extract** each drawn group and compare the reported `(class, W, L, count)`
   against the group's own schematic-derived expectation.
5. **Compose** every drawn group of a block into one `pll_<block>` cell,
   placed in a single left-to-right row. For the block(s) named in
   :data:`FLOORPLAN_STRATEGIES` (`vco`, issue #101) the row order, the
   member->slot order inside each matched group cell and the track order are
   first permuted by :func:`cmos5l_floorplan.locality_floorplan` -- a
   net-affinity pass that shortens the nets the block's own topology makes
   local without changing one net, device or drawn footprint.
6. **Route** it (issue #29): every terminal the plan's own
   `groups[].members[].ports` map names is brought up on its own Metal2 riser
   to a per-net Metal3 trunk in a channel above the row, and the trunk is
   labelled with the schematic's own net name on `Metal3.pin` (30/2) -- the
   layer the curated deck reads. See `cmos5l_route.py` for the scheme and for
   why `klt gen-compose`'s own router cannot be used on this PDK.
7. **DRC + extract the composed cell** and cross-check its device-count
   multiset against the block's own schematic-derived totals.
8. **LVS** the composed cell against that block's own committed schematic
   netlist.

Capacitor groups (`cap_cmomi`, the MIM->MoM swap DR-004/#22 ratified) are
drawn by this flow as of issue #114 -- locally, because no `klt gen`
generator draws MoM geometry on this family (see
`pll_layout.BLOCKED_REASONS["cap_cmomi"]` for the tracked upstream state),
and LVS-compared through a caller-side reference rewrite (see
`_mom_cap_reference`) that emits the `X ... cap_cmomi PARAMS: W= L=` card
shape `klt lvs`'s custom-device-class reader (klayout-tools#1942/#1944)
recognises.

Nothing here relaxes a claim to make it pass: every `klt` invocation's raw
JSON response is written into the record directory, and the summary is derived
from those responses rather than asserted alongside them.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cmos5l_devices as dev  # noqa: E402
import cmos5l_floorplan  # noqa: E402
import cmos5l_probes  # noqa: E402
import cmos5l_route as route  # noqa: E402
import pll_layout  # noqa: E402

#: Gap left between two unit devices' own drawn extents inside a group (um).
#: Every same-layer spacing rule in the curated `sg13cmos5l` deck is at or
#: below 0.21 um (`activ.space.1`); the unit devices' own marker overhangs
#: add at least another 0.36 um on top of this, so a placement error would
#: have to be an order of magnitude larger than the tolerance to hide here.
DEVICE_GAP_UM = 0.6

#: Gap between a group's device array and its own well/substrate tap strip
#: (um). Larger than :data:`DEVICE_GAP_UM` on purpose: the tap carries an
#: implant marker (`nSD`/`pSD`) whose enclosure must not reach a device's own
#: diffusion, or it would counter-dope that device's source/drain.
TAP_GAP_UM = 1.0

#: Gap between two stacked poly-resistor bars in a `res_array` group (um).
RES_GAP_UM = 0.6

#: x offset applied to each successive bar in a stacked `res_array` group
#: (um). Without it, every bar's own end pads would sit in the *same* riser
#: column, and two bars on different nets cannot share one column
#: (`cmos5l_route.check_riser_columns`). One `ROUTE_PITCH_UM` per bar is the
#: minimum stagger that separates them.
RES_STAGGER_UM = dev.ROUTE_PITCH_UM

#: Spacing between placed groups inside a composed block cell (um).
GROUP_SPACING_UM = 6.0

#: Riser-column x offsets of a unit MOS's source and drain terminals, measured
#: from its own active box's left edge (um).
#:
#: Both land inside the full-width `Metal1` source/drain pads
#: :func:`cmos5l_devices.draw_hv_mos` draws on any device at least
#: `DRAIN_RISER_DX_UM + ROUTE_W_UM / 2` = 1.2 um wide. They are 0.6 um apart --
#: one :data:`cmos5l_devices.ROUTE_PITCH_UM` -- and the gate's own column sits
#: a further 0.88 um to the left, off the gate landing pad.
#:
#: Narrower devices exist since issue #66 re-sized `lock_detector`'s XMPD to
#: `w = 0.25 um`, and on those both columns used to fall *outside* the pads:
#: the two Via1s landed on no Metal1 and both diffusion terminals extracted
#: as open nets (issue #136). :func:`draw_mos_group` now passes each column's
#: reach to `draw_hv_mos`, which grows a Metal1 tab out to it whenever the
#: pad is too narrow -- a no-op on every device >= 1.2 um wide.
SOURCE_RISER_DX_UM = 0.45
DRAIN_RISER_DX_UM = 1.05

#: Deck and PDK variant names. The deck name (`sg13cmos5l`) and the PDK
#: variant name (`ihp-sg13cmos5l`) are deliberately distinct -- `klt` resolves
#: them independently, and `--pdk` is what binds an extracted MOS to the
#: PDK's own `sg13_hv_nmos`/`sg13_hv_pmos` subcircuit rather than leaving it a
#: bare `nfet`/`pfet` primitive.
DEFAULT_DECK = "sg13cmos5l"
DEFAULT_PDK = "ihp-sg13cmos5l"

DRAWABLE_KINDS = ("mos_array", "res_array", "capacitor")

#: The model this flow draws with its own MoM footprint (issue #114). The
#: shared planner still records `cap_cmomi` groups with the upstream
#: generator's blocked reason (`klt gen` has no MoM generator for this
#: family); :func:`promote_local_mom_caps` below promotes exactly those
#: groups to locally drawn ones, which is what `draw_cap_group` consumes.
MOM_CAP_MODEL = "cap_cmomi"

#: Marker the extraction side recognises `cap_cmomi` by -- kept beside the
#: promotion step that depends on it so the two cannot drift apart.
#: (`klayout_tools.decks.sg13cmos5l.EXTRACTION_DECK.mom_capacitors[0]`,
#: klayout-tools#1466 merged as #1475, carried at this repo's pin.)
MOM_CAP_MARKER_LAYER = dev.L_RECOG_MOM


def _parse_mom_cap_um(value: str) -> float:
    """`'40u'` -> 40.0 microns; a bare SI-metres literal -> microns."""
    if value[-1] in "uU":
        return float(value[:-1])
    return float(value) * 1e6


_MOM_CAP_RUN_RE = re.compile(r"^\* loom-mom-cap-run (\d+)$")

#: A converted resistor card: `R<name> <nets...> 0 <class> L=<l>U W=<w>U` --
#: `_convert_geometry_card`'s own output shape (value `0` placeholder,
#: uppercase-suffixed geometry). The value is the first positional token
#: after the nets, immediately before the class name.
_RESISTOR_CARD_RE = re.compile(
    r"^(?P<name>R\S+)\s+(?P<nets>\S+(?:\s+\S+)*?)\s+(?P<value>0)\s+"
    r"(?P<model>rppd|rhigh|rsil)\s+(?P<params>L=\S+\s+W=\S+)\s*$"
)


def _deck_resistor_sheet_ohm_per_sq() -> dict[str, tuple[float, float]]:
    """`{class: (sheet_ohm_per_sq, fixed_offset_ohm)}` for this deck's
    resistors -- the same curated coefficients `klt extract` computes a drawn
    resistor's reported resistance from, read straight out of the deck so the
    reference value and the extracted value cannot drift apart."""
    from klayout_tools.decks import get_extraction_deck

    deck = get_extraction_deck(DEFAULT_DECK)
    return {
        resistor.name: (resistor.sheet_rho_ohm_sq, resistor.fixed_offset_ohm)
        for resistor in deck.resistors
    }


def _fill_resistor_values(converted: str) -> str:
    """Replace converted resistor cards' `0` value placeholder with the real
    resistance (and area/perimeter) the deck's own coefficients compute.

    `netlist_normalize`'s converter writes the literal `0` because it
    deliberately carries no PDK sheet-resistance table; `klt lvs`'s own
    `subckt-call` path then has to *exclude* the value parameter from the
    compare to let the class pair at all (issue #1907's
    `device.placeholder_value` disclosure). This flow has the deck one call
    away, so it computes the real value instead -- which means the compare
    verifies the resistance dimension too, rather than disclosing that it
    skipped it. `A`/`P` ride along for the same reason: the extracted device
    reports them (a plain `L*W` / `2(L+W)` rectangle), while the converted
    card leaves them unset.
    """
    sheets = _deck_resistor_sheet_ohm_per_sq()
    out: list[str] = []
    for raw in converted.splitlines():
        match = _RESISTOR_CARD_RE.match(raw.strip())
        if match is None or match.group("model") not in sheets:
            out.append(raw)
            continue
        params = dict(
            token.split("=", 1) for token in match.group("params").split()
        )
        l_um = _parse_mom_cap_um(params["L"])
        w_um = _parse_mom_cap_um(params["W"])
        sheet, offset = sheets[match.group("model")]
        value = sheet * l_um / w_um + offset
        area = l_um * w_um
        perim = 2.0 * (l_um + w_um)
        out.append(
            f"{match.group('name')} {match.group('nets')} {value:g} "
            f"{match.group('model')} {match.group('params')} "
            f"A={area:g} P={perim:g}"
        )
    return "\n".join(out) + "\n"


def mom_cap_reference(text: str) -> str:
    """Convert a committed schematic netlist into an LVS-readable reference.

    Two rewrites, both caller-side because no single `klt lvs` request shape
    performs them together (the gap between `reference.form:
    "subckt-call"`'s converter and the custom-device-class reader of
    klayout-tools#1942/#1944 is itself filed upstream -- see the README's
    friction log):

    * Every ``X<name> <a> <b> cap_cmomi w= l= ... m=M ...`` card becomes `M`
      cards of the exact shape that reader recognises --
      ``X<name>__<k> <a> <b> cap_cmomi PARAMS: W=<w_um> L=<l_um>`` -- with
      `W`/`L` in **microns as bare numbers** (the extractor reports the
      marker bbox in um; a `40u` suffix would parse as SI metres and
      mismatch by 1e6) and the `m=` multiplier expanded one card per unit,
      matching the one-marker-per-unit layout the footprint draws. The
      PDK-cell parameters the card also carries (`mmin`/`mmax`/`feed`/
      `subblock`/`mm_ok`) describe the *generator's* geometry; the
      extracted device's only matched parameters are `W`/`L`, so the card
      carries exactly those.
    * Everything else (MOS `sg13_hv_*` X cards, `rppd`/`rhigh` resistor X
      cards, the `.subckt` hierarchy itself) is converted to plain-element
      form by `klayout_tools.netlist_normalize.normalize_reference_netlist`
      -- the same conversion `reference.form: "subckt-call"` performs --
      run on the text with the cap cards lifted out, so its converter never
      sees the `PARAMS:` token it would otherwise reject. Converted resistor
      cards then get their `0` value placeholder replaced with the real
      resistance/area/perimeter the deck's own curated coefficients compute
      (:func:`_fill_resistor_values`), so nothing in the final reference
      relies on `klt lvs`'s placeholder-exclusion disclosure -- the compare
      verifies the resistance dimension instead of skipping it.

    The returned text is a `form: "plain-element"` reference: `klt lvs`
    reads it with `reference.deck` set, and that deck's `mom_capacitors`
    plus curated tables recognise every card in it.
    """
    from klayout_tools.netlist_normalize import normalize_reference_netlist

    keepers: list[str] = []
    lifted: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not (stripped[:1].upper() == "X" and MOM_CAP_MODEL in stripped.split()):
            lifted.append(raw)
            continue
        tokens = stripped.split()
        name, net_a, net_b, rest = tokens[0], tokens[1], tokens[2], tokens[3:]
        if tokens[3].lower() != MOM_CAP_MODEL:
            raise ValueError(
                f"mom_cap_reference: {stripped!r}: expected "
                f"'<name> <netA> <netB> {MOM_CAP_MODEL} ...'"
            )
        params: dict[str, str] = {}
        for token in rest[1:]:
            key, sep, value = token.partition("=")
            if sep:
                params[key.strip().lower()] = value.strip()
        try:
            w_um = _parse_mom_cap_um(params["w"])
            l_um = _parse_mom_cap_um(params["l"])
            multiplicity = int(float(params.get("m", "1")))
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"mom_cap_reference: {stripped!r}: unreadable w/l/m ({exc})"
            ) from exc
        if multiplicity < 1:
            raise ValueError(
                f"mom_cap_reference: {stripped!r}: m={params.get('m')!r} is "
                "not a positive multiplier"
            )
        for k in range(multiplicity):
            suffix = "" if multiplicity == 1 else f"__{k}"
            keepers.append(
                f"{name}{suffix} {net_a} {net_b} {MOM_CAP_MODEL} "
                f"PARAMS: W={w_um:g} L={l_um:g}"
            )
        # One slot line per original card; the splice re-expands the run.
        lifted.append(f"* loom-mom-cap-run {multiplicity}")

    converted = normalize_reference_netlist(
        "\n".join(lifted) + "\n", deck=DEFAULT_DECK
    )

    out: list[str] = []
    taken = 0
    for raw in converted.splitlines():
        match = _MOM_CAP_RUN_RE.match(raw.strip())
        if match is None:
            out.append(raw)
            continue
        count = int(match.group(1))
        out.extend(keepers[taken : taken + count])
        taken += count
    if taken != len(keepers):
        raise ValueError(
            "mom_cap_reference: the normalizer dropped a lifted cap slot "
            f"({taken} of {len(keepers)} cards spliced back)"
        )
    return _fill_resistor_values("\n".join(out) + "\n")


def promote_local_mom_caps(plan: dict[str, Any]) -> list[str]:
    """Promote every `cap_cmomi` plan group to a locally drawn one.

    The plan (shared with the SG13G2 flow) leaves `cap_cmomi` groups
    undrawable because no `klt gen` generator exists for them -- correct for
    the planner, which only knows about generators. This flow *can* draw
    them (`cmos5l_devices.draw_mom_cap`, the same local-footprint decision
    issues #24/#35 made for MOS and resistors) and LVS-recognise them at
    this repo's pin, so each such group gets a `local_mom_cap` generator, an
    `expected` device of the marker's own `(class, w_um, l_um)`, and its
    `blocked_reason` removed -- the group is no longer blocked, and leaving
    the reason in place would misreport it in the record.

    Returns the promoted group ids (recorded in `build.json` as the
    promotion's own evidence).
    """
    promoted: list[str] = []
    for block in plan["blocks"]:
        for group in block["groups"]:
            if (
                group["kind"] == "capacitor"
                and group["generator"] is None
                and group["params"].get("model") == MOM_CAP_MODEL
            ):
                group["generator"] = "local_mom_cap"
                group["expected"] = {
                    "class": MOM_CAP_MODEL,
                    "w_um": group["params"]["w_um"],
                    "l_um": group["params"]["l_um"],
                    "count": 1,
                }
                group.pop("blocked_reason", None)
                promoted.append(group["id"])
    return promoted


# --- Drawing ---------------------------------------------------------------


def group_body_net(group: dict[str, Any]) -> str | None:
    """The one schematic net every device in a MOS group ties its body to.

    Returns `None` when the group carries no members (the synthetic groups
    the unit tests build) or -- deliberately, rather than picking one -- when
    the members disagree. Every group this design's six netlists produce has
    exactly one body net; a future one that does not must be split into two
    wells before it can be labelled, and returning `None` is what makes that
    show up as an unnamed body rather than as a wrong name.
    """
    bodies = {
        member["ports"][f"U{member['unit']}_B"] for member in group.get("members", [])
    }
    return bodies.pop() if len(bodies) == 1 else None


def draw_mos_group(builder: dev.Builder, group: dict[str, Any]) -> dict[str, Any]:
    """Draw one matched MOS group as its own cell. Returns its geometry.

    **Single-row (issue #29).** The plan's own `rows`/`cols` are ignored here
    and every group is drawn one device tall. A second row would put two
    devices' source/drain/gate terminals in the *same* riser column, and the
    router's no-shared-column invariant (`cmos5l_route.check_riser_columns`)
    is what makes its output structurally short-free. The trade is width --
    `divider_chain`'s 158-device NMOS group is ~0.7 mm wide -- which is a
    floorplan cost, recorded as one in `layout/sg13cmos5l-pll/README.md`, not
    a correctness one. Device *count*, class and W/L (what
    `_match_group_extraction` checks against the schematic) are unchanged.
    """
    params = group["params"]
    flavor = params["flavor"]
    w_um, l_um = params["w_um"], params["l_um"]
    count = group["count"]

    act_w, act_h = dev.mos_active_size(w_um, l_um)
    mx, my = dev.mos_margins(flavor)
    pitch_x = act_w + 2 * mx + DEVICE_GAP_UM

    # Leave room below the array for the tap strip (and, for a PMOS group,
    # the shared well's own NW_c1 enclosure of it).
    base_x = mx + dev.NW_C1
    base_y = my + TAP_GAP_UM + dev.TAP_H_UM + dev.NW_C1

    builder.open_cell(group["id"])
    actives: list[tuple[float, float, float, float]] = []
    terminals: dict[str, tuple[float, float]] = {}
    for index in range(count):
        x = base_x + index * pitch_x
        drawn = dev.draw_hv_mos(
            builder,
            flavor,
            x,
            base_y,
            w_um,
            l_um,
            source_reach_um=SOURCE_RISER_DX_UM + dev.ROUTE_W_UM / 2,
            drain_reach_um=DRAIN_RISER_DX_UM + dev.ROUTE_W_UM / 2,
        )
        actives.append(drawn["active"])  # type: ignore[arg-type]
        source_pad = drawn["source_pad"]  # type: ignore[index]
        drain_pad = drawn["drain_pad"]  # type: ignore[index]
        gate_pad = drawn["gate_pad"]  # type: ignore[index]
        terminals[f"U{index}_S"] = (
            x + SOURCE_RISER_DX_UM,
            (source_pad[1] + source_pad[3]) / 2,
        )
        terminals[f"U{index}_D"] = (
            x + DRAIN_RISER_DX_UM,
            (drain_pad[1] + drain_pad[3]) / 2,
        )
        terminals[f"U{index}_G"] = (
            (gate_pad[0] + gate_pad[2]) / 2,
            (gate_pad[1] + gate_pad[3]) / 2,
        )

    # The body net comes from the schematic, not from an invented label: an
    # NWell named `<group>_B` extracts as a net the reference netlist has
    # never heard of, and LVS then reports a mismatch this flow manufactured.
    body_net = group_body_net(group) or f"{group['id']}_B"
    if flavor == "pfet":
        # One shared well per group, biased by one n+ tap -- three separate
        # wells would extract as three separate, unrelated body nets.
        tap = dev.draw_pfet_array_well(builder, actives, TAP_GAP_UM, body_net)
    else:
        tap = dev.draw_nfet_array_tap(builder, actives, TAP_GAP_UM)

    return {
        "rows": 1,
        "cols": count,
        "pitch_x_um": round(pitch_x, 4),
        "unit_size_um": [round(act_w + 2 * mx, 4), round(act_h + 2 * my, 4)],
        "body_tie": {
            "kind": "nwell_tap" if flavor == "pfet" else "substrate_tap",
            "net": body_net,
            "well_labelled": flavor == "pfet",
        },
        "terminals": {k: [round(v[0], 4), round(v[1], 4)] for k, v in terminals.items()},
        "tie_point": [round(v, 4) for v in tap["tie_point"]],  # type: ignore[index,union-attr]
        "tap": {
            k: [round(v, 4) for v in box]
            for k, box in tap.items()  # type: ignore[union-attr]
            if k != "tie_point"
        },
    }


def draw_res_group(builder: dev.Builder, group: dict[str, Any]) -> dict[str, Any]:
    """Draw one poly-resistor group as its own cell (bars stacked in y).

    Each successive bar is also stepped :data:`RES_STAGGER_UM` to the right,
    so two bars' end pads never share a riser column (see that constant).
    """
    params = group["params"]
    flavor, w_um, l_um = params["flavor"], params["width_um"], params["length_um"]
    bar_w, bar_h = dev.res_size(w_um, l_um)

    builder.open_cell(group["id"])
    terminals: dict[str, tuple[float, float]] = {}
    for index in range(group["count"]):
        drawn = dev.draw_poly_res(
            builder,
            flavor,
            index * RES_STAGGER_UM,
            index * (bar_h + RES_GAP_UM),
            w_um,
            l_um,
        )
        for port, key in ((f"R{index}_A", "end_a_pad"), (f"R{index}_B", "end_b_pad")):
            pad = drawn[key]  # type: ignore[index]
            terminals[port] = ((pad[0] + pad[2]) / 2, (pad[1] + pad[3]) / 2)

    return {
        "bars": group["count"],
        "bar_size_um": [round(bar_w, 4), round(bar_h, 4)],
        "stack_pitch_um": round(bar_h + RES_GAP_UM, 4),
        "stagger_um": RES_STAGGER_UM,
        "terminals": {k: [round(v[0], 4), round(v[1], 4)] for k, v in terminals.items()},
    }


def draw_cap_group(builder: dev.Builder, group: dict[str, Any]) -> dict[str, Any]:
    """Draw one `cap_cmomi` MoM-capacitor group as its own cell (issue #114).

    One group per schematic instance (the planner's own shape for
    capacitors), one recognition marker per unit, the two terminals brought
    to Metal1 feed pads at the cell's extreme x -- which is what keeps the
    router's two riser columns one marker width apart.
    """
    params = group["params"]
    builder.open_cell(group["id"])
    drawn = dev.draw_mom_cap(
        builder,
        0.0,
        0.0,
        params["w_um"],
        params["l_um"],
        mmin=params.get("mmin", 1),
        mmax=params.get("mmax", 4),
        feed=params.get("feed", "double"),
        label=group["id"],
    )
    terminals = {
        "TOP": drawn["terminals"]["TOP"],  # type: ignore[index]
        "BOT": drawn["terminals"]["BOT"],  # type: ignore[index]
    }
    return {
        "footprint": "cmos5l_devices.draw_mom_cap",
        "marker_layer": list(MOM_CAP_MARKER_LAYER),
        "marker_um": [
            round(drawn["marker"][2] - drawn["marker"][0], 4),  # type: ignore[index]
            round(drawn["marker"][3] - drawn["marker"][1], 4),  # type: ignore[index]
        ],
        "unit_cells": {"nx": drawn["nx"], "ny": drawn["ny"]},  # type: ignore[index]
        "metals": list(drawn["metals"]),  # type: ignore[index]
        "terminals": {k: [round(v[0], 4), round(v[1], 4)] for k, v in terminals.items()},
        "plus_pad": [round(v, 4) for v in drawn["plus_pad"]],  # type: ignore[index]
        "minus_pad": [round(v, 4) for v in drawn["minus_pad"]],  # type: ignore[index]
    }


def group_size_um(group: dict[str, Any]) -> tuple[float, float]:
    """Drawn `(width, height)` of one group's own cell, in microns.

    Derived from the same constants :func:`draw_mos_group`/
    :func:`draw_res_group` place with, so the packer never has to read
    geometry back out of the layout.
    """
    params = group["params"]
    count = group["count"]
    if group["kind"] == "mos_array":
        flavor = params["flavor"]
        act_w, act_h = dev.mos_active_size(params["w_um"], params["l_um"])
        mx, my = dev.mos_margins(flavor)
        pitch_x = act_w + 2 * mx + DEVICE_GAP_UM
        width = 2 * dev.NW_C1 + 2 * mx + act_w + (count - 1) * pitch_x
        height = 2 * dev.NW_C1 + TAP_GAP_UM + dev.TAP_H_UM + 2 * my + act_h
        return width, height
    if group["kind"] == "capacitor":
        # The marker is the whole drawn extent; mom_cap_size records why the
        # packer's box is the schematic-declared (l_um, w_um), not the PCell's.
        return dev.mom_cap_size(params["w_um"], params["l_um"])
    bar_w, bar_h = dev.res_size(params["width_um"], params["length_um"])
    return (
        bar_w + (count - 1) * RES_STAGGER_UM,
        count * bar_h + (count - 1) * RES_GAP_UM,
    )


# --- klt invocation --------------------------------------------------------


class Verifier:
    """Runs `klt drc`/`klt extract` and records the raw response, unedited."""

    def __init__(self, klt: str, deck: str, pdk: str, pdk_root: str | None, out_dir: Path):
        self.klt = klt
        self.deck = deck
        self.pdk = pdk
        self.pdk_root = pdk_root
        self.out_dir = out_dir

    def _relativise(self, text: str) -> str:
        """Replace this record's own absolute path with `.` in `klt` output.

        A record is committed evidence, so an absolute path inside it is a
        reproducibility defect, not cosmetics: the same run in a different
        checkout would produce a byte-different record for no reason anyone
        could act on, and a reader diffing two records would see machine
        noise. Only this record directory's own prefix is rewritten -- every
        other byte of `klt`'s response is committed unedited.
        """
        return text.replace(str(self.out_dir.resolve()), ".").replace(
            str(self.out_dir), "."
        )

    def _run(self, args: list[str]) -> dict[str, Any]:
        proc = subprocess.run(
            [self.klt, *args], capture_output=True, text=True, cwd=self.out_dir
        )
        # `klt ... --format json` writes its envelope to stdout on success and
        # to stderr on error, so read whichever stream is non-empty rather
        # than silently swallowing a captured error as `{}` (the same
        # behaviour `pll_layout.Builder._parse_json_envelope` documents).
        raw = self._relativise(proc.stdout.strip() or proc.stderr.strip())
        try:
            report = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            report = {"error": {"message": raw[:2000]}}
        return {
            "returncode": proc.returncode,
            "ok": proc.returncode == 0 and "error" not in report,
            "response": report,
            "stderr": self._relativise(proc.stderr.strip())[:2000],
        }

    def drc(self, gds: str, top: str, report_name: str) -> dict[str, Any]:
        result = self._run(
            ["drc", "--deck", self.deck, "--top", top, gds, "--format", "json"]
        )
        result["clean"] = bool(
            result["ok"] and result["response"].get("status") == "clean"
        )
        (self.out_dir / report_name).write_text(json.dumps(result, indent=2) + "\n")
        return result

    def lvs(
        self,
        gds: str,
        top: str,
        reference: str,
        request_name: str,
        report_name: str,
    ) -> dict[str, Any]:
        """Compare one composed block against its own schematic netlist.

        `reference` is already the **plain-element** text
        :func:`mom_cap_reference` produced (MOS/resistor X cards converted,
        `cap_cmomi` cards in the `X ... PARAMS: W= L=` shape the
        custom-device-class reader of klayout-tools#1942/#1944 recognises),
        so the request reads it with `form: "plain-element"` plus
        `reference.deck` -- the deck is what makes both the curated
        MOS/resistor tables and the `mom_capacitors` custom classes resolve
        on the reference side. Both sides are flattened so the comparison is
        device-set-vs-device-set: the reference is hierarchical (six
        `.subckt` levels deep in places) while the composed layout is one
        flat cell of per-group instances.
        """
        request = {
            "schema": "klt.lvs.request/1",
            "engine": "klayout",
            "layout": {"file": gds, "deck": self.deck, "top": top},
            "reference": {
                "netlist": reference,
                "deck": self.deck,
            },
            "options": {"flatten_layout": True, "flatten_reference": True},
        }
        (self.out_dir / request_name).write_text(json.dumps(request, indent=2) + "\n")
        result = self._run(["lvs", request_name, "--format", "json"])
        (self.out_dir / report_name).write_text(json.dumps(result, indent=2) + "\n")
        return result

    def extract(self, gds: str, top: str, report_name: str) -> dict[str, Any]:
        args = [
            "extract",
            "--deck",
            self.deck,
            "--pdk",
            self.pdk,
            "--top",
            top,
            gds,
            "-o",
            f"{top}.extracted.spice",
            "--format",
            "json",
        ]
        if self.pdk_root:
            args[1:1] = ["--pdk-root", self.pdk_root]
        result = self._run(args)
        (self.out_dir / report_name).write_text(json.dumps(result, indent=2) + "\n")
        return result

    def gen_compose(self, request_name: str, report_name: str) -> dict[str, Any]:
        """Run one `klt gen-compose` request and record the raw response.

        Used **only** by :mod:`cmos5l_probes` -- this flow composes and routes
        its own blocks (see `cmos5l_route.py` for the two measured reasons
        why), so nothing in the drawn, DRC'd, LVS'd layout comes from here.
        `request_name` is resolved relative to the record directory, which is
        also `klt`'s own working directory.
        """
        result = self._run(["gen-compose", request_name, "--format", "json"])
        (self.out_dir / report_name).write_text(json.dumps(result, indent=2) + "\n")
        return result

    def gen(
        self,
        generator: str,
        params: dict[str, Any],
        cell_name: str,
        report_name: str,
    ) -> dict[str, Any]:
        """Run one `klt gen <generator>` request and record the raw response.

        Used **only** by :func:`cmos5l_probes.probe_generator_footprints` --
        this flow draws
        its own footprints (see that function for the measurement that says
        why). Nothing in the drawn, DRC'd, LVS'd layout comes from here.
        """
        args = [
            "gen",
            generator,
            "--pdk",
            self.pdk,
            "--params",
            json.dumps(params),
            "--cell-name",
            cell_name,
            "-o",
            f"{cell_name}.gds",
            "--format",
            "json",
        ]
        if self.pdk_root:
            args[2:2] = ["--pdk-root", self.pdk_root]
        result = self._run(args)
        (self.out_dir / report_name).write_text(json.dumps(result, indent=2) + "\n")
        return result


# --- Placement and terminal collection --------------------------------------


#: Composition strategy a block's groups are placed with (issue #101).
#:
#: ``"single_row"`` -- the default and the only strategy every block used
#: before issue #101 -- places the drawn group cells left to right in the
#: plan's own (type-sorted) order, and lets :func:`cmos5l_route.route` assign
#: Metal3 tracks by net name. It is not a considered floorplan, and the block
#: README says so rather than pretending otherwise.
#:
#: ``"locality"`` hands the same drawn group cells, the same geometries and
#: the same ``collect_terminals`` to :func:`cmos5l_floorplan.locality_floorplan`,
#: which permutes the group order, the member->slot order inside each matched
#: group cell and the track order to shorten the nets the block's own
#: topology makes local -- on `vco`, the ring and per-stage nets. The
#: membership, geometry, spacing and every net are unchanged, so the
#: router's structural-correctness invariants and the extraction/LVS
#: comparisons are unchanged; only the wire length moves. Applied per block
#: by name: a block not listed here keeps byte-for-byte the composition its
#: committed record and PEX netlist were produced from.
DEFAULT_FLOORPLAN_STRATEGY = "single_row"

FLOORPLAN_STRATEGIES: dict[str, str] = {"vco": "locality"}


def single_row_pack(
    sizes: list[tuple[str, float, float]], spacing_um: float
) -> dict[str, dict[str, float]]:
    """Place every group in one left-to-right row, bottom-aligned at `y = 0`.

    Replaces `pll_layout.shelf_pack` on this flow (issue #29). A shelf pack
    wraps groups onto a second row once they exceed a target width, which puts
    a lower group's risers underneath an upper group -- the one arrangement
    the router's straight-up-to-the-channel scheme cannot make. One row keeps
    the whole channel reachable from every terminal by a vertical line through
    empty space. It is wider (`divider_chain` reaches ~1.9 mm) and it is not a
    floorplan; the block README says so.
    """
    origins: dict[str, dict[str, float]] = {}
    x = 0.0
    for group_id, width, _height in sizes:
        origins[group_id] = {"x": round(x, 4), "y": 0.0}
        x += width + spacing_um
    return origins


def collect_terminals(
    drawn_groups: list[dict[str, Any]],
    geometries: dict[str, dict[str, Any]],
    origins: dict[str, dict[str, float]],
) -> tuple[list[route.Terminal], list[dict[str, Any]]]:
    """Turn the plan's own port->net map into composed-frame route terminals.

    Nothing here decides connectivity: every net name is read straight out of
    `groups[].members[].ports`, which `pll_layout.build_plan` derived from the
    committed schematic netlist. Returns `(terminals, notes)`, where `notes`
    records every planned port that got **no** terminal and why -- a port is
    never silently dropped.
    """
    terminals: list[route.Terminal] = []
    notes: list[dict[str, Any]] = []
    for group in drawn_groups:
        geometry = geometries[group["id"]]
        origin = origins[group["id"]]
        local = geometry["terminals"]
        for member in group["members"]:
            for port, net in member["ports"].items():
                if port in local:
                    x, y = local[port]
                    terminals.append(
                        route.Terminal(
                            net=net,
                            x_um=origin["x"] + x,
                            y_um=origin["y"] + y,
                            label=f"{group['id']}.{port}",
                        )
                    )
                elif port.endswith("_B") and group["kind"] == "mos_array":
                    continue  # tied once per group, below
                elif port.endswith("_BULK"):
                    notes.append(
                        {
                            "port": f"{group['id']}.{port}",
                            "net": net,
                            "reason": (
                                "a drawn poly resistor's bulk terminal is the "
                                "p-substrate, which the curated sg13cmos5l deck "
                                "extracts onto its own `vsubs` global rather "
                                "than onto a drawn, routable pad -- there is no "
                                "terminal here to route to"
                            ),
                        }
                    )
                else:  # pragma: no cover - defensive
                    raise route.RouteError(
                        f"{group['id']}: planned port {port!r} has no drawn terminal"
                    )
        if group["kind"] == "mos_array":
            tie_x, tie_y = geometry["tie_point"]
            terminals.append(
                route.Terminal(
                    net=geometry["body_tie"]["net"],
                    x_um=origin["x"] + tie_x,
                    y_um=origin["y"] + tie_y,
                    label=f"{group['id']}.{geometry['body_tie']['kind']}",
                )
            )
    return terminals, notes


def undrawn_net_notes(block: dict[str, Any]) -> list[dict[str, Any]]:
    """One entry per net the schematic declares that the layout cannot finish.

    A net whose pin list includes a device that was never drawn is routed
    between the terminals that *do* exist and reported here as incomplete,
    with the undrawn group's own `blocked_reason` attached. Never waived,
    never silently treated as fully routed.
    """
    notes: list[dict[str, Any]] = []
    for group in block["groups"]:
        if group.get("generator") is not None:
            continue
        for member in group["members"]:
            for port, net in member["ports"].items():
                notes.append(
                    {
                        "net": net,
                        "missing_pin": f"{group['id']}.{port}",
                        "device": member["device"],
                        "reason": group["blocked_reason"],
                    }
                )
    return notes


# --- Build -----------------------------------------------------------------


def _lvs_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Condense one `klt lvs` response into the record's own summary shape.

    Reported, deliberately, without a pass/fail verdict of this flow's own
    invention: `status` is whatever `klt lvs` said, and `counts` is its own
    device/net/pin tally. What the record then *interprets* is written next
    to these numbers in `record.md`, never substituted for them.
    """
    response = result.get("response", {})
    unmatched: dict[str, int] = {}
    for mismatch in response.get("mismatches", []) or []:
        device = mismatch.get("device") or {}
        if mismatch.get("category") == "device.unmatched" and device.get("class"):
            key = f"{device['class']} ({'layout' if device.get('layout') else 'reference'})"
            unmatched[key] = unmatched.get(key, 0) + 1
    return {
        "ran": result["ok"] or "status" in response,
        "status": response.get("status"),
        "mismatch_count": response.get("mismatch_count"),
        "category_counts": response.get("category_counts"),
        "counts": response.get("counts"),
        "unmatched_device_classes": unmatched,
        "error": response.get("error", {}).get("message"),
    }


def build_block(
    block: dict[str, Any],
    verifier: Verifier,
    out_dir: Path,
    netlist_dir: Path,
) -> dict[str, Any]:
    """Draw, DRC, extract, compose and re-verify one block. Never asserts a
    result it did not read back out of `klt`'s own response."""
    builder = dev.Builder()
    group_results: list[dict[str, Any]] = []
    drawn_groups: list[dict[str, Any]] = []
    geometries: dict[str, dict[str, Any]] = {}

    for group in block["groups"]:
        if group.get("generator") is None:
            group_results.append(
                {
                    "group_id": group["id"],
                    "kind": group["kind"],
                    "count": group["count"],
                    "attempted": False,
                    "ok": False,
                    "reason": group["blocked_reason"],
                }
            )
            continue

        if group["kind"] == "mos_array":
            geometry = draw_mos_group(builder, group)
        elif group["kind"] == "capacitor":
            geometry = draw_cap_group(builder, group)
        else:
            geometry = draw_res_group(builder, group)
        dev.write_cell(builder, group["id"], out_dir / f"{group['id']}.gds")

        drc_result = verifier.drc(
            f"{group['id']}.gds", group["id"], f"drc.{group['id']}.json"
        )
        extract_result = verifier.extract(
            f"{group['id']}.gds", group["id"], f"extract.{group['id']}.json"
        )
        match = (
            pll_layout._match_group_extraction(group, extract_result["response"])
            if extract_result["ok"]
            else {"matched": False, "mismatches": ["extraction failed"]}
        )
        result = {
            "group_id": group["id"],
            "kind": group["kind"],
            "count": group["count"],
            "attempted": True,
            "geometry": geometry,
            "drc": {
                "clean": drc_result["clean"],
                "violation_count": drc_result["response"].get("violation_count"),
                "rule_counts": drc_result["response"].get("rule_counts"),
            },
            "extract_ok": extract_result["ok"],
            "match": match,
        }
        result["ok"] = drc_result["clean"] and extract_result["ok"] and match["matched"]
        group_results.append(result)
        drawn_groups.append(group)
        geometries[group["id"]] = geometry

    compose: dict[str, Any] | None = None
    block_drc: dict[str, Any] | None = None
    block_extract: dict[str, Any] | None = None
    block_match: dict[str, Any] | None = None
    block_lvs: dict[str, Any] | None = None

    if drawn_groups:
        strategy = FLOORPLAN_STRATEGIES.get(block["name"], DEFAULT_FLOORPLAN_STRATEGY)
        floorplan: dict[str, Any] | None = None
        track_order: list[str] | None = None
        ordered_groups = drawn_groups
        if strategy == "locality":
            sizes_for_plan = [
                (g["id"], *group_size_um(g)) for g in drawn_groups
            ]
            floorplan = cmos5l_floorplan.locality_floorplan(
                drawn_groups,
                geometries,
                sizes_for_plan,
                GROUP_SPACING_UM,
                collect=collect_terminals,
            )
            ordered_groups = floorplan["ordered_groups"]
            track_order = floorplan["track_order"]
        sizes = [(g["id"], *group_size_um(g)) for g in ordered_groups]
        origins = single_row_pack(sizes, GROUP_SPACING_UM)
        cell = builder.open_cell(block["cell_name"])
        for group in ordered_groups:
            origin = origins[group["id"]]
            builder.instantiate(
                cell, builder.layout.cell(group["id"]), origin["x"], origin["y"]
            )
        terminals, port_notes = collect_terminals(ordered_groups, geometries, origins)
        channel_y0 = max(height for _id, _w, height in sizes) + route.CHANNEL_GAP_UM
        routing = route.route(
            builder,
            cell,
            terminals,
            channel_y0,
            incomplete_nets=undrawn_net_notes(block),
            track_order=track_order,
        )
        gds_name = f"{block['cell_name']}.gds"
        dev.write_cell(builder, block["cell_name"], out_dir / gds_name)
        compose = {
            "cell_name": block["cell_name"],
            "gds": gds_name,
            "strategy": strategy,
            "spacing_um": GROUP_SPACING_UM,
            "placements": origins,
            "terminal_count": len(terminals),
            "unrouted_ports": port_notes,
            "routing": routing.as_dict(),
        }
        if floorplan is not None:
            compose["floorplan"] = {
                "pass": "cmos5l_floorplan.locality_floorplan",
                "baseline_wire_length_um": floorplan["baseline_wire_length_um"],
                "baseline_per_net_wire_length_um": floorplan[
                    "baseline_per_net_wire_length_um"
                ],
                "single_row_optimal_tracks_wire_length_um": floorplan[
                    "single_row_optimal_tracks_wire_length_um"
                ],
                "wire_length_um": floorplan["wire_length_um"],
                "per_net_wire_length_um": floorplan["per_net_wire_length_um"],
                "per_net_pin_count": floorplan["per_net_pin_count"],
                "group_order": floorplan["group_order"],
                "member_slots": floorplan["member_slots"],
                "track_order": floorplan["track_order"],
                "passes": floorplan["passes"],
            }
        (out_dir / f"compose.{block['name']}.json").write_text(
            json.dumps(compose, indent=2) + "\n"
        )
        block_drc = verifier.drc(
            gds_name, block["cell_name"], f"drc.{block['cell_name']}.json"
        )
        block_extract = verifier.extract(
            gds_name, block["cell_name"], f"extract.{block['cell_name']}.json"
        )
        if block_extract["ok"]:
            block_match = pll_layout._match_block_extraction(
                block, block_extract["response"]
            )
        # The reference netlist is copied into the record -- in the
        # plain-element form `mom_cap_reference` produces, so the committed
        # evidence is self-contained and `klt lvs --check` can re-hash it
        # later without reaching back out of the record directory.
        reference_name = f"{block['name']}.reference.spice"
        (out_dir / reference_name).write_text(
            mom_cap_reference((netlist_dir / f"{block['name']}.spice").read_text())
        )
        block_lvs = _lvs_summary(
            verifier.lvs(
                gds_name,
                block["cell_name"],
                reference_name,
                f"lvs.{block['name']}.request.json",
                f"lvs.{block['name']}.json",
            )
        )

    devices_drawn = sum(r["count"] for r in group_results if r.get("attempted"))
    devices_matched = sum(
        r["count"] for r in group_results if r.get("match", {}).get("matched")
    )
    devices_drc_clean = sum(
        r["count"] for r in group_results if r.get("drc", {}).get("clean")
    )
    return {
        "name": block["name"],
        "cell_name": block["cell_name"],
        "device_count": block["device_count"],
        "group_count": len(block["groups"]),
        "groups_drawn": len(drawn_groups),
        "devices_drawn": devices_drawn,
        "devices_drc_clean": devices_drc_clean,
        "devices_matched": devices_matched,
        "results": group_results,
        "composed": compose is not None,
        "compose": compose,
        "routed_nets": (compose["routing"]["net_count"] if compose else 0),
        "incomplete_nets": (
            len({n["net"] for n in compose["routing"]["incomplete_nets"]})
            if compose
            else 0
        ),
        "block_drc_clean": bool(block_drc and block_drc["clean"]),
        "block_drc_violations": (
            block_drc["response"].get("violation_count") if block_drc else None
        ),
        "block_extract_ok": bool(block_extract and block_extract["ok"]),
        "block_match": block_match,
        "block_lvs": block_lvs,
    }


def build(
    plan: dict[str, Any], verifier: Verifier, out_dir: Path, netlist_dir: Path
) -> dict[str, Any]:
    blocks = [build_block(b, verifier, out_dir, netlist_dir) for b in plan["blocks"]]
    return {
        "gen_compose_probe": cmos5l_probes.probe_gen_compose_router(
            verifier, out_dir
        ),
        "gen_compose_block_probe": cmos5l_probes.probe_gen_compose_block_routing(
            plan, blocks, verifier, out_dir
        ),
        "generator_footprint_probe": cmos5l_probes.probe_generator_footprints(
            plan, verifier, out_dir
        ),
        "blocks": blocks,
    }


# --- CLI -------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--netlist-dir",
        type=Path,
        default=Path("design/sg13cmos5l/netlist"),
        help="directory containing <block>.spice for each of BLOCK_ORDER",
    )
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--klt", default="klt")
    ap.add_argument("--deck", default=DEFAULT_DECK)
    ap.add_argument("--pdk", default=DEFAULT_PDK)
    ap.add_argument("--pdk-root", default=None)
    ap.add_argument(
        "--plan-only",
        action="store_true",
        help="write plan.json and stop (no PDK, no klt, no klayout needed)",
    )
    args = ap.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plan = pll_layout.build_plan(args.netlist_dir)
    promoted = promote_local_mom_caps(plan)
    plan["schema"] = "sg13g2-pll.pll_cmos5l_layout_plan/1"
    plan["pdk"] = args.pdk
    plan["deck"] = args.deck
    plan["local_mom_cap_groups"] = promoted
    (args.out_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(f"plan: {sum(b['device_count'] for b in plan['blocks'])} device(s) planned")
    if args.plan_only:
        return 0

    verifier = Verifier(args.klt, args.deck, args.pdk, args.pdk_root, args.out_dir)
    summary = build(plan, verifier, args.out_dir, args.netlist_dir)
    (args.out_dir / "build.json").write_text(json.dumps(summary, indent=2) + "\n")

    for block in summary["blocks"]:
        lvs = block.get("block_lvs") or {}
        print(
            f"  {block['name']}: {block['devices_matched']}/{block['device_count']} "
            f"matched, {block['routed_nets']} net(s) routed, block DRC "
            f"{'clean' if block['block_drc_clean'] else 'NOT clean'}, "
            f"LVS {lvs.get('status') or 'not converted'}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
