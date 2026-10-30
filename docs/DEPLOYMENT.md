# GitHub Pages Deployment

The review dashboard is a static web application located in website/. It can be hosted on GitHub Pages or any static web host without backend infrastructure.

## Deployment Steps

1. Run Python unit tests and verify the local web preview:
   `ash
   python -m unittest discover -s tests -t .
   python -m http.server 8088 --directory website --bind 127.0.0.1
   `
2. In your GitHub repository:
   - Navigate to **Settings** → **Pages**
   - Under **Build and deployment** → **Source**, select **GitHub Actions**
3. Trigger the deployment workflow:
   - Go to **Actions** → **Deploy UAV Address Verification**
   - Click **Run workflow** on the main branch
4. Once completed, your dashboard will be available at:
   https://<username>.github.io/<repository-name>/

## Verification Checklist

- Landing page video/poster loads properly.
- Surveys (Route 01 and Route 02) load detections, cropped plates, and candidate addresses.
- Interactive map markers render and align with address register coordinates.
- Route playback, camera side-switching (left/right), and playback speeds function smoothly.
- Local note persistence works across page reloads.
- CSV and GeoJSON export downloads generate correctly.
