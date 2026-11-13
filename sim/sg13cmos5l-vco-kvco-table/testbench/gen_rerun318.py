#!/usr/bin/env python3
"""Render RECORD-001's 60-point grid as a `klt sim` deck-list request that runs
against the **pinned** `ihp-sg13cmos5l` tree (issue #318, child of #216).

    python3 -I gen_rerun318.py OUTDIR --pinned-pdk DIR [--probe]

Why this is not the sibling benches' generator: the fleet image's
`/opt/pdk/ihp-sg13cmos5l` is the post-2026-10-15 `f7bca326...` install, not
`sim/README.md`'s `PDK-PIN ihp-sg13cmos5l 607e18d4...`.  A deck that writes
`.lib $PDK_ROOT/ihp-sg13cmos5l/...` is resolved on the worker and therefore
runs on the wrong revision, which is why a same-bench superseding rerun could
not cite the pin (the `sim/README.md` "Provenance addenda" contract requires
it to).  `klt sim`'s deck-list preservation contract gives the way out: a
`.include`/`.lib <file> <section>`/`pre_osdi` target written as a path
*relative to the deck* is staged from the submitting host at that same
relative path inside each unit directory, with its own closure, so the deck
bytes still ship verbatim.  This generator therefore copies the pinned tree's
corner-library closure and OSDI objects beside the decks and references them
relatively, so the grid runs on the pinned model bytes on fleet capacity.

What the decks differ in from `run.sh`'s, all mechanical and disclosed in
RECORD-002:
  1. the two `.lib` paths are `models/corner*.lib` (staged, see above)
     instead of `$PDK_ROOT/$PDK/libs.tech/ngspice/models/corner*.lib`;
  2. the four OSDI objects are preloaded with `pre_osdi osdi/<n>.osdi` lines
     inside the existing `.control` block, because a deck-list unit has no
     `.spiceinit` (`run.sh` writes one);
  3. `XCDECAP` is commented out in the staged DUT copy, which is exactly
     what `run.sh` does (see its header).
Everything else -- the matrix, `.option`, `.ic`, `.tran` and the `.meas`
line -- is `tb_vco_kvco.sp.tmpl` rendered with `run.sh`'s own substitutions.

Submit with (host policy: no local ngspice grids):

    klt sim OUTDIR/request.json --backend batch --wait-for-capacity 600 \
        -o OUTDIR/out --format json --report-out OUTDIR/report.json
"""
import argparse
import csv
import hashlib
import json
import pathlib
import re
import shutil

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent

# run.sh's 3 correlated PVT bundles (see ../corners/matrix.md for the subset
# rationale), 4 band codes and 5 VCTRL points = 60 units.
BUNDLES = [("typ", "mos_tt", "res_typ", "27"),
           ("slow", "mos_ss", "res_wcs", "125"),
           ("fast", "mos_ff", "res_bcs", "-40")]
BANDS = [("00", "0.0", "0.0"), ("10", "3.3", "0.0"),
         ("01", "0.0", "3.3"), ("11", "3.3", "3.3")]
VCTRLS = ["0.3", "0.9", "1.5", "2.1", "2.7"]

# Exactly run.sh's .spiceinit list: this DUT needs PSP103 (sg13_hv_nmos/pmos)
# and r3_cmc (rppd/rhigh) only -- cap_cmomi/cap_cmomf are deliberately NOT
# loaded, because XCDECAP is stripped (run.sh's header explains why that is
# sound for this measurement).
OSDI = ["psp103", "psp103_nqs", "mosvar", "r3_cmc"]

MODELS_TOKEN = "@PDK_ROOT@/@PDK@/libs.tech/ngspice/models"
INCLUDE_RE = re.compile(r"^\s*\.(?:include|inc)\s+(\S+)\s*$", re.I | re.M)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_closure(src_models: pathlib.Path, dest: pathlib.Path, seeds):
    """Copy `seeds` and, recursively, every file their `.include` directives
    name, dereferencing symlinks (the pinned tree tracks most model cards as
    symlinks into the sibling ihp-sg13g2 tree).  Returns the copied names."""
    dest.mkdir(parents=True, exist_ok=True)
    queue, done = list(seeds), []
    while queue:
        name = queue.pop(0)
        if name in done:
            continue
        src = src_models / name
        if not src.is_file():
            raise SystemExit(f"model closure: {src} is not a readable file")
        shutil.copyfile(src, dest / name)  # follows symlinks
        done.append(name)
        for target in INCLUDE_RE.findall(src.read_text(errors="replace")):
            if "/" in target or target.startswith("$"):
                raise SystemExit(
                    f"model closure: {src} includes {target!r}; this generator "
                    "only follows same-directory relative includes")
            queue.append(target)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--pinned-pdk", required=True,
                    help="the ihp-sg13cmos5l tree at sim/README.md's "
                         "PDK-PIN revision (a clean checkout of it)")
    ap.add_argument("--probe", action="store_true",
                    help="emit one unit only (typ / band 00 / VCTRL=1.5 V)")
    ap.add_argument("--cap-probe", action="store_true",
                    help="emit probe_cap_cmom_rerun318.sp instead of the grid: "
                         "the cap_cmom* availability check RECORD-002 cites "
                         "(it also stages cornerCAP.lib and both cap_cmom* "
                         "OSDI objects, which the grid never loads)")
    a = ap.parse_args()

    out = pathlib.Path(a.outdir).resolve()
    pdk = pathlib.Path(a.pinned_pdk).resolve()
    decks_dir = out / "decks"
    if decks_dir.exists():
        shutil.rmtree(decks_dir)
    decks_dir.mkdir(parents=True)

    # The DUT: run.sh's own XCDECAP-stripped derivation of the frozen snapshot
    # (the snapshot itself stays an exact, unmodified export).
    snap = RECORD / "netlist-snapshots" / "vco.spice"
    (decks_dir / "vco_open.spice").write_text(
        re.sub(r"^(XCDECAP)", r"*\1", snap.read_text(), flags=re.M))

    staged = []  # (staged_name, source_path, sha256)
    seeds = ["cornerMOShv.lib", "cornerRES.lib"]
    osdi_names = list(OSDI)
    if a.cap_probe:
        # Only the cap_cmom* probe needs these; the grid's DUT has no
        # cap_cmom instance (XCDECAP is stripped), so it never loads them.
        seeds = ["cornerCAP.lib"]
        osdi_names += ["cap_cmomi", "cap_cmomf"]
    models = copy_closure(pdk / "libs.tech" / "ngspice" / "models",
                          decks_dir / "models", seeds)
    for name in models:
        src = pdk / "libs.tech" / "ngspice" / "models" / name
        staged.append((f"models/{name}", str(src.resolve()),
                       sha256(decks_dir / "models" / name)))
    (decks_dir / "osdi").mkdir()
    for name in osdi_names:
        src = pdk / "libs.tech" / "ngspice" / "osdi" / f"{name}.osdi"
        if not src.is_file():
            raise SystemExit(f"OSDI: {src} is not a readable file")
        shutil.copyfile(src, decks_dir / "osdi" / f"{name}.osdi")
        staged.append((f"osdi/{name}.osdi", str(src.resolve()),
                       sha256(decks_dir / "osdi" / f"{name}.osdi")))

    decks, rows = [], []
    if a.cap_probe:
        uid = "cap_cmom_probe"
        text = (HERE / "probe_cap_cmom_rerun318.sp").read_text()
        (decks_dir / f"{uid}.sp").write_text(text)
        decks.append({"id": uid, "deck": f"decks/{uid}.sp", "timeout_s": 600})
        rows.append((uid, "-", "-", "-", "27", "-", "-",
                     sha256(decks_dir / f"{uid}.sp")))

    pre = "".join(f"pre_osdi osdi/{n}.osdi\n" for n in OSDI)
    tmpl = (HERE / "tb_vco_kvco.sp.tmpl").read_text()
    for bname, mos, res, temp in BUNDLES:
        for blabel, b0v, b1v in BANDS:
            for vctrl in VCTRLS:
                if a.cap_probe:
                    continue
                if a.probe and (bname, blabel, vctrl) != ("typ", "00", "1.5"):
                    continue
                uid = f"{bname}_b{blabel}_v{vctrl.replace('.', 'p')}"
                text = tmpl
                for token, value in (("@CORNER_MOS@", mos), ("@CORNER_RES@", res),
                                     ("@TEMP@", temp), ("@VCTRL@", vctrl),
                                     ("@B0V@", b0v), ("@B1V@", b1v),
                                     (MODELS_TOKEN, "models")):
                    text = text.replace(token, value)
                text = text.replace(".control\nrun", ".control\n" + pre + "run")
                if "@" in re.sub(r"(?m)^\*.*$", "", text):
                    raise SystemExit(f"{uid}: unsubstituted @TOKEN@ left in deck")
                (decks_dir / f"{uid}.sp").write_text(text)
                decks.append({"id": uid, "deck": f"decks/{uid}.sp",
                              "timeout_s": 1800})
                rows.append((uid, bname, mos, res, temp, blabel, vctrl,
                             sha256(decks_dir / f"{uid}.sp")))

    request = {
        "engine": "ngspice",
        "backend": "batch",
        # Selects the fleet image, exactly as the corner path does. The model
        # bytes themselves are the staged pinned ones, not this image's.
        "models": {"pdk": "ihp-sg13cmos5l"},
        "decks": decks,
        "batch": {"capacity_wait_s": 600},
        "options": {"timeout_s": 1800, "max_workers": 2},
    }
    name = ("cap_probe.request.json" if a.cap_probe
            else "probe.request.json" if a.probe else "request.json")
    (out / name).write_text(json.dumps(request, indent=2) + "\n")

    with open(out / "decks.sha256.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "pvt_bundle", "mos_corner", "res_corner", "temp_c",
                    "band_code", "vctrl_v", "deck_sha256"])
        w.writerows(rows)
    with open(out / "staged_pdk.sha256.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["staged_name", "source_path", "sha256"])
        w.writerows(staged)
    print(f"wrote {len(decks)} decks and {len(staged)} staged PDK files to {out}")
    print(f"request: {out / name}")


main()
