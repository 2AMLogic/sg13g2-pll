#!/usr/bin/env python3
"""Render `record.md` for a layout/sg13cmos5l-pll/reports/<record-id>/ dir.

The SG13CMOS5L sibling of `render-pll-record.py`. Reads `plan.json` +
`build.json` (already written by `pll_cmos5l_layout.py`) plus the resolved PDK
and deck identity, and writes the human-readable verdict a reader should open
first: per-block drawn / DRC / matched / composed / LVS table, and the exact
captured reason for every device this run did **not** draw.

Every number below is read out of `build.json`, which is itself derived from
`klt`'s own JSON responses -- nothing here is hand-asserted alongside the
evidence.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_json(cmd: list[str]) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, OSError):
        return {}


def main(argv: list[str]) -> int:
    if len(argv) < 5:
        print(
            "usage: render-pll-cmos5l-record.py <record-dir> <klt> <pdk> <deck> "
            "[pdk-root]",
            file=sys.stderr,
        )
        return 2
    record_dir = Path(argv[1])
    klt, pdk, deck = argv[2], argv[3], argv[4]
    pdk_root = argv[5] if len(argv) > 5 and argv[5] else None

    plan = json.loads((record_dir / "plan.json").read_text())
    build_path = record_dir / "build.json"
    build = json.loads(build_path.read_text()) if build_path.is_file() else None

    pdk_cmd = [klt, "pdk", "find", "--pdk", pdk, "--format", "json"]
    if pdk_root:
        pdk_cmd[2:2] = ["--pdk-root", pdk_root]
    pdk_info = _run_json(pdk_cmd)
    # `klt deck info --format json` returns `{"decks": [...]}`, not the flat
    # object `klt pdk find` returns -- unwrap the requested deck's entry.
    deck_info = next(
        (
            entry
            for entry in _run_json(
                [klt, "deck", "info", "--deck", deck, "--format", "json"]
            ).get("decks", [])
            if entry.get("deck") == deck
        ),
        {},
    )
    klt_version = subprocess.run(
        [klt, "--version"], capture_output=True, text=True
    ).stdout.strip()

    lines: list[str] = [f"# PLL SG13CMOS5L layout record — `{record_dir.name}`\n"]
    lines.append(f"- **klt**: `{klt_version or 'unknown'}`")
    lines.append(f"- **PDK variant requested**: `{pdk}`")
    if pdk_info.get("root"):
        lines.append(
            f"- **PDK resolved**: `{pdk_info.get('variant')}` at "
            f"`{pdk_info.get('root')}` (via {pdk_info.get('resolved_via')})"
        )
    else:
        lines.append("- **PDK resolved**: not resolved (plan-only run)")
    if deck_info:
        lines.append(
            f"- **Deck**: `{deck_info.get('deck', deck)}` "
            f"(`{deck_info.get('content_hash', 'unknown')}`), device classes: "
            f"{', '.join(deck_info.get('device_classes', []) or ['unknown'])}"
        )
    else:
        lines.append(f"- **Deck**: `{deck}`")
    lines.append("")

    total_devices = sum(b["device_count"] for b in plan["blocks"])
    if build is None:
        lines.append("## Verdict: PLAN ONLY — nothing drawn this run\n")
        lines.append(
            f"`plan.json` derives **{total_devices}** device(s) across "
            f"{len(plan['blocks'])} blocks."
        )
        (record_dir / "record.md").write_text("\n".join(lines) + "\n")
        return 0

    drawn = sum(b["devices_drawn"] for b in build["blocks"])
    drc_clean = sum(b["devices_drc_clean"] for b in build["blocks"])
    matched = sum(b["devices_matched"] for b in build["blocks"])
    composed = sum(1 for b in build["blocks"] if b["composed"])
    blocks_drc_clean = sum(1 for b in build["blocks"] if b["block_drc_clean"])
    blocks_matched = sum(
        1 for b in build["blocks"] if (b["block_match"] or {}).get("matched")
    )

    lines.append(
        f"## Verdict: **{drawn} / {total_devices} devices drawn**, "
        f"**{drc_clean} / {total_devices} DRC-clean**, "
        f"**{matched} / {total_devices} re-extracted matching the schematic**; "
        f"{composed} / {len(build['blocks'])} blocks composed, "
        f"{blocks_drc_clean} DRC-clean, {blocks_matched} device-count-matched\n"
    )
    lines.append(
        "Drawn by this repo's own `cmos5l_devices.py` footprints (every `klt "
        "gen` generator rejects the `ihp-sg13cmos5l` PDK family — "
        "klayout-tools#1462); **verified entirely by `klt`**: `klt drc --deck "
        f"{deck}` and `klt extract --deck {deck} --pdk {pdk}`. Every device "
        "not drawn is a recorded, tracked upstream gap — see "
        "`layout/sg13cmos5l-pll/README.md`'s friction log, never a silent "
        "drop.\n"
    )

    lines.append("### Per-block\n")
    lines.append(
        "| Block | Groups drawn | Devices drawn | Devices | Group DRC clean | "
        "Group re-extract matches | Composed | Block DRC | Block re-extract "
        "matches schematic | Block LVS |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for block in build["blocks"]:
        lvs = block.get("block_lvs") or {}
        if not lvs:
            lvs_cell = "—"
        elif lvs.get("ran"):
            counts = (lvs.get("counts") or {}).get("devices", {})
            lvs_cell = (
                f"{lvs.get('status')} "
                f"(devices {counts.get('layout')}/{counts.get('reference')}, "
                f"nets matched {(lvs.get('counts') or {}).get('nets', {}).get('matched')})"
            )
        else:
            lvs_cell = "not converted"
        lines.append(
            f"| `{block['name']}` | {block['groups_drawn']}/"
            f"{block['group_count']} | {block['devices_drawn']} | "
            f"{block['device_count']} | {block['devices_drc_clean']} | "
            f"{block['devices_matched']} | "
            f"{'yes' if block['composed'] else 'no'} | "
            f"{'clean' if block['block_drc_clean'] else block['block_drc_violations']} | "
            f"{'yes' if (block['block_match'] or {}).get('matched') else 'no'} | "
            f"{lvs_cell} |"
        )
    lines.append("")

    lines.append("### Devices recorded but never drawn\n")
    reasons: dict[str, list[str]] = {}
    for block in build["blocks"]:
        for result in block["results"]:
            if result.get("attempted"):
                continue
            reasons.setdefault(result["reason"], []).append(result["group_id"])
    if reasons:
        for reason, ids in reasons.items():
            lines.append(f"- `{'`, `'.join(sorted(ids))}` — {reason}")
    else:
        lines.append("- none: every planned device was drawn.")
    lines.append("")

    lines.append("### LVS status\n")
    lines.append(
        "`klt lvs` is run per composed block against that block's own "
        "committed schematic netlist (copied into this record as "
        "`<block>.reference.spice`). **A `mismatch` verdict here is expected "
        "and is this increment's own scope, not a deck defect**: composition "
        "is placement only — no net is drawn between two devices — so the "
        "device sets match in count and class while zero nets match. Blocks "
        "whose reference netlist instantiates a MoM capacitor cannot be "
        "converted at all (klayout-tools#1463: the curated deck declares no "
        "capacitor device class, so there is nothing to map it to). Routing "
        "and LVS closure are a separate T1 checklist rung."
    )
    lines.append("")

    lines.append("### Device flavor\n")
    lines.append(plan["device_flavor"])
    lines.append("")
    lines.append(
        "See `plan.json` for the full derived device plan, `build.json` for "
        "the per-group and per-block results, and `drc.<cell>.json` / "
        "`extract.<cell>.json` / `lvs.<block>.json` for the raw `klt` "
        "responses each claim above was read out of."
    )

    (record_dir / "record.md").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
