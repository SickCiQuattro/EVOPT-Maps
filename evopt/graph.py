import itertools

import numpy as np
import osmnx as ox

ox.settings.use_cache = False  # the expiring cache lives in evopt.cache; osmnx's own never expires


def load_graph(place):
    """Drivable road network with 'length', 'speed_kph' and 'travel_time' on every edge. It stays directed."""
    G = ox.graph_from_place(place, network_type="drive")
    G = ox.routing.add_edge_speeds(G)
    return ox.routing.add_edge_travel_times(G)


def haversine_m(lat, lon, lats, lons):
    """Distance in metres from one point to an array of points (degrees)."""
    lat, lon, lats, lons = map(np.radians, (lat, lon, lats, lons))
    a = np.sin((lats - lat) / 2) ** 2 + np.cos(lat) * np.cos(lats) * np.sin((lons - lon) / 2) ** 2
    return 2 * 6371000 * np.arcsin(np.sqrt(a))


def nearest_nodes(G, points):
    """For each (lat, lon), the nearest node and its distance in metres."""
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


def path_coords(G, path):
    """(lat, lon) coordinates of a path, following edge geometry when present."""
    coords = [(G.nodes[path[0]]["y"], G.nodes[path[0]]["x"])]
    for u, v in itertools.pairwise(path):
        edge = min(G.get_edge_data(u, v).values(), key=lambda d: d["travel_time"])
        geom = edge.get("geometry")
        if geom is None:
            coords.append((G.nodes[v]["y"], G.nodes[v]["x"]))
            continue
        points = [(y, x) for x, y in geom.coords]
        if _gap(points[-1], coords[-1]) < _gap(
            points[0], coords[-1]
        ):  # geometry stored in the opposite direction
            points.reverse()
        coords += points[1:]
    return coords


def _gap(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
