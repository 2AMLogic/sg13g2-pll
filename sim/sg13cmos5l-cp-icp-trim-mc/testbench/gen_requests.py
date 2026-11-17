#!/usr/bin/env python3
"""Regenerate the three `klt sim` request files in this directory.

    python3 -I gen_requests.py --pinned-pdk DIR     (or PINNED_PDK=DIR)

`DIR` is an `ihp-sg13cmos5l` tree at `sim/README.md`'s
`PDK-PIN ihp-sg13cmos5l 607e18d4...`.  There is no `$PDK_ROOT` fallback, and
that is load-bearing -- see "Why the pinned tree, and the mm_ok guard" below.

mc.request.json                the campaign: 5 mismatch-enabled process
                               corners x 3 temperatures x N=100, seed 178,
                               batch backend (1500 units).
negative_control.request.json  mos_tt (NO mismatch section) x 27 C x 20
                               samples, local: every spread must be exactly 0.
positive_probe.request.json    mos_tt_mismatch x 27 C x 3 samples, local: the
                               spread must be non-zero (the mismatch section
                               is live under this exact netlist).

All three share one measurement block and one options block, so a control
exercises the same deck path as the campaign.

Why the pinned tree, and the mm_ok guard
----------------------------------------
IHP moved the per-instance mismatch enable between the two `ihp-sg13cmos5l`
revisions `sim/README.md` names.  In the pin (`607e18d4...`) the HV MOS
mismatch subcircuits default to `mm_ok=1`, so every instance draws.  In the
newer install (`f7bca326...`) that default is `mm_ok=0` and the enable moved
to the xschem symbol, which now emits `mm_ok=@mm_ok` per instance.  This
repo's `design/sg13cmos5l/netlist/cp.spice` was netlisted with the older
symbols, so its MOS instance lines carry no `mm_ok` at all: run against the
newer tree, every `agauss(...)` collapses to its nominal and the campaign
returns sigma **exactly 0** on every measurement, with no error, no warning
and a `pass` status.  That is an invisible-null-result trap, so this
generator refuses to emit a request it cannot prove will draw:
`check_mismatch_enabled()` below reads the resolved mismatch library and
aborts unless the HV MOS subcircuits default to `mm_ok=1`.
See ../records/RECORD-002 and ../README.md "Mismatch is PDK-revision
sensitive".

Running on the pin is also what `sim/README.md`'s provenance contract
requires of a record (`manifests/check_testbench_coverage.py` fails a record
citing any revision that is not the pin), and it is the same mechanism
`../../sg13cmos5l-vco-kvco-table/testbench/gen_rerun318.py` uses for issue
#318: the pinned bytes are shipped with the job rather than resolved on the
worker.  Here the shipping mechanism is `options.stage_model_inputs`, which
stages `models.lib`'s whole `.include` closure plus the OSDI objects from the
*submitting* host and reports a sha256 per staged file in the response's
`environment.staged_model_inputs[]` -- so the record can state the bytes that
ran instead of trusting the fleet image.  `models.pdk` is deliberately
omitted: with nothing to resolve on the worker, the image's own PDK tree
(the newer, mismatch-off one) is never read.
"""
import argparse
import json
import os
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent

#: `.subckt <name> ... mm_ok=<v> ...` -- the per-instance mismatch enable.
SUBCKT_MM_OK = re.compile(
    r"^\.subckt\s+(sg13_hv_[np]mos)\b(?:[^\n]*\n\+[^\n]*)*", re.I | re.M)
MM_OK = re.compile(r"\bmm_ok\s*=\s*([0-9.]+)")
INCLUDE = re.compile(r"^\s*\.(?:include|inc)\s+(\S+)\s*$", re.I | re.M)


def check_mismatch_enabled(models: pathlib.Path) -> list[str]:
    """Abort unless this tree's HV MOS mismatch subcircuits default to
    ``mm_ok=1``.  Returns the files that carried the proof.

    A tree whose default is ``mm_ok=0`` (the post-2026-10-15 install) silently
    produces a zero-sigma campaign against this repo's `mm_ok`-less netlists,
    which is worse than a failure: it looks like a passing result.
    """
    seen, queue, proof, found = set(), ["cornerMOShv.lib"], [], {}
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        src = models / name
        if not src.is_file():
            raise SystemExit(f"model closure: {src} is not a readable file")
        text = src.read_text(errors="replace")
        for block in SUBCKT_MM_OK.finditer(text):
            dev = block.group(1).lower()
            m = MM_OK.search(block.group(0))
            if m:
                found.setdefault(dev, (float(m.group(1)), name))
        if found and name not in proof:
            proof.append(name)
        for target in INCLUDE.findall(text):
            if "/" in target or target.startswith("$"):
                raise SystemExit(
                    f"model closure: {src} includes {target!r}; this generator "
                    "only follows same-directory relative includes")
            queue.append(target)
    missing = {"sg13_hv_nmos", "sg13_hv_pmos"} - set(found)
    if missing:
        raise SystemExit(
            f"mm_ok guard: no `.subckt {'/'.join(sorted(missing))}` with an "
            f"mm_ok parameter under {models}. This generator cannot prove the "
            "campaign would draw per-instance mismatch; refusing to emit a "
            "request. See the module docstring.")
    off = {d: v for d, (v, _) in found.items() if v != 1.0}
    if off:
        raise SystemExit(
            "mm_ok guard: per-instance mismatch is OFF by default in "
            f"{models} ({', '.join(f'{d} mm_ok={v:g}' for d, v in sorted(off.items()))}). "
            "This repo's netlists carry no `mm_ok=` on their MOS instance "
            "lines, so a campaign against this tree would return sigma "
            "exactly 0 on every measurement and still report `pass`. Point "
            "--pinned-pdk at sim/README.md's PDK-PIN tree "
            "(607e18d4..., where the default is mm_ok=1). See the module "
            "docstring and ../records/RECORD-002.")
    return proof


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--pinned-pdk", default=os.environ.get("PINNED_PDK"),
        help="an ihp-sg13cmos5l tree at sim/README.md's PDK-PIN revision "
             "607e18d4... (env: PINNED_PDK). Required: there is no $PDK_ROOT "
             "fallback, see the module docstring.")
    a = ap.parse_args()
    if not a.pinned_pdk:
        raise SystemExit(
            "gen_requests.py: --pinned-pdk DIR (or PINNED_PDK=DIR) is "
            "required -- an ihp-sg13cmos5l checkout at sim/README.md's "
            "PDK-PIN revision 607e18d4.... See the module docstring for why "
            "the current install pin cannot be used.")
    pdk = pathlib.Path(a.pinned_pdk).expanduser().resolve()
    tech = pdk / "libs.tech" / "ngspice"
    proof = check_mismatch_enabled(tech / "models")

    base = {
        "engine": "ngspice",
        "netlist": "tb_cp_mc.sp",
        "models": {"lib": f"{tech}/models/cornerMOShv.lib"},
        "analysis": {"kind": "dc", "args": "Vup 0 3.3 3.3"},
        "measurements": [
            {"name": "iup_a", "unit": "A", "expr": "i(Vout)[1]"},
            {"name": "idn_a", "unit": "A", "expr": "i(Vout)[0]"},
            # (Iup + Idn) / mean(|Iup|, |Idn|), Idn < 0.  Limit: see README
            # "Limit" -- an evidence-derived screening limit, NOT a ratified
            # spec number (spec row 7 proposes none).
            {"name": "mismatch_pct", "unit": "%",
             "expr": "(i(Vout)[1] + i(Vout)[0]) / ((i(Vout)[1] - i(Vout)[0]) / 2) * 100",
             "limits": {"min": -3.5, "max": 3.5}},
        ],
        "options": {
            "osdi_preload": [f"{tech}/osdi/{n}.osdi"
                             for n in ("psp103", "psp103_nqs", "mosvar")],
            "stage_model_inputs": True,
            # num_threads=1: one ngspice thread per unit, so the fleet
            # instance's own concurrency owns the parallelism (as in the
            # sibling bench's rerun requests).
            "ngspice_init": ["set numdgt=12", "set num_threads=1"],
            # 30 s per unit is ~180x the measured 0.167 s a unit of this deck
            # takes, and it is also what sizes the campaign's shards: the
            # fleet's whole-job ceiling is 3600 s, so `job_ceiling_check:
            # "split"` packs floor((3600 - 120) / 30) = 116 units per job and
            # submits ceil(1500 / 116) = 13 of them.
            "timeout_s": 30,
        },
    }

    def emit(name, **over):
        r = json.loads(json.dumps(base))
        r.update(over)
        (HERE / name).write_text(json.dumps(r, indent=2) + "\n")
        print("wrote", name)

    emit("mc.request.json", backend="batch",
         # Host rules: a multi-corner / Monte Carlo grid goes to the batch
         # fleet, and the submit waits for Spot capacity instead of failing.
         # 1500 units do not fit one job: klt's conservative fully-serial
         # bound (timeout_s x units + 120 s) exceeds the fleet's 3600 s
         # whole-job ceiling, so the run is split into balanced shard jobs
         # that each fit, at most 4 in flight so one campaign does not take
         # the whole shared fleet. Monte Carlo seeds are sample_index-derived
         # and resolved client-side, so slicing the unit list does not change
         # a single draw.
         batch={"capacity_wait_s": 600, "job_ceiling_check": "split",
                "max_concurrent_jobs": 4},
         corners={"process": [f"mos_{c}_mismatch"
                              for c in ("tt", "ss", "ff", "sf", "fs")],
                  "temperature_c": [-40, 27, 125]},
         monte_carlo={"n": 100, "seed": 178, "vary": "mismatch",
                      "quantiles": [0.5, 5, 50, 95, 99.5]})
    emit("negative_control.request.json", backend="local",
         corners={"process": ["mos_tt"], "temperature_c": [27]},
         monte_carlo={"n": 20, "seed": 178, "vary": "mismatch"})
    emit("positive_probe.request.json", backend="local",
         corners={"process": ["mos_tt_mismatch"], "temperature_c": [27]},
         monte_carlo={"n": 3, "seed": 178, "vary": "mismatch"})
    print(f"mm_ok guard: per-instance mismatch enabled by default in {pdk}"
          f" (proof read from {', '.join(proof)})")


main()
