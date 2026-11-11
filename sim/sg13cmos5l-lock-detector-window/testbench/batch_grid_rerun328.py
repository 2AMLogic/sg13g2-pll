#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-lock-detector-window (issue #328, Part of #257)

Batch rerun of RECORD-002's campaign (`07e1866:testbench/run.sh`, issue #52).

Thin profile over `batch_grid.py` (issue #322): the same phase0/1/2 deck-list
machinery, with RECORD-002's own inputs substituted so the DUT and the grid are
the ones RECORD-002 measured, not today's:

  * DUT   netlist-snapshots/lock_detector_resized.spice (byte-identical to the
          07e1866 snapshot; same circuit as design/.../lock_detector.spice there)
  * grid  RECORD-002's 18-point ladder matrix (run.sh section 4 at 07e1866); the
          window / Schmitt / tstep / R,C matrices of batch_grid.py are the same
          lists as 07e1866's run.sh and are reused unchanged
  * ladder fractions `record002` (frozen set in sim/tools/gen_lock_ladder.py)
  * templates tb_lock_recovery / tb_lock_ladder_point from `07e1866`
          (testbench/rerun328/): later copies add `itl4=5000 gmin=1e-11` (#66),
          which RECORD-002 did not have.  The other templates are byte-identical
          between 07e1866 and HEAD.
  * output suffix `rerun328` (never run.sh's, never RECORD-002's `resized`)

Subcommands are batch_grid.py's: gen / retry / reduce.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # driver runs under `python3 -I`
import batch_grid as bg  # noqa: E402
OVERRIDE = HERE / "rerun328"

bg.SNAP = bg.RECORD / "netlist-snapshots" / "lock_detector_resized.spice"
bg.LADDER_SET = "record002"
bg.SUFFIX = "rerun328"

_orig_render = bg.render


def _render(tmpl, subs, extra_control=True):
    if (OVERRIDE / tmpl).exists():
        real = bg.HERE
        try:
            bg.HERE = OVERRIDE
            return _orig_render(tmpl, subs, extra_control)
        finally:
            bg.HERE = real
    return _orig_render(tmpl, subs, extra_control)


bg.render = _render


def ladder_points(nominal, primary):
    """run.sh @ 07e1866 section 4: 18 points."""
    V = bg.VSUP_NOM
    pts = []
    for res in ("res_typ", "res_bcs", "res_wcs"):
        for temp in (-40, 27, 125):
            pts.append(("mos_tt", res, temp, V, "3.5e6", primary))
    for res, temp in (("res_typ", 27), ("res_bcs", 125), ("res_wcs", -40)):
        pts.append(("mos_tt", res, temp, V, "24.4e6", primary))
    for var in ("ideal-0.20", "ideal0.20"):
        pts.append(("mos_tt", "res_typ", 27, V, "3.5e6", var))
    for mos in ("mos_ff", "mos_ss"):
        pts.append((mos, "res_typ", 27, V, "3.5e6", primary))
    for vsup in ("2.97", "3.63"):
        pts.append(("mos_tt", "res_typ", 27, vsup, "3.5e6", primary))
    return pts


bg.ladder_points = ladder_points

# ---- second-tier retry (deviation from RECORD-002's options, disclosed) -------
# A unit that still aborts at trtol=1 is re-run once more with the solver-effort
# options later added to the templates by issue #66 (itl4=5000 gmin=1e-11), which
# that issue measured as accuracy-neutral.  Units resolved this way are logged to
# solver_retries_rerun328.txt with a `[+itl4/gmin]` mark.
_orig_stdout_of = bg.stdout_of


def _stdout_of(work, phase, uid):
    p = work / (phase + "_retry2") / "out" / uid / "stdout.bin"
    if p.exists():
        return p.read_text(errors="replace"), True
    return _orig_stdout_of(work, phase, uid)


bg.stdout_of = _stdout_of


def retry2(work, phase):
    import json
    import re
    rep = json.loads((work / (phase + "_retry") / "report.json").read_text())
    bad = [u["id"] for u in rep["units"] if u.get("status") != "pass"]
    units = []
    for uid in bad:
        text = (work / (phase + "_retry") / "decks" / (uid + ".sp")).read_text()
        new = re.sub(r"^(\.options reltol=.*)$", r"\1 itl4=5000 gmin=1e-11", text, flags=re.M)
        incs = re.findall(r"^\.include +(dut_\S+)", text, flags=re.M)
        units.append((uid, new, [work / phase / "decks" / i for i in incs]))
        print("[solver-retry2] %s failed at trtol=1; retrying with trtol=1 itl4=5000 gmin=1e-11" % uid,
              file=sys.stderr)
    bg.write_request(work / (phase + "_retry2"), units)


# ---- corners with a unit that never converged are kept as NA rows ------------
_orig_ladder_params = bg.ladder_params


def _ladder_params(work, nominal, pt, rval, cnom):
    import json
    tag = bg.tag_of(*pt)
    for d in ("phase2_retry2", "phase2_retry"):
        rp = work / d / "report.json"
        if rp.exists():
            for u in json.loads(rp.read_text())["units"]:
                if u.get("status") != "pass" and u["id"].startswith("lad_%s_" % tag):
                    print("[unconverged] %s: unit %s failed under every solver setting; NA row" %
                          (tag, u["id"]), file=sys.stderr)
                    return None
            break
    return _orig_ladder_params(work, nominal, pt, rval, cnom)


bg.ladder_params = _ladder_params

if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[1] == "retry2":
        retry2(pathlib.Path(sys.argv[2]).resolve(), sys.argv[3])
    else:
        bg.main()
