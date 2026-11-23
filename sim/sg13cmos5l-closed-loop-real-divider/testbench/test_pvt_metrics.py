#!/usr/bin/env python3
"""Pins pvt_metrics.grade_unit's failing-block attribution (issue #516 review).

    python3 -I test_pvt_metrics.py
"""
import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("pvt_metrics", HERE / "pvt_metrics.py")
pm = importlib.util.module_from_spec(_s)
_s.loader.exec_module(pm)

T = pm.TREF


def mv(fb_drift, vc_max=1.2, vc_min=1.1, n_per_fb=64):
    """Synthetic crossings: ref every T_ref; fb every T_ref*(1+fb_drift) so a
    drifting loop never dual-locks; clk n_per_fb edges per fb period from the
    first fb edge at/after CLK_FROM_S, preceded by a partial first period."""
    ref = [i * T for i in range(1, 100)]
    fb = [i * T * (1 + fb_drift) for i in range(1, 100)]
    clk = []
    for a, b in zip(fb[:-1], fb[1:]):
        k = 57 if b - a and a < pm.CLK_FROM_S <= b else n_per_fb
        clk += [a + (b - a) * j / k for j in range(k)]
    return {"t_ref": {"times": ref}, "t_fb": {"times": fb},
            "t_clk": {"times": sorted(clk)}, "vc_max": vc_max, "vc_min": vc_min}


class FailingBlock(unittest.TestCase):
    def test_partial_first_period_is_not_a_miscount(self):
        g = pm.grade_unit(mv(0.2, vc_max=3.2))      # unlocked, rail-pinned, all-64
        self.assertEqual(g["lock_verdict"], "not_locked")
        self.assertIn("57", g["clk_per_fb_period_hist"])
        self.assertIn("high rail", g["failing_block"])

    def test_rail_scales_with_the_unit_supply(self):
        hi = pm.grade_unit(mv(0.2, vc_max=3.5), 3.6)["failing_block"]
        mid = pm.grade_unit(mv(0.2, vc_max=3.0), 3.6)["failing_block"]
        self.assertIn("high rail", hi)
        self.assertIn("not isolated", mid)

    def test_real_miscount_is_attributed_to_the_divider(self):
        g = pm.grade_unit(mv(0.2, n_per_fb=63))
        self.assertIn("divider_chain", g["failing_block"])


if __name__ == "__main__":
    unittest.main()
