"""Writing of results: CSV tables, summary JSON, GeoJSON and a standalone HTML report."""

from __future__ import annotations

import json
import math
from importlib import resources
from pathlib import Path

import numpy as np
import pandas as pd

from .statuses import STATUS_INFO


def _clean(value):
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        v = float(value)
        return None if math.isnan(v) else v
    if value is pd.NA:
        return None
    return value


def _records(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def _finite(*values) -> bool:
    return all(v is not None and isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def build_geojson(result) -> dict:
    features: list[dict] = []

    def point(lat, lon, props):
        if _finite(lat, lon):
            features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props})

    def line(coords, props):
        if all(_finite(lat, lon) for lat, lon in coords):
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in coords]},
                    "properties": props,
                }
            )

    for p in _records(result.photos):
        lat = p["lat_corrected"] if p.get("valid") else p["lat"]
        lon = p["lon_corrected"] if p.get("valid") else p["lon"]
        point(lat, lon, {"kind": "photo", **p})
    for a in _records(result.addresses):
        point(a.get("lat"), a.get("lon"), {"kind": "address", **a})
    plate_pos = {}
    for p in _records(result.plates):
        plate_pos[p["plate_id"]] = (p["lat"], p["lon"])
        point(p["lat"], p["lon"], {"kind": "plate", **p})
        if p.get("official_lat") is not None and p.get("status") in ("WRONG_SIDE", "OUT_OF_PLACE", "UNCERTAIN"):
            line(
                [(p["lat"], p["lon"]), (p["official_lat"], p["official_lon"])],
                {"kind": "link", "plate_id": p["plate_id"], "status": p.get("status")},
            )
    for d in _records(result.detections):
        target = plate_pos.get(d.get("plate_id"))
        if target and d.get("used"):
            line(
                [(d["cam_lat"], d["cam_lon"]), target],
                {"kind": "ray", "plate_id": d["plate_id"], "det_id": d["det_id"], "sequence_number": d["sequence_number"], "view": d["view"]},
            )
    return {"type": "FeatureCollection", "features": features}


def render_html(result, geojson: dict | None = None) -> str:
    template = (resources.files("plateverif") / "templates" / "report.html").read_text(encoding="utf-8")
    payload = {
        "summary": result.summary,
        "statuses": STATUS_INFO,
        "geojson": geojson if geojson is not None else build_geojson(result),
        "expected": _records(result.expected_views),
    }
    data = json.dumps(payload, ensure_ascii=False, default=str).replace("</", "<\\/")
    return template.replace("__REPORT_DATA__", data)


def write_outputs(result, out_dir: str | Path, html: bool = True) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    tables = {
        "addresses": result.addresses,
        "plates": result.plates,
        "detections": result.detections,
        "photos": result.photos,
        "expected_views": result.expected_views,
    }
    for name, df in tables.items():
        path = out / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        paths[name] = path
    paths["summary"] = out / "summary.json"
    paths["summary"].write_text(json.dumps(result.summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    geojson = build_geojson(result)
    paths["geojson"] = out / "results.geojson"
    paths["geojson"].write_text(json.dumps(geojson, ensure_ascii=False, default=str), encoding="utf-8")
    if html:
        paths["report"] = out / "report.html"
        paths["report"].write_text(render_html(result, geojson), encoding="utf-8")
    return paths
