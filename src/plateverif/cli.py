"""Command-line interface: python -m plateverif <command> ..."""

from __future__ import annotations

import argparse
import functools
import http.server
import sys
import threading
import webbrowser
from importlib import resources
from pathlib import Path

from ._version import __version__
from .config import load_config
from .errors import PlateVerifError
from .metadata import load_metadata
from .report import write_outputs
from .statuses import label
from .verify import run_verification

TEMPLATE_COLUMNS = ["image", "x_min", "y_min", "x_max", "y_max", "image_width", "image_height", "text", "source"]


def _print_result(result, paths) -> None:
    s = result.summary
    print(f"Photos: {s['photos']['usable']} usable / {s['photos']['total']} (skipped {s['photos']['skipped']})")
    if result.mode == "verify":
        print(f"Detections: {s['detections']['used']} used / {s['detections']['total']}; plates: {s['plates']['total']}")
        cal = s["calibration"]
        if cal.get("applied"):
            print(f"GPS offset corrected: {cal['offset_m']} m (east {cal['offset_east_m']}, north {cal['offset_north_m']}, {cal['anchors']} anchors)")
        else:
            print(f"GPS offset not corrected: {cal.get('reason', '')}")
    print(f"Addresses reported: {s['addresses']['reported']}")
    for status, n in sorted(s["addresses"]["by_status"].items(), key=lambda kv: -kv[1]):
        print(f"  {label(status):<18} {n}")
    for warning in s["warnings"]:
        print(f"Warning: {warning}")
    print("Outputs:")
    for name, path in paths.items():
        print(f"  {name:<15} {path}")


def _config(args, extra=None):
    overrides = {}
    if getattr(args, "no_calibration", False):
        overrides["calibration"] = {"enabled": False}
    if extra:
        overrides.update(extra)
    return load_config(getattr(args, "config", None), overrides or None)


def cmd_verify(args) -> int:
    cfg = _config(args)
    result = run_verification(
        args.metadata, args.addresses, args.detections, cfg, reviewed=args.reviewed, images_root=args.images_root
    )
    paths = write_outputs(result, args.out, html=not args.no_html)
    _print_result(result, paths)
    return 0


def cmd_inspect(args) -> int:
    cfg = _config(args)
    result = run_verification(args.metadata, args.addresses, None, cfg)
    paths = write_outputs(result, args.out, html=not args.no_html)
    _print_result(result, paths)
    return 0


def cmd_template(args) -> int:
    cfg = _config(args)
    meta = load_metadata(args.metadata, cfg)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "detections_template.csv").write_text(",".join(TEMPLATE_COLUMNS) + "\n", encoding="utf-8")
    valid = meta.photos.loc[meta.photos["valid"], "picture_id"]
    crops = meta.views[meta.views["view"].isin(cfg.photos.coverage_views) & meta.views["picture_id"].isin(valid)]
    crops = crops[["sequence_number", "picture_id", "view", "file"]].rename(columns={"file": "image"})
    crops.to_csv(out / "crops_to_annotate.csv", index=False, encoding="utf-8-sig")
    skipped = meta.photos[~meta.photos["valid"]]
    print(f"Wrote {out / 'detections_template.csv'}")
    print(f"Wrote {out / 'crops_to_annotate.csv'} ({len(crops)} crops from {len(valid)} usable photos)")
    if len(skipped):
        print(f"{len(skipped)} photo(s) skipped, e.g. photo {int(skipped.iloc[0]['sequence_number'])}: {skipped.iloc[0]['skip_reason']}")
    return 0


def cmd_demo(args) -> int:
    from .demo import make_demo

    out = Path(args.out)
    paths = make_demo(out / "data", seed=args.seed)
    cfg = load_config()
    result = run_verification(paths["metadata"], paths["addresses"], paths["detections"], cfg)
    result.summary["demo"] = True
    written = write_outputs(result, out / "results")
    print("SYNTHETIC DEMO: the photos and detections are generated; only the address register is real.")
    _print_result(result, written)
    return 0


def _resolve_report(path) -> tuple[Path, str]:
    """Return (folder to serve, page name) for a results folder or a report file."""
    p = Path(path).resolve()
    if p.is_file():
        return p.parent, p.name
    for candidate in (p / "report.html", p / "results" / "report.html"):
        if candidate.is_file():
            return candidate.parent, candidate.name
    raise PlateVerifError(f"No report.html found in {p}. Run verify, inspect or demo first.")


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - signature defined by the base class
        pass


def cmd_serve(args) -> int:
    folder, page = _resolve_report(args.path)
    handler = functools.partial(_QuietHandler, directory=str(folder))
    try:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as exc:
        raise PlateVerifError(f"Cannot use port {args.port} ({exc}). Try another one, for example --port 8090.") from exc
    url = f"http://localhost:{httpd.server_address[1]}/{page}"
    print(f"Serving {folder}")
    print(f"Open {url}  (press Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        httpd.server_close()
    return 0


def cmd_show_config(_args) -> int:
    print((resources.files("plateverif") / "default_config.toml").read_text(encoding="utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plateverif",
        description="Verify house-number plates seen in street photos against the official address register.",
    )
    parser.add_argument("--version", action="version", version=f"plateverif {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    v = sub.add_parser("verify", help="compare plate detections with the official addresses")
    v.add_argument("--metadata", required=True, help="photo metadata (csv, json or geojson)")
    v.add_argument("--addresses", required=True, help="official addresses (Paris adresse_paris CSV)")
    v.add_argument("--detections", required=True, help="plate detections CSV (manual or model)")
    v.add_argument("--reviewed", help="CSV of crops that were checked, including crops with no plate")
    v.add_argument("--images-root", help="crops folder, only needed when image sizes are not in the CSV")
    v.add_argument("--config", help="TOML file with settings to override")
    v.add_argument("--no-calibration", action="store_true", help="do not correct a constant GPS offset")
    v.add_argument("--out", default="results", help="output folder (default: results)")
    v.add_argument("--no-html", action="store_true", help="skip the HTML report")
    v.set_defaults(func=cmd_verify)

    i = sub.add_parser("inspect", help="list the addresses each crop should show (no detections needed)")
    i.add_argument("--metadata", required=True)
    i.add_argument("--addresses", required=True)
    i.add_argument("--config")
    i.add_argument("--out", default="inspection")
    i.add_argument("--no-html", action="store_true")
    i.set_defaults(func=cmd_inspect)

    t = sub.add_parser("template", help="write an empty detections file and the list of crops to annotate")
    t.add_argument("--metadata", required=True)
    t.add_argument("--config")
    t.add_argument("--out", default="annotation")
    t.set_defaults(func=cmd_template)

    d = sub.add_parser("demo", help="generate the synthetic demo and verify it")
    d.add_argument("--out", default="demo")
    d.add_argument("--seed", type=int, default=7)
    d.set_defaults(func=cmd_demo)

    s = sub.add_parser("serve", help="open a report through a small local web server (needed for the OpenStreetMap map)")
    s.add_argument("path", nargs="?", default="results", help="results folder or report.html (default: results)")
    s.add_argument("--port", type=int, default=8088, help="port on this computer (default: 8088)")
    s.add_argument("--no-browser", action="store_true", help="do not open the browser automatically")
    s.set_defaults(func=cmd_serve)

    c = sub.add_parser("show-config", help="print the default settings")
    c.set_defaults(func=cmd_show_config)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except PlateVerifError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
