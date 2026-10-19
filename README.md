# EVOPT Maps

Plan the fastest route for an electric car, with charging stops only where the battery needs them.

![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)

![EVOPT Maps web interface showing a planned trip with one charging stop](example/web.png)

EVOPT Maps downloads real roads and real charging stations, estimates how much energy each road segment costs for a chosen vehicle and temperature, and searches for the trip that arrives fastest, charging as little as possible. The result is shown on a map and as a trip line where every charging stop prints its minutes, energy and the battery level before and after.

It started as a university project for the Intelligent Systems course and has been rewritten as a small, tested web app. The original A\* and desktop GUI version lives in the [`legacy`](../../tree/legacy) branch.

## Features

- Real road network from OpenStreetMap, kept directed so one-way streets are respected.
- Real charging stations with their operator and name, from OpenStreetMap, completed with power data from Open Charge Map when an API key is set. Fast-charger sockets (CCS, CHAdeMO) hint at 50 kW when no power is published.
- Physical energy model: rolling resistance, air drag, drivetrain efficiency, temperature-dependent climate load, and climbs and descents from terrain data.
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

**Real trip: Milano Duomo to Torino Porta Nuova** (47,068 nodes, 86,195 edges, 859 charger nodes). Renault Twingo Electric (22 kWh), 0 °C, from 90% to at least 10%. The best plan is one 33-minute stop and 113.8 minutes in total.

Road-level search between the two points:

| Algorithm | Trip (min) | States | ms |
| --- | --- | --- | --- |
| Dijkstra | 80.84 | 40,202 | 106 |
| A\*, straight line | 80.84 | 17,580 | 121 |
| A\* + ALT (8 landmarks) | 80.84 | 4,824 | 33 |
| Weighted A\* (w=2) | 95.92 (+18.7%) | 5,024 | 15 |
| ARA\*, first answer (w=3) | 95.92 (+18.7%) | 632 | |
| ARA\*, final | 80.84 | 18,013 | 56 |

ALT needs 1.9 s of preprocessing, once per graph.

Electric trip, with charging (legs already computed):

| Algorithm | Trip (min) | Stops | States | Search (ms) |
| --- | --- | --- | --- | --- |
| Dijkstra | 113.84 | 1 | 41,750 | 24,286 (also builds the missing legs) |
| A\*, straight line | 113.84 | 1 | 28,253 | 3,271 |
| A\*, energy-aware | 113.84 | 1 | 24,793 | 3,168 |
| **A\*, exact potentials** | 113.84 | 1 | **8,486** | **993** |
| Weighted A\* (w=1.5) | 124.15 (+9.1%) | 4 | 1,309 | 361 |
| ARA\* | 113.84 | 1 | 27,542 | 3,740 |
| Naive driver | 147.65 (+29.7%) | 1 | 2 | 107 |

Weighted A\* trades quality for effort in a steep way on this trip:

| Weight | Trip | States | vs optimal states |
| --- | --- | --- | --- |
| 1.05 | +0.0% | 7,781 | 92% |
| 1.1 | +3.3% | 7,104 | 84% |
| 1.25 | +3.2% | 4,778 | 56% |
| 1.5 | +9.1% | 1,309 | 15% |
| 2.0 | +16.2% | 109 | 1% |

ARA\* anytime profile: weight 3 gives +32% after 60 states, weight 2 gives +13.6% after 100, weight 1.5 gives +10.2% after 2,033 states (7% of its final effort), then the optimum after 27,542.

**Synthetic grid, 60x60** (3,600 nodes, 80 stations, three stops): Dijkstra 9,521 states, A\* 9,279, A\* with exact potentials 6,954; naive driver 1.6% slower; exact reference 596,823 states in 2.8 s against 47 ms for the reduced graph, within 0.1% of its result.

What the numbers say:

- **On real roads the heuristic matters a lot.** At road level ALT expands 8 times fewer states than Dijkstra and 3.6 times fewer than straight-line A\*, because real roads are far from straight. On the electric problem the exact backward potentials expand 80% fewer states than Dijkstra and 70% fewer than A\*, and search 3.3 times faster. On a small synthetic grid the same gain is only 27%: it grows with the size of the problem.
- **The energy-aware heuristic with a per-metre bound is barely better than plain A\*** (24,793 against 28,253 states). The potentials, which use the true minimum energy to the goal, are what pays.
- **Most of the cost is the legs between chargers**, not the search: each is a road search of about 35 ms in Python. Computing them lazily, reusing them and saving them to disk is the biggest saving: the first plan on the corridor takes about 25 s including geocoding; after a restart it takes about 9 s (the 22 MB table is read from disk), and 3 s while the server stays up. A strong heuristic also wins because it reaches fewer stations.
- **ARA\* is useful as a progress bar, not as a shortcut here.** Its answers improve steadily and each carries a proven bound, but to land within about 10% it needs 7% of the final effort, and the final optimum costs as much as plain A\*.
- **Free stops mislead.** With no plug-in time a greedy search stops at every charger (10 stops where 4 were optimal); with a realistic plug-in time the same search behaves.
- **The naive driver loses 30% on the real trip**, charging to 80% at the charger nearest the destination each time. On the easier grid it loses under 2%.
- **The reduced graph agrees with the exact reference** within 0.1%.
- **Pareto legs cost 7 to 8 times more** to build and gave the same trip on the grids.

### Elevation

Node elevations come from terrain tiles on AWS Open Data (Terrarium, about 30 m, no key or login), sampled with bilinear interpolation, cached under `cache/dem/` and lightly smoothed along the road network. Turn it off per trip under **Advanced** to see how much it matters. `Planner(elevation=False)` does the same in code.

Measured on the real corridors, with the Tesla Model 3 (54 kWh) so a leg fits the battery:

| Trip | Net climb | Energy, flat | Energy, with elevation | Difference |
| --- | --- | --- | --- | --- |
| Milano to Torino, 145 km | +120 m | 27.62 kWh | 28.73 kWh | +1.11 kWh |
| Torino to Milano | −120 m | 27.14 kWh | 27.34 kWh | +0.20 kWh |
| Torino to Courmayeur, 149 km | +967 m | 25.10 kWh | 30.80 kWh | **+23%** |
| Courmayeur to Torino | −967 m | 25.13 kWh | 24.43 kWh | −3% |

With the Twingo (22 kWh, 0 °C, 3 minutes per stop), Torino to Courmayeur goes from 113.6 to 123.2 minutes, the stop growing from 24 to 34 minutes. The same trip in the web app, with Courmayeur geocoded at 1,677 m, goes from 2 h 00 to 2 h 11.

What to trust, and what not:

- **Climbs are close to physics:** the Torino to Courmayeur climb costs 5.7 kWh against about 5.3 kWh of potential energy over efficiency.
- **Descents are prudent:** the model gives back 60% and never below zero, so Courmayeur to Torino saves 0.7 kWh where the physics suggests 1.5 to 2.7.
- **Elevation noise is real.** On the flat Milano to Torino corridor, raw terrain data added about +0.9 kWh of spurious energy in both directions (bridges and viaducts read as dips, so climbs are paid in full and descents only partly refunded). Smoothing the elevations along the network brings it to about +0.5 kWh, roughly 2%, part of which is real rolling terrain. On the Torino to Courmayeur path the gross ascent is 442 m and the gross descent 1,409 m for a net −967 m, which is why the app shows the net climb and the highest point, not the gross figures.
- Segments steeper than a 12% average are capped, to protect against data glitches (39 of 446 segments on that path).

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
- Vehicle parameters are approximate values from public data sheets.
- With the default `fastest` legs the energy of a leg is that of the fastest road, not the most efficient one (`pareto` removes this).
- The efficient-frontier and exact searches are slow on big areas; the comparison skips the exact reference above 2,500 nodes.

## Credits

Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. Station data from [Open Charge Map](https://openchargemap.org). Elevation from terrain tiles on [AWS Open Data](https://registry.opendata.aws/terrain-tiles/) (Mapzen, SRTM and other sources). Maps drawn with [Leaflet](https://leafletjs.com).

By Filippo Camossi and Daniele Cioli. The original course presentation is in [`example/`](example/).
