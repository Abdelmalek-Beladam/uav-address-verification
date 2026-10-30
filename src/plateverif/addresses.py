"""Loading of the official address register.

Two layouts are supported:

* Paris open data "adresse_paris" export (semicolon CSV with columns
  ``Geometry X Y``, ``N_VOIE``, ``L_NVOIE``, ``L_ADR``, ``N_SQ_VO``, ``A_NVOIE``...).
* A generic table with columns ``lat``, ``lon``, ``number``, ``street_name`` and
  optionally ``street_id``, ``address_id``, ``facade_bearing_deg``.

Output columns: address_id, street_id, street_name, street_display, key,
number, label, lat, lon, facade_bearing_deg, is_corner.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .errors import InputError
from .tables import column, to_number
from .textnorm import display_number, normalize_number, split_key

PARIS_COLUMNS = {"Geometry X Y", "N_VOIE", "L_NVOIE", "L_ADR", "N_SQ_VO"}

STREET_TYPES = {
    "R": "RUE",
    "QU": "QUAI",
    "BD": "BOULEVARD",
    "AV": "AVENUE",
    "PL": "PLACE",
    "IMP": "IMPASSE",
    "PAS": "PASSAGE",
    "SQ": "SQUARE",
    "VLA": "VILLA",
    "ALL": "ALLEE",
    "CHEM": "CHEMIN",
    "CRS": "COURS",
}

OUTPUT_COLUMNS = [
    "address_id",
    "street_id",
    "street_name",
    "street_display",
    "key",
    "number",
    "label",
    "lat",
    "lon",
    "facade_bearing_deg",
    "is_corner",
]


def street_display_name(name: str) -> str:
    if not name:
        return ""
    parts = name.split(" ", 1)
    head = STREET_TYPES.get(parts[0], parts[0])
    text = head if len(parts) == 1 else f"{head} {parts[1]}"
    small = {"DE", "DES", "DU", "LA", "LE", "LES", "D'", "L'", "ET", "AUX", "AU", "EN", "SUR", "SOUS"}
    words = []
    for i, word in enumerate(text.split()):
        words.append(word.lower() if (i > 0 and word in small) else word.capitalize())
    return " ".join(words)


def _read(path: Path) -> pd.DataFrame:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        first = fh.readline()
    sep = ";" if first.count(";") >= first.count(",") else ","
    return pd.read_csv(path, sep=sep, encoding="utf-8-sig", dtype=str, keep_default_na=True)


def _parse_paris(raw: pd.DataFrame) -> pd.DataFrame:
    latlon = raw["Geometry X Y"].astype(str).str.split(",", n=1, expand=True)
    lat = to_number(latlon[0])
    lon = to_number(latlon[1]) if latlon.shape[1] > 1 else pd.Series(np.nan, index=raw.index)
    if lat.isna().any() and "Geometry" in raw.columns:
        missing = lat.isna()
        for idx in raw.index[missing]:
            try:
                coords = json.loads(raw.at[idx, "Geometry"])["coordinates"]
                lon.at[idx], lat.at[idx] = float(coords[0]), float(coords[1])
            except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                continue

    l_nvoie = column(raw, "L_NVOIE", "").fillna("").astype(str).str.strip()
    key = l_nvoie.map(normalize_number)
    built = (
        column(raw, "N_VOIE", "").fillna("").astype(str).str.strip()
        + column(raw, "C_SUF1", "").fillna("").astype(str).str.strip()
        + column(raw, "C_SUF2", "").fillna("").astype(str).str.strip()
    )
    key = key.where(key.notna(), built.map(normalize_number))

    l_adr = column(raw, "L_ADR", "").fillna("").astype(str).str.strip()
    street_name = [
        adr[len(num) :].strip() if num and adr.upper().startswith(num.upper()) else adr
        for adr, num in zip(l_adr, l_nvoie)
    ]
    street_name = pd.Series(street_name, index=raw.index)

    n_sq_vo = column(raw, "N_SQ_VO", "").fillna("").astype(str).str.strip()
    n_sq_ad = column(raw, "N_SQ_AD", "").fillna("").astype(str).str.strip()
    address_id = n_sq_ad.where(n_sq_ad != "", pd.Series([f"row{i}" for i in range(len(raw))], index=raw.index))
    street_id = n_sq_vo.where(n_sq_vo != "", ("name:" + street_name).where(street_name != "", "addr:" + address_id))

    # A_NVOIE is the label angle (degrees, counter-clockwise from east) drawn along
    # the street. The facade faces the street at compass bearing 180 - A_NVOIE.
    angle = to_number(column(raw, "A_NVOIE"))
    facade = (180.0 - angle) % 360.0

    return pd.DataFrame(
        {
            "address_id": address_id,
            "street_id": street_id,
            "street_name": street_name,
            "key": key,
            "lat": lat,
            "lon": lon,
            "facade_bearing_deg": facade,
            "is_corner": column(raw, "B_ANGLE", "").fillna("").astype(str).str.upper().eq("O"),
        }
    )


def _parse_generic(raw: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower(): c for c in raw.columns}

    def pick(*names):
        for n in names:
            if n in cols:
                return raw[cols[n]]
        return None

    lat = pick("lat", "latitude")
    lon = pick("lon", "lng", "longitude")
    number = pick("number", "numero", "house_number")
    street = pick("street_name", "street", "nom_voie")
    if lat is None or lon is None or number is None or street is None:
        raise InputError(
            "Address file not recognised. Use the Paris 'adresse_paris' export or a table with "
            "columns lat, lon, number, street_name (optional: street_id, address_id, facade_bearing_deg)."
        )
    street = street.fillna("").astype(str).str.strip().str.upper()
    street_id = pick("street_id", "id_voie")
    street_id = street_id.fillna("").astype(str) if street_id is not None else "name:" + street
    address_id = pick("address_id", "id")
    address_id = (
        address_id.fillna("").astype(str)
        if address_id is not None
        else pd.Series([f"A{i + 1:06d}" for i in range(len(raw))], index=raw.index)
    )
    facade = pick("facade_bearing_deg")
    return pd.DataFrame(
        {
            "address_id": address_id,
            "street_id": street_id,
            "street_name": street,
            "key": number.map(normalize_number),
            "lat": to_number(lat),
            "lon": to_number(lon),
            "facade_bearing_deg": to_number(facade) if facade is not None else np.nan,
            "is_corner": False,
        }
    )


def load_addresses(source, bbox: tuple[float, float, float, float] | None = None) -> pd.DataFrame:
    """Load official addresses.

    ``bbox`` = (min_lat, min_lon, max_lat, max_lon) keeps only addresses inside it.
    """
    if isinstance(source, pd.DataFrame):
        raw = source.copy()
    else:
        path = Path(source)
        if not path.exists():
            raise InputError(f"Address file not found: {path}")
        raw = _read(path)
    raw.columns = [str(c).strip() for c in raw.columns]
    if set(OUTPUT_COLUMNS).issubset(raw.columns):
        out = raw[OUTPUT_COLUMNS].copy()
        for c in ("lat", "lon", "facade_bearing_deg"):
            out[c] = to_number(out[c])
    elif PARIS_COLUMNS.issubset(raw.columns):
        out = _parse_paris(raw)
    else:
        out = _parse_generic(raw)

    total = len(out)
    out = out[out["lat"].notna() & out["lon"].notna() & out["key"].notna()].copy()
    dropped = total - len(out)
    if bbox is not None:
        min_lat, min_lon, max_lat, max_lon = bbox
        out = out[out["lat"].between(min_lat, max_lat) & out["lon"].between(min_lon, max_lon)].copy()

    out["key"] = out["key"].astype(str)
    out["number"] = out["key"].map(lambda k: split_key(k)[0]).astype(int)
    out["street_name"] = out["street_name"].fillna("").astype(str)
    out["street_display"] = out["street_name"].map(street_display_name)
    out["label"] = [
        f"{display_number(k)} {s}".strip() for k, s in zip(out["key"], out["street_display"])
    ]
    out["is_corner"] = out["is_corner"].astype(str).str.lower().isin(["true", "1", "o"])
    out = out[OUTPUT_COLUMNS].reset_index(drop=True)
    out.attrs["dropped_rows"] = int(dropped)
    return out
