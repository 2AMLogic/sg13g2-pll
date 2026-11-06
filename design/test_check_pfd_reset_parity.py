#!/usr/bin/env python3
"""Tests for check_pfd_reset_parity.py (#297). Run: python3 design/test_check_pfd_reset_parity.py"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_pfd_reset_parity as chk  # noqa: E402

ROOT = HERE.parent
BEFORE = ROOT / "sim/sg13g2-pfd-reset-parity/netlist-snapshots/pfd_before.spice"


class ResetParity(unittest.TestCase):
    def mutated(self, src, fn):
        text = fn(Path(src).read_text())
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "pfd.spice"
        p.write_text(text)
        return p

    def test_committed_netlists_pass(self):
        for p in chk.DEFAULT_NETLISTS:
            with self.subTest(p=str(p)):
                self.assertEqual(chk.check(p) % 2, 1)

    def test_before_snapshot_rejected_with_even_count(self):
        with self.assertRaisesRegex(chk.ParityError, r"even inverter count \(2\)"):
            chk.check(BEFORE)

    def test_removing_xi1b_rejected(self):
        for src in chk.DEFAULT_NETLISTS:
            with self.subTest(src=str(src)):
                def drop(t):
                    t = re.sub(r"^XI1B .*\n", "", t, flags=re.M)
                    return t.replace("XI2 reset_d2 reset", "XI2 reset_d1 reset")
                with self.assertRaises(chk.ParityError):
                    chk.check(self.mutated(src, drop))

    def test_swapped_nand_input_rejected(self):
        src = chk.DEFAULT_NETLISTS[0]
        p = self.mutated(src, lambda t: t.replace("XNR UP DN", "XNR UP REF"))
        with self.assertRaises(chk.ParityError):
            chk.check(p)

    def test_split_reset_nets_rejected(self):
        src = chk.DEFAULT_NETLISTS[0]
        p = self.mutated(src, lambda t: t.replace("XLD set_dn reset", "XLD set_dn resetx"))
        with self.assertRaisesRegex(chk.ParityError, "different nets"):
            chk.check(p)

    def test_non_inverter_in_chain_rejected(self):
        src = chk.DEFAULT_NETLISTS[0]
        p = self.mutated(src, lambda t: t.replace(
            "XI1B reset_d1 reset_d2 VDD VSS inv_hv",
            "XI1B reset_d1 reset_d2 VDD VSS nand2_hv"))
        with self.assertRaises(chk.ParityError):
            chk.check(p)

    def test_continuation_lines(self):
        src = chk.DEFAULT_NETLISTS[0]
        p = self.mutated(src, lambda t: t.replace(
            "XI1 reset_raw reset_d1 VDD VSS inv_hv",
            "XI1 reset_raw reset_d1\n+ VDD VSS inv_hv"))
        self.assertEqual(chk.check(p), 3)


if __name__ == "__main__":
    unittest.main()
