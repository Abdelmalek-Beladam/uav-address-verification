"use strict";
const $ = (s, r = document) => r.querySelector(s),
  E = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    ),
  N = (v) => (v !== "" && v != null && isFinite(Number(v)) ? Number(v) : null),
  F = (v) => Number(v || 0).toLocaleString("en-US");
const S = {
  catalog: [],
  cache: {},
  data: null,
  page: "overview",
  mode: "plates",
  filter: "all",
  search: "",
  selected: null,
  obs: 0,
  index: 0,
  timer: null,
  speed: 2,
  side: "left",
};
let routeVersion = 0;
const flags = new Set([
  "OUT_OF_PLACE",
  "WRONG_SIDE",
  "UNKNOWN_NUMBER",
  "NO_ADDRESS_NEARBY",
  "SUFFIX_MISMATCH",
  "NOT_FOUND",
]);
const G = (s) =>
    s === "CORRECT"
      ? "correct"
      : flags.has(s)
        ? "flag"
        : s === "UNCERTAIN"
          ? "uncertain"
          : "insufficient",
  C = (s) =>
    ({
      correct: "#216047",
      flag: "#9e2d32",
      uncertain: "#76510a",
      insufficient: "#425469",
    })[G(s)],
  ID = (r) => r.plate_id || r.address_id;
const decisionLabels = {
  CORRECT: "Register match",
  UNCERTAIN: "Needs review",
  UNREADABLE: "Number unclear",
  NOT_FOUND: "No plate found in covered views",
  NOT_COVERED: "Insufficient coverage",
  OUT_OF_PLACE: "Location to check",
  WRONG_SIDE: "Street side to check",
  UNKNOWN_NUMBER: "Number to check",
  NO_ADDRESS_NEARBY: "No nearby register match",
};
const badge = (r) =>
  `<span class="status ${G(r.status)}">${E(decisionLabels[r.status] || r.status_label || r.status)}</span>`;
function toast(t) {
  $(".toast")?.remove();
  const d = document.createElement("div");
  d.className = "toast";
  d.setAttribute("role", "status");
  d.textContent = t;
  document.body.append(d);
  setTimeout(() => d.remove(), 5000);
}
/** Cache saved outputs; this app never executes inference. */
async function data(id) {
  if (!S.cache[id]) {
    if (!S.catalog.some((c) => c.id === id)) throw Error("Unknown recording");
    const r = await fetch("data/" + encodeURIComponent(id) + ".json");
    if (!r.ok) throw Error("Recording unavailable");
    S.cache[id] = await r.json();
    Object.assign(S.cache[id], PRODUCT.routes[id] || {});
  }
  return S.cache[id];
}
/** Keep existing browser notes compatible with the previous release. */
function key() {
  return "address-observatory:" + S.data.id + ":" + S.data.summary.generated_at;
}
function notes() {
  try {
    const value = JSON.parse(localStorage.getItem(key()));
    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : {};
  } catch {
    return {};
  }
}
function stop() {
  clearInterval(S.timer);
  S.timer = null;
}
function heading(k, t, p, a = "") {
  return `<div class="heading"><div><p class="eyebrow">${k}</p><h1>${t}</h1><p class="muted">${p}</p></div><div class="actions">${a}</div></div>`;
}
function metric(k, v, p) {
  return `<div class="metric"><label>${k}</label><strong>${F(v)}</strong><small>${p}</small></div>`;
}
const options = () =>
  S.catalog
    .map(
      (c) =>
        `<option value="${E(c.id)}" ${S.data.id === c.id ? "selected" : ""}>${E(c.name)}</option>`,
    )
    .join("");
const report = () =>
  `<a class="btn small" href="${E(S.data.report_url)}" target="_blank" rel="noopener">Detailed report ↗</a>`;
function card(c) {
  return `<article class="panel survey-card"><div class="map" id="mini-${E(c.id)}"></div><div class="pad"><p class="eyebrow">INSPECTION RECORDING</p><h2>${E(c.name)}</h2><p class="muted">${F(c.summary.photos.usable)} capture positions · ${F(c.summary.plates.total)} plate observations</p><details class="survey-context"><summary>About this recording</summary><p class="muted">${E(c.role)}</p><p class="muted">Includes neighbouring streets; the route name is an area label.</p></details><a class="link" href="#review/${E(c.id)}">Open recording →</a></div></article>`;
}
async function route() {
  const version = ++routeVersion;
  stop();
  document.querySelectorAll(".map").forEach((el) => el._cleanup?.());
  document.querySelectorAll("video").forEach((v) => v.pause());
  const bits = location.hash.slice(1).split("/");
  S.page = [
    "overview",
    "surveys",
    "review",
    "playback",
    "privacy",
    "terms",
    "safety",
    "sources",
    "project",
  ].includes(bits[0])
    ? bits[0]
    : "overview";
  document
    .querySelectorAll("[data-page]")
    .forEach((a) => a.classList.toggle("active", a.dataset.page === S.page));
  document.body.classList.toggle(
    "public",
    ["overview", "privacy", "terms", "safety", "sources", "project"].includes(
      S.page,
    ),
  );
  $("#sidebar").classList.remove("open");
  $("#menu").setAttribute("aria-expanded", "false");
  $("#crumb").textContent = {
    overview: "Overview",
    surveys: "Survey library",
    review: "Review workspace",
    playback: "Route playback",
    privacy: "Privacy",
    terms: "Demo terms",
    safety: "Responsible use",
    sources: "Sources",
    project: "About the project",
  }[S.page];
  try {
    const nextData = await data(
      S.catalog.some((c) => c.id === bits[1])
        ? bits[1]
        : S.data?.id || S.catalog[0].id,
    );
    if (version !== routeVersion) return;
    S.data = nextData;
    S.selected = null;
    S.obs = 0;
    S.search = "";
    S.filter = "all";
    S.index = 0;
    if (["privacy", "terms", "safety", "sources", "project"].includes(S.page)) {
      informationPage(S.page);
      return;
    }
    if (S.page === "overview") await overview();
    if (S.page === "surveys") await library();
    if (S.page === "review") {
      if (bits[2]) {
        S.selected = decodeURIComponent(bits[2]);
        S.mode = S.data.addresses.some((a) => a.address_id === S.selected)
          ? "addresses"
          : "plates";
      }
      review();
    }
    if (S.page === "playback") playback();
  } catch (e) {
    error(e);
  }
}
function error(e) {
  $("#app").innerHTML =
    `<div class="notice"><h2>Could not open recorded data</h2><p>${E(e.message)}</p><p>Refresh the page and try again. For a downloaded copy, use the included dashboard launcher and keep its console open.</p><button class="btn" onclick="location.reload()">Retry</button></div>`;
}
/** Product landing: the film illustrates the proposed UAV acquisition stage. */
async function overview() {
  const d = await data("rue_de_four"),
    p = d.plates.find((x) => x.plate_id === "P0001"),
    o = p.observations[0];
  $("#app").innerHTML =
    `<section class="service-hero landing-hero" aria-labelledby="hero-title"><video class="hero-film" autoplay muted loop playsinline preload="auto" src="assets/uav-concept.mp4" poster="assets/uav-poster.jpg" aria-hidden="true" tabindex="-1"></video><div class="hero-scrim"></div><div class="landing-intro"><p class="eyebrow">UAV ADDRESS VERIFICATION</p><h1 id="hero-title">Put every number<br>in its place.</h1><p>Find house-number plates. Check them against the address register. Bring the cases that need attention to the people who can resolve them.</p><div class="actions"><a class="btn primary hero-cta" href="#review/rue_bonaparte">Explore the demo ↗</a><a class="btn ghost-glass hero-secondary" href="#how-it-works">How it works ↓</a></div></div></section>
<section class="mission-section"><div class="mission-inner"><div class="mission-heading"><p class="eyebrow">BUILT FOR ADDRESS INSPECTION</p><h2>A number on a wall.<br>A place on the map.</h2></div><div class="mission-content"><p class="lead">Address records and what is visible on the street do not always line up. Inspection teams need to see the plate, check the location and decide what to follow up.</p><p>Our project brings that work into one review workspace, with UAV image collection as the next stage.</p><div class="demo-note"><span class="note-icon">ℹ</span><p>The current demo uses recorded Paris imagery processed offline. UAV acquisition is planned, not demonstrated.</p></div></div></div></section>
<section class="workflow-band" id="how-it-works"><div class="section-inner"><div class="workflow-heading"><p class="eyebrow">HOW IT WORKS</p><h2>From inspection<br>to follow-up.</h2><p class="section-lead">Keep the source images, detected numbers, and address verification together.</p></div><div class="steps"><article><span class="step-num">01</span><h3>Find the number</h3><p>Locate house-number plates in inspection imagery and read the numbers that are visible.</p></article><article><span class="step-num">02</span><h3>Check the address</h3><p>Compare the reading and estimated location with the official address register.</p></article><article><span class="step-num">03</span><h3>Review the case</h3><p>Open the source images. Compare multiple views and check why a case has been flagged.</p></article><article><span class="step-num">04</span><h3>Plan the follow-up</h3><p>Add a review note and export the evidence for further inspection or GIS work.</p></article></div></div></section>
<section class="service-case" id="real-evidence"><div class="case-inner"><div class="case-photo"><img class="hero-source" src="${E(o.view_url)}" alt="Recorded street image containing a house-number plate" width="480" height="600" loading="lazy"><span class="photo-caption">Recorded Paris imagery · current software demo</span></div><div class="case-narrative"><p class="eyebrow">INSIDE THE WORKSPACE</p><h2>See why a case<br>needs attention.</h2><p class="case-lead">The reading is <strong>33</strong>. The nearest matching register point is <strong>4.5 metres</strong> from the estimated plate position. The system keeps the case open for review.</p><div class="case-specs"><div class="spec-item"><span class="spec-label">Case</span><span class="spec-val">P0001</span></div><div class="spec-item"><span class="spec-label">Reading</span><span class="spec-val">33</span></div><div class="spec-item"><span class="spec-label">Register offset</span><span class="spec-val">4.5 m</span></div><div class="spec-item"><span class="spec-label">Status</span><span class="spec-val flag">Flagged</span></div></div><p>Inspect its five supporting views, compare the location and leave a note without changing the original result.</p><div class="actions"><a class="btn primary" href="#review/rue_de_four/P0001">Open this case ↗</a></div></div></div></section>
<section class="landing-close"><div class="close-card"><p class="eyebrow">TRY THE WORKSPACE</p><h2>Start with a case.<br>Follow the evidence.</h2><p class="close-sub">Browse recorded routes, inspect plate crops and verify location geometry.</p><div class="actions"><a class="btn primary" href="#surveys">Choose a recording ↗</a></div></div></section>`;
  const film = $(".hero-film");
  if (film) {
    film.play().catch(() => {
      const unlock = () => {
        film.play().catch(() => {});
        window.removeEventListener("click", unlock);
        window.removeEventListener("scroll", unlock);
        window.removeEventListener("touchstart", unlock);
      };
      window.addEventListener("click", unlock, { once: true });
      window.addEventListener("scroll", unlock, { once: true });
      window.addEventListener("touchstart", unlock, { once: true });
    });
  }
  if (["how-it-works", "real-evidence"].includes(location.hash.slice(1)))
    requestAnimationFrame(() =>
      document.getElementById(location.hash.slice(1))?.scrollIntoView(),
    );
}
async function library() {
  const page = heading(
    "RECORDING LIBRARY",
    "Inspection recordings",
    "Choose a multi-street route to review its address cases.",
  );
  $("#app").innerHTML =
    page + `<div class="survey-grid">${S.catalog.map(card).join("")}</div>`;
  for (const c of S.catalog)
    map($("#mini-" + c.id), await data(c.id), [], null, true);
}
function rows() {
  return (S.mode === "plates" ? S.data.plates : S.data.addresses).filter(
    (r) =>
      (S.filter === "all" || G(r.status) === S.filter) &&
      (!S.search ||
        [
          r.plate_id,
          r.address_id,
          r.address,
          r.reading_display,
          r.expected_address,
          r.candidate_address,
          r.status_label,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(S.search.toLowerCase())),
  );
}
function review() {
  $("#app").innerHTML =
    heading(
      "REVIEW WORKSPACE",
      E(S.data.name),
      "Select a case to check the image, address and location.",
      report(),
    ) +
    `<div class="toolbar"><div class="controls"><label class="control">Recording<select id="survey">${options()}</select></label><label class="control">Search<input id="search" type="search" placeholder="Number, address or record ID"></label><label class="control">Status group<select id="filter"><option value="all">All results</option><option value="correct">Matches</option><option value="flag">Flagged cases</option><option value="uncertain">Needs review</option><option value="insufficient">Insufficient evidence</option></select></label></div><div class="actions"><button id="csv" class="btn small">Export filtered CSV</button><button id="notesExport" class="btn small">Export review notes</button></div></div><div class="toolbar"><div class="actions"><button class="btn small ${S.mode === "plates" ? "active-mode" : ""}" id="plateMode">Plates (${S.data.plates.length})</button><button class="btn small ${S.mode === "addresses" ? "active-mode" : ""}" id="addressMode">Addresses (${S.data.addresses.length})</button></div><span class="muted">${E(S.data.role)}</span></div><div class="workspace"><section class="panel"><div id="reviewMap" class="map tall"></div><div class="pad" style="padding-bottom:12px"><div class="toolbar" style="margin:0 0 10px"><span id="count" class="muted"></span></div><div class="legend"><span><i style="background:#5f8a58"></i>Matches</span><span><i style="background:#b57450"></i>Flags</span><span><i style="background:#bd9c4e"></i>Uncertain</span><span><i style="background:#91a292"></i>Insufficient</span></div></div><div class="table-wrap"><table><thead><tr><th>RESULT</th><th>STATUS</th><th>VIEWS</th><th>SUPPORT</th></tr></thead><tbody id="rows"></tbody></table></div></section><section class="panel detail" id="detail" aria-live="polite"></section></div><p class="small-note">Case notes are saved in this browser. Export them to keep a separate copy.</p>`;
  $("#search").value = S.search;
  $("#filter").value = S.filter;
  $("#survey").onchange = (e) => (location.hash = "#review/" + e.target.value);
  $("#search").oninput = (e) => {
    S.search = e.target.value;
    refresh();
  };
  $("#filter").onchange = (e) => {
    S.filter = e.target.value;
    refresh();
  };
  $("#plateMode").onclick = () => {
    S.mode = "plates";
    review();
  };
  $("#addressMode").onclick = () => {
    S.mode = "addresses";
    review();
  };
  $("#csv").onclick = exportCSV;
  $("#notesExport").onclick = () =>
    download(
      S.data.id + "-reviews.json",
      JSON.stringify(
        {
          survey: S.data.id,
          scope: "Browser-local notes; original statuses unchanged",
          reviews: notes(),
        },
        null,
        2,
      ),
      "application/json",
    );
  refresh();
}
function refresh() {
  const rs = rows();
  if (!rs.some((r) => ID(r) === S.selected))
    S.selected = rs[0] ? ID(rs[0]) : null;
  $("#count").textContent = rs.length + " " + S.mode + " shown";
  $("#rows").innerHTML =
    rs
      .map(
        (r) =>
          `<tr tabindex="0" data-id="${E(ID(r))}" class="${ID(r) === S.selected ? "selected" : ""}"><td>${E(S.mode === "plates" ? r.reading_display : r.address)}<span class="cell-id">${E(ID(r))}</span></td><td>${badge(r)}</td><td>${E(r.n_photos || r.n_photos_in_view || "—")}</td><td>${E(r.confidence || "—")}</td></tr>`,
      )
      .join("") || '<tr><td colspan="4">No matching results.</td></tr>';
  $("#rows")
    .querySelectorAll("[data-id]")
    .forEach((e) => {
      e.onclick = () => select(e.dataset.id);
      e.onkeydown = (k) => {
        if (k.key === "Enter" || k.key === " ") {
          k.preventDefault();
          select(e.dataset.id);
        }
      };
    });
  map($("#reviewMap"), S.data, rs, select);
  detail();
}
function select(id) {
  S.selected = id;
  S.obs = 0;
  history.replaceState(
    null,
    "",
    "#review/" + S.data.id + "/" + encodeURIComponent(id),
  );
  refresh();
}
/** Show source evidence first and technical interpretation on demand. */
function detail() {
  const r = rows().find((r) => ID(r) === S.selected),
    el = $("#detail");
  if (!r) {
    el.innerHTML = '<div class="empty">No matching result selected.</div>';
    return;
  }
  const ps =
    S.mode === "plates"
      ? [r]
      : S.data.plates.filter((p) =>
          String(r.plates || "")
            .split(";")
            .includes(p.plate_id),
        );
  const obs = ps.flatMap((p) => p.observations);
  const o = obs[Math.min(S.obs, Math.max(0, obs.length - 1))],
    nk = S.mode + ":" + ID(r),
    saved = notes()[nk] || {};
  const pct = (v) =>
    N(v) == null ? "Not available" : (Number(v) * 100).toFixed(1) + "%";
  el.innerHTML = `<div class="detail-title"><p class="eyebrow">${S.mode === "plates" ? "ADDRESS CASE" : "REGISTER ADDRESS"} / ${E(ID(r))}</p><h2>${E(S.mode === "plates" ? r.reading_display : r.address)}</h2>${badge(r)}</div>${o?.view_url ? `<a href="${E(o.view_url)}" target="_blank" rel="noopener"><svg class="detail-image" viewBox="0 0 ${Number(o.image_width) || 1600} ${Number(o.image_height) || 2000}" role="img" aria-label="Source image with plate detection box"><image href="${E(o.view_url)}" width="${Number(o.image_width) || 1600}" height="${Number(o.image_height) || 2000}"/><rect x="${Number(o.x_center) - Number(o.box_width) / 2}" y="${Number(o.y_center) - Number(o.box_height) / 2}" width="${Number(o.box_width)}" height="${Number(o.box_height)}" fill="none" stroke="#ffb386" stroke-width="7"/></svg></a>` : '<div class="empty">No source view linked to this result.</div>'}<div class="detail-body">${o?.crop ? `<div class="crop-summary"><img src="${E(o.crop)}" alt="Detected plate crop"><div><span class="muted">Reading from this image</span><code class="raw-text">${E(o.raw_ocr || "(empty)")}</code></div></div>` : ""}<div class="crops">${obs.map((x, i) => (x.crop ? `<button data-obs="${i}" aria-label="Show observation ${i + 1}"><img src="${E(x.crop)}" alt="Observation ${i + 1}" loading="lazy"></button>` : "")).join("")}</div><div class="decision-grid"><article><span>NUMBER</span><h3>${E(ps[0]?.recognition_state || "No plate observation")}</h3><p>${E(ps[0]?.recognition_state === "unreadable" ? "Open the source views to check the number." : "Compare the reading with the source views below.")}</p></article><article><span>REGISTER ADDRESS</span><h3>${E(r.candidate_address || r.address || ps[0]?.candidate_address || "No candidate identified")}</h3><p>${E(r.candidate_distance_m ?? ps[0]?.candidate_distance_m ?? "—")} m from estimated position</p></article><article><span>LOCATION</span><h3>${E(ps[0]?.location_state || "No linked plate position")}</h3><p>${E(ps[0]?.located_by || "Not available")}</p></article></div><details class="reason"><summary>Assessment details</summary><p>${E(r.explanation)}</p>${ps[0]?.decision_notes ? "<ul>" + ps[0].decision_notes.map((n) => "<li>" + E(n) + "</li>").join("") : ""}</details><details class="record-metadata"><summary>Record details</summary><dl class="definition"><dt>Register candidate</dt><dd>${E(r.candidate_address || r.expected_address || r.address || "No candidate identified")}</dd><dt>Supporting views</dt><dd>${E(S.mode === "plates" ? r.n_photos : r.supporting_photo_count || 0)}</dd>${S.mode === "addresses" ? "<dt>Predicted coverage views</dt><dd>" + E(r.n_photos_in_view) + "</dd>" : ""}<dt>Location method</dt><dd>${E(r.located_by || "See linked plate evidence")}</dd><dt>Support level</dt><dd>${E(r.confidence || "Not available")}</dd><dt>Source image</dt><dd>${E(o?.image || "Not available")}</dd></dl></details><details><summary>Technical evidence & interpretation</summary><dl class="definition"><dt>Pipeline status</dt><dd>${E(r.status)}</dd><dt>Reading agreement</dt><dd>${pct(r.reading_agreement)}</dd><dt>Selected detection score</dt><dd>${pct(o?.det_conf)}</dd><dt>Selected OCR score</dt><dd>${pct(o?.ocr_conf)}</dd><dt>Combined evidence score</dt><dd>${E(r.confidence_score || "Not available")}</dd><dt>Latitude / longitude</dt><dd>${E(r.lat)}, ${E(r.lon)}</dd></dl><p class="muted">These scores are evidence indicators, not probabilities that an address is correct. Repeated views can share the same error. Suffixes are not verified.</p></details><form class="note-form" id="noteForm"><label for="disposition">Operator review</label><select id="disposition">${["Pending", "Needs follow-up", "No issue after review", "Reviewed — unresolved"].map((v) => `<option ${saved.disposition === v ? "selected" : ""}>${v}</option>`).join("")}</select><label for="note">Case note</label><textarea id="note" maxlength="2000" placeholder="Record what the image evidence supports.">${E(saved.note || "")}</textarea><div class="actions" style="margin-top:10px"><button class="btn small primary">Save review</button><span id="saveState" class="muted"></span></div><p class="small-note">Browser-local only. Export notes before clearing browser data.</p></form></div>`;
  el.querySelectorAll("[data-obs]").forEach(
    (b) =>
      (b.onclick = () => {
        S.obs = Number(b.dataset.obs);
        detail();
      }),
  );
  $("#noteForm").onsubmit = (e) => {
    e.preventDefault();
    try {
      const ns = notes();
      ns[nk] = {
        disposition: $("#disposition").value,
        note: $("#note").value,
        updated_at: new Date().toISOString(),
        pipeline_status: r.status,
      };
      localStorage.setItem(key(), JSON.stringify(ns));
      history.replaceState(
        null,
        "",
        "#review/" + S.data.id + "/" + encodeURIComponent(ID(r)),
      );
      $("#saveState").textContent = "Saved in this browser";
    } catch {
      toast(
        "Browser storage unavailable. Use a normal browser session and export notes.",
      );
    }
  };
}
/** Mercator map with keyboard controls, explicit tile fallback and observer cleanup. */
function map(el, d, rs, onSelect = null, mini = false, photo = null) {
  if (!el) return;
  if (el._cleanup) el._cleanup();
  const valid = d.photos.filter((p) => N(p.lat) !== null && N(p.lon) !== null);
  if (!valid.length) return;
  const chosen = rs.find((r) => ID(r) === S.selected),
    focus = photo || (!mini && chosen),
    ls = valid.map((p) => Number(p.lat_corrected || p.lat)),
    os = valid.map((p) => Number(p.lon_corrected || p.lon));
  let center = focus
      ? [
          Number(focus.lat_corrected || focus.lat),
          Number(focus.lon_corrected || focus.lon),
        ]
      : [
          (Math.min(...ls) + Math.max(...ls)) / 2,
          (Math.min(...os) + Math.max(...os)) / 2,
        ],
    zoom = focus ? 18 : 15;
  const original = center.slice(),
    originalZoom = zoom;
  let ro,
    dead = false,
    drag = null;
  const project = (lat, lon, z) => {
      const n = 256 * 2 ** z,
        s = Math.sin((Math.max(-85, Math.min(85, lat)) * Math.PI) / 180);
      return [
        ((lon + 180) / 360) * n,
        (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * n,
      ];
    },
    inverse = (x, y, z) => {
      const n = 256 * 2 ** z;
      return [
        (180 / Math.PI) * Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n))),
        (x / n) * 360 - 180,
      ];
    };
  el.innerHTML =
    '<div class="geo-surface" tabindex="0" role="region" aria-label="Geographic map. Use plus/minus to zoom and arrow keys to pan."><div class="geo-tiles"></div><svg class="geo-overlay" aria-hidden="true"></svg><div class="geo-markers"></div></div><div class="geo-controls"><button data-map="in" aria-label="Zoom in">+</button><button data-map="out" aria-label="Zoom out">−</button><button data-map="reset" aria-label="Recenter">Centre</button></div><div class="geo-note">Loading street basemap…</div><div class="geo-credit">© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a></div>';
  const surface = $(".geo-surface", el),
    tiles = $(".geo-tiles", el),
    overlay = $(".geo-overlay", el),
    markers = $(".geo-markers", el),
    note = $(".geo-note", el);
  function draw() {
    if (dead || !el.isConnected) return;
    const w = el.clientWidth,
      h = el.clientHeight,
      c = project(...center, zoom),
      origin = [c[0] - w / 2, c[1] - h / 2],
      xy = (lat, lon) => {
        let p = project(lat, lon, zoom);
        return [p[0] - origin[0], p[1] - origin[1]];
      };
    tiles.innerHTML = "";
    let good = 0;
    note.textContent =
      "Street basemap loading · " + center.map((v) => v.toFixed(5)).join(", ");
    for (
      let x = Math.floor(origin[0] / 256);
      x <= Math.floor((origin[0] + w) / 256);
      x++
    )
      for (
        let y = Math.floor(origin[1] / 256);
        y <= Math.floor((origin[1] + h) / 256);
        y++
      ) {
        if (x < 0 || y < 0 || x >= 2 ** zoom || y >= 2 ** zoom) continue;
        const im = document.createElement("img");
        im.src = [
          "https:",
          "",
          "tile.openstreetmap.org",
          zoom,
          x,
          y + ".png",
        ].join("/");
        im.alt = "";
        im.width = 256;
        im.height = 256;
        im.style.left = 256 * x - origin[0] + "px";
        im.style.top = 256 * y - origin[1] + "px";
        im.onload = () => {
          good++;
          note.textContent =
            "Street basemap · " + center.map((v) => v.toFixed(5)).join(", ");
        };
        im.onerror = () => {
          im.style.visibility = "hidden";
          if (!good)
            note.textContent =
              "Basemap unavailable · actual coordinates remain visible";
        };
        tiles.append(im);
      }
    let extra = "";
    if (chosen) {
      let pin = d.addresses.find((a) => a.address_id === chosen.address_id);
      if (!pin && N(chosen.official_lat) !== null)
        pin = { lat: chosen.official_lat, lon: chosen.official_lon };
      if (S.mode === "addresses") pin = chosen;
      if (pin) {
        const [x, y] = xy(Number(pin.lat), Number(pin.lon));
        extra = `<rect x="${x - 6}" y="${y - 6}" width="12" height="12" fill="white" stroke="#152e40" stroke-width="3"/>`;
      }
    }
    if (photo) {
      const [x, y] = xy(
        Number(photo.lat_corrected || photo.lat),
        Number(photo.lon_corrected || photo.lon),
      );
      extra += `<circle cx="${x}" cy="${y}" r="10" fill="white" stroke="#17569b" stroke-width="4"/>`;
    }
    overlay.setAttribute("viewBox", `0 0 ${w} ${h}`);
    overlay.innerHTML = `<polyline points="${valid.map((p) => xy(Number(p.lat_corrected || p.lat), Number(p.lon_corrected || p.lon)).join(",")).join(" ")}" fill="none" stroke="#17569b" stroke-width="3"/>${extra}`;
    markers.innerHTML = mini
      ? ""
      : rs
          .map((r) => {
            if (N(r.lat) === null || N(r.lon) === null) return "";
            const [x, y] = xy(Number(r.lat), Number(r.lon));
            if (x < -30 || y < -30 || x > w + 30 || y > h + 30) return "";
            return `<button class="geo-pin ${ID(r) === S.selected ? "selected" : ""}" style="left:${x}px;top:${y}px;background:${C(r.status)}" data-id="${E(ID(r))}" aria-label="Inspect ${E(r.reading_display || r.address || ID(r))}">${ID(r) === S.selected ? E(r.reading || "●") : ""}</button>`;
          })
          .join("");
    markers.querySelectorAll("button").forEach((n) => {
      n.onpointerdown = (e) => e.stopPropagation();
      n.onclick = () =>
        onSelect ? onSelect(n.dataset.id) : toast(n.getAttribute("aria-label"));
    });
  }
  $(".geo-controls", el).onclick = (e) => {
    const a = e.target.dataset.map;
    if (a === "in") zoom = Math.min(20, zoom + 1);
    if (a === "out") zoom = Math.max(13, zoom - 1);
    if (a === "reset") {
      center = original.slice();
      zoom = originalZoom;
    }
    draw();
  };
  surface.onkeydown = (e) => {
    let c = project(...center, zoom),
      handled = true;
    if (e.key === "+") zoom = Math.min(20, zoom + 1);
    else if (e.key === "-") zoom = Math.max(13, zoom - 1);
    else if (e.key === "ArrowLeft") c[0] -= 80;
    else if (e.key === "ArrowRight") c[0] += 80;
    else if (e.key === "ArrowUp") c[1] -= 80;
    else if (e.key === "ArrowDown") c[1] += 80;
    else handled = false;
    if (handled) {
      e.preventDefault();
      if (e.key.startsWith("Arrow")) center = inverse(...c, zoom);
      draw();
    }
  };
  surface.onpointerdown = (e) => {
    if (e.pointerType !== "mouse" || e.button !== 0) return;
    drag = { x: e.clientX, y: e.clientY, c: project(...center, zoom) };
    surface.setPointerCapture(e.pointerId);
  };
  surface.onpointerup = (e) => {
    if (!drag) return;
    center = inverse(
      drag.c[0] - e.clientX + drag.x,
      drag.c[1] - e.clientY + drag.y,
      zoom,
    );
    drag = null;
    draw();
  };
  ro = new ResizeObserver(() => {
    if (!el.isConnected) {
      dead = true;
      ro.disconnect();
    } else draw();
  });
  ro.observe(el);
  el._cleanup = () => {
    dead = true;
    ro.disconnect();
  };
  draw();
}
function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
/** Export filtered records and neutralize spreadsheet-formula prefixes. */
function exportCSV() {
  const cs =
    S.mode === "plates"
      ? [
          "plate_id",
          "reading_display",
          "candidate_address",
          "candidate_distance_m",
          "recognition_state",
          "location_state",
          "status",
          "status_label",
          "n_photos",
          "confidence",
          "lat",
          "lon",
          "explanation",
        ]
      : [
          "address_id",
          "address",
          "status",
          "status_label",
          "n_photos_in_view",
          "supporting_photo_count",
          "confidence",
          "lat",
          "lon",
          "explanation",
        ];
  const cell = (v) => {
    let s = String(v ?? "");
    if (/^[=+@\-\t\r]/.test(s)) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  };
  download(
    S.data.id + "-" + S.mode + "-filtered.csv",
    "\ufeff" +
      [
        cs.join(","),
        ...rows().map((r) => cs.map((k) => cell(r[k])).join(",")),
      ].join("\r\n"),
    "text/csv;charset=utf-8",
  );
}
/** Reveal capture order, not simulated inference progress. */
function playback() {
  $("#app").innerHTML =
    heading(
      "ROUTE PLAYBACK",
      "Replay the inspection route.",
      "Browse the images in capture order and open the address cases along the route.",
      `<a class="btn" href="#review/${E(S.data.id)}">Open review workspace ↗</a>`,
    ) +
    `<div class="toolbar"><label class="control">Recording<select id="playSurvey">${options()}</select></label><span class="tag amber">PREVIOUSLY PROCESSED</span></div><div class="playback-grid"><section class="panel"><div class="panel-head"><h2 id="frameTitle"></h2><select id="side" aria-label="Camera view"><option value="left">Left view</option><option value="right">Right view</option></select></div><div class="frame" id="frame"></div><div class="pad"><div class="actions playback-actions"><button class="btn primary" id="playToggle">Play recording</button><button class="btn" id="reset">Reset</button><div class="speed-control"><label for="speed" class="speed-label">Playback speed:</label><select id="speed" aria-label="Playback speed"><option value="1">1 position / s</option><option value="2" selected>2 positions / s</option><option value="5">5 positions / s</option></select></div></div><input id="scrub" class="range" type="range" min="0" max="${S.data.photos.length - 1}" value="0" aria-label="Capture position"><div class="progress"><span id="position"></span><span id="seen"></span></div></div></section><section class="panel"><div class="panel-head"><h2>Recorded route</h2><span class="tag">CAPTURE LOCATIONS</span></div><div class="map" id="playMap"></div><div class="pad"><p class="muted">Markers show cases seen by this point. Their assessments use the complete recording.</p></div></section></div><section class="panel" style="margin-top:20px"><div class="panel-head"><h2>Observations at this position</h2><span class="muted" id="currentCount"></span></div><div id="observations" class="observation-list"></div></section><div class="notice">Playback displays previously processed images and results, not fresh inference.</div>`;
  $("#playSurvey").onchange = (e) =>
    (location.hash = "#playback/" + e.target.value);
  $("#playToggle").onclick = () => (S.timer ? pause() : start());
  $("#reset").onclick = () => {
    pause();
    S.index = 0;
    update();
  };
  $("#scrub").oninput = (e) => {
    pause();
    S.index = Number(e.target.value);
    update();
  };
  $("#speed").value = String(S.speed);
  $("#speed").onchange = (e) => {
    S.speed = Number(e.target.value);
    if (S.timer) {
      pause();
      start();
    }
  };
  $("#side").value = S.side;
  $("#side").onchange = (e) => {
    S.side = e.target.value;
    update();
  };
  update();
}
function pause() {
  stop();
  if ($("#playToggle")) $("#playToggle").textContent = "Play recording";
}
function start() {
  if (S.index >= S.data.photos.length - 1) S.index = 0;
  $("#playToggle").textContent = "Pause";
  S.timer = setInterval(() => {
    S.index++;
    if (S.index >= S.data.photos.length - 1) {
      S.index = S.data.photos.length - 1;
      pause();
    }
    update();
  }, 1000 / S.speed);
}
function update() {
  const p = S.data.photos[S.index],
    seq = Number(p.sequence_number),
    visible = S.data.plates.filter((p) => p.first_photo <= seq),
    current = S.data.plates.filter((p) =>
      p.photos.split(";").includes(String(seq)),
    ),
    im = p.views[S.side];
  $("#frameTitle").textContent = "Capture " + seq + " · " + S.data.name;
  $("#frame").innerHTML =
    (im
      ? `<img src="${E(im)}" alt="Recorded ${E(S.side)} view at capture ${seq}">`
      : '<div class="empty" style="color:white">View not included in recorded assets.</div>') +
    `<span class="frame-label">RECORDED IMAGE · ${E(S.side.toUpperCase())}</span>`;
  $("#scrub").value = S.index;
  $("#position").textContent =
    `Position ${S.index + 1} / ${S.data.photos.length}`;
  $("#seen").textContent = visible.length + " grouped plates seen";
  map($("#playMap"), S.data, visible, null, false, p);
  $("#currentCount").textContent = current.length + " grouped plates";
  $("#observations").innerHTML =
    current
      .map(
        (p) =>
          `<div class="observation"><div><strong>${E(p.reading_display)}</strong> <span class="muted">${E(p.plate_id)} · saved result</span></div>${badge(p)}</div>`,
      )
      .join("") ||
    '<div class="empty">No grouped plate linked to this capture position.</div>';
}
$("#scopeButton").onclick = () => $("#scope").showModal();
$("#closeScope").onclick = () => $("#scope").close();
$("#menu").onclick = () => {
  const open = $("#sidebar").classList.toggle("open");
  $("#menu").setAttribute("aria-expanded", String(open));
};
window.addEventListener("hashchange", route);
(async () => {
  try {
    const r = await fetch("data/catalog.json");
    if (!r.ok) throw Error("Catalog unavailable");
    S.catalog = (await r.json()).map((c) => ({
      ...c,
      ...(PRODUCT.routes[c.id] || {}),
    }));
    if (!S.catalog.length) throw Error("No inspection recordings");
    await route();
  } catch (e) {
    error(e);
  }
})();

function initAnimations() {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) {
    document.querySelectorAll(".stat-counter[data-target]").forEach((e) => {
      e.textContent = F(e.dataset.target);
    });
    document
      .querySelectorAll(".reveal-up, .reveal-fade, .reveal-scale")
      .forEach((e) => e.classList.add("is-revealed"));
    return;
  }
  const reveals = document.querySelectorAll(
    ".reveal-up, .reveal-fade, .reveal-scale",
  );
  if ("IntersectionObserver" in window && reveals.length) {
    const obs = new IntersectionObserver(
      (entries, o) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-revealed");
            o.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -30px 0px" },
    );
    reveals.forEach((r) => obs.observe(r));
  } else {
    reveals.forEach((r) => r.classList.add("is-revealed"));
  }
  const counters = document.querySelectorAll(".stat-counter[data-target]");
  if ("IntersectionObserver" in window && counters.length) {
    const cObs = new IntersectionObserver(
      (entries, o) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const el = entry.target;
            o.unobserve(el);
            const target = Number(el.dataset.target) || 0;
            const duration = 1500;
            const t0 = performance.now();
            const frame = (now) => {
              const p = Math.min((now - t0) / duration, 1);
              const ease = 1 - Math.pow(1 - p, 3);
              el.textContent = F(Math.round(target * ease));
              if (p < 1) requestAnimationFrame(frame);
              else el.textContent = F(target);
            };
            requestAnimationFrame(frame);
          }
        });
      },
      { threshold: 0.15 },
    );
    counters.forEach((c) => cObs.observe(c));
  } else {
    counters.forEach((c) => {
      c.textContent = F(c.dataset.target);
    });
  }
  const stepCards = document.querySelectorAll(".steps article");
  stepCards.forEach((c) => {
    c.addEventListener("mouseenter", () => {
      stepCards.forEach((s) => s.classList.remove("step-active"));
      c.classList.add("step-active");
    });
  });
  if (stepCards.length) stepCards[0].classList.add("step-active");
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden && S.timer) pause();
});
window.addEventListener("pagehide", stop);

$("#scope")
  .querySelectorAll('a[href^="#"]')
  .forEach((a) => a.addEventListener("click", () => $("#scope").close()));
document.addEventListener("visibilitychange", () => {
  if (document.hidden)
    document.querySelectorAll("video").forEach((v) => v.pause());
});
