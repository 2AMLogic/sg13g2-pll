#!/usr/bin/env python3
"""Build the `klt sim` requests for the 125 C acquisition diagnosis (issue #389,
RECORD-015): RECORD-014's closed-loop grid railed at 125 C without acquiring at
any mismatch point, and this script emits the two measurements that diagnose
why.

    python3 -I gen_125c_acquisition_requests.py --pinned-pdk DIR OUTDIR

`DIR` is an `ihp-sg13cmos5l` tree at `sim/README.md`'s
`PDK-PIN ihp-sg13cmos5l 607e18d4...`; there is no `$PDK_ROOT` fallback (same
rule and reason as `gen_mismatch_gain_requests.py`, whose staged-bytes
mechanism this reuses).

What is emitted
---------------
OUTDIR/vco/{decks/...,decks.sha256.csv,staged_pdk.sha256.csv,request.json}
    An open-loop VCO deck-list request at `mos_tt` / `res_typ` / 125 C /
    3.3 V: band `11` (the proposal deck's own selection,
    `run_closed_loop_otabuf.sh`: `B0V=$VDD; B1V=$VDD`) swept with `vctrl`
    taken past the rail to 3.3 V, plus a four-band probe at one `vctrl`
    (2.1 V) because the committed Kvco table shows band code to be inert in
    that bench (`results_rerun318.csv`: byte-identical period at equal
    `vctrl` for all four codes) -- the record must not conclude anything from
    the band choice before this probe shows whether the inputs move the
    frequency here.  The DUT is this slug's own frozen
    `../netlist-snapshots/vco.spice` with `XCDECAP` commented out, exactly
    the derivation `../../sg13cmos5l-vco-kvco-table/testbench/run.sh` uses
    for its own open-loop bench; the deck body is that bench's
    `tb_vco_kvco.sp.tmpl` with the model `.lib` paths rewritten to the
    staged `models/` closure (the deck-list staging contract
    `gen_rerun318.py` documents) and the four OSDI objects preloaded with
    `pre_osdi` lines because a deck-list unit has no `.spiceinit`.

OUTDIR/loop_nominal/{pll.cir,corner_mm.lib,request.json}
    RECORD-014's unperturbed (`mm_nom`, `k` = 1) closed-loop deck narrowed
    to the single corner where it failed to acquire -- `mos_tt` / `res_typ`
    / 125 C -- built by importing `gen_mismatch_gain_requests.py` unmodified
    (`perturb_cp` at `k` = 1 returns the committed snapshot byte for byte,
    asserted here against the snapshot's sha256).  This is the sanity point
    the issue's test plan asks for: with the unchanged deck it must
    reproduce RECORD-014's railed `vc_avg` 3.28989 V before any deck
    variable is changed.  Same measurement block, same `.meas` window and
    the same `crossings` series as the RECORD-014 loop requests, so
    `mismatch_gain_metrics.lock_trace_from_edges` / `cpdiag_metrics` read it
    unchanged.

Running them (host rules: a grid goes to the batch fleet, never a local loop)
----------------------------------------------------------------------------
    klt sim --batch-set OUTDIR/vco/request.json OUTDIR/loop_nominal/request.json \
        --wait-for-capacity 600 --capacity-retries 3 --format json
    python3 -I collect_125c_acquisition.py <vco -o DIR> OUTDIR/vco/decks.sha256.csv \
        <loop report> --vco-csv ../corners/vco_openloop_125c.csv \
        --loop-json ../corners/loop_nominal_125c_metrics.json
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SNAP = HERE.parent / "netlist-snapshots"
REPO = HERE.parents[2]

sys.path.insert(0, str(REPO / "sim" / "tools"))  # python3 -I: no script dir
from stage_pinned_pdk import (  # noqa: E402
    resolve_pinned_pdk, sha256, stage_pinned_pdk, write_staged_manifest,
)

sys.path.insert(0, str(HERE))
import gen_mismatch_gain_requests as g  # noqa: E402  (same directory)

#: The one PVT bundle this diagnosis runs: exactly the corner where
#: RECORD-014's grid railed (mos_tt / res_typ / 125 C), at 3.3 V as every
#: deck in this slug.
MOS_CORNER = "mos_tt"
RES_CORNER = "res_typ"
TEMP_C = "125"

#: Band `11` is what the proposal deck selects (`B0V=$VDD; B1V=$VDD`,
#: `run_closed_loop_otabuf.sh:76`).  The sweep takes `vctrl` past RECORD-014's
#: railed 3.289 V to the 3.3 V rail; 0.3..2.7 are the committed Kvco table's
#: own points so the new curve anchors to it.
BAND_11 = ("11", "3.3", "3.3")
SWEEP_VCTRLS = ["0.3", "0.9", "1.5", "2.1", "2.7", "3.0", "3.3"]
#: Four-band probe at one `vctrl` -- band `11` at 2.1 V is already a sweep
#: point, so these three complete the set the inertness check compares.
PROBE_BANDS = [("00", "0.0", "0.0"), ("01", "0.0", "3.3"), ("10", "3.3", "0.0")]
PROBE_VCTRL = "2.1"

#: Exactly `gen_rerun318.py`'s OSDI list for this DUT (the staged-closure
#: deck-list units have no `.spiceinit` to preload from).
OSDI = ["psp103", "psp103_nqs", "mosvar", "r3_cmc"]

VCO_DECK = """\
* sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock (issue #389, RECORD-015)
* Open-loop VCO probe at @MOS@/@RES@/@TEMP@ C, band @BAND@ (B0V=@B0V@ B1V=@B1V@),
* VCTRL=@VCTRL@ V.  Deck body: ../../sg13cmos5l-vco-kvco-table/testbench/
* tb_vco_kvco.sp.tmpl with its model .lib paths rewritten to the staged
* `models/` closure and the OSDI objects preloaded in-control (deck-list
* units have no .spiceinit) -- the same staging contract
* gen_rerun318.py documents for that bench's own pinned rerun.  DUT: this
* slug's frozen ../netlist-snapshots/vco.spice with XCDECAP commented out,
* exactly what the Kvco bench's run.sh derives for the same measurement.
* The `.ic` breaks the ring's node symmetry exactly as that bench's deck
* does.  Band `11` is the proposal deck's own selection; the band probe
* units in this request exist because the committed Kvco table shows band
* code inert there -- confirm it moves frequency here before concluding
* anything from the band choice (issue #389's verified correction 4).

.lib models/cornerMOShv.lib @MOS@
.lib models/cornerRES.lib @RES@
.option scale=1 temp=@TEMP@
.global sub!

.include vco_open.spice

Vvctrl vctrl 0 dc @VCTRL@
Vb0 b0 0 dc @B0V@
Vb1 b1 0 dc @B1V@
Vdd vdd 0 dc 3.3
Vsub sub! 0 dc 0

Xvco vctrl b0 b1 clk vdd 0 vco

.ic v(xvco.ring1)=0.5

.tran 20p 40n

.control
pre_osdi osdi/psp103.osdi
pre_osdi osdi/psp103_nqs.osdi
pre_osdi osdi/mosvar.osdi
pre_osdi osdi/r3_cmc.osdi
run
meas tran per1 trig v(clk) val=1.65 rise=3 targ v(clk) val=1.65 rise=4
print per1
.endc
.end
"""


def write_vco_request(pdk: pathlib.Path, out: pathlib.Path) -> None:
    decks_dir = out / "vco" / "decks"
    if decks_dir.exists():
        shutil.rmtree(decks_dir)
    decks_dir.mkdir(parents=True)

    staged = stage_pinned_pdk(pdk, decks_dir,
                              ["cornerMOShv.lib", "cornerRES.lib"], OSDI)

    # The DUT: the Kvco bench's own XCDECAP-stripped derivation of this
    # slug's frozen snapshot (the snapshot itself stays an exact export).
    snap = (SNAP / "vco.spice").read_text()
    stripped, n = re.subn(r"(?m)^(XCDECAP)", r"*\1", snap)
    if n != 1:
        raise SystemExit(f"vco snapshot: expected 1 XCDECAP line, commented {n}")
    (decks_dir / "vco_open.spice").write_text(stripped)

    decks, rows = [], []
    units = [(f"b{b[0]}_v{v.replace('.', 'p')}", b, v)
             for v in SWEEP_VCTRLS for b in [BAND_11]]
    units += [(f"b{b[0]}_v{PROBE_VCTRL.replace('.', 'p')}", b, PROBE_VCTRL)
              for b in PROBE_BANDS]
    for uid, (band, b0v, b1v), vctrl in units:
        text = VCO_DECK
        for token, value in (("@MOS@", MOS_CORNER), ("@RES@", RES_CORNER),
                             ("@TEMP@", TEMP_C), ("@BAND@", band),
                             ("@B0V@", b0v), ("@B1V@", b1v), ("@VCTRL@", vctrl)):
            text = text.replace(token, value)
        if "@" in re.sub(r"(?m)^\*.*$", "", text):
            raise SystemExit(f"{uid}: unsubstituted @TOKEN@ left in deck")
        (decks_dir / f"{uid}.sp").write_text(text)
        decks.append({"id": uid, "deck": f"decks/{uid}.sp", "timeout_s": 600})
        rows.append((uid, MOS_CORNER, RES_CORNER, TEMP_C, band, vctrl,
                     sha256(decks_dir / f"{uid}.sp")))

    (out / "vco" / "request.json").write_text(json.dumps({
        "engine": "ngspice",
        "backend": "batch",
        # Selects the fleet image, exactly as gen_rerun318.py does.  The
        # model bytes themselves are the staged ones, not this image's.
        "models": {"pdk": "ihp-sg13cmos5l"},
        "decks": decks,
        "batch": {"capacity_wait_s": 600},
        "options": {"timeout_s": 600, "max_workers": 2},
    }, indent=2) + "\n")

    with open(out / "vco" / "decks.sha256.csv", "w", newline="") as fh:
        import csv
        w = csv.writer(fh)
        w.writerow(["id", "mos_corner", "res_corner", "temp_c", "band_code",
                    "vctrl_v", "deck_sha256"])
        w.writerows(rows)
    write_staged_manifest(out / "vco" / "staged_pdk.sha256.csv", staged)
    print(f"wrote {len(decks)} vco decks to {out / 'vco'}")


def write_loop_nominal_request(pdk: pathlib.Path, out: pathlib.Path) -> None:
    """RECORD-014's `mm_nom` loop deck at 125 C only, via the committed
    generator's own functions."""
    tech = pdk / "libs.tech" / "ngspice"
    d = out / "loop_nominal"
    d.mkdir(parents=True, exist_ok=True)

    snapshot_path = g.SNAP / "cp_otabuf.spice"
    snapshot = snapshot_path.read_text()
    cp_text = g.perturb_cp(snapshot, 1.0)
    if cp_text != snapshot:
        raise SystemExit("k=1 must return the snapshot byte for byte")
    # RECORD-014 cites c8a55d8d... for this snapshot; print the bytes that
    # ran so the record can state them.
    cp_sha = sha256(snapshot_path)

    work = d / ".build"
    work.mkdir(exist_ok=True)
    (work / "cp_cascbias.spice").write_text(cp_text)
    for b in ("pfd", "vco", "loop_filter", "lock_detector"):
        (work / f"{b}.spice").write_text((SNAP / f"{b}.spice").read_text())
    subprocess.run([sys.executable, "-I", str(g.HERE / "cpdiag_build.py"),
                    "control_probe", str(work), str(work)], check=True)
    if (work / "variant.diff").read_text():
        raise SystemExit("control_probe must apply no cp/pfd edit")
    body = g.loop_body((work / "pll_blocks_cpdiag.spice").read_text(),
                       (work / "cpdiag_models.inc").read_text())
    (d / "corner_mm.lib").write_text(g.corner_wrapper(tech))
    (d / "pll.cir").write_text(body)

    fref = g.FREF
    tstop = g.TSTOP_S
    meas = [{"name": n, "unit": u,
             "spice": f".meas tran {n} avg {e} from=2000n to={tstop * 1e9:.0f}n"}
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
        "analysis": {"kind": "tran", "args": f"100p {tstop * 1e9:.0f}n 0 100p"},
        "measurements": meas,
        "options": {
            **g.base_options(tech, 1100, ("psp103", "psp103_nqs", "mosvar", "r3_cmc")),
            "save_vectors": ["v(ref)", "v(fb)", "v(vctrl)"],
        },
        "backend": "batch",
        "batch": {"capacity_wait_s": 600, "job_ceiling_check": "split",
                  "max_concurrent_jobs": 4},
        "corners": {"process": [MOS_CORNER], "temperature_c": [int(TEMP_C)]},
    }, indent=2) + "\n")
    print(f"wrote loop_nominal request (cp snapshot sha256 {cp_sha[:16]}...)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("outdir", help="directory to write the request tree into")
    ap.add_argument(
        "--pinned-pdk", default=None,
        help="an ihp-sg13cmos5l tree at sim/README.md's PDK-PIN revision "
             "607e18d4... (env: PINNED_PDK). Required.")
    a = ap.parse_args()
    pdk = resolve_pinned_pdk(a.pinned_pdk,
                             prog="gen_125c_acquisition_requests.py")
    if not (pdk / "libs.tech" / "ngspice" / "models" / "cornerMOShv.lib").is_file():
        raise SystemExit(f"--pinned-pdk: {pdk} has no ngspice model closure")
    out = pathlib.Path(a.outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_vco_request(pdk, out)
    write_loop_nominal_request(pdk, out)
    print("submit with: klt sim --batch-set OUTDIR/vco/request.json "
          "OUTDIR/loop_nominal/request.json --wait-for-capacity 600 "
          "--capacity-retries 3 -o OUTDIR/sim-out --format json")


if __name__ == "__main__":
    main()
