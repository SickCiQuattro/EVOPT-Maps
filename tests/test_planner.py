import random

import networkx as nx
import pytest

from evopt.planner import ALGORITHMS, Planner
from evopt.router import NoRouteError
from evopt.vehicle import Vehicle
from tests.graphs import grid
from tests.test_router import CAR, line

SMALL = Vehicle(capacity_kwh=0.5, mass_kg=1500, cda=0.6, max_charge_kw=50)


@pytest.fixture(scope="module")
def city():
    """Griglia 12×12 con 15 stazioni, batteria troppo piccola per attraversarla senza ricaricare."""
    G = grid(12, seed=3)
    for n in random.Random(5).sample(list(G.nodes), 15):
        G.nodes[n]["charger_kw"] = 50
    return G


def plan(G, algorithm, vehicle=SMALL, **kw):
    return Planner(G, vehicle, 20).plan(0, len(G) - 1, algorithm=algorithm, start_soc=1.0, min_soc=0.1, **kw)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_every_algorithm_returns_a_feasible_route(city, algorithm):
    r = plan(city, algorithm)
    assert r.path[0] == 0 and r.path[-1] == len(city) - 1
    assert r.arrival_soc >= 0.1 - 1e-9 and r.charges and r.time_s > 0
    assert r.stats["algorithm"] == algorithm


def test_astar_matches_dijkstra_and_expands_fewer_states(city):
    d, a = plan(city, "dijkstra"), plan(city, "astar")
    assert a.time_s == pytest.approx(d.time_s)
    assert a.stats["expanded"] < d.stats["expanded"]


def test_energy_aware_heuristic_keeps_the_optimum_and_prunes_more(city):
    t, e = plan(city, "astar"), plan(city, "astar_energy")
    assert e.time_s == pytest.approx(t.time_s)
    assert e.stats["expanded"] < t.stats["expanded"]


def test_weighted_astar_stays_within_its_bound(city):
    d, w = plan(city, "dijkstra"), plan(city, "wastar", weight=2.0)
    assert d.time_s - 1e-6 <= w.time_s <= 2.0 * d.time_s + 1e-6


def test_ara_star_history_improves_and_ends_optimal(city):
    d, r = plan(city, "dijkstra"), plan(city, "ara", eps=3.0, decrease=1.0)
    times = [h["time_s"] for h in r.history]
    assert len(times) >= 2 and times == sorted(times, reverse=True)
    assert r.time_s == pytest.approx(d.time_s) and r.history[-1]["bound"] == pytest.approx(1.0)


def test_exact_reference_agrees_with_the_reduced_search_within_discretisation(city):
    d, e = plan(city, "dijkstra"), plan(city, "exact")
    assert e.time_s <= 1.01 * d.time_s  # carica a passi di un livello: può restare di poco sopra
    assert d.time_s <= 1.15 * e.time_s


def test_naive_driver_is_never_faster_than_the_optimal_plan(city):
    assert plan(city, "greedy").time_s >= plan(city, "dijkstra").time_s - 1e-6


def test_naive_driver_loses_time_charging_to_80_percent_everywhere():
    G = line(30, stations=range(2, 30, 2))
    p = Planner(G, CAR, 20)
    kw = {"start_soc": 1.0, "min_soc": 0.1}
    assert p.plan(0, 29, algorithm="greedy", **kw).time_s > p.plan(0, 29, algorithm="astar", **kw).time_s


def test_naive_driver_charges_beyond_80_percent_when_that_is_not_enough_to_arrive():
    G = line(12, stations=[6])  # dopo il tratto fino alla stazione servono più dell'80% per arrivare
    r = Planner(G, CAR, 20).plan(0, 11, 1.0, 0.1, algorithm="greedy")
    assert r.charges[0][4] > 0.8 and r.arrival_soc >= 0.1 - 1e-9


def test_station_legs_are_computed_once_per_planner(city):
    p = Planner(city, SMALL, 20)
    p.plan(0, 143, algorithm="astar", start_soc=1.0, min_soc=0.1)
    after_first = p.leg_searches
    p.plan(5, 140, algorithm="astar", start_soc=1.0, min_soc=0.1)
    assert p.leg_searches - after_first == 2  # solo partenza e arrivo del nuovo viaggio


def test_pareto_legs_find_the_efficient_road_the_fastest_leg_would_miss():
    """Il nodo 1 si raggiunge in fretta (energivoro) o piano (parsimonioso): solo la seconda via arriva alla stazione 2."""
    G = nx.MultiDiGraph()
    for n, x in enumerate((0.0, 0.35, 0.6, 0.7)):
        G.add_node(n, x=x, y=45.0)

    def road(u, v, km, kph):
        G.add_edge(u, v, length=km * 1000, speed_kph=kph, travel_time=km * 1000 / (kph / 3.6))

    road(0, 1, 30, 130)
    road(0, 1, 31, 50)
    road(1, 2, 20, 90)
    road(2, 3, 5, 50)
    G.nodes[2]["charger_kw"] = 50
    car = Vehicle(capacity_kwh=8, mass_kg=1500, cda=0.6, max_charge_kw=50)
    kw = {"start_soc": 1.0, "min_soc": 0.1}
    with pytest.raises(NoRouteError):
        Planner(G, car, 20, legs="fastest").plan(0, 3, **kw)
    assert Planner(G, car, 20, legs="pareto").plan(0, 3, **kw).path == [0, 1, 2, 3]


def test_unknown_algorithm_is_rejected(city):
    with pytest.raises(ValueError, match="algorithm"):
        plan(city, "magic")
