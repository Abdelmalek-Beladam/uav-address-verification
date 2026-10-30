# Selected detector

Selected artifact: best.pt. SHA-256: `27ce0faed13002bf5fdd363a4e49d0cfa7edbce5b7a613da4ae09fb82446764b`.

The user pipeline checkpoint is byte-identical to Amira's yolo26n_img1280_b8_s0/weights/best.pt. File size: 5,567,237 bytes. Trained base: yolo26n.pt; image size 1280; batch 8; seed 0. The selected run's args and results contain 50 epochs. The best recorded validation mAP50-95 row is epoch 30, not proof of a 30-epoch-only run.

Recorded validation metrics at that row: precision 0.77984; recall 0.78159; mAP50 0.83681; mAP50-95 0.62608.

Recorded split=test comparison: precision 0.9170657413672552; recall 0.7979862035711002; mAP50 0.8634139868050539; mAP50-95 0.6409994775003226. These are historical detector metrics, not OCR or address-verification accuracy. Multiple models were compared on this split; no new independent final test was run here.

Selection is an accuracy/size/runtime trade-off. The larger YOLO26s 960 batch-8 entry has higher saved mAP, so do not claim YOLO26n wins every metric. Recorded inference timing is specific to that saved evaluation and is not a minimum-PC or UAV benchmark.

This audit compares files without loading pickle-based checkpoints. No inference was run and no new performance numbers were created. Dataset/model/code licensing must be checked before public distribution; no new licence is assigned here.
