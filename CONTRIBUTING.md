# Contributing

Start with README.md. The website has no build step; optional browser tests use Node, Playwright and Chromium. Python verification tests use requirements.txt.

## Change boundaries

- UI-only changes must not modify `src/`, `config/`, reference data or saved result artifacts.
- Stable dataset IDs are join keys and local-storage namespaces, not marketing names. Change display names in `website/assets/product-config.js`.
- Shared demo notices live in `website/assets/information.js`; `app.js` handles route, review, map, export and playback interactions.
- Escape data before inserting it into HTML. Keep spreadsheet-formula neutralization in CSV exports. Never add secrets or user tracking by accident.
- Preserve keyboard navigation, text labels alongside colours, explicit map failures, export behaviour, note persistence and reduced-motion support.
- New processing outputs belong in a new folder. Record input provenance, model/environment identity and dataset overlap before assigning an evaluation role.

## Before a pull request

Run Python tests and `python tools/check_handoff.py`. Serve `website` on port 8088 and run `node tests/browser_qa.cjs` with Playwright installed (`CHROMIUM_PATH` can point to a local Chromium executable). Test at 375, 768, 1024 and 1440 pixels. Explain behaviour changes and verification evidence. Prefer small, reviewable fixes over unrelated rewrites. Do not refresh protected hashes to conceal changed model results.

Use comments to explain assumptions, join keys, safety rules and non-obvious behaviour, not to narrate every line. Do not submit `.venv`, `node_modules`, caches, raw Drive archives, private documents or model binaries without their own approval.
