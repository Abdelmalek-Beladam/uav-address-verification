"""Loading of plate detections (manual annotations today, detector + OCR output later).

One row per plate seen in one crop. Accepted columns (case-insensitive):

* where:   ``image`` (crop file name) or ``picture_id`` + ``view``
           or ``sequence_number`` + ``view``
* box:     ``x_min, y_min, x_max, y_max`` or ``x_center, y_center`` (pixels)
* size:    ``image_width, image_height`` (pixels) or ``--images-root`` to read them
* number:  ``text`` (aliases: number, plate_number, plate_text, ocr_text); ``?`` = unreadable
* optional ``det_conf``, ``ocr_conf`` (0-1, default 1.0), ``source``, ``det_id``
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from .errors import InputError
from .metadata import Metadata
from .tables import file_basename, read_table, to_number
from .textnorm import normalize_number

TEXT_ALIASES = ("text", "number", "plate_number", "plate_text", "ocr_text", "reading")
DET_CONF_ALIASES = ("det_conf", "confidence", "det_confidence", "score")

DETECTION_COLUMNS = [
    "det_id",
    "image",
    "picture_id",
    "sequence_number",
    "view",
    "x_center",
    "y_center",
    "box_width",
    "box_height",
    "image_width",
    "image_height",
    "text",
    "reading",
    "det_conf",
    "ocr_conf",
    "source",
]


def empty_detections() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype=object) for c in DETECTION_COLUMNS})


class ImageSizeIndex:
    """Finds crop files under a folder and reads their pixel size."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        if not self.root.is_dir():
            raise InputError(f"Images folder not found: {self.root}")
        self._paths: dict[str, Path] = {}
        for folder, _dirs, files in os.walk(self.root):
            for name in files:
                if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    self._paths.setdefault(name, Path(folder) / name)
        self._cache: dict[str, tuple[int, int]] = {}

    def size(self, name: str) -> tuple[int, int] | None:
        if name in self._cache:
            return self._cache[name]
        path = self._paths.get(name)
        if path is None:
            return None
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover
            raise InputError("Reading image sizes needs Pillow: pip install Pillow") from exc
        with Image.open(path) as img:
            self._cache[name] = (int(img.width), int(img.height))
        return self._cache[name]


def _first(raw: pd.DataFrame, names) -> pd.Series | None:
    for name in names:
        if name in raw.columns:
            return raw[name]
    return None


def load_detections(source, metadata: Metadata, images_root: str | Path | None = None) -> pd.DataFrame:
    raw = read_table(source)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    if raw.empty:
        return empty_detections()
    raw = raw.reset_index(drop=True)
    views = metadata.views

    # 1. Which crop does each detection belong to?
    if "image" in raw.columns:
        names = raw["image"].map(file_basename)
        lookup = metadata.file_lookup()
        unknown = names[~names.isin(lookup.index)]
        if len(unknown):
            examples = ", ".join(unknown.unique()[:5])
            raise InputError(
                f"{len(unknown)} detection(s) refer to images that are not in the metadata, e.g. {examples}"
            )
        rows = lookup.loc[names.to_numpy()]
        picture_id = rows["picture_id"].astype(str).to_numpy()
        view = rows["view"].astype(str).to_numpy()
        image = names.to_numpy()
    elif {"picture_id", "view"}.issubset(raw.columns) or {"sequence_number", "view"}.issubset(raw.columns):
        if "picture_id" in raw.columns:
            keys = list(zip(raw["picture_id"].astype(str).str.strip(), raw["view"].astype(str).str.strip()))
            index = views.set_index(["picture_id", "view"])
        else:
            seqs = to_number(raw["sequence_number"])
            if seqs.isna().any():
                raise InputError("Detections contain an empty sequence_number")
            keys = list(zip(seqs.astype(int), raw["view"].astype(str).str.strip()))
            index = views.set_index(["sequence_number", "view"])
        missing = [k for k in keys if k not in index.index]
        if missing:
            raise InputError(f"{len(missing)} detection(s) refer to unknown photo/view pairs, e.g. {missing[0]}")
        rows = index.loc[keys]
        picture_id = rows["picture_id"].astype(str).to_numpy() if "picture_id" in rows else np.array([k[0] for k in keys])
        view = np.array([k[1] for k in keys])
        image = rows["file"].astype(str).to_numpy()
    else:
        raise InputError("Detections need an 'image' column (crop file name) or 'picture_id' + 'view' columns")

    # 2. Box position
    if {"x_min", "x_max"}.issubset(raw.columns):
        x_min, x_max = to_number(raw["x_min"]), to_number(raw["x_max"])
        x_center = (x_min + x_max) / 2.0
        box_w = (x_max - x_min).abs()
        if {"y_min", "y_max"}.issubset(raw.columns):
            y_min, y_max = to_number(raw["y_min"]), to_number(raw["y_max"])
            y_center = (y_min + y_max) / 2.0
            box_h = (y_max - y_min).abs()
        else:
            y_center = pd.Series(np.nan, index=raw.index)
            box_h = pd.Series(np.nan, index=raw.index)
    elif "x_center" in raw.columns:
        x_center = to_number(raw["x_center"])
        y_center = to_number(raw["y_center"]) if "y_center" in raw.columns else pd.Series(np.nan, index=raw.index)
        box_w = to_number(raw["width"]) if "width" in raw.columns else pd.Series(np.nan, index=raw.index)
        box_h = to_number(raw["height"]) if "height" in raw.columns else pd.Series(np.nan, index=raw.index)
    else:
        raise InputError("Detections need box columns: x_min, y_min, x_max, y_max (or x_center, y_center)")
    if x_center.isna().any():
        raise InputError(f"Empty box coordinates in detection row {int(x_center.isna().idxmax()) + 2}")

    # 3. Image size
    width = to_number(raw["image_width"]) if "image_width" in raw.columns else pd.Series(np.nan, index=raw.index)
    height = to_number(raw["image_height"]) if "image_height" in raw.columns else pd.Series(np.nan, index=raw.index)
    need = width.isna() | height.isna()
    if need.any():
        if images_root is None:
            raise InputError(
                f"image_width / image_height missing for {int(need.sum())} detection(s). "
                "Add the columns or pass the images folder (--images-root)."
            )
        sizes = ImageSizeIndex(images_root)
        for i in np.flatnonzero(need.to_numpy()):
            size = sizes.size(image[i])
            if size is None:
                raise InputError(f"Image {image[i]} not found under {images_root}")
            width.iat[i], height.iat[i] = size
    if (width <= 0).any() or (height <= 0).any():
        raise InputError("image_width and image_height must be positive")
    y_center = y_center.fillna(height / 2.0)
    outside = (x_center < -1) | (x_center > width + 1) | (y_center < -1) | (y_center > height + 1)
    if outside.any():
        i = int(np.flatnonzero(outside.to_numpy())[0])
        raise InputError(f"Box of detection row {i + 2} ({image[i]}) is outside the image. Coordinates must be in pixels.")

    # 4. Number text and confidences
    text = _first(raw, TEXT_ALIASES)
    if text is None:
        raise InputError("Detections need a 'text' column with the plate number (use ? when unreadable)")
    text = text.fillna("?").astype(str).str.strip()
    det_conf = _first(raw, DET_CONF_ALIASES)
    det_conf = to_number(det_conf).fillna(1.0) if det_conf is not None else pd.Series(1.0, index=raw.index)
    ocr_conf = to_number(raw["ocr_conf"]).fillna(1.0) if "ocr_conf" in raw.columns else pd.Series(1.0, index=raw.index)
    if "source" in raw.columns:
        source = raw["source"].fillna("manual").astype(str)
    else:
        source = pd.Series("manual", index=raw.index)
    if "det_id" in raw.columns and raw["det_id"].notna().all() and not raw["det_id"].duplicated().any():
        det_id = raw["det_id"].astype(str)
    else:
        det_id = pd.Series([f"D{i + 1:05d}" for i in range(len(raw))], index=raw.index)

    seq_lookup = metadata.photos.set_index("picture_id")["sequence_number"]
    out = pd.DataFrame(
        {
            "det_id": det_id.to_numpy(),
            "image": image,
            "picture_id": picture_id,
            "sequence_number": seq_lookup.loc[picture_id].to_numpy().astype(int),
            "view": view,
            "x_center": x_center.to_numpy(),
            "y_center": y_center.to_numpy(),
            "box_width": box_w.to_numpy(),
            "box_height": box_h.to_numpy(),
            "image_width": width.to_numpy(),
            "image_height": height.to_numpy(),
            "text": text.to_numpy(),
            "reading": text.map(normalize_number).to_numpy(),
            "det_conf": det_conf.clip(0, 1).to_numpy(),
            "ocr_conf": ocr_conf.clip(0, 1).to_numpy(),
            "source": source.to_numpy(),
        }
    )
    out["reading"] = out["reading"].astype(object).where(out["reading"].notna(), None)
    return out
