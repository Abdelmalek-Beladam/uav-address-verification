import unittest
from importlib import resources

import numpy as np

from plateverif.config import Config, load_config
from plateverif.errors import ConfigError
from plateverif.geo import LocalFrame, bearing_deg, pixel_azimuth_offset, side_of, triangulate
from plateverif.textnorm import display_number, normalize_number


class GeoTests(unittest.TestCase):
    def test_frame_round_trip(self):
        frame = LocalFrame(48.8545, 2.3410)
        x, y = frame.to_xy(48.8555, 2.3425)
        lat, lon = frame.to_latlon(x, y)
        self.assertAlmostEqual(float(lat), 48.8555, places=9)
        self.assertAlmostEqual(float(lon), 2.3425, places=9)
        self.assertAlmostEqual(float(y), 111.2, delta=0.5)

    def test_pixel_offset(self):
        self.assertAlmostEqual(float(pixel_azimuth_offset(800, 600, 1600, 1200, 80, 0, "rectilinear")), 0.0, places=9)
        self.assertAlmostEqual(float(pixel_azimuth_offset(1600, 600, 1600, 1200, 80, 0, "rectilinear")), 40.0, places=6)
        self.assertAlmostEqual(float(pixel_azimuth_offset(0, 600, 1600, 1200, 80, 0, "rectilinear")), -40.0, places=6)
        self.assertAlmostEqual(float(pixel_azimuth_offset(800, 100, 1600, 1200, 80, -8, "rectilinear")), 0.0, places=9)
        self.assertAlmostEqual(float(pixel_azimuth_offset(1200, 600, 1600, 1200, 80, 0, "linear")), 20.0, places=9)

    def test_triangulation_recovers_point(self):
        target = np.array([5.0, 10.0])
        origins = np.array([[0.0, 0.0], [4.0, 0.0], [8.0, 0.0]])
        az = np.array([bearing_deg(*(target - o)) for o in origins], dtype=float)
        tri = triangulate(origins, az, 5.0)
        self.assertIsNotNone(tri)
        np.testing.assert_allclose(tri.point, target, atol=1e-6)
        self.assertLess(tri.rms, 1e-6)

    def test_parallel_rays_rejected(self):
        origins = np.array([[0.0, 0.0], [1.0, 0.0]])
        self.assertIsNone(triangulate(origins, np.array([0.0, 0.5]), 5.0))

    def test_side(self):
        cam = np.array([0.0, 0.0])
        self.assertGreater(side_of(np.array([[-5.0, 0.0]]), cam, 0.0)[0], 0)
        self.assertLess(side_of(np.array([[5.0, 0.0]]), cam, 0.0)[0], 0)


class TextTests(unittest.TestCase):
    def test_normalize(self):
        cases = {"12": "12", " 12 ": "12", "12 bis": "12b", "12BIS": "12b", "7 ter": "7t", "17 A": "17a",
                 "17a": "17a", "?": None, "": None, "illisible": None, "N/A": None, "abc": None}
        for raw, expected in cases.items():
            self.assertEqual(normalize_number(raw), expected, raw)

    def test_display(self):
        self.assertEqual(display_number("12b"), "12 bis")
        self.assertEqual(display_number("17a"), "17 A")
        self.assertEqual(display_number(None), "unreadable")


class ConfigTests(unittest.TestCase):
    def test_bundled_defaults_match_code(self):
        path = resources.files("plateverif") / "default_config.toml"
        self.assertEqual(load_config(str(path)), Config())

    def test_unknown_key_rejected(self):
        with self.assertRaises(ConfigError):
            load_config(None, {"matching": {"max_match_distanse_m": 3}})

    def test_override(self):
        cfg = load_config(None, {"calibration": {"enabled": False}})
        self.assertFalse(cfg.calibration.enabled)


if __name__ == "__main__":
    unittest.main()
