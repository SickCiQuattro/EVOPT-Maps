"""Compare the planning algorithms on synthetic grids and, when available, on real roads.

Usage: uv run python -m benchmarks.compare [--real "Pieve Emanuele, Italy"] [--local milano-torino]

A Planner's first search pays for the legs of the chargers it expands, so it is measured separately ("cold");
then every algorithm runs on a partly filled, warm table, which keeps the comparison fair.
"""

import argparse
import random
import time

from evopt.planner import ALGORITHMS, Planner
from evopt.router import NoRouteError
from evopt.search import alt_landmarks, ara_star, astar, dijkstra
from evopt.vehicle import VEHICLES, Vehicle
from tests.graphs import grid

CAR = Vehicle(capacity_kwh=0.8, mass_kg=1500, cda=0.6, max_charge_kw=50)


def synthetic(n, stations):
    G = grid(n, seed=3)
    for s in random.Random(5).sample(list(G.nodes), stations):
        G.nodes[s]["charger_kw"] = 50
    return G, 0, len(G) - 1


def run(
    G, start, goal, vehicle, temp_c=20, start_soc=1.0, min_soc=0.1, legs="fastest", skip=(), plug_in_s=180
):
    planner = Planner(G, vehicle, temp_c, legs=legs, plug_in_s=plug_in_s)
    kw = {"start_soc": start_soc, "min_soc": min_soc}
    cold = planner.plan(start, goal, algorithm="astar_potential", **kw)
    results = {}
    for alg in ALGORITHMS:
        if alg in skip:
            continue
        try:
            results[alg] = planner.plan(start, goal, algorithm=alg, **kw)
        except NoRouteError:
            results[alg] = None
    best = min(r.time_s for r in results.values() if r)
    print(
        f"First plan, cold (A* with exact potentials): {cold.stats['total_ms']:.0f} ms, "
        f"{cold.stats['leg_searches']} road searches (legs are computed only for stations the search reaches)\n"
    )
    print("| algorithm | trip (min) | vs best | stops | states expanded | prep ms | search ms |")
    print("|---|---|---|---|---|---|---|")
    for alg, r in results.items():
        if r is None:
            print(f"| {alg} | no route | | | | | |")
        else:
            gap = f"+{100 * (r.time_s / best - 1):.1f}%" if r.time_s > best * 1.0005 else "best"
            print(
                f"| {alg} | {r.time_s / 60:.2f} | {gap} | {len(r.charges)} | {r.stats.get('expanded', 0)} | {r.stats.get('prep_ms', 0):.0f} | {r.stats['search_ms']:.1f} |"
            )
    ara = results.get("ara")
    if ara and ara.history:
        steps = ", ".join(
            f"eps {h['eps']:g}: {h['time_s'] / 60:.2f} min after {h['expanded']} states" for h in ara.history
        )
        print(f"\nARA* anytime: {steps}")


def road_level(G, a, b):
    """Fastest route between two nodes of the road network: states expanded by each algorithm."""
    t = time.perf_counter()
    landmarks = alt_landmarks(G, k=8)
    print(f"ALT preprocessing, built once: {(time.perf_counter() - t) * 1000:.0f} ms (8 landmarks)\n")
    print("| algorithm | trip (min) | states expanded | ms |")
    print("|---|---|---|---|")
    runs = [
        ("Dijkstra", lambda: dijkstra(G, a, b)),
        ("A* straight line", lambda: astar(G, a, b)),
        ("A* + ALT", lambda: astar(G, a, b, landmarks=landmarks)),
        ("Weighted A* (w=2)", lambda: astar(G, a, b, weight=2.0)),
    ]
    for name, fn in runs:
        t = time.perf_counter()
        r = fn()
        print(f"| {name} | {r.time_s / 60:.2f} | {r.expanded} | {(time.perf_counter() - t) * 1000:.0f} |")
    t = time.perf_counter()
    steps = list(ara_star(G, a, b, eps=3.0, decrease=1.0))
    ms = (time.perf_counter() - t) * 1000
    first = steps[0]
    print(f"| ARA* first answer (w=3) | {first.time_s / 60:.2f} | {first.expanded} | |")
    print(f"| ARA* final (w=1) | {steps[-1].time_s / 60:.2f} | {steps[-1].expanded} | {ms:.0f} |")


def local(name, origin, target, vehicle, temp_c, start_soc, min_soc, legs):
    from evopt.data import load_network
    from evopt.graph import nearest_node

    G = load_network(f"local:{name}")  # with OCM_API_KEY the stations are completed from Open Charge Map
    chargers = sum("charger_kw" in d for _, d in G.nodes(data=True))
    a, b = nearest_node(G, *origin), nearest_node(G, *target)
    print(f"\n### {name}: {len(G)} nodes, {G.number_of_edges()} edges, {chargers} charger nodes\n")
    print("Road-level search between the two endpoints\n")
    road_level(G, a, b)
    print(f"\nElectric trip: {vehicle}, {temp_c} C, charge {start_soc:.0%} to {min_soc:.0%}, legs={legs}\n")
    run(
        G,
        a,
        b,
        VEHICLES[vehicle],
        temp_c=temp_c,
        start_soc=start_soc,
        min_soc=min_soc,
        legs=legs,
        skip=("exact",),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", help="a city already in cache (graph and stations)")
    ap.add_argument("--local", help="name of an extract made by benchmarks.extract (data/<name>.graphml)")
    ap.add_argument("--from", dest="origin", default="45.4642,9.1900", help="lat,lon (default: Milano Duomo)")
    ap.add_argument(
        "--to", dest="target", default="45.0620,7.6780", help="lat,lon (default: Torino Porta Nuova)"
    )
    ap.add_argument("--vehicle", default="Renault Twingo Electric")
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--start-soc", type=float, default=0.9)
    ap.add_argument("--min-soc", type=float, default=0.1)
    ap.add_argument("--legs", default="fastest", choices=("fastest", "pareto"))
    ap.add_argument("--synthetic", action="store_true", help="also run the synthetic grids")
    args = ap.parse_args()
    if args.local:
        pt = lambda v: tuple(float(x) for x in v.split(","))
        local(
            args.local,
            pt(args.origin),
            pt(args.target),
            args.vehicle,
            args.temp,
            args.start_soc,
            args.min_soc,
            args.legs,
        )
        if not args.synthetic:
            return
    for n, k in ((20, 20), (40, 40), (60, 80)):
        G, a, b = synthetic(n, k)
        print(f"\n### Grid {n}x{n}: {len(G)} nodes, {k} stations\n")
        run(G, a, b, CAR)
    if args.real:
        from evopt.data import load_network

        G = load_network(args.real)
        ns = list(G.nodes)
        a = ns[0]
        b = max(
            ns,
            key=lambda n: (G.nodes[n]["x"] - G.nodes[a]["x"]) ** 2 + (G.nodes[n]["y"] - G.nodes[a]["y"]) ** 2,
        )
        print(f"\n### {args.real}: {len(G)} nodes, Renault Twizy at -10 C, 13% charge\n")
        run(G, a, b, VEHICLES["Renault Twizy"], temp_c=-10, start_soc=0.13, min_soc=0.10)


if __name__ == "__main__":
    main()
