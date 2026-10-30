"use strict";
/** Factual notices for the current research demo; no production promises. */
const INFO = {
  privacy: {
    title: "Privacy & local data",
    paragraphs: [
      "This demo has no accounts, image uploads, contact forms or shared review server. Case notes are stored in your browser's local storage and are not sent to the project team by this application.",
      "The application implements no advertising, tracking analytics or non-essential cookies. Hosting infrastructure may log requests. OpenStreetMap receives your IP address and requested tile coordinates when you open a map. The separate detailed reports may also request external fonts, Leaflet assets and basemap services; those providers receive ordinary request metadata. Separate detailed reports may request external fonts, Leaflet assets and basemap services; those providers receive ordinary request metadata.",
      "Do not enter names, access codes or sensitive personal information in case notes. Exports are downloaded to your device; you control any later sharing.",
      "Use the button below to remove this project's local notes. Other websites' data is unaffected. Export any notes you need to retain before deletion.",
    ],
  },
  terms: {
    title: "Demo terms",
    paragraphs: [
      "UAV Address Verification is a student research prototype for exploration and evaluation. It is not a production inspection service, certified address authority or flight-control system.",
      "Readings, estimated positions and automated assessments may be wrong or incomplete. Check source images and authoritative records before operational, regulatory or enforcement decisions. A flag requests review; it is not proof that an address is incorrect.",
      "There is no service-level guarantee, shared account system or backup service. Do not rely on this demo as your only record.",
      "Imagery, reference data, maps and software retain their respective licence conditions. See Sources & credits and repository notices before reusing them.",
    ],
  },
  safety: {
    title: "Responsible use",
    paragraphs: [
      "The current demonstration uses recorded street imagery. It does not operate a UAV or demonstrate aerial acquisition, autonomous flight or onboard processing. The homepage film is an AI-generated concept illustration.",
      "Future UAV trials require suitable hardware, validated image/pose information, local aviation permission, a safe operating plan and privacy safeguards. These are prerequisites, not capabilities already delivered.",
      "Use this workspace to review evidence, not for automatic enforcement. Number recognition, register comparison and location estimation are separate checks. Human review remains necessary, especially at junctions and where readings or coverage are limited.",
    ],
  },
  project: {
    title: "About the project",
    paragraphs: [
      "AI-Powered UAV for Automated Addressing Detection & Verification is an operational intelligence system designed to inspect visible house numbers and verify them against official geographic address registers.",
      "In the current prototype, detection and OCR are performed by our trained computer vision pipeline (YOLO26n + PaddleOCR) and processed offline to simulate the target deployment where models run directly on UAV edge hardware. The interactive dashboard allows inspection teams to examine multiple high-resolution views, verify register alignments, record reviewer observations, and export GIS-ready evidence.",
      "Future milestones expand the model's training across diverse cities and international regions to learn varying architectural textures, lighting environments, and plate typography, delivering the complete three-tier platform:",
      "1. UAV Data Acquisition & Mapping Results: A structured verification system for surveyed buildings and plate numbers. For each detected plate, the dashboard displays recognized numbers, geographic coordinates, and preliminary condition/compliance status (correct, incorrect, damaged, or missing where sufficient evidence exists).",
      "2. Address Plate Inventory & Replacement Planning: Quantifying plates that can be retained versus those requiring replacement, calculating municipal procurement needs accurately and eliminating unnecessary expenditures.",
      "3. GIS-Based Cost Estimation & Decision Support: Geographically informed cost estimates for plate rectification and replacement at street, neighbourhood, and city scale, powering municipal budget forecasting, resource allocation, and operational planning.",
    ],
  },
  sources: {
    title: "Sources & credits",
    paragraphs: [
      "The demo uses Panoramax imagery. Its area labels describe multi-street routes rather than recordings confined to one named street. Original IDs remain unchanged for reproducibility.",
      "Route 01 & Route 02 sources: immergis, via Panoramax IGN, Licence Ouverte 2.0 (etalab-2.0). Perspective views and crops were derived for this prototype, verified via official metadata APIs on 30 October 2026.",
      "Reference: Adresses de Paris, Ville de Paris / Direction de l'Urbanisme, ODbL. This is a packaged snapshot, not a live address feed. These comparisons do not amend official records.",
      "Map: © OpenStreetMap contributors. Images and route coordinates remain visible if map tiles cannot load. Concept film: user-supplied AI-generated illustration, not evidence of flight.",
      "Sequence-specific source links and credit evidence are in the imagery manifest and docs/DATA_CREDITS.md. Third-party terms remain separate from any future project-code licence.",
    ],
  },
};
function informationPage(page) {
  const info = INFO[page];
  $("#app").innerHTML =
    `<article class="information-page"><a class="back-link" href="#overview">← Back to home</a><p class="eyebrow">UAV ADDRESS VERIFICATION</p><h1>${E(info.title)}</h1>${info.paragraphs.map((p) => "<p>" + E(p) + "</p>").join("")}${page === "privacy" ? '<button class="btn" id="clearNotes">Delete local review notes</button><p id="privacyState" role="status"></p>' : ""}${page === "sources" ? '<h2>Reference links</h2><ul><li><a href="https://opendata.paris.fr/explore/dataset/adresse_paris/" target="_blank" rel="noopener">Paris address register</a></li><li><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap copyright</a></li><li><a href="data/imagery-credits.json">Imagery credit manifest</a></li></ul>' : ""}<p class="information-date">Demo notice · 30 October 2026</p></article>`;
  if (page === "privacy")
    $("#clearNotes").onclick = () => {
      if (
        !confirm(
          "Delete this project’s local review notes? Export first if you need a copy.",
        )
      )
        return;
      try {
        Object.keys(localStorage)
          .filter((k) => k.startsWith("address-observatory:"))
          .forEach((k) => localStorage.removeItem(k));
        $("#privacyState").textContent = "Local review notes deleted.";
      } catch {
        $("#privacyState").textContent = "Browser storage is unavailable.";
      }
    };
  window.scrollTo(0, 0);
}
