from shapely.geometry import LineString

from evopt.graph import path_coords
from tests.test_router import line


def test_path_coords_are_lat_lon_in_travel_order():
    assert path_coords(line(3), [0, 1, 2]) == [(45.0, 0.0), (45.0, 0.1), (45.0, 0.2)]


def test_path_coords_follow_edge_geometry_when_present():
    G = line(2)
    for _, _, d in G.edges(data=True):
        d["geometry"] = LineString([(0.0, 45.0), (0.05, 45.01), (0.1, 45.0)])
    assert path_coords(G, [0, 1]) == [(45.0, 0.0), (45.01, 0.05), (45.0, 0.1)]
    assert path_coords(G, [1, 0])[0] == (
        45.0,
        0.1,
    )  # l'arco 1->0 ha la stessa geometria, ma l'ordine segue il viaggio
