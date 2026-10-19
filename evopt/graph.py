import numpy as np
import osmnx as ox

ox.settings.use_cache = False  # la cache con scadenza è in evopt.cache: quella di osmnx non invecchia mai


def load_graph(place):
    """Rete stradale guidabile con 'length', 'speed_kph' e 'travel_time' su ogni arco. Resta orientata."""
    G = ox.graph_from_place(place, network_type="drive")
    G = ox.routing.add_edge_speeds(G)
    return ox.routing.add_edge_travel_times(G)


def haversine_m(lat, lon, lats, lons):
    """Distanza in metri tra un punto e un array di punti (gradi)."""
    lat, lon, lats, lons = map(np.radians, (lat, lon, lats, lons))
    a = np.sin((lats - lat) / 2) ** 2 + np.cos(lat) * np.cos(lats) * np.sin((lons - lon) / 2) ** 2
    return 2 * 6371000 * np.arcsin(np.sqrt(a))


def nearest_nodes(G, points):
    """Per ogni (lat, lon) il nodo più vicino e la distanza in metri."""
    ids = np.fromiter(G.nodes, dtype=np.int64, count=len(G))
    ys = np.array([G.nodes[n]["y"] for n in ids])
    xs = np.array([G.nodes[n]["x"] for n in ids])
    found = []
    for lat, lon in points:
        d = haversine_m(lat, lon, ys, xs)
        i = int(np.argmin(d))
        found.append((int(ids[i]), float(d[i])))
    return found


def nearest_node(G, lat, lon):
    return nearest_nodes(G, [(lat, lon)])[0][0]
