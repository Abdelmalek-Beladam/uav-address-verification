"""Loading of the photo metadata produced by the 360-cropping step.

One row per 360 photo. Each crop ("view") is described by four columns:
``<view>_file``, ``<view>_global_direction``, ``<view>_horizontal_fov`` and
optionally ``<view>_pitch``. Views are discovered automatically (forward,
left, right, ...).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import Config
from .errors import InputError
from .tables import column, file_basename, read_table, to_number

REQUIRED_COLUMNS = ("picture_id", "latitude", "longitude", "travel_bearing")
PREFERRED_VIEW_ORDER = ("forward", "left", "right", "back")


@dataclass
class Metadata:
    photos: pd.DataFrame
    views: pd.DataFrame
    view_names: list[str]

    def file_lookup(self) -> pd.DataFrame:
        return self.views.set_index("file")[["picture_id", "view", "sequence_number"]]


def _discover_views(columns) -> list[str]:
    names = [
        c[: -len("_file")]
        for c in columns
        if c.endswith("_file") and f"{c[: -len('_file')]}_global_direction" in columns
    ]
    ordered = [v for v in PREFERRED_VIEW_ORDER if v in names]
    return ordered + sorted(v for v in names if v not in ordered)


def load_metadata(source, config: Config | None = None) -> Metadata:
    cfg = config or Config()
    raw = read_table(source)
    raw.columns = [str(c).strip() for c in raw.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise InputError(f"Metadata is missing required column(s): {', '.join(missing)}")
    if raw.empty:
        raise InputError("Metadata has no rows")

    if "sequence_number" in raw.columns:
        seq = to_number(raw["sequence_number"])
        if seq.isna().any():
            raise InputError("sequence_number has empty or non-numeric values")
    else:
        seq = pd.Series(np.arange(1, len(raw) + 1), index=raw.index, dtype=float)

    photos = pd.DataFrame(
        {
            "sequence_number": seq.astype(int),
            "picture_id": raw["picture_id"].astype(str).str.strip(),
            "sequence_id": column(raw, "sequence_id", "").fillna("").astype(str),
            "datetime": column(raw, "datetime", "").fillna("").astype(str),
            "lat": to_number(raw["latitude"]),
            "lon": to_number(raw["longitude"]),
            "travel_bearing": to_number(raw["travel_bearing"]) % 360.0,
            "distance_to_street_m": to_number(column(raw, "distance_to_street_m")),
            "source_url": column(raw, "source_url", "").fillna("").astype(str),
            "original_file": column(raw, "original_360_file", "").map(file_basename),
        }
    )
    dup = photos["picture_id"].duplicated(keep=False)
    if dup.any():
        examples = ", ".join(photos.loc[dup, "picture_id"].unique()[:3])
        raise InputError(f"Duplicate picture_id in metadata: {examples}")
    if photos["sequence_number"].duplicated().any():
        raise InputError("Duplicate sequence_number in metadata")

    limit = cfg.photos.max_distance_to_street_m
    dist = photos["distance_to_street_m"]
    no_gps = photos["lat"].isna() | photos["lon"].isna()
    no_bearing = photos["travel_bearing"].isna()
    too_far = dist.notna() & (dist > limit)
    photos["skip_reason"] = np.select(
        [no_gps, no_bearing, too_far],
        [
            "missing GPS position",
            "missing travel bearing",
            dist.map(lambda d: f"{d:.1f} m from the street (limit {limit:g} m)"),
        ],
        default="",
    )
    photos["valid"] = photos["skip_reason"] == ""

    view_names = _discover_views(list(raw.columns))
    if not view_names:
        raise InputError(
            "No crop columns found. Expected e.g. left_file, left_global_direction, left_horizontal_fov."
        )
    frames = []
    for view in view_names:
        fov_col = f"{view}_horizontal_fov"
        if fov_col not in raw.columns:
            raise InputError(f"Column {fov_col} is missing")
        frames.append(
            pd.DataFrame(
                {
                    "picture_id": photos["picture_id"],
                    "sequence_number": photos["sequence_number"],
                    "view": view,
                    "file": raw[f"{view}_file"].map(file_basename),
                    "direction_deg": to_number(raw[f"{view}_global_direction"]) % 360.0,
                    "hfov_deg": to_number(raw[fov_col]),
                    "pitch_deg": to_number(column(raw, f"{view}_pitch", 0)).fillna(0.0),
                }
            )
        )
    views = pd.concat(frames, ignore_index=True)
    views = views[views["file"] != ""].reset_index(drop=True)
    bad = views["direction_deg"].isna() | views["hfov_deg"].isna() | (views["hfov_deg"] <= 0)
    if bad.any():
        row = views[bad].iloc[0]
        raise InputError(f"Invalid direction or field of view for {row['file']}")
    dup_files = views["file"].duplicated(keep=False)
    if dup_files.any():
        raise InputError(f"The same crop file name is used twice: {views.loc[dup_files, 'file'].iloc[0]}")

    photos = photos.sort_values("sequence_number").reset_index(drop=True)
    views = views.sort_values(["sequence_number", "view"]).reset_index(drop=True)
    return Metadata(photos=photos, views=views, view_names=view_names)


def load_reviewed(source, metadata: Metadata) -> set[tuple[str, str]]:
    """Set of (picture_id, view) that a person has looked at."""
    raw = read_table(source)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    if raw.empty:
        return set()
    if "image" in raw.columns:
        lookup = metadata.file_lookup()
        names = raw["image"].map(file_basename)
        unknown = names[~names.isin(lookup.index)]
        if len(unknown):
            raise InputError(f"Reviewed list contains unknown images, e.g. {unknown.iloc[0]}")
        rows = lookup.loc[names]
        return set(zip(rows["picture_id"].astype(str), rows["view"].astype(str)))
    if {"picture_id", "view"}.issubset(raw.columns):
        return set(zip(raw["picture_id"].astype(str).str.strip(), raw["view"].astype(str).str.strip()))
    raise InputError("Reviewed list needs an 'image' column or 'picture_id' + 'view' columns")
