#!/usr/bin/env python3
"""Build the perturbed `cp` snapshots and the `klt sim` requests for the
RECORD-014 mismatch-to-phase-error gain sweep (issue #385).

    python3 -I gen_mismatch_gain_requests.py --pinned-pdk DIR OUTDIR

`DIR` is an `ihp-sg13cmos5l` tree at `sim/README.md`'s
`PDK-PIN ihp-sg13cmos5l 607e18d4...`; there is no `$PDK_ROOT` fallback (same
rule, and the same reason, as `sim/sg13cmos5l-cp-icp-trim-mc/testbench/
gen_requests.py` -- the pinned bytes are shipped with the job via
`options.stage_model_inputs` so the fleet image's own PDK tree is never read).

What this sweeps
----------------
`sim/sg13cmos5l-cp-icp-trim-mc`'s campaign grades `mismatch_pct` against a
`+/-3.5 %` screening limit derived from ONE closed-loop point measured on the
**pre-DR-010** `cp` (9.176 % static phase error at -6.42 % DC mismatch,
assumed linear through the origin).  This bench re-measures that gain on the
committed DR-010 `cp`, by stepping the DC mismatch deliberately instead of
drawing it.

The perturbation is a **diagnostic substitution in the style of RECORD-004**:
`design/sg13cmos5l/cp.sch` is not edited.  The committed snapshot
`../netlist-snapshots/cp_otabuf.spice` is copied and the two cascode mirror
devices of the UP leg (`.subckt cp_leg_p`: `XM1` tail, `XM2` cascode) have
their width scaled by one factor `k`; every other device, including the DN
leg, the bias replica, the steering switches and the DR-010 dump buffer, is
byte-identical to the committed snapshot.  `k = 1` IS the committed snapshot
(asserted below), so the unperturbed baseline is not a separate deck.

`k` is chosen from a target mismatch with the mirror-ratio inverse of the
bench's own definition,

    mismatch_pct = (Iup + Idn) / ((Iup - Idn) / 2) * 100,   Idn < 0

i.e. `k = (1 + m/200) / (1 - m/200)` for a target `m`, offset by the
snapshot's own nominal `-0.2985 %` so the requested points land near round
numbers.  **That is a starting point, not a claim**: the DC mismatch each
snapshot actually produces is measured by the `dc/` requests this script
emits (RECORD-014's x-axis is the measured value, never the requested one).

What is emitted
---------------
    OUTDIR/dc/<tag>/{cp_mm.spice,tb_cp_mm.sp,request.json}
        One DC request per mismatch point: the same two-point `Vup` sweep and
        the same `mismatch_pct` expression as the Monte Carlo bench, at the
        three temperatures, NO mismatch library (these points are
        deterministic -- the spread is injected by hand, not drawn).
    OUTDIR/loop/<tag>/{pll.cir,request.json}
        One closed-loop transient request per mismatch point, at the three
        temperatures.  `pll.cir` is `tb_pll_cpdiag.sp.tmpl` (RECORD-006's
        probe deck, which RECORD-007 also used) with its `.control`, `.lib`
        and `.tran` cards removed -- klt owns those -- and the block bundle
        from `cpdiag_build.py control_probe` inlined, so the deck is one
        self-contained file with no sibling `.include`.

        Static phase error is NOT a `.meas` quantity: it is the final-20
        reference cycles' mean of `(nearest fb edge - ref edge) / T_ref`
        (`cpdiag_metrics.lock_trace`).  The request therefore declares two
        `measurements[].crossings` series -- every rising 1.65 V crossing of
        `v(ref)` and of `v(fb)` -- and `mismatch_gain_post.py` feeds those
        two edge lists to `mismatch_gain_metrics.lock_trace_from_edges`,
        which `test_mismatch_gain_metrics.py` pins to be the same function
        `cpdiag_metrics.lock_trace` computes from a sampled trace.  The
        supply-current and `vc_avg` `.meas` cards of the template are kept.

Running them (host rules: a grid goes to the batch fleet, never a local loop)
----------------------------------------------------------------------------
    klt sim --batch-set OUTDIR/dc/*/request.json   --wait-for-capacity 600 \
        --format json > reports/sim.mismatch_gain_dc.json
    klt sim --batch-set OUTDIR/loop/*/request.json --wait-for-capacity 600 \
        --format json > reports/sim.mismatch_gain_loop.json
    python3 -I mismatch_gain_post.py reports/sim.mismatch_gain_dc.json \
        reports/sim.mismatch_gain_loop.json ../corners/mismatch_gain.csv
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SNAP = HERE.parent / "netlist-snapshots"

#: Target DC mismatch for each perturbed point, in percent.  The committed
#: snapshot's own nominal is -0.2985 %, which is the unperturbed baseline and
#: is carried as the `k = 1` point rather than as a seventh perturbation.
TARGET_PCT = (-12.0, -8.0, -4.0, 4.0, 8.0, 12.0)
NOMINAL_PCT = -0.2985     # the committed snapshot at VOUT = 2.40 V, Iref = 10 uA
TEMPS = (-40, 27, 125)
MOS_CORNER = "mos_tt"
RES_CORNER = "res_typ"

VDD = "3.3"
FREF = 20e6
TREF = 1.0 / FREF
TSTOP_S = 2500e-9
#: `.subckt cp_leg_p`'s two cascode mirror devices -- the only lines scaled.
LEG_P_MIRROR = re.compile(
    r"(?m)^(XM[12] \S+ \S+ \S+ \S+ sg13_hv_pmos w=)([0-9.]+)(u l=1u ng=1 m=1)$")
LEG_P_BLOCK = re.compile(r"(?ms)^\.subckt cp_leg_p\b.*?^\.ends\s*?$")


def scale_for(target_pct: float) -> float:
    """Mirror-ratio `k` that puts the UP leg `target_pct` above the DN leg.

    The snapshot's own `NOMINAL_PCT` offset is removed first, so `target_pct`
    is the mismatch asked of the finished deck, not of the perturbation.
    """
    m = target_pct - NOMINAL_PCT
    return (1.0 + m / 200.0) / (1.0 - m / 200.0)


def perturb_cp(text: str, k: float) -> str:
    """Scale `.subckt cp_leg_p`'s two mirror widths by `k`; nothing else.

    `k == 1.0` returns `text` byte-for-byte unchanged, so the unperturbed
    point is provably the committed snapshot and not a re-rendered copy of
    it -- the match count is still checked, so a snapshot this function can
    no longer find the mirror devices in is an error at every `k`.
    """
    block = LEG_P_BLOCK.search(text)
    if block is None:
        raise SystemExit("perturb_cp: no `.subckt cp_leg_p` block in the snapshot")
    body, n = LEG_P_MIRROR.subn(
        lambda mo: f"{mo.group(1)}{float(mo.group(2)) * k:.6f}{mo.group(3)}", block.group(0))
    if n != 2:
        raise SystemExit(f"perturb_cp: expected 2 cp_leg_p mirror devices, scaled {n}")
    if k == 1.0:
        return text
    return text[:block.start()] + body + text[block.end():]


def tag_for(target_pct: float | None) -> str:
    if target_pct is None:
        return "mm_nom"
    s = f"{abs(target_pct):g}".replace(".", "p")
    return f"mm_{'n' if target_pct < 0 else 'p'}{s}"


def points() -> list[tuple[str, float | None, float]]:
    """[(tag, target_pct or None for the unperturbed baseline, k), ...]"""
    out = [(tag_for(None), None, 1.0)]
    out += [(tag_for(t), t, scale_for(t)) for t in TARGET_PCT]
    return out


# --------------------------------------------------------------------------
# request bodies
# --------------------------------------------------------------------------
def dc_body(cp_name: str) -> str:
    """The Monte Carlo bench's two-point `Vup` sweep, on a local cp include.

    Byte-for-byte the circuit of `../../sg13cmos5l-cp-icp-trim-mc/testbench/
    tb_cp_mc.sp` apart from the `.include` target: same VOUT = 2.40 V, same
    Iref = 10 uA trim code, same single `XCP` instance for both sweep points.
    """
    return f"""* sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock (issue #385)
* Circuit body for `klt sim` (no .control/.end; klt owns those).
* DC up/dn mismatch of ONE perturbed cp snapshot -- the x-axis of RECORD-014.
* Same deck as ../../sg13cmos5l-cp-icp-trim-mc/testbench/tb_cp_mc.sp (same
* VOUT = 2.40 V operating point, same 10 uA trim code, same two-point sweep
* through one XCP instance); only the included snapshot differs.
.include {cp_name}

Vdd VDD 0 dc 3.3
XCP up dn ibp icp ibn icn vout VDD 0 cp

Irefbp ibp 0 dc 10u
Irefcp icp 0 dc 10u
Irefbn 0 ibn dc 10u
Irefcn 0 icn dc 10u

Vup up 0 dc 0
Bdn dn 0 V=3.3-v(up)
Vout vout 0 dc 2.4
"""


def loop_body(bundle: str, models_inc: str) -> str:
    """`tb_pll_cpdiag.sp.tmpl` as a klt-sim circuit body.

    Drops the cards klt synthesizes itself (`.lib`, `.tran`, `.control`,
    `.end`), substitutes the template placeholders with the same values
    `run_closed_loop_otabuf.sh` uses, and inlines the two `.include` files so
    the request ships one self-contained netlist.
    """
    subs = {"@TEMP@": "@TEMP@", "@VDD@": VDD, "@TREF@": f"{TREF:.6e}",
            "@TREFH@": f"{TREF / 2 - 100e-12:.6e}", "@IREF@": "10u",
            "@B0V@": VDD, "@B1V@": VDD, "@VC0@": "2.46"}
    keep = []
    for ln in (HERE / "tb_pll_cpdiag.sp.tmpl").read_text().splitlines():
        if ln.startswith(".control"):
            break
        if ln.startswith((".lib ", ".tran")):
            # klt owns the model `.lib` cards (via `models.lib`, below) and
            # the `.tran` card (via `analysis`).  `.option scale=1` stays;
            # the template's `temp=@TEMP@` does NOT -- klt emits its own
            # `.temp` per corner, and a second temperature card in the body
            # would silently override the temperature axis.
            continue
        if ln.startswith(".option "):
            keep.append(".option scale=1")
            continue
        if ln.startswith(".include pll_blocks_cpdiag.spice"):
            keep.append(bundle.rstrip("\n"))
            continue
        if ln.startswith(".include cpdiag_models.inc"):
            keep.append(models_inc.rstrip("\n"))
            continue
        keep.append(ln)
    body = "\n".join(keep) + "\n"
    for key, val in subs.items():
        body = body.replace(key, val)
    return body


def corner_wrapper(tech: pathlib.Path) -> str:
    """A one-section model library naming BOTH corner libraries this deck needs.

    `klt sim` resolves exactly one `models.lib`, and leaves a `.lib` card
    written in the *netlist body* verbatim (only `.include` lines are staged
    and rewritten), so the closed-loop deck's own
    `.lib <abs>/cornerRES.lib res_typ` card would name a path that does not
    exist on a fleet worker -- `rppd` would then be an unknown subcircuit.
    `options.stage_model_inputs` does follow file-bearing `.lib <file>
    <section>` references inside a staged library, so this wrapper -- a
    `.lib mos_tt` section that pulls in the pinned `cornerMOShv.lib mos_tt`
    and `cornerRES.lib res_typ` -- ships both closures with the job and is
    rewritten to staged names on the way.
    """
    return (f"* sg13g2-pll :: generated by gen_mismatch_gain_requests.py (issue #385)\n"
            f"* One section per `corners.process` entry; each pulls in the pinned\n"
            f"* MOS-HV corner and the typical resistor corner.\n"
            f".lib {MOS_CORNER}\n"
            f'.lib "{tech}/models/cornerMOShv.lib" {MOS_CORNER}\n'
            f'.lib "{tech}/models/cornerRES.lib" {RES_CORNER}\n'
            f".endl {MOS_CORNER}\n")


def base_options(tech: pathlib.Path, timeout_s: int, osdi: tuple[str, ...]) -> dict:
    return {
        "osdi_preload": [f"{tech}/osdi/{n}.osdi" for n in osdi],
        "stage_model_inputs": True,
        "ngspice_init": ["set numdgt=12", "set num_threads=1"],
        "timeout_s": timeout_s,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("outdir", help="directory to write the request tree into")
    ap.add_argument(
        "--pinned-pdk", default=os.environ.get("PINNED_PDK"),
        help="an ihp-sg13cmos5l tree at sim/README.md's PDK-PIN revision "
             "607e18d4... (env: PINNED_PDK). Required; there is no $PDK_ROOT "
             "fallback -- see the module docstring.")
    a = ap.parse_args()
    if not a.pinned_pdk:
        raise SystemExit(
            "gen_mismatch_gain_requests.py: --pinned-pdk DIR (or PINNED_PDK=DIR) "
            "is required -- an ihp-sg13cmos5l checkout at sim/README.md's "
            "PDK-PIN revision 607e18d4....")
    pdk = pathlib.Path(a.pinned_pdk).expanduser().resolve()
    tech = pdk / "libs.tech" / "ngspice"
    if not (tech / "models" / "cornerMOShv.lib").is_file():
        raise SystemExit(f"--pinned-pdk: {tech}/models/cornerMOShv.lib is not readable")
    out = pathlib.Path(a.outdir).resolve()

    snapshot = (SNAP / "cp_otabuf.spice").read_text()
    corners = {"process": [MOS_CORNER], "temperature_c": list(TEMPS)}
    # The batch fleet's whole-job ceiling is 3600 s and klt's serial bound is
    # timeout_s * units + 120 s, so a 3-temperature transient request needs
    # timeout_s <= 1160 to fit one job.  1100 s is ~2.3x the 8 min a unit of
    # this deck takes on this host; `job_ceiling_check: "split"` is set anyway
    # so a slower fleet instance shards instead of being refused.
    batch = {"capacity_wait_s": 600, "job_ceiling_check": "split",
             "max_concurrent_jobs": 4}

    for tag, target, k in points():
        cp_text = perturb_cp(snapshot, k)

        d = out / "dc" / tag
        d.mkdir(parents=True, exist_ok=True)
        (d / "corner_mm.lib").write_text(corner_wrapper(tech))
        (d / "cp_mm.spice").write_text(cp_text)
        (d / "tb_cp_mm.sp").write_text(dc_body("cp_mm.spice"))
        (d / "request.json").write_text(json.dumps({
            "engine": "ngspice",
            "netlist": "tb_cp_mm.sp",
            "models": {"lib": "corner_mm.lib"},
            "analysis": {"kind": "dc", "args": "Vup 0 3.3 3.3"},
            "measurements": [
                {"name": "iup_a", "unit": "A", "expr": "i(Vout)[1]"},
                {"name": "idn_a", "unit": "A", "expr": "i(Vout)[0]"},
                {"name": "mismatch_pct", "unit": "%",
                 "expr": "(i(Vout)[1] + i(Vout)[0]) / ((i(Vout)[1] - i(Vout)[0]) / 2) * 100"},
            ],
            "options": base_options(tech, 60, ("psp103", "psp103_nqs", "mosvar")),
            "backend": "batch", "batch": batch, "corners": corners,
        }, indent=2) + "\n")

        d = out / "loop" / tag
        d.mkdir(parents=True, exist_ok=True)
        work = d / ".build"
        work.mkdir(exist_ok=True)
        (work / "cp_cascbias.spice").write_text(cp_text)
        for b in ("pfd", "vco", "loop_filter", "lock_detector"):
            (work / f"{b}.spice").write_text((SNAP / f"{b}.spice").read_text())
        subprocess.run([sys.executable, "-I", str(HERE / "cpdiag_build.py"),
                        "control_probe", str(work), str(work)], check=True)
        if (work / "variant.diff").read_text():
            raise SystemExit("control_probe must apply no cp/pfd edit")
        body = loop_body((work / "pll_blocks_cpdiag.spice").read_text(),
                         (work / "cpdiag_models.inc").read_text())
        (d / "corner_mm.lib").write_text(corner_wrapper(tech))
        (d / "pll.cir").write_text(body)
        meas = [{"name": n, "unit": u,
                 "spice": f".meas tran {n} avg {e} from=2000n to={TSTOP_S * 1e9:.0f}n"}
                for n, e, u in (("i_pfd", "i(Vdd_pfd)", "A"), ("i_cp", "i(Vdd_cp)", "A"),
                                ("i_vco", "i(Vdd_vco)", "A"), ("i_ld", "i(Vdd_ld)", "A"),
                                ("vc_avg", "v(vctrl)", "V"))]
        meas += [{"name": f"t_{sig}", "unit": None,
                  "crossings": {"signal": f"v({sig})", "level": 1.65,
                                "edge": "rise", "max": 200}}
                 for sig in ("ref", "fb")]
        (d / "request.json").write_text(json.dumps({
            "engine": "ngspice",
            "netlist": "pll.cir",
            "models": {"lib": "corner_mm.lib"},
            "analysis": {"kind": "tran", "args": f"100p {TSTOP_S * 1e9:.0f}n 0 100p"},
            "measurements": meas,
            "options": {
                **base_options(tech, 1100,
                               ("psp103", "psp103_nqs", "mosvar", "r3_cmc")),
                "save_vectors": ["v(ref)", "v(fb)", "v(vctrl)"],
            },
            "backend": "batch", "batch": batch, "corners": corners,
        }, indent=2) + "\n")
        print(f"wrote {tag}: k={k:.6f} target={'baseline' if target is None else f'{target:+g} %'}")

    manifest = {"pinned_pdk": str(pdk), "temps_c": list(TEMPS),
                "mos_corner": MOS_CORNER, "res_corner": RES_CORNER,
                "points": [{"tag": t, "target_pct": p, "k": k} for t, p, k in points()]}
    (out / "points.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("wrote", out / "points.json")


if __name__ == "__main__":
    main()
