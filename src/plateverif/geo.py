"""Geometry helpers: local metric frame, bearings, pixel directions and triangulation.

Conventions
-----------
* Local frame: x = east (m), y = north (m), origin near the sequence.
* Bearings are compass bearings in degrees: 0 = north, 90 = east, clockwise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

EARTH_RADIUS_M = 6371008.8


class LocalFrame:
    """Equirectangular projection around a reference point (cm-accurate over a few km)."""

    def __init__(self, lat0: float, lon0: float):
        if not (math.isfinite(lat0) and math.isfinite(lon0)):
            raise ValueError("LocalFrame needs a finite reference point")
        self.lat0 = float(lat0)
        self.lon0 = float(lon0)
        self._ky = math.radians(1.0) * EARTH_RADIUS_M
        self._kx = self._ky * math.cos(math.radians(self.lat0))

    def to_xy(self, lat, lon) -> tuple[np.ndarray, np.ndarray]:
        lat = np.asarray(lat, dtype=float)
        lon = np.asarray(lon, dtype=float)
        return (lon - self.lon0) * self._kx, (lat - self.lat0) * self._ky

    def to_latlon(self, x, y) -> tuple[np.ndarray, np.ndarray]:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        return self.lat0 + y / self._ky, self.lon0 + x / self._kx

    def metres_to_degrees(self, metres: float) -> tuple[float, float]:
        """Return (dlat, dlon) spanned by a distance in metres."""
        return metres / self._ky, metres / self._kx


def wrap180(angle):
    """Wrap angles to [-180, 180)."""
    return (np.asarray(angle, dtype=float) + 180.0) % 360.0 - 180.0


def wrap360(angle):
    """Wrap angles to [0, 360)."""
    return np.asarray(angle, dtype=float) % 360.0


def bearing_deg(dx, dy):
    """Compass bearing of a vector (dx east, dy north)."""
    return wrap360(np.degrees(np.arctan2(dx, dy)))


def direction(bearing) -> np.ndarray:
    """Unit vector(s) (east, north) for compass bearing(s)."""
    b = np.radians(np.asarray(bearing, dtype=float))
    return np.stack([np.sin(b), np.cos(b)], axis=-1)


def pixel_azimuth_offset(x, y, width, height, hfov_deg, pitch_deg=0.0, projection="rectilinear"):
    """Horizontal angle (deg) between the crop centre and the pixel (x, y).

    Positive values are to the right of the crop centre (clockwise).
    ``pitch_deg`` is positive when the crop looks upward.
    """
    x = np.asarray(x, dtype=float)
    width = np.asarray(width, dtype=float)
    hfov = np.asarray(hfov_deg, dtype=float)
    if projection == "linear":
        return (x / width - 0.5) * hfov
    y = np.asarray(y, dtype=float)
    height = np.asarray(height, dtype=float)
    t = np.tan(np.radians(hfov) / 2.0)
    u = (2.0 * x / width - 1.0) * t
    w = (1.0 - 2.0 * y / height) * t * height / width
    th = np.radians(np.asarray(pitch_deg, dtype=float))
    return np.degrees(np.arctan2(u, np.cos(th) - w * np.sin(th)))


def angle_to_pixel_fraction(angle_deg, hfov_deg, projection="rectilinear"):
    """Inverse of pixel_azimuth_offset for the horizon line (pitch ignored)."""
    angle = np.asarray(angle_deg, dtype=float)
    hfov = np.asarray(hfov_deg, dtype=float)
    if projection == "linear":
        return 0.5 + angle / hfov
    return 0.5 + np.tan(np.radians(angle)) / (2.0 * np.tan(np.radians(hfov) / 2.0))


@dataclass
class Triangulation:
    point: np.ndarray
    depths: np.ndarray
    residuals: np.ndarray
    rms: float
    angle_spread_deg: float


def angle_spread(azimuths) -> float:
    az = np.asarray(azimuths, dtype=float)
    if az.size < 2:
        return 0.0
    diff = np.abs(wrap180(az[:, None] - az[None, :]))
    return float(diff.max())


def triangulate(origins, azimuths, min_angle_deg: float = 5.0) -> Triangulation | None:
    """Least-squares intersection of sight lines.

    Returns None with fewer than two lines or when the lines are almost parallel.
    """
    o = np.asarray(origins, dtype=float).reshape(-1, 2)
    az = np.asarray(azimuths, dtype=float).reshape(-1)
    if len(o) < 2:
        return None
    spread = angle_spread(az)
    if spread < min_angle_deg:
        return None
    d = direction(az)
    a = np.zeros((2, 2))
    b = np.zeros(2)
    for oi, di in zip(o, d):
        p = np.eye(2) - np.outer(di, di)
        a += p
        b += p @ oi
    if abs(np.linalg.det(a)) < 1e-9:
        return None
    point = np.linalg.solve(a, b)
    v = point - o
    depths = np.einsum("ij,ij->i", v, d)
    residuals = np.abs(v[:, 0] * d[:, 1] - v[:, 1] * d[:, 0])
    rms = float(np.sqrt(np.mean(residuals**2)))
    return Triangulation(point=point, depths=depths, residuals=residuals, rms=rms, angle_spread_deg=spread)


def ray_offsets(origins, azimuths, points) -> tuple[np.ndarray, np.ndarray]:
    """Distance along and across each ray for each point.

    Returns arrays of shape (n_points, n_rays): ``along`` (positive in front of
    the camera) and ``across`` (absolute perpendicular distance).
    """
    o = np.asarray(origins, dtype=float).reshape(-1, 2)
    d = direction(np.asarray(azimuths, dtype=float).reshape(-1))
    p = np.asarray(points, dtype=float).reshape(-1, 2)
    vx = p[:, 0][:, None] - o[:, 0][None, :]
    vy = p[:, 1][:, None] - o[:, 1][None, :]
    along = vx * d[:, 0][None, :] + vy * d[:, 1][None, :]
    across = np.abs(vx * d[:, 1][None, :] - vy * d[:, 0][None, :])
    return along, across


def side_of(points, cam_xy, travel_bearing) -> np.ndarray:
    """+1 when a point is left of the travel direction, -1 when right."""
    p = np.asarray(points, dtype=float).reshape(-1, 2)
    c = np.asarray(cam_xy, dtype=float).reshape(-1, 2)
    h = direction(np.asarray(travel_bearing, dtype=float).reshape(-1))
    v = p - c
    cross = h[:, 0] * v[:, 1] - h[:, 1] * v[:, 0]
    return np.where(cross > 0, 1, -1)
