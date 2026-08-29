#!/usr/bin/env python3
"""Schematic-driven, per-block PLL layout plan + build attempt (issue #13).

Reads the *authored schematics' own netlists* (`design/netlist/*.spice`,
committed by #7) and derives, deterministically, each block's device set from
them -- then drives `klt gen` to attempt drawing that device set. Nothing
about the device set is typed in by hand here: every planned device exists
because a device card in a schematic netlist asked for it, which is what
makes "the layout matches the schematic's device set" a checkable claim
rather than an assertion.

Two halves, deliberately separated so the first is testable with no PDK and
no `klt` installed (`layout/tests/test_pll_layout_plan.py` exercises it):

1. **Plan** (pure, PDK-free): parse each block's netlist, recursively flatten
   its schematic hierarchy down to leaf devices (MOS/resistor/capacitor;
   every other model name is a locally-defined sub-block and is expanded, not
   drawn), group the leaf devices of each block into matched arrays keyed by
   `(class, W, L)`, and record what `klt gen` request each group *would* be.
   `build_plan()` returns plain JSON-serialisable data -- see `plan_block()`.
2. **Build** (impure): attempt `klt gen` per planned group and record the
   real result -- success or the tool's own error message -- rather than
   asserting one in advance. See `layout/pll/README.md`'s "What is drawn
   today" table for why every group currently comes back blocked, and the
   friction log for the exact upstream gaps (klayout-tools#1450, #1451)
   filed after reproducing each failure directly against a real `ihp-sg13g2`
   install.

Six blocks, six independent netlist files (`spec/porting-plan.md` §1.4;
`design/netlist.sh`'s own `BLOCKS` list) -- unlike a single closed-loop
top-level netlist, there is no `pll_top`-equivalent file in this design yet
(top-level integration is explicitly future work, `spec/porting-plan.md`
§3.3/§3.4), so this flow composes nothing above the per-block level.

Scope caveat, stated here because it is the honest headline of this
deliverable: this is a **device-level plan**, not a routed full-custom
layout, and (see the friction log) not, today, a drawn one either. DRC-clean
and LVS-clean closure are later T1 checklist items, not this one. See
`layout/pll/README.md` for the full "what is and is not verified" statement.
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
#: but neither is reachable from `res_array` today -- see
#: layout/pll/README.md's friction log (klayout-tools#1451).
RESISTOR_MODELS = {
    "rppd": "rppd",
    "rhigh": "rhigh",
}

#: `cap_cmim` (MIM) has no `klt gen` generator on any family for sg13g2 --
#: `cap_array` (sky130-only) explicitly rejects the family, and no MiM
#: capacitor extraction device class exists in the curated sg13g2 deck
#: either (`klt deck info --deck sg13g2`: no `capacitor` entry, consistent
#: with klayout-tools#1233, already tracked). Per this issue's own
#: Non-goals, capacitor devices are recorded in the plan (so they are never
#: silently dropped) but never attempted in the build step.
CAP_MODELS = {
    "cap_cmim": "cap_cmim",
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


#: Why each `kind` is not drawable by any `klt gen` generator against sg13g2
#: today -- filled in once, cited by every group of that kind in the plan,
#: and re-verified directly (not inferred) against a real `ihp-sg13g2`
#: install at klt commit `6d2028a32bfd385724498941572f3976783ae720` (the
#: exact commit `layout/requirements.txt` pins). See
#: `layout/pll/README.md`'s friction log for the full transcripts.
BLOCKED_REASONS = {
    "mos_array": (
        "klt gen mos_array (and diff_pair) reject the sg13g2 PDK family "
        "outright: the unit device's shared gate-poly landing pad trips "
        "sg13g2's real gatpoly.separation.activ.1 DRC rule -- "
        "klayout-tools#1450"
    ),
    "res_array": (
        "klt gen res_array exposes only the 'generic' (rsil) sg13g2 "
        "poly-resistor flavour; this design's rppd/rhigh resistors are "
        "rejected with 'supported flavours: generic' -- klayout-tools#1451"
    ),
    "capacitor": (
        "no klt gen generator draws a MIM capacitor for sg13g2 on any "
        "family (cap_array is sky130-only), and the curated sg13g2 "
        "extraction deck has no capacitor device class either "
        "(klayout-tools#1233, already tracked) -- out of scope per this "
        "issue's own Non-goals, never attempted"
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
                "blocked_reason": BLOCKED_REASONS["mos_array"],
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
                "blocked_reason": BLOCKED_REASONS["res_array"],
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
        groups.append(
            {
                "id": f"{block_name}_{member['path']}",
                "kind": "capacitor",
                "generator": None,
                "params": {"w_um": w_um, "l_um": l_um, "model": member["model"]},
                "count": 1,
                "blocked_reason": BLOCKED_REASONS["capacitor"],
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
        )

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


# --- 3. Build attempt (impure: runs `klt`) ----------------------------------


class Builder:
    """Attempts `klt gen` per planned group and records the real result.

    Deliberately does not assume any group succeeds or fails -- it runs the
    request and reports back exactly what `klt` says, which is what makes
    this build step self-correcting: once an upstream fix lands (e.g.
    klayout-tools#1450/#1451 resolve), re-running this same script picks up
    the change with no code edit here.
    """

    def __init__(self, klt: str, pdk: str, pdk_root: str | None, out_dir: Path) -> None:
        self.klt = klt
        self.pdk = pdk
        self.pdk_root = pdk_root
        self.out_dir = out_dir

    def gen_group(self, group: dict[str, Any]) -> dict[str, Any]:
        """Attempt one `klt gen` group (mos_array / res_array). Never raises
        -- a `klt` failure is a *result* this build step records, not an
        exception this driver crashes on."""
        cell = group["id"]
        args = [
            self.klt,
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
            args[2:2] = ["--pdk-root", self.pdk_root]
        proc = subprocess.run(args, capture_output=True, text=True, cwd=self.out_dir)
        # `klt gen --format json` writes its JSON envelope to stdout on
        # success but to stderr on error (confirmed directly, not assumed --
        # see layout/pll/README.md's friction log) -- try whichever stream
        # is non-empty so a captured error is never silently swallowed as
        # `{}`.
        raw = proc.stdout.strip() or proc.stderr.strip()
        try:
            report = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            report = {"unparsed_output": raw}
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


def attempt_build(plan: dict[str, Any], builder: Builder) -> dict[str, Any]:
    """Attempt every drawable-kind group in the plan; skip capacitor groups
    (never attempted -- see BLOCKED_REASONS["capacitor"] and this issue's
    own Non-goals)."""
    summary: dict[str, Any] = {"blocks": []}
    for block in plan["blocks"]:
        group_results = []
        for group in block["groups"]:
            if group["kind"] in ("mos_array", "res_array"):
                group_results.append(builder.gen_group(group))
            else:
                group_results.append(
                    {
                        "group_id": group["id"],
                        "attempted": False,
                        "ok": False,
                        "reason": group["blocked_reason"],
                    }
                )
        drawn = sum(1 for r in group_results if r.get("ok"))
        summary["blocks"].append(
            {
                "name": block["name"],
                "cell_name": block["cell_name"],
                "group_count": len(block["groups"]),
                "groups_drawn": drawn,
                "device_count": block["device_count"],
                "devices_drawn": sum(
                    g["count"]
                    for g, r in zip(block["groups"], group_results)
                    if r.get("ok")
                ),
                "results": group_results,
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

    builder = Builder(args.klt, args.pdk, args.pdk_root, args.out_dir)
    summary = attempt_build(plan, builder)
    summary["totals"] = totals
    summary["devices_drawn_total"] = sum(
        b["devices_drawn"] for b in summary["blocks"]
    )
    (args.out_dir / "build.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"devices_drawn_total": summary["devices_drawn_total"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
