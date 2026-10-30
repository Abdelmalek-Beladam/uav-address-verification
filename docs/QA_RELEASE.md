# Release QA — 30 October 2026

## Executed against the exact delivered public-preparation tree

- Python tests: 75 passed. The outdated MAV/model-heavy HTML text assertion was replaced with explicit UAV planned/not-implemented and saved-output assertions. Computational tests were not weakened.
- Browser checks: 57 passed using Playwright and Chromium. See browser_checks.json. Desktop/mobile widths 375, 768, 1024, 1440; routing, source/crop switching, case 33, filters, local note persistence, CSV/JSON exports, privacy deletion, playback/seek/side, dialogs and reduced-motion behaviour exercised.
- No browser JavaScript errors or missing requested local assets in that run. External OSM tiles deliberately blocked to verify the explicit fallback, not to certify external availability.
- Every saved linked view/crop path checked for existence.
- All public Python source parsed; JSON parsed; credential-pattern scan found no matches. These are best-effort checks, not a security certification.
- All 2364 retained protected artifact hashes match the supplied handoff manifest. Excluded private/binary identities are retained separately.
- Saved verification reproduced from preserved raw rows; all ten compared CSV tables equal. No new detector/OCR inference, training or accuracy benchmark performed.

## Audit boundaries and pending publication

The archive and code were inspected, but no audit can guarantee all defects absent. Browser screenshots were generated; final human image inspection was blocked by the conversation's 100-attachment viewing limit. Automated layout/interaction tests do not establish full WCAG conformance or visual perfection.

Route 02 imagery source metadata was verified (immergis, etalab-2.0). Route 01 source metadata could not be retrieved; curl failed DNS. It remains a publication gate. The chosen project-code licence, generated-film rights/privacy approval and actual public commit/Pages deployment are not established by QA.

No public deployment, video upload or Thirduni form submission was performed. Do not imply otherwise. See PUBLICATION.md and the Antigravity publication prompt.
