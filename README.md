# AI-Powered UAV for Automated Address Detection & Verification

[![Live Demo](https://img.shields.io/badge/Demo-Live_Dashboard-blue?style=for-the-badge&logo=googlechrome&logoColor=white)](https://abdelmalek-beladam.github.io/uav-address-verification/)
[![Release](https://img.shields.io/github/v/release/Abdelmalek-Beladam/uav-address-verification?style=for-the-badge&color=success)](https://github.com/Abdelmalek-Beladam/uav-address-verification/releases)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE.md)

An end-to-end computer vision and geospatial verification system designed for municipal address inspection and drone-assisted urban inventory. The system detects house number plates from street imagery, reads plate numbers via optical character recognition, triangulates observed camera positions, and cross-references candidate addresses against official municipal address registers.

---

## 🌐 Live Demonstration

Explore the interactive review dashboard directly in your browser without installing dependencies:

👉 **[Launch Live Demo Workspace](https://abdelmalek-beladam.github.io/uav-address-verification/)**

---

## 🚀 Key Capabilities

- **High-Resolution Object Detection**: Fine-tuned YOLO26n detector trained on high-resolution (1280px) urban street imagery for robust detection of house number plates across varying lighting and angles.
- **OCR Recognition & Safety Abstention**: Integrated PaddleOCR recognition pipeline equipped with conservative digit validation to prevent false positives on ambiguous or partially obscured plates.
- **Geospatial Triangulation & Matching**: Associates multi-view detections with camera positions, calculates spatial offsets, and matches estimated plate coordinates against the official municipal address register.
- **Interactive Review Workspace**: Lightweight, dependency-free browser interface featuring route playback, street map inspection, multi-angle evidence comparison, localized note-taking, and CSV/GeoJSON exports.

---

## 🧠 Model Checkpoint

The fine-tuned detector weights (est.pt) are available on the [Releases Page](https://github.com/Abdelmalek-Beladam/uav-address-verification/releases/tag/v1.0.0):

| Model | Input Size | Parameters | Size | mAP50 | Precision | Recall | Download |
|---|---|---|---|---|---|---|---|
| **YOLO26n** (fine-tuned) | 1280×1280 | 2.53M | 5.31 MB | **86.3%** | **91.7%** | **79.8%** | [v1.0.0 Release](https://github.com/Abdelmalek-Beladam/uav-address-verification/releases/tag/v1.0.0) |

To run fresh inference, download est.pt and place it in models/selected_detector/best.pt. See [docs/RUN_GUIDE.md](docs/RUN_GUIDE.md) for execution details.

---

## 💻 Quickstart

### 1. Run the Web Dashboard Locally

No machine learning frameworks or Node.js required:

`powershell
# Clone the repository
git clone https://github.com/Abdelmalek-Beladam/uav-address-verification.git
cd uav-address-verification

# Start a local HTTP server
python -m http.server 8088 --directory website --bind 127.0.0.1
`

Open **[http://127.0.0.1:8088/](http://127.0.0.1:8088/)** in your browser. *(On Windows, you can also double-click OPEN_DASHBOARD.bat)*.

### 2. Python Verification Environment & Tests

For geospatial verification and running tests:

`ash
# Create and activate virtual environment
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run unit tests
python -m unittest discover -s tests -t .
`

---

## 📁 Repository Structure

`	ext
├── src/plateverif/       # Core Python library: matching, triangulation, verification
├── website/              # Production browser review dashboard & map interface
├── models/               # Model card and configuration specifications
├── data/                 # Sample Paris municipal address extract & metadata
├── evidence/             # Training evaluation metrics, confusion matrices, PR curves
├── docs/                 # System architecture, data formats, and guides
├── tools/                # Pipeline runners and dashboard generation utilities
└── tests/                # Unit and regression test suite
`

---

## 👥 Authors & Team

Developed by:
- **Abdelmalek Beladam** — Project Lead, Geospatial Pipeline Integration & Web Dashboard Architecture
- **Amira Benmoussa** — Computer Vision Engineering & YOLO26n Model Training
- **Khaoula Ghaleth** — Geomatics Research & Problem Methodology
- **Ines Ait Dris** — UI/UX Product Design & Inspection Workflow
- **Naila Sadaoui** — OCR Pipeline & Verification Logic

---

## 📜 License & Data Credits

- Code is licensed under the [MIT License](LICENSE.md).
- **Street Imagery**: Panoramax open imagery platform (licensed under Licence Ouverte / Etalab 2.0).
- **Address Data**: Ville de Paris Open Data — Base Adresse Nationale (ODbL).
- **Map Tiles**: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
