# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
Backend: FastAPI (Python), already decided. Frontend: plain static HTML/CSS/JS with Leaflet, no build step, served by the backend. Chosen by the user among static, React+Vite and "delegated".

## Users
Portfolio audience: recruiters, lecturers and peers who open the project from a repository link and judge it in a couple of minutes. They are not EV experts. Secondary user is the author, who uses it to try real trips. The interface language is English only.

## Product Purpose
EVOPT Maps plans the fastest route for an electric vehicle, adding charging stops only where the battery requires them. It started as a university project (Intelligent Systems course) and is being revived as a working, polished demo. Success: a visitor enters a start, a destination and a car, and within seconds sees a credible route with charging stops and understands why each stop is there.

## Positioning
Unlike general maps apps that hide their reasoning, EVOPT Maps exposes the model: a physical energy estimate per road segment (speed, rolling and aerodynamic resistance, temperature-dependent cabin load) and a time-optimal search over battery state, using real OpenStreetMap roads and real charging stations.

## Operating Context
Local web app: FastAPI serves a JSON API and the static frontend. Road graph and stations are downloaded on demand from OpenStreetMap (Overpass) and Open Charge Map, then cached on disk (graph 30 days, stations 7 days). First load of a new city can take minutes, later loads are instant. Python package `evopt/` holds the routing core; the legacy desktop GUI lives in the `legacy` branch.

## Capabilities and Constraints
- Inputs: place (city), start, destination, vehicle (five built-in models), ambient temperature, start charge, minimum arrival charge.
- Output: route geometry, total time, distance, list of charging stops (station, kWh added, minutes), arrival charge.
- Known limits: speed from OSM tags, no elevation, no traffic, linear charging at constant power, 22 kW assumed when a station's power is unknown. Large areas can be rejected by the public Overpass endpoint. No live availability of chargers.
- Open Charge Map key is read from `OCM_API_KEY`; without it only OSM stations are used.

## Brand Commitments
Name: EVOPT Maps. Authors: Camossi Filippo, Cioli Daniele. No logo or brand palette exists.

## Evidence on Hand
Screenshots of the old GUI and map in `example/`, and the course presentation PDF. No testimonials, benchmarks or usage numbers exist and none may be invented.

## Product Principles
1. Show the reasoning: every charging stop is explained, never just drawn.
2. Be honest about the model: state its limits next to the result.
3. Slow work is visible: city downloads can take minutes, so progress and cause must always be on screen.
4. The map is the product: controls support it and never cover the route.

## Accessibility & Inclusion
Keyboard operable controls and visible focus, sufficient contrast, status not conveyed by colour alone. Interface in English.
