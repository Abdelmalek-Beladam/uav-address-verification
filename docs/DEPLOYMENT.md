# GitHub Pages deployment

The browser app is static. Deploy **website/** only. Models and Python inference do not run on GitHub Pages. No paid server, database or environment variables are needed for the current review demo.

## Before any public push

Resolve verified imagery credits before public GitHub publication, not only before Pages. Do not commit model binaries, old ZIPs or private artifacts. Check the actual staged file list — a .gitignore does not untrack files already committed.

## Publish

1. Verify imagery credits and rights are resolved. Run Python checks (python tools/check_handoff.py) and local browser tests.
2. Create a clean Git commit or branch. Do not force-push or replace unrelated history. Use GitHub CLI login; never paste tokens into code.
3. In GitHub, Settings → Pages → Build and deployment → Source → **GitHub Actions**.
4. Run the **Deploy UAV Address Verification** workflow manually.
5. Use the deployment URL returned by the workflow, not a guessed URL. Add it to repository About. Confirm logged-out access to both repository and site.

The workflow uploads website/ with ctions/upload-pages-artifact@v4, configures Pages and deploys with pages/id-token permissions. Manual dispatch prevents accidental automatic publication. CI runs CPU tests and integrity checks separately.

## Acceptance checks at the public subpath

- Home film/poster loads; concept caption and pause control remain visible.
- Open Route 01 and Route 02, source images/crops, number 33 case, filters, map attribution/fallback and legacy detailed report.
- Save a local note, reload, export CSV and notes, then test the privacy deletion control.
- Playback, right/left view, seek and pause work. Deep-link reloads use hash routes and remain under the project path.
- Check footer notices on mobile. No 404s or JavaScript exceptions in the console.
- Test video/repository/demo links from a private browser window. Keep deployment available throughout 1–7 November judging.

Record the actual commit, workflow run and public URL after success.
