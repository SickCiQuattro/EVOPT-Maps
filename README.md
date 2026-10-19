# EVOPT Maps

Plan the fastest route for an electric car, with charging stops only where the battery needs them.

![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)

![EVOPT Maps web interface showing a planned trip with one charging stop](example/web.png)

EVOPT Maps downloads real roads and real charging stations, estimates how much energy each road segment costs for a chosen vehicle and temperature, and searches for the trip that arrives fastest, charging as little as possible. The result is shown on a map and as a trip line where every charging stop prints its minutes, energy and the battery level before and after.

It started as a university project for the Intelligent Systems course and has been rewritten as a small, tested web app. The original A\* and desktop GUI version lives in the [`legacy`](../../tree/legacy) branch.

## Features

- Real road network from OpenStreetMap, kept directed so one-way streets are respected.
- Real charging stations with their operator and name, from OpenStreetMap, completed with power data from Open Charge Map when an API key is set. Fast-charger sockets (CCS, CHAdeMO) hint at 50 kW when no power is published.
- Physical energy model, calibrated on public consumption figures for four vehicles: rolling resistance, air drag, drivetrain efficiency, a cold penalty per kilometre, urban stop-and-go, and climbs and descents from terrain data.
- Charging that slows down above 80% on fast chargers, and a fixed 3 minutes per stop for plugging in (in the web app), so the plan avoids pointless one-minute stops.
- Time-optimal planning over battery state, with eight algorithms you can switch and compare.
- Web interface with live progress, clear errors, a vehicle roster and a comparison page.
- Expiring disk cache for the road graph (30 days) and stations (7 days), and a saved table of the legs between chargers, so a trip is planned from disk after the first time.
- Realistic tests on a local OpenStreetMap extract: no dependence on the public Overpass server.

## Getting started

You need [uv](https://docs.astral.sh/uv/) and Python 3.13 or newer.

```bash
git clone https://github.com/PasticciniTeams/EVOPT-Maps.git
cd EVOPT-Maps
uv sync
uv run uvicorn evopt.api:app
```

Open <http://127.0.0.1:8000>. The form is pre-filled with a small example that needs a charging stop; for a real 145 km trip see [Realistic test](#realistic-test).

> [!NOTE]
> The first plan for a new area downloads its roads and takes from a few seconds to a few minutes. After that it is instant. The public Overpass server can refuse large areas: use a city, not a region.

### Open Charge Map (optional)

Open Charge Map fills in the power of stations that OpenStreetMap does not describe. Get a free key from [openchargemap.org](https://openchargemap.org) (My Profile, My Apps) and put it in a `.env` file:

```bash
echo 'OCM_API_KEY=your_key' > .env
uv run --env-file .env uvicorn evopt.api:app
```

Without a key only OpenStreetMap is used, and stations with unknown power are assumed to be 22 kW. On a local extract the key also adds stations in tiles of 25 km along the whole area.

## Use it as a library

```python
from evopt.data import load_network
from evopt.graph import nearest_node
from evopt.planner import Planner
from evopt.vehicle import VEHICLES

G = load_network("Pieve Emanuele, Italy")  # roads + charging stations
start = nearest_node(G, 45.35, 9.17)
goal = nearest_node(G, 45.33, 9.15)

planner = Planner(G, VEHICLES["Renault Twizy"], temp_c=-10)  # reuse it: station legs are computed once
route = planner.plan(start, goal, start_soc=0.15, min_soc=0.10, algorithm="astar")
print(route.time_s / 60, "min,", len(route.charges), "charging stop(s),", route.stats["expanded"], "states")
```

## How it works

1. **Energy per segment.** For each road segment the model adds rolling resistance and air drag at the segment speed, divided by drivetrain efficiency, plus the power of heating or cooling over the time spent on it:

   ```text
   energy = (Crr·m·g + ½·ρ·CdA·v²) · distance / efficiency + m·g·rise / efficiency + aux(temperature) · time
   ```

   On a descent the last gravity term is replaced by a recovery of 60%, and the energy of a segment never goes below its auxiliary load: a descent saves energy but never charges the battery.

2. **Reduced graph.** Dijkstra on travel time from the start and towards the goal keeps only the legs the battery can cover. The legs between stations are computed lazily, only for stations the search actually reaches, then reused by every later plan and saved on disk in `cache/` (they keep only time, energy and metres; the road path is rebuilt for the legs of the chosen trip). This leaves a small graph of start, goal and stations.
3. **Search over battery state.** A state is `(node, charge level, charging)` with the charge in 1% steps. Driving spends levels; charging adds one level at a power that depends on the charge (it tapers above 80% on fast chargers); starting to charge costs a fixed plug-in time once per stop; and the trip never goes below the chosen arrival charge. The goal is any state at the destination.

Plain shortest-path search is not enough here: battery is a constrained resource, so the best route depends on where you charge and how much. That is why the search runs over `(node, charge)` and not over nodes.

## Algorithms

The same problem is solved by several algorithms, selectable under **Advanced** in the web app. Tick **Compare all algorithms** to run all of them on your trip and see the differences on the **Algorithms** page.

| Algorithm | Guarantee | Idea |
| --- | --- | --- |
| Dijkstra | optimal | expands states by cost only |
| A\* | optimal | adds the straight-line travel time to the goal as a heuristic |
| A\*, energy-aware | optimal | heuristic also counts a lower bound on the charging time still needed |
| A\*, exact potentials | optimal | heuristic from two backward searches: true minimum drive time and minimum energy to the goal |
| Weighted A\* (w=1.5) | at most 1.5x optimal | inflates the heuristic: fewer states, often a slower trip |
| ARA\* | anytime, ends optimal | answers fast with a large weight, then improves it reusing earlier work, with a proven bound at each step |
| Naive driver | none | goes to the charger nearest the destination and charges to 80% each time |
| Exact reference | optimal at 1% charge steps | label search on the full road network, no reduced graph |

The road-level search (Dijkstra, A\*, Weighted A\*, ARA\* between two nodes) is in `evopt/search.py`. Its default heuristic is straight-line distance over the best straight-line speed of any road, admissible and consistent by construction; optional ALT landmarks tighten it. The state search also prunes dominated states, a state being useless if another at the same place has more charge and no higher cost.

The exact reference and the other algorithms are tested against each other: every optimal algorithm returns the same trip, Weighted A\* never exceeds its bound, ARA\* improves monotonically and ends optimal.

Legs between chargers can use the single fastest road (default) or **Pareto labels** (time, energy), which keep slower but more efficient roads that the fastest-road shortcut would miss.

### Measured results

Regenerate with `uv run python -m benchmarks.compare` (synthetic grids) and `uv run --env-file .env python -m benchmarks.compare --local milano-torino` (real roads, see [Realistic test](#realistic-test)). One laptop core, pure Python, 3 minutes of plug-in time per stop.

**Real trip: Milano Duomo to Torino Porta Nuova** (47,068 nodes, 86,195 edges, 859 charger nodes). Renault Twingo Electric (21.3 kWh usable), 0 °C, from 90% to at least 10%, planned at the speed limit (130 km/h on the motorway). The best plan takes two stops and 142.6 minutes.

Road-level search between the two points:

| Algorithm | Trip (min) | States | ms |
| --- | --- | --- | --- |
| Dijkstra | 80.84 | 40,202 | 105 |
| A\*, straight line | 80.84 | 17,580 | 120 |
| A\* + ALT (8 landmarks) | 80.84 | 4,824 | 32 |
| Weighted A\* (w=2) | 95.92 (+18.7%) | 5,024 | 15 |
| ARA\*, first answer (w=3) | 95.92 (+18.7%) | 632 | |
| ARA\*, final | 80.84 | 18,013 | 56 |

ALT needs 1.9 s of preprocessing, once per graph.

Electric trip, with charging (legs already computed):

| Algorithm | Trip (min) | Stops | States | Search (ms) |
| --- | --- | --- | --- | --- |
| Dijkstra | 142.61 | 2 | 48,638 | 17,034 (also builds the missing legs) |
| A\*, straight line | 142.61 | 2 | 41,790 | 4,090 |
| A\*, energy-aware | 142.61 | 2 | 41,265 | 3,944 |
| **A\*, exact potentials** | 142.61 | 2 | **16,040** | **1,769** |
| Weighted A\* (w=1.5) | 153.13 (+7.4%) | 4 | 4,700 | 703 |
| ARA\* | 142.61 | 2 | 52,816 | 6,076 |
| Naive driver | 195.34 (+37.0%) | 2 | 3 | 120 |

The naive driver heads for the reachable charger nearest the destination, ignoring chargers slower than half the vehicle's maximum charge power when a faster one is reachable, and charges to 80% (more if that is not enough to arrive). Without the power rule it picked a slow charger and lost 239%, which says more about the rule than about the planner, so it was added.

Weighted A\* trades quality for effort in a steep way on this trip:

| Weight | Trip | States | vs optimal states |
| --- | --- | --- | --- |
| 1.05 | +0.0% | 15,850 | 99% |
| 1.1 | +0.0% | 13,990 | 87% |
| 1.25 | +5.2% | 9,345 | 58% |
| 1.5 | +7.4% | 4,700 | 29% |
| 2.0 | +24.9% | 650 | 4% |

ARA\* anytime profile: weight 3 gives +24.7% after 115 states, weight 2 gives +14.8% after 154, weight 1.5 gives +11.1% after 7,914 states (15% of its final effort), then the optimum after 52,816.

**Synthetic grid, 60x60** (3,600 nodes, 80 stations, three stops): Dijkstra 9,521 states, A\* 9,279, A\* with exact potentials 6,954; naive driver 1.6% slower; exact reference 596,823 states in 2.8 s against 47 ms for the reduced graph, within 0.1% of its result.

What the numbers say:

- **On real roads the heuristic matters a lot.** At road level ALT expands 8 times fewer states than Dijkstra and 3.6 times fewer than straight-line A\*, because real roads are far from straight. On the electric problem the exact backward potentials expand 67% fewer states than Dijkstra and 62% fewer than A\*, and search 2.3 times faster than A\*. On a small synthetic grid the same gain is only 27%: it grows with the size of the problem.
- **The energy-aware heuristic with a per-metre bound is barely better than plain A\*** (41,265 against 41,790 states). The potentials, which use the true minimum energy to the goal, are what pays.
- **Most of the cost is the legs between chargers**, not the search: each is a road search of about 35 ms in Python. Computing them lazily, reusing them and saving them to disk is the biggest saving. The first plan on this corridor takes about 28 s including geocoding; after a restart about 9 s (the table is read from disk) and 4.5 s while the server stays up. A strong heuristic also wins because it reaches fewer stations.
- **ARA\* is useful as a progress bar, not as a shortcut here.** Its answers improve steadily and each carries a proven bound, but to land within about 11% it needs 15% of the final effort, and the final optimum costs more than plain A\*.
- **Free stops mislead.** With no plug-in time a greedy search stops at every charger (10 stops where 4 were optimal); with a realistic plug-in time the same search behaves.
- **The naive driver loses 37% on the real trip.** On the easier grid it loses under 2%.
- **The reduced graph agrees with the exact reference** within 0.1%.
- **Pareto legs cost 7 to 8 times more** to build and gave the same trip on the grids.

### Elevation

Node elevations come from terrain tiles on AWS Open Data (Terrarium, about 30 m, no key or login), sampled with bilinear interpolation, cached under `cache/dem/` and lightly smoothed along the road network. Turn it off per trip under **Advanced** to see how much it matters. `Planner(elevation=False)` does the same in code.

Measured on the real corridors, with the Tesla Model 3 (49 kWh usable) so a leg fits the battery:

| Trip | Net climb | Energy, flat | Energy, with elevation | Difference |
| --- | --- | --- | --- | --- |
| Milano to Torino, 145 km | +120 m | 32.23 kWh | 33.25 kWh | +1.01 kWh |
| Torino to Milano | −120 m | 31.62 kWh | 31.77 kWh | +0.14 kWh |
| Torino to Courmayeur, 149 km | +967 m | 28.97 kWh | 34.25 kWh | **+18%** |
| Courmayeur to Torino | −967 m | 29.02 kWh | 28.16 kWh | −3% |

With the Twingo (21.3 kWh usable, 0 °C, 3 minutes per stop), Torino to Courmayeur goes from 134.4 to 147.3 minutes and from one stop to two. The same trip in the web app, with Courmayeur geocoded at 1,677 m, goes from 2 h 20 to 2 h 35.

What to trust, and what not:

- **Climbs are close to physics:** the Torino to Courmayeur climb costs 5.3 kWh against about 4.9 kWh of potential energy over efficiency.
- **Descents are prudent:** the model gives back 60% and never below zero, so Courmayeur to Torino saves 0.9 kWh where the physics suggests 1.5 to 2.7.
- **Elevation noise is real.** On the flat Milano to Torino corridor, raw terrain data added about +0.9 kWh of spurious energy in both directions (bridges and viaducts read as dips, so climbs are paid in full and descents only partly refunded). Smoothing the elevations along the network brings it to about +0.5 kWh, roughly 2%, part of which is real rolling terrain. On the Torino to Courmayeur path the gross ascent is 442 m and the gross descent 1,409 m for a net −967 m, which is why the app shows the net climb and the highest point, not the gross figures.
- Segments steeper than a 12% average are capped, to protect against data glitches (39 of 446 segments on that path).

### Calibration

Vehicle consumption is calibrated on public figures from [EV Database](https://ev-database.org) for four of the five vehicles (the Twizy has no comparable data and keeps approximate values, marked as such in the app). The reference gives usable battery, kerb mass and consumption in town, on the motorway at a constant 110 km/h, and combined, in mild weather (23 °C) and in the cold (−10 °C, heating on). These are estimates built from tests and the WLTP cycle, not instrumented measurements of this project.

Three parameters per vehicle are fitted, with rolling resistance (0.010) and drivetrain efficiency (0.90) fixed:

1. the effective drag area, on the motorway consumption in mild weather;
2. the cold penalty per kilometre, on the difference between cold and mild on the motorway;
3. the stop-and-go overhead below 70 km/h, on the urban consumption in mild weather.

The cold penalty is modelled per kilometre, not per hour, because the reference shows almost the same cold surcharge in town (54 to 57 Wh/km) and on the motorway (50 to 59 Wh/km), which constant heating power would not.

Before and after, range at 110 km/h against the reference (`uv run python -m benchmarks.calibrate` prints every point):

| Vehicle | Mild, before | Cold, before | Mild and cold, after | Urban cold, held out |
| --- | --- | --- | --- | --- |
| Tesla Model 3 SR+ | +18% | +32% | 0% | −4% |
| Renault Twingo Electric | +20% | +37% | 0% | +3% |
| Fiat 500e | +21% | +36% | 0% | −3% |
| MINI Electric | +19% | +37% | 0% | 0% |

The earlier model was too optimistic: it overstated range at 110 km/h by 18 to 37%. The last column is a point the fit never used (urban consumption in the cold), predicted within 4%. The calibration also changed the plans: Milano to Torino with the Twingo went from one stop and 113.8 minutes to two stops and 142.6 minutes.

Limits: the fit leans on one source and on a modelled "constant 110 km/h"; hot-weather consumption (above 24 °C) is not calibrated; the urban term is fitted at one point (50 km/h); the plans run at the speed limit, so on a motorway at 130 km/h consumption is about a third above the 110 km/h reference.

## Realistic test

Big areas fail on the public Overpass server, so the real trip above uses a local OpenStreetMap extract.

```bash
mkdir -p data
curl -L -o data/nord-ovest.osm.pbf https://download.geofabrik.de/europe/italy/nord-ovest-latest.osm.pbf   # 593 MB
uv run --group extract python -m benchmarks.extract data/nord-ovest.osm.pbf --bbox 7.4 44.9 9.5 45.7 --name milano-torino
uv run python -m benchmarks.compare --local milano-torino

# a mountain trip: Torino to Courmayeur, about 1,000 m of climb
uv run --group extract python -m benchmarks.extract data/nord-ovest.osm.pbf --bbox 6.8 44.95 7.9 45.9 --name torino-courmayeur
```

The extraction keeps motorways, trunk, primary and secondary roads, contracts nodes that are not junctions, and reads charging stations (with name, operator and power) from the same file. Select it in the web app with the area name `local:milano-torino`. With `OCM_API_KEY` set, Open Charge Map completes the stations in 25 km tiles (859 charger nodes instead of 506 on this corridor). The `data/` folder is not tracked by git.

## Project structure

| Path | Purpose |
| --- | --- |
| `evopt/vehicle.py` | Vehicle data and the energy model |
| `evopt/graph.py` | Road graph loading, nearest node, route geometry |
| `evopt/elevation.py` | Terrain tiles, bilinear sampling, smoothing, node elevations |
| `evopt/stations.py` | Stations from OpenStreetMap and Open Charge Map, merging, snapping to the graph |
| `evopt/search.py` | Dijkstra, A*, Weighted A*, ARA* on a generic implicit graph |
| `evopt/planner.py` | The `Planner`: energy legs, state graph, all algorithms, naive and exact baselines |
| `evopt/router.py` | `Route`, `NoRouteError` and the one-call `plan_route` |
| `benchmarks/compare.py`, `benchmarks/extract.py` | Algorithm comparison; extraction of roads and stations from a local OSM file |
| `evopt/cache.py`, `evopt/data.py` | Expiring disk cache and one-call network loading |
| `evopt/api.py` | FastAPI app: planning jobs, vehicles, static frontend |
| `web/` | Static frontend (HTML, CSS, JS, Leaflet), no build step |
| `tests/` | pytest suite |
| `PRODUCT.md`, `DESIGN.md` | Product context and design system of the web interface |

The API is small: `GET /api/vehicles`, `GET /api/algorithms`, `POST /api/plan` (returns a job id; accepts `algorithm`, `legs`, `compare`) and `GET /api/jobs/{id}` (status, stage, result or error).

## Development

```bash
uv run pytest        # tests
uv run ruff check .  # lint
uv run ruff format . # format
```

The tests replace only the network boundaries (Overpass, Open Charge Map, geocoding), so the routing, cache and API logic run for real.

## Limitations

> [!IMPORTANT]
> This is an estimate, not a navigation system.

- No traffic or road works.
- Elevation is approximate: 30 m terrain data, smoothed, with prudent energy recovery on descents (see [Elevation](#elevation)).
- No live charger availability, and no access rules: a car may be sent to a charger its network does not allow.
- Charging power tapers with a simple curve (above 80% on fast chargers, constant on AC); real curves depend on temperature and battery state.
- Station power is often missing in OpenStreetMap (217 of 1,400 on the corridor): it is estimated from the sockets, completed from Open Charge Map when a key is set, and otherwise assumed to be 22 kW.
- Vehicle parameters are calibrated on EV Database estimates for four of five vehicles (see [Calibration](#calibration)); the Twizy is approximate.
- With the default `fastest` legs the energy of a leg is that of the fastest road, not the most efficient one (`pareto` removes this).
- The efficient-frontier and exact searches are slow on big areas; the comparison skips the exact reference above 2,500 nodes.

## Credits

Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. Station data from [Open Charge Map](https://openchargemap.org). Elevation from terrain tiles on [AWS Open Data](https://registry.opendata.aws/terrain-tiles/) (Mapzen, SRTM and other sources). Maps drawn with [Leaflet](https://leafletjs.com).

By Filippo Camossi and Daniele Cioli. The original course presentation is in [`example/`](example/).
