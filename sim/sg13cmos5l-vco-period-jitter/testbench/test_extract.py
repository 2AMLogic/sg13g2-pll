#!/usr/bin/env python3
"""Offline unit tests for sim/sg13cmos5l-vco-period-jitter/testbench/extract.py (#553).

    python3 -I sim/sg13cmos5l-vco-period-jitter/testbench/test_extract.py
"""
import csv
import importlib.util
import math
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
EXTRACT = HERE / "extract.py"

_spec = importlib.util.spec_from_file_location("extract", EXTRACT)
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)


def _freq_grid(n=121):
    # 100 kHz .. 100 GHz (6 decades, 20 pts/dec -> 121 points >= 100)
    return [1e5 * (10.0 ** (6.0 * i / (n - 1))) for i in range(n)]


def _make_cal_logs(trip_line="v(sout) = 1.361047e+00",
                   extra_dev_line=None,
                   bad_table_row=None,
                   n_freq=121):
    freqs = _freq_grid(n_freq)
    nz_lines = []
    if trip_line is not None:
        nz_lines.append(trip_line)
    nz_lines += ["v(sin1) = 1.361047e+00", "", "Index\tfrequency\tonoise_spectrum"]
    for idx, f in enumerate(freqs):
        if bad_table_row is not None and idx == 5:
            nz_lines.append(bad_table_row)
        else:
            nz_lines.append(f"{idx}\t{f:.15e}\t3.400000000000000e-09")
    nz_lines += [
        "",
        "onoise_total = 2.885483e-03",
        "onoise_total_n.xs1.xmn.nsg13_hv_nmos = 1.900000e-03",
        "onoise_total_n.xs1.xmn.nsg13_hv_nmos_idid = 1.800000e-03",
        "onoise_total_n.xs1.xmn.nsg13_hv_nmos_flicker = 3.000000e-04",
        "onoise_total_n.xs1.xmn.nsg13_hv_nmos_gate = 5.000000e-04",
    ]
    if extra_dev_line is not None:
        nz_lines.append(extra_dev_line)

    ac_lines = ["Index\tfrequency\tv(sout)"]
    for idx, f in enumerate(freqs):
        ac_lines.append(f"{idx}\t{f:.15e}\t1.000000000000000e+03,\t0.000000000000000e+00")

    sw_lines = ["Index\tv-sweep\tv(sout)"]
    for idx in range(21):
        vin = 1.31 + idx * 0.005
        vout = 1.361047 - 15.6075 * (vin - 1.361047)
        sw_lines.append(f"{idx}\t{vin:.15e}\t{vout:.15e}")

    return "\n".join(nz_lines) + "\n", "\n".join(ac_lines) + "\n", "\n".join(sw_lines) + "\n"


def _write_unit(outdir, uid, text):
    p = outdir / "out" / uid
    p.mkdir(parents=True, exist_ok=True)
    (p / "stdout.bin").write_text(text)


def _seed_corners(corners):
    corners.mkdir(parents=True, exist_ok=True)
    sentinels = {
        "calibration_bias.csv": b"SENTINEL_BIAS\n",
        "calibration_noise.csv": b"SENTINEL_NOISE\n",
        "calibration_devices.csv": b"SENTINEL_DEVICES\n",
        "calibration_fit.csv": b"SENTINEL_FIT\n",
    }
    for name, data in sentinels.items():
        (corners / name).write_bytes(data)
    return sentinels


def _snapshot_dir(d):
    return {p.name: p.read_bytes() for p in sorted(d.iterdir()) if p.is_file()}


def _run_extract(*args):
    return subprocess.run(
        [sys.executable, "-I", str(EXTRACT), *map(str, args)],
        capture_output=True,
        text=True,
    )


class ExtractCalibrationTests(unittest.TestCase):
    def test_valid_cal_writes_expected_csvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cal_dir, corners = root / "cal", root / "corners"
            nz, ac, sw = _make_cal_logs()
            _write_unit(cal_dir, "cal_noise", nz)
            _write_unit(cal_dir, "cal_ac", ac)
            _write_unit(cal_dir, "cal_dcsweep", sw)

            proc = _run_extract("cal", cal_dir, corners)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stderr, "")
            sigma = float(proc.stdout.strip())
            self.assertTrue(math.isfinite(sigma) and sigma > 0)

            with open(corners / "calibration_fit.csv") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["trip_v"], "1.361047e+00")
            self.assertEqual(rows[0]["ss_gain_v_per_v"], "15.6075")
            expected_sub = math.sqrt(1.8e-3 ** 2 + 3.0e-4 ** 2 + 5.0e-4 ** 2)
            self.assertEqual(rows[0]["onoise_subcomponent_quadrature_v"], f"{expected_sub:.6e}")

            with open(corners / "calibration_devices.csv") as f:
                devs = {r["name"]: r["class"] for r in csv.DictReader(f)}
            self.assertEqual(devs["n.xs1.xmn.nsg13_hv_nmos"], "excluded_aggregate")
            self.assertEqual(devs["n.xs1.xmn.nsg13_hv_nmos_idid"], "thermal")
            self.assertEqual(devs["n.xs1.xmn.nsg13_hv_nmos_flicker"], "flicker")
            self.assertEqual(devs["n.xs1.xmn.nsg13_hv_nmos_gate"], "other")

    def test_bad_or_missing_trip_point_fails_closed_and_preserves_csvs(self):
        cases = [
            ("missing", None),
            ("nan", "v(sout) = nan"),
            ("neg_nan", "v(sout) = -NaN"),
            ("inf", "v(sout) = inf"),
            ("neg_inf", "v(sout) = -inf"),
            ("failed", "v(sout) = failed"),
            ("empty_val", "v(sout) = "),
            ("trailing_tokens", "v(sout) = 1.361047 extra"),
        ]
        for label, trip_line in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                cal_dir, corners = root / "cal", root / "corners"
                before = _seed_corners(corners)
                nz, ac, sw = _make_cal_logs(trip_line=trip_line)
                _write_unit(cal_dir, "cal_noise", nz)
                _write_unit(cal_dir, "cal_ac", ac)
                _write_unit(cal_dir, "cal_dcsweep", sw)

                proc = _run_extract("cal", cal_dir, corners)
                self.assertEqual(proc.returncode, 1, f"{label}: stderr={proc.stderr!r}")
                self.assertIn(
                    "extract.py: could not parse the trip point v(sout) from cal_noise stdout",
                    proc.stderr,
                )
                self.assertNotIn("Traceback", proc.stderr)
                self.assertNotIn("ValueError", proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(_snapshot_dir(corners), before)

    def test_zero_volt_trip_point_is_accepted_and_not_rendered_na(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cal_dir, corners = root / "cal", root / "corners"
            nz, ac, sw = _make_cal_logs(trip_line="v(sout) = 0.0")
            _write_unit(cal_dir, "cal_noise", nz)
            _write_unit(cal_dir, "cal_ac", ac)
            _write_unit(cal_dir, "cal_dcsweep", sw)

            proc = _run_extract("cal", cal_dir, corners)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(corners / "calibration_fit.csv") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["trip_v"], "0.000000e+00")

    def test_other_cal_parse_failures_preserve_existing_csvs(self):
        bad_inputs = [
            ("short_table", dict(n_freq=10)),
            ("bad_dev_nan", dict(extra_dev_line="onoise_total_n.xs1.xmp.nsg13_hv_pmos_idid = nan")),
            ("bad_dev_failed", dict(extra_dev_line="onoise_total_n.xs1.xmp.nsg13_hv_pmos_idid = failed")),
            ("bad_table_nan", dict(bad_table_row="5\t1.0e+06\tnan")),
            ("bad_table_str", dict(bad_table_row="5\t1.0e+06\tfailed")),
        ]
        for label, kw in bad_inputs:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                cal_dir, corners = root / "cal", root / "corners"
                before = _seed_corners(corners)
                nz, ac, sw = _make_cal_logs(**kw)
                _write_unit(cal_dir, "cal_noise", nz)
                _write_unit(cal_dir, "cal_ac", ac)
                _write_unit(cal_dir, "cal_dcsweep", sw)

                proc = _run_extract("cal", cal_dir, corners)
                self.assertEqual(proc.returncode, 1, f"{label}: stderr={proc.stderr!r}")
                self.assertIn("extract.py:", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(_snapshot_dir(corners), before)

    def test_repeated_device_names_are_all_preserved(self):
        dup = "onoise_total_n.xs1.xmn.nsg13_hv_nmos_flicker"
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cal_dir, corners = root / "cal", root / "corners"
            nz, ac, sw = _make_cal_logs(extra_dev_line=f"{dup} = 4.000000e-04")
            _write_unit(cal_dir, "cal_noise", nz)
            _write_unit(cal_dir, "cal_ac", ac)
            _write_unit(cal_dir, "cal_dcsweep", sw)
            proc = _run_extract("cal", cal_dir, corners)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(corners / "calibration_devices.csv") as f:
                rows = list(csv.DictReader(f))
            flick = [r["onoise_total_v"] for r in rows
                     if r["name"] == dup[len("onoise_total_"):]]
            self.assertEqual(flick, ["3.000000e-04", "4.000000e-04"])
            self.assertEqual(len(rows), 5)
            with open(corners / "calibration_fit.csv") as f:
                fit = next(csv.DictReader(f))
            self.assertEqual(fit["stage_flicker_rms_v"], f"{math.hypot(3e-4, 4e-4):.6e}")
            expected_sub = math.sqrt(1.8e-3 ** 2 + 3.0e-4 ** 2 + 4.0e-4 ** 2 + 5.0e-4 ** 2)
            self.assertEqual(fit["onoise_subcomponent_quadrature_v"], f"{expected_sub:.6e}")

    def test_malformed_noise_evidence_fails_closed_and_preserves_csvs(self):
        idid = "onoise_total_n.xs1.xmn.nsg13_hv_nmos_idid = 1.800000e-03"
        total = "onoise_total = 2.885483e-03"
        dump = [l for l in _make_cal_logs()[0].splitlines()
                if l.startswith("onoise_total_")]
        cases = [
            ("dev_empty_value", lambda t: t.replace(idid, "onoise_total_n.xs1.xmn.nsg13_hv_nmos_idid = ")),
            ("dev_extra_token", lambda t: t.replace(idid, idid + " extra")),
            ("dev_dump_missing", lambda t: "\n".join(
                l for l in t.splitlines() if l not in dump) + "\n"),
            ("total_failed", lambda t: t.replace(total, "onoise_total = failed")),
            ("total_nan", lambda t: t.replace(total, "onoise_total = nan")),
            ("total_missing", lambda t: t.replace(total + "\n", "")),
        ]
        for label, mutate in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                cal_dir, corners = root / "cal", root / "corners"
                before = _seed_corners(corners)
                nz, ac, sw = _make_cal_logs()
                mutated = mutate(nz)
                self.assertNotEqual(mutated, nz)
                _write_unit(cal_dir, "cal_noise", mutated)
                _write_unit(cal_dir, "cal_ac", ac)
                _write_unit(cal_dir, "cal_dcsweep", sw)
                proc = _run_extract("cal", cal_dir, corners)
                self.assertEqual(proc.returncode, 1, f"{label}: stderr={proc.stderr!r}")
                self.assertIn("extract.py:", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(_snapshot_dir(corners), before)

    def test_bias_rejects_nonfinite_and_malformed_readings_without_writing(self):
        for label, line in [
            ("missing", "v(vbp) = 1.77\n"),
            ("nan", "v(vbp) = nan\nv(vbn) = 1.34\n"),
            ("inf", "v(vbp) = 1.77\nv(vbn) = inf\n"),
            ("failed", "v(vbp) = failed\nv(vbn) = 1.34\n"),
        ]:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                bias_dir, corners = root / "bias", root / "corners"
                before = _seed_corners(corners)
                _write_unit(bias_dir, "bias_op", line)

                proc = _run_extract("bias", bias_dir, corners)
                self.assertEqual(proc.returncode, 1)
                self.assertIn("extract.py: could not parse v(vbp)/v(vbn)", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(_snapshot_dir(corners), before)

    def test_crossings_rejects_failed_and_nonfinite_meas_tokens(self):
        lines = [f"tc{k} = {k * 1.5e-9:.12e}" for k in range(ex.FIRST, ex.LAST + 1)]
        lines[0] = f"tc{ex.FIRST} = failed"
        with self.assertRaises(SystemExit) as ctx:
            ex.crossings("\n".join(lines), "ring_s42_t10p")
        self.assertIn("1 crossings missing", str(ctx.exception))

        lines[0] = f"tc{ex.FIRST} = nan"
        with self.assertRaises(SystemExit) as ctx2:
            ex.crossings("\n".join(lines), "ring_s42_t10p")
        self.assertIn("1 crossings missing", str(ctx2.exception))

    def test_main_missing_calpsd_preserves_existing_csvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            main_dir, corners = root / "main", root / "corners"
            before = _seed_corners(corners)
            (corners / "calibration_noise.csv").write_text(
                "f_hz,onoise_v_rthz,z_out_ohm,si_eff_a_rthz\n"
                "1.000000e+08,3.400000e-09,1.000000e+03,3.400000e-12\n"
            )
            (corners / "period_jitter.csv").write_bytes(b"SENTINEL_JITTER\n")
            (corners / "crossing_digest.csv").write_bytes(b"SENTINEL_DIGEST\n")
            before = _snapshot_dir(corners)

            meta = {
                "units": {
                    "ring_s42_t10p": {
                        "seed": 42, "sigma_a": "7.68923e-07",
                        "ts_s": "1e-11", "tran_step_s": "10p",
                    },
                    "cal_tran_s42": {
                        "seed": 42, "sigma_a": "7.68923e-07",
                        "ts_s": "1e-11", "tran_step_s": "5p",
                    },
                }
            }
            main_dir.mkdir(parents=True, exist_ok=True)
            (main_dir / "decks_meta.json").write_text(__import__("json").dumps(meta))
            tc_lines = "\n".join(
                f"tc{k} = {k * 1.5e-9:.12e}" for k in range(ex.FIRST, ex.LAST + 1)
            )
            _write_unit(main_dir, "ring_s42_t10p", tc_lines + "\n")
            # Deliberately omit main_dir/out/cal_tran_s42/calpsd.txt

            proc = _run_extract("main", main_dir, corners)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("missing wrdata output", proc.stderr)
            self.assertEqual(_snapshot_dir(corners), before)


if __name__ == "__main__":
    unittest.main()
