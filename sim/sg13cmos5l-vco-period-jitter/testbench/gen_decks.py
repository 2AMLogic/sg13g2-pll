#!/usr/bin/env python3
"""Render the sg13cmos5l-vco-period-jitter units (#518) as `klt sim` deck-list
requests.

    python3 -I gen_decks.py --phase bias  OUTDIR
    python3 -I gen_decks.py --phase cal   OUTDIR --vbp V --vbn W
    python3 -I gen_decks.py --phase main  OUTDIR --vbp V --vbn W --sigma S
    python3 -I gen_decks.py --phase seedgap OUTDIR --vbp V --vbn W --sigma S

Each phase writes OUTDIR/decks/*.sp (+ decks/vco_open.spice, the
XCDECAP-stripped derivation of the frozen ../netlist-snapshots/vco.spice,
identical to the duty-cycle bench's), OUTDIR/request.json and
OUTDIR/decks_meta.json (every unit's exact deck parameters -- extract.py
reads that file, so the committed CSVs quote the deck strings, never a
re-derivation).

Phases:
  bias     1 unit: vco_bias .op at the bench operating point -> VBP/VBN.
  cal      3 units: single-vco_stage calibration -- .op+.noise, 1A .ac
           (|Z_out|), and the DC transfer around the self-bias point.
  main    11 units: 2 calibration transients (PSD validation, seeds 42/43)
           + 9 free-running-ring units: the primary seed-42 run, its
           bit-identical rerun, seeds 43/44, noise-off (sigma=0), the
           halved-.tran-step pair, and the 2x/0.5x amplitude pair.
  seedgap  1 unit: the primary seed-42 ring deck rebuilt in fleet form
           ($PDK_ROOT-relative .lib/pre_osdi paths, per the duty-cycle
           bench's fleet rerun) -- submitted to the batch backend to
           demonstrate, with a real job id, that the pinned klt report
           carries no transient-noise seed (the 2AMLogic/klayout-tools#5772
           gap this issue parks on).

Single corner throughout (mos_tt/res_typ/27C, band 00, VCTRL=1.5V, 3.3V):
this bench is the method validation the issue's step 6 sanctions to run
locally; the PVT campaign is deliberately NOT generated here.
"""
import argparse, hashlib, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
SNAP = HERE.parent / "netlist-snapshots" / "vco.spice"

CORNER_MOS, CORNER_RES, TEMP = "mos_tt", "res_typ", 27
VCTRL, B0V, B1V = "1.5", "0.0", "0.0"
TS = "1e-11"            # trrandom sample interval: 10 ps (a source parameter)
TSTOP = "1.75u"         # >= 75 ns startup + 1000 settled periods + margin
CAL_TRAN_TSTEP = "5p"   # uniform PSD grid for the calibration transient
FIRST, LAST = 51, 1051  # measured rising crossings (1000 periods)
SEED_PRIMARY = 42

# .tran step for the ring units (the max-step axis of the timestep control)
RING_TSTEP = {"t10p": "10p", "t5p": "5p"}


def strip_decap(text):
    return re.sub(r"^(XCDECAP)", r"*\1", text, flags=re.M)


def subst(tmpl, **vals):
    s = tmpl
    for k, v in vals.items():
        s = s.replace("@" + k + "@", v)
    if "@" in s.replace("@PDK_ROOT@/@PDK@", ""):
        left = re.findall(r"@\w+@", s)
        unknown = [t for t in left if t not in ("@PDK_ROOT@", "@PDK@")]
        if unknown:
            sys.exit(f"gen_decks.py: unsubstituted placeholders {unknown}")
    return s


def meas_lines():
    return "\n".join(
        f"meas tran tc{k} when v(clk)=1.65 rise={k}" for k in range(FIRST, LAST + 1))


def fmt2x(s):
    return f"{float(s) * 2:.5e}"


def fmt05x(s):
    return f"{float(s) * 0.5:.5e}"


def write_decks(out, decks, meta):
    (out / "decks").mkdir(parents=True, exist_ok=True)
    (out / "decks" / "vco_open.spice").write_text(strip_decap(SNAP.read_text()))
    rows = []
    req_decks = []
    for d in decks:
        p = out / "decks" / f"{d['id']}.sp"
        p.write_text(d["text"])
        rows.append((d["id"], hashlib.sha256(d["text"].encode()).hexdigest()))
        req_decks.append({"id": d["id"], "deck": f"decks/{d['id']}.sp",
                          "timeout_s": d["timeout_s"]})
    req = {"engine": "ngspice", "models": {"pdk": "ihp-sg13cmos5l"},
           "decks": req_decks, "options": {"timeout_s": max(d["timeout_s"] for d in decks)}}
    if meta["phase"] == "seedgap":
        req["backend"] = "batch"
        req["batch"] = {"capacity_wait_s": 600}
    (out / "request.json").write_text(json.dumps(req, indent=2) + "\n")
    (out / "decks_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    with open(out / "decks.sha256.csv", "w") as f:
        f.write("id,deck_sha256\n")
        for i, h in rows:
            f.write(f"{i},{h}\n")
    print(f"wrote {len(decks)} decks + request.json to {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["bias", "cal", "main", "seedgap"])
    ap.add_argument("--vbp"), ap.add_argument("--vbn"), ap.add_argument("--sigma")
    ap.add_argument("out", type=pathlib.Path)
    a = ap.parse_args()
    out = a.out.resolve()
    if a.phase in ("cal", "main", "seedgap") and not (a.vbp and a.vbn):
        sys.exit(f"--vbp/--vbn required for phase {a.phase}")
    if a.phase in ("main", "seedgap") and not a.sigma:
        sys.exit(f"--sigma required for phase {a.phase}")

    shared = {"CORNER_MOS": CORNER_MOS, "CORNER_RES": CORNER_RES,
              "TEMP": str(TEMP), "PDK_ROOT": "$PDK_ROOT", "PDK": "ihp-sg13cmos5l",
              "OSDI": "$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi"}

    decks, meta = [], {"phase": a.phase, "corner": {"mos": CORNER_MOS, "res": CORNER_RES,
                      "temp_c": TEMP}, "op_point": {"vctrl_v": VCTRL, "b0_v": B0V,
                      "b1_v": B1V, "vdd_v": "3.3"}, "ts_s": TS, "tstop_s": TSTOP,
                      "crossings": [FIRST, LAST], "cal_band_hz": [1e8, 1e10], "units": {}}

    if a.phase == "bias":
        t = subst((HERE / "tb_bias_op.sp.tmpl").read_text(), VCTRL=VCTRL, B0V=B0V,
                  B1V=B1V, **shared)
        decks.append({"id": "bias_op", "text": t, "timeout_s": 300})
        meta["units"]["bias_op"] = {"template": "tb_bias_op.sp.tmpl"}

    elif a.phase == "cal":
        for tid, tmpl, extra, to in (
                ("cal_noise", "tb_cal_noise.sp.tmpl", {}, 600),
                ("cal_ac", "tb_cal_ac.sp.tmpl", {}, 600),
                ("cal_dcsweep", "tb_cal_dcsweep.sp.tmpl",
                 {"VTRIP": "1.361047", "VLO": "1.1", "VHI": "1.6", "VSTEP": "0.005"}, 600)):
            t = subst((HERE / tmpl).read_text(), VBP=a.vbp, VBN=a.vbn, **extra, **shared)
            decks.append({"id": tid, "text": t, "timeout_s": to})
            meta["units"][tid] = {"template": tmpl, "vbp_v": a.vbp, "vbn_v": a.vbn, **extra}

    else:  # main / seedgap
        sig2, sig05 = fmt2x(a.sigma), fmt05x(a.sigma)
        base = {"VBP": a.vbp, "VBN": a.vbn, "VCTRL": VCTRL, "B0V": B0V, "B1V": B1V,
                "TS": TS, "TSTOP": TSTOP, "MEAS_LINES": meas_lines(), **shared}
        ring = lambda seed, sigma, tstep: subst(
            (HERE / "tb_ring_jitter.sp.tmpl").read_text(), SEED=str(seed),
            SIGMA=sigma, TSTEP=tstep, **base)

        if a.phase == "main":
            cal = (HERE / "tb_cal_tran.sp.tmpl").read_text()
            for seed in (42, 43):
                t = subst(cal, SEED=str(seed), SIGMA=a.sigma,
                          TSTEP=CAL_TRAN_TSTEP, **base)
                decks.append({"id": f"cal_tran_s{seed}", "text": t, "timeout_s": 900})
                meta["units"][f"cal_tran_s{seed}"] = {
                    "template": "tb_cal_tran.sp.tmpl", "seed": seed, "sigma_a": a.sigma,
                    "ts_s": TS, "tran_step_s": CAL_TRAN_TSTEP}
            units = [
                ("ring_s42_t10p", SEED_PRIMARY, a.sigma, "t10p"),
                ("ring_s42_t10p_rep", SEED_PRIMARY, a.sigma, "t10p"),
                ("ring_s43_t10p", 43, a.sigma, "t10p"),
                ("ring_s44_t10p", 44, a.sigma, "t10p"),
                ("ring_off_s42_t10p", SEED_PRIMARY, "0.00000e+00", "t10p"),
                ("ring_off_s42_t5p", SEED_PRIMARY, "0.00000e+00", "t5p"),
                ("ring_s42_t5p", SEED_PRIMARY, a.sigma, "t5p"),
                ("ring_s42_amp2_t10p", SEED_PRIMARY, sig2, "t10p"),
                ("ring_s42_amp05_t10p", SEED_PRIMARY, sig05, "t10p"),
            ]
            for uid, seed, sigma, tstep in units:
                decks.append({"id": uid, "text": ring(seed, sigma, RING_TSTEP[tstep]),
                              "timeout_s": 2400})
                meta["units"][uid] = {"template": "tb_ring_jitter.sp.tmpl", "seed": seed,
                                      "sigma_a": sigma, "ts_s": TS,
                                      "tran_step_s": RING_TSTEP[tstep]}
        else:  # seedgap: the primary deck only, in fleet form
            uid = "ring_s42_t10p"
            decks.append({"id": uid, "text": ring(SEED_PRIMARY, a.sigma, RING_TSTEP["t10p"]),
                          "timeout_s": 2400})
            meta["units"][uid] = {"template": "tb_ring_jitter.sp.tmpl (fleet form)",
                                  "seed": SEED_PRIMARY, "sigma_a": a.sigma, "ts_s": TS,
                                  "tran_step_s": RING_TSTEP["t10p"]}

    meta["sigma_a"] = a.sigma or ""
    write_decks(out, decks, meta)


if __name__ == "__main__":
    main()
