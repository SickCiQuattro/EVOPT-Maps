import numpy as np
import osmnx as ox


def load_graph(place):
    """Rete stradale guidabile con 'length', 'speed_kph' e 'travel_time' su ogni arco. Resta orientata."""
    G = ox.graph_from_place(place, network_type="drive")
    G = ox.routing.add_edge_speeds(G)
    return ox.routing.add_edge_travel_times(G)


def nearest_node(G, lat, lon):
    ids = np.fromiter(G.nodes, dtype=np.int64, count=len(G))
    ys = np.radians([G.nodes[n]["y"] for n in ids])
    xs = np.radians([G.nodes[n]["x"] for n in ids])
    lat, lon = np.radians(lat), np.radians(lon)
    a = np.sin((ys - lat) / 2) ** 2 + np.cos(lat) * np.cos(ys) * np.sin((xs - lon) / 2) ** 2
    return int(ids[np.argmin(a)])  # haversine è monotona in `a`
