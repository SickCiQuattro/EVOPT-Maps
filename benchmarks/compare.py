"""Confronta gli algoritmi di pianificazione su griglie sintetiche e, se in cache, su una città reale.

Uso: uv run python -m benchmarks.compare [--real "Pieve Emanuele, Italy"]

La prima ricerca di un Planner paga la tabella dei tratti tra stazioni; la si misura a parte ("cold")
e poi tutti gli algoritmi girano a cache calda, così il confronto è equo.
"""

import argparse
import random

from evopt.planner import ALGORITHMS, Planner
from evopt.router import NoRouteError
from evopt.vehicle import VEHICLES, Vehicle
from tests.graphs import grid

CAR = Vehicle(capacity_kwh=0.8, mass_kg=1500, cda=0.6, max_charge_kw=50)


def synthetic(n, stations):
    G = grid(n, seed=3)
    for s in random.Random(5).sample(list(G.nodes), stations):
        G.nodes[s]["charger_kw"] = 50
    return G, 0, len(G) - 1


def run(G, start, goal, vehicle, temp_c=20, start_soc=1.0, min_soc=0.1, legs="fastest", skip=()):
    planner = Planner(G, vehicle, temp_c, legs=legs)
    kw = {"start_soc": start_soc, "min_soc": min_soc}
    cold = planner.plan(start, goal, algorithm="dijkstra", **kw)
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
        f"Station-leg table, built once: {cold.stats['prep_ms']:.0f} ms ({planner.leg_searches} road searches)\n"
    )
    print("| algorithm | trip (min) | vs best | stops | states expanded | search ms |")
    print("|---|---|---|---|---|---|")
    for alg, r in results.items():
        if r is None:
            print(f"| {alg} | no route | | | | |")
        else:
            gap = f"+{100 * (r.time_s / best - 1):.1f}%" if r.time_s > best * 1.0005 else "best"
            print(
                f"| {alg} | {r.time_s / 60:.2f} | {gap} | {len(r.charges)} | {r.stats.get('expanded', 0)} | {r.stats['search_ms']:.1f} |"
            )
    ara = results.get("ara")
    if ara and ara.history:
        steps = ", ".join(
            f"eps {h['eps']:g}: {h['time_s'] / 60:.2f} min after {h['expanded']} states" for h in ara.history
        )
        print(f"\nARA* anytime: {steps}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", help="a city already in cache (graph and stations)")
    args = ap.parse_args()
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
