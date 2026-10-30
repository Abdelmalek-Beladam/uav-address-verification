import json
import re
import tempfile
import unittest
from importlib import resources
from pathlib import Path

from plateverif.cli import _resolve_report, build_parser
from plateverif.demo import make_demo
from plateverif.errors import PlateVerifError
from plateverif.report import write_outputs
from plateverif.verify import run_verification


def _template() -> str:
    return (resources.files("plateverif") / "templates" / "report.html").read_text(encoding="utf-8")


class TemplateTests(unittest.TestCase):
    def test_map_sources(self):
        html = _template()
        self.assertIn("__REPORT_DATA__", html)
        self.assertNotIn("cartocdn", html)
        self.assertNotIn("key=", html)
        self.assertIn("tile.openstreetmap.org", html)
        self.assertIn("World_Street_Map", html)
        self.assertIn("World_Imagery", html)
        self.assertIn("location.protocol === 'file:'", html)
        self.assertIn("OpenStreetMap</a> contributors", html)

    def test_rendered_report_contains_valid_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_demo(Path(tmp) / "data")
            result = run_verification(paths["metadata"], paths["addresses"], paths["detections"])
            out = write_outputs(result, Path(tmp) / "results")
            html = Path(out["report"]).read_text(encoding="utf-8")
        match = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        kinds = {f["properties"]["kind"] for f in data["geojson"]["features"]}
        self.assertTrue({"photo", "address", "plate", "ray"} <= kinds)
        self.assertIn("CORRECT", data["statuses"])
        self.assertTrue(data["summary"]["plates"]["by_status"])


class ServeTests(unittest.TestCase):
    def test_resolve_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            (root / "results" / "report.html").write_text("x", encoding="utf-8")
            self.assertEqual(_resolve_report(root / "results"), ((root / "results").resolve(), "report.html"))
            self.assertEqual(_resolve_report(root), ((root / "results").resolve(), "report.html"))
            self.assertEqual(_resolve_report(root / "results" / "report.html")[1], "report.html")
            with self.assertRaises(PlateVerifError):
                _resolve_report(root / "missing")

    def test_parser(self):
        args = build_parser().parse_args(["serve", "demo", "--port", "9001", "--no-browser"])
        self.assertEqual((args.path, args.port, args.no_browser), ("demo", 9001, True))
        self.assertEqual(build_parser().parse_args(["serve"]).path, "results")


if __name__ == "__main__":
    unittest.main()
