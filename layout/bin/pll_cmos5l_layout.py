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
  outright (the gap klayout-tools#1462 tracked, closed upstream 2026-08-30;
  re-probed on every run by :func:`probe_gen_compose_router`, whose raw
  responses are committed in each record -- the probe now reports that gap
  fixed at a pin on or after that closure) and because past that fix
  `gen-compose`'s router was separately measured routing only 1 of this
  design's smallest block's 13 nets (klayout-tools#1467, filed by this pass
  -- see `cmos5l_route.py`'s own docstring for the measurement). That
  second measurement predates the current pin and has not been repeated
  against it, so this flow still draws and routes with its own code rather
  than switching to `klt gen-compose`'s router on the strength of an
  unconfirmed fix -- see `render-pll-cmos5l-record.py`'s own probe-outcome
  reporting and `layout/sg13cmos5l-pll/README.md`'s friction log. The
  verification half is unchanged and is still entirely `klt`'s: `klt drc
  --deck sg13cmos5l`, `klt extract --deck sg13cmos5l --pdk ihp-sg13cmos5l`
  and `klt lvs` are what produce every pass/fail claim here.

What this flow does, per block, in order:

1. **Plan** (pure, PDK-free, shared with the SG13G2 flow): parse
   `design/sg13cmos5l/netlist/<block>.spice`, flatten the schematic hierarchy
   to leaf devices, group them by `(class, W, L)`.
2. **Draw** each `mos_array`/`res_array` group as its own cell, with a shared
   NWell + n+ well tap per PMOS group and a p+ substrate tap per NMOS group
   (`cmos5l_devices.draw_pfet_array_well`/`draw_nfet_array_tap`).
3. **DRC** each drawn group (`klt drc --deck sg13cmos5l`).
4. **Extract** each drawn group and compare the reported `(class, W, L, count)`
   against the group's own schematic-derived expectation.
5. **Compose** every drawn group of a block into one `pll_<block>` cell,
   placed in a single left-to-right row.
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
recorded in the plan and never drawn -- see
`pll_layout.BLOCKED_REASONS["cap_cmomi"]` for the two tracked upstream reasons
(klayout-tools#1462 and #1463).

Nothing here relaxes a claim to make it pass: every `klt` invocation's raw
JSON response is written into the record directory, and the summary is derived
from those responses rather than asserted alongside them.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cmos5l_devices as dev  # noqa: E402
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
#: :func:`cmos5l_devices.draw_hv_mos` draws, on the narrowest device this
#: design has (`w = 2 um`). They are 0.6 um apart -- one
#: :data:`cmos5l_devices.ROUTE_PITCH_UM` -- and the gate's own column sits a
#: further 0.88 um to the left, off the gate landing pad.
SOURCE_RISER_DX_UM = 0.45
DRAIN_RISER_DX_UM = 1.05

#: Deck and PDK variant names. The deck name (`sg13cmos5l`) and the PDK
#: variant name (`ihp-sg13cmos5l`) are deliberately distinct -- `klt` resolves
#: them independently, and `--pdk` is what binds an extracted MOS to the
#: PDK's own `sg13_hv_nmos`/`sg13_hv_pmos` subcircuit rather than leaving it a
#: bare `nfet`/`pfet` primitive.
DEFAULT_DECK = "sg13cmos5l"
DEFAULT_PDK = "ihp-sg13cmos5l"

DRAWABLE_KINDS = ("mos_array", "res_array")

#: Explicit `klt lvs` `reference.device_map` entries for this design's two
#: drawn poly resistors, and **why they have to be written out by hand**.
#:
#: `klt lvs`'s `reference.form: "subckt-call"` converter turns the schematic
#: netlist's `X<name> ... rppd` cards into plain-element devices it can
#: compare against the extracted layout. Its per-deck conversion table --
#: what `reference.deck` selects -- is MOS-only, so it rejects `rppd`/`rhigh`
#: even though *this same deck* recognises both for extraction
#: (`EXTRACTION_DECK.resistors`, klayout-tools#1415) and `klt extract --pdk`
#: emits them bound to those very subcircuit names. Filed upstream as
#: **klayout-tools#1464**; this map is the caller-side declaration that issue
#: names as the current workaround, recorded here (rather than left implicit)
#: so it can be deleted when #1464 lands.
#:
#: There is deliberately **no `cap_cmomi` entry**: the curated `sg13cmos5l`
#: deck declares no capacitor device class at all (klayout-tools#1463), so
#: there is no class to map a MoM capacitor to. Every block that instantiates
#: one therefore cannot be LVS-converted at all -- reported as exactly that in
#: the record, never waived.
REFERENCE_DEVICE_MAP: dict[str, dict[str, str]] = {
    "rppd": {"kind": "resistor", "class": "rppd"},
    "rhigh": {"kind": "resistor", "class": "rhigh"},
}

#: The same map plus a `cap_cmomi` entry, used **only** for a clearly-labelled
#: secondary probe on the blocks whose primary LVS run cannot convert.
#:
#: Issue #24's record stated there was "no class to map a MoM capacitor to".
#: Re-measured for issue #29, that is not quite right, and the correction is
#: worth having: `reference.device_map`'s `kind` vocabulary is caller-side and
#: **does** accept `"capacitor"` on a deck whose `EXTRACTION_DECK.capacitors`
#: is empty. What klayout-tools#1463 actually blocks is the *layout* half --
#: a drawn MoM capacitor extracts as no device at all -- so mapping the
#: reference side alone converts the netlist and then reports the missing
#: capacitors as `device.unmatched` rather than refusing to compare.
#:
#: That is strictly more information than "not converted", and it is
#: deliberately **not** the primary run: a mismatch this flow induced by
#: declaring a device the layout provably cannot carry is a diagnostic, not a
#: verdict. The primary run stays honest about what the deck can do; this one
#: shows what is unmatched underneath.
CAPACITOR_PROBE_DEVICE_MAP: dict[str, dict[str, str]] = {
    **REFERENCE_DEVICE_MAP,
    "cap_cmomi": {"kind": "capacitor", "class": "cap_cmomi"},
}


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
        drawn = dev.draw_hv_mos(builder, flavor, x, base_y, w_um, l_um)
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
        device_map: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Compare one composed block against its own schematic netlist.

        `reference.form: "subckt-call"` is required, not optional: the
        committed schematic netlists instantiate the PDK's own
        `sg13_hv_nmos`/`sg13_hv_pmos` subcircuits via `X` cards, and `klt lvs`
        refuses to compare that form against extracted plain-element devices
        rather than silently degrading into a topology mismatch. Both sides
        are flattened so the comparison is device-set-vs-device-set: the
        reference is hierarchical (six `.subckt` levels deep in places) while
        the composed layout is one flat cell of per-group instances.
        """
        request = {
            "schema": "klt.lvs.request/1",
            "engine": "klayout",
            "layout": {"file": gds, "deck": self.deck, "top": top},
            "reference": {
                "netlist": reference,
                "form": "subckt-call",
                # `deck` and `device_map` are both required, and the pairing
                # is load-bearing: `device_map` alone *replaces* the curated
                # table (so the MOS subcircuits stop resolving), while `deck`
                # alone gives only that deck's MOS entries (klayout-tools#1464).
                # Together they merge -- `device_map` on top of `deck` -- which
                # is the only combination that resolves both.
                "deck": self.deck,
                "device_map": device_map or REFERENCE_DEVICE_MAP,
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


def write_cell(builder: dev.Builder, cell_name: str, path: Path) -> None:
    """Write `cell_name` (and its subtree) out as its own GDS stream."""
    import klayout.db as kdb  # local import: only needed on the impure path

    cell = builder.layout.cell(cell_name)
    if cell is None:  # pragma: no cover - defensive
        raise RuntimeError(f"no such cell: {cell_name}")
    opts = kdb.SaveLayoutOptions()
    opts.gds2_write_timestamps = False
    opts.clear_cells()
    opts.add_cell(cell.cell_index())
    builder.layout.write(str(path), opts)


# --- Placement and terminal collection --------------------------------------


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

    A net whose pin list includes a device that was never drawn (on this port,
    always one of the five `cap_cmomi` MoM capacitors) is routed between the
    terminals that *do* exist and reported here as incomplete, with the
    undrawn group's own `blocked_reason` attached. Never waived, never
    silently treated as fully routed.
    """
    notes: list[dict[str, Any]] = []
    for group in block["groups"]:
        if group["kind"] in DRAWABLE_KINDS:
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
        if group["kind"] not in DRAWABLE_KINDS:
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
        else:
            geometry = draw_res_group(builder, group)
        write_cell(builder, group["id"], out_dir / f"{group['id']}.gds")

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
        sizes = [(g["id"], *group_size_um(g)) for g in drawn_groups]
        origins = single_row_pack(sizes, GROUP_SPACING_UM)
        cell = builder.open_cell(block["cell_name"])
        for group in drawn_groups:
            origin = origins[group["id"]]
            builder.instantiate(
                cell, builder.layout.cell(group["id"]), origin["x"], origin["y"]
            )
        terminals, port_notes = collect_terminals(drawn_groups, geometries, origins)
        channel_y0 = max(height for _id, _w, height in sizes) + route.CHANNEL_GAP_UM
        routing = route.route(
            builder,
            cell,
            terminals,
            channel_y0,
            incomplete_nets=undrawn_net_notes(block),
        )
        gds_name = f"{block['cell_name']}.gds"
        write_cell(builder, block["cell_name"], out_dir / gds_name)
        compose = {
            "cell_name": block["cell_name"],
            "gds": gds_name,
            "strategy": "single_row",
            "spacing_um": GROUP_SPACING_UM,
            "placements": origins,
            "terminal_count": len(terminals),
            "unrouted_ports": port_notes,
            "routing": routing.as_dict(),
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
        # The reference netlist is copied into the record so the committed
        # evidence is self-contained and `klt lvs --check` can re-hash it
        # later without reaching back out of the record directory.
        reference_name = f"{block['name']}.reference.spice"
        (out_dir / reference_name).write_text(
            (netlist_dir / f"{block['name']}.spice").read_text()
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
        if not block_lvs["ran"]:
            # Secondary, explicitly-labelled probe: map the MoM capacitor on
            # the reference side so the comparison at least runs, and record
            # exactly what is unmatched underneath the conversion failure.
            # See CAPACITOR_PROBE_DEVICE_MAP for why this is never the
            # headline result.
            block_lvs["capacitor_probe"] = _lvs_summary(
                verifier.lvs(
                    gds_name,
                    block["cell_name"],
                    reference_name,
                    f"lvs.{block['name']}.cap-probe.request.json",
                    f"lvs.{block['name']}.cap-probe.json",
                    device_map=CAPACITOR_PROBE_DEVICE_MAP,
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


def probe_gen_compose_router(verifier: Verifier, out_dir: Path) -> dict[str, Any]:
    """Re-check, every run, whether `klt gen-compose` can route on this PDK.

    This flow routes its own interconnect (`cmos5l_route.py`) because at this
    repo's pin `klt gen-compose`'s router resolves `routing.layer_role`
    through the same per-PDK-family role->layer table every `klt gen`
    generator uses, and that table has no `sg13cmos5l` entry -- the gap
    klayout-tools#1462 tracked. That is a claim about the *tool*, and #1462
    closed upstream on 2026-08-30 (after this pin), so it is re-measured on
    every run rather than asserted: two otherwise identical `gen-compose`
    requests are sent against a throwaway two-pad cell, one placement-only
    and one with `routing`, and both raw responses are written into the
    record.

    When the routing probe starts returning exit 0 the pin has moved past
    #1462 -- at which point the second, independent reason still stands
    (klayout-tools#1467: measured 1 of 13 nets routed on this design's
    smallest block), so the probe flipping is a prompt to re-measure #1467,
    not on its own a reason to drop this flow's own router.
    """
    builder = dev.Builder()
    builder.open_cell("gencompose_probe")
    builder.box(dev.L_METAL1, 0.0, 0.0, 1.0, 0.3)
    builder.box(dev.L_METAL1, 0.0, 1.0, 1.0, 1.3)
    write_cell(builder, "gencompose_probe", out_dir / "gencompose_probe.gds")

    def _cell_block(block_id: str) -> dict[str, Any]:
        return {
            "id": block_id,
            "cell": {
                "gds_path": "gencompose_probe.gds",
                "cell_name": "gencompose_probe",
                "ports": [
                    {
                        "name": "P",
                        "x_um": 0.5,
                        "y_um": 1.15,
                        "width_um": 0.3,
                        "direction_deg": 90,
                        "layer": {"layer": 8, "datatype": 0},
                    }
                ],
            },
        }

    base = {
        "schema": "klt.gen_compose.request/1",
        "pdk": {"variant": verifier.pdk},
        "blocks": [_cell_block("a"), _cell_block("b")],
        "placement": {"strategy": "row", "order": ["a", "b"], "spacing_um": 2.0},
        "options": {"cell_name": "gencompose_probe_top", "output": "gencompose_probe_top.gds"},
    }
    routed = json.loads(json.dumps(base))
    routed["connectivity"] = [
        {"net": "PROBE", "pins": [{"block": "a", "port": "P"}, {"block": "b", "port": "P"}]}
    ]
    routed["routing"] = {"layer_role": "metal", "width_um": dev.ROUTE_W_UM}

    results: dict[str, Any] = {}
    for name, request in (("placement", base), ("routing", routed)):
        request_name = f"gen-compose.probe.{name}.request.json"
        (out_dir / request_name).write_text(json.dumps(request, indent=2) + "\n")
        result = verifier._run(["gen-compose", request_name, "--format", "json"])
        (out_dir / f"gen-compose.probe.{name}.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        results[name] = {
            "ok": result["ok"],
            "returncode": result["returncode"],
            "error": result["response"].get("error", {}).get("message"),
        }
    return results


def build(
    plan: dict[str, Any], verifier: Verifier, out_dir: Path, netlist_dir: Path
) -> dict[str, Any]:
    return {
        "gen_compose_probe": probe_gen_compose_router(verifier, out_dir),
        "blocks": [build_block(b, verifier, out_dir, netlist_dir) for b in plan["blocks"]],
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
    plan["schema"] = "sg13g2-pll.pll_cmos5l_layout_plan/1"
    plan["pdk"] = args.pdk
    plan["deck"] = args.deck
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
