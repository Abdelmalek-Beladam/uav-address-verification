# UAV Address Verification

Inspection software for reading visible house numbers, comparing their estimated positions with an official address register, and reviewing the evidence behind each case.

Developed for **AI-Powered UAV for Automated Addressing Detection & Verification**. The current prototype uses recorded Paris imagery. UAV acquisition is the next stage, not an implemented flight capability.

## Open the demo locally

From the repository root, using an existing Python installation:

```powershell
py -m http.server 8088 --directory website --bind 127.0.0.1
```

Open **http://127.0.0.1:8088/**. On macOS/Linux, use `python3` in place of `py`. On Windows, `OPEN_DASHBOARD.bat` is an alternative. No ML packages, Node build, account or API key are required for the website. Keep the server console open. Do not open index.html by double-clicking: browsers restrict fetching local JSON.

## What works

- Offline processing: selected fine-tuned YOLO26n detector, pretrained PaddleOCR `en_PP-OCRv5_mobile_rec`, crop preprocessing, multi-view grouping, position estimates and conservative numeric verification.
- Browser: source views and plate crops, register candidates, map inspection, filters, browser-local notes, CSV/JSON exports and recorded route playback.
- Saved-result reproduction from preserved detector rows, without rerunning detection or OCR.

**The website reads saved outputs.** It does not perform new inference or accept uploaded photos. Playback is not simulated live model processing. Aerial acquisition, flight control, onboard inference, street-name recognition and a shared review backend are not implemented.

## Data and interpretation

| Display label | Stable dataset ID | Role |
|---|---|---|
| Saint-Germain · Route 01 | `rue_bonaparte` | Development/demo material, multiple streets |
| Saint-Sulpice · Route 02 | `rue_de_four` | Training-area material, multiple streets |

Area names are not claims that each recording covers a single street. Stable IDs and saved artifacts remain unchanged. The recordings contain 743 capture positions and 299 plate groups; these are coverage counts, **not accuracy**.

A recognised number, a register candidate and a reliable location are separate checks. The number 33 example remains **Needs review**. Route 02 is not an independent test. See [Evaluation](docs/EVALUATION.md) for actual historical comparisons and their limits.

## Setup for verification and tests

Do not replace an existing working inference environment just to open the website. For a new CPU verification environment only:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH="src"
python -m unittest discover -s tests -t .
python tools/check_handoff.py
```

On Linux/macOS: `python3 -m venv .venv`, `source .venv/bin/activate`, install the same requirements, then `PYTHONPATH=src python -m unittest discover -s tests -t .`.

Reproduce saved verification with a **new output folder outside this repo**:

```powershell
python tools/reproduce_saved_release.py --out "C:\UAV-Verification-Reproduction"
```

This replays 21 documented OCR safety abstentions, reruns verification and compares five CSV tables per recording with the saved revised release. It does not validate OCR accuracy or execute the models. Original evidence is preserved under `archive/baseline_v1/`.

## Run fresh inference

See [Running and environment notes](docs/RUN_GUIDE.md), [input formats](docs/DATA_FORMATS.md) and [adding a recording](docs/ADDING_A_SURVEY.md). A suitable detector checkpoint is required. The public preparation excludes the selected binary while redistribution permission remains unconfirmed. Its SHA-256 and actual configuration remain in `models/model_registry.json`. Obtain it from the maintainers with permission, then place it at `models/selected_detector/best.pt`.

`requirements-inference.in` is a declared dependency input, not a validated exact historical lock. PaddleOCR assets may download on first use. Test a small batch in a compatible environment before a long run. Neither free-server nor user-PC performance has been established.

## Repository map

- `src/plateverif/`: CPU geographic matching, evidence rules and reports.
- `tools/`: ingestion, image-processing runner, site-data builder and saved-result reproduction.
- `website/`: dependency-free browser application and saved demo assets.
- `config/`, `data/`: verification rules and attributed Paris reference snapshot.
- `evidence/`: actual detector comparisons, selected training log and OCR diagnostics.
- `models/`: checkpoint identity/configuration and model card, not all experimental weights.
- `notebooks/source_evidence/`: historical source-only notebooks, **not** a supported Run All installation.
- `tests/`: Python unit/contract tests and optional browser regression tests.
- `submission/`: concise current project description, contributions, stack/prior-work disclosure and recording script.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [architecture](docs/ARCHITECTURE.md) and [formats](docs/DATA_FORMATS.md). Keep inference outputs immutable for UI-only changes. Do not rename stored IDs or regenerate results merely to change presentation. A new dataset needs its own provenance and overlap/role assessment. See [SECURITY.md](SECURITY.md) for reporting sensitive issues.

## Deployment and rights

The static site can be hosted on GitHub Pages without hosting the models. [Deployment guide](docs/DEPLOYMENT.md) covers the workflow and public-release checks. Prepared files are **not proof of an actual deployment**. Add the final public demo URL to the GitHub repository About field once deployed.

Public GitHub publication redistributes files even before Pages is enabled. Check [credits](docs/DATA_CREDITS.md) and [publication preflight](docs/PUBLICATION.md) before making a repository public. No project-wide open-source licence is granted until the maintainers choose one; third-party licences remain separate. See LICENSE.md and THIRD_PARTY_NOTICES.md.

## Team and development tools

[Specific human contributions](submission/TEAM_ROLES.md) and [AI tools, stack and prior work](submission/TOOLS_AND_PRIOR_WORK.md) are recorded separately. This is an AI-assisted student project, not a claim of entirely unaided development.
