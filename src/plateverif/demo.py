"""Synthetic demo on Rue des Grands-Augustins (Paris 6e).

The official address extract is real (Ville de Paris open data). The photos,
GPS errors and plate detections are SYNTHETIC. They exist only to test the
method end to end and must never be presented as real results.

Injected situations on the demo street:
  * no plate at number 9                     -> Plate not found
  * plate "12 bis" at number 12              -> Suffix mismatch
  * plate "18" at number 14                  -> Out of place
  * one frame of number 17 misread as "11"   -> still Correct (vote)
  * plate "20" at number 19                  -> Wrong side
  * plate "123" at number 23                 -> Unknown number
  * unreadable plate at number 25            -> Unreadable
  * extra plate with a number that does not exist, far from any address -> No address here
  * the first photo is the real photo 1, 24 m from the street -> skipped
  * every GPS position is shifted by a constant 2.2 m plus noise
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from importlib import resources
from pathlib import Path

import numpy as np
import pandas as pd

from .addresses import load_addresses
from .geo import LocalFrame, bearing_deg, direction, wrap180
from .statuses import Status
from .textnorm import display_number

DEMO_STREET_ID = "750004691"
EXTRACT_FILE = "paris_extract_grands_augustins.csv"
IMAGE_WIDTH, IMAGE_HEIGHT = 1600, 1200
CAMERA_HEIGHT_M = 2.2
PLATE_HEIGHT_M = 2.8
PLATE_WIDTH_M = 0.30
PLATE_TALL_M = 0.22
PHOTO_SPACING_M = 4.0
GPS_BIAS_M = (1.8, -1.2)
GPS_NOISE_M = 0.6
HEADING_NOISE_DEG = 1.0
SIDE_HFOV, SIDE_PITCH = 80.0, -8.0
FORWARD_HFOV, FORWARD_PITCH = 90.0, -3.0

REMOVED = {"9"}
INJECTED_TEXT = {"12": "12 bis", "14": "18", "19": "20", "23": "123", "25": "?"}
OCR_SLIP = ("17", "11")
EXTRA_PLATE_CANDIDATES = ("48", "56", "64", "72", "96", "98")
EXPECTED_STATUS = {
    "9": Status.NOT_FOUND,
    "12": Status.SUFFIX_MISMATCH,
    "14": Status.OUT_OF_PLACE,
    "17": Status.CORRECT,
    "19": Status.WRONG_SIDE,
    "23": Status.UNKNOWN_NUMBER,
    "25": Status.UNREADABLE,
}

REAL_FIRST_ROW = {
    "sequence_number": 1,
    "picture_id": "7dbe4267-1e9c-413d-9f4a-ae2924170947",
    "sequence_id": "cb2825a3-372d-4ed1-9b73-53d8dbdc2c9d",
    "datetime": "2025-05-05T05:42:35.931000+00:00",
    "longitude": 2.340770699,
    "latitude": 48.8547647,
    "distance_to_street_m": 24.221,
    "travel_bearing": 136.735,
    "panorama_azimuth": 133,
    "source_url": "https://panoramax.ign.fr/api/pictures/7dbe4267-1e9c-413d-9f4a-ae2924170947/hd.jpg",
    "original_360_file": "rue_grands_augustins_complete_dataset\\original_360\\000001_7dbe4267-1e9c-413d-9f4a-ae2924170947.jpg",
    "forward_file": "rue_grands_augustins_complete_dataset\\forward\\000001_forward.jpg",
    "forward_global_direction": 136.735,
    "forward_relative_yaw": 3.735,
    "forward_horizontal_fov": 90,
    "forward_pitch": -3,
    "left_file": "rue_grands_augustins_complete_dataset\\left_side\\000001_left.jpg",
    "left_global_direction": 46.735,
    "left_relative_yaw": -86.265,
    "left_horizontal_fov": 80,
    "left_pitch": -8,
    "right_file": "rue_grands_augustins_complete_dataset\\right_side\\000001_right.jpg",
    "right_global_direction": 226.735,
    "right_relative_yaw": 93.735,
    "right_horizontal_fov": 80,
    "right_pitch": -8,
}


def extract_path() -> Path:
    """Path of the bundled real address extract around the demo street."""
    return Path(str(resources.files("plateverif") / "data" / EXTRACT_FILE))


def _camera_axes(azimuth_deg: float, pitch_deg: float):
    a, t = np.radians(azimuth_deg), np.radians(pitch_deg)
    forward = np.array([np.sin(a) * np.cos(t), np.cos(a) * np.cos(t), np.sin(t)])
    right = np.array([np.cos(a), -np.sin(a), 0.0])
    up = np.array([-np.sin(a) * np.sin(t), -np.cos(a) * np.sin(t), np.cos(t)])
    return forward, right, up


def make_demo(out_dir: str | Path, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pins = load_addresses(extract_path())
    on = (pins["street_id"] == DEMO_STREET_ID).to_numpy()
    if not on.any():
        raise RuntimeError("Demo street not found in the bundled extract")
    frame = LocalFrame(float(pins.loc[on, "lat"].mean()), float(pins.loc[on, "lon"].mean()))
    px, py = frame.to_xy(pins["lat"].to_numpy(), pins["lon"].to_numpy())

    # Route along the (curved) street centre line, from the quai southwards.
    pts = np.column_stack([px[on], py[on]])
    centre = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - centre)
    axis = vt[0] / np.linalg.norm(vt[0])
    if axis[1] > 0:
        axis = -axis
    left = np.array([-axis[1], axis[0]])
    along = (pts - centre) @ axis
    lateral = (pts - centre) @ left
    numbers = pins.loc[on, "number"].to_numpy()
    odd = numbers % 2 == 1
    side = np.where(odd, 1.0, -1.0)
    scale = max(float(np.abs(along).max()), 1.0)
    tt = along / scale
    design = np.column_stack([np.ones_like(tt), tt, tt**2, tt**3, side])
    coef, *_ = np.linalg.lstsq(design, lateral, rcond=None)
    half_width = float(coef[4])

    def centre_lateral(a):
        u = np.asarray(a, dtype=float) / scale
        return coef[0] + coef[1] * u + coef[2] * u**2 + coef[3] * u**3

    def centre_slope(a):
        u = np.asarray(a, dtype=float) / scale
        return (coef[1] + 2 * coef[2] * u + 3 * coef[3] * u**2) / scale

    def tangent_bearing(a):
        t = axis[None, :] + np.atleast_1d(centre_slope(a))[:, None] * left[None, :]
        return bearing_deg(t[:, 0], t[:, 1])

    stations = np.arange(along.min() - 6.0, along.max() + 8.0, PHOTO_SPACING_M)
    true_xy = centre + np.outer(stations, axis) + np.outer(centre_lateral(stations), left)
    travel = np.asarray(tangent_bearing(stations), dtype=float) % 360
    n = len(true_xy)
    measured_xy = true_xy + np.array(GPS_BIAS_M) + rng.normal(0.0, GPS_NOISE_M, size=(n, 2))
    true_heading = travel + rng.normal(0.0, HEADING_NOISE_DEG, size=n)

    # Plates in the synthetic world: one per official address, plus injected cases.
    keys = pins["key"].to_numpy()
    streets = pins["street_id"].to_numpy()
    facades = pins["facade_bearing_deg"].to_numpy(dtype=float)
    plates = []
    for j in range(len(pins)):
        text = display_number(keys[j])
        if streets[j] == DEMO_STREET_ID:
            if keys[j] in REMOVED:
                continue
            text = INJECTED_TEXT.get(keys[j], text)
        shift = rng.normal(0.0, 0.4)
        along_facade = direction(facades[j] + 90.0) if np.isfinite(facades[j]) else np.zeros(2)
        plates.append(
            {"key": keys[j], "street": streets[j], "x": px[j] + shift * along_facade[0], "y": py[j] + shift * along_facade[1], "facade": facades[j], "text": text}
        )
    # Extra plate on the even side, as far as possible from any official address,
    # with a number that does not exist in the extract.
    extra_text = next(t for t in EXTRA_PLATE_CANDIDATES if t not in set(keys))
    cand = np.linspace(along.min() + 5.0, along.max() - 5.0, 300)
    cand_xy = centre + np.outer(cand, axis) + np.outer(centre_lateral(cand) - half_width, left)
    gap = np.min(np.hypot(cand_xy[:, None, 0] - px[None, :], cand_xy[:, None, 1] - py[None, :]), axis=1)
    best = int(np.argmax(gap))
    extra_facade = float((tangent_bearing(cand[best])[0] - 90.0) % 360)
    plates.append(
        {"key": None, "street": DEMO_STREET_ID, "x": cand_xy[best, 0], "y": cand_xy[best, 1], "facade": extra_facade, "text": extra_text}
    )

    # Project plates into the left and right crops.
    focal = (IMAGE_WIDTH / 2.0) / np.tan(np.radians(SIDE_HFOV / 2.0))
    detections = []
    for i in range(n):
        seq = i + 2
        for view, sign in (("left", -1.0), ("right", 1.0)):
            fwd, right, up = _camera_axes(true_heading[i] + sign * 90.0, SIDE_PITCH)
            for k, plate in enumerate(plates):
                v = np.array([plate["x"] - true_xy[i, 0], plate["y"] - true_xy[i, 1], PLATE_HEIGHT_M - CAMERA_HEIGHT_M])
                depth = float(v @ fwd)
                if depth < 1.5 or np.hypot(v[0], v[1]) > 17.0:
                    continue
                oblique = 0.0
                if np.isfinite(plate["facade"]):
                    oblique = abs(float(wrap180(bearing_deg(-v[0], -v[1]) - plate["facade"])))
                    if oblique > 75.0:
                        continue
                x = IMAGE_WIDTH / 2.0 + focal * float(v @ right) / depth
                y = IMAGE_HEIGHT / 2.0 - focal * float(v @ up) / depth
                if not (0.02 * IMAGE_WIDTH <= x <= 0.98 * IMAGE_WIDTH and 0.02 * IMAGE_HEIGHT <= y <= 0.98 * IMAGE_HEIGHT):
                    continue
                bw = focal * PLATE_WIDTH_M * np.cos(np.radians(oblique)) / depth
                bh = focal * PLATE_TALL_M / depth
                if bw < 9.0:
                    continue
                detections.append(
                    {
                        "plate": k,
                        "sequence_number": seq,
                        "image": f"{seq:06d}_{view}.jpg",
                        "x_min": round(x - bw / 2, 1),
                        "y_min": round(y - bh / 2, 1),
                        "x_max": round(x + bw / 2, 1),
                        "y_max": round(y + bh / 2, 1),
                        "image_width": IMAGE_WIDTH,
                        "image_height": IMAGE_HEIGHT,
                        "text": plate["text"],
                        "det_conf": 0.9,
                        "ocr_conf": 0.9,
                        "source": "demo",
                    }
                )
    det_df = pd.DataFrame(detections)
    slip_plate = next(k for k, p in enumerate(plates) if p["street"] == DEMO_STREET_ID and p["key"] == OCR_SLIP[0])
    slip_rows = det_df.index[det_df["plate"] == slip_plate].tolist()
    if len(slip_rows) >= 3:
        r = slip_rows[len(slip_rows) // 2]
        det_df.loc[r, "text"] = OCR_SLIP[1]
        det_df.loc[r, "ocr_conf"] = 0.55
    det_df = det_df.drop(columns=["plate"]).sort_values(["sequence_number", "image", "x_min"]).drop(columns=["sequence_number"])

    # Metadata in the same format as the real dataset.
    lat_m, lon_m = frame.to_latlon(measured_xy[:, 0], measured_xy[:, 1])
    rel = measured_xy - centre
    dist_street = np.abs(rel @ left - centre_lateral(rel @ axis))
    t0 = datetime(2025, 5, 5, 5, 43, 0, tzinfo=timezone.utc)
    rows = [REAL_FIRST_ROW]
    for i in range(n):
        seq = i + 2
        stem = "rue_grands_augustins_demo"
        rows.append(
            {
                "sequence_number": seq,
                "picture_id": f"demo-{seq:06d}",
                "sequence_id": "demo-sequence",
                "datetime": (t0 + timedelta(seconds=2 * i)).isoformat(),
                "longitude": round(float(lon_m[i]), 9),
                "latitude": round(float(lat_m[i]), 9),
                "distance_to_street_m": round(float(dist_street[i]), 3),
                "travel_bearing": round(float(travel[i]), 3),
                "panorama_azimuth": round(float(travel[i]) - 3.735, 3),
                "source_url": "",
                "original_360_file": f"{stem}\\original_360\\{seq:06d}_demo.jpg",
                "forward_file": f"{stem}\\forward\\{seq:06d}_forward.jpg",
                "forward_global_direction": round(float(travel[i]) % 360, 3),
                "forward_relative_yaw": 3.735,
                "forward_horizontal_fov": FORWARD_HFOV,
                "forward_pitch": FORWARD_PITCH,
                "left_file": f"{stem}\\left_side\\{seq:06d}_left.jpg",
                "left_global_direction": round(float(travel[i] - 90) % 360, 3),
                "left_relative_yaw": -86.265,
                "left_horizontal_fov": SIDE_HFOV,
                "left_pitch": SIDE_PITCH,
                "right_file": f"{stem}\\right_side\\{seq:06d}_right.jpg",
                "right_global_direction": round(float(travel[i] + 90) % 360, 3),
                "right_relative_yaw": 93.735,
                "right_horizontal_fov": SIDE_HFOV,
                "right_pitch": SIDE_PITCH,
            }
        )
    meta_path = out / "metadata_demo.csv"
    det_path = out / "detections_demo.csv"
    pd.DataFrame(rows).to_csv(meta_path, index=False)
    det_df.to_csv(det_path, index=False)
    truth = {
        "warning": "SYNTHETIC DATA - for testing the method only",
        "street_id": DEMO_STREET_ID,
        "gps_bias_east_north_m": list(GPS_BIAS_M),
        "gps_noise_m": GPS_NOISE_M,
        "heading_noise_deg": HEADING_NOISE_DEG,
        "photo_spacing_m": PHOTO_SPACING_M,
        "expected_status_by_number": EXPECTED_STATUS,
        "extra_plate": {"text": extra_text, "expected": Status.NO_ADDRESS_NEARBY, "nearest_address_m": round(float(gap[best]), 1)},
        "photos": n + 1,
        "detections": int(len(det_df)),
    }
    truth_path = out / "truth.json"
    truth_path.write_text(json.dumps(truth, indent=2), encoding="utf-8")
    return {"metadata": meta_path, "detections": det_path, "addresses": extract_path(), "truth": truth_path}
