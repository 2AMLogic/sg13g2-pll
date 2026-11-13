#!/usr/bin/env python3
"""Upstream-capability probes for the SG13CMOS5L PLL layout flow (issue #35).

The canary half of `pll_cmos5l_layout.py`, split out of it by issue #372.
Nothing here draws, routes or verifies the layout that flow's record makes a
claim about: these three functions re-measure, on **every** run, whether the
upstream capability this flow deliberately does *not* use yet has become
usable -- so the decision to keep drawing and routing locally
(`cmos5l_devices.py`, `cmos5l_route.py`) rests on this run's own evidence
rather than on a remembered measurement.

* :func:`probe_gen_compose_router` -- the original two-pad probe, which now
  reports the `ihp-sg13cmos5l` family accepted (klayout-tools#1462 closed
  upstream 2026-08-30, after this repo's pin).
* :func:`probe_gen_compose_block_routing` -- the same request shape against a
  **real** block (:data:`ROUTER_PROBE_BLOCK`, this design's smallest composed
  one), where `gen-compose` routes the first net and rejects the rest
  (klayout-tools#1467) and offers no second routing plane on this family to
  move them onto. This is the probe the local router's continued existence
  actually rests on; the counts it reports are whatever this run's own plan
  and composition produce, not a quoted figure.
* :func:`probe_generator_footprints` -- `klt gen mos_array`/`res_array` run
  on this design's own group parameters, which shows `mos_array` output
  extracting as the *thin*-oxide `sg13_lv_*` devices, leaving every PMOS body
  unbiased, and reporting terminal columns too tight for `cmos5l_route`'s
  risers. See `cmos5l_devices.py`'s own docstring for the three findings and
  `layout/sg13cmos5l-pll/README.md`'s friction log for what is filed
  upstream.

Every raw `klt` response these probes take is committed into the record
directory unedited, under its own `gen-compose.probe.*` / `gen.probe.*` /
`drc.genprobe_*` / `extract.genprobe_*` name, and the summaries returned here
are derived from those responses rather than asserted alongside them. The
`build.json` keys they land under (`gen_compose_probe`,
`gen_compose_block_probe`, `generator_footprint_probe`) are
`pll_cmos5l_layout.build`'s, and are what
`layout/bin/render-pll-cmos5l-record.py` reads.

**Why this is a separate module.** The probes share only the `klt` runner
(`pll_cmos5l_layout.Verifier`) and the GDS cell writer
(`cmos5l_devices.write_cell`) with the flow proper; they consume its plan and
per-block build results as plain data and hand back plain data. Keeping them
here means a change to the draw/route path and a change to a probe cannot
hide in each other's diff.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cmos5l_devices as dev  # noqa: E402

if TYPE_CHECKING:  # pragma: no cover - typing only, and a cycle at runtime
    from pll_cmos5l_layout import Verifier


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
    (klayout-tools#1467: 1 of 13 nets routed on this design's smallest
    block). This cell is far too small to exercise that second reason, so
    this probe is deliberately **not** the one that decides anything about
    the router; :func:`probe_gen_compose_block_routing` re-measures #1467
    against a real block on every run, and is what that decision rests on.
    """
    builder = dev.Builder()
    builder.open_cell("gencompose_probe")
    builder.box(dev.L_METAL1, 0.0, 0.0, 1.0, 0.3)
    builder.box(dev.L_METAL1, 0.0, 1.0, 1.0, 1.3)
    dev.write_cell(builder, "gencompose_probe", out_dir / "gencompose_probe.gds")

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
        result = verifier.gen_compose(
            request_name, f"gen-compose.probe.{name}.json"
        )
        results[name] = {
            "ok": result["ok"],
            "returncode": result["returncode"],
            "error": result["response"].get("error", {}).get("message"),
        }
    return results


#: Block the real-block `gen-compose` routing re-probe is taken against
#: (issue #35). `cp` is this design's *smallest* composed block -- 8 groups,
#: 14 devices, 13 multi-pin nets -- and is the same block klayout-tools#1467
#: was originally measured on, so the two measurements are comparable rather
#: than merely both "a real block".
ROUTER_PROBE_BLOCK = "cp"

#: The second routing plane a two-layer `gen-compose` route would need. Not a
#: guess: `routing.cross_block_layer_role` is the only mechanism `klt
#: gen-compose` has for putting a rejected net on a different metal, and
#: `"metal2"` is the role name sky130/gf180mcu expose for it. Requested here
#: purely to record, in this run's own evidence, whether this PDK family has
#: such a role at all.
ROUTER_PROBE_CROSS_LAYER_ROLE = "metal2"

#: The `mos_array` `voltage_flavor` this design's MOS devices would need.
#: DR-002 Decision 0 ratifies the **thick-gate-oxide (HV)** flavour, and the
#: committed netlists instantiate `sg13_hv_nmos`/`sg13_hv_pmos`, so a
#: generator-drawn footprint must carry `ThickGateOx` (44/0) or it extracts as
#: the thin-oxide device instead. The exact spelling is not load-bearing here:
#: `klt gen` resolves a flavour name through a per-PDK-family table, and a
#: family absent from that table resolves *every* name to no layer -- which is
#: precisely what the probe is measuring, and what its recorded
#: `drc_hints.notes` reports in the tool's own words.
MOS_VOLTAGE_FLAVOR = "thick_oxide"


def _port_column_pitch(ports: list[dict[str, Any]]) -> float | None:
    """Smallest gap between two distinct reported port x columns (um).

    :mod:`cmos5l_route`'s whole no-short claim rests on every terminal owning
    its own riser column at least :data:`cmos5l_devices.ROUTE_PITCH_UM` from
    the next (`check_riser_columns`), so this is the one number that decides
    whether a generator-drawn footprint's `ports[]` is routable *by this
    flow's router* at all.
    """
    xs = sorted({round(float(p["x_um"]), 4) for p in ports})
    if len(xs) < 2:
        return None
    return round(min(b - a for a, b in zip(xs, xs[1:])), 4)


def _extracted_models(out_dir: Path, cell_name: str) -> list[str]:
    """PDK subcircuit names `klt extract --pdk` bound a cell's devices to.

    Read back out of the written netlist rather than the JSON response,
    because the response reports the *deck* device class (`nfet`/`pfet`) while
    the PDK binding -- `sg13_hv_nmos` vs `sg13_lv_nmos`, i.e. the ratified
    thick-oxide flavour (DR-002 Decision 0) vs the thin-oxide one -- only
    appears on the emitted `X` cards.
    """
    path = out_dir / f"{cell_name}.extracted.spice"
    if not path.exists():
        return []
    models: list[str] = []
    for line in path.read_text().splitlines():
        for token in line.split():
            if token.startswith("sg13_") and token not in models:
                models.append(token)
    return sorted(models)


def probe_generator_footprints(
    plan: dict[str, Any], verifier: Verifier, out_dir: Path
) -> list[dict[str, Any]]:
    """Measure `klt gen mos_array`/`res_array` output against what this flow
    needs, every run (issue #35).

    klayout-tools#1462 -- the gap that made the local footprints necessary in
    the first place -- closed upstream, and both generators now draw on
    `ihp-sg13cmos5l`. "Draws" is not the bar, though: the footprints this flow
    substitutes have to (a) carry the ratified **thick-oxide** flavour so
    `klt extract --pdk` binds them to `sg13_hv_nmos`/`sg13_hv_pmos`, (b) put a
    biased, *schematic-named* body under every PMOS so
    `unbiased_pmos_body_nets[]` stays empty and LVS has a body net to match,
    and (c) report terminal columns at least
    :data:`cmos5l_devices.ROUTE_PITCH_UM` apart so `cmos5l_route`'s riser
    scheme can escape them.

    Each of those three is measured here, on the *design's own* group
    parameters (taken verbatim out of `plan.json`, never a synthetic device),
    and every raw `klt` response is committed. The generator's output is
    DRC'd and extracted with the same deck the drawn layout uses -- it is
    never composed, routed or LVS'd, and nothing it draws reaches the
    layout this record's verdict is about.
    """
    picks: list[tuple[str, dict[str, Any]]] = []
    ordered_blocks = sorted(
        plan["blocks"], key=lambda b: b["name"] != ROUTER_PROBE_BLOCK
    )
    for block in ordered_blocks:
        for group in block["groups"]:
            if group["kind"] == "mos_array":
                key = f"mos_{group['params']['flavor']}"
            elif group["kind"] == "res_array":
                key = "res"
            else:
                continue
            if any(name == key for name, _ in picks):
                continue
            picks.append((key, group))

    results: list[dict[str, Any]] = []
    for key, group in picks:
        cell_name = f"genprobe_{key}"
        params = dict(group["params"])
        if group["generator"] == "mos_array":
            # Ask for the thick-oxide flavour explicitly. This design's MOS
            # devices *are* the HV ones (DR-002 Decision 0), so this is the
            # request a swap would have to make -- and asking for it is what
            # makes the generator report, in its own words, whether the
            # resolved PDK family has a marker layer for it at all.
            params["voltage_flavor"] = MOS_VOLTAGE_FLAVOR
        gen_result = verifier.gen(
            group["generator"],
            params,
            cell_name,
            f"gen.probe.{key}.json",
        )
        response = gen_result["response"]
        entry: dict[str, Any] = {
            "key": key,
            "generator": group["generator"],
            "source_group": group["id"],
            "params": params,
            "drew": gen_result["ok"],
            "returncode": gen_result["returncode"],
            "error": response.get("error", {}).get("message"),
        }
        if not gen_result["ok"]:
            results.append(entry)
            continue

        ports = response.get("ports") or []
        pitch = _port_column_pitch(ports)
        drc_result = verifier.drc(
            f"{cell_name}.gds", cell_name, f"drc.{cell_name}.json"
        )
        extract_result = verifier.extract(
            f"{cell_name}.gds", cell_name, f"extract.{cell_name}.json"
        )
        extract_response = extract_result["response"]
        entry.update(
            {
                "port_names": [p["name"] for p in ports],
                "port_columns_um": sorted(
                    {round(float(p["x_um"]), 4) for p in ports}
                ),
                "min_port_column_pitch_um": pitch,
                "required_column_pitch_um": dev.ROUTE_PITCH_UM,
                "column_pitch_ok": pitch is None or pitch >= dev.ROUTE_PITCH_UM - 1e-9,
                # A body/bulk terminal this flow could route to. `mos_array`
                # names a MOS body port `U<i>_B` and `res_array` a resistor
                # bulk `R<i>_BULK`, matching the plan's own port vocabulary --
                # checked per generator so `res_array`'s ordinary `R<i>_B`
                # end terminal is not mistaken for a bulk port.
                "body_port_declared": any(
                    p["name"].endswith("_B" if group["generator"] == "mos_array" else "_BULK")
                    for p in ports
                ),
                "drc_clean": drc_result["clean"],
                "drc_violation_count": drc_result["response"].get("violation_count"),
                "extract_ok": extract_result["ok"],
                "device_counts": extract_response.get("device_counts"),
                "pdk_models": _extracted_models(out_dir, cell_name),
                "unbiased_pmos_body_nets": len(
                    extract_response.get("unbiased_pmos_body_nets") or []
                ),
                "drc_hint_notes": (response.get("drc_hints") or {}).get("notes") or [],
                "voltage_flavor_mark_present": (response.get("drc_hints") or {}).get(
                    "voltage_flavor_mark_present"
                ),
            }
        )
        results.append(entry)
    return results


def probe_gen_compose_block_routing(
    plan: dict[str, Any],
    blocks: list[dict[str, Any]],
    verifier: Verifier,
    out_dir: Path,
) -> dict[str, Any]:
    """Re-measure klayout-tools#1467 against a **real multi-net block**
    (issue #35), every run.

    :func:`probe_gen_compose_router`'s two-pad cell answers only "does the
    router accept this PDK family at all" -- it is far too small to exercise
    the finding that actually keeps `cmos5l_route.py` alive: that
    `gen-compose`'s router routes the *first* net and then rejects the rest
    with ``crosses already-routed net``. So this probe rebuilds
    :data:`ROUTER_PROBE_BLOCK` as a `gen-compose` request from exactly the
    inputs this flow's own router consumes -- the already-drawn group cells,
    their declared terminal coordinates, and the plan's own schematic-derived
    port->net map -- and sends it three times:

    1. **declare-only** (no `routing` block): validates `connectivity[]`
       without drawing, so an accept here separates "the request is
       well-formed" from "the router can route it";
    2. **routed** (`routing.layer_role: "metal"`): the measurement itself;
    3. **routed with a second plane** (`routing.cross_block_layer_role`):
       records whether this PDK family even *has* a second routing metal role
       for the router to fall back onto.

    Single-pin nets are excluded because `gen-compose` rejects the whole
    request on one (`pins must be an array of at least 2 entries`); they are
    counted and reported rather than silently dropped.
    """
    block_plan = next(
        (b for b in plan["blocks"] if b["name"] == ROUTER_PROBE_BLOCK), None
    )
    block_build = next(
        (b for b in blocks if b["name"] == ROUTER_PROBE_BLOCK), None
    )
    if block_plan is None or block_build is None or not block_build.get("compose"):
        return {"block": ROUTER_PROBE_BLOCK, "ran": False, "reason": "block not composed"}

    origins = block_build["compose"]["placements"]
    geometries = {
        r["group_id"]: r["geometry"]
        for r in block_build["results"]
        if r.get("geometry")
    }

    request_blocks: list[dict[str, Any]] = []
    order: list[str] = []
    pins_by_net: dict[str, list[dict[str, str]]] = {}
    for group in block_plan["groups"]:
        gid = group["id"]
        geometry = geometries.get(gid)
        if geometry is None:
            continue
        ports = [
            {
                "name": port,
                "x_um": x,
                "y_um": y,
                "width_um": dev.ROUTE_W_UM,
                # Every terminal is a Metal1 pad this flow escapes straight up
                # onto its own riser, so every port faces the channel.
                "direction_deg": 90,
                "layer": {"layer": dev.L_METAL1[0], "datatype": dev.L_METAL1[1]},
            }
            for port, (x, y) in geometry["terminals"].items()
        ]
        body = geometry.get("body_tie") or {}
        tie = geometry.get("tie_point")
        if tie:
            ports.append(
                {
                    "name": "BODY",
                    "x_um": tie[0],
                    "y_um": tie[1],
                    "width_um": dev.ROUTE_W_UM,
                    "direction_deg": 180,
                    "layer": {"layer": dev.L_METAL1[0], "datatype": dev.L_METAL1[1]},
                }
            )
            if body.get("net"):
                pins_by_net.setdefault(body["net"], []).append(
                    {"block": gid, "port": "BODY"}
                )
        request_blocks.append(
            {
                "id": gid,
                "cell": {"gds_path": f"{gid}.gds", "cell_name": gid, "ports": ports},
            }
        )
        order.append(gid)
        for member in group["members"]:
            for port, net in member["ports"].items():
                if port in geometry["terminals"]:
                    pins_by_net.setdefault(net, []).append({"block": gid, "port": port})

    declared = [{"net": net, "pins": pins} for net, pins in sorted(pins_by_net.items())]
    connectivity = [entry for entry in declared if len(entry["pins"]) > 1]
    single_pin = [entry["net"] for entry in declared if len(entry["pins"]) == 1]

    base: dict[str, Any] = {
        "schema": "klt.gen_compose.request/1",
        "pdk": {"variant": verifier.pdk},
        "blocks": request_blocks,
        "placement": {
            "strategy": "row",
            "order": order,
            # The spacing this run's own composition was packed with, read off
            # the compose record rather than re-quoted from
            # `pll_cmos5l_layout.GROUP_SPACING_UM`: the request has to mirror
            # the placement `cmos5l_route` actually routed, and reading it
            # here means the two cannot drift apart.
            "spacing_um": block_build["compose"]["spacing_um"],
        },
        "connectivity": connectivity,
        "options": {
            "cell_name": f"gencompose_{ROUTER_PROBE_BLOCK}_probe",
            "output": f"gencompose_{ROUTER_PROBE_BLOCK}_probe.gds",
        },
    }
    routed = json.loads(json.dumps(base))
    routed["routing"] = {"layer_role": "metal", "width_um": dev.ROUTE_W_UM}
    two_layer = json.loads(json.dumps(routed))
    two_layer["routing"]["cross_block_layer_role"] = ROUTER_PROBE_CROSS_LAYER_ROLE

    summary: dict[str, Any] = {
        "block": ROUTER_PROBE_BLOCK,
        "ran": True,
        "group_count": len(request_blocks),
        "device_count": block_plan["device_count"],
        "port_count": sum(len(b["cell"]["ports"]) for b in request_blocks),
        "nets_declared": len(connectivity),
        "single_pin_nets_excluded": single_pin,
        "attempts": {},
    }
    for name, request in (
        ("block-declare", base),
        ("block-routing", routed),
        ("block-routing-two-layer", two_layer),
    ):
        request_name = f"gen-compose.probe.{name}.request.json"
        (out_dir / request_name).write_text(json.dumps(request, indent=2) + "\n")
        result = verifier.gen_compose(
            request_name, f"gen-compose.probe.{name}.json"
        )
        response = result["response"]
        nets = response.get("nets") or []
        reason_counts: dict[str, int] = {}
        for net in nets:
            for leg in net.get("legs") or []:
                if not leg.get("routed"):
                    reason = str(leg.get("reason") or "unreported")
                    # The per-leg reasons are long, geometry-specific prose;
                    # tally them by their first clause so the summary stays
                    # readable. The full strings are in the committed response.
                    reason_counts[reason.split(" -- ")[0][:120]] = (
                        reason_counts.get(reason.split(" -- ")[0][:120], 0) + 1
                    )
        summary["attempts"][name] = {
            "ok": result["ok"],
            "returncode": result["returncode"],
            "error": response.get("error", {}).get("message"),
            "net_count": len(nets),
            "routed_net_count": sum(
                1
                for net in nets
                if (net.get("legs") or [])
                and all(leg.get("routed") for leg in net["legs"])
            ),
            "unrouted_nets": response.get("unrouted_nets"),
            "leg_rejection_reasons": dict(
                sorted(reason_counts.items(), key=lambda kv: -kv[1])
            ),
        }
    return summary
