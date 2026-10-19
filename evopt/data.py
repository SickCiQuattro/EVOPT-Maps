import math
import os
import warnings
from pathlib import Path

import numpy as np
import osmnx as ox

from evopt.cache import CACHE_DIR, cached, slug
from evopt.elevation import add_node_elevations
from evopt.graph import haversine_m, load_graph
from evopt.stations import apply_stations, fetch_ocm, fetch_osm, load_stations, merge, save_stations

DATA_DIR = Path("data")
GRAPH_TTL_DAYS = 30  # roads change slowly and the download is heavy
STATIONS_TTL_DAYS = 7  # chargers change more often


def load_network(place, cache_dir=CACHE_DIR, progress=None, data_dir=DATA_DIR):
    """Graph of `place` with stations (OSM, plus OCM when OCM_API_KEY is set) as 'charger_kw' on nodes."""
    progress = progress or (lambda stage: None)
    if place.startswith("local:"):
        return _load_local(place[len("local:") :], progress, Path(data_dir), Path(cache_dir))
    key = slug(place)
    progress("roads")
    G = cached(
        cache_dir / f"graph-{key}.graphml",
        GRAPH_TTL_DAYS,
        lambda: _with_elevation(load_graph(place), cache_dir),
        ox.load_graphml,
        ox.save_graphml,
    )
    ensure_elevation(G, cache_dir)  # no-op if the saved graph already has elevations
    progress("stations")
    # the cached graph holds no stations: they are applied on every load so they expire on their own
    stations = cached(
        cache_dir / f"stations-osm-{key}.json",
        STATIONS_TTL_DAYS,
        lambda: fetch_osm(place),
        load_stations,
        save_stations,
    )
    if os.environ.get("OCM_API_KEY"):
        progress("power")
        lat, lon, radius_km = _circle(G)
        try:
            ocm = cached(
                cache_dir / f"stations-ocm-{key}.json",
                STATIONS_TTL_DAYS,
                lambda: fetch_ocm(lat, lon, radius_km),
                load_stations,
                save_stations,
            )
            stations = merge(stations, ocm)
        except OSError as e:  # no network, or Open Charge Map unreachable
            warnings.warn(f"Open Charge Map unavailable ({e}): using OpenStreetMap only", stacklevel=2)
    apply_stations(G, stations)
    return G


def _circle(G):
    """Centre and radius (km) covering every node."""
    ys = np.array([d["y"] for _, d in G.nodes(data=True)])
    xs = np.array([d["x"] for _, d in G.nodes(data=True)])
    lat, lon = ys.mean(), xs.mean()
    return lat, lon, float(haversine_m(lat, lon, ys, xs).max()) / 1000 + 1


def _load_local(name, progress, data_dir, cache_dir):
    """Local extract made by `benchmarks.extract`; with OCM_API_KEY it is completed with Open Charge Map."""
    graph, stations = data_dir / f"{name}.graphml", data_dir / f"{name}-stations.json"
    if not graph.exists():
        raise FileNotFoundError(
            f"no local extract {name!r}: make it with `python -m benchmarks.extract` (see README)"
        )
    progress("roads")
    G = ox.load_graphml(graph)
    ensure_elevation(G, cache_dir)
    progress("stations")
    found = load_stations(stations) if stations.exists() else []
    if os.environ.get("OCM_API_KEY"):
        progress("power")
        try:
            ocm = cached(
                cache_dir / f"stations-ocm-local-{slug(name)}.json",
                STATIONS_TTL_DAYS,
                lambda: _ocm_tiles(G),
                load_stations,
                save_stations,
            )
            found = merge(found, ocm)
        except OSError as e:
            warnings.warn(f"Open Charge Map unavailable ({e}): using the extract only", stacklevel=3)
    apply_stations(G, found)
    return G


def _ocm_tiles(G, step_km=25.0):
    """Open Charge Map answers per circle with a result cap, so a long area is covered in tiles."""
    ys = [d["y"] for _, d in G.nodes(data=True)]
    xs = [d["x"] for _, d in G.nodes(data=True)]
    dlat = step_km / 111.0
    seen, out = set(), []
    lat = min(ys)
    while lat < max(ys) + dlat:
        dlon = step_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
        lon = min(xs)
        while lon < max(xs) + dlon:
            for s in fetch_ocm(lat, lon, step_km * 0.75):
                key = (round(s.lat, 5), round(s.lon, 5))
                if key not in seen:
                    seen.add(key)
                    out.append(s)
            lon += dlon
        lat += dlat
    return out


def _with_elevation(G, cache_dir):
    """Add elevations before the graph is cached; if tiles are missing, ensure_elevation retries on the next load."""
    try:
        add_node_elevations(G, cache_dir)
    except OSError:
        pass
    return G


def ensure_elevation(G, cache_dir):
    try:
        add_node_elevations(G, cache_dir)
    except OSError as e:
        warnings.warn(f"Elevation data not available ({e}): roads are treated as flat", stacklevel=3)
