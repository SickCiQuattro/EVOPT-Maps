import os
import warnings

import numpy as np
import osmnx as ox

from evopt.cache import CACHE_DIR, cached, slug
from evopt.graph import haversine_m, load_graph
from evopt.stations import apply_stations, fetch_ocm, fetch_osm, load_stations, merge, save_stations

GRAPH_TTL_DAYS = 30  # le strade cambiano piano e il download pesa
STATIONS_TTL_DAYS = 7  # le colonnine cambiano più spesso


def load_network(place, cache_dir=CACHE_DIR):
    """Grafo di `place` con le stazioni (OSM, più OCM se c'è OCM_API_KEY) sui nodi 'charger_kw'."""
    key = slug(place)
    G = cached(
        cache_dir / f"graph-{key}.graphml",
        GRAPH_TTL_DAYS,
        lambda: load_graph(place),
        ox.load_graphml,
        ox.save_graphml,
    )
    # il grafo in cache non contiene stazioni: si applicano ogni volta, così scadono per conto loro
    stations = cached(
        cache_dir / f"stations-osm-{key}.json",
        STATIONS_TTL_DAYS,
        lambda: fetch_osm(place),
        load_stations,
        save_stations,
    )
    if os.environ.get("OCM_API_KEY"):
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
        except OSError as e:  # rete assente o Open Charge Map non raggiungibile
            warnings.warn(f"Open Charge Map non disponibile ({e}): uso solo OpenStreetMap", stacklevel=2)
    apply_stations(G, stations)
    return G


def _circle(G):
    """Centro e raggio (km) che coprono tutti i nodi."""
    ys = np.array([d["y"] for _, d in G.nodes(data=True)])
    xs = np.array([d["x"] for _, d in G.nodes(data=True)])
    lat, lon = ys.mean(), xs.mean()
    return lat, lon, float(haversine_m(lat, lon, ys, xs).max()) / 1000 + 1
