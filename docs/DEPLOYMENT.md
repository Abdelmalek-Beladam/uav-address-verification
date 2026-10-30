# GitHub Pages deployment

The browser app is static. Deploy **website/** only. Models and Python inference do not run on GitHub Pages. No paid server, database or environment variables are needed for the current review demo.

## Before any public push

Read PUBLICATION.md. Resolve verified imagery credits before public GitHub publication, not only before Pages. Do not commit the sibling private-handoff folder, checkpoint, old ZIP or conversation backup. Use the prepared public-repo folder as the repository root; check the actual staged list, not just .gitignore.

## Publish

1. Open the prepared project in Antigravity. Read the supplied ANTIGRAVITY_PUBLISH_PROMPT.md from outside the public tree.
2. Resolve rights/credit preflight from a connected environment and obtain owner approval for any unresolved publication/licence choice. Run Python checks and local browser tests. Do not retrain or rewrite the pipeline.
3. Create a clean Git branch/repository or a reviewed commit in the user's chosen repository. Do not force-push or replace unrelated history. Use GitHub/CLI login; never paste tokens into code.
4. In GitHub, Settings → Pages → Build and deployment → Source → **GitHub Actions**.
5. Run the **Deploy UAV Address Verification** workflow manually and acknowledge the publication checks only when they are actually complete.
6. Use the deployment URL returned by the workflow, not a guessed URL. Add it to repository About and the Thirduni Live demo field. Confirm logged-out access to both repository and site.

The workflow uploads website/ with `actions/upload-pages-artifact@v4`, configures Pages and deploys with pages/id-token permissions. Manual dispatch prevents accidental automatic publication. CI runs CPU tests and integrity checks separately.

## Acceptance checks at the public subpath

- Home film/poster loads; concept caption and pause control remain visible.
- Open Route 01 and Route 02, source images/crops, number 33 case, filters, map attribution/fallback and legacy detailed report.
- Save a local note, reload, export CSV and notes, then test the privacy deletion control.
- Playback, right/left view, seek and pause work. Deep-link reloads use hash routes and remain under the project path.
- Check footer notices on mobile. No 404s or JavaScript exceptions in the console.
- Test video/repository/demo links from a private browser window. Keep deployment available throughout 1–7 November judging.

Record the actual commit, workflow run and public URL after success. Prepared configuration is not a claim of successful deployment.
