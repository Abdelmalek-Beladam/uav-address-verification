"""Grouping of detections of the same physical plate across consecutive photos.

Two detections belong to the same plate when they are in the same kind of view,
at most ``max_frame_gap`` photos apart, show the same reading and their sight
lines cross in front of the cameras at a plausible distance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import Config
from .geo import Triangulation, triangulate, wrap180

PARALLEL_ANGLE_DEG = 10.0
PARALLEL_MAX_MOVE_M = 3.0


@dataclass
class Track:
    track_id: str
    view: str
    reading: str | None
    rows: list[int] = field(default_factory=list)
    seqs: list[int] = field(default_factory=list)
    origins: list[tuple[float, float]] = field(default_factory=list)
    azimuths: list[float] = field(default_factory=list)

    @property
    def first_seq(self) -> int:
        return min(self.seqs)

    @property
    def last_seq(self) -> int:
        return max(self.seqs)

    def origin_array(self) -> np.ndarray:
        return np.asarray(self.origins, dtype=float).reshape(-1, 2)

    def azimuth_array(self) -> np.ndarray:
        return np.asarray(self.azimuths, dtype=float)

    def shift(self, dx: float, dy: float) -> None:
        self.origins = [(x + dx, y + dy) for x, y in self.origins]


def rays_consistent(origins: np.ndarray, azimuths: np.ndarray, cfg: Config) -> tuple[bool, float]:
    """Check that sight lines can belong to one plate. Returns (ok, cost)."""
    t = cfg.tracking
    tri = triangulate(origins, azimuths, t.min_triangulation_angle_deg)
    if tri is None:
        # Nearly parallel lines: same plate only if the camera barely moved.
        az_ok = np.max(np.abs(wrap180(azimuths - azimuths[0]))) <= PARALLEL_ANGLE_DEG
        move = np.max(np.hypot(*(origins - origins[0]).T)) if len(origins) > 1 else 0.0
        return bool(az_ok and move <= PARALLEL_MAX_MOVE_M), 5.0
    if np.any(tri.depths < t.min_depth_m) or np.any(tri.depths > t.max_depth_m):
        return False, np.inf
    if tri.rms > t.max_track_residual_m:
        return False, np.inf
    return True, tri.rms


def build_tracks(dets: pd.DataFrame, cfg: Config) -> list[Track]:
    """Greedy, order-preserving grouping. ``dets`` needs columns view,
    sequence_number, reading, x_center, cam_x, cam_y, azimuth_deg."""
    if dets.empty:
        return []
    views = dets["view"].astype(str).to_numpy()
    seqs = dets["sequence_number"].astype(int).to_numpy()
    readings = [r if isinstance(r, str) else None for r in dets["reading"]]
    xs = dets["x_center"].astype(float).to_numpy()
    cam = dets[["cam_x", "cam_y"]].astype(float).to_numpy()
    az = dets["azimuth_deg"].astype(float).to_numpy()
    order = np.lexsort((xs, seqs, views))

    tracks: list[Track] = []
    open_by_view: dict[str, list[Track]] = {}
    gap_limit = cfg.tracking.max_frame_gap
    for pos in order:
        view, seq, reading = views[pos], int(seqs[pos]), readings[pos]
        best, best_cost = None, np.inf
        for track in open_by_view.get(view, []):
            gap = seq - track.last_seq
            if gap > gap_limit or seq in track.seqs or track.reading != reading:
                continue
            ok, cost = rays_consistent(
                np.vstack([track.origin_array(), cam[pos]]),
                np.append(track.azimuth_array(), az[pos]),
                cfg,
            )
            cost += 0.25 * gap
            if ok and cost < best_cost:
                best, best_cost = track, cost
        if best is None:
            best = Track(track_id=f"T{len(tracks) + 1:04d}", view=view, reading=reading)
            tracks.append(best)
            open_by_view.setdefault(view, []).append(best)
        best.rows.append(int(pos))
        best.seqs.append(seq)
        best.origins.append((float(cam[pos][0]), float(cam[pos][1])))
        best.azimuths.append(float(az[pos]))
        open_by_view[view] = [t for t in open_by_view[view] if seq - t.last_seq <= gap_limit]
    return tracks


def track_triangulation(track: Track, cfg: Config) -> Triangulation | None:
    tri = triangulate(track.origin_array(), track.azimuth_array(), cfg.tracking.min_triangulation_angle_deg)
    if tri is None:
        return None
    t = cfg.tracking
    if np.any(tri.depths < t.min_depth_m) or np.any(tri.depths > t.max_depth_m) or tri.rms > t.max_track_residual_m:
        return None
    return tri
