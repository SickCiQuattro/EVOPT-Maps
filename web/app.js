"use strict";

const $ = (id) => document.getElementById(id);
const STORE_KEY = "evopt:v1";
const EXAMPLE = { area: "Pieve Emanuele, Italy", start: "Pieve Emanuele", goal: "Siziano", vehicle: "", temp: -10, startSoc: 15, minSoc: 10, algorithm: "astar", legs: "fastest", compare: true, elevation: true };
const STEPS = [
  { label: "Locating your places", stages: ["locating"] },
  { label: "Road network", stages: ["roads"] },
  { label: "Charging stations", stages: ["stations", "power"] },
  { label: "Searching the fastest route", stages: ["planning"] },
];
const ERROR_TITLES = {
  not_found: "Place not found",
  outside_area: "Outside the map area",
  no_route: "No route found",
  map_unavailable: "Map data unavailable",
  unreachable: "Cannot reach the planner",
  too_large: "Area too large for this algorithm",
  internal: "Something went wrong",
};

const VIEWS = ["plan", "vehicles", "algorithms", "about"];
const state = { vehicles: [], algorithms: [], result: null, job: 0, timer: 0, started: 0, activeIndex: -1 };
const layers = { route: null, stations: null, stops: [] };
let map;

/* ---------- small helpers ---------- */
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null) el.append(kid);
  return el;
}
const strong = (t) => h("strong", {}, t);
const kwh = (v) => v.toFixed(v < 1 ? 2 : 1);
const pct = (f) => `${Math.round(f * 100)} %`;
function dur(min) {
  const m = Math.round(min);
  return m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}` : `${m} min`;
}
const clock = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const load = () => { try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch { return {}; } };
const save = (v) => { try { localStorage.setItem(STORE_KEY, JSON.stringify(v)); } catch { /* storage unavailable */ } };

/* ---------- form ---------- */
const sliders = [
  { id: "temp", out: "temp-out", fmt: (v) => `${v} °C` },
  { id: "start-soc", out: "start-soc-out", fmt: (v) => `${v} %` },
  { id: "min-soc", out: "min-soc-out", fmt: (v) => `${v} %` },
];
function paintSlider(s) {
  const el = $(s.id);
  const p = ((el.value - el.min) / (el.max - el.min)) * 100;
  el.style.setProperty("--p", `${p}%`);
  $(s.out).textContent = s.fmt(el.value);
  el.setAttribute("aria-valuetext", s.fmt(el.value).replace("-", "−"));
}
function onSlider(e) {
  const start = $("start-soc"), min = $("min-soc");
  if (e.target === start && +start.value <= +min.value) min.value = Math.max(+min.min, +start.value - 5);
  if (e.target === min && +min.value >= +start.value) start.value = Math.min(+start.max, +min.value + 5);
  sliders.forEach(paintSlider);
  persist();
}
function values() {
  return {
    area: $("area").value.trim(), start: $("start").value.trim(), goal: $("goal").value.trim(), vehicle: $("vehicle").value,
    temp: +$("temp").value, startSoc: +$("start-soc").value, minSoc: +$("min-soc").value,
    algorithm: $("algorithm").value, legs: $("legs").value, compare: $("compare").checked, elevation: $("elevation").checked,
    speed: $("speed").value, minKw: +$("minkw").value, known: $("known").checked, compareSpeeds: $("compare-speeds").checked,
  };
}
/* the request the server expects; `over` changes single values (the cruise speed for the comparison) */
function requestBody(v, over = {}) {
  return {
    area: v.area, start: v.start, goal: v.goal, vehicle: v.vehicle, temp_c: v.temp, start_soc: v.startSoc / 100, min_soc: v.minSoc / 100,
    algorithm: v.algorithm, legs: v.legs, compare: v.compare, elevation: v.elevation,
    max_speed_kph: v.speed ? +v.speed : null, min_kw: v.minKw, known_power: v.known, ...over,
  };
}
/* the form in the address bar, so a trip can be shared: ?from=...&to=... */
const QUERY = { area: "area", start: "from", goal: "to", vehicle: "car", temp: "temp", startSoc: "soc", minSoc: "min", speed: "speed", minKw: "kw", algorithm: "alg", legs: "legs" };
function toQuery(v) {
  const q = new URLSearchParams();
  for (const [k, name] of Object.entries(QUERY)) if (v[k] !== "" && v[k] != null) q.set(name, v[k]);
  if (v.known) q.set("known", "1");
  if (!v.elevation) q.set("flat", "1");
  return q;
}
function fromQuery(q) {
  if (!q.get("from") || !q.get("to")) return null;
  const n = (name) => (q.has(name) && Number.isFinite(+q.get(name)) ? +q.get(name) : undefined);
  const out = { area: q.get("area") ?? undefined, start: q.get("from"), goal: q.get("to"), vehicle: q.get("car") ?? undefined,
    temp: n("temp"), startSoc: n("soc"), minSoc: n("min"), speed: q.get("speed") ?? "", minKw: n("kw") ?? 0, algorithm: q.get("alg") ?? undefined,
    legs: q.get("legs") ?? undefined, known: q.get("known") === "1", elevation: q.get("flat") !== "1" };
  return Object.fromEntries(Object.entries(out).filter(([, x]) => x !== undefined));
}
function persist() { save(values()); paintSummary(); }
function paintSummary() {
  const v = values();
  $("settings-summary").textContent = `${v.vehicle} \u00b7 ${v.start} \u2192 ${v.goal}. ${String(v.temp).replace("-", "\u2212")}\u00a0\u00b0C, ${v.startSoc}\u00a0% to ${v.minSoc}\u00a0%.`;
}
function fill(v) {
  $("area").value = v.area ?? ""; $("start").value = v.start ?? ""; $("goal").value = v.goal ?? "";
  if (v.vehicle && state.vehicles.some((x) => x.name === v.vehicle)) $("vehicle").value = v.vehicle;
  $("temp").value = v.temp; $("start-soc").value = v.startSoc; $("min-soc").value = v.minSoc;
  if (state.algorithms.some((a) => a.id === v.algorithm)) $("algorithm").value = v.algorithm;
  if (["fastest", "pareto"].includes(v.legs)) $("legs").value = v.legs;
  $("compare").checked = !!v.compare;
  $("elevation").checked = v.elevation !== false;
  $("speed").value = ["130", "110", "90"].includes(String(v.speed)) ? String(v.speed) : "";
  $("minkw").value = ["22", "50", "100"].includes(String(v.minKw)) ? String(v.minKw) : "0";
  $("known").checked = !!v.known;
  $("compare-speeds").checked = !!v.compareSpeeds;
  sliders.forEach(paintSlider); paintSpec(); paintSummary(); paintAlgorithmHelp();
}
function paintAlgorithmHelp() {
  $("algorithm-help").textContent = state.algorithms.find((a) => a.id === $("algorithm").value)?.summary ?? "";
}
function paintSpec() {
  const v = state.vehicles.find((x) => x.name === $("vehicle").value);
  const spec = $("vehicle-spec");
  spec.replaceChildren();
  if (!v) return;
  spec.append(`${v.capacity_kwh} kWh usable battery · charges at up to ${v.max_charge_kw} kW`);
  if (v.max_charge_kw < 10) spec.append(h("span", { class: "warn" }, "Slow charging: stops will be long."));
}
function clearFieldErrors() {
  for (const id of ["area", "start", "goal"]) { $(id).removeAttribute("aria-invalid"); $(`${id}-err`).hidden = true; }
}
function fieldError(id, text) {
  $(id).setAttribute("aria-invalid", "true");
  const e = $(`${id}-err`); e.textContent = text; e.hidden = false;
}
function validate(v) {
  clearFieldErrors();
  let first = null;
  for (const [id, label] of [["area", "an area"], ["start", "a starting point"], ["goal", "a destination"]]) {
    if (v[id].length < 2) { fieldError(id, `Enter ${label}.`); first ||= id; }
  }
  if (first) $(first).focus();
  return !first;
}

/* ---------- panels ---------- */
function show(panel) {
  for (const id of ["status", "error", "result", "empty"]) $(id).hidden = id !== panel;
  $("settings").open = panel === "error" || panel === "empty";
  document.querySelector(".rail").scrollTop = 0;
}
function renderSteps(stage) {
  const at = Math.max(0, STEPS.findIndex((s) => s.stages.includes(stage)));
  $("steps").replaceChildren(...STEPS.map((s, i) => {
    const st = i < at ? "done" : i === at ? "active" : "wait";
    const tag = { done: "done", active: "working", wait: "waiting" }[st];
    return h("li", { "data-state": st }, h("span", { class: "dot", "aria-hidden": "true" }), s.label, h("span", { class: "tag" }, tag));
  }));
  $("live").textContent = STEPS[at].label;
  $("status-note").textContent = stage === "roads"
    ? "First time for this area: downloading its roads can take a few minutes. It is then saved for 30 days."
    : stage === "stations" || stage === "power" ? "Finding charging stations in OpenStreetMap and Open Charge Map." : "";
}

/* ---------- planning ---------- */
async function plan(e) {
  e.preventDefault();
  const v = values();
  if (!validate(v)) return;
  persist();
  const id = ++state.job;
  clearRoute();
  showCompare("none");
  setBusy(true);
  show("status");
  renderSteps("locating");
  state.started = Date.now();
  $("elapsed").textContent = "0:00";
  clearInterval(state.timer);
  state.timer = setInterval(() => ($("elapsed").textContent = clock((Date.now() - state.started) / 1000)), 1000);
  try {
    const r = await fetch("/api/plan", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody(v)),
    });
    if (!r.ok) return fail(id, { code: "internal", message: "Some of the values are not valid. Check the form and try again." });
    await poll(id, (await r.json()).job_id);
  } catch {
    fail(id, { code: "unreachable", message: "The planner server is not responding. Check that it is running, then try again." });
  }
}
async function poll(id, jobId) {
  for (;;) {
    await new Promise((res) => setTimeout(res, 1000));
    if (id !== state.job) return; // cancelled or replaced
    const job = await (await fetch(`/api/jobs/${jobId}`)).json();
    if (job.status === "running") { renderSteps(job.stage); continue; }
    if (job.status !== "done") return fail(id, job.error);
    state.jobId = jobId;
    done(id, job.result);
    if (job.compare) await pollCompare(id, jobId, job).catch(() => id === state.job && showCompare("error"));
    return;
  }
}
async function pollCompare(id, jobId, job) {
  for (;;) {
    if (id !== state.job) return; // another plan has taken over
    if (job.compare === "running") {
      const [done, total] = job.compare_progress;
      showCompare("pending", `${done} of ${total || state.algorithms.length} algorithms done.`);
    } else if (job.compare === "done") {
      return showCompare("table", job.comparison);
    } else {
      return showCompare("error");
    }
    await new Promise((res) => setTimeout(res, 1000));
    job = await (await fetch(`/api/jobs/${jobId}`)).json();
  }
}
function showCompare(mode, payload) {
  $("compare-pending").hidden = mode !== "pending";
  $("compare-result").hidden = mode !== "table";
  if (mode === "pending") $("compare-progress").textContent = payload;
  if (mode === "table") renderAlgorithms(state.result, payload);
  if (mode === "error") {
    $("compare-pending").hidden = false;
    $("compare-progress").textContent = "The comparison could not be completed.";
  }
}
function finish(id) {
  if (id !== state.job) return false;
  clearInterval(state.timer);
  setBusy(false);
  return true;
}
function setBusy(busy) {
  const b = $("submit");
  b.disabled = busy;
  b.textContent = busy ? "Planning…" : "Plan route";
  b.setAttribute("aria-busy", busy);
}
function cancel() { state.job++; clearInterval(state.timer); setBusy(false); show("empty"); $("submit").focus(); }
function fail(id, err) {
  if (!finish(id)) return;
  $("error-title").textContent = ERROR_TITLES[err.code] ?? ERROR_TITLES.internal;
  $("error-text").textContent = err.message;
  $("retry").hidden = !["map_unavailable", "internal", "unreachable"].includes(err.code);
  const v = values();
  for (const f of ["area", "start", "goal"]) if (v[f] && err.message.includes(`“${v[f]}”`)) fieldError(f, "Check this place.");
  show("error");
  $("error-title").focus();
}

/* ---------- result ---------- */
function done(id, res) {
  if (!finish(id)) return;
  const s = res.summary, v = values();
  $("total").textContent = dur(s.total_min);
  $("s-drive").textContent = dur(s.drive_min);
  $("s-charge").textContent = res.stops.length ? dur(s.charge_min) : "none";
  $("s-dist").textContent = `${Math.round(s.distance_km)} km`;
  $("s-arrive").textContent = pct(s.arrival_soc);
  const hasElevation = s.net_climb_m != null;
  $("s-climb-box").hidden = $("s-high-box").hidden = !hasElevation;
  if (hasElevation) {
    const climb = Math.round(s.net_climb_m);
    $("s-climb").textContent = `${climb > 0 ? "+" : climb < 0 ? "\u2212" : ""}${Math.abs(climb).toLocaleString("en")}\u00a0m`;
    $("s-high").textContent = `${Math.round(s.highest_m).toLocaleString("en")}\u00a0m`;
  }
  $("line").replaceChildren(...diagram(res, v));
  renderProfile(res, v);
  $("share-out").hidden = true;
  $("speeds").hidden = true;
  if (v.compareSpeeds) compareSpeeds(state.job, v, res);
  state.result = res;
  const algo = state.algorithms.find((a) => a.id === res.algorithm)?.name ?? res.algorithm;
  $("solved-by").textContent = `Solved with ${algo}: ${res.stats.expanded?.toLocaleString("en") ?? "?"} states, ${Math.max(1, Math.round(res.stats.search_ms ?? 0)).toLocaleString("en")}\u00a0ms.`;
  $("compare-link").hidden = !values().compare;
  showCompare(values().compare ? "pending" : "none", values().compare ? "Starting\u2026" : "");
  drawMap(res);
  show("result");
  $("result-title").focus({ preventScroll: true });
}
function station(n, cls, name, note, i) {
  const out = h("span", { class: "busy-out", role: "status" });
  const ask = cls === "stop" && h("button", { type: "button", class: "text busy", onclick: (e) => busy(i, e.currentTarget, out) }, "If it is busy?");
  return h("li", {}, h("button", { type: "button", class: `st ${cls}`, "data-n": n, "data-i": i, onclick: () => activate(i, true), onfocus: () => activate(i, false) },
    h("span", { class: "st-name" }, name), h("span", { class: "st-note" }, ...note)), ask || null, out);
}
function diagram(res, v) {
  const items = [station("", "end", res.start.label, ["Leave with ", strong(`${v.startSoc} %`)], 0)];
  res.stops.forEach((s, k) => items.push(station(k + 1, "stop", `Charging stop ${k + 1}`, [
    ...(s.label ? [h("strong", {}, s.label), h("br")] : []),
    "Arrive ", strong(pct(s.soc_before)), " · charge ", strong(dur(s.minutes)), " to ", strong(pct(s.soc_after)),
    h("br"), `+${kwh(s.kwh)}\u00a0kWh at up to ${+s.power_kw.toFixed(1)}\u00a0kW`,
    h("span", { class: "gauge", role: "img", "aria-label": `Battery from ${pct(s.soc_before)} to ${pct(s.soc_after)}` },
      h("i", { style: `left:${s.soc_before * 100}%;width:${(s.soc_after - s.soc_before) * 100}%` })),
  ], k + 1)));
  const last = res.stops.length + 1;
  items.push(station("", "end", res.goal.label, res.stops.length
    ? ["Arrive with ", strong(pct(res.summary.arrival_soc))]
    : ["No charging stop needed. Arrive with ", strong(pct(res.summary.arrival_soc))], last));
  return items;
}

/* ---------- map ---------- */
const icon = (cls, html = "", size = 24) => L.divIcon({ className: "", html: `<span class="mk ${cls}">${html}</span>`, iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
function initMap() {
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // one-finger drags on a touch screen scroll the page; the map keeps its zoom buttons and pinch
  map = L.map("map", { zoomControl: false, dragging: !L.Browser.mobile, zoomAnimation: !still, fadeAnimation: !still, markerZoomAnimation: !still }).setView([45.2, 9.1], 8);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "© <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
  }).addTo(map);
}
function drawMap(res) {
  for (const l of [layers.route, layers.stations]) l && l.remove();
  layers.stops = [];
  const line = res.route;
  const casing = L.polyline(line, { className: "route-casing", weight: 11, opacity: 1, interactive: false });
  const routeLine = L.polyline(line, { className: "route-line", weight: 6, opacity: 1, lineJoin: "round", interactive: false });
  const pts = [[line[0], icon("end"), 0], ...res.stops.map((s, k) => [[s.lat, s.lon], icon("stop", k + 1, 32), k + 1]), [line[line.length - 1], icon("end"), res.stops.length + 1]];
  const markers = pts.map(([ll, ic, i]) => L.marker(ll, { icon: ic, keyboard: false, zIndexOffset: 1000 }).on("click", () => activate(i, true)));
  layers.route = L.layerGroup([casing, routeLine, ...markers]).addTo(map);
  layers.stops = markers;
  layers.stations = L.layerGroup(res.stations.map(([la, lo, kw]) => L.marker([la, lo], { icon: icon("station", "", 12), keyboard: false }).bindTooltip(`${Math.round(kw)} kW`)));
  $("station-count").textContent = `(${res.stations.length})`;
  toggleStations();
  const wide = matchMedia("(min-width: 901px)").matches; // the rail floats over the left 432 px of the map
  map.fitBounds(routeLine.getBounds(), { paddingTopLeft: [wide ? 480 : 32, 80], paddingBottomRight: [64, 64], animate: false });
  state.activeIndex = -1;
}
function clearRoute() {
  for (const l of [layers.route, layers.stations]) l && l.remove();
  layers.route = layers.stations = null;
  layers.stops = [];
  $("station-count").textContent = "";
}
function toggleStations() {
  if (!layers.stations) return;
  $("show-stations").checked ? layers.stations.addTo(map) : layers.stations.remove();
}
function activate(i, pan) {
  state.activeIndex = i;
  document.querySelectorAll(".st").forEach((b) => b.classList.toggle("is-active", +b.dataset.i === i));
  layers.stops.forEach((m, k) => m.getElement()?.firstChild.classList.toggle("is-active", k === i));
  if (pan && layers.stops[i]) {
    map.setView(layers.stops[i].getLatLng(), Math.max(map.getZoom(), 13), { animate: false });
    if (matchMedia("(min-width: 901px)").matches) map.panBy([-216, 0], { animate: false });
  }
}

/* ---------- algorithms ---------- */
const num = (v, d = 0) => v.toLocaleString("en", { minimumFractionDigits: d, maximumFractionDigits: d });
function insights(rows) {
  const by = (id) => rows.find((r) => r.algorithm === id);
  const out = [];
  const [d, a, w, r, g] = ["dijkstra", "astar_potential", "wastar", "ara", "greedy"].map(by);
  if (g?.time_min != null && g.gap_pct > 0.05) out.push(`The naive driver needs ${num(g.gap_pct, 1)}\u00a0% more time than the best plan.`);
  else if (g && g.time_min == null) out.push("The naive driver could not complete this trip.");
  if (d?.expanded && a?.expanded && a.expanded < d.expanded) out.push(`A* with exact potentials expands ${num((1 - a.expanded / d.expanded) * 100)}\u00a0% fewer states than Dijkstra and finds the same trip.`);
  if (w?.expanded && d?.expanded && w.expanded < d.expanded) out.push(`Weighted A* expands ${num(d.expanded / w.expanded, 1)}\u00d7 fewer states than Dijkstra and lands ${num(w.gap_pct, 1)}\u00a0% above the best trip.`);
  if (r?.anytime?.length > 1 && r.anytime[0].expanded < 0.9 * r.anytime.at(-1).expanded) {
    const first = r.anytime[0], last = r.anytime.at(-1);
    out.push(`ARA* had a first answer after ${num(first.expanded)} states, ${num(first.expanded / last.expanded * 100, first.expanded / last.expanded < 0.01 ? 1 : 0)}\u00a0% of the effort of its final proven-optimal one.`);
  }
  return out;
}
function renderAlgorithms(res, rows) {
  const info = Object.fromEntries(state.algorithms.map((a) => [a.id, a]));
  $("insights").replaceChildren(...insights(rows).map((t) => h("li", {}, t)));
  $("compare-rows").replaceChildren(...rows.map((r) => {
    const chosen = r.algorithm === res.algorithm;
    const name = h("th", { scope: "row" }, info[r.algorithm]?.name ?? r.algorithm, chosen ? h("span", { class: "tag" }, " selected") : null,
      h("span", { class: "sub" }, r.note ?? info[r.algorithm]?.summary ?? ""));
    if (r.time_min == null) return h("tr", {}, name, h("td", { class: "r", colspan: 5 }, "No result"));
    const gap = r.gap_pct < 0.05 ? "best" : `+${num(r.gap_pct, 1)}\u00a0%`;
    return h("tr", { class: r.gap_pct < 0.05 ? "best" : "" }, name, h("td", { class: "r num" }, `${num(r.time_min, 2)}\u00a0min`),
      h("td", { class: "r num" }, gap), h("td", { class: "r num" }, r.stops), h("td", { class: "r num" }, num(r.expanded)), h("td", { class: "r num" }, `${num(r.search_ms, 1)}\u00a0ms`));
  }));
  const ara = rows.find((r) => r.algorithm === "ara");
  $("anytime").hidden = !ara?.anytime;
  if (ara?.anytime) $("anytime-rows").replaceChildren(...ara.anytime.map((s) => h("tr", {},
    h("td", { class: "r num" }, `\u00d7${num(s.eps, 1)}`), h("td", { class: "r num" }, `${num(s.time_s / 60, 2)}\u00a0min`),
    h("td", { class: "r num" }, `${num((s.bound - 1) * 100, 1)}\u00a0%`), h("td", { class: "r num" }, num(s.expanded)))));
}

/* ---------- vehicles ---------- */
function renderRoster() {
  const current = $("vehicle").value;
  $("roster").replaceChildren(...state.vehicles.map((v) => {
    const on = v.name === current;
    return h("li", { class: "cell", "data-selected": String(on) },
      h("div", { class: "cell-head" }, v.name),
      h("dl", {}, h("dt", {}, "Usable battery"), h("dd", { class: "num" }, `${v.capacity_kwh} kWh`), h("dt", {}, "Fastest charging"), h("dd", { class: "num" }, `${v.max_charge_kw} kW`), h("dt", {}, "Consumption data"), h("dd", {}, v.source ? "Calibrated" : "Approximate")),
      on ? h("span", { class: "selected-tag" }, "Selected") : h("button", { type: "button", class: "secondary", onclick: () => { $("vehicle").value = v.name; paintSpec(); persist(); location.hash = "#plan"; } }, "Use this vehicle"));
  }));
}

/* ---------- views ---------- */
function route(first) {
  const view = VIEWS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "plan";
  for (const v of VIEWS) $(`view-${v}`).hidden = v !== view;
  document.querySelectorAll("nav a").forEach((a) => (a.dataset.view === view ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  if (view === "vehicles") renderRoster();
  if (view === "plan") map.invalidateSize();
  if (!first) $(view === "plan" ? "plan-title" : `${view}-title`).focus({ preventScroll: true });
}

/* ---------- battery profile ---------- */
const SVG = "http://www.w3.org/2000/svg";
const svg = (tag, attrs = {}, text) => {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (text != null) el.textContent = text;
  return el;
};
function renderProfile(res, v) {
  const pts = res.profile;
  $("profile-fig").hidden = !pts?.length;
  if (!pts?.length) return;
  const W = 360, H = 132, L = 34, R = 8, T = 8, B = 24;
  const total = pts.at(-1)[0] || 1;
  const x = (km) => L + (km / total) * (W - L - R), y = (soc) => T + (1 - soc) * (H - T - B);
  const g = [];
  for (const t of [0, 0.5, 1]) {
    g.push(svg("line", { x1: L, x2: W - R, y1: y(t), y2: y(t), class: "grid" }), svg("text", { x: L - 6, y: y(t) + 4, class: "tick", "text-anchor": "end" }, `${t * 100}%`));
  }
  g.push(svg("line", { x1: L, x2: W - R, y1: y(v.minSoc / 100), y2: y(v.minSoc / 100), class: "floor" }));
  const line = pts.map(([km, soc]) => `${x(km).toFixed(1)},${y(soc).toFixed(1)}`).join(" ");
  g.push(svg("polygon", { points: `${x(0)},${y(0)} ${line} ${x(total)},${y(0)}`, class: "area" }), svg("polyline", { points: line, class: "trace" }));
  let n = 0;
  pts.forEach(([km, soc], i) => {
    const prev = pts[i - 1];
    if (prev && prev[0] === km && soc > prev[1]) {
      g.push(svg("circle", { cx: x(km), cy: y(soc), r: 9, class: "stopdot" }), svg("text", { x: x(km), y: y(soc) + 3.5, "text-anchor": "middle", class: "stopnum" }, String(++n)));
    }
  });
  g.push(svg("text", { x: L, y: H - 6, class: "tick" }, "0 km"), svg("text", { x: W - R, y: H - 6, class: "tick", "text-anchor": "end" }, `${Math.round(total)} km`));
  $("profile").replaceChildren(...g);
  $("profile-desc").textContent = `Battery from ${pct(pts[0][1])} to ${pct(pts.at(-1)[1])} over ${Math.round(total)} km, with ${n} charging ${n === 1 ? "stop" : "stops"}.`;
}

/* ---------- busy charger, speed comparison ---------- */
async function busy(k, button, out) {
  button.disabled = true;
  out.textContent = "Checking\u2026";
  try {
    const r = await fetch(`/api/jobs/${state.jobId}/busy/${k}`, { method: "POST" });
    if (!r.ok) throw new Error();
    const a = await r.json();
    out.textContent = a.extra_min == null
      ? "No other charger in reach: this stop is needed."
      : `${a.extra_min < 0.5 ? "No extra time" : `+${dur(a.extra_min)}`} by another charger${a.via?.filter(Boolean).length ? `, for example ${a.via.filter(Boolean)[0]}` : ""}.`;
  } catch {
    out.textContent = "Could not check. Plan the trip again.";
  }
  button.disabled = false;
}
async function planJob(body, id) {
  const r = await fetch("/api/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) return null;
  const { job_id } = await r.json();
  for (;;) {
    await new Promise((res) => setTimeout(res, 1000));
    if (id !== state.job) return null;
    const job = await (await fetch(`/api/jobs/${job_id}`)).json();
    if (job.status === "running") continue;
    return job.status === "done" ? job.result : null;
  }
}
async function compareSpeeds(id, v, base) {
  const rows = $("speed-rows");
  $("speeds").hidden = false;
  rows.replaceChildren(h("li", {}, "Planning at other speeds\u2026"));
  const here = v.speed ? +v.speed : null;
  const items = [];
  for (const speed of [110, 90].filter((s) => !here || s < here)) {
    const res = await planJob(requestBody(v, { max_speed_kph: speed, compare: false }), id).catch(() => null);
    if (id !== state.job) return;
    if (!res) { items.push(h("li", {}, `${speed} km/h: no route.`)); continue; }
    const dm = res.summary.total_min - base.summary.total_min, ds = res.stops.length - base.stops.length;
    const stops = ds === 0 ? "same stops" : `${Math.abs(ds)} stop${Math.abs(ds) === 1 ? "" : "s"} ${ds < 0 ? "fewer" : "more"}`;
    const time = Math.abs(dm) < 0.5 ? "same time" : `${dur(Math.abs(dm))} ${dm > 0 ? "slower" : "faster"}`;
    items.push(h("li", {}, h("strong", {}, `${speed} km/h`), `: ${stops}, ${time}`, h("span", { class: "unit" }, ` (${dur(res.summary.total_min)} in total)`)));
  }
  rows.replaceChildren(...(items.length ? items : [h("li", {}, "The trip already runs at or below these speeds.")]));
}

/* ---------- share and export ---------- */
function shareUrl() {
  const q = toQuery(values());
  return `${location.origin}${location.pathname}?${q}#plan`;
}
async function copyLink() {
  const url = shareUrl(), out = $("share-out");
  history.replaceState(null, "", url);
  out.hidden = false;
  try {
    await navigator.clipboard.writeText(url);
    out.textContent = "Link copied. Anyone who opens it gets this trip planned.";
  } catch {
    out.textContent = url; // clipboard blocked (plain http): the address bar already holds it
  }
}
function download(name, type, text) {
  const a = h("a", { href: URL.createObjectURL(new Blob([text], { type })), download: name });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const xml = (t) => t.replace(/[<>&"]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" })[c]);
function stopName(s, k) { return s.label ?? `Charging stop ${k + 1}`; }
function toGpx(res) {
  const wpt = [[res.route[0], res.start.label], ...res.stops.map((s, k) => [[s.lat, s.lon], stopName(s, k)]), [res.route.at(-1), res.goal.label]];
  return `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="EVOPT Maps" xmlns="http://www.topografix.com/GPX/1/1">\n`
    + wpt.map(([[la, lo], n]) => `<wpt lat="${la}" lon="${lo}"><name>${xml(n)}</name></wpt>\n`).join("")
    + `<trk><name>${xml(`${res.start.label} to ${res.goal.label}`)}</name><trkseg>\n${res.route.map(([la, lo]) => `<trkpt lat="${la}" lon="${lo}"/>`).join("\n")}\n</trkseg></trk>\n</gpx>\n`;
}
function toGeoJson(res) {
  const point = (lat, lon, properties) => ({ type: "Feature", geometry: { type: "Point", coordinates: [lon, lat] }, properties });
  return JSON.stringify({ type: "FeatureCollection", features: [
    { type: "Feature", geometry: { type: "LineString", coordinates: res.route.map(([la, lo]) => [lo, la]) }, properties: { name: `${res.start.label} to ${res.goal.label}`, ...res.summary } },
    point(...res.route[0], { name: res.start.label, role: "start" }),
    ...res.stops.map((s, k) => point(s.lat, s.lon, { name: stopName(s, k), role: "charging stop", minutes: +s.minutes.toFixed(1), kwh: +s.kwh.toFixed(1), power_kw: s.power_kw, charge_before: s.soc_before, charge_after: s.soc_after })),
    point(...res.route.at(-1), { name: res.goal.label, role: "goal" }),
  ] });
}

/* ---------- temperature now ---------- */
async function useCurrentTemperature() {
  const note = $("temp-note"), place = $("start").value.trim();
  note.hidden = false;
  if (place.length < 2) { note.textContent = "Enter a starting point first."; return; }
  note.textContent = "Asking Open-Meteo\u2026";
  try {
    const r = await fetch(`/api/temperature?place=${encodeURIComponent(place)}`);
    if (!r.ok) throw new Error();
    const { temp_c } = await r.json();
    const t = $("temp");
    t.value = Math.max(+t.min, Math.min(+t.max, temp_c));
    t.dispatchEvent(new Event("input", { bubbles: true }));
    note.textContent = `${String(temp_c).replace("-", "\u2212")}\u00a0\u00b0C now at ${place}.`;
  } catch {
    note.textContent = "Could not get the temperature. Set it with the slider.";
  }
}

/* ---------- start ---------- */
async function init() {
  initMap();
  try {
    state.vehicles = await (await fetch("/api/vehicles")).json();
  } catch {
    state.vehicles = [];
  }
  try {
    state.algorithms = await (await fetch("/api/algorithms")).json();
  } catch {
    state.algorithms = [];
  }
  $("algorithm").replaceChildren(...state.algorithms.map((a) => h("option", { value: a.id }, a.name)));
  $("algo-list").replaceChildren(...state.algorithms.flatMap((a) => [h("dt", {}, a.name), h("dd", {}, a.summary)]));
  $("vehicle").replaceChildren(...state.vehicles.map((v) => h("option", { value: v.name }, v.name)));
  if (!state.vehicles.length || !state.algorithms.length) {
    $("error-title").textContent = ERROR_TITLES.unreachable;
    $("error-text").textContent = "The vehicle and algorithm lists could not be loaded. Is the server running?";
    $("retry").hidden = true;
    $("submit").disabled = true;
    show("error");
  }
  try {
    Object.assign(EXAMPLE, (await (await fetch("/api/demo")).json()) ?? {}); // ready-made trip on the bundled extract
  } catch { /* keep the built-in example */ }
  const shared = fromQuery(new URLSearchParams(location.search));
  const saved = { ...EXAMPLE, ...load(), ...shared };
  if (!saved.vehicle) saved.vehicle = (state.vehicles.find((v) => v.name.includes("Renault Twizy")) ?? state.vehicles[0] ?? {}).name;
  fill(saved);
  sliders.forEach((s) => $(s.id).addEventListener("input", onSlider));
  for (const id of ["area", "start", "goal"]) $(id).addEventListener("input", () => { persist(); $(id).removeAttribute("aria-invalid"); $(`${id}-err`).hidden = true; });
  $("vehicle").addEventListener("change", () => { paintSpec(); persist(); });
  for (const id of ["algorithm", "legs", "compare", "elevation"]) $(id).addEventListener("change", () => { paintAlgorithmHelp(); persist(); });
  $("swap").addEventListener("click", () => { const a = $("start").value; $("start").value = $("goal").value; $("goal").value = a; persist(); });
  $("plan-form").addEventListener("submit", plan);
  $("cancel").addEventListener("click", cancel);
  $("retry").addEventListener("click", () => $("plan-form").requestSubmit());
  $("show-stations").addEventListener("change", toggleStations);
  for (const id of ["speed", "minkw", "known", "compare-speeds"]) $(id).addEventListener("change", persist);
  $("temp-auto").addEventListener("click", useCurrentTemperature);
  $("copy-link").addEventListener("click", copyLink);
  $("dl-gpx").addEventListener("click", () => state.result && download("evopt-trip.gpx", "application/gpx+xml", toGpx(state.result)));
  $("dl-geojson").addEventListener("click", () => state.result && download("evopt-trip.geojson", "application/geo+json", toGeoJson(state.result)));
  $("theme").addEventListener("click", () => {
    const dark = (document.documentElement.dataset.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
    document.documentElement.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("evopt-theme", document.documentElement.dataset.theme); } catch { /* storage unavailable */ }
  });
  window.addEventListener("hashchange", () => route(false));
  route(true);
  if (shared) $("plan-form").requestSubmit(); // a shared link plans its trip straight away
}
init();
