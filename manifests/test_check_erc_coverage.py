"""Negative tests for check_erc_coverage.py, on temporary copies only.

Run from the repo root: python3 manifests/test_check_erc_coverage.py
The committed evidence is never modified (GDS files are symlinked read-only
into the temporary tree; JSON is copied and edited there).
"""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_erc_coverage as chk  # noqa: E402

MANIFEST = Path("manifests/sg13g2-pll.json")
TIER = Path("manifests/sg13g2-pll.tier-report.json")
EV = json.loads(MANIFEST.read_text())["evidence"]
ERC_REC = Path(EV["11.analog"][0]["file"]).parent
LVS_REC = Path(EV["4.analog"]["file"]).parent
SPECS = Path(chk.DEFAULT_SPECS)
BLOCKS = chk.ANALOG_BLOCKS
ORIG_KNOWN = dict(chk.KNOWN_DEFECTS)
ORIG_ALLOWED = dict(chk.DISCLOSURE_ALLOWED)


def restore_module():
    chk.KNOWN_DEFECTS.clear()
    chk.KNOWN_DEFECTS.update(ORIG_KNOWN)
    chk.DISCLOSURE_ALLOWED.clear()
    chk.DISCLOSURE_ALLOWED.update(ORIG_ALLOWED)


def sha(p):
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Cov(unittest.TestCase):
    tmp = None

    def setUp(self):
        """Fresh temporary tree; also called again inside subtests to reset."""
        self.tearDown()
        self.tmp = Path(tempfile.mkdtemp())
        self.erc, self.lvs, self.specs = (self.tmp / d for d in ("erc", "lvs", "specs"))
        for d in (self.erc, self.lvs, self.specs):
            d.mkdir()
        for b in BLOCKS:
            shutil.copy(ERC_REC / f"erc.supply-spec.pll_{b}.json", self.erc)
            shutil.copy(LVS_REC / f"lvs.{b}.json", self.lvs)
            shutil.copy(LVS_REC / f"{b}.reference.spice", self.lvs)
            (self.lvs / f"pll_{b}.gds").symlink_to((LVS_REC / f"pll_{b}.gds").resolve())
            shutil.copy(SPECS / f"erc-supply-spec.pll_{b}.json", self.specs)
        m = json.loads(MANIFEST.read_text())
        ev = m["evidence"]
        ev["4.analog"]["file"] = (self.lvs / "lvs.lock_detector.json").as_posix()
        ev["11.analog"][0]["file"] = (self.erc / "erc.supply-spec.pll_lock_detector.json").as_posix()
        ev["11.analog"][1]["file"] = (self.lvs / "lvs.lock_detector.json").as_posix()
        self.manifest = self.tmp / "manifest.json"
        self.manifest.write_text(json.dumps(m))
        self.tier = self.tmp / "tier.json"
        shutil.copy(TIER, self.tier)

    def tearDown(self):
        restore_module()
        if self.tmp is not None:
            shutil.rmtree(self.tmp)
            self.tmp = None

    def edit(self, path, fn):
        d = json.loads(path.read_text())
        fn(d)
        path.write_text(json.dumps(d))

    def rep(self, b):
        return self.erc / f"erc.supply-spec.pll_{b}.json"

    def set_tier(self, status):
        def f(d):
            for it in d["items"]:
                if it.get("id") == 11 and it.get("partition") == "analog":
                    it["status"] = status
        self.edit(self.tier, f)

    def run_main(self):
        return chk.main(["--manifest", str(self.manifest), "--tier-report", str(self.tier),
                         "--erc-record", str(self.erc), "--lvs-record", str(self.lvs),
                         "--specs", str(self.specs)])

    def test_committed_state(self):
        self.assertEqual(chk.main([]), 0)

    def test_copy_passes(self):
        self.assertEqual(self.run_main(), 0)

    def test_missing_report(self):
        for b in BLOCKS:
            with self.subTest(b):
                self.setUp()
                self.rep(b).unlink()
                self.assertEqual(self.run_main(), 1)

    def test_duplicate_block_identity(self):
        shutil.copy(self.rep("cp"), self.rep("pfd"))
        self.assertEqual(self.run_main(), 1)

    def test_wrapper_or_error_envelope(self):
        self.edit(self.rep("vco"), lambda d: (d.clear(), d.update(error={"message": "x"})))
        self.assertEqual(self.run_main(), 1)

    def test_corrupted_input_hash(self):
        self.edit(self.rep("vco"), lambda d: d["provenance"]["input"].update(content_hash="sha256:" + "0" * 64))
        self.assertEqual(self.run_main(), 1)

    def test_lvs_input_mismatch(self):
        self.edit(self.lvs / "lvs.cp.json",
                  lambda d: d["response"]["provenance"]["input"].update(content_hash="sha256:" + "1" * 64))
        self.assertEqual(self.run_main(), 1)

    def test_missing_supply_mapping(self):
        for b, net in (("vco", "VDD_VCO"), ("loop_filter", "VSS"), ("pfd", "VSS")):
            with self.subTest(b):
                self.setUp()
                self.edit(self.lvs / f"lvs.{b}.json", lambda d: d["response"].update(
                    net_correspondence=[r for r in d["response"]["net_correspondence"] if r["layout"] != net]))
                self.assertEqual(self.run_main(), 1)

    def test_lvs_wrong_pair_or_reference(self):
        self.edit(self.lvs / "lvs.vco.json", lambda d: d["response"].update(top="pll_cp"))
        self.assertEqual(self.run_main(), 1, "lvs of another top cell")
        self.setUp()
        ref = self.lvs / "cp.reference.spice"
        ref.write_text(ref.read_text().replace(" VDD VSS\n", " VDD\n", 1))
        self.assertEqual(self.run_main(), 1, "reference no longer carries the rail as a port")

    def add_finding(self, b):
        def f(d):
            d["erc_findings"] = [{"rule": "erc.unconnected_net", "net": "VSS"}]
            d["erc_finding_count"] = 1
            d["erc_status"] = "violations"
        self.edit(self.rep(b), f)

    def test_finding_rejects_met_claim(self):
        for b in BLOCKS:
            with self.subTest(b):
                self.setUp()
                self.add_finding(b)
                self.assertEqual(self.run_main(), 1)

    def test_unmet_branch(self):
        self.add_finding("cp")
        self.set_tier("unmet")
        self.assertEqual(self.run_main(), 1, "undocumented defect must fail")
        chk.KNOWN_DEFECTS["cp"] = "#999"
        self.assertEqual(self.run_main(), 0, "documented defect under unmet passes")
        self.set_tier("met")
        self.assertEqual(self.run_main(), 1, "met claim with a known defect must fail")

    def test_unmet_branch_rejects_stale_or_cited_defect(self):
        self.set_tier("unmet")
        chk.KNOWN_DEFECTS["pfd"] = "#999"
        self.assertEqual(self.run_main(), 1, "stale KNOWN_DEFECTS entry")
        chk.KNOWN_DEFECTS.clear()
        self.add_finding("lock_detector")
        chk.KNOWN_DEFECTS["lock_detector"] = "#999"
        self.assertEqual(self.run_main(), 1, "cited block is the defective one")

    def test_non_clean_status_without_findings(self):
        self.edit(self.rep("pfd"), lambda d: d.update(erc_status="clean_partial"))
        self.assertEqual(self.run_main(), 1)

    def test_degenerate_tie(self):
        self.edit(self.rep("vco"), lambda d: d["erc_coverage"].update(
            skipped=[{"id": 'erc.missing_tie:["nwell_tap"]', "reason": "degenerate_tap_declaration"}]))
        self.assertEqual(self.run_main(), 1)

    def test_unchecked_tie_or_supply(self):
        for wid in ('erc.missing_tie:["substrate_tap"]', 'erc.net_connectivity:["VDD"]'):
            with self.subTest(wid):
                self.setUp()
                self.edit(self.rep("cp"), lambda d: d["erc_coverage"].update(
                    checked=[c for c in d["erc_coverage"]["checked"] if c != wid]))
                self.assertEqual(self.run_main(), 1)

    def test_unknown_coverage(self):
        self.edit(self.rep("pfd"), lambda d: d["erc_coverage"].update(unknown=["x"]))
        self.assertEqual(self.run_main(), 1)

    def test_assertion_classification(self):
        self.edit(self.rep("pfd"), lambda d: d["erc_coverage"]["checked_by_well_assertion"].append(
            'erc.missing_tie:["nwell_tap"]'))
        self.assertEqual(self.run_main(), 1, "drawn NWell tie presented as an assertion")
        self.setUp()
        self.edit(self.rep("pfd"), lambda d: d["erc_coverage"].update(checked_by_well_assertion=[]))
        self.assertEqual(self.run_main(), 1, "substrate assertion presented as drawn coverage")

    def test_loop_filter_disclosure_must_be_justified(self):
        self.edit(self.rep("loop_filter"), lambda d: d["erc_coverage"].update(
            inapplicable=[{"id": "erc.missing_tie:[]", "reason": "no_ties_declared"}]))
        self.assertEqual(self.run_main(), 1, "undisclosed omission")
        self.setUp()
        chk.DISCLOSURE_ALLOWED["loop_filter"] = (5,)  # GatPoly IS drawn there
        self.assertEqual(self.run_main(), 1, "geometry contradicts the disclosure")
        self.setUp()
        chk.DISCLOSURE_ALLOWED.pop("loop_filter")
        self.assertEqual(self.run_main(), 1, "disclosure with no geometric justification")

    def test_gds_layer_scan(self):
        self.assertFalse(chk.gds_layers(LVS_REC / "pll_loop_filter.gds") & {1, 31})
        self.assertTrue({1, 31} <= chk.gds_layers(LVS_REC / "pll_pfd.gds"))

    def test_gds_layer_scan_rejects_malformed_stream(self):
        data = (LVS_REC / "pll_loop_filter.gds").read_bytes()
        first = int.from_bytes(data[:2], "big")  # HEADER record length
        cases = {
            "truncated (no ENDLIB)": data[: len(data) // 2],
            "zero-length record": data[:first] + b"\x00\x00\x00\x00" + data[first:],
            "record past EOF": data[:-4] + b"\x00\x40\x04\x00",
        }
        for name, blob in cases.items():
            with self.subTest(name):
                bad = self.tmp / "bad.gds"
                bad.write_bytes(blob)
                with self.assertRaises(ValueError):
                    chk.gds_layers(bad)
        # and the gate turns that into a failure, not a "layer absent" pass
        gds = self.lvs / "pll_loop_filter.gds"
        gds.unlink()
        gds.write_bytes(data[: len(data) // 2])
        self.edit(self.rep("loop_filter"), lambda d: d["provenance"]["input"].update(content_hash=sha(gds)))
        self.edit(self.lvs / "lvs.loop_filter.json",
                  lambda d: d["response"]["provenance"]["input"].update(content_hash=sha(gds)))
        self.assertEqual(self.run_main(), 1, "truncated GDS must not justify the disclosure")

    def test_mos_block_without_deck(self):
        """Re-running a MOS block without --deck (resistor bodies as wires) fails."""
        for b in ("pfd", "cp", "vco", "lock_detector"):
            with self.subTest(b):
                self.setUp()
                self.edit(self.rep(b), lambda d: d["provenance"].update(deck=None, devices=[]))
                self.assertEqual(self.run_main(), 1)

    def test_mos_block_wrong_deck(self):
        self.edit(self.rep("cp"), lambda d: d["provenance"]["deck"].update(name="sg13g2"))
        self.assertEqual(self.run_main(), 1, "another deck")
        self.setUp()
        self.edit(self.rep("cp"), lambda d: d["provenance"]["deck"].update(content_hash="sha256:" + "3" * 64))
        self.assertEqual(self.run_main(), 1, "deck content hash drifted from the pin")

    def test_resistor_bodies_not_carved(self):
        for b, name in (("vco", "rppd"), ("vco", "rhigh"), ("lock_detector", "rhigh")):
            with self.subTest(f"{b}/{name} missing"):
                self.setUp()
                self.edit(self.rep(b), lambda d: d["provenance"].update(
                    devices=[x for x in d["provenance"]["devices"] if x["name"] != name]))
                self.assertEqual(self.run_main(), 1)
            with self.subTest(f"{b}/{name} zero area"):
                self.setUp()
                self.edit(self.rep(b), lambda d: [x.update(body_area_um2=0.0)
                                                   for x in d["provenance"]["devices"] if x["name"] == name])
                self.assertEqual(self.run_main(), 1)

    def test_loop_filter_run_form(self):
        self.edit(self.rep("loop_filter"), lambda d: d["provenance"].update(
            deck={"name": "sg13cmos5l", "content_hash": chk.MOS_DECK["content_hash"], "released": True}))
        self.assertEqual(self.run_main(), 1, "gate-less block reported as run with a deck")
        self.setUp()
        self.edit(self.rep("loop_filter"), lambda d: d["gates"][0].update(net="NZ,VCTRL,VSS"))
        self.assertEqual(self.run_main(), 1, "the uncarved 'gate' net touches VSS")
        self.setUp()
        self.edit(self.rep("loop_filter"), lambda d: d["gates"][0].update(net="vss"))
        self.assertEqual(self.run_main(), 1, "supply match is case-insensitive")
        self.setUp()
        self.edit(self.rep("loop_filter"), lambda d: d.update(gates=[]))
        self.assertEqual(self.run_main(), 1, "no gates[] to verify")

    def test_spec_drift(self):
        """A spec edited after the run no longer matches the report's spec hash."""
        self.edit(self.specs / "erc-supply-spec.pll_vco.json", lambda d: d["ties"].pop())
        self.assertEqual(self.run_main(), 1)

    def test_spec_content_rules(self):
        """Spec rules hold even when the report's spec hash is made consistent."""
        cases = {
            "wrong rails": lambda d: d["nets"].pop(),
            "island count": lambda d: d["nets"][0].update(expected_islands=2),
            "tie on wrong net": lambda d: d["ties"][1].update(net="VDD"),
            "no narrowing": lambda d: d["ties"][0].update(tap_requires=[]),
        }
        for name, fn in cases.items():
            with self.subTest(name):
                self.setUp()
                spec = self.specs / "erc-supply-spec.pll_lock_detector.json"
                self.edit(spec, fn)
                self.edit(self.rep("lock_detector"),
                          lambda d: d["provenance"]["spec"].update(content_hash=sha(spec)))
                self.assertEqual(self.run_main(), 1)

    def test_manifest_citation(self):
        self.edit(self.manifest, lambda d: d["evidence"].pop("11.analog"))
        self.assertEqual(self.run_main(), 1, "met claim with no 11.analog citation")
        self.setUp()
        self.edit(self.manifest, lambda d: d["evidence"]["11.analog"][1].update(
            content_hash="sha256:" + "2" * 64))
        self.assertEqual(self.run_main(), 1, "lvs part pinned to another revision")
        self.setUp()
        self.edit(self.manifest, lambda d: d["evidence"]["11.analog"][1].pop("pointer"))
        self.assertEqual(self.run_main(), 1, "lvs part without /response pointer")


if __name__ == "__main__":
    unittest.main()
