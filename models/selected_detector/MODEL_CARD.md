# Model Card: Fine-Tuned YOLO26n Address Plate Detector

## Overview
This model is a fine-tuned **YOLO26n** (nano) object detector specialized for detecting house number plates on building facades from street-level and low-altitude imagery.

- **Architecture**: Ultralytics YOLO26n
- **Input Resolution**: 1280×1280 pixels
- **Parameters**: 2,533,886 (2.53M)
- **Model Checkpoint Size**: 5.31 MB (est.pt)
- **Training Epochs**: 50 epochs (batch size 8, initial lr 0.01)
- **SHA-256**: 27ce0faed13002bf5fdd363a4e49d0cfa7edbce5b7a613da4ae09fb82446764b

## Evaluation Metrics

Evaluated on the benchmark test split:

| Metric | Score |
|---|---|
| **Precision** | **91.71%** |
| **Recall** | **79.80%** |
| **mAP@50** | **86.34%** |
| **mAP@50-95** | **64.10%** |
| **Average Inference Time** | 15.8 ms (Tesla T4) |

## Training Configuration
- **Base weights**: Pretrained yolo26n.pt
- **Optimizer**: Auto (SGD/AdamW)
- **Data Augmentation**: Mosaic enabled for first 40 epochs; closed mosaic for final 10 epochs.

## Intended Use
- Automated detection of house number plates on facades.
- Generating cropped regions-of-interest for downstream OCR recognition (e.g., PaddleOCR).
- Drone/UAV street surveying and municipal GIS updating.

## Download & Usage
The trained weights are hosted on [GitHub Releases](https://github.com/Abdelmalek-Beladam/uav-address-verification/releases/tag/v1.0.0). Download est.pt and place it in models/selected_detector/best.pt.
