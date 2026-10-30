# Start here

1. Extract this handoff into a **new folder on C:**. Preserve the old project.
2. The `public-repo` folder is the prepared project. The sibling `private-handoff` folder is **not for GitHub**.
3. Open a PowerShell terminal in `public-repo` and run:

```powershell
py -m http.server 8088 --directory website --bind 127.0.0.1
```

4. Open http://127.0.0.1:8088/ . No model installation is needed for browser review.
5. Give Antigravity the separate `ANTIGRAVITY_PUBLISH_PROMPT.md`, from the handoff root. It covers public-file exclusions, preflight, commit and GitHub Pages.
6. Record the product demonstration using `VIDEO_RECORDING_GUIDE.md`. Replace submission links only with the real deployed/video URLs.

The release has been locally tested. It is not already public, deployed or submitted. Source rights and project-code licence choices are not silently approved by tests.
