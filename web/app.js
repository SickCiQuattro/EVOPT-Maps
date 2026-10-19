"use strict";

const $ = (id) => document.getElementById(id);
const STORE_KEY = "evopt:v1";
const EXAMPLE = { area: "Pieve Emanuele, Italy", start: "Pieve Emanuele", goal: "Siziano", vehicle: "", temp: -10, startSoc: 15, minSoc: 10, algorithm: "astar", legs: "fastest", compare: true };
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
    algorithm: $("algorithm").value, legs: $("legs").value, compare: $("compare").checked,
  };
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
  spec.append(`${v.capacity_kwh} kWh battery · charges at up to ${v.max_charge_kw} kW`);
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
      body: JSON.stringify({ area: v.area, start: v.start, goal: v.goal, vehicle: v.vehicle, temp_c: v.temp, start_soc: v.startSoc / 100, min_soc: v.minSoc / 100, algorithm: v.algorithm, legs: v.legs, compare: v.compare }),
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
    return job.status === "done" ? done(id, job.result) : fail(id, job.error);
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
  $("line").replaceChildren(...diagram(res, v));
  state.result = res;
  const algo = state.algorithms.find((a) => a.id === res.algorithm)?.name ?? res.algorithm;
  $("solved-by").textContent = `Solved with ${algo}: ${res.stats.expanded?.toLocaleString("en") ?? "?"} states, ${Math.max(1, Math.round(res.stats.search_ms ?? 0))}\u00a0ms.`;
  $("compare-link").hidden = !res.comparison;
  renderAlgorithms(res);
  drawMap(res);
  show("result");
  $("result-title").focus({ preventScroll: true });
}
function station(n, cls, name, note, i) {
  return h("li", {}, h("button", { type: "button", class: `st ${cls}`, "data-n": n, "data-i": i, onclick: () => activate(i, true), onfocus: () => activate(i, false) },
    h("span", { class: "st-name" }, name), h("span", { class: "st-note" }, ...note)));
}
function diagram(res, v) {
  const items = [station("", "end", res.start.label, ["Leave with ", strong(`${v.startSoc} %`)], 0)];
  res.stops.forEach((s, k) => items.push(station(k + 1, "stop", `Charging stop ${k + 1}`, [
    "Arrive ", strong(pct(s.soc_before)), " · charge ", strong(dur(s.minutes)), " to ", strong(pct(s.soc_after)),
    h("br"), `+${kwh(s.kwh)}\u00a0kWh at up to ${+s.power_kw.toFixed(1)}\u00a0kW`,
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
  map = L.map("map", { zoomControl: true }).setView([45.2, 9.1], 8);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "© <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors",
  }).addTo(map);
}
function drawMap(res) {
  for (const l of [layers.route, layers.stations]) l && l.remove();
  layers.stops = [];
  const line = res.route;
  const casing = L.polyline(line, { color: "#fff", weight: 11, opacity: 1, interactive: false });
  const red = L.polyline(line, { color: "#e30613", weight: 6, opacity: 1, lineJoin: "round", interactive: false });
  const pts = [[line[0], icon("end"), 0], ...res.stops.map((s, k) => [[s.lat, s.lon], icon("stop", k + 1, 32), k + 1]), [line[line.length - 1], icon("end"), res.stops.length + 1]];
  const markers = pts.map(([ll, ic, i]) => L.marker(ll, { icon: ic, keyboard: false }).on("click", () => activate(i, true)));
  layers.route = L.layerGroup([casing, red, ...markers]).addTo(map);
  layers.stops = markers;
  layers.stations = L.layerGroup(res.stations.map(([la, lo, kw]) => L.marker([la, lo], { icon: icon("station", "", 12), keyboard: false }).bindTooltip(`${Math.round(kw)} kW`)));
  $("station-count").textContent = `(${res.stations.length})`;
  toggleStations();
  map.fitBounds(red.getBounds(), { padding: [64, 64], animate: false });
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
  if (pan && layers.stops[i]) map.setView(layers.stops[i].getLatLng(), Math.max(map.getZoom(), 13), { animate: false });
}

/* ---------- algorithms ---------- */
const num = (v, d = 0) => v.toLocaleString("en", { minimumFractionDigits: d, maximumFractionDigits: d });
function insights(rows) {
  const by = (id) => rows.find((r) => r.algorithm === id);
  const out = [];
  const [d, a, w, r, g] = ["dijkstra", "astar_energy", "wastar", "ara", "greedy"].map(by);
  if (g?.time_min != null && g.gap_pct > 0.05) out.push(`The naive driver needs ${num(g.gap_pct, 1)}\u00a0% more time than the best plan.`);
  else if (g && g.time_min == null) out.push("The naive driver could not complete this trip.");
  if (d?.expanded && a?.expanded && a.expanded < d.expanded) out.push(`A* expands ${num((1 - a.expanded / d.expanded) * 100)}\u00a0% fewer states than Dijkstra and finds the same trip.`);
  if (w?.expanded && d?.expanded && w.expanded < d.expanded) out.push(`Weighted A* expands ${num(d.expanded / w.expanded, 1)}\u00d7 fewer states than Dijkstra and lands ${num(w.gap_pct, 1)}\u00a0% above the best trip.`);
  if (r?.anytime?.length > 1 && r.anytime[0].expanded < 0.9 * r.anytime.at(-1).expanded) {
    const first = r.anytime[0], last = r.anytime.at(-1);
    out.push(`ARA* had a first answer after ${num(first.expanded)} states, ${num(first.expanded / last.expanded * 100)}\u00a0% of the effort of its final proven-optimal one.`);
  }
  return out;
}
function renderAlgorithms(res) {
  const rows = res.comparison;
  $("compare-result").hidden = !rows;
  $("compare-empty").hidden = !!rows;
  if (!rows) return;
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
      h("dl", {}, h("dt", {}, "Battery"), h("dd", { class: "num" }, `${v.capacity_kwh} kWh`), h("dt", {}, "Fastest charging"), h("dd", { class: "num" }, `${v.max_charge_kw} kW`)),
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
  const saved = { ...EXAMPLE, ...load() };
  if (!saved.vehicle) saved.vehicle = (state.vehicles.find((v) => v.name.includes("Renault Twizy")) ?? state.vehicles[0] ?? {}).name;
  fill(saved);
  sliders.forEach((s) => $(s.id).addEventListener("input", onSlider));
  for (const id of ["area", "start", "goal"]) $(id).addEventListener("input", () => { persist(); $(id).removeAttribute("aria-invalid"); $(`${id}-err`).hidden = true; });
  $("vehicle").addEventListener("change", () => { paintSpec(); persist(); });
  for (const id of ["algorithm", "legs", "compare"]) $(id).addEventListener("change", () => { paintAlgorithmHelp(); persist(); });
  $("swap").addEventListener("click", () => { const a = $("start").value; $("start").value = $("goal").value; $("goal").value = a; persist(); });
  $("plan-form").addEventListener("submit", plan);
  $("cancel").addEventListener("click", cancel);
  $("retry").addEventListener("click", () => $("plan-form").requestSubmit());
  $("show-stations").addEventListener("change", toggleStations);
  window.addEventListener("hashchange", () => route(false));
  route(true);
}
init();
