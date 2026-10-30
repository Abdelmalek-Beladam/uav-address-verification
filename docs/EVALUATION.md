# Evaluation and model selection

## Historical detector comparison

These are actual saved comparison rows supplied with Amira's training artifacts. Results compare trained YOLO26 nano/small configurations, image size and batch size. They are not a new run performed during packaging.

| Model | Image size | Batch | mAP50 | mAP50–95 | Precision | Recall | Recorded ms/image | Weight MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| yolo26n.pt | 640 | 16 | 0.8249 | 0.5538 | 0.8981 | 0.7726 | 4.37 | 5.44 |
| yolo26s.pt | 640 | 16 | 0.8209 | 0.5902 | 0.8957 | 0.7526 | 9.48 | 20.30 |
| yolo26n.pt | 960 | 16 | 0.8633 | 0.6297 | 0.9149 | 0.7757 | 8.94 | 5.49 |
| yolo26n.pt | 960 | 8 | 0.8260 | 0.6013 | 0.9034 | 0.7629 | 8.19 | 5.49 |
| yolo26n.pt | 1280 | 8 | 0.8634 | 0.6410 | 0.9171 | 0.7980 | 15.80 | 5.57 |
| yolo26n.pt | 640 | 32 | 0.8043 | 0.5489 | 0.9214 | 0.7216 | 3.90 | 5.44 |
| yolo26s.pt | 960 | 16 | 0.8451 | 0.6336 | 0.9401 | 0.7784 | 20.86 | 20.35 |
| yolo26s.pt | 960 | 8 | 0.8684 | 0.6633 | 0.9116 | 0.7629 | 22.16 | 20.35 |

Selected: YOLO26n, image size 1280, batch 8, seed 0. Its checkpoint SHA-256 is `27ce0faed13002bf5fdd363a4e49d0cfa7edbce5b7a613da4ae09fb82446764b` (5,567,237 bytes). The original training log contains 50 epochs; the best recorded validation mAP50–95 row is epoch 30.

The 960/batch-8 small model has higher mAP, so the nano model must not be called the most accurate. Nano was selected as a compact quality/size trade-off. Its recorded weight size is 5.57 MB versus 20.35 MB for that small model. Recorded times belong to the historical evaluation environment, **not** a browser, UAV or free-hosting benchmark. Other binary checkpoints are unnecessary for explaining these comparisons.

Model selection reused the split labelled `test`. These rows are therefore historical selection evidence, not a fresh unbiased final holdout after selection. Dataset split membership is not bundled, so exact full retraining is not promised.

## OCR evidence

The implementation uses pretrained PaddleOCR `en_PP-OCRv5_mobile_rec`, not a newly trained OCR model. `evidence/ocr_diagnostics/` retains the actual diagnostic tables. The 180-row variant table is 30 items × 6 variants, not 180 independent examples. The small human-labelled exercise had 22 readable examples, five non-house-number examples and three unresolved cases. Earlier exact agreement was 11/22 on readable crops; EasyOCR digit filtering was 3/22 and also returned digits for all five non-house-number examples. These small development diagnostics are not final unbiased OCR accuracy.

Blanket I→1/O→0 conversion was not adopted. The revised release abstains on 21 suspicious raw-reading rows and reruns verification; it does not hand-pick final labels. Original rows remain in `archive/baseline_v1/`, with a machine-readable change log.

## End-to-end limits

743 positions and 299 plate groups describe coverage. Pipeline statuses and register agreement are not ground truth. There is no established independent end-to-end accuracy, character-error rate, false-alert rate, cost saving, aerial performance or deployment throughput. Route 02 includes the detector training area; Route 01 is development/demo material. Neither should be presented as a new independent final test.

Saved-result reproduction establishes deterministic table agreement, not detector/OCR correctness. See `docs/QA_RELEASE.md` and the reproduced report.
