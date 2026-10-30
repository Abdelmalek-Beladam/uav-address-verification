"""Reading of CSV / JSON / GeoJSON tables with tolerant delimiter detection."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .errors import InputError


def file_basename(value) -> str:
    """File name without folders; accepts Windows and POSIX separators."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value).strip()
    if text.lower() in ("", "nan", "none"):
        return ""
    return text.replace("\\", "/").rsplit("/", 1)[-1]


def to_number(series) -> pd.Series:
    """Numeric conversion that also accepts decimal commas."""
    if not isinstance(series, pd.Series):
        series = pd.Series(series)
    if series.dtype == object or pd.api.types.is_string_dtype(series):
        series = series.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(series, errors="coerce").astype(float)


def column(df: pd.DataFrame, name: str, default=np.nan) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)


def _sniff_separator(first_line: str) -> str:
    counts = {sep: first_line.count(sep) for sep in (",", ";", "\t", "|")}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def read_table(source) -> pd.DataFrame:
    """Read a DataFrame, CSV/TSV (any common delimiter), JSON records or GeoJSON."""
    if isinstance(source, pd.DataFrame):
        return source.copy()
    path = Path(source)
    if not path.exists():
        raise InputError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix in (".json", ".geojson"):
        with open(path, encoding="utf-8-sig") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise InputError(f"Invalid JSON in {path}: {exc}") from exc
        if isinstance(data, dict) and data.get("type") == "FeatureCollection":
            rows = []
            for feature in data.get("features", []):
                props = dict(feature.get("properties") or {})
                geom = feature.get("geometry") or {}
                if geom.get("type") == "Point" and len(geom.get("coordinates", [])) >= 2:
                    props.setdefault("longitude", geom["coordinates"][0])
                    props.setdefault("latitude", geom["coordinates"][1])
                rows.append(props)
            return pd.DataFrame(rows)
        if isinstance(data, dict):
            for key in ("records", "data", "pictures", "items", "rows"):
                if isinstance(data.get(key), list):
                    return pd.DataFrame(data[key])
            return pd.DataFrame(data)
        return pd.DataFrame(data)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        first_line = fh.readline()
    if not first_line.strip():
        raise InputError(f"Empty file: {path}")
    sep = _sniff_separator(first_line)
    try:
        return pd.read_csv(path, sep=sep, encoding="utf-8-sig", dtype=str, keep_default_na=True)
    except pd.errors.ParserError as exc:
        raise InputError(f"Could not parse {path}: {exc}") from exc
