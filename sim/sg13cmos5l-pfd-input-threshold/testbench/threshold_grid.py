#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-pfd-input-threshold (issue #403, spec row 2 / R-5)

Reference-input electrical levels for the committed SG13CMOS5L `pfd`
(../netlist-snapshots/pfd.spice, byte-identical to
design/sg13cmos5l/netlist/pfd.spice), expressed as `klt sim` deck-list
requests for the batch fleet (dispatch hosts forbid hand-launched ngspice
grids).  It never calls ngspice.

Two deck families (templates in this directory; the DUT snapshot is copied
verbatim into each request as decks/pfd_snap.spice):

  dc    tb_pfd_dc.sp.tmpl    one .dc sweep of REF 0 -> VDD per corner;
                             static trip points on the named internal
                             nodes d1 / xd5 / ntmp of the REF edgedet.
  edge  tb_pfd_edge.sp.tmpl  the REF low level ("il" decks, ascending) or
                             high level ("ih" decks, descending) stepped
                             through a 32-segment ladder, 16 identical
                             cycles per segment; registration counted on
                             edgedet's OUT (`set_up`) rising crossings,
                             whose times (t_rise_<n>) locate the boundary
                             between the last fully-registering segment and
                             the first failing one.  Segment 1 is the
                             full-swing control in both directions.  FB is
                             a full-rail copy at a fixed 5 ns offset (as
                             sg13g2-pfd-reset-parity): reset needs UP and DN
                             both high, so a static FB would latch UP on the
                             first edge and make every later count read
                             1-of-N regardless of level.

Subcommands:

  gen    WORKDIR [--probe]    write WORKDIR/pfdthr/{request.json,units.json,decks/}
                              (--probe: nominal corner only, 3 units, into
                              WORKDIR/pfdthr-probe/, for the bring-up job)
  reduce WORKDIR CORNERS_DIR  read WORKDIR/pfdthr/out/*/stdout.bin, recompute
                              the ladder geometry from the same constants,
                              write CORNERS_DIR/results.csv and print the
                              sanity summary (segment-1 control, ladder
                              contiguity, DC-bracket check, binding corners).

Grid (the operating box of spec/target-spec.md row 2): 3 correlated PVT
bundles x 3 supplies = 9 corners, x 2 frequencies x 2 duties = 4 stimulus
points -> 9 DC decks + 72 edge decks.  The bundles are process+temperature
PAIRS (spec/target-spec.md: fast = mos_ff/-40 C, typ = mos_tt/27 C,
slow = mos_ss/125 C), not a 27-point cross product.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent
SIM = RECORD.parent
SNAP = RECORD / "netlist-snapshots" / "pfd.spice"
PDK = "ihp-sg13cmos5l"
OSDI = ("psp103", "psp103_nqs")

BUNDLES = [("typ", "mos_tt", "res_typ", 27),
           ("slow", "mos_ss", "res_wcs", 125),
           ("fast", "mos_ff", "res_bcs", -40)]
VDDS = ["3.0", "3.3", "3.6"]
FREQS = [("3p5", 3.5e6), ("24p4", 24.4e6)]
DUTIES = [30, 70]                       # percent of period held high

N_SEG = 32                              # ladder steps
N_CYC = 16                              # REF cycles per segment
FBTD = 5e-9                             # FB offset, as sg13g2-pfd-reset-parity
TR = TF = 100e-12                       # REF edge transition times
IL_TOP = 0.90                           # il ladder: low level climbs to 0.90*VDD
IH_BOT = 0.10                           # ih ladder: high level descends to 0.10*VDD
TIMING = {"3p5": (500e-12, 500e-12),     # (TSTEP, TMAX) per frequency tag; the
          "24p4": (250e-12, 250e-12)}    # ~300 ps set_up pulses are resolved by
                                         # LTE refinement at the PWL breakpoints,
                                         # not by TMAX: t_rise_1/t_rise_16 are
                                         # byte-identical at TMAX 100p vs 500p


def tag(*a):
    return "_".join(str(x) for x in a).replace(".", "p").replace("-", "m")


def sub(text, **kw):
    for k, v in kw.items():
        text = text.replace("@%s@" % k, str(v))
    left = [l for l in text.splitlines() if not l.startswith("*") and re.search(r"@[A-Z_0-9]+@", l)]
    if left:
        raise SystemExit("threshold_grid: unsubstituted placeholders: %s" % left)
    return text


def with_init(text):
    """Insert pre_osdi + num_threads=1 into the deck (a deck-list unit has no
    .spiceinit).  Reuses the template's own .control block."""
    pre = "\n".join("pre_osdi $PDK_ROOT/%s/libs.tech/ngspice/osdi/%s.osdi" % (PDK, o)
                    for o in OSDI) + "\nset num_threads=1\n"
    if ".control\n" not in text:
        raise SystemExit("threshold_grid: template has no .control block")
    return text.replace(".control\n", ".control\n" + pre, 1)


def ladder(direction, vdd):
    """Per-segment (low, high) REF levels; segment 1 is full swing both ways."""
    v = float(vdd)
    out = []
    for k in range(N_SEG):
        f = k / (N_SEG - 1)
        if direction == "il":
            out.append((f * IL_TOP * v, v))
        else:
            out.append((0.0, v - f * (1.0 - IH_BOT) * v))
    return out


def ref_pwl(direction, vdd, tper, duty):
    """PWL text for the whole ladder.  High time at mid-rail is exactly
    duty*T (the ramps straddle the crossings symmetrically), so segment
    geometry in reduce matches the deck bit for bit."""
    pw = duty / 100.0 * tper - (TR + TF) / 2.0
    pts = []
    for k, (lo, hi) in enumerate(ladder(direction, vdd)):
        t0 = k * N_CYC * tper
        for j in range(N_CYC):
            tr_ = t0 + j * tper
            tf_ = tr_ + TR + pw
            pts += [(tr_, lo), (tr_ + TR, hi), (tf_, hi), (tf_ + TF, lo)]
    return " ".join("%.10e %.6f" % (t, x) for t, x in pts)


def meas_block(vmid):
    """meas + print lines: the set_up rising crossings at the LAST edge of
    every segment (cumulative indices 1, N_CYC, 2*N_CYC, ...) plus the first
    edge overall."""
    names = ["t_rise_1"] + ["t_rise_%d" % (k * N_CYC) for k in range(1, N_SEG + 1)]
    lines = ["meas tran %s when v(xpfd.set_up)=%.6f rise=%d" % (n, vmid, 1 if n == "t_rise_1" else int(n.split("_")[2]))
             for n in names]
    for i in range(0, len(names), 8):
        lines.append("print " + " ".join(names[i:i + 8]))
    return "\n".join(lines)


def edge_text(direction, bundle, vdd, freqtag, fref, duty):
    mos, res, temp = bundle[1], bundle[2], bundle[3]
    tper = 1.0 / fref
    tstep, tmax = TIMING[freqtag]
    tstop = N_SEG * N_CYC * tper + 0.5 * tper
    vmid = float(vdd) / 2.0
    pwf = 0.5 * tper - (TR + TF) / 2.0
    if direction == "il":
        axis, ladder_desc = "low", "low level ascending 0 -> %.2f*VDD, high fixed at VDD" % IL_TOP
    else:
        axis, ladder_desc = "high", "high level descending VDD -> %.2f*VDD, low fixed at 0" % IH_BOT
    t = (HERE / "tb_pfd_edge.sp.tmpl").read_text()
    t = sub(t, PDK=PDK, CORNER_MOS=mos, TEMP=temp, VDD=vdd, VMID="%.6f" % vmid,
            DIR=direction.upper(), AXIS=axis, NSEG=N_SEG, LADDER=ladder_desc,
            FBTD_s="%.1e" % FBTD, FBTD="%.3e" % FBTD, TR="%.3e" % TR, TF="%.3e" % TF,
            PWF="%.6e" % pwf, TPER="%.10e" % tper,
            PWL=ref_pwl(direction, vdd, tper, duty),
            TSTEP="%.3e" % tstep, TSTOP="%.10e" % tstop, TMAX="%.3e" % tmax,
            MEASBLOCK=meas_block(vmid))
    return with_init(t)


def dc_text(bundle, vdd):
    mos, res, temp = bundle[1], bundle[2], bundle[3]
    t = (HERE / "tb_pfd_dc.sp.tmpl").read_text()
    t = sub(t, PDK=PDK, CORNER_MOS=mos, TEMP=temp, VDD=vdd,
            VMID="%.6f" % (float(vdd) / 2.0), DSTEP="%.6f" % (float(vdd) / 2048.0))
    return with_init(t)


def points(probe):
    return [(BUNDLES[0], "3.3")] if probe else [(b, v) for b in BUNDLES for v in VDDS]


def write_request(d, units, files, name="request.json"):
    """files: (source path, staged name) pairs -- the staged name must match
    the .include the decks carry."""
    (d / "decks").mkdir(parents=True, exist_ok=True)
    for uid, text in units:
        (d / "decks" / (uid + ".sp")).write_text(text)
    for src, name_ in files:
        (d / "decks" / name_).write_text(pathlib.Path(src).read_text())
    decks = []
    for uid, _ in units:
        timeout = 900 if uid.startswith("dc_") else (3600 if "_3p5_" in uid else 1800)
        decks.append({"id": uid, "deck": "decks/%s.sp" % uid, "timeout_s": timeout})
    req = {"engine": "ngspice", "backend": "batch", "models": {"pdk": PDK},
           "decks": decks,
           "options": {"timeout_s": 14400, "max_workers": 2},
           "batch": {"capacity_wait_s": 600}}
    (d / name).write_text(json.dumps(req, indent=2) + "\n")
    (d / name.replace("request", "units", 1)).write_text(
        json.dumps([u for u, _ in units], indent=2) + "\n")
    print("wrote %s (%d decks)" % (d / name, len(units)))


def gen(work, probe):
    d = work / ("pfdthr-probe" if probe else "pfdthr")
    units = []
    if probe:
        b, vdd = points(probe)[0]
        units.append(("dc_%s_%s" % (b[0], tag(vdd)), dc_text(b, vdd)))
        for direction in ("il", "ih"):
            units.append(("%s_%s_%s_3p5_d30" % (direction, b[0], tag(vdd)),
                          edge_text(direction, b, vdd, "3p5", 3.5e6, 30)))
    else:
        for b, vdd in points(False):
            units.append(("dc_%s_%s" % (b[0], tag(vdd)), dc_text(b, vdd)))
            for freqtag, fref in FREQS:
                for duty in DUTIES:
                    for direction in ("il", "ih"):
                        units.append(("%s_%s_%s_%s_d%d" % (direction, b[0], tag(vdd), freqtag, duty),
                                      edge_text(direction, b, vdd, freqtag, fref, duty)))
    d.mkdir(parents=True, exist_ok=True)
    files = [(SNAP, "pfd_snap.spice")]
    write_request(d, units, files, "request.json")
    if probe:
        return
    # Sharded submissions (run_batch.sh): one request file per shard, all
    # sharing this request dir's decks/.  Units are grouped per PVT corner
    # (1 DC + 8 edge decks) so each shard stays well inside the ~1 h
    # spot-reclamation window; 9 corners -> shards of 2/2/2/1/1/1 corners.
    by_corner = {}
    for uid, text in units:
        by_corner.setdefault("_".join(uid.split("_")[1:3]), []).append((uid, text))
    corners = list(by_corner)
    ci = 0
    for si, size in enumerate([2, 2, 2, 1, 1, 1]):
        chunk = []
        for _ in range(size):
            if ci < len(corners):
                chunk += by_corner[corners[ci]]
                ci += 1
        write_request(d, chunk, files, "request.shard%d.json" % si)


# ------------------------------------------------------------------ reduce
def val(text, k):
    m = re.search(r"^%s\s*=\s*(\S+)" % re.escape(k), text, re.M)
    if not m:
        return None
    try:
        float(m.group(1))
        return m.group(1)
    except ValueError:
        return None


def out_of(work, uid):
    p = work / "pfdthr" / "out" / uid / "stdout.bin"
    return p.read_text(errors="replace") if p.exists() else ""


def seg_of(tmeas, t_exp, tper):
    """True if measured crossing time matches the expected segment-last edge."""
    return t_exp - 0.05 * tper <= tmeas <= t_exp + 0.25 * tper


def reduce_all(work, corners):
    corners.mkdir(parents=True, exist_ok=True)
    hdr = ["kind", "bundle", "mos_corner", "res_corner", "temp_c", "vdd_v",
           "freq_mhz", "duty_pct", "seg_pass", "v_pass_v", "v_fail_v",
           "t_rise_1_s", "t_rise_last_s", "flag",
           "vth_d1_v", "vth_xd5_v", "vth_ntmp_v", "ntmp_min_v"]
    rows = []
    bad_seg1, nonmono = [], []
    for b, vdd in points(False):
        bn, mos, res, temp = b
        txt = out_of(work, "dc_%s_%s" % (bn, tag(vdd)))
        rows.append(["dc", bn, mos, res, temp, vdd, "", "", "", "", "", "", "", "",
                     val(txt, "vth_d1") or "NA", val(txt, "vth_xd5") or "NA",
                     val(txt, "vth_ntmp") or "NA", val(txt, "ntmp_min") or "NA"])
        v = float(vdd)
        vmid = v / 2.0
        for freqtag, fref in FREQS:
            tper = 1.0 / fref
            for duty in DUTIES:
                for direction in ("il", "ih"):
                    uid = "%s_%s_%s_%s_d%d" % (direction, bn, tag(vdd), freqtag, duty)
                    txt = out_of(work, uid)
                    lad = ladder(direction, vdd)
                    meas = {}
                    for k in range(1, N_SEG + 1):
                        meas[k] = val(txt, "t_rise_%d" % (k * N_CYC))
                    t1 = val(txt, "t_rise_1")
                    t1_exp = TR / 2.0
                    if t1 is None or not seg_of(float(t1), t1_exp, tper):
                        bad_seg1.append(uid)
                    passed = 0
                    hit = []
                    for k in range(1, N_SEG + 1):
                        if meas[k] is None:
                            continue
                        t_exp = (k - 1) * N_CYC * tper + (N_CYC - 1) * tper + TR / 2.0
                        if seg_of(float(meas[k]), t_exp, tper):
                            hit.append(k)
                    for k in sorted(hit):        # contiguous run from segment 1
                        if k == passed + 1:
                            passed = k
                        else:
                            break
                    if sorted(hit) != list(range(1, passed + 1)) or \
                       any(k in hit for k in range(passed + 1, N_SEG + 1)):
                        nonmono.append(uid)
                    flag = ""
                    if uid in bad_seg1:
                        flag = "seg1"
                    if uid in nonmono:
                        flag = (flag + "," if flag else "") + "nonmonotone"
                    v_pass = v_fail = t_last = None
                    if passed:
                        idx = passed - 1
                        v_pass = lad[idx][0] if direction == "il" else lad[idx][1]
                        if passed < N_SEG:
                            v_fail = lad[passed][0] if direction == "il" else lad[passed][1]
                        t_last = meas[passed]
                    elif "seg1" not in flag:
                        flag = (flag + "," if flag else "") + "nofail-found"
                    rows.append([direction, bn, mos, res, temp, vdd,
                                 "%.6g" % (fref / 1e6), duty, passed or "NA",
                                 "%.6f" % v_pass if v_pass is not None else "NA",
                                 "%.6f" % v_fail if v_fail is not None else "NA",
                                 t1 or "NA", t_last or "NA", flag,
                                 "", "", "", ""])
    out = corners / "results.csv"
    lines = [",".join(hdr)]
    lines += [",".join(str(x) for x in r) for r in rows]
    out.write_text("\n".join(lines) + "\n")
    print("wrote %s (%d rows)" % (out, len(rows)))
    # sanity summary ------------------------------------------------------
    n_edge = 2 * len(FREQS) * len(DUTIES) * len(points(False))       # 72 decks
    print("SANITY seg1 control (full-swing segment 1 must register first edge): "
          "%d/%d decks OK" % (n_edge - len(bad_seg1), n_edge))
    if bad_seg1:
        print("  seg1 FAILURES: %s" % ", ".join(bad_seg1))
    print("SANITY ladder contiguity/monotonicity: %d nonmonotone rows" % len(nonmono))
    if nonmono:
        print("  NONMONOTONE: %s" % ", ".join(nonmono))
    # binding corners + DC bracket check
    edge = [r for r in rows if r[0] in ("il", "ih")]
    il = [r for r in edge if r[0] == "il" and r[9] != "NA"]
    ih = [r for r in edge if r[0] == "ih" and r[9] != "NA"]
    if il:
        w = min(il, key=lambda r: float(r[9]))
        print("BINDING V_IL (lowest still-registering low level): %s V at %s/%s V/%s MHz/d%d"
              % (w[9], w[1], w[5], w[6], w[7]))
    if ih:
        w = max(ih, key=lambda r: float(r[9]))
        print("BINDING V_IH (highest still-registering high level): %s V at %s/%s V/%s MHz/d%d"
              % (w[9], w[1], w[5], w[6], w[7]))
    dcmap = {(r[1], r[5]): r for r in rows if r[0] == "dc"}
    # DC trip vs dynamic boundary.  Expected physics (see RECORD-001): the il
    # boundary brackets the DC trip, while the ih boundary sits ABOVE it --
    # near-trip high levels make the XN1 series pulldown cut early (xd5 only
    # reaches ~0.2 V), so the set_up pulse amplitude degrades below mid-rail
    # before the DC trip itself is crossed.  Reported as information, not a
    # pass/fail check.
    offs = []
    for r in ih:
        dc = dcmap.get((r[1], r[5]))
        if dc and r[9] != "NA" and dc[14] != "NA":
            offs.append(float(r[9]) - float(dc[14]))
    if offs:
        print("INFO ih boundary vs DC trip (vth_d1): offset +%.3f to +%.3f V "
              "(positive = pulse-amplitude degradation pushes V_IH above V_M)"
              % (min(offs), max(offs)))
    ok = 0
    for r in il:
        dc = dcmap.get((r[1], r[5]))
        if dc and r[9] != "NA" and r[10] != "NA" and dc[14] != "NA":
            if float(r[9]) <= float(dc[14]) <= float(r[10]):
                ok += 1
    print("INFO il boundary brackets the DC trip at %d/%d stimulus points" % (ok, len(il)))


def main(argv):
    if len(argv) < 3 or argv[1] not in ("gen", "reduce"):
        raise SystemExit(__doc__)
    work = pathlib.Path(argv[2])
    if argv[1] == "gen":
        gen(work, "--probe" in argv)
    else:
        reduce_all(work, pathlib.Path(argv[3]))


if __name__ == "__main__":
    main(sys.argv)
