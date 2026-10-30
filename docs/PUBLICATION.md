# Publication preflight

A local test pass does not establish redistribution permission. The handoff root contains `public-repo` and a separate private folder. **Do not publish the handoff root.**

## Included public preparation

Source code, verification configuration, attributed address snapshot, saved demo evidence, actual evaluation tables, source-only historical notebooks, regression tests and current documentation. The imagery is included for continuity but is still subject to the source-credit gate below.

## Excluded from the public preparation

Selected detector binary (private until terms/permission are confirmed), other model binaries, Drive archives, original private source documents, old submission documents, coding-agent prompts/skills, scratch files, caches, virtual environments, node_modules, logs and conversation-memory material. Historical public proof tables remain where the saved reproduction requires them.

## Gates before publishing even the GitHub repository

1. Resolve Route 01 contributor/licence from the official source sequence metadata, then record the verified credit in `website/data/imagery-credits.json` and DATA_CREDITS.md. Route 02 source metadata was verified during this audit. Do not guess Route 01 terms.
2. Confirm the user-supplied generated concept film is publishable; it is labelled as generated concept imagery.
3. Check imagery/privacy suitability and any source licence conditions for derived views/crops. Automated checks do not substitute for this.
4. Choose a code licence with contributor approval if licensing reuse as open source. Without it the source may be publicly inspectable but is not generally licensed for reuse. Model/dependency terms remain separate.
5. Inspect the exact staged file list and scan credentials. Never use `git add .` from the handoff parent or an old working folder containing private artifacts. A .gitignore does not untrack files already committed.

Run `python tools/publication_preflight.py` for machine-readable gates. It deliberately fails when verified Route 01 rights evidence is absent; never fill it with invented approval. Deployment is manual to avoid accidental public redistribution. See the separate Antigravity publication prompt.
