"""Matching of located plates to official addresses, and GPS offset calibration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Config
from .geo import bearing_deg, ray_offsets, wrap180


@dataclass
class Pins:
    """Official addresses in local metric coordinates."""

    x: np.ndarray
    y: np.ndarray
    keys: np.ndarray
    streets: np.ndarray
    facade: np.ndarray

    def __len__(self) -> int:
        return len(self.x)

    def xy(self) -> np.ndarray:
        return np.column_stack([self.x, self.y])


@dataclass
class PinMatch:
    pin: int | None
    distance_m: float | None
    method: str
    n_candidates: int
    runner_up: int | None = None
    ambiguous: bool = False


def facing(pins: Pins, cam_xy: np.ndarray, cfg: Config) -> np.ndarray:
    """True for addresses whose facade faces the camera (or has no orientation)."""
    if len(pins) == 0:
        return np.zeros(0, dtype=bool)
    if not cfg.addresses.use_facade_orientation:
        return np.ones(len(pins), dtype=bool)
    to_cam = bearing_deg(cam_xy[0] - pins.x, cam_xy[1] - pins.y)
    ok = np.abs(wrap180(to_cam - pins.facade)) <= cfg.addresses.max_facade_view_angle_deg
    return ok | np.isnan(pins.facade)


def match_plate(
    origins: np.ndarray,
    azimuths: np.ndarray,
    point: np.ndarray | None,
    reading: str | None,
    pins: Pins,
    cfg: Config,
) -> PinMatch:
    """Find the official address at the plate location.

    With a located plate (two or more sight lines) the nearest address within
    ``max_match_distance_m`` wins. With a single line, addresses close to the
    line are candidates. If one candidate carries the plate number it is
    preferred (two plates of a corner can be close together).
    """
    method = "position" if point is not None else "sight line"
    if len(pins) == 0:
        return PinMatch(None, None, method, 0)
    seen = np.zeros(len(pins), dtype=bool)
    for origin in origins:
        seen |= facing(pins, origin, cfg)

    if point is not None:
        dist = np.hypot(pins.x - point[0], pins.y - point[1])
        ok = seen & (dist <= cfg.matching.max_match_distance_m)
        score = dist
    else:
        along, across = ray_offsets(origins, azimuths, pins.xy())
        t = cfg.tracking
        ok = (
            seen
            & np.all((along >= t.min_depth_m) & (along <= t.max_depth_m), axis=1)
            & np.all(across <= cfg.matching.max_ray_offset_m, axis=1)
        )
        dist = np.sqrt(np.mean(across**2, axis=1))
        score = dist + 0.05 * np.mean(along, axis=1)

    idx = np.flatnonzero(ok)
    if idx.size == 0:
        return PinMatch(None, None, method, 0)
    idx = idx[np.argsort(score[idx])]
    chosen = int(idx[0])
    if reading is not None:
        same = [int(j) for j in idx if pins.keys[j] == reading]
        if same and same[0] != chosen:
            chosen = same[0]
            method += " + number"
    runner = next((int(j) for j in idx if j != chosen), None)
    ambiguous = runner is not None and (score[runner] - score[chosen]) < 1.0 and "number" not in method
    return PinMatch(chosen, float(dist[chosen]), method, int(idx.size), runner, bool(ambiguous))


def estimate_gps_offset(points: list[np.ndarray], readings: list[str], pins: Pins, cfg: Config) -> tuple[np.ndarray, dict]:
    """Estimate a constant GPS offset from plates whose number matches a nearby address.

    Returns (offset_xy, info). The offset is added to every camera position.
    """
    c = cfg.calibration
    info: dict = {"enabled": bool(c.enabled), "applied": False, "anchors": 0, "offset_east_m": 0.0, "offset_north_m": 0.0}
    if not c.enabled:
        info["reason"] = "disabled in the configuration"
        return np.zeros(2), info
    vectors = []
    for point, reading in zip(points, readings):
        if point is None or reading is None:
            continue
        same = np.flatnonzero(pins.keys == reading)
        if same.size == 0:
            continue
        d = np.hypot(pins.x[same] - point[0], pins.y[same] - point[1])
        j = int(np.argmin(d))
        if d[j] <= c.search_radius_m:
            vectors.append([pins.x[same[j]] - point[0], pins.y[same[j]] - point[1]])
    info["anchors"] = len(vectors)
    if len(vectors) < c.min_anchors:
        info["reason"] = f"only {len(vectors)} located plate(s) match a nearby address (need {c.min_anchors})"
        return np.zeros(2), info
    v = np.asarray(vectors)
    offset = np.median(v, axis=0)
    spread = float(np.median(np.hypot(*(v - offset).T)))
    info["spread_m"] = round(spread, 2)
    magnitude = float(np.hypot(*offset))
    if spread > c.max_spread_m:
        info["reason"] = f"anchors disagree (spread {spread:.1f} m > {c.max_spread_m:g} m)"
        return np.zeros(2), info
    if magnitude > c.max_offset_m:
        info["reason"] = f"estimated offset {magnitude:.1f} m is larger than the {c.max_offset_m:g} m limit"
        return np.zeros(2), info
    info.update(
        applied=True,
        offset_east_m=round(float(offset[0]), 2),
        offset_north_m=round(float(offset[1]), 2),
        offset_m=round(magnitude, 2),
    )
    return offset, info
