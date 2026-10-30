"""End-to-end verification pipeline.

Steps
1. Load photos, keep usable ones, project positions to a local metric frame.
2. Turn every plate box into a sight line (camera position + compass direction).
3. Group detections of the same plate across consecutive photos (tracking).
4. Locate each plate where its sight lines cross (triangulation).
5. Optionally remove a constant GPS offset using plates that match an address.
6. Find the official address at each plate location and compare the numbers.
7. For each official address in view, report Correct / problem / not found.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ._version import __version__
from .addresses import load_addresses
from .config import Config
from .detections import empty_detections, load_detections
from .errors import VerificationError
from .geo import (
    LocalFrame,
    angle_to_pixel_fraction,
    bearing_deg,
    direction,
    pixel_azimuth_offset,
    side_of,
    triangulate,
    wrap180,
    wrap360,
)
from .matching import PinMatch, Pins, estimate_gps_offset, match_plate
from .metadata import Metadata, load_metadata, load_reviewed
from .statuses import Status, label
from .textnorm import base_number, display_number
from .tracking import Track, build_tracks, rays_consistent, track_triangulation


@dataclass
class VerificationResult:
    addresses: pd.DataFrame
    plates: pd.DataFrame
    detections: pd.DataFrame
    photos: pd.DataFrame
    expected_views: pd.DataFrame
    summary: dict
    mode: str


@dataclass
class _Plate:
    view: str
    tracks: list[Track]
    rows: list[int]
    seqs: list[int]
    origins: np.ndarray
    azimuths: np.ndarray
    plate_id: str = ""
    reading: str | None = None
    agreement: float = 0.0
    votes: dict = field(default_factory=dict)
    tri: object = None
    match: PinMatch | None = None
    location: np.ndarray | None = None
    located_by: str = ""
    side: str = ""
    status: str = ""
    raw_status: str = ""
    explanation: str = ""
    official: int | None = None
    official_distance: float | None = None
    confidence_score: float = 0.0
    mean_det_conf: float = 1.0
    mean_ocr_conf: float = 1.0


def _fmt_m(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f} m"


def _join(values) -> str:
    return ";".join(str(v) for v in values)


def _attach_geometry(dets: pd.DataFrame, meta: Metadata, photos: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    dets = dets.copy().reset_index(drop=True)
    extra = ["direction_deg", "hfov_deg", "pitch_deg", "gps_x", "gps_y", "azimuth_deg"]
    if dets.empty:
        for c in extra:
            dets[c] = pd.Series(dtype=float)
        dets["used"] = pd.Series(dtype=bool)
        dets["skip_reason"] = pd.Series(dtype=object)
        return dets
    views = meta.views.set_index(["picture_id", "view"])
    v = views.reindex(pd.MultiIndex.from_arrays([dets["picture_id"], dets["view"]]))
    for c in ("direction_deg", "hfov_deg", "pitch_deg"):
        dets[c] = v[c].to_numpy(dtype=float)
    p = photos.set_index("picture_id").reindex(dets["picture_id"])
    valid = p["valid"].fillna(False).to_numpy(dtype=bool)
    dets["gps_x"] = p["gps_x"].to_numpy(dtype=float)
    dets["gps_y"] = p["gps_y"].to_numpy(dtype=float)
    dets["skip_reason"] = np.where(valid, "", "photo skipped: " + p["skip_reason"].fillna("").astype(str).to_numpy())
    pitch = dets["pitch_deg"] if cfg.photos.pitch_positive_up else -dets["pitch_deg"]
    offset = pixel_azimuth_offset(
        dets["x_center"].astype(float),
        dets["y_center"].astype(float),
        dets["image_width"].astype(float),
        dets["image_height"].astype(float),
        dets["hfov_deg"],
        pitch,
        cfg.photos.projection,
    )
    dets["azimuth_deg"] = wrap360(dets["direction_deg"].to_numpy() + np.asarray(offset))
    dets["used"] = valid
    return dets


def _locate(origins: np.ndarray, azimuths: np.ndarray, cfg: Config):
    tri = triangulate(origins, azimuths, cfg.tracking.min_triangulation_angle_deg)
    if tri is None:
        return None
    t = cfg.tracking
    if np.any(tri.depths < t.min_depth_m) or np.any(tri.depths > t.max_depth_m) or tri.rms > t.max_track_residual_m:
        return None
    return tri


class _World:
    """Official addresses and corrected cameras in the local frame."""

    def __init__(self, addr: pd.DataFrame, pins: Pins, cams: np.ndarray, travel: np.ndarray):
        self.addr = addr
        self.pins = pins
        self.cams = cams
        self.travel = travel
        self.by_street_key: dict[tuple[str, str], list[int]] = {}
        self.by_key: dict[str, list[int]] = {}
        for j in range(len(pins)):
            self.by_street_key.setdefault((pins.streets[j], pins.keys[j]), []).append(j)
            self.by_key.setdefault(pins.keys[j], []).append(j)

    def side_at(self, point: np.ndarray) -> str:
        d = np.hypot(self.cams[:, 0] - point[0], self.cams[:, 1] - point[1])
        k = int(np.argmin(d))
        return "left" if side_of(point, self.cams[k], self.travel[k])[0] > 0 else "right"

    def nearest(self, candidates: list[int], point: np.ndarray) -> tuple[int, float]:
        d = np.hypot(self.pins.x[candidates] - point[0], self.pins.y[candidates] - point[1])
        k = int(np.argmin(d))
        return candidates[k], float(d[k])

    def label(self, j: int) -> str:
        return str(self.addr.at[j, "label"])


def _relaxed_match(plate: _Plate, world: _World, cfg: Config) -> None:
    """Conservative fallback; never replace an existing geometric assignment.

    This is tolerance-based register agreement, not independently proven truth.
    Keep the measured location, require two photos and confident agreement,
    and reject ambiguous street/number choices (including suffix duplicates).
    """
    limit = cfg.matching.relaxed_match_distance_m
    if limit <= 0 or plate.match.pin is not None or plate.reading is None or plate.tri is None:
        return
    if (len(set(plate.seqs)) < 2 or plate.agreement < max(0.8, cfg.decision.min_reading_agreement)
        or plate.mean_det_conf < max(0.7, cfg.decision.min_detection_conf)
        or plate.mean_ocr_conf < max(0.8, cfg.decision.min_ocr_conf)):
        return
    if not len(world.pins):
        return
    distances = np.linalg.norm(world.pins.xy() - plate.location, axis=1)
    # Do not override a nearby conflicting address, even if it failed facing/ray tests.
    if np.any((distances <= cfg.matching.max_match_distance_m) & (world.pins.keys != plate.reading)):
        return
    near = np.flatnonzero(distances <= limit)
    streets = set(world.pins.streets[j] for j in near)
    guard_radius = max(limit, cfg.matching.frontage_match_max_m)
    streets = set(world.pins.streets[j] for j in np.flatnonzero(distances <= guard_radius))
    if len(streets) != 1:
        return
    candidates = [int(j) for j in near if world.pins.keys[j] == plate.reading
                  and world.addr.at[int(j), "side"] == plate.side]
    if len(candidates) != 1:
        return
    j = candidates[0]
    plate.match = PinMatch(j, float(distances[j]), "multi-view tolerance (12 m maximum)", 1)


def _frontage_match(plate: _Plate, world: _World, cfg: Config) -> None:
    """Building-front rule: same number on a shop front or second door.

    Accept the official address with the plate number when the plate is closer
    to it than to any other number on the same side, within the limit, with a
    measured position (two photos) and a confident reading. Never replaces an
    existing assignment.
    """
    limit = cfg.matching.frontage_match_max_m
    if limit <= 0 or plate.match.pin is not None or plate.reading is None or plate.tri is None:
        return
    if (len(set(plate.seqs)) < 2 or plate.agreement < 0.8 or plate.mean_ocr_conf < 0.8
        or plate.mean_det_conf < cfg.decision.min_detection_conf or not len(world.pins)):
        return
    pins = world.pins
    dist = np.linalg.norm(pins.xy() - plate.location, axis=1)
    sides = world.addr["side"].to_numpy()
    base = base_number(plate.reading)
    if np.any((dist <= cfg.matching.max_match_distance_m) & (pins.keys != plate.reading)):
        return
    # Conservative corner guard: do not infer a street from the OCR digits.
    near = np.flatnonzero(dist <= limit)
    streets = set(pins.streets[j] for j in near)
    if len(streets) != 1:
        return
    street = next(iter(streets))
    own = [int(j) for j in near if pins.streets[j] == street and pins.keys[j] == plate.reading and sides[j] == plate.side]
    if len(own) != 1:
        return
    j = own[0]
    other = [k for k in range(len(pins)) if pins.streets[k] == street and sides[k] == plate.side and base_number(pins.keys[k]) != base]
    if other and float(np.min(dist[other])) <= dist[j]:
        return
    plate.match = PinMatch(j, float(dist[j]), "building front (closest own number)", 1)


def _partial_read(reading: str, key: str) -> bool:
    a, b = str(base_number(reading)), str(base_number(key))
    return len(a) < len(b) and (b.startswith(a) or b.endswith(a))


def _decide(plate: _Plate, world: _World, cfg: Config) -> None:
    m, pins = plate.match, world.pins
    pin, reading, loc = m.pin, plate.reading, plate.location
    expected = world.label(pin) if pin is not None else None
    shown = display_number(reading)
    official, official_d = None, None

    if reading is None:
        status = Status.UNREADABLE
        text = "A plate was found but its number cannot be read."
        if expected:
            text += f" The official address at this spot is {expected}."
    elif pin is not None and reading == pins.keys[pin]:
        status = Status.CORRECT
        text = f"The plate reads {shown}, the official number at this spot ({expected})."
    elif pin is not None and base_number(reading) == base_number(pins.keys[pin]):
        status = Status.SUFFIX_MISMATCH
        text = f"The plate reads {shown} but the official address at this spot is {expected}. Only the suffix differs."
    elif pin is not None and cfg.decision.partial_read_check and _partial_read(reading, pins.keys[pin]):
        status = Status.UNCERTAIN
        text = (
            f"The plate reads {shown}, but the official address at this spot is {expected}. "
            f"Part of the number was probably missed by the OCR (partly read)."
        )
    else:
        street = pins.streets[pin] if pin is not None else None
        if street is None and len(pins):
            street = pins.streets[world.nearest(list(range(len(pins))), loc)[0]]
        same = world.by_street_key.get((street, reading), [])
        here = f" The official address at this spot is {expected}." if expected else " No official point passed the geometric matching checks."
        if same:
            official, official_d = world.nearest(same, loc)
            if world.addr.at[official, "side"] != plate.side:
                status = Status.WRONG_SIDE
                text = (
                    f"The plate reads {shown}, but {world.label(official)} is on the other side of the street "
                    f"({official_d:.0f} m away).{here}"
                )
            elif official_d >= cfg.matching.out_of_place_min_m:
                status = Status.OUT_OF_PLACE
                text = (
                    f"The plate reads {shown}, but the official position of {world.label(official)} "
                    f"is {official_d:.0f} m away on the same side.{here}"
                )
            else:
                status = Status.UNCERTAIN
                text = (
                    f"The plate reads {shown}; the official position of {world.label(official)} is only "
                    f"{official_d:.1f} m away. This is probably a position error, not a wrong plate."
                )
        else:
            others = [j for j in world.by_key.get(reading, []) if pins.streets[j] != street]
            if others:
                official, official_d = world.nearest(others, loc)
                if official_d >= cfg.matching.out_of_place_min_m:
                    status = Status.OUT_OF_PLACE
                    text = (
                        f"The plate reads {shown}, a number of another street: {world.label(official)}, "
                        f"{official_d:.0f} m away.{here}"
                    )
                else:
                    status = Status.UNCERTAIN
                    text = (
                        f"The plate reads {shown}, which matches {world.label(official)} on the corner "
                        f"street ({official_d:.1f} m away). Check the corner by eye."
                    )
            elif pin is not None:
                status = Status.UNKNOWN_NUMBER
                street_name = world.addr.at[pin, "street_display"]
                text = f"The plate reads {shown}, which is not an official number on {street_name}.{here}"
            else:
                status = Status.NO_ADDRESS_NEARBY
                text = f"The plate reads {shown}. No official point passed the geometric checks, and no nearby number candidate was identified. This does not prove that the address does not exist."

    if m.method.startswith("building front"):
        text += (f" The plate is {m.distance_m:.0f} m from the official point but closer to it than to any other "
                 f"number on this side: probably a shop front or a second door of the same building.")
    if m.method.startswith("multi-view tolerance"):
        text += f" Tolerance-based register match ({m.distance_m:.1f} m); not independent proof of plate placement."

    plate.raw_status = status
    d = cfg.decision
    n_views = len(set(plate.seqs))
    notes = []
    if reading is not None and plate.agreement < d.min_reading_agreement:
        status = Status.UNCERTAIN
        notes.append(f"Readings disagree ({plate.agreement:.0%} agree: {_votes_text(plate.votes)}).")
    if status not in (Status.CORRECT, Status.UNREADABLE) and (
        plate.mean_det_conf < d.min_detection_conf or plate.mean_ocr_conf < d.min_ocr_conf
    ):
        status = Status.UNCERTAIN
        notes.append("Low detector or OCR confidence.")
    if (
        status == Status.OUT_OF_PLACE
        and n_views < d.min_views_out_of_place
        and (official_d or 0.0) < 2 * cfg.matching.out_of_place_min_m
    ):
        status = Status.UNCERTAIN
        notes.append(f"Seen in {n_views} photo only; not enough to call it out of place.")
    if d.strict_error_claims and status in (Status.OUT_OF_PLACE, Status.WRONG_SIDE) and (
        n_views < 2 or plate.tri is None or plate.agreement < 0.8 or plate.mean_ocr_conf < 0.8
    ):
        status = Status.UNCERTAIN
        notes.append("Not enough evidence to call it an error (needs 2 photos, a measured position and a confident reading).")
    if status == Status.UNCERTAIN and plate.raw_status in (Status.OUT_OF_PLACE, Status.WRONG_SIDE):
        candidate = world.label(official) if official is not None else expected
        distance = f" ({official_d:.1f} m from the estimated position)" if official_d is not None else ""
        text = (f"The plate reads {shown}. Placement remains unverified. "
                + (f"Register candidate: {candidate}{distance}. " if candidate else "")
                + "The available location evidence does not justify declaring the plate misplaced or on the wrong side.")
    if m.ambiguous and status != Status.CORRECT:
        notes.append("Two official addresses are almost equally close to this plate.")
    text += f" Seen in {n_views} photo{'s' if n_views != 1 else ''}."
    if notes:
        text += " " + " ".join(notes)

    plate.status = status
    plate.explanation = text
    plate.official = official
    plate.official_distance = official_d

    agreement = plate.agreement if reading is not None else 0.6
    geometry = 1.0 if plate.tri is not None else 0.8
    if m.method.startswith("multi-view tolerance"):
        geometry *= 0.7
    if m.method.startswith("building front"):
        geometry *= 0.8
    if m.ambiguous:
        geometry *= 0.85
    score = min(1.0, n_views / 2.0) * agreement * plate.mean_det_conf * plate.mean_ocr_conf * geometry
    plate.confidence_score = round(float(score), 3)


def _votes_text(votes: dict) -> str:
    parts = sorted(votes.items(), key=lambda kv: -kv[1])
    return ", ".join(f"{display_number(k)} x{v:.1f}" for k, v in parts)


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _coverage(world: _World, photos: pd.DataFrame, meta: Metadata, cfg: Config, reviewed_keys) -> pd.DataFrame:
    """One row per (address, photo view) where the address should be visible."""
    pins = world.pins
    columns = ["pin", "sequence_number", "picture_id", "view", "image", "angle_deg", "distance_m", "x_fraction"]
    if len(pins) == 0:
        return pd.DataFrame(columns=columns)
    valid = photos[photos["valid"]].set_index("picture_id")
    records = []
    c = cfg.coverage
    for view in cfg.photos.coverage_views:
        vv = meta.views[(meta.views["view"] == view) & meta.views["picture_id"].isin(valid.index)]
        if vv.empty:
            continue
        if reviewed_keys is not None:
            vv = vv[[(pid, view) in reviewed_keys for pid in vv["picture_id"]]]
            if vv.empty:
                continue
        cams = valid.loc[vv["picture_id"], ["x", "y"]].to_numpy(dtype=float)
        dirs = vv["direction_deg"].to_numpy(dtype=float)
        hfov = vv["hfov_deg"].to_numpy(dtype=float)
        dx = pins.x[:, None] - cams[None, :, 0]
        dy = pins.y[:, None] - cams[None, :, 1]
        dist = np.hypot(dx, dy)
        ang = wrap180(bearing_deg(dx, dy) - dirs[None, :])
        visible = (dist >= c.min_visible_m) & (dist <= c.max_visible_m) & (np.abs(ang) <= hfov[None, :] / 2 - c.edge_margin_deg)
        if cfg.addresses.use_facade_orientation:
            to_cam = bearing_deg(-dx, -dy)
            faces = np.abs(wrap180(to_cam - pins.facade[:, None])) <= c.max_facade_angle_deg
            visible &= faces | np.isnan(pins.facade)[:, None]
        pj, ci = np.nonzero(visible)
        for j, i in zip(pj, ci):
            row = vv.iloc[i]
            records.append(
                (
                    int(j),
                    int(row["sequence_number"]),
                    row["picture_id"],
                    view,
                    row["file"],
                    float(ang[j, i]),
                    float(dist[j, i]),
                    float(angle_to_pixel_fraction(ang[j, i], hfov[i], cfg.photos.projection)),
                )
            )
    return pd.DataFrame(records, columns=columns)


def _build_plates(tracks: list[Track], matches: list[PinMatch], cfg: Config) -> list[list[int]]:
    """Merge tracks matched to the same address (e.g. one misread frame)."""
    groups: dict[tuple, list[int]] = {}
    for k, (track, m) in enumerate(zip(tracks, matches)):
        key = (m.pin, track.view) if m.pin is not None else (None, k)
        groups.setdefault(key, []).append(k)
    plates: list[list[int]] = []
    for members in groups.values():
        members.sort(key=lambda k: tracks[k].first_seq)
        current = [members[0]]
        for k in members[1:]:
            seqs = set().union(*(tracks[j].seqs for j in current))
            ok = tracks[k].first_seq - max(seqs) <= cfg.tracking.max_frame_gap and not seqs & set(tracks[k].seqs)
            if ok:
                origins = np.vstack([tracks[j].origin_array() for j in current + [k]])
                azimuths = np.concatenate([tracks[j].azimuth_array() for j in current + [k]])
                ok, _ = rays_consistent(origins, azimuths, cfg)
            if ok:
                a = _locate(np.vstack([tracks[j].origin_array() for j in current]), np.concatenate([tracks[j].azimuth_array() for j in current]), cfg)
                b = track_triangulation(tracks[k], cfg)
                if a is not None and b is not None and np.hypot(*(a.point - b.point)) > cfg.tracking.merge_distance_m:
                    ok = False
            if ok:
                current.append(k)
            else:
                plates.append(current)
                current = [k]
        plates.append(current)
    return plates


def run_verification(
    metadata,
    addresses,
    detections=None,
    config: Config | None = None,
    reviewed=None,
    images_root=None,
) -> VerificationResult:
    """Run the verification. Without detections, runs in inspection mode
    (lists which addresses each crop should show)."""
    cfg = config if config is not None else Config()
    mode = "verify" if detections is not None else "inspect"
    warnings: list[str] = []

    meta = metadata if isinstance(metadata, Metadata) else load_metadata(metadata, cfg)
    photos = meta.photos.copy()
    valid = photos["valid"].to_numpy(dtype=bool)
    if not valid.any():
        raise VerificationError("No usable photo: every photo was skipped (see skip_reason in photos.csv).")
    frame = LocalFrame(float(photos.loc[valid, "lat"].mean()), float(photos.loc[valid, "lon"].mean()))
    gx, gy = frame.to_xy(photos["lat"].to_numpy(), photos["lon"].to_numpy())
    photos["gps_x"], photos["gps_y"] = gx, gy
    for view in cfg.photos.coverage_views:
        if view not in meta.view_names:
            warnings.append(f"View '{view}' is not in the metadata; it is ignored for coverage.")

    reviewed_keys = load_reviewed(reviewed, meta) if reviewed is not None else None

    dets = load_detections(detections, meta, images_root) if detections is not None else empty_detections()
    if not cfg.decision.compare_suffix and len(dets):
        dets["reading"] = [None if (r is None or (isinstance(r, float) and np.isnan(r))) else str(base_number(r)) for r in dets["reading"]]
    dets = _attach_geometry(dets, meta, photos, cfg)
    if reviewed_keys is not None and len(dets):
        reviewed_keys |= set(zip(dets["picture_id"].astype(str), dets["view"].astype(str)))
    used = dets[dets["used"].astype(bool)].reset_index().rename(columns={"index": "det_row"})

    # Official addresses around the usable photos
    vp = photos[valid]
    pad = cfg.addresses.scope_radius_m + 20.0
    dlat, dlon = frame.metres_to_degrees(pad)
    bbox = (vp["lat"].min() - dlat, vp["lon"].min() - dlon, vp["lat"].max() + dlat, vp["lon"].max() + dlon)
    addr = load_addresses(addresses, bbox=bbox)
    ax, ay = frame.to_xy(addr["lat"].to_numpy(), addr["lon"].to_numpy())
    raw_cams = vp[["gps_x", "gps_y"]].to_numpy(dtype=float)
    if len(addr):
        dmin = np.min(np.hypot(ax[:, None] - raw_cams[None, :, 0], ay[:, None] - raw_cams[None, :, 1]), axis=1)
        keep = dmin <= cfg.addresses.scope_radius_m
    else:
        keep = np.zeros(0, dtype=bool)
    addr = addr[keep].reset_index(drop=True)
    ax, ay = ax[keep], ay[keep]
    if not cfg.decision.compare_suffix:
        addr["key"] = [str(base_number(k)) for k in addr["key"]]
        warnings.append("Numbers only: suffixes (bis, ter, A) are not compared.")
    if addr.empty:
        warnings.append("No official address near the photos. Check that the address file covers this area.")
    pins = Pins(
        x=ax,
        y=ay,
        keys=addr["key"].to_numpy(dtype=object),
        streets=addr["street_id"].astype(str).to_numpy(dtype=object),
        facade=addr["facade_bearing_deg"].to_numpy(dtype=float),
    )

    # Tracking on raw GPS positions
    used["cam_x"], used["cam_y"] = used["gps_x"], used["gps_y"]
    tracks = build_tracks(used, cfg)

    # GPS offset calibration
    if mode == "verify":
        tris = [track_triangulation(t, cfg) for t in tracks]
        offset, calibration = estimate_gps_offset(
            [t.point if t is not None else None for t in tris], [t.reading for t in tracks], pins, cfg
        )
    else:
        offset = np.zeros(2)
        calibration = {"enabled": bool(cfg.calibration.enabled), "applied": False, "reason": "inspection mode"}
    for track in tracks:
        track.shift(float(offset[0]), float(offset[1]))
    used["cam_x"] = used["gps_x"] + offset[0]
    used["cam_y"] = used["gps_y"] + offset[1]
    photos["x"] = photos["gps_x"] + offset[0]
    photos["y"] = photos["gps_y"] + offset[1]
    lat_c, lon_c = frame.to_latlon(photos["x"].to_numpy(), photos["y"].to_numpy())
    photos["lat_corrected"], photos["lon_corrected"] = lat_c, lon_c

    vp = photos[photos["valid"]]
    cams = vp[["x", "y"]].to_numpy(dtype=float)
    travel = vp["travel_bearing"].to_numpy(dtype=float)
    if len(pins):
        d = np.hypot(pins.x[:, None] - cams[None, :, 0], pins.y[:, None] - cams[None, :, 1])
        near = np.argmin(d, axis=1)
        sides = side_of(pins.xy(), cams[near], travel[near])
        addr["side"] = np.where(sides > 0, "left", "right")
    else:
        addr["side"] = pd.Series(dtype=object)
    world = _World(addr, pins, cams, travel)

    # Plates
    matches = []
    for track in tracks:
        tri = track_triangulation(track, cfg)
        matches.append(
            match_plate(track.origin_array(), track.azimuth_array(), tri.point if tri else None, track.reading, pins, cfg)
        )
    plates: list[_Plate] = []
    for members in _build_plates(tracks, matches, cfg):
        trs = [tracks[k] for k in members]
        rows = [r for t in trs for r in t.rows]
        plates.append(
            _Plate(
                view=trs[0].view,
                tracks=trs,
                rows=rows,
                seqs=[s for t in trs for s in t.seqs],
                origins=np.vstack([t.origin_array() for t in trs]),
                azimuths=np.concatenate([t.azimuth_array() for t in trs]),
            )
        )
    plates.sort(key=lambda p: (min(p.seqs), p.view))

    for n, plate in enumerate(plates, start=1):
        plate.plate_id = f"P{n:04d}"
        sub = used.iloc[plate.rows]
        votes: dict[str, float] = {}
        for reading, weight in zip(sub["reading"], sub["ocr_conf"].astype(float)):
            if isinstance(reading, str):
                votes[reading] = votes.get(reading, 0.0) + max(float(weight), 1e-6)
        plate.votes = votes
        if votes:
            best = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            plate.reading = best[0]
            plate.agreement = best[1] / sum(votes.values())
        plate.mean_det_conf = float(sub["det_conf"].astype(float).mean())
        plate.mean_ocr_conf = float(sub["ocr_conf"].astype(float).mean())
        plate.tri = _locate(plate.origins, plate.azimuths, cfg)
        plate.match = match_plate(
            plate.origins, plate.azimuths, plate.tri.point if plate.tri else None, plate.reading, pins, cfg
        )
        mid = len(plate.origins) // 2
        o, dvec = plate.origins[mid], direction(plate.azimuths[mid])
        if plate.tri is not None:
            plate.location, plate.located_by = plate.tri.point, "sight lines crossing"
        elif plate.match.pin is not None:
            pin_xy = pins.xy()[plate.match.pin]
            depth = max(float(np.dot(pin_xy - o, dvec)), cfg.tracking.min_depth_m)
            plate.location, plate.located_by = o + depth * dvec, "single sight line"
        else:
            plate.location, plate.located_by = o + cfg.tracking.nominal_depth_m * dvec, "assumed distance"
        if plate.view in ("left", "right"):
            plate.side = plate.view
        else:
            plate.side = world.side_at(plate.location) if len(cams) else ""
        if mode == "verify":
            _relaxed_match(plate, world, cfg)
            _frontage_match(plate, world, cfg)
            _decide(plate, world, cfg)
        for row in plate.rows:
            used.at[row, "plate_id"] = plate.plate_id

    # Coverage
    cover = _coverage(world, photos, meta, cfg, reviewed_keys)
    plates_by_pin: dict[int, list[_Plate]] = {}
    for plate in plates:
        if plate.match is not None and plate.match.pin is not None:
            plates_by_pin.setdefault(plate.match.pin, []).append(plate)

    # Address results
    address_rows = []
    in_view = cover.groupby("pin")["sequence_number"].apply(lambda s: sorted(set(int(v) for v in s))).to_dict() if len(cover) else {}
    for j in sorted(set(in_view) | set(plates_by_pin)):
        seen = in_view.get(j, [])
        assigned = plates_by_pin.get(j, [])
        notes = ""
        if mode == "inspect":
            status = Status.IN_VIEW
            text = f"Should be visible in {len(seen)} photo(s): {', '.join(map(str, seen))}."
            confidence, score = "", None
        elif assigned:
            correct = [p for p in assigned if p.status == Status.CORRECT]
            main = max(correct or assigned, key=lambda p: (p.confidence_score, len(p.seqs)))
            status, text = main.status, main.explanation
            score = main.confidence_score
            confidence = _confidence_label(score)
            others = [p for p in assigned if p is not main]
            if others:
                notes = "Other plate(s) at this address: " + "; ".join(
                    f"{p.plate_id} reads {display_number(p.reading)} ({label(p.status)})" for p in others
                )
        elif len(seen) >= cfg.coverage.min_views_for_missing:
            status = Status.NOT_FOUND
            text = (
                f"No plate was found although this address was in view in {len(seen)} photos "
                f"({', '.join(map(str, seen))}). The plate may be missing, hidden or too small to read."
            )
            confidence, score = ("high" if len(seen) >= 3 else "medium"), None
        else:
            status = Status.NOT_COVERED
            text = (
                f"In view in {len(seen)} photo(s) only; at least {cfg.coverage.min_views_for_missing} "
                "are needed to report a missing plate."
            )
            confidence, score = "", None
        a = addr.loc[j]
        address_rows.append(
            {
                "address_id": a["address_id"],
                "address": a["label"],
                "street": a["street_display"],
                "street_id": a["street_id"],
                "number": display_number(a["key"]),
                "side": a["side"],
                "is_corner": bool(a["is_corner"]),
                "lat": float(a["lat"]),
                "lon": float(a["lon"]),
                "facade_bearing_deg": None if pd.isna(a["facade_bearing_deg"]) else round(float(a["facade_bearing_deg"]), 1),
                "photos_in_view": _join(seen),
                "n_photos_in_view": len(seen),
                "plates": _join(p.plate_id for p in assigned),
                "readings": _join(display_number(p.reading) for p in assigned),
                "status": status,
                "status_label": label(status),
                "confidence": confidence,
                "confidence_score": score,
                "explanation": text,
                "notes": notes,
                "_sort": (str(a["street_display"]), int(a["number"]), str(a["key"])),
            }
        )
    address_df = pd.DataFrame(address_rows)
    if len(address_df):
        address_df = address_df.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)
    else:
        address_df = pd.DataFrame(columns=["address_id", "address", "status"])

    plate_df = _plates_table(plates, used, world, frame, mode)
    det_df = _detections_table(dets, used, frame)
    photo_df = _photos_table(photos, dets)
    expected_df = _expected_views_table(cover, world)

    summary = {
        "tool": "plateverif",
        "version": __version__,
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "photos": {
            "total": int(len(photos)),
            "usable": int(photos["valid"].sum()),
            "skipped": int((~photos["valid"]).sum()),
            "skip_reasons": photos.loc[~photos["valid"], "skip_reason"].value_counts().to_dict(),
            "reviewed_views": None if reviewed_keys is None else len(reviewed_keys),
        },
        "detections": {
            "total": int(len(dets)),
            "used": int(len(used)),
            "ignored": int(len(dets) - len(used)),
            "unreadable": int(sum(1 for r in used["reading"] if not isinstance(r, str))) if len(used) else 0,
        },
        "plates": {
            "total": len(plates),
            "by_status": plate_df["status"].value_counts().to_dict() if len(plate_df) and mode == "verify" else {},
        },
        "addresses": {
            "in_scope": int(len(addr)),
            "reported": int(len(address_df)),
            "by_status": address_df["status"].value_counts().to_dict() if len(address_df) else {},
        },
        "calibration": calibration,
        "frame_origin": {"lat": frame.lat0, "lon": frame.lon0},
        "config": cfg.to_dict(),
        "warnings": warnings,
    }
    return VerificationResult(
        addresses=address_df,
        plates=plate_df,
        detections=det_df,
        photos=photo_df,
        expected_views=expected_df,
        summary=summary,
        mode=mode,
    )


def _plates_table(plates: list[_Plate], used: pd.DataFrame, world: _World, frame: LocalFrame, mode: str) -> pd.DataFrame:
    rows = []
    for p in plates:
        lat, lon = frame.to_latlon(p.location[0], p.location[1])
        pin = p.match.pin if p.match else None
        official = p.official
        o_lat = o_lon = None
        if official is not None:
            o_lat, o_lon = float(world.addr.at[official, "lat"]), float(world.addr.at[official, "lon"])
        sub = used.iloc[p.rows]
        rows.append(
            {
                "plate_id": p.plate_id,
                "view": p.view,
                "side": p.side,
                "reading": p.reading or "",
                "reading_display": display_number(p.reading),
                "reading_agreement": round(p.agreement, 3) if p.reading else None,
                "readings": _votes_text(p.votes) if p.votes else "",
                "n_detections": len(p.rows),
                "n_photos": len(set(p.seqs)),
                "photos": _join(sorted(set(p.seqs))),
                "images": _join(sub["image"]),
                "lat": float(lat),
                "lon": float(lon),
                "located_by": p.located_by,
                "position_error_m": round(p.tri.rms, 2) if p.tri is not None else None,
                "sight_line_angle_deg": round(p.tri.angle_spread_deg, 1) if p.tri is not None else None,
                "address_id": world.addr.at[pin, "address_id"] if pin is not None else "",
                "expected_address": world.label(pin) if pin is not None else "",
                "match_distance_m": round(p.match.distance_m, 2) if pin is not None else None,
                "match_method": p.match.method if p.match else "",
                "ambiguous_match": bool(p.match.ambiguous) if p.match else False,
                "status": p.status if mode == "verify" else "",
                "status_label": label(p.status) if mode == "verify" else "",
                "raw_status": p.raw_status,
                "confidence": _confidence_label(p.confidence_score) if mode == "verify" else "",
                "confidence_score": p.confidence_score if mode == "verify" else None,
                "explanation": p.explanation,
                "official_address_of_reading": world.label(official) if official is not None else "",
                "official_distance_m": round(p.official_distance, 1) if p.official_distance is not None else None,
                "official_lat": o_lat,
                "official_lon": o_lon,
                "mean_det_conf": round(p.mean_det_conf, 3),
                "mean_ocr_conf": round(p.mean_ocr_conf, 3),
                "detection_ids": _join(sub["det_id"]),
            }
        )
    return pd.DataFrame(rows)


def _detections_table(dets: pd.DataFrame, used: pd.DataFrame, frame: LocalFrame) -> pd.DataFrame:
    out = dets.copy()
    out["plate_id"] = ""
    out["cam_lat"] = np.nan
    out["cam_lon"] = np.nan
    if len(used):
        rows = used["det_row"].to_numpy()
        if "plate_id" in used.columns:
            out.loc[rows, "plate_id"] = used["plate_id"].fillna("").to_numpy()
        lat, lon = frame.to_latlon(used["cam_x"].to_numpy(), used["cam_y"].to_numpy())
        out.loc[rows, "cam_lat"] = lat
        out.loc[rows, "cam_lon"] = lon
    out["reading_display"] = [display_number(r) if isinstance(r, str) else "unreadable" for r in out["reading"]]
    keep = [
        "det_id", "image", "picture_id", "sequence_number", "view", "text", "reading_display",
        "x_center", "y_center", "box_width", "box_height", "image_width", "image_height",
        "det_conf", "ocr_conf", "source", "azimuth_deg", "used", "skip_reason", "plate_id", "cam_lat", "cam_lon",
    ]
    return out[[c for c in keep if c in out.columns]]


def _photos_table(photos: pd.DataFrame, dets: pd.DataFrame) -> pd.DataFrame:
    counts = dets["picture_id"].value_counts() if len(dets) else pd.Series(dtype=int)
    out = photos[
        ["sequence_number", "picture_id", "datetime", "lat", "lon", "lat_corrected", "lon_corrected",
         "travel_bearing", "distance_to_street_m", "valid", "skip_reason", "source_url"]
    ].copy()
    out["n_detections"] = out["picture_id"].map(counts).fillna(0).astype(int)
    return out


def _expected_views_table(cover: pd.DataFrame, world: _World) -> pd.DataFrame:
    columns = ["sequence_number", "picture_id", "view", "image", "n_expected", "expected_addresses", "expected_positions"]
    if cover.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for (seq, pid, view, image), g in cover.sort_values("x_fraction").groupby(["sequence_number", "picture_id", "view", "image"], sort=True):
        rows.append(
            {
                "sequence_number": int(seq),
                "picture_id": pid,
                "view": view,
                "image": image,
                "n_expected": len(g),
                "expected_addresses": "; ".join(world.label(int(j)) for j in g["pin"]),
                "expected_positions": "; ".join(
                    f"{display_number(world.pins.keys[int(j)])} at {x:.0%} of width, {d:.0f} m"
                    for j, x, d in zip(g["pin"], g["x_fraction"], g["distance_m"])
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)
