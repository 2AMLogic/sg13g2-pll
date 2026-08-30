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

    routed_nets = sum(b.get("routed_nets", 0) for b in build["blocks"])
    lvs_match = sum(
        1
        for b in build["blocks"]
        if (b.get("block_lvs") or {}).get("status") == "match"
    )

    lines.append(
        f"## Verdict: **{drawn} / {total_devices} devices drawn**, "
        f"**{drc_clean} / {total_devices} DRC-clean**, "
        f"**{matched} / {total_devices} re-extracted matching the schematic**; "
        f"{composed} / {len(build['blocks'])} blocks composed and routed "
        f"({routed_nets} nets), {blocks_drc_clean} DRC-clean, "
        f"{blocks_matched} device-count-matched, "
        f"**{lvs_match} / {len(build['blocks'])} LVS `match`**\n"
    )
    lines.append(
        "Drawn *and routed* by this repo's own `cmos5l_devices.py` / "
        "`cmos5l_route.py` (every `klt gen` generator — and `klt gen-compose`'s "
        "router — rejects the `ihp-sg13cmos5l` PDK family, klayout-tools#1462; "
        "see \"Routing\" below for this run's own re-probe); **verified "
        f"entirely by `klt`**: `klt drc --deck {deck}`, `klt extract --deck "
        f"{deck} --pdk {pdk}` and `klt lvs`. Every device not drawn is a "
        "recorded, tracked upstream gap — see "
        "`layout/sg13cmos5l-pll/README.md`'s friction log, never a silent "
        "drop.\n"
    )

    lines.append("### Per-block\n")
    lines.append(
        "| Block | Groups drawn | Devices drawn | Devices | Group DRC clean | "
        "Group re-extract matches | Composed | Nets routed | Block DRC | "
        "Block re-extract matches schematic | Block LVS |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for block in build["blocks"]:
        lvs = block.get("block_lvs") or {}
        if not lvs:
            lvs_cell = "—"
        elif lvs.get("ran"):
            counts = lvs.get("counts") or {}
            devices = counts.get("devices", {})
            nets = counts.get("nets", {})
            lvs_cell = (
                f"**{lvs.get('status')}** "
                f"(devices {devices.get('matched')}/{devices.get('reference')}, "
                f"nets {nets.get('matched')}/{nets.get('reference')})"
            )
        else:
            lvs_cell = "not converted"
        routed = block.get("routed_nets", 0)
        incomplete = block.get("incomplete_nets", 0)
        routed_cell = f"{routed}" + (f" ({incomplete} incomplete)" if incomplete else "")
        lines.append(
            f"| `{block['name']}` | {block['groups_drawn']}/"
            f"{block['group_count']} | {block['devices_drawn']} | "
            f"{block['device_count']} | {block['devices_drc_clean']} | "
            f"{block['devices_matched']} | "
            f"{'yes' if block['composed'] else 'no'} | {routed_cell} | "
            f"{'clean' if block['block_drc_clean'] else block['block_drc_violations']} | "
            f"{'yes' if (block['block_match'] or {}).get('matched') else 'no'} | "
            f"{lvs_cell} |"
        )
    lines.append("")

    lines.append("### Routing\n")
    probe = build.get("gen_compose_probe") or {}
    if probe:
        placement = probe.get("placement", {})
        routing = probe.get("routing", {})
        lines.append(
            "`klt gen-compose` was re-probed this run against a throwaway "
            "two-pad cell on this same PDK, once placement-only and once with "
            "`routing` — the raw responses are `gen-compose.probe.*.json`:\n"
        )
        lines.append(
            f"- placement-only: exit {placement.get('returncode')} "
            f"({'accepted' if placement.get('ok') else 'rejected'})"
        )
        lines.append(
            f"- with `routing`: exit {routing.get('returncode')} "
            f"({'accepted' if routing.get('ok') else 'rejected'})"
            + (f" — `{routing.get('error')}`" if routing.get("error") else "")
        )
        lines.append("")
    lines.append(
        "Interconnect is therefore drawn by `cmos5l_route.py`: one vertical "
        "`Metal2` riser per device terminal, one horizontal `Metal3` trunk per "
        "net in a channel above the row, `Via1`/`Via2` between them, and the "
        "net name written on `Metal3.pin` (30/2) — the layer this deck's own "
        "`EXTRACTION_DECK.metal_labels` reads. Every net and every terminal's "
        "net membership comes from `plan.json`'s own "
        "`groups[].members[].ports` map, which is derived from the committed "
        "schematic netlist rather than typed in.\n"
    )
    lines.append(
        "| Block | Terminals routed | Nets | Wire length (µm) | Nets the layout cannot complete |"
    )
    lines.append("| --- | --- | --- | --- | --- |")
    for block in build["blocks"]:
        compose = block.get("compose") or {}
        routing = compose.get("routing") or {}
        incomplete = sorted({n["net"] for n in routing.get("incomplete_nets", [])})
        lines.append(
            f"| `{block['name']}` | {compose.get('terminal_count', 0)} | "
            f"{routing.get('net_count', 0)} | "
            f"{routing.get('wire_length_um', 0)} | "
            f"{'`' + '`, `'.join(incomplete) + '`' if incomplete else '—'} |"
        )
    lines.append("")
    incomplete_all = [
        note
        for block in build["blocks"]
        for note in ((block.get("compose") or {}).get("routing") or {}).get(
            "incomplete_nets", []
        )
    ]
    if incomplete_all:
        lines.append(
            "A net listed as incomplete is routed between the terminals that "
            "*do* exist and reported here with the undrawn device's own "
            "blocked reason — never dropped, never counted as fully routed:\n"
        )
        seen: set[tuple[str, str]] = set()
        for note in incomplete_all:
            key = (note["net"], note["missing_pin"])
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"- net `{note['net']}` is missing `{note['missing_pin']}` "
                f"({note['device']}) — {note['reason']}"
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
        "`<block>.reference.spice`, so this evidence is self-contained). "
        "Per-block, read out of `lvs.<block>.json` rather than asserted:\n"
    )
    def _lvs_line(name: str, lvs: dict) -> str:
        counts = lvs.get("counts") or {}
        categories = lvs.get("category_counts") or {}
        return (
            f"{name} — **{lvs.get('status')}**, "
            f"devices {counts.get('devices', {}).get('matched')}/"
            f"{counts.get('devices', {}).get('reference')}, "
            f"nets {counts.get('nets', {}).get('matched')}/"
            f"{counts.get('nets', {}).get('reference')}, "
            f"pins {counts.get('pins', {}).get('matched')}/"
            f"{counts.get('pins', {}).get('reference')}; "
            f"`mismatch_count` {lvs.get('mismatch_count')} "
            f"({', '.join(f'{k}: {v}' for k, v in sorted(categories.items())) or 'none'})"
        )

    for block in build["blocks"]:
        lvs = block.get("block_lvs") or {}
        if not lvs.get("ran"):
            lines.append(
                f"- `{block['name']}` — **not converted**: "
                f"{lvs.get('error') or 'no LVS response'}"
            )
            probe = lvs.get("capacitor_probe") or {}
            if probe.get("ran"):
                lines.append(
                    "  - secondary probe (`lvs.%s.cap-probe.json`), reference-side "
                    "`cap_cmomi` mapped so the compare runs anyway: %s"
                    % (block["name"], _lvs_line("", probe).lstrip(" —"))
                )
                unmatched = probe.get("unmatched_device_classes") or {}
                if unmatched:
                    lines.append(
                        "    unmatched devices: "
                        + ", ".join(f"{v} x `{k}`" for k, v in sorted(unmatched.items()))
                    )
            elif probe:
                lines.append(
                    f"  - secondary probe also could not convert: {probe.get('error')}"
                )
            continue
        lines.append("- " + _lvs_line(f"`{block['name']}`", lvs))
    lines.append("")
    lines.append(
        "A block whose reference netlist instantiates a MoM capacitor does "
        "not convert: `klt lvs`'s `subckt-call` converter has no `cap_cmomi` "
        "entry for this deck, because the deck declares no capacitor device "
        "class at all (klayout-tools#1463). That is recorded above as `not "
        "converted` with `klt lvs`'s own message, never as \"clean\" and never "
        "waived. The secondary probe under each such block maps the capacitor "
        "on the *reference* side only — which converts, since `device_map`'s "
        "`kind` vocabulary is caller-side — so the comparison runs and the "
        "undrawn capacitors show up as `device.unmatched` instead of hiding "
        "behind a conversion failure. It is a diagnostic, not a verdict: a "
        "layout that provably cannot carry the device cannot match a "
        "reference that declares it."
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
