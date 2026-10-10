#!/usr/bin/env python3
"""Item 9 coverage gate: testbench shipped, cold-start documented, PDK pinned.

T1 item 9 ("Testbenches shipped") needs every claimed measurement's testbench
committed, a cold-start invocation a third party can run, and a pinned PDK
revision. Nothing in klt can grade that, so this gate checks it directly.

sim/README.md carries a "Cold start" section with (a) a pin block, one line
per PDK tree, ``PDK-PIN <tree> <40-hex commit | UNKNOWN>``, and (b) a bench
index table, one row per bench: ``| `slug` | `entry` | `invocation` |``.

For every sim/<slug>/ that has a records/ directory the gate requires:
  * the slug is in the index, and every indexed slug exists (both ways);
  * the indexed entry point exists inside the bench and is executable;
  * the invocation documents that entry point (contains its basename);
  * every records/RECORD-*.md cites a PDK revision (a line naming the PDK
    ``revision``/``commit`` with a >=12-hex SHA) and a tool version
    (ngspice-NN or klt X.Y). A cited revision that disagrees with the pin for
    the bench's PDK tree is a DISCREPANCY and always fails.
  * the pin for the bench's PDK tree is a 40-hex commit (not UNKNOWN).

Records are append-only, so records written before this gate cannot be
edited to add a revision. Those are grandfathered in KNOWN_DEFECTS (path ->
follow-up issue); a record not listed there must pass, and a listed record
that now passes is a stale entry. If the committed tier report grades item 9
met, KNOWN_DEFECTS must be empty and the pins resolved; while it is non-empty
the manifest must not cite any item-9 evidence (a topically unrelated passing
envelope would render item 9 met dishonestly).

Provenance addenda (append-only migration of a grandfathered record). A
committed record is never edited. Instead a new file
``sim/<slug>/records/ADDENDUM-*.md`` associates itself with ONE original in
the same bench through ``KEY: value`` lines (format: sim/README.md,
"Provenance addenda"):
  * ``ADDENDUM-FOR``  bench-relative path of the original record;
  * ``ADDENDUM-KIND`` ``recovered`` (historical provenance was recovered from
    evidence) or ``superseded`` (a new rerun replaces the evidence claim);
  * ``ADDENDUM-SHA256`` sha256 of the original's bytes (pins "unmodified");
  * ``ADDENDUM-EVIDENCE`` what was recovered / rerun (non-empty);
  * recovered: one or more ``ADDENDUM-PDK: <tree> <40-hex>`` lines (several
    trees = a mixed-PDK record; the slug is never trusted) and
    ``ADDENDUM-TOOL`` (ngspice-NN / klt X.Y);
  * superseded: ``ADDENDUM-RERUN`` = same-bench RECORD-*.md that cites the
    original by file name and itself passes (or is itself resolved); PDK
    lines are forbidden, since a new run does not prove the old environment.
A valid association resolves the original's defect (the KNOWN_DEFECTS entry
stays until a human removes it; it is then reported as resolved). Missing,
contradictory, dangling, cyclic, cross-bench, duplicate or hash-mismatched
associations fail closed. Historical revisions that differ from today's pin
are kept as-is and reported, never rewritten. Item 9 stays unmet/uncited
while any defect is unresolved or any pin is UNKNOWN.

Stdlib only. Exit 0 = pass, 1 = fail.

Usage: check_testbench_coverage.py [--sim DIR] [--manifest P] [--tier-report P]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

FOLLOWUP = 182  # backfill of PDK revision for pre-gate records

# Pre-gate records (append-only, no PDK revision). path relative to sim/.
_GRANDFATHERED = (
    "sg13cmos5l-closed-loop-lock/records/RECORD-001-closed-loop-lock-spur-power.md",
    "sg13cmos5l-closed-loop-lock/records/RECORD-002-pfd-reset-parity-root-cause.md",
    "sg13cmos5l-closed-loop-lock/records/RECORD-003-pfd-reset-fix-closed-loop-rerun.md",
    "sg13cmos5l-closed-loop-lock/records/RECORD-004-icp-mismatch-phase-error-diagnostic.md",
    "sg13cmos5l-closed-loop-lock/records/RECORD-005-cascbias-real-cp-static-phase-error-rerun.md",
    "sg13cmos5l-closed-loop-lock/records/RECORD-006-cp-dynamic-charge-term-diagnostic.md",
    "sg13cmos5l-closed-loop-real-divider/records/RECORD-001-repaired-divider-in-loop-nominal.md",
    "sg13cmos5l-cp-icp-trim/records/RECORD-001-icp-trim-and-mismatch.md",
    "sg13cmos5l-cp-icp-trim/records/RECORD-002-cascode-bias-mismatch-remeasure.md",
    "sg13cmos5l-cp-icp-trim/records/RECORD-003-issue83-finetrim-icp.md",
    "sg13cmos5l-cp-icp-trim/records/RECORD-004-issue79-finetrim-icp.md",
    "sg13cmos5l-divider-nrange-retiming/records/RECORD-001-nrange-retiming-margin.md",
    "sg13cmos5l-divider-nrange-retiming/records/RECORD-002-pdk-root-token-fix-reverification.md",
    "sg13cmos5l-divider-nrange-retiming/records/RECORD-003-divider-repair-reverification.md",
    "sg13cmos5l-klt-pex-signoff/records/RECORD-001-klt-pex-nominal-envelopes.md",
    "sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md",
    "sg13cmos5l-lock-detector-window/records/RECORD-002-resized-window-hysteresis-chatter.md",
    "sg13cmos5l-lock-detector-window/records/RECORD-003-hysteresis-fix.md",
    "sg13cmos5l-lock-detector-window/records/RECORD-004-crowbar-current-mitigation.md",
    "sg13cmos5l-lock-detector-window/records/RECORD-005-rpu-body-on-vss.md",
    "sg13cmos5l-loop-bandwidth-pm/records/RECORD-001-loop-bandwidth-phase-margin.md",
    "sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-icp-input-refresh.md",
    "sg13cmos5l-loop-bandwidth-pm/records/RECORD-002-r1-resize-full-fref-range.md",
    "sg13cmos5l-loop-bandwidth-pm/records/RECORD-003-issue83-close-band00-mid-fref4p5-pm-gap.md",
    "sg13cmos5l-loop-bandwidth-pm/records/RECORD-004-issue79-close-band00-low-fref4p5-pm-gap.md",
    "sg13cmos5l-loop-filter-momcap/records/RECORD-001-rc-corner-momcap-sensitivity.md",
    "sg13cmos5l-loop-filter-momcap/records/RECORD-002-r1-resize-momcap.md",
    "sg13cmos5l-postlayout-pex-pvt/records/RECORD-001-postlayout-pex-pvt-vco-and-cp.md",
    "sg13cmos5l-postlayout-pex-pvt/records/RECORD-002-floorplan-aware-vco-route.md",
    "sg13cmos5l-postlayout-pex-pvt/records/RECORD-003-postlayout-pex-pvt-pfd-and-lock-detector.md",
    "sg13cmos5l-postlayout-pex-pvt/records/RECORD-004-postlayout-pex-pvt-loop-filter-and-divider-chain.md",
    "sg13cmos5l-vco-decap-momcap/records/RECORD-001-decap-momcap-sensitivity.md",
    "sg13cmos5l-vco-duty-cycle/records/RECORD-001-duty-cycle-and-vco-current.md",
    "sg13cmos5l-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md",
    "sg13g2-divider-repair-reverification/records/RECORD-001-divider-repair-reverification.md",
    "sg13g2-lock-detector-window/records/RECORD-001-resized-window-hysteresis-chatter.md",
    "sg13g2-vco-kvco-table/records/RECORD-001-kvco-band-code-table.md",
)
KNOWN_DEFECTS = {p: FOLLOWUP for p in _GRANDFATHERED}

REV_RE = re.compile(r"PDK[^\n]{0,60}?(?:revision|commit|rev)[^\n]{0,40}?\b([0-9a-f]{12,40})\b", re.I)
TOOL_RE = re.compile(r"ngspice[- ]?\d+|\bklt \d+\.\d+", re.I)
PIN_RE = re.compile(r"^PDK-PIN (\S+) ([0-9a-f]{40}|UNKNOWN)\s*$", re.M)
ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|", re.M)


TREES = ("ihp-sg13g2", "ihp-sg13cmos5l")
ADD_RE = re.compile(r"^ADDENDUM-([A-Z0-9]+):[ \t]*(.*?)[ \t]*$", re.M)
SINGLE = ("FOR", "KIND", "SHA256", "EVIDENCE", "TOOL", "RERUN")


def parse_addendum(path, sim):
    """Return (assoc dict | None, errors). Pure syntax/field checks."""
    rel = path.relative_to(sim).as_posix()
    errs = []
    fields, pdk = {}, []
    for k, v in ADD_RE.findall(path.read_text(errors="replace")):
        if k == "PDK":
            m = re.fullmatch(r"(\S+) ([0-9a-f]{40})", v)
            if not m:
                errs.append(f"{rel}: ADDENDUM-PDK needs '<tree> <40-hex revision>', got {v!r}")
            else:
                pdk.append(m.groups())
        elif k in SINGLE:
            if k in fields:
                errs.append(f"{rel}: duplicate ADDENDUM-{k}")
            fields[k] = v
        else:
            errs.append(f"{rel}: unknown field ADDENDUM-{k}")
    for k in ("FOR", "KIND", "SHA256", "EVIDENCE"):
        if not fields.get(k):
            errs.append(f"{rel}: missing ADDENDUM-{k}")
    kind = fields.get("KIND")
    if kind == "recovered":
        if not pdk:
            errs.append(f"{rel}: recovered addendum has no ADDENDUM-PDK line")
        seen = {}
        for tree, rev in pdk:
            if tree not in TREES:
                errs.append(f"{rel}: unknown PDK tree {tree!r}")
            if seen.setdefault(tree, rev) != rev:
                errs.append(f"{rel}: contradictory revisions for tree {tree}")
        if not TOOL_RE.search(fields.get("TOOL", "")):
            errs.append(f"{rel}: recovered addendum has no tool version (ADDENDUM-TOOL)")
        if "RERUN" in fields:
            errs.append(f"{rel}: recovered addendum must not name a rerun")
    elif kind == "superseded":
        if not fields.get("RERUN"):
            errs.append(f"{rel}: superseded addendum has no ADDENDUM-RERUN")
        if pdk or "TOOL" in fields:
            errs.append(f"{rel}: superseded addendum must not assert the old PDK/tool "
                        "(a new run does not prove the old environment)")
    elif kind is not None:
        errs.append(f"{rel}: ADDENDUM-KIND must be recovered|superseded, got {kind!r}")
    if errs:
        return None, errs
    return dict(fields, pdk=dict(pdk), addendum=rel), []


def load_associations(sim, on_disk):
    """Map original rel path -> association; plus errors."""
    assocs, errs = {}, []
    for s in on_disk:
        for add in sorted((sim / s / "records").glob("ADDENDUM-*.md")):
            a, e = parse_addendum(add, sim)
            errs += e
            if a is None:
                continue
            tgt = a["FOR"]
            if not tgt.startswith(s + "/records/") or "/" in tgt[len(s) + 9:] or ".." in tgt:
                errs.append(f"{a['addendum']}: ADDENDUM-FOR {tgt} is not a record in the same bench")
                continue
            orig = sim / tgt
            if not (orig.is_file() and Path(tgt).name.startswith("RECORD-")):
                errs.append(f"{a['addendum']}: dangling ADDENDUM-FOR {tgt}")
                continue
            if hashlib.sha256(orig.read_bytes()).hexdigest() != a["SHA256"].lower():
                errs.append(f"{a['addendum']}: ADDENDUM-SHA256 does not match the bytes of {tgt}")
                continue
            if tgt in assocs:
                errs.append(f"{tgt}: more than one addendum ({assocs[tgt]['addendum']}, "
                            f"{a['addendum']})")
                continue
            a["bench"] = s
            assocs[tgt] = a
    return assocs, errs


def resolve(rel, defects, assocs, sim, pins, state, errs, notes):
    """True if record `rel` is defect-free or resolved by a valid association."""
    if rel not in defects:
        return True
    if rel in state:  # memo: True/False, or None while in progress (cycle)
        if state[rel] is None:
            errs.append(f"{rel}: cyclic addendum/rerun chain")
            state[rel] = False
        return state[rel]
    state[rel] = None
    a = assocs.get(rel)
    ok = False
    if a is None:
        pass
    elif a["KIND"] == "recovered":
        text = (sim / rel).read_text(errors="replace")
        revs = {m.lower() for m in REV_RE.findall(text)}
        allrevs = set(a["pdk"].values())
        bad = [r for r in revs if not any(x.startswith(r) for x in allrevs)]
        if bad:
            errs.append(f"{a['addendum']}: contradicts revision(s) {sorted(bad)} cited by {rel}")
        else:
            ok = True
            for tree, rev in sorted(a["pdk"].items()):
                pin = pins.get(tree)
                if pin and re.fullmatch(r"[0-9a-f]{40}", pin) and pin != rev:
                    notes.append(f"recovered {rel}: historical {tree} revision {rev} "
                                 f"differs from today's pin {pin} (retained)")
            if len(a["pdk"]) > 1:
                notes.append(f"recovered {rel}: mixed-PDK record {sorted(a['pdk'])}")
    else:
        rr = a["RERUN"]
        rp = sim / rr
        if not rr.startswith(a["bench"] + "/records/") or ".." in rr or "/" in rr[len(a["bench"]) + 9:]:
            errs.append(f"{a['addendum']}: ADDENDUM-RERUN {rr} is not a record in the same bench")
        elif rr == rel:
            errs.append(f"{a['addendum']}: record cannot supersede itself")
        elif not (rp.is_file() and Path(rr).name.startswith("RECORD-")):
            errs.append(f"{a['addendum']}: dangling ADDENDUM-RERUN {rr}")
        elif Path(rel).name not in rp.read_text(errors="replace"):
            errs.append(f"{a['addendum']}: rerun {rr} does not cite {Path(rel).name} (unrelated)")
        elif not resolve(rr, defects, assocs, sim, pins, state, errs, notes):
            errs.append(f"{a['addendum']}: rerun {rr} is itself unresolved")
        else:
            ok = True
            notes.append(f"superseded {rel} by rerun {rr} (old environment still unproven)")
    state[rel] = ok
    return ok


def tree_of(slug):
    return "ihp-sg13g2" if slug.startswith("sg13g2-") else "ihp-sg13cmos5l"


def benches(sim):
    return sorted(p.name for p in sim.iterdir() if (p / "records").is_dir())


def parse_readme(sim):
    text = (sim / "README.md").read_text()
    if "## Cold start" not in text:
        return None, None, ['sim/README.md has no "## Cold start" section']
    sect = text.split("## Cold start", 1)[1]
    sect = re.split(r"\n## ", sect, 1)[0]
    return dict(PIN_RE.findall(sect)), {m[0]: m[1:] for m in ROW_RE.findall(sect)}, []


def check_record(path, pin):
    """Return (errors, discrepancies) for one record."""
    text = path.read_text(errors="replace")
    errs, disc = [], []
    revs = {m.lower() for m in REV_RE.findall(text)}
    if not revs:
        errs.append("no PDK revision (commit hash) cited")
    elif pin and re.fullmatch(r"[0-9a-f]{40}", pin):
        for r in revs:
            if not pin.startswith(r):
                disc.append(f"cites PDK revision {r}, pin is {pin}")
    if not TOOL_RE.search(text):
        errs.append("no tool version cited (ngspice-NN / klt X.Y)")
    return errs, disc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default="sim")
    ap.add_argument("--manifest", default="manifests/sg13g2-pll.json")
    ap.add_argument("--tier-report", default="manifests/sg13g2-pll.tier-report.json")
    a = ap.parse_args(argv)
    sim = Path(a.sim)
    errs, notes = [], []

    pins, index, e = parse_readme(sim)
    if e:
        return fail(e)
    on_disk = benches(sim)
    for s in on_disk:
        if s not in index:
            errs.append(f"{s}: bench has records/ but is not in the sim/README.md bench index")
    for s in index:
        if s not in on_disk:
            errs.append(f"{s}: listed in the sim/README.md bench index but no sim/{s}/records/")
    defects = {}
    for s in on_disk:
        if s in index:
            entry, inv = index[s]
            ep = sim / s / entry
            if not ep.is_file():
                errs.append(f"{s}: entry point {entry} does not exist")
            elif not os.access(ep, os.X_OK):
                errs.append(f"{s}: entry point {entry} is not executable")
            if Path(entry).name not in inv:
                errs.append(f"{s}: invocation {inv!r} does not document entry point {entry}")
        for rec in sorted((sim / s / "records").glob("RECORD-*.md")):
            rel = rec.relative_to(sim).as_posix()
            re_, disc = check_record(rec, pins.get(tree_of(s)))
            for d in disc:
                errs.append(f"DISCREPANCY {rel}: {d}")
            if re_:
                defects[rel] = re_

    assocs, ae = load_associations(sim, on_disk)
    errs += ae
    for rel in assocs:
        if rel not in defects:
            errs.append(f"{assocs[rel]['addendum']}: {rel} has no provenance defect to resolve")
    state, unresolved = {}, set()
    for rel, d in sorted(defects.items()):
        if resolve(rel, defects, assocs, sim, pins, state, errs, notes):
            notes.append(f"resolved {rel} via {assocs[rel]['addendum']}")
        elif rel in KNOWN_DEFECTS:
            unresolved.add(rel)
            notes.append(f"known (follow-up #{KNOWN_DEFECTS[rel]}) {rel}: {'; '.join(d)}")
        else:
            unresolved.add(rel)
            errs.append(f"{rel}: {'; '.join(d)}")
    for rel in KNOWN_DEFECTS:
        if rel not in defects:
            errs.append(f"KNOWN_DEFECTS lists {rel} but it passes (stale entry)")
    for tree in sorted({tree_of(s) for s in on_disk}):
        if tree not in pins:
            errs.append(f"{tree}: no PDK-PIN line in the Cold start section")
        elif pins[tree] == "UNKNOWN":
            msg = f"{tree}: PDK revision pin is UNKNOWN (no record establishes it)"
            if unresolved:
                notes.append(f"known (follow-up #{FOLLOWUP}) {msg}")
            else:
                errs.append(msg)

    ev = json.loads(Path(a.manifest).read_text()).get("evidence", {})
    items = json.loads(Path(a.tier_report).read_text()).get("items", [])
    met = [i for i in items if i.get("id") == 9 and i.get("status") == "met"]
    cited = [k for k in ev if k == "9" or k.startswith("9.")]
    if met:
        if unresolved:
            errs.append("tier report grades item 9 met while records still lack a PDK revision")
    elif cited and (unresolved or any(v == "UNKNOWN" for v in pins.values())):
        errs.append(f"manifest cites item 9 evidence {cited} while the gate still has open defects")

    if errs:
        return fail(errs, notes)
    print(f"OK: {len(on_disk)} benches indexed; {len(KNOWN_DEFECTS)} grandfathered records, "
          f"{len(unresolved)} unresolved")
    for n in notes:
        print("  " + n)
    return 0


def fail(errs, notes=()):
    print("FAIL: item-9 testbench / PDK-pin coverage", file=sys.stderr)
    for e in errs:
        print("  - " + e, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
