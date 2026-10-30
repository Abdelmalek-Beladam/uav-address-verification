"""Configuration of the verification pipeline.

All thresholds live here. Defaults are documented in ``default_config.toml``.
A user config file only needs the keys that differ from the defaults.
"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from .errors import ConfigError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


@dataclass
class PhotosConfig:
    max_distance_to_street_m: float = 12.0
    coverage_views: list[str] = field(default_factory=lambda: ["left", "right"])
    projection: str = "rectilinear"
    pitch_positive_up: bool = True


@dataclass
class AddressesConfig:
    scope_radius_m: float = 40.0
    use_facade_orientation: bool = True
    max_facade_view_angle_deg: float = 80.0


@dataclass
class TrackingConfig:
    max_frame_gap: int = 3
    max_track_residual_m: float = 2.0
    min_triangulation_angle_deg: float = 5.0
    min_depth_m: float = 1.0
    max_depth_m: float = 30.0
    nominal_depth_m: float = 7.0
    merge_distance_m: float = 2.5


@dataclass
class MatchingConfig:
    max_match_distance_m: float = 4.0
    max_ray_offset_m: float = 3.0
    out_of_place_min_m: float = 8.0
    relaxed_match_distance_m: float = 0.0
    frontage_match_max_m: float = 0.0


@dataclass
class CalibrationConfig:
    enabled: bool = True
    search_radius_m: float = 12.0
    min_anchors: int = 3
    max_spread_m: float = 2.5
    max_offset_m: float = 15.0


@dataclass
class CoverageConfig:
    min_visible_m: float = 2.0
    max_visible_m: float = 15.0
    edge_margin_deg: float = 5.0
    max_facade_angle_deg: float = 60.0
    min_views_for_missing: int = 2


@dataclass
class DecisionConfig:
    min_reading_agreement: float = 0.6
    min_detection_conf: float = 0.5
    min_ocr_conf: float = 0.5
    min_views_out_of_place: int = 2
    compare_suffix: bool = True
    partial_read_check: bool = False
    strict_error_claims: bool = False


@dataclass
class Config:
    photos: PhotosConfig = field(default_factory=PhotosConfig)
    addresses: AddressesConfig = field(default_factory=AddressesConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    coverage: CoverageConfig = field(default_factory=CoverageConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce(current: Any, value: Any, name: str) -> Any:
    if isinstance(current, bool):
        if not isinstance(value, bool):
            raise ConfigError(f"'{name}' must be true or false")
        return value
    if isinstance(current, int):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
            raise ConfigError(f"'{name}' must be an integer")
        return int(value)
    if isinstance(current, float):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"'{name}' must be a number")
        return float(value)
    if isinstance(current, list):
        if not isinstance(value, list):
            raise ConfigError(f"'{name}' must be a list")
        return [str(v) for v in value]
    if isinstance(current, str):
        if not isinstance(value, str):
            raise ConfigError(f"'{name}' must be a string")
        return value
    raise ConfigError(f"Unsupported setting type for '{name}'")  # pragma: no cover


def _apply(obj: Any, data: dict[str, Any], prefix: str = "") -> None:
    known = {f.name for f in fields(obj)}
    for key, value in data.items():
        name = f"{prefix}{key}"
        if key not in known:
            raise ConfigError(f"Unknown setting '{name}'")
        current = getattr(obj, key)
        if is_dataclass(current):
            if not isinstance(value, dict):
                raise ConfigError(f"'{name}' must be a section")
            _apply(current, value, prefix=f"{name}.")
        else:
            setattr(obj, key, _coerce(current, value, name))


def _validate(cfg: Config) -> None:
    positive = {
        "photos.max_distance_to_street_m": cfg.photos.max_distance_to_street_m,
        "addresses.scope_radius_m": cfg.addresses.scope_radius_m,
        "tracking.max_depth_m": cfg.tracking.max_depth_m,
        "tracking.nominal_depth_m": cfg.tracking.nominal_depth_m,
        "matching.max_match_distance_m": cfg.matching.max_match_distance_m,
        "matching.max_ray_offset_m": cfg.matching.max_ray_offset_m,
        "matching.out_of_place_min_m": cfg.matching.out_of_place_min_m,
        "coverage.max_visible_m": cfg.coverage.max_visible_m,
    }
    for name, value in positive.items():
        if value <= 0:
            raise ConfigError(f"'{name}' must be greater than 0")
    if cfg.photos.projection not in ("rectilinear", "linear"):
        raise ConfigError("'photos.projection' must be 'rectilinear' or 'linear'")
    if cfg.tracking.min_depth_m >= cfg.tracking.max_depth_m:
        raise ConfigError("'tracking.min_depth_m' must be smaller than 'tracking.max_depth_m'")
    if cfg.coverage.min_visible_m >= cfg.coverage.max_visible_m:
        raise ConfigError("'coverage.min_visible_m' must be smaller than 'coverage.max_visible_m'")
    if not 0.0 <= cfg.decision.min_reading_agreement <= 1.0:
        raise ConfigError("'decision.min_reading_agreement' must be between 0 and 1")
    if cfg.tracking.max_frame_gap < 1:
        raise ConfigError("'tracking.max_frame_gap' must be at least 1")


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> Config:
    """Build a Config from defaults, an optional TOML file and optional overrides."""
    cfg = Config()
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"Config file not found: {p}")
        with open(p, "rb") as fh:
            try:
                data = tomllib.load(fh)
            except tomllib.TOMLDecodeError as exc:
                raise ConfigError(f"Invalid TOML in {p}: {exc}") from exc
        _apply(cfg, data)
    if overrides:
        _apply(cfg, overrides)
    _validate(cfg)
    return cfg
