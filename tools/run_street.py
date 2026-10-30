"""Run the full automatic pipeline on one street downloaded with panoramax_split.

Steps
  1. unzip the street (left_side/, right_side/, metadata.csv)
  2. detect house-number plates with the YOLO model (best.pt)
  3. read the number on every plate with PaddleOCR (recognition only, digits kept)
  4. verify the numbers against the official Paris addresses (plateverif)
  5. export the files used by the website (small photos, plate crops, results)

Example
  python tools/run_street.py --zip "/content/drive/MyDrive/yolo_runs/Rue_Bonaparte (2).zip" \
      --name rue_bonaparte --model best.pt --out /content/out/rue_bonaparte

This script never deletes files. Existing output files are overwritten only
inside the --out folder given on the command line.
"""

from __future__ import annotations

import argparse
import os
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
VIEWS = ("left", "right")
OCR_MODEL = "en_PP-OCRv5_mobile_rec"
SOURCE = "yolo26n+en_ppocrv5+3prep"
DETECTION_COLUMNS = [
    "image", "view", "x_min", "y_min", "x_max", "y_max", "image_width", "image_height",
    "text", "det_conf", "ocr_conf", "source",
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- 1. unzip
def find_street(root: Path) -> Path:
    found = sorted(root.rglob("metadata.csv"), key=lambda p: len(p.parts))
    if not found:
        raise SystemExit(f"No metadata.csv found under {root}")
    return found[0].parent


def extract(zip_path: Path, work: Path) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    marker = work / ".extracted"
    if not marker.exists():
        log(f"Unzipping {zip_path.name} ...")
        with zipfile.ZipFile(zip_path) as z:
            # Validate all members before extracting any user-supplied street files.
            for member in z.infolist():
                clean = member.filename.replace("\\", "/")
                target = (work / clean).resolve()
                mode = member.external_attr >> 16
                if (clean.startswith("/") or re.match(r"^[A-Za-z]:", clean)
                        or ".." in Path(clean).parts
                        or not target.is_relative_to(work.resolve())
                        or (mode & 0o170000) == 0o120000):
                    raise SystemExit("Unsafe street ZIP member; nothing was extracted: " + member.filename)
            z.extractall(work)
        marker.write_text(str(zip_path))
    else:
        log("Street already unzipped, reusing it.")
    return find_street(work)


def list_views(street: Path) -> pd.DataFrame:
    meta = pd.read_csv(street / "metadata.csv")
    rows = []
    for _, r in meta.iterrows():
        for view in VIEWS:
            rel = r.get(f"{view}_file")
            if isinstance(rel, str) and rel.strip():
                path = street / rel.replace("\\", "/")
                if path.exists():
                    rows.append({"rel": rel.replace("\\", "/"), "view": view, "path": str(path),
                                 "sequence_number": int(r["sequence_number"])})
    views = pd.DataFrame(rows)
    if views.empty:
        raise SystemExit("No left/right crop found next to metadata.csv")
    return views.sort_values(["sequence_number", "view"]).reset_index(drop=True)


# ---------------------------------------------------------------- 3. OCR helpers
def load_ocr():
    from paddleocr import TextRecognition

    return TextRecognition(model_name=OCR_MODEL)


def _field(res, key):
    try:
        return res[key]
    except Exception:
        pass
    data = getattr(res, "json", None)
    if callable(data):
        data = data()
    if isinstance(data, dict):
        data = data.get("res", data)
        return data.get(key)
    return None


def plate_crop(img: np.ndarray, box, pad: float) -> np.ndarray:
    import cv2

    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    px, py = (x2 - x1) * pad, (y2 - y1) * pad
    x1, y1 = int(max(0, x1 - px)), int(max(0, y1 - py))
    x2, y2 = int(min(w, x2 + px)), int(min(h, y2 + py))
    crop = img[y1:y2, x1:x2]
    if crop.size and crop.shape[0] < 64:
        scale = 64.0 / crop.shape[0]
        crop = cv2.resize(crop, (max(1, int(crop.shape[1] * scale)), 64), interpolation=cv2.INTER_CUBIC)
    return np.ascontiguousarray(crop)


def digits_of(text: str) -> str:
    """Accept a whole reading, never a fragment from ambiguous raw OCR."""
    if str(REPO / "src") not in sys.path: sys.path.insert(0,str(REPO / "src"))
    from plateverif.ocr_safety import numeric_reading
    return numeric_reading(text)


def ocr_variants(crop: np.ndarray) -> list[np.ndarray]:
    """As is, 3x bigger with more contrast, and 3x bigger inverted (dark digits on light)."""
    import cv2

    big = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
    lab = cv2.cvtColor(big, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = cv2.createCLAHE(2.0, (4, 4)).apply(lab[:, :, 0])
    big = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    inv = cv2.cvtColor(255 - cv2.cvtColor(big, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    return [crop, np.ascontiguousarray(big), np.ascontiguousarray(inv)]


def read_plate(ocr, crops: list[np.ndarray]) -> tuple[str, float, str]:
    """Read a padded and a tight crop, each in 3 versions, then vote.

    Each digit reading gets the sum of its scores, so a number read by several
    versions beats a single confident partial read ("1" instead of "17").
    Ties go to the longer number. The confidence is the best score of the winner.
    """
    images = [v for crop in crops if crop.size for v in ocr_variants(crop)]
    if not images:
        return ("", 0.0, "")
    votes: dict[str, list[float]] = {}
    raws: dict[str, str] = {}
    first_raw = ""
    for out in ocr.predict(input=images, batch_size=len(images)):
        raw = str(_field(out, "rec_text") or "")
        score = float(_field(out, "rec_score") or 0.0)
        first_raw = first_raw or raw
        num = digits_of(raw)
        if num:
            votes.setdefault(num, []).append(score)
            if score >= max(votes[num]):
                raws[num] = raw
    if not votes:
        return ("", 0.0, first_raw)
    win = max(votes, key=lambda n: (sum(votes[n]), len(n), max(votes[n])))
    return (win, max(votes[win]), raws[win])


# ---------------------------------------------------------------- 2+3. detect and read
def detect(views: pd.DataFrame, model_path: Path, out: Path, conf: float, imgsz: int, batch: int) -> pd.DataFrame:
    import cv2
    from ultralytics import YOLO

    try:
        import torch
        device = 0 if torch.cuda.is_available() else "cpu"
    except Exception:
        device = "cpu"
    log(f"Detector: {model_path} on {'GPU' if device == 0 else 'CPU'}, imgsz {imgsz}, conf {conf}")
    model = YOLO(str(model_path))
    log(f"OCR: PaddleOCR {OCR_MODEL} (recognition only)")
    ocr = load_ocr()

    plates_dir = out / "web" / "plates"
    plates_dir.mkdir(parents=True, exist_ok=True)
    rows, extra = [], []
    paths = views["path"].tolist()
    t0 = time.time()
    for start in range(0, len(paths), batch):
        chunk = views.iloc[start:start + batch]
        results = model.predict(source=chunk["path"].tolist(), imgsz=imgsz, conf=conf, device=device, verbose=False)
        for (_, v), r in zip(chunk.iterrows(), results):
            boxes = r.boxes
            if boxes is None or len(boxes) == 0:
                continue
            img = cv2.imread(v["path"])
            h, w = img.shape[:2]
            xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else np.asarray(boxes.xyxy)
            confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else np.asarray(boxes.conf)
            for k, (box, dc) in enumerate(zip(xyxy, confs)):
                x1, y1, x2, y2 = [float(c) for c in box]
                x1, y1, x2, y2 = max(0.0, x1), max(0.0, y1), min(float(w), x2), min(float(h), y2)
                if x2 - x1 < 2 or y2 - y1 < 2:
                    continue
                padded = plate_crop(img, (x1, y1, x2, y2), 0.15)
                tight = plate_crop(img, (x1, y1, x2, y2), 0.0)
                text, oc, raw = read_plate(ocr, [padded, tight])
                crop_name = f"{Path(v['rel']).stem}_{k}.jpg"
                cv2.imwrite(str(plates_dir / crop_name), padded, [cv2.IMWRITE_JPEG_QUALITY, 85])
                rows.append({
                    "image": v["rel"], "view": v["view"],
                    "x_min": round(x1, 1), "y_min": round(y1, 1), "x_max": round(x2, 1), "y_max": round(y2, 1),
                    "image_width": w, "image_height": h,
                    "text": text, "det_conf": round(float(dc), 4), "ocr_conf": round(oc, 4), "source": SOURCE,
                })
                extra.append({"image": v["rel"], "box": k, "plate_crop": f"plates/{crop_name}", "ocr_raw_text": raw})
        done = min(start + batch, len(paths))
        if done % (batch * 10) < batch or done == len(paths):
            log(f"  {done}/{len(paths)} photos, {len(rows)} plates so far ({time.time() - t0:.0f} s)")
    dets = pd.DataFrame(rows, columns=DETECTION_COLUMNS)
    dets.to_csv(out / "detections.csv", index=False)
    pd.DataFrame(extra, columns=["image", "box", "plate_crop", "ocr_raw_text"]).to_csv(out / "web" / "plate_crops.csv", index=False)
    log(f"Detections written: {len(dets)} plates, {int((dets['text'] != '').sum())} with a number read")
    return dets


# ---------------------------------------------------------------- 4. verify
def verify(street: Path, addresses: Path, out: Path, config: Path) -> Path:
    res = out / "results"
    cmd = [sys.executable, "-m", "plateverif", "verify",
           "--metadata", str(street / "metadata.csv"), "--addresses", str(addresses),
           "--detections", str(out / "detections.csv"), "--config", str(config), "--out", str(res)]
    log("Verifying against the official addresses ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src") + ((os.pathsep + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
    done = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(done.stdout[-3000:])
    if done.returncode != 0:
        print(done.stderr[-3000:])
        raise SystemExit("Verification failed (see the message above)")
    return res


# ---------------------------------------------------------------- 5. website files
def export_web(views: pd.DataFrame, street: Path, out: Path, res: Path, name: str, thumb_width: int) -> None:
    from PIL import Image

    web = out / "web"
    (web / "views").mkdir(parents=True, exist_ok=True)
    (web / "data").mkdir(parents=True, exist_ok=True)
    for f in ["summary.json", "addresses.csv", "plates.csv", "detections.csv", "photos.csv",
              "expected_views.csv", "results.geojson", "report.html"]:
        if (res / f).exists():
            shutil.copy2(res / f, web / "data" / f)
    shutil.copy2(street / "metadata.csv", web / "data" / "metadata.csv")
    log(f"Making small photos for the website (width {thumb_width}px) ...")
    for p, rel in zip(views["path"], views["rel"]):
        target = web / "views" / Path(rel).name
        with Image.open(p) as im:
            im = im.convert("RGB")
            scale = thumb_width / im.width
            im.resize((thumb_width, max(1, round(im.height * scale)))).save(target, quality=72, optimize=True)
    manifest = {"street": name, "photos": int(views["sequence_number"].nunique()), "views": len(views),
                "thumb_width": thumb_width, "ocr_model": OCR_MODEL, "source": SOURCE,
                "suffix_checked": False, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    (web / "manifest.json").write_text(json.dumps(manifest, indent=2))


def print_summary(res: Path, name: str) -> None:
    addr = pd.read_csv(res / "addresses.csv") if (res / "addresses.csv").exists() else pd.DataFrame()
    plates = pd.read_csv(res / "plates.csv") if (res / "plates.csv").exists() else pd.DataFrame()
    print("\n========== SUMMARY:", name, "==========")
    for label, df in (("Addresses", addr), ("Plates", plates)):
        if not df.empty and "status" in df.columns:
            print(f"{label} ({len(df)}):")
            print(df["status"].value_counts().to_string())
    print("========================================\n")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", required=True, help="street zip from panoramax_split")
    ap.add_argument("--name", required=True, help="short name, e.g. rue_bonaparte")
    ap.add_argument("--model", required=True, help="YOLO best.pt")
    ap.add_argument("--addresses", default=str(REPO / "data" / "adresse_paris.csv"))
    ap.add_argument("--config", default=str(REPO / "config" / "numbers_only.toml"))
    ap.add_argument("--out", required=True, help="output folder")
    ap.add_argument("--work", default="/content/streets", help="where streets are unzipped")
    ap.add_argument("--conf", type=float, default=0.5)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--thumb-width", type=int, default=480)
    ap.add_argument("--skip-detect", action="store_true", help="reuse detections.csv already in --out")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    street = extract(Path(a.zip), Path(a.work) / a.name)
    views = list_views(street)
    log(f"{a.name}: {views['sequence_number'].nunique()} photos, {len(views)} left/right crops in {street}")
    if not (a.skip_detect and (out / "detections.csv").exists()):
        detect(views, Path(a.model), out, a.conf, a.imgsz, a.batch)
    res = verify(street, Path(a.addresses), out, Path(a.config))
    export_web(views, street, out, res, a.name, a.thumb_width)
    print_summary(res, a.name)
    log(f"Done. Output in {out}")


if __name__ == "__main__":
    main()
