import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from plateverif.addresses import load_addresses
from plateverif.cli import main
from plateverif.demo import DEMO_STREET_ID, EXPECTED_STATUS, extract_path, make_demo
from plateverif.report import write_outputs
from plateverif.statuses import Status
from plateverif.verify import run_verification


class AddressTests(unittest.TestCase):
    def test_paris_extract(self):
        pins = load_addresses(extract_path())
        street = pins[pins["street_id"] == DEMO_STREET_ID]
        self.assertEqual(len(street), 29)
        self.assertIn("RUE DES GRANDS AUGUSTINS", street["street_name"].iloc[0])
        five = street[street["key"] == "5"].iloc[0]
        self.assertAlmostEqual(five["facade_bearing_deg"], 300.0, delta=15.0)
        self.assertTrue(bool(street[street["key"] == "1"].iloc[0]["is_corner"]))


class DemoPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.paths = make_demo(Path(cls.tmp.name) / "data")
        cls.truth = json.loads(Path(cls.paths["truth"]).read_text())
        cls.result = run_verification(cls.paths["metadata"], cls.paths["addresses"], cls.paths["detections"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def street_rows(self):
        a = self.result.addresses
        return a[a["street_id"].astype(str) == DEMO_STREET_ID].set_index("number")

    def test_injected_errors_found(self):
        rows = self.street_rows()
        for number, expected in EXPECTED_STATUS.items():
            self.assertEqual(rows.loc[number, "status"], expected, f"number {number}")

    def test_no_false_alarm_on_street(self):
        rows = self.street_rows()
        others = rows[~rows.index.isin(list(EXPECTED_STATUS))]
        self.assertGreaterEqual(len(others), 15)
        self.assertTrue(set(others["status"]) <= {Status.CORRECT, Status.NOT_COVERED}, others["status"].value_counts())

    def test_misread_frame_outvoted(self):
        rows = self.street_rows()
        plate_id = rows.loc["17", "plates"]
        plate = self.result.plates.set_index("plate_id").loc[plate_id]
        self.assertEqual(plate["reading"], "17")

    def test_extra_plate(self):
        plates = self.result.plates
        extra = plates[plates["reading"] == self.truth["extra_plate"]["text"]]
        self.assertEqual(len(extra), 1)
        self.assertEqual(extra.iloc[0]["status"], Status.NO_ADDRESS_NEARBY)

    def test_far_photo_skipped(self):
        photos = self.result.photos.set_index("sequence_number")
        self.assertFalse(bool(photos.loc[1, "valid"]))
        self.assertIn("from the street", photos.loc[1, "skip_reason"])
        self.assertEqual(int(photos["valid"].sum()), len(photos) - 1)

    def test_gps_offset_recovered(self):
        cal = self.result.summary["calibration"]
        self.assertTrue(cal["applied"])
        bias_e, bias_n = self.truth["gps_bias_east_north_m"]
        self.assertLess(abs(cal["offset_east_m"] + bias_e), 1.0)
        self.assertLess(abs(cal["offset_north_m"] + bias_n), 1.0)

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as out:
            paths = write_outputs(self.result, out)
            for path in paths.values():
                self.assertTrue(Path(path).exists(), path)
            html = Path(paths["report"]).read_text(encoding="utf-8")
            self.assertNotIn("__REPORT_DATA__", html)
            geo = json.loads(Path(paths["geojson"]).read_text(encoding="utf-8"))
            kinds = {f["properties"]["kind"] for f in geo["features"]}
            self.assertTrue({"photo", "address", "plate", "ray"} <= kinds)
            df = pd.read_csv(paths["addresses"])
            self.assertEqual(len(df), len(self.result.addresses))

    def test_inspect_mode(self):
        result = run_verification(self.paths["metadata"], self.paths["addresses"])
        self.assertEqual(set(result.addresses["status"]), {Status.IN_VIEW})
        self.assertGreater(len(result.expected_views), 20)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as out:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main(["template", "--metadata", str(self.paths["metadata"]), "--out", out]), 0)
                self.assertEqual(
                    main(["verify", "--metadata", str(self.paths["metadata"]), "--addresses", str(self.paths["addresses"]),
                          "--detections", str(self.paths["detections"]), "--out", out, "--no-html"]),
                    0,
                )
            self.assertTrue((Path(out) / "crops_to_annotate.csv").exists())
            self.assertTrue((Path(out) / "addresses.csv").exists())
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = main(["verify", "--metadata", str(Path(out) / "missing.csv"), "--addresses", str(self.paths["addresses"]),
                             "--detections", str(self.paths["detections"]), "--out", out])
            self.assertEqual(code, 2)
            self.assertIn("Error", err.getvalue())


if __name__ == "__main__":
    unittest.main()
