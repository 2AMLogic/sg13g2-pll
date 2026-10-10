#!/usr/bin/env python3
"""Item 11 (analog) coverage gate: all five analog blocks' `klt erc` supply reports.

manifests/sg13g2-pll.json cites ONE analog block's [erc, lvs] pair for T1 item
11's analog partition. One citation stands for five blocks, so this gate
inspects every block (pfd, cp, loop_filter, vco, lock_detector) and requires,
for each one:

  * erc.supply-spec.pll_<block>.json exists in the ERC record, is a direct
    `klt erc` envelope (not a wrapper, not an error envelope), and names
    pll_<block>.gds as its input;
  * its provenance.input.content_hash equals sha256 of the adjacent
    pll_<block>.gds in the LVS record AND the input hash of that record's
    lvs.<block>.json (same-input ERC/LVS pair), and the five hashes are
    distinct (no block evidenced by another block's run);
  * its provenance.spec.content_hash equals sha256 of the committed spec
    layout/sg13cmos5l-pll/erc-supply-spec.pll_<block>.json, whose supply
    nets are exactly the block's DR-004 rails (each `expected_islands: 1`,
    or the native `islands: 1` on a strict build) and whose ties are
    exactly the ones expected below;
  * cp only (issue #195, DR-010): its PMOS OTA input pair ties its bulk to
    its own source, so pll_cp draws one NWell on `XBUF.PSRC` beside five on
    `VDD`. The one NWell layer then carries two bias classes with no marker
    layer to separate them, so the two NWell ties select their wells with
    literal boxes (`well_excludes_boxes` on the VDD tie, the same boxes as
    `well_requires_boxes` on the PSRC tie: complementary by construction,
    klayout-tools#2540). Such a "drawn_selected" tie must be in
    erc_coverage.checked AND in checked_by_well_assertion (the selection is
    the caller's word), and its non-supply net must be declared with one
    island and connectivity-checked. Any other block's spec may not use a
    well selector at all;
  * coverage: every declared supply's erc.net_connectivity and every tie's
    erc.missing_tie in erc_coverage.checked; nothing skipped or unknown; a
    drawn-NWell tie never presented as an assertion, a well_boxes substrate
    tie always listed in checked_by_well_assertion;
  * run form (provenance): the four MOS blocks were run with --deck
    sg13cmos5l at the pinned deck content hash (cp: at the pinned build
    in BLOCK_BUILD, the one build here that has the box selectors and the
    deck hash it bundles), and the blocks that draw
    resistors (vco: rppd + rhigh, lock_detector: rhigh) report those bodies
    carved out in provenance.devices with non-zero area -- so a resistor body
    can never count as a wire bridging a split supply island; loop_filter
    (gate-less) was run with NO deck and no gate net (gates[].net, comma-
    joined merged names) contains a declared supply, i.e. the uncarved rppd
    "gate" cannot be what joins VSS's island;
  * loop_filter only: zero ties, an `unexpressible` ties_disclosure, the
    matching inapplicable record, and -- re-verified from the GDS itself --
    no Activ (1/*) and no NWell (31/*) drawn, i.e. no MOS body and no tap
    can exist;
  * the lvs.<block>.json wrapper is ok/returncode 0/status "match", compared
    top pll_<block> against <block>.reference.spice, and its
    net_correspondence pairs every declared supply to a reference-side net;
    the rails are ports of `.subckt <block>` in both that reference and
    design/sg13cmos5l/netlist/<block>.spice.

A block whose report is structurally sound but carries a finding (or a
non-"clean" erc_status) is a DEFECT, not a gate error. The committed tier
report's 11.analog row decides which branch applies:

  * met   -> every block must be clean and KNOWN_DEFECTS must be empty
             (the unconditional all-five-clean requirement);
  * unmet -> every defective block must be listed in KNOWN_DEFECTS with its
             follow-up issue (the documented unmet state), and no block in
             KNOWN_DEFECTS may be clean (stale entry).

The manifest's 11.analog citation, when present, must point at one block's
ERC report in the ERC record plus that block's lvs.<block>.json with pointer
"/response", both pinned to that block's GDS hash.

Stdlib only. Exit 0 = pass, 1 = fail.

Usage: check_erc_coverage.py [--manifest P] [--tier-report P] [--erc-record D]
                             [--lvs-record D] [--specs D]
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

DEFAULT_ERC_RECORD = "layout/sg13cmos5l-pll/reports/20261008-230856-cd95c87"
DEFAULT_SPECS = "layout/sg13cmos5l-pll"
DEFAULT_NETLISTS = "design/sg13cmos5l/netlist"

# DR-004 rail table / design/sg13cmos5l/netlist/<block>.spice top-level ports.
# ties: name -> (kind, net); kind "drawn" = drawn NWell (31/0), "asserted" =
# well_layer null + well_boxes (native substrate, the weaker claim).
EXPECT = {
    "pfd": {"supplies": ("VDD", "VSS"),
            "ties": {"nwell_tap": ("drawn", "VDD"), "substrate_tap": ("asserted", "VSS")}},
    # cp (DR-010, #195): five VDD wells plus the PMOS input pair's own
    # source-tied well on XBUF.PSRC, selected by literal box (see docstring).
    "cp": {"supplies": ("VDD", "VSS"), "signals": ("XBUF.PSRC",),
           "ties": {"nwell_tap": ("drawn_selected", "VDD"),
                    "psrc_nwell_tap": ("drawn_selected", "XBUF.PSRC"),
                    "substrate_tap": ("asserted", "VSS")}},
    "loop_filter": {"supplies": ("VSS",), "ties": {}},
    "vco": {"supplies": ("VDD_VCO", "GND_VCO"),
            "ties": {"nwell_tap": ("drawn", "VDD_VCO"), "substrate_tap": ("asserted", "GND_VCO")}},
    "lock_detector": {"supplies": ("VDD", "VSS"),
                      "ties": {"nwell_tap": ("drawn", "VDD"), "substrate_tap": ("asserted", "VSS")}},
}
ANALOG_BLOCKS = tuple(EXPECT)
# Run form. MOS blocks: the curated deck, pinned to the content hash every
# committed report records (klt 0.6.0+ge6284fbe62e2's bundled sg13cmos5l).
MOS_DECK = {"name": "sg13cmos5l",
            "content_hash": "sha256:1912f17486e78de5259aab5d68533488ebbd239a05018f096217aa62ddee2909"}
# Per-block build pin, overriding MOS_DECK. cp's well ties need
# well_requires_boxes / well_excludes_boxes (klayout-tools#2540), which the
# grading build (e6284fbe62e2) predates -- and silently ignores as unknown
# keys. cp is therefore run at klayout-tools 1eb3e4bfd0f5 (the item-7 klt pex
# build), pinned here by version AND bundled-deck hash.
BLOCK_BUILD = {
    "cp": {"klt_version": "0.6.0+g1eb3e4bfd0f5",
           "deck": {"name": "sg13cmos5l",
                    "content_hash": "sha256:db9f44fadafe6a1f7d83729b299d98127144f9e66497cf7f5197c486d38c222a"}},
}
WELL_SELECTORS = ("well_requires", "well_excludes", "well_requires_boxes", "well_excludes_boxes")
# Blocks drawing resistor bodies on GatPoly: device -> must be carved out.
CARVED_DEVICES = {"vco": ("rppd", "rhigh"), "lock_detector": ("rhigh",)}
# Gate-less blocks run without --deck (klayout-tools#2896).
NO_DECK = ("loop_filter",)

# A gate-less passive block may disclose its ties instead of declaring them,
# but only when the GDS really draws none of these layers (Activ, NWell).
DISCLOSURE_ALLOWED = {"loop_filter": (1, 31)}

# Block -> follow-up issue for a recorded layout defect. Must be empty while
# the tier report claims 11.analog met.
KNOWN_DEFECTS = {}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def gds_layers(path):
    """Set of GDS layer numbers drawn anywhere in the stream (LAYER records).

    Raises ValueError on a malformed or truncated stream (bad record length,
    record running past EOF, or no ENDLIB), so a partial parse can never
    report a layer as absent.
    """
    layers = set()
    data = Path(path).read_bytes()
    i = 0
    while i + 4 <= len(data):
        size, rtype = struct.unpack(">HH", data[i:i + 4])
        if size < 4 or size % 2:
            raise ValueError(f"{path}: malformed GDS record length {size} at offset {i}")
        if i + size > len(data):
            raise ValueError(f"{path}: GDS record at offset {i} runs past end of file")
        if rtype == 0x0D02:  # LAYER, INTEGER_2
            if size != 6:
                raise ValueError(f"{path}: malformed LAYER record at offset {i}")
            layers.add(struct.unpack(">h", data[i + 4:i + 6])[0])
        if rtype == 0x0400:  # ENDLIB
            return layers
        i += size
    raise ValueError(f"{path}: no ENDLIB record (truncated GDS stream)")


def load(path):
    try:
        return json.loads(Path(path).read_text()), None
    except (OSError, ValueError) as e:
        return None, f"unreadable {path}: {e}"


def subckt_ports(path, name):
    """Port list of `.subckt <name> ...` in a SPICE file (None if absent)."""
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        tok = line.split()
        if len(tok) >= 2 and tok[0].lower() == ".subckt" and tok[1].lower() == name.lower():
            return [t.upper() for t in tok[2:] if "=" not in t]
    return None


def check_lvs(lvs_record, block, supplies, netlists=DEFAULT_NETLISTS):
    """Errors for the block's LVS wrapper; returns (errs, input_hash)."""
    errs = []
    for src in (Path(netlists) / f"{block}.spice", lvs_record / f"{block}.reference.spice"):
        ports = subckt_ports(src, block)
        if ports is None:
            errs.append(f"{block}: no .subckt {block} in {src}")
        elif not set(s.upper() for s in supplies) <= set(ports):
            errs.append(f"{block}: rails {list(supplies)} are not all ports of .subckt {block} in {src}")
    doc, err = load(lvs_record / f"lvs.{block}.json")
    if err:
        return errs + [f"{block}: {err}"], None
    if doc.get("ok") is not True or doc.get("returncode") != 0:
        errs.append(f"{block}: lvs wrapper not ok/returncode 0")
    resp = doc.get("response") if isinstance(doc.get("response"), dict) else {}
    if resp.get("status") != "match":
        errs.append(f"{block}: lvs status {resp.get('status')!r}, expected 'match'")
    if resp.get("top") != f"pll_{block}" or resp.get("reference") != f"{block}.reference.spice":
        errs.append(f"{block}: lvs compared top {resp.get('top')!r} against {resp.get('reference')!r}, "
                    f"expected pll_{block} vs {block}.reference.spice")
    paired = {
        str(r.get("layout")).upper()
        for r in resp.get("net_correspondence") or []
        if isinstance(r, dict) and isinstance(r.get("layout"), str)
        and isinstance(r.get("reference"), str) and r.get("reference")
    }
    for s in supplies:
        if s.upper() not in paired:
            errs.append(f"{block}: lvs net_correspondence does not pair supply {s} to a reference net")
    h = ((resp.get("provenance") or {}).get("input") or {}).get("content_hash")
    if not h:
        errs.append(f"{block}: lvs response has no provenance.input.content_hash")
    return errs, h


def check_spec(spec_path, block, exp):
    spec, err = load(spec_path)
    if err:
        return [f"{block}: {err}"]
    errs = []
    nets = spec.get("nets") or []
    sup = [n for n in nets if n.get("kind") == "supply"]
    if sorted(n.get("name") for n in sup) != sorted(exp["supplies"]):
        errs.append(f"{block}: spec supplies {[n.get('name') for n in sup]} != DR-004 rails {list(exp['supplies'])}")
    def one_island(n):
        # `expected_islands` is this repo's annotation (ignored by builds that
        # ignore unknown keys); `islands` is the native, graded field (#2400).
        keys = [k for k in ("expected_islands", "islands") if k in n]
        return bool(keys) and all(n[k] == 1 for k in keys)
    for n in sup:
        if not one_island(n):
            errs.append(f"{block}: spec supply {n.get('name')} islands is "
                        f"{n.get('islands', n.get('expected_islands'))!r}, expected 1")
    for name in exp.get("signals", ()):
        n = next((n for n in nets if n.get("name") == name), None)
        if n is None or n.get("kind", "signal") != "signal" or not one_island(n):
            errs.append(f"{block}: spec must declare signal net {name} with exactly one island")
    ties = {t.get("name"): t for t in spec.get("ties") or []}
    if set(ties) != set(exp["ties"]):
        errs.append(f"{block}: spec ties {sorted(ties)} != expected {sorted(exp['ties'])}")
    for name, (kind, net) in exp["ties"].items():
        t = ties.get(name)
        if not t:
            continue
        if t.get("net") != net:
            errs.append(f"{block}: tie {name} net {t.get('net')!r}, expected {net!r}")
        if kind in ("drawn", "drawn_selected") and t.get("well_layer") != "31/0":
            errs.append(f"{block}: tie {name} must be on the drawn NWell 31/0")
        if kind in ("drawn", "asserted") and any(t.get(k) for k in WELL_SELECTORS):
            errs.append(f"{block}: tie {name} uses a well selector; only a declared drawn_selected tie may")
        if kind == "drawn_selected":
            if t.get("well_boxes") or t.get("well_requires") or t.get("well_excludes"):
                errs.append(f"{block}: tie {name} must select by literal box only (no well_boxes/marker selectors)")
            if bool(t.get("well_requires_boxes")) == bool(t.get("well_excludes_boxes")):
                errs.append(f"{block}: tie {name} must carry exactly one of well_requires_boxes/well_excludes_boxes")
        if kind == "asserted" and (t.get("well_layer") is not None or not t.get("well_boxes")):
            errs.append(f"{block}: tie {name} must be a well_layer null + well_boxes assertion")
        if not t.get("tap_requires"):
            errs.append(f"{block}: tie {name} has no tap_requires narrowing")
    sel = [ties[n] for n, (k, _) in exp["ties"].items() if k == "drawn_selected" and n in ties]
    if sel:
        def boxes(key):
            return sorted(tuple(b) for t in sel for b in (t.get(key) or []))
        req, exc = boxes("well_requires_boxes"), boxes("well_excludes_boxes")
        if not req or req != exc:
            errs.append(f"{block}: box-selected NWell ties are not complementary "
                        f"(requires {req} != excludes {exc}); some well would be graded twice or never")
    if not exp["ties"]:
        disc = spec.get("ties_disclosure") or {}
        if disc.get("kind") != "unexpressible" or not str(disc.get("reason", "")).strip():
            errs.append(f"{block}: zero ties without an 'unexpressible' ties_disclosure")
    elif spec.get("ties_disclosure"):
        errs.append(f"{block}: a block with expected ties must not carry a ties_disclosure")
    return errs


def check_run_form(doc, block, exp):
    """Errors if the report was not produced in the form its evidence relies on."""
    errs = []
    prov = doc.get("provenance") or {}
    deck = prov.get("deck")
    devices = prov.get("devices")
    if not isinstance(devices, list):
        return [f"{block}: provenance.devices missing (cannot verify the run form)"]
    if block in NO_DECK:
        if deck is not None:
            errs.append(f"{block}: gate-less block must be run without --deck, provenance.deck is {deck!r}")
        if devices:
            errs.append(f"{block}: expected no carved devices in the no-deck form, got {devices}")
        gates = doc.get("gates")
        if not isinstance(gates, list) or not gates:
            errs.append(f"{block}: no gates[] in report (cannot verify the uncarved 'gate' net)")
        else:
            sup = {s.upper() for s in exp["supplies"]}
            for g in gates:
                net = g.get("net") if isinstance(g, dict) else None
                if not isinstance(net, str):
                    errs.append(f"{block}: gate entry without a net name: {g!r}")
                    continue
                hit = sup & {n.strip().upper() for n in net.split(",")}
                if hit:
                    errs.append(f"{block}: gate net {net!r} contains declared supply {sorted(hit)} "
                                f"(the uncarved resistor body would join that supply's island)")
        return errs
    build = BLOCK_BUILD.get(block)
    want_deck = build["deck"] if build else MOS_DECK
    if build and prov.get("klt_version") != build["klt_version"]:
        errs.append(f"{block}: run with klt {prov.get('klt_version')!r}, pinned {build['klt_version']!r}")
    if not isinstance(deck, dict) or deck.get("name") != want_deck["name"]:
        errs.append(f"{block}: must be run with --deck {want_deck['name']}, provenance.deck is {deck!r}")
    elif deck.get("content_hash") != want_deck["content_hash"]:
        errs.append(f"{block}: deck content_hash {deck.get('content_hash')} != pinned {want_deck['content_hash']}")
    carved = {d.get("name"): d for d in devices if isinstance(d, dict)}
    for name in CARVED_DEVICES.get(block, ()):
        d = carved.get(name)
        area = d.get("body_area_um2") if d else None
        if not d or not isinstance(area, (int, float)) or area <= 0:
            errs.append(f"{block}: {name} resistor bodies not carved out (provenance.devices: {devices})")
        elif d.get("source") != "deck":
            errs.append(f"{block}: {name} carve-out source {d.get('source')!r}, expected 'deck'")
    return errs


def check_erc(erc_record, lvs_record, specs_dir, block):
    """Return (errors, defects, input_hash) for one block."""
    exp = EXPECT[block]
    rep = erc_record / f"erc.supply-spec.pll_{block}.json"
    if not rep.is_file():
        return [f"{block}: missing ERC report {rep}"], [], None
    doc, err = load(rep)
    if err:
        return [f"{block}: {err}"], [], None
    if not isinstance(doc, dict) or "error" in doc or "response" in doc:
        return [f"{block}: {rep.name} is not a direct klt erc envelope"], [], None
    errs, defects = [], []
    gds = lvs_record / f"pll_{block}.gds"
    if Path(str(doc.get("file", ""))).name != gds.name:
        errs.append(f"{block}: ERC report input is {doc.get('file')!r}, expected {gds.name}")
    prov = doc.get("provenance") or {}
    h = (prov.get("input") or {}).get("content_hash")
    if not gds.is_file():
        errs.append(f"{block}: missing GDS {gds}")
    elif h != sha256_file(gds):
        errs.append(f"{block}: ERC input hash {h} != sha256 of {gds}")
    errs += check_run_form(doc, block, exp)
    lvs_errs, lvs_h = check_lvs(lvs_record, block, exp["supplies"])
    errs += lvs_errs
    if lvs_h and h != lvs_h:
        errs.append(f"{block}: ERC input {h} != LVS input {lvs_h} (not a same-input pair)")

    spec_path = Path(specs_dir) / f"erc-supply-spec.pll_{block}.json"
    if Path(str(doc.get("spec", ""))).name != spec_path.name:
        errs.append(f"{block}: ERC report spec is {doc.get('spec')!r}, expected {spec_path.name}")
    if not spec_path.is_file():
        errs.append(f"{block}: missing spec {spec_path}")
    else:
        if (prov.get("spec") or {}).get("content_hash") != sha256_file(spec_path):
            errs.append(f"{block}: ERC spec hash != sha256 of committed {spec_path}")
        errs += check_spec(spec_path, block, exp)

    cov = doc.get("erc_coverage")
    if not isinstance(cov, dict) or cov.get("known") is not True or cov.get("nothing_checked"):
        return errs + [f"{block}: erc_coverage missing, unknown or nothing_checked"], defects, h
    checked = set(cov.get("checked") or [])
    for s in exp["supplies"] + exp.get("signals", ()):
        if f'erc.net_connectivity:["{s}"]' not in checked:
            errs.append(f"{block}: net {s} connectivity not in erc_coverage.checked")
    well_asserted = set(cov.get("checked_by_well_assertion") or [])
    tap_asserted = set(cov.get("checked_by_assertion") or [])
    for name, (kind, _net) in exp["ties"].items():
        wid = f'erc.missing_tie:["{name}"]'
        if wid not in checked:
            errs.append(f"{block}: tie {name} not in erc_coverage.checked")
        if kind == "drawn" and (wid in well_asserted or wid in tap_asserted):
            errs.append(f"{block}: drawn-well tie {name} reported as an assertion")
        if kind == "asserted" and wid not in well_asserted:
            errs.append(f"{block}: substrate tie {name} not listed in checked_by_well_assertion")
        if kind == "drawn_selected" and (wid not in well_asserted or wid in tap_asserted):
            errs.append(f"{block}: box-selected well tie {name} must be listed in checked_by_well_assertion "
                        "(and only there)")
    if cov.get("skipped"):
        errs.append(f"{block}: erc_coverage.skipped is not empty: {cov.get('skipped')}")
    if cov.get("unknown"):
        errs.append(f"{block}: erc_coverage.unknown is not empty: {cov.get('unknown')}")
    inapp = cov.get("inapplicable") or []
    if exp["ties"]:
        if inapp:
            errs.append(f"{block}: unexpected erc_coverage.inapplicable {inapp}")
    else:
        want = [{"id": "erc.missing_tie:[]", "reason": "ties_disclosed_unexpressible"}]
        if [{"id": r.get("id"), "reason": r.get("reason")} for r in inapp] != want:
            errs.append(f"{block}: inapplicable {inapp} is not the disclosed-unexpressible record")
        absent = DISCLOSURE_ALLOWED.get(block)
        if absent is None:
            errs.append(f"{block}: no geometric justification for a tie disclosure")
        elif gds.is_file():
            try:
                drawn = gds_layers(gds) & set(absent)
            except (OSError, ValueError) as e:
                errs.append(f"{block}: tie disclosure unverifiable, cannot read GDS layers: {e}")
            else:
                if drawn:
                    errs.append(f"{block}: tie disclosure unjustified, GDS draws layer(s) {sorted(drawn)}")

    if doc.get("erc_finding_count") != 0 or doc.get("erc_findings"):
        rules = sorted({f.get("rule") for f in doc.get("erc_findings") or [] if isinstance(f, dict)})
        defects.append(f"{block}: {doc.get('erc_finding_count')} ERC finding(s) {rules}")
    elif doc.get("erc_status") != "clean":
        defects.append(f"{block}: erc_status {doc.get('erc_status')!r}")
    return errs, defects, h


def check_manifest(ev, erc_record, lvs_record, hashes):
    cite = ev.get("11.analog")
    if cite is None:
        return [], None
    if not isinstance(cite, list) or len(cite) != 2:
        return ["manifest: 11.analog must be an [erc, lvs] list"], None
    erc_c, lvs_c = cite
    block = next((b for b in ANALOG_BLOCKS
                  if erc_c.get("file") == (erc_record / f"erc.supply-spec.pll_{b}.json").as_posix()), None)
    if block is None:
        return [f"manifest: 11.analog erc part {erc_c.get('file')!r} is not a report in {erc_record}"], None
    errs = []
    if lvs_c.get("file") != (lvs_record / f"lvs.{block}.json").as_posix() or lvs_c.get("pointer") != "/response":
        errs.append(f"manifest: 11.analog lvs part must be {lvs_record}/lvs.{block}.json with pointer /response")
    for c in (erc_c, lvs_c):
        if hashes.get(block) is None or c.get("content_hash") != hashes.get(block):
            errs.append(f"manifest: 11.analog part {c.get('file')} pinned to {c.get('content_hash')}, block GDS is {hashes.get(block)}")
    return errs, block


def analog_11_row(tier_report):
    for it in tier_report.get("items", []):
        if it.get("id") == 11 and it.get("partition") == "analog":
            return it
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", default="manifests/sg13g2-pll.json")
    ap.add_argument("--tier-report", default="manifests/sg13g2-pll.tier-report.json")
    ap.add_argument("--erc-record", help="ERC record dir (default: the one 11.analog cites)")
    ap.add_argument("--lvs-record", help="LVS/GDS record dir (default: the one 4.analog cites)")
    ap.add_argument("--specs", default=DEFAULT_SPECS)
    a = ap.parse_args(argv)
    ev = json.loads(Path(a.manifest).read_text()).get("evidence", {})
    lvs_record = Path(a.lvs_record or Path(ev["4.analog"]["file"]).parent)
    cite = ev.get("11.analog")
    if a.erc_record:
        erc_record = Path(a.erc_record)
    elif isinstance(cite, list) and cite and isinstance(cite[0], dict) and "file" in cite[0]:
        erc_record = Path(cite[0]["file"]).parent
    else:
        erc_record = Path(DEFAULT_ERC_RECORD)

    errs, defects, hashes = [], {}, {}
    for b in ANALOG_BLOCKS:
        e, d, h = check_erc(erc_record, lvs_record, a.specs, b)
        errs += e
        if d:
            defects[b] = d
        hashes[b] = h
    seen = [h for h in hashes.values() if h]
    if len(set(seen)) != len(seen):
        errs.append("two blocks' ERC reports share one input hash (duplicate block identity)")

    m_errs, cited = check_manifest(ev, erc_record, lvs_record, hashes)
    errs += m_errs

    tier, err = load(a.tier_report)
    row = analog_11_row(tier) if tier else None
    if row is None:
        errs.append(f"tier report: no 11.analog row ({err or 'missing'})")
    elif row.get("status") == "met":
        if cited is None:
            errs.append("tier report claims 11.analog met but the manifest cites no 11.analog pair")
        if defects:
            errs.append("tier report claims 11.analog met but blocks are not clean: "
                        + "; ".join(x for d in defects.values() for x in d))
        if KNOWN_DEFECTS:
            errs.append(f"tier report claims 11.analog met while KNOWN_DEFECTS lists {sorted(KNOWN_DEFECTS)}")
        pd = (row.get("citation") or {}).get("power_delivery") or {}
        if cited and sorted(pd.get("supply_nets") or []) != sorted(EXPECT[cited]["supplies"]):
            errs.append(f"tier report 11.analog supply_nets {pd.get('supply_nets')} != {cited} rails")
    else:
        for b, d in defects.items():
            if b not in KNOWN_DEFECTS:
                errs.append(f"undocumented defect (add a follow-up to KNOWN_DEFECTS): {'; '.join(d)}")
        for b in KNOWN_DEFECTS:
            if b not in defects:
                errs.append(f"KNOWN_DEFECTS lists {b} but its report is clean (stale entry)")
        if cited in defects:
            errs.append(f"manifest cites defective block {cited} for 11.analog")

    if errs:
        print(f"FAIL: item-11 analog ERC coverage ({erc_record} vs {lvs_record})", file=sys.stderr)
        for e in errs:
            print("  " + e, file=sys.stderr)
        return 1
    state = (row or {}).get("status")
    print(f"OK: {erc_record}: {len(ANALOG_BLOCKS)} analog ERC supply reports, same-input LVS pairs; "
          f"11.analog {state}, cited block {cited}, defects {sorted(defects) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
