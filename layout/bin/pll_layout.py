#!/usr/bin/env python3
"""Schematic-driven, per-block PLL device-level layout (issue #13).

Reads the *authored schematics' own netlists* (`design/netlist/*.spice`,
committed by #7) and derives, deterministically, each block's device set from
them -- then drives `klt gen` to draw that device set, `klt extract` to check
each drawn group and each composed block back against the schematic's own
device set, and `klt gen-compose` to place a block's groups into one
`pll_<block>` cell. Nothing about the device set is typed in by hand here:
every planned device exists because a device card in a schematic netlist
asked for it, which is what makes "the layout matches the schematic's device
set" a checkable claim rather than an assertion.

Two halves, deliberately separated so the first is testable with no PDK and
no `klt` installed (`layout/tests/test_pll_layout_plan.py` exercises it):

1. **Plan** (pure, PDK-free): parse each block's netlist, recursively flatten
   its schematic hierarchy down to leaf devices (MOS/resistor/capacitor;
   every other model name is a locally-defined sub-block and is expanded, not
   drawn), group the leaf devices of each block into matched arrays keyed by
   `(class, W, L)`, and record what `klt gen` request each group *would* be,
   plus the `(class, w_um, l_um, count)` the group is expected to re-extract
   as. `build_plan()` returns plain JSON-serialisable data -- see
   `plan_block()`.
2. **Build** (impure): draw every group (`klt gen`), extract each drawn
   group's own GDS (`klt extract --deck sg13g2`) and compare its reported
   device set against the group's own expectation, compose each block's
   drawn groups into one `pll_<block>` cell (`klt gen-compose`, placement
   only -- no routing, per this issue's own Non-goals), and extract the
   composed block cell too, cross-checking its device-count multiset against
   the block's own schematic-derived totals. `mos_array`/`res_array` now draw
   against `sg13g2` (klayout-tools#1450/#1451, both fixed upstream --
   `layout/requirements.txt`'s own header records the pin bump this depended
   on); `cap_array` now draws `sg13g2`'s `cap_cmim` MiM capacitors too
   (klayout-tools#1461, closing #1455 -- see `layout/requirements.txt`'s own
   header for that bump). This design's other capacitor model,
   `cap_cmomi` (the SG13CMOS5L port's MoM capacitor, `pll_cmos5l_layout.py`),
   still has no generator on any `klt` release and is recorded in the plan
   (never silently dropped) but never attempted -- see
   `layout/pll/README.md`'s friction log
   (klayout-tools#1233/#1243/#1454/#1455/#1461).

Six blocks, six independent netlist files (`spec/porting-plan.md` §1.4;
`design/netlist.sh`'s own `BLOCKS` list) -- unlike a single closed-loop
top-level netlist, there is no `pll_top`-equivalent file in this design yet
(top-level integration is explicitly future work, `spec/porting-plan.md`
§3.3/§3.4), so this flow composes each block's own groups but nothing above
the per-block level.

Scope caveat, stated here because it is the honest headline of this
deliverable: this is a **device-level layout**, not a routed full-custom
one -- composition here is placement only, with no `connectivity[]`/
`routing` request (routing is a later, separate T1 checklist item, out of
scope per this issue's own Non-goals). DRC-clean and LVS-clean closure are
later T1 checklist items too. See `layout/pll/README.md` for the full "what
is and is not verified" statement.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

# --- Device model recognition ----------------------------------------------
#
# The ratified supply flavor is SG13G2's 3.3 V thick-oxide devices (DR-002
# Decision 0, spec/decision-records/DR-002-supply-device-flavor.md). These
# tables are the only place a model name is turned into a drawable
# primitive, so a stray thin-oxide (`sg13_lv_*`) or bipolar device carried in
# by a future edit cannot be silently planned -- it raises `PlanError`
# instead (and layout/tests/test_pll_layout_plan.py asserts the committed
# netlists contain none).

MOS_MODELS = {
    "sg13_hv_nmos": "nfet",
    "sg13_hv_pmos": "pfet",
}

#: model -> `klt gen res_array` `params.flavor` name. Both of this design's
#: resistor classes (design/README.md "Device choices and the LVS deck") are
#: real, separately-extractable `klt deck info --deck sg13g2` device classes,
#: and both are reachable from `res_array` as of `layout/requirements.txt`'s
#: current pin (klayout-tools#1451, fixed upstream -- see
#: layout/pll/README.md's friction log).
RESISTOR_MODELS = {
    "rppd": "rppd",
    "rhigh": "rhigh",
}

#: Capacitor models this plan recognises -- one entry per PDK the design is
#: ported to, because the two ports use physically different capacitors:
#: `cap_cmim` is SG13G2's MIM capacitor, `cap_cmomi` is the SG13CMOS5L port's
#: metal-oxide-metal replacement (the MIM->MoM swap DR-004/issue #22
#: ratified, because CMOS5L forbids the MIM plate layers outright).
CAP_MODELS = {
    "cap_cmim": "cap_cmim",
    "cap_cmomi": "cap_cmomi",
}

#: `klt gen` generator name for each capacitor model, or `None` if no
#: generator exists on any `klt` release yet. `cap_cmim` draws via
#: `cap_array` as of `klayout-tools#1461` (closing #1455) --
#: `layout/requirements.txt`'s own header records the pin bump this depended
#: on. `cap_cmomi` has no generator on any `klt` release
#: (:data:`BLOCKED_REASONS` records its own tracked upstream reason); per
#: issue #13's own Non-goals, a capacitor device with no generator is
#: recorded in the plan (so it is never silently dropped) but never
#: attempted in the build step.
CAP_GENERATORS: dict[str, str | None] = {
    "cap_cmim": "cap_array",
    "cap_cmomi": None,
}

LEAF_MODELS = set(MOS_MODELS) | set(RESISTOR_MODELS) | set(CAP_MODELS)

#: The six blocks `spec/porting-plan.md` §1.4 and `design/netlist.sh`'s own
#: `BLOCKS` array name, in that script's own order.
BLOCK_ORDER = ["pfd", "cp", "loop_filter", "vco", "divider_chain", "lock_detector"]


class PlanError(Exception):
    """The schematic netlist contains something this builder cannot plan."""


# --- 1. Netlist parsing + recursive flattening (pure, PDK-free) ------------


def read_cards(netlist_text: str) -> dict[str, dict[str, Any]]:
    """Parse a flat SPICE netlist into `{subckt: {"ports": [...], "cards": [...]}}`.

    Handles xschem's `+` continuation lines and its `*`-comment convention.
    An instance card is `{name, model, nets, params}` -- the trailing tokens
    of the form `k=v` are params (key lower-cased; SG13G2's own netlists
    write `w=`/`l=`/`ng=`/`m=`/`b=` in lowercase, unlike sky130's uppercase
    `W=`/`L=`), and the last remaining positional token is the model/subckt
    name, with every earlier positional token an ordered net.
    """
    joined: list[str] = []
    for raw in netlist_text.splitlines():
        line = raw.rstrip()
        if line.startswith("+") and joined:
            joined[-1] = joined[-1] + " " + line[1:].strip()
        else:
            joined.append(line)

    blocks: dict[str, dict[str, Any]] = {}
    current: str | None = None
    for line in joined:
        stripped = line.strip()
        # xschem comments out the *top-level* subcircuit's own header/footer
        # ("**.subckt <top> ..." / "**.ends") while emitting its instance
        # cards uncommented (design/netlist.sh promotes these back to real
        # `.subckt`/`.ends` at export time -- see that script's
        # `export_block`), so by the time this parser sees a committed
        # `design/netlist/*.spice` file, every subckt header is already
        # real. The `**.` unwrap stays here defensively in case this module
        # is ever pointed at a raw, un-promoted xschem export.
        if stripped.startswith("**.subckt") or stripped.startswith("**.ends"):
            stripped = stripped[2:]
        if not stripped or stripped.startswith("*"):
            continue
        lowered = stripped.lower()
        if lowered.startswith(".subckt"):
            tokens = stripped.split()
            current = tokens[1]
            blocks[current] = {"ports": tokens[2:], "cards": []}
            continue
        if lowered.startswith(".ends"):
            current = None
            continue
        if stripped.startswith("."):
            continue
        if current is None:
            continue

        tokens = stripped.split()
        params: dict[str, str] = {}
        positional: list[str] = []
        for token in tokens[1:]:
            if "=" in token:
                key, value = token.split("=", 1)
                params[key.lower()] = value
            else:
                positional.append(token)
        if len(positional) < 1:
            raise PlanError(f"unparsable instance card: {stripped!r}")
        blocks[current]["cards"].append(
            {
                "name": tokens[0],
                "model": positional[-1],
                "nets": positional[:-1],
                "params": params,
            }
        )
    return blocks


def _um(params: dict[str, str], key: str, device_name: str) -> float:
    raw = params.get(key)
    if raw is None:
        raise PlanError(f"{device_name}: no {key!r} param")
    text = raw[:-1] if raw.endswith(("u", "U")) else raw
    try:
        return float(text)
    except ValueError as exc:  # pragma: no cover - malformed netlist
        raise PlanError(f"{device_name}: {key}={raw!r} is not a number") from exc


def _resolve_net(net: str, path_prefix: str, net_map: dict[str, str]) -> str:
    """Resolve one net name used inside a subckt body to its flattened name.

    xschem's global-net convention is a trailing `!` (`VDD!`, `GND!`, ...):
    a global net is the *same* net at every level of hierarchy and is never
    remapped or prefixed. None of this design's committed netlists actually
    use one today (every supply crosses a block boundary as an ordinary
    port, e.g. `VDD_VCO`), but the convention is honored here defensively --
    `sub!` (the resistor body/bulk tie every `rppd`/`rhigh` instance in this
    design connects to) is exactly this case: a single global substrate net,
    named identically at every level it appears, on purpose.

    A net that is one of the enclosing subckt's own ports resolves to
    whatever net the caller connected there (`net_map`). Anything else is
    genuinely local to this particular instantiation and is namespaced by
    `path_prefix` so two instances of the same leaf subckt (e.g.
    `divider_chain`'s six `div23_cell` instances) never collide.
    """
    if net.endswith("!"):
        return net
    if net in net_map:
        return net_map[net]
    return path_prefix + net


def flatten_block(
    blocks: dict[str, dict[str, Any]], top: str
) -> list[dict[str, Any]]:
    """Recursively expand `top`'s own instance hierarchy to leaf devices.

    Every instance card whose model is a locally-defined subckt (not one of
    `LEAF_MODELS`) is expanded in place, with its own nets resolved through
    the parent's port-to-net connections (`_resolve_net`) and its own
    internal nets namespaced by the accumulated hierarchical path. The
    result is a flat list of `{path, model, nets, params}`, where `path` is
    a dotted instance path back to the schematic (e.g.
    `"XD0.XN3.XMP1"` inside `divider_chain`), preserving full traceability
    to the source schematic without ever hand-declaring a device.
    """
    if top not in blocks:
        raise PlanError(f"netlist has no .subckt {top!r}")

    out: list[dict[str, Any]] = []

    def walk(name: str, path_prefix: str, net_map: dict[str, str]) -> None:
        for card in blocks[name]["cards"]:
            nets = [_resolve_net(n, path_prefix, net_map) for n in card["nets"]]
            model = card["model"]
            if model in LEAF_MODELS:
                out.append(
                    {
                        "path": path_prefix + card["name"],
                        "model": model,
                        "nets": nets,
                        "params": card["params"],
                    }
                )
            elif model in blocks:
                ports = blocks[model]["ports"]
                if len(ports) != len(nets):
                    raise PlanError(
                        f"{path_prefix}{card['name']}: {model} declares "
                        f"{len(ports)} port(s) but is instantiated with "
                        f"{len(nets)} net(s)"
                    )
                child_map = dict(zip(ports, nets))
                walk(model, f"{path_prefix}{card['name']}.", child_map)
            else:
                raise PlanError(
                    f"{path_prefix}{card['name']}: no layout primitive is "
                    f"defined for model {model!r} (if this is a new device "
                    "class, extend MOS_MODELS/RESISTOR_MODELS/CAP_MODELS in "
                    "layout/bin/pll_layout.py rather than drawing it as "
                    "something it is not; if it is a new leaf subckt, "
                    "check the netlist was generated by design/netlist.sh)"
                )

    walk(top, "", {})
    return out


def assert_ratified_device_flavor(devices: list[dict[str, Any]]) -> None:
    """Guard DR-002 Decision 0: every MOS device is 3.3 V thick-oxide CMOS.

    Raises `PlanError` naming the offending device on any `sg13_lv_*`
    (thin-oxide) or bipolar model, so a future flavor regression cannot be
    planned silently. Mirrors sky130-pll's own core-flavor-only assertion,
    adapted to SG13G2's thick-/thin-oxide split (`spec/decision-records/
    DR-002-supply-device-flavor.md` Decision 0).
    """
    allowed = set(MOS_MODELS)
    for device in devices:
        model = device["model"]
        if model.startswith("sg13_") and "mos" in model and model not in allowed:
            raise PlanError(
                f"{device['path']}: model {model!r} is not the ratified "
                f"device flavor (DR-002 Decision 0 requires one of "
                f"{sorted(allowed)}) -- refusing to plan a flavor "
                "regression silently"
            )


# --- 2. Grouping into `klt gen` requests (pure, PDK-free) -------------------


def factor_rows_cols(count: int) -> tuple[int, int]:
    """Pick a `(rows, cols)` pair whose product is exactly `count`.

    Exactly -- never rounded up -- so an array never draws a device the
    schematic did not ask for. `rows` is the largest divisor of `count` at
    or below its square root, keeping the array as close to square as its
    own factorization allows (18 -> 3x6, 6 -> 2x3, 5 -> 1x5, 1 -> 1x1).
    """
    if count < 1:
        raise PlanError(f"cannot lay out a group of {count} devices")
    rows = 1
    for candidate in range(1, int(math.isqrt(count)) + 1):
        if count % candidate == 0:
            rows = candidate
    return rows, count // rows


def _slug(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


#: Why a capacitor model with no entry in `CAP_GENERATORS` (i.e. mapped to
#: `None`) is recorded but never attempted by the build step -- the only
#: still-blocked case is `cap_cmomi` (SG13CMOS5L). `mos_array`/`res_array`
#: drew against `sg13g2` as of klt commit
#: `5482cfe1c67eacf9d2f27d750a11a37ec14b1984` (klayout-tools#1450/#1451,
#: both fixed upstream -- see `layout/requirements.txt`'s own header), and
#: `cap_cmim` (SG13G2's own MIM capacitor) drew as of klt commit
#: `fdf04f71ab39159838acb86e63a92d6fa0c714fa` (klayout-tools#1461, closing
#: #1455 -- see `layout/requirements.txt`'s own header for that bump), so
#: none of them carry a reason here any more; a real `klt gen`/`klt extract`
#: result is what the build step now records for them instead of an
#: assumption. Keyed by the *model name*, not by `kind`: the two ports'
#: capacitors are physically different devices with separately-tracked
#: upstream histories, so a single "capacitor" string would misattribute
#: one port's gap to the other.
BLOCKED_REASONS = {
    "cap_cmomi": (
        "SG13CMOS5L has no MIM capacitor at all (its plate layers are on "
        "cmos5l's own DRC/LVS forbidden-layer lists), so this design's "
        "MIM->MoM swap (DR-004 / issue #22) lands on cap_cmomi -- and "
        "neither half of the tooling covers it. Draw side: klt gen "
        "cap_array reports 'PDK family sg13cmos5l has no MiM capacitor "
        "plate layers configured -- supported families: sky130, sg13g2' -- "
        "re-verified as a non-regression check for issue #31 at "
        "klt 0.3.0+gfdf04f71ab39 (fdf04f71ab39159838acb86e63a92d6fa0c714fa), "
        "i.e. *after* klayout-tools#1461 gave sg13g2 its own MiM plate-layer "
        "configuration (the message's supported-families list grew by one "
        "entry as a result), but sg13cmos5l itself is still absent -- MoM "
        "still has no generator on any family. Verify side: the curated "
        "sg13cmos5l extraction deck's EXTRACTION_DECK.capacitors is still "
        "empty, so a hand-drawn MoM capacitor extracts as no device at all "
        "(klayout-tools#1463, open, filed by issue #24's pass; "
        "klayout-tools#1466 is the follow-on it spawned on what "
        "device-recognition shape a MoM plate pair actually needs). "
        "Recorded here, never drawn, never silently dropped"
    ),
}


def plan_block(block_name: str, devices: list[dict[str, Any]]) -> dict[str, Any]:
    """Group one block's flattened leaf devices into `klt gen` group plans."""
    mos: dict[tuple[str, float, float], list[dict[str, Any]]] = {}
    res: dict[tuple[str, float, float], list[dict[str, Any]]] = {}
    caps: list[dict[str, Any]] = []

    for device in devices:
        model = device["model"]
        name = device["path"]
        if model in MOS_MODELS:
            key = (
                MOS_MODELS[model],
                _um(device["params"], "w", name),
                _um(device["params"], "l", name),
            )
            mos.setdefault(key, []).append(device)
        elif model in RESISTOR_MODELS:
            key = (
                RESISTOR_MODELS[model],
                _um(device["params"], "w", name),
                _um(device["params"], "l", name),
            )
            res.setdefault(key, []).append(device)
        elif model in CAP_MODELS:
            caps.append(device)
        else:  # pragma: no cover - unreachable, flatten_block already guards
            raise PlanError(f"{name}: unclassified model {model!r}")

    groups: list[dict[str, Any]] = []

    for (flavor, w_um, l_um), members in sorted(mos.items()):
        count = len(members)
        rows, cols = factor_rows_cols(count)
        group_id = f"{block_name}_{flavor}_w{_slug(w_um)}_l{_slug(l_um)}"
        groups.append(
            {
                "id": group_id,
                "kind": "mos_array",
                "generator": "mos_array",
                "params": {
                    "w_um": w_um,
                    "l_um": l_um,
                    "rows": rows,
                    "cols": cols,
                    "dummy": 0,
                    "flavor": flavor,
                    "topology": "common_centroid" if count % 2 == 0 else "array",
                    "gate_contact": True,
                },
                "count": count,
                # What `klt extract --deck sg13g2` should report back for
                # this group once drawn: one device per unit, all sharing
                # this group's own (class, W, L) -- the schematic-vs-layout
                # cross-check the build step performs.
                "expected": {"class": flavor, "w_um": w_um, "l_um": l_um, "count": count},
                "members": [
                    {
                        "device": member["path"],
                        "unit": index,
                        # SG13G2 MOS cards are `X<name> D G S B <model>`.
                        "ports": {
                            f"U{index}_D": member["nets"][0],
                            f"U{index}_G": member["nets"][1],
                            f"U{index}_S": member["nets"][2],
                            f"U{index}_B": member["nets"][3],
                        },
                    }
                    for index, member in enumerate(members)
                ],
            }
        )

    for (flavor, w_um, l_um), members in sorted(res.items()):
        count = len(members)
        group_id = f"{block_name}_res{flavor}_w{_slug(w_um)}_l{_slug(l_um)}"
        groups.append(
            {
                "id": group_id,
                "kind": "res_array",
                "generator": "res_array",
                "params": {
                    "length_um": l_um,
                    "width_um": w_um,
                    "num": count,
                    "dummy": 0,
                    "rows": 1,
                    "flavor": flavor,
                },
                "count": count,
                "expected": {"class": flavor, "w_um": w_um, "l_um": l_um, "count": count},
                "members": [
                    {
                        "device": member["path"],
                        "unit": index,
                        # `X<name> A B BULK <model>`.
                        "ports": {
                            f"R{index}_A": member["nets"][0],
                            f"R{index}_B": member["nets"][1],
                            f"R{index}_BULK": member["nets"][2],
                        },
                    }
                    for index, member in enumerate(members)
                ],
            }
        )

    for member in sorted(caps, key=lambda d: d["path"]):
        w_um = _um(member["params"], "w", member["path"])
        l_um = _um(member["params"], "l", member["path"])
        model = member["model"]
        generator = CAP_GENERATORS[model]
        group: dict[str, Any] = {
            "id": f"{block_name}_{member['path']}",
            "kind": "capacitor",
            "generator": generator,
            "count": 1,
            "members": [
                {
                    "device": member["path"],
                    "unit": 0,
                    # `X<name> TOP BOT <model>`.
                    "ports": {
                        "TOP": member["nets"][0],
                        "BOT": member["nets"][1],
                    },
                }
            ],
        }
        if generator is not None:
            # `klt gen cap_array` draws a *square* plate here (every drawn
            # unit capacitor in this design has w == l -- see
            # design/netlist/*.spice); `num: 1` mirrors this plan's
            # one-group-per-instance shape for capacitors (unlike
            # mos_array/res_array, which batch same-(class, W, L) devices
            # into one group). `klt extract` reports a MiM cap's own
            # geometric overlap as `area_um2`/`perimeter_um`, not `w_um`/
            # `l_um` (there is no single "W"/"L" for a two-plate device) --
            # see `_match_group_extraction`'s area/perimeter branch.
            group["params"] = {
                "plate_w_um": w_um,
                "plate_h_um": l_um,
                "num": 1,
            }
            group["expected"] = {
                "class": model,
                "area_um2": w_um * l_um,
                "perimeter_um": 2.0 * (w_um + l_um),
                "count": 1,
            }
        else:
            group["params"] = {"w_um": w_um, "l_um": l_um, "model": model}
            group["expected"] = None
            group["blocked_reason"] = BLOCKED_REASONS[model]
        groups.append(group)

    return {
        "name": block_name,
        "cell_name": f"pll_{block_name}",
        "device_count": len(devices),
        "groups": groups,
    }


def build_plan(netlist_dir: Path) -> dict[str, Any]:
    """Derive the whole layout plan from `design/netlist/*.spice`."""
    blocks_plan: list[dict[str, Any]] = []
    for block_name in BLOCK_ORDER:
        netlist_path = netlist_dir / f"{block_name}.spice"
        if not netlist_path.is_file():
            raise PlanError(f"missing netlist: {netlist_path}")
        blocks = read_cards(netlist_path.read_text())
        devices = flatten_block(blocks, block_name)
        assert_ratified_device_flavor(devices)
        blocks_plan.append(plan_block(block_name, devices))

    return {
        "schema": "sg13g2-pll.pll_layout_plan/1",
        "device_flavor": (
            "sg13_hv_nmos/sg13_hv_pmos (3.3V thick-oxide CMOS) throughout, "
            "per spec/decision-records/DR-002-supply-device-flavor.md "
            "Decision 0"
        ),
        "blocks": blocks_plan,
    }


def plan_totals(plan: dict[str, Any]) -> dict[str, int]:
    """Device totals per primitive kind, for the record's cross-check table."""
    totals: dict[str, int] = {}
    for block in plan["blocks"]:
        for group in block["groups"]:
            totals[group["kind"]] = totals.get(group["kind"], 0) + group["count"]
    return totals


# --- 3. Build: draw, extract, compose (impure: runs `klt`) ------------------

#: Floating-point tolerance (um / ohm-independent, since `klt extract`
#: reports back the same `w_um`/`l_um` units this plan requested) for the
#: schematic-vs-extracted W/L cross-check. Comfortably above any rounding
#: `klt gen`/`klt extract` themselves introduce (both reported exact
#: round-trip values in every group observed while building this flow), so a
#: mismatch this loose still means the layout and the schematic disagree.
DEVICE_MATCH_TOL_UM = 1e-6

#: Floating-point tolerance for the capacitor schematic-vs-extracted
#: area/perimeter cross-check (um^2 for `area_um2`, um for `perimeter_um`).
#: A drawn `cap_array` unit's plate is an exact rectangle and `klt extract`
#: computes both from the actual drawn geometry, so this is a sanity
#: tolerance against floating-point/DBU-snapping noise, not a real physical
#: margin -- comfortably above the 1e-3 dbu_um `klt extract --deck sg13g2`
#: reports (0.001 um), well below any real drawing/extraction disagreement.
CAP_MATCH_TOL_UM2 = 1e-3

#: Spacing left between placed groups inside a block's composed cell (um).
#: Comfortably above every curated-deck same-layer spacing rule (placement
#: only -- no routing, so this is not itself DRC-checked here), mirroring
#: sky130-pll's own `GROUP_SPACING_UM`.
GROUP_SPACING_UM = 4.0

#: Shelf-packer target width for a block's own group floorplan (um) --
#: groups are placed left to right and wrap to a new shelf past this.
BLOCK_TARGET_WIDTH_UM = 220.0


def shelf_pack(
    sizes: list[tuple[str, float, float]], target_width_um: float, spacing_um: float
) -> dict[str, dict[str, float]]:
    """Place `(id, width, height)` boxes left to right, wrapping past a width.

    Deterministic: identical input always yields identical origins, so a
    re-run of the flow produces a byte-comparable floorplan. Mirrors
    `2AMLogic/sky130-pll`'s own `shelf_pack` helper.
    """
    origins: dict[str, dict[str, float]] = {}
    x = y = shelf_height = 0.0
    for box_id, width, height in sizes:
        if x > 0.0 and x + width > target_width_um:
            y += shelf_height + spacing_um
            x = 0.0
            shelf_height = 0.0
        origins[box_id] = {"x": round(x, 3), "y": round(y, 3)}
        x += width + spacing_um
        shelf_height = max(shelf_height, height)
    return origins


class Builder:
    """Draws, extracts, and composes every planned group -- and records the
    real `klt` result for each step rather than assuming one in advance.

    Deliberately does not assume any step succeeds or fails: it runs the
    request and reports back exactly what `klt` says, which is what makes
    this build step self-correcting -- a future upstream change shows up as
    a different `devices_drawn_total`/`devices_matched_total` on the next
    re-run, with no code edit here.
    """

    def __init__(
        self,
        klt: str,
        pdk: str,
        pdk_root: str | None,
        deck: str,
        out_dir: Path,
    ) -> None:
        self.klt = klt
        self.pdk = pdk
        self.pdk_root = pdk_root
        self.deck = deck
        self.out_dir = out_dir

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.klt, *args], capture_output=True, text=True, cwd=self.out_dir
        )

    @staticmethod
    def _parse_json_envelope(proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        # `klt ... --format json` writes its JSON envelope to stdout on
        # success but to stderr on error (confirmed directly, not assumed --
        # see layout/pll/README.md's friction log) -- try whichever stream is
        # non-empty so a captured error is never silently swallowed as `{}`.
        raw = proc.stdout.strip() or proc.stderr.strip()
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {"unparsed_output": raw}

    def gen_group(self, group: dict[str, Any]) -> dict[str, Any]:
        """Draw one group (`klt gen mos_array`/`res_array`). Never raises --
        a `klt` failure is a *result* this build step records, not an
        exception this driver crashes on."""
        cell = group["id"]
        args = [
            "gen",
            group["generator"],
            "--pdk",
            self.pdk,
            "--params",
            json.dumps(group["params"]),
            "--cell-name",
            cell,
            "-o",
            f"{cell}.gds",
            "--format",
            "json",
        ]
        if self.pdk_root:
            args[1:1] = ["--pdk-root", self.pdk_root]
        proc = self._run(args)
        report = self._parse_json_envelope(proc)
        result = {
            "group_id": cell,
            "attempted": True,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0 and "error" not in report,
            "response": report,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
        (self.out_dir / f"gen.{cell}.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        return result

    def extract(self, gds_path: str, top: str, report_name: str) -> dict[str, Any]:
        """Run `klt extract --deck <deck>` against one drawn/composed stream.
        Never raises -- an extraction failure is a recorded result."""
        args = [
            "extract",
            "--deck",
            self.deck,
            gds_path,
            "--top",
            top,
            "--format",
            "json",
        ]
        proc = self._run(args)
        report = self._parse_json_envelope(proc)
        result = {
            "top": top,
            "attempted": True,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0 and report.get("status") == "extracted",
            "response": report,
            "stderr": proc.stderr.strip(),
        }
        (self.out_dir / report_name).write_text(json.dumps(result, indent=2) + "\n")
        return result

    def compose_block(
        self,
        block: dict[str, Any],
        drawable_groups: list[dict[str, Any]],
        gen_results: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Place a block's own successfully-drawn groups into one
        `pll_<block>` cell (`klt gen-compose`, placement only -- no
        `connectivity[]`/`routing`, since routing is out of scope per this
        issue's own Non-goals). Never raises."""
        cell_name = block["cell_name"]
        sizes = []
        blocks_field = []
        for group in drawable_groups:
            report = gen_results[group["id"]]["response"]
            bbox = report["bbox_um"]
            sizes.append((group["id"], bbox["x1"] - bbox["x0"], bbox["y1"] - bbox["y0"]))
            blocks_field.append({"id": group["id"], "generator_report": report})
        origins = shelf_pack(sizes, BLOCK_TARGET_WIDTH_UM, GROUP_SPACING_UM)
        request = {
            "schema": "klt.gen_compose.request/1",
            "pdk": {"variant": self.pdk},
            "blocks": blocks_field,
            "placement": {
                "strategy": "explicit",
                "order": [group["id"] for group in drawable_groups],
                "origins_um": origins,
            },
            "options": {"cell_name": cell_name, "output": f"{cell_name}.gds"},
        }
        request_path = self.out_dir / f"compose.{block['name']}.request.json"
        request_path.write_text(json.dumps(request, indent=2) + "\n")
        proc = self._run(["gen-compose", request_path.name, "--format", "json"])
        report = self._parse_json_envelope(proc)
        result = {
            "cell_name": cell_name,
            "attempted": True,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0 and "error" not in report,
            "response": report,
            "stderr": proc.stderr.strip(),
        }
        (self.out_dir / f"compose.{block['name']}.response.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        return result


def _match_group_extraction(
    group: dict[str, Any], extract_report: dict[str, Any]
) -> dict[str, Any]:
    """Compare one group's own drawn-and-extracted device set against its
    `expected` -- the schematic-vs-layout cross-check this issue's own pass
    condition asks for. Two shapes of `expected`, keyed by which dimension
    fields it carries: a MOS/resistor group's `(class, w_um, l_um, count)`
    (a single W/L pair defines the device), or a MiM-capacitor group's
    `(class, area_um2, perimeter_um, count)` -- `klt extract` reports a
    two-plate capacitor's geometric overlap as area/perimeter, not a single
    W/L, so there is no `w_um`/`l_um` to compare for that `kind`."""
    expected = group["expected"]
    devices = extract_report.get("devices", [])
    mismatches: list[str] = []
    if len(devices) != expected["count"]:
        mismatches.append(
            f"expected {expected['count']} device(s), extracted {len(devices)}"
        )
    dimension_keys = (
        ("w_um", "l_um", DEVICE_MATCH_TOL_UM)
        if "w_um" in expected
        else ("area_um2", "perimeter_um", CAP_MATCH_TOL_UM2)
    )
    for device in devices:
        if device.get("class") != expected["class"]:
            mismatches.append(
                f"{device.get('name')}: class {device.get('class')!r} != "
                f"expected {expected['class']!r}"
            )
            continue
        params = device.get("params", {})
        for key in dimension_keys[:2]:
            got = params.get(key)
            want = expected[key]
            if got is None or abs(got - want) > dimension_keys[2]:
                mismatches.append(
                    f"{device.get('name')}: {key}={got!r} != expected {want!r}"
                )
    return {"matched": not mismatches, "mismatches": mismatches}


def _match_block_extraction(
    block: dict[str, Any], extract_report: dict[str, Any]
) -> dict[str, Any]:
    """Compare a composed block cell's own extracted device-class counts
    against the block's schematic-derived totals (drawable groups only --
    a group whose `generator` is `None` is never drawn/composed, see
    BLOCKED_REASONS -- checked per-group, not per-`kind`, since `kind ==
    "capacitor"` covers both a drawable model (`cap_cmim`) and a blocked one
    (`cap_cmomi`))."""
    expected_counts: dict[str, int] = {}
    for group in block["groups"]:
        if group.get("generator") is not None:
            expected_counts[group["expected"]["class"]] = (
                expected_counts.get(group["expected"]["class"], 0) + group["count"]
            )
    got_counts = extract_report.get("device_counts", {})
    mismatches = [
        f"class {cls!r}: expected {count}, extracted {got_counts.get(cls, 0)}"
        for cls, count in sorted(expected_counts.items())
        if got_counts.get(cls, 0) != count
    ]
    # A class the composed cell reports that the schematic did not expect at
    # all is also a mismatch (e.g. an extraction picking up stray geometry).
    mismatches += [
        f"class {cls!r}: extracted {count}, not expected at all"
        for cls, count in sorted(got_counts.items())
        if cls not in expected_counts and count
    ]
    return {
        "expected_counts": expected_counts,
        "extracted_counts": got_counts,
        "matched": not mismatches,
        "mismatches": mismatches,
    }


def attempt_build(plan: dict[str, Any], builder: Builder) -> dict[str, Any]:
    """Draw, extract, and compose every block; skip only groups with no
    generator (`generator is None` -- a still-blocked capacitor model, see
    BLOCKED_REASONS[<model>] and issue #13's own Non-goals). A group is
    "drawable" by its own `generator` field, not by `kind`: `kind ==
    "capacitor"` covers both `cap_cmim` (drawn via `cap_array`) and
    `cap_cmomi` (still blocked)."""
    summary: dict[str, Any] = {"blocks": []}
    for block in plan["blocks"]:
        group_results = []
        gen_reports: dict[str, dict[str, Any]] = {}
        drawable_groups = [g for g in block["groups"] if g["generator"] is not None]
        for group in block["groups"]:
            if group["generator"] is None:
                group_results.append(
                    {
                        "group_id": group["id"],
                        "attempted": False,
                        "ok": False,
                        "reason": group["blocked_reason"],
                    }
                )
                continue
            gen_result = builder.gen_group(group)
            gen_reports[group["id"]] = gen_result
            result: dict[str, Any] = {
                "group_id": group["id"],
                "gen": gen_result,
            }
            if gen_result["ok"]:
                cell = group["id"]
                extract_result = builder.extract(
                    f"{cell}.gds", cell, f"extract.{cell}.json"
                )
                result["extract"] = extract_result
                if extract_result["ok"]:
                    result["match"] = _match_group_extraction(
                        group, extract_result["response"]
                    )
                else:
                    result["match"] = {"matched": False, "mismatches": ["extraction failed"]}
            else:
                result["match"] = {"matched": False, "mismatches": ["draw failed"]}
            result["ok"] = (
                gen_result["ok"]
                and result.get("extract", {}).get("ok", False)
                and result["match"]["matched"]
            )
            group_results.append(result)

        drawn_groups = [
            g for g in drawable_groups if gen_reports.get(g["id"], {}).get("ok")
        ]
        compose_result = None
        block_extract_result = None
        block_match = None
        if drawn_groups:
            compose_result = builder.compose_block(
                block, drawn_groups, {gid: r for gid, r in gen_reports.items()}
            )
            if compose_result["ok"]:
                block_extract_result = builder.extract(
                    compose_result["response"]["gds_path"],
                    block["cell_name"],
                    f"extract.{block['cell_name']}.json",
                )
                if block_extract_result["ok"]:
                    block_match = _match_block_extraction(
                        block, block_extract_result["response"]
                    )

        devices_drawn = sum(
            g["count"]
            for g, r in zip(block["groups"], group_results)
            if r.get("gen", {}).get("ok")
        )
        devices_matched = sum(
            g["count"]
            for g, r in zip(block["groups"], group_results)
            if r.get("match", {}).get("matched")
        )
        summary["blocks"].append(
            {
                "name": block["name"],
                "cell_name": block["cell_name"],
                "group_count": len(block["groups"]),
                "groups_drawn": sum(1 for r in group_results if r.get("gen", {}).get("ok")),
                "device_count": block["device_count"],
                "devices_drawn": devices_drawn,
                "devices_matched": devices_matched,
                "results": group_results,
                "composed": compose_result is not None and compose_result["ok"],
                "compose": compose_result,
                "block_extract_ok": bool(
                    block_extract_result and block_extract_result["ok"]
                ),
                "block_match": block_match,
            }
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--netlist-dir",
        type=Path,
        default=Path("design/netlist"),
        help="directory containing <block>.spice for each of BLOCK_ORDER",
    )
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--klt", default="klt")
    ap.add_argument("--pdk", default="ihp-sg13g2")
    ap.add_argument("--pdk-root", default=None)
    ap.add_argument(
        "--deck",
        default="sg13g2",
        help="klt extract --deck name (distinct from --pdk's variant name)",
    )
    ap.add_argument(
        "--plan-only",
        action="store_true",
        help="write plan.json and stop (no PDK or klt needed)",
    )
    args = ap.parse_args(argv)

    plan = build_plan(args.netlist_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    totals = plan_totals(plan)
    print(json.dumps(totals, indent=2))
    if args.plan_only:
        return 0

    builder = Builder(args.klt, args.pdk, args.pdk_root, args.deck, args.out_dir)
    summary = attempt_build(plan, builder)
    summary["totals"] = totals
    summary["devices_drawn_total"] = sum(
        b["devices_drawn"] for b in summary["blocks"]
    )
    summary["devices_matched_total"] = sum(
        b["devices_matched"] for b in summary["blocks"]
    )
    (args.out_dir / "build.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps(
            {
                "devices_drawn_total": summary["devices_drawn_total"],
                "devices_matched_total": summary["devices_matched_total"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
