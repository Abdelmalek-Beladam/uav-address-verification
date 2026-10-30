# Execution & Inference Guide

This guide covers running the web dashboard, running the geospatial verification engine, and processing new street surveys.

## 1. Web Dashboard (Review Workspace)
The review workspace is static and runs without machine learning dependencies:
```bash
python -m http.server 8088 --directory website --bind 127.0.0.1
```
Open http://127.0.0.1:8088/ in your browser.

## 2. Geospatial Verification Engine
To run verification against the municipal address register using CPU:
```bash
# Setup environment
python -m venv .venv
# Activate:
.\.venv\Scripts\Activate.ps1    # Windows
source .venv/bin/activate       # Linux/macOS

pip install -r requirements.txt
```

### Reproduce Saved Verification:
```bash
python tools/reproduce_saved_release.py --out ./reproduced_output
```
This replays the verification engine across preserved detections and cross-references them with municipal address coordinates.

## 3. Fresh Image Inference Pipeline
To run end-to-end detection and OCR on a newly recorded street survey:

1. Download best.pt from the GitHub Releases page and save it to `models/selected_detector/best.pt`.
2. Prepare survey imagery with associated GPS metadata (`metadata.csv`).
3. Run the processing pipeline:
```bash
python tools/run_street.py --zip "/path/to/street_data.zip" --name "survey_name" --model "models/selected_detector/best.pt" --out "./output_run" --work "./work_dir"
```

## 4. Running Tests
To run the automated test suite:
```powershell
python -m unittest discover -s tests -t .
```
