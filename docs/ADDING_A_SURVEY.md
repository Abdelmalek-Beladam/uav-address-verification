# Add another real survey

This is developer documentation, not website copy.

1. Obtain the sequence and retain its source metadata, left/right image paths, pose conventions, contributor attribution and licence.
2. Check a small portion for metadata/projection compatibility and plate visibility before processing the full long sequence. This is a compatibility check, not a new accuracy claim.
3. Process it in the existing Colab YOLO/PaddleOCR/verification pipeline with the existing trained checkpoint. Do not call inference training.
4. Inspect matched, unresolved and intersection cases. Record its development/training/independent-test role accurately.
5. Preserve the original outputs. Add the completed directory under website/surveys/<id>/ with detections.csv, results/ and web/ in the existing format.
6. Add the human-readable survey name and confirmed role to LABELS in tools/build_dashboard_data.py. Run python tools/build_dashboard_data.py --site website.
7. Check counts, source links, crop joins, runtime/load size, both image views, playback and attribution. The current exporter expects the existing crop-manifest/image ordering; do not import an unrelated export schema without validating it.

Do not put full-resolution sequence ZIPs, model runs, private files or a new .venv into the static website. Retain the full source in a documented dataset location and serve the necessary review thumbnails/crops. A long sequence is a new dataset addition, not a reason to rewrite the UI.
