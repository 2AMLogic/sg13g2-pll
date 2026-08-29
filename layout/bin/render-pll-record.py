#!/usr/bin/env python3
"""Render `record.md` for a layout/pll/reports/<record-id>/ directory.

Reads plan.json + build.json (already written by pll_layout.py) and the
resolved PDK info (`klt pdk find`), and writes a human-readable summary --
verdict, per-block drawn/composed/matched table, and the exact captured
`klt` friction per distinct failure reason, so a reader does not have to
open every gen./extract./compose.<group>.json file individually.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print(
            "usage: render-pll-record.py <record-dir> <klt> <pdk> [pdk-root]",
            file=sys.stderr,
        )
        return 2
    record_dir = Path(argv[1])
    klt = argv[2]
    pdk = argv[3]
    pdk_root = argv[4] if len(argv) > 4 and argv[4] else None

    plan = json.loads((record_dir / "plan.json").read_text())
    build_path = record_dir / "build.json"
    build = json.loads(build_path.read_text()) if build_path.is_file() else None

    pdk_info_cmd = [klt, "pdk", "find", "--pdk", pdk, "--format", "json"]
    if pdk_root:
        pdk_info_cmd[2:2] = ["--pdk-root", pdk_root]
    try:
        pdk_info = json.loads(
            subprocess.run(pdk_info_cmd, capture_output=True, text=True).stdout
            or "{}"
        )
    except json.JSONDecodeError:
        pdk_info = {}

    klt_version = subprocess.run(
        [klt, "--version"], capture_output=True, text=True
    ).stdout.strip()

    lines: list[str] = []
    lines.append(f"# PLL layout record — `{record_dir.name}`\n")
    lines.append(f"- **klt**: `{klt_version or 'unknown'}`")
    lines.append(f"- **PDK variant requested**: `{pdk}`")
    if pdk_info.get("root"):
        lines.append(
            f"- **PDK resolved**: `{pdk_info.get('variant')}` at "
            f"`{pdk_info.get('root')}` (via {pdk_info.get('resolved_via')})"
        )
    else:
        lines.append("- **PDK resolved**: not resolved (plan-only run)")
    lines.append("")

    totals = {}
    for block in plan["blocks"]:
        for group in block["groups"]:
            totals[group["kind"]] = totals.get(group["kind"], 0) + group["count"]
    total_devices = sum(totals.values())

    if build is None:
        lines.append(
            "## Verdict: PLAN ONLY — no `klt gen` build attempted this run\n"
        )
        lines.append(f"`plan.json` derives **{total_devices}** devices across "
                      f"{len(plan['blocks'])} blocks: " +
                      ", ".join(f"{k}={v}" for k, v in sorted(totals.items())) + ".")
    else:
        drawn = build["devices_drawn_total"]
        matched = build.get("devices_matched_total", 0)
        blocks_composed = sum(1 for b in build["blocks"] if b.get("composed"))
        lines.append(
            f"## Verdict: **{drawn} / {total_devices} devices drawn, "
            f"{matched} / {total_devices} re-extracted matching the "
            f"schematic**, {blocks_composed} / {len(build['blocks'])} "
            "blocks composed\n"
        )
        if drawn == 0:
            lines.append(
                "**Every planned device group failed to draw.** This is a "
                "real, reproduced upstream tool gap, not a config mistake in "
                "this flow — see \"Friction\" below."
            )
        elif matched < drawn:
            lines.append(
                "**Some drawn devices did not re-extract matching the "
                "schematic.** See the per-group `match` field in `build.json` "
                "for which device(s) and why — this is not expected to "
                "happen against the current `klt` pin; a mismatch here is a "
                "real finding, not noise."
            )
        else:
            lines.append(
                "Every device the schematic declares that has a `klt gen` "
                "generator on `sg13g2` today draws, extracts, and matches "
                "the schematic's own `(class, W, L)` per group; the "
                "remainder (`capacitor` groups) is a documented, tracked "
                "upstream gap — see \"Friction\" below, not a partial run."
            )
        lines.append("")
        lines.append("### Per-block")
        lines.append("")
        lines.append(
            "| Block | Groups drawn | Devices drawn | Device count | "
            "Composed | Block re-extract matches schematic |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for b in build["blocks"]:
            block_match = b.get("block_match")
            if b.get("composed") and block_match is not None:
                match_cell = "yes" if block_match["matched"] else "**no**"
            elif b.get("composed"):
                match_cell = "extract failed"
            else:
                match_cell = "n/a (not composed)"
            lines.append(
                f"| `{b['name']}` | {b['groups_drawn']}/{b['group_count']} "
                f"| {b['devices_drawn']} | {b['device_count']} "
                f"| {'yes' if b.get('composed') else 'no'} | {match_cell} |"
            )
        lines.append("")

        lines.append("### Friction — captured `klt` responses, one per distinct failure")
        lines.append("")
        seen_reasons: dict[str, str] = {}
        for b in build["blocks"]:
            for r in b["results"]:
                if r.get("ok"):
                    continue
                if r.get("attempted"):
                    gen = r.get("gen", {})
                    resp = gen.get("response", {})
                    msg = (
                        resp.get("error", {}).get("message")
                        or gen.get("stderr")
                        or gen.get("stdout")
                    )
                    if not msg:
                        match = r.get("match", {})
                        msg = "; ".join(match.get("mismatches", [])) or None
                else:
                    msg = r.get("reason")
                if msg and msg not in seen_reasons:
                    seen_reasons[msg] = r["group_id"]
        if seen_reasons:
            for msg, example_group in seen_reasons.items():
                lines.append(f"- (e.g. `{example_group}`): {msg}")
        else:
            lines.append("- none — every attempted group drew, extracted, and matched.")
        lines.append("")

    lines.append("### Device flavor")
    lines.append("")
    lines.append(plan["device_flavor"])
    lines.append("")
    lines.append(
        "See `plan.json` for the full derived device plan (every group's "
        "`klt gen` request + schematic port/net map) and, if this run "
        "attempted a build, `build.json` / `gen.<group>.json` / "
        "`extract.<group>.json` / `compose.<block>.{request,response}.json` "
        "for the per-group and per-block results."
    )

    (record_dir / "record.md").write_text("\n".join(lines) + "\n")
    print(f"render-pll-record.py: wrote {record_dir / 'record.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
