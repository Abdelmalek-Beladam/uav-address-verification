# Execution guide

## Website only
Use OPEN_DASHBOARD.bat or the HTTP-server command in README.md. Do not install YOLO, PaddleOCR, Node dependencies or create a new environment for the static website.

## Saved-result reproduction
Use tools/reproduce_saved_release.py with a NEW output folder outside the repo. It preserves source results and runs verification only. Requirements.txt covers this CPU stage, not the full image pipeline.

## Future full image processing
Use an existing compatible Colab inference environment. The selected detector is models/selected_detector/best.pt (available in releases). The official address snapshot and configuration are included. A street ZIP must contain metadata.csv and its referenced left/right images, camera directions and source identifiers.

Example from the repository root, with NEW output and work folders:

`powershell
python tools/run_street.py --zip "C:\StreetData\new_street.zip" --name new_street --model models/selected_detector/best.pt --out "C:\StreetRuns\new_street_run01" --work "C:\StreetWork\new_street_run01"
`

The equivalent Colab command uses the actual existing Drive ZIP and output paths. A new output/work folder avoids mixing an older extraction or run. Do not rerun the two completed streets to test interface changes. Check a small subset before processing a long sequence.

requirements-inference.in is a declared dependency input, not a tested historical lock. The supplied notebook did not freeze exact PaddleOCR/PaddlePaddle versions. tools/capture_environment.py records versions from whichever environment actually runs it without installing or importing model frameworks. Record the real environment before the next planned processing run; do not invent historical pins or rebuild a working environment merely to collect them.

The first OCR-model load may require internet to obtain pretrained OCR assets. These assets are not bundled in the repository.

## Development tests
Run the Python tests in the existing verification environment with PYTHONPATH=src. On PowerShell: $env:PYTHONPATH="src". Browser tests use Node/Playwright/Chromium and are not a prerequisite for opening the app. Never commit .venv or API keys.
