#!/usr/bin/env python3
"""Build the `klt sim` requests for the closed-loop PVT campaign at the
RECORD-002 operating point (issue #516, RECORD-003).

    python3 -I gen_pvt_requests.py --pinned-pdk DIR [--probe-only]
            [--timeout-s S] [--max-units-per-job N] OUTDIR

`DIR` is an `ihp-sg13cmos5l` tree at `sim/README.md`'s
`PDK-PIN ihp-sg13cmos5l 607e18d4...`; there is no `$PDK_ROOT` fallback (same
rule and reason as `../../sg13cmos5l-closed-loop-lock/testbench/
gen_mismatch_gain_requests.py`, whose corner-request shape -- staged pinned
models, `.meas` + `crossings` measurements, batch fleet -- this campaign
reuses).

What this sweeps
----------------
RECORD-002 locked the N = 64 loop (band `00`, `f_ref` = 9.375 MHz, 600 MHz)
at ONE nominal point. This campaign runs that same deck across PVT: 5 MOS
corners x {-40, 27, 125} C at 3.3 V (15 units) plus `mos_tt` / 27 C at 3.0
and 3.6 V (row 18's supply range), each with the behavioural-divider control
arm at the three `mos_tt` temperatures. 17 real + 3 control units.

The circuit body per arm is byte-for-byte what `run.sh` renders for
RECORD-002's `_o2` runs (same snapshot derivation: DR-010 `cp`, ideal
loop-filter caps at the campaign values, `XCDECAP` stripped, real-arm latch
`.ic`), minus the cards `klt sim` owns (`.lib`, `.tran`, `.control`, `.save`,
`.end`, and the `temp=` on `.option`): klt composes those per corner. The
resistor corner is held at `res_typ` for every unit (the issue's axes are
MOS corner x temperature x supply; RECORD-002's deck is `res_typ`); the
corner wrapper stages the pinned `cornerMOShv.lib`/`cornerRES.lib` closure
via `options.stage_model_inputs`, so the fleet image's own PDK tree is never
read (the `sg13cmos5l-vco-kvco-table` RECORD-002 / `gen_125c_acquisition`
staging contract, and the RECORD-015 trap it closes: the pinned tree's model
cards are symlinks into the sibling `ihp-sg13g2` tree, so the closure --
not just the `cornerMOShv.lib` hash -- is what must ship; `pvt_metrics.py`
checks the report's `staged_model_inputs.source_sha256` against the
`pinned-closure.csv` this generator writes).

The `vctrl` start-point policy (issue #516 step 3): `.ic v(vctrl)` stays at
RECORD-002's 1.23 V at EVERY unit -- a per-corner interpolation is impossible
for 14 of 17 units (the committed Kvco table covers exactly three bundles) --
and the window stays 10 us = 93.75 `T_ref`, so any corner acquiring within
7.87 us still has >= 20 post-acquisition cycles for the dual-lock criterion.
Every lock time is therefore warm-started, exactly as RECORD-002's was.

What is emitted
---------------
    OUTDIR/<group>/{pll_*.cir,corner_pvt.lib,request.json}, one per group:
    real_3v3 (warm 3.3 V units, 4 per job), real_3v0, real_3v6, five
    real_cold_<mos>_-40c and three real_slow_<mos>_<temp>c single-unit
    requests, and control. Together they carry the 17 real + 3 control
    corner requests (`corners.units`: explicit
        PVT records, no cross product). Measurements: the seven RECORD-002
        `.meas` averages over the 8-10 us window plus three `crossings`
        series (every 50 %-of-rail rising crossing of `v(ref)` and `v(fb)`,
        and of `v(clk)` from 7.8 us on, for the per-FB-period edge counts).
        Supply rails are per-unit `supply_v` values (the four Vdd sources
        are `alter`ed); the reference pulse is swept with
        `corners.supply_waveforms` so its amplitude tracks the rail at the
        3.0/3.6 V units and is byte-identical (scale 1.0) at 3.3 V.
    OUTDIR/probe/{...}
        The single-unit pre-grid probe: the real arm at the slowest expected
        corner (`mos_ss` / 125 C / 3.3 V), same netlist, same measurements.
        Run this one first (host policy: probe one unit before the grid).
    OUTDIR/units.csv           arm, unit_id, mos_corner, temp_c, vdd_v
    OUTDIR/pinned-closure.csv  every staged pinned-PDK file, dereferenced
                               source path and sha256 (the closure check
                               `pvt_metrics.py` grades the reports against)

Running them (host rules: a grid goes to the batch fleet, never a local loop)
----------------------------------------------------------------------------
    # 1. probe (slowest expected corner) -- single unit
    klt sim OUTDIR/probe/request.json --backend batch \
        --wait-for-capacity 600 -o OUTDIR/probe-run --format json \
        --report-out OUTDIR/probe-run/probe.report.json
    # 2. the grid, as one batch-set of the group requests (the end-of-run
    #    print lists the full member set, incl. the real_cold_*/real_slow_*)
    klt sim --batch-set OUTDIR/real_3v3/request.json \
        OUTDIR/real_3v0/request.json OUTDIR/real_3v6/request.json \
        OUTDIR/control/request.json --wait-for-capacity 600 --capacity-retries 3 --format json \
        --report-out OUTDIR/pvt.report.json
    # 3. collect
    python3 -I pvt_metrics.py --pinned-closure OUTDIR/pinned-closure.csv \
        --out-dir ../corners/pvt1 OUTDIR/pvt.report.json
"""
import argparse
import csv
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "sim" / "tools"))  # python3 -I: no script dir
from stage_pinned_pdk import pinned_closure, resolve_pinned_pdk, write_staged_manifest  # noqa: E402
SNAP = HERE.parent / "netlist-snapshots"

# ---- operating point: RECORD-002's, unchanged (issue #516) ----------------
FREF = 9.375e6                 # band 00, N = 64 -> f_vco = 600 MHz
VDD_NOM = 3.3
B0V, B1V = 0, 0                # band code 00
IREF = "10u"
VC0 = 1.23                     # RECORD-002's warm start, every unit
TSTOP_S = 10e-6                # 93.75 T_ref
TAVG0_S = 8e-6                 # .meas averaging window 8-10 us (last 20 %)
TSTEP, TMAX = "100p", "100p"
CP_SNAP = "cp-dr010.spice"     # the committed DR-010 cp (RECORD-002's swap)
RES_CORNER = "res_typ"
C1_F, C2_F = 1.691196e-12, 1.001529e-13   # run.sh's campaign cap values

# ---- campaign geometry (stated in RECORD-003; do not edit independently) --
MOS_CORNERS = ("mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs")
TEMPS = (-40, 27, 125)
SUPPLY_V = (3.0, 3.6)          # row 18's range, mos_tt / 27 C only
RAILS = ("vdd_pfd", "vdd_cp", "vdd_vco", "vdd_div")
#: crossings window for v(clk): covers the 8-10 us average window and the
#: final ~18 FB periods with margin on both sides (bucket alignment).
CLK_FROM_S = 7.8e-6
CLK_MAX = 2600                 # 2.2 us x ~1025 MHz (band-00 fast top) + margin
REF_FB_MAX = 500               # 188 edges at f_ref; misdivide can double f_fb

#: the ss/-40 C unit's tran needs `uic` (start directly from the deck's
#: `.ic`s): at default and at both augmentation option lines ngspice-47
#: aborts it with timestep_too_small inside the first 300 ns (measured
#: locally, 2026-11-21; the tt/-40 C unit passes without uic, so it is the
#: ss corner's start-up region, not the campaign geometry). With `uic` the
#: same 300 ns window integrates cleanly; the fleet unit runs the full
#: 10 us window on the uic deck.
UIC_COLD_MOS = {"mos_ss"}

#: three warm 3.3 V units that run as their OWN single-unit jobs. Measured
#: on the fleet (2026-11-21): as a 3-unit shared shard they starve -- 3
#: ngspice x num_threads 4 = 12 solver threads on an 8-vCPU instance is
#: 1.5x oversubscribed, and the whole job died at the fleet's hard 3600 s
#: ceiling (job klt-sim-f5918c7938d2, exit 124 at 3504 s) with no unit
#: finished. Solo (the cold units' pattern: 4 threads on 8 vCPU, ~1.8-2.9
#: ks) they fit the ceiling; the remaining seven warm units shard 4-per-job
#: as before (they finished in 1.2-1.5 ks even three-way oversubscribed).
SOLO_WARM_UNITS = {("mos_sf", 125), ("mos_fs", 27), ("mos_fs", 125)}

OSDI = ("psp103", "psp103_nqs", "mosvar", "r3_cmc")


def g(x, fmt=".6e"):
    return format(x, fmt)


def rd(name: str) -> str:
    return (SNAP / name).read_text()


def build_blocks(arm: str) -> str:
    """`run.sh`'s pll_blocks_realdiv.spice derivation, byte for byte."""
    vco = re.sub(r"(?m)^XCDECAP", "*XCDECAP", rd("vco.spice"))
    assert "*XCDECAP" in vco

    def sub_cap(text, x, n1, n2, v):
        new, n = re.subn(rf"(?m)^X{x}\s+{n1}\s+{n2}\s+cap_cmomi\b.*$",
                         f"C{x} {n1} {n2} {v:.6e}", text)
        assert n == 1
        return new

    lf = sub_cap(sub_cap(rd("loop_filter.spice"), "C1", "NZ", "VSS", C1_F),
                 "C2", "VCTRL", "VSS", C2_F)
    blocks = [rd("pfd.spice"), rd(CP_SNAP), lf, vco]
    if arm == "real":
        blocks.append(rd("divider_chain.spice"))
    return "\n".join(blocks)


def body_for(arm: str, vdd: float) -> str:
    """tb_pll_realdiv.sp.tmpl as a klt-sim circuit body (one self-contained
    netlist: the block bundle and the arm .inc are inlined).

    Drops the cards klt synthesizes itself and keeps everything else at
    RECORD-002's values: rails, reference, bias currents, `.ic` on
    vctrl/ring1 (+ the real arm's latch `.ic`), `scale=1`. The template's
    `temp=@TEMP@` does NOT survive (klt emits its own `.temp` per corner);
    the body `.save`/`.tran`/`.control`/`.end` go the same way.

    `vdd` sets BOTH the rail sources and the reference pulse amplitude --
    the template's single `@VDD@` token, as `run.sh` renders it. One request
    per supply value therefore carries the amplitude in its netlist bytes
    (`corners.supply_waveforms` is not relied on: the fleet runner in
    service when this campaign ran refused a `corners.units` request that
    combined the two, klayout-tools #4981 territory). The rails are still
    declared per unit in `corners.supply_v` at the same value, so the
    `frac_of` crossing levels resolve and the emitted `alter`s are no-ops.
    """
    tref = 1.0 / FREF
    tmpl = (HERE / "tb_pll_realdiv.sp.tmpl").read_text()
    inc = (HERE / f"arm_{arm}.inc").read_text()
    text = tmpl.replace("@ARM_BLOCK@", inc)
    keep = []
    for ln in text.splitlines():
        if ln.startswith(".control"):
            break
        if ln.startswith((".lib ", ".tran ", ".save ", ".end")):
            continue
        if ln.startswith(".option "):
            # RECORD-002's deck is `.option scale=1 temp=@TEMP@` and converged
            # at 27 C; at -40 C that tran aborts (timestep too small, dynamic
            # gmin stepping failed -- attempt 1 of this campaign, all three
            # cold units). The divider-max-frequency campaign's proven cold-
            # corner line (tb_div_maxfreq.sp.tmpl, its -40 C star points) is
            # added verbatim: same DUT family, same solver.
            keep.append(".option scale=1 reltol=1e-3 vntol=1e-4 abstol=1e-9 "
                        "trtol=7")
            continue
        if ln.startswith(".include pll_blocks_realdiv.spice"):
            keep.append(build_blocks(arm).rstrip("\n"))
            continue
        keep.append(ln)
    body = "\n".join(keep) + "\n"
    subs = {"@VDD@": f"{vdd}", "@TREF@": g(tref),
            "@TREFH@": g(tref / 2 - 100e-12),
            "@IREF@": IREF, "@B0V@": str(B0V), "@B1V@": str(B1V),
            "@VC0@": str(VC0)}
    for key, val in subs.items():
        body = body.replace(key, val)
    if re.search(r"@[A-Z0-9_]+@", re.sub(r"(?m)^\*.*$", "", body)):
        raise SystemExit(f"{arm}: unsubstituted @TOKEN@ left in body")
    return body


def corner_wrapper(tech: pathlib.Path, corners) -> str:
    """One `.lib <corner>` section per MOS corner; each pulls in the pinned
    `cornerMOShv.lib <corner>` and `cornerRES.lib res_typ` (gen_mismatch_gain_
    requests.py's wrapper: `options.stage_model_inputs` follows the
    file-bearing `.lib` references, shipping both closures with the job)."""
    out = ["* sg13g2-pll :: generated by gen_pvt_requests.py (issue #516)",
           "* One section per MOS corner of the campaign; each pulls in the",
           "* pinned MOS-HV corner and the typical resistor corner."]
    for c in corners:
        out += [f".lib {c}",
                f'.lib "{tech}/models/cornerMOShv.lib" {c}',
                f'.lib "{tech}/models/cornerRES.lib" {RES_CORNER}',
                f".endl {c}"]
    return "\n".join(out) + "\n"


def units_for(arm: str):
    """[(unit_id, mos, temp_c, vdd)] -- the issue's 17+3 point list."""
    pts = []
    if arm == "real":
        for mos in MOS_CORNERS:
            for temp in TEMPS:
                pts.append((mos, temp, VDD_NOM))
        pts.append(("mos_tt", 27, SUPPLY_V[0]))
        pts.append(("mos_tt", 27, SUPPLY_V[1]))
    else:
        for temp in TEMPS:
            pts.append(("mos_tt", temp, VDD_NOM))
    def uid(mos, temp, vdd):
        return f"{arm}_{mos}_{temp}c_{str(vdd).replace('.', 'v')}"
    return [(uid(mos, temp, vdd), mos, temp, vdd) for mos, temp, vdd in pts]
def measurements():
    meas = [{"name": n, "unit": u,
             "spice": f".meas tran {n} avg {e} from={TAVG0_S * 1e9:.0f}n "
                      f"to={TSTOP_S * 1e9:.0f}n"}
            for n, e, u in (("i_pfd", "i(Vdd_pfd)", "A"),
                            ("i_cp", "i(Vdd_cp)", "A"),
                            ("i_vco", "i(Vdd_vco)", "A"),
                            ("i_div", "i(Vdd_div)", "A"),
                            ("vc_avg", "v(vctrl)", "V"))]
    meas += [{"name": n, "unit": "V",
              "spice": f".meas tran {n} {op} v(vctrl) from={TAVG0_S * 1e9:.0f}n "
                       f"to={TSTOP_S * 1e9:.0f}n"}
             for n, op in (("vc_max", "max"), ("vc_min", "min"))]
    # 50 %-of-rail crossing series. frac_of follows each signal's own rail,
    # so the threshold is 1.65 V at 3.3 V units and 1.50/1.80 V at 3.0/3.6 V
    # (RECORD-002's 1.65 V criterion is "half the rail", not a fixed level).
    meas += [{"name": "t_ref", "unit": None,
              "crossings": {"signal": "v(ref)", "level": {"frac_of": "vdd_pfd",
                                                          "fraction": 0.5},
                            "edge": "rise", "max": REF_FB_MAX}},
             {"name": "t_fb", "unit": None,
              "crossings": {"signal": "v(fb)", "level": {"frac_of": "vdd_div",
                                                          "fraction": 0.5},
                            "edge": "rise", "max": REF_FB_MAX}},
             {"name": "t_clk", "unit": None,
              "crossings": {"signal": "v(clk)", "level": {"frac_of": "vdd_vco",
                                                          "fraction": 0.5},
                            "edge": "rise", "from": g(CLK_FROM_S),
                            "max": CLK_MAX}}]
    return meas


def write_request(d: pathlib.Path, arm: str, pts, tech: pathlib.Path,
                  timeout_s: int, max_units_per_job: int,
                  uic: bool = False) -> None:
    d.mkdir(parents=True, exist_ok=True)
    vdd = pts[0][3]
    assert all(p[3] == vdd for p in pts), "one supply value per request"
    corners = sorted({mos for _, mos, _, _ in pts})
    (d / "corner_pvt.lib").write_text(corner_wrapper(tech, corners))
    (d / f"pll_{arm}.cir").write_text(body_for(arm, vdd))
    units = [{"process": mos, "temperature_c": temp,
              "supply_v": {r: vdd for r in RAILS}}
             for _, mos, temp, _ in pts]
    (d / "request.json").write_text(json.dumps({
        "engine": "ngspice",
        "netlist": f"pll_{arm}.cir",
        "models": {"lib": "corner_pvt.lib"},
        "analysis": {"kind": "tran",
                     "args": f"{TSTEP} {TSTOP_S * 1e9:.0f}n 0 {TMAX}"
                             + (" uic" if uic else "")},
        "measurements": measurements(),
        "options": {
            "osdi_preload": [f"{tech}/osdi/{n}.osdi" for n in OSDI],
            "stage_model_inputs": True,
            "ngspice_init": ["set numdgt=12", "set num_threads=4"],
            "save_vectors": ["v(ref)", "v(fb)", "v(vctrl)", "v(clk)"],
            "timeout_s": timeout_s,
            "max_workers": 4,
        },
        "backend": "batch",
        "batch": {
            "capacity_wait_s": 600,
            # The fleet's whole-job ceiling is 3600 s (fleet_config);
            # 3500 s is this request's client-side job timeout, kept under
            # it. Stating the job wall directly (unit-count-independent) and balancing
            # into small shards keeps every job under it without the serial
            # bound (timeout_s x units + 120) refusing anything.
            "job_timeout_s": 3500,
            "max_units_per_job": max_units_per_job,
            "max_concurrent_jobs": 2,
        },
        "corners": {"units": units},
    }, indent=2) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("outdir", help="directory to write the request tree into")
    ap.add_argument("--pinned-pdk", default=None,
                    help="an ihp-sg13cmos5l tree at sim/README.md's PDK-PIN "
                         "revision 607e18d4... (env: PINNED_PDK). Required.")
    ap.add_argument("--probe-only", action="store_true",
                    help="emit only the single-unit slowest-corner probe")
    ap.add_argument("--timeout-s", type=int, default=3400,
                    help="per-unit engine timeout (default 3400)")
    ap.add_argument("--max-units-per-job", type=int, default=4,
                    help="batch shard size (default 4)")
    a = ap.parse_args()
    pdk = resolve_pinned_pdk(a.pinned_pdk, prog="gen_pvt_requests.py")
    tech = pdk / "libs.tech" / "ngspice"
    if not (tech / "models" / "cornerMOShv.lib").is_file():
        raise SystemExit(f"--pinned-pdk: {tech}/models/cornerMOShv.lib "
                         "is not readable")
    out = pathlib.Path(a.outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    rows = pinned_closure(pdk, ["cornerMOShv.lib", "cornerRES.lib"], OSDI,
                          label="pinned closure")
    write_staged_manifest(out / "pinned-closure.csv", rows)

    all_units = []
    if not a.probe_only:
        real = units_for("real")
        # The five -40 C units are the stiffest transients of the campaign
        # (attempt 1: the three that ran all aborted at default tolerances,
        # the other two were never launched) and the fleet's
        # whole-job ceiling is a hard 3600 s (batch-fleet.env
        # BATCH_MAX_JOB_SECONDS), so each runs as its OWN single-unit job --
        # a cold unit that overruns then dies alone instead of taking its
        # shard-mates with it. The three SOLO_WARM_UNITS starve a shared
        # shard the same way (12 threads on 8 vCPU; measured, see its
        # comment); the seven remaining warm 3.3 V units shard 4-per-job.
        warm = [p for p in real
                if p[3] == 3.3 and p[2] != -40
                and (p[1], p[2]) not in SOLO_WARM_UNITS]
        cold = [p for p in real if p[3] == 3.3 and p[2] == -40]
        groups = {"real_3v3": warm}
        groups.update({f"real_cold_{p[1].split('_')[1]}_-40c": [p]
                       for p in cold})
        groups.update({f"real_slow_{p[1].split('_')[1]}_{p[2]}c": [p]
                       for p in real if p[3] == 3.3 and p[2] != -40
                       and (p[1], p[2]) in SOLO_WARM_UNITS})
        groups.update({"real_3v0": [p for p in real if p[3] == 3.0],
                       "real_3v6": [p for p in real if p[3] == 3.6],
                       "control": units_for("control")})
        for name, pts in groups.items():
            arm = "control" if name == "control" else "real"
            solo = name.startswith(("real_cold_", "real_slow_"))
            write_request(out / name, arm, pts, tech,
                          3200 if solo else a.timeout_s,
                          1 if solo else a.max_units_per_job,
                          uic=solo and pts[0][2] == -40 and pts[0][1] in UIC_COLD_MOS)
            all_units += pts
            print(f"wrote {name}: {len(pts)} units -> {out / name / 'request.json'}")
    # probe: the real arm at the slowest expected corner (mos_ss / 125 C)
    probe_pt = [("real_mos_ss_125c_3v3", "mos_ss", 125, VDD_NOM)]
    write_request(out / "probe", "real", probe_pt, tech, a.timeout_s, 1)
    print(f"wrote probe: {probe_pt[0][0]} -> {out / 'probe' / 'request.json'}")

    with open(out / "units.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["unit_id", "arm", "mos_corner", "temp_c", "vdd_v"])
        for uid, mos, temp, vdd in all_units + probe_pt:
            w.writerow([uid, uid.split("_")[0], mos, temp, vdd])
    print("submit with: klt sim --batch-set OUTDIR/real_3v3/request.json "
          "OUTDIR/real_3v0/request.json OUTDIR/real_3v6/request.json "
          "OUTDIR/control/request.json --wait-for-capacity 600 "
          "--capacity-retries 3 --format json --report-out OUTDIR/pvt.report.json "
          "(plus the real_cold_*/real_slow_* single-unit requests)")


if __name__ == "__main__":
    main()
