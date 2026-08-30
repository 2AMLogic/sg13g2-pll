#!/usr/bin/env python3
"""Schematic-driven, per-block PLL device-level layout on **SG13CMOS5L** (#24).

The SG13CMOS5L sibling of `pll_layout.py` (issue #13, SG13G2). Same contract,
same evidence shape, one structural difference:

* `pll_layout.py` **plans** the device set and then asks `klt gen` to draw it.
* This module reuses that identical plan half verbatim (`pll_layout.build_plan`,
  `shelf_pack`, `_match_group_extraction`, `_match_block_extraction` are all
  imported, not re-implemented) and draws the geometry itself with
  `cmos5l_devices.py`, because **every `klt gen` generator rejects the
  `ihp-sg13cmos5l` PDK family** (klayout-tools#1462, filed by this pass -- see
  `layout/sg13cmos5l-pll/README.md`'s friction log). The verification half is
  unchanged and is still entirely `klt`'s: `klt drc --deck sg13cmos5l` and
  `klt extract --deck sg13cmos5l --pdk ihp-sg13cmos5l` are what produce every
  pass/fail claim here.

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
   shelf-packed -- *placement only, no routing*, the same Non-goal the SG13G2
   side records.
6. **DRC + extract the composed cell** and cross-check its device-count
   multiset against the block's own schematic-derived totals.

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

#: Spacing between placed groups inside a composed block cell (um), and the
#: shelf-packer's target width. Both mirror the SG13G2 flow's own
#: `GROUP_SPACING_UM`/`BLOCK_TARGET_WIDTH_UM`, widened here because this
#: port's groups carry their own wells and taps.
GROUP_SPACING_UM = 6.0
BLOCK_TARGET_WIDTH_UM = 600.0

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


# --- Drawing ---------------------------------------------------------------


def draw_mos_group(builder: dev.Builder, group: dict[str, Any]) -> dict[str, Any]:
    """Draw one matched MOS group as its own cell. Returns its geometry."""
    params = group["params"]
    flavor = params["flavor"]
    w_um, l_um = params["w_um"], params["l_um"]
    rows, cols = params["rows"], params["cols"]
    count = group["count"]

    act_w, act_h = dev.mos_active_size(w_um, l_um)
    mx, my = dev.mos_margins(flavor)
    pitch_x = act_w + 2 * mx + DEVICE_GAP_UM
    pitch_y = act_h + 2 * my + DEVICE_GAP_UM

    # Leave room below the array for the tap strip (and, for a PMOS group,
    # the shared well's own NW_c1 enclosure of it).
    base_x = mx + dev.NW_C1
    base_y = my + TAP_GAP_UM + dev.TAP_H_UM + dev.NW_C1

    builder.open_cell(group["id"])
    actives: list[tuple[float, float, float, float]] = []
    for index in range(count):
        row, col = divmod(index, cols)
        drawn = dev.draw_hv_mos(
            builder,
            flavor,
            base_x + col * pitch_x,
            base_y + row * pitch_y,
            w_um,
            l_um,
        )
        actives.append(drawn["active"])  # type: ignore[arg-type]

    if flavor == "pfet":
        # One shared well per group, biased by one n+ tap and named after the
        # group so two physically separate wells never collide on one label.
        tap = dev.draw_pfet_array_well(builder, actives, TAP_GAP_UM, f"{group['id']}_B")
    else:
        tap = dev.draw_nfet_array_tap(builder, actives, TAP_GAP_UM)

    return {
        "rows": rows,
        "cols": cols,
        "pitch_x_um": round(pitch_x, 4),
        "pitch_y_um": round(pitch_y, 4),
        "body_tie": {
            "kind": "nwell_tap" if flavor == "pfet" else "substrate_tap",
            "net_label": f"{group['id']}_B" if flavor == "pfet" else None,
        },
        "tap": {k: [round(v, 4) for v in box] for k, box in tap.items()},  # type: ignore[union-attr]
    }


def draw_res_group(builder: dev.Builder, group: dict[str, Any]) -> dict[str, Any]:
    """Draw one poly-resistor group as its own cell (bars stacked in y)."""
    params = group["params"]
    flavor, w_um, l_um = params["flavor"], params["width_um"], params["length_um"]
    bar_w, bar_h = dev.res_size(w_um, l_um)

    builder.open_cell(group["id"])
    for index in range(group["count"]):
        dev.draw_poly_res(builder, flavor, 0.0, index * (bar_h + RES_GAP_UM), w_um, l_um)

    return {
        "bars": group["count"],
        "bar_size_um": [round(bar_w, 4), round(bar_h, 4)],
        "stack_pitch_um": round(bar_h + RES_GAP_UM, 4),
    }


def group_size_um(group: dict[str, Any]) -> tuple[float, float]:
    """Drawn `(width, height)` of one group's own cell, in microns.

    Derived from the same constants :func:`draw_mos_group`/
    :func:`draw_res_group` place with, so the shelf-packer never has to read
    geometry back out of the layout.
    """
    params = group["params"]
    if group["kind"] == "mos_array":
        flavor = params["flavor"]
        act_w, act_h = dev.mos_active_size(params["w_um"], params["l_um"])
        mx, my = dev.mos_margins(flavor)
        pitch_x = act_w + 2 * mx + DEVICE_GAP_UM
        pitch_y = act_h + 2 * my + DEVICE_GAP_UM
        width = 2 * dev.NW_C1 + 2 * mx + act_w + (params["cols"] - 1) * pitch_x
        height = (
            2 * dev.NW_C1
            + TAP_GAP_UM
            + dev.TAP_H_UM
            + 2 * my
            + act_h
            + (params["rows"] - 1) * pitch_y
        )
        return width, height
    bar_w, bar_h = dev.res_size(params["width_um"], params["length_um"])
    return bar_w, group["count"] * bar_h + (group["count"] - 1) * RES_GAP_UM


# --- klt invocation --------------------------------------------------------


class Verifier:
    """Runs `klt drc`/`klt extract` and records the raw response, unedited."""

    def __init__(self, klt: str, deck: str, pdk: str, pdk_root: str | None, out_dir: Path):
        self.klt = klt
        self.deck = deck
        self.pdk = pdk
        self.pdk_root = pdk_root
        self.out_dir = out_dir

    def _run(self, args: list[str]) -> dict[str, Any]:
        proc = subprocess.run(
            [self.klt, *args], capture_output=True, text=True, cwd=self.out_dir
        )
        # `klt ... --format json` writes its envelope to stdout on success and
        # to stderr on error, so read whichever stream is non-empty rather
        # than silently swallowing a captured error as `{}` (the same
        # behaviour `pll_layout.Builder._parse_json_envelope` documents).
        raw = proc.stdout.strip() or proc.stderr.strip()
        try:
            report = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            report = {"error": {"message": raw[:2000]}}
        return {
            "returncode": proc.returncode,
            "ok": proc.returncode == 0 and "error" not in report,
            "response": report,
            "stderr": proc.stderr.strip()[:2000],
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
        self, gds: str, top: str, reference: str, request_name: str, report_name: str
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
                "device_map": REFERENCE_DEVICE_MAP,
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


# --- Build -----------------------------------------------------------------


def _lvs_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Condense one `klt lvs` response into the record's own summary shape.

    Reported, deliberately, without a pass/fail verdict of this flow's own
    invention: `status` is whatever `klt lvs` said, and `counts` is its own
    device/net/pin tally. What the record then *interprets* -- that the
    device sets match in count and class while zero nets match, because this
    composition is placement-only -- is written next to these numbers in
    `record.md`, never substituted for them.
    """
    response = result.get("response", {})
    return {
        "ran": result["ok"] or "status" in response,
        "status": response.get("status"),
        "mismatch_count": response.get("mismatch_count"),
        "category_counts": response.get("category_counts"),
        "counts": response.get("counts"),
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

    compose: dict[str, Any] | None = None
    block_drc: dict[str, Any] | None = None
    block_extract: dict[str, Any] | None = None
    block_match: dict[str, Any] | None = None
    block_lvs: dict[str, Any] | None = None

    if drawn_groups:
        sizes = [(g["id"], *group_size_um(g)) for g in drawn_groups]
        origins = pll_layout.shelf_pack(sizes, BLOCK_TARGET_WIDTH_UM, GROUP_SPACING_UM)
        cell = builder.open_cell(block["cell_name"])
        for group in drawn_groups:
            origin = origins[group["id"]]
            builder.instantiate(
                cell, builder.layout.cell(group["id"]), origin["x"], origin["y"]
            )
        gds_name = f"{block['cell_name']}.gds"
        write_cell(builder, block["cell_name"], out_dir / gds_name)
        compose = {
            "cell_name": block["cell_name"],
            "gds": gds_name,
            "strategy": "shelf_pack",
            "spacing_um": GROUP_SPACING_UM,
            "target_width_um": BLOCK_TARGET_WIDTH_UM,
            "placements": origins,
            "routing": None,  # placement only -- see this module's docstring
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
    return {
        "blocks": [build_block(b, verifier, out_dir, netlist_dir) for b in plan["blocks"]]
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
        print(
            f"  {block['name']}: {block['devices_matched']}/{block['device_count']} "
            f"matched, block DRC "
            f"{'clean' if block['block_drc_clean'] else 'NOT clean'}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
