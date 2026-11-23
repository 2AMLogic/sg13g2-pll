#!/usr/bin/env python3
"""Tests for sim/tools/stage_pinned_pdk.py (issue #544).

Stdlib `unittest`, offline, <1 s: no ngspice, no klt, no host PDK checkout --
every test runs against a synthetic `ihp-sg13cmos5l` fixture built in a
`tempfile.TemporaryDirectory()` (symlinked model seeds, a multi-hop
case-insensitive `.include` closure, fake OSDI objects, and -- for the
git-pin check -- a temporary `git init` fixture).  The end-to-end tests
drive three of the four repointed generators exactly as their benches do
(`python3 -I`, one with `PINNED_PDK` instead of `--pinned-pdk`, which the
pre-#544 copy advertised and never implemented) and import the fourth's
`stage_pinned` directly (`gen_rerun319.py render` writes next to its own
source tree, so the shared staging is exercised through its public function
on a temporary decks directory instead).

Run from the repo root: python3 -B sim/tools/test_stage_pinned_pdk.py
"""
import csv
import contextlib
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import stage_pinned_pdk as spp  # noqa: E402

KVCO = REPO / "sim" / "sg13cmos5l-vco-kvco-table" / "testbench"
CLOSED = REPO / "sim" / "sg13cmos5l-closed-loop-lock" / "testbench"
DIVIDER = REPO / "sim" / "sg13cmos5l-divider-max-frequency" / "testbench"
BWM = REPO / "sim" / "sg13cmos5l-loop-bandwidth-pm" / "testbench"

#: The MOS closure in BFS order: the two seeds, then each include as
#: discovered -- mixed-case `.INCLUDE`, `.inc` and indented directives all
#: followed (the pre-#544 copies dropped one or more of those three).
MOS_CLOSURE = ["cornerMOShv.lib", "cornerRES.lib", "sg13_hv.lib",
               "resistors_mod.lib", "psp_cards.inc", "svaricap.lib",
               "indented_card.lib"]
OSDI_FOUR = ["psp103", "psp103_nqs", "mosvar", "r3_cmc"]


def make_synthetic_pdk(root):
    """A minimal ihp-sg13cmos5l-shaped tree: corner libraries whose
    `.include` closure mixes `.include`, `.INCLUDE`, `.inc` and indented
    directives, a symlinked seed (the pinned tree tracks cards as symlinks
    into the sibling ihp-sg13g2 tree), and fake OSDI objects."""
    pdk = root / "ihp-sg13cmos5l"
    models = pdk / "libs.tech" / "ngspice" / "models"
    osdi = pdk / "libs.tech" / "ngspice" / "osdi"
    models.mkdir(parents=True)
    osdi.mkdir(parents=True)
    (models / "cornerMOShv.lib").write_text(
        "* synthetic cornerMOShv\n.include sg13_hv.lib\n")
    (models / "sg13_hv.lib").write_text(
        "* synthetic hv cards\n"
        ".INCLUDE psp_cards.inc\n"
        ".inc svaricap.lib\n"
        "  .include indented_card.lib\n")
    (models / "psp_cards.inc").write_text("* synthetic psp cards\n")
    (models / "svaricap.lib").write_text("* synthetic svaricap\n")
    (models / "indented_card.lib").write_text("* synthetic indented card\n")
    sister = root / "ihp-sg13g2" / "libs.tech" / "ngspice" / "models"
    sister.mkdir(parents=True)
    (sister / "resistors_mod.lib").write_text("* synthetic resistors_mod\n")
    (models / "cornerRES.lib").write_text(
        "* synthetic cornerRES\n.include resistors_mod.lib\n")
    # The pinned tree tracks cards as symlinks into the sibling ihp-sg13g2
    # tree; the include still resolves inside the pinned models directory.
    (models / "resistors_mod.lib").symlink_to(sister / "resistors_mod.lib")
    for n in OSDI_FOUR + ["cap_cmomi", "cap_cmomf"]:
        (osdi / f"{n}.osdi").write_bytes(f"synthetic-osdi-{n}\n".encode())
    return pdk


def read_rows(path):
    with open(path, newline="") as fh:
        return list(csv.reader(fh))


class CopyModelClosure(unittest.TestCase):
    def test_multihop_case_insensitive_closure_and_symlinks(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            dest = Path(td) / "decks" / "models"
            done = spp.copy_model_closure(
                pdk / "libs.tech" / "ngspice" / "models", dest,
                ["cornerMOShv.lib", "cornerRES.lib"])
            self.assertEqual(done, MOS_CLOSURE)
            # Symlinked seeds are copied by content, not as links.
            self.assertFalse((dest / "resistors_mod.lib").is_symlink())
            self.assertEqual((dest / "resistors_mod.lib").read_text(),
                             "* synthetic resistors_mod\n")

    def test_restage_is_idempotent_and_repairs_drifted_bytes(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            src_models = pdk / "libs.tech" / "ngspice" / "models"
            dest = Path(td) / "decks" / "models"
            spp.copy_model_closure(src_models, dest, ["cornerMOShv.lib"])
            sentinel = 1_000_000
            os.utime(dest / "sg13_hv.lib", (sentinel, sentinel))
            spp.copy_model_closure(src_models, dest, ["cornerMOShv.lib"])
            self.assertEqual(os.stat(dest / "sg13_hv.lib").st_mtime, sentinel,
                             "identical bytes must not be rewritten")
            (dest / "sg13_hv.lib").write_text("tampered\n")
            spp.copy_model_closure(src_models, dest, ["cornerMOShv.lib"])
            self.assertEqual((dest / "sg13_hv.lib").read_text(),
                             (src_models / "sg13_hv.lib").read_text(),
                             "drifted bytes must be restaged")

    def test_missing_seed_fails(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            with self.assertRaises(SystemExit) as ctx:
                spp.copy_model_closure(
                    pdk / "libs.tech" / "ngspice" / "models",
                    Path(td) / "decks" / "models", ["no_such.lib"])
            self.assertIn("no_such.lib", str(ctx.exception))

    def test_pathlike_and_env_includes_are_rejected(self):
        for directive in (".include sub/dir.lib", ".include $PDK_ROOT/x.lib"):
            with TemporaryDirectory() as td:
                pdk = make_synthetic_pdk(Path(td))
                models = pdk / "libs.tech" / "ngspice" / "models"
                (models / "cornerMOShv.lib").write_text(f"* t\n{directive}\n")
                with self.assertRaises(SystemExit) as ctx:
                    spp.copy_model_closure(
                        models, Path(td) / "decks" / "models",
                        ["cornerMOShv.lib"], label="unit")
                self.assertIn("same-directory relative includes",
                              str(ctx.exception))


class StagePinnedPdk(unittest.TestCase):
    def test_rows_are_bfs_models_then_caller_osdi(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            decks = Path(td) / "decks"
            decks.mkdir()
            rows = spp.stage_pinned_pdk(pdk, decks,
                                        ["cornerMOShv.lib", "cornerRES.lib"],
                                        ["mosvar", "psp103"])
            names = [r[0] for r in rows]
            self.assertEqual(names,
                             [f"models/{n}" for n in MOS_CLOSURE]
                             + ["osdi/mosvar.osdi", "osdi/psp103.osdi"])
            for staged, src, digest in rows:
                self.assertEqual(
                    (decks / staged).read_bytes(),
                    (pdk / "libs.tech" / "ngspice" / staged).read_bytes())
                self.assertTrue(Path(src).is_file())
                self.assertEqual(digest, spp.sha256(decks / staged))

    def test_missing_osdi_fails(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            decks = Path(td) / "decks"
            decks.mkdir()
            with self.assertRaises(SystemExit) as ctx:
                spp.stage_pinned_pdk(pdk, decks, ["cornerMOShv.lib"],
                                     ["not_an_osdi"])
            self.assertIn("not_an_osdi.osdi", str(ctx.exception))


class WriteStagedManifest(unittest.TestCase):
    ROWS = [("osdi/b.osdi", "/src/b", "bb"),
            ("models/a.lib", "/src/a", "aa"),
            ("models/c.lib", "/src/c", "cc")]

    def test_default_preserves_order_and_header(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "staged_pdk.sha256.csv"
            spp.write_staged_manifest(path, self.ROWS)
            self.assertEqual(read_rows(path),
                             [["staged_name", "source_path", "sha256"]]
                             + [list(r) for r in self.ROWS])

    def test_sort_rows_sorts_the_whole_tuple(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "staged_pdk.sha256.csv"
            spp.write_staged_manifest(path, self.ROWS, sort_rows=True)
            self.assertEqual(read_rows(path)[1:],
                             sorted([list(r) for r in self.ROWS]))


class ResolvePinnedPdk(unittest.TestCase):
    def _with_env(self, value, fn):
        old = os.environ.get("PINNED_PDK")
        if value is None:
            os.environ.pop("PINNED_PDK", None)
        else:
            os.environ["PINNED_PDK"] = value
        try:
            return fn()
        finally:
            if old is None:
                os.environ.pop("PINNED_PDK", None)
            else:
                os.environ["PINNED_PDK"] = old

    def test_cli_argument_wins_over_env(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            other = Path(td) / "other"
            other.mkdir()
            self._with_env(str(other),
                           lambda: self.assertEqual(
                               spp.resolve_pinned_pdk(str(pdk), prog="gen.py"),
                               pdk))

    def test_env_fallback_when_cli_absent(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            self._with_env(str(pdk),
                           lambda: self.assertEqual(
                               spp.resolve_pinned_pdk(None, prog="gen.py"),
                               pdk))

    def test_required_without_env(self):
        def check():
            with self.assertRaises(SystemExit) as ctx:
                spp.resolve_pinned_pdk(None, prog="gen.py", allow_env=False)
            self.assertEqual(str(ctx.exception),
                             "gen.py: --pinned-pdk DIR is required.")
        self._with_env(None, check)

    def test_required_with_env_mentions_the_env_var(self):
        def check():
            with self.assertRaises(SystemExit) as ctx:
                spp.resolve_pinned_pdk(None, prog="gen.py")
            self.assertEqual(
                str(ctx.exception),
                "gen.py: --pinned-pdk DIR (or PINNED_PDK=DIR) is required.")
        self._with_env(None, check)

    def test_allow_env_false_ignores_env(self):
        def check():
            with self.assertRaises(SystemExit):
                spp.resolve_pinned_pdk(None, prog="gen.py", allow_env=False)
        self._with_env("/nonexistent-from-env", check)

    @staticmethod
    def _git_fixture(td):
        tree = Path(td) / "pinned"
        (tree / "libs.tech").mkdir(parents=True)
        (tree / "libs.tech" / "pin.txt").write_text("pinned\n")
        readme = Path(td) / "README.md"
        readme.write_text("placeholder\n")
        for cmd in (["git", "init", "-q"],
                    ["git", "config", "user.email", "t@example.org"],
                    ["git", "config", "user.name", "t"],
                    ["git", "add", "-A"],
                    ["git", "commit", "-q", "-m", "t"]):
            subprocess.run(cmd, cwd=tree, check=True)
        head = subprocess.check_output(
            ["git", "-C", str(tree), "rev-parse", "HEAD"], text=True).strip()
        return tree, readme, head

    def test_verify_pin_readme_match_mismatch_and_missing_line(self):
        with TemporaryDirectory() as td:
            tree, readme, head = self._git_fixture(td)
            readme.write_text(f"preamble\nPDK-PIN ihp-sg13cmos5l {head}\n")
            with contextlib.redirect_stdout(io.StringIO()):
                got = spp.resolve_pinned_pdk(str(tree), prog="gen.py",
                                             verify_pin_readme=readme)
            self.assertEqual(got, tree)
            readme.write_text("PDK-PIN ihp-sg13cmos5l " + "0" * 40 + "\n")
            with self.assertRaises(SystemExit) as ctx:
                spp.resolve_pinned_pdk(str(tree), prog="gen.py",
                                       verify_pin_readme=readme)
            self.assertIn("pins", str(ctx.exception))
            readme.write_text("no pin line at all\n")
            with self.assertRaises(SystemExit) as ctx:
                spp.resolve_pinned_pdk(str(tree), prog="gen.py",
                                       verify_pin_readme=readme)
            self.assertIn("PDK-PIN", str(ctx.exception))


class GeneratorsEndToEnd(unittest.TestCase):
    """The four repointed generators, driven against the synthetic PDK."""

    def test_gen_rerun318_probe(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            out = Path(td) / "out"
            subprocess.run([sys.executable, "-I", str(KVCO / "gen_rerun318.py"),
                            str(out), "--pinned-pdk", str(pdk), "--probe"],
                           check=True)
            names = [r[0] for r in read_rows(out / "staged_pdk.sha256.csv")[1:]]
            self.assertEqual(names,
                             [f"models/{n}" for n in MOS_CLOSURE]
                             + [f"osdi/{n}.osdi" for n in OSDI_FOUR])
            self.assertTrue((out / "probe.request.json").exists())
            self.assertTrue((out / "decks" / "vco_open.spice").exists())
            self.assertTrue(list((out / "decks").glob("*.sp")))

    def test_gen_rerun318_cap_probe_stages_cornerCAP(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            models = pdk / "libs.tech" / "ngspice" / "models"
            (models / "cornerCAP.lib").write_text("* synthetic cap corner\n")
            osdi = pdk / "libs.tech" / "ngspice" / "osdi"
            for n in ("cap_cmomi", "cap_cmomf"):
                (osdi / f"{n}.osdi").write_bytes(f"synthetic-osdi-{n}\n".encode())
            out = Path(td) / "out"
            subprocess.run([sys.executable, "-I", str(KVCO / "gen_rerun318.py"),
                            str(out), "--pinned-pdk", str(pdk), "--cap-probe"],
                           check=True)
            names = [r[0] for r in read_rows(out / "staged_pdk.sha256.csv")[1:]]
            self.assertEqual(names,
                             ["models/cornerCAP.lib",
                              "osdi/psp103.osdi", "osdi/psp103_nqs.osdi",
                              "osdi/mosvar.osdi", "osdi/r3_cmc.osdi",
                              "osdi/cap_cmomi.osdi", "osdi/cap_cmomf.osdi"])

    def test_gen_125c_via_PINNED_PDK_env(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            out = Path(td) / "out"
            env = dict(os.environ, PINNED_PDK=str(pdk))
            subprocess.run([sys.executable, "-I",
                            str(CLOSED / "gen_125c_acquisition_requests.py"),
                            str(out)], check=True, env=env)
            names = [r[0] for r in read_rows(out / "vco" / "staged_pdk.sha256.csv")[1:]]
            self.assertEqual(names,
                             [f"models/{n}" for n in MOS_CLOSURE]
                             + [f"osdi/{n}.osdi" for n in OSDI_FOUR])
            self.assertTrue((out / "vco" / "request.json").exists())
            self.assertTrue((out / "loop_nominal" / "request.json").exists())

    def test_gen_maxfreq_anchors_manifest_is_sorted(self):
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            out = Path(td) / "out"
            subprocess.run([sys.executable, "-I",
                            str(DIVIDER / "gen_maxfreq_requests.py"),
                            "--pinned-pdk", str(pdk),
                            "--outdir", str(out), "anchors"], check=True)
            rows = read_rows(out / "staged_pdk.sha256.csv")
            self.assertEqual(rows[0], ["staged_name", "source_path", "sha256"])
            names = [r[0] for r in rows[1:]]
            self.assertEqual(names, sorted(names))
            # maxfreq seeds cornerMOShv.lib only, and stages three OSDI
            # objects (no r3_cmc: the divider DUT has no resistors).
            mos_only = [n for n in MOS_CLOSURE if n != "cornerRES.lib"
                        and n != "resistors_mod.lib"]
            self.assertEqual(names,
                             sorted([f"models/{n}" for n in mos_only]
                                    + ["osdi/psp103.osdi", "osdi/psp103_nqs.osdi",
                                       "osdi/mosvar.osdi"]))
            # The DUT snapshot is staged beside the decks (not manifested).
            self.assertTrue((out / "decks" / "divider_chain.spice").exists())
            self.assertTrue((out / "anchors.request.json").exists())

    def test_gen_rerun319_stage_pinned_imported(self):
        sys.path.insert(0, str(BWM))
        try:
            import gen_rerun319
        finally:
            sys.path.remove(str(BWM))
        with TemporaryDirectory() as td:
            pdk = make_synthetic_pdk(Path(td))
            decks = Path(td) / "decks"
            decks.mkdir()
            (decks / "arm.sp").write_text(
                ".lib models/cornerMOShv.lib mos_tt\n"
                ".lib models/cornerRES.lib res_typ\n")
            rows = gen_rerun319.stage_pinned(pdk, decks, "fixture-arm")
            self.assertEqual([r[0] for r in rows],
                             [f"models/{n}" for n in MOS_CLOSURE]
                             + [f"osdi/{n}.osdi"
                                for n in gen_rerun319.OSDI_NAMES])
            with self.assertRaises(SystemExit):
                gen_rerun319.stage_pinned(pdk, decks / "empty", "empty-arm")


if __name__ == "__main__":
    unittest.main()
