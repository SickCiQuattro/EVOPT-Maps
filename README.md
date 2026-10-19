# EVOPT Maps

Plan the fastest route for an electric car, with charging stops only where the battery needs them.

![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)

![EVOPT Maps web interface showing a planned trip with one charging stop](example/web.png)

EVOPT Maps downloads real roads and real charging stations, estimates how much energy each road segment costs for a chosen vehicle and temperature, and searches for the trip that arrives fastest, charging as little as possible. The result is shown on a map and as a trip line where every charging stop prints its minutes, energy and the battery level before and after.

It started as a university project for the Intelligent Systems course and has been rewritten as a small, tested web app. The original A\* and desktop GUI version lives in the [`legacy`](../../tree/legacy) branch.

## Features

- Real road network from OpenStreetMap, kept directed so one-way streets are respected.
- Real charging stations from OpenStreetMap, completed with power data from Open Charge Map when an API key is set.
- Physical energy model: rolling resistance, air drag, drivetrain efficiency and temperature-dependent climate load.
- Time-optimal planning over battery state, so charging stops appear only when and where they pay off.
- Web interface with live progress, clear errors, a vehicle roster and an explanation of the model.
- Expiring disk cache, so a city is downloaded once (roads for 30 days, stations for 7).

## Getting started

You need [uv](https://docs.astral.sh/uv/) and Python 3.13 or newer.

```bash
git clone https://github.com/PasticciniTeams/EVOPT-Maps.git
cd EVOPT-Maps
uv sync
uv run uvicorn evopt.api:app
```

Open <http://127.0.0.1:8000>. The form is pre-filled with a small example that needs a charging stop.

> [!NOTE]
> The first plan for a new area downloads its roads and takes from a few seconds to a few minutes. After that it is instant. The public Overpass server can refuse large areas: use a city, not a region.

### Open Charge Map (optional)

Open Charge Map fills in the power of stations that OpenStreetMap does not describe. Get a free key from [openchargemap.org](https://openchargemap.org) (My Profile, My Apps) and put it in a `.env` file:

```bash
echo 'OCM_API_KEY=your_key' > .env
uv run --env-file .env uvicorn evopt.api:app
```

Without a key only OpenStreetMap is used, and stations with unknown power are assumed to be 22 kW.

## Use it as a library

```python
from evopt.data import load_network
from evopt.graph import nearest_node
from evopt.router import plan_route
from evopt.vehicle import VEHICLES

G = load_network("Pieve Emanuele, Italy")  # roads + charging stations
start = nearest_node(G, 45.35, 9.17)
goal = nearest_node(G, 45.33, 9.15)

route = plan_route(G, start, goal, VEHICLES["Renault Twizy"], temp_c=-10, start_soc=0.15, min_soc=0.10)
print(route.time_s / 60, "min,", len(route.charges), "charging stop(s)")
```

## How it works

1. **Energy per segment.** For each road segment the model adds rolling resistance and air drag at the segment speed, divided by drivetrain efficiency, plus the power of heating or cooling over the time spent on it:

   ```text
   energy = (Crr·m·g + ½·ρ·CdA·v²) · distance / efficiency + aux(temperature) · time
   ```

2. **Reduced graph.** The planner runs Dijkstra on travel time from the start and from every station, keeping only legs the battery can cover. This gives a small graph of start, goal and stations.
3. **Search over battery state.** A second Dijkstra runs over `(node, charge level)` with the charge discretised to 1%. Driving spends charge, charging at a station adds it at the lower of the vehicle's and the station's power, and the trip must never go below the chosen arrival charge.

## Project structure

| Path | Purpose |
| --- | --- |
| `evopt/vehicle.py` | Vehicle data and the energy model |
| `evopt/graph.py` | Road graph loading, nearest node, route geometry |
| `evopt/stations.py` | Stations from OpenStreetMap and Open Charge Map, merging, snapping to the graph |
| `evopt/router.py` | Route planning with charging stops |
| `evopt/cache.py`, `evopt/data.py` | Expiring disk cache and one-call network loading |
| `evopt/api.py` | FastAPI app: planning jobs, vehicles, static frontend |
| `web/` | Static frontend (HTML, CSS, JS, Leaflet), no build step |
| `tests/` | pytest suite |
| `PRODUCT.md`, `DESIGN.md` | Product context and design system of the web interface |

The API is small: `GET /api/vehicles`, `POST /api/plan` (returns a job id) and `GET /api/jobs/{id}` (status, stage, result or error).

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

- No traffic, road works, elevation or braking energy recovery.
- No live charger availability.
- Charging is modelled at constant power, so long stops are slightly optimistic.
- Vehicle parameters are approximate values from public data sheets.
- The energy of a leg is computed along the fastest path, not the most efficient one.

## Credits

Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. Station data from [Open Charge Map](https://openchargemap.org). Maps drawn with [Leaflet](https://leafletjs.com).

By Filippo Camossi and Daniele Cioli. The original course presentation is in [`example/`](example/).
