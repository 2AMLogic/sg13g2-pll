#!/usr/bin/env python3
"""Build the seeded PVT campaign and the row-12 supply-ripple units of
sg13g2-pll issue #518 (steps 4-5) as `klt sim` requests.

    python3 -I gen_campaign.py --phase cal  OUTDIR [--pinned-pdk DIR]
    python3 -I gen_campaign.py --phase pvt  OUTDIR --sigma-csv CSV \
            [--pinned-pdk DIR] [--local-probe-only]

`--phase cal` emits ONE deck-list request (`OUTDIR/request.json`, backend
batch) carrying the per-operating-point calibration decks: for each of the
12 campaign points (3 PVT bundles x 2 band codes x 2 VCTRL) a `bias_op`
deck (`vco_bias` .op -> VBP/VBN at that point) and, once those are known to
the fleet run's own consumer, the `cal_noise`/`cal_ac` pair (the .noise
output density and the 1 A |Z_out| sweep of the single linear-biased
`vco_stage`, RECORD-001's calibration circuit, re-run per point because
sigma is corner- and bias-dependent).  The `cal_noise`/`cal_ac` decks take
VBP/VBN from `--bias-csv` (the `calset` extractor's first output); with it
absent only the 12 `bias_op` decks are emitted (the two-step flow run_pvt.sh
drives).  Models ship beside the decks the #318 way (relative `.lib
models/...` + `pre_osdi osdi/...`, staged from the pinned tree by
sim/tools/stage_pinned_pdk.py), so the fleet runner's own PDK tree is never
read.

`--phase pvt` emits the structured corner-matrix requests (netlist +
corners.units + analysis + a `crossings` measurement + options.
stage_model_inputs / osdi_preload / transient_noise_seed), one single-unit
request per point -- the sigma of the injected `trrandom` sources and the
seed are per-operating-point, and both live in the request's own bytes
(sigma in the netlist, seed in `options.transient_noise_seed`; one seed per
request is the #7709 contract, which `decks[]` requests cannot honour at
all).  Points: the 12 campaign units (bundles typ/slow/fast at the kvco
table's own corners, band codes 00/11, VCTRL 1.5/2.1 V, seeds 42..53), the
6 row-12 supply-ripple units at the RECORD-001 reference point (typ/27C,
band 00, VCTRL 1.5 V, seed 42: choked-supply baseline and 1 MHz / 100 MHz
ripple, each noise-on and noise-off), and `probe/` -- the typ/b00/v1p5/seed
42 campaign unit alone, the 1-unit fleet probe the issue's step-6 ladder
runs before the grid.  `--local-probe-only` emits just the probe (the local
backend's method-bridge run: same operating point, seed and sigma as
RECORD-001's committed ring_s42_t10p row, for the crossings-vs-`meas`
precision check RECORD-003 reports).

Sigma comes from `--sigma-csv` (the `calset` extractor's
`corners/calibration_pvt.csv`); the typ/b00/v1p5 row may instead be the
committed RECORD-001 calibration (same columns), which is how the local
probe runs before any fleet calibration exists.

Corner geometry (stated in ../corners/matrix.md and RECORD-003; do not edit
independently): bundles and frequencies are the committed kvco table's own
(`sim/sg13cmos5l-vco-kvco-table/corners/results_rerun318.csv`); the per-unit
`.tran` stop is sized from that table's frequency as 1250/f (>= 50
startup-skip + 1000 measured crossings + margin), rounded up to 10 ns.
"""
import argparse
import csv
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "sim" / "tools"))  # python3 -I: no script dir
from stage_pinned_pdk import pinned_closure, resolve_pinned_pdk, write_staged_manifest  # noqa: E402

SNAP = HERE.parent / "netlist-snapshots" / "vco.spice"
KVCO = HERE.parents[2] / "sim" / "sg13cmos5l-vco-kvco-table" / "corners" / "results_rerun318.csv"
OSDI = ("psp103", "psp103_nqs", "mosvar", "r3_cmc")
OSDI_RIP = OSDI + ("cap_cmomi",)     # the row-12 deck keeps XCDECAP (OSDI model)

# ---- campaign geometry (kvco-table 3-bundle convention) --------------------
BUNDLES = {"typ": ("mos_tt", "res_typ", 27),
           "slow": ("mos_ss", "res_wcs", 125),
           "fast": ("mos_ff", "res_bcs", -40)}
BANDS = {"00": ("0.0", "0.0"), "11": ("3.3", "3.3")}
VCTRLS = ("1.5", "2.1")
TS = "1e-11"                # trrandom sample interval (RECORD-001's)
TSTEP = "10p"               # .tran step (the method's reference step)
RIP_F_HZ = (1e6, 100e6)     # one decade either side of the 10.03 MHz decap pole
RIP_V_PEAK = 0.01           # 10 mV: "small sinusoid", ~0.3 % of the 3.3 V rail
RIP_R_SRC = 3000            # the decap record's illustrative source impedance
#: Thevenin DC behind R_src: 3.3 V + I_ring_DC * R_src, with I_ring_DC =
#: 1.39022 mA measured at this bench's reference point (typ/27C, band 00,
#: VCTRL 1.5 V, ngspice-47, .tran 10p over 600-1200 ns; see RECORD-003).
#: A series R_src alone would drop 4.17 V and collapse the rail (the
#: issue's explicit constraint); the Thevenin form keeps the rail at
#: 3.3 V DC while presenting exactly R_src to the rail's small signals --
#: no choke, so no L*C tank (a 0.1 H feed against the 5.286 pF decap
#: rings for ~33 us, far past any measurement window).
RIP_V_THEV = 3.3 + 1.39022e-3 * 3000
RIP_TSTOP = "3500n"         # ~3.5 ripple cycles at 1 MHz; ~2280 ring crossings
XING_SKIP = 50              # startup crossings skipped by the extractor
XING_NEED = 1000            # measured periods per unit (issue step 1)
PROBE_UNIT = ("typ", "00", "1.5", 42)   # RECORD-001's reference point and seed


def rd(name: str) -> str:
    return (HERE / name).read_text()


def subst(tmpl: str, **vals) -> str:
    s = tmpl
    for k, v in vals.items():
        s = s.replace("@" + k + "@", v)
    left = [t for t in re.findall(r"@\w+@", s) if t not in ("@PDK_ROOT@", "@PDK@", "@OSDI@")]
    if left:
        sys.exit(f"gen_campaign.py: unsubstituted placeholders {left}")
    return s


def staged_paths(text: str) -> str:
    """Rewrite a template's absolute PDK tokens to deck-relative staged
    paths (the #318 transport contract: models/ and osdi/ staged beside the
    decks by stage_pinned_pdk.py, `host_resolved: []`)."""
    return (text
            .replace("$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/", "models/")
            .replace("$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/", "osdi/"))


def freq_table():
    """(bundle, band, vctrl) -> f_hz from the committed kvco table."""
    out = {}
    with open(KVCO) as f:
        for r in csv.DictReader(f):
            out[(r["pvt_bundle"], r["band_code"], f'{float(r["vctrl_v"]):g}')] = \
                float(r["freq_hz"])
    return out


def tstop_for(f_hz: float) -> str:
    ns = math.ceil(1250.0 / f_hz * 1e9 / 10.0) * 10
    return f"{ns:.0f}n"


def xmax_for(f_hz: float, tstop_s: float) -> int:
    return int(math.ceil(tstop_s * f_hz * 1.2)) + 200


def strip_decap(text: str) -> str:
    return re.sub(r"^(XCDECAP)", r"*\1", text, flags=re.M)


# ---------------------------------------------------------------- phase: cal
def gen_cal(a):
    out = a.out.resolve()
    (out / "decks").mkdir(parents=True, exist_ok=True)
    (out / "decks" / "vco_open.spice").write_text(strip_decap(SNAP.read_text()))
    pdk = resolve_pinned_pdk(a.pinned_pdk, prog="gen_campaign.py")
    from stage_pinned_pdk import stage_pinned_pdk
    stage_pinned_pdk(pdk, out / "decks", ["cornerMOShv.lib", "cornerRES.lib"], list(OSDI))

    bias = {}
    if a.bias_csv:
        with open(a.bias_csv) as f:
            for r in csv.DictReader(f):
                bias[(r["bundle"], r["band_code"], r["vctrl_v"])] = (r["vbp_v"], r["vbn_v"])

    decks, meta = [], {"phase": "cal", "points": {}, "pdk": str(pdk)}
    n_bias = 0
    for bundle, (mos, res, temp) in BUNDLES.items():
        for band, (b0v, b1v) in BANDS.items():
            for vc in VCTRLS:
                pid = f"{bundle}_b{band}_v{vc.replace('.', 'p')}"
                shared = {"CORNER_MOS": mos, "CORNER_RES": res, "TEMP": str(temp),
                          "VCTRL": vc, "B0V": b0v, "B1V": b1v,
                          "PDK_ROOT": "$PDK_ROOT", "PDK": "ihp-sg13cmos5l",
                          "OSDI": "$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi"}
                meta["points"][pid] = {"bundle": bundle, "band_code": band,
                                       "vctrl_v": vc, "mos": mos, "res": res,
                                       "temp_c": temp, "units": []}
                tb = subst(rd("tb_bias_op.sp.tmpl"), **shared)
                tb = tb.replace(
                    "corner and operating point (mos_tt/res_typ/27C, band 00, "
                    "VCTRL=1.5V).",
                    f"corner and operating point ({mos}/{res}/{temp}C, band "
                    f"{band}, VCTRL={vc}V).")
                tb = tb.replace("../testbench/gen_decks.py",
                                "../testbench/gen_campaign.py")
                tb = staged_paths(tb)
                did = f"{pid}__bias"
                (out / "decks" / f"{did}.sp").write_text(tb)
                decks.append({"id": did, "deck": f"decks/{did}.sp", "timeout_s": 600})
                meta["points"][pid]["units"].append(did)
                n_bias += 1
                if (bundle, band, vc) in bias:
                    vbp, vbn = bias[(bundle, band, vc)]
                    for tag, tmpl in (("noise", "tb_cal_noise.sp.tmpl"),
                                      ("ac", "tb_cal_ac.sp.tmpl")):
                        t = staged_paths(subst(rd(tmpl), VBP=vbp, VBN=vbn, **shared))
                        did2 = f"{pid}__{tag}"
                        (out / "decks" / f"{did2}.sp").write_text(t)
                        decks.append({"id": did2, "deck": f"decks/{did2}.sp",
                                      "timeout_s": 900})
                        meta["points"][pid]["units"].append(did2)
    (out / "cal_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    (out / "request.json").write_text(json.dumps({
        "engine": "ngspice",
        "models": {"pdk": "ihp-sg13cmos5l"},
        "decks": decks,
        "options": {"timeout_s": max(d["timeout_s"] for d in decks)},
        "backend": "batch",
        "batch": {"capacity_wait_s": 600, "job_timeout_s": 3500},
    }, indent=2) + "\n")
    print(f"cal: {n_bias} bias + {len(decks) - n_bias} noise/ac decks "
          f"({'bias-csv given' if a.bias_csv else 'bias only, rerun with --bias-csv'}); "
          f"staged models from {pdk}; deck lists stay ONE batch job "
          f"(klt: only corner requests shard)")


# ---------------------------------------------------------------- phase: pvt
def vco_body(sigma: str, ripple: dict | None = None,
             caplib: pathlib.Path | None = None) -> str:
    """The ring netlist as a klt-sim circuit body: the snapshot's own
    subckt definitions with XCDECAP stripped (ideal-rail campaign units) or
    retained (row-12 ripple units), the top-level ring instantiation of
    tb_ring_jitter.sp.tmpl, and the five calibrated trrandom sources.

    Cards klt composes itself (.lib corner sections, .tran, .control,
    save) are absent; `.option scale=1` (no `temp=`) and `.ic` stay --
    RECORD-001's solver options verbatim, with klt's per-corner `.temp`.
    The ripple variant's `cap_cmomi.lib` rides as a body `.include`:
    cap_cmomi is a plain `.subckt`, not a corner-section `.lib` (the
    wrapper's `.lib <file> cap_cmomi` form is refused by ngspice --
    "section definition not found"), and the netlist's .include closure
    ships with the job the same #319 staging way.
    """
    snap = SNAP.read_text()
    defs = snap if ripple else strip_decap(snap)
    lines = [
        "* sg13g2-pll :: gen_campaign.py (issue #518 steps 4-5)",
        "* vco snapshot body " + ("WITH XCDECAP (row-12 ripple unit)"
                                  if ripple else "(XCDECAP-stripped, ideal rail)"),
        "* + one calibrated trrandom noise source per ring-stage output",
        "* (RECORD-001 noise injection model; sigma per operating point).",
        ".option scale=1",
        ".global sub!",
    ]
    if caplib is not None:
        lines.append(f'.include "{caplib}"')
    lines.append(defs.rstrip("\n"))
    lines += [
        "vctrl vctrl 0 dc @VCTRL@",
        "vb0 b0 0 dc @B0V@",
        "vb1 b1 0 dc @B1V@",
    ]
    if ripple:
        lines += [
            "* -- Thevenin supply: the decap record's illustrative",
            f"* R_src={RIP_R_SRC} ohm source impedance, with the DC set to",
            f"* 3.3 V + I_ring_dc*R_src = {RIP_V_THEV:.5f} V so the rail sits",
            "* at 3.3 V DC (a bare series R_src drops ~4.2 V and collapses",
            "* the rail).  ngspice semantics: in a .tran the SIN spec alone",
            "* is the waveform (a `dc <v> sin(0 a f)` source is the SIN",
            "* around ZERO -- measured), so the offset rides inside the",
            f"* sin() and the dc token carries the same value for .op.",
            "* f_pole = 1/(2 pi R_src C_decap) = 10.03 MHz --",
            "vfeed vsrc 0 dc " + f"{RIP_V_THEV:.5f} sin({RIP_V_THEV:.5f} "
            "@VRIP@ @FRIP@)",
            f"rs vsrc vdd {RIP_R_SRC}",
            "XCDECAP vdd 0 cap_cmomi w=70u l=70u mmin=1 mmax=4 feed=double "
            "subblock=0 m=1 mm_ok=1",
        ]
    else:
        lines.append("vdd vdd 0 dc 3.3")
    lines += [
        "vsub sub! 0 dc 0",
        "xbias vctrl b0 b1 vbp vbn vdd 0 vco_bias",
        "xs1 ring5 vbp vbn ring1 vdd 0 vco_stage",
        "xs2 ring1 vbp vbn ring2 vdd 0 vco_stage",
        "xs3 ring2 vbp vbn ring3 vdd 0 vco_stage",
        "xs4 ring3 vbp vbn ring4 vdd 0 vco_stage",
        "xs5 ring4 vbp vbn ring5 vdd 0 vco_stage",
        "xbuf1 ring1 bufmid vdd 0 inv2x_hv",
        "xbuf2 bufmid clk vdd 0 inv2x_hv",
        f"inj1 ring1 0 dc 0 trrandom(2, {TS}, 0, {sigma})",
        f"inj2 ring2 0 dc 0 trrandom(2, {TS}, 0, {sigma})",
        f"inj3 ring3 0 dc 0 trrandom(2, {TS}, 0, {sigma})",
        f"inj4 ring4 0 dc 0 trrandom(2, {TS}, 0, {sigma})",
        f"inj5 ring5 0 dc 0 trrandom(2, {TS}, 0, {sigma})",
        ".ic v(ring1)=0.5",
    ]
    return "\n".join(lines) + "\n"


def corner_wrapper(tech: pathlib.Path, mos: str, res: str) -> str:
    out = ["* sg13g2-pll :: generated by gen_campaign.py (issue #518)",
           "* The request's one PVT bundle; file-bearing .lib references the",
           "* stage_model_inputs closure ships (pinned bytes, RECORD-015 trap).",
           "* (cap_cmomi.lib, a plain .subckt library, rides as a body",
           "* .include of the ripple netlists instead -- see vco_body.)"]
    out += [f".lib {mos}",
            f'.lib "{tech}/models/cornerMOShv.lib" {mos}',
            f'.lib "{tech}/models/cornerRES.lib" {res}',
            f".endl {mos}"]
    return "\n".join(out) + "\n"


def write_structured(d: pathlib.Path, uid: str, body: str, mos: str, res: str,
                     temp: int, tech: pathlib.Path, seed: int, tstop: str,
                     xmax: int, rail: str, cap_osdi: bool = False,
                     rail_meas: bool = False,
                     timeout_s: int = 2400) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "corner.lib").write_text(corner_wrapper(tech, mos, res))
    (d / f"{uid}.cir").write_text(body)
    meas = [{"name": "t_clk", "unit": None,
             "crossings": {"signal": "v(clk)", "level": 1.65,
                           "edge": "rise", "max": xmax}}]
    if rail_meas:
        # the row-12 unit's DC-bias proof: the rail must stay at 3.3 V
        # (the Thevenin sizing) with only the small ripple on it
        meas += [{"name": f"vdd_{k}", "unit": "V",
                  "spice": f".meas tran vdd_{k} {k} v(vdd) from=1000n"}
                 for k in ("avg", "min", "max")]
    (d / "request.json").write_text(json.dumps({
        "engine": "ngspice",
        "netlist": f"{uid}.cir",
        "models": {"lib": "corner.lib"},
        "analysis": {"kind": "tran", "args": f"{TSTEP} {tstop}"},
        "measurements": meas,
        "options": {
            "osdi_preload": [f"{tech}/osdi/{n}.osdi" for n in
                             (OSDI_RIP if cap_osdi else OSDI)],
            "stage_model_inputs": True,
            "transient_noise_seed": seed,
            "ngspice_init": ["set numdgt=12", "set num_threads=4"],
            "timeout_s": timeout_s,
            "max_workers": 4,
        },
        "backend": "batch",
        "batch": {"capacity_wait_s": 600, "job_timeout_s": 3400,
                  "max_units_per_job": 1, "max_concurrent_jobs": 2},
        "corners": {"units": [{"process": mos, "temperature_c": temp,
                               **({"supply_v": {rail: 3.3}} if rail else {})}]},
    }, indent=2) + "\n")


def gen_pvt(a):
    if not a.sigma_csv:
        sys.exit("gen_campaign.py: --sigma-csv required for phase pvt")
    sigma, vbpv = {}, {}
    with open(a.sigma_csv) as f:
        for r in csv.DictReader(f):
            sigma[(r["bundle"], r["band_code"], r["vctrl_v"])] = r["sigma_a"]
            vbpv[(r["bundle"], r["band_code"], r["vctrl_v"])] = (r["vbp_v"], r["vbn_v"])
    freq = freq_table()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    pdk = resolve_pinned_pdk(a.pinned_pdk, prog="gen_campaign.py")
    tech = pdk / "libs.tech" / "ngspice"
    if not (tech / "models" / "cornerMOShv.lib").is_file():
        sys.exit(f"gen_campaign.py: {tech}/models/cornerMOShv.lib not readable")
    units, probe_dir = [], None

    def emit(uid, bundle, band, vc, seed, ripple=None, tstop=None):
        mos, res, temp = BUNDLES[bundle]
        body = vco_body(sigma[(bundle, band, vc)], ripple,
                        caplib=tech / "models" / "cap_cmomi.lib" if ripple else None)
        body = (body.replace("@VCTRL@", vc).replace("@B0V@", BANDS[band][0])
                .replace("@B1V@", BANDS[band][1]))
        if ripple:
            body = body.replace("@FRIP@", f"{ripple:.6g}") \
                       .replace("@VRIP@", f"{RIP_V_PEAK:.6g}")
        if re.search(r"@[A-Za-z0-9_]+@", body):
            sys.exit(f"gen_campaign.py: unsubstituted token in {uid} body")
        f_hz = freq[(bundle, band, vc)]
        ts_ = tstop or tstop_for(f_hz)
        xm = xmax_for(f_hz, _parse_tstop(ts_))
        rail = "vdd" if not ripple else ""
        d = out / uid
        write_structured(d, uid, body, mos, res, temp, tech, seed, ts_, xm,
                         rail, cap_osdi=bool(ripple),
                         rail_meas=bool(ripple))
        units.append({"unit_id": uid, "bundle": bundle, "band_code": band,
                      "vctrl_v": vc, "mos": mos, "res": res, "temp_c": temp,
                      "seed": seed, "sigma_a": sigma[(bundle, band, vc)],
                      "vbp_v": vbpv[(bundle, band, vc)][0],
                      "vbn_v": vbpv[(bundle, band, vc)][1],
                      "f_est_hz": f"{f_hz:.6e}", "tstop_s": ts_,
                      "xmax": xm, "ripple_hz": ripple or "",
                      "kind": "ripple" if ripple else "pvt"})
        return d

    if a.local_probe_only:
        b, band, vc, seed = PROBE_UNIT
        d = emit("probe", b, band, vc, seed)
        print(f"local probe only: probe -> {d / 'request.json'}")
        return

    # the fleet probe shares the campaign's first unit bytes exactly; the
    # 12 campaign units take seeds 42..53 in (bundle, band, vctrl) order
    pts = [(b, band, vc) for b in BUNDLES for band in BANDS for vc in VCTRLS]
    for i, (bundle, band, vc) in enumerate(pts):
        uid = "probe" if (bundle, band, vc) == PROBE_UNIT[:3] else \
            f"pvt_{bundle}_b{band}_v{vc.replace('.', 'p')}"
        d = emit(uid, bundle, band, vc, 42 + i)
        if (bundle, band, vc) == PROBE_UNIT[:3]:
            probe_dir = d

    # row-12 supply-ripple units at RECORD-001's reference point: all seed
    # 42 (the seed-matched differencing that separates the deterministic
    # period modulation from the random jitter needs one stream), the
    # noise-on units at the calibrated sigma, the _off twins at sigma=0,
    # and the zero-ripple baseline sharing the choked-supply topology.
    ref = PROBE_UNIT[:3]
    f_hz = freq[ref]
    rip = [("ripbase_s42", None, True), ("ripbase_off_s42", None, False),
           ("rip_f1M_s42", RIP_F_HZ[0], True), ("rip_f1M_off_s42", RIP_F_HZ[0], False),
           ("rip_f100M_s42", RIP_F_HZ[1], True), ("rip_f100M_off_s42", RIP_F_HZ[1], False)]
    for uid, f_rip, noise_on in rip:
        mos, res, temp = BUNDLES["typ"]
        sig = sigma[ref] if noise_on else "0.00000e+00"
        body = vco_body(sig, ripple={"f": f_rip if f_rip else RIP_F_HZ[0],
                                     "v": RIP_V_PEAK if f_rip else 0.0},
                        caplib=tech / "models" / "cap_cmomi.lib")
        body = body.replace("@VCTRL@", ref[2]).replace("@B0V@", BANDS[ref[1]][0]) \
                   .replace("@B1V@", BANDS[ref[1]][1])
        body = body.replace("@FRIP@", f"{(f_rip if f_rip else RIP_F_HZ[0]):.6g}") \
                   .replace("@VRIP@", f"{(RIP_V_PEAK if f_rip else 0.0):.6g}")
        write_structured(out / uid, uid, body, mos, res, temp, tech, 42,
                         RIP_TSTOP, xmax_for(f_hz, _parse_tstop(RIP_TSTOP)),
                         "", cap_osdi=True, rail_meas=True, timeout_s=3400)
        units.append({"unit_id": uid, "bundle": "typ", "band_code": ref[1],
                      "vctrl_v": ref[2], "mos": mos, "res": res, "temp_c": temp,
                      "seed": 42, "sigma_a": sig,
                      "vbp_v": vbpv[ref][0], "vbn_v": vbpv[ref][1],
                      "f_est_hz": f"{f_hz:.6e}", "tstop_s": RIP_TSTOP,
                      "xmax": xmax_for(f_hz, _parse_tstop(RIP_TSTOP)),
                      "ripple_hz": f"{f_rip:.6g}" if f_rip else "0",
                      "kind": "ripple"})

    rows = pinned_closure(pdk, ["cornerMOShv.lib", "cornerRES.lib", "cap_cmomi.lib"],
                          OSDI_RIP, label="pinned closure")
    write_staged_manifest(out / "pinned-closure.csv", rows)
    with open(out / "units.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(units[0].keys()))
        w.writeheader()
        w.writerows(units)
    members = sorted(p for p in out.iterdir() if (p / "request.json").is_file())
    print(f"wrote {len(members)} structured requests under {out}:")
    for p in members:
        print(f"  {p.name}")
    print(f"probe first: klt sim {probe_dir / 'request.json'} --backend batch "
          f"--wait-for-capacity 600 ...")
    print("then the grid: klt sim --batch-set " +
          " ".join(str(p / "request.json") for p in members if p.name != "probe") +
          " --wait-for-capacity 600 --capacity-retries 3 --format json "
          "--report-out pvt.report.json")


def _parse_tstop(s: str) -> float:
    m = re.match(r"^([\d.]+)([a-z]*)$", s.strip())
    if not m:
        sys.exit(f"gen_campaign.py: bad tstop {s!r}")
    return float(m.group(1)) * {"": 1.0, "p": 1e-12, "n": 1e-9, "u": 1e-6,
                                "m": 1e-3}[m.group(2)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--phase", required=True, choices=["cal", "pvt"])
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--pinned-pdk", default=None,
                    help="an ihp-sg13cmos5l tree at sim/README.md's PDK-PIN "
                         "revision (env: PINNED_PDK). Required.")
    ap.add_argument("--bias-csv", default=None,
                    help="calset extractor's calibration_bias_pvt.csv; phase cal "
                         "then also emits the noise/ac decks")
    ap.add_argument("--sigma-csv", default=None,
                    help="calset extractor's calibration_pvt.csv (sigma per point)")
    ap.add_argument("--local-probe-only", action="store_true")
    a = ap.parse_args()
    if a.phase == "cal":
        gen_cal(a)
    else:
        gen_pvt(a)


if __name__ == "__main__":
    main()
