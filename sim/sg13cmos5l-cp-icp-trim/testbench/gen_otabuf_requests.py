#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim/testbench/gen_otabuf_requests.py
(issue #165, Part of #16) -- RECORD-005 of this slug.

Regenerates the `klt sim` circuit body and the three request files that
measure the cp whose dump buffer tracks VOUT (DR-010), frozen as
../netlist-snapshots/cp_otabuf.spice:

    PDK_ROOT=<parent of ihp-sg13cmos5l> python3 gen_otabuf_requests.py

tb_cp_otabuf_dc.sp              circuit body (no .control/.end; klt owns them)
otabuf_nominal.request.json     mos_tt / 27 C / 3.3 V, ONE corner, local
otabuf_pvt.request.json         5 MOS corners x {-40, 27, 125} C at 3.3 V,
                                batch fleet (15 corners) -- never run locally
otabuf_supply.request.json      mos_tt / 27 C x VDD {3.0, 3.6}, batch fleet
tb_cp_otabuf_dc_control.sp      the SAME body, but including the pre-#165
                                snapshot ../netlist-snapshots/cp.spice (NMOS
                                source-follower dump buffer; cp's own pinout
                                is unchanged, so the deck is identical)
otabuf_control_nominal.request.json  that control, mos_tt / 27 C, local.
                                It must FAIL the offset limit (~0.9 V): the
                                negative control that the bound discriminates.

ONE deck answers both questions issue #165 asks of the DC bench, from ONE
DC sweep of a shared output voltage VS (0.30 -> 2.90 V, 50 mV, 53 points,
index k <-> 0.30 + 0.05 k V):

  1. |VDUMP - VOUT| (the dump buffer's tracking error). Six `off`
     instances (UP = DN = 0, both legs dumping -- the idle state every UP
     and DN turn-on starts from, which is what sets the charge-sharing step
     RECORD-006 measured), one per trim code, because the buffer's tails
     mirror the trim-code reference and so its gm scales with the code.
     Plus two one-sided instances at the 10 uA code (`up`: the N leg alone
     dumps Icp into VDUMP, which the buffer must sink; `dn`: the P leg alone
     sources Icp into VDUMP) -- the acquisition load case.
  2. The Icp trim table and up/dn mismatch, exactly as ../testbench/run.sh
     defines them (RECORD-001/002), for the six trim codes, so this record is
     directly comparable with RECORD-002: `up` / `dn` instances give each
     leg's own delivered current, `both` gives the net mismatch current.

Every cp instance has its own four ideal reference currents and its own 0 V
ammeter in series between VS and its VOUT pin (positive = current the cp
delivers INTO the output, the same sign convention as tb_cp_dc.sp.tmpl).

GRADED LIMIT (see ../records/RECORD-005 "Pass bound" and DR-010):
  ofs_off_max_mv_<code>  max |VDUMP - VOUT| over VOUT 0.30-2.70 V (indices
                         0..48, the VCO's characterised VCTRL range, spec
                         row 1), idle state  <= 100 mV.
Everything else is report-only (no limits): the trim table is compared with
RECORD-002 in the record rather than graded against an unratified number.

models.pdk is deliberately omitted, as in ../../sg13cmos5l-cp-icp-trim-mc/:
klt's batch backend refuses `ihp-sg13cmos5l` (2AMLogic/klayout-tools#2727);
options.stage_model_inputs ships the model library and OSDI objects with the
job instead.
"""
import json
import os
import pathlib

pdk_root = os.environ.get("PDK_ROOT", "/home/ubuntu/share/pdk")
tech = f"{pdk_root}/ihp-sg13cmos5l/libs.tech/ngspice"
here = pathlib.Path(__file__).resolve().parent

CODES = [("2p5", "2.5u"), ("5", "5u"), ("10", "10u"), ("20", "20u"), ("40", "40u"), ("80", "80u")]
VS0, VS1, VSTEP = 0.30, 2.90, 0.05
N_PTS = round((VS1 - VS0) / VSTEP) + 1          # 53


def idx(v):
    k = round((v - VS0) / VSTEP)
    assert 0 <= k < N_PTS and abs(VS0 + k * VSTEP - v) < 1e-9, v
    return k


K_165, K_240, K_270, K_090, K_290 = idx(1.65), idx(2.40), idx(2.70), idx(0.90), idx(2.90)
OFS_BOUND_MV = 100.0


def instance(name, upv, dnv, iref, own_supply=False):
    """One cp instance with its own bias, switch levels and output ammeter."""
    vdd = f"vdd_{name}" if own_supply else "VDD"
    lines = [f"* --- {name}: UP={upv} DN={dnv} Iref={iref}"]
    if own_supply:
        lines.append(f"Vmdd_{name} VDD {vdd} dc 0")
    lines += [
        f"X{name} up_{name} dn_{name} ibp_{name} icp_{name} ibn_{name} icn_{name} vo_{name} {vdd} 0 cp",
        f"Irbp_{name} ibp_{name} 0 dc {iref}",
        f"Ircp_{name} icp_{name} 0 dc {iref}",
        f"Irbn_{name} 0 ibn_{name} dc {iref}",
        f"Ircn_{name} 0 icn_{name} dc {iref}",
        f"Bup_{name} up_{name} 0 V={'v(VDD)' if upv else '0'}",
        f"Bdn_{name} dn_{name} 0 V={'v(VDD)' if dnv else '0'}",
        # n+ on the cp side: current leaving the cp's VOUT pin enters n+, so
        # i(Vm_<inst>) > 0 means the cp SOURCES current into the output.
        f"Vm_{name} vo_{name} vs dc 0",
    ]
    return "\n".join(lines)


def body(snapshot="cp_otabuf.spice", what="DR-010 tracking dump buffer"):
    head = f"""* sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim (issue #165, RECORD-005)
* GENERATED by gen_otabuf_requests.py -- do not edit by hand.
* Circuit body for `klt sim` (no .control/.end; klt owns those).
* DUT: ../netlist-snapshots/{snapshot} ({what}),
* 24 instances (6 trim codes x states off/up/dn/both) share
* ONE swept output voltage VS ({VS0:.2f} -> {VS1:.2f} V, {VSTEP * 1e3:.0f} mV, {N_PTS} points);
* each instance has its own 0 V ammeter Vm_<inst> (i > 0 = cp sources INTO
* the output) and its own four ideal trim-code reference currents.
* Switch levels follow VDD through B-sources, so `corners.supply_v` (which
* alters the source named Vdd) moves them with the rail.
.include ../netlist-snapshots/{snapshot}

Vdd VDD 0 dc 3.3
Vs vs 0 dc 1.65
"""
    parts = [head]
    for tag, iref in CODES:
        parts.append(instance(f"off{tag}", 0, 0, iref, own_supply=(tag == "10")))
        parts.append(instance(f"up{tag}", 1, 0, iref))
        parts.append(instance(f"dn{tag}", 0, 1, iref))
        parts.append(instance(f"both{tag}", 1, 1, iref))
    return "\n".join(parts) + "\n"


def measurements():
    m = []
    for tag, _ in CODES:
        m.append({"name": f"ofs_off_max_mv_{tag}", "unit": "mV",
                  "expr": f"vecmax(abs(v(xoff{tag}.vdump)[0,{K_270}] - v(vs)[0,{K_270}])) * 1000",
                  "limits": {"max": OFS_BOUND_MV}})
    for tag, _ in CODES:
        m.append({"name": f"ofs_off_max_mv_to2p9_{tag}", "unit": "mV",
                  "expr": f"vecmax(abs(v(xoff{tag}.vdump) - v(vs))) * 1000"})
    m += [
        {"name": "ofs_off_at2p40_mv_10", "unit": "mV",
         "expr": f"(v(xoff10.vdump)[{K_240}] - v(vs)[{K_240}]) * 1000"},
        {"name": "ofs_off_at1p65_mv_10", "unit": "mV",
         "expr": f"(v(xoff10.vdump)[{K_165}] - v(vs)[{K_165}]) * 1000"},
        {"name": "ofs_up_max_mv_10", "unit": "mV",
         "expr": f"vecmax(abs(v(xup10.vdump)[0,{K_270}] - v(vs)[0,{K_270}])) * 1000"},
        {"name": "ofs_dn_max_mv_10", "unit": "mV",
         "expr": f"vecmax(abs(v(xdn10.vdump)[0,{K_270}] - v(vs)[0,{K_270}])) * 1000"},
        {"name": "ofs_up_at2p40_mv_10", "unit": "mV",
         "expr": f"(v(xup10.vdump)[{K_240}] - v(vs)[{K_240}]) * 1000"},
        {"name": "ofs_dn_at2p40_mv_10", "unit": "mV",
         "expr": f"(v(xdn10.vdump)[{K_240}] - v(vs)[{K_240}]) * 1000"},
        {"name": "idd_off_at2p40_ua_10", "unit": "uA",
         "expr": f"i(Vmdd_off10)[{K_240}] * 1e6"},
    ]
    for tag, _ in CODES:
        up, dn = f"i(Vm_up{tag})", f"i(Vm_dn{tag})"
        m += [
            {"name": f"iup_at1p65_ua_{tag}", "unit": "uA", "expr": f"{up}[{K_165}] * 1e6"},
            {"name": f"idn_at1p65_ua_{tag}", "unit": "uA", "expr": f"{dn}[{K_165}] * 1e6"},
            {"name": f"mm_at1p65_pct_{tag}", "unit": "%",
             "expr": f"({up}[{K_165}] + {dn}[{K_165}]) / (({up}[{K_165}] - {dn}[{K_165}]) / 2) * 100"},
            {"name": f"mm_at2p40_pct_{tag}", "unit": "%",
             "expr": f"({up}[{K_240}] + {dn}[{K_240}]) / (({up}[{K_240}] - {dn}[{K_240}]) / 2) * 100"},
        ]
    up, dn = "i(Vm_up10)", "i(Vm_dn10)"
    m += [
        {"name": "mm_absmax_0p90_2p90_pct_10", "unit": "%",
         "expr": f"vecmax(abs(({up}[{K_090},{K_290}] + {dn}[{K_090},{K_290}]) / "
                 f"(({up}[{K_090},{K_290}] - {dn}[{K_090},{K_290}]) / 2))) * 100"},
        {"name": "inet_both_at2p70_na_10", "unit": "nA",
         "expr": f"i(Vm_both10)[{K_270}] * 1e9"},
    ]
    return m


base = {
    "engine": "ngspice",
    "netlist": "tb_cp_otabuf_dc.sp",
    "models": {"lib": f"{tech}/models/cornerMOShv.lib"},
    "analysis": {"kind": "dc", "args": f"Vs {VS0:.2f} {VS1:.2f} {VSTEP:.2f}"},
    "measurements": measurements(),
    "options": {
        "osdi_preload": [f"{tech}/osdi/{n}.osdi" for n in ("psp103", "psp103_nqs", "mosvar")],
        "stage_model_inputs": True,
        "ngspice_init": ["set numdgt=12", "set num_threads=1"],
        "timeout_s": 900,
    },
}


# Batch requests wait out a Spot capacity refusal for up to 15 min per launch
# (klt sim `batch.capacity_wait_s`); the first submission of this bench was
# refused with `batch_no_capacity` (see ../records/RECORD-005).
BATCH = {"capacity_wait_s": 900}


def emit(name, **over):
    r = json.loads(json.dumps(base))
    r.update(over)
    if r.get("backend") == "batch":
        r["batch"] = dict(BATCH)
    (here / name).write_text(json.dumps(r, indent=2) + "\n")


(here / "tb_cp_otabuf_dc.sp").write_text(body())
(here / "tb_cp_otabuf_dc_control.sp").write_text(
    body("cp.spice", "CONTROL: pre-#165 source-follower dump buffer"))
emit("otabuf_control_nominal.request.json", backend="local", netlist="tb_cp_otabuf_dc_control.sp",
     corners={"process": ["mos_tt"], "temperature_c": [27]})
emit("otabuf_nominal.request.json", backend="local",
     corners={"process": ["mos_tt"], "temperature_c": [27]})
emit("otabuf_pvt.request.json", backend="batch",
     corners={"process": ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"],
              "temperature_c": [-40, 27, 125]})
emit("otabuf_supply.request.json", backend="batch",
     corners={"process": ["mos_tt"], "temperature_c": [27],
              "supply_v": {"Vdd": [3.0, 3.6]}})

# ---------------------------------------------------------------------------
# Loop-filter-node loading (DR-010 / DR-001's adopted gf180-pll DR-005
# condition 2: added control-node capacitance <= 1% of the smallest C1).
# For each VOUT point, a PAIR of idle (UP = DN = 0) 10 uA cp instances is
# driven by one AC source: the real cp, and a baseline copy whose XBUF is
# replaced by an ideal unity VCVS (EDUMP, as RECORD-006's `ideal_dump`
# variant), which draws nothing from VOUT. The difference in imaginary
# admittance at 1 MHz (inside the loop's crossover decade) is the capacitance
# the dump buffer itself adds to the loop-filter node.
#   cin_ff_<v>  limit <= 16.9 fF = 1% of C1 = 1.691196 pF (the loop_filter
#               C1 value the closed-loop decks use).
# ---------------------------------------------------------------------------
CIN_VOUTS = [round(0.3 + 0.2 * i, 2) for i in range(14)]     # 0.3 .. 2.9 V
C1_F = 1.691196e-12
CIN_BOUND_FF = round(0.01 * C1_F * 1e15, 1)                    # 16.9 fF


def cin_body():
    snap = (here / ".." / "netlist-snapshots" / "cp_otabuf.spice").read_text()
    import re
    top = re.search(r"(?ms)^\.subckt cp .*?^\.ends\n", snap).group(0)
    base_top = top.replace(".subckt cp ", ".subckt cp_idealdump ", 1)
    base_top, n = re.subn(r"(?m)^XBUF VOUT IBN IBP VDUMP VDD VSS cp_dumpbuf$",
                          "EDUMP VDUMP VSS VOUT VSS 1", base_top)
    assert n == 1
    out = [f"""* sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim (issue #165, RECORD-005)
* GENERATED by gen_otabuf_requests.py -- do not edit by hand.
* Circuit body for `klt sim` (AC). Buffer input capacitance on VOUT: for each
* VOUT point a real cp (Xr_<k>) and a baseline cp_idealdump (Xb_<k>, XBUF ->
* ideal unity VCVS, derived below from the frozen snapshot's own cp subckt)
* share one AC source Vs_<k>; each has its own 0 V ammeter. Idle state
* (UP = DN = 0), 10 uA trim code.
.include ../netlist-snapshots/cp_otabuf.spice

* baseline: the snapshot's cp top-level subckt with XBUF -> EDUMP
{base_top}
Vdd VDD 0 dc 3.3
"""]
    for k, v in enumerate(CIN_VOUTS):
        for kind, sub in (("r", "cp"), ("b", "cp_idealdump")):
            nm = f"{kind}{k}"
            out.append(f"""X{nm} 0 0 ibp_{nm} icp_{nm} ibn_{nm} icn_{nm} vo_{nm} VDD 0 {sub}
Irbp_{nm} ibp_{nm} 0 dc 10u
Ircp_{nm} icp_{nm} 0 dc 10u
Irbn_{nm} 0 ibn_{nm} dc 10u
Ircn_{nm} 0 icn_{nm} dc 10u
Vm_{nm} vs_{k} vo_{nm} dc 0
""")
        out.append(f"Vs_{k} vs_{k} 0 dc {v} ac 1\n")
    return "".join(out)


def cin_measurements():
    m = []
    for k, v in enumerate(CIN_VOUTS):
        tag = f"{v:.1f}".replace(".", "p")
        m.append({"name": f"cin_ff_{tag}", "unit": "fF",
                  "expr": f"(imag(i(Vm_r{k})) - imag(i(Vm_b{k}))) / (2 * pi * 1e6) * 1e15",
                  "limits": {"max": CIN_BOUND_FF}})
    return m


def emit_cin(name, **over):
    r = json.loads(json.dumps(base))
    r.update({"netlist": "tb_cp_otabuf_cin.sp",
              "analysis": {"kind": "ac", "args": "lin 1 1e6 1e6"},
              "measurements": cin_measurements()})
    r.update(over)
    if r.get("backend") == "batch":
        r["batch"] = dict(BATCH)
    (here / name).write_text(json.dumps(r, indent=2) + "\n")


(here / "tb_cp_otabuf_cin.sp").write_text(cin_body())
emit_cin("otabuf_cin_nominal.request.json", backend="local",
         corners={"process": ["mos_tt"], "temperature_c": [27]})
emit_cin("otabuf_cin_pvt.request.json", backend="batch",
         corners={"process": ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"],
                  "temperature_c": [-40, 27, 125]})

# ---------------------------------------------------------------------------
# Buffer stability (DR-010 / adopted gf180-pll DR-005 condition 4: no nested
# stability problem). Loop gain of the unity-gain feedback, measured IN SITU
# (the real cp legs and switches load VDUMP): a copy of the snapshot's
# cp_dumpbuf whose MN2/MP2 gates (the feedback inputs) are moved to node FB,
# closed at DC through a 1 GH inductor and driven at AC through a 1 F cap from
# INJ. With v(FB) = 1, T(jw) = -v(VDUMP); DC phase of v(VDUMP) is +180 deg,
# so the phase margin is vp(VDUMP) at |T| = 1. The loop is broken at a gate,
# so the MN2/MP2 gate load is absent from VDUMP (a small optimistic error).
# Idle (UP = DN = 0), 10 uA code, five VOUT points.
#   pm_rad_<v>  limit >= 0.785398 rad (45 deg)
# ---------------------------------------------------------------------------
LG_VOUTS = [0.5, 1.0, 1.65, 2.4, 2.7]


def lg_body():
    import re
    snap = (here / ".." / "netlist-snapshots" / "cp_otabuf.spice").read_text()
    buf = re.search(r"(?ms)^\.subckt cp_dumpbuf .*?^\.ends\n", snap).group(0)
    lb = buf.replace(".subckt cp_dumpbuf VOUT IBN IBP VDUMP VDD VSS",
                     ".subckt cp_dumpbuf_lb VOUT IBN IBP VDUMP VDD VSS INJ", 1)
    for dev in ("XMN2 VDUMP VDUMP NSRC", "XMP2 VDUMP VDUMP PSRC"):
        assert dev in lb, dev
        lb = lb.replace(dev, dev.replace("VDUMP VDUMP", "VDUMP FB"))
    lb = lb.replace(".ends", "Lbrk VDUMP FB 1G\nCinj FB INJ 1\n.ends")
    top = re.search(r"(?ms)^\.subckt cp .*?^\.ends\n", snap).group(0)
    toplb = top.replace(".subckt cp UP DN IBP ICP IBN ICN VOUT VDD VSS",
                        ".subckt cp_lb UP DN IBP ICP IBN ICN VOUT VDD VSS INJ", 1)
    toplb, n = re.subn(r"(?m)^XBUF VOUT IBN IBP VDUMP VDD VSS cp_dumpbuf$",
                       "XBUF VOUT IBN IBP VDUMP VDD VSS INJ cp_dumpbuf_lb", toplb)
    assert n == 1
    out = [f"""* sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim (issue #165, RECORD-005)
* GENERATED by gen_otabuf_requests.py -- do not edit by hand.
* Circuit body for `klt sim` (AC): cp_dumpbuf unity-feedback loop gain, loop
* broken at the MN2/MP2 gates (see the generator for the method).
.include ../netlist-snapshots/cp_otabuf.spice

{lb}
{toplb}
Vdd VDD 0 dc 3.3
"""]
    for k, v in enumerate(LG_VOUTS):
        out.append(f"""X{k} 0 0 ibp{k} icp{k} ibn{k} icn{k} vo{k} VDD 0 inj{k} cp_lb
Irbp{k} ibp{k} 0 dc 10u
Ircp{k} icp{k} 0 dc 10u
Irbn{k} 0 ibn{k} dc 10u
Ircn{k} 0 icn{k} dc 10u
Vo{k} vo{k} 0 dc {v}
Vinj{k} inj{k} 0 dc 0 ac 1
""")
    return "".join(out)


def lg_measurements():
    m = []
    for k, v in enumerate(LG_VOUTS):
        tag = f"{v:.2f}".rstrip("0").rstrip(".").replace(".", "p")
        m += [
            {"name": f"a0_db_{tag}", "unit": "dB",
             "spice": f".meas ac a0_db_{tag} find vdb(x{k}.vdump) at=1e3"},
            {"name": f"ugf_hz_{tag}", "unit": "Hz",
             "spice": f".meas ac ugf_hz_{tag} when vdb(x{k}.vdump)=0"},
            {"name": f"pm_rad_{tag}", "unit": "rad",
             "spice": f".meas ac pm_rad_{tag} find vp(x{k}.vdump) when vdb(x{k}.vdump)=0",
             "limits": {"min": 0.785398}},
        ]
    return m


def emit_lg(name, **over):
    r = json.loads(json.dumps(base))
    r.update({"netlist": "tb_cp_otabuf_loopgain.sp",
              "analysis": {"kind": "ac", "args": "dec 20 1e3 1e11"},
              "measurements": lg_measurements()})
    r.update(over)
    if r.get("backend") == "batch":
        r["batch"] = dict(BATCH)
    (here / name).write_text(json.dumps(r, indent=2) + "\n")


(here / "tb_cp_otabuf_loopgain.sp").write_text(lg_body())
emit_lg("otabuf_lg_nominal.request.json", backend="local",
        corners={"process": ["mos_tt"], "temperature_c": [27]})
emit_lg("otabuf_lg_pvt.request.json", backend="batch",
        corners={"process": ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"],
                 "temperature_c": [-40, 27, 125]})
