#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-loop-bandwidth-pm/testbench/gen_issue196_ccp_requests.py
(issue #196, Part of #16) -- RECORD-005 of this slug.

The PM bench of RECORD-001..004 (tb_loop_ac_real_resized.sp.tmpl) drives the
loop-filter node with an ideal transconductor `Gcp`, so nothing the real `cp`
hangs on VCTRL (steering-switch and leg drain capacitance, the DR-010
`cp_dumpbuf` input gates) is in the phase-margin evidence. C2 is ~100 fF, so
a few fF matters. This generator writes two `klt sim` benches that close that
gap without editing any earlier template, script, CSV or record:

    PDK_ROOT=<parent of ihp-sg13cmos5l> python3 gen_issue196_ccp_requests.py

1. tb_cp_cout_issue196.sp  -- cp idle-state VOUT capacitance (no PM).
   For 14 VOUT points 0.3..2.9 V, four idle (UP = DN = 0) cp instances, each
   with its own 0 V ammeter from one shared AC source Vs_<k>:
     c375_<k>, c10_<k>, c11_<k>  real `cp` at the 3.75 / 10 / 11 uA codes
                                 (DR-007 code, RECORD-005 reference, DR-008)
     b10_<k>                     `cp_idealdump` at 10 uA (XBUF -> ideal VCVS,
                                 exactly as ../../sg13cmos5l-cp-icp-trim/
                                 testbench/tb_cp_otabuf_cin.sp), i.e. the
                                 legs + switches + bias replica only
   Nothing else sits on the source, so imag(i)/omega is the TOTAL capacitance
   the cp presents on VOUT ("real cp vs no cp"); c10 - b10 is the buffer-only
   part and must reproduce cp-icp-trim RECORD-005's cin_ff_* (regression
   anchor for the method).
     cout_nominal.request.json   typ bundle (mos_tt/27 C), local, ONE corner
     cout_bundles.request.json   fast + slow bundles, batch fleet only

2. tb_loop_ac_ccp_issue196.sp -- the PM bench with the REAL cp on VCTRL.
   Four tuples (the ones DR-007 / DR-008 closed), with Kd/Kv/N read from the
   committed CSVs of RECORD-003/004 so the operating point cannot drift:
     dr008_fast / dr008_typ / dr008_slow   band 00, low,  f_ref 4.5 MHz, 11 uA
     dr007_slow                            band 00, mid,  f_ref 4.5 MHz, 3.75 uA
   For each tuple:
     <t>_nocp       the RECORD-003/004 loop verbatim (C_cp = 0): regression
                    anchor, must reproduce their pm_deg/fc_hz.
     <t>_v<v>       the same loop plus a real idle `cp` (that tuple's own trim
                    code) with its VOUT pin ON the loop-filter node, biased to
                    VCTRL = v through a 1 TH inductor (DC only: |Z| = 2.5e15
                    Ohm at 400 kHz vs R1 = 344 kOhm; its resonance with C1+C2
                    is ~0.1 Hz, below the 10 Hz sweep start), for the 14 VCTRL
                    points 0.3..2.9 V. The cp's whole small-signal admittance
                    (C and G) is in the loop, not a lumped estimate.
     <t>_lonly      the bias network (Lb + Vb at 1.5 V) with NO cp: control,
                    must equal <t>_nocp, proving the bias path is invisible.
   In the biased loops the VCO integrator is driven by v(vc) - v(vb) (vb has no
   AC, so the AC loop is identical) -- otherwise the DC bias winds the ideal
   integrator to ~1e23 V and the operating point fails.
   PM per loop = 180 deg + phase(v(fb)) at |v(fb)| = 1 (vp is in (-pi, pi];
   the type-2 open loop sits between -180 and 0 deg at crossover, so no wrap
   for 0 < PM < 180).
     pm_ccp_nominal.request.json   typ bundle (mos_tt/res_typ/27 C), local
     pm_ccp_bundles.request.json   fast + slow bundles, batch fleet only

   Every corner evaluates every tuple's loops (one deck, one netlist per
   request); only a tuple's OWN bundle is its result. summarize_issue196.py
   reads exactly those and ignores the off-bundle rows.

Bundles (the same three RECORD-002..004 use):
     fast = mos_ff + res_bcs at -40 C, typ = mos_tt + res_typ at 27 C,
     slow = mos_ss + res_wcs at 125 C.

models.pdk is omitted on purpose: klt's batch backend refuses ihp-sg13cmos5l
(2AMLogic/klayout-tools#2727), so the model library ships through
options.stage_model_inputs, as in ../../sg13cmos5l-cp-icp-trim/testbench/.
"""
import csv
import json
import math
import os
import pathlib

pdk_root = os.environ.get("PDK_ROOT", "/home/ubuntu/share/pdk")
tech = f"{pdk_root}/ihp-sg13cmos5l/libs.tech/ngspice"
here = pathlib.Path(__file__).resolve().parent
slug = here.parent
sim = slug.parent

MOS_LIB = f"{tech}/models/cornerMOShv.lib"
RES_LIB = f"{tech}/models/cornerRES.lib"
CAP_LIB = f"{tech}/models/cap_cmomi.lib"

BUNDLES = {
    "fast": ("mos_ff", "res_bcs", -40),
    "typ": ("mos_tt", "res_typ", 27),
    "slow": ("mos_ss", "res_wcs", 125),
}

VOUTS = [round(0.3 + 0.2 * i, 2) for i in range(14)]     # 0.3 .. 2.9 V


def vtag(v):
    return f"{v:.1f}".replace(".", "p")


def process_entry(bundle):
    mos, res, _ = BUNDLES[bundle]
    return {"name": bundle, "sections": [mos, {"lib": RES_LIB, "section": res}]}


def corners_for(bundles):
    temps = sorted({BUNDLES[b][2] for b in bundles})
    exclude = [{"process": b, "temperature_c": t}
               for b in bundles for t in temps if t != BUNDLES[b][2]]
    return ({"process": [process_entry(b) for b in bundles], "temperature_c": temps},
            exclude)


BATCH = {"capacity_wait_s": 900}

base = {
    "engine": "ngspice",
    "models": {"lib": MOS_LIB},
    "options": {
        "osdi_preload": [f"{tech}/osdi/{n}.osdi" for n in
                         ("psp103", "psp103_nqs", "mosvar", "cap_cmomi", "cap_cmomf", "r3_cmc")],
        "stage_model_inputs": True,
        "ngspice_init": ["set numdgt=12", "set num_threads=1"],
        "timeout_s": 900,
    },
}


def emit(name, netlist, analysis, measurements, bundles, backend):
    r = json.loads(json.dumps(base))
    corners, exclude = corners_for(bundles)
    r.update({"netlist": netlist, "analysis": analysis,
              "measurements": measurements, "backend": backend,
              "corners": corners})
    if exclude:
        r["exclude"] = exclude
    if backend == "batch":
        r["batch"] = dict(BATCH)
    (here / name).write_text(json.dumps(r, indent=2) + "\n")


# ---------------------------------------------------------------------------
# 1. cp idle-state VOUT capacitance
# ---------------------------------------------------------------------------
snap = (slug / "netlist-snapshots" / "cp_otabuf.spice").read_text()
import re  # noqa: E402
top = re.search(r"(?ms)^\.subckt cp .*?^\.ends\n", snap).group(0)
base_top = top.replace(".subckt cp ", ".subckt cp_idealdump ", 1)
base_top, n = re.subn(r"(?m)^XBUF VOUT IBN IBP VDUMP VDD VSS cp_dumpbuf$",
                      "EDUMP VDUMP VSS VOUT VSS 1", base_top)
assert n == 1

COUT_KINDS = [("c375", "cp", "3.75u"), ("c10", "cp", "10u"),
              ("c11", "cp", "11u"), ("b10", "cp_idealdump", "10u")]


def cout_body():
    out = [f"""* sg13g2-pll :: sim/sg13cmos5l-loop-bandwidth-pm (issue #196, RECORD-005)
* GENERATED by gen_issue196_ccp_requests.py -- do not edit by hand.
* Circuit body for `klt sim` (AC, 400 kHz / 700 kHz / 1 MHz). Total idle-state (UP =
* DN = 0) capacitance the cp presents on VOUT: each instance is alone on its
* own 0 V ammeter Vm_<inst> from the shared source Vs_<k> (no baseline is
* subtracted), so imag(i(Vm))/omega is the whole cp ("real cp vs no cp").
.include ../netlist-snapshots/cp_otabuf.spice

* buffer-less baseline: the snapshot's cp top-level subckt with XBUF -> EDUMP
{base_top}
Vdd VDD 0 dc 3.3
"""]
    for k, v in enumerate(VOUTS):
        for kind, sub, iref in COUT_KINDS:
            nm = f"{kind}_{k}"
            out.append(f"""X{nm} 0 0 ibp_{nm} icp_{nm} ibn_{nm} icn_{nm} vo_{nm} VDD 0 {sub}
Irbp_{nm} ibp_{nm} 0 dc {iref}
Ircp_{nm} icp_{nm} 0 dc {iref}
Irbn_{nm} 0 ibn_{nm} dc {iref}
Ircn_{nm} 0 icn_{nm} dc {iref}
Vm_{nm} vs_{k} vo_{nm} dc 0
""")
        out.append(f"Vs_{k} vs_{k} 0 dc {v} ac 1\n")
    return "".join(out)


def cout_measurements():
    m = []
    for k, v in enumerate(VOUTS):
        t = vtag(v)
        for kind, _, _ in COUT_KINDS:
            m.append({"name": f"cout_ff_{kind}_{t}", "unit": "fF",
                      "expr": f"imag(i(Vm_{kind}_{k}))[2] / (2 * pi * 1e6) * 1e15"})
        m.append({"name": f"cout400k_ff_c11_{t}", "unit": "fF",
                  "expr": f"imag(i(Vm_c11_{k}))[0] / (2 * pi * 4e5) * 1e15"})
        m.append({"name": f"gout_ns_c11_{t}", "unit": "nS",
                  "expr": f"real(i(Vm_c11_{k}))[2] * 1e9"})
    return m


(here / "tb_cp_cout_issue196.sp").write_text(cout_body())
# lin 3 -> 400 kHz, 700 kHz, 1 MHz (index 0, 1, 2). ngspice-46 `ac lin 2 a b`
# yields ONE point, so two-point form is not used.
COUT_AC = {"kind": "ac", "args": "lin 3 4e5 1e6"}
emit("cout_nominal.request.json", "tb_cp_cout_issue196.sp", COUT_AC,
     cout_measurements(), ["typ"], "local")
emit("cout_bundles.request.json", "tb_cp_cout_issue196.sp", COUT_AC,
     cout_measurements(), ["fast", "slow"], "batch")


# ---------------------------------------------------------------------------
# 2. PM bench with the real idle cp on VCTRL
# ---------------------------------------------------------------------------
def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


r79 = {r["pvt_bundle"]: r for r in
       load(slug / "corners" / "results_resized_issue79_finetrim.csv")}
r83 = {r["pvt_bundle"]: r for r in
       load(slug / "corners" / "results_resized_issue83_finetrim.csv")}

# tuple id -> (bundle, committed row, cp trim code)
TUPLES = {
    "dr008_fast": ("fast", r79["fast"], "11u"),
    "dr008_typ": ("typ", r79["typ"], "11u"),
    "dr008_slow": ("slow", r79["slow"], "11u"),
    "dr007_slow": ("slow", r83["slow"], "3.75u"),
}
for tid, (b, row, code) in TUPLES.items():
    assert row["trim_code"] == code, (tid, row["trim_code"])


def gains(row):
    icp = float(row["icp_a"])
    return (repr(icp / (2 * math.pi)), repr(2 * math.pi * float(row["kvco_hz_per_v"])),
            repr(1.0 / int(row["n_div"])))


def loop(tag, kd, kv, invn, bias=None):
    """One open loop. bias=None: the RECORD-003/004 loop verbatim. bias=(iref,
    v): VCTRL biased to v through Lb (DC only), and the VCO integrator driven
    by v(vc) - v(vb) so the DC bias does not wind it up (AC-identical: vb has
    no AC). iref=None: the bias network alone (control, no cp)."""
    vco_ref = "0" if bias is None else f"vb_{tag}"
    s = f"""* --- loop {tag}
Gcp_{tag} 0 vc_{tag} pe 0 {kd}
XLF_{tag} vc_{tag} 0 loop_filter
Gvco_{tag} 0 vph_{tag} vc_{tag} {vco_ref} {kv}
Cint_{tag} vph_{tag} 0 1
Rleak_{tag} vph_{tag} 0 1e15
Ediv_{tag} fb_{tag} 0 vph_{tag} 0 {invn}
"""
    if bias is not None:
        iref, vbias = bias
        s += f"""Lb_{tag} vc_{tag} vb_{tag} 1e12
Vb_{tag} vb_{tag} 0 dc {vbias}
"""
        if iref is not None:
            s += f"""Xcp_{tag} 0 0 ibp_{tag} icp_{tag} ibn_{tag} icn_{tag} vc_{tag} VDD 0 cp
Irbp_{tag} ibp_{tag} 0 dc {iref}
Ircp_{tag} icp_{tag} 0 dc {iref}
Irbn_{tag} 0 ibn_{tag} dc {iref}
Ircn_{tag} 0 icn_{tag} dc {iref}
"""
    return s


def loop_tags():
    """(tuple id, loop tag, bias) -- bias as loop()'s, minus the trim code."""
    for tid in TUPLES:
        yield tid, f"{tid}_nocp", None
        yield tid, f"{tid}_lonly", ("lonly", 1.5)
        for v in VOUTS:
            yield tid, f"{tid}_v{vtag(v)}", ("cp", v)


def pm_body():
    out = [f"""* sg13g2-pll :: sim/sg13cmos5l-loop-bandwidth-pm (issue #196, RECORD-005)
* GENERATED by gen_issue196_ccp_requests.py -- do not edit by hand.
* Circuit body for `klt sim` (AC, dec 200 10 1e9 as RECORD-001..004).
* Open-loop gain v(fb_<loop>) per 1 rad of phase error on `pe`. Each <t>_nocp
* loop is tb_loop_ac_real_resized.sp.tmpl verbatim (ideal Gcp, no cp); each
* <t>_v<v> loop adds the real idle cp (VOUT pin on vc_<loop>, VCTRL = v).
* Kd/Kv/N per tuple are read from the committed RECORD-003/004 CSVs.
.include {CAP_LIB}
.include ../netlist-snapshots/loop_filter_resized.spice
.include ../netlist-snapshots/cp_otabuf.spice
.option scale=1
.global sub!

Vsub sub! 0 dc 0
Vdd VDD 0 dc 3.3
Vpe pe 0 dc 0 ac 1
"""]
    for tid, tag, bias in loop_tags():
        _, row, code = TUPLES[tid]
        kd, kv, invn = gains(row)
        if bias is not None:
            bias = (code if bias[0] == "cp" else None, bias[1])
        out.append(loop(tag, kd, kv, invn, bias))
    return "".join(out)


def pm_measurements():
    m = []
    for _, tag, _ in loop_tags():
        m += [
            {"name": f"fc_hz_{tag}", "unit": "Hz",
             "spice": f".meas ac fc_hz_{tag} when vdb(fb_{tag})=0"},
            {"name": f"ph_rad_{tag}", "unit": "rad",
             "spice": f".meas ac ph_rad_{tag} find vp(fb_{tag}) when vdb(fb_{tag})=0"},
            {"name": f"pm_deg_{tag}", "unit": "deg",
             "spice": f".meas ac pm_deg_{tag} param='180+ph_rad_{tag}*57.29577951308232'"},
        ]
    return m


(here / "tb_loop_ac_ccp_issue196.sp").write_text(pm_body())
PM_AC = {"kind": "ac", "args": "dec 200 10 1e9"}
emit("pm_ccp_nominal.request.json", "tb_loop_ac_ccp_issue196.sp", PM_AC,
     pm_measurements(), ["typ"], "local")
emit("pm_ccp_bundles.request.json", "tb_loop_ac_ccp_issue196.sp", PM_AC,
     pm_measurements(), ["fast", "slow"], "batch")
