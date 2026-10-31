# AI-Powered UAV for Automated Address Detection & Verification

[![Live Demo](https://img.shields.io/badge/Demo-Live_Dashboard-blue?style=for-the-badge&logo=googlechrome&logoColor=white)](https://abdelmalek-beladam.github.io/uav-address-verification/)
[![Release](https://img.shields.io/github/v/release/Abdelmalek-Beladam/uav-address-verification?style=for-the-badge&color=success)](https://github.com/Abdelmalek-Beladam/uav-address-verification/releases)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Inspection_Only-lightgrey.svg?style=for-the-badge)](LICENSE.md)

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

The fine-tuned detector weights (`best.pt`) are available on the [Releases Page](https://github.com/Abdelmalek-Beladam/uav-address-verification/releases/tag/v1.0.0):

| Model | Input Size | Parameters | Size | mAP50 | Precision | Recall | Download |
|---|---|---|---|---|---|---|---|
| **YOLO26n** (fine-tuned) | 1280×1280 | 2.53M | 5.31 MB | **86.3%** | **91.7%** | **79.8%** | [v1.0.0 Release](https://github.com/Abdelmalek-Beladam/uav-address-verification/releases/tag/v1.0.0) |

To run fresh inference, download `best.pt` and place it in `models/selected_detector/best.pt`. See [docs/RUN_GUIDE.md](docs/RUN_GUIDE.md) for execution details.

---

## 💻 Quickstart

### 1. Run the Web Dashboard Locally

No machine learning frameworks or Node.js required:

```powershell
# Clone the repository
git clone https://github.com/Abdelmalek-Beladam/uav-address-verification.git
cd uav-address-verification

# Start a local HTTP server
python -m http.server 8088 --directory website --bind 127.0.0.1
```

Open **[http://127.0.0.1:8088/](http://127.0.0.1:8088/)** in your browser. *(On Windows, you can also double-click `OPEN_DASHBOARD.bat`)*.

### 2. Python Verification Environment & Tests

For geospatial verification and running tests:

```bash
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
```

---

## 📁 Repository Structure

```text
├── src/plateverif/       # Core Python library: matching, triangulation, verification
├── website/              # Production browser review dashboard & map interface
├── models/               # Model card and configuration specifications
├── data/                 # Sample Paris municipal address extract & metadata
├── evidence/             # Training evaluation metrics, confusion matrices, PR curves
├── docs/                 # System architecture, data formats, and guides
├── tools/                # Pipeline runners and dashboard generation utilities
└── tests/                # Unit and regression test suite
```

---

## 👥 Team Contributions

- **Khaoula Ghaleth** (*Project Leadership & Methodology*): Led project methodology and technical planning, team supervision, and coordination. Provided project documentation for data collection, annotation, and models development. Participated in detection models development using three techniques, including YOLO11n, YOLO26n and Faster R-CNN. Proposed a UAV simulation testing in a virtual environment. Proposed the development of a Decision Support System and provided functional and technical dashboard design. Contributed to submission preparation.

- **Abdelmalek Beladam** (*Project Coordination & End-To-End Prototype Development*): Coordinated the project and led end-to-end prototype development. Conducted data research, sourced the street survey imagery from Panoramax, and manually annotated the complete dataset across training, validation, and testing splits. Participated in developing, training, and evaluating the YOLO11n and YOLO11s plate detection models, built and tested OCR recognition pipelines with PaddleOCR, and reviewed OCR examples and failure cases. Integrated the selected detector, OCR processing, and geospatial verification workflow, handling street-survey processing and result exports against official Paris address records. Developed and tested the entire interactive web demonstrator and review dashboard, created the GitHub repository, set up automated testing and technical documentation, and contributed to submission preparation.

- **Amira Benmoussa** (*AI Models Development*): Contributed to the development, training, and evaluation of YOLO26n and YOLO26s model for address-plate detection.

- **Ines Ait Dris** (*AI Models Research & Development*): Provided models documentation and contributed to the development, training, and evaluation of YOLO11s model.

- **Naila Sadaoui** (*Data Research & AI Models Development*): Conducted data research and contributed to the development, training, and evaluation of YOLO11n model, for address-plate detection.

---

## 📜 License & Data Credits

- **Software License**: The source code and repository materials are made available for evaluation and inspection only. All rights reserved. No commercial reuse or redistribution license is granted without explicit written permission. See [LICENSE.md](LICENSE.md).
- **Street Imagery**: Panoramax open imagery platform (licensed under Licence Ouverte / Etalab 2.0).
- **Address Data**: Ville de Paris Open Data — Base Adresse Nationale (ODbL).
- **Map Tiles**: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
