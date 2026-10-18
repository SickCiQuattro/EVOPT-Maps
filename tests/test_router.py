import networkx as nx
import pytest

from evopt.graph import nearest_node
from evopt.router import NoRouteError, plan_route
from evopt.vehicle import Vehicle

CAR = Vehicle(capacity_kwh=10, mass_kg=1500, cda=0.6, max_charge_kw=50)


def line(n, stations=(), both_ways=True):
    """Strada dritta di n nodi a 10 km l'uno dall'altro, percorsa a 100 km/h."""
    G = nx.MultiDiGraph()
    for i in range(n):
        G.add_node(i, x=0.1 * i, y=45.0)
    for i in range(n - 1):
        for a, b in ((i, i + 1), (i + 1, i)) if both_ways else ((i, i + 1),):
            G.add_edge(a, b, length=10_000, speed_kph=100, travel_time=360)
    for s in stations:
        G.nodes[s]["charger_kw"] = 50
    return G


def test_short_trip_needs_no_charge():
    r = plan_route(line(4), 0, 3, CAR)
    assert r.path == [0, 1, 2, 3]
    assert r.charges == []
    assert r.distance_m == 30_000
    assert r.time_s == 3 * 360
    assert r.arrival_soc >= 0.1


def test_long_trip_charges_at_the_only_station():
    r = plan_route(line(12, stations=[6]), 0, 11, CAR)
    assert r.path == list(range(12))
    assert [c[0] for c in r.charges] == [6]
    assert r.charges[0][1] > 0 and r.time_s > 11 * 360
    assert r.arrival_soc >= 0.1


def test_unreachable_without_station():
    with pytest.raises(NoRouteError):
        plan_route(line(12), 0, 11, CAR)


def test_one_way_streets_are_respected():
    with pytest.raises(NoRouteError):
        plan_route(line(4, both_ways=False), 3, 0, CAR)


def test_min_arrival_soc_is_honoured():
    # 5 tratti consumano ~6.6 kWh su 10: con riserva 50% serve la stazione
    G = line(6, stations=[3])
    assert plan_route(G, 0, 5, CAR, min_soc=0.1).charges == []
    assert plan_route(G, 0, 5, CAR, min_soc=0.5).charges != []


def test_nearest_node():
    G = line(5)
    assert nearest_node(G, 45.0, 0.31) == 3
