---
version: 1
slug: "web-index-html"
primary_target: "web/index.html"
related_targets: []
---

# Surface brief: web/index.html (EVOPT Maps planner)

Mode: Operate. Visitor: portfolio audience (recruiters, lecturers, peers), non-experts, judging in minutes. Task: enter area, start, destination, vehicle, conditions; get a route with charging stops and understand each stop. English UI. Static HTML/CSS/JS + Leaflet; FastAPI serves it.

Views: Plan (default), Vehicles (roster of five cells, selecting returns to Plan), About the model (assumptions and limits).

Open decisions: none. Build path: code-led.

## Direction contract

THESIS: A route is a metro line and a charging stop is a station. The trip is read as a line diagram with the reasoning printed at each stop. Refuses the category default of a generic maps card list with a blue accent.

OWN-WORLD: Milan Metro signage / Noorda-Vignelli diagram. Paper white #fff, ink #111, one line red #e30613 used for the route, primary action and the active state only, map ground #efefec, hairlines #cfcfcf, 3px black rules between regions. One grotesque (Helvetica Neue / Arimo), tabular figures, no shadows, 0 radius, no gradients. All spacing on an 8px grid. State changes are instant two-frame 90ms steps, no easing.

STORY: The visitor understands in seconds that this plans EV trips; fills five fields; sees the red line on the map and the same line as a vertical station diagram; believes each stop because minutes, kWh and charge before and after are printed; does: change a slider and re-plan.

FIRST VIEWPORT: 1440x900. 56px white header with 3px black bottom rule: wordmark left, tabs Plan / Vehicles / About the model. Left rail 392px: City, From, To, Vehicle, three sliders with live tabular readouts, red Plan route button, then trip summary (drive, charging, distance) over a 3px black rule and the vertical red line diagram with stations as ringed circles. Map fills the rest with the same red line, black start and end dots, larger numbered ringed stops, small grey stations.

FORM: Chosen form: Noorda Line, assigned candidate, index 3 of my list; seed: none (unavailable). Raises: Crouwel (8px cell grid), Variable font specimen (live readouts on inputs), Acetate manual (90ms two-frame steps).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
