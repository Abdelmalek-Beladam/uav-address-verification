# Contributing to UAV Address Verification

Thank you for your interest in contributing! This project is an open-source prototype combining computer vision and geospatial verification for automated address auditing.

## How to Contribute

### 1. Reporting Bugs & Suggesting Enhancements
- Check existing [GitHub Issues](https://github.com/Abdelmalek-Beladam/uav-address-verification/issues) to see if the issue or idea has already been reported.
- If not, open a new Issue with a clear title, reproduction steps, expected behavior, and system details.

### 2. Proposing Changes (Pull Requests)
1. **Fork** the repository and clone your fork locally:
   `ash
   git clone https://github.com/<your-username>/uav-address-verification.git
   cd uav-address-verification
   `
2. **Create a virtual environment** and install dependencies:
   `ash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r requirements.txt
   `
3. **Create a feature branch**:
   `ash
   git checkout -b feature/your-feature-name
   `
4. **Make your changes** following PEP 8 style guidelines.
5. **Run the test suite** to ensure all tests pass:
   `ash
   python -m unittest discover -s tests -t .
   `
6. **Commit and push** to your fork, then submit a **Pull Request** targeting the main branch.

## Code Guidelines
- Keep core algorithmic logic in src/plateverif/ modular and unit-tested.
- The web viewer in website/ is vanilla JavaScript/CSS without a build step to maximize accessibility and portability.
- Include unit tests for any new verification rules or data processing functions.
