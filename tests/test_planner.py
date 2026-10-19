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
    assert r.arrival_soc >= 0.1 - 1e-9 and r.time_s > 0
    if algorithm != "wastar":  # entro il suo limite 2x può preferire un percorso lento senza soste
        assert r.charges
    assert r.stats["algorithm"] == algorithm


def test_astar_matches_dijkstra_and_expands_fewer_states(city):
    d, a = plan(city, "dijkstra"), plan(city, "astar")
    assert a.time_s == pytest.approx(d.time_s)
    assert a.stats["expanded"] < d.stats["expanded"]


def test_energy_aware_heuristic_keeps_the_optimum_and_prunes_more(city):
    t, e = plan(city, "astar"), plan(city, "astar_energy")
    assert e.time_s == pytest.approx(t.time_s)
    assert e.stats["expanded"] < t.stats["expanded"]


def test_exact_goal_potentials_keep_the_optimum_and_prune_hard(city):
    e, p = plan(city, "astar_energy"), plan(city, "astar_potential")
    assert p.time_s == pytest.approx(e.time_s)
    assert p.stats["expanded"] < e.stats["expanded"]


def test_dominance_pruning_never_changes_the_answer(city):
    on = Planner(city, SMALL, 20).plan(0, 143, 1.0, 0.1, algorithm="dijkstra")
    off = Planner(city, SMALL, 20, dominance=False).plan(0, 143, 1.0, 0.1, algorithm="dijkstra")
    assert on.time_s == pytest.approx(off.time_s) and on.stats["expanded"] < off.stats["expanded"]


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
    p.plan(0, 143, algorithm="astar", start_soc=1.0, min_soc=0.1)
    assert (
        p.leg_searches - after_first == 2
    )  # solo partenza e arrivo: i tratti tra stazioni sono già in tabella


def test_station_legs_are_computed_lazily_only_for_stations_the_search_reaches():
    G = line(40, stations=range(2, 40, 2))  # 19 stazioni, ma il viaggio è breve
    p = Planner(G, CAR, 20)
    p.plan(0, 6, algorithm="astar_potential", start_soc=1.0, min_soc=0.1)
    assert p.leg_searches < 19


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


@pytest.mark.parametrize("algorithm", ["dijkstra", "astar_potential", "exact", "greedy"])
def test_plug_in_time_is_paid_once_per_stop(algorithm):
    G = line(12, stations=[6])
    base = Planner(G, CAR, 20).plan(0, 11, 1.0, 0.1, algorithm=algorithm)
    slow = Planner(G, CAR, 20, plug_in_s=600).plan(0, 11, 1.0, 0.1, algorithm=algorithm)
    assert len(slow.charges) == len(base.charges) == 1
    assert slow.charges[0][2] == pytest.approx(base.charges[0][2] + 600)
    assert slow.time_s == pytest.approx(base.time_s + 600)


def test_plug_in_time_discourages_useless_short_stops(city):
    free = Planner(city, SMALL, 20).plan(0, 143, 1.0, 0.1, algorithm="astar_potential")
    costly = Planner(city, SMALL, 20, plug_in_s=900).plan(0, 143, 1.0, 0.1, algorithm="astar_potential")
    assert len(costly.charges) <= len(free.charges)
    assert costly.time_s >= free.time_s


def test_weighted_search_makes_no_pointless_stops_once_a_stop_has_a_cost(city):
    """Con stop gratuiti una ricerca golosa ne fa molti; col tempo di collegamento torna sensata."""
    p = Planner(city, SMALL, 20, plug_in_s=180)
    opt = p.plan(0, 143, 1.0, 0.1, algorithm="astar_potential")
    w = p.plan(0, 143, 1.0, 0.1, algorithm="wastar", weight=3.0)
    assert w.time_s <= 3.0 * opt.time_s + 1e-6
    assert len(w.charges) <= len(opt.charges) + 1


def test_station_table_keeps_no_paths_but_the_route_still_has_them(city):
    p = Planner(city, SMALL, 20)
    r = p.plan(0, 143, 1.0, 0.1, algorithm="astar")
    assert r.path[0] == 0 and r.path[-1] == 143
    assert all(leg.path is None for legs in p._table.values() for ls in legs.values() for leg in ls)
    assert all(b in city[a] for a, b in zip(r.path, r.path[1:]))  # ogni passo è un arco vero


def test_station_table_can_be_saved_and_reloaded(city, tmp_path):
    first = Planner(city, SMALL, 20)
    a = first.plan(0, 143, 1.0, 0.1, algorithm="astar")
    assert first.save_table(tmp_path / "t.pkl")
    again = Planner(city, SMALL, 20)
    assert again.load_table(tmp_path / "t.pkl")
    b = again.plan(0, 143, 1.0, 0.1, algorithm="astar")
    assert b.time_s == pytest.approx(a.time_s) and b.path == a.path
    assert again.leg_searches == 2  # solo partenza e arrivo: i tratti tra stazioni vengono dal disco


def test_saved_table_is_ignored_when_the_scenario_differs(city, tmp_path):
    Planner(city, SMALL, 20).plan(0, 143, 1.0, 0.1, algorithm="astar")
    p = Planner(city, SMALL, 20)
    p.plan(0, 143, 1.0, 0.1, algorithm="astar")
    p.save_table(tmp_path / "t.pkl")
    assert not Planner(city, SMALL, 5).load_table(tmp_path / "t.pkl")  # altra temperatura
    assert not Planner(city, SMALL, 20, legs="pareto").load_table(tmp_path / "t.pkl")
    (tmp_path / "bad.pkl").write_bytes(b"not a pickle")
    assert not Planner(city, SMALL, 20).load_table(tmp_path / "bad.pkl")
    assert not Planner(city, SMALL, 20).load_table(tmp_path / "missing.pkl")


def test_charging_slows_down_above_the_knee_so_the_last_percent_costs_more():
    G = line(12)
    G.nodes[6]["charger_kw"] = 150
    fast = Vehicle(capacity_kwh=10, mass_kg=1500, cda=0.6, max_charge_kw=150, taper_from=0.5, taper_to=0.2)
    flat = Vehicle(capacity_kwh=10, mass_kg=1500, cda=0.6, max_charge_kw=150)
    a = Planner(G, fast, 20).plan(0, 11, 1.0, 0.1, algorithm="astar_potential")
    b = Planner(G, flat, 20).plan(0, 11, 1.0, 0.1, algorithm="astar_potential")
    assert a.charges[0][1] >= b.charges[0][1] * 0.99  # stessa energia circa, da una carica più lenta
    assert a.charges[0][2] > b.charges[0][2]


@pytest.mark.parametrize("algorithm", ["dijkstra", "astar_potential", "exact", "greedy"])
def test_tapered_charging_is_consistent_across_algorithms(algorithm):
    G = line(12)
    G.nodes[6]["charger_kw"] = 150
    car = Vehicle(capacity_kwh=10, mass_kg=1500, cda=0.6, max_charge_kw=150, taper_from=0.5, taper_to=0.2)
    ref = Planner(G, car, 20).plan(0, 11, 1.0, 0.1, algorithm="dijkstra")
    r = Planner(G, car, 20).plan(0, 11, 1.0, 0.1, algorithm=algorithm)
    assert (
        r.time_s >= ref.time_s * 0.99
    )  # nessun algoritmo può battere l'ottimo (tolleranza di discretizzazione)


def hill(rise_m):
    """Strada di 60 km (7 nodi) con una colonnina a metà, che sale di `rise_m` da un capo all'altro."""
    G = line(7, stations=[3])
    for n in G.nodes:
        G.nodes[n]["elevation"] = rise_m * n / 6
    return G


def test_a_climb_costs_energy_and_a_descent_saves_some():
    up, flat, down = (Planner(hill(r), CAR, 20)._edges(0)[0][3] for r in (400, 0, -400))
    assert up > flat > down


def test_elevation_can_be_switched_off_to_compare():
    on = Planner(hill(400), CAR, 20)._edges(0)[0][3]
    off = Planner(hill(400), CAR, 20, elevation=False)._edges(0)[0][3]
    assert on > off == pytest.approx(Planner(hill(0), CAR, 20)._edges(0)[0][3])


def test_a_climb_that_does_not_fit_in_the_battery_forces_a_stop():
    kw = {"start_soc": 1.0, "min_soc": 0.1, "algorithm": "astar_potential"}
    assert Planner(hill(0), CAR, 20).plan(0, 6, **kw).charges == []  # in piano ci si arriva senza fermarsi
    assert Planner(hill(400), CAR, 20).plan(0, 6, **kw).charges  # in salita no
    assert Planner(hill(-400), CAR, 20).plan(0, 6, **kw).charges == []  # in discesa meno ancora


def test_unreasonable_dem_glitches_are_limited_to_a_plausible_grade():
    G = line(2)
    G.nodes[0]["elevation"], G.nodes[1]["elevation"] = 0.0, 9000.0  # un buco nel DEM: 9 km di salita in 10 km
    arc = Planner(G, CAR, 20)._edges(0)[0]
    capped = CAR.edge_energy_kwh(10_000, 100, 360, 20, rise_m=0.12 * 10_000)
    assert arc[3] == pytest.approx(capped)


def test_the_saved_table_knows_about_elevation(tmp_path):
    a, b = Planner(hill(400), CAR, 20), Planner(hill(400), CAR, 20, elevation=False)
    assert a.fingerprint() != b.fingerprint() != Planner(hill(0), CAR, 20).fingerprint()


def test_naive_driver_skips_a_much_slower_charger_when_a_decent_one_is_reachable():
    G = line(9, stations=[])  # 80 km: serve una sosta
    G.nodes[5]["charger_kw"] = 3.7  # più vicina alla meta ma lentissima
    G.nodes[4]["charger_kw"] = 50  # un po' più indietro, veloce
    r = Planner(G, CAR, 20).plan(0, 8, 1.0, 0.1, algorithm="greedy")
    assert [c[0] for c in r.charges] == [4]


def test_naive_driver_still_uses_a_slow_charger_if_it_is_the_only_one():
    G = line(9, stations=[])
    G.nodes[5]["charger_kw"] = 3.7
    r = Planner(G, CAR, 20).plan(0, 8, 1.0, 0.1, algorithm="greedy")
    assert [c[0] for c in r.charges] == [5]
