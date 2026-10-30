# Contributing to UAV Address Verification

Thank you for your interest in this project. This repository is a research prototype combining computer vision and geospatial verification for automated address inspection.

## How to Contribute

### 1. Reporting Issues & Feedback
- If you find a bug or have questions regarding the prototype, please check existing [GitHub Issues](https://github.com/Abdelmalek-Beladam/uav-address-verification/issues).
- You can open an issue detailing reproduction steps, expected behavior, and environment details.

### 2. Proposing Improvements
1. Fork the repository and clone your fork locally:
```bash
git clone https://github.com/<your-username>/uav-address-verification.git
cd uav-address-verification
```
2. Set up the Python environment:
```bash
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```
3. Create a feature branch for your changes:
```bash
git checkout -b feature/improvement
```
4. Run the automated test suite to ensure all tests pass:
```bash
python -m unittest discover -s tests -t .
```
5. Submit a Pull Request describing your proposed changes.

## Code Guidelines
- Keep core verification logic in `src/plateverif/` modular and accompanied by unit tests.
- The web viewer in `website/` uses dependency-free vanilla JavaScript and CSS to ensure simple, direct execution without a build step.
